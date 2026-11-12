"""Agreement between annotators and the thesis' LLMs (data for /auswertung).

Two questions are compared per unit (company × obligation):
  * Anwendbarkeit  — human is_applicable  vs  model Stage-1 relevance
  * Erfüllung      — human is_fulfilled   vs  model Stage-3 fulfillment
                     (only where BOTH sides have a fulfilment judgment)

agreement = matching judgments / compared judgments (both questions pooled).
n_units   = number of shared units the score rests on.

Everything below ``compare`` is pure (plain dicts), so it is testable without
Postgres; ``load_*`` are the thin data wrappers. Other annotators are
pseudonymised ("Annotator·in A", …) in the order of their ids.
"""
import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Annotation, AnnotationItem

MIN_ANNOTATIONS = 25          # "Auswertungen" unlock threshold
MODEL_CSV = Path(__file__).resolve().parents[1] / "data" / "model_judgments.csv"
ME = "Sie"
OTHERS = "Andere Annotator·innen"

APPLICABLE_MAP = {"yes": "relevant", "no": "not_relevant", "unsure": "unclear"}
FULFILLED_MAP = {"yes": "fulfilled", "no": "not_fulfilled", "partially": "not_fulfilled"}

Unit = tuple[str, str]                       # (company_id, obligation_id)
Judgments = dict[Unit, dict]                 # unit -> {"relevance", "fulfillment"}


@dataclass
class Stats:
    name: str
    kind: str = "human"      # "human" | "model" | "pool"
    n_units: int = 0
    app_match: int = 0
    app_n: int = 0
    ful_match: int = 0
    ful_n: int = 0

    @property
    def n_compared(self) -> int:
        return self.app_n + self.ful_n

    @property
    def n_match(self) -> int:
        return self.app_match + self.ful_match

    @property
    def agreement(self) -> float:
        return self.n_match / self.n_compared if self.n_compared else 0.0

    def __iadd__(self, other: "Stats") -> "Stats":
        self.n_units += other.n_units
        self.app_match += other.app_match
        self.app_n += other.app_n
        self.ful_match += other.ful_match
        self.ful_n += other.ful_n
        return self


def compare(a: Judgments, b: Judgments, name: str = "", kind: str = "human",
            obligation: str | None = None) -> Stats:
    """Pure: compare two judgment maps (optionally restricted to one obligation)."""
    s = Stats(name, kind)
    for unit, ja in a.items():
        if obligation is not None and unit[1] != obligation:
            continue
        jb = b.get(unit)
        if jb is None:
            continue
        s.n_units += 1
        if ja.get("relevance") and jb.get("relevance"):
            s.app_n += 1
            s.app_match += ja["relevance"] == jb["relevance"]
        if ja.get("fulfillment") and jb.get("fulfillment"):
            s.ful_n += 1
            s.ful_match += ja["fulfillment"] == jb["fulfillment"]
    return s


def pooled(a_list: list[Judgments], b: Judgments, name: str,
           obligation: str | None = None) -> Stats:
    """Sum of compare(a, b) over several judgment maps (e.g. all other humans)."""
    s = Stats(name, "pool")
    for a in a_list:
        s += compare(a, b, obligation=obligation)
    return s


@dataclass
class Data:
    """Everything the dashboard needs, pseudonymised; humans keyed by display name."""
    me: Judgments
    humans: dict[str, Judgments] = field(default_factory=dict)   # others only
    models: dict[str, Judgments] = field(default_factory=dict)

    def humans_with_min(self, min_shared: int) -> dict[str, Judgments]:
        """Other annotators sharing at least `min_shared` units with me."""
        return {n: j for n, j in self.humans.items()
                if compare(self.me, j).n_units >= min_shared}

    def obligations(self) -> list[str]:
        return sorted({u[1] for u in self.me})


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def _human_judgment(ann: Annotation) -> dict:
    app = ann.is_applicable.value if ann.is_applicable else ""
    ful = ann.is_fulfilled.value if (ann.is_fulfilled and app == "yes") else ""
    return {"relevance": APPLICABLE_MAP.get(app, ""), "fulfillment": FULFILLED_MAP.get(ful, "")}


def load_human_judgments(db: Session) -> dict[int, Judgments]:
    """{annotator_id: judgments} over submitted annotations."""
    q = (db.query(Annotation, AnnotationItem.company_id, AnnotationItem.obligation_id)
         .join(AnnotationItem, Annotation.item_id == AnnotationItem.id)
         .filter(Annotation.submitted_at.isnot(None)))
    out: dict[int, Judgments] = {}
    for ann, company, obligation in q:
        out.setdefault(ann.annotator_id, {})[(company, obligation)] = _human_judgment(ann)
    return out


@lru_cache(maxsize=1)
def load_model_judgments() -> dict[str, Judgments]:
    """{model_name: judgments} from the baked-in CSV (thesis model runs)."""
    out: dict[str, Judgments] = {}
    if not MODEL_CSV.exists():
        return out
    with open(MODEL_CSV, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["model_name"], {})[(r["company_id"], r["obligation_id"])] = {
                "relevance": r["relevance"], "fulfillment": r["fulfillment"]}
    return out


def pseudonym(i: int) -> str:
    return f"Annotator·in {chr(ord('A') + i)}" if i < 26 else f"Annotator·in {i + 1}"


def load_data(db: Session, aid: int) -> Data:
    humans = load_human_judgments(db)
    others = sorted(k for k in humans if k != aid)
    return Data(me=humans.get(aid, {}),
                humans={pseudonym(i): humans[k] for i, k in enumerate(others)},
                models=dict(load_model_judgments()))


def submitted_count(db: Session, aid: int) -> int:
    return (db.query(Annotation)
            .filter(Annotation.annotator_id == aid, Annotation.submitted_at.isnot(None))
            .count())
