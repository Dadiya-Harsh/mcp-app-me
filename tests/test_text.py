"""Snapshots of the plain text every tool returns.

These are what clients without MCP Apps show, and what the model reads, so a change in
wording should be a decision, not an accident. If you change a renderer on purpose, run

    UPDATE_SNAPSHOTS=1 uv run pytest tests/test_text.py

and read the diff in tests/snapshots before committing it.
"""

from pathlib import Path
from typing import Any

import pytest
import respx

from tests.helpers import (
    MEDIUM_JSON,
    MEDIUM_URL,
    Caller,
    assert_snapshot,
    copy_fixtures,
    edit_content,
    make_server,
    text_of,
)


async def snapshot_of(
    client: Caller, name: str, tool: str, args: dict[str, Any] | None = None
) -> None:
    result = await client.call_tool(tool, args or {})
    assert result.is_error is False
    assert_snapshot(name, text_of(result))


async def test_profile(client: Caller) -> None:
    await snapshot_of(client, "profile", "get_profile")


async def test_profile_without_the_optional_parts(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)

    def change(data: dict[str, Any]) -> None:
        data["profile"]["openToRoles"] = False
        data["profile"]["nowBuilding"]["show"] = False
        data["caseStudies"] = []

    edit_content(path, change)
    await snapshot_of(Caller(make_server(path)), "profile_minimal", "get_profile")


async def test_case_study_list(client: Caller) -> None:
    await snapshot_of(client, "case_study_list", "list_case_studies")


async def test_case_study_list_when_empty(tmp_path: Path) -> None:
    path = copy_fixtures(tmp_path)
    edit_content(path, lambda d: d.update(caseStudies=[]))
    await snapshot_of(
        Caller(make_server(path)), "case_study_list_empty", "list_case_studies"
    )


async def test_case_study_all_sections(client: Caller) -> None:
    await snapshot_of(
        client, "case_study_voice_agent_all", "get_case_study", {"id": "voice-agent"}
    )


@pytest.mark.parametrize("section", ["overview", "architecture", "hard"])
async def test_case_study_one_section(client: Caller, section: str) -> None:
    await snapshot_of(
        client,
        f"case_study_voice_agent_{section}",
        "get_case_study",
        {"id": "voice-agent", "section": section},
    )


async def test_projects(client: Caller) -> None:
    await snapshot_of(client, "projects_all", "list_projects")
    await snapshot_of(
        client, "projects_open_source", "list_projects", {"group": "openSource"}
    )


@respx.mock
async def test_posts(client: Caller) -> None:
    respx.get(MEDIUM_URL).respond(200, json=MEDIUM_JSON)
    await snapshot_of(client, "posts", "get_recent_posts", {"limit": 3})


@respx.mock
async def test_posts_when_medium_is_down(client: Caller) -> None:
    respx.get(MEDIUM_URL).respond(500)
    await snapshot_of(client, "posts_unavailable", "get_recent_posts")


async def test_search(client: Caller) -> None:
    await snapshot_of(client, "search_voice", "search_portfolio", {"query": "voice"})
    await snapshot_of(
        client, "search_no_match", "search_portfolio", {"query": "kubernetes operator"}
    )


async def test_resume(client: Caller) -> None:
    await snapshot_of(client, "resume", "get_resume")


async def test_contact(client: Caller, tmp_path: Path) -> None:
    await snapshot_of(client, "contact", "get_contact_options")

    path = copy_fixtures(tmp_path)
    edit_content(
        path,
        lambda d: d["profile"]["links"].update(
            booking="https://cal.example.test/harsh"
        ),
    )
    await snapshot_of(
        Caller(make_server(path)), "contact_with_booking", "get_contact_options"
    )
