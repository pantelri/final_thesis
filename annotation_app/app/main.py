"""
NiceGUI annotation app — entry point.

Route registration happens via decorator side-effects: importing app.pages
registers all @ui.page routes; importing app.routes registers plain FastAPI
endpoints (e.g. PDF serving). Keep page/route logic in those modules — this
file only wires configuration and starts the server.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from nicegui import ui  # noqa: E402

from app import pages, routes  # noqa: E402,F401 — import side-effect registers routes


def main() -> None:
    storage_path = os.environ.get(
        "STORAGE_PATH",
        str(Path(__file__).parent.parent / ".nicegui_storage"),
    )
    Path(storage_path).mkdir(parents=True, exist_ok=True)

    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        storage_secret=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        title="HGB Annotation",
        favicon="📋",
        dark=False,
        show=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
