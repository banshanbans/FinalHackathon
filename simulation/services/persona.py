from collections.abc import Mapping, Sequence
from typing import Protocol

from simulation.models.action import ProvinceAction
from simulation.models.common import (
    DataQuality,
    InterprovincialStrategy,
    ProvinceConstraint,
    ProvincePersonaType,
    ProvincePriorityGoal,
)
from simulation.models.province import (
    ProvinceDecisionPersona,
    ProvincePersonaAxes,
    ProvinceProfile,
)


class WeightedEdge(Protocol):
    weight: float


AXIS_ORDER = (
    "green_priority",
    "sme_inclusiveness",
    "technology_ambition",
    "cooperation_orientation",
    "fiscal_prudence",
    "execution_drive",
)

AXIS_TYPES = {
    "execution_drive": ProvincePersonaType.EXECUTION_DRIVEN,
    "fiscal_prudence": ProvincePersonaType.FISCALLY_PRUDENT,
    "sme_inclusiveness": ProvincePersonaType.INCLUSIVE_DIFFUSION,
    "technology_ambition": ProvincePersonaType.TECHNOLOGY_LEAP,
    "green_priority": ProvincePersonaType.GREEN_TRANSITION,
    "cooperation_orientation": ProvincePersonaType.REGIONAL_COLLABORATION,
}

TYPE_GOALS = {
    ProvincePersonaType.EXECUTION_DRIVEN: ProvincePriorityGoal.EQUIPMENT_RENEWAL,
    ProvincePersonaType.FISCALLY_PRUDENT: ProvincePriorityGoal.FISCAL_SUSTAINABILITY,
    ProvincePersonaType.INCLUSIVE_DIFFUSION: ProvincePriorityGoal.SME_FINANCING_ACCESS,
    ProvincePersonaType.TECHNOLOGY_LEAP: ProvincePriorityGoal.DIGITAL_UPGRADE,
    ProvincePersonaType.GREEN_TRANSITION: ProvincePriorityGoal.GREEN_EQUIPMENT_RENEWAL,
    ProvincePersonaType.REGIONAL_COLLABORATION: ProvincePriorityGoal.CROSS_REGIONAL_COORDINATION,
}

TYPE_LABELS = {
    ProvincePersonaType.EXECUTION_DRIVEN: "执行攻坚型",
    ProvincePersonaType.FISCALLY_PRUDENT: "财政审慎型",
    ProvincePersonaType.INCLUSIVE_DIFFUSION: "普惠扩散型",
    ProvincePersonaType.TECHNOLOGY_LEAP: "技术跃迁型",
    ProvincePersonaType.GREEN_TRANSITION: "绿色转型型",
    ProvincePersonaType.REGIONAL_COLLABORATION: "区域协同型",
}

CONSTRAINT_ORDER = (
    ProvinceConstraint.FISCAL_GAP,
    ProvinceConstraint.FINANCING_GAP,
    ProvinceConstraint.TRANSITION_PRESSURE,
    ProvinceConstraint.WEAK_DIGITAL_BASE,
    ProvinceConstraint.EMPLOYMENT_PRESSURE,
    ProvinceConstraint.INDUSTRIAL_CONCENTRATION,
)


def _raw_axes(profile: ProvinceProfile, related: Sequence[WeightedEdge]) -> dict[str, float]:
    network_weight = sum(edge.weight for edge in related) / len(related) if related else 0
    return {
        "execution_drive": (
            0.35 * profile.fiscal_capacity
            + 0.25 * profile.advanced_manufacturing_base
            + 0.20 * profile.digital_infrastructure
            + 0.20 * profile.economic_scale
        ),
        "fiscal_prudence": (
            0.70 * profile.fiscal_conservatism + 0.30 * (1 - profile.fiscal_capacity)
        ),
        "sme_inclusiveness": (
            0.40 * profile.sme_density
            + 0.35 * (1 - profile.credit_access)
            + 0.25 * profile.employment_pressure
        ),
        "technology_ambition": (
            0.40 * profile.advanced_manufacturing_base
            + 0.35 * profile.digital_infrastructure
            + 0.25 * profile.rd_capacity
        ),
        "green_priority": (
            0.50 * profile.transition_pressure
            + 0.30 * profile.green_energy_base
            + 0.20 * (1 - profile.industrial_diversity)
        ),
        "cooperation_orientation": (0.70 * profile.cooperation_tendency + 0.30 * network_weight),
    }


def _percentiles(values: Mapping[str, float]) -> dict[str, float]:
    """Return inclusive 0–1 percentile ranks with average rank for ties."""

    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    denominator = max(1, len(ordered) - 1)
    result: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1][1] == ordered[index][1]:
            end += 1
        average_zero_based_rank = (index + end) / 2
        percentile = average_zero_based_rank / denominator
        for position in range(index, end + 1):
            result[ordered[position][0]] = percentile
        index = end + 1
    return result


def _constraints(profile: ProvinceProfile) -> list[ProvinceConstraint]:
    scores = {
        ProvinceConstraint.FISCAL_GAP: 1 - profile.fiscal_capacity,
        ProvinceConstraint.FINANCING_GAP: 1 - profile.credit_access,
        ProvinceConstraint.TRANSITION_PRESSURE: profile.transition_pressure,
        ProvinceConstraint.WEAK_DIGITAL_BASE: 1 - profile.digital_infrastructure,
        ProvinceConstraint.EMPLOYMENT_PRESSURE: profile.employment_pressure,
        ProvinceConstraint.INDUSTRIAL_CONCENTRATION: 1 - profile.industrial_diversity,
    }
    priority = {constraint: index for index, constraint in enumerate(CONSTRAINT_ORDER)}
    return sorted(scores, key=lambda item: (-scores[item], priority[item]))[:2]


def build_province_personas(
    profiles: Mapping[str, ProvinceProfile],
    network: Mapping[str, Sequence[WeightedEdge]],
) -> dict[str, ProvinceDecisionPersona]:
    """Build deterministic decision personas from frozen profiles and network edges."""

    if set(profiles) != set(network):
        raise ValueError("persona generation requires matching profile and network provinces")
    raw_by_axis: dict[str, dict[str, float]] = {axis: {} for axis in AXIS_TYPES}
    for code, profile in profiles.items():
        for axis, value in _raw_axes(profile, network[code]).items():
            raw_by_axis[axis][code] = value
    percentiles = {axis: _percentiles(values) for axis, values in raw_by_axis.items()}
    tie_priority = {axis: index for index, axis in enumerate(AXIS_ORDER)}
    personas: dict[str, ProvinceDecisionPersona] = {}
    for code, profile in sorted(profiles.items()):
        unrounded = {axis: percentiles[axis][code] for axis in AXIS_TYPES}
        ranked = sorted(
            unrounded,
            key=lambda axis: (-unrounded[axis], tie_priority[axis]),
        )
        primary_type = AXIS_TYPES[ranked[0]]
        secondary_type = (
            AXIS_TYPES[ranked[1]] if unrounded[ranked[0]] - unrounded[ranked[1]] <= 0.10 else None
        )
        goals = [TYPE_GOALS[primary_type]]
        if secondary_type and TYPE_GOALS[secondary_type] not in goals:
            goals.append(TYPE_GOALS[secondary_type])
        secondary_copy = f"，兼顾{TYPE_LABELS[secondary_type]}" if secondary_type else ""
        personas[code] = ProvinceDecisionPersona(
            province_code=code,
            axes=ProvincePersonaAxes(
                **{axis: round(value, 4) for axis, value in unrounded.items()}
            ),
            primary_type=primary_type,
            secondary_type=secondary_type,
            priority_goals=goals,
            key_constraints=_constraints(profile),
            data_quality=(
                DataQuality.DEMO if profile.data_quality == DataQuality.DEMO else DataQuality.PROXY
            ),
            public_summary=(
                f"本次实验决策画像为{TYPE_LABELS[primary_type]}{secondary_copy}，"
                "用于约束地方策略选择。"
            ),
        )
    return personas


def validate_interprovincial_targets(action: ProvinceAction, allowed_targets: set[str]) -> None:
    """Reject targets outside the current frozen Top-K province network."""

    targets = set(action.target_province_codes)
    if action.interprovincial_strategy == InterprovincialStrategy.INDEPENDENT:
        if targets:
            raise ValueError("independent strategy cannot contain province targets")
        return
    if not targets or not targets <= allowed_targets:
        raise ValueError("province strategy targets must come from the current Top-K network")
