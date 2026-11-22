"""Shared test helpers: fixture copies, a ready-made server, and snapshot checks."""

import json
import os
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.shared.exceptions import MCPError
from mcp.types import (
    CallToolResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    ReadResourceResult,
    TextContent,
)

from portfolio_mcp.content.loader import ContentLoader
from portfolio_mcp.integrations.medium import MediumClient
from portfolio_mcp.server import build_server
from portfolio_mcp.settings import Settings

TESTS = Path(__file__).parent
FIXTURES = TESTS / "fixtures"
SNAPSHOTS = TESTS / "snapshots"
SITE = "https://www.harshdadiya.in"
TODAY = date(2026, 11, 22)  # experience is 1.8 years on this date

MEDIUM_URL = f"{SITE}/api/medium"
MEDIUM_JSON = {
    "articles": [
        {
            "title": "Post one",
            "link": "https://medium.com/@harshdadiya/one",
            "pubDate": "Mon, 10 Nov 2025 08:12:33 GMT",
            "categories": ["mcp"],
        },
        {
            "title": "Post two",
            "link": "https://medium.com/@harshdadiya/two",
            "pubDate": "Tue, 04 Nov 2025 10:00:00 GMT",
            "categories": [],
        },
        {
            "title": "Post three",
            "link": "https://medium.com/@harshdadiya/three",
            "pubDate": "Tue, 28 Oct 2025 10:00:00 GMT",
            "categories": [],
        },
    ]
}


def copy_fixtures(target: Path) -> Path:
    """Copy tests/fixtures into `target` so a test can change them. Returns content.json."""
    shutil.copytree(FIXTURES, target, dirs_exist_ok=True)
    return target / "content.json"


def edit_content(path: Path, change: Any) -> None:
    """Load content.json, let `change(data)` edit it, write it back."""
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_server(
    fixture: Path | None = None,
    today: date = TODAY,
) -> Any:
    settings = Settings(
        portfolio_url=SITE,
        content_fixture_path=str(fixture or FIXTURES / "content.json"),
    )
    return build_server(
        settings,
        loader=ContentLoader(settings),
        medium=MediumClient(settings),
        today=lambda: today,
    )


def text_of(result: CallToolResult) -> str:
    first = result.content[0]
    assert isinstance(first, TextContent)
    return first.text


def assert_snapshot(name: str, actual: str) -> None:
    """Compare with tests/snapshots/<name>.txt. Run with UPDATE_SNAPSHOTS=1 to rewrite."""
    path = SNAPSHOTS / f"{name}.txt"
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOTS.mkdir(exist_ok=True)
        path.write_text(actual + "\n", encoding="utf-8", newline="\n")
        return
    assert path.exists(), f"no snapshot {path.name}; run with UPDATE_SNAPSHOTS=1"
    assert actual + "\n" == path.read_text(encoding="utf-8"), (
        f"{path.name} changed. If that is on purpose, run with UPDATE_SNAPSHOTS=1 "
        "and look at the diff."
    )


class Caller:
    """A client that opens a fresh in-process connection for every call.

    The server is stateless, so this is how it behaves in production too. It also keeps
    the anyio task group of a long-lived Client out of pytest's fixture handling.
    """

    def __init__(self, server: Any) -> None:
        self._server = server

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> CallToolResult:
        async with Client(self._server) as client:
            return await client.call_tool(name, arguments)

    async def list_tools(self) -> ListToolsResult:
        async with Client(self._server) as client:
            return await client.list_tools()

    async def list_resources(self) -> ListResourcesResult:
        async with Client(self._server) as client:
            return await client.list_resources()

    async def list_resource_templates(self) -> ListResourceTemplatesResult:
        async with Client(self._server) as client:
            return await client.list_resource_templates()

    async def read_resource(self, uri: str) -> ReadResourceResult:
        failure: MCPError | None = None
        async with Client(self._server) as client:
            try:
                return await client.read_resource(uri)
            except MCPError as exc:
                # Let it out only after the connection is closed, or the client's task
                # group wraps it in an ExceptionGroup.
                failure = exc
        raise failure

    async def instructions(self) -> str:
        async with Client(self._server) as client:
            return client.instructions or ""
