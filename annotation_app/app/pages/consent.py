"""Consent page."""
from datetime import datetime, timezone

from nicegui import app, ui

from ..database import SessionLocal
from ..models import Annotator
from ..session import annotator_id, require_auth


@ui.page("/consent")
def consent_page() -> None:
    if not require_auth():
        return

    db = SessionLocal()
    try:
        ann = db.get(Annotator, annotator_id())
        if ann and ann.consent_given_at:
            ui.navigate.to("/annotate")
            return
    finally:
        db.close()

    with ui.column().classes("max-w-2xl mx-auto mt-8 px-4 gap-4"):
        ui.label("Einwilligungserklärung").classes("text-2xl font-bold")

        with ui.card().classes("w-full p-4"):
            ui.markdown("""
## Datenschutzhinweis

Im Rahmen dieser wissenschaftlichen Studie (Masterarbeit) werden folgende Daten erhoben:

**Welche Daten?**
Ihre Beurteilungen von Textabschnitten aus öffentlich zugänglichen deutschen Jahresabschlüssen
(Relevanz, Anwendbarkeit und Erfüllung von HGB-Offenlegungspflichten) sowie optionale Kommentare.

**Zweck**
Erstellung eines Gold-Standards zur Evaluation einer automatisierten NLP-Pipeline (Masterarbeit).
Keine kommerzielle Nutzung.

**Speicherdauer**
Für die Dauer der Masterarbeit; danach anonymisiert archiviert (voraussichtlich bis Ende 2026).

**Weitergabe**
Keine Weitergabe von Rohdaten an Dritte. Veröffentlichungen enthalten nur aggregierte Ergebnisse
ohne Personenbezug.

**Ihre Rechte**
Widerruf und Datenlöschung jederzeit möglich (Kontakt: pantelri@hs-albsig.de).

---

Mit Klick auf *Zustimmen* bestätigen Sie, diese Hinweise gelesen zu haben, und stimmen
der beschriebenen Verarbeitung Ihrer Annotationsdaten zu.
""")

        def give_consent() -> None:
            db2 = SessionLocal()
            try:
                a = db2.get(Annotator, annotator_id())
                if a:
                    a.consent_given_at = datetime.now(timezone.utc)
                    db2.commit()
            finally:
                db2.close()
            ui.navigate.to("/annotate")

        with ui.row().classes("gap-3"):
            ui.button("Zustimmen und starten", on_click=give_consent).props("color=indigo")
            ui.button(
                "Abbrechen",
                on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/")),
            ).props("flat")
