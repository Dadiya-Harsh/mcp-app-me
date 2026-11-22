"""Small helpers every tool uses."""

from collections.abc import Awaitable
from typing import Any

from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel

from portfolio_mcp.content.loader import ContentError

# SDK 2.3 takes snake_case here. Every tool is read-only. open_world is for the ones
# that call another service (Medium, later Google Calendar).
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
READ_ONLY_OPEN_WORLD = ToolAnnotations(read_only_hint=True, open_world_hint=True)


def dump(model: BaseModel) -> Any:
    """A model as plain JSON data, with the contract's camelCase names."""
    return model.model_dump(mode="json", by_alias=True)


def ok(text: str, data: dict[str, Any]) -> CallToolResult:
    """Readable text for every client, and the same facts as structured data."""
    return CallToolResult(
        content=[TextContent(type="text", text=text)], structured_content=data
    )


def fail(text: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=text)], is_error=True)


async def guarded(work: Awaitable[CallToolResult]) -> CallToolResult:
    """Turn content problems into a plain error result instead of a stack trace."""
    try:
        return await work
    except ContentError as exc:
        return fail(str(exc))
