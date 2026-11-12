"""Shared page chrome."""
from nicegui import app, ui

from .agreement import MIN_ANNOTATIONS, submitted_count
from .database import SessionLocal


def _evaluation_unlocked() -> bool:
    aid = app.storage.user.get("annotator_id")
    if not aid:
        return False
    db = SessionLocal()
    try:
        return submitted_count(db, aid) >= MIN_ANNOTATIONS
    finally:
        db.close()


def render_header(label: str) -> None:
    with ui.header().classes(
        "bg-indigo-700 text-white px-6 py-2 flex justify-between items-center"
    ):
        ui.label("HGB-Annotationsplattform").classes("text-base font-semibold tracking-wide")
        with ui.row().classes("items-center gap-3"):
            if _evaluation_unlocked():
                ui.button(
                    "Auswertungen",
                    on_click=lambda: ui.navigate.to("/auswertung"),
                ).props("flat dense color=white size=sm icon=bubble_chart")
            if app.storage.user.get("is_admin"):
                ui.button(
                    "Admin",
                    on_click=lambda: ui.navigate.to("/admin"),
                ).props("flat dense color=white size=sm")
            ui.label(f"Angemeldet: {label}").classes("text-sm opacity-90")
            ui.button(
                "Abmelden",
                on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/")),
            ).props("flat dense color=white size=sm")
