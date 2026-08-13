from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from simulation.models.presentation import (
    PresentationCamera,
    PresentationFrame,
    PresentationFrameKind,
    PresentationMapProjection,
    PresentationMode,
    PresentationProvinceValue,
    PresentationStoryChapter,
    PresentationTimeline,
)
from simulation.models.v32 import EventIntensityV32, EventTriggerPoint, SimulationRound
from simulation.presentation_catalog import presentation_event_catalog


def map_projection() -> PresentationMapProjection:
    return PresentationMapProjection(
        mode="difference",
        fill_metric="local_subsidy_intensity",
        unit="指数点",
        camera=PresentationCamera(
            longitude=104.0,
            latitude=35.0,
            zoom=3.2,
            pitch=18,
            bearing=0,
        ),
        enabled_overlays=["competition", "coordination"],
    )


def frame(frame_id: str = "frame-province-initial") -> PresentationFrame:
    return PresentationFrame(
        frame_id=frame_id,
        sequence=1,
        kind=PresentationFrameKind.ROUND,
        branch_id="control",
        round=SimulationRound.PROVINCE_INITIAL,
        title="省级初始行动",
        summary="31 个省份已形成首轮政策配置。",
        map_projection=map_projection(),
        province_values=[
            PresentationProvinceValue(
                province_code="11",
                value=2.5,
                data_quality="proxy",
            ),
            PresentationProvinceValue(
                province_code="12",
                value=None,
                missing=True,
                data_quality="proxy",
            ),
        ],
        source_event_ids=["event-1"],
        source_hash="12345678abcdef",
    )


def test_presentation_timeline_accepts_ordered_frozen_frames() -> None:
    current = frame()
    timeline = PresentationTimeline(
        experiment_id="exp-present",
        product_version="v3_2_m32",
        status="running",
        current_frame_id=current.frame_id,
        frames=[current],
        story_chapters=[
            PresentationStoryChapter(
                chapter_id="chapter-policy",
                title="政策输入",
                summary="双分支从同一基线派生。",
                frame_ids=[current.frame_id],
                evidence_refs=["policy:control"],
            )
        ],
        available_modes=[PresentationMode.LIVE, PresentationMode.STORY],
        source_world_hash="abcdef1234567890",
        generated_at=datetime.now(UTC),
    )
    assert timeline.frames[0].frozen is True
    assert timeline.frames[0].province_values[1].missing is True


def test_presentation_frame_rejects_invented_missing_value() -> None:
    with pytest.raises(ValidationError, match="missing province values"):
        PresentationProvinceValue(
            province_code="11",
            value=0,
            missing=True,
            data_quality="proxy",
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_presentation_province_value_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValidationError):
        PresentationProvinceValue(
            province_code="11",
            value=value,
            data_quality="proxy",
        )


def test_presentation_round_frame_requires_round() -> None:
    with pytest.raises(ValidationError, match="round frames require"):
        PresentationFrame(
            frame_id="invalid-round",
            sequence=0,
            kind="round",
            title="错误帧",
            summary="缺少轮次。",
            map_projection=map_projection(),
            source_hash="12345678",
        )


def test_presentation_timeline_rejects_unknown_story_frame() -> None:
    current = frame()
    with pytest.raises(ValidationError, match="unknown presentation frame"):
        PresentationTimeline(
            experiment_id="exp-present",
            product_version="v3_2_m32",
            status="completed",
            current_frame_id=current.frame_id,
            frames=[current],
            story_chapters=[
                PresentationStoryChapter(
                    chapter_id="chapter-result",
                    title="政策结论",
                    summary="结果已形成。",
                    frame_ids=["missing-frame"],
                    evidence_refs=["comparison:exp-present"],
                )
            ],
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
