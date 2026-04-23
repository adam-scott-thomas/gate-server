# gate-server

[![status](https://img.shields.io/badge/status-v0.1.0-blue)]()
[![tests](https://img.shields.io/badge/tests-34_passing-brightgreen)]()
[![license](https://img.shields.io/badge/license-Apache_2.0-green)]()

> HTTP microservice exposing Maelstrom Gate as a deployable service.

Wraps `maelstrom-gate` in a FastAPI app so agents, dashboards, and CI systems can
talk to a single governance endpoint over HTTP. One process holds the mode zone,
the registered tool set, and the signing key for envelopes.

## Install

```bash
pip install gate-server  # once published
# or from source:
pip install -e .[dev]
```

## Run

```bash
uvicorn gate_server.app:app --host 0.0.0.0 --port 8090
# or: python -m gate_server
```

With Docker:

```bash
docker build -t gate-server .
docker run -p 8090:8090 -e GATE_SIGNING_KEY=changeme gate-server
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/tools` | register tool manifest |
| POST | `/v1/filter` | filter manifest at current mode |
| POST | `/v1/validate` | validate ingress proposal |
| GET  | `/v1/mode` | current mode + zone |
| POST | `/v1/mode` | update mode |
| POST | `/v1/envelope/build` | issue signed envelope |
| POST | `/v1/envelope/verify` | verify envelope signature |
| GET  | `/health` | liveness |

## Quick example

```python
import httpx

httpx.post("http://localhost:8090/v1/tools", json={
    "tools": [
        {"name": "read_file", "execution_class": "read_only"},
        {"name": "deploy",    "execution_class": "high_impact"},
    ]
})

r = httpx.post("http://localhost:8090/v1/filter", json={"mode": 0.85})
print(r.json()["visible_names"])  # ['read_file'] — deploy suppressed at crisis
```

## Integration modules

`gate_server` ships optional routes for the rest of the Gate stack:

- `policy_routes.py` — mount `gate-policy` evaluation
- `guard_middleware.py` — `gate-guard` runtime enforcement
- `metrics_mount.py` — Prometheus endpoint from `gate-metrics`
- `compliance_webhook.py` — stream decisions to `gate-compliance`
- `schema_validation.py` — validate payloads via `gate-schema`

Each mounts on import and degrades cleanly if the optional dep is absent.

## Configuration

- `GATE_SIGNING_KEY` — HMAC key for envelope signing (required for `/envelope/*`)
- `GATE_MODE_INITIAL` — starting mode value (default `0.0`)

## Tests

```bash
pytest tests/
```

34 tests cover API surface, failure injection, and envelope round-trips.

## How it fits

Layer 1 (transport) in [Maelstrom Gate](https://github.com/adam-scott-thomas/maelstrom-gate).
Consumed by `gate-sdk`, `gatectl`, `gate-dash`, `gate-dashboard`, and any process
that can speak HTTP.

## License

Apache-2.0.
