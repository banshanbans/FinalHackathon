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
    schema_version: Literal["presentation-overlay-record-v1"] = "presentation-overlay-record-v1"
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


class PresentationFrame(FrozenDomainModel):
    schema_version: Literal["presentation-frame-v1"] = "presentation-frame-v1"
    frame_id: str = Field(min_length=1, max_length=160)
    sequence: int = Field(ge=0)
    kind: PresentationFrameKind
    branch_id: str | None = Field(default=None, max_length=160)
    round: SimulationRound | None = None
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=280)
    frozen: Literal[True] = True
    map_projection: PresentationMapProjection
    province_values: list[PresentationProvinceValue] = Field(default_factory=list, max_length=31)
    overlay_records: list[PresentationOverlayRecord] = Field(default_factory=list)
    key_changes: list[PresentationKeyChange] = Field(default_factory=list, max_length=3)
    metric_summary: list[PresentationMetricSummary] = Field(default_factory=list, max_length=12)
    focus_subjects: list[str] = Field(default_factory=list, max_length=16)
    panel_refs: list[str] = Field(default_factory=list, max_length=16)
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)
    source_event_ids: list[str] = Field(default_factory=list, max_length=64)
    source_hash: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def frame_is_consistent(self) -> PresentationFrame:
        codes = [item.province_code for item in self.province_values]
        if len(codes) != len(set(codes)):
            raise ValueError("presentation frame contains duplicate province values")
        if self.kind is PresentationFrameKind.ROUND and self.round is None:
            raise ValueError("round frames require a simulation round")
        if self.kind is not PresentationFrameKind.ROUND and self.round is not None:
            raise ValueError("only round frames may set round")
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise ValueError("presentation frame source events must be unique")
        return self


class PresentationEventMarker(FrozenDomainModel):
    schema_version: Literal["presentation-event-marker-v1"] = "presentation-event-marker-v1"
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


class PresentationStoryChapter(FrozenDomainModel):
    chapter_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=280)
    frame_ids: list[str] = Field(min_length=1, max_length=8)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)


class PresentationTimeline(FrozenDomainModel):
    schema_version: Literal["presentation-timeline-v1"] = "presentation-timeline-v1"
    experiment_id: str = Field(min_length=1, max_length=160)
    product_version: str = Field(min_length=1, max_length=80)
    status: str = Field(min_length=1, max_length=80)
    current_frame_id: str
    frames: list[PresentationFrame] = Field(min_length=1)
    event_markers: list[PresentationEventMarker] = Field(default_factory=list)
    story_chapters: list[PresentationStoryChapter] = Field(default_factory=list, max_length=8)
    available_modes: list[PresentationMode] = Field(min_length=1, max_length=3)
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
        known_frames = set(frame_ids)
        for chapter in self.story_chapters:
            if not set(chapter.frame_ids) <= known_frames:
                raise ValueError("story chapter references an unknown presentation frame")
        marker_ids = [item.marker_id for item in self.event_markers]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError("presentation event marker ids must be unique")
        return self
