"""Splitting case study markdown into sections."""

import logging
from pathlib import Path

import pytest

from portfolio_mcp.content.markdown import parse_case_study, split_sections

FIXTURES = Path(__file__).parent / "fixtures"


def test_voice_agent_has_all_five_sections_in_order() -> None:
    parsed = parse_case_study((FIXTURES / "voice-agent.md").read_text())
    assert parsed.title == "Real-Time Voice Agent for Phone Calls"
    assert [s.id for s in parsed.sections] == [
        "overview",
        "problem",
        "architecture",
        "hard",
        "result",
    ]
    assert [s.heading for s in parsed.sections][-1] == "Where It Ended Up"
    # the heading line itself isn't part of the section text
    assert not parsed.sections[0].markdown.startswith("##")
    assert parsed.sections[0].markdown.startswith("I built a voice agent")


def test_voice_agent_architecture_steps() -> None:
    parsed = parse_case_study((FIXTURES / "voice-agent.md").read_text())
    assert [(s.number, s.title) for s in parsed.steps] == [
        (1, "Getting the call in"),
        (2, "Understanding the caller"),
        (3, "Talking to the CRM"),
        (4, "Sending the answer back"),
    ]
    assert all(step.markdown for step in parsed.steps)


def test_tech_stack_stays_under_where_it_ended_up() -> None:
    result = split_sections((FIXTURES / "voice-agent.md").read_text())[-1]
    assert result.id == "result"
    assert "### Tech Stack" in result.markdown


def test_unknown_heading_is_kept_with_the_section_above(
    caplog: pytest.LogCaptureFixture,
) -> None:
    md = "# T\n\n## Overview\nA\n\n## Lessons\nB\n\n## The Problem\nC\n"
    with caplog.at_level(logging.WARNING):
        sections = split_sections(md)
    assert [s.id for s in sections] == ["overview", "problem"]
    assert sections[0].markdown == "A\n\n## Lessons\nB"
    assert sections[1].markdown == "C"
    assert "Lessons" in caplog.text


def test_generative_video_fixture_has_the_two_old_headings(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # This fixture is the portfolio file from before phase P3, which renames two headings.
    # Until then both old headings stay inside "System Architecture".
    with caplog.at_level(logging.WARNING):
        parsed = parse_case_study((FIXTURES / "generative-video.md").read_text())
    assert [s.id for s in parsed.sections] == ["overview", "problem", "architecture"]
    architecture = parsed.sections[2].markdown
    assert "## Technical Hurdles & Trade-offs" in architecture
    assert "## Results & Impact" in architecture
    assert "Technical Hurdles & Trade-offs" in caplog.text
    assert [s.number for s in parsed.steps] == [1, 2, 3]


def test_headings_inside_code_fences_are_ignored() -> None:
    md = "## Overview\nText\n```\n## Not a heading\n```\n## The Problem\nP\n"
    sections = split_sections(md)
    assert [s.id for s in sections] == ["overview", "problem"]
    assert "## Not a heading" in sections[0].markdown


def test_repeated_known_heading_is_kept_with_the_section_above() -> None:
    sections = split_sections("## Overview\nA\n## Overview\nB\n")
    assert len(sections) == 1
    assert "B" in sections[0].markdown


def test_windows_line_endings() -> None:
    sections = split_sections("## Overview\r\nA\r\n\r\n## The Problem\r\nB\r\n")
    assert [s.markdown for s in sections] == ["A", "B"]


def test_section_can_be_left_out() -> None:
    assert [s.id for s in split_sections("## Overview\nA\n## What Was Hard\nB\n")] == [
        "overview",
        "hard",
    ]


def test_no_headings_gives_no_sections() -> None:
    parsed = parse_case_study("just text")
    assert parsed.sections == []
    assert parsed.steps == []
