#!/usr/bin/env python3
"""
Create annotators by name and print their one-time access codes.

    docker compose exec app python -m scripts.add_annotators Hanna Marcus Felix Jerome Richard

Names that already exist (same label) are skipped. Codes are printed once and
only their hash is stored — note them down immediately.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from app.auth import create_annotator  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Annotator  # noqa: E402


def main(names: list[str]) -> None:
    if not names:
        print(__doc__)
        sys.exit(1)
    db = SessionLocal()
    try:
        existing = {a.label for a in db.query(Annotator).all()}
        for name in names:
            if name in existing:
                print(f"  übersprungen (existiert bereits): {name}")
                continue
            ann, code = create_annotator(db, "", label=name)
            print(f"  #{ann.id:<3d} {name:12s} Code: {code}")
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1:])
