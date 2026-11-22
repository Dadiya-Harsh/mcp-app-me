"""Unpublished content must never get out, by any route.

A case study that is not in content.json is unpublished. Its markdown may still sit on
disk (or on the site's server) somewhere, for instance a draft. These tests put such
files next to the fixtures and check that no tool, resource or search can reach them.
"""

import json
from pathlib import Path

import pytest
import respx
from mcp.shared.exceptions import MCPError
from mcp.types import TextResourceContents

from portfolio_mcp.server import build_server
from portfolio_mcp.settings import Settings
from tests.helpers import FIXTURES, SITE, Caller, copy_fixtures, make_server, text_of

MARKER = "DRAFT-MARKER-7f3a91"

# Ids someone might try. Only voice-agent and generative-video are published.
UNPUBLISHED_IDS = [
    "draft-study",
    "draft-study.md",
    "../drafts/secret",
    "drafts/secret",
    "..%2Fdrafts%2Fsecret",
    "/etc/passwd",
]


def fixture_with_drafts(tmp_path: Path) -> Path:
    path = copy_fixtures(tmp_path)
    (tmp_path / "draft-study.md").write_text(
        f"# Draft\n\n## Overview\n{MARKER}\n", encoding="utf-8"
    )
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "secret.md").write_text(
        f"# Secret\n\n## Overview\n{MARKER}\n", encoding="utf-8"
    )
    return path


@pytest.fixture
def drafts_client(tmp_path: Path) -> Caller:
    return Caller(make_server(fixture_with_drafts(tmp_path)))


# -- not listed, not searched --------------------------------------------------


async def test_draft_is_not_listed(drafts_client: Caller) -> None:
    result = await drafts_client.call_tool("list_case_studies")
    ids = [s["id"] for s in (result.structured_content or {})["caseStudies"]]
    assert ids == ["voice-agent", "generative-video"]
    assert "draft" not in text_of(result).lower()

    index = (await drafts_client.read_resource("portfolio://case-studies")).contents[0]
    assert isinstance(index, TextResourceContents)
    assert "draft" not in index.text.lower()


async def test_draft_is_not_in_the_resource_list(drafts_client: Caller) -> None:
    uris = [str(r.uri) for r in (await drafts_client.list_resources()).resources]
    assert not [u for u in uris if "draft" in u or "secret" in u]


@pytest.mark.parametrize("query", [MARKER, "DRAFT-MARKER", "secret"])
async def test_draft_is_not_searchable(drafts_client: Caller, query: str) -> None:
    result = await drafts_client.call_tool("search_portfolio", {"query": query})
    assert result.is_error is False
    # the tool repeats the query back, so look at the results only
    assert (result.structured_content or {})["results"] == []


async def test_draft_text_is_in_no_published_answer(drafts_client: Caller) -> None:
    calls = [
        ("get_profile", {}),
        ("list_case_studies", {}),
        ("get_case_study", {"id": "voice-agent"}),
        ("get_case_study", {"id": "generative-video"}),
        ("list_projects", {}),
        ("get_resume", {}),
        ("get_contact_options", {}),
    ]
    for name, args in calls:
        result = await drafts_client.call_tool(name, args)
        assert MARKER not in text_of(result), name
        assert MARKER not in json.dumps(result.structured_content), name


# -- not fetchable by id ---------------------------------------------------------


@pytest.mark.parametrize("bad_id", UNPUBLISHED_IDS)
async def test_tool_refuses_unpublished_ids(drafts_client: Caller, bad_id: str) -> None:
    result = await drafts_client.call_tool("get_case_study", {"id": bad_id})
    assert result.is_error is True
    message = text_of(result)
    assert MARKER not in message
    # tells the caller what does exist
    assert "voice-agent" in message and "generative-video" in message


@pytest.mark.parametrize("bad_id", UNPUBLISHED_IDS)
async def test_resource_refuses_unpublished_ids(
    drafts_client: Caller, bad_id: str
) -> None:
    with pytest.raises(MCPError) as caught:
        await drafts_client.read_resource(f"portfolio://case-studies/{bad_id}")
    assert MARKER not in str(caught.value)


@pytest.mark.parametrize(
    "bad_id", ["voice-agent/../draft-study", "VOICE-AGENT", " voice-agent"]
)
async def test_ids_must_match_exactly(drafts_client: Caller, bad_id: str) -> None:
    result = await drafts_client.call_tool("get_case_study", {"id": bad_id})
    assert result.is_error is True


async def test_over_long_id_is_refused(drafts_client: Caller) -> None:
    result = await drafts_client.call_tool("get_case_study", {"id": "a" * 101})
    assert result.is_error is True


# -- over HTTP: no request for anything that isn't published ---------------------


@respx.mock
async def test_http_mode_never_asks_the_site_for_unlisted_files() -> None:
    content = (FIXTURES / "content.json").read_text(encoding="utf-8")
    respx.get(f"{SITE}/content.json").respond(200, text=content)
    for study in ("voice-agent", "generative-video"):
        respx.get(f"{SITE}/case-studies/{study}.md").respond(
            200, text=(FIXTURES / f"{study}.md").read_text(encoding="utf-8")
        )
    # If any of these is ever requested, the marker would leak. They must stay unused.
    traps = [
        respx.get(f"{SITE}/case-studies/draft-study.md").respond(200, text=MARKER),
        respx.get(f"{SITE}/drafts/secret.md").respond(200, text=MARKER),
        respx.get(f"{SITE}/case-studies/registry.json").respond(200, text=MARKER),
    ]
    client = Caller(build_server(Settings(portfolio_url=SITE)))

    for bad_id in UNPUBLISHED_IDS:
        result = await client.call_tool("get_case_study", {"id": bad_id})
        assert result.is_error is True
        with pytest.raises(MCPError):
            await client.read_resource(f"portfolio://case-studies/{bad_id}")
    search = await client.call_tool("search_portfolio", {"query": MARKER})
    assert (search.structured_content or {})["results"] == []

    assert not any(trap.called for trap in traps)
    # and the published ones do work
    ok = await client.call_tool("get_case_study", {"id": "voice-agent"})
    assert ok.is_error is False
