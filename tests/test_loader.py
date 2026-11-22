"""Loader: fixture mode, HTTP mode, cache, stale copy, version check, absolute URLs."""

import copy
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from portfolio_mcp.content.loader import (
    ContentLoader,
    ContentUnavailable,
    ContentVersionError,
    UnknownCaseStudy,
)
from portfolio_mcp.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_JSON = FIXTURES / "content.json"
SITE = "https://www.harshdadiya.in"
TTL = 300


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def raw_content() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE_JSON.read_text())
    return data


def http_loader(clock: Clock | None = None) -> ContentLoader:
    return ContentLoader(
        Settings(portfolio_url=SITE, content_ttl_seconds=TTL), clock or Clock()
    )


def fixture_loader(path: Path = FIXTURE_JSON) -> ContentLoader:
    return ContentLoader(Settings(content_fixture_path=str(path)))


# -- fixture mode ------------------------------------------------------------


async def test_parses_the_fixture() -> None:
    content = await fixture_loader().content()
    assert content.version == 1
    assert content.profile.name == "Harsh Dadiya"
    assert content.profile.career_start == "2025-01"
    assert [c.id for c in content.case_studies] == ["voice-agent", "generative-video"]
    assert content.case_studies[0].tech_stack[:2] == ["Python", "FastAPI"]
    assert content.projects.open_source[0].repo_stars == "81K"
    assert content.profile.experience[0].tags  # the extra field the portfolio sends


async def test_no_placeholder_is_left_in_the_fixture() -> None:
    content = await fixture_loader().content()
    assert "{" not in content.profile.stats[0].label
    assert "{" not in content.projects.open_source[0].description


async def test_site_relative_paths_become_absolute() -> None:
    content = await fixture_loader().content()
    links = content.profile.links
    assert content.profile.photo == f"{SITE}/images/profile.jpg"
    assert links.resume == f"{SITE}/resume"
    assert links.resume_pdf == f"{SITE}/resume/Harsh_Dadiya_Resume.pdf"
    assert links.contact == f"{SITE}/contact"
    assert (
        links.github == "https://github.com/Dadiya-Harsh"
    )  # already absolute, untouched
    assert content.case_studies[0].url == f"{SITE}/case-studies/voice-agent"
    assert content.case_studies[0].markdown_url == f"{SITE}/case-studies/voice-agent.md"
    linked = [f.href for f in content.profile.focus if f.href]
    assert linked
    assert all(href.startswith(f"{SITE}/") for href in linked)
    assert any(f.href is None for f in content.profile.focus)


async def test_dump_by_alias_gives_the_contract_names() -> None:
    dumped = (await fixture_loader().content()).model_dump(mode="json", by_alias=True)
    assert {
        "version",
        "generatedAt",
        "siteUrl",
        "profile",
        "projects",
        "caseStudies",
    } <= dumped.keys()
    assert "openToRolesLabel" in dumped["profile"]
    assert "resumePdf" in dumped["profile"]["links"]
    assert "markdownUrl" in dumped["caseStudies"][0]


async def test_fixture_mode_reads_case_study_markdown_from_disk() -> None:
    md = await fixture_loader().case_study_md("voice-agent")
    assert md.startswith("# Real-Time Voice Agent")


async def test_case_study_markdown_has_absolute_image_links() -> None:
    md = await fixture_loader().case_study_md("voice-agent")
    assert f"]({SITE}/images/voice_agent_architect.png)" in md
    assert "](/images/" not in md


async def test_version_2_is_rejected(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    data = raw_content()
    data["version"] = 2
    (tmp_path / "content.json").write_text(json.dumps(data))
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ContentVersionError, match="version 2"),
    ):
        await fixture_loader(tmp_path / "content.json").content()
    assert "not supported" in caplog.text


async def test_version_check_wins_over_the_shape(tmp_path: Path) -> None:
    (tmp_path / "content.json").write_text(
        json.dumps({"version": 2, "something": "new"})
    )
    with pytest.raises(ContentVersionError):
        await fixture_loader(tmp_path / "content.json").content()


async def test_missing_fixture_file_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(ContentUnavailable):
        await fixture_loader(tmp_path / "content.json").content()


async def test_unknown_case_study_lists_the_valid_ids() -> None:
    with pytest.raises(UnknownCaseStudy) as info:
        await fixture_loader().case_study_md("enterprise-rag")
    assert info.value.valid_ids == ["voice-agent", "generative-video"]
    assert "voice-agent" in str(info.value)


# -- HTTP mode ---------------------------------------------------------------


@respx.mock
async def test_fetches_content_json_and_caches_it() -> None:
    route = respx.get(f"{SITE}/content.json").mock(
        return_value=httpx.Response(200, json=raw_content())
    )
    loader = http_loader()
    first = await loader.content()
    second = await loader.content()
    assert first is second
    assert route.call_count == 1


@respx.mock
async def test_refetches_after_the_ttl() -> None:
    route = respx.get(f"{SITE}/content.json").mock(
        return_value=httpx.Response(200, json=raw_content())
    )
    clock = Clock()
    loader = http_loader(clock)
    await loader.content()
    clock.now += TTL - 1
    await loader.content()
    assert route.call_count == 1
    clock.now += 2
    await loader.content()
    assert route.call_count == 2


@respx.mock
async def test_serves_the_last_copy_when_a_refresh_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    route = respx.get(f"{SITE}/content.json").mock(
        side_effect=[httpx.Response(200, json=raw_content()), httpx.Response(500)]
    )
    clock = Clock()
    loader = http_loader(clock)
    good = await loader.content()
    clock.now += TTL + 1
    with caplog.at_level(logging.WARNING):
        stale = await loader.content()
    assert stale is good
    assert "serving the last copy" in caplog.text
    assert route.call_count == 2
    # it doesn't hit the site again on every request while it is down
    await loader.content()
    assert route.call_count == 2


@respx.mock
async def test_serves_the_last_copy_when_the_network_fails() -> None:
    respx.get(f"{SITE}/content.json").mock(
        side_effect=[
            httpx.Response(200, json=raw_content()),
            httpx.ConnectTimeout("slow"),
        ]
    )
    clock = Clock()
    loader = http_loader(clock)
    good = await loader.content()
    clock.now += TTL + 1
    assert await loader.content() is good


@respx.mock
async def test_serves_the_last_copy_when_the_new_file_is_broken() -> None:
    broken = copy.deepcopy(raw_content())
    del broken["profile"]["name"]
    respx.get(f"{SITE}/content.json").mock(
        side_effect=[
            httpx.Response(200, json=raw_content()),
            httpx.Response(200, json=broken),
            httpx.Response(200, text="not json"),
        ]
    )
    clock = Clock()
    loader = http_loader(clock)
    good = await loader.content()
    clock.now += TTL + 1
    assert await loader.content() is good  # wrong shape
    clock.now += TTL + 1
    assert await loader.content() is good  # not JSON


@respx.mock
async def test_fails_cleanly_with_no_cached_copy() -> None:
    respx.get(f"{SITE}/content.json").mock(return_value=httpx.Response(503))
    with pytest.raises(ContentUnavailable, match="couldn't be loaded right now"):
        await http_loader().content()


@respx.mock
async def test_a_new_version_is_not_hidden_by_the_old_copy() -> None:
    v2 = raw_content()
    v2["version"] = 2
    respx.get(f"{SITE}/content.json").mock(
        side_effect=[
            httpx.Response(200, json=raw_content()),
            httpx.Response(200, json=v2),
        ]
    )
    clock = Clock()
    loader = http_loader(clock)
    await loader.content()
    clock.now += TTL + 1
    with pytest.raises(ContentVersionError):
        await loader.content()


@respx.mock
async def test_case_study_markdown_is_fetched_and_cached() -> None:
    respx.get(f"{SITE}/content.json").mock(
        return_value=httpx.Response(200, json=raw_content())
    )
    md_route = respx.get(f"{SITE}/case-studies/voice-agent.md").mock(
        return_value=httpx.Response(200, text="# Voice\n\n## Overview\nHi\n")
    )
    loader = http_loader()
    assert (await loader.case_study_md("voice-agent")).startswith("# Voice")
    await loader.case_study_md("voice-agent")
    assert md_route.call_count == 1


@respx.mock
async def test_only_ids_in_content_json_are_ever_fetched() -> None:
    # respx refuses any request that has no route, so a fetch for a draft would raise
    respx.get(f"{SITE}/content.json").mock(
        return_value=httpx.Response(200, json=raw_content())
    )
    with pytest.raises(UnknownCaseStudy):
        await http_loader().case_study_md("enterprise-rag")
    with pytest.raises(UnknownCaseStudy):
        await http_loader().case_study_md("../drafts/case-studies/enterprise-rag")
    assert [str(call.request.url) for call in respx.calls] == [
        f"{SITE}/content.json"
    ] * 2


@respx.mock
async def test_markdown_comes_from_portfolio_url_not_site_url() -> None:
    # PORTFOLIO_URL can point at a preview of the portfolio
    preview = "https://portfolio-preview.example.test"
    respx.get(f"{preview}/content.json").mock(
        return_value=httpx.Response(200, json=raw_content())
    )
    md_route = respx.get(f"{preview}/case-studies/generative-video.md").mock(
        return_value=httpx.Response(200, text="# G\n")
    )
    loader = ContentLoader(
        Settings(portfolio_url=preview, content_ttl_seconds=TTL), Clock()
    )
    assert await loader.case_study_md("generative-video") == "# G\n"
    assert md_route.called


@respx.mock
async def test_stale_markdown_is_served_when_a_refresh_fails() -> None:
    respx.get(f"{SITE}/content.json").mock(
        return_value=httpx.Response(200, json=raw_content())
    )
    respx.get(f"{SITE}/case-studies/voice-agent.md").mock(
        side_effect=[httpx.Response(200, text="# V\n"), httpx.Response(502)]
    )
    clock = Clock()
    loader = http_loader(clock)
    assert await loader.case_study_md("voice-agent") == "# V\n"
    clock.now += TTL + 1
    assert await loader.case_study_md("voice-agent") == "# V\n"
