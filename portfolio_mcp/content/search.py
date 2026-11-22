"""Simple keyword search over the portfolio content. No LLM, no index files.

Every word of the query is matched against the start of words in each piece of
content (so "agent" finds "agents"). A hit in the title counts more than a hit in
the text. Results with no hit are dropped.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from portfolio_mcp.content.markdown import parse_case_study
from portfolio_mcp.content.models import Content

MAX_QUERY_CHARS = 200
SNIPPET_CHARS = 180
TITLE_WEIGHT = 3
PHRASE_BONUS = 5

ResultType = Literal[
    "profile", "experience", "education", "certification", "project", "case-study"
]

_WORD = re.compile(r"[a-z0-9][a-z0-9+#.]*")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


class SearchResult(BaseModel):
    type: ResultType
    title: str
    snippet: str
    url: str | None = None


@dataclass
class _Doc:
    type: ResultType
    title: str
    text: str
    url: str | None


def _tokens(query: str) -> list[str]:
    seen: list[str] = []
    for word in _WORD.findall(query.lower()[:MAX_QUERY_CHARS]):
        word = word.strip(".")
        if word and word not in seen:
            seen.append(word)
    return seen


def _pattern(token: str) -> re.Pattern[str]:
    start = r"(?<![a-z0-9])" + re.escape(token)
    # very short words (ai, c) must be a whole word, or "ai" would match "aiohttp"
    return re.compile(start + (r"(?![a-z0-9])" if len(token) <= 2 else ""))


def _documents(content: Content, case_study_markdown: Mapping[str, str]) -> list[_Doc]:
    p = content.profile
    docs: list[_Doc] = [
        _Doc(
            "profile",
            f"{p.name}, {p.title}",
            " ".join(
                [p.headline, p.summary, p.tagline, p.location]
                + [f"{f.title}: {f.description}" for f in p.focus]
                + [f"{s.value} {s.label}" for s in p.stats]
            ),
            None,
        ),
    ]
    docs += [
        _Doc(
            "experience",
            f"{e.role}, {e.org} ({e.period})",
            " ".join(e.points + e.tags),
            e.org_url,
        )
        for e in p.experience
    ]
    docs += [
        _Doc("education", f"{e.title}, {e.org}", f"{e.period}", None)
        for e in p.education
    ]
    docs += [
        _Doc("certification", c.title, f"{c.issuer} {c.date}", c.url)
        for c in p.certifications
    ]

    groups = (
        content.projects.recent,
        content.projects.open_source,
        content.projects.earlier,
    )
    for group in groups:
        for project in group:
            extra = " ".join(getattr(project, "technologies", []))
            url = project.links[0].url if project.links else None
            docs.append(
                _Doc(
                    "project",
                    project.title,
                    f"{project.description} {extra}".strip(),
                    url,
                )
            )

    for study in content.case_studies:
        docs.append(
            _Doc(
                "case-study",
                study.title,
                " ".join(
                    [
                        study.subtitle,
                        study.type,
                        study.desc,
                        study.role,
                        *study.tech_stack,
                        *study.bullets,
                    ]
                ),
                study.url,
            )
        )
        markdown = case_study_markdown.get(study.id)
        if markdown:
            for section in parse_case_study(markdown).sections:
                docs.append(
                    _Doc(
                        "case-study",
                        f"{study.title}: {section.heading}",
                        section.markdown,
                        study.url,
                    )
                )
    return docs


def _snippet(text: str, patterns: list[re.Pattern[str]]) -> str:
    flat = " ".join(_IMAGE.sub("", text).split())  # a picture is no use in a snippet
    first = min(
        (m.start() for pat in patterns if (m := pat.search(flat.lower()))), default=0
    )
    start = max(0, first - 60)
    end = min(len(flat), start + SNIPPET_CHARS)
    if end - start < SNIPPET_CHARS:
        start = max(0, end - SNIPPET_CHARS)
    piece = flat[start:end].strip()
    return ("..." if start > 0 else "") + piece + ("..." if end < len(flat) else "")


def search(
    content: Content,
    query: str,
    case_study_markdown: Mapping[str, str] | None = None,
    limit: int = 5,
) -> list[SearchResult]:
    """Best matches first. `case_study_markdown` maps case study id to its markdown;
    pass it to search inside the case study sections too. Only ids in `content` are used."""
    tokens = _tokens(query)
    if not tokens:
        return []
    patterns = [_pattern(t) for t in tokens]
    phrase = " ".join(query.lower().split())[:MAX_QUERY_CHARS]

    scored: list[tuple[int, int, _Doc]] = []
    for order, doc in enumerate(_documents(content, case_study_markdown or {})):
        title, text = doc.title.lower(), doc.text.lower()
        score = 0
        for pat in patterns:
            score += TITLE_WEIGHT * len(pat.findall(title)) + len(pat.findall(text))
        if score == 0:
            continue
        if len(tokens) > 1 and phrase in f"{title} {text}":
            score += PHRASE_BONUS
        scored.append((score, order, doc))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        SearchResult(
            type=d.type,
            title=d.title,
            snippet=_snippet(d.text or d.title, patterns),
            url=d.url,
        )
        for _, _, d in scored[: max(0, limit)]
    ]
