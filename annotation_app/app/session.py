"""Session helpers: authentication and consent gates."""
from nicegui import app, ui

from .database import SessionLocal
from .models import Annotator


def annotator_id() -> int | None:
    return app.storage.user.get("annotator_id")


def require_auth() -> bool:
    """Redirect to login if not authenticated. Returns False when redirected."""
    if not annotator_id():
        ui.navigate.to("/")
        return False
    return True


def require_consent() -> bool:
    """Redirect to consent page if consent not yet given. Returns False when redirected."""
    db = SessionLocal()
    try:
        ann = db.get(Annotator, annotator_id())
        if not ann or not ann.consent_given_at:
            ui.navigate.to("/consent")
            return False
        return True
    finally:
        db.close()
