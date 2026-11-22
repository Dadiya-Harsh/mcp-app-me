"""Builds the MCP server. M0 has one tool, `ping`. Real tools arrive in M2."""

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

INSTRUCTIONS = (
    "This server is Harsh Dadiya's portfolio. Answer only from what these tools return "
    "and link to the pages they give. If something isn't covered, say so. "
    "Never invent numbers, dates, employers or clients."
)

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def build_server() -> MCPServer:
    mcp = MCPServer(
        name="harsh-portfolio",
        title="Harsh Dadiya's portfolio",
        version="0.1.0",
        website_url="https://www.harshdadiya.in",
        instructions=INSTRUCTIONS,
    )

    @mcp.tool(
        name="ping",
        description="Health check. Returns 'ok'. Only used to test the connection.",
        annotations=READ_ONLY,
    )
    def ping() -> str:
        return "ok"

    return mcp
