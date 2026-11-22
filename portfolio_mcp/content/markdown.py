"""Split a case study markdown file into sections by its `##` headings.

The headings the portfolio promises are in the table in the master plan (section 6).
A `##` heading that isn't in that table is kept inside the section above it, and a
warning is logged (the portfolio's build check is there to stop this happening).
"""

import logging
import re
from typing import Literal

from pydantic import BaseModel

log = logging.getLogger(__name__)

SectionId = Literal["overview", "problem", "architecture", "hard", "result"]

SECTION_IDS: dict[str, SectionId] = {
    "Overview": "overview",
    "The Problem": "problem",
    "System Architecture": "architecture",
    "What Was Hard": "hard",
    "Where It Ended Up": "result",
}

_FENCE = re.compile(r"^\s*(```|~~~)")
_STEP = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
_RULE = re.compile(r"^\s*-{3,}\s*$")
# the target of a markdown link or image that starts with one "/" (not "//")
_SITE_RELATIVE = re.compile(r"(\]\()(/(?!/)[^)\s]*)")


class Section(BaseModel):
    id: SectionId
    heading: str
    markdown: str  # the text under the heading, without the heading line itself


class Step(BaseModel):
    number: int
    title: str
    markdown: str


class ParsedCaseStudy(BaseModel):
    title: str | None  # the `# Title` line, if there is one
    sections: list[Section]
    steps: list[Step]  # numbered `### N. Title` parts of the architecture section


def _finish(lines: list[str]) -> str:
    # The case study files separate their parts with a `---` line. It belongs to the
    # layout of the page, not to the text, so a rule at the very end is dropped.
    trimmed = list(lines)
    while True:
        while trimmed and not trimmed[-1].strip():
            trimmed.pop()
        if trimmed and _RULE.match(trimmed[-1]):
            trimmed.pop()
        else:
            break
    return "\n".join(trimmed).strip()


def absolute_links(markdown: str, site_url: str) -> str:
    """Make site-relative link and image targets full URLs, so they work outside the site.

    `[text](/case-studies/x)` and `![alt](/images/y.png)` get `site_url` in front.
    Targets that are already full URLs, `#anchors`, `mailto:` and anything inside a code
    fence are left alone.
    """
    base = site_url.rstrip("/")
    out: list[str] = []
    in_fence = False
    for line in markdown.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            line = _SITE_RELATIVE.sub(lambda m: f"{m.group(1)}{base}{m.group(2)}", line)
        out.append(line)
    return "\n".join(out)


def split_sections(markdown: str) -> list[Section]:
    return parse_case_study(markdown).sections


def parse_case_study(markdown: str) -> ParsedCaseStudy:
    title: str | None = None
    # [id, heading, lines] for each known section, in file order
    found: list[tuple[SectionId, str, list[str]]] = []
    seen: set[SectionId] = set()
    in_fence = False

    for line in markdown.replace("\r\n", "\n").split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            if line.startswith("# ") and title is None and not found:
                title = line[2:].strip()
                continue
            if line.startswith("## "):
                heading = line[3:].strip()
                section_id = SECTION_IDS.get(heading)
                if section_id is not None and section_id not in seen:
                    seen.add(section_id)
                    found.append((section_id, heading, []))
                    continue
                reason = "repeated" if section_id is not None else "not a known heading"
                log.warning(
                    "case study heading %r is %s, keeping it with the section above",
                    heading,
                    reason,
                )
        if found:
            found[-1][2].append(line)
        # text before the first known heading (apart from the title) is dropped

    sections = [
        Section(id=i, heading=h, markdown=_finish(lines)) for i, h, lines in found
    ]
    architecture = next((s for s in sections if s.id == "architecture"), None)
    return ParsedCaseStudy(
        title=title,
        sections=sections,
        steps=_steps(architecture.markdown) if architecture else [],
    )


def _steps(markdown: str) -> list[Step]:
    steps: list[Step] = []
    current: tuple[int, str, list[str]] | None = None
    in_fence = False
    for line in markdown.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        match = None if in_fence else _STEP.match(line)
        if match:
            if current:
                steps.append(
                    Step(
                        number=current[0],
                        title=current[1],
                        markdown=_finish(current[2]),
                    )
                )
            current = (int(match.group(1)), match.group(2), [])
        elif not in_fence and line.startswith("### "):
            # a `###` that isn't numbered ends the current step
            if current:
                steps.append(
                    Step(
                        number=current[0],
                        title=current[1],
                        markdown=_finish(current[2]),
                    )
                )
            current = None
        elif current:
            current[2].append(line)
    if current:
        steps.append(
            Step(number=current[0], title=current[1], markdown=_finish(current[2]))
        )
    return steps
