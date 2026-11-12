"""Admin card: create annotators/admins from the browser and list existing ones.

The plaintext access code is generated here, shown ONCE in a dialog, and only its
hash is stored (same path as scripts/seed_annotators.py → auth.create_annotator).
"""
import json

from nicegui import ui
from sqlalchemy import func

from ..auth import create_annotator, generate_code
from ..database import SessionLocal
from ..models import Annotation, Annotator


def _annotator_rows() -> list[dict]:
    db = SessionLocal()
    try:
        counts = dict(
            db.query(Annotation.annotator_id, func.count(Annotation.id))
            .filter(Annotation.submitted_at.isnot(None))
            .group_by(Annotation.annotator_id)
        )
        return [
            {"id": a.id, "label": a.label or f"Annotator #{a.id}",
             "role": "Admin" if a.is_admin else "Annotator",
             "n": counts.get(a.id, 0),
             "consent": "ja" if a.consent_given_at else "–",
             "created": a.created_at.strftime("%d.%m.%Y") if a.created_at else ""}
            for a in db.query(Annotator).order_by(Annotator.id)
        ]
    finally:
        db.close()


def _show_code(label: str, code: str) -> None:
    with ui.dialog().props("persistent") as dlg, ui.card().classes("gap-3"):
        ui.label(f"Zugang für „{label}“ angelegt").classes("text-lg font-semibold")
        ui.label("Dieser Code wird nur jetzt angezeigt und ist nicht wiederherstellbar:").classes(
            "text-sm text-gray-600")
        ui.label(code).classes("text-2xl font-mono font-bold tracking-widest select-all")
        with ui.row().classes("gap-2"):
            ui.button("Kopieren", icon="content_copy", on_click=lambda: (
                ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(code)})"),
                ui.notify("Code kopiert"))).props("color=indigo")
            ui.button("Schließen", on_click=dlg.close).props("flat")
    dlg.open()


def render_user_card() -> None:
    with ui.card().classes("w-full"):
        ui.label("Personen & Zugangscodes").classes("font-semibold text-lg mb-1")
        ui.label("Neue Person anlegen: Es wird ein zufälliger 12-stelliger Code erzeugt "
                 "und einmalig angezeigt.").classes("text-gray-500 text-sm mb-2")

        columns = [
            {"name": "id", "label": "ID", "field": "id", "align": "left"},
            {"name": "label", "label": "Bezeichnung", "field": "label", "align": "left"},
            {"name": "role", "label": "Rolle", "field": "role", "align": "left"},
            {"name": "n", "label": "Annotationen", "field": "n"},
            {"name": "consent", "label": "Einwilligung", "field": "consent"},
            {"name": "created", "label": "Angelegt", "field": "created"},
        ]

        with ui.row().classes("items-end gap-3 flex-wrap"):
            label_in = ui.input("Bezeichnung (z. B. „Demo Prüfer C“)").classes("w-64")
            admin_cb = ui.checkbox("Admin-Rechte")
            ui.button("Anlegen", icon="person_add", on_click=lambda: create()).props("color=indigo")

        table = ui.table(columns=columns, rows=_annotator_rows(), row_key="id").classes(
            "w-full mt-3").props("dense flat")

        def create() -> None:
            label = (label_in.value or "").strip()
            if not label:
                ui.notify("Bitte eine Bezeichnung eingeben.", type="warning")
                return
            db = SessionLocal()
            try:
                _, code = create_annotator(db, generate_code(), label=label,
                                           is_admin=bool(admin_cb.value))
            except Exception as exc:  # noqa: BLE001 — surface DB errors in the UI
                db.rollback()
                ui.notify(f"Anlegen fehlgeschlagen: {exc}", type="negative")
                return
            finally:
                db.close()
            label_in.value, admin_cb.value = "", False
            table.rows = _annotator_rows()
            table.update()
            _show_code(label, code)

