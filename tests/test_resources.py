"""The portfolio:// data resources."""

import json
from pathlib import Path
from typing import Any

import pytest
import respx
from mcp.shared.exceptions import MCPError
from mcp.types import TextResourceContents

from portfolio_mcp.server import build_server
from portfolio_mcp.settings import Settings
from tests.helpers import (
    FIXTURES,
    SITE,
    Caller,
    copy_fixtures,
    make_server,
)

STATIC_URIS = {
    "portfolio://profile": "application/json",
    "portfolio://projects": "application/json",
    "portfolio://case-studies": "application/json",
    "portfolio://resume": "application/json",
    "portfolio://llms-full": "text/plain",
}


async def read(client: Caller, uri: str) -> TextResourceContents:
    contents = (await client.read_resource(uri)).contents
    assert len(contents) == 1
    assert isinstance(contents[0], TextResourceContents)
    return contents[0]


async def read_json(client: Caller, uri: str) -> Any:
    return json.loads((await read(client, uri)).text)


async def test_resource_list(client: Caller) -> None:
    listed = {
        str(r.uri): r.mime_type for r in (await client.list_resources()).resources
    }
    # the ui:// page is listed too (its own tests are in test_ui.py)
    assert listed == {
        **STATIC_URIS,
        "ui://portfolio/app.html": "text/html;profile=mcp-app",
    }
    templates = (await client.list_resource_templates()).resource_templates
    assert [(t.uri_template, t.mime_type) for t in templates] == [
        ("portfolio://case-studies/{id}", "text/markdown")
    ]


async def test_profile_resource_is_the_full_profile(client: Caller) -> None:
    contents = await read(client, "portfolio://profile")
    assert contents.mime_type == "application/json"
    data = json.loads(contents.text)
    assert data["name"] == "Harsh Dadiya"
    assert data["experienceYears"] == 1.8
    assert data["email"] == "harshdadiya@gmail.com"
    assert [e["role"] for e in data["experience"]][:2] == [
        "Associate AI Engineer",
        "AI/ML Intern",
    ]
    assert len(data["education"]) == 2
    assert len(data["certifications"]) == 4
    assert data["photo"] == f"{SITE}/images/profile.jpg"


async def test_projects_resource(client: Caller) -> None:
    data = await read_json(client, "portfolio://projects")
    assert set(data) == {"recent", "openSource", "earlier"}
    assert data["openSource"][0]["repoStars"] == "81K"


async def test_case_study_index_matches_the_tool(client: Caller) -> None:
    from_resource = await read_json(client, "portfolio://case-studies")
    from_tool = (await client.call_tool("list_case_studies")).structured_content
    assert from_resource == from_tool


async def test_resume_resource_matches_the_tool(client: Caller) -> None:
    from_resource = await read_json(client, "portfolio://resume")
    from_tool = (await client.call_tool("get_resume")).structured_content
    assert from_resource == from_tool


@pytest.mark.parametrize("case_study_id", ["voice-agent", "generative-video"])
async def test_case_study_markdown_resource(client: Caller, case_study_id: str) -> None:
    contents = await read(client, f"portfolio://case-studies/{case_study_id}")
    assert contents.mime_type == "text/markdown"
    # the file as published, except that links to the site are full URLs
    source = (FIXTURES / f"{case_study_id}.md").read_text(encoding="utf-8")
    assert contents.text == source.replace("](/", f"]({SITE}/")
    assert "](/" not in contents.text


async def test_unknown_case_study_resource_lists_valid_ids(client: Caller) -> None:
    with pytest.raises(MCPError) as caught:
        await client.read_resource("portfolio://case-studies/nope")
    assert "voice-agent" in str(caught.value)
    assert "generative-video" in str(caught.value)


async def test_unknown_resource(client: Caller) -> None:
    with pytest.raises(MCPError):
        await client.read_resource("portfolio://nothing-here")


# -- llms-full -------------------------------------------------------------------


async def test_llms_full_from_a_fixture_file(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    (tmp_path / "llms-full.txt").write_text("whole site, as text\n", encoding="utf-8")
    contents = await read(Caller(make_server(path)), "portfolio://llms-full")
    assert contents.mime_type == "text/plain"
    assert contents.text == "whole site, as text\n"


async def test_llms_full_without_a_file_is_a_clear_error(client: Caller) -> None:
    # there is no llms-full.txt in tests/fixtures
    with pytest.raises(MCPError) as caught:
        await client.read_resource("portfolio://llms-full")
    assert "couldn't be loaded" in str(caught.value)


@respx.mock
async def test_llms_full_over_http_is_fetched_once_and_cached() -> None:
    route = respx.get(f"{SITE}/llms-full.txt").respond(200, text="plain text page")
    client = Caller(build_server(Settings(portfolio_url=SITE)))
    # each Caller call is a new connection, but the loader (and its cache) is shared
    assert (await read(client, "portfolio://llms-full")).text == "plain text page"
    assert (await read(client, "portfolio://llms-full")).text == "plain text page"
    assert route.call_count == 1


@respx.mock
async def test_llms_full_when_the_site_is_down() -> None:
    respx.get(f"{SITE}/llms-full.txt").respond(503)
    client = Caller(build_server(Settings(portfolio_url=SITE)))
    with pytest.raises(MCPError) as caught:
        await client.read_resource("portfolio://llms-full")
    assert "couldn't be loaded" in str(caught.value)
