"""Annotation page route — auth, load the next unit, and render either the
form (``annotate_form``) driven by a ``FormController`` (``annotate_logic``) or
one of the end pages (quota reached / nothing left). Data loading and form logic
live in those modules to keep this file thin; this one only wires them together.

Voluntary continuation past the personal quota is a per-login opt-in kept in
``app.storage.user["voluntary"]`` (cleared on logout; the annotator simply clicks
"Freiwillig weitermachen" again).
"""
from nicegui import app, ui

from ..database import SessionLocal
from ..layout import render_header
from ..session import annotator_id, require_auth, require_consent
from .annotate_form import build_form
from .annotate_logic import FormController, load_context


@ui.page("/annotate")
def annotate_page() -> None:
    if not require_auth() or not require_consent():
        return

    aid = annotator_id()
    voluntary = bool(app.storage.user.get("voluntary"))
    db = SessionLocal()
    try:
        ctx, meta = load_context(db, aid, voluntary=voluntary)
    finally:
        db.close()

    render_header(meta["ann_label"])
    if ctx is None:
        if meta["quota"]["blocked"] and meta.get("more_available"):
            render_quota_page(meta)
        else:
            render_done_page(meta)
        return

    ctrl = FormController(aid, ctx)
    build_form(ctrl, meta)


def _continue_voluntarily() -> None:
    app.storage.user["voluntary"] = True
    ui.navigate.to("/annotate")


def _review_hint(n_review: int) -> None:
    if not n_review:
        return
    with ui.card().classes("bg-amber-50 border-l-4 border-amber-500 mt-2"):
        ui.label(
            f"{n_review} Einheit(en) könnten eine erneute Prüfung gebrauchen – "
            "der Textabschnitt wurde seit Ihrer Bewertung ergänzt oder die "
            "Antwortoption „Teilweise“ entfällt."
        ).classes("text-sm text-amber-800")
        ui.button("Jetzt überprüfen",
                  on_click=lambda: ui.navigate.to("/review")).props("color=amber-8")


def render_quota_page(meta: dict) -> None:
    q = meta["quota"]
    with ui.column().classes("max-w-2xl mx-auto mt-16 px-4 items-center gap-4"):
        ui.icon("emoji_events", size="5rem", color="green")
        ui.label("Ziel erreicht – vielen Dank!").classes("text-2xl font-semibold text-center")
        ui.linear_progress(value=1.0, show_value=False).classes("w-64").props(
            "color=green rounded size=10px")
        ui.label(f"{q['done']} von {q['quota']} Einheiten abgeschlossen").classes(
            "text-sm text-green-700 font-medium")
        ui.label(
            "Damit haben Sie Ihren Beitrag vollständig geleistet. Wenn Sie mögen, "
            "können Sie freiwillig weitermachen – jede zusätzliche Einheit macht die "
            "Auswertung belastbarer. Sie können jederzeit wieder aufhören."
        ).classes("text-gray-500 text-center max-w-lg")
        ui.button("Freiwillig weitermachen", icon="arrow_forward",
                  on_click=_continue_voluntarily).props("color=indigo")
        _review_hint(meta.get("n_review", 0))


def render_done_page(meta: dict) -> None:
    q = meta["quota"]
    with ui.column().classes("max-w-2xl mx-auto mt-16 px-4 items-center gap-4"):
        ui.icon("check_circle", size="5rem", color="green")
        ui.label("Geschafft – aktuell keine weiteren Einheiten für Sie!").classes(
            "text-2xl font-semibold text-center")
        ui.label(
            "Alle Einheiten, die Sie bearbeiten können, haben bereits genügend "
            "unabhängige Urteile. Vielen Dank für Ihre Mitwirkung!"
        ).classes("text-gray-500 text-center max-w-lg")
        _review_hint(meta.get("n_review", 0))
        ui.separator()
        extra = f" (davon {q['extra']} freiwillig)" if q["extra"] else ""
        ui.label(f"Ihre abgeschlossenen Annotationen: {q['done']}{extra}").classes(
            "text-sm text-gray-400")
