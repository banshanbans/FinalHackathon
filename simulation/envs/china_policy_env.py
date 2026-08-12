from __future__ import annotations

from copy import deepcopy
from math import isfinite
from pathlib import Path
from statistics import fmean, pstdev

import yaml

from simulation.data import NetworkEdge, load_enterprise_profiles, load_network, load_profiles
from simulation.models.action import MechanismContribution, ProvinceAction
from simulation.models.audit import MechanismExplanation, MechanismTerm
from simulation.models.common import (
    EnterpriseArchetype,
    FinancingChoice,
    Participation,
    Phase,
    RegionGroup,
    UpgradeType,
)
from simulation.models.enterprise import (
    EnterpriseAction,
    EnterpriseAggregate,
    EnterpriseGroupProfile,
    EnterpriseGroupState,
)
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState
from simulation.models.world import NationalMetrics

MECHANISM_PATH = Path(__file__).resolve().parents[1] / "mechanisms" / "equipment_renewal_v2.yaml"


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return round(max(minimum, min(maximum, value)), 4)


def _weighted_state(
    items: list[tuple[EnterpriseGroupProfile, EnterpriseGroupState, EnterpriseAction]],
    field: str,
) -> float:
    total = sum(profile.weight for profile, _, _ in items)
    return sum(profile.weight * float(getattr(state, field)) for profile, state, _ in items) / total


def _explanation(
    *,
    scope: str,
    subject_id: str,
    metric: str,
    phase: Phase,
    formula_id: str,
    formula_version: str,
    terms: list[MechanismTerm],
    raw_value: float,
    final_value: float,
    previous_value: float | None = None,
    source_refs: list[str] | None = None,
) -> MechanismExplanation:
    values = [raw_value, final_value, *(item.contribution for item in terms)]
    if not all(isfinite(value) for value in values):
        raise ValueError(f"mechanism explanation contains a non-finite value: {formula_id}")
    clamped = max(0.0, min(100.0, raw_value))
    residual = final_value - round(clamped, 4)
    if abs(residual) > 1e-3:
        raise ValueError(f"mechanism explanation does not reconcile: {formula_id}")
    safe_subject = subject_id.replace(":", "_")
    return MechanismExplanation(
        explanation_id=f"mex_{phase.value}_{scope}_{safe_subject}_{metric}",
        scope=scope,  # type: ignore[arg-type]
        subject_id=subject_id,
        metric=metric,
        formula_id=formula_id,
        formula_version=formula_version,
        source_refs=source_refs or [],
        terms=terms,
        previous_value=previous_value,
        raw_value=round(raw_value, 4),
        clamp_adjustment=round(final_value - raw_value, 4),
        final_value=round(final_value, 4),
        residual=round(residual, 6),
    )


class ChinaPolicyEnv:
    """Deterministic authority for V2 equipment-renewal state transitions."""

    def __init__(
        self,
        *,
        profiles: dict[str, ProvinceProfile] | None = None,
        network: dict[str, list[NetworkEdge]] | None = None,
        enterprise_profiles: dict[str, EnterpriseGroupProfile] | None = None,
        policy: PolicySchema,
        province_states: dict[str, ProvinceState] | None = None,
        enterprise_states: dict[str, EnterpriseGroupState] | None = None,
        mechanism_path: Path = MECHANISM_PATH,
    ):
        is_fresh_initialization = province_states is None and enterprise_states is None
        self.profiles = profiles or load_profiles()
        self.network = network or load_network()
        self.enterprise_profiles = enterprise_profiles or load_enterprise_profiles()
        self.policy = policy.model_copy(deep=True)
        with mechanism_path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if raw["mechanism_version"] != policy.mechanism_version:
            raise ValueError("policy and mechanism configuration versions do not match")
        self.config: dict[str, object] = raw
        self.enterprise_states = enterprise_states or {
            enterprise_id: self._initial_enterprise_state(profile)
            for enterprise_id, profile in self.enterprise_profiles.items()
        }
        self.province_states = province_states or {
            code: self._initial_province_state(profile) for code, profile in self.profiles.items()
        }
        self.enterprise_aggregates: dict[str, EnterpriseAggregate] = {}
        self.contributions: dict[str, MechanismContribution] = {}
        self.explanations: list[MechanismExplanation] = (
            self._initial_explanations() if is_fresh_initialization else []
        )

    def _initial_explanations(self) -> list[MechanismExplanation]:
        explanations: list[MechanismExplanation] = []
        for enterprise_id, profile in self.enterprise_profiles.items():
            state = self.enterprise_states[enterprise_id]
            formulas = {
                "participation_score": (
                    "enterprise.initial.participation",
                    [
                        MechanismTerm(name="base", input_value=1, coefficient=38, contribution=38),
                        MechanismTerm(
                            name="cash_flow_resilience",
                            input_value=profile.cash_flow_resilience,
                            coefficient=24,
                            contribution=24 * profile.cash_flow_resilience,
                        ),
                        MechanismTerm(
                            name="financing_constraint",
                            input_value=profile.financing_constraint,
                            coefficient=-18,
                            contribution=-18 * profile.financing_constraint,
                        ),
                    ],
                ),
                "renewal_willingness": (
                    "enterprise.initial.renewal",
                    [
                        MechanismTerm(name="base", input_value=1, coefficient=38, contribution=38),
                        MechanismTerm(
                            name="equipment_age_pressure",
                            input_value=profile.equipment_age_pressure,
                            coefficient=36,
                            contribution=36 * profile.equipment_age_pressure,
                        ),
                        MechanismTerm(
                            name="digital_readiness",
                            input_value=profile.digital_readiness,
                            coefficient=8,
                            contribution=8 * profile.digital_readiness,
                        ),
                    ],
                ),
                "financing_accessibility": (
                    "enterprise.initial.financing",
                    [
                        MechanismTerm(name="base", input_value=1, coefficient=30, contribution=30),
                        MechanismTerm(
                            name="collateral_capacity",
                            input_value=profile.collateral_capacity,
                            coefficient=42,
                            contribution=42 * profile.collateral_capacity,
                        ),
                        MechanismTerm(
                            name="financing_constraint",
                            input_value=profile.financing_constraint,
                            coefficient=-20,
                            contribution=-20 * profile.financing_constraint,
                        ),
                    ],
                ),
                "upgrade_progress": (
                    "enterprise.initial.upgrade",
                    [
                        MechanismTerm(name="base", input_value=1, coefficient=26, contribution=26),
                        MechanismTerm(
                            name="digital_readiness",
                            input_value=profile.digital_readiness,
                            coefficient=23,
                            contribution=23 * profile.digital_readiness,
                        ),
                        MechanismTerm(
                            name="equipment_remaining",
                            input_value=1 - profile.equipment_age_pressure,
                            coefficient=14,
                            contribution=14 * (1 - profile.equipment_age_pressure),
                        ),
                    ],
                ),
            }
            for metric, (formula_id, terms) in formulas.items():
                explanations.append(
                    _explanation(
                        scope="enterprise",
                        subject_id=enterprise_id,
                        metric=metric,
                        phase=Phase.T0,
                        formula_id=formula_id,
                        formula_version=str(self.config["mechanism_version"]),
                        terms=terms,
                        raw_value=sum(item.contribution for item in terms),
                        final_value=float(getattr(state, metric)),
                        source_refs=[f"enterprise:{enterprise_id}:profile"],
                    )
                )
        for code, profile in self.profiles.items():
            state = self.province_states[code]
            definitions = {
                "enterprise_participation_index": (
                    35,
                    [
                        ("credit_access", 22, profile.credit_access),
                        ("advanced_manufacturing_base", 12, profile.advanced_manufacturing_base),
                    ],
                ),
                "equipment_renewal_willingness_index": (
                    40,
                    [
                        ("transition_pressure", 30, profile.transition_pressure),
                        ("advanced_manufacturing_base", 10, profile.advanced_manufacturing_base),
                    ],
                ),
                "sme_financing_accessibility_index": (
                    28,
                    [("credit_access", 48, profile.credit_access)],
                ),
                "industrial_upgrade_index": (
                    28,
                    [
                        ("advanced_manufacturing_base", 24, profile.advanced_manufacturing_base),
                        ("digital_infrastructure", 18, profile.digital_infrastructure),
                    ],
                ),
                "fiscal_pressure_index": (
                    24,
                    [
                        ("inverse_fiscal_capacity", 30, 1 - profile.fiscal_capacity),
                        ("fiscal_conservatism", 12, profile.fiscal_conservatism),
                    ],
                ),
            }
            for metric, (base, factors) in definitions.items():
                terms = [
                    MechanismTerm(name="base", input_value=1, coefficient=base, contribution=base)
                ]
                terms.extend(
                    MechanismTerm(
                        name=name,
                        input_value=value,
                        coefficient=coefficient,
                        contribution=coefficient * value,
                    )
                    for name, coefficient, value in factors
                )
                explanations.append(
                    _explanation(
                        scope="province",
                        subject_id=code,
                        metric=metric,
                        phase=Phase.T0,
                        formula_id=f"province.initial.{metric}",
                        formula_version=str(self.config["mechanism_version"]),
                        terms=terms,
                        raw_value=sum(item.contribution for item in terms),
                        final_value=float(getattr(state, metric)),
                        source_refs=[f"province:{code}:profile"],
                    )
                )
        return explanations

    @staticmethod
    def _initial_enterprise_state(profile: EnterpriseGroupProfile) -> EnterpriseGroupState:
        return EnterpriseGroupState(
            enterprise_id=profile.enterprise_id,
            province_code=profile.province_code,
            participation_score=_clamp(
                38 + 24 * profile.cash_flow_resilience - 18 * profile.financing_constraint
            ),
            renewal_willingness=_clamp(
                38 + 36 * profile.equipment_age_pressure + 8 * profile.digital_readiness
            ),
            financing_accessibility=_clamp(
                30 + 42 * profile.collateral_capacity - 20 * profile.financing_constraint
            ),
            upgrade_progress=_clamp(
                26 + 23 * profile.digital_readiness + 14 * (1 - profile.equipment_age_pressure)
            ),
        )

    @staticmethod
    def _initial_province_state(profile: ProvinceProfile) -> ProvinceState:
        return ProvinceState(
            province_code=profile.province_code,
            enterprise_participation_index=_clamp(
                35 + 22 * profile.credit_access + 12 * profile.advanced_manufacturing_base
            ),
            equipment_renewal_willingness_index=_clamp(
                40 + 30 * profile.transition_pressure + 10 * profile.advanced_manufacturing_base
            ),
            sme_financing_accessibility_index=_clamp(28 + 48 * profile.credit_access),
            industrial_upgrade_index=_clamp(
                28 + 24 * profile.advanced_manufacturing_base + 18 * profile.digital_infrastructure
            ),
            fiscal_pressure_index=_clamp(
                24 + 30 * (1 - profile.fiscal_capacity) + 12 * profile.fiscal_conservatism
            ),
        )

    def _technology_match(self, action: EnterpriseAction) -> float:
        if action.upgrade_type == UpgradeType.DIGITAL:
            return self.policy.technology_mix.digital
        if action.upgrade_type == UpgradeType.GREEN:
            return self.policy.technology_mix.green
        if action.upgrade_type == UpgradeType.GENERAL:
            return self.policy.technology_mix.general
        return 0.0

    def _tool_value(
        self, action: EnterpriseAction, province: ProvinceAction
    ) -> tuple[float, float, float]:
        support = self.policy.support_intensity / 100
        if action.financing_choice == FinancingChoice.DIRECT_SUBSIDY:
            return support * province.instrument_mix.direct_subsidy, 0.0, 0.0
        if action.financing_choice == FinancingChoice.INTEREST_SUBSIDY:
            return 0.0, support * province.instrument_mix.interest_subsidy, 0.0
        if action.financing_choice == FinancingChoice.GUARANTEE_LOAN:
            return 0.0, 0.0, support * province.instrument_mix.financing_guarantee
        return 0.0, 0.0, 0.0

    def _contribution(
        self,
        action: EnterpriseAction,
        province_action: ProvinceAction,
        profile: EnterpriseGroupProfile,
        phase: Phase,
    ) -> MechanismContribution:
        weights = self.config["contributions"]
        if not isinstance(weights, dict):
            raise ValueError("mechanism contributions configuration is invalid")
        step_scale = float(self.config["step_scale"])
        active = {
            Participation.PARTICIPATE: 1.0,
            Participation.CONDITIONAL: 0.72,
            Participation.WAIT: 0.15,
            Participation.DECLINE: 0.0,
        }[action.participation]
        direct, interest, guarantee = self._tool_value(action, province_action)
        is_sme = profile.archetype in {
            EnterpriseArchetype.TECHNOLOGY_SME,
            EnterpriseArchetype.TRADITIONAL_SME,
        }
        province = self.profiles[profile.province_code]
        regional_need = 1.0 if province.region_group != RegionGroup.EAST else 0.35
        regional_bias = max(0.0, self.policy.regional_support_bias)
        minimum_intensity = 0.12 if action.participation == Participation.WAIT else 0
        intensity = max(action.investment_intensity, minimum_intensity)
        values = {
            "policy_match": step_scale
            * float(weights["policy_match"])
            * self._technology_match(action)
            * active,
            "direct_subsidy": step_scale * float(weights["direct_subsidy"]) * direct * active,
            "interest_subsidy": step_scale * float(weights["interest_subsidy"]) * interest * active,
            "financing_guarantee": step_scale
            * float(weights["financing_guarantee"])
            * guarantee
            * active,
            "sme_preference": step_scale
            * float(weights["sme_preference"])
            * self.policy.sme_preference
            * active
            * (1.0 if is_sme else 0.18),
            "regional_support": step_scale
            * float(weights["regional_support"])
            * regional_bias
            * regional_need
            * active,
            "financing_constraint": step_scale
            * float(weights["financing_constraint"])
            * profile.financing_constraint
            * (1 - guarantee * 0.7)
            * max(active, 0.45),
            "fiscal_cost": step_scale
            * float(weights["fiscal_cost"])
            * (self.policy.support_intensity / 100)
            * province_action.local_match_ratio
            * intensity,
        }
        return MechanismContribution(
            enterprise_id=profile.enterprise_id,
            province_code=profile.province_code,
            phase=phase,
            **{field: round(value, 4) for field, value in values.items()},
        )

    @staticmethod
    def _participation_target(action: EnterpriseAction) -> float:
        return {
            Participation.PARTICIPATE: 84.0,
            Participation.CONDITIONAL: 65.0,
            Participation.WAIT: 42.0,
            Participation.DECLINE: 20.0,
        }[action.participation]

    def process_actions(
        self,
        province_actions: dict[str, ProvinceAction],
        enterprise_actions: dict[str, EnterpriseAction],
        phase: Phase,
    ) -> tuple[
        dict[str, ProvinceState],
        dict[str, EnterpriseGroupState],
        dict[str, EnterpriseAggregate],
        dict[str, MechanismContribution],
    ]:
        if set(province_actions) != set(self.profiles):
            raise ValueError("province actions must cover all 31 provinces")
        if set(enterprise_actions) != set(self.enterprise_profiles):
            raise ValueError("enterprise actions must cover all 186 groups")
        self.explanations = []
        next_enterprise: dict[str, EnterpriseGroupState] = {}
        contributions: dict[str, MechanismContribution] = {}
        for enterprise_id, profile in self.enterprise_profiles.items():
            action = enterprise_actions[enterprise_id]
            province_action = province_actions[profile.province_code]
            previous = self.enterprise_states[enterprise_id]
            contribution = self._contribution(action, province_action, profile, phase)
            renewal = _clamp(previous.renewal_willingness + contribution.net_effect)
            actual_delta = renewal - previous.renewal_willingness
            if abs(actual_delta - contribution.net_effect) > 1e-6:
                contribution = contribution.model_copy(
                    update={
                        "policy_match": round(
                            contribution.policy_match + actual_delta - contribution.net_effect,
                            4,
                        )
                    }
                )
            direct, interest, guarantee = self._tool_value(action, province_action)
            financing_gain = 12 * (direct + interest + guarantee) - 7 * profile.financing_constraint
            participation = _clamp(
                0.55 * previous.participation_score
                + 0.45 * self._participation_target(action)
                + 0.6 * contribution.net_effect
            )
            financing = _clamp(previous.financing_accessibility + financing_gain)
            upgrade = _clamp(
                previous.upgrade_progress
                + action.investment_intensity * 7
                + max(0, contribution.policy_match)
            )
            next_enterprise[enterprise_id] = EnterpriseGroupState(
                enterprise_id=enterprise_id,
                province_code=profile.province_code,
                phase=phase,
                participation_score=participation,
                renewal_willingness=renewal,
                financing_accessibility=financing,
                upgrade_progress=upgrade,
                last_action_id=action.action_id,
            )
            contribution_terms = [
                MechanismTerm(
                    name=field,
                    input_value=float(getattr(contribution, field)),
                    coefficient=1,
                    contribution=float(getattr(contribution, field)),
                    source_ref=f"mechanism:{enterprise_id}:{field}:{phase.value}",
                )
                for field in (
                    "policy_match",
                    "direct_subsidy",
                    "interest_subsidy",
                    "financing_guarantee",
                    "sme_preference",
                    "regional_support",
                    "financing_constraint",
                    "fiscal_cost",
                )
            ]
            metric_specs = [
                (
                    "renewal_willingness",
                    "enterprise.transition.renewal",
                    contribution_terms,
                    previous.renewal_willingness + contribution.net_effect,
                    renewal,
                    previous.renewal_willingness,
                ),
                (
                    "participation_score",
                    "enterprise.transition.participation",
                    [
                        MechanismTerm(
                            name="previous",
                            input_value=previous.participation_score,
                            coefficient=0.55,
                            contribution=0.55 * previous.participation_score,
                        ),
                        MechanismTerm(
                            name="participation_target",
                            input_value=self._participation_target(action),
                            coefficient=0.45,
                            contribution=0.45 * self._participation_target(action),
                        ),
                        MechanismTerm(
                            name="mechanism_net",
                            input_value=contribution.net_effect,
                            coefficient=0.6,
                            contribution=0.6 * contribution.net_effect,
                        ),
                    ],
                    0.55 * previous.participation_score
                    + 0.45 * self._participation_target(action)
                    + 0.6 * contribution.net_effect,
                    participation,
                    previous.participation_score,
                ),
                (
                    "financing_accessibility",
                    "enterprise.transition.financing",
                    [
                        MechanismTerm(
                            name="previous",
                            input_value=previous.financing_accessibility,
                            coefficient=1,
                            contribution=previous.financing_accessibility,
                        ),
                        MechanismTerm(
                            name="selected_financing_tools",
                            input_value=direct + interest + guarantee,
                            coefficient=12,
                            contribution=12 * (direct + interest + guarantee),
                        ),
                        MechanismTerm(
                            name="financing_constraint",
                            input_value=profile.financing_constraint,
                            coefficient=-7,
                            contribution=-7 * profile.financing_constraint,
                        ),
                    ],
                    previous.financing_accessibility + financing_gain,
                    financing,
                    previous.financing_accessibility,
                ),
                (
                    "upgrade_progress",
                    "enterprise.transition.upgrade",
                    [
                        MechanismTerm(
                            name="previous",
                            input_value=previous.upgrade_progress,
                            coefficient=1,
                            contribution=previous.upgrade_progress,
                        ),
                        MechanismTerm(
                            name="investment_intensity",
                            input_value=action.investment_intensity,
                            coefficient=7,
                            contribution=action.investment_intensity * 7,
                        ),
                        MechanismTerm(
                            name="positive_policy_match",
                            input_value=max(0, contribution.policy_match),
                            coefficient=1,
                            contribution=max(0, contribution.policy_match),
                        ),
                    ],
                    previous.upgrade_progress
                    + action.investment_intensity * 7
                    + max(0, contribution.policy_match),
                    upgrade,
                    previous.upgrade_progress,
                ),
            ]
            for metric, formula_id, terms, raw, final, prior in metric_specs:
                self.explanations.append(
                    _explanation(
                        scope="enterprise",
                        subject_id=enterprise_id,
                        metric=metric,
                        phase=phase,
                        formula_id=formula_id,
                        formula_version=str(self.config["mechanism_version"]),
                        terms=terms,
                        raw_value=raw,
                        final_value=final,
                        previous_value=prior,
                        source_refs=[action.action_id, province_action.action_id],
                    )
                )
            contributions[enterprise_id] = contribution

        aggregates: dict[str, EnterpriseAggregate] = {}
        next_provinces: dict[str, ProvinceState] = {}
        for code, province_profile in self.profiles.items():
            items = [
                (profile, next_enterprise[enterprise_id], enterprise_actions[enterprise_id])
                for enterprise_id, profile in self.enterprise_profiles.items()
                if profile.province_code == code
            ]
            sme_items = [
                (profile, state)
                for profile, state, _ in items
                if profile.archetype
                in {EnterpriseArchetype.TECHNOLOGY_SME, EnterpriseArchetype.TRADITIONAL_SME}
            ]
            sme_weight = sum(profile.weight for profile, _ in sme_items)
            sme_financing = (
                sum(profile.weight * state.financing_accessibility for profile, state in sme_items)
                / sme_weight
            )
            counts = {participation: 0 for participation in Participation}
            for _, _, action in items:
                counts[action.participation] += 1
            aggregate = EnterpriseAggregate(
                province_code=code,
                participation_index=_clamp(_weighted_state(items, "participation_score")),
                renewal_willingness_index=_clamp(_weighted_state(items, "renewal_willingness")),
                sme_financing_accessibility_index=_clamp(sme_financing),
                industrial_upgrade_index=_clamp(_weighted_state(items, "upgrade_progress")),
                participation_counts=counts,
            )
            aggregates[code] = aggregate
            province_action = province_actions[code]
            fiscal = self.config["fiscal_pressure"]
            if not isinstance(fiscal, dict):
                raise ValueError("fiscal pressure configuration is invalid")
            policy_cost = 100 * (
                float(fiscal["support_intensity"]) * self.policy.support_intensity / 100
                + float(fiscal["direct_subsidy"]) * province_action.instrument_mix.direct_subsidy
                + float(fiscal["interest_subsidy"])
                * province_action.instrument_mix.interest_subsidy
                + float(fiscal["financing_guarantee"])
                * province_action.instrument_mix.financing_guarantee
                + float(fiscal["local_match"]) * province_action.local_match_ratio
                + float(fiscal["sme_preference"]) * self.policy.sme_preference
                + float(fiscal["regional_support"]) * max(0.0, self.policy.regional_support_bias)
            )
            fiscal_pressure = _clamp(
                0.52 * self.province_states[code].fiscal_pressure_index
                + 0.48 * policy_cost * (1.12 - 0.45 * province_profile.fiscal_capacity)
            )
            next_provinces[code] = ProvinceState(
                province_code=code,
                phase=phase,
                enterprise_participation_index=aggregate.participation_index,
                equipment_renewal_willingness_index=aggregate.renewal_willingness_index,
                sme_financing_accessibility_index=aggregate.sme_financing_accessibility_index,
                industrial_upgrade_index=aggregate.industrial_upgrade_index,
                fiscal_pressure_index=fiscal_pressure,
                last_action_id=province_action.action_id,
            )
            weighted_metrics = {
                "enterprise_participation_index": "participation_score",
                "equipment_renewal_willingness_index": "renewal_willingness",
                "industrial_upgrade_index": "upgrade_progress",
            }
            total_weight = sum(profile.weight for profile, _, _ in items)
            for province_metric, enterprise_metric in weighted_metrics.items():
                terms = [
                    MechanismTerm(
                        name=profile.enterprise_id,
                        input_value=float(getattr(state, enterprise_metric)),
                        coefficient=profile.weight / total_weight,
                        contribution=profile.weight
                        * float(getattr(state, enterprise_metric))
                        / total_weight,
                        source_ref=f"mechanism:{profile.enterprise_id}:{enterprise_metric}:{phase.value}",
                    )
                    for profile, state, _ in items
                ]
                final = float(getattr(next_provinces[code], province_metric))
                self.explanations.append(
                    _explanation(
                        scope="province",
                        subject_id=code,
                        metric=province_metric,
                        phase=phase,
                        formula_id=f"province.aggregate.{province_metric}",
                        formula_version=str(self.config["mechanism_version"]),
                        terms=terms,
                        raw_value=sum(item.contribution for item in terms),
                        final_value=final,
                        source_refs=[item.source_ref for item in terms if item.source_ref],
                    )
                )
            sme_terms = [
                MechanismTerm(
                    name=profile.enterprise_id,
                    input_value=state.financing_accessibility,
                    coefficient=profile.weight / sme_weight,
                    contribution=profile.weight * state.financing_accessibility / sme_weight,
                    source_ref=f"mechanism:{profile.enterprise_id}:financing_accessibility:{phase.value}",
                )
                for profile, state in sme_items
            ]
            self.explanations.append(
                _explanation(
                    scope="province",
                    subject_id=code,
                    metric="sme_financing_accessibility_index",
                    phase=phase,
                    formula_id="province.aggregate.sme_financing_accessibility",
                    formula_version=str(self.config["mechanism_version"]),
                    terms=sme_terms,
                    raw_value=sum(item.contribution for item in sme_terms),
                    final_value=aggregate.sme_financing_accessibility_index,
                    source_refs=[item.source_ref for item in sme_terms if item.source_ref],
                )
            )
            fiscal_terms = [
                MechanismTerm(
                    name="previous_fiscal_pressure",
                    input_value=self.province_states[code].fiscal_pressure_index,
                    coefficient=0.52,
                    contribution=0.52 * self.province_states[code].fiscal_pressure_index,
                ),
                MechanismTerm(
                    name="capacity_adjusted_policy_cost",
                    input_value=policy_cost * (1.12 - 0.45 * province_profile.fiscal_capacity),
                    coefficient=0.48,
                    contribution=0.48
                    * policy_cost
                    * (1.12 - 0.45 * province_profile.fiscal_capacity),
                ),
            ]
            self.explanations.append(
                _explanation(
                    scope="province",
                    subject_id=code,
                    metric="fiscal_pressure_index",
                    phase=phase,
                    formula_id="province.fiscal_pressure",
                    formula_version=str(self.config["mechanism_version"]),
                    terms=fiscal_terms,
                    raw_value=sum(item.contribution for item in fiscal_terms),
                    final_value=fiscal_pressure,
                    previous_value=self.province_states[code].fiscal_pressure_index,
                    source_refs=[province_action.action_id],
                )
            )
        self.enterprise_states = next_enterprise
        self.enterprise_aggregates = aggregates
        self.province_states = next_provinces
        self.contributions = contributions
        return (
            deepcopy(next_provinces),
            deepcopy(next_enterprise),
            deepcopy(aggregates),
            deepcopy(contributions),
        )

    def calculate_national_metrics(self) -> NationalMetrics:
        states = list(self.province_states.values())
        if not states:
            return NationalMetrics()
        participation = fmean(item.enterprise_participation_index for item in states)
        renewal = fmean(item.equipment_renewal_willingness_index for item in states)
        financing = fmean(item.sme_financing_accessibility_index for item in states)
        upgrade = fmean(item.industrial_upgrade_index for item in states)
        fiscal = fmean(item.fiscal_pressure_index for item in states)
        gap = min(100.0, 2.2 * pstdev(item.enterprise_participation_index for item in states))
        result = NationalMetrics(
            enterprise_participation_index=_clamp(participation),
            equipment_renewal_willingness_index=_clamp(renewal),
            sme_financing_accessibility_index=_clamp(financing),
            industrial_upgrade_index=_clamp(upgrade),
            local_fiscal_pressure_index=_clamp(fiscal),
            regional_gap_index=_clamp(gap),
        )
        phase = states[0].phase
        metric_fields = (
            "enterprise_participation_index",
            "equipment_renewal_willingness_index",
            "sme_financing_accessibility_index",
            "industrial_upgrade_index",
            "fiscal_pressure_index",
        )
        national_fields = (
            "enterprise_participation_index",
            "equipment_renewal_willingness_index",
            "sme_financing_accessibility_index",
            "industrial_upgrade_index",
            "local_fiscal_pressure_index",
        )
        for source_field, target_field in zip(metric_fields, national_fields, strict=True):
            terms = [
                MechanismTerm(
                    name=state.province_code,
                    input_value=float(getattr(state, source_field)),
                    coefficient=1 / len(states),
                    contribution=float(getattr(state, source_field)) / len(states),
                    source_ref=f"mechanism:{state.province_code}:{source_field}:{phase.value}",
                )
                for state in states
            ]
            self.explanations.append(
                _explanation(
                    scope="national",
                    subject_id="national",
                    metric=target_field,
                    phase=phase,
                    formula_id=f"national.mean.{target_field}",
                    formula_version=str(self.config["mechanism_version"]),
                    terms=terms,
                    raw_value=sum(item.contribution for item in terms),
                    final_value=float(getattr(result, target_field)),
                    source_refs=[item.source_ref for item in terms if item.source_ref],
                )
            )
        stddev = pstdev(item.enterprise_participation_index for item in states)
        self.explanations.append(
            _explanation(
                scope="national",
                subject_id="national",
                metric="regional_gap_index",
                phase=phase,
                formula_id="national.regional_gap",
                formula_version=str(self.config["mechanism_version"]),
                terms=[
                    MechanismTerm(
                        name="province_participation_pstdev",
                        input_value=stddev,
                        coefficient=2.2,
                        contribution=2.2 * stddev,
                    )
                ],
                raw_value=2.2 * stddev,
                final_value=result.regional_gap_index,
                source_refs=[
                    f"mechanism:{state.province_code}:enterprise_participation_index:{phase.value}"
                    for state in states
                ],
            )
        )
        return result

    def snapshot(self) -> dict[str, object]:
        return {
            "policy": self.policy.model_dump(mode="json"),
            "province_states": {
                code: state.model_dump(mode="json") for code, state in self.province_states.items()
            },
            "enterprise_states": {
                key: state.model_dump(mode="json") for key, state in self.enterprise_states.items()
            },
        }

    @classmethod
    def restore(
        cls,
        snapshot: dict[str, object],
        *,
        profiles: dict[str, ProvinceProfile] | None = None,
        network: dict[str, list[NetworkEdge]] | None = None,
        enterprise_profiles: dict[str, EnterpriseGroupProfile] | None = None,
    ) -> ChinaPolicyEnv:
        raw_provinces = snapshot["province_states"]
        raw_enterprises = snapshot["enterprise_states"]
        if not isinstance(raw_provinces, dict) or not isinstance(raw_enterprises, dict):
            raise ValueError("snapshot states are invalid")
        return cls(
            profiles=profiles,
            network=network,
            enterprise_profiles=enterprise_profiles,
            policy=PolicySchema.model_validate(snapshot["policy"]),
            province_states={
                code: ProvinceState.model_validate(state) for code, state in raw_provinces.items()
            },
            enterprise_states={
                key: EnterpriseGroupState.model_validate(state)
                for key, state in raw_enterprises.items()
            },
        )
