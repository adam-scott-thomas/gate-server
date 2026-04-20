"""API routes — thin HTTP layer over gate-core.

State comes from app.state (set in create_app), not module globals.
This allows fresh state per app instance and proper test isolation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from maelstrom_gate import Tool
from maelstrom_gate.envelope import (
    AuthorizationEnvelope,
    build_envelope,
    verify_envelope,
    verify_envelope_fresh,
)
from maelstrom_gate.ingress import validate_proposal

from gate_server import __version__
from gate_server.models import (
    EnvelopeBuildRequest,
    EnvelopeOut,
    EnvelopeVerifyFreshRequest,
    EnvelopeVerifyRequest,
    EnvelopeVerifyResponse,
    FilterRequest,
    FilterResponse,
    HealthResponse,
    ModeEntry,
    ModeHistoryResponse,
    OpenAIExportRequest,
    RegisterRequest,
    RegisterResponse,
    ToolOut,
    ValidateRequest,
    ValidateResponse,
)

router = APIRouter(prefix="/api/v1")


def _tool_out(t: Tool) -> ToolOut:
    return ToolOut(
        name=t.name,
        execution_class=t.execution_class,
        description=t.description,
        inputs=t.inputs,
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(request: Request):
    gate = request.app.state.gate
    return HealthResponse(
        version=__version__,
        tool_count=len(gate.tools),
    )


@router.post("/tools/register", response_model=RegisterResponse, tags=["tools"])
async def register_tools(req: RegisterRequest, request: Request):
    gate = request.app.state.gate
    for t in req.tools:
        gate.add_tool(
            Tool(
                name=t.name,
                execution_class=t.execution_class,
                description=t.description,
                inputs=t.inputs,
                metadata=t.metadata,
            )
        )
    return RegisterResponse(registered=len(req.tools), total=len(gate.tools))


@router.post("/tools/filter", response_model=FilterResponse, tags=["tools"])
async def filter_tools(req: FilterRequest, request: Request):
    gate = request.app.state.gate
    mode_history = request.app.state.mode_history
    result = gate.filter(req.mode)
    mode_history.append(ModeEntry(
        mode=result.mode,
        mode_status=result.mode_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        visible_count=len(result.visible),
        suppressed_count=len(result.suppressed),
    ))
    return FilterResponse(
        visible=[_tool_out(t) for t in result.visible],
        suppressed=[_tool_out(t) for t in result.suppressed],
        mode=result.mode,
        mode_status=result.mode_status,
        thresholds=result.thresholds,
    )


@router.get("/tools", response_model=list[ToolOut], tags=["tools"])
async def list_tools(request: Request):
    gate = request.app.state.gate
    return [_tool_out(t) for t in gate.tools]


@router.delete("/tools/{name}", tags=["tools"])
async def remove_tool(name: str, request: Request):
    gate = request.app.state.gate
    tools_before = len(gate.tools)
    gate.remove_tool(name)
    if len(gate.tools) == tools_before:
        raise HTTPException(404, f"Tool '{name}' not found")
    return {"removed": name}


# --- Ingress validation ---


@router.post("/tools/validate", response_model=ValidateResponse, tags=["tools"])
async def validate_tool(req: ValidateRequest, request: Request):
    gate = request.app.state.gate
    result = validate_proposal(req.tool_name, gate, req.mode)
    return ValidateResponse(
        accepted=result.accepted,
        reason=result.reason,
        detail=result.detail,
    )


# --- OpenAI-compatible export ---


@router.post("/tools/openai", tags=["tools"])
async def export_openai(req: OpenAIExportRequest, request: Request):
    gate = request.app.state.gate
    result = gate.filter(req.mode)
    return result.to_openai_tools()


# --- Envelope endpoints ---


def _envelope_to_out(env: AuthorizationEnvelope) -> EnvelopeOut:
    return EnvelopeOut(
        envelope_id=env.envelope_id,
        context_id=env.context_id,
        tool_name=env.tool_name,
        allowed_tools=list(env.allowed_tools),
        max_tool_calls=env.max_tool_calls,
        max_retries=env.max_retries,
        budget_seconds=env.budget_seconds,
        execution_mode=env.execution_mode,
        dry_run=env.dry_run,
        branching=env.branching,
        human_approved=env.human_approved,
        created_at=env.created_at,
        signature=env.signature,
    )


@router.post("/envelope/build", response_model=EnvelopeOut, tags=["envelope"])
async def build_env(req: EnvelopeBuildRequest, request: Request):
    gate = request.app.state.gate
    signing_key = request.app.state.signing_key
    tools_by_name = {t.name: t for t in gate.tools}
    tool = tools_by_name.get(req.tool_name)
    if tool is None:
        raise HTTPException(404, f"Tool '{req.tool_name}' not registered")
    env = build_envelope(
        tool=tool,
        mode=req.mode,
        context_id=req.context_id,
        signing_key=signing_key,
        human_approved=req.human_approved,
        extra_tools=tuple(req.extra_tools),
    )
    return _envelope_to_out(env)


@router.post("/envelope/verify", response_model=EnvelopeVerifyResponse, tags=["envelope"])
async def verify_env(req: EnvelopeVerifyRequest, request: Request):
    signing_key = request.app.state.signing_key
    env = AuthorizationEnvelope(
        envelope_id=req.envelope.envelope_id,
        context_id=req.envelope.context_id,
        tool_name=req.envelope.tool_name,
        allowed_tools=tuple(req.envelope.allowed_tools),
        max_tool_calls=req.envelope.max_tool_calls,
        max_retries=req.envelope.max_retries,
        budget_seconds=req.envelope.budget_seconds,
        execution_mode=req.envelope.execution_mode,
        dry_run=req.envelope.dry_run,
        branching=req.envelope.branching,
        human_approved=req.envelope.human_approved,
        created_at=req.envelope.created_at,
        signature=req.envelope.signature,
    )
    return EnvelopeVerifyResponse(valid=verify_envelope(env, signing_key))


@router.post("/envelope/verify-fresh", tags=["envelope"])
async def verify_env_fresh(req: EnvelopeVerifyFreshRequest, request: Request):
    """Verify envelope signature AND check it hasn't expired (replay protection)."""
    signing_key = request.app.state.signing_key
    env = AuthorizationEnvelope(
        envelope_id=req.envelope.envelope_id,
        context_id=req.envelope.context_id,
        tool_name=req.envelope.tool_name,
        allowed_tools=tuple(req.envelope.allowed_tools),
        max_tool_calls=req.envelope.max_tool_calls,
        max_retries=req.envelope.max_retries,
        budget_seconds=req.envelope.budget_seconds,
        execution_mode=req.envelope.execution_mode,
        dry_run=req.envelope.dry_run,
        branching=req.envelope.branching,
        human_approved=req.envelope.human_approved,
        created_at=req.envelope.created_at,
        signature=req.envelope.signature,
    )
    valid, reason = verify_envelope_fresh(env, signing_key, req.max_age_seconds)
    return {"valid": valid, "reason": reason}


# --- Mode history ---


@router.get("/mode/history", response_model=ModeHistoryResponse, tags=["mode"])
async def mode_history(request: Request):
    entries = list(request.app.state.mode_history)
    return ModeHistoryResponse(entries=entries, total=len(entries))
