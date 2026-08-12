from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, model_validator

from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.base import DomainModel
from simulation.models.common import (
    CoordinationStatus,
    EventFamily,
    EventIntensity,
    EventPerception,
    EventPolicyFocus,
    EventScenarioStatus,
    EventTemplateId,
    PeerResponseMode,
    Phase,
    RunMode,
)


class EventScenarioTemplate(DomainModel):
    schema_version: Literal["event-scenario-template-v1"] = "event-scenario-template-v1"
    template_id: EventTemplateId
    family: EventFamily
    title: str
    description: str
    target_province_codes: list[str] = Field(default_factory=list)
    mechanism_channels: list[str] = Field(min_length=1)
    provenance_refs: list[str] = Field(min_length=1)


class EventScenarioSelection(DomainModel):
    template_id: EventTemplateId
    intensity: EventIntensity = EventIntensity.MEDIUM


class EventScenario(DomainModel):
    schema_version: Literal["event-scenario-v1"] = "event-scenario-v1"
    scenario_id: str
    template_id: EventTemplateId
    family: EventFamily
    title: str
    intensity: EventIntensity
    magnitude: float = Field(ge=0, le=1)
    target_province_codes: list[str] = Field(default_factory=list)
    activation_phase: Literal[Phase.Y2_Q3] = Phase.Y2_Q3
    duration_quarters: Literal[2] = 2
    status: Literal[EventScenarioStatus.APPROVED] = EventScenarioStatus.APPROVED
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_by: Literal["user"] = "user"
    mechanism_version: Literal["nev-policy-env-v2"] = "nev-policy-env-v2"
    provenance_refs: list[str] = Field(min_length=1)
    disclaimer: str = "本事件为冻结机制参数下的情景实验，不代表现实事件、法规或价格走势预测。"

    @model_validator(mode="after")
    def canonical_intensity_and_scope(self) -> "EventScenario":
        if abs(self.magnitude - self.intensity.magnitude) > 1e-9:
            raise ValueError("event magnitude must match the frozen intensity mapping")
        if not set(self.target_province_codes) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError("event target is outside the 31-province scope")
        return self


class SubsidyMixDelta(DomainModel):
    consumer: float = Field(default=0, ge=-1, le=1)
    fixed_cost: float = Field(default=0, ge=-1, le=1)
    variable_cost: float = Field(default=0, ge=-1, le=1)

    @model_validator(mode="after")
    def sums_to_zero(self) -> "SubsidyMixDelta":
        if abs(self.consumer + self.fixed_cost + self.variable_cost) > 1e-6:
            raise ValueError("event subsidy mix deltas must sum to 0")
        return self


class ProvinceEventSignal(DomainModel):
    schema_version: Literal["province-event-signal-v1"] = "province-event-signal-v1"
    signal_id: str
    scenario_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Literal[Phase.Y2_Q3] = Phase.Y2_Q3
    exposure: float = Field(ge=0, le=1)
    perception: EventPerception
    policy_focus: EventPolicyFocus
    proposed_peer_codes: list[str] = Field(default_factory=list, max_length=2)
    evidence_refs: list[str] = Field(min_length=1, max_length=6)
    summary: str = Field(min_length=1, max_length=80)
    run_mode: RunMode = RunMode.FAKE
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def valid_signal(self) -> "ProvinceEventSignal":
        if self.province_code not in MAINLAND_PROVINCE_CODES:
            raise ValueError("province is outside the 31-province scope")
        peers = self.proposed_peer_codes
        if len(peers) != len(set(peers)) or self.province_code in peers:
            raise ValueError("proposed peers must be unique and cannot include self")
        if not set(peers) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError("unknown proposed peer")
        if self.fallback_used != (self.run_mode is RunMode.FALLBACK) or self.fallback_used != bool(
            self.fallback_reason
        ):
            raise ValueError("fallback fields are inconsistent")
        return self


class ProvinceEventResponse(DomainModel):
    schema_version: Literal["province-event-response-v1"] = "province-event-response-v1"
    response_id: str
    scenario_id: str
    province_code: str = Field(pattern=r"^\d{2}$")
    phase: Literal[Phase.Y2_Q3] = Phase.Y2_Q3
    observed_signal_ids: list[str] = Field(default_factory=list, max_length=5)
    observed_peer_codes: list[str] = Field(default_factory=list, max_length=5)
    response_mode: PeerResponseMode
    policy_focus: EventPolicyFocus
    response_intensity: float = Field(ge=0, le=1)
    subsidy_mix_delta: SubsidyMixDelta = Field(default_factory=SubsidyMixDelta)
    coordination_target_codes: list[str] = Field(default_factory=list, max_length=2)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=1, max_length=80)
    run_mode: RunMode = RunMode.FAKE
    fallback_used: bool = False
    fallback_reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def valid_response(self) -> "ProvinceEventResponse":
        if self.province_code not in MAINLAND_PROVINCE_CODES:
            raise ValueError("province is outside the 31-province scope")
        peers = self.observed_peer_codes
        targets = self.coordination_target_codes
        if len(peers) != len(set(peers)) or len(targets) != len(set(targets)):
            raise ValueError("event peer lists must be unique")
        if self.province_code in peers or self.province_code in targets:
            raise ValueError("province cannot observe or coordinate with itself")
        if not set(peers + targets) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError("unknown event peer")
        if len(self.observed_signal_ids) != len(peers):
            raise ValueError("each observed peer must have one frozen signal")
        if self.response_mode is PeerResponseMode.COORDINATE:
            if not targets or not set(targets) <= set(peers):
                raise ValueError("coordinate responses require observed coordination targets")
        elif targets:
            raise ValueError("only coordinate responses may name coordination targets")
        if self.fallback_used != (self.run_mode is RunMode.FALLBACK) or self.fallback_used != bool(
            self.fallback_reason
        ):
            raise ValueError("fallback fields are inconsistent")
        return self


class CoordinationMatch(DomainModel):
    schema_version: Literal["province-coordination-v1"] = "province-coordination-v1"
    match_id: str
    scenario_id: str
    left_province_code: str = Field(pattern=r"^\d{2}$")
    right_province_code: str = Field(pattern=r"^\d{2}$")
    status: CoordinationStatus
    policy_focus: EventPolicyFocus
    complementarity: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def ordered_pair(self) -> "CoordinationMatch":
        if self.left_province_code >= self.right_province_code:
            raise ValueError("coordination pair must be unique and canonically ordered")
        if self.status is CoordinationStatus.UNMATCHED and self.contribution != 0:
            raise ValueError("unmatched coordination cannot contribute")
        return self


class EventScenarioDiff(DomainModel):
    control_scenario_id: str | None = None
    treatment_scenario_id: str | None = None
    changed: bool
    description: str


class ProvinceInteractionEdge(DomainModel):
    source_province_code: str = Field(pattern=r"^\d{2}$")
    target_province_code: str = Field(pattern=r"^\d{2}$")
    observation_weight: float = Field(gt=0, le=1)
    coordinate_eligible: bool

    @model_validator(mode="after")
    def no_self_edge(self) -> "ProvinceInteractionEdge":
        if self.source_province_code == self.target_province_code:
            raise ValueError("interaction network cannot contain self edges")
        return self


class ProvinceInteractionNetwork(DomainModel):
    schema_version: Literal["province-interaction-network-v1"] = "province-interaction-network-v1"
    source_network_version: Literal["nev-peer-network-v1"] = "nev-peer-network-v1"
    edges: list[ProvinceInteractionEdge]

    @model_validator(mode="after")
    def complete_observation_scope(self) -> "ProvinceInteractionNetwork":
        sources = {edge.source_province_code for edge in self.edges}
        if sources != set(MAINLAND_PROVINCE_CODES):
            raise ValueError("interaction network must cover all 31 provinces")
        pairs = [(edge.source_province_code, edge.target_province_code) for edge in self.edges]
        if len(pairs) != len(set(pairs)):
            raise ValueError("interaction network edges must be unique")
        return self
