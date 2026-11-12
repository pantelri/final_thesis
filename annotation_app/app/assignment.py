"""
Annotation assignment — double coverage first, then targeted third votes.

Phase A · Zweiturteil (reliability sample)
    Every item is brought to TARGET_DOUBLE (= 2) independent judgments. Items are
    served in ONE fixed order: shuffled with a fixed seed inside each obligation and
    then interleaved round-robin across obligations (R02, R03, …, R24, R02, …).
    Whatever prefix of that order gets done is therefore a balanced random sample
    over all obligations — the IAA sample stays valid even if Phase A never finishes.
    Selection here never looks at annotation *content*, only at counts, so Phase-A
    pairs are an unbiased sample for Krippendorff's alpha.

Phase B · Klärung (ground truth)
    Only once an annotator has no Phase-A item left: items with exactly 2 votes and
    at least one unresolved question (see consensus.py) receive a third vote, in the
    same fixed order. These votes are chosen *because* of disagreement and must NOT
    enter the alpha computation — they only feed the adjudicated ground truth.

Hard cap: no item ever gets more than MAX_ANNOTATIONS_PER_ITEM (= 3) votes. What
is still unresolved after 3 votes is adjudicated by the author.

Soft reservation: an item served to another annotator within the last
RESERVATION_MINUTES (and not yet submitted by them) is skipped, so two people do
not work on the same Phase-A slot in parallel. If only reserved items remain, they
are served anyway (nobody gets stuck on an abandoned tab).

Validity: this module reads counts and consensus status only; the caller never
receives another annotator's answers.
"""
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from .consensus import has_disagreement, votes_by_item
from .models import Annotation, AnnotationItem, Annotator, AssignmentLog

TARGET_DOUBLE = 2
MAX_ANNOTATIONS_PER_ITEM = max(
    TARGET_DOUBLE, int(os.environ.get("MAX_ANNOTATIONS_PER_ITEM", "3")))
ASSIGNMENT_SEED = int(os.environ.get("ASSIGNMENT_SEED", "20260929"))
RESERVATION_MINUTES = int(os.environ.get("RESERVATION_MINUTES", "30"))
ANNOTATION_QUOTA = max(1, int(os.environ.get("ANNOTATION_QUOTA", "25")))

PHASE_DOUBLE = "double"      # Phase A
PHASE_CLARIFY = "clarify"    # Phase B
PHASE_COMPLETE = "complete"


# ---------------------------------------------------------------------------
# Pure logic (unit-tested without a database)
# ---------------------------------------------------------------------------

def stratified_order(items: list[tuple[int, str]], seed: int = ASSIGNMENT_SEED) -> dict[int, int]:
    """items: (item_id, obligation_id) → {item_id: rank}.

    Seeded shuffle within each obligation, then round-robin across obligations in
    sorted order. Deterministic for a given item set and seed."""
    rng = random.Random(seed)
    groups: dict[str, list[int]] = defaultdict(list)
    for iid, ob in items:
        groups[ob].append(iid)
    queues = []
    for ob in sorted(groups):
        ids = sorted(groups[ob])
        rng.shuffle(ids)
        queues.append(ids)
    order, depth = [], 0
    while any(depth < len(q) for q in queues):
        order.extend(q[depth] for q in queues if depth < len(q))
        depth += 1
    return {iid: rank for rank, iid in enumerate(order)}


def choose_next(
    rank: dict[int, int],
    votes: dict[int, list[dict]],
    done: set[int],
    reserved: set[int] = frozenset(),
    max_per_item: int = MAX_ANNOTATIONS_PER_ITEM,
) -> tuple[int | None, str | None]:
    """Return (item_id, phase) for the next item, or (None, None).

    Phase A candidates (fewer than TARGET_DOUBLE votes) always win over Phase B
    candidates (exactly/at least TARGET_DOUBLE votes, below the cap, disagreement).
    Within a phase: fewest votes first, then the fixed rank. Reserved items are
    used only when no unreserved candidate of that phase exists."""
    phase_a, phase_b = [], []
    for iid, r in rank.items():
        if iid in done:
            continue
        v = votes.get(iid, [])
        n = len(v)
        if n < TARGET_DOUBLE:
            phase_a.append(((n, r), iid))
        elif n < max_per_item and has_disagreement(v):
            phase_b.append(((n, r), iid))

    for pool, phase in ((phase_a, PHASE_DOUBLE), (phase_b, PHASE_CLARIFY)):
        if not pool:
            continue
        free = [p for p in pool if p[1] not in reserved]
        best = min(free or pool)
        return best[1], phase
    return None, None


def global_phase(votes: dict[int, list[dict]], item_ids, max_per_item: int = MAX_ANNOTATIONS_PER_ITEM) -> str:
    counts = [len(votes.get(i, [])) for i in item_ids]
    if not counts:
        return PHASE_COMPLETE
    if min(counts) < TARGET_DOUBLE:
        return PHASE_DOUBLE
    if any(TARGET_DOUBLE <= len(votes.get(i, [])) < max_per_item and has_disagreement(votes.get(i, []))
           for i in item_ids):
        return PHASE_CLARIFY
    return PHASE_COMPLETE


def quota_state(done_count: int, quota: int, voluntary: bool) -> dict:
    """Progress numbers for the UI. `blocked` = quota reached and not opted in."""
    reached = done_count >= quota
    return {
        "quota": quota,
        "done": done_count,
        "reached": reached,
        "extra": max(0, done_count - quota),
        "blocked": reached and not voluntary,
        "fraction": min(1.0, done_count / quota) if quota else 1.0,
    }


# ---------------------------------------------------------------------------
# DB wrappers
# ---------------------------------------------------------------------------

def _rank(db: Session) -> dict[int, int]:
    return stratified_order(db.query(AnnotationItem.id, AnnotationItem.obligation_id).all())


def _done(db: Session, annotator_id: int) -> set[int]:
    return {iid for (iid,) in db.query(Annotation.item_id).filter(
        Annotation.annotator_id == annotator_id,
        Annotation.submitted_at.isnot(None)).all()}


def _reserved(db: Session, annotator_id: int) -> set[int]:
    """Items served to someone else recently that they have not submitted yet."""
    since = datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_MINUTES)
    recent = (db.query(AssignmentLog.item_id, AssignmentLog.annotator_id)
              .filter(AssignmentLog.assigned_at >= since,
                      AssignmentLog.annotator_id != annotator_id)
              .all())
    if not recent:
        return set()
    submitted = {(i, a) for i, a in db.query(Annotation.item_id, Annotation.annotator_id)
                 .filter(Annotation.submitted_at.isnot(None)).all()}
    return {i for i, a in recent if (i, a) not in submitted}


def pick_item(db: Session, annotator_id: int) -> tuple[AnnotationItem | None, str | None]:
    """Next item + phase for this annotator (no logging)."""
    item_id, phase = choose_next(
        _rank(db), votes_by_item(db), _done(db, annotator_id), _reserved(db, annotator_id))
    return (db.get(AnnotationItem, item_id) if item_id is not None else None), phase


def get_phase(db: Session) -> str:
    ids = [i for (i,) in db.query(AnnotationItem.id).all()]
    return global_phase(votes_by_item(db), ids)


def count_done(db: Session, annotator_id: int) -> int:
    return len(_done(db, annotator_id))


def get_item_annotation_count(db: Session, item_id: int) -> int:
    """Completed-annotation count for one item."""
    return (
        db.query(func.count(Annotation.id))
        .filter(Annotation.item_id == item_id, Annotation.submitted_at.isnot(None))
        .scalar()
    ) or 0


def assign_next_item(db: Session, annotator_id: int) -> tuple[AnnotationItem | None, str | None, int]:
    """Pick the next item, log the assignment (also acts as the soft reservation).

    Returns (item, phase, max_per_item); item is None when nothing is left."""
    item, phase = pick_item(db, annotator_id)
    if item is not None:
        db.add(AssignmentLog(item_id=item.id, annotator_id=annotator_id))
        db.commit()
    return item, phase, MAX_ANNOTATIONS_PER_ITEM


# ---------------------------------------------------------------------------
# Stats (admin page)
# ---------------------------------------------------------------------------

def get_coverage_stats(db: Session) -> dict:
    ids = [i for (i,) in db.query(AnnotationItem.id).all()]
    votes = votes_by_item(db)
    depth = {i: 0 for i in range(MAX_ANNOTATIONS_PER_ITEM + 1)}
    disagree_at_2 = 0
    for iid in ids:
        v = votes.get(iid, [])
        depth[min(len(v), MAX_ANNOTATIONS_PER_ITEM)] += 1
        if len(v) == TARGET_DOUBLE and has_disagreement(v):
            disagree_at_2 += 1
    total = len(ids)
    at_least_2 = sum(n for k, n in depth.items() if k >= TARGET_DOUBLE)
    return {
        "total_items": total,
        "phase": global_phase(votes, ids),
        "max_per_item": MAX_ANNOTATIONS_PER_ITEM,
        "quota": ANNOTATION_QUOTA,
        "depth": depth,
        "at_least_1": total - depth[0],
        "at_least_2": at_least_2,
        "disagree_at_2": disagree_at_2,
        "complete": depth[MAX_ANNOTATIONS_PER_ITEM],
    }


def get_annotator_stats(db: Session) -> list[dict]:
    """Per-annotator submitted counts, for the admin table."""
    counts = dict(
        db.query(Annotation.annotator_id, func.count(Annotation.id))
        .filter(Annotation.submitted_at.isnot(None))
        .group_by(Annotation.annotator_id).all()
    )
    rows = []
    for a in db.query(Annotator).order_by(Annotator.id).all():
        n = counts.get(a.id, 0)
        rows.append({
            "id": a.id, "label": a.label or f"Annotator #{a.id}", "is_admin": a.is_admin,
            "consent": a.consent_given_at is not None, "done": n,
            "quota_reached": n >= ANNOTATION_QUOTA,
        })
    return rows
