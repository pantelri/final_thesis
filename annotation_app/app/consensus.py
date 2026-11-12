"""Per-item consensus over annotator votes — strict majority of *cast* votes.

GT for each question = the value holding a STRICT majority among the votes actually
cast for that question (abstentions excluded). `is_fulfilled` is conditional: it is
only cast when an annotator judged `is_applicable = 'yes'`, so its consensus is taken
among the applicable-yes voters and it is treated as "not applicable" (resolved, no
winner) once `is_applicable` resolves to a non-'yes' value; while `is_applicable`
itself is undecided, `is_fulfilled` stays unresolved.

An item still needs annotation while any question is unresolved OR it has fewer than
TARGET_VOTES votes. An item shows *disagreement* once >= 2 votes exist and a question
is still unresolved — such items receive a third vote in Phase B, i.e. only after
double coverage (Phase A) is exhausted for that annotator (see assignment.py).

The vote-tallying is pure (operates on plain per-annotator dicts) so it is unit-testable
without Postgres; `votes_for_item` is the thin DB wrapper.
"""
from collections import Counter

from sqlalchemy.orm import Session

from .models import Annotation

TARGET_VOTES = 3
# Questions that must reach consensus (is_fulfilled handled conditionally; see module doc).
# length_judgment is intentionally NOT a consensus question — a split length judgment is
# acceptable and must not block an item from resolving (author decision 2026-06-28).
QUESTION_FIELDS = ["is_relevant", "is_applicable", "is_fulfilled"]


def _strict_majority(values) -> tuple[object, dict]:
    """(winner, counts) for the strict-majority value among cast (non-empty) values.

    winner is None when no value exceeds half the cast votes (ties / zero cast)."""
    cast = [v for v in values if v not in (None, "")]
    counts = dict(Counter(cast))
    if not cast:
        return None, counts
    val, n = Counter(cast).most_common(1)[0]
    return (val if n * 2 > len(cast) else None), counts


def _entry(winner, counts, resolved, applicable=True) -> dict:
    return {"winner": winner, "counts": counts, "resolved": resolved, "applicable": applicable}


def tally(votes: list[dict]) -> dict:
    """votes: list of per-annotator dicts → {field: {winner, counts, resolved, applicable}}."""
    out = {}
    for f in ("is_relevant", "length_judgment", "is_applicable"):
        winner, counts = _strict_majority([v.get(f) for v in votes])
        out[f] = _entry(winner, counts, winner is not None)

    appl = out["is_applicable"]["winner"]
    f_votes = [v.get("is_fulfilled") for v in votes if v.get("is_applicable") == "yes"]
    if appl is not None and appl != "yes":
        out["is_fulfilled"] = _entry(None, {}, True, applicable=False)
    elif appl is None:                       # applicability undecided → fulfillment pending
        winner, counts = _strict_majority(f_votes)
        out["is_fulfilled"] = _entry(winner, counts, False)
    else:                                    # applicable = yes
        winner, counts = _strict_majority(f_votes)
        out["is_fulfilled"] = _entry(winner, counts, winner is not None)
    return out


def unresolved_questions(votes: list[dict]) -> list[str]:
    t = tally(votes)
    return [f for f in QUESTION_FIELDS if t[f]["applicable"] and not t[f]["resolved"]]


def has_disagreement(votes: list[dict]) -> bool:
    """>= 2 votes and at least one applicable question still unresolved."""
    return len(votes) >= 2 and bool(unresolved_questions(votes))


def needs_more(votes: list[dict], target: int = TARGET_VOTES) -> bool:
    """Item needs another annotation while a question is unresolved or it has < target votes."""
    return bool(unresolved_questions(votes)) or len(votes) < target


def majority_gt(votes: list[dict]) -> dict:
    """Per-question GT = strict-majority winner (None where unresolved / not applicable)."""
    t = tally(votes)
    return {f: t[f]["winner"] for f in QUESTION_FIELDS}


def _vote_dict(a: Annotation) -> dict:
    return {
        "annotator_id": a.annotator_id,
        "is_relevant": None if a.is_relevant is None else ("yes" if a.is_relevant else "no"),
        "length_judgment": a.length_judgment.value if a.length_judgment else None,
        "is_applicable": a.is_applicable.value if a.is_applicable else None,
        "is_fulfilled": a.is_fulfilled.value if a.is_fulfilled else None,
    }


def votes_for_item(db: Session, item_id: int) -> list[dict]:
    rows = (db.query(Annotation)
            .filter(Annotation.item_id == item_id, Annotation.submitted_at.isnot(None))
            .all())
    return [_vote_dict(a) for a in rows]


def votes_by_item(db: Session) -> dict[int, list[dict]]:
    """All submitted votes grouped by item_id, in one query (for assignment ranking)."""
    from collections import defaultdict
    out: dict[int, list[dict]] = defaultdict(list)
    for a in db.query(Annotation).filter(Annotation.submitted_at.isnot(None)).all():
        out[a.item_id].append(_vote_dict(a))
    return dict(out)
