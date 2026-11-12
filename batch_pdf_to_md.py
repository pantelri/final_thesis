"""
batch_pdf_to_md.py

Konvertiert alle PDF-Dateien im Input-Ordner in Markdown-Dateien
und speichert diese gemeinsam in einem einzigen Output-Unterordner.

Nur PDF → MD-Konvertierung; kein Chunking, Rechunking oder Embedding.
"""

import logging
import sys
from pathlib import Path

from adobe.pdfservices.operation.exception.exceptions import (
    ServiceApiException,
    ServiceUsageException,
    SdkException,
)

from Ingestion.adobe_extraction import load_credentials
from Ingestion.pdf_to_md import build_markdown, convert_pdf_to_markdown
from Ingestion.adobe_extraction import extract_pdf_with_adobe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_SCRIPT_DIR      = Path(__file__).parent
INPUT_DIR        = _SCRIPT_DIR / "Input"
OUTPUT_DIR       = _SCRIPT_DIR / "Output" / "md_files"
CREDENTIALS_PATH = _SCRIPT_DIR / "pdfservices-api-credentials.json"


def main() -> None:
    if not INPUT_DIR.exists():
        logger.error("Input-Ordner nicht gefunden: %s", INPUT_DIR)
        sys.exit(1)

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.error("Keine PDF-Dateien im Input-Ordner gefunden.")
        sys.exit(1)

    logger.info("Gefundene PDFs: %d", len(pdf_files))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Output-Ordner: %s", OUTPUT_DIR)

    credentials = load_credentials(CREDENTIALS_PATH)

    success, failed = [], []

    for i, pdf_path in enumerate(pdf_files, start=1):
        out_file = OUTPUT_DIR / f"{pdf_path.stem}.md"

        if out_file.exists():
            logger.info("[%d/%d] Übersprungen (existiert bereits): %s", i, len(pdf_files), pdf_path.name)
            success.append(pdf_path.name)
            continue

        logger.info("[%d/%d] Verarbeite: %s", i, len(pdf_files), pdf_path.name)
        try:
            zip_bytes    = extract_pdf_with_adobe(pdf_path, credentials)
            markdown     = build_markdown(zip_bytes, pdf_path.stem)
            out_file.write_text(markdown, encoding="utf-8")
            logger.info("  → Gespeichert: %s", out_file.name)
            success.append(pdf_path.name)
        except (ServiceApiException, ServiceUsageException, SdkException) as exc:
            logger.error("  → Adobe-Fehler bei %s: %s", pdf_path.name, exc)
            failed.append(pdf_path.name)
        except Exception as exc:
            logger.exception("  → Unerwarteter Fehler bei %s: %s", pdf_path.name, exc)
            failed.append(pdf_path.name)

    print(f"\n{'='*50}")
    print(f"Fertig: {len(success)}/{len(pdf_files)} erfolgreich konvertiert")
    print(f"Output-Ordner: {OUTPUT_DIR}")
    if failed:
        print(f"\nFehlgeschlagen ({len(failed)}):")
        for name in failed:
            print(f"  - {name}")
    print("=" * 50)


if __name__ == "__main__":
    main()
