from math import isfinite
from statistics import fmean
from typing import Literal

from pydantic import Field

from simulation.data import load_automaker_profiles, load_profiles
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.action import MechanismContribution, MechanismTerm
from simulation.models.automaker import AutomakerAction, AutomakerProfile, AutomakerState
from simulation.models.base import DomainModel
from simulation.models.common import FacilityActionKind, Phase
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceAction, ProvinceProfile, ProvinceState
from simulation.models.world import NationalMetrics


def _round(value: float) -> float:
    return round(float(value), 4)


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    if not isfinite(value):
        raise ValueError("environment value must be finite")
    return _round(max(minimum, min(maximum, value)))


def normalized_gini(values: list[float]) -> float:
    if not values or any(not isfinite(value) or value < 0 for value in values):
        raise ValueError("Gini requires finite non-negative values")
    total = sum(values)
    if total == 0 or len(values) == 1:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    raw = sum((2 * index - n - 1) * value for index, value in enumerate(ordered, 1)) / (n * total)
    return _round(_clamp(raw * n / (n - 1) * 100))


def normalized_hhi(values: list[float]) -> float:
    if not values or any(not isfinite(value) or value < 0 for value in values):
        raise ValueError("HHI requires finite non-negative values")
    total = sum(values)
    n = len(values)
    if total == 0 or n == 1:
        return 0.0
    hhi = sum((value / total) ** 2 for value in values)
    return _round(_clamp((hhi - 1 / n) / (1 - 1 / n) * 100))


def province_development_index(demand_index: float, industry_activity_index: float) -> float:
    return _round(0.5 * demand_index + 0.5 * industry_activity_index)


def delta_gap(treatment_gap: float, control_gap: float) -> float:
    return _round(treatment_gap - control_gap)


class FiscalOffer(DomainModel):
    province_code: str
    program_index: float = Field(ge=0)
    central_funding_index: float = Field(ge=0)
    local_matching_index: float = Field(ge=0)
    fiscal_space_index: float = Field(ge=0, le=100)


class FixedVariableThreshold(DomainModel):
    province_code: str
    crossing_quarter: int | None = Field(default=None, ge=1, le=4)
    effective_scale_index: float | None = Field(default=None, ge=0, le=1)
    fixed_support_effect: float = Field(ge=0)
    variable_support_effects: list[float] = Field(min_length=4, max_length=4)


class YearSettlement(DomainModel):
    schema_version: Literal["year-settlement-v1"] = "year-settlement-v1"
    phase: Phase
    province_states: dict[str, ProvinceState]
    automaker_states: dict[str, AutomakerState]
    national_metrics: NationalMetrics
    mechanism_contributions: dict[str, MechanismContribution]
    fixed_variable_thresholds: dict[str, FixedVariableThreshold]


def fixed_variable_cost_threshold(
    province_code: str,
    fixed_support: float,
    variable_support: float,
    entry_cost_sensitivity: float = 0.72,
) -> FixedVariableThreshold:
    fixed_effect = fixed_support * entry_cost_sensitivity
    scales = [0.25, 0.50, 0.75, 1.0]
    variable_effects = [variable_support * scale for scale in scales]
    crossing = next(
        (index for index, value in enumerate(variable_effects, 1) if value >= fixed_effect), None
    )
    return FixedVariableThreshold(
        province_code=province_code,
        crossing_quarter=crossing,
        effective_scale_index=scales[crossing - 1] if crossing else None,
        fixed_support_effect=_round(fixed_effect),
        variable_support_effects=[_round(value) for value in variable_effects],
    )


class ChinaPolicyEnv:
    """Deterministic authority for fiscal, demand, ROI and industrial-layout outcomes."""

    formula_version = "nev-policy-env-v1"

    def __init__(
        self,
        *,
        profiles: dict[str, ProvinceProfile] | None = None,
        automaker_profiles: dict[str, AutomakerProfile] | None = None,
        policy: PolicySchema | None = None,
    ):
        self.profiles = profiles or load_profiles()
        self.automaker_profiles = automaker_profiles or load_automaker_profiles()
        self.policy = policy or PolicySchema()
        if set(self.profiles) != set(MAINLAND_PROVINCE_CODES):
            raise ValueError("environment requires exactly 31 province profiles")
        if set(self.automaker_profiles) != set(AUTOMAKER_IDS):
            raise ValueError("environment requires exactly 10 automaker profiles")
        self.province_states = {
            code: self._initial_province_state(profile) for code, profile in self.profiles.items()
        }
        self.automaker_states = {
            automaker_id: AutomakerState(
                automaker_id=automaker_id,
                simulated_roi_index=_round(35 + 35 * profile.profitability_index),
                sales_activity_index=_round(30 + 50 * profile.sales_scale_index),
                operating_cost_index=_round(45 + 30 * (1 - profile.liquidity_index)),
            )
            for automaker_id, profile in self.automaker_profiles.items()
        }

    def _fiscal_offer(self, profile: ProvinceProfile, policy: PolicySchema) -> FiscalOffer:
        program = (
            20
            + 35 * profile.market_scale
            + 25 * profile.vehicle_consumption_index
            + 20 * profile.nev_penetration_index
        )
        central = program * policy.central_share_for_region(profile.policy_region)
        local = program - central
        fiscal_space = _clamp(
            100
            * (
                0.45 * profile.fiscal_capacity
                + 0.30 * (1 - profile.fiscal_rigidity)
                + 0.25 * (central / program)
            )
        )
        return FiscalOffer(
            province_code=profile.province_code,
            program_index=_round(program),
            central_funding_index=_round(central),
            local_matching_index=_round(local),
            fiscal_space_index=fiscal_space,
        )

    def _initial_province_state(self, profile: ProvinceProfile) -> ProvinceState:
        offer = self._fiscal_offer(profile, self.policy)
        demand = _clamp(
            100
            * (
                0.35 * profile.willingness_to_pay_index
                + 0.30 * profile.market_scale
                + 0.20 * profile.charging_infrastructure_index
                + 0.15 * profile.nev_penetration_index
            )
        )
        industry = _clamp(
            100
            * (
                0.35 * profile.nev_industry_base
                + 0.25 * profile.vehicle_manufacturing_base
                + 0.20 * profile.components_base
                + 0.20 * (1 - profile.battery_supply_distance_index)
            )
        )
        return ProvinceState(
            province_code=profile.province_code,
            local_matching_burden_index=_clamp(offer.local_matching_index),
            fiscal_space_index=offer.fiscal_space_index,
            demand_index=demand,
            industry_activity_index=industry,
            development_index=province_development_index(demand, industry),
            fiscal_pressure_index=_clamp(
                100
                * (
                    0.45 * profile.fiscal_rigidity
                    + 0.35 * offer.local_matching_index / offer.program_index
                    + 0.20 * (1 - profile.fiscal_capacity)
                )
            ),
        )

    @staticmethod
    def _contribution(
        province_code: str, metric: str, terms: list[MechanismTerm], evidence_refs: list[str]
    ) -> MechanismContribution:
        raw = sum(term.contribution for term in terms)
        final = _clamp(raw)
        return MechanismContribution(
            province_code=province_code,
            target_metric=metric,
            terms=terms,
            raw_value=raw,
            clamp_adjustment=final - raw,
            final_value=final,
            evidence_refs=evidence_refs,
        )

    def settle_year(
        self,
        *,
        policy: PolicySchema,
        province_actions: dict[str, ProvinceAction],
        automaker_actions: dict[str, AutomakerAction],
        phase: Phase,
        previous_province_states: dict[str, ProvinceState] | None = None,
    ) -> YearSettlement:
        if phase not in {Phase.Y1_Q4, Phase.Y2_Q4}:
            raise ValueError("annual settlement is only valid in Q4")
        if set(province_actions) != set(MAINLAND_PROVINCE_CODES):
            raise ValueError("settlement requires 31 province actions")
        if set(automaker_actions) != set(AUTOMAKER_IDS):
            raise ValueError("settlement requires 10 automaker actions")
        expected_province_phase = Phase.Y1_Q1 if phase is Phase.Y1_Q4 else Phase.Y2_Q1
        expected_automaker_phase = Phase.Y1_Q2 if phase is Phase.Y1_Q4 else Phase.Y2_Q2
        if any(action.phase is not expected_province_phase for action in province_actions.values()):
            raise ValueError("province action year does not match settlement")
        if any(
            action.phase is not expected_automaker_phase for action in automaker_actions.values()
        ):
            raise ValueError("automaker action year does not match settlement")
        states: dict[str, ProvinceState] = {}
        contributions: dict[str, MechanismContribution] = {}
        thresholds: dict[str, FixedVariableThreshold] = {}
        central_total = 0.0
        program_total = 0.0
        facility_values: list[float] = []
        for code in MAINLAND_PROVINCE_CODES:
            profile = self.profiles[code]
            action = province_actions[code]
            offer = self._fiscal_offer(profile, policy)
            central_total += offer.central_funding_index
            program_total += offer.program_index
            sales = fmean(
                next(
                    item.sales_investment_intensity
                    for item in automaker.province_market_actions
                    if item.province_code == code
                )
                for automaker in automaker_actions.values()
            )
            facility = sum(
                item.investment_intensity
                for automaker in automaker_actions.values()
                for item in automaker.facility_actions
                if item.province_code == code and item.action is not FacilityActionKind.DELAY
            )
            facility_values.append(facility)
            local_support = 100 * action.overall_support_intensity
            demand_terms = [
                MechanismTerm(
                    name="consumer_wtp",
                    input_value=profile.willingness_to_pay_index,
                    coefficient=28,
                    contribution=28 * profile.willingness_to_pay_index,
                ),
                MechanismTerm(
                    name="consumer_subsidy",
                    input_value=action.overall_support_intensity * action.subsidy_mix.consumer,
                    coefficient=27,
                    contribution=27
                    * action.overall_support_intensity
                    * action.subsidy_mix.consumer,
                ),
                MechanismTerm(
                    name="automaker_sales",
                    input_value=sales,
                    coefficient=25,
                    contribution=25 * sales,
                ),
                MechanismTerm(
                    name="charging_access",
                    input_value=profile.charging_infrastructure_index,
                    coefficient=20,
                    contribution=20 * profile.charging_infrastructure_index,
                ),
            ]
            industry_terms = [
                MechanismTerm(
                    name="industry_base",
                    input_value=profile.nev_industry_base,
                    coefficient=25,
                    contribution=25 * profile.nev_industry_base,
                ),
                MechanismTerm(
                    name="fixed_cost_support",
                    input_value=action.overall_support_intensity * action.subsidy_mix.fixed_cost,
                    coefficient=25,
                    contribution=25
                    * action.overall_support_intensity
                    * action.subsidy_mix.fixed_cost,
                ),
                MechanismTerm(
                    name="variable_cost_support",
                    input_value=action.overall_support_intensity * action.subsidy_mix.variable_cost,
                    coefficient=20,
                    contribution=20
                    * action.overall_support_intensity
                    * action.subsidy_mix.variable_cost,
                ),
                MechanismTerm(
                    name="battery_proximity",
                    input_value=1 - profile.battery_supply_distance_index,
                    coefficient=15,
                    contribution=15 * (1 - profile.battery_supply_distance_index),
                ),
                MechanismTerm(
                    name="facility_activity",
                    input_value=min(1, facility),
                    coefficient=15,
                    contribution=15 * min(1, facility),
                ),
            ]
            demand_contribution = self._contribution(
                code, "demand_index", demand_terms, [f"action:{action.action_id}"]
            )
            industry_contribution = self._contribution(
                code, "industry_activity_index", industry_terms, [f"action:{action.action_id}"]
            )
            demand = demand_contribution.final_value
            industry = industry_contribution.final_value
            if previous_province_states and code in previous_province_states:
                demand = _clamp(0.35 * previous_province_states[code].demand_index + 0.65 * demand)
                industry = _clamp(
                    0.40 * previous_province_states[code].industry_activity_index + 0.60 * industry
                )
            fiscal_pressure = _clamp(
                100
                * (
                    0.35 * profile.fiscal_rigidity
                    + 0.35 * offer.local_matching_index / offer.program_index
                    + 0.30 * action.overall_support_intensity * (1 - offer.fiscal_space_index / 100)
                )
            )
            states[code] = ProvinceState(
                province_code=code,
                phase=phase,
                local_matching_burden_index=_clamp(offer.local_matching_index),
                fiscal_space_index=offer.fiscal_space_index,
                local_support_index=_clamp(local_support),
                demand_index=demand,
                industry_activity_index=industry,
                development_index=province_development_index(demand, industry),
                fiscal_pressure_index=fiscal_pressure,
                last_action_id=action.action_id,
            )
            contributions[f"{code}:demand"] = demand_contribution
            contributions[f"{code}:industry"] = industry_contribution
            thresholds[code] = fixed_variable_cost_threshold(
                code,
                action.overall_support_intensity * action.subsidy_mix.fixed_cost,
                action.overall_support_intensity * action.subsidy_mix.variable_cost,
            )
        automaker_states: dict[str, AutomakerState] = {}
        for automaker_id, action in automaker_actions.items():
            profile = self.automaker_profiles[automaker_id]
            mean_sales = fmean(
                item.sales_investment_intensity for item in action.province_market_actions
            )
            facility = sum(
                item.investment_intensity
                for item in action.facility_actions
                if item.action is not FacilityActionKind.DELAY
            )
            operating = 100 * fmean(
                0.25 * self.profiles[item.province_code].land_cost_index
                + 0.25 * self.profiles[item.province_code].talent_cost_index
                + 0.25 * self.profiles[item.province_code].energy_cost_index
                + 0.25 * self.profiles[item.province_code].logistics_cost_index
                for item in action.province_market_actions
            )
            automaker_states[automaker_id] = AutomakerState(
                automaker_id=automaker_id,
                phase=phase,
                simulated_roi_index=_clamp(
                    100
                    * (
                        0.45 * mean_sales
                        + 0.30 * profile.profitability_index
                        + 0.25 * (1 - operating / 100)
                    )
                ),
                sales_activity_index=_clamp(mean_sales * 100),
                facility_activity_index=_clamp(facility / 3 * 100),
                operating_cost_index=_clamp(operating),
                last_action_id=action.action_id,
            )
        development = [state.development_index for state in states.values()]
        industry = [state.industry_activity_index for state in states.values()]
        market_total = sum(profile.market_scale for profile in self.profiles.values())
        metrics = NationalMetrics(
            regional_development_gap=normalized_gini(development),
            central_fiscal_burden=_clamp(central_total / program_total * 100),
            local_fiscal_pressure=_round(
                fmean(state.fiscal_pressure_index for state in states.values())
            ),
            nev_demand=_round(
                sum(states[code].demand_index * self.profiles[code].market_scale for code in states)
                / market_total
            ),
            new_investment_concentration=normalized_hhi(facility_values),
            industrial_agglomeration=normalized_hhi(industry),
        )
        return YearSettlement(
            phase=phase,
            province_states=states,
            automaker_states=automaker_states,
            national_metrics=metrics,
            mechanism_contributions=contributions,
            fixed_variable_thresholds=thresholds,
        )
