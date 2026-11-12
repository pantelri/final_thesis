"""Login page."""
from nicegui import app, ui

from ..auth import verify_annotator
from ..database import SessionLocal
from ..session import annotator_id


@ui.page("/")
def login_page() -> None:
    if annotator_id():
        ui.navigate.to("/annotate")
        return

    with ui.column().classes("absolute-center items-center gap-2"):
        ui.label("HGB-Annotationsplattform").classes("text-2xl font-bold text-indigo-700")
        ui.label("Jahresabschluss-Vollständigkeitsprüfung").classes(
            "text-sm text-gray-500 mb-2"
        )
        with ui.card().classes("w-80 p-6 shadow-lg"):
            code_input = ui.input(
                "Zugangscode", password=True, password_toggle_button=True
            ).classes("w-full")
            error_msg = ui.label("").classes("text-red-500 text-sm min-h-5")

            def handle_login() -> None:
                code = code_input.value.strip()
                if not code:
                    error_msg.set_text("Bitte Zugangscode eingeben.")
                    return
                db = SessionLocal()
                try:
                    ann = verify_annotator(db, code)
                    if ann is None:
                        error_msg.set_text("Ungültiger Zugangscode.")
                        code_input.value = ""
                        return
                    app.storage.user["annotator_id"] = ann.id
                    app.storage.user["is_admin"] = ann.is_admin
                    if ann.consent_given_at is None:
                        ui.navigate.to("/consent")
                    elif ann.is_admin:
                        ui.navigate.to("/admin")
                    else:
                        ui.navigate.to("/annotate")
                finally:
                    db.close()

            ui.button("Anmelden", on_click=handle_login).classes("w-full mt-2").props(
                "color=indigo"
            )
            code_input.on("keydown.enter", handle_login)
