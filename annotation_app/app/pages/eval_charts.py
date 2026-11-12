"""Dashboard widgets for /auswertung: model bar chart, human list, heatmaps.

All widgets take precomputed ``Stats`` (see app.agreement) and only render.
Colour scale for agreement cells: one hue (indigo), light = low, dark = high.
"""
from html import escape

from nicegui import ui

from ..agreement import Stats

C_MODEL, C_MODEL_SEL, C_HUMAN = "#a5b4fc", "#4f46e5", "#0d9488"
BAR_H = 220   # px for 100 %


def pct(x: float) -> str:
    return f"{round(100 * x)} %"


def html(content: str):
    """ui.html across NiceGUI versions (3.x requires `sanitize`; content is escaped here)."""
    try:
        return ui.html(content, sanitize=False)
    except TypeError:
        return ui.html(content)


def cell_style(agr: float | None) -> str:
    if agr is None:
        return "background:#f9fafb;color:#d1d5db"
    # Scale spans 50–100 % (almost all values live there); ≤ 50 % = lightest.
    t = max(0.0, min(1.0, (agr - 0.5) / 0.5))
    light = 95 - 62 * t                          # 95 % (≤50) → 33 % (100) lightness
    fg = "white" if t > 0.5 else "#1f2937"
    return f"background:hsl(239,70%,{light:.0f}%);color:{fg}"


def model_bars(models: list[Stats], selected: str, on_select, reference: Stats | None) -> None:
    """Vertical bars, height linear in agreement; click selects the model."""
    with ui.element("div").classes("relative w-full overflow-x-auto"):
        # Fixed geometry: row padding 24px, each bar area = 20px label + BAR_H, so a bar's
        # top sits at 24 + 20 + BAR_H·(1 − agreement) — the reference line uses the same.
        with ui.row().classes("items-start gap-4 no-wrap px-2").style("padding-top:24px"):
            for m in models:
                sel = m.name == selected
                with ui.column().classes("items-center gap-1 cursor-pointer shrink-0").style(
                        "width:84px").on("click", lambda _, n=m.name: on_select(n)):
                    area = ui.element("div").classes("flex flex-col justify-end items-center").style(
                        f"height:{BAR_H + 20}px;width:100%")
                    with area:
                        ui.label(pct(m.agreement)).classes(
                            "text-sm font-semibold leading-5 " +
                            ("text-indigo-700" if sel else "text-gray-600")).style("height:20px")
                        bar = ui.element("div")
                    bar.classes("w-12 rounded-t transition-all").style(
                        f"height:{max(2, BAR_H * m.agreement):.0f}px;"
                        f"background:{C_MODEL_SEL if sel else C_MODEL};"
                        + ("box-shadow:0 0 0 3px #c7d2fe;" if sel else "")).tooltip(
                        f"{m.name}: {m.n_match}/{m.n_compared} gleiche Urteile, "
                        f"{m.n_units} gemeinsame Einheiten")
                    ui.label(m.name).classes("text-xs text-center leading-tight h-8 " +
                                             ("font-bold" if sel else "text-gray-500"))
        if reference and reference.n_compared:
            top = 24 + 20 + BAR_H * (1 - reference.agreement)
            html(f'<div style="position:absolute;left:0;right:0;top:{top:.0f}px;'
                 f'border-top:2px dashed {C_HUMAN};pointer-events:none">'
                 f'<span style="position:absolute;right:4px;top:-18px;font-size:11px;'
                 f'color:{C_HUMAN}">Andere Annotator·innen {pct(reference.agreement)}</span></div>')


def human_list(humans: list[Stats]) -> None:
    if not humans:
        ui.label("Keine Annotator·innen mit so vielen gemeinsamen Einheiten.").classes(
            "text-sm text-gray-500")
        return
    for h in humans:
        with ui.row().classes("w-full items-center gap-3 no-wrap"):
            ui.label(h.name).classes("w-32 shrink-0 text-sm font-medium")
            with ui.element("div").classes("grow bg-gray-100 rounded h-4 overflow-hidden"):
                ui.element("div").classes("h-4").style(
                    f"width:{100 * h.agreement:.1f}%;background:{C_HUMAN}")
            ui.label(pct(h.agreement)).classes("w-12 text-right text-sm font-mono")
            ui.label(f"n={h.n_units}").classes("w-14 text-right text-xs text-gray-400")


def heatmap(names: list[str], cells: dict[tuple[str, str], Stats], min_shared: int) -> None:
    """Symmetric pair matrix; cells with fewer than `min_shared` shared units are blank."""
    head = "".join(f'<th style="writing-mode:vertical-rl;transform:rotate(180deg);'
                   f'padding:4px;font-weight:500">{escape(n)}</th>' for n in names)
    rows = []
    for a in names:
        tds = []
        for b in names:
            if a == b:
                tds.append('<td style="background:#e5e7eb;text-align:center">–</td>')
                continue
            s = cells.get((a, b))
            ok = s is not None and s.n_compared and s.n_units >= min_shared
            tip = (f"{a} × {b}: {pct(s.agreement)} bei {s.n_units} gemeinsamen Einheiten"
                   if s else "keine gemeinsamen Einheiten")
            tds.append(f'<td title="{escape(tip)}" style="{cell_style(s.agreement if ok else None)};'
                       f'text-align:center;padding:4px 6px;min-width:44px">'
                       f'{pct(s.agreement) if ok else "·"}'
                       f'{f"<br><span style=font-size:10px;opacity:.75>n={s.n_units}</span>" if ok else ""}'
                       "</td>")
        rows.append(f'<tr><th style="text-align:right;padding:4px 8px;font-weight:500;'
                    f'white-space:nowrap">{escape(a)}</th>{"".join(tds)}</tr>')
    html('<div style="overflow-x:auto"><table style="border-collapse:separate;border-spacing:2px;'
         f'font-size:12px"><tr><th></th>{head}</tr>{"".join(rows)}</table></div>')


def obligation_table(obligations: list[tuple[str, str]], columns: list[str],
                     cells: dict[tuple[str, str], Stats], min_shared: int) -> None:
    """Rows = obligations (id, title), columns = comparison partners; your agreement."""
    head = "".join(f'<th style="padding:4px 6px;font-weight:500;font-size:11px">{escape(c)}</th>'
                   for c in columns)
    rows = []
    for oid, title in obligations:
        tds = []
        for c in columns:
            s = cells.get((oid, c))
            ok = s is not None and s.n_compared and s.n_units >= min_shared
            tip = f"{oid} · {c}: {s.n_match}/{s.n_compared} gleiche Urteile" if ok else ""
            tds.append(f'<td title="{escape(tip)}" style="{cell_style(s.agreement if ok else None)};'
                       f'text-align:center;padding:4px 6px">{pct(s.agreement) if ok else "·"}'
                       f'{f"<br><span style=font-size:10px;opacity:.75>n={s.n_units}</span>" if ok else ""}'
                       "</td>")
        rows.append(f'<tr><th style="text-align:left;padding:4px 8px;font-weight:500" '
                    f'title="{escape(title)}"><span style="font-family:monospace">{escape(oid)}</span> '
                    f'<span style="color:#6b7280;font-size:11px">{escape(title[:48])}'
                    f'{"…" if len(title) > 48 else ""}</span></th>{"".join(tds)}</tr>')
    html('<div style="overflow-x:auto"><table style="border-collapse:separate;border-spacing:2px;'
         f'font-size:12px;width:100%"><tr><th></th>{head}</tr>{"".join(rows)}</table></div>')
