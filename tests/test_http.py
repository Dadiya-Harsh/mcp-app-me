"""M0 checks: the lifespan wrapper works, ping answers, the Host check behaves."""

import json

from fastapi.testclient import TestClient

from portfolio_mcp.http import create_app
from portfolio_mcp.settings import Settings, load_settings

MCP_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
}
PING = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "ping", "arguments": {}},
}


def make_client(hosts: list[str]) -> TestClient:
    app = create_app(Settings(allowed_hosts=hosts, allowed_origins=[]))
    return TestClient(app, base_url="http://mcp.example.test")


def test_ping_works_with_lifespan() -> None:
    # `with` runs the lifespan. If the wrapper is broken this fails with
    # "Task group is not initialized".
    with make_client(["mcp.example.test"]) as client:
        assert client.get("/health").json() == {"ok": True, "lifespan": True}
        res = client.post("/mcp", headers=MCP_HEADERS, content=json.dumps(PING))
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["result"]["isError"] is False
        assert body["result"]["content"][0]["text"] == "ok"


def test_unknown_host_is_rejected() -> None:
    with make_client(["somewhere-else.test"]) as client:
        res = client.post("/mcp", headers=MCP_HEADERS, content=json.dumps(PING))
        assert res.status_code == 421


def test_vercel_hosts_are_added_to_allow_list() -> None:
    settings = load_settings(
        {
            "ALLOWED_HOSTS": "mcp.harshdadiya.in",
            "VERCEL_URL": "mcp-app-me-abc123-harsh.vercel.app",
            "VERCEL_BRANCH_URL": "mcp-app-me-git-feat-m0-harsh.vercel.app",
            "VERCEL_PROJECT_PRODUCTION_URL": "mcp.harshdadiya.in",
        }
    )
    assert settings.allowed_hosts == [
        "mcp.harshdadiya.in",
        "mcp-app-me-abc123-harsh.vercel.app",
        "mcp-app-me-git-feat-m0-harsh.vercel.app",
    ]


def test_no_vercel_env_means_only_listed_hosts() -> None:
    settings = load_settings({"ALLOWED_HOSTS": "a.test,b.test:*"})
    assert settings.allowed_hosts == ["a.test", "b.test:*"]
