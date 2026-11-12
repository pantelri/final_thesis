#!/usr/bin/env python3
"""
Create test annotators and one admin for local development.

Usage:
    cd annotation_app
    python -m scripts.seed_annotators

Prints the plaintext codes — note them down. They are never stored in the DB.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.auth import create_annotator, generate_code
from app.database import SessionLocal

SEED: list[tuple[str, str, bool]] = [
    # (label, plaintext_code_or_empty_to_generate, is_admin)
    ("Prüfer A",  "TEST-AAAA-1111", False),
    ("Prüfer B",  "TEST-BBBB-2222", False),
    ("Admin",     "ADMIN-XXXX-9999", True),
]


def main() -> None:
    db = SessionLocal()
    try:
        print("Seeding annotators (codes are shown only once):\n")
        for label, code, is_admin in SEED:
            plain = code or generate_code()
            ann, plain = create_annotator(db, plain, label=label, is_admin=is_admin)
            role = "ADMIN" if is_admin else "Annotator"
            print(f"  [{role}] {label!r:20s}  code: {plain}")
        print("\nDone. Store the codes securely — they cannot be recovered from the database.")
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
