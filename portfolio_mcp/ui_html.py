"""Loads the built UI (portfolio_mcp/ui_dist/app.html).

The file is built from ui/ with `npm run build` and committed, because the Python
build on Vercel doesn't run npm. CI checks that the committed file is up to date (M7).
"""

from functools import cache
from pathlib import Path

UI_URI = "ui://portfolio/app.html"
UI_FILE = Path(__file__).parent / "ui_dist" / "app.html"


@cache
def load_ui_html() -> str:
    try:
        return UI_FILE.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"{UI_FILE} is missing. Build it with: cd ui && npm ci && npm run build"
        ) from exc
