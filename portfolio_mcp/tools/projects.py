"""list_projects."""

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from portfolio_mcp import text
from portfolio_mcp.deps import Deps
from portfolio_mcp.tools._common import READ_ONLY, dump, guarded, ok

Group = Literal["all", "recent", "openSource", "earlier"]


async def projects_result(deps: Deps, group: Group) -> CallToolResult:
    projects = (await deps.loader.content()).projects
    shown = dump(projects)
    # All three keys are always there, so a screen can rely on them. A group that wasn't
    # asked for is an empty list.
    data = {
        key: shown[key] if group in ("all", key) else []
        for key in ("recent", "openSource", "earlier")
    }
    return ok(text.projects(projects, group), {"group": group, "projects": data})


def register(mcp: MCPServer, deps: Deps) -> None:
    @mcp.tool(
        name="list_projects",
        title="Harsh's projects",
        description=(
            "Harsh's projects with links: recent work, open source contributions and "
            "earlier projects. Use `group` to see just one kind. For his bigger "
            "production work, use list_case_studies instead."
        ),
        annotations=READ_ONLY,
    )
    async def list_projects(
        group: Annotated[
            Group,
            Field(description="all, recent, openSource or earlier."),
        ] = "all",
    ) -> CallToolResult:
        return await guarded(projects_result(deps, group))
