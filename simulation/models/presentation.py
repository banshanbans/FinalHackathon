from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from simulation.models.base import FrozenDomainModel
from simulation.models.v32 import EventIntensityV32, EventTriggerPoint, SimulationRound

PRESENTATION_EVENT_DISCLAIMER = "本事件为机制实验情景，不代表现实战争、法规、价格或企业行为预测。"


class PresentationEventCatalogEntry(FrozenDomainModel):
    schema_version: Literal["presentation-event-catalog-entry-v1"] = (
        "presentation-event-catalog-entry-v1"
    )
    template_id: str = Field(min_length=1, max_length=120)
    catalog_version: Literal["presentation-event-catalog-v1"] = "presentation-event-catalog-v1"
    family: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=280)
    trigger_points: list[EventTriggerPoint] = Field(min_length=3, max_length=3)
    affected_subjects: list[Literal["province", "automaker", "consumer", "supply_chain"]] = Field(
        min_length=1, max_length=4
    )
    mechanism_channels: list[str] = Field(min_length=1, max_length=12)
    supported_intensities: list[EventIntensityV32] = Field(min_length=3, max_length=3)
    branch_scopes: list[Literal["both", "treatment_only"]] = Field(min_length=2, max_length=2)
    advance_notice_supported: bool = True
    provenance_refs: list[str] = Field(min_length=1, max_length=8)
    mechanism_version: Literal["nev-policy-env-v6"] = "nev-policy-env-v6"
    data_quality: Literal["scenario_assumption"] = "scenario_assumption"
    disclaimer: str = Field(default=PRESENTATION_EVENT_DISCLAIMER, min_length=1, max_length=200)

    @model_validator(mode="after")
    def complete_capability_matrix(self) -> PresentationEventCatalogEntry:
        if self.trigger_points != list(EventTriggerPoint):
            raise ValueError("presentation event must expose the three frozen trigger points")
        if self.supported_intensities != list(EventIntensityV32):
            raise ValueError("presentation event must expose low, medium and high")
        if self.branch_scopes != ["both", "treatment_only"]:
            raise ValueError("presentation event branch scopes must be canonical")
        if len(self.affected_subjects) != len(set(self.affected_subjects)):
            raise ValueError("presentation event affected subjects must be unique")
        return self


class PresentationEventCatalog(FrozenDomainModel):
    schema_version: Literal["presentation-event-catalog-v1"] = "presentation-event-catalog-v1"
    catalog_version: Literal["presentation-event-catalog-v1"] = "presentation-event-catalog-v1"
    mechanism_version: Literal["nev-policy-env-v6"] = "nev-policy-env-v6"
    templates: list[PresentationEventCatalogEntry] = Field(min_length=5)

    @model_validator(mode="after")
    def unique_templates(self) -> PresentationEventCatalog:
        ids = [item.template_id for item in self.templates]
        if len(ids) != len(set(ids)):
            raise ValueError("presentation event catalog template ids must be unique")
        return self


class PresentationMode(StrEnum):
    LIVE = "live"
    STORY = "story"
    COMPARE = "compare"


class PresentationFrameKind(StrEnum):
    SETUP = "setup"
    ROUND = "round"
    EVENT = "event"
    SETTLEMENT = "settlement"
    COMPARISON = "comparison"


class PresentationOverlayKind(StrEnum):
    COMPETITION = "competition"
    NEGOTIATION = "negotiation"
    COORDINATION = "coordination"
    TOPK = "topk"
    EVENT = "event"
    AUTOMAKER = "automaker"


class PresentationCamera(FrozenDomainModel):
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    zoom: float = Field(ge=0, le=24, allow_inf_nan=False)
    pitch: float = Field(default=0, ge=0, le=85, allow_inf_nan=False)
    bearing: float = Field(default=0, ge=-180, le=180, allow_inf_nan=False)


class PresentationMapProjection(FrozenDomainModel):
    mode: Literal["absolute", "difference"]
    fill_metric: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=40)
    camera: PresentationCamera
    enabled_overlays: list[PresentationOverlayKind] = Field(default_factory=list)


class PresentationProvinceValue(FrozenDomainModel):
    province_code: str = Field(pattern=r"^\d{2}$")
    value: float | None = Field(default=None, allow_inf_nan=False)
    missing: bool = False
    data_quality: Literal["verified", "proxy", "scenario_assumption"]

    @model_validator(mode="after")
    def missing_value_is_explicit(self) -> PresentationProvinceValue:
        if self.missing != (self.value is None):
            raise ValueError("missing province values must use value=None")
        return self


class PresentationOverlayRecord(FrozenDomainModel):
    schema_version: Literal["presentation-overlay-record-v2"] = "presentation-overlay-record-v2"
    overlay_id: str = Field(min_length=1, max_length=160)
    kind: PresentationOverlayKind
    source_subject: str = Field(min_length=1, max_length=120)
    target_subject: str | None = Field(default=None, max_length=120)
    status: str = Field(min_length=1, max_length=80)
    weight: float | None = Field(default=None, allow_inf_nan=False)
    label: str = Field(min_length=1, max_length=160)
    style_semantic: Literal[
        "policy",
        "evidence",
        "event",
        "competition",
        "coordination",
        "neutral",
    ]
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class PresentationSubjectRef(FrozenDomainModel):
    subject_type: Literal["province", "automaker", "event", "policy", "environment"]
    subject_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=120)


class PresentationScoreComponent(FrozenDomainModel):
    component: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    value: float = Field(ge=-100, le=100, allow_inf_nan=False)
    weight: float = Field(ge=0, le=1, allow_inf_nan=False)
    contribution: float = Field(ge=-100, le=100, allow_inf_nan=False)
    direction: Literal["benefit", "cost"]


class PresentationOptionParameter(FrozenDomainModel):
    parameter: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=32)


class DecisionOptionEvaluation(FrozenDomainModel):
    schema_version: Literal["decision-option-evaluation-v1"] = "decision-option-evaluation-v1"
    option_id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=160)
    option_type: Literal[
        "chosen",
        "maintain",
        "policy_shift",
        "accept",
        "reject",
        "counteroffer",
        "reallocate",
        "no_action",
    ]
    feasible: bool
    infeasible_reasons: list[str] = Field(default_factory=list, max_length=6)
    score: float | None = Field(default=None, ge=-100, le=100, allow_inf_nan=False)
    delta_from_chosen: float | None = Field(default=None, ge=-200, le=200, allow_inf_nan=False)
    components: list[PresentationScoreComponent] = Field(default_factory=list, max_length=8)
    parameters: list[PresentationOptionParameter] = Field(default_factory=list, max_length=8)
    assumptions: list[str] = Field(default_factory=list, max_length=6)
    evidence_refs: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def evaluation_is_consistent(self) -> DecisionOptionEvaluation:
        if self.feasible != (self.score is not None):
            raise ValueError("feasible decision options require a score")
        if self.feasible and self.infeasible_reasons:
            raise ValueError("feasible decision options cannot have infeasible reasons")
        return self


class PresentationObservedSignal(FrozenDomainModel):
    source: PresentationSubjectRef
    signal: str = Field(min_length=1, max_length=220)
    evidence_refs: list[str] = Field(default_factory=list, max_length=6)


class PresentationActualResponse(FrozenDomainModel):
    response_id: str = Field(min_length=1, max_length=180)
    actor: PresentationSubjectRef
    action: str = Field(min_length=1, max_length=220)
    status: str = Field(min_length=1, max_length=80)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class PresentationDecisionMoment(FrozenDomainModel):
    schema_version: Literal["presentation-decision-moment-v1"] = "presentation-decision-moment-v1"
    moment_id: str = Field(min_length=1, max_length=180)
    trace_id: str = Field(min_length=1, max_length=180)
    branch_role: Literal["control", "treatment"]
    branch_id: str = Field(min_length=1, max_length=180)
    round: SimulationRound
    actor: PresentationSubjectRef
    objective: str = Field(min_length=1, max_length=240)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    observed_signals: list[PresentationObservedSignal] = Field(default_factory=list, max_length=8)
    actual_choice: str = Field(min_length=1, max_length=240)
    action_changes: list[str] = Field(default_factory=list, max_length=8)
    recorded_alternatives: list[str] = Field(default_factory=list, max_length=5)
    rejected_alternatives: list[str] = Field(default_factory=list, max_length=6)
    opportunity_costs: list[str] = Field(default_factory=list, max_length=6)
    change_conditions: list[str] = Field(default_factory=list, max_length=6)
    option_evaluations: list[DecisionOptionEvaluation] = Field(default_factory=list, max_length=4)
    response_status: Literal["not_applicable", "pending", "responded", "settled"]
    actual_responses: list[PresentationActualResponse] = Field(default_factory=list, max_length=8)
    affected_subjects: list[PresentationSubjectRef] = Field(default_factory=list, max_length=16)
    fallback_used: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)


class PresentationThreadBeat(FrozenDomainModel):
    beat_id: str = Field(min_length=1, max_length=180)
    round: SimulationRound
    label: str = Field(min_length=1, max_length=160)
    status: Literal["frozen", "pending"]
    subject: PresentationSubjectRef | None = None
    fact_ref: str | None = Field(default=None, max_length=200)


class PresentationGameThread(FrozenDomainModel):
    schema_version: Literal["presentation-game-thread-v1"] = "presentation-game-thread-v1"
    thread_id: str = Field(min_length=1, max_length=200)
    branch_role: Literal["control", "treatment"]
    thread_type: Literal[
        "policy_response", "competition", "coordination", "negotiation", "topk", "settlement"
    ]
    title: str = Field(min_length=1, max_length=180)
    participants: list[PresentationSubjectRef] = Field(min_length=1, max_length=12)
    resource_subject: PresentationSubjectRef | None = None
    state: Literal[
        "action_frozen", "awaiting_response", "response_frozen", "matched", "rejected", "settled"
    ]
    moment_ids: list[str] = Field(default_factory=list, max_length=20)
    beats: list[PresentationThreadBeat] = Field(min_length=1, max_length=12)
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)


class PresentationDivergence(FrozenDomainModel):
    schema_version: Literal["presentation-divergence-v1"] = "presentation-divergence-v1"
    divergence_id: str = Field(min_length=1, max_length=200)
    subject: PresentationSubjectRef
    round: SimulationRound
    dimension: Literal["choice", "action", "target", "response", "topk", "utility", "result"]
    control_summary: str = Field(min_length=1, max_length=220)
    treatment_summary: str = Field(min_length=1, max_length=220)
    magnitude: float = Field(ge=0, le=100, allow_inf_nan=False)
    first_for_subject: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)


class PresentationSpotlightScore(FrozenDomainModel):
    divergence: float = Field(ge=0, le=25, allow_inf_nan=False)
    response: float = Field(ge=0, le=20, allow_inf_nan=False)
    scarcity: float = Field(ge=0, le=15, allow_inf_nan=False)
    action_change: float = Field(ge=0, le=15, allow_inf_nan=False)
    state_change: float = Field(ge=0, le=15, allow_inf_nan=False)
    evidence: float = Field(ge=0, le=10, allow_inf_nan=False)
    total: float = Field(ge=0, le=100, allow_inf_nan=False)


class PresentationNarrativeBeat(FrozenDomainModel):
    beat: Literal["focus", "observe", "options", "action", "response", "tradeoff"]
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=240)
    status: Literal["frozen", "pending"]


class PresentationSpotlight(FrozenDomainModel):
    schema_version: Literal["presentation-spotlight-v1"] = "presentation-spotlight-v1"
    spotlight_id: str = Field(min_length=1, max_length=200)
    rank: Literal[1, 2, 3]
    label: str = Field(min_length=1, max_length=120)
    primary_moment_id: str = Field(min_length=1, max_length=180)
    thread_id: str | None = Field(default=None, max_length=200)
    branch_role: Literal["control", "treatment"]
    score: PresentationSpotlightScore
    narrative_beats: list[PresentationNarrativeBeat] = Field(min_length=4, max_length=6)
    focus_subjects: list[PresentationSubjectRef] = Field(min_length=1, max_length=8)
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)


class PresentationKeyChange(FrozenDomainModel):
    change_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=240)
    semantic: Literal[
        "policy",
        "event",
        "competition",
        "negotiation",
        "coordination",
        "result",
    ]
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class PresentationMetricSummary(FrozenDomainModel):
    metric_id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=80)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=40)
    delta: float | None = Field(default=None, allow_inf_nan=False)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)


class PresentationBranchProjection(FrozenDomainModel):
    schema_version: Literal["presentation-branch-projection-v2"] = (
        "presentation-branch-projection-v2"
    )
    branch_role: Literal["shared", "control", "treatment"]
    branch_id: str | None = Field(default=None, max_length=160)
    label: str = Field(min_length=1, max_length=80)
    map_projection: PresentationMapProjection
    province_values: list[PresentationProvinceValue] = Field(default_factory=list, max_length=31)
    overlay_records: list[PresentationOverlayRecord] = Field(default_factory=list)
    key_changes: list[PresentationKeyChange] = Field(default_factory=list, max_length=3)
    metric_summary: list[PresentationMetricSummary] = Field(default_factory=list, max_length=12)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)
    source_event_ids: list[str] = Field(default_factory=list, max_length=64)
    source_hash: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def branch_projection_is_consistent(self) -> PresentationBranchProjection:
        if (self.branch_role == "shared") != (self.branch_id is None):
            raise ValueError(
                "shared projection must omit branch id and branch projections require it"
            )
        codes = [item.province_code for item in self.province_values]
        if len(codes) != len(set(codes)):
            raise ValueError("presentation branch projection contains duplicate province values")
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise ValueError("presentation branch source events must be unique")
        return self


class PresentationFrame(FrozenDomainModel):
    schema_version: Literal["presentation-frame-v2"] = "presentation-frame-v2"
    frame_id: str = Field(min_length=1, max_length=160)
    sequence: int = Field(ge=0)
    kind: PresentationFrameKind
    round: SimulationRound | None = None
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=280)
    frozen: Literal[True] = True
    shared_projection: PresentationBranchProjection | None = None
    branch_projections: dict[Literal["control", "treatment"], PresentationBranchProjection] = Field(
        default_factory=dict
    )
    difference_projection: PresentationBranchProjection | None = None
    decision_moments: list[PresentationDecisionMoment] = Field(default_factory=list, max_length=512)
    interaction_threads: list[PresentationGameThread] = Field(default_factory=list, max_length=512)
    divergences: list[PresentationDivergence] = Field(default_factory=list, max_length=256)
    spotlights: list[PresentationSpotlight] = Field(default_factory=list, max_length=3)
    panel_refs: list[str] = Field(default_factory=list, max_length=16)
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)
    source_event_ids: list[str] = Field(default_factory=list, max_length=64)
    source_hash: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def frame_is_consistent(self) -> PresentationFrame:
        if self.kind is PresentationFrameKind.ROUND and self.round is None:
            raise ValueError("round frames require a simulation round")
        if self.kind is not PresentationFrameKind.ROUND and self.round is not None:
            raise ValueError("only round frames may set round")
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise ValueError("presentation frame source events must be unique")
        has_shared = self.shared_projection is not None
        has_branches = set(self.branch_projections) == {"control", "treatment"}
        if has_shared == has_branches:
            raise ValueError("presentation frame requires either shared or both branch projections")
        if has_branches:
            for role, projection in self.branch_projections.items():
                if projection.branch_role != role:
                    raise ValueError("branch projection role does not match its key")
        if self.difference_projection is not None and not has_branches:
            raise ValueError("difference projection requires both branch projections")
        if self.kind is PresentationFrameKind.ROUND and not self.spotlights:
            raise ValueError("round frames require at least one deterministic spotlight")
        if [item.rank for item in self.spotlights] != list(range(1, len(self.spotlights) + 1)):
            raise ValueError("presentation spotlight ranks must be contiguous")
        return self


class PresentationEventMarker(FrozenDomainModel):
    schema_version: Literal["presentation-event-marker-v2"] = "presentation-event-marker-v2"
    marker_id: str = Field(min_length=1, max_length=160)
    event_plan_id: str = Field(min_length=1, max_length=160)
    template_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    family: str = Field(min_length=1, max_length=80)
    intensity: EventIntensityV32
    trigger_point: EventTriggerPoint
    timeline_position: float = Field(ge=0, le=1, allow_inf_nan=False)
    branch_scope: Literal["both", "treatment_only"]
    advance_notice: bool = False
    affected_subjects: list[Literal["province", "automaker", "consumer", "supply_chain"]] = Field(
        min_length=1, max_length=4
    )
    mechanism_channels: list[str] = Field(min_length=1, max_length=12)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    source_hash: str = Field(min_length=8, max_length=128)


class PresentationFrameIndex(FrozenDomainModel):
    schema_version: Literal["presentation-frame-index-v2"] = "presentation-frame-index-v2"
    frame_id: str = Field(min_length=1, max_length=160)
    sequence: int = Field(ge=0)
    kind: PresentationFrameKind
    round: SimulationRound | None = None
    title: str = Field(min_length=1, max_length=120)
    spotlight_count: int = Field(ge=0, le=3)
    divergence_count: int = Field(ge=0)
    projection_roles: list[Literal["shared", "control", "treatment"]] = Field(min_length=1)
    source_hash: str = Field(min_length=8, max_length=128)


class PresentationTimeline(FrozenDomainModel):
    schema_version: Literal["presentation-timeline-v2"] = "presentation-timeline-v2"
    experiment_id: str = Field(min_length=1, max_length=160)
    product_version: str = Field(min_length=1, max_length=80)
    status: str = Field(min_length=1, max_length=80)
    current_frame_id: str
    frames: list[PresentationFrameIndex] = Field(min_length=1)
    event_markers: list[PresentationEventMarker] = Field(default_factory=list)
    first_divergence_frame_id: str | None = None
    available_modes: list[PresentationMode] = Field(min_length=1, max_length=2)
    source_world_hash: str = Field(min_length=8, max_length=128)
    generated_at: datetime

    @model_validator(mode="after")
    def timeline_is_consistent(self) -> PresentationTimeline:
        frame_ids = [item.frame_id for item in self.frames]
        sequences = [item.sequence for item in self.frames]
        if len(frame_ids) != len(set(frame_ids)):
            raise ValueError("presentation frame ids must be unique")
        if len(sequences) != len(set(sequences)) or sequences != sorted(sequences):
            raise ValueError("presentation frame sequences must be unique and ordered")
        if self.current_frame_id not in set(frame_ids):
            raise ValueError("current presentation frame is not in timeline")
        if len(self.available_modes) != len(set(self.available_modes)):
            raise ValueError("presentation modes must be unique")
        if PresentationMode.STORY in self.available_modes:
            raise ValueError("Presentation V2 reserves story mode for a later milestone")
        known_frames = set(frame_ids)
        if (
            self.first_divergence_frame_id is not None
            and self.first_divergence_frame_id not in known_frames
        ):
            raise ValueError("first divergence frame must exist in the timeline")
        marker_ids = [item.marker_id for item in self.event_markers]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError("presentation event marker ids must be unique")
        return self
