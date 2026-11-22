"""Plain-text renderers, one per tool.

This is what ChatGPT and other clients without MCP Apps show, and it is also what the
model reads on every call, so it is kept short and plain, with links.
Snapshot tests (tests/snapshots) keep the wording from changing by accident.
"""

from collections.abc import Sequence

from portfolio_mcp.content.markdown import Section
from portfolio_mcp.content.models import CaseStudy, Link, Profile, Projects
from portfolio_mcp.content.search import SearchResult
from portfolio_mcp.integrations.medium import MediumPost

CONTACT_NOTE = (
    "If you have email or calendar tools connected, "
    "I can draft a message for you to send."
)


def profile(
    p: Profile,
    experience_years: str,
    case_studies: Sequence[CaseStudy],
    site_url: str,
) -> str:
    first = f"{p.name}, {p.title} in {p.location}."
    if p.open_to_roles:
        first += f" {p.open_to_roles_label}."
    first += f" {experience_years} years of experience."
    lines = [
        first,
        p.summary,
        "Works on: " + ", ".join(f.title for f in p.focus) + ".",
    ]
    if case_studies:
        names = ", ".join(f"{c.title} ({c.id})" for c in case_studies)
        lines.append(f"Case studies: {names}.")
    if p.now_building.show:
        lines.append(
            f"Now building: {p.now_building.name}. {p.now_building.description} "
            f"{p.now_building.repo_url}"
        )
    lines.append(
        f"Links: site {site_url} | GitHub {p.links.github} | "
        f"LinkedIn {p.links.linkedin} | Medium {p.links.medium} | "
        f"resume {p.links.resume}"
    )
    return "\n".join(lines)


def case_study_list(studies: Sequence[CaseStudy]) -> str:
    if not studies:
        return "There are no published case studies right now."
    noun = "case study" if len(studies) == 1 else "case studies"
    lines = [
        f"{len(studies)} {noun}. Use get_case_study with the id for the full write-up."
    ]
    for s in studies:
        lines += [
            "",
            f"- {s.title} (id: {s.id}) | {s.type} | {s.role}, {s.team}, {s.duration}",
            f"  {s.desc}",
            f"  Stack: {', '.join(s.tech_stack)}",
            f"  {s.url}",
        ]
    return "\n".join(lines)


def case_study(study: CaseStudy, sections: Sequence[Section]) -> str:
    lines = [
        study.title,
        study.subtitle,
        f"{study.role} | {study.team} | {study.duration}",
    ]
    for section in sections:
        lines += ["", f"## {section.heading}", section.markdown]
    lines += ["", f"Read it on the site: {study.url}"]
    return "\n".join(lines)


def projects(p: Projects, group: str = "all") -> str:
    lines: list[str] = []

    def heading(text: str) -> None:
        if lines:
            lines.append("")
        lines.append(text)

    def links(items: Sequence[Link]) -> str:
        return " | ".join(f"{i.label}: {i.url}" for i in items)

    if group in ("all", "recent") and p.recent:
        heading("Recent")
        for project in p.recent:
            lines += [f"- {project.title}: {project.description}"]
            if project.links:
                lines.append(f"  {links(project.links)}")
    if group in ("all", "openSource") and p.open_source:
        heading("Open source")
        for oss in p.open_source:
            lines += [
                f"- {oss.title}: {oss.description}",
                f"  Tech: {', '.join(oss.technologies)}",
            ]
            if oss.links:
                lines.append(f"  {links(oss.links)}")
    if group in ("all", "earlier") and p.earlier:
        heading("Earlier")
        for project in p.earlier:
            lines += [f"- {project.title}: {project.description}"]
            if project.links:
                lines.append(f"  {links(project.links)}")
    return "\n".join(lines) if lines else "No projects in this group."


def posts(items: Sequence[MediumPost], medium_url: str) -> str:
    if not items:
        return f"No Medium posts found. His Medium page: {medium_url}"
    lines = [f"Latest {len(items)} on Medium ({medium_url}):"]
    for post in items:
        when = f" ({post.date})" if post.date else ""
        tags = f" [{', '.join(post.tags)}]" if post.tags else ""
        lines.append(f"- {post.title}{when}{tags}")
        lines.append(f"  {post.link}")
    return "\n".join(lines)


def posts_unavailable(medium_url: str) -> str:
    return (
        "Couldn't load the Medium posts right now. "
        f"They are all on his Medium page: {medium_url}"
    )


def search_results(query: str, results: Sequence[SearchResult]) -> str:
    if not results:
        return (
            f'No matches for "{query}" in the portfolio. Try other words, or use '
            "get_profile, list_case_studies or list_projects."
        )
    lines = [f'Top {len(results)} matches for "{query}":']
    for number, r in enumerate(results, start=1):
        lines += ["", f"{number}. [{r.type}] {r.title}", f"   {r.snippet}"]
        if r.url:
            lines.append(f"   {r.url}")
    return "\n".join(lines)


def resume(page: str, pdf: str, docx: str) -> str:
    return "\n".join(
        [
            "Harsh's resume:",
            f"- Web page: {page}",
            f"- PDF: {pdf}",
            f"- Word: {docx}",
        ]
    )


def contact(
    email: str,
    mailto_url: str,
    contact_page: str,
    linkedin: str,
    booking_url: str | None,
    subject: str,
) -> str:
    return "\n".join(
        [
            f"Email: {email}",
            f"Mailto link: {mailto_url}",
            f"Contact page: {contact_page}",
            f"LinkedIn: {linkedin}",
            f"Booking link: {booking_url or 'none yet'}",
            f"Suggested subject: {subject}",
            CONTACT_NOTE,
        ]
    )
