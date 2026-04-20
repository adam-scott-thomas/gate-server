"""Policy HTTP endpoints for gate-server — STUB.

These routes would let gate-server load, query, and hot-reload
gate-policy policies over HTTP. Seeded by Creator 4 for Improvers.

Endpoints:
  GET  /v1/policy          → active policy name + rule count
  PUT  /v1/policy           → hot-reload policy from YAML body
  POST /v1/filter/policy    → filter with mode + context (policy-aware)
  GET  /v1/policy/audit     → recent audit log entries

Depends on: gate-policy (pip install gate-policy)
"""

# from fastapi import APIRouter, HTTPException
# from gate_policy import load_policy, PolicyGate
# from gate_policy.audit import AuditLog

# router = APIRouter(prefix="/v1/policy", tags=["policy"])

# TODO: Improver — wire these into gate-server/app.py
# TODO: Add policy file path config to gate-server settings
# TODO: Support multiple named policies with switching
# TODO: Connect AuditLog to policy filter results
