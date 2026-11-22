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


UI_TOOLS = {"get_profile", "list_case_studies", "get_case_study", "list_projects"}


async def test_ui_tools_point_at_the_ui(client: Caller) -> None:
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in UI_TOOLS:
        meta: dict[str, Any] = tools[name].meta or {}
        assert meta["ui"]["resourceUri"] == UI_URI, name
    # everything else stays plain text (the contact screen comes in M6)
    others = {
        n for n, t in tools.items() if n not in UI_TOOLS and "ui" in (t.meta or {})
    }
    assert others == set()


async def test_ui_tools_are_open_to_the_model_and_the_app(client: Caller) -> None:
    # The UI calls get_case_study and list_projects itself (tabs, "show all"). Hosts
    # only allow that for tools whose visibility includes "app". Unset means both.
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in UI_TOOLS:
        visibility = ((tools[name].meta or {}).get("ui") or {}).get("visibility")
        assert visibility in (None, ["model", "app"]), name


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


async def test_case_study_and_project_tools_still_return_text_and_data(
    client: Caller,
) -> None:
    for name, args in (
        ("list_case_studies", {}),
        ("get_case_study", {"id": "voice-agent", "section": "hard"}),
        ("list_projects", {"group": "recent"}),
    ):
        result = await client.call_tool(name, args)
        assert not result.is_error, name
        assert result.content and result.structured_content, name
