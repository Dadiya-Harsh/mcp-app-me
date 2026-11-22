"""Settings from environment variables. Plain os.environ, no extra library."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Local dev only. On Vercel there is no .env file, so this does nothing.
load_dotenv()

# Vercel sets these at runtime for each deployment (production and previews).
# Adding them to the Host allow list means preview URLs just work, with no wildcards.
_VERCEL_HOST_VARS = ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL")


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _vercel_hosts(source: Mapping[str, str]) -> list[str]:
    return [source[name] for name in _VERCEL_HOST_VARS if source.get(name)]


@dataclass(frozen=True)
class Settings:
    portfolio_url: str = "https://www.harshdadiya.in"
    content_ttl_seconds: int = 300
    content_fixture_path: str | None = None
    allowed_hosts: list[str] = field(default_factory=list)
    allowed_origins: list[str] = field(default_factory=list)
    log_level: str = "INFO"


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source: Mapping[str, str] = os.environ if env is None else env
    hosts = _split(
        source.get("ALLOWED_HOSTS", "mcp.harshdadiya.in,localhost:*,127.0.0.1:*")
    )
    for host in _vercel_hosts(source):
        if host not in hosts:
            hosts.append(host)
    return Settings(
        portfolio_url=source.get("PORTFOLIO_URL", "https://www.harshdadiya.in").rstrip(
            "/"
        ),
        content_ttl_seconds=int(source.get("CONTENT_TTL_SECONDS", "300")),
        content_fixture_path=source.get("CONTENT_FIXTURE_PATH") or None,
        allowed_hosts=hosts,
        allowed_origins=_split(source.get("ALLOWED_ORIGINS", "http://localhost:*")),
        log_level=source.get("LOG_LEVEL", "INFO").upper(),
    )
