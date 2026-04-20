# Gate Server — Integration Intent

## How the ecosystem connects through gate-server

```
                         ┌──────────────┐
                         │  gate-server │  ← Layer 1
                         │  :8900/api/v1│
                         └──────┬───────┘
                                │
                    depends on  │  wraps
                                ▼
                         ┌──────────────┐
                         │  gate-core   │  ← Layer 0
                         │  (Python lib)│
                         └──────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │                    CONSUMERS (Layer 2-3)                 │
  │                                                         │
  │  gate-sdk ──────► POST /tools/register                  │
  │   (L1)           POST /tools/filter                     │
  │                  POST /tools/openai                     │
  │                                                         │
  ���  dashboard ────► GET  /api/v1/tools                     │
  │   (L3)          GET  /api/v1/mode/history               │
  │                 POST /api/v1/tools/filter (live view)   │
  │                                                         │
  │  compliance ──► POST /api/v1/envelope/build             │
  │   (L2)         POST /api/v1/envelope/verify             │
  │                GET  /api/v1/mode/history (audit trail)  │
  │                                                         │
  │  policy ──────► POST /api/v1/tools/validate             │
  │   (L2)         POST /api/v1/tools/filter                │
  │                                                         │
  │  gate-ctf ────► POST /api/v1/tools/register (scenarios) │
  │   (L3)         POST /api/v1/tools/filter (challenges)   │
  │                POST /api/v1/envelope/build (auth CTF)   │
  └─────────────────────────────────────────────────────────┘
```

## Endpoint Map

| Endpoint | Consumer | Purpose |
|----------|----------|---------|
| `POST /tools/register` | SDK, CTF, any agent framework | Register tools with the gate |
| `POST /tools/filter` | SDK, dashboard, policy engine | Get visible tools at a mode level |
| `GET /tools` | Dashboard, admin UIs | List all registered tools |
| `DELETE /tools/{name}` | Admin, policy engine | Remove a tool |
| `POST /tools/validate` | Policy engine, agent runtime | Pre-flight check before tool execution |
| `POST /tools/openai` | SDK, agent frameworks | Export as OpenAI function-calling format |
| `POST /envelope/build` | Compliance, agent runtime | Build signed auth envelope for invocation |
| `POST /envelope/verify` | Compliance, executor | Verify envelope signature before execution |
| `GET /mode/history` | Dashboard, compliance | Audit trail of mode transitions |
| `GET /health` | Load balancer, monitoring | Health check |

## Connection Protocol

Any consumer hits gate-server over HTTP. No SDK required — plain curl works:

```bash
# Register tools
curl -X POST http://localhost:8900/api/v1/tools/register \
  -H "Content-Type: application/json" \
  -d '{"tools": [{"name": "read_file", "execution_class": "read_only"}]}'

# Filter at crisis mode
curl -X POST http://localhost:8900/api/v1/tools/filter \
  -H "Content-Type: application/json" \
  -d '{"mode": 0.8}'

# Get OpenAI-compatible tools
curl -X POST http://localhost:8900/api/v1/tools/openai \
  -H "Content-Type: application/json" \
  -d '{"mode": 0.3}'
```

## Not Yet Connected (integration gaps for Improvers)

- No auth middleware (API key or JWT)
- No WebSocket for live mode streaming to dashboards
- No event hooks for mode transitions (webhook/callback)
- No multi-tenant gate isolation (single gate per process)
- gate-sdk could embed a client class pointing at gate-server
