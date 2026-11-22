"""Fetch and cache content.json and the case study markdown.

The portfolio is the only source. Nothing here keeps its own copy of Harsh's info.

- Cached in memory for CONTENT_TTL_SECONDS (each warm Vercel instance keeps its own).
- If a refresh fails (network, bad JSON, wrong shape) the last good copy is served, and the
  next try waits 30 seconds instead of hitting the site on every request.
- No cached copy and the fetch fails: ContentUnavailable.
- `version` other than 1 means the contract changed. That is logged and raised, and the
  old copy is NOT served, so the change gets noticed.
- CONTENT_FIXTURE_PATH set: read content.json (and `<id>.md` next to it) from disk.
- Only ids listed in content.json are ever fetched, so nothing unpublished can be served.
"""

import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

import httpx

from portfolio_mcp.content.markdown import absolute_links
from portfolio_mcp.content.models import CONTENT_VERSION, Content
from portfolio_mcp.settings import Settings, load_settings

log = logging.getLogger(__name__)

FETCH_TIMEOUT_SECONDS = 5.0
STALE_RETRY_SECONDS = 30.0
UNAVAILABLE_MESSAGE = "The portfolio content couldn't be loaded right now."


class ContentError(Exception):
    """The content can't be used. The message is safe to show to the user."""


class ContentUnavailable(ContentError):
    """Couldn't fetch or read the content, and there is no cached copy."""

    def __init__(self) -> None:
        super().__init__(UNAVAILABLE_MESSAGE)


class ContentVersionError(ContentError):
    """content.json has a version this server doesn't know."""


class UnknownCaseStudy(ContentError):
    def __init__(self, case_study_id: str, valid_ids: list[str]) -> None:
        self.case_study_id = case_study_id
        self.valid_ids = valid_ids
        super().__init__(
            f"No case study with id {case_study_id!r}. Valid ids: {', '.join(valid_ids)}."
        )


@dataclass
class _Entry:
    value: Any
    stored_at: float


def _absolute(site_url: str, value: str) -> str:
    if value.startswith(("http://", "https://", "mailto:")):
        return value
    return f"{site_url}/{value.lstrip('/')}"


def make_urls_absolute(content: Content) -> Content:
    """Turn site-relative paths (/images/profile.jpg, /resume, ...) into full URLs."""
    site = content.site_url.rstrip("/")
    profile = content.profile
    profile.photo = _absolute(site, profile.photo)
    links = profile.links
    links.resume = _absolute(site, links.resume)
    links.resume_pdf = _absolute(site, links.resume_pdf)
    links.resume_docx = _absolute(site, links.resume_docx)
    links.contact = _absolute(site, links.contact)
    for item in profile.focus:
        if item.href:
            item.href = _absolute(site, item.href)
    for study in content.case_studies:
        study.url = _absolute(site, study.url)
        study.markdown_url = _absolute(site, study.markdown_url)
    return content


class ContentLoader:
    def __init__(
        self,
        settings: Settings,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._cache: dict[str, _Entry] = {}

    async def content(self) -> Content:
        return await self._cached("content.json", self._load_content)

    async def case_study_md(self, case_study_id: str) -> str:
        """Markdown of one published case study, with site links made absolute."""
        content = await self.content()
        study = next((s for s in content.case_studies if s.id == case_study_id), None)
        if study is None:
            raise UnknownCaseStudy(case_study_id, [s.id for s in content.case_studies])
        # Use the path from content.json with our own PORTFOLIO_URL, so a preview of
        # the portfolio can be tested without content.json pointing at production.
        path = urlsplit(study.markdown_url).path

        async def load() -> str:
            raw = await self._read_text(path, fixture_name=f"{case_study_id}.md")
            # images and links in the .md point at the site (/images/...); make them
            # full URLs so they still work in a chat window
            return absolute_links(raw, content.site_url)

        return await self._cached(f"md:{case_study_id}", load)

    async def llms_full(self) -> str:
        """The portfolio's /llms-full.txt, as plain text."""
        return await self._cached(
            "llms-full.txt",
            lambda: self._read_text("/llms-full.txt", fixture_name="llms-full.txt"),
        )

    # -- cache -----------------------------------------------------------

    async def _cached[T](self, key: str, load: Callable[[], Awaitable[T]]) -> T:
        ttl = self._settings.content_ttl_seconds
        now = self._clock()
        entry = self._cache.get(key)
        if entry is not None and now - entry.stored_at < ttl:
            return cast(T, entry.value)
        try:
            value = await load()
        except ContentVersionError:
            raise
        except (httpx.HTTPError, ValueError, OSError) as exc:
            # ValueError covers bad JSON and pydantic's ValidationError
            if entry is None:
                log.error("loading %s failed and nothing is cached: %r", key, exc)
                raise ContentUnavailable from exc
            log.warning("refreshing %s failed, serving the last copy: %r", key, exc)
            entry.stored_at = max(entry.stored_at, now - ttl + STALE_RETRY_SECONDS)
            return cast(T, entry.value)
        self._cache[key] = _Entry(value, now)
        return value

    # -- reading ---------------------------------------------------------

    async def _load_content(self) -> Content:
        raw = json.loads(
            await self._read_text("/content.json", fixture_name="content.json")
        )
        version = raw.get("version") if isinstance(raw, dict) else None
        if version != CONTENT_VERSION:
            log.error(
                "content.json version %r is not supported (expected %d)",
                version,
                CONTENT_VERSION,
            )
            raise ContentVersionError(
                f"content.json has version {version!r}, this server understands version {CONTENT_VERSION}."
            )
        return make_urls_absolute(Content.model_validate(raw))

    async def _read_text(self, path: str, fixture_name: str) -> str:
        fixture = self._settings.content_fixture_path
        if fixture:
            return (Path(fixture).parent / fixture_name).read_text(encoding="utf-8")
        url = f"{self._settings.portfolio_url}{path}"
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text


_default_loader: ContentLoader | None = None


def get_loader() -> ContentLoader:
    """The shared loader (one cache per warm instance), built from the environment."""
    global _default_loader
    if _default_loader is None:
        _default_loader = ContentLoader(load_settings())
    return _default_loader
