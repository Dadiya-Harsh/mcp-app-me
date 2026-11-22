"""portfolio:// data resources. The ui:// resource is added in M4.

Resources use the same functions as the tools, so there is one place for each piece of
logic. They are for clients that let people (or the model) attach data directly.
"""

import json
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError

from portfolio_mcp.content.experience import experience_years
from portfolio_mcp.content.loader import ContentError
from portfolio_mcp.deps import Deps
from portfolio_mcp.tools._common import dump
from portfolio_mcp.tools.case_studies import case_study_meta

JSON = "application/json"


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def register(mcp: MCPServer, deps: Deps) -> None:
    # ContentError messages are written to be shown to people, so they go out as they are.

    @mcp.resource(
        "portfolio://profile",
        name="profile",
        title="Profile",
        description="Harsh's full profile, including work history, education and "
        "certifications, with his years of experience worked out for today.",
        mime_type=JSON,
    )
    async def profile() -> str:
        try:
            p = (await deps.loader.content()).profile
        except ContentError as exc:
            raise ResourceError(str(exc)) from exc
        data = dump(p)
        data["experienceYears"] = experience_years(p.career_start, deps.today())
        return _json(data)

    @mcp.resource(
        "portfolio://projects",
        name="projects",
        title="Projects",
        description="Recent, open source and earlier projects, with links.",
        mime_type=JSON,
    )
    async def projects() -> str:
        try:
            return _json(dump((await deps.loader.content()).projects))
        except ContentError as exc:
            raise ResourceError(str(exc)) from exc

    @mcp.resource(
        "portfolio://case-studies",
        name="case-studies",
        title="Case study index",
        description="The published case studies, one entry each. Read "
        "portfolio://case-studies/{id} for a full write-up.",
        mime_type=JSON,
    )
    async def case_studies() -> str:
        try:
            studies = (await deps.loader.content()).case_studies
        except ContentError as exc:
            raise ResourceError(str(exc)) from exc
        return _json({"caseStudies": [case_study_meta(s) for s in studies]})

    @mcp.resource(
        "portfolio://case-studies/{id}",
        name="case-study",
        title="Case study",
        description="The full markdown of one published case study.",
        mime_type="text/markdown",
    )
    async def case_study(id: str) -> str:
        # Only ids listed in content.json are ever fetched.
        try:
            return await deps.loader.case_study_md(id)
        except ContentError as exc:
            raise ResourceError(str(exc)) from exc

    @mcp.resource(
        "portfolio://resume",
        name="resume",
        title="Resume links",
        description="Links to the resume page, PDF and Word file.",
        mime_type=JSON,
    )
    async def resume() -> str:
        try:
            links = (await deps.loader.content()).profile.links
        except ContentError as exc:
            raise ResourceError(str(exc)) from exc
        return _json(
            {"page": links.resume, "pdf": links.resume_pdf, "docx": links.resume_docx}
        )

    @mcp.resource(
        "portfolio://llms-full",
        name="llms-full",
        title="Whole portfolio as text",
        description="Everything on the portfolio as one plain-text page "
        "(the site's /llms-full.txt).",
        mime_type="text/plain",
    )
    async def llms_full() -> str:
        try:
            return await deps.loader.llms_full()
        except ContentError as exc:
            raise ResourceError(str(exc)) from exc
