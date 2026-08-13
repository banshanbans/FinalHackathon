from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from simulation.models.presentation import (
    PresentationBranchProjection,
    PresentationCamera,
    PresentationDecisionMoment,
    PresentationFrame,
    PresentationFrameIndex,
    PresentationMapProjection,
    PresentationMode,
    PresentationNarrativeBeat,
    PresentationProvinceValue,
    PresentationSpotlight,
    PresentationSpotlightScore,
    PresentationSubjectRef,
    PresentationTimeline,
)
from simulation.models.v32 import EventIntensityV32, EventTriggerPoint, SimulationRound
from simulation.presentation_catalog import presentation_event_catalog


def map_projection() -> PresentationMapProjection:
    return PresentationMapProjection(
        mode="absolute",
        fill_metric="local_subsidy_intensity",
        unit="指数点",
        camera=PresentationCamera(longitude=104, latitude=35, zoom=3.2, pitch=18, bearing=0),
        enabled_overlays=["competition", "coordination"],
    )


def branch_projection(role: str) -> PresentationBranchProjection:
    return PresentationBranchProjection(
        branch_role=role,
        branch_id=f"branch-{role}",
        label="原始方案" if role == "control" else "干预方案",
        map_projection=map_projection(),
        province_values=[
            PresentationProvinceValue(province_code="11", value=2.5, data_quality="proxy"),
            PresentationProvinceValue(
                province_code="12", value=None, missing=True, data_quality="proxy"
            ),
        ],
        source_event_ids=[f"event-{role}"],
        source_hash=f"12345678-{role}",
    )


def frame(frame_id: str = "frame-round-province_initial") -> PresentationFrame:
    actor = PresentationSubjectRef(subject_type="province", subject_id="11", display_name="北京")
    moment = PresentationDecisionMoment(
        moment_id="moment-control-11",
        trace_id="trace-control-11",
        branch_role="control",
        branch_id="branch-control",
        round=SimulationRound.PROVINCE_INITIAL,
        actor=actor,
        objective="形成省级初始策略",
        actual_choice="保持资源守恒的政策组合",
        response_status="pending",
        evidence_refs=["trace:control-11"],
    )
    spotlight = PresentationSpotlight(
        spotlight_id="spotlight-control-11",
        rank=1,
        label="北京初始策略",
        primary_moment_id=moment.moment_id,
        branch_role="control",
        score=PresentationSpotlightScore(
            divergence=0,
            response=0,
            scarcity=15,
            action_change=5,
            state_change=0,
            evidence=10,
            total=30,
        ),
        narrative_beats=[
            PresentationNarrativeBeat(
                beat="focus", title="聚焦", detail="北京形成初始策略。", status="frozen"
            ),
            PresentationNarrativeBeat(
                beat="observe", title="观察", detail="财政空间已冻结。", status="frozen"
            ),
            PresentationNarrativeBeat(
                beat="action", title="行动", detail="实际组合已冻结。", status="frozen"
            ),
            PresentationNarrativeBeat(
                beat="response", title="回应", detail="等待下一轮回应。", status="pending"
            ),
        ],
        focus_subjects=[actor],
        evidence_refs=["trace:control-11"],
    )
    return PresentationFrame(
        frame_id=frame_id,
        sequence=1,
        kind="round",
        round=SimulationRound.PROVINCE_INITIAL,
        title="省级初始行动",
        summary="两个分支已同步形成首轮政策配置。",
        branch_projections={
            "control": branch_projection("control"),
            "treatment": branch_projection("treatment"),
        },
        decision_moments=[moment],
        spotlights=[spotlight],
        source_event_ids=["event-control", "event-treatment"],
        source_hash="12345678abcdef",
    )


def test_presentation_timeline_is_a_lightweight_ordered_index() -> None:
    current = frame()
    index = PresentationFrameIndex(
        frame_id=current.frame_id,
        sequence=current.sequence,
        kind=current.kind,
        round=current.round,
        title=current.title,
        spotlight_count=1,
        divergence_count=0,
        projection_roles=["control", "treatment"],
        source_hash=current.source_hash,
    )
    timeline = PresentationTimeline(
        experiment_id="exp-present",
        product_version="v3_2_m32",
        status="running",
        current_frame_id=current.frame_id,
        frames=[index],
        available_modes=[PresentationMode.LIVE],
        source_world_hash="abcdef1234567890",
        generated_at=datetime.now(UTC),
    )
    assert timeline.schema_version == "presentation-timeline-v2"
    assert not hasattr(timeline.frames[0], "province_values")


def test_round_frame_requires_both_branch_projections() -> None:
    current = frame().model_dump()
    current["branch_projections"].pop("treatment")
    with pytest.raises(ValidationError, match="either shared or both branch projections"):
        PresentationFrame.model_validate(current)


def test_branch_projection_rejects_cross_key_role() -> None:
    current = frame().model_dump()
    current["branch_projections"]["control"]["branch_role"] = "treatment"
    with pytest.raises(ValidationError, match="role does not match"):
        PresentationFrame.model_validate(current)


def test_presentation_frame_rejects_invented_missing_value() -> None:
    with pytest.raises(ValidationError, match="missing province values"):
        PresentationProvinceValue(province_code="11", value=0, missing=True, data_quality="proxy")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_presentation_province_value_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValidationError):
        PresentationProvinceValue(province_code="11", value=value, data_quality="proxy")


def test_presentation_timeline_rejects_story_mode_until_later_milestone() -> None:
    current = frame()
    index = PresentationFrameIndex(
        frame_id=current.frame_id,
        sequence=0,
        kind=current.kind,
        round=current.round,
        title=current.title,
        spotlight_count=1,
        divergence_count=0,
        projection_roles=["control", "treatment"],
        source_hash=current.source_hash,
    )
    with pytest.raises(ValidationError, match="reserves story mode"):
        PresentationTimeline(
            experiment_id="exp-present",
            product_version="v3_2_m32",
            status="completed",
            current_frame_id=current.frame_id,
            frames=[index],
            available_modes=["story", "compare"],
            source_world_hash="abcdef1234567890",
            generated_at=datetime.now(UTC),
        )


def test_presentation_event_catalog_exposes_the_frozen_capability_matrix() -> None:
    catalog = presentation_event_catalog()
    assert catalog.schema_version == "presentation-event-catalog-v1"
    assert catalog.mechanism_version == "nev-policy-env-v6"
    assert {item.template_id for item in catalog.templates} == {
        "battery_node_upgrade_sichuan",
        "intelligent_driving_upgrade",
        "l3_enterprise_liability_increase",
        "oil_price_fall",
        "oil_price_rise",
    }
    assert all(item.trigger_points == list(EventTriggerPoint) for item in catalog.templates)
    assert all(item.supported_intensities == list(EventIntensityV32) for item in catalog.templates)
    assert all(item.branch_scopes == ["both", "treatment_only"] for item in catalog.templates)
    assert all("不代表现实" in item.disclaimer for item in catalog.templates)
