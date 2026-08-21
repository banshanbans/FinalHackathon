from __future__ import annotations

from statistics import fmean

from simulation.data import load_automaker_profiles, load_profiles
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.envs.china_policy_env import (
    ChinaPolicyEnv,
    normalized_gini,
    normalized_hhi,
    province_development_index,
)
from simulation.models.automaker import AutomakerState
from simulation.models.common import FacilityActionKind, PolicyStatus
from simulation.models.m34 import (
    AutomakerQuarterAction,
    EventPlanV2,
    InteractionSession,
    MacroTick,
    ProvinceQuarterAction,
    QuarterSettlement,
    TickCheckpoint,
    TransactionState,
)
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceState
from simulation.models.v32 import PolicyV4
from simulation.models.world import NationalMetrics
from simulation.services.replay import canonical_hash


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    if value != value or value in {float("inf"), float("-inf")}:
        raise ValueError("quarter settlement requires finite values")
    return round(max(minimum, min(maximum, float(value))), 4)


def _policy(policy: PolicyV4) -> PolicySchema:
    return PolicySchema(
        policy_id=policy.policy_id,
        west_central_share=policy.west_central_share,
        central_central_share=policy.central_central_share,
        east_central_share=policy.east_central_share,
        status=PolicyStatus.APPROVED,
        mechanism_version="nev-policy-env-v7",
    )


def _event_effect(events: list[EventPlanV2], channel: str) -> float:
    magnitude = {"low": 0.25, "medium": 0.5, "high": 0.75}
    return sum(
        magnitude[event.intensity]
        for event in events
        if any(channel in item for item in event.mechanism_channels)
    )


def settle_quarter(
    previous_checkpoint: TickCheckpoint | None,
    committed_actions: tuple[
        PolicyV4,
        dict[str, ProvinceQuarterAction],
        dict[str, AutomakerQuarterAction],
    ],
    settled_interactions: list[InteractionSession],
    active_events: list[EventPlanV2],
    *,
    branch_id: str,
    tick: MacroTick,
) -> QuarterSettlement:
    """Pure deterministic M34 quarterly transition.

    Inputs are frozen DTOs. The function neither mutates the previous checkpoint nor
    reads runtime state, message order or another branch.
    """

    policy, province_actions, automaker_actions = committed_actions
    if set(province_actions) != set(MAINLAND_PROVINCE_CODES):
        raise ValueError("quarter settlement requires 31 province actions")
    if set(automaker_actions) != set(AUTOMAKER_IDS):
        raise ValueError("quarter settlement requires 10 automaker actions")
    if any(
        item.branch_id != branch_id or item.tick.order > tick.order
        for item in province_actions.values()
    ):
        raise ValueError("province quarter action branch/tick mismatch")
    if any(
        item.branch_id != branch_id or item.tick.order > tick.order
        for item in automaker_actions.values()
    ):
        raise ValueError("automaker quarter action branch/tick mismatch")
    if any(
        session.branch_id != branch_id
        or session.tick is not tick
        or session.state is not TransactionState.SETTLED
        for session in settled_interactions
    ):
        raise ValueError("only same-branch settled interactions may reach the environment")

    profiles = load_profiles()
    automaker_profiles = load_automaker_profiles()
    legacy_env = ChinaPolicyEnv(
        profiles=profiles,
        automaker_profiles=automaker_profiles,
        policy=_policy(policy),
    )
    previous_states = previous_checkpoint.settlement.province_states if previous_checkpoint else {}
    interaction_by_province = {code: 0.0 for code in MAINLAND_PROVINCE_CODES}
    for session in sorted(settled_interactions, key=lambda item: item.session_id):
        for participant in session.participant_ids:
            if participant in interaction_by_province:
                interaction_by_province[participant] += session.settled_contribution

    demand_event = _event_effect(active_events, "demand") + _event_effect(active_events, "oil")
    industry_event = (
        _event_effect(active_events, "industry")
        + _event_effect(active_events, "battery")
        + _event_effect(active_events, "supply")
    )
    states: dict[str, ProvinceState] = {}
    facility_values: list[float] = []
    central_total = 0.0
    program_total = 0.0
    demand_total = 0.0
    market_total = sum(profile.market_scale for profile in profiles.values())
    mechanism_totals = {
        "consumer_subsidy_effect": 0.0,
        "channel_investment_effect": 0.0,
        "facility_investment_effect": 0.0,
        "settled_interaction_effect": 0.0,
        "active_event_effect": 0.0,
        "local_fiscal_constraint": 0.0,
    }

    for code in MAINLAND_PROVINCE_CODES:
        profile = profiles[code]
        action = province_actions[code]
        fiscal_offer = legacy_env._fiscal_offer(profile, _policy(policy))
        initial = legacy_env._initial_province_state(profile)
        previous = previous_states.get(code, initial)
        central_total += fiscal_offer.central_funding_index
        program_total += fiscal_offer.program_index
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
        interaction = min(1.0, interaction_by_province[code])
        target_demand = _clamp(
            28 * profile.willingness_to_pay_index
            + 25 * action.overall_support_intensity * action.subsidy_mix.consumer
            + 24 * sales
            + 18 * profile.charging_infrastructure_index
            + 3 * interaction
            + 2 * demand_event
        )
        target_industry = _clamp(
            24 * profile.nev_industry_base
            + 23 * action.overall_support_intensity * action.subsidy_mix.fixed_cost
            + 18 * action.overall_support_intensity * action.subsidy_mix.variable_cost
            + 14 * (1 - profile.battery_supply_distance_index)
            + 13 * min(1.0, facility)
            + 5 * interaction
            + 3 * industry_event
        )
        # A quarter advances only part of the annual stock while still permitting Q4 to
        # accumulate the complete sequence through repeated immutable transitions.
        demand = _clamp(0.62 * previous.demand_index + 0.38 * target_demand)
        industry = _clamp(0.68 * previous.industry_activity_index + 0.32 * target_industry)
        fiscal_pressure = _clamp(
            100
            * (
                0.35 * profile.fiscal_rigidity
                + 0.35 * fiscal_offer.local_matching_index / fiscal_offer.program_index
                + 0.30
                * action.overall_support_intensity
                * (1 - fiscal_offer.fiscal_space_index / 100)
            )
        )
        states[code] = ProvinceState(
            province_code=code,
            local_matching_burden_index=_clamp(fiscal_offer.local_matching_index),
            fiscal_space_index=fiscal_offer.fiscal_space_index,
            local_support_index=_clamp(action.overall_support_intensity * 100),
            demand_index=demand,
            industry_activity_index=industry,
            development_index=province_development_index(demand, industry),
            fiscal_pressure_index=fiscal_pressure,
            event_exposure_index=_clamp(min(1.0, demand_event + industry_event) * 100),
            event_response_effect_index=_clamp(
                min(1.0, interaction + 0.1 * (demand_event + industry_event)) * 100
            ),
            last_action_id=action.action_id,
        )
        demand_total += demand * profile.market_scale
        mechanism_totals["consumer_subsidy_effect"] += (
            action.overall_support_intensity * action.subsidy_mix.consumer
        )
        mechanism_totals["channel_investment_effect"] += sales
        mechanism_totals["facility_investment_effect"] += min(1.0, facility)
        mechanism_totals["settled_interaction_effect"] += interaction
        mechanism_totals["active_event_effect"] += demand_event + industry_event
        mechanism_totals["local_fiscal_constraint"] += fiscal_pressure / 100

    automaker_states: dict[str, AutomakerState] = {}
    for automaker_id, action in automaker_actions.items():
        profile = automaker_profiles[automaker_id]
        mean_sales = fmean(
            item.sales_investment_intensity for item in action.province_market_actions
        )
        facility = sum(
            item.investment_intensity
            for item in action.facility_actions
            if item.action is not FacilityActionKind.DELAY
        )
        operating = 100 * fmean(
            0.25 * profiles[item.province_code].land_cost_index
            + 0.25 * profiles[item.province_code].talent_cost_index
            + 0.25 * profiles[item.province_code].energy_cost_index
            + 0.25 * profiles[item.province_code].logistics_cost_index
            for item in action.province_market_actions
        )
        automaker_states[automaker_id] = AutomakerState(
            automaker_id=automaker_id,
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

    metrics = NationalMetrics(
        regional_development_gap=normalized_gini(
            [state.development_index for state in states.values()]
        ),
        central_fiscal_burden=_clamp(central_total / program_total * 100),
        local_fiscal_pressure=round(
            fmean(state.fiscal_pressure_index for state in states.values()), 4
        ),
        nev_demand=round(demand_total / market_total, 4),
        new_investment_concentration=normalized_hhi(facility_values),
        industrial_agglomeration=normalized_hhi(
            [state.industry_activity_index for state in states.values()]
        ),
    )
    rounded_totals = {key: round(value, 6) for key, value in sorted(mechanism_totals.items())}
    payload = {
        "branch_id": branch_id,
        "tick": tick,
        "province_states": states,
        "automaker_states": automaker_states,
        "national_metrics": metrics,
        "mechanism_totals": rounded_totals,
        "active_event_ids": sorted(item.event_plan_id for item in active_events),
        "settled_session_ids": sorted(item.session_id for item in settled_interactions),
    }
    return QuarterSettlement(
        **payload,
        state_hash=canonical_hash(payload),
    )
