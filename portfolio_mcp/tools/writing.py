"""get_recent_posts."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from portfolio_mcp import text
from portfolio_mcp.deps import Deps
from portfolio_mcp.integrations.medium import MediumUnavailable
from portfolio_mcp.tools._common import READ_ONLY_OPEN_WORLD, guarded, ok


async def posts_result(deps: Deps, limit: int) -> CallToolResult:
    medium_url = (await deps.loader.content()).profile.links.medium
    try:
        posts = await deps.medium.posts(limit)
    except MediumUnavailable:
        # Not an error for the caller: say so and give the Medium page.
        return ok(
            text.posts_unavailable(medium_url),
            {"posts": [], "mediumUrl": medium_url, "unavailable": True},
        )
    return ok(
        text.posts(posts, medium_url),
        {
            "posts": [p.model_dump(mode="json") for p in posts],
            "mediumUrl": medium_url,
            "unavailable": False,
        },
    )


def register(mcp: MCPServer, deps: Deps) -> None:
    @mcp.tool(
        name="get_recent_posts",
        title="Harsh's recent writing",
        description=(
            "The latest articles Harsh has published on Medium: title, date, tags and "
            "link. Loaded live. If Medium can't be reached it returns an empty list and "
            "the link to his Medium page."
        ),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def get_recent_posts(
        limit: Annotated[
            int, Field(ge=1, le=10, description="How many posts, 1 to 10.")
        ] = 5,
    ) -> CallToolResult:
        return await guarded(posts_result(deps, limit))
