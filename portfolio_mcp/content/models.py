"""Pydantic models for content.json v1.

Same shape as the contract (plans/mcp/master-plan.md, section 6). Field names are
snake_case in Python and camelCase in JSON, so `model_dump(by_alias=True)` gives
back the contract's names. Extra keys in the JSON are ignored.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

CONTENT_VERSION = 1


class _Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="ignore"
    )


class Link(_Model):
    label: str
    url: str


class FocusItem(_Model):
    title: str
    description: str
    href: str | None = None  # left out of the JSON when the card doesn't link anywhere


class Stat(_Model):
    value: str
    label: str


class ProfileLinks(_Model):
    github: str
    linkedin: str
    medium: str
    resume: str
    resume_pdf: str
    resume_docx: str
    contact: str
    booking: str | None = None


class NowBuilding(_Model):
    show: bool
    name: str
    description: str
    repo_url: str


class Experience(_Model):
    role: str
    org: str
    org_url: str | None = None
    period: str
    points: list[str]
    tags: list[
        str
    ] = []  # tech pills; not in the contract yet, the portfolio sends them


class Education(_Model):
    title: str
    org: str
    period: str


class Certification(_Model):
    title: str
    issuer: str
    date: str
    url: str | None = None


class Profile(_Model):
    name: str
    title: str
    location: str
    career_start: str  # "YYYY-MM"
    open_to_roles: bool
    open_to_roles_label: str
    headline: str
    summary: str
    tagline: str
    focus: list[FocusItem]
    stats: list[Stat]
    photo: str
    email: str
    links: ProfileLinks
    now_building: NowBuilding
    experience: list[Experience]
    education: list[Education]
    certifications: list[Certification]


class Project(_Model):
    title: str
    description: str
    links: list[Link]


class OpenSourceProject(Project):
    technologies: list[str]
    repo_stars: str


class Projects(_Model):
    recent: list[Project]
    open_source: list[OpenSourceProject]
    earlier: list[Project]


class CaseStudy(_Model):
    id: str
    type: str
    title: str
    subtitle: str
    role: str
    team: str
    duration: str
    tech_stack: list[str]
    desc: str
    bullets: list[str]
    url: str
    markdown_url: str


class Content(_Model):
    version: int
    generated_at: str
    site_url: str
    profile: Profile
    projects: Projects
    case_studies: list[CaseStudy]
