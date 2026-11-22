"""Latest Medium posts, read from the portfolio's own /api/medium.

The portfolio already reads Harsh's Medium feed and cleans it up, so this server asks the
portfolio instead of talking to Medium itself. Same rules as the content loader: short
timeout, a small in-memory cache, and the last good copy is served if a refresh fails.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from pydantic import BaseModel

from portfolio_mcp.content.loader import FETCH_TIMEOUT_SECONDS, STALE_RETRY_SECONDS
from portfolio_mcp.settings import Settings

log = logging.getLogger(__name__)

POSTS_TTL_SECONDS = 300


class MediumUnavailable(Exception):
    """The posts couldn't be loaded and there is no cached copy."""


class MediumPost(BaseModel):
    title: str
    date: str | None  # YYYY-MM-DD
    tags: list[str]
    link: str


def _iso_date(pub_date: object) -> str | None:
    if not isinstance(pub_date, str) or not pub_date.strip():
        return None
    try:
        parsed: datetime = parsedate_to_datetime(pub_date)
    except TypeError, ValueError:
        return None
    return parsed.date().isoformat()


def parse_posts(payload: Any) -> list[MediumPost]:
    """Turn the /api/medium JSON into posts. Anything that isn't a post is skipped.

    Posts with the same title (cross-posted articles) are kept once, first one wins.
    That is the same thing the site's Blog page does.
    """
    articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(articles, list):
        # ValueError on purpose: MediumClient treats it like any other bad response
        raise ValueError("no articles list in /api/medium response")  # noqa: TRY004
    posts: list[MediumPost] = []
    seen: set[str] = set()
    for item in articles:
        if not isinstance(item, dict):
            continue
        title, link = item.get("title"), item.get("link")
        if not isinstance(title, str) or not isinstance(link, str):
            continue
        title, link = title.strip(), link.strip()
        if not title or not link or title.lower() in seen:
            continue
        seen.add(title.lower())
        categories = item.get("categories")
        tags = (
            [c.strip() for c in categories if isinstance(c, str) and c.strip()]
            if isinstance(categories, list)
            else []
        )
        posts.append(
            MediumPost(
                title=title, date=_iso_date(item.get("pubDate")), tags=tags, link=link
            )
        )
    return posts


class MediumClient:
    def __init__(
        self, settings: Settings, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._posts: list[MediumPost] | None = None
        self._stored_at = 0.0

    async def posts(self, limit: int) -> list[MediumPost]:
        """Newest first, at most `limit`. Raises MediumUnavailable if nothing can be had."""
        now = self._clock()
        fresh = self._posts is not None and now - self._stored_at < POSTS_TTL_SECONDS
        if not fresh:
            try:
                self._posts = await self._fetch()
                self._stored_at = now
            except (httpx.HTTPError, ValueError) as exc:
                if self._posts is None:
                    log.error("loading Medium posts failed, nothing cached: %r", exc)
                    raise MediumUnavailable from exc
                log.warning("refreshing Medium posts failed, serving old copy: %r", exc)
                self._stored_at = max(
                    self._stored_at, now - POSTS_TTL_SECONDS + STALE_RETRY_SECONDS
                )
        assert self._posts is not None
        return self._posts[: max(0, limit)]

    async def _fetch(self) -> list[MediumPost]:
        url = f"{self._settings.portfolio_url}/api/medium"
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return parse_posts(response.json())
