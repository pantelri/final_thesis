"""/auswertung — agreement dashboard (unlocked after MIN_ANNOTATIONS submissions).

Sections:
  1. Säulendiagramm: Ihre Übereinstimmung mit jedem KI-Modell (linear). Klick wählt
     das Modell für das Gravitationsmodell; vorausgewählt = höchste Übereinstimmung.
  2. Gravitationsmodell: Sie / andere Annotator·innen / gewähltes Modell; Lücke ∝ (1 − Ü)².
  3. Übereinstimmung mit einzelnen Annotator·innen, Filter "mind. N gemeinsame Einheiten".
  4. Heatmap über alle Paare.   5. Übereinstimmung je Pflicht.
The min-shared filter applies to 2–5 (which humans count / which cells are shown).
"""
from nicegui import ui

from ..agreement import (MIN_ANNOTATIONS, ME, OTHERS, Data, compare, load_data,
                         pooled, submitted_count)
from ..database import SessionLocal
from ..layout import render_header
from ..models import Annotator, Obligation
from ..session import annotator_id, require_auth, require_consent
from .eval_charts import heatmap, html, human_list, model_bars, obligation_table
from .eval_space import gravity_svg, scale_for

DEFAULT_MIN_SHARED = 3


def _card(title: str, hint: str = ""):
    card = ui.card().classes("w-full gap-2")
    with card:
        ui.label(title).classes("font-semibold text-lg")
        if hint:
            ui.label(hint).classes("text-xs text-gray-500")
    return card


def _dashboard(data: Data, titles: dict[str, str]) -> None:
    model_stats = sorted((compare(data.me, j, n, "model") for n, j in data.models.items()),
                         key=lambda s: -s.agreement)
    model_stats = [s for s in model_stats if s.n_compared]
    state = {"model": model_stats[0].name if model_stats else "", "min": DEFAULT_MIN_SHARED}

    def humans() -> dict:
        return data.humans_with_min(state["min"])

    def select(name: str) -> None:
        state["model"] = name
        bars.refresh()
        space.refresh()

    def set_min(v) -> None:
        state["min"] = max(1, int(v or 1))
        for r in (bars, space, people, pairs, per_obl):
            r.refresh()

    with ui.row().classes("w-full items-center gap-3 bg-indigo-50 rounded p-3"):
        ui.icon("filter_alt", color="indigo")
        ui.label("Menschliche Vergleiche nur bei mind.").classes("text-sm")
        ui.number(value=DEFAULT_MIN_SHARED, min=1, step=1, format="%d",
                  on_change=lambda e: set_min(e.value)).props("dense outlined").classes("w-20")
        ui.label("gemeinsam annotierten Einheiten").classes("text-sm")

    @ui.refreshable
    def bars() -> None:
        ref = pooled(list(humans().values()), data.me, OTHERS)
        model_bars(model_stats, state["model"], select, ref)

    @ui.refreshable
    def space() -> None:
        m = next((s for s in model_stats if s.name == state["model"]), None)
        if m is None:
            ui.label("Keine KI-Daten vorhanden.").classes("text-gray-500")
            return
        hs = list(humans().values())
        others = pooled(hs, data.me, OTHERS) if hs else None
        o_vs_m = pooled(hs, data.models[m.name], OTHERS) if hs else None
        # one scale for the whole page: all models' me/others gaps share the same K
        agrs = [s.agreement for s in model_stats]
        if hs:
            agrs.append(others.agreement)
            agrs += [pooled(hs, data.models[s.name], OTHERS).agreement for s in model_stats]
        html(gravity_svg(len(data.me), m, others, o_vs_m, scale_for(agrs))).classes("w-full")
        if not hs:
            ui.label("Noch keine anderen Annotator·innen mit genug gemeinsamen Einheiten – "
                     "es werden nur Sie und das Modell gezeigt.").classes("text-xs text-gray-500")

    @ui.refreshable
    def people() -> None:
        hs = sorted((compare(data.me, j, n) for n, j in humans().items()),
                    key=lambda s: (-s.agreement, -s.n_units))
        human_list([s for s in hs if s.n_compared])

    @ui.refreshable
    def pairs() -> None:
        ents = {ME: data.me, **humans(), **data.models}
        names = list(ents)
        cells = {(a, b): compare(ents[a], ents[b]) for a in names for b in names if a != b}
        heatmap(names, cells, state["min"])

    @ui.refreshable
    def per_obl() -> None:
        hs = list(humans().values())
        cols = [OTHERS] + [s.name for s in model_stats]
        cells = {}
        for o in data.obligations():
            cells[(o, OTHERS)] = pooled(hs, data.me, OTHERS, obligation=o)
            for s in model_stats:
                cells[(o, s.name)] = compare(data.me, data.models[s.name], obligation=o)
        obligation_table([(o, titles.get(o, "")) for o in data.obligations()], cols, cells, 1)

    with _card("Übereinstimmung mit KI-Modellen",
               "Anteil gleicher Urteile (Anwendbarkeit + Erfüllung). Klicken Sie auf eine Säule, "
               "um das Modell im Gravitationsmodell darzustellen."):
        bars()
    with _card("Gravitationsmodell",
               "Je höher die Übereinstimmung, desto stärker ziehen sich zwei Kreise an: "
               "Abstand = (100 % − Übereinstimmung)², bei 100 % berühren sie sich. "
               "Größerer Kreis = mehr Einheiten, auf denen der Wert beruht."):
        space()
    with _card("Übereinstimmung mit anderen Annotator·innen",
               "Pseudonymisiert. n = gemeinsam annotierte Einheiten – kleine n sind wenig "
               "aussagekräftig, daher der Filter oben."):
        people()
    with _card("Heatmap über alle Paare",
               "Jede Zelle: Übereinstimmung zweier Beteiligter. „·“ = zu wenige gemeinsame "
               "Einheiten (Filter)."):
        pairs()
    with _card("Ihre Übereinstimmung je Pflicht",
               "Wo stimmen Sie mit Menschen und Modellen überein, wo nicht? "
               "Fahren Sie über eine Zeile für den vollständigen Pflichttitel."):
        per_obl()


@ui.page("/auswertung")
def evaluation_page() -> None:
    if not require_auth() or not require_consent():
        return
    aid = annotator_id()
    db = SessionLocal()
    try:
        ann = db.get(Annotator, aid)
        label = ann.label or f"Annotator #{aid}"
        done = submitted_count(db, aid)
        data = load_data(db, aid) if done >= MIN_ANNOTATIONS else None
        titles = {o.id: o.title_de for o in db.query(Obligation).all()}
    finally:
        db.close()

    render_header(label)
    with ui.column().classes("w-full max-w-4xl mx-auto mt-8 px-4 gap-5 mb-12"):
        ui.label("Auswertungen").classes("text-2xl font-bold")
        if data is None:
            ui.label(f"Die Auswertung wird nach {MIN_ANNOTATIONS} Annotationen freigeschaltet – "
                     f"noch {MIN_ANNOTATIONS - done}.").classes("text-gray-600")
            ui.linear_progress(value=done / MIN_ANNOTATIONS, show_value=False).props("color=indigo")
            ui.button("Weiter annotieren", on_click=lambda: ui.navigate.to("/annotate")).props(
                "color=indigo")
            return
        ui.label("Verglichen werden Ihre Urteile zu „Anwendbarkeit“ und „Erfüllung“ mit denen "
                 "anderer Annotator·innen und der KI-Modelle der Masterarbeit – jeweils auf den "
                 "Einheiten, die beide beurteilt haben.").classes("text-gray-600 text-sm")
        _dashboard(data, titles)
