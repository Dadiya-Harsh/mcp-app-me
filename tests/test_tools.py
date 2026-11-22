"""Every tool end to end, through an in-process MCP client."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import respx
from mcp import Client
from mcp.types import CallToolResult

from tests.helpers import (
    MEDIUM_JSON,
    MEDIUM_URL,
    SITE,
    Caller,
    copy_fixtures,
    edit_content,
    make_server,
    text_of,
)

TOOL_NAMES = {
    "get_profile",
    "list_case_studies",
    "get_case_study",
    "list_projects",
    "get_recent_posts",
    "search_portfolio",
    "get_resume",
    "get_contact_options",
}


def structured(result: CallToolResult) -> dict[str, Any]:
    data = result.structured_content
    assert data is not None
    return dict(data)


# -- the tool list -------------------------------------------------------------


async def test_tool_list(client: Caller) -> None:
    tools = {t.name: t for t in (await client.list_tools()).tools}
    assert TOOL_NAMES <= set(tools)
    assert "get_availability" not in tools  # M6
    for name in TOOL_NAMES:
        tool = tools[name]
        assert tool.description, name
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True, name
        # only the tool that calls another service is open-world
        assert tool.annotations.open_world_hint is (name == "get_recent_posts"), name


async def test_instructions(client: Caller) -> None:
    instructions = await client.instructions()
    assert "get_contact_options" in instructions
    assert "Never invent" in instructions
    for name in TOOL_NAMES - {"get_case_study"}:
        assert name in instructions


# -- every tool gives text and structured data ----------------------------------


@respx.mock
@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("get_profile", {}),
        ("list_case_studies", {}),
        ("get_case_study", {"id": "voice-agent"}),
        ("list_projects", {}),
        ("get_recent_posts", {}),
        ("search_portfolio", {"query": "voice"}),
        ("get_resume", {}),
        ("get_contact_options", {}),
    ],
)
async def test_text_and_structured(
    client: Caller, name: str, args: dict[str, Any]
) -> None:
    respx.get(MEDIUM_URL).respond(200, json=MEDIUM_JSON)
    result = await client.call_tool(name, args)
    assert result.is_error is False
    assert text_of(result).strip()
    assert structured(result)  # not empty


# -- get_profile ----------------------------------------------------------------


async def test_profile_structured(client: Caller) -> None:
    data = structured(await client.call_tool("get_profile", {}))
    assert data["name"] == "Harsh Dadiya"
    assert data["experienceYears"] == 1.8
    assert data["openToRoles"] is True
    assert data["photo"] == f"{SITE}/images/profile.jpg"
    assert data["links"]["resume"] == f"{SITE}/resume"
    assert data["links"]["booking"] is None
    assert data["nowBuilding"]["name"] == "SecureWorkspace"
    assert len(data["focus"]) == 6
    assert [s["value"] for s in data["stats"]] == ["OpenMontage", "500+"]
    # work history and the email live elsewhere (resource / contact tool)
    assert "experience" not in data
    assert "email" not in data


async def test_profile_experience_follows_the_date() -> None:
    async with Client(make_server(today=date(2027, 1, 10))) as client:
        data = structured(await client.call_tool("get_profile", {}))
        assert data["experienceYears"] == 2.0
        assert "2.0 years" in text_of(await client.call_tool("get_profile", {}))


async def test_profile_hides_now_building_when_site_does(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    edit_content(path, lambda d: d["profile"]["nowBuilding"].update(show=False))
    async with Client(make_server(path)) as client:
        result = await client.call_tool("get_profile", {})
        assert structured(result)["nowBuilding"] is None
        assert "Now building" not in text_of(result)


# -- case studies ---------------------------------------------------------------


async def test_list_case_studies(client: Caller) -> None:
    data = structured(await client.call_tool("list_case_studies", {}))
    studies = data["caseStudies"]
    assert [s["id"] for s in studies] == ["voice-agent", "generative-video"]
    first = studies[0]
    assert first["url"] == f"{SITE}/case-studies/voice-agent"
    assert first["techStack"][:2] == ["Python", "FastAPI"]
    assert {
        "type",
        "title",
        "subtitle",
        "role",
        "team",
        "duration",
        "desc",
        "bullets",
    } <= set(first)
    assert "markdownUrl" not in first


async def test_get_case_study_all(client: Caller) -> None:
    result = await client.call_tool("get_case_study", {"id": "voice-agent"})
    data = structured(result)
    assert data["id"] == "voice-agent"
    assert data["requestedSection"] == "all"
    assert [s["id"] for s in data["sections"]] == [
        "overview",
        "problem",
        "architecture",
        "hard",
        "result",
    ]
    assert all(s["heading"] and s["markdown"] for s in data["sections"])
    assert [s["number"] for s in data["steps"]] == [1, 2, 3, 4]
    text = text_of(result)
    assert "## System Architecture" in text
    assert text.rstrip().endswith(f"{SITE}/case-studies/voice-agent")


async def test_get_case_study_one_section(client: Caller) -> None:
    result = await client.call_tool(
        "get_case_study", {"id": "voice-agent", "section": "architecture"}
    )
    data = structured(result)
    assert data["requestedSection"] == "architecture"
    assert [s["id"] for s in data["sections"]] == ["architecture"]
    assert len(data["steps"]) == 4
    assert "## The Problem" not in text_of(result)

    overview = await client.call_tool(
        "get_case_study", {"id": "voice-agent", "section": "overview"}
    )
    assert structured(overview)["steps"] == []


async def test_get_case_study_section_that_is_not_there(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    (tmp_path / "voice-agent.md").write_text(
        "# Title\n\n## Overview\nJust this.\n", encoding="utf-8"
    )
    async with Client(make_server(path)) as client:
        result = await client.call_tool(
            "get_case_study", {"id": "voice-agent", "section": "hard"}
        )
        assert result.is_error is True
        message = text_of(result)
        assert "no 'hard' section" in message
        assert "overview" in message  # says what is there


async def test_get_case_study_unknown_id_lists_valid_ids(client: Caller) -> None:
    result = await client.call_tool("get_case_study", {"id": "nope"})
    assert result.is_error is True
    assert "voice-agent" in text_of(result)
    assert "generative-video" in text_of(result)


async def test_get_case_study_bad_section_is_an_error(client: Caller) -> None:
    result = await client.call_tool(
        "get_case_study", {"id": "voice-agent", "section": "bogus"}
    )
    assert result.is_error is True


# -- projects -------------------------------------------------------------------


async def test_list_projects_all(client: Caller) -> None:
    data = structured(await client.call_tool("list_projects", {}))
    assert data["group"] == "all"
    projects = data["projects"]
    assert [p["title"] for p in projects["recent"]] == ["SecureWorkspace"]
    assert projects["openSource"][0]["repoStars"] == "81K"
    assert len(projects["earlier"]) == 4


async def test_list_projects_one_group(client: Caller) -> None:
    result = await client.call_tool("list_projects", {"group": "openSource"})
    projects = structured(result)["projects"]
    assert len(projects["openSource"]) == 1
    assert projects["recent"] == []
    assert projects["earlier"] == []
    text = text_of(result)
    assert "Open source" in text
    assert "Earlier" not in text


async def test_list_projects_bad_group(client: Caller) -> None:
    assert (await client.call_tool("list_projects", {"group": "x"})).is_error is True


# -- recent posts ---------------------------------------------------------------


@respx.mock
async def test_recent_posts(client: Caller) -> None:
    respx.get(MEDIUM_URL).respond(200, json=MEDIUM_JSON)
    result = await client.call_tool("get_recent_posts", {"limit": 2})
    data = structured(result)
    assert [p["title"] for p in data["posts"]] == ["Post one", "Post two"]
    assert data["posts"][0] == {
        "title": "Post one",
        "date": "2025-11-10",
        "tags": ["mcp"],
        "link": "https://medium.com/@harshdadiya/one",
    }
    assert data["unavailable"] is False
    assert data["mediumUrl"] == "https://medium.com/@harshdadiya"


@respx.mock
async def test_recent_posts_default_limit_is_five(client: Caller) -> None:
    articles = [
        {"title": f"Post {i}", "link": f"https://medium.com/p/{i}"} for i in range(8)
    ]
    respx.get(MEDIUM_URL).respond(200, json={"articles": articles})
    data = structured(await client.call_tool("get_recent_posts", {}))
    assert len(data["posts"]) == 5


@respx.mock
async def test_recent_posts_when_medium_fails_is_not_an_error(client: Caller) -> None:
    respx.get(MEDIUM_URL).respond(500)
    result = await client.call_tool("get_recent_posts", {})
    assert result.is_error is False
    data = structured(result)
    assert data["posts"] == []
    assert data["unavailable"] is True
    assert "https://medium.com/@harshdadiya" in text_of(result)


@pytest.mark.parametrize("limit", [0, 11, -1])
async def test_recent_posts_limit_bounds(client: Caller, limit: int) -> None:
    result = await client.call_tool("get_recent_posts", {"limit": limit})
    assert result.is_error is True


# -- search ---------------------------------------------------------------------


async def test_search_finds_case_study(client: Caller) -> None:
    result = await client.call_tool("search_portfolio", {"query": "voice"})
    data = structured(result)
    assert data["query"] == "voice"
    top = data["results"][0]
    assert top["type"] == "case-study"
    assert top["url"] == f"{SITE}/case-studies/voice-agent"
    assert 1 <= len(data["results"]) <= 5


async def test_search_looks_inside_the_case_study_text(client: Caller) -> None:
    # "interrupt" is in the voice agent write-up but not in its short description
    data = structured(
        await client.call_tool("search_portfolio", {"query": "interrupt"})
    )
    assert any("voice-agent" in (r["url"] or "") for r in data["results"])


async def test_search_other_content_types(client: Caller) -> None:
    data = structured(await client.call_tool("search_portfolio", {"query": "wappnet"}))
    assert {r["type"] for r in data["results"]} == {"experience"}


async def test_search_no_match(client: Caller) -> None:
    result = await client.call_tool(
        "search_portfolio", {"query": "kubernetes operator"}
    )
    assert result.is_error is False
    assert structured(result)["results"] == []
    assert "No matches" in text_of(result)


@pytest.mark.parametrize("query", ["", "x" * 201])
async def test_search_input_limits(client: Caller, query: str) -> None:
    assert (
        await client.call_tool("search_portfolio", {"query": query})
    ).is_error is True


async def test_search_skips_a_case_study_that_cannot_be_loaded(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    (tmp_path / "generative-video.md").unlink()
    async with Client(make_server(path)) as client:
        result = await client.call_tool("search_portfolio", {"query": "interrupt"})
        assert result.is_error is False
        assert structured(result)["results"]  # voice-agent text still searched


# -- resume and contact ---------------------------------------------------------


async def test_resume(client: Caller) -> None:
    data = structured(await client.call_tool("get_resume", {}))
    assert data == {
        "page": f"{SITE}/resume",
        "pdf": f"{SITE}/resume/Harsh_Dadiya_Resume.pdf",
        "docx": f"{SITE}/resume/Harsh_Dadiya_Resume.docx",
    }


async def test_contact_options(client: Caller) -> None:
    result = await client.call_tool("get_contact_options", {})
    data = structured(result)
    assert data["email"] == "harshdadiya@gmail.com"
    assert data["mailtoUrl"].startswith("mailto:harshdadiya@gmail.com?subject=")
    assert " " not in data["mailtoUrl"]  # the subject is URL-encoded
    assert data["contactPage"] == f"{SITE}/contact"
    assert data["linkedin"] == "https://www.linkedin.com/in/harsh-dadiya/"
    assert data["bookingUrl"] is None
    assert data["suggestedSubject"]
    assert "draft a message for you to send" in text_of(result)
    assert "none yet" in text_of(result)


async def test_contact_options_with_booking_link(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    book = "https://cal.example.test/harsh"
    edit_content(path, lambda d: d["profile"]["links"].update(booking=book))
    async with Client(make_server(path)) as client:
        result = await client.call_tool("get_contact_options", {})
        assert structured(result)["bookingUrl"] == book
        assert f"Booking link: {book}" in text_of(result)


# -- content problems -----------------------------------------------------------


@respx.mock
@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("get_profile", {}),
        ("list_case_studies", {}),
        ("get_case_study", {"id": "voice-agent"}),
        ("list_projects", {}),
        ("get_recent_posts", {}),
        ("search_portfolio", {"query": "voice"}),
        ("get_resume", {}),
        ("get_contact_options", {}),
    ],
)
async def test_unreadable_content_is_a_clear_error(
    tmp_path: Path, name: str, args: dict[str, Any]
) -> None:
    respx.get(MEDIUM_URL).respond(200, json=MEDIUM_JSON)
    async with Client(make_server(tmp_path / "missing" / "content.json")) as client:
        result = await client.call_tool(name, args)
        assert result.is_error is True
        assert text_of(result) == "The portfolio content couldn't be loaded right now."


async def test_content_version_change_is_reported(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    edit_content(path, lambda d: d.update(version=2))
    async with Client(make_server(path)) as client:
        result = await client.call_tool("get_profile", {})
        assert result.is_error is True
        assert "version" in text_of(result)
