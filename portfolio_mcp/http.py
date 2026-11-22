"""FastAPI wrapper around the MCP app.

Why this exists: the SDK's streamable HTTP app needs its lifespan to run (it starts a
task group). Without it every request fails with "Task group is not initialized".
A mounted sub-app's lifespan is not run by the parent, so we run it by hand here.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings

from portfolio_mcp.server import build_server
from portfolio_mcp.settings import Settings, load_settings

log = logging.getLogger("portfolio_mcp")


def create_app(settings: Settings) -> FastAPI:
    logging.basicConfig(
        level=settings.log_level, format="%(levelname)s %(name)s: %(message)s"
    )

    mcp_app = build_server().streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        max_request_body_size=64_000,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.allowed_hosts,
            allowed_origins=settings.allowed_origins,
        ),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Starts the SDK's task group.
        async with mcp_app.router.lifespan_context(mcp_app):
            app.state.mcp_lifespan_running = True
            log.info("MCP lifespan started")
            yield
        app.state.mcp_lifespan_running = False
        log.info("MCP lifespan stopped")

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.mcp_lifespan_running = False

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True, "lifespan": bool(app.state.mcp_lifespan_running)}

    # Serves POST /mcp. Mounted last so /health matches first.
    app.mount("/", mcp_app)
    return app


app = create_app(load_settings())
