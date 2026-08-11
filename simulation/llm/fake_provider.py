import hashlib
import json
from statistics import mean

from simulation.data import NetworkEdge
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
    ParameterChange,
    ReviewFinding,
)
from simulation.models.common import (
    ApprovalStatus,
    Industry,
    InteractionStrategy,
    Phase,
    ReasonCode,
    Stance,
    TalentStrategy,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics


def _clamp(value: float, minimum: float = 0, maximum: float = 1) -> float:
    return max(minimum, min(maximum, value))


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


class FakeLLMProvider:
    """Deterministic structured decision policy used for tests and offline demos."""

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
                config.objective,
                "在创新、就业、区域均衡与财政效率之间保留可审计权衡",
            ],
            hard_constraints=[
                "evaluation_weights_sum_to_1",
                "approved_policy_domain_only",
                "human_approval_required",
            ],
            public_summary="国务院 Agent 已形成战略性新兴产业扶持实验指令，等待用户审批。",
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
    ) -> ProvinceAction:
        industry_scores = {
            Industry.AI: profile.ai_base,
            Industry.ADVANCED_MANUFACTURING: profile.advanced_manufacturing_base,
            Industry.GREEN_ENERGY: profile.green_energy_base,
        }
        allowed_scores = {
            industry: score
            for industry, score in industry_scores.items()
            if industry in policy.priority_industries
        }
        priorities = sorted(allowed_scores, key=allowed_scores.get, reverse=True)[:2]
        fit = mean(allowed_scores[industry] for industry in priorities)
        observed_competition = mean(
            [
                action.implementation_intensity
                for action in neighbor_actions.values()
                if action.interaction_strategy == InteractionStrategy.COMPETE
            ]
            or [0]
        )
        intensity = _clamp(
            0.28
            + 0.43 * fit
            + 0.23 * profile.fiscal_capacity
            - 0.14 * profile.fiscal_conservatism
            + (0.06 * observed_competition if phase in {Phase.T3, Phase.T4} else 0)
        )
        budget = _clamp(
            0.20 + 0.50 * profile.fiscal_capacity + 0.18 * fit - 0.22 * profile.fiscal_conservatism
        )
        request_support = _clamp(
            0.62 * (1 - profile.fiscal_capacity) + 0.30 * profile.transition_pressure
        )
        if intensity >= 0.72:
            stance = Stance.AGGRESSIVE
        elif intensity >= 0.52:
            stance = Stance.BALANCED
        else:
            stance = Stance.CAUTIOUS

        cooperation_score = profile.cooperation_tendency * policy.cooperation_incentive
        if cooperation_score >= 0.42:
            interaction = InteractionStrategy.COOPERATE
        elif profile.talent_attractiveness >= 0.70 and intensity >= 0.65:
            interaction = InteractionStrategy.COMPETE
        else:
            interaction = InteractionStrategy.OBSERVE
        targets = (
            [edge.target for edge in related[:2]]
            if interaction != InteractionStrategy.OBSERVE
            else []
        )

        if priorities[0] == Industry.GREEN_ENERGY and profile.transition_pressure >= 0.65:
            talent_strategy = TalentStrategy.RESKILL
        elif profile.talent_attractiveness >= 0.72:
            talent_strategy = TalentStrategy.EXPAND
        elif profile.employment_pressure >= 0.62:
            talent_strategy = TalentStrategy.RETAIN
        else:
            talent_strategy = TalentStrategy.STABLE

        reasons: list[ReasonCode] = [ReasonCode.HIGH_INDUSTRY_FIT]
        if profile.fiscal_capacity >= 0.65:
            reasons.append(ReasonCode.HIGH_FISCAL_CAPACITY)
        else:
            reasons.append(ReasonCode.FISCAL_CONSTRAINT)
        if profile.transition_pressure >= 0.65:
            reasons.append(ReasonCode.TRANSITION_PRIORITY)
        if interaction == InteractionStrategy.COMPETE:
            reasons.append(ReasonCode.TALENT_COMPETITION)
        elif interaction == InteractionStrategy.COOPERATE:
            reasons.append(ReasonCode.REGIONAL_COOPERATION)
        if request_support >= 0.60:
            reasons.append(ReasonCode.CENTRAL_SUPPORT_REQUEST)

        industry_names = {
            Industry.AI: "人工智能",
            Industry.ADVANCED_MANUFACTURING: "先进制造",
            Industry.GREEN_ENERGY: "绿色能源",
        }
        strategy_text = {
            InteractionStrategy.COMPETE: "并关注区域竞争",
            InteractionStrategy.COOPERATE: "并推动跨省协作",
            InteractionStrategy.OBSERVE: "并保持审慎观察",
        }[interaction]
        return ProvinceAction(
            action_id=_stable_id(
                f"act_{profile.province_code}_{phase.value}",
                {
                    "state": state.model_dump(mode="json"),
                    "policy": policy.model_dump(mode="json"),
                    "neighbors": {
                        code: action.action_id for code, action in sorted(neighbor_actions.items())
                    },
                },
            ),
            province_code=profile.province_code,
            phase=phase,
            stance=stance,
            implementation_intensity=round(intensity, 4),
            local_budget_ratio=round(budget, 4),
            priority_industries=priorities,
            talent_strategy=talent_strategy,
            interaction_strategy=interaction,
            target_provinces=targets,
            requested_central_support=round(request_support, 4),
            reason_codes=reasons[:5],
            public_summary=(f"围绕{industry_names[priorities[0]]}配置地方资源，{strategy_text}。"),
            run_mode=self.run_mode,
        )

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        actions: dict[str, ProvinceAction],
    ) -> list[CentralInterventionProposal]:
        target_bias = max(policy.regional_bias, 0.45)
        target_cooperation = max(policy.cooperation_incentive, 0.65)
        support_requests = mean(
            [action.requested_central_support for action in actions.values()] or [0]
        )
        return [
            CentralInterventionProposal(
                proposal_id=_stable_id(
                    "central_t3",
                    {
                        "policy": policy.model_dump(mode="json"),
                        "metrics": metrics.model_dump(mode="json"),
                    },
                ),
                parameter_changes={
                    "regional_bias": ParameterChange(
                        from_value=policy.regional_bias, to_value=round(target_bias, 2)
                    ),
                    "cooperation_incentive": ParameterChange(
                        from_value=policy.cooperation_incentive,
                        to_value=round(target_cooperation, 2),
                    ),
                },
                target_metrics=["policy_accessibility", "regional_gap"],
                expected_directions={
                    "policy_accessibility": "increase",
                    "regional_gap": "decrease",
                    "fiscal_pressure": "may_increase",
                },
                tradeoffs=["区域覆盖改善可能增加财政与协调成本"],
                evidence_refs=[
                    "metric:regional_gap:T3",
                    "metric:policy_accessibility:T3",
                    f"metric:mean_support_request:{support_requests:.2f}",
                ],
                public_summary=(
                    "国务院 Agent 建议提高中西部与东北倾斜并增强跨省合作激励，"
                    "其效果仍需通过 Treatment 分支验证。"
                ),
            )
        ]

    async def generate_central_review(self, comparison: ComparisonResult) -> CentralReview:
        accessibility = comparison.national_metrics["policy_accessibility"]
        fiscal = comparison.national_metrics["fiscal_pressure"]
        gap = comparison.national_metrics["regional_gap"]
        benefit = comparison.national_metrics["overall_policy_benefit"]
        findings = [
            ReviewFinding(
                title="政策可达性变化",
                summary=f"Treatment 相对 Control 的政策可达性指数变化 {accessibility.delta:+.2f}。",
                evidence_refs=["comparison:national_metrics:policy_accessibility"],
                tradeoff=f"财政压力指数同步变化 {fiscal.delta:+.2f}。",
            ),
            ReviewFinding(
                title="区域差距变化",
                summary=f"区域差距指数变化 {gap.delta:+.2f}，需与总收益共同判断。",
                evidence_refs=["comparison:national_metrics:regional_gap"],
                tradeoff=f"综合政策收益指数变化 {benefit.delta:+.2f}。",
            ),
        ]
        return CentralReview(
            review_id=_stable_id(
                "review", comparison.model_dump(mode="json", exclude={"central_review"})
            ),
            findings=findings,
            limitations=[
                "结果只适用于当前数据、参数、模型与机制版本。",
                "省级响应代理不代表现实政府立场，指数不映射为现实GDP或就业变化。",
            ],
            public_summary=(
                "国务院 Agent 已完成结构化对照复盘；请结合收益、区域均衡与财政代价共同判断。"
            ),
        )
