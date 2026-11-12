import hashlib
import os
import secrets

from sqlalchemy.orm import Session

from .models import Annotator


def hash_code(code: str) -> str:
    """Hash an access code with PBKDF2-SHA256 using SECRET_KEY as salt."""
    salt = os.environ.get("SECRET_KEY", "dev-only-secret").encode()
    key = hashlib.pbkdf2_hmac("sha256", code.strip().upper().encode(), salt, iterations=100_000)
    return key.hex()


def generate_code(length: int = 12) -> str:
    """
    Generate a random access code from a 32-character alphabet (no 0/O/1/I).
    Default length 12 gives 32^12 ≈ 1.2 × 10^18 possible codes (~60 bits).
    Never pass length < 12.
    """
    assert length >= 12, "Code length must be at least 12 characters"
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def verify_annotator(db: Session, code: str) -> Annotator | None:
    """Return the Annotator for the given plaintext code, or None if not found."""
    code_hash = hash_code(code)
    return db.query(Annotator).filter_by(code_hash=code_hash).first()


def create_annotator(db: Session, code: str, label: str = "", is_admin: bool = False) -> tuple[Annotator, str]:
    """Create a new annotator. Returns (annotator, plaintext_code)."""
    plain = code or generate_code()
    ann = Annotator(code_hash=hash_code(plain), label=label or None, is_admin=is_admin)
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann, plain
