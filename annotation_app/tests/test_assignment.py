"""Pure tests of the assignment rules (no database)."""
from app.assignment import (
    PHASE_CLARIFY, PHASE_COMPLETE, PHASE_DOUBLE, choose_next, global_phase,
    quota_state, stratified_order,
)

OBS = ["R02", "R03", "R04"]
ITEMS = [(i, OBS[i % 3]) for i in range(1, 31)]          # 30 items, 10 per obligation


def vote(rel="yes", app="yes", ful="yes"):
    return {"is_relevant": rel, "length_judgment": "ok", "is_applicable": app, "is_fulfilled": ful}


def test_order_is_deterministic_and_complete():
    a, b = stratified_order(ITEMS, seed=7), stratified_order(ITEMS, seed=7)
    assert a == b
    assert sorted(a) == [i for i, _ in ITEMS]
    assert sorted(a.values()) == list(range(30))
    assert stratified_order(ITEMS, seed=8) != a


def test_every_prefix_is_balanced_across_obligations():
    rank = stratified_order(ITEMS, seed=7)
    ob = dict(ITEMS)
    ordered = sorted(rank, key=rank.get)
    for k in range(3, 31, 3):
        counts = {o: sum(ob[i] == o for i in ordered[:k]) for o in OBS}
        assert set(counts.values()) == {k // 3}


def test_phase_a_before_disagreement():
    rank = stratified_order(ITEMS, seed=1)
    votes = {i: [vote()] for i, _ in ITEMS}
    disputed = 5
    votes[disputed] = [vote(), vote(app="no")]          # 2 votes, disagreement
    iid, phase = choose_next(rank, votes, done=set())
    assert phase == PHASE_DOUBLE and len(votes[iid]) == 1


def test_phase_a_follows_fixed_rank():
    rank = stratified_order(ITEMS, seed=1)
    votes = {i: [vote()] for i, _ in ITEMS}
    iid, _ = choose_next(rank, votes, done=set())
    assert rank[iid] == 0


def test_phase_b_only_disputed_and_capped():
    rank = stratified_order(ITEMS, seed=1)
    votes = {i: [vote(), vote()] for i, _ in ITEMS}      # all doubled, all agree
    assert choose_next(rank, votes, done=set()) == (None, None)
    votes[9] = [vote(), vote(ful="no")]
    assert choose_next(rank, votes, done=set()) == (9, PHASE_CLARIFY)
    votes[9] = [vote(), vote(ful="no"), vote(app="no")]  # still unresolved, but cap 3
    assert choose_next(rank, votes, done=set()) == (None, None)


def test_own_items_and_reservations():
    rank = stratified_order(ITEMS, seed=1)
    ordered = sorted(rank, key=rank.get)
    votes = {i: [vote()] for i, _ in ITEMS}
    iid, _ = choose_next(rank, votes, done={ordered[0]}, reserved={ordered[1]})
    assert iid == ordered[2]
    only = {ordered[0]: [vote()]}
    r1 = {ordered[0]: 0}
    assert choose_next(r1, only, done=set(), reserved={ordered[0]})[0] == ordered[0]


def test_global_phase():
    ids = [i for i, _ in ITEMS]
    assert global_phase({i: [vote()] for i in ids}, ids) == PHASE_DOUBLE
    both = {i: [vote(), vote()] for i in ids}
    assert global_phase(both, ids) == PHASE_COMPLETE
    both[3] = [vote(), vote(rel="no")]
    assert global_phase(both, ids) == PHASE_CLARIFY


def test_quota_state():
    q = quota_state(12, 25, voluntary=False)
    assert not q["reached"] and not q["blocked"] and abs(q["fraction"] - 0.48) < 1e-9
    q = quota_state(25, 25, voluntary=False)
    assert q["reached"] and q["blocked"] and q["extra"] == 0
    q = quota_state(31, 25, voluntary=True)
    assert q["reached"] and not q["blocked"] and q["extra"] == 6 and q["fraction"] == 1.0
