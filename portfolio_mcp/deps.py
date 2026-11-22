"""The things tools and resources need, in one place so tests can swap them."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from portfolio_mcp.content.loader import ContentLoader
from portfolio_mcp.integrations.medium import MediumClient
from portfolio_mcp.settings import Settings


def utc_today() -> date:
    return datetime.now(UTC).date()


@dataclass(frozen=True)
class Deps:
    settings: Settings
    loader: ContentLoader
    medium: MediumClient
    today: Callable[[], date] = utc_today
