from collections import defaultdict

from simulation.models.central import CentralReview
from simulation.models.province import ProvinceProfile
from simulation.models.world import (
    ComparisonResult,
    MetricDelta,
    ProvinceDelta,
    WorldState,
)


class ComparisonService:
    """Builds auditable deltas from two states sharing one checkpoint."""

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
        if control.versions.data != treatment.versions.data:
            raise ValueError("branches use different data versions")
        if control.versions.mechanism != treatment.versions.mechanism:
            raise ValueError("branches use different mechanism versions")

        control_policy = control.policy.model_dump(mode="json")
        treatment_policy = treatment.policy.model_dump(mode="json")
        policy_diff: dict[str, dict[str, float]] = {}
        for field in (
            "central_budget_index",
            "local_match_requirement",
            "regional_bias",
            "cooperation_incentive",
        ):
            before = float(control_policy[field])
            after = float(treatment_policy[field])
            if abs(before - after) > 1e-9:
                policy_diff[field] = {"control": before, "treatment": after}

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
                policy_benefit_delta=round(
                    treatment.provinces[code].policy_benefit_index
                    - control.provinces[code].policy_benefit_index,
                    4,
                ),
                accessibility_delta=round(
                    treatment.provinces[code].policy_accessibility
                    - control.provinces[code].policy_accessibility,
                    4,
                ),
                fiscal_pressure_delta=round(
                    treatment.provinces[code].fiscal_pressure
                    - control.provinces[code].fiscal_pressure,
                    4,
                ),
            )
            for code in sorted(control.provinces)
        ]

        mechanism_totals: defaultdict[str, float] = defaultdict(float)
        fields = [
            "policy_match",
            "central_support",
            "local_investment",
            "cooperation_spillover",
            "geographic_spillover",
            "competition_crowding_out",
            "fiscal_execution_cost",
        ]
        for code in control.provinces:
            control_contribution = control.contributions.get(code)
            treatment_contribution = treatment.contributions.get(code)
            if not control_contribution or not treatment_contribution:
                continue
            for field in fields:
                mechanism_totals[field] += getattr(treatment_contribution, field) - getattr(
                    control_contribution, field
                )

        sorted_deltas = sorted(
            province_deltas, key=lambda item: item.policy_benefit_delta, reverse=True
        )
        return ComparisonResult(
            experiment_id=control.experiment_id,
            checkpoint_id=checkpoint_id,
            control_branch_id=control.branch_id,
            treatment_branch_id=treatment.branch_id,
            policy_diff=policy_diff,
            national_metrics=metrics,
            province_deltas=province_deltas,
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
        for finding in review.findings:
            invalid = [ref for ref in finding.evidence_refs if ref not in allowed]
            if invalid:
                raise ValueError(f"central review contains invalid evidence refs: {invalid}")
