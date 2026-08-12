from simulation.models.world import ComparisonResult


def comparison_review_evidence_refs(comparison: ComparisonResult) -> list[str]:
    """Return the only evidence refs a comparison review may cite."""

    refs = [
        f"comparison:national_metrics:{metric}"
        for metric in comparison.national_metrics
    ]
    refs.extend(
        f"comparison:province:{item.province_code}"
        for item in comparison.province_deltas
    )
    refs.extend(
        f"comparison:province_strategy:{item.province_code}"
        for item in comparison.province_strategy_transitions
    )
    refs.append("comparison:policy_diff")
    return refs
