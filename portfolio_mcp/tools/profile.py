"""get_profile and get_resume."""

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult

from portfolio_mcp import text
from portfolio_mcp.content.experience import experience_years, format_experience_years
from portfolio_mcp.deps import Deps
from portfolio_mcp.tools._common import READ_ONLY, dump, guarded, ok

# What get_profile returns as structured data (the contract's names), in this order.
# Work history, education and certifications are left out on purpose: they are in the
# portfolio://profile resource and are found by search_portfolio.
_BEFORE_EXPERIENCE = ("name", "title", "location")
_AFTER_EXPERIENCE = (
    "openToRoles",
    "openToRolesLabel",
    "headline",
    "summary",
    "tagline",
    "focus",
    "stats",
)


async def profile_data(deps: Deps) -> dict[str, Any]:
    """The profile as shown by get_profile (no work history)."""
    p = (await deps.loader.content()).profile
    full = dump(p)
    data: dict[str, Any] = {key: full[key] for key in _BEFORE_EXPERIENCE}
    data["experienceYears"] = experience_years(p.career_start, deps.today())
    data.update({key: full[key] for key in _AFTER_EXPERIENCE})
    data["nowBuilding"] = full["nowBuilding"] if p.now_building.show else None
    data["links"] = full["links"]
    data["photo"] = full["photo"]
    return data


async def profile_result(deps: Deps) -> CallToolResult:
    content = await deps.loader.content()
    data = await profile_data(deps)
    return ok(
        text.profile(
            content.profile,
            format_experience_years(data["experienceYears"]),
            content.case_studies,
            content.site_url,
        ),
        data,
    )


async def resume_result(deps: Deps) -> CallToolResult:
    links = (await deps.loader.content()).profile.links
    return ok(
        text.resume(links.resume, links.resume_pdf, links.resume_docx),
        {"page": links.resume, "pdf": links.resume_pdf, "docx": links.resume_docx},
    )


def register(mcp: MCPServer, deps: Deps) -> None:
    @mcp.tool(
        name="get_profile",
        title="Harsh's profile",
        description=(
            "Who Harsh Dadiya is: job title, location, years of experience, what he "
            "works on, what he is building now, and his links. Start here for any "
            "'who is Harsh' or 'tell me about him' question."
        ),
        annotations=READ_ONLY,
    )
    async def get_profile() -> CallToolResult:
        return await guarded(profile_result(deps))

    @mcp.tool(
        name="get_resume",
        title="Harsh's resume",
        description="Links to Harsh's resume: the web page, the PDF and the Word file.",
        annotations=READ_ONLY,
    )
    async def get_resume() -> CallToolResult:
        return await guarded(resume_result(deps))
