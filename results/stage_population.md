# Stage Populations — Annotation GT (Annotator A, post `rebuild_passages`)

> Generated from the frozen DB export (`results/_db_export/`). One annotation per item
> (Annotator A only, so far). **182 items = 13 obligations × 14 companies.**

## Direct answers

- **Items with `is_applicable = "yes"`: 141**
- **Items with `is_relevant = "t" (True)`: 170**

## The three independent annotation fields

| Field | Values (count) | Meaning | Drives stage |
|---|---|---|---|
| `is_applicable` | yes 141 / no 37 / unsure 4 | Is the obligation applicable to this company? | **Stage 1 — relevance** |
| `is_relevant` | t 170 / f 12 | Was the *originally shown candidate passage* the correct evidence? | retrieval-GT positive filter |
| `is_fulfilled` | yes 104 / partially 27 / no 10 / (empty 41) | Is the disclosure actually present/complete? | **Stage 3 — fulfillment** |

`is_fulfilled` is only annotated when `is_applicable = yes` → the 141 non-empty
`is_fulfilled` values are **exactly** the 141 `is_applicable = yes` items.

## Cross-tabs

**is_applicable × is_relevant**
```
is_relevant     f    t  All
is_applicable              
no              3   34   37
unsure          1    3    4
yes             8  133  141
All            12  170  182
```

**is_applicable × has_fulfillment**
```
has_fulf       has_fulfillment  no_fulfillment  All
is_applicable                                      
no                           0              37   37
unsure                       0               4    4
yes                        141               0  141
All                        141              41  182
```

## Correct population per experiment stage

| Stage | Experiment population | n | Definition |
|---|---|---|---|
| **Stage 1 — relevance** | all items | **182** | every item carries an `is_applicable` judgment |
| **Stage 2 — retrieval** | pairs with evidence | see note | currently `is_relevant = t` → **170** |
| **Stage 3 — fulfillment** | pairs with `is_fulfilled` set | **141** | = `is_applicable = yes` |

### ⚠ Population mismatch to watch (Stage 2)

The current retrieval population (`is_relevant = t`, 170 pairs) does **not** equal the
applicable population (141):

- **8 pairs are `is_applicable = yes` but `is_relevant = f`** → currently *excluded* from retrieval eval
  even though they have curated evidence (the 8 review pairs below).
- **37 pairs are `is_applicable ≠ yes` but `is_relevant = t`** → currently *included* in retrieval eval
  although Stage 1 would have filtered them out.

Decision (per author): **Phase 4b uses all 141 `is_fulfilled`-labelled pairs.**
Phase 3 retrieval is **not** recomputed now — revisit the Stage-2 population definition when the
GT is finalised (after IAA / majority vote).
