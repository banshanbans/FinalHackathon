from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from simulation.models.base import DomainModel
from simulation.models.common import Phase


class AuditRecordType(StrEnum):
    AGENT_INVOCATION = "agent_invocation"
    MECHANISM_EXPLANATION = "mechanism_explanation"
    DECISION_GATE = "decision_gate"


class AuditActorKind(StrEnum):
    CENTRAL_AGENT = "central_agent"
    PROVINCE_AGENT = "province_agent"
    ENTERPRISE_AGENT = "enterprise_agent"
    PERSONA_RULE = "persona_rule"
    ENVIRONMENT = "environment"
    USER = "user"
    ORCHESTRATOR = "orchestrator"


class AuditOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    REPAIRED = "repaired"
    FALLBACK = "fallback"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    REJECTED = "rejected"


class ProviderAttemptTrace(DomainModel):
    attempt: int = Field(ge=1, le=2)
    status: Literal["succeeded", "validation_error", "provider_error"]
    latency_ms: float = Field(ge=0)
    error_code: str | None = None
    validation_paths: list[str] = Field(default_factory=list)
    invalid_response_hash: str | None = None


class TokenUsageTrace(DomainModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AgentInvocationTrace(DomainModel):
    kind: Literal[AuditRecordType.AGENT_INVOCATION] = AuditRecordType.AGENT_INVOCATION
    actor_kind: AuditActorKind
    actor_id: str
    operation: str
    run_mode: str
    model: str
    prompt_version: str
    response_schema: str
    input_hash: str
    input_snapshot: JsonValue
    attempts: list[ProviderAttemptTrace] = Field(default_factory=list, max_length=2)
    usage: TokenUsageTrace | None = None
    latency_ms: float = Field(ge=0)
    outcome: AuditOutcome
    output_ids: list[str] = Field(default_factory=list)
    output_hash: str
    output_snapshot: JsonValue
    cache_key_hash: str | None = None
    fallback_reason: str | None = Field(default=None, max_length=240)


class MechanismTerm(DomainModel):
    name: str
    input_value: float
    coefficient: float
    contribution: float
    source_ref: str | None = None


class MechanismExplanation(DomainModel):
    kind: Literal[AuditRecordType.MECHANISM_EXPLANATION] = AuditRecordType.MECHANISM_EXPLANATION
    explanation_id: str
    scope: Literal["enterprise", "province", "national", "comparison"]
    subject_id: str
    metric: str
    formula_id: str
    formula_version: str
    source_refs: list[str] = Field(default_factory=list)
    terms: list[MechanismTerm] = Field(default_factory=list)
    previous_value: float | None = None
    raw_value: float
    clamp_min: float = 0
    clamp_max: float = 100
    clamp_adjustment: float = 0
    final_value: float
    residual: float = 0
    unit: str = "指数点"


class DecisionGateTrace(DomainModel):
    kind: Literal[AuditRecordType.DECISION_GATE] = AuditRecordType.DECISION_GATE
    actor_kind: AuditActorKind
    actor_id: str
    operation: str
    outcome: AuditOutcome
    object_ids: list[str] = Field(default_factory=list)
    details: dict[str, JsonValue] = Field(default_factory=dict)


AuditPayload = Annotated[
    AgentInvocationTrace | MechanismExplanation | DecisionGateTrace,
    Field(discriminator="kind"),
]


class AuditRecord(DomainModel):
    schema_version: Literal["audit-record-v1"] = "audit-record-v1"
    record_id: str
    sequence: int = Field(ge=1)
    experiment_id: str
    branch_id: str
    phase: Phase
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parent_record_ids: list[str] = Field(default_factory=list)
    previous_record_hash: str | None = None
    record_hash: str
    payload: AuditPayload


class AuditListResponse(DomainModel):
    schema_version: Literal["audit-list-v1"] = "audit-list-v1"
    records: list[AuditRecord]
    next_sequence: int | None = None
