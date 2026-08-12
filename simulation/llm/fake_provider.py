import hashlib
import json
from statistics import fmean

from simulation.data import NetworkEdge
from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.automaker import (
    AutomakerAction,
    AutomakerProfile,
    AutomakerState,
    FacilityAction,
    ProvinceMarketAction,
)
from simulation.models.central import (
    CentralInterventionProposal,
    CentralReview,
    CentralSubsidyDirective,
    PolicyFieldChange,
    ReviewFinding,
)
from simulation.models.common import (
    AdjustmentDirection,
    ApprovalStatus,
    AutomakerReasonCode,
    ChannelStrategy,
    EventPerception,
    EventPolicyFocus,
    EventTemplateId,
    ExpectedDirection,
    FacilityActionKind,
    PeerResponseMode,
    Phase,
    PolicyStatus,
    ProvinceConstraint,
    ProvinceReasonCode,
    ProvinceSignalType,
    ReviewMode,
    RunMode,
    SignalDirection,
    SignalSeverity,
    SimulatedRoiBand,
    StrategyAssessment,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    AdjustmentIntent,
    CentralShareRecommendation,
    ProvinceAction,
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
    ProvinceSignal,
    ProvinceState,
    SubsidyMix,
)
from simulation.models.scenario import (
    EventScenario,
    ProvinceEventResponse,
    ProvinceEventSignal,
    SubsidyMixDelta,
)
from simulation.models.world import ComparisonResult, NationalMetrics, WorldState


def _clamp(value: float, low: float = 0, high: float = 1) -> float:
    return max(low, min(high, value))


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def policy_diff(before: PolicySchema, after: PolicySchema) -> list[PolicyFieldChange]:
    return [
        PolicyFieldChange(
            path=path, from_value=getattr(before, path), to_value=getattr(after, path)
        )
        for path in ("west_central_share", "central_central_share", "east_central_share")
        if abs(getattr(before, path) - getattr(after, path)) > 1e-9
    ]


class FakeLLMProvider:
    """Deterministic strategy provider used for tests, cache generation and fallback."""

    run_mode = "fake"

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralSubsidyDirective:
        del config
        return CentralSubsidyDirective(
            policy=default_policy.model_copy(deep=True),
            policy_objectives=[
                "缩小省域新能源汽车发展差距",
                "平衡中央与地方财政压力",
                "观察真实头部车企的模拟布局响应",
            ],
            hard_constraints=[
                "human_approval_required",
                "only_three_regional_shares_change",
                "no_real_world_forecast",
            ],
            evidence_refs=["policy:ndrc-2025-nev-cost-sharing", "method:nev-policy-env-v1"],
            public_summary="中央 Agent 已形成新能源汽车以旧换新共担比例草案，待人工审批。",
            approval_status=ApprovalStatus.AWAITING_APPROVAL,
        )

    async def generate_province_action(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
        previous_action: ProvinceAction | None,
        feedback: ProvinceFeedback | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceAction:
        del seed, prompt_version, model_version, feedback
        central_share = policy.central_share_for_region(profile.policy_region)
        peer_support = fmean(
            [item.overall_support_intensity for item in neighbor_actions.values()] or [0.5]
        )
        fiscal_space = (
            0.55 * profile.fiscal_capacity
            + 0.25 * (1 - profile.fiscal_rigidity)
            + 0.20 * central_share
        )
        support = _clamp(
            0.22
            + 0.42 * fiscal_space
            + 0.18 * profile.nev_industry_base
            + (0.06 * peer_support if phase is Phase.Y2_Q1 else 0)
        )
        consumer = _clamp(
            0.34 + 0.28 * profile.market_scale + 0.18 * profile.willingness_to_pay_index, 0.25, 0.70
        )
        fixed = _clamp(
            0.18 + 0.30 * profile.nev_industry_base + 0.14 * (1 - profile.land_cost_index),
            0.12,
            0.50,
        )
        variable = max(0.08, 1 - consumer - fixed)
        total = consumer + fixed + variable
        consumer_share = round(consumer / total, 6)
        fixed_share = round(fixed / total, 6)
        mix = SubsidyMix(
            consumer=consumer_share,
            fixed_cost=fixed_share,
            variable_cost=round(1 - consumer_share - fixed_share, 6),
        )
        mode = (
            PeerResponseMode.FOLLOW
            if persona.axes.peer_response_sensitivity >= 0.63
            else (
                PeerResponseMode.DIFFERENTIATE
                if persona.axes.industry_attraction >= 0.65
                else PeerResponseMode.HOLD
            )
        )
        observed = [edge.target for edge in sorted(related, key=lambda item: -item.weight)[:3]]
        reasons = [ProvinceReasonCode.CENTRAL_SHARE_RELIEF, ProvinceReasonCode.CONSUMER_DEMAND]
        if profile.nev_industry_base >= 0.55:
            reasons.append(ProvinceReasonCode.INDUSTRY_BASE)
        if profile.fiscal_capacity < 0.5:
            reasons.append(ProvinceReasonCode.FISCAL_CONSTRAINT)
        return ProvinceAction(
            action_id=_stable_id(
                f"province_{profile.province_code}_{phase.value}",
                {
                    "policy": policy.model_dump(mode="json"),
                    "profile": profile.province_code,
                    "previous": previous_action.action_id if previous_action else None,
                },
            ),
            previous_action_id=previous_action.action_id if previous_action else None,
            province_code=profile.province_code,
            phase=phase,
            overall_support_intensity=round(support, 4),
            subsidy_mix=mix,
            peer_response_mode=mode,
            observed_peer_codes=observed,
            reason_codes=reasons[:5],
            summary="结合地方财政空间、消费潜力和产业基础配置三类新能源汽车支持工具。",
            run_mode=RunMode(self.run_mode),
        )

    async def generate_automaker_action(
        self,
        *,
        profile: AutomakerProfile,
        state: AutomakerState,
        province_profiles: dict[str, ProvinceProfile],
        province_actions: dict[str, ProvinceAction],
        policy: PolicySchema,
        phase: Phase,
        previous_action: AutomakerAction | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> AutomakerAction:
        del policy, seed, prompt_version, model_version
        coverage = {
            item.province_code: item.coverage_index for item in profile.channel_coverage_by_province
        }
        scores: dict[str, float] = {}
        market_actions: list[ProvinceMarketAction] = []
        for code in MAINLAND_PROVINCE_CODES:
            province = province_profiles[code]
            action = province_actions[code]
            score = _clamp(
                0.24 * province.willingness_to_pay_index
                + 0.24 * action.overall_support_intensity
                + 0.18 * province.nev_industry_base
                + 0.14 * (1 - province.battery_supply_distance_index)
                + 0.12 * coverage[code]
                + 0.08 * profile.sales_growth_index
            )
            scores[code] = score
            strategy = (
                ChannelStrategy.EXPAND
                if score >= 0.62
                else (ChannelStrategy.MAINTAIN if score >= 0.42 else ChannelStrategy.REDUCE)
            )
            market_actions.append(
                ProvinceMarketAction(
                    province_code=code,
                    sales_investment_intensity=round(score, 4),
                    channel_strategy=strategy,
                )
            )
        facility_actions: list[FacilityAction] = []
        for code in sorted(scores, key=scores.get, reverse=True)[:3]:
            score = scores[code]
            if score >= 0.66 and profile.liquidity_index >= 0.55:
                kind = (
                    FacilityActionKind.NEW_PLANT
                    if code not in {x.province_code for x in profile.production_footprint}
                    else FacilityActionKind.EXPAND
                )
            elif profile.capacity_utilization_index >= 0.88:
                kind = FacilityActionKind.DELAY
            else:
                continue
            facility_actions.append(
                FacilityAction(
                    province_code=code, action=kind, investment_intensity=round(score, 4)
                )
            )
        mean_score = fmean(scores.values())
        roi = (
            SimulatedRoiBand.HIGH
            if mean_score >= 0.62
            else (SimulatedRoiBand.MEDIUM if mean_score >= 0.45 else SimulatedRoiBand.LOW)
        )
        return AutomakerAction(
            action_id=_stable_id(
                f"automaker_{profile.automaker_id}_{phase.value}",
                {
                    "scores": scores,
                    "previous": previous_action.action_id if previous_action else None,
                },
            ),
            previous_action_id=previous_action.action_id if previous_action else None,
            automaker_id=profile.automaker_id,
            phase=phase,
            province_market_actions=market_actions,
            facility_actions=facility_actions,
            simulated_roi_band=roi,
            reason_codes=[
                AutomakerReasonCode.CONSUMER_WTP,
                AutomakerReasonCode.SUBSIDY_SUPPORT,
                AutomakerReasonCode.INDUSTRY_BASE,
            ],
            summary="按 31 省需求、支持强度和产业条件配置模拟销售投入与设施动作。",
            run_mode=RunMode(self.run_mode),
        )

    async def generate_province_feedback(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        automaker_actions: dict[str, AutomakerAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback:
        del persona, seed, prompt_version, model_version
        sales = fmean(
            next(
                item.sales_investment_intensity
                for item in action.province_market_actions
                if item.province_code == profile.province_code
            )
            for action in automaker_actions.values()
        )
        facilities = sum(
            any(
                item.province_code == profile.province_code
                and item.action is not FacilityActionKind.DELAY
                for item in action.facility_actions
            )
            for action in automaker_actions.values()
        )
        constrained = state.fiscal_pressure_index > 60
        assessment = (
            StrategyAssessment.CONSTRAINED
            if constrained
            else (StrategyAssessment.EFFECTIVE if sales >= 0.55 else StrategyAssessment.MIXED)
        )
        recommendation = CentralShareRecommendation()
        region_field = f"{profile.policy_region.value}_delta"
        recommendation = recommendation.model_copy(
            update={region_field: 0.02 if constrained else 0.01}
        )
        return ProvinceFeedback(
            feedback_id=_stable_id(
                f"feedback_{profile.province_code}",
                {"state": state.model_dump(mode="json"), "sales": sales},
            ),
            province_code=profile.province_code,
            strategy_assessment=assessment,
            signals=[
                ProvinceSignal(
                    signal_type=ProvinceSignalType.AUTOMAKER_SALES,
                    direction=SignalDirection.POSITIVE if sales >= 0.5 else SignalDirection.NEUTRAL,
                    severity=SignalSeverity.MEDIUM,
                    evidence_refs=[f"metric:{profile.province_code}:automaker-sales"],
                ),
                ProvinceSignal(
                    signal_type=ProvinceSignalType.FACILITY_ACTIVITY,
                    direction=SignalDirection.POSITIVE if facilities else SignalDirection.NEUTRAL,
                    severity=SignalSeverity.LOW,
                    evidence_refs=[f"metric:{profile.province_code}:facility-activity"],
                ),
            ],
            constraints=[ProvinceConstraint.FISCAL_RIGIDITY],
            adjustment_intents=[
                AdjustmentIntent(
                    path="overall_support_intensity",
                    direction=AdjustmentDirection.HOLD
                    if not constrained
                    else AdjustmentDirection.DECREASE,
                    reason="根据首年财政压力保持或收敛地方支持强度。",
                )
            ],
            central_share_recommendation=recommendation,
            reason_codes=[
                ProvinceReasonCode.FISCAL_CONSTRAINT
                if constrained
                else ProvinceReasonCode.CONSUMER_DEMAND
            ],
            evidence_refs=[
                f"metric:{profile.province_code}:development",
                f"action:{current_action.action_id}",
            ],
            summary="首年复盘聚合财政、需求与车企响应信号，形成次年调整意向。",
            run_mode=RunMode(self.run_mode),
        )

    async def generate_province_event_signal(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        exposure: float,
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventSignal:
        del state, current_action, seed, prompt_version, model_version
        focus = {
            EventTemplateId.BATTERY_NODE_UPGRADE_SICHUAN: (
                EventPolicyFocus.SUPPLY_CHAIN_COORDINATION
            ),
            EventTemplateId.INTELLIGENT_DRIVING_UPGRADE: EventPolicyFocus.REGULATORY_PILOT,
            EventTemplateId.L3_ENTERPRISE_LIABILITY_INCREASE: EventPolicyFocus.REGULATORY_PILOT,
            EventTemplateId.OIL_PRICE_RISE: EventPolicyFocus.CONSUMER_SUPPORT,
            EventTemplateId.OIL_PRICE_FALL: EventPolicyFocus.FISCAL_RESERVE,
        }[scenario.template_id]
        perception = (
            EventPerception.OPPORTUNITY
            if scenario.template_id is not EventTemplateId.L3_ENTERPRISE_LIABILITY_INCREASE
            and scenario.template_id is not EventTemplateId.OIL_PRICE_FALL
            else EventPerception.MIXED
        )
        peers = [edge.target for edge in sorted(related, key=lambda item: -item.weight)[:2]]
        return ProvinceEventSignal(
            signal_id=_stable_id(
                f"event_signal_{profile.province_code}",
                {"scenario": scenario.scenario_id, "exposure": exposure, "focus": focus.value},
            ),
            scenario_id=scenario.scenario_id,
            province_code=profile.province_code,
            exposure=round(exposure, 4),
            perception=perception,
            policy_focus=focus,
            proposed_peer_codes=peers,
            evidence_refs=[f"scenario:{scenario.scenario_id}", f"profile:{profile.province_code}"],
            summary="结合事件暴露、产业条件与稳定画像发布省际可观察政策信号。",
            run_mode=RunMode(self.run_mode),
        )

    async def generate_province_event_response(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        own_signal: ProvinceEventSignal,
        peer_signals: dict[str, ProvinceEventSignal],
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventResponse:
        del state, seed, prompt_version, model_version
        allowed = [edge.target for edge in sorted(related, key=lambda item: -item.weight)]
        observed = {code: peer_signals[code] for code in allowed if code in peer_signals}
        coordination_candidates = [
            code
            for code, signal in observed.items()
            if profile.province_code in signal.proposed_peer_codes
            or code in own_signal.proposed_peer_codes
        ]
        coordinate = persona.axes.supply_chain_coordination >= 0.58 and bool(
            coordination_candidates
        )
        if coordinate:
            mode = PeerResponseMode.COORDINATE
        elif persona.axes.peer_response_sensitivity >= 0.60:
            mode = PeerResponseMode.FOLLOW
        elif persona.axes.industry_attraction >= 0.62:
            mode = PeerResponseMode.DIFFERENTIATE
        else:
            mode = PeerResponseMode.HOLD
        shift = min(0.06, 0.08 * scenario.magnitude)
        mix = current_action.subsidy_mix
        delta = SubsidyMixDelta()
        if own_signal.policy_focus is EventPolicyFocus.CONSUMER_SUPPORT:
            moved = min(shift, mix.fixed_cost / 2 + mix.variable_cost / 2)
            delta = SubsidyMixDelta(consumer=moved, fixed_cost=-moved / 2, variable_cost=-moved / 2)
        elif own_signal.policy_focus is EventPolicyFocus.FIXED_COST_SUPPORT:
            moved = min(shift, mix.consumer / 2 + mix.variable_cost / 2)
            delta = SubsidyMixDelta(consumer=-moved / 2, fixed_cost=moved, variable_cost=-moved / 2)
        elif own_signal.policy_focus in {
            EventPolicyFocus.VARIABLE_COST_SUPPORT,
            EventPolicyFocus.SUPPLY_CHAIN_COORDINATION,
        }:
            moved = min(shift, mix.consumer / 2 + mix.fixed_cost / 2)
            delta = SubsidyMixDelta(consumer=-moved / 2, fixed_cost=-moved / 2, variable_cost=moved)
        peer_codes = list(observed)
        return ProvinceEventResponse(
            response_id=_stable_id(
                f"event_response_{profile.province_code}",
                {
                    "scenario": scenario.scenario_id,
                    "signal": own_signal.signal_id,
                    "peers": [item.signal_id for item in observed.values()],
                    "mode": mode.value,
                },
            ),
            scenario_id=scenario.scenario_id,
            province_code=profile.province_code,
            observed_signal_ids=[observed[code].signal_id for code in peer_codes],
            observed_peer_codes=peer_codes,
            response_mode=mode,
            policy_focus=own_signal.policy_focus,
            response_intensity=round(
                _clamp(
                    0.35
                    + 0.45 * own_signal.exposure
                    + 0.20 * persona.axes.peer_response_sensitivity
                ),
                4,
            ),
            subsidy_mix_delta=delta,
            coordination_target_codes=coordination_candidates[:1] if coordinate else [],
            evidence_refs=[
                f"scenario:{scenario.scenario_id}",
                f"interaction:{own_signal.signal_id}",
            ],
            summary="读取冻结 Peer 信号后形成有限响应；最终结果由确定性环境统一传播。",
            run_mode=RunMode(self.run_mode),
        )

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        feedback: dict[str, ProvinceFeedback],
        automaker_actions: dict[str, AutomakerAction],
    ) -> list[CentralInterventionProposal]:
        del states, feedback, automaker_actions
        proposed = policy.model_copy(
            update={
                "west_central_share": min(1, policy.west_central_share + 0.02),
                "central_central_share": min(1, policy.central_central_share + 0.01),
                "status": PolicyStatus.AWAITING_APPROVAL,
            },
            deep=True,
        )
        changes = policy_diff(policy, proposed)
        return [
            CentralInterventionProposal(
                proposed_policy=proposed,
                parameter_changes=changes,
                expected_directions={
                    "regional_development_gap": ExpectedDirection.MAY_DECREASE,
                    "central_fiscal_burden": ExpectedDirection.INCREASE,
                },
                tradeoffs=[
                    "中央财政负担可能上升",
                    "地方财政空间改善幅度取决于省级工具选择与车企响应",
                ],
                evidence_refs=[
                    "metric:national:regional_development_gap",
                    "method:nev-policy-env-v1",
                ],
                public_summary=(
                    "建议西部中央承担比例提高 2 个百分点、中部提高 1 个百分点；"
                    f"当前 Gap 为 {metrics.regional_development_gap:.2f}。"
                ),
                approval_status=ApprovalStatus.AWAITING_APPROVAL,
            )
        ]

    async def generate_central_review(self, result: ComparisonResult | WorldState) -> CentralReview:
        if isinstance(result, ComparisonResult):
            summary = f"同源 A/B 的 ΔGap 为 {result.delta_gap:+.3f} 指数点；负值表示差距缩小。"
            mode = ReviewMode.COMPARISON
            refs = ["comparison:latest"]
        else:
            summary = "用户拒绝干预，仅完成原始方案次年复盘，不生成伪 A/B 结论。"
            mode = ReviewMode.SINGLE_BRANCH
            refs = ["metric:national:control"]
        return CentralReview(
            review_mode=mode,
            findings=[ReviewFinding(title="年度机制结果", summary=summary, evidence_refs=refs)],
            limitations=[
                "结果是当前数据与机制参数下的模拟指数",
                "不代表真实车企承诺或现实政策预测",
            ],
            public_summary=summary,
        )
