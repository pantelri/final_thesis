"""Annotation page — pure UI construction.

``build_form`` lays out the cards and wires every widget's ``on_change`` /
``on_click`` to a :class:`FormController` method. Widgets the handlers need to
mutate later register themselves in ``ctrl.refs``. No DB access here.
"""
from nicegui import ui

PHASE_LABELS = {
    "double": ("Zweiturteil", "teal",
               "Diese Einheit hat bisher ein Urteil und erhält Ihr unabhängiges zweites."),
    "clarify": ("Klärung · Dritturteil", "amber-8",
                "Die bisherigen zwei Urteile weichen ab – Ihr Urteil hilft bei der Klärung."),
}


def _progress(ctx: dict, meta: dict) -> None:
    q = meta["quota"]
    with ui.row().classes("items-center justify-between mt-4 w-full"):
        with ui.row().classes("items-center gap-2"):
            if q["reached"]:
                ui.label(f"Ziel erreicht ✓ · {q['extra']} freiwillig zusätzlich").classes(
                    "text-sm font-medium text-green-700")
            else:
                ui.label(f"Ihr Fortschritt: {q['done']} von {q['quota']}").classes(
                    "text-sm font-medium text-indigo-700")
            if ctx["phase"] in PHASE_LABELS:
                label_txt, color, tip = PHASE_LABELS[ctx["phase"]]
                ui.badge(label_txt).props(f"color={color} outline").tooltip(tip)
        ui.linear_progress(value=q["fraction"], show_value=False).classes("w-48").props(
            f"color={'green' if q['reached'] else 'indigo'} rounded size=8px")


def _obligation_card(ctx: dict) -> None:
    with ui.card().classes("w-full bg-indigo-50 border-l-4 border-indigo-500"):
        with ui.row().classes("items-start gap-3 mb-1"):
            ui.badge(ctx["ob_id"]).props("color=indigo")
            ui.label(ctx["ob_title"]).classes("text-lg font-semibold leading-tight")
        if ctx["ob_legal"]:
            ui.label(f"Rechtsgrundlage: {ctx['ob_legal']}").classes(
                "text-sm text-gray-600 mt-1")
        if ctx["ob_criterion"]:
            with ui.expansion("Prüfkriterium einblenden").classes("mt-2 text-sm"):
                ui.label(ctx["ob_criterion"]).classes(
                    "text-sm text-gray-700 whitespace-pre-wrap")


def _passage_card(ctx: dict) -> None:
    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between mb-2"):
            with ui.row().classes("items-center gap-2"):
                ui.label("Textabschnitt").classes(
                    "text-xs font-semibold text-gray-500 uppercase tracking-wider")
                ui.badge(ctx["co_name"]).props("color=grey-7 outline")
                if ctx["year"]:
                    ui.badge(f"Geschäftsjahr {ctx['year']}").props("color=teal-7 outline")
            if ctx["has_pdf"]:
                cid = ctx["company_id"]
                ui.button(
                    "Jahresabschluss (PDF)", icon="picture_as_pdf",
                    on_click=lambda: ui.navigate.to(f"/pdf/{cid}", new_tab=True),
                ).props("flat dense color=indigo size=sm").tooltip(
                    "Original-Jahresabschluss in neuem Tab öffnen")
        ui.separator()
        ui.markdown(ctx["passage_text"]).classes("text-sm mt-2 leading-relaxed")


def _too_long_section(ctrl, ctx: dict) -> None:
    section = ui.column().classes("w-full mt-4 gap-1 pl-1")
    section.set_visibility(False)
    ctrl.refs["too_long_section"] = section
    with section:
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("info_outline", size="sm", color="orange")
            ui.label("Markiere die Elemente, die für diese Pflicht NICHT relevant sind:").classes(
                "font-medium text-orange-700 text-sm")
        for s in ctx["sents"]:
            is_table = s["type"] == "table"
            if is_table:
                n_rows = len([l for l in s["text"].split("\n") if l.strip().startswith("|")])
                display = (f"[Tabelle, {n_rows} Zeile{'n' if n_rows != 1 else ''}]  "
                           + s["text"].split("\n")[0][:60])
            else:
                t = s["text"]
                display = t[:160] + ("…" if len(t) > 160 else "")
            with ui.row().classes("items-start gap-2 py-0.5"):
                ui.checkbox(
                    "", on_change=lambda e, idx=s["idx"]: ctrl.on_irrelevant_toggle(idx, e.value),
                ).props("dense")
                ui.label("📊" if is_table else f"#{s['idx'] + 1:02d}").classes(
                    "text-xs font-mono text-gray-400 mt-1 w-8 shrink-0")
                ui.label(display).classes("text-sm text-gray-700 leading-snug")


def _too_short_section(ctrl) -> None:
    section = ui.column().classes("w-full mt-4 gap-2 pl-1")
    section.set_visibility(False)
    ctrl.refs["too_short_section"] = section
    with section:
        with ui.row().classes("items-center gap-2"):
            ui.icon("search", size="sm", color="indigo")
            ui.label("Welche Informationen, Tabellen oder Erklärungen fehlen Ihnen?").classes(
                "font-medium text-indigo-700 text-sm")
        ui.textarea(
            placeholder="z. B. „Die Aufschlüsselung der sonstigen Rückstellungen fehlt …“",
            on_change=lambda e: ctrl.set_missing_info(e.value),
        ).classes("w-full").props("rows=3 outlined autogrow")
        with ui.row().classes("items-center gap-3"):
            ctrl.refs["suggest_btn"] = ui.button(
                "KI-Vorschläge holen", icon="auto_awesome",
                on_click=lambda: ctrl.fetch_suggestions(),
            ).props("color=indigo outline size=sm")
            ctrl.refs["suggest_spinner"] = ui.spinner(size="sm").classes("text-indigo-600")
            ctrl.refs["suggest_spinner"].set_visibility(False)
        ctrl.refs["suggestions_container"] = ui.column().classes("w-full gap-1 mt-1")


def _question1(ctrl, ctx: dict) -> None:
    with ui.card().classes("w-full"):
        ui.label("Frage 1 · Relevanz und Länge").classes(
            "font-semibold text-base mb-4 text-indigo-800")
        ui.label("Ist dieser Abschnitt relevant für die Pflicht?").classes(
            "font-medium text-gray-700")
        ui.radio({"yes": "Ja", "no": "Nein"},
                 on_change=lambda e: ctrl.set_relevant(e.value)).props("inline")
        ui.separator().classes("my-4")
        ui.label("Wie beurteilen Sie die Länge des Abschnitts?").classes(
            "font-medium text-gray-700")
        ui.radio({"ok": "Passend", "too_short": "Zu kurz", "too_long": "Zu lang"},
                 on_change=lambda e: ctrl.on_length_change(e.value)).props("inline")
        _too_long_section(ctrl, ctx)
        _too_short_section(ctrl)


def _question2(ctrl) -> None:
    with ui.card().classes("w-full"):
        ui.label("Frage 2 · Anwendbarkeit").classes(
            "font-semibold text-base mb-4 text-indigo-800")
        ui.label("Muss die Gesellschaft diese Pflicht erfüllen?").classes(
            "font-medium text-gray-700")
        ui.radio({"yes": "Ja", "no": "Nein", "unsure": "Unklar"},
                 on_change=lambda e: ctrl.on_applicable_change(e.value)).props("inline")


def _question3(ctrl) -> None:
    card = ui.card().classes("w-full border-2 border-green-300 bg-green-50")
    card.set_visibility(False)
    ctrl.refs["fulfilled_card"] = card
    with card:
        ui.label("Frage 3 · Erfüllung").classes(
            "font-semibold text-base mb-4 text-indigo-800")
        ui.label("Ist die Pflicht durch den Abschnitt ausreichend erfüllt?").classes(
            "font-medium text-gray-700")
        ctrl.refs["fulfilled_radio"] = ui.radio(
            {"yes": "Ja", "no": "Nein"},
            on_change=lambda e: ctrl.set_fulfilled(e.value)).props("inline")


def _comment_and_submit(ctrl) -> None:
    with ui.card().classes("w-full"):
        ui.label("Kommentar (optional):").classes("font-medium text-gray-700 mb-1")
        ctrl.refs["comment"] = ui.textarea(
            placeholder="Anmerkungen zum Abschnitt oder zur Pflicht …"
        ).classes("w-full").props("rows=3 outlined autogrow")

    ctrl.refs["submit_btn"] = ui.button(
        "Absenden →", on_click=lambda: ctrl.submit()
    ).classes("w-full mt-2").props("color=indigo size=lg")
    ctrl.refs["submit_btn"].set_enabled(False)
    ctrl.refs["validation_msg"] = ui.label("Bitte alle Pflichtfelder ausfüllen.").classes(
        "text-orange-500 text-sm text-center")


def build_form(ctrl, meta: dict) -> None:
    ctx = ctrl.ctx
    with ui.column().classes("max-w-3xl mx-auto px-4 pb-12 gap-4 w-full"):
        _progress(ctx, meta)
        _obligation_card(ctx)
        _passage_card(ctx)
        _question1(ctrl, ctx)
        _question2(ctrl)
        _question3(ctrl)
        _comment_and_submit(ctrl)
