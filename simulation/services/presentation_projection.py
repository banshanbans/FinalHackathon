from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import fmean

from simulation.catalog import automaker_catalog, event_scenario_catalog, policy_region_catalog
from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.presentation import (
    PresentationCamera,
    PresentationEventMarker,
    PresentationFrame,
    PresentationFrameKind,
    PresentationKeyChange,
    PresentationMapProjection,
    PresentationMetricSummary,
    PresentationMode,
    PresentationOverlayKind,
    PresentationOverlayRecord,
    PresentationProvinceValue,
    PresentationStoryChapter,
    PresentationTimeline,
)
from simulation.models.v32 import (
    BranchRuntimeState,
    ComparisonResultV6,
    EventTriggerPoint,
    EventV6,
    SimulationRound,
    V32ExperimentStatus,
    WorldStateV6,
)
from simulation.services.replay import canonical_hash

ROUND_TITLES = {
    SimulationRound.PROVINCE_INITIAL: "省级初始行动",
    SimulationRound.AUTOMAKER_INITIAL: "车企初步 Top-K",
    SimulationRound.PROVINCE_REVISION: "省级竞争反制与协同",
    SimulationRound.AUTOMAKER_NEGOTIATION: "车企报价与反报价",
    SimulationRound.PROVINCE_COUNTER_RESPONSE: "省级反报价回应",
    SimulationRound.AUTOMAKER_FINAL: "车企最终确认与重配",
    SimulationRound.ENVIRONMENT_SETTLEMENT: "环境结算",
}

ROUND_SUMMARIES = {
    SimulationRound.PROVINCE_INITIAL: "31 个省份已形成首轮政策配置。",
    SimulationRound.AUTOMAKER_INITIAL: "10 家车企已完成全国资源初步配置。",
    SimulationRound.PROVINCE_REVISION: "省级竞争反制、合作提议与回应已经冻结。",
    SimulationRound.AUTOMAKER_NEGOTIATION: "省企报价、回应与反报价已经冻结。",
    SimulationRound.PROVINCE_COUNTER_RESPONSE: "省级反报价接受或拒绝结果已经冻结。",
    SimulationRound.AUTOMAKER_FINAL: "车企最终全国资源配置与重配结果已经冻结。",
    SimulationRound.ENVIRONMENT_SETTLEMENT: "确定性环境已完成双分支结算。",
}

METRIC_LABELS = {
    "regional_development_gap": "区域发展差距",
    "central_fiscal_burden": "中央财政负担",
    "local_fiscal_pressure": "地方财政压力",
    "nev_demand": "新能源汽车需求",
    "new_investment_concentration": "新增投资集中度",
    "industrial_agglomeration": "产业集聚度",
}

TRIGGER_POSITIONS = {
    EventTriggerPoint.BEFORE_PROVINCE_INITIAL: 0.18,
    EventTriggerPoint.AFTER_PROVINCE_INITIAL: 0.32,
    EventTriggerPoint.AFTER_AUTOMAKER_INITIAL: 0.45,
}


def _camera() -> PresentationCamera:
    return PresentationCamera(
        longitude=104.0,
        latitude=35.0,
        zoom=3.2,
        pitch=18,
        bearing=0,
    )


class PresentationProjectionService:
    """Build immutable presentation frames from committed M32 facts and Replay events."""

    def __init__(
        self,
        world: WorldStateV6,
        events: list[EventV6],
        comparison: ComparisonResultV6 | None,
    ) -> None:
        self.world = world
        self.events = events
        self.comparison = comparison
        self.province_catalog = policy_region_catalog()

    def build_timeline(self) -> PresentationTimeline:
        frames = self._frames()
        modes = [PresentationMode.LIVE]
        chapters: list[PresentationStoryChapter] = []
        if self.world.status is V32ExperimentStatus.COMPLETED and self.comparison is not None:
            modes.extend([PresentationMode.STORY, PresentationMode.COMPARE])
            chapters = self._story_chapters(frames)
        generated_at = self.events[-1].timestamp if self.events else datetime.now(UTC)
        return PresentationTimeline(
            experiment_id=self.world.experiment_id,
            product_version=self.world.product_version,
            status=self.world.status.value,
            current_frame_id=frames[-1].frame_id,
            frames=frames,
            event_markers=self._event_markers(),
            story_chapters=chapters,
            available_modes=modes,
            source_world_hash=canonical_hash(self.world),
            generated_at=generated_at,
        )

    def get_frame(self, frame_id: str) -> PresentationFrame:
        frame = next((item for item in self._frames() if item.frame_id == frame_id), None)
        if frame is None:
            raise KeyError(f"presentation frame not found: {frame_id}")
        return frame

    def _frames(self) -> list[PresentationFrame]:
        frames = [self._setup_frame()]
        if self.world.baseline is None or not self.world.branches:
            return frames
        frames.append(self._baseline_frame(sequence=len(frames)))
        event_plan = self.world.design.event_plan if self.world.design else None
        if event_plan and event_plan.trigger_point is EventTriggerPoint.BEFORE_PROVINCE_INITIAL:
            frames.append(self._event_frame(sequence=len(frames)))
        treatment = self.world.branches["treatment"]
        for round_name in SimulationRound:
            if round_name not in treatment.completed_rounds:
                break
            frames.append(self._round_frame(treatment, round_name, sequence=len(frames)))
            if event_plan and (
                event_plan.trigger_point is EventTriggerPoint.AFTER_PROVINCE_INITIAL
                and round_name is SimulationRound.PROVINCE_INITIAL
                or event_plan.trigger_point is EventTriggerPoint.AFTER_AUTOMAKER_INITIAL
                and round_name is SimulationRound.AUTOMAKER_INITIAL
            ):
                frames.append(self._event_frame(sequence=len(frames)))
        if self.comparison is not None:
            frames.append(self._comparison_frame(sequence=len(frames)))
        return frames

    def _setup_frame(self) -> PresentationFrame:
        interpretation = self.world.interpretation
        source_ids = self._source_event_ids(
            event_types={"interpretation.generated", "interpretation.confirmed", "design.confirmed"}
        )
        policy = interpretation.executable_policy
        metrics = [
            PresentationMetricSummary(
                metric_id=f"central-share-{region}",
                label=label,
                value=value * 100,
                unit="%",
                evidence_refs=[f"policy:{policy.policy_id}"],
            )
            for region, label, value in (
                ("west", "西部中央承担", policy.west_central_share),
                ("central", "中部中央承担", policy.central_central_share),
                ("east", "东部中央承担", policy.east_central_share),
            )
        ]
        return self._frame(
            frame_id="frame-setup-policy",
            sequence=0,
            kind=PresentationFrameKind.SETUP,
            title="政策输入",
            summary=interpretation.public_summary,
            fill_metric="central_share",
            unit="%",
            province_values=[],
            overlays=[],
            metrics=metrics,
            evidence_refs=[f"policy:{policy.policy_id}"],
            source_event_ids=source_ids,
            panel_refs=["panel:policy", "panel:experiment-design"],
        )

    def _baseline_frame(self, *, sequence: int) -> PresentationFrame:
        assert self.world.baseline is not None
        treatment = self.world.branches["treatment"]
        values = {
            code: treatment.policy.share_for_region(self.province_catalog[code].policy_region.value)
            * 100
            for code in MAINLAND_PROVINCE_CODES
        }
        return self._frame(
            frame_id="frame-baseline-frozen",
            sequence=sequence,
            kind=PresentationFrameKind.SETUP,
            title="方案冻结",
            summary="两个方案从同一代理数据基线与不可变 Checkpoint 派生。",
            fill_metric="central_share",
            unit="%",
            province_values=self._province_values(values),
            overlays=self._event_overlays(),
            metrics=[],
            evidence_refs=[f"checkpoint:{self.world.baseline.checkpoint_id}"],
            source_event_ids=self._source_event_ids(
                event_types={"baseline.confirmed", "branches.created"}
            ),
            panel_refs=["panel:baseline", "panel:methods"],
        )

    def _round_frame(
        self,
        branch: BranchRuntimeState,
        round_name: SimulationRound,
        *,
        sequence: int,
    ) -> PresentationFrame:
        if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT:
            kind = PresentationFrameKind.SETTLEMENT
            frame_round = None
        else:
            kind = PresentationFrameKind.ROUND
            frame_round = round_name
        values, fill_metric, unit = self._round_values(branch, round_name)
        overlays = self._round_overlays(branch, round_name)
        metrics = (
            self._settlement_metrics(branch)
            if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT
            else []
        )
        evidence_refs = self._round_evidence_refs(branch, round_name)
        return self._frame(
            frame_id=f"frame-treatment-{round_name.value}",
            sequence=sequence,
            kind=kind,
            branch_id=branch.branch_id,
            round_name=frame_round,
            title=ROUND_TITLES[round_name],
            summary=ROUND_SUMMARIES[round_name],
            fill_metric=fill_metric,
            unit=unit,
            province_values=self._province_values(values),
            overlays=overlays,
            metrics=metrics,
            evidence_refs=evidence_refs,
            source_event_ids=self._source_event_ids(round_name=round_name),
            panel_refs=self._round_panel_refs(round_name),
        )

    def _event_frame(self, *, sequence: int) -> PresentationFrame:
        assert self.world.design is not None and self.world.design.event_plan is not None
        plan = self.world.design.event_plan
        source_ids = self._source_event_ids(event_types={"design.confirmed"})
        boundary_round = {
            EventTriggerPoint.BEFORE_PROVINCE_INITIAL: None,
            EventTriggerPoint.AFTER_PROVINCE_INITIAL: SimulationRound.PROVINCE_INITIAL,
            EventTriggerPoint.AFTER_AUTOMAKER_INITIAL: SimulationRound.AUTOMAKER_INITIAL,
        }[plan.trigger_point]
        if boundary_round is not None:
            source_ids = list(
                dict.fromkeys([*source_ids, *self._source_event_ids(round_name=boundary_round)])
            )
        return self._frame(
            frame_id=f"frame-event-{plan.event_plan_id}",
            sequence=sequence,
            kind=PresentationFrameKind.EVENT,
            title=plan.name,
            summary="冻结事件情景进入后续主体上下文与确定性环境，不代表现实预测。",
            fill_metric="event_exposure",
            unit="模拟指数",
            province_values=[],
            overlays=self._event_overlays(),
            metrics=[],
            evidence_refs=plan.evidence_refs,
            source_event_ids=source_ids,
            panel_refs=["panel:event", "panel:methods"],
        )

    def _comparison_frame(self, *, sequence: int) -> PresentationFrame:
        assert self.comparison is not None
        values = {
            item.province_code: item.development_delta for item in self.comparison.province_deltas
        }
        metrics = [
            PresentationMetricSummary(
                metric_id=metric_id,
                label=METRIC_LABELS[metric_id],
                value=value.treatment,
                unit="模拟指数",
                delta=value.delta,
                evidence_refs=[f"comparison:{self.world.experiment_id}"],
            )
            for metric_id, value in self.comparison.national_metrics.items()
        ]
        overlays = self._round_overlays(
            self.world.branches["treatment"], SimulationRound.ENVIRONMENT_SETTLEMENT
        )
        return self._frame(
            frame_id="frame-comparison-result",
            sequence=sequence,
            kind=PresentationFrameKind.COMPARISON,
            title="结果复盘",
            summary=self.comparison.conclusion,
            fill_metric="development_delta",
            unit="模拟指数点",
            province_values=self._province_values(values),
            overlays=overlays,
            metrics=metrics,
            evidence_refs=[f"comparison:{self.world.experiment_id}"],
            source_event_ids=self._source_event_ids(event_types={"comparison.completed"}),
            panel_refs=["panel:result", "panel:methods"],
            difference=True,
        )

    def _frame(
        self,
        *,
        frame_id: str,
        sequence: int,
        kind: PresentationFrameKind,
        title: str,
        summary: str,
        fill_metric: str,
        unit: str,
        province_values: list[PresentationProvinceValue],
        overlays: list[PresentationOverlayRecord],
        metrics: list[PresentationMetricSummary],
        evidence_refs: list[str],
        source_event_ids: list[str],
        panel_refs: list[str],
        branch_id: str | None = None,
        round_name: SimulationRound | None = None,
        difference: bool = False,
    ) -> PresentationFrame:
        key_changes = self._key_changes(province_values, unit)
        focus_subjects = [
            f"province:{item.province_code}" for item in self._rank_values(province_values)
        ]
        source_payload = {
            "frame_id": frame_id,
            "branch_id": branch_id,
            "round": round_name,
            "province_values": province_values,
            "overlay_records": overlays,
            "metric_summary": metrics,
            "evidence_refs": evidence_refs,
            "source_event_ids": source_event_ids,
        }
        return PresentationFrame(
            frame_id=frame_id,
            sequence=sequence,
            kind=kind,
            branch_id=branch_id,
            round=round_name,
            title=title,
            summary=summary,
            map_projection=PresentationMapProjection(
                mode="difference" if difference else "absolute",
                fill_metric=fill_metric,
                unit=unit,
                camera=_camera(),
                enabled_overlays=list(dict.fromkeys(item.kind for item in overlays)),
            ),
            province_values=province_values,
            overlay_records=overlays,
            key_changes=key_changes,
            metric_summary=metrics,
            focus_subjects=focus_subjects,
            panel_refs=panel_refs,
            evidence_refs=list(dict.fromkeys(evidence_refs))[:16],
            source_event_ids=source_event_ids,
            source_hash=canonical_hash(source_payload),
        )

    def _round_values(
        self, branch: BranchRuntimeState, round_name: SimulationRound
    ) -> tuple[dict[str, float], str, str]:
        if round_name is SimulationRound.PROVINCE_INITIAL:
            return (
                {
                    code: action.overall_support_intensity * 100
                    for code, action in branch.province_initial_actions.items()
                },
                "local_subsidy_intensity",
                "模拟指数",
            )
        if round_name is SimulationRound.PROVINCE_REVISION:
            return (
                {
                    code: action.overall_support_intensity * 100
                    for code, action in branch.province_final_actions.items()
                },
                "local_subsidy_intensity",
                "模拟指数",
            )
        if round_name is SimulationRound.PROVINCE_COUNTER_RESPONSE:
            accepted = {code: 0.0 for code in MAINLAND_PROVINCE_CODES}
            for response in branch.province_counter_offer_responses:
                accepted[response.province_code] += float(response.decision == "accept")
            return accepted, "accepted_counteroffers", "项"
        if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT:
            return (
                {code: state.development_index for code, state in branch.province_states.items()},
                "province_nev_development_index",
                "模拟指数",
            )
        actions = {
            SimulationRound.AUTOMAKER_INITIAL: branch.automaker_initial_actions,
            SimulationRound.AUTOMAKER_NEGOTIATION: branch.automaker_negotiation_actions,
            SimulationRound.AUTOMAKER_FINAL: branch.automaker_final_actions,
        }[round_name]
        by_province: dict[str, list[float]] = {code: [] for code in MAINLAND_PROVINCE_CODES}
        for action in actions.values():
            for item in action.province_market_actions:
                by_province[item.province_code].append(item.sales_investment_intensity * 100)
        return (
            {code: fmean(values) for code, values in by_province.items() if values},
            "automaker_sales_activity",
            "模拟指数",
        )

    def _province_values(self, values: dict[str, float]) -> list[PresentationProvinceValue]:
        return [
            PresentationProvinceValue(
                province_code=code,
                value=round(values[code], 4) if code in values else None,
                missing=code not in values,
                data_quality="scenario_assumption",
            )
            for code in MAINLAND_PROVINCE_CODES
        ]

    def _round_overlays(
        self, branch: BranchRuntimeState, round_name: SimulationRound
    ) -> list[PresentationOverlayRecord]:
        if round_name is SimulationRound.AUTOMAKER_INITIAL:
            return self._competition_overlays(branch)
        if round_name is SimulationRound.PROVINCE_REVISION:
            return self._limit_overlays(
                [*self._coordination_overlays(branch), *self._competition_overlays(branch)]
            )
        if round_name is SimulationRound.AUTOMAKER_NEGOTIATION:
            return self._negotiation_overlays(branch)
        if round_name is SimulationRound.PROVINCE_COUNTER_RESPONSE:
            return self._counter_response_overlays(branch)
        if round_name is SimulationRound.AUTOMAKER_FINAL:
            return self._limit_overlays(
                [*self._topk_overlays(branch), *self._enterprise_match_overlays(branch)]
            )
        if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT:
            return self._limit_overlays(
                [*self._event_overlays(), *self._coordination_overlays(branch)]
            )
        return []

    def _competition_overlays(self, branch: BranchRuntimeState) -> list[PresentationOverlayRecord]:
        records = sorted(
            branch.competition_outcomes, key=lambda item: (-item.loss_index, item.outcome_id)
        )
        return self._limit_overlays(
            PresentationOverlayRecord(
                overlay_id=f"overlay-{item.outcome_id}",
                kind=PresentationOverlayKind.COMPETITION,
                source_subject=f"province:{item.winner_province_code}",
                target_subject=f"province:{item.loser_province_code}",
                status="competition_loss",
                weight=item.loss_index,
                label=(
                    f"{self.province_catalog[item.winner_province_code].short_name} → "
                    f"{self.province_catalog[item.loser_province_code].short_name} 竞争挤出"
                ),
                style_semantic="competition",
                evidence_refs=[f"competition:{item.outcome_id}", *item.evidence_refs][:8],
            )
            for item in records
        )

    def _coordination_overlays(self, branch: BranchRuntimeState) -> list[PresentationOverlayRecord]:
        records = sorted(
            branch.coordination_records,
            key=lambda item: (item.status != "matched", -item.contribution, item.coordination_id),
        )
        return self._limit_overlays(
            PresentationOverlayRecord(
                overlay_id=f"overlay-{item.coordination_id}",
                kind=PresentationOverlayKind.COORDINATION,
                source_subject=f"province:{item.left_province_code}",
                target_subject=f"province:{item.right_province_code}",
                status=item.status,
                weight=item.contribution,
                label=item.summary[:160],
                style_semantic="coordination" if item.status == "matched" else "neutral",
                evidence_refs=[f"match:{item.coordination_id}", *item.evidence_refs][:8],
            )
            for item in records
        )

    def _negotiation_overlays(self, branch: BranchRuntimeState) -> list[PresentationOverlayRecord]:
        records = sorted(
            branch.province_enterprise_offers, key=lambda item: (item.priority, item.offer_id)
        )
        return self._limit_overlays(
            PresentationOverlayRecord(
                overlay_id=f"overlay-{item.offer_id}",
                kind=PresentationOverlayKind.NEGOTIATION,
                source_subject=f"province:{item.source_province_code}",
                target_subject=f"automaker:{item.target_automaker_id}",
                status="offered",
                weight=round(item.channel_commitment_share + item.industry_coordination_share, 4),
                label=(
                    f"{self.province_catalog[item.source_province_code].short_name} → "
                    f"{automaker_catalog()[item.target_automaker_id].display_name} 省企报价"
                ),
                style_semantic="policy",
                evidence_refs=[f"offer:{item.offer_id}", *item.evidence_refs][:8],
            )
            for item in records
        )

    def _counter_response_overlays(
        self, branch: BranchRuntimeState
    ) -> list[PresentationOverlayRecord]:
        records = sorted(
            branch.province_counter_offer_responses,
            key=lambda item: (item.decision != "accept", item.response_id),
        )
        offer_by_id = {item.counter_offer_id: item for item in branch.automaker_counter_offers}
        overlays: list[PresentationOverlayRecord] = []
        for item in records:
            offer = offer_by_id[item.counter_offer_id]
            overlays.append(
                PresentationOverlayRecord(
                    overlay_id=f"overlay-{item.response_id}",
                    kind=PresentationOverlayKind.NEGOTIATION,
                    source_subject=f"province:{item.province_code}",
                    target_subject=f"automaker:{offer.automaker_id}",
                    status=item.decision,
                    weight=1.0 if item.decision == "accept" else 0.0,
                    label=(
                        f"{self.province_catalog[item.province_code].short_name}"
                        f"{('接受' if item.decision == 'accept' else '拒绝')}反报价"
                    ),
                    style_semantic="evidence" if item.decision == "accept" else "neutral",
                    evidence_refs=[f"counterresponse:{item.response_id}", *item.evidence_refs][:8],
                )
            )
        return self._limit_overlays(overlays)

    def _topk_overlays(self, branch: BranchRuntimeState) -> list[PresentationOverlayRecord]:
        records = sorted(branch.top_k_reallocations, key=lambda item: item.reallocation_id)
        return self._limit_overlays(
            PresentationOverlayRecord(
                overlay_id=f"overlay-{item.reallocation_id}",
                kind=PresentationOverlayKind.TOPK,
                source_subject=f"province:{item.released_province_code}",
                target_subject=f"province:{item.recipient_province_code}",
                status="reallocated",
                weight=1.0,
                label=(
                    f"{automaker_catalog()[item.automaker_id].display_name} "
                    f"{self.province_catalog[item.released_province_code].short_name} → "
                    f"{self.province_catalog[item.recipient_province_code].short_name}"
                ),
                style_semantic="policy",
                evidence_refs=[f"topk:{item.reallocation_id}", *item.evidence_refs][:8],
            )
            for item in records
        )

    def _enterprise_match_overlays(
        self, branch: BranchRuntimeState
    ) -> list[PresentationOverlayRecord]:
        records = sorted(
            branch.province_enterprise_matches,
            key=lambda item: (item.status != "matched", item.match_id),
        )
        return self._limit_overlays(
            PresentationOverlayRecord(
                overlay_id=f"overlay-{item.match_id}",
                kind=PresentationOverlayKind.AUTOMAKER,
                source_subject=f"province:{item.province_code}",
                target_subject=f"automaker:{item.automaker_id}",
                status=item.status,
                weight=round(item.channel_contribution + item.industry_contribution, 4),
                label=item.summary[:160],
                style_semantic="evidence" if item.status == "matched" else "neutral",
                evidence_refs=[f"match:{item.match_id}", *item.evidence_refs][:8],
            )
            for item in records
        )

    def _event_overlays(self) -> list[PresentationOverlayRecord]:
        if self.world.design is None or self.world.design.event_plan is None:
            return []
        plan = self.world.design.event_plan
        catalog = event_scenario_catalog()
        template = next(
            (item for key, item in catalog.items() if key.value == plan.template_id),
            None,
        )
        targets = template.target_province_codes if template else []
        target_subject = f"province:{targets[0]}" if len(targets) == 1 else None
        return [
            PresentationOverlayRecord(
                overlay_id=f"overlay-event-{plan.event_plan_id}",
                kind=PresentationOverlayKind.EVENT,
                source_subject=f"event:{plan.event_plan_id}",
                target_subject=target_subject,
                status=plan.intensity.value,
                weight=plan.intensity.magnitude,
                label=plan.name[:160],
                style_semantic="event",
                evidence_refs=plan.evidence_refs,
            )
        ]

    @staticmethod
    def _limit_overlays(
        records: Iterable[PresentationOverlayRecord],
    ) -> list[PresentationOverlayRecord]:
        return list(records)[:10]

    def _settlement_metrics(self, branch: BranchRuntimeState) -> list[PresentationMetricSummary]:
        return [
            PresentationMetricSummary(
                metric_id=metric_id,
                label=label,
                value=getattr(branch.national_metrics, metric_id),
                unit="模拟指数",
                evidence_refs=[f"metric:{branch.branch_id}:{metric_id}"],
            )
            for metric_id, label in METRIC_LABELS.items()
        ]

    def _round_evidence_refs(
        self, branch: BranchRuntimeState, round_name: SimulationRound
    ) -> list[str]:
        if round_name is SimulationRound.PROVINCE_INITIAL:
            return [
                f"action:{item.action_id}" for item in branch.province_initial_actions.values()
            ][:16]
        if round_name is SimulationRound.PROVINCE_REVISION:
            return [f"action:{item.action_id}" for item in branch.province_final_actions.values()][
                :16
            ]
        if round_name is SimulationRound.PROVINCE_COUNTER_RESPONSE:
            return [
                f"counterresponse:{item.response_id}"
                for item in branch.province_counter_offer_responses
            ][:16]
        if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT:
            return [f"metric:{branch.branch_id}:{metric_id}" for metric_id in METRIC_LABELS]
        actions = {
            SimulationRound.AUTOMAKER_INITIAL: branch.automaker_initial_actions,
            SimulationRound.AUTOMAKER_NEGOTIATION: branch.automaker_negotiation_actions,
            SimulationRound.AUTOMAKER_FINAL: branch.automaker_final_actions,
        }[round_name]
        return [f"action:{item.action_id}" for item in actions.values()][:16]

    @staticmethod
    def _round_panel_refs(round_name: SimulationRound) -> list[str]:
        return {
            SimulationRound.PROVINCE_INITIAL: ["panel:provinces"],
            SimulationRound.AUTOMAKER_INITIAL: ["panel:automakers", "panel:competition"],
            SimulationRound.PROVINCE_REVISION: ["panel:competition", "panel:coordination"],
            SimulationRound.AUTOMAKER_NEGOTIATION: ["panel:negotiation"],
            SimulationRound.PROVINCE_COUNTER_RESPONSE: ["panel:negotiation"],
            SimulationRound.AUTOMAKER_FINAL: ["panel:automakers", "panel:topk"],
            SimulationRound.ENVIRONMENT_SETTLEMENT: ["panel:result", "panel:methods"],
        }[round_name]

    def _source_event_ids(
        self,
        *,
        event_types: set[str] | None = None,
        round_name: SimulationRound | None = None,
    ) -> list[str]:
        return [
            item.event_id
            for item in self.events
            if (event_types is None or item.type in event_types)
            and (round_name is None or item.round is round_name)
        ]

    def _event_markers(self) -> list[PresentationEventMarker]:
        if self.world.design is None or self.world.design.event_plan is None:
            return []
        plan = self.world.design.event_plan
        catalog = event_scenario_catalog()
        template = next(
            (item for key, item in catalog.items() if key.value == plan.template_id),
            None,
        )
        family = template.family.value if template else "scenario"
        payload = {
            "plan": plan,
            "design_event_ids": self._source_event_ids(event_types={"design.confirmed"}),
        }
        return [
            PresentationEventMarker(
                marker_id=f"marker-{plan.event_plan_id}",
                event_plan_id=plan.event_plan_id,
                template_id=plan.template_id,
                title=plan.name[:120],
                family=family,
                intensity=plan.intensity,
                trigger_point=plan.trigger_point,
                timeline_position=TRIGGER_POSITIONS[plan.trigger_point],
                branch_scope=plan.branch_scope,
                advance_notice=plan.advance_notice,
                affected_subjects=plan.affected_subjects,
                mechanism_channels=plan.mechanism_channels,
                evidence_refs=plan.evidence_refs,
                source_hash=canonical_hash(payload),
            )
        ]

    def _key_changes(
        self, province_values: list[PresentationProvinceValue], unit: str
    ) -> list[PresentationKeyChange]:
        return [
            PresentationKeyChange(
                change_id=f"change-{item.province_code}",
                title=self.province_catalog[item.province_code].short_name,
                detail=f"当前帧显示值 {item.value:.2f} {unit}。",
                semantic="result",
                evidence_refs=[],
            )
            for item in self._rank_values(province_values)
        ]

    @staticmethod
    def _rank_values(
        province_values: list[PresentationProvinceValue],
    ) -> list[PresentationProvinceValue]:
        return sorted(
            (item for item in province_values if item.value is not None),
            key=lambda item: (-abs(item.value or 0), item.province_code),
        )[:3]

    def _story_chapters(self, frames: list[PresentationFrame]) -> list[PresentationStoryChapter]:
        known = {item.frame_id for item in frames}

        def existing(*frame_ids: str) -> list[str]:
            return [frame_id for frame_id in frame_ids if frame_id in known]

        return [
            PresentationStoryChapter(
                chapter_id="chapter-policy-input",
                title="政策输入",
                summary="政策输入、同源基线与双分支方案完成冻结。",
                frame_ids=existing("frame-setup-policy", "frame-baseline-frozen"),
                evidence_refs=[f"checkpoint:{self.world.baseline.checkpoint_id}"],
            ),
            PresentationStoryChapter(
                chapter_id="chapter-enterprise-feedback",
                title="企业反馈",
                summary="车企在全国范围形成初步 Top-K 与明确省域行动。",
                frame_ids=existing("frame-treatment-automaker_initial"),
                evidence_refs=["panel:automakers"],
            ),
            PresentationStoryChapter(
                chapter_id="chapter-province-coordination",
                title="省级互动",
                summary="省份基于观察、竞争与协同上下文自主调整。",
                frame_ids=existing("frame-treatment-province_revision"),
                evidence_refs=["panel:coordination"],
            ),
            PresentationStoryChapter(
                chapter_id="chapter-resource-reallocation",
                title="资源重配",
                summary="谈判、反报价与最终确认改变全国资源分布。",
                frame_ids=existing(
                    "frame-treatment-automaker_negotiation",
                    "frame-treatment-province_counter_response",
                    "frame-treatment-automaker_final",
                ),
                evidence_refs=["panel:negotiation"],
            ),
            PresentationStoryChapter(
                chapter_id="chapter-policy-conclusion",
                title="政策结论",
                summary="确定性环境结算并形成同源 A/B 结果。",
                frame_ids=existing(
                    "frame-treatment-environment_settlement", "frame-comparison-result"
                ),
                evidence_refs=[f"comparison:{self.world.experiment_id}"],
            ),
        ]
