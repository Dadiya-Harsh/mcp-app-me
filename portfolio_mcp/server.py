"""Builds the MCP server: tools, resources and the instructions every client gets.

Prompts come in M3 and the UI (MCP Apps) in M4.
"""

from collections.abc import Callable
from datetime import date

from mcp.server.mcpserver import MCPServer

from portfolio_mcp import resources
from portfolio_mcp.content.loader import ContentLoader
from portfolio_mcp.deps import Deps, utc_today
from portfolio_mcp.integrations.medium import MediumClient
from portfolio_mcp.settings import Settings, load_settings
from portfolio_mcp.tools import (
    case_studies,
    contact,
    profile,
    projects,
    search,
    writing,
)
from portfolio_mcp.tools._common import READ_ONLY

INSTRUCTIONS = """\
This server is Harsh Dadiya's portfolio. Use it to answer questions about him: who he is, what he has built and how to reach him.

Answer only from what these tools and resources return, and link to the pages they give. If something isn't covered, say so and point to get_contact_options. Never invent numbers, dates, employers or clients.

Where to start:
- Who is he, what does he do: get_profile
- What has he built: list_case_studies, then get_case_study for the full write-up. list_projects for open source and smaller projects.
- A specific skill, tool or topic: search_portfolio
- His writing: get_recent_posts. His resume: get_resume. Getting in touch: get_contact_options.
"""


def build_server(
    settings: Settings | None = None,
    *,
    loader: ContentLoader | None = None,
    medium: MediumClient | None = None,
    today: Callable[[], date] = utc_today,
) -> MCPServer:
    """Build the server. Tests pass their own loader, Medium client and date."""
    settings = settings or load_settings()
    deps = Deps(
        settings=settings,
        loader=loader or ContentLoader(settings),
        medium=medium or MediumClient(settings),
        today=today,
    )

    mcp = MCPServer(
        name="harsh-portfolio",
        title="Harsh Dadiya's portfolio",
        version="0.1.0",
        website_url="https://www.harshdadiya.in",
        instructions=INSTRUCTIONS,
    )

    # M0 leftover: lets the connection be tested without touching any content.
    @mcp.tool(
        name="ping",
        description="Health check. Returns 'ok'. Only used to test the connection.",
        annotations=READ_ONLY,
    )
    def ping() -> str:
        return "ok"

    for module in (profile, case_studies, projects, writing, search, contact):
        module.register(mcp, deps)
    resources.register(mcp, deps)
    return mcp
