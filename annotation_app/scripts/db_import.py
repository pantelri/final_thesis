"""
Database import helpers for obligations, companies, and annotation items.

Char-offset note
----------------
AnnotationItem.passage_start / passage_end  — char offsets from df1_spans.csv;
  reference the *original* (pre-normalization) source document text.
PassageSentence.char_start / char_end       — not computed, always NULL.
  Would need to be calculated relative to the normalized passage_text if required.
"""
import json
import random
from pathlib import Path

import pandas as pd

from app.models import AnnotationItem, Company, ElementType, Obligation, PassageSentence
from .segmentation import normalize_text, segment_passage


def import_obligations(db, json_path: Path) -> int:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for req in data["requirements"]:
        if db.get(Obligation, req["id"]):
            continue
        db.add(Obligation(
            id=req["id"],
            legal_basis=req.get("legal_basis"),
            title_de=req.get("title_de", ""),
            category=req.get("category"),
            verification_criterion=req.get("verification_criterion"),
            applicability_type=req.get("applicability", {}).get("type"),
            applicability_trigger=req.get("applicability", {}).get("trigger"),
        ))
        count += 1
    db.commit()
    return count


def import_companies(db, md_dir: Path, pdf_dir: Path) -> int:
    count = 0
    for md_file in sorted(md_dir.glob("*.md")):
        company_id = md_file.stem
        if db.get(Company, company_id):
            continue
        pdf_path = pdf_dir / f"{company_id}.pdf"
        parts = company_id.rsplit("_", 1)
        name = (
            parts[0].replace("_", " ")
            if len(parts) == 2 and parts[1].isdigit()
            else company_id
        )
        db.add(Company(
            id=company_id,
            name=name,
            pdf_path=str(pdf_path) if pdf_path.exists() else None,
        ))
        count += 1
    db.commit()
    return count


def import_annotation_items(
    db,
    df2_path: Path,
    df1_path: Path,
    overlap_fraction: float,
    min_per_obligation: int,
    seed: int,
) -> tuple[int, int, dict]:
    df2 = pd.read_csv(df2_path)
    df1 = pd.read_csv(df1_path)

    # Char-offset lookup from df1: (company, label) → (min_start, max_end)
    offsets: dict[tuple, tuple] = {}
    for _, r in df1.iterrows():
        k = (r["company"], r["label"])
        start, end = int(r["start"]), int(r["end"])
        offsets[k] = (
            min(offsets[k][0], start) if k in offsets else start,
            max(offsets[k][1], end) if k in offsets else end,
        )

    # Reproducible overlap selection
    rng = random.Random(seed)
    by_label: dict[str, list[str]] = {}
    for _, r in df2.iterrows():
        by_label.setdefault(str(r["label"]), []).append(str(r["company"]))

    overlap_pairs: set[tuple] = set()
    for label, companies in by_label.items():
        n_total = len(companies)
        n_overlap = min(max(round(n_total * overlap_fraction), min_per_obligation), n_total)
        for c in rng.sample(companies, n_overlap):
            overlap_pairs.add((c, label))

    # Per-obligation stats for summary table
    stats: dict[str, dict] = {}
    for _, r in df2.iterrows():
        rcode, label, company = str(r["rcode"]), str(r["label"]), str(r["company"])
        if rcode not in stats:
            stats[rcode] = {"title": str(r.get("title_de", rcode)), "total": 0, "overlap": 0}
        stats[rcode]["total"] += 1
        if (company, label) in overlap_pairs:
            stats[rcode]["overlap"] += 1

    imported = skipped = 0
    for _, row in df2.iterrows():
        company_id, label, rcode = str(row["company"]), str(row["label"]), str(row["rcode"])

        if not db.get(Company, company_id):
            print(f"  SKIP (company not found): {company_id}")
            skipped += 1
            continue
        if not db.get(Obligation, rcode):
            print(f"  SKIP (obligation not found): {rcode}")
            skipped += 1
            continue
        if db.query(AnnotationItem).filter_by(company_id=company_id, obligation_id=rcode).first():
            continue

        # Normalize literal \n/\t from CSV source before storing and segmenting
        raw = str(row["text_combined"]) if pd.notna(row.get("text_combined")) else ""
        passage_text = normalize_text(raw)
        ps, pe = offsets.get((company_id, label), (None, None))

        item = AnnotationItem(
            company_id=company_id,
            obligation_id=rcode,
            passage_text=passage_text,
            passage_start=ps,
            passage_end=pe,
            in_overlap_set=(company_id, label) in overlap_pairs,
            stratum=str(row["category"]) if pd.notna(row.get("category")) else None,
        )
        db.add(item)
        db.flush()

        for idx, (etype, etext) in enumerate(segment_passage(passage_text)):
            db.add(PassageSentence(
                item_id=item.id,
                idx=idx,
                element_type=ElementType.sentence if etype == "sentence" else ElementType.table,
                text=etext,
            ))

        imported += 1

    db.commit()
    return imported, skipped, stats
