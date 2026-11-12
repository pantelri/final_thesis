"""Annotation page — data loading + form controller (no UI construction).

`load_context` snapshots everything the form needs out of one DB session so no
ORM object is touched after the session closes. `FormController` owns the
per-connection mutable form state, the field-change handlers, the LLM passage
suggestion flow, and persistence. The presentation lives in ``annotate_form``;
the page wiring in ``annotate``.
"""
from datetime import datetime, timezone

from nicegui import run, ui
from sqlalchemy.exc import IntegrityError

from ..assignment import (
    ANNOTATION_QUOTA, MAX_ANNOTATIONS_PER_ITEM, assign_next_item, count_done,
    pick_item, quota_state,
)
from ..database import SessionLocal
from ..llm_suggest import SuggestError, request_suggestions
from ..models import (
    Annotation, Annotator, ApplicableType, Company,
    FulfilledType, IrrelevantElement, LengthJudgment, Obligation,
    PassageSentence, SuggestedPassage,
)
from .review import review_items


def _company_year(company_id: str) -> str | None:
    """Fiscal year is encoded as the trailing _YYYY of the company id."""
    parts = company_id.rsplit("_", 1)
    return parts[1] if len(parts) == 2 and parts[1].isdigit() else None


def load_context(db, aid: int, voluntary: bool = False) -> tuple[dict | None, dict]:
    """Snapshot the next item + page meta; ctx is None when nothing is served —
    either the personal quota is reached (and the annotator has not opted in to
    continue voluntarily) or no item is left. meta then carries n_review and
    more_available."""
    ann = db.get(Annotator, aid)
    ann_label = ann.label or f"Annotator #{aid}"
    done_count = count_done(db, aid)
    q = quota_state(done_count, ANNOTATION_QUOTA, voluntary)
    meta = {"done_count": done_count, "quota": q, "max_per_item": MAX_ANNOTATIONS_PER_ITEM,
            "ann_label": ann_label}

    if q["blocked"]:
        nxt, _ = pick_item(db, aid)          # peek only, no reservation
        meta["more_available"] = nxt is not None
        meta["n_review"] = len(review_items(db, aid))
        return None, meta

    item, phase, _ = assign_next_item(db, aid)
    if item is None:
        meta["more_available"] = False
        meta["n_review"] = len(review_items(db, aid))
        return None, meta

    obligation = db.get(Obligation, item.obligation_id)
    company = db.get(Company, item.company_id)
    sentences_raw = (
        db.query(PassageSentence)
        .filter_by(item_id=item.id)
        .order_by(PassageSentence.idx)
        .all()
    )
    ctx = {
        "item_id": item.id,
        "passage_text": item.passage_text,
        "company_id": item.company_id,
        "ob_id": item.obligation_id,
        "ob_title": obligation.title_de if obligation else item.obligation_id,
        "ob_legal": (obligation.legal_basis or "") if obligation else "",
        "ob_criterion": (obligation.verification_criterion or "") if obligation else "",
        "co_name": company.name if company else item.company_id,
        "has_pdf": bool(company and company.pdf_path),
        "year": _company_year(item.company_id),
        "phase": phase,
        "sents": [
            {"idx": s.idx, "type": s.element_type.value, "text": s.text}
            for s in sentences_raw
        ],
    }
    return ctx, meta


class FormController:
    """Per-connection form state + handlers; widgets register in ``refs`` during
    ``build_form`` and handlers run only after that completes."""

    def __init__(self, aid: int, ctx: dict) -> None:
        self.aid = aid
        self.ctx = ctx
        self.state: dict = {
            "is_relevant": None, "length_judgment": None, "is_applicable": None,
            "is_fulfilled": None, "irrelevant_indices": set(),
            "missing_info": "", "selected_suggestions": [],  # {text, source, reason}
        }
        self.refs: dict = {}

    def validate(self) -> tuple[bool, str]:
        s = self.state
        if s["is_relevant"] is None:
            return False, "Bitte Relevanz angeben (Frage 1)."
        if s["length_judgment"] is None:
            return False, "Bitte Länge des Abschnitts angeben (Frage 1)."
        if s["is_applicable"] is None:
            return False, "Bitte Anwendbarkeit angeben (Frage 2)."
        if s["is_applicable"] == "yes" and s["is_fulfilled"] is None:
            return False, "Bitte Erfüllung angeben (Frage 3)."
        return True, ""

    def update_submit(self) -> None:
        valid, msg = self.validate()
        self.refs["submit_btn"].set_enabled(valid)
        self.refs["validation_msg"].set_text("" if valid else msg)

    def set_relevant(self, val: str) -> None:
        self.state["is_relevant"] = val
        self.update_submit()

    def on_length_change(self, val: str) -> None:
        self.state["length_judgment"] = val
        self.refs["too_long_section"].set_visibility(val == "too_long")
        self.refs["too_short_section"].set_visibility(val == "too_short")
        if val != "too_long":
            self.state["irrelevant_indices"].clear()
        if val != "too_short":
            self.state["missing_info"] = ""
            self.state["selected_suggestions"].clear()
            self.refs["suggestions_container"].clear()
        self.update_submit()

    def on_applicable_change(self, val: str) -> None:
        self.state["is_applicable"] = val
        self.refs["fulfilled_card"].set_visibility(val == "yes")
        if val != "yes":
            self.state["is_fulfilled"] = None
            self.refs["fulfilled_radio"].value = None
        self.update_submit()

    def set_fulfilled(self, val: str) -> None:
        self.state["is_fulfilled"] = val
        self.update_submit()

    def set_missing_info(self, val: str) -> None:
        self.state["missing_info"] = val

    def on_irrelevant_toggle(self, idx: int, checked: bool) -> None:
        if checked:
            self.state["irrelevant_indices"].add(idx)
        else:
            self.state["irrelevant_indices"].discard(idx)

    def toggle_suggestion(self, sg: dict, checked: bool) -> None:
        sel = self.state["selected_suggestions"]
        if checked and sg not in sel:
            sel.append(sg)
        elif not checked and sg in sel:
            sel.remove(sg)

    def render_suggestions(self, suggestions: list[dict]) -> None:
        container = self.refs["suggestions_container"]
        container.clear()
        with container:
            if not suggestions:
                ui.label("Keine passenden Textstellen gefunden.").classes(
                    "text-sm text-gray-500")
                return
            ui.label("Passende Textstellen auswählen:").classes(
                "text-sm font-medium text-gray-700")
            for sg in suggestions:
                with ui.row().classes("items-start gap-2 py-0.5"):
                    ui.checkbox(
                        "", on_change=lambda e, sg=sg: self.toggle_suggestion(sg, e.value)
                    ).props("dense")
                    with ui.column().classes("gap-0"):
                        text = sg["text"]
                        ui.label(text[:300] + ("…" if len(text) > 300 else "")).classes(
                            "text-sm text-gray-800 leading-snug")
                        meta = " · ".join(p for p in (sg.get("source"), sg.get("reason")) if p)
                        if meta:
                            ui.label(meta).classes("text-xs text-gray-400")

    async def fetch_suggestions(self) -> None:
        note = (self.state["missing_info"] or "").strip()
        if not note:
            ui.notify("Bitte zuerst beschreiben, was fehlt.", color="warning")
            return
        self.refs["suggest_btn"].set_enabled(False)
        self.refs["suggest_spinner"].set_visibility(True)
        self.refs["suggestions_container"].clear()
        self.state["selected_suggestions"].clear()
        try:
            suggestions = await run.io_bound(
                request_suggestions, note, self.ctx["passage_text"], self.ctx["company_id"])
            self.render_suggestions(suggestions)
        except SuggestError as exc:
            ui.notify(str(exc), color="negative", multi_line=True)
        except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the user
            ui.notify(f"Unerwarteter Fehler: {exc}", color="negative", multi_line=True)
        finally:
            self.refs["suggest_spinner"].set_visibility(False)
            self.refs["suggest_btn"].set_enabled(True)

    def submit(self) -> None:
        valid, msg = self.validate()
        if not valid:
            ui.notify(msg, color="warning")
            return
        if self._persist():
            ui.navigate.to("/annotate")

    def _persist(self) -> bool:
        s = self.state
        db = SessionLocal()
        try:
            annotation = Annotation(
                item_id=self.ctx["item_id"],
                annotator_id=self.aid,
                is_relevant=(s["is_relevant"] == "yes"),
                length_judgment=LengthJudgment(s["length_judgment"]),
                is_applicable=ApplicableType(s["is_applicable"]),
                is_fulfilled=(FulfilledType(s["is_fulfilled"]) if s["is_fulfilled"] else None),
                comment=self.refs["comment"].value.strip() or None,
                missing_info=(
                    s["missing_info"].strip()
                    if s["length_judgment"] == "too_short" and s["missing_info"].strip()
                    else None
                ),
                submitted_at=datetime.now(timezone.utc),
            )
            db.add(annotation)
            db.flush()  # populate annotation.id

            for idx in s["irrelevant_indices"]:
                db.add(IrrelevantElement(annotation_id=annotation.id, sentence_idx=idx))

            if s["length_judgment"] == "too_short":
                for sg in s["selected_suggestions"]:
                    db.add(SuggestedPassage(
                        annotation_id=annotation.id,
                        passage_text=sg["text"],
                        source_ref=sg.get("source") or None,
                    ))

            db.commit()
            ui.notify("Annotation gespeichert! Nächste Einheit wird geladen.", color="positive")
            return True
        except IntegrityError:
            db.rollback()
            ui.notify("Diese Einheit wurde bereits annotiert. Nächste Einheit wird geladen.",
                      color="info")
            return True
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            ui.notify(f"Fehler beim Speichern: {exc}", color="negative")
            return False
        finally:
            db.close()
