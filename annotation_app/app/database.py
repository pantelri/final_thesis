import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load .env from the annotation_app directory
load_dotenv(Path(__file__).parent.parent / ".env")


class Base(DeclarativeBase):
    pass


def _build_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # Fallback: assemble from parts (useful for scripts run outside Docker)
    user = os.environ.get("POSTGRES_USER", "annotation")
    pw = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "annotation")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


def _pin_driver(url: str) -> str:
    """Use psycopg2 explicitly: SQLAlchemy >= 2.1 maps a bare postgresql:// to
    psycopg (v3), which is not installed in the image."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


engine = create_engine(_pin_driver(_build_url()), pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
