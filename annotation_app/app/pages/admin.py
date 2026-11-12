"""Admin page — coverage/agreement stats + CSV/ZIP export (M5)."""
from nicegui import app, ui

from ..assignment import get_annotator_stats, get_coverage_stats
from ..database import SessionLocal
from ..export import (
    build_annotations_csv,
    build_bundle,
    build_irrelevant_csv,
    build_suggested_csv,
    timestamp,
)
from ..layout import render_header
from ..models import Annotator
from ..session import annotator_id, require_auth
from .admin_users import render_user_card


def _download(builder, filename: str, media_type: str) -> None:
    """Run a sync export builder against a fresh session and stream it."""
    db = SessionLocal()
    try:
        data = builder(db)
    finally:
        db.close()
    ui.download(data, filename, media_type)


@ui.page("/admin")
def admin_page() -> None:
    if not require_auth():
        return
    if not app.storage.user.get("is_admin"):
        ui.navigate.to("/annotate")
        return

    db = SessionLocal()
    try:
        ann = db.get(Annotator, annotator_id())
        ann_label = ann.label or f"Annotator #{annotator_id()}"
        stats = get_coverage_stats(db)
        ann_rows = get_annotator_stats(db)
    finally:
        db.close()

    render_header(ann_label)

    with ui.column().classes("max-w-3xl mx-auto mt-8 px-4 gap-6"):
        ui.label("Admin-Bereich").classes("text-2xl font-bold")

        # ── Assignment overview ──────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("Annotationsfortschritt").classes("font-semibold text-lg mb-3")

            max_k = stats["max_per_item"]
            phase_text = {
                "double": "Phase A · Zweiturteil (jede Einheit → 2 Urteile, Basis für α)",
                "clarify": f"Phase B · Klärung (strittige Einheiten → bis {max_k} Urteile)",
                "complete": "Abgeschlossen (doppelt abgedeckt, keine offene Klärung)",
            }
            phase_color = {"double": "teal", "clarify": "amber-8", "complete": "green"}
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.label("Aktuelle Phase:").classes("font-medium text-gray-600")
                ui.badge(phase_text.get(stats["phase"], stats["phase"])).props(
                    f"color={phase_color.get(stats['phase'], 'grey')}"
                )
            ui.label(
                f"Persönliches Ziel je Annotator: {stats['quota']} Einheiten "
                "(danach freiwillig weiter)."
            ).classes("text-sm text-gray-500 mb-3")

            total = stats["total_items"]

            def _pct(n: int) -> str:
                return f"{round(100 * n / total)} %" if total else "0 %"

            with ui.grid(columns=2).classes("w-full gap-3"):
                with ui.card().classes("bg-gray-50 p-3"):
                    ui.label("Einheiten gesamt").classes("text-xs text-gray-500 uppercase")
                    ui.label(str(total)).classes("text-3xl font-bold")

                with ui.card().classes("bg-teal-50 p-3"):
                    ui.label("Mind. 2× annotiert").classes("text-xs text-gray-500 uppercase")
                    ui.label(f"{stats['at_least_2']}  ({_pct(stats['at_least_2'])})").classes(
                        "text-3xl font-bold text-teal-700"
                    )

                with ui.card().classes("bg-amber-50 p-3"):
                    ui.label("Uneinig bei 2 Urteilen").classes("text-xs text-gray-500 uppercase")
                    ui.label(str(stats["disagree_at_2"])).classes(
                        "text-3xl font-bold text-amber-700"
                    )

                with ui.card().classes("bg-indigo-50 p-3"):
                    ui.label("Verteilung nach Urteilen").classes(
                        "text-xs text-gray-500 uppercase"
                    )
                    depth = stats["depth"]
                    parts = " · ".join(
                        f"{k}×: {depth[k]}" for k in sorted(depth)
                    )
                    ui.label(parts).classes("text-base font-mono font-semibold mt-1")

        # ── Per-annotator progress ───────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("Fortschritt je Annotator").classes("font-semibold text-lg mb-2")
            ui.table(
                columns=[
                    {"name": "id", "label": "ID", "field": "id", "align": "left"},
                    {"name": "label", "label": "Name", "field": "label", "align": "left"},
                    {"name": "done", "label": "Urteile", "field": "done", "sortable": True},
                    {"name": "status", "label": "Status", "field": "status", "align": "left"},
                ],
                rows=[
                    {**r, "status": (
                        "Admin" if r["is_admin"] else
                        (f"Ziel erreicht (+{r['done'] - stats['quota']} freiwillig)"
                         if r["done"] > stats["quota"] else "Ziel erreicht")
                        if r["quota_reached"] else
                        "noch keine Einwilligung" if not r["consent"] else
                        f"{r['done']} / {stats['quota']}"
                    )}
                    for r in ann_rows
                ],
                row_key="id",
            ).classes("w-full").props("dense flat")

        # ── Users / access codes ──────────────────────────────────────────────
        render_user_card()

        # ── Export ───────────────────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("Export").classes("font-semibold text-lg mb-1")
            ui.label(
                "Flacher CSV-Export aller Annotationen, verknüpft mit Einheit, "
                "Gesellschaft und Pflicht. Kodierung UTF-8 (Excel-kompatibel)."
            ).classes("text-gray-500 mb-3")

            with ui.row().classes("gap-3 flex-wrap"):
                ui.button(
                    "⬇ Alles als ZIP",
                    on_click=lambda: _download(
                        build_bundle,
                        f"hgb_annotation_export_{timestamp()}.zip",
                        "application/zip",
                    ),
                ).props("color=indigo")
                ui.button(
                    "Annotationen (CSV)",
                    on_click=lambda: _download(
                        build_annotations_csv, "annotations.csv", "text/csv"
                    ),
                ).props("flat color=indigo")
                ui.button(
                    "Irrelevante Sätze (CSV)",
                    on_click=lambda: _download(
                        build_irrelevant_csv, "irrelevant_sentences.csv", "text/csv"
                    ),
                ).props("flat color=indigo")
                ui.button(
                    "Zusätzliche Textstellen (CSV)",
                    on_click=lambda: _download(
                        build_suggested_csv, "suggested_passages.csv", "text/csv"
                    ),
                ).props("flat color=indigo")

            ui.label(
                "Inter-Annotator-Agreement: auf dem Server "
                "`docker compose exec app python -m scripts.iaa_alpha` ausführen "
                "(nutzt je Einheit nur die ersten zwei Urteile, Krippendorffs α "
                "mit Bootstrap-KI)."
            ).classes("text-xs text-gray-400 mt-3")

        with ui.row().classes("gap-3"):
            ui.button(
                "Zur Annotationsmaske",
                on_click=lambda: ui.navigate.to("/annotate"),
            ).props("color=indigo flat")
            ui.button(
                "Seite aktualisieren",
                on_click=lambda: ui.navigate.to("/admin"),
            ).props("flat")
