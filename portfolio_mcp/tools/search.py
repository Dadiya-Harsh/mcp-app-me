"""search_portfolio."""

import asyncio
import logging
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from portfolio_mcp import text
from portfolio_mcp.content.loader import ContentError
from portfolio_mcp.content.models import Content
from portfolio_mcp.content.search import MAX_QUERY_CHARS, search
from portfolio_mcp.deps import Deps
from portfolio_mcp.tools._common import READ_ONLY, guarded, ok

log = logging.getLogger(__name__)

RESULT_LIMIT = 5


async def _case_study_markdown(deps: Deps, content: Content) -> dict[str, str]:
    """Markdown of the published case studies. One that can't be loaded is skipped."""

    async def one(case_study_id: str) -> tuple[str, str | None]:
        try:
            return case_study_id, await deps.loader.case_study_md(case_study_id)
        except ContentError:
            log.warning("search: case study %s skipped, not loadable", case_study_id)
            return case_study_id, None

    pairs = await asyncio.gather(*(one(s.id) for s in content.case_studies))
    return {key: md for key, md in pairs if md is not None}


async def search_result(deps: Deps, query: str) -> CallToolResult:
    content = await deps.loader.content()
    markdown = await _case_study_markdown(deps, content)
    results = search(content, query, markdown, limit=RESULT_LIMIT)
    shown = " ".join(query.split())
    return ok(
        text.search_results(shown, results),
        {"query": shown, "results": [r.model_dump(mode="json") for r in results]},
    )


def register(mcp: MCPServer, deps: Deps) -> None:
    @mcp.tool(
        name="search_portfolio",
        title="Search the portfolio",
        description=(
            "Keyword search over everything on the portfolio: profile, work history, "
            "education, projects and the text of the case studies. Use it for a specific "
            "skill, tool or topic, like 'RAG' or 'AWS'. Returns the best 5 matches with "
            "a snippet and a link. No match means it isn't on the portfolio."
        ),
        annotations=READ_ONLY,
    )
    async def search_portfolio(
        query: Annotated[
            str,
            Field(
                min_length=1,
                max_length=MAX_QUERY_CHARS,
                description="Words to look for, up to 200 characters.",
            ),
        ],
    ) -> CallToolResult:
        return await guarded(search_result(deps, query))
