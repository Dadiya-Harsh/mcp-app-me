"""MCP Apps wiring (M4): get_profile points at the UI, the UI resource has its CSP."""

from typing import Any

from mcp.types import TextResourceContents

from portfolio_mcp.ui_html import UI_FILE, UI_URI, load_ui_html
from tests.helpers import Caller


def test_built_ui_is_committed() -> None:
    html = load_ui_html()
    assert UI_FILE.name == "app.html"
    assert html.lstrip().lower().startswith("<!doctype html")
    # Single file: scripts and styles are inline, nothing is loaded from outside.
    assert '<script type="module" crossorigin src=' not in html
    assert '<link rel="stylesheet"' not in html


async def test_get_profile_points_at_the_ui(client: Caller) -> None:
    tools = {t.name: t for t in (await client.list_tools()).tools}
    meta: dict[str, Any] = tools["get_profile"].meta or {}
    assert meta["ui"]["resourceUri"] == UI_URI
    # no other tool shows the UI yet (M5 and M6 add theirs)
    others = {
        n for n, t in tools.items() if n != "get_profile" and "ui" in (t.meta or {})
    }
    assert others == set()


async def test_ui_resource(client: Caller) -> None:
    listed = {str(r.uri): r for r in (await client.list_resources()).resources}
    assert listed[UI_URI].mime_type == "text/html;profile=mcp-app"

    contents = (await client.read_resource(UI_URI)).contents
    assert len(contents) == 1
    item = contents[0]
    assert isinstance(item, TextResourceContents)
    assert item.mime_type == "text/html;profile=mcp-app"
    assert item.text == load_ui_html()

    ui = (item.meta or {})["ui"]
    assert ui["csp"] == {"resourceDomains": ["https://www.harshdadiya.in"]}
    assert ui["prefersBorder"] is False


async def test_get_profile_still_returns_text_and_data(client: Caller) -> None:
    result = await client.call_tool("get_profile")
    assert not result.is_error
    assert result.content and result.structured_content
    assert result.structured_content["name"] == "Harsh Dadiya"
