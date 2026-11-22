"""Keyword search."""

from pathlib import Path

import pytest

from portfolio_mcp.content.loader import ContentLoader
from portfolio_mcp.content.models import Content
from portfolio_mcp.content.search import search
from portfolio_mcp.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
async def content() -> Content:
    return await ContentLoader(
        Settings(content_fixture_path=str(FIXTURES / "content.json"))
    ).content()


@pytest.fixture
def markdown() -> dict[str, str]:
    return {
        "voice-agent": (FIXTURES / "voice-agent.md").read_text(),
        "generative-video": (FIXTURES / "generative-video.md").read_text(),
    }


def test_finds_a_case_study_by_its_tech(content: Content) -> None:
    results = search(content, "twilio")
    assert results
    assert results[0].type == "case-study"
    assert results[0].title == "Voice Agent Pipeline"
    assert results[0].url == "https://www.harshdadiya.in/case-studies/voice-agent"
    assert "Twilio" in results[0].snippet


def test_title_hits_rank_above_text_hits(content: Content) -> None:
    results = search(content, "SecureWorkspace")
    assert results[0].type == "project"
    assert results[0].title == "SecureWorkspace"


def test_prefix_match_finds_plurals(content: Content) -> None:
    assert any(
        "agent" in r.title.lower() or "agent" in r.snippet.lower()
        for r in search(content, "agent")
    )


def test_short_words_must_match_whole_words(content: Content) -> None:
    # "ai" would otherwise match words like "aiohttp" or "air": AQI project says "air quality"
    titles = [r.title for r in search(content, "ai", limit=20)]
    assert "AQI Monitoring" not in titles


def test_searches_inside_case_study_sections(
    content: Content, markdown: dict[str, str]
) -> None:
    without = search(content, "choppy audio")
    with_md = search(content, "choppy audio", markdown)
    assert not without
    assert with_md
    assert with_md[0].title == "Voice Agent Pipeline: What Was Hard"
    assert with_md[0].type == "case-study"


def test_only_known_case_study_ids_are_searched(content: Content) -> None:
    results = search(
        content,
        "secret draft text",
        {"enterprise-rag": "## Overview\nsecret draft text\n"},
    )
    assert results == []


def test_no_match_and_empty_query(content: Content) -> None:
    assert search(content, "kubernetes operator rust") == []
    assert search(content, "") == []
    assert search(content, "   ") == []
    assert search(content, "?!") == []


def test_limit(content: Content) -> None:
    assert len(search(content, "python", limit=2)) == 2
    assert search(content, "python", limit=0) == []


def test_long_query_is_cut(content: Content) -> None:
    assert search(
        content, "twilio " + "x" * 5000
    )  # doesn't blow up, still finds twilio


def test_snippets_are_short_and_single_line(content: Content) -> None:
    for r in search(content, "python", limit=10):
        assert "\n" not in r.snippet
        assert len(r.snippet) <= 190


def test_results_come_from_the_content_only(content: Content) -> None:
    for r in search(content, "wappnet", limit=10):
        assert r.type in {"experience", "profile", "case-study", "project"}


def test_snippets_have_no_image_syntax(
    content: Content, markdown: dict[str, str]
) -> None:
    results = search(content, "voice agent architecture", markdown, limit=10)
    assert results
    for r in results:
        assert "![" not in r.snippet
        assert "](/" not in r.snippet
