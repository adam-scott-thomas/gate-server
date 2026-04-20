"""Failure injection tests — verify gate-server handles bad input gracefully."""

import pytest
from httpx import ASGITransport, AsyncClient

from gate_server.app import create_app


@pytest.fixture
def client():
    app = create_app()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- Bad Payloads ---


class TestBadPayloads:
    @pytest.mark.asyncio
    async def test_register_empty_tools(self, client):
        r = await client.post("/api/v1/tools/register", json={"tools": []})
        assert r.status_code == 200
        assert r.json()["registered"] == 0

    @pytest.mark.asyncio
    async def test_register_missing_name(self, client):
        r = await client.post("/api/v1/tools/register", json={
            "tools": [{"execution_class": "read_only"}]
        })
        assert r.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_register_invalid_json(self, client):
        r = await client.post("/api/v1/tools/register",
                              content=b"not json",
                              headers={"content-type": "application/json"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_filter_missing_mode(self, client):
        r = await client.post("/api/v1/tools/filter", json={})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_filter_mode_out_of_range(self, client):
        """Mode values outside 0-1 are rejected by Pydantic validation."""
        await client.post("/api/v1/tools/register", json={
            "tools": [{"name": "t", "execution_class": "read_only"}]
        })
        r = await client.post("/api/v1/tools/filter", json={"mode": 5.0})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_validate_unknown_tool(self, client):
        """Validating an unregistered tool should return not-found result."""
        r = await client.post("/api/v1/tools/validate", json={
            "tool_name": "nonexistent", "mode": 0.5
        })
        assert r.status_code == 200
        assert r.json()["accepted"] is False

    @pytest.mark.asyncio
    async def test_envelope_build_no_tools(self, client):
        r = await client.post("/api/v1/envelope/build", json={
            "tool_name": "missing", "mode": 0.5, "context_id": "test"
        })
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_envelope_verify_bad_signature(self, client):
        """Envelope with garbage signature should return valid=False."""
        r = await client.post("/api/v1/envelope/verify", json={
            "envelope": {
                "envelope_id": "fake",
                "context_id": "fake",
                "tool_name": "fake",
                "allowed_tools": [],
                "max_tool_calls": 1,
                "max_retries": 0,
                "budget_seconds": 10,
                "execution_mode": "standard",
                "dry_run": False,
                "branching": "auto",
                "human_approved": False,
                "signature": "definitely_not_a_valid_hmac",
            }
        })
        assert r.status_code == 200
        assert r.json()["valid"] is False


# --- State Isolation ---


class TestStateIsolation:
    @pytest.mark.asyncio
    async def test_fresh_app_has_no_tools(self):
        """Each create_app() should start with zero tools."""
        app1 = create_app()
        app2 = create_app()
        c1 = AsyncClient(transport=ASGITransport(app=app1), base_url="http://t")
        c2 = AsyncClient(transport=ASGITransport(app=app2), base_url="http://t")

        await c1.post("/api/v1/tools/register", json={
            "tools": [{"name": "only_in_app1", "execution_class": "read_only"}]
        })

        r1 = await c1.get("/api/v1/tools")
        r2 = await c2.get("/api/v1/tools")
        assert len(r1.json()) == 1
        assert len(r2.json()) == 0  # app2 should be clean

    @pytest.mark.asyncio
    async def test_fresh_app_has_no_history(self):
        app1 = create_app()
        app2 = create_app()
        c1 = AsyncClient(transport=ASGITransport(app=app1), base_url="http://t")
        c2 = AsyncClient(transport=ASGITransport(app=app2), base_url="http://t")

        await c1.post("/api/v1/tools/register", json={
            "tools": [{"name": "t", "execution_class": "read_only"}]
        })
        await c1.post("/api/v1/tools/filter", json={"mode": 0.5})

        r1 = await c1.get("/api/v1/mode/history")
        r2 = await c2.get("/api/v1/mode/history")
        assert r1.json()["total"] == 1
        assert r2.json()["total"] == 0


# --- Full Workflow Under Stress ---


class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_register_filter_validate_envelope_cycle(self, client):
        """Complete lifecycle: register → filter → validate → envelope → verify."""
        # Register
        r = await client.post("/api/v1/tools/register", json={
            "tools": [
                {"name": "safe", "execution_class": "read_only"},
                {"name": "danger", "execution_class": "high_impact"},
            ]
        })
        assert r.json()["registered"] == 2

        # Filter at crisis
        r = await client.post("/api/v1/tools/filter", json={"mode": 0.9})
        visible = {t["name"] for t in r.json()["visible"]}
        assert "safe" in visible
        assert "danger" not in visible

        # Validate
        r = await client.post("/api/v1/tools/validate", json={
            "tool_name": "safe", "mode": 0.9
        })
        assert r.json()["accepted"] is True

        r = await client.post("/api/v1/tools/validate", json={
            "tool_name": "danger", "mode": 0.9
        })
        assert r.json()["accepted"] is False

        # Envelope round-trip
        r = await client.post("/api/v1/envelope/build", json={
            "tool_name": "safe", "mode": 0.3, "context_id": "stress-test"
        })
        envelope = r.json()
        assert envelope["tool_name"] == "safe"

        r = await client.post("/api/v1/envelope/verify", json={
            "envelope": envelope
        })
        assert r.json()["valid"] is True

        # Tamper and verify fails
        envelope["budget_seconds"] = 999
        r = await client.post("/api/v1/envelope/verify", json={
            "envelope": envelope
        })
        assert r.json()["valid"] is False

        # History recorded
        r = await client.get("/api/v1/mode/history")
        assert r.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_many_registrations(self, client):
        """Register many tools and verify they all show up."""
        tools = [{"name": f"tool_{i}", "execution_class": "read_only"}
                 for i in range(50)]
        r = await client.post("/api/v1/tools/register", json={"tools": tools})
        assert r.json()["registered"] == 50

        r = await client.get("/api/v1/tools")
        assert len(r.json()) == 50

    @pytest.mark.asyncio
    async def test_remove_then_reregister(self, client):
        """Remove a tool then re-add it."""
        await client.post("/api/v1/tools/register", json={
            "tools": [{"name": "phoenix", "execution_class": "read_only"}]
        })
        r = await client.delete("/api/v1/tools/phoenix")
        assert r.json()["removed"] == "phoenix"

        r = await client.get("/api/v1/tools")
        assert len(r.json()) == 0

        await client.post("/api/v1/tools/register", json={
            "tools": [{"name": "phoenix", "execution_class": "high_impact"}]
        })
        r = await client.get("/api/v1/tools")
        assert len(r.json()) == 1
        assert r.json()[0]["execution_class"] == "high_impact"
