from collections import defaultdict
from statistics import fmean

from simulation.llm.fake_provider import policy_diff
from simulation.models.central import CentralReview
from simulation.models.common import EnterpriseArchetype, Participation
from simulation.models.province import ProvinceProfile
from simulation.models.world import (
    ActionMigration,
    ComparisonResult,
    EnterpriseGroupChange,
    MetricDelta,
    ProvinceDelta,
    ProvinceStrategyFieldChange,
    ProvinceStrategyTransition,
    WorldState,
)

PROVINCE_STRATEGY_PATHS = (
    "primary_goal",
    "decision_posture",
    "target_enterprise_groups",
    "interprovincial_strategy",
    "target_province_codes",
    "implementation_intensity",
    "local_match_ratio",
    "instrument_mix.direct_subsidy",
    "instrument_mix.interest_subsidy",
    "instrument_mix.financing_guarantee",
    "sme_preference",
    "regional_delivery_focus",
    "technology_mix.digital",
    "technology_mix.green",
    "technology_mix.general",
    "requested_central_support",
)


def _path_value(payload: dict[str, object], path: str) -> object:
    current: object = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            raise ValueError(f"cannot resolve province strategy path: {path}")
        current = current[segment]
    return current


class ComparisonService:
    """Creates a traceable V2.1 comparison from checkpoint sibling branches."""

    def compare(
        self,
        *,
        checkpoint_id: str,
        control: WorldState,
        treatment: WorldState,
        profiles: dict[str, ProvinceProfile],
    ) -> ComparisonResult:
        if control.parent_checkpoint_id != checkpoint_id:
            raise ValueError("control branch does not reference the requested checkpoint")
        if treatment.parent_checkpoint_id != checkpoint_id:
            raise ValueError("treatment branch does not reference the requested checkpoint")
        for field in ("data", "mechanism", "prompt", "model"):
            if getattr(control.versions, field) != getattr(treatment.versions, field):
                raise ValueError(f"branches use different {field} versions")
        if control.seed != treatment.seed:
            raise ValueError("branches use different seeds")
        if control.province_personas != treatment.province_personas:
            raise ValueError("branches use different province personas")

        strategy_transitions: list[ProvinceStrategyTransition] = []
        for code in sorted(profiles):
            before = control.province_actions[code]
            after = treatment.province_actions[code]
            before_json = before.model_dump(mode="json")
            after_json = after.model_dump(mode="json")
            changes = [
                ProvinceStrategyFieldChange(
                    path=path,
                    from_value=_path_value(before_json, path),
                    to_value=_path_value(after_json, path),
                )
                for path in PROVINCE_STRATEGY_PATHS
                if _path_value(before_json, path) != _path_value(after_json, path)
            ]
            strategy_transitions.append(
                ProvinceStrategyTransition(
                    province_code=code,
                    province_name=profiles[code].short_name,
                    persona_primary_type=control.province_personas[code].primary_type,
                    control_action_id=before.action_id,
                    treatment_action_id=after.action_id,
                    changed=bool(changes),
                    changes=changes,
                )
            )

        metrics: dict[str, MetricDelta] = {}
        for field in type(control.national_metrics).model_fields:
            if field == "schema_version":
                continue
            before = float(getattr(control.national_metrics, field))
            after = float(getattr(treatment.national_metrics, field))
            metrics[field] = MetricDelta(
                control=round(before, 4),
                treatment=round(after, 4),
                delta=round(after - before, 4),
            )

        province_deltas = [
            ProvinceDelta(
                province_code=code,
                province_name=profiles[code].short_name,
                enterprise_participation_delta=round(
                    treatment.province_states[code].enterprise_participation_index
                    - control.province_states[code].enterprise_participation_index,
                    4,
                ),
                renewal_willingness_delta=round(
                    treatment.province_states[code].equipment_renewal_willingness_index
                    - control.province_states[code].equipment_renewal_willingness_index,
                    4,
                ),
                sme_financing_accessibility_delta=round(
                    treatment.province_states[code].sme_financing_accessibility_index
                    - control.province_states[code].sme_financing_accessibility_index,
                    4,
                ),
                fiscal_pressure_delta=round(
                    treatment.province_states[code].fiscal_pressure_index
                    - control.province_states[code].fiscal_pressure_index,
                    4,
                ),
            )
            for code in sorted(control.province_states)
        ]

        migration_counts: defaultdict[tuple[Participation, Participation], int] = defaultdict(int)
        for enterprise_id, control_action in control.enterprise_actions.items():
            treatment_action = treatment.enterprise_actions[enterprise_id]
            migration_counts[(control_action.participation, treatment_action.participation)] += 1
        migrations = [
            ActionMigration(
                from_participation=source,
                to_participation=target,
                count=count,
            )
            for (source, target), count in sorted(
                migration_counts.items(), key=lambda item: (item[0][0].value, item[0][1].value)
            )
        ]

        group_changes: list[EnterpriseGroupChange] = []
        for archetype in EnterpriseArchetype:
            ids = [
                enterprise_id
                for enterprise_id, profile in control.enterprise_profiles.items()
                if profile.archetype == archetype
            ]
            group_changes.append(
                EnterpriseGroupChange(
                    archetype=archetype.value,
                    participation_delta=round(
                        fmean(
                            treatment.enterprise_states[key].participation_score
                            - control.enterprise_states[key].participation_score
                            for key in ids
                        ),
                        4,
                    ),
                    renewal_willingness_delta=round(
                        fmean(
                            treatment.enterprise_states[key].renewal_willingness
                            - control.enterprise_states[key].renewal_willingness
                            for key in ids
                        ),
                        4,
                    ),
                    financing_accessibility_delta=round(
                        fmean(
                            treatment.enterprise_states[key].financing_accessibility
                            - control.enterprise_states[key].financing_accessibility
                            for key in ids
                        ),
                        4,
                    ),
                )
            )

        contribution_fields = [
            "policy_match",
            "direct_subsidy",
            "interest_subsidy",
            "financing_guarantee",
            "sme_preference",
            "regional_support",
            "financing_constraint",
            "fiscal_cost",
        ]
        mechanism_totals: defaultdict[str, float] = defaultdict(float)
        for enterprise_id in control.enterprise_profiles:
            before = control.contributions.get(enterprise_id)
            after = treatment.contributions.get(enterprise_id)
            if not before or not after:
                continue
            for field in contribution_fields:
                mechanism_totals[field] += getattr(after, field) - getattr(before, field)

        sorted_deltas = sorted(
            province_deltas,
            key=lambda item: item.enterprise_participation_delta,
            reverse=True,
        )
        return ComparisonResult(
            experiment_id=control.experiment_id,
            checkpoint_id=checkpoint_id,
            control_branch_id=control.branch_id,
            treatment_branch_id=treatment.branch_id,
            policy_diff=policy_diff(control.policy, treatment.policy),
            national_metrics=metrics,
            province_strategy_transitions=strategy_transitions,
            province_deltas=province_deltas,
            action_migrations=migrations,
            enterprise_group_changes=group_changes,
            mechanism_totals={field: round(value, 4) for field, value in mechanism_totals.items()},
            top_improved=[item.province_code for item in sorted_deltas[:5]],
            top_pressured=[item.province_code for item in sorted_deltas[-5:]],
        )

    @staticmethod
    def validate_review(review: CentralReview, comparison: ComparisonResult) -> None:
        allowed = {
            f"comparison:national_metrics:{metric}" for metric in comparison.national_metrics
        }
        allowed.update(
            f"comparison:province:{item.province_code}" for item in comparison.province_deltas
        )
        allowed.update(
            f"comparison:province_strategy:{item.province_code}"
            for item in comparison.province_strategy_transitions
        )
        for finding in review.findings:
            invalid = [ref for ref in finding.evidence_refs if ref not in allowed]
            if invalid:
                raise ValueError(f"central review contains invalid evidence refs: {invalid}")
