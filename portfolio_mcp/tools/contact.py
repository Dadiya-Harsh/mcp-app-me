"""get_contact_options. get_availability comes in M6."""

from urllib.parse import quote

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult

from portfolio_mcp import text
from portfolio_mcp.deps import Deps
from portfolio_mcp.tools._common import READ_ONLY, guarded, ok

SUGGESTED_SUBJECT = "Reaching out from your portfolio"


async def contact_result(deps: Deps) -> CallToolResult:
    profile = (await deps.loader.content()).profile
    links = profile.links
    mailto = f"mailto:{profile.email}?subject={quote(SUGGESTED_SUBJECT, safe='')}"
    return ok(
        text.contact(
            profile.email,
            mailto,
            links.contact,
            links.linkedin,
            links.booking,
            SUGGESTED_SUBJECT,
        ),
        {
            "email": profile.email,
            "mailtoUrl": mailto,
            "contactPage": links.contact,
            "bookingUrl": links.booking,
            "linkedin": links.linkedin,
            "suggestedSubject": SUGGESTED_SUBJECT,
        },
    )


def register(mcp: MCPServer, deps: Deps) -> None:
    @mcp.tool(
        name="get_contact_options",
        title="Contact Harsh",
        description=(
            "How to reach Harsh: email, a ready mailto link, the contact page, LinkedIn "
            "and a booking link if he has one. This server sends nothing itself. Use it "
            "when someone wants to get in touch, or when the portfolio doesn't cover "
            "what they asked."
        ),
        annotations=READ_ONLY,
    )
    async def get_contact_options() -> CallToolResult:
        return await guarded(contact_result(deps))
