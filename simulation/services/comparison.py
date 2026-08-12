from collections import defaultdict

from simulation.llm.fake_provider import policy_diff
from simulation.models.province import ProvinceProfile
from simulation.models.world import (
    AutomakerStrategyTransition,
    ComparisonResult,
    MetricDelta,
    ProvinceDelta,
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
            policy_diff=policy_diff(control.policy, treatment.policy),
            delta_gap=round(
                treatment.national_metrics.regional_development_gap
                - control.national_metrics.regional_development_gap,
                4,
            ),
            national_metrics=metric_deltas,
            province_strategy_transitions=province_transitions,
            automaker_strategy_transitions=automaker_transitions,
            province_deltas=province_deltas,
            mechanism_totals={key: round(value, 4) for key, value in mechanism_totals.items()},
            top_improved=[item.province_code for item in ranked[:5]],
            top_pressured=[item.province_code for item in ranked[-5:]],
        )
