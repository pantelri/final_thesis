"""Plain FastAPI routes mounted on the NiceGUI app (non-page endpoints)."""
import os

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app

from .database import SessionLocal
from .models import Company


def _is_authenticated() -> bool:
    """Best-effort auth check. Annual reports are public, so on any storage
    access issue we still allow the download."""
    try:
        return bool(app.storage.user.get("annotator_id"))
    except Exception:
        return True


@app.get("/pdf/{company_id}")
def serve_pdf(company_id: str):
    """Stream a company's annual-report PDF for in-browser viewing."""
    if not _is_authenticated():
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")

    db = SessionLocal()
    try:
        company = db.get(Company, company_id)
        pdf_path = company.pdf_path if company else None
    finally:
        db.close()

    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF nicht gefunden.")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{company_id}.pdf",
        content_disposition_type="inline",
    )
