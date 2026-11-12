"""
pdf_to_md.py

Konvertiert eine PDF-Datei aus dem Input-Ordner mithilfe der Adobe PDF Services API
in eine Markdown-Datei und speichert diese in einem Zeitstempel-Unterordner des Output-Ordners.

Verwendete Bereinigungsfunktionen aus pdf_to_markdown.py:
  - adobe_elem_to_markdown  : Wandelt jedes Adobe-Strukturelement in Markdown um
  - html_bold_to_markdown   : Konvertiert HTML-Bold-Tags (<b>…</b>) in Markdown (**…**)
  - word_count              : Filtert inhaltsleere Elemente heraus
  - markdown_to_plain_text  : Wird für Debug-Logging (Vorschau) verwendet
"""

import io
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Funktionen aus pdf_to_markdown importieren
# ---------------------------------------------------------------------------
from Ingestion.transform_md_file import (
    adobe_elem_to_markdown,
    html_bold_to_markdown,
    markdown_to_plain_text,
    word_count,
)

from Ingestion.adobe_extraction import load_credentials, extract_pdf_with_adobe
# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Pfade relativ zum Projekt-Stammverzeichnis (eine Ebene über Ingestion/)
_SCRIPT_DIR       = Path(__file__).parent.parent
INPUT_DIR         = _SCRIPT_DIR / "Input"
OUTPUT_DIR        = _SCRIPT_DIR / "Output"
CREDENTIALS_PATH  = _SCRIPT_DIR / "pdfservices-api-credentials.json"



# ===========================================================================
# Markdown-Konvertierung
# ===========================================================================

def csv_bytes_to_markdown_table(csv_bytes: bytes) -> str:
    """
    Wandelt den Inhalt einer CSV-Datei (als Bytes) in eine Markdown-Tabelle um.
    Fallback für Tabellen, die adobe_elem_to_markdown nicht vollständig abdeckt.
    """
    import csv

    text  = csv_bytes.decode("utf-8", errors="replace")
    lines = list(csv.reader(io.StringIO(text)))
    if not lines:
        return ""

    rows = []
    for i, row in enumerate(lines):
        # Zellen mit Leerzeichen auffüllen, falls eine Zeile kürzer ist
        cells      = [cell.replace("|", "\\|").strip() for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")

    return "\n".join(rows) + "\n"


def elements_to_markdown(elements: list) -> str:
    """
    Iteriert über alle Adobe-Strukturelemente und wandelt sie mithilfe von
    adobe_elem_to_markdown() (aus pdf_to_markdown.py) in Markdown-Text um.

    Angewendete Bereinigungsschritte pro Element:
      1. html_bold_to_markdown : HTML <b>-Tags → Markdown **fett**
      2. adobe_elem_to_markdown: Pfad-basierte Markdown-Konvertierung
      3. word_count             : Leere / inhaltlose Einträge werden übersprungen
    """
    parts     = []
    prev_path = ""

    for elem in elements:
        path = elem.get("Path", "")
        text = elem.get("Text") or ""

        # Schritt 1: HTML Bold → Markdown Bold (aus pdf_to_markdown.py)
        text = html_bold_to_markdown(text)

        # Schritt 2: Pfad-basierte Konvertierung (aus pdf_to_markdown.py)
        md_text, _ = adobe_elem_to_markdown(path, text, prev_path)

        # Schritt 3: Inhaltsleere Ergebnisse überspringen (aus pdf_to_markdown.py)
        plain = markdown_to_plain_text(md_text)
        if md_text and word_count(plain) == 0:
            # Strukturelle Zeichen (|, Leerzeilen) dennoch behalten
            if md_text.strip() not in ("", "|"):
                parts.append(md_text)
        elif md_text:
            parts.append(md_text)

        if path:
            prev_path = path

    return "".join(parts)


def build_markdown(zip_bytes: bytes, pdf_stem: str) -> str:
    """
    Entpackt das Adobe-Ergebnis-ZIP, liest structuredData.json und
    erzeugt daraus den vollständigen Markdown-Text.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zip_names = zf.namelist()
        logger.debug("ZIP-Inhalt: %s", zip_names)

        # structuredData.json einlesen
        if "structuredData.json" not in zip_names:
            raise ValueError("Kein 'structuredData.json' im Adobe-Ergebnis-ZIP gefunden.")

        with zf.open("structuredData.json") as fh:
            structured_data = json.load(fh)

        elements = structured_data.get("elements", [])
        logger.info("Adobe-Strukturelemente gefunden: %d", len(elements))

        # Markdown aus Strukturelementen aufbauen
        markdown_text = elements_to_markdown(elements)

    # Metadaten-Header
    header = (
        f"# {pdf_stem}\n\n"
        f"> Extrahiert am {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} "
        f"via Adobe PDF Services\n\n---\n\n"
    )

    return header + markdown_text


# ===========================================================================
# Hauptfunktion
# ===========================================================================

def convert_pdf_to_markdown(
    pdf_path: Path,
    output_subdir: Path,
) -> Path:
    """
    Vollständige Pipeline: PDF → Adobe API → structuredData.json → Markdown-Datei.

    Gibt den Pfad zur erzeugten .md-Datei zurück.
    """
    credentials = load_credentials(CREDENTIALS_PATH)
    zip_bytes   = extract_pdf_with_adobe(pdf_path, credentials)
    markdown    = build_markdown(zip_bytes, pdf_path.stem)

    output_file = output_subdir / f"{pdf_path.stem}.md"
    output_file.write_text(markdown, encoding="utf-8")
    logger.info("Markdown-Datei gespeichert: %s", output_file)

    # Kurze Vorschau im Log
    preview_lines = markdown.splitlines()[:10]
    logger.info("Vorschau (erste 10 Zeilen):\n%s", "\n".join(preview_lines))

    return output_file
