"""Pydantic models for Gate Server request/response shapes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolIn(BaseModel):
    name: str
    execution_class: str = "read_only"
    description: str = ""
    inputs: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterRequest(BaseModel):
    tools: list[ToolIn]


class FilterRequest(BaseModel):
    mode: float = Field(ge=0.0, le=1.0)


class ToolOut(BaseModel):
    name: str
    execution_class: str
    description: str
    inputs: dict[str, str]


class FilterResponse(BaseModel):
    visible: list[ToolOut]
    suppressed: list[ToolOut]
    mode: float
    mode_zone: str
    thresholds: dict[str, float | None]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    tool_count: int


class RegisterResponse(BaseModel):
    registered: int
    total: int


# --- Envelope models ---

class EnvelopeBuildRequest(BaseModel):
    tool_name: str
    mode: float = Field(ge=0.0, le=1.0)
    context_id: str
    human_approved: bool = False
    extra_tools: list[str] = Field(default_factory=list)


class EnvelopeOut(BaseModel):
    envelope_id: str
    context_id: str
    tool_name: str
    allowed_tools: list[str]
    max_tool_calls: int
    max_retries: int
    budget_seconds: int
    execution_mode: str
    dry_run: bool
    branching: str
    human_approved: bool
    created_at: float = 0.0
    signature: str


class EnvelopeVerifyRequest(BaseModel):
    envelope: EnvelopeOut


class EnvelopeVerifyFreshRequest(BaseModel):
    envelope: EnvelopeOut
    max_age_seconds: float = 300.0


class EnvelopeVerifyResponse(BaseModel):
    valid: bool


# --- Ingress validation ---

class ValidateRequest(BaseModel):
    tool_name: str
    mode: float = Field(ge=0.0, le=1.0)


class ValidateResponse(BaseModel):
    accepted: bool
    reason: str | None = None
    detail: str | None = None


# --- OpenAI export ---

class OpenAIExportRequest(BaseModel):
    mode: float = Field(ge=0.0, le=1.0)


# --- Mode history ---

class ModeEntry(BaseModel):
    mode: float
    mode_zone: str
    timestamp: str
    visible_count: int
    suppressed_count: int


class ModeHistoryResponse(BaseModel):
    entries: list[ModeEntry]
    total: int
