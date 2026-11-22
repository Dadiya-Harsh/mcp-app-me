"""list_case_studies and get_case_study."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from portfolio_mcp import text
from portfolio_mcp.content.loader import UnknownCaseStudy
from portfolio_mcp.content.markdown import parse_case_study
from portfolio_mcp.content.models import CaseStudy
from portfolio_mcp.deps import Deps
from portfolio_mcp.tools._common import READ_ONLY, dump, fail, guarded, ok

SectionName = Literal["overview", "problem", "architecture", "hard", "result", "all"]


def case_study_meta(study: CaseStudy) -> dict[str, Any]:
    """The facts about a case study, without the markdown path."""
    data: dict[str, Any] = dump(study)
    del data["markdownUrl"]
    return data


async def list_result(deps: Deps) -> CallToolResult:
    studies = (await deps.loader.content()).case_studies
    return ok(
        text.case_study_list(studies),
        {"caseStudies": [case_study_meta(s) for s in studies]},
    )


async def case_study_result(
    deps: Deps, case_study_id: str, section: SectionName
) -> CallToolResult:
    # Only ids listed in content.json can get through (UnknownCaseStudy otherwise).
    markdown = await deps.loader.case_study_md(case_study_id)
    studies = (await deps.loader.content()).case_studies
    study = next((s for s in studies if s.id == case_study_id), None)
    if study is None:  # can't happen after the call above, but keeps mypy honest
        raise UnknownCaseStudy(case_study_id, [s.id for s in studies])

    parsed = parse_case_study(markdown)
    available = [s.id for s in parsed.sections]
    chosen = (
        parsed.sections
        if section == "all"
        else [s for s in parsed.sections if s.id == section]
    )
    if not chosen:
        problem = (
            "This case study has no sections to show."
            if section == "all"
            else f"This case study has no '{section}' section."
        )
        return fail(
            f"{problem} Sections available: {', '.join(available) or 'none'}. "
            f"Read it on the site: {study.url}"
        )

    has_architecture = any(s.id == "architecture" for s in chosen)
    data = case_study_meta(study)
    data["requestedSection"] = section
    data["sections"] = [s.model_dump(mode="json") for s in chosen]
    data["steps"] = (
        [s.model_dump(mode="json") for s in parsed.steps] if has_architecture else []
    )
    return ok(text.case_study(study, chosen), data)


def register(mcp: MCPServer, deps: Deps) -> None:
    @mcp.tool(
        name="list_case_studies",
        title="Harsh's case studies",
        description=(
            "Lists Harsh's published case studies: what each one is, his role, team size, "
            "duration, tech stack and a short description. Use it to see what he has "
            "built, then call get_case_study with an id for the full write-up."
        ),
        annotations=READ_ONLY,
    )
    async def list_case_studies() -> CallToolResult:
        return await guarded(list_result(deps))

    @mcp.tool(
        name="get_case_study",
        title="Read a case study",
        description=(
            "The full write-up of one case study: overview, the problem, how the system "
            "works, what was hard and where it ended up. Get the id from "
            "list_case_studies. Use `section` when only one part is needed."
        ),
        annotations=READ_ONLY,
    )
    async def get_case_study(
        id: Annotated[
            str,
            Field(
                max_length=100,
                description="Case study id from list_case_studies, e.g. 'voice-agent'.",
            ),
        ],
        section: Annotated[
            SectionName,
            Field(
                description=(
                    "Which part to return: overview, problem, architecture (how it "
                    "works), hard (what was hard), result (where it ended up), or all."
                )
            ),
        ] = "all",
    ) -> CallToolResult:
        return await guarded(case_study_result(deps, id, section))
