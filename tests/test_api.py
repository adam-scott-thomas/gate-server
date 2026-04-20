"""Comprehensive tests for Gate Server API — all 10 endpoints."""

import os
import pytest
from httpx import ASGITransport, AsyncClient

from gate_server.app import create_app


@pytest.fixture
def client():
    """Fresh app per test — no shared state between tests."""
    app = create_app()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- Health ---


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["tool_count"] == 0


# --- Tool Registration ---


@pytest.mark.asyncio
async def test_register_single_tool(client):
    r = await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "read_file", "execution_class": "read_only"}]
    })
    assert r.status_code == 200
    assert r.json()["registered"] == 1
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_register_multiple_tools(client):
    r = await client.post("/api/v1/tools/register", json={
        "tools": [
            {"name": "read_file", "execution_class": "read_only"},
            {"name": "deploy", "execution_class": "high_impact"},
            {"name": "send_email", "execution_class": "external_action"},
        ]
    })
    assert r.status_code == 200
    assert r.json()["registered"] == 3
    assert r.json()["total"] == 3


@pytest.mark.asyncio
async def test_register_with_metadata(client):
    r = await client.post("/api/v1/tools/register", json={
        "tools": [{
            "name": "deploy",
            "execution_class": "high_impact",
            "description": "Deploy to production",
            "inputs": {"branch": "string"},
            "metadata": {"danger": "extreme"},
        }]
    })
    assert r.status_code == 200


# --- List Tools ---


@pytest.mark.asyncio
async def test_list_empty(client):
    r = await client.get("/api/v1/tools")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_after_register(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [
            {"name": "t1", "execution_class": "read_only"},
            {"name": "t2", "execution_class": "advisory"},
        ]
    })
    r = await client.get("/api/v1/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    assert names == {"t1", "t2"}


# --- Filter ---


@pytest.mark.asyncio
async def test_filter_normal(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [
            {"name": "safe", "execution_class": "read_only"},
            {"name": "risky", "execution_class": "high_impact"},
        ]
    })
    r = await client.post("/api/v1/tools/filter", json={"mode": 0.1})
    assert r.status_code == 200
    body = r.json()
    assert body["mode_zone"] == "normal"
    assert len(body["visible"]) == 2
    assert len(body["suppressed"]) == 0


@pytest.mark.asyncio
async def test_filter_crisis(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [
            {"name": "safe", "execution_class": "read_only"},
            {"name": "risky", "execution_class": "high_impact"},
        ]
    })
    r = await client.post("/api/v1/tools/filter", json={"mode": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body["mode_zone"] == "crisis"
    visible_names = [t["name"] for t in body["visible"]]
    suppressed_names = [t["name"] for t in body["suppressed"]]
    assert "safe" in visible_names
    assert "risky" in suppressed_names


@pytest.mark.asyncio
async def test_filter_returns_thresholds(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "t", "execution_class": "read_only"}]
    })
    r = await client.post("/api/v1/tools/filter", json={"mode": 0.5})
    body = r.json()
    assert "thresholds" in body
    assert isinstance(body["thresholds"], dict)


# --- Remove Tool ---


@pytest.mark.asyncio
async def test_remove_existing_tool(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "doomed", "execution_class": "read_only"}]
    })
    r = await client.delete("/api/v1/tools/doomed")
    assert r.status_code == 200
    assert r.json()["removed"] == "doomed"

    # Verify it's gone
    r = await client.get("/api/v1/tools")
    assert len(r.json()) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_tool(client):
    r = await client.delete("/api/v1/tools/ghost")
    assert r.status_code == 404


# --- Validate ---


@pytest.mark.asyncio
async def test_validate_accepted(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "safe", "execution_class": "read_only"}]
    })
    r = await client.post("/api/v1/tools/validate", json={
        "tool_name": "safe", "mode": 0.9
    })
    assert r.status_code == 200
    assert r.json()["accepted"] is True


@pytest.mark.asyncio
async def test_validate_rejected(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "risky", "execution_class": "high_impact"}]
    })
    r = await client.post("/api/v1/tools/validate", json={
        "tool_name": "risky", "mode": 0.9
    })
    assert r.status_code == 200
    assert r.json()["accepted"] is False
    assert "reason" in r.json()


# --- OpenAI Export ---


@pytest.mark.asyncio
async def test_openai_export(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{
            "name": "read_file",
            "execution_class": "read_only",
            "description": "Read a file",
            "inputs": {"path": "string"},
        }]
    })
    r = await client.post("/api/v1/tools/openai", json={"mode": 0.1})
    assert r.status_code == 200
    tools = r.json()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "read_file"


@pytest.mark.asyncio
async def test_openai_export_filters_by_mode(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [
            {"name": "safe", "execution_class": "read_only"},
            {"name": "risky", "execution_class": "high_impact"},
        ]
    })
    r = await client.post("/api/v1/tools/openai", json={"mode": 0.9})
    tools = r.json()
    names = [t["function"]["name"] for t in tools]
    assert "safe" in names
    assert "risky" not in names


# --- Envelope Build + Verify ---


@pytest.mark.asyncio
async def test_envelope_build(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "tool1", "execution_class": "read_only"}]
    })
    r = await client.post("/api/v1/envelope/build", json={
        "tool_name": "tool1", "mode": 0.3, "context_id": "test"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["tool_name"] == "tool1"
    assert "signature" in body
    assert body["envelope_id"].startswith("env_")


@pytest.mark.asyncio
async def test_envelope_build_unknown_tool(client):
    r = await client.post("/api/v1/envelope/build", json={
        "tool_name": "nonexistent", "mode": 0.3, "context_id": "test"
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_envelope_verify_valid(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "tool1", "execution_class": "read_only"}]
    })
    build_r = await client.post("/api/v1/envelope/build", json={
        "tool_name": "tool1", "mode": 0.3, "context_id": "test"
    })
    envelope = build_r.json()
    r = await client.post("/api/v1/envelope/verify", json={
        "envelope": envelope
    })
    assert r.status_code == 200
    assert r.json()["valid"] is True


@pytest.mark.asyncio
async def test_envelope_tamper_detection(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "tool1", "execution_class": "read_only"}]
    })
    build_r = await client.post("/api/v1/envelope/build", json={
        "tool_name": "tool1", "mode": 0.3, "context_id": "test"
    })
    envelope = build_r.json()
    envelope["budget_seconds"] = 999  # tamper
    r = await client.post("/api/v1/envelope/verify", json={
        "envelope": envelope
    })
    assert r.status_code == 200
    assert r.json()["valid"] is False


# --- Mode History ---


@pytest.mark.asyncio
async def test_mode_history_empty(client):
    r = await client.get("/api/v1/mode/history")
    assert r.status_code == 200
    assert r.json()["entries"] == []
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_mode_history_after_filter(client):
    await client.post("/api/v1/tools/register", json={
        "tools": [{"name": "t", "execution_class": "read_only"}]
    })
    await client.post("/api/v1/tools/filter", json={"mode": 0.3})
    await client.post("/api/v1/tools/filter", json={"mode": 0.9})
    r = await client.get("/api/v1/mode/history")
    body = r.json()
    assert body["total"] == 2
    assert body["entries"][0]["mode"] == 0.3
    assert body["entries"][1]["mode"] == 0.9
    assert body["entries"][1]["mode_zone"] == "crisis"
