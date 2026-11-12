"""Re-review page — let an annotator revisit their own judgments that may need a fresh
decision.

Two triggers (an item can match both):
  * STALE RELEVANCE — the annotator marked the passage not-relevant (is_relevant=False)
    yet judged the obligation applicable=yes. The originally-shown passage was "too short"
    and better evidence was later folded in by rebuild_passages, so the flag may be stale.
  * DROPPED "PARTIALLY" — the annotator chose is_fulfilled='partially', which is being
    removed; they must re-decide fulfilled (Ja) or not_fulfilled (Nein).

The annotator sees the current (rebuilt) passage with their previous answers pre-filled
(fulfillment left blank when it was 'partially', forcing a choice) and UPDATEs the existing
annotation in place (no new row).
"""
from datetime import datetime, timezone

from nicegui import ui
from sqlalchemy import and_, or_

from ..database import SessionLocal
from ..layout import render_header
from ..models import (
    Annotation, AnnotationItem, ApplicableType, Company, FulfilledType,
    LengthJudgment, Obligation,
)
from ..session import annotator_id, require_auth, require_consent


def review_items(db, aid: int) -> list[dict]:
    """Snapshots of this annotator's items needing re-review (stale relevance OR partially)."""
    rows = (
        db.query(Annotation, AnnotationItem, Obligation, Company)
        .join(AnnotationItem, Annotation.item_id == AnnotationItem.id)
        .join(Obligation, AnnotationItem.obligation_id == Obligation.id)
        .join(Company, AnnotationItem.company_id == Company.id)
        .filter(Annotation.annotator_id == aid,
                Annotation.reviewed_at.is_(None),  # already-revisited items drop out
                or_(and_(Annotation.is_relevant.is_(False),
                         Annotation.is_applicable == ApplicableType.yes),
                    Annotation.is_fulfilled == FulfilledType.partially))
        .order_by(AnnotationItem.company_id, AnnotationItem.obligation_id)
        .all()
    )
    out = []
    for ann, item, obl, comp in rows:
        was_partially = ann.is_fulfilled == FulfilledType.partially
        reasons = []
        if ann.is_relevant is False and ann.is_applicable == ApplicableType.yes:
            reasons.append("Abschnitt wurde seit Ihrer Bewertung ergänzt")
        if was_partially:
            reasons.append("Option „Teilweise“ entfällt – bitte „Ja“ oder „Nein“ wählen")
        out.append({
            "item_id": item.id, "ob_id": obl.id, "ob_title": obl.title_de,
            "ob_legal": obl.legal_basis or "", "company": comp.name,
            "passage_text": item.passage_text, "reason": " · ".join(reasons),
            "is_relevant": "yes" if ann.is_relevant else "no",
            "length_judgment": ann.length_judgment.value if ann.length_judgment else None,
            "is_applicable": ann.is_applicable.value if ann.is_applicable else None,
            # blank the fulfillment radio when it was 'partially' so a fresh choice is required
            "is_fulfilled": None if was_partially or not ann.is_fulfilled else ann.is_fulfilled.value,
            "comment": ann.comment or "",
        })
    return out


def _save(item_id: int, aid: int, st: dict) -> bool:
    if st["is_relevant"] is None or st["length_judgment"] is None or st["is_applicable"] is None:
        ui.notify("Bitte Relevanz, Länge und Anwendbarkeit angeben.", color="warning")
        return False
    if st["is_applicable"] == "yes" and not st["is_fulfilled"]:
        ui.notify("Bitte Erfüllung angeben (Pflicht ist anwendbar).", color="warning")
        return False
    db = SessionLocal()
    try:
        ann = (db.query(Annotation)
               .filter_by(item_id=item_id, annotator_id=aid).first())
        if ann is None:
            ui.notify("Annotation nicht gefunden.", color="negative")
            return False
        ann.is_relevant = st["is_relevant"] == "yes"
        ann.length_judgment = LengthJudgment(st["length_judgment"])
        ann.is_applicable = ApplicableType(st["is_applicable"])
        ann.is_fulfilled = (FulfilledType(st["is_fulfilled"])
                            if st["is_applicable"] == "yes" and st["is_fulfilled"] else None)
        ann.comment = (st["comment"].strip() or None) if st.get("comment") else ann.comment
        now = datetime.now(timezone.utc)
        ann.submitted_at = now
        ann.reviewed_at = now  # mark revisited → drops out of the re-review queue
        db.commit()
        ui.notify("Aktualisiert. Vielen Dank!", color="positive")
        return True
    except Exception as exc:  # noqa: BLE001 — surface to annotator
        db.rollback()
        ui.notify(f"Fehler beim Speichern: {exc}", color="negative")
        return False
    finally:
        db.close()


def _render_item(d: dict, aid: int) -> None:
    st = {"is_relevant": d["is_relevant"], "length_judgment": d["length_judgment"],
          "is_applicable": d["is_applicable"], "is_fulfilled": d["is_fulfilled"],
          "comment": d["comment"]}
    with ui.card().classes("w-full mb-4"):
        with ui.row().classes("items-center gap-2"):
            ui.badge(d["ob_id"]).props("color=indigo")
            ui.label(d["ob_title"]).classes("text-base font-semibold")
            ui.badge(d["company"]).props("color=grey-7 outline")
        if d["ob_legal"]:
            ui.label(f"Rechtsgrundlage: {d['ob_legal']}").classes("text-sm text-gray-600")
        if d["reason"]:
            ui.label(d["reason"]).classes("text-xs text-amber-700 mt-1")
        ui.separator()
        ui.label("Aktueller Textabschnitt (nach Überarbeitung):").classes(
            "text-xs font-semibold text-gray-500 uppercase mt-2")
        ui.markdown(d["passage_text"]).classes("text-sm leading-relaxed")
        ui.separator().classes("my-2")

        ui.label("Ist dieser Abschnitt relevant für die Pflicht?").classes("font-medium text-gray-700")
        ui.radio({"yes": "Ja", "no": "Nein"}, value=st["is_relevant"],
                 on_change=lambda e: st.update(is_relevant=e.value)).props("inline")
        ui.label("Länge des Abschnitts?").classes("font-medium text-gray-700 mt-2")
        ui.radio({"ok": "Passend", "too_short": "Zu kurz", "too_long": "Zu lang"},
                 value=st["length_judgment"],
                 on_change=lambda e: st.update(length_judgment=e.value)).props("inline")
        ui.label("Muss die Gesellschaft diese Pflicht erfüllen?").classes("font-medium text-gray-700 mt-2")
        ui.radio({"yes": "Ja", "no": "Nein", "unsure": "Unklar"}, value=st["is_applicable"],
                 on_change=lambda e: st.update(is_applicable=e.value)).props("inline")
        ui.label("Ist die Pflicht ausreichend erfüllt? (falls anwendbar)").classes(
            "font-medium text-gray-700 mt-2")
        ui.radio({"yes": "Ja", "no": "Nein"}, value=st["is_fulfilled"],
                 on_change=lambda e: st.update(is_fulfilled=e.value)).props("inline")

        btn = ui.button("Aktualisieren").props("color=indigo")
        btn.on_click(lambda _, iid=d["item_id"], s=st, b=btn:
                     (b.set_enabled(False) if _save(iid, aid, s) else b.set_enabled(True)))


@ui.page("/review")
def review_page() -> None:
    if not require_auth() or not require_consent():
        return
    aid = annotator_id()
    db = SessionLocal()
    try:
        from ..models import Annotator
        ann = db.get(Annotator, aid)
        label = (ann.label if ann else None) or f"Annotator #{aid}"
        items = review_items(db, aid)
    finally:
        db.close()

    render_header(label)
    with ui.column().classes("max-w-3xl mx-auto px-4 pb-12 gap-2 w-full"):
        ui.label("Einheiten zur erneuten Überprüfung").classes("text-xl font-semibold mt-4")
        ui.label(
            "Bitte prüfen Sie Ihre Bewertung erneut – entweder weil der Textabschnitt seit "
            "Ihrer Bewertung ergänzt wurde, oder weil die Antwortoption „Teilweise“ entfällt "
            "und Sie sich für „Ja“ oder „Nein“ entscheiden müssen."
        ).classes("text-sm text-gray-500 mb-2")
        if not items:
            ui.label("Aktuell nichts zu überprüfen. Vielen Dank!").classes("text-gray-500")
            ui.button("Zurück", on_click=lambda: ui.navigate.to("/annotate")).props("flat color=indigo")
            return
        for d in items:
            _render_item(d, aid)
