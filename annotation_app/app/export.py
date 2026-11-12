"""
Flat CSV exports of the annotation data (Milestone 5).

Three views, each one row per record, all joined to unit (annotation_item),
company and obligation so the files are self-contained for analysis:

  annotations.csv          one row per (item × annotator) judgment
  irrelevant_sentences.csv one row per sentence an annotator marked irrelevant
  suggested_passages.csv   one row per alternative passage chosen in the
                           "text too short" flow

`build_bundle()` returns a ZIP of all three plus a short README, so the whole
gold standard can be downloaded in one click.  Everything is built in memory;
no temp files are written.
"""
import csv
import io
import zipfile
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import (
    Annotation,
    AnnotationItem,
    Annotator,
    Company,
    IrrelevantElement,
    Obligation,
    PassageSentence,
    SuggestedPassage,
)


def _enum(value) -> str:
    """SQLAlchemy Enum value -> its .value string, '' for None."""
    return value.value if value is not None else ""


def _bool(value) -> str:
    return "" if value is None else ("true" if value else "false")


def _iso(value) -> str:
    return value.isoformat() if value is not None else ""


def _fiscal_year(company_id: str) -> str:
    """Year encoded as the trailing _YYYY suffix of the company id."""
    parts = company_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[1]
    return ""


def _csv_bytes(header: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    # utf-8-sig so Excel opens German umlauts correctly
    return buf.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# annotations.csv  — main flat table, one row per judgment
# ---------------------------------------------------------------------------

def build_annotations_csv(db: Session) -> bytes:
    header = [
        "annotation_id", "item_id",
        "company_id", "company_name", "fiscal_year",
        "obligation_id", "obligation_title", "legal_basis", "category",
        "in_overlap_set", "stratum",
        "annotator_id", "annotator_label",
        "is_relevant", "length_judgment", "is_applicable", "is_fulfilled",
        "comment", "missing_info",
        "n_irrelevant_sentences", "n_suggested_passages",
        "submitted_at", "passage_text",
    ]

    rows = (
        db.query(Annotation, AnnotationItem, Company, Obligation, Annotator)
        .join(AnnotationItem, Annotation.item_id == AnnotationItem.id)
        .join(Company, AnnotationItem.company_id == Company.id)
        .join(Obligation, AnnotationItem.obligation_id == Obligation.id)
        .join(Annotator, Annotation.annotator_id == Annotator.id)
        .order_by(AnnotationItem.id, Annotation.annotator_id)
        .all()
    )

    out = []
    for ann, item, company, obl, annotator in rows:
        out.append([
            ann.id, item.id,
            company.id, company.name, _fiscal_year(company.id),
            obl.id, obl.title_de, obl.legal_basis or "", obl.category or "",
            _bool(item.in_overlap_set), item.stratum or "",
            annotator.id, annotator.label or "",
            _bool(ann.is_relevant), _enum(ann.length_judgment),
            _enum(ann.is_applicable), _enum(ann.is_fulfilled),
            ann.comment or "", ann.missing_info or "",
            len(ann.irrelevant_elements), len(ann.suggested_passages),
            _iso(ann.submitted_at), item.passage_text,
        ])
    return _csv_bytes(header, out)


# ---------------------------------------------------------------------------
# irrelevant_sentences.csv  — one row per marked-irrelevant sentence
# ---------------------------------------------------------------------------

def build_irrelevant_csv(db: Session) -> bytes:
    header = [
        "annotation_id", "item_id",
        "company_id", "fiscal_year", "obligation_id",
        "annotator_id", "annotator_label",
        "sentence_idx", "sentence_text", "submitted_at",
    ]

    # Lookup table for sentence text keyed by (item_id, idx).
    sentence_text: dict[tuple[int, int], str] = {
        (s.item_id, s.idx): s.text
        for s in db.query(PassageSentence).all()
    }

    rows = (
        db.query(IrrelevantElement, Annotation, AnnotationItem, Annotator)
        .join(Annotation, IrrelevantElement.annotation_id == Annotation.id)
        .join(AnnotationItem, Annotation.item_id == AnnotationItem.id)
        .join(Annotator, Annotation.annotator_id == Annotator.id)
        .order_by(AnnotationItem.id, Annotation.annotator_id, IrrelevantElement.sentence_idx)
        .all()
    )

    out = []
    for irr, ann, item, annotator in rows:
        out.append([
            ann.id, item.id,
            item.company_id, _fiscal_year(item.company_id), item.obligation_id,
            annotator.id, annotator.label or "",
            irr.sentence_idx,
            sentence_text.get((item.id, irr.sentence_idx), ""),
            _iso(ann.submitted_at),
        ])
    return _csv_bytes(header, out)


# ---------------------------------------------------------------------------
# suggested_passages.csv  — one row per LLM-suggested passage the annotator kept
# ---------------------------------------------------------------------------

def build_suggested_csv(db: Session) -> bytes:
    header = [
        "suggestion_id", "annotation_id", "item_id",
        "company_id", "fiscal_year", "obligation_id",
        "annotator_id", "annotator_label",
        "missing_info", "passage_text", "source_ref", "created_at",
    ]

    rows = (
        db.query(SuggestedPassage, Annotation, AnnotationItem, Annotator)
        .join(Annotation, SuggestedPassage.annotation_id == Annotation.id)
        .join(AnnotationItem, Annotation.item_id == AnnotationItem.id)
        .join(Annotator, Annotation.annotator_id == Annotator.id)
        .order_by(AnnotationItem.id, Annotation.annotator_id, SuggestedPassage.id)
        .all()
    )

    out = []
    for sug, ann, item, annotator in rows:
        out.append([
            sug.id, ann.id, item.id,
            item.company_id, _fiscal_year(item.company_id), item.obligation_id,
            annotator.id, annotator.label or "",
            ann.missing_info or "", sug.passage_text, sug.source_ref or "",
            _iso(sug.created_at),
        ])
    return _csv_bytes(header, out)


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------

def timestamp() -> str:
    """UTC timestamp for filenames, e.g. 20260611T1530Z."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_bundle(db: Session) -> bytes:
    """All three CSVs + a README in one ZIP."""
    ts = timestamp()
    readme = (
        "HGB-Annotation – Export\n"
        f"Erstellt: {ts} (UTC)\n\n"
        "Dateien:\n"
        "  annotations.csv          Eine Zeile je (Einheit x Annotator)-Urteil.\n"
        "                           Fuer das Inter-Annotator-Agreement die Einheiten\n"
        "                           (item_id) mit >= 2 Urteilen heranziehen und je\n"
        "                           Label-Dimension ueber annotator_id pivotieren.\n"
        "  irrelevant_sentences.csv Eine Zeile je als irrelevant markiertem Satz.\n"
        "  suggested_passages.csv   Eine Zeile je zusaetzlich gewaehlter Textstelle\n"
        "                           (Flow 'Text zu kurz').\n\n"
        "Kodierung: UTF-8 (mit BOM, Excel-kompatibel). Trennzeichen: Komma.\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", readme)
        zf.writestr("annotations.csv", build_annotations_csv(db))
        zf.writestr("irrelevant_sentences.csv", build_irrelevant_csv(db))
        zf.writestr("suggested_passages.csv", build_suggested_csv(db))
    return buf.getvalue()
