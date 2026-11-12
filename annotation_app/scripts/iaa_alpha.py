#!/usr/bin/env python3
"""
Inter-annotator agreement on the Phase-A pairs (first two judgments per item).

Only the first two submitted judgments of each item are used: they were assigned
by count alone (see app/assignment.py), so they form an unbiased reliability
sample. Third votes are routed to disputed items on purpose and are excluded.

Per question: n pairable units, percent agreement, Krippendorff's alpha (nominal)
and a 95 % bootstrap CI (units resampled with replacement).

  is_relevant      yes / no
  is_applicable    yes / no            ('unsure' treated as missing; --keep-unsure)
  is_fulfilled     yes / no            (only where BOTH judged applicable = yes;
                                        'partially' counted as 'no'; --fulfilled-3way)
  length_judgment  ok / too_short / too_long

Usage (on the server, in annotation_app/):
    docker compose exec app python -m scripts.iaa_alpha
    docker compose exec app python -m scripts.iaa_alpha --by-rater --by-obligation
    docker compose exec app python -m scripts.iaa_alpha --disagreements /tmp/disagreements.csv
    docker compose cp app:/tmp/disagreements.csv ./disagreements.csv
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from app.database import SessionLocal  # noqa: E402
from app.iaa import alpha_nominal, bootstrap_ci, n_pairable, percent_agreement  # noqa: E402
from app.consensus import unresolved_questions  # noqa: E402
from app.models import Annotation, AnnotationItem, Annotator  # noqa: E402

QUESTIONS = ["is_relevant", "is_applicable", "is_fulfilled", "length_judgment"]


def load_votes(db) -> dict[int, list[dict]]:
    """item_id -> submitted votes ordered by submission time."""
    rows = (
        db.query(Annotation, AnnotationItem, Annotator)
        .join(AnnotationItem, Annotation.item_id == AnnotationItem.id)
        .join(Annotator, Annotation.annotator_id == Annotator.id)
        .filter(Annotation.submitted_at.isnot(None))
        .order_by(Annotation.item_id, Annotation.submitted_at, Annotation.id)
        .all()
    )
    out: dict[int, list[dict]] = defaultdict(list)
    for a, item, ann in rows:
        out[item.id].append({
            "item_id": item.id, "company": item.company_id, "obligation": item.obligation_id,
            "annotator_id": ann.id, "annotator": ann.label or f"#{ann.id}",
            "is_relevant": None if a.is_relevant is None else ("yes" if a.is_relevant else "no"),
            "is_applicable": a.is_applicable.value if a.is_applicable else None,
            "is_fulfilled": a.is_fulfilled.value if a.is_fulfilled else None,
            "length_judgment": a.length_judgment.value if a.length_judgment else None,
            "comment": (a.comment or "").replace("\n", " "),
        })
    return out


def value(v: dict, q: str, args) -> str | None:
    x = v[q]
    if q == "is_applicable" and x == "unsure" and not args.keep_unsure:
        return None
    if q == "is_fulfilled":
        if v["is_applicable"] != "yes":
            return None
        if x == "partially" and not args.fulfilled_3way:
            return "no"
    return x


def units_for(pairs: list[list[dict]], q: str, args) -> list[list]:
    return [[value(v, q, args) for v in pair] for pair in pairs]


def fmt(x, digits=3) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def report(title: str, pairs: list[list[dict]], args, with_ci: bool = True) -> None:
    print(f"\n{title}  (Einheiten mit 2 Urteilen: {len(pairs)})")
    print(f"  {'Frage':16s} {'n':>4s} {'% Übereinst.':>13s} {'alpha':>7s}   95%-KI")
    for q in QUESTIONS:
        units = units_for(pairs, q, args)
        a = alpha_nominal(units)
        lo, hi = bootstrap_ci(units, reps=args.reps) if with_ci else (None, None)
        pa = percent_agreement(units)
        ci = f"[{fmt(lo)}, {fmt(hi)}]" if with_ci else ""
        print(f"  {q:16s} {n_pairable(units):4d} {fmt(pa and pa * 100, 1):>12s}% {fmt(a):>7s}   {ci}")


def write_disagreements(path: str, votes: dict[int, list[dict]], args) -> int:
    n = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["item_id", "company", "obligation", "questions_differing",
                    "rater1", "rater1_votes", "rater1_comment",
                    "rater2", "rater2_votes", "rater2_comment",
                    "rater3", "rater3_votes", "adjudicated_value", "adjudication_note"])
        for iid in sorted(votes):
            vs = votes[iid]
            if len(vs) < 2:
                continue
            first2 = vs[:2]
            diff = unresolved_questions(first2)   # same definition as Phase B
            if not diff:
                continue
            n += 1

            def fmt_votes(v):
                return ", ".join(f"{q}={v[q]}" for q in QUESTIONS)

            third = vs[2] if len(vs) > 2 else None
            w.writerow([iid, vs[0]["company"], vs[0]["obligation"], "|".join(diff),
                        vs[0]["annotator"], fmt_votes(vs[0]), vs[0]["comment"],
                        vs[1]["annotator"], fmt_votes(vs[1]), vs[1]["comment"],
                        third["annotator"] if third else "",
                        fmt_votes(third) if third else "", "", ""])
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=5000, help="Bootstrap-Replikationen (Default 5000)")
    ap.add_argument("--keep-unsure", action="store_true", help="'unsure' als eigene Kategorie werten")
    ap.add_argument("--fulfilled-3way", action="store_true", help="'partially' als eigene Kategorie werten")
    ap.add_argument("--by-rater", action="store_true", help="Sensitivität: getrennt nach Zweitannotator")
    ap.add_argument("--by-obligation", action="store_true", help="n und %% Übereinstimmung je Pflicht")
    ap.add_argument("--exclude", help="Datei mit item_ids (eine pro Zeile), die ausgeschlossen werden")
    ap.add_argument("--disagreements", help="CSV aller Einheiten, deren erste zwei Urteile laut "
                    "Konsensregel (wie Phase B) ungeklärt sind – Vorlage für die Adjudikation")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        votes = load_votes(db)
    finally:
        db.close()

    if args.exclude:
        excl = {int(x) for x in Path(args.exclude).read_text().split() if x.strip().isdigit()}
        votes = {k: v for k, v in votes.items() if k not in excl}

    pairs = [vs[:2] for vs in votes.values() if len(vs) >= 2]
    report("GESAMT (erste zwei Urteile je Einheit)", pairs, args)

    if args.by_rater:
        by = defaultdict(list)
        for p in pairs:
            by[p[1]["annotator"]].append(p)
        for label, ps in sorted(by.items()):
            report(f"Zweitannotator: {label}", ps, args)

    if args.by_obligation:
        print("\nJE PFLICHT (% Übereinstimmung; α je Pflicht bei kleinem n nicht belastbar)")
        by = defaultdict(list)
        for p in pairs:
            by[p[0]["obligation"]].append(p)
        print(f"  {'Pflicht':8s} {'n':>3s}  " + "  ".join(f"{q[:13]:>13s}" for q in QUESTIONS[:3]))
        for ob, ps in sorted(by.items()):
            cells = []
            for q in QUESTIONS[:3]:
                pa = percent_agreement(units_for(ps, q, args))
                cells.append(f"{fmt(pa and pa * 100, 0):>12s}%")
            print(f"  {ob:8s} {len(ps):3d}  " + "  ".join(cells))

    if args.disagreements:
        n = write_disagreements(args.disagreements, votes, args)
        print(f"\n{n} uneinige Einheiten → {args.disagreements}")


if __name__ == "__main__":
    main()
