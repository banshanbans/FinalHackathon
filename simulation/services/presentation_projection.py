from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import fmean

from simulation.catalog import automaker_catalog, event_scenario_catalog, policy_region_catalog
from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.presentation import (
    DecisionOptionEvaluation,
    PresentationActualResponse,
    PresentationBranchProjection,
    PresentationCamera,
    PresentationDecisionMoment,
    PresentationDivergence,
    PresentationEventMarker,
    PresentationFrame,
    PresentationFrameIndex,
    PresentationFrameKind,
    PresentationGameThread,
    PresentationKeyChange,
    PresentationMapProjection,
    PresentationMetricSummary,
    PresentationMode,
    PresentationNarrativeBeat,
    PresentationObservedSignal,
    PresentationOptionParameter,
    PresentationOverlayKind,
    PresentationOverlayRecord,
    PresentationProvinceValue,
    PresentationScoreComponent,
    PresentationSpotlight,
    PresentationSpotlightScore,
    PresentationSubjectRef,
    PresentationThreadBeat,
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
    SimulationRound.PROVINCE_INITIAL: "省份在同一冻结基线下按各自目标与财政约束形成初始策略。",
    SimulationRound.AUTOMAKER_INITIAL: (
        "车企比较全国省域条件，在有限渠道与产能名额内形成初步 Top-K。"
    ),
    SimulationRound.PROVINCE_REVISION: (
        "省份读取企业与 Peer 信号后调整政策，并明确竞争反制或协同选择。"
    ),
    SimulationRound.AUTOMAKER_NEGOTIATION: "省企资源包进入接受、拒绝或反报价阶段。",
    SimulationRound.PROVINCE_COUNTER_RESPONSE: "省份在资源约束内逐项接受或拒绝企业条件。",
    SimulationRound.AUTOMAKER_FINAL: "车企根据已冻结回应完成最终确认与资源重配。",
    SimulationRound.ENVIRONMENT_SETTLEMENT: "确定性环境结算双方得失、效用和全国指标。",
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

ROUND_ORDER = {round_name: index for index, round_name in enumerate(SimulationRound)}


def _camera() -> PresentationCamera:
    return PresentationCamera(longitude=104.0, latitude=35.0, zoom=3.2, pitch=18, bearing=0)


class PresentationProjectionService:
    """Project committed M32 facts into a deterministic, read-only game narrative."""

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
        self.automakers = automaker_catalog()

    def build_timeline(self) -> PresentationTimeline:
        frames = self._frames()
        indexes = [
            PresentationFrameIndex(
                frame_id=frame.frame_id,
                sequence=frame.sequence,
                kind=frame.kind,
                round=frame.round,
                title=frame.title,
                spotlight_count=len(frame.spotlights),
                divergence_count=len(frame.divergences),
                projection_roles=(
                    ["shared"] if frame.shared_projection is not None else ["control", "treatment"]
                ),
                source_hash=frame.source_hash,
            )
            for frame in frames
        ]
        first_divergence = next((item.frame_id for item in frames if item.divergences), None)
        generated_at = self.events[-1].timestamp if self.events else datetime.now(UTC)
        modes = [PresentationMode.LIVE]
        if self.world.status is V32ExperimentStatus.COMPLETED and self.comparison is not None:
            modes.append(PresentationMode.COMPARE)
        return PresentationTimeline(
            experiment_id=self.world.experiment_id,
            product_version=self.world.product_version,
            status=self.world.status.value,
            current_frame_id=frames[-1].frame_id,
            frames=indexes,
            event_markers=self._event_markers(),
            first_divergence_frame_id=first_divergence,
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
        if self.world.baseline is None or set(self.world.branches) != {"control", "treatment"}:
            return frames
        frames.append(self._baseline_frame(sequence=len(frames)))
        plan = self.world.design.event_plan if self.world.design else None
        if plan and plan.trigger_point is EventTriggerPoint.BEFORE_PROVINCE_INITIAL:
            frames.append(self._event_frame(sequence=len(frames)))
        for round_name in SimulationRound:
            if not all(
                round_name in branch.completed_rounds for branch in self.world.branches.values()
            ):
                break
            frames.append(self._round_frame(round_name, sequence=len(frames)))
            if plan and (
                plan.trigger_point is EventTriggerPoint.AFTER_PROVINCE_INITIAL
                and round_name is SimulationRound.PROVINCE_INITIAL
                or plan.trigger_point is EventTriggerPoint.AFTER_AUTOMAKER_INITIAL
                and round_name is SimulationRound.AUTOMAKER_INITIAL
            ):
                frames.append(self._event_frame(sequence=len(frames)))
        if self.comparison is not None:
            frames.append(self._comparison_frame(sequence=len(frames)))
        return frames

    def _setup_frame(self) -> PresentationFrame:
        interpretation = self.world.interpretation
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
        source_ids = self._source_event_ids(
            event_types={"interpretation.generated", "interpretation.confirmed", "design.confirmed"}
        )
        projection = self._projection(
            role="shared",
            branch=None,
            label="政策输入",
            values=[],
            fill_metric="central_share",
            unit="%",
            overlays=[],
            metrics=metrics,
            evidence_refs=[f"policy:{policy.policy_id}"],
            source_event_ids=source_ids,
        )
        return self._frame(
            frame_id="frame-setup-policy",
            sequence=0,
            kind=PresentationFrameKind.SETUP,
            title="政策输入",
            summary=interpretation.public_summary,
            shared_projection=projection,
            panel_refs=["panel:policy", "panel:experiment-design"],
        )

    def _baseline_frame(self, *, sequence: int) -> PresentationFrame:
        assert self.world.baseline is not None
        projections: dict[str, PresentationBranchProjection] = {}
        for role in ("control", "treatment"):
            branch = self.world.branches[role]
            values = {
                code: branch.policy.share_for_region(
                    self.province_catalog[code].policy_region.value
                )
                * 100
                for code in MAINLAND_PROVINCE_CODES
            }
            projections[role] = self._projection(
                role=role,
                branch=branch,
                label="原始方案" if role == "control" else "干预方案",
                values=self._province_values(values),
                fill_metric="central_share",
                unit="%",
                overlays=self._event_overlays(branch),
                metrics=[],
                evidence_refs=[f"checkpoint:{self.world.baseline.checkpoint_id}"],
                source_event_ids=self._source_event_ids(
                    event_types={"baseline.confirmed", "branches.created"},
                    branch_id=branch.branch_id,
                ),
            )
        return self._frame(
            frame_id="frame-baseline-frozen",
            sequence=sequence,
            kind=PresentationFrameKind.SETUP,
            title="方案冻结",
            summary="两个方案从同一代理数据基线派生，后续行动按分支独立记录。",
            branch_projections=projections,
            panel_refs=["panel:baseline", "panel:methods"],
        )

    def _event_frame(self, *, sequence: int) -> PresentationFrame:
        assert self.world.design is not None and self.world.design.event_plan is not None
        plan = self.world.design.event_plan
        template = event_scenario_catalog()[plan.template_id]
        target_codes = set(template.target_province_codes or MAINLAND_PROVINCE_CODES)
        projections: dict[str, PresentationBranchProjection] = {}
        for role in ("control", "treatment"):
            branch = self.world.branches[role]
            applies = branch.event_applied
            exposure = {
                code: (plan.intensity.magnitude * 100 if applies and code in target_codes else 0.0)
                for code in MAINLAND_PROVINCE_CODES
            }
            projections[role] = self._projection(
                role=role,
                branch=branch,
                label="原始方案" if role == "control" else "干预方案",
                values=self._province_values(exposure),
                fill_metric="event_exposure",
                unit="模拟指数",
                overlays=self._event_overlays(branch),
                metrics=[],
                evidence_refs=plan.evidence_refs,
                source_event_ids=self._event_source_ids(branch),
                key_changes=[
                    PresentationKeyChange(
                        change_id=f"event-{role}-{plan.event_plan_id}",
                        title="事件情景已冻结",
                        detail=(
                            f"{plan.name} · {plan.intensity.value} · "
                            f"{'适用于本分支' if applies else '本分支暴露为零'}"
                        ),
                        semantic="event",
                        evidence_refs=plan.evidence_refs,
                    )
                ],
            )
        return self._frame(
            frame_id=f"frame-event-{plan.event_plan_id}",
            sequence=sequence,
            kind=PresentationFrameKind.EVENT,
            title=plan.name,
            summary="冻结事件情景进入适用分支的后续主体上下文，结果仍待推演验证。",
            branch_projections=projections,
            panel_refs=["panel:event", "panel:methods"],
        )

    def _round_frame(self, round_name: SimulationRound, *, sequence: int) -> PresentationFrame:
        projections: dict[str, PresentationBranchProjection] = {}
        moments: list[PresentationDecisionMoment] = []
        threads: list[PresentationGameThread] = []
        for role in ("control", "treatment"):
            branch = self.world.branches[role]
            values, fill_metric, unit = self._round_values(branch, round_name)
            metrics = (
                self._settlement_metrics(branch)
                if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT
                else []
            )
            evidence_refs = self._round_evidence_refs(branch, round_name)
            projections[role] = self._projection(
                role=role,
                branch=branch,
                label="原始方案" if role == "control" else "干预方案",
                values=self._province_values(values),
                fill_metric=fill_metric,
                unit=unit,
                overlays=self._round_overlays(branch, round_name),
                metrics=metrics,
                evidence_refs=evidence_refs,
                source_event_ids=self._source_event_ids(
                    round_name=round_name, branch_id=branch.branch_id
                ),
            )
            branch_moments = self._decision_moments(role, branch, round_name)
            moments.extend(branch_moments)
            threads.extend(self._game_threads(role, branch, round_name, branch_moments))
        divergences = self._divergences(
            round_name, [item for item in moments if item.round is round_name]
        )
        spotlights = self._spotlights(round_name, moments, threads, divergences)
        kind = (
            PresentationFrameKind.SETTLEMENT
            if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT
            else PresentationFrameKind.ROUND
        )
        return self._frame(
            frame_id=f"frame-round-{round_name.value}",
            sequence=sequence,
            kind=kind,
            round_name=(None if kind is PresentationFrameKind.SETTLEMENT else round_name),
            title=ROUND_TITLES[round_name],
            summary=ROUND_SUMMARIES[round_name],
            branch_projections=projections,
            decision_moments=moments,
            interaction_threads=threads,
            divergences=divergences,
            spotlights=spotlights,
            panel_refs=self._round_panel_refs(round_name),
        )

    def _comparison_frame(self, *, sequence: int) -> PresentationFrame:
        assert self.comparison is not None
        projections: dict[str, PresentationBranchProjection] = {}
        for role in ("control", "treatment"):
            branch = self.world.branches[role]
            values = {
                code: state.development_index for code, state in branch.province_states.items()
            }
            projections[role] = self._projection(
                role=role,
                branch=branch,
                label="原始方案" if role == "control" else "干预方案",
                values=self._province_values(values),
                fill_metric="province_nev_development_index",
                unit="模拟指数",
                overlays=self._round_overlays(branch, SimulationRound.ENVIRONMENT_SETTLEMENT),
                metrics=self._settlement_metrics(branch),
                evidence_refs=[f"comparison:{self.world.experiment_id}"],
                source_event_ids=self._source_event_ids(
                    event_types={"comparison.completed"}, branch_id=branch.branch_id
                ),
            )
        delta_values = {
            item.province_code: item.development_delta for item in self.comparison.province_deltas
        }
        delta_metrics = [
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
        difference = self._projection(
            role="shared",
            branch=None,
            label="干预方案 − 原始方案",
            values=self._province_values(delta_values),
            fill_metric="development_delta",
            unit="模拟指数点",
            overlays=[],
            metrics=delta_metrics,
            evidence_refs=[f"comparison:{self.world.experiment_id}"],
            source_event_ids=self._source_event_ids(event_types={"comparison.completed"}),
            difference=True,
        )
        settlement_moments = [
            *self._decision_moments(
                "control", self.world.branches["control"], SimulationRound.ENVIRONMENT_SETTLEMENT
            ),
            *self._decision_moments(
                "treatment",
                self.world.branches["treatment"],
                SimulationRound.ENVIRONMENT_SETTLEMENT,
            ),
        ]
        divergences = self._divergences(SimulationRound.ENVIRONMENT_SETTLEMENT, settlement_moments)
        return self._frame(
            frame_id="frame-comparison-result",
            sequence=sequence,
            kind=PresentationFrameKind.COMPARISON,
            title="结果复盘",
            summary=self.comparison.conclusion,
            branch_projections=projections,
            difference_projection=difference,
            decision_moments=settlement_moments,
            divergences=divergences,
            panel_refs=["panel:result", "panel:methods"],
        )

    def _projection(
        self,
        *,
        role: str,
        branch: BranchRuntimeState | None,
        label: str,
        values: list[PresentationProvinceValue],
        fill_metric: str,
        unit: str,
        overlays: list[PresentationOverlayRecord],
        metrics: list[PresentationMetricSummary],
        evidence_refs: list[str],
        source_event_ids: list[str],
        difference: bool = False,
        key_changes: list[PresentationKeyChange] | None = None,
    ) -> PresentationBranchProjection:
        payload = {
            "role": role,
            "branch_id": branch.branch_id if branch else None,
            "values": values,
            "overlays": overlays,
            "metrics": metrics,
            "events": source_event_ids,
        }
        return PresentationBranchProjection(
            branch_role=role,
            branch_id=branch.branch_id if branch else None,
            label=label,
            map_projection=PresentationMapProjection(
                mode="difference" if difference else "absolute",
                fill_metric=fill_metric,
                unit=unit,
                camera=_camera(),
                enabled_overlays=list(dict.fromkeys(item.kind for item in overlays)),
            ),
            province_values=values,
            overlay_records=overlays,
            key_changes=key_changes if key_changes is not None else self._key_changes(values, unit),
            metric_summary=metrics,
            evidence_refs=list(dict.fromkeys(evidence_refs))[:20],
            source_event_ids=list(dict.fromkeys(source_event_ids)),
            source_hash=canonical_hash(payload),
        )

    def _frame(
        self,
        *,
        frame_id: str,
        sequence: int,
        kind: PresentationFrameKind,
        title: str,
        summary: str,
        panel_refs: list[str],
        round_name: SimulationRound | None = None,
        shared_projection: PresentationBranchProjection | None = None,
        branch_projections: dict[str, PresentationBranchProjection] | None = None,
        difference_projection: PresentationBranchProjection | None = None,
        decision_moments: list[PresentationDecisionMoment] | None = None,
        interaction_threads: list[PresentationGameThread] | None = None,
        divergences: list[PresentationDivergence] | None = None,
        spotlights: list[PresentationSpotlight] | None = None,
    ) -> PresentationFrame:
        branch_projections = branch_projections or {}
        decisions = decision_moments or []
        threads = interaction_threads or []
        frame_divergences = divergences or []
        frame_spotlights = spotlights or []
        projection_values = [shared_projection, *branch_projections.values(), difference_projection]
        evidence_refs = list(
            dict.fromkeys(
                ref
                for projection in projection_values
                if projection is not None
                for ref in projection.evidence_refs
            )
        )[:16]
        event_ids = list(
            dict.fromkeys(
                event_id
                for projection in projection_values
                if projection is not None
                for event_id in projection.source_event_ids
            )
        )[:64]
        source_payload = {
            "frame_id": frame_id,
            "round": round_name,
            "shared": shared_projection,
            "branches": branch_projections,
            "difference": difference_projection,
            "decisions": decisions,
            "threads": threads,
            "divergences": frame_divergences,
            "spotlights": frame_spotlights,
        }
        return PresentationFrame(
            frame_id=frame_id,
            sequence=sequence,
            kind=kind,
            round=round_name,
            title=title,
            summary=summary,
            shared_projection=shared_projection,
            branch_projections=branch_projections,
            difference_projection=difference_projection,
            decision_moments=decisions,
            interaction_threads=threads,
            divergences=frame_divergences,
            spotlights=frame_spotlights,
            panel_refs=panel_refs,
            evidence_refs=evidence_refs,
            source_event_ids=event_ids,
            source_hash=canonical_hash(source_payload),
        )

    def _subject(self, subject_type: str, subject_id: str) -> PresentationSubjectRef:
        if subject_type == "province" and subject_id in self.province_catalog:
            name = self.province_catalog[subject_id].short_name
        elif subject_type == "automaker" and subject_id in self.automakers:
            name = self.automakers[subject_id].display_name
        elif subject_type == "policy":
            name = "中央政策参数"
        elif subject_type == "event":
            name = (
                self.world.design.event_plan.name
                if self.world.design and self.world.design.event_plan
                else "事件情景"
            )
        else:
            name = "确定性环境" if subject_type == "environment" else subject_id
        return PresentationSubjectRef(
            subject_type=subject_type, subject_id=subject_id, display_name=name
        )

    def _decision_moments(
        self, role: str, branch: BranchRuntimeState, round_name: SimulationRound
    ) -> list[PresentationDecisionMoment]:
        if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT:
            return self._settlement_moments(role, branch)
        traces = sorted(
            (
                trace
                for trace in branch.decision_traces
                if ROUND_ORDER[trace.round] <= ROUND_ORDER[round_name]
            ),
            key=lambda item: (ROUND_ORDER[item.round], item.agent_id, item.trace_id),
        )
        moments: list[PresentationDecisionMoment] = []
        for trace in traces:
            trace_type = (
                trace.trace_type.value if hasattr(trace.trace_type, "value") else trace.trace_type
            )
            actor_type = "province" if trace_type == "province" else "automaker"
            actor = self._subject(actor_type, trace.agent_id)
            responses = self._actual_responses(
                branch, trace.agent_id, actor_type, trace.round, round_name
            )
            observed = [
                PresentationObservedSignal(
                    source=self._subject(
                        observation.source_type,
                        observation.source_id,
                    ),
                    signal=observation.summary[:220],
                    evidence_refs=observation.evidence_refs,
                )
                for observation in trace.observations[:8]
            ]
            affected = []
            for subject_id in trace.affected_agents[:16]:
                subject_type = "province" if subject_id in self.province_catalog else "automaker"
                if subject_id in self.province_catalog or subject_id in self.automakers:
                    affected.append(self._subject(subject_type, subject_id))
            moments.append(
                PresentationDecisionMoment(
                    moment_id=f"moment-{trace.trace_id}",
                    trace_id=trace.trace_id,
                    branch_role=role,
                    branch_id=branch.branch_id,
                    round=trace.round,
                    actor=actor,
                    objective=trace.primary_goal[:240],
                    constraints=trace.constraints[:8],
                    observed_signals=observed,
                    actual_choice=trace.primary_choice[:240],
                    action_changes=[item.display_summary for item in trace.action_delta[:8]],
                    recorded_alternatives=trace.alternatives_considered[:5],
                    rejected_alternatives=[
                        f"{item.alternative}：{item.rejection_basis}"
                        for item in trace.rejected_alternatives[:6]
                    ],
                    opportunity_costs=[item.summary for item in trace.opportunity_costs[:6]],
                    change_conditions=[
                        f"{item.field} {item.operator} {item.threshold} 时：{item.action_if_met}"
                        for item in trace.change_conditions[:6]
                    ],
                    option_evaluations=self._option_evaluations(branch, trace, actor_type),
                    response_status=(
                        "responded"
                        if responses
                        else "pending"
                        if trace.round
                        in {
                            SimulationRound.PROVINCE_INITIAL,
                            SimulationRound.PROVINCE_REVISION,
                            SimulationRound.AUTOMAKER_NEGOTIATION,
                            SimulationRound.PROVINCE_COUNTER_RESPONSE,
                        }
                        else "not_applicable"
                    ),
                    actual_responses=responses,
                    affected_subjects=affected,
                    fallback_used=trace.fallback_reason is not None,
                    evidence_refs=list(dict.fromkeys(trace.evidence_refs))[:16],
                )
            )
        return moments

    def _settlement_moments(
        self, role: str, branch: BranchRuntimeState
    ) -> list[PresentationDecisionMoment]:
        utilities = sorted(
            branch.province_utilities.values(),
            key=lambda item: (-abs(item.utility_index), item.province_code),
        )
        moments = []
        for utility in utilities:
            actor = self._subject("province", utility.province_code)
            components = [
                ("需求", utility.demand_index),
                ("产业", utility.industry_index),
                ("省企匹配", utility.enterprise_gain),
                ("省际协同", utility.coordination_gain),
                ("财政压力", -utility.fiscal_pressure),
                ("竞争损失", -utility.competition_loss),
            ]
            moments.append(
                PresentationDecisionMoment(
                    moment_id=f"moment-settlement-{role}-{utility.province_code}",
                    trace_id=f"utility:{utility.utility_id}",
                    branch_role=role,
                    branch_id=branch.branch_id,
                    round=SimulationRound.ENVIRONMENT_SETTLEMENT,
                    actor=actor,
                    objective="结算有限资源选择的综合得失",
                    constraints=["需求、产业、匹配、协同、财政和竞争按冻结权重共同结算"],
                    actual_choice=f"综合效用 {utility.utility_index:.2f}",
                    action_changes=[f"{label} {value:+.2f}" for label, value in components],
                    opportunity_costs=[
                        "财政压力 "
                        f"{utility.fiscal_pressure:.2f}；竞争损失 {utility.competition_loss:.2f}"
                    ],
                    response_status="settled",
                    affected_subjects=[actor],
                    evidence_refs=utility.evidence_refs,
                )
            )
        return moments

    def _actual_responses(
        self,
        branch: BranchRuntimeState,
        agent_id: str,
        actor_type: str,
        decision_round: SimulationRound,
        as_of_round: SimulationRound,
    ) -> list[PresentationActualResponse]:
        responses: list[PresentationActualResponse] = []
        if (
            decision_round is SimulationRound.PROVINCE_INITIAL
            and actor_type == "province"
            and ROUND_ORDER[as_of_round] >= ROUND_ORDER[SimulationRound.AUTOMAKER_INITIAL]
        ):
            for action in branch.automaker_initial_actions.values():
                signal = next(
                    (item for item in action.province_signals if item.province_code == agent_id),
                    None,
                )
                if signal:
                    responses.append(
                        PresentationActualResponse(
                            response_id=signal.signal_id,
                            actor=self._subject("automaker", signal.automaker_id),
                            action=f"市场行动：{signal.decision}",
                            status=signal.decision,
                            evidence_refs=signal.evidence_refs,
                        )
                    )
        elif (
            decision_round is SimulationRound.AUTOMAKER_INITIAL
            and actor_type == "automaker"
            and ROUND_ORDER[as_of_round] >= ROUND_ORDER[SimulationRound.PROVINCE_REVISION]
        ):
            for outcome in branch.competition_outcomes:
                if outcome.automaker_id == agent_id:
                    responses.append(
                        PresentationActualResponse(
                            response_id=outcome.outcome_id,
                            actor=self._subject("province", outcome.loser_province_code),
                            action=(
                                "Top-K 竞争中由"
                                f"{self.province_catalog[outcome.winner_province_code].short_name}"
                                "取得名额"
                            ),
                            status="competition_loss",
                            evidence_refs=[
                                f"competition:{outcome.outcome_id}",
                                *outcome.evidence_refs,
                            ][:8],
                        )
                    )
        elif (
            decision_round is SimulationRound.PROVINCE_REVISION
            and actor_type == "province"
            and ROUND_ORDER[as_of_round] >= ROUND_ORDER[SimulationRound.PROVINCE_REVISION]
        ):
            for response in branch.province_coordination_responses:
                proposal = next(
                    (
                        item
                        for item in branch.province_coordination_proposals
                        if item.proposal_id == response.proposal_id
                    ),
                    None,
                )
                if proposal and proposal.source_province_code == agent_id:
                    responses.append(
                        PresentationActualResponse(
                            response_id=response.response_id,
                            actor=self._subject("province", response.responding_province_code),
                            action="接受协同提议"
                            if response.decision == "accept"
                            else "拒绝协同提议",
                            status=response.decision,
                            evidence_refs=response.evidence_refs,
                        )
                    )
        elif (
            decision_round is SimulationRound.AUTOMAKER_NEGOTIATION
            and actor_type == "automaker"
            and ROUND_ORDER[as_of_round] >= ROUND_ORDER[SimulationRound.AUTOMAKER_NEGOTIATION]
        ):
            action = branch.automaker_negotiation_actions.get(agent_id)
            if action:
                offers = {item.offer_id: item for item in branch.province_enterprise_offers}
                for response in action.enterprise_offer_responses[:8]:
                    offer = offers.get(response.offer_id)
                    if offer:
                        responses.append(
                            PresentationActualResponse(
                                response_id=response.response_id,
                                actor=self._subject("province", offer.source_province_code),
                                action={
                                    "accept": "接受省企报价",
                                    "reject": "拒绝省企报价",
                                    "counteroffer": "提出反报价",
                                }[response.decision],
                                status=response.decision,
                                evidence_refs=response.evidence_refs,
                            )
                        )
        elif (
            decision_round is SimulationRound.PROVINCE_COUNTER_RESPONSE
            and actor_type == "province"
            and ROUND_ORDER[as_of_round] >= ROUND_ORDER[SimulationRound.PROVINCE_COUNTER_RESPONSE]
        ):
            counteroffers = {
                item.counter_offer_id: item for item in branch.automaker_counter_offers
            }
            for response in branch.province_counter_offer_responses:
                if response.province_code == agent_id:
                    offer = counteroffers.get(response.counter_offer_id)
                    if offer:
                        responses.append(
                            PresentationActualResponse(
                                response_id=response.response_id,
                                actor=self._subject("automaker", offer.automaker_id),
                                action="接受企业条件"
                                if response.decision == "accept"
                                else "拒绝企业条件",
                                status=response.decision,
                                evidence_refs=response.evidence_refs,
                            )
                        )
        elif (
            decision_round is SimulationRound.AUTOMAKER_FINAL
            and actor_type == "automaker"
            and ROUND_ORDER[as_of_round] >= ROUND_ORDER[SimulationRound.AUTOMAKER_FINAL]
        ):
            for match in branch.province_enterprise_matches:
                if match.automaker_id == agent_id:
                    responses.append(
                        PresentationActualResponse(
                            response_id=match.match_id,
                            actor=self._subject("province", match.province_code),
                            action=match.action_summary
                            or ("形成匹配" if match.status == "matched" else "未形成匹配"),
                            status=match.status,
                            evidence_refs=[f"match:{match.match_id}"],
                        )
                    )
        return responses[:8]

    def _option_evaluations(
        self, branch: BranchRuntimeState, trace: object, actor_type: str
    ) -> list[DecisionOptionEvaluation]:
        if actor_type == "province":
            return self._province_options(branch, trace)
        return self._automaker_options(branch, trace)

    @staticmethod
    def _scored_option(
        option_id: str,
        label: str,
        option_type: str,
        values: list[tuple[str, str, float, float, str]],
        evidence_refs: list[str],
        assumptions: list[str],
        parameters: list[tuple[str, str, float, str]] | None = None,
    ) -> DecisionOptionEvaluation:
        components = [
            PresentationScoreComponent(
                component=code,
                label=component_label,
                value=round(value, 4),
                weight=weight,
                contribution=round(value * weight * (-1 if direction == "cost" else 1), 4),
                direction=direction,
            )
            for code, component_label, value, weight, direction in values
        ]
        score = round(sum(item.contribution for item in components), 4)
        return DecisionOptionEvaluation(
            option_id=option_id,
            label=label,
            option_type=option_type,
            feasible=True,
            score=max(-100.0, min(100.0, score)),
            components=components,
            parameters=[
                PresentationOptionParameter(
                    parameter=code, label=parameter_label, value=round(value, 6), unit=unit
                )
                for code, parameter_label, value, unit in parameters or []
            ],
            assumptions=assumptions,
            evidence_refs=evidence_refs[:10],
        )

    def _province_options(
        self, branch: BranchRuntimeState, trace: object
    ) -> list[DecisionOptionEvaluation]:
        code = trace.agent_id
        action = (
            branch.province_initial_actions.get(code)
            if trace.round is SimulationRound.PROVINCE_INITIAL
            else branch.province_final_actions.get(code)
        )
        if action is None:
            return []
        envelope = branch.province_resource_envelopes.get(code)

        def evaluate(
            option_id: str,
            label: str,
            option_type: str,
            support: float,
            mix: tuple[float, float, float],
        ) -> DecisionOptionEvaluation:
            budget = envelope.available_policy_budget if envelope else max(support, 0.0001)
            values = [
                ("consumer", "消费激活", mix[0] * 100, 0.24, "benefit"),
                ("fixed", "产业进入", mix[1] * 100, 0.24, "benefit"),
                ("variable", "运营支持", mix[2] * 100, 0.22, "benefit"),
                (
                    "budget",
                    "预算占用",
                    min(100.0, 100 * support / max(budget, 0.0001)),
                    0.30,
                    "cost",
                ),
            ]
            return self._scored_option(
                option_id,
                label,
                option_type,
                values,
                trace.evidence_refs,
                ["仅使用决策时点已冻结资源", "份额敏感度步长为 0.02", "不重跑后续主体"],
                [
                    ("support", "总体支持强度", support, "0-1"),
                    ("consumer_share", "消费端份额", mix[0], "份额"),
                    ("fixed_cost_share", "固定成本份额", mix[1], "份额"),
                    ("variable_cost_share", "可变成本份额", mix[2], "份额"),
                    ("available_budget", "可用资源包", budget, "模拟资源"),
                ],
            )

        current_mix = (
            action.subsidy_mix.consumer,
            action.subsidy_mix.fixed_cost,
            action.subsidy_mix.variable_cost,
        )
        options = [
            evaluate(
                f"option-{trace.trace_id}-chosen",
                "实际选择",
                "chosen",
                action.overall_support_intensity,
                current_mix,
            )
        ]
        previous = (
            branch.province_initial_actions.get(code)
            if trace.round is SimulationRound.PROVINCE_REVISION
            else None
        )
        if previous and previous.action_id != action.action_id:
            previous_mix = (
                previous.subsidy_mix.consumer,
                previous.subsidy_mix.fixed_cost,
                previous.subsidy_mix.variable_cost,
            )
            options.append(
                evaluate(
                    f"option-{trace.trace_id}-maintain",
                    "保持初始方案",
                    "maintain",
                    previous.overall_support_intensity,
                    previous_mix,
                )
            )
        focuses = ((0, "消费端小幅加码"), (1, "固定成本小幅加码"), (2, "可变成本小幅加码"))
        for focus, label in focuses:
            if len(options) >= 4:
                break
            donors = sorted(
                (index for index in range(3) if index != focus),
                key=lambda index: current_mix[index],
                reverse=True,
            )
            donor = donors[0]
            shift = min(0.02, current_mix[donor])
            candidate = list(current_mix)
            candidate[focus] += shift
            candidate[donor] -= shift
            caps = (
                envelope.consumer_cap if envelope else 1.0,
                envelope.fixed_cost_cap if envelope else 1.0,
                envelope.variable_cost_cap if envelope else 1.0,
            )
            feasible = (
                abs(sum(candidate) - 1) <= 1e-6
                and action.overall_support_intensity * candidate[focus] <= caps[focus] + 1e-6
            )
            if feasible and tuple(round(item, 6) for item in candidate) != tuple(
                round(item, 6) for item in current_mix
            ):
                options.append(
                    evaluate(
                        f"option-{trace.trace_id}-focus-{focus}",
                        label,
                        "policy_shift",
                        action.overall_support_intensity,
                        tuple(candidate),
                    )
                )
        chosen_score = options[0].score or 0.0
        return [
            item.model_copy(
                update={"delta_from_chosen": round((item.score or 0.0) - chosen_score, 4)}
            )
            for item in options
        ]

    def _automaker_options(
        self, branch: BranchRuntimeState, trace: object
    ) -> list[DecisionOptionEvaluation]:
        action_map = {
            SimulationRound.AUTOMAKER_INITIAL: branch.automaker_initial_actions,
            SimulationRound.AUTOMAKER_NEGOTIATION: branch.automaker_negotiation_actions,
            SimulationRound.AUTOMAKER_FINAL: branch.automaker_final_actions,
        }
        action = action_map.get(trace.round, {}).get(trace.agent_id)
        if action is None:
            return []

        def evaluate(
            option_id: str, label: str, option_type: str, candidate: object
        ) -> DecisionOptionEvaluation:
            signals = candidate.province_signals
            top = sorted((item.investment_inclination for item in signals), reverse=True)[:5]
            market_total = sum(
                item.sales_investment_intensity for item in candidate.province_market_actions
            )
            envelope = branch.automaker_resource_envelopes.get(trace.agent_id)
            budget = envelope.national_market_budget if envelope else max(market_total, 0.0001)
            values = [
                ("market_fit", "候选省份匹配", 100 * fmean(top), 0.55, "benefit"),
                (
                    "coverage",
                    "明确扩张覆盖",
                    100 * sum(item.decision == "expand" for item in signals) / 31,
                    0.20,
                    "benefit",
                ),
                (
                    "budget",
                    "全国资源占用",
                    min(100.0, 100 * market_total / max(budget, 0.0001)),
                    0.25,
                    "cost",
                ),
            ]
            return self._scored_option(
                option_id,
                label,
                option_type,
                values,
                trace.evidence_refs,
                ["复用冻结省份吸引力与企业资源包", "不预测后续省级回应"],
                [
                    ("market_total", "全国资源使用", market_total, "模拟资源"),
                    ("market_budget", "全国资源包", budget, "模拟资源"),
                    (
                        "expand_count",
                        "扩张省份数",
                        float(sum(item.decision == "expand" for item in signals)),
                        "省",
                    ),
                ],
            )

        options = [evaluate(f"option-{trace.trace_id}-chosen", "实际资源配置", "chosen", action)]
        previous = branch.automaker_initial_actions.get(trace.agent_id)
        if previous and previous.action_id != action.action_id:
            options.append(
                evaluate(f"option-{trace.trace_id}-maintain", "保持初步配置", "maintain", previous)
            )
        if trace.round is SimulationRound.AUTOMAKER_NEGOTIATION:
            responses = action.enterprise_offer_responses
            if responses:
                accepted = sum(item.decision == "accept" for item in responses)
                countered = sum(item.decision == "counteroffer" for item in responses)
                option_type = "counteroffer" if countered else "accept" if accepted else "reject"
                options.append(
                    self._scored_option(
                        f"option-{trace.trace_id}-response",
                        f"报价回应：接受 {accepted}，反报价 {countered}",
                        option_type,
                        [
                            (
                                "package_fit",
                                "资源包匹配",
                                min(100.0, 20.0 * (accepted + countered)),
                                0.65,
                                "benefit",
                            ),
                            (
                                "management",
                                "管理名额占用",
                                min(100.0, 20.0 * accepted),
                                0.35,
                                "cost",
                            ),
                        ],
                        trace.evidence_refs,
                        ["只评估本轮已收到资源包", "接受与反报价不创造新资源"],
                    )
                )
        chosen_score = options[0].score or 0.0
        return [
            item.model_copy(
                update={"delta_from_chosen": round((item.score or 0.0) - chosen_score, 4)}
            )
            for item in options[:4]
        ]

    def _game_threads(
        self,
        role: str,
        branch: BranchRuntimeState,
        current_round: SimulationRound,
        moments: list[PresentationDecisionMoment],
    ) -> list[PresentationGameThread]:
        current_index = ROUND_ORDER[current_round]
        threads: list[PresentationGameThread] = []
        if current_index >= ROUND_ORDER[SimulationRound.AUTOMAKER_INITIAL]:
            for outcome in branch.competition_outcomes:
                participants = [
                    self._subject("province", outcome.winner_province_code),
                    self._subject("province", outcome.loser_province_code),
                    self._subject("automaker", outcome.automaker_id),
                ]
                threads.append(
                    PresentationGameThread(
                        thread_id=f"thread-{role}-competition-{outcome.outcome_id}",
                        branch_role=role,
                        thread_type="competition",
                        title=f"{participants[0].display_name}与{participants[1].display_name}竞争{participants[2].display_name}资源",
                        participants=participants,
                        resource_subject=participants[2],
                        state="response_frozen",
                        moment_ids=self._thread_moment_ids(moments, participants),
                        beats=[
                            PresentationThreadBeat(
                                beat_id=f"beat-{outcome.outcome_id}",
                                round=SimulationRound.AUTOMAKER_INITIAL,
                                label=f"Top-K 竞争损失 {outcome.loss_index:.2f}",
                                status="frozen",
                                subject=participants[1],
                                fact_ref=f"competition:{outcome.outcome_id}",
                            )
                        ],
                        evidence_refs=[f"competition:{outcome.outcome_id}", *outcome.evidence_refs][
                            :16
                        ],
                    )
                )
        if current_index >= ROUND_ORDER[SimulationRound.PROVINCE_REVISION]:
            responses = {item.proposal_id: item for item in branch.province_coordination_responses}
            records = {item.proposal_id: item for item in branch.coordination_records}
            for proposal in branch.province_coordination_proposals:
                response = responses.get(proposal.proposal_id)
                record = records.get(proposal.proposal_id)
                participants = [
                    self._subject("province", proposal.source_province_code),
                    self._subject("province", proposal.target_province_code),
                ]
                state = (
                    "matched"
                    if record and record.status == "matched"
                    else "rejected"
                    if response and response.decision == "reject"
                    else "awaiting_response"
                )
                beats = [
                    PresentationThreadBeat(
                        beat_id=f"beat-{proposal.proposal_id}-proposal",
                        round=SimulationRound.PROVINCE_REVISION,
                        label="提出省际协同",
                        status="frozen",
                        subject=participants[0],
                        fact_ref=f"proposal:{proposal.proposal_id}",
                    )
                ]
                if response:
                    beats.append(
                        PresentationThreadBeat(
                            beat_id=f"beat-{response.response_id}",
                            round=SimulationRound.PROVINCE_REVISION,
                            label="接受协同" if response.decision == "accept" else "拒绝协同",
                            status="frozen",
                            subject=participants[1],
                            fact_ref=f"response:{response.response_id}",
                        )
                    )
                threads.append(
                    PresentationGameThread(
                        thread_id=f"thread-{role}-coordination-{proposal.proposal_id}",
                        branch_role=role,
                        thread_type="coordination",
                        title=f"{participants[0].display_name}向{participants[1].display_name}提出协同",
                        participants=participants,
                        state=state,
                        moment_ids=self._thread_moment_ids(moments, participants),
                        beats=beats,
                        evidence_refs=proposal.evidence_refs,
                    )
                )
            offer_responses = {
                item.offer_id: item for item in branch.province_enterprise_offer_responses
            }
            counters = {item.offer_id: item for item in branch.automaker_counter_offers}
            counter_responses = {
                item.counter_offer_id: item for item in branch.province_counter_offer_responses
            }
            matches = {item.offer_id: item for item in branch.province_enterprise_matches}
            for offer in branch.province_enterprise_offers:
                province = self._subject("province", offer.source_province_code)
                automaker = self._subject("automaker", offer.target_automaker_id)
                beats = [
                    PresentationThreadBeat(
                        beat_id=f"beat-{offer.offer_id}",
                        round=SimulationRound.PROVINCE_REVISION,
                        label="省方提出资源包",
                        status="frozen",
                        subject=province,
                        fact_ref=f"offer:{offer.offer_id}",
                    )
                ]
                state = "awaiting_response"
                response = (
                    offer_responses.get(offer.offer_id)
                    if current_index >= ROUND_ORDER[SimulationRound.AUTOMAKER_NEGOTIATION]
                    else None
                )
                counter = (
                    counters.get(offer.offer_id)
                    if current_index >= ROUND_ORDER[SimulationRound.AUTOMAKER_NEGOTIATION]
                    else None
                )
                if response:
                    beats.append(
                        PresentationThreadBeat(
                            beat_id=f"beat-{response.response_id}",
                            round=SimulationRound.AUTOMAKER_NEGOTIATION,
                            label={
                                "accept": "企业接受",
                                "reject": "企业拒绝",
                                "counteroffer": "企业反报价",
                            }[response.decision],
                            status="frozen",
                            subject=automaker,
                            fact_ref=f"response:{response.response_id}",
                        )
                    )
                    state = "rejected" if response.decision == "reject" else "response_frozen"
                province_response = (
                    counter_responses.get(counter.counter_offer_id)
                    if counter
                    and current_index >= ROUND_ORDER[SimulationRound.PROVINCE_COUNTER_RESPONSE]
                    else None
                )
                if province_response:
                    beats.append(
                        PresentationThreadBeat(
                            beat_id=f"beat-{province_response.response_id}",
                            round=SimulationRound.PROVINCE_COUNTER_RESPONSE,
                            label="省方接受条件"
                            if province_response.decision == "accept"
                            else "省方拒绝条件",
                            status="frozen",
                            subject=province,
                            fact_ref=f"counterresponse:{province_response.response_id}",
                        )
                    )
                    state = (
                        "response_frozen" if province_response.decision == "accept" else "rejected"
                    )
                match = (
                    matches.get(offer.offer_id)
                    if current_index >= ROUND_ORDER[SimulationRound.AUTOMAKER_FINAL]
                    else None
                )
                if match:
                    beats.append(
                        PresentationThreadBeat(
                            beat_id=f"beat-{match.match_id}",
                            round=SimulationRound.AUTOMAKER_FINAL,
                            label="形成有效匹配" if match.status == "matched" else "未形成匹配",
                            status="frozen",
                            subject=automaker,
                            fact_ref=f"match:{match.match_id}",
                        )
                    )
                    state = "matched" if match.status == "matched" else "rejected"
                threads.append(
                    PresentationGameThread(
                        thread_id=f"thread-{role}-negotiation-{offer.offer_id}",
                        branch_role=role,
                        thread_type="negotiation",
                        title=f"{province.display_name}与{automaker.display_name}资源谈判",
                        participants=[province, automaker],
                        resource_subject=automaker,
                        state=state,
                        moment_ids=self._thread_moment_ids(moments, [province, automaker]),
                        beats=beats,
                        evidence_refs=offer.evidence_refs,
                    )
                )
        if current_index >= ROUND_ORDER[SimulationRound.AUTOMAKER_FINAL]:
            for item in branch.top_k_reallocations:
                participants = [
                    self._subject("province", item.released_province_code),
                    self._subject("province", item.recipient_province_code),
                    self._subject("automaker", item.automaker_id),
                ]
                threads.append(
                    PresentationGameThread(
                        thread_id=f"thread-{role}-topk-{item.reallocation_id}",
                        branch_role=role,
                        thread_type="topk",
                        title=f"{participants[2].display_name}释放并重配渠道名额",
                        participants=participants,
                        resource_subject=participants[2],
                        state="matched",
                        moment_ids=self._thread_moment_ids(moments, participants),
                        beats=[
                            PresentationThreadBeat(
                                beat_id=f"beat-{item.reallocation_id}",
                                round=SimulationRound.AUTOMAKER_FINAL,
                                label=(
                                    f"{participants[0].display_name} → "
                                    f"{participants[1].display_name}"
                                ),
                                status="frozen",
                                subject=participants[2],
                                fact_ref=f"topk:{item.reallocation_id}",
                            )
                        ],
                        evidence_refs=item.evidence_refs,
                    )
                )
        return sorted(threads, key=lambda item: (item.thread_type, item.thread_id))

    @staticmethod
    def _thread_moment_ids(
        moments: list[PresentationDecisionMoment], participants: list[PresentationSubjectRef]
    ) -> list[str]:
        keys = {(item.subject_type, item.subject_id) for item in participants}
        return [
            item.moment_id
            for item in moments
            if (item.actor.subject_type, item.actor.subject_id) in keys
        ][:20]

    def _divergences(
        self, round_name: SimulationRound, moments: list[PresentationDecisionMoment]
    ) -> list[PresentationDivergence]:
        grouped: dict[tuple[str, str], dict[str, PresentationDecisionMoment]] = {}
        for moment in moments:
            key = (moment.actor.subject_type, moment.actor.subject_id)
            grouped.setdefault(key, {})[moment.branch_role] = moment
        divergences = []
        for key, pair in sorted(grouped.items()):
            if set(pair) != {"control", "treatment"}:
                continue
            control = pair["control"]
            treatment = pair["treatment"]
            control_signature = (
                control.actual_choice,
                tuple(control.action_changes),
                tuple(item.status for item in control.actual_responses),
            )
            treatment_signature = (
                treatment.actual_choice,
                tuple(treatment.action_changes),
                tuple(item.status for item in treatment.actual_responses),
            )
            if control_signature == treatment_signature:
                continue
            magnitude = min(
                100.0,
                25.0
                + 8.0 * abs(len(control.action_changes) - len(treatment.action_changes))
                + 6.0 * abs(len(control.actual_responses) - len(treatment.actual_responses)),
            )
            divergences.append(
                PresentationDivergence(
                    divergence_id=f"divergence-{round_name.value}-{key[0]}-{key[1]}",
                    subject=control.actor,
                    round=round_name,
                    dimension=(
                        "utility"
                        if round_name is SimulationRound.ENVIRONMENT_SETTLEMENT
                        else "action"
                    ),
                    control_summary=(
                        control.action_changes[0]
                        if control.action_changes
                        else control.actual_choice
                    )[:220],
                    treatment_summary=(
                        treatment.action_changes[0]
                        if treatment.action_changes
                        else treatment.actual_choice
                    )[:220],
                    magnitude=magnitude,
                    first_for_subject=not self._subject_diverged_before(round_name, key),
                    evidence_refs=list(
                        dict.fromkeys([*control.evidence_refs, *treatment.evidence_refs])
                    )[:12],
                )
            )
        return divergences

    def _subject_diverged_before(self, round_name: SimulationRound, key: tuple[str, str]) -> bool:
        for prior in SimulationRound:
            if ROUND_ORDER[prior] >= ROUND_ORDER[round_name]:
                break
            control = next(
                (
                    item
                    for item in self.world.branches["control"].decision_traces
                    if item.round is prior and item.agent_id == key[1]
                ),
                None,
            )
            treatment = next(
                (
                    item
                    for item in self.world.branches["treatment"].decision_traces
                    if item.round is prior and item.agent_id == key[1]
                ),
                None,
            )
            if (
                control
                and treatment
                and (
                    control.primary_choice != treatment.primary_choice
                    or [item.display_summary for item in control.action_delta]
                    != [item.display_summary for item in treatment.action_delta]
                )
            ):
                return True
        return False

    def _spotlights(
        self,
        round_name: SimulationRound,
        moments: list[PresentationDecisionMoment],
        threads: list[PresentationGameThread],
        divergences: list[PresentationDivergence],
    ) -> list[PresentationSpotlight]:
        divergence_subjects = {
            (item.subject.subject_type, item.subject.subject_id) for item in divergences
        }
        thread_by_moment = {
            moment_id: thread for thread in threads for moment_id in thread.moment_ids
        }
        candidates = []
        for moment in moments:
            thread = thread_by_moment.get(moment.moment_id)
            divergence = (
                25.0
                if (moment.actor.subject_type, moment.actor.subject_id) in divergence_subjects
                else 0.0
            )
            response = 20.0 if moment.response_status in {"responded", "settled"} else 0.0
            scarcity = 15.0 if moment.constraints or moment.opportunity_costs else 0.0
            action_change = min(15.0, 3.0 * len(moment.action_changes))
            state_change = (
                15.0
                if moment.actual_responses
                or (thread and thread.state not in {"action_frozen", "awaiting_response"})
                else 0.0
            )
            evidence = min(10.0, 10.0 * len(moment.evidence_refs) / 8.0)
            total = round(
                divergence + response + scarcity + action_change + state_change + evidence, 4
            )
            candidates.append(
                (
                    total,
                    moment,
                    thread,
                    (divergence, response, scarcity, action_change, state_change, evidence),
                )
            )
        candidates.sort(
            key=lambda item: (
                -item[0],
                item[1].actor.subject_type,
                item[1].actor.subject_id,
                item[1].moment_id,
            )
        )
        selected = []
        used_actors: set[tuple[str, str]] = set()
        used_resources: set[tuple[str, str]] = set()
        for candidate in candidates:
            _, moment, thread, _ = candidate
            actor_key = (moment.actor.subject_type, moment.actor.subject_id)
            resource_key = (
                (thread.resource_subject.subject_type, thread.resource_subject.subject_id)
                if thread and thread.resource_subject
                else actor_key
            )
            if actor_key in used_actors or resource_key in used_resources:
                continue
            selected.append(candidate)
            used_actors.add(actor_key)
            used_resources.add(resource_key)
            if len(selected) == 3:
                break
        spotlights = []
        for rank, (total, moment, thread, parts) in enumerate(selected, start=1):
            divergence, response, scarcity, action_change, state_change, evidence = parts
            response_detail = (
                moment.actual_responses[0].action
                if moment.actual_responses
                else "尚无后续主体回应，等待下一冻结轮次。"
            )
            option_detail = (
                "；".join(
                    f"{item.label} {item.score:.1f}"
                    for item in moment.option_evaluations
                    if item.score is not None
                )
                or "没有足够合法备选，不生成虚构方案。"
            )
            tradeoff = (
                moment.opportunity_costs[0]
                if moment.opportunity_costs
                else "当前记录未新增机会成本。"
            )
            beats = [
                PresentationNarrativeBeat(
                    beat="focus",
                    title="聚焦主体",
                    detail=f"{moment.actor.display_name}正在决策。",
                    status="frozen",
                ),
                PresentationNarrativeBeat(
                    beat="observe",
                    title="观察信号",
                    detail=(
                        moment.observed_signals[0].signal
                        if moment.observed_signals
                        else "本轮依据冻结政策与资源约束行动。"
                    ),
                    status="frozen",
                ),
                PresentationNarrativeBeat(
                    beat="options", title="合法策略", detail=option_detail[:240], status="frozen"
                ),
                PresentationNarrativeBeat(
                    beat="action", title="实际选择", detail=moment.actual_choice, status="frozen"
                ),
                PresentationNarrativeBeat(
                    beat="response",
                    title="实际回应",
                    detail=response_detail[:240],
                    status=("frozen" if moment.actual_responses else "pending"),
                ),
                PresentationNarrativeBeat(
                    beat="tradeoff", title="取舍与分歧", detail=tradeoff[:240], status="frozen"
                ),
            ]
            focus_subjects = [moment.actor]
            if thread:
                focus_subjects.extend(
                    item
                    for item in thread.participants
                    if (item.subject_type, item.subject_id)
                    != (moment.actor.subject_type, moment.actor.subject_id)
                )
            spotlights.append(
                PresentationSpotlight(
                    spotlight_id=f"spotlight-{round_name.value}-{rank}-{moment.moment_id}",
                    rank=rank,
                    label=f"{moment.actor.display_name} · {moment.actual_choice}"[:120],
                    primary_moment_id=moment.moment_id,
                    thread_id=thread.thread_id if thread else None,
                    branch_role=moment.branch_role,
                    score=PresentationSpotlightScore(
                        divergence=divergence,
                        response=response,
                        scarcity=scarcity,
                        action_change=action_change,
                        state_change=state_change,
                        evidence=evidence,
                        total=total,
                    ),
                    narrative_beats=beats,
                    focus_subjects=focus_subjects[:8],
                    evidence_refs=moment.evidence_refs[:12],
                )
            )
        return spotlights

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
                [*self._event_overlays(branch), *self._coordination_overlays(branch)]
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
                    f"{self.automakers[item.target_automaker_id].display_name} 省企报价"
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
        overlays = []
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
                        f"{'接受' if item.decision == 'accept' else '拒绝'}反报价"
                    ),
                    style_semantic="evidence" if item.decision == "accept" else "neutral",
                    evidence_refs=[f"counterresponse:{item.response_id}", *item.evidence_refs][:8],
                )
            )
        return self._limit_overlays(overlays)

    def _topk_overlays(self, branch: BranchRuntimeState) -> list[PresentationOverlayRecord]:
        return self._limit_overlays(
            PresentationOverlayRecord(
                overlay_id=f"overlay-{item.reallocation_id}",
                kind=PresentationOverlayKind.TOPK,
                source_subject=f"province:{item.released_province_code}",
                target_subject=f"province:{item.recipient_province_code}",
                status="reallocated",
                weight=1.0,
                label=(
                    f"{self.automakers[item.automaker_id].display_name} "
                    f"{self.province_catalog[item.released_province_code].short_name} → "
                    f"{self.province_catalog[item.recipient_province_code].short_name}"
                ),
                style_semantic="policy",
                evidence_refs=[f"topk:{item.reallocation_id}", *item.evidence_refs][:8],
            )
            for item in sorted(branch.top_k_reallocations, key=lambda item: item.reallocation_id)
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
                label=(
                    item.action_summary
                    or (
                        f"{self.province_catalog[item.province_code].short_name}与"
                        f"{self.automakers[item.automaker_id].display_name}匹配"
                    )
                )[:160],
                style_semantic="evidence" if item.status == "matched" else "neutral",
                evidence_refs=[f"match:{item.match_id}"],
            )
            for item in records
        )

    def _event_overlays(self, branch: BranchRuntimeState) -> list[PresentationOverlayRecord]:
        if (
            not branch.event_applied
            or self.world.design is None
            or self.world.design.event_plan is None
        ):
            return []
        plan = self.world.design.event_plan
        template = event_scenario_catalog()[plan.template_id]
        targets = template.target_province_codes or [None]
        return [
            PresentationOverlayRecord(
                overlay_id=f"overlay-event-{plan.event_plan_id}-{target or 'national'}",
                kind=PresentationOverlayKind.EVENT,
                source_subject=f"event:{plan.event_plan_id}",
                target_subject=f"province:{target}" if target else None,
                status=plan.intensity.value,
                weight=plan.intensity.magnitude,
                label=plan.name[:160],
                style_semantic="event",
                evidence_refs=plan.evidence_refs,
            )
            for target in targets
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
            SimulationRound.PROVINCE_INITIAL: ["panel:provinces", "panel:decisions"],
            SimulationRound.AUTOMAKER_INITIAL: [
                "panel:automakers",
                "panel:competition",
                "panel:decisions",
            ],
            SimulationRound.PROVINCE_REVISION: [
                "panel:competition",
                "panel:coordination",
                "panel:decisions",
            ],
            SimulationRound.AUTOMAKER_NEGOTIATION: ["panel:negotiation", "panel:decisions"],
            SimulationRound.PROVINCE_COUNTER_RESPONSE: ["panel:negotiation", "panel:decisions"],
            SimulationRound.AUTOMAKER_FINAL: ["panel:automakers", "panel:topk", "panel:decisions"],
            SimulationRound.ENVIRONMENT_SETTLEMENT: [
                "panel:result",
                "panel:methods",
                "panel:decisions",
            ],
        }[round_name]

    def _source_event_ids(
        self,
        *,
        event_types: set[str] | None = None,
        round_name: SimulationRound | None = None,
        branch_id: str | None = None,
    ) -> list[str]:
        return [
            item.event_id
            for item in self.events
            if (event_types is None or item.type in event_types)
            and (round_name is None or item.round is round_name)
            and (branch_id is None or item.branch_id in {None, branch_id})
        ]

    def _event_source_ids(self, branch: BranchRuntimeState) -> list[str]:
        plan = self.world.design.event_plan if self.world.design else None
        if plan is None:
            return []
        boundary = {
            EventTriggerPoint.BEFORE_PROVINCE_INITIAL: None,
            EventTriggerPoint.AFTER_PROVINCE_INITIAL: SimulationRound.PROVINCE_INITIAL,
            EventTriggerPoint.AFTER_AUTOMAKER_INITIAL: SimulationRound.AUTOMAKER_INITIAL,
        }[plan.trigger_point]
        ids = self._source_event_ids(event_types={"design.confirmed"}, branch_id=branch.branch_id)
        if boundary is not None:
            ids.extend(self._source_event_ids(round_name=boundary, branch_id=branch.branch_id))
        return list(dict.fromkeys(ids))

    def _event_markers(self) -> list[PresentationEventMarker]:
        if self.world.design is None or self.world.design.event_plan is None:
            return []
        plan = self.world.design.event_plan
        template = event_scenario_catalog()[plan.template_id]
        payload = {"plan": plan, "events": self._source_event_ids(event_types={"design.confirmed"})}
        return [
            PresentationEventMarker(
                marker_id=f"marker-{plan.event_plan_id}",
                event_plan_id=plan.event_plan_id,
                template_id=plan.template_id,
                title=plan.name[:120],
                family=template.family.value,
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
        self, values: list[PresentationProvinceValue], unit: str
    ) -> list[PresentationKeyChange]:
        ranked = sorted(
            (item for item in values if item.value is not None),
            key=lambda item: (-abs(item.value or 0), item.province_code),
        )[:3]
        return [
            PresentationKeyChange(
                change_id=f"change-{item.province_code}",
                title=self.province_catalog[item.province_code].short_name,
                detail=f"当前冻结值 {item.value:.2f} {unit}。",
                semantic="result",
                evidence_refs=[],
            )
            for item in ranked
        ]
