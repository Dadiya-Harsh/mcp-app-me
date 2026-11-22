"""The Medium client: parsing /api/medium, cache, stale copy, failure."""

import httpx
import pytest
import respx

from portfolio_mcp.integrations.medium import (
    POSTS_TTL_SECONDS,
    MediumClient,
    MediumUnavailable,
    parse_posts,
)
from portfolio_mcp.settings import Settings

URL = "https://www.harshdadiya.in/api/medium"

ARTICLES = {
    "articles": [
        {
            "title": "First post",
            "link": "https://medium.com/@harshdadiya/first",
            "pubDate": "Mon, 10 Nov 2025 08:12:33 GMT",
            "description": "ignored",
            "categories": ["ai", "mcp"],
        },
        {
            "title": "Cross posted",
            "link": "https://medium.com/@harshdadiya/cross",
            "pubDate": "Tue, 04 Nov 2025 10:00:00 GMT",
            "categories": [],
        },
        {
            "title": "cross posted",  # same title, other place: dropped
            "link": "https://medium.com/other/cross",
            "pubDate": "Tue, 04 Nov 2025 10:00:00 GMT",
            "categories": [],
        },
        {"title": "No link"},
        "not a dict",
        {
            "title": "Odd date",
            "link": "https://medium.com/@harshdadiya/odd",
            "pubDate": "last tuesday",
            "categories": ["x", 5, ""],
        },
    ]
}


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def client_with(clock: Clock | None = None) -> MediumClient:
    return MediumClient(
        Settings(portfolio_url="https://www.harshdadiya.in"), clock or Clock()
    )


def test_parse_posts() -> None:
    posts = parse_posts(ARTICLES)
    assert [p.title for p in posts] == ["First post", "Cross posted", "Odd date"]
    assert posts[0].date == "2025-11-10"
    assert posts[0].tags == ["ai", "mcp"]
    assert posts[2].date is None  # a date that can't be read is left out, not guessed
    assert posts[2].tags == ["x"]


@pytest.mark.parametrize("payload", [{}, [], {"articles": "nope"}, None])
def test_parse_posts_rejects_other_shapes(payload: object) -> None:
    with pytest.raises(ValueError):
        parse_posts(payload)


@respx.mock
async def test_limit_and_cache() -> None:
    route = respx.get(URL).respond(200, json=ARTICLES)
    medium = client_with()
    assert len(await medium.posts(2)) == 2
    assert len(await medium.posts(10)) == 3
    assert route.call_count == 1  # second call came from the cache


@respx.mock
async def test_refreshes_after_ttl() -> None:
    route = respx.get(URL).respond(200, json=ARTICLES)
    clock = Clock()
    medium = client_with(clock)
    await medium.posts(5)
    clock.now += POSTS_TTL_SECONDS + 1
    await medium.posts(5)
    assert route.call_count == 2


@respx.mock
async def test_serves_old_copy_when_refresh_fails() -> None:
    route = respx.get(URL)
    route.respond(200, json=ARTICLES)
    clock = Clock()
    medium = client_with(clock)
    await medium.posts(5)

    clock.now += POSTS_TTL_SECONDS + 1
    route.respond(500)
    assert len(await medium.posts(5)) == 3
    assert route.call_count == 2
    # and it doesn't hit the site again straight away
    assert len(await medium.posts(5)) == 3
    assert route.call_count == 2


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json={"error": "Failed to fetch Medium feed"}),
    ],
)
async def test_unavailable_without_a_cached_copy(response: httpx.Response) -> None:
    respx.get(URL).mock(return_value=response)
    with pytest.raises(MediumUnavailable):
        await client_with().posts(5)


@respx.mock
async def test_network_error_is_unavailable() -> None:
    respx.get(URL).mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(MediumUnavailable):
        await client_with().posts(5)
