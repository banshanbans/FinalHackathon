from collections import defaultdict

from simulation.llm.fake_provider import policy_diff
from simulation.models.common import ComparisonMode
from simulation.models.province import ProvinceProfile
from simulation.models.scenario import EventScenarioDiff
from simulation.models.world import (
    ActiveDifferenceProof,
    AutomakerStrategyTransition,
    ComparisonResult,
    MetricDelta,
    ProvinceDelta,
    ProvinceEventTransition,
    ProvinceStrategyTransition,
    StrategyFieldChange,
    WorldState,
)

PROVINCE_STRATEGY_PATHS = (
    "overall_support_intensity",
    "subsidy_mix.consumer",
    "subsidy_mix.fixed_cost",
    "subsidy_mix.variable_cost",
    "peer_response_mode",
)


def _path_value(payload: dict[str, object], path: str) -> object:
    current: object = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            raise ValueError(f"cannot resolve strategy path: {path}")
        current = current[segment]
    return current


class ComparisonService:
    def compare(
        self,
        *,
        checkpoint_id: str,
        control: WorldState,
        treatment: WorldState,
        profiles: dict[str, ProvinceProfile],
    ) -> ComparisonResult:
        if (
            control.parent_checkpoint_id != checkpoint_id
            or treatment.parent_checkpoint_id != checkpoint_id
        ):
            raise ValueError("both branches must reference the same year-one checkpoint")
        if control.seed != treatment.seed or control.versions != treatment.versions:
            raise ValueError("same-source branches must share seed and versions")
        if control.province_personas != treatment.province_personas:
            raise ValueError("same-source branches must share province personas")
        policy_changes = policy_diff(control.policy, treatment.policy)
        control_event_id = (
            control.approved_event_scenario.scenario_id
            if control.event_applied and control.approved_event_scenario
            else None
        )
        treatment_event_id = (
            treatment.approved_event_scenario.scenario_id
            if treatment.event_applied and treatment.approved_event_scenario
            else None
        )
        if control.comparison_mode is not treatment.comparison_mode:
            raise ValueError("same-source branches must share comparison mode")
        if control.comparison_mode is ComparisonMode.POLICY_INTERVENTION:
            if not policy_changes or control_event_id != treatment_event_id or not control_event_id:
                raise ValueError(
                    "policy comparison requires one policy difference and the same event"
                )
            same_policy, same_event, active_difference = False, True, "policy"
        else:
            if policy_changes or control_event_id is not None or treatment_event_id is None:
                raise ValueError(
                    "event comparison requires the same policy and event only in treatment"
                )
            same_policy, same_event, active_difference = True, False, "event"
        metric_deltas: dict[str, MetricDelta] = {}
        for field in type(control.national_metrics).model_fields:
            if field == "schema_version":
                continue
            before = float(getattr(control.national_metrics, field))
            after = float(getattr(treatment.national_metrics, field))
            metric_deltas[field] = MetricDelta(
                control=before, treatment=after, delta=round(after - before, 4)
            )
        province_transitions: list[ProvinceStrategyTransition] = []
        province_deltas: list[ProvinceDelta] = []
        for code in sorted(profiles):
            before = control.province_actions[code]
            after = treatment.province_actions[code]
            before_json = before.model_dump(mode="json")
            after_json = after.model_dump(mode="json")
            changes = [
                StrategyFieldChange(
                    path=path,
                    from_value=_path_value(before_json, path),
                    to_value=_path_value(after_json, path),
                )
                for path in PROVINCE_STRATEGY_PATHS
                if _path_value(before_json, path) != _path_value(after_json, path)
            ]
            province_transitions.append(
                ProvinceStrategyTransition(
                    province_code=code,
                    province_name=profiles[code].short_name,
                    control_action_id=before.action_id,
                    treatment_action_id=after.action_id,
                    changed=bool(changes),
                    changes=changes,
                )
            )
            c_state = control.province_states[code]
            t_state = treatment.province_states[code]
            province_deltas.append(
                ProvinceDelta(
                    province_code=code,
                    province_name=profiles[code].short_name,
                    development_delta=round(
                        t_state.development_index - c_state.development_index, 4
                    ),
                    demand_delta=round(t_state.demand_index - c_state.demand_index, 4),
                    industry_activity_delta=round(
                        t_state.industry_activity_index - c_state.industry_activity_index, 4
                    ),
                    fiscal_pressure_delta=round(
                        t_state.fiscal_pressure_index - c_state.fiscal_pressure_index, 4
                    ),
                )
            )
        automaker_transitions: list[AutomakerStrategyTransition] = []
        for automaker_id in sorted(control.automaker_profiles):
            before = control.automaker_actions[automaker_id]
            after = treatment.automaker_actions[automaker_id]
            before_markets = {
                item.province_code: item.model_dump(mode="json")
                for item in before.province_market_actions
            }
            after_markets = {
                item.province_code: item.model_dump(mode="json")
                for item in after.province_market_actions
            }
            changed = sum(before_markets[code] != after_markets[code] for code in before_markets)
            before_facilities = [item.model_dump(mode="json") for item in before.facility_actions]
            after_facilities = [item.model_dump(mode="json") for item in after.facility_actions]
            facility_changes = (
                []
                if before_facilities == after_facilities
                else [
                    StrategyFieldChange(
                        path="facility_actions",
                        from_value=before_facilities,
                        to_value=after_facilities,
                    )
                ]
            )
            automaker_transitions.append(
                AutomakerStrategyTransition(
                    automaker_id=automaker_id,
                    display_name=control.automaker_profiles[automaker_id].display_name,
                    control_action_id=before.action_id,
                    treatment_action_id=after.action_id,
                    changed_province_allocations=changed,
                    facility_changes=facility_changes,
                )
            )
        event_transitions = [
            ProvinceEventTransition(
                province_code=code,
                control_response_id=(
                    control.province_event_responses[code].response_id
                    if code in control.province_event_responses
                    else None
                ),
                treatment_response_id=(
                    treatment.province_event_responses[code].response_id
                    if code in treatment.province_event_responses
                    else None
                ),
                control_mode=(
                    control.province_event_responses[code].response_mode.value
                    if code in control.province_event_responses
                    else None
                ),
                treatment_mode=(
                    treatment.province_event_responses[code].response_mode.value
                    if code in treatment.province_event_responses
                    else None
                ),
            )
            for code in sorted(profiles)
        ]
        mechanism_totals: defaultdict[str, float] = defaultdict(float)
        for key, after in treatment.contributions.items():
            before = control.contributions.get(key)
            if before:
                mechanism_totals[after.target_metric] += after.final_value - before.final_value
        ranked = sorted(province_deltas, key=lambda item: item.development_delta, reverse=True)
        return ComparisonResult(
            experiment_id=control.experiment_id,
            checkpoint_id=checkpoint_id,
            control_branch_id=control.branch_id,
            treatment_branch_id=treatment.branch_id,
            comparison_mode=control.comparison_mode,
            active_difference_proof=ActiveDifferenceProof(
                comparison_mode=control.comparison_mode,
                checkpoint_id=checkpoint_id,
                same_policy=same_policy,
                same_event=same_event,
                active_difference=active_difference,
            ),
            policy_diff=policy_changes,
            event_diff=EventScenarioDiff(
                control_scenario_id=control_event_id,
                treatment_scenario_id=treatment_event_id,
                changed=control_event_id != treatment_event_id,
                description=(
                    "两分支共享同一事件情景"
                    if same_event
                    else "原始分支无事件，事件情景仅作用于干预分支"
                ),
            ),
            delta_gap=round(
                treatment.national_metrics.regional_development_gap
                - control.national_metrics.regional_development_gap,
                4,
            ),
            national_metrics=metric_deltas,
            province_strategy_transitions=province_transitions,
            automaker_strategy_transitions=automaker_transitions,
            province_event_transitions=event_transitions,
            province_deltas=province_deltas,
            mechanism_totals={key: round(value, 4) for key, value in mechanism_totals.items()},
            top_improved=[item.province_code for item in ranked[:5]],
            top_pressured=[item.province_code for item in ranked[-5:]],
        )
