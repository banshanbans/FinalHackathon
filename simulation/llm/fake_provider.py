import hashlib
import json
from statistics import fmean

from simulation.data import NetworkEdge
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
    PolicyFieldChange,
    ReviewFinding,
)
from simulation.models.common import (
    ApprovalStatus,
    EnterpriseArchetype,
    EnterpriseReasonCode,
    FinancingChoice,
    Participation,
    Phase,
    ProvinceReasonCode,
    ReviewMode,
    UpgradeType,
)
from simulation.models.enterprise import (
    EnterpriseAction,
    EnterpriseActionBatch,
    EnterpriseAggregate,
    EnterpriseGroupProfile,
    EnterpriseGroupState,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import InstrumentMix, PolicySchema, TechnologyMix
from simulation.models.province import ProvinceFeedback, ProvinceProfile, ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics, WorldState


def _clamp(value: float, minimum: float = 0, maximum: float = 1) -> float:
    return max(minimum, min(maximum, value))


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def policy_diff(before: PolicySchema, after: PolicySchema) -> list[PolicyFieldChange]:
    fields = [
        "support_intensity",
        "local_match_requirement",
        "sme_preference",
        "regional_support_bias",
        "instrument_mix.direct_subsidy",
        "instrument_mix.interest_subsidy",
        "instrument_mix.financing_guarantee",
        "technology_mix.digital",
        "technology_mix.green",
        "technology_mix.general",
    ]

    def value(policy: PolicySchema, path: str) -> float:
        current: object = policy
        for part in path.split("."):
            current = getattr(current, part)
        return float(current)

    return [
        PolicyFieldChange(path=path, from_value=value(before, path), to_value=value(after, path))
        for path in fields
        if abs(value(before, path) - value(after, path)) > 1e-9
    ]


class FakeLLMProvider:
    """Deterministic V2 strategy provider for tests, fallback and offline demos."""

    run_mode = "fake"

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralPolicyDirective:
        return CentralPolicyDirective(
            directive_id=_stable_id(
                "directive",
                {"objective": config.objective, "policy": default_policy.model_dump(mode="json")},
            ),
            policy=default_policy.model_copy(deep=True),
            policy_objectives=[
                "推动制造业设备更新",
                "提高中小企业参与",
                "促进绿色转型",
                "保持就业稳定",
                "改善区域可达性",
            ],
            hard_constraints=[
                "instrument_mix_sum_to_1",
                "technology_mix_sum_to_1",
                "human_approval_required",
                "no_real_world_forecast",
            ],
            public_summary="中央政策研判 Agent 已形成设备更新实验草案，等待用户核对并批准。",
            approval_status=ApprovalStatus.DRAFT,
        )

    async def generate_province_action(
        self,
        *,
        profile: ProvinceProfile,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceAction:
        del seed, prompt_version, model_version
        observed = fmean(
            [item.implementation_intensity for item in neighbor_actions.values()] or [0.5]
        )
        intensity = _clamp(
            0.28
            + 0.30 * profile.advanced_manufacturing_base
            + 0.18 * profile.fiscal_capacity
            + 0.12 * profile.transition_pressure
            + (0.06 * observed if phase == Phase.T4 else 0)
        )
        local_match = _clamp(
            policy.local_match_requirement
            * (0.66 + 0.48 * profile.fiscal_capacity - 0.18 * profile.fiscal_conservatism)
        )
        guarantee_shift = 0.10 * (1 - profile.credit_access)
        direct = _clamp(policy.instrument_mix.direct_subsidy - guarantee_shift * 0.55)
        interest = _clamp(policy.instrument_mix.interest_subsidy + guarantee_shift * 0.20)
        direct = round(direct, 6)
        interest = round(interest, 6)
        guarantee = round(1 - direct - interest, 6)
        instrument_mix = InstrumentMix(
            direct_subsidy=direct,
            interest_subsidy=interest,
            financing_guarantee=guarantee,
        )
        digital = _clamp(
            policy.technology_mix.digital
            + 0.08 * (profile.digital_infrastructure - profile.green_energy_base)
        )
        green = _clamp(
            policy.technology_mix.green
            + 0.08 * (profile.green_energy_base - profile.digital_infrastructure)
        )
        digital = round(digital, 6)
        green = round(green, 6)
        general = round(1 - digital - green, 6)
        technology_mix = TechnologyMix(digital=digital, green=green, general=general)
        requested = _clamp(
            0.55 * (1 - profile.fiscal_capacity) + 0.35 * profile.transition_pressure
        )
        reasons = [ProvinceReasonCode.MANUFACTURING_BASE]
        if profile.credit_access < 0.55:
            reasons.append(ProvinceReasonCode.FINANCING_GAP)
        if profile.fiscal_capacity < 0.5:
            reasons.append(ProvinceReasonCode.FISCAL_CONSTRAINT)
        if profile.transition_pressure > 0.62:
            reasons.append(ProvinceReasonCode.GREEN_TRANSITION)
        if requested > 0.55:
            reasons.append(ProvinceReasonCode.CENTRAL_SUPPORT_REQUEST)
        return ProvinceAction(
            action_id=_stable_id(
                f"province_{profile.province_code}_{phase.value}",
                {
                    "profile": profile.model_dump(mode="json"),
                    "state": state.model_dump(mode="json"),
                    "policy": policy.model_dump(mode="json"),
                    "neighbors": sorted(neighbor_actions),
                },
            ),
            province_code=profile.province_code,
            phase=phase,
            implementation_intensity=round(intensity, 4),
            local_match_ratio=round(local_match, 4),
            instrument_mix=instrument_mix,
            sme_preference=round(_clamp(policy.sme_preference + 0.12 * profile.sme_density), 4),
            regional_delivery_focus=round(_clamp(0.45 + 0.35 * (1 - profile.credit_access)), 4),
            technology_mix=technology_mix,
            requested_central_support=round(requested, 4),
            reason_codes=reasons[:5],
            public_summary="结合制造基础与融资约束配置补贴、贴息和担保工具。",
            run_mode=self.run_mode,
        )

    @staticmethod
    def _upgrade_type(profile: EnterpriseGroupProfile, policy: PolicySchema) -> UpgradeType:
        scores = {
            UpgradeType.DIGITAL: profile.digital_readiness * policy.technology_mix.digital,
            UpgradeType.GREEN: profile.green_transition_pressure * policy.technology_mix.green,
            UpgradeType.GENERAL: profile.equipment_age_pressure * policy.technology_mix.general,
        }
        return max(scores, key=scores.get)

    @staticmethod
    def _financing_choice(
        profile: EnterpriseGroupProfile, province_action: ProvinceAction
    ) -> FinancingChoice:
        if profile.financing_constraint >= 0.62:
            return FinancingChoice.GUARANTEE_LOAN
        if profile.archetype == EnterpriseArchetype.TECHNOLOGY_SME:
            return FinancingChoice.INTEREST_SUBSIDY
        if profile.cash_flow_resilience >= 0.74:
            return FinancingChoice.SELF_FUNDED
        if province_action.instrument_mix.direct_subsidy >= 0.42:
            return FinancingChoice.DIRECT_SUBSIDY
        return FinancingChoice.INTEREST_SUBSIDY

    async def generate_enterprise_actions_batch(
        self,
        *,
        province_profile: ProvinceProfile,
        province_action: ProvinceAction,
        enterprise_profiles: list[EnterpriseGroupProfile],
        enterprise_states: dict[str, EnterpriseGroupState],
        policy: PolicySchema,
        phase: Phase,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> EnterpriseActionBatch:
        del seed, prompt_version, model_version
        actions: list[EnterpriseAction] = []
        for profile in enterprise_profiles:
            state = enterprise_states[profile.enterprise_id]
            support = (
                policy.support_intensity / 100 * province_action.implementation_intensity
                + 0.18 * province_profile.credit_access
                + (0.14 * policy.sme_preference if "sme" in profile.archetype.value else 0)
                - 0.46 * profile.financing_constraint
                + 0.18 * profile.equipment_age_pressure
            )
            if phase == Phase.T4:
                support += 0.04 * (state.renewal_willingness / 100 - 0.5)
            if support >= 0.52:
                participation = Participation.PARTICIPATE
            elif support >= 0.34:
                participation = Participation.CONDITIONAL
            elif support >= 0.20:
                participation = Participation.WAIT
            else:
                participation = Participation.DECLINE
            active = participation in {Participation.PARTICIPATE, Participation.CONDITIONAL}
            upgrade = self._upgrade_type(profile, policy) if active else UpgradeType.NONE
            financing = (
                self._financing_choice(profile, province_action)
                if participation != Participation.DECLINE
                else FinancingChoice.NONE
            )
            if participation == Participation.WAIT:
                financing = FinancingChoice.NONE
            investment = 0.0 if not active else _clamp(0.36 + 0.46 * support)
            request = _clamp(
                0.62 * profile.financing_constraint
                + 0.28 * profile.equipment_age_pressure
                - 0.18 * province_profile.credit_access
            )
            reasons = [EnterpriseReasonCode.POLICY_MATCH]
            if profile.financing_constraint > 0.62:
                reasons.append(EnterpriseReasonCode.CASH_FLOW_CONSTRAINT)
                reasons.append(EnterpriseReasonCode.GUARANTEE_NEEDED)
            if participation == Participation.WAIT:
                reasons.append(EnterpriseReasonCode.DEMAND_UNCERTAINTY)
            if financing == FinancingChoice.INTEREST_SUBSIDY:
                reasons.append(EnterpriseReasonCode.CREDIT_ACCESS)
            if upgrade == UpgradeType.GREEN:
                reasons.append(EnterpriseReasonCode.GREEN_COMPLIANCE)
            actions.append(
                EnterpriseAction(
                    action_id=_stable_id(
                        f"enterprise_{profile.enterprise_id}_{phase.value}",
                        {
                            "profile": profile.model_dump(mode="json"),
                            "state": state.model_dump(mode="json"),
                            "policy": policy.model_dump(mode="json"),
                            "province_action": province_action.model_dump(mode="json"),
                        },
                    ),
                    enterprise_id=profile.enterprise_id,
                    province_code=profile.province_code,
                    archetype=profile.archetype,
                    phase=phase,
                    participation=participation,
                    upgrade_type=upgrade,
                    financing_choice=financing,
                    investment_intensity=round(investment, 4),
                    requested_support=round(request, 4),
                    reason_codes=reasons[:5],
                    public_summary=(
                        "在当前支持与融资条件下参与设备更新。"
                        if active
                        else "当前融资与需求约束较强，暂不启动设备更新。"
                    ),
                )
            )
        return EnterpriseActionBatch(
            batch_id=_stable_id(
                f"batch_{province_profile.province_code}_{phase.value}",
                [item.action_id for item in actions],
            ),
            province_code=province_profile.province_code,
            phase=phase,
            actions=actions,
            run_mode=self.run_mode,
        )

    async def generate_province_feedback(
        self,
        *,
        profile: ProvinceProfile,
        state: ProvinceState,
        aggregate: EnterpriseAggregate,
        enterprise_actions: list[EnterpriseAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback:
        del policy, seed, prompt_version, model_version
        constrained = sorted(
            enterprise_actions, key=lambda item: item.requested_support, reverse=True
        )[:2]
        reasons = [ProvinceReasonCode.MANUFACTURING_BASE]
        if aggregate.sme_financing_accessibility_index < 55:
            reasons.extend(
                [ProvinceReasonCode.FINANCING_GAP, ProvinceReasonCode.SME_ACCESS_PRIORITY]
            )
        if state.fiscal_pressure_index > 55:
            reasons.append(ProvinceReasonCode.FISCAL_CONSTRAINT)
        return ProvinceFeedback(
            feedback_id=_stable_id(
                f"feedback_{profile.province_code}",
                {
                    "state": state.model_dump(mode="json"),
                    "aggregate": aggregate.model_dump(mode="json"),
                },
            ),
            province_code=profile.province_code,
            implementation_assessment=(
                "融资可达性仍是主要约束"
                if aggregate.sme_financing_accessibility_index < 55
                else "设备更新参与度稳步形成"
            ),
            priority_enterprise_groups=[item.archetype.value for item in constrained],
            requested_central_support=round(
                fmean(item.requested_support for item in enterprise_actions), 4
            ),
            reason_codes=reasons[:5],
            evidence_refs=[
                f"metric:{profile.province_code}:sme_financing_accessibility_index:T2",
                f"enterprise:{constrained[0].enterprise_id}:action:T2",
            ],
            public_summary="地方反馈显示企业参与存在分化，融资约束集中在中小企业群体。",
            run_mode=self.run_mode,
        )

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        feedback: dict[str, ProvinceFeedback],
        enterprise_actions: dict[str, EnterpriseAction],
    ) -> list[CentralInterventionProposal]:
        del states, enterprise_actions
        target_guarantee = min(0.36, policy.instrument_mix.financing_guarantee + 0.12)
        target_interest = min(0.40, policy.instrument_mix.interest_subsidy + 0.03)
        target_direct = 1 - target_guarantee - target_interest
        proposed = policy.model_copy(
            update={
                "instrument_mix": InstrumentMix(
                    direct_subsidy=round(target_direct, 6),
                    interest_subsidy=round(target_interest, 6),
                    financing_guarantee=round(target_guarantee, 6),
                ),
                "sme_preference": min(0.82, policy.sme_preference + 0.14),
                "regional_support_bias": max(0.35, policy.regional_support_bias),
            },
            deep=True,
        )
        support_request = fmean(item.requested_central_support for item in feedback.values())
        return [
            CentralInterventionProposal(
                proposal_id=_stable_id(
                    "central_t3",
                    {
                        "policy": policy.model_dump(mode="json"),
                        "metrics": metrics.model_dump(mode="json"),
                    },
                ),
                proposed_policy=proposed,
                parameter_changes=policy_diff(policy, proposed),
                target_metrics=[
                    "enterprise_participation_index",
                    "sme_financing_accessibility_index",
                    "regional_gap_index",
                ],
                expected_directions={
                    "enterprise_participation_index": "increase",
                    "sme_financing_accessibility_index": "increase",
                    "regional_gap_index": "decrease",
                    "local_fiscal_pressure_index": "may_increase",
                },
                tradeoffs=["担保与区域倾斜提高可达性的同时可能增加财政压力。"],
                evidence_refs=[
                    "metric:national:sme_financing_accessibility_index:T2",
                    "metric:national:regional_gap_index:T2",
                    f"feedback:mean_support_request:{support_request:.3f}",
                ],
                public_summary="".join(
                    [
                        "中央政策研判 Agent 建议提高担保、SME 与区域倾斜；",
                        "预期方向待同源分支验证。",
                    ]
                ),
            )
        ]

    async def generate_central_review(self, result: ComparisonResult | WorldState) -> CentralReview:
        if isinstance(result, ComparisonResult):
            access = result.national_metrics["sme_financing_accessibility_index"]
            fiscal = result.national_metrics["local_fiscal_pressure_index"]
            participation = result.national_metrics["enterprise_participation_index"]
            findings = [
                ReviewFinding(
                    title="企业参与变化",
                    summary=f"干预方案相对原始方案变化 {participation.delta:+.1f} 指数点。",
                    evidence_refs=["comparison:national_metrics:enterprise_participation_index"],
                ),
                ReviewFinding(
                    title="融资可达性与财政代价",
                    summary=f"SME 融资可达性变化 {access.delta:+.1f} 指数点。",
                    evidence_refs=["comparison:national_metrics:sme_financing_accessibility_index"],
                    tradeoff=f"地方财政压力同步变化 {fiscal.delta:+.1f} 指数点。",
                ),
            ]
            review_mode = ReviewMode.COMPARISON
            public_summary = "".join(
                [
                    "中央政策研判 Agent 已完成同源 A/B 复盘，",
                    "请结合参与、可达性与财政代价判断。",
                ]
            )
            payload = result.model_dump(mode="json", exclude={"central_review"})
        else:
            metrics = result.national_metrics
            findings = [
                ReviewFinding(
                    title="原始方案单线结算",
                    summary=(
                        f"企业参与指数为 {metrics.enterprise_participation_index:.1f} / 100，"
                        "本次未创建干预分支。"
                    ),
                    evidence_refs=["world:control:national_metrics:T5"],
                    tradeoff=(
                        f"地方财政压力指数为 {metrics.local_fiscal_pressure_index:.1f} / 100。"
                    ),
                )
            ]
            review_mode = ReviewMode.SINGLE_BRANCH
            public_summary = "用户拒绝干预后，原始方案已单线结算；系统未伪造 A/B 结果。"
            payload = result.model_dump(mode="json", exclude={"central_review"})
        return CentralReview(
            review_id=_stable_id("review", payload),
            review_mode=review_mode,
            findings=findings,
            limitations=[
                "结果只适用于当前数据、参数、机制版本与 seed。",
                "企业群体为合成主体，指数不映射现实金额、GDP、就业或生产率。",
            ],
            public_summary=public_summary,
        )
