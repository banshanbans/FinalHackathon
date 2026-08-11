import json
from pathlib import Path

from pydantic import BaseModel, Field

from simulation.models.common import DataQuality, EnterpriseArchetype
from simulation.models.enterprise import EnterpriseArchetypeDefinition, EnterpriseGroupProfile
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


class NetworkEdge(BaseModel):
    target: str
    weight: float = Field(ge=0, le=1)


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def load_profiles(path: Path | None = None) -> dict[str, ProvinceProfile]:
    """Load the frozen province source and project it into the V2 equipment profile."""

    raw = _read_json(path or DATA_DIR / "province_profiles_v1.json")
    if not isinstance(raw, list):
        raise ValueError("province profiles must be a JSON array")
    profiles: list[ProvinceProfile] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("province profile entries must be objects")
        profiles.append(
            ProvinceProfile(
                province_code=str(item["province_code"]),
                name=str(item["name"]),
                short_name=str(item["short_name"]),
                region_group=item["region_group"],
                economic_scale=float(item["economic_scale"]),
                fiscal_capacity=float(item["fiscal_capacity"]),
                industrial_diversity=float(item["industrial_diversity"]),
                advanced_manufacturing_base=float(item["advanced_manufacturing_base"]),
                digital_infrastructure=float(item["digital_infrastructure"]),
                green_energy_base=float(item["green_energy_base"]),
                sme_density=_clamp(
                    0.72 * float(item["industrial_diversity"])
                    + 0.28 * (1 - float(item["economic_scale"]))
                ),
                credit_access=_clamp(
                    0.45 * float(item["fiscal_capacity"])
                    + 0.35 * float(item["digital_infrastructure"])
                    + 0.20 * float(item["economic_scale"])
                ),
                transition_pressure=float(item["transition_pressure"]),
                fiscal_conservatism=float(item["fiscal_conservatism"]),
                data_quality=DataQuality(str(item["data_quality"])),
                source_year=int(item["source_year"]),
            )
        )
    result = {profile.province_code: profile for profile in profiles}
    if len(result) != len(profiles):
        raise ValueError("province codes must be unique")
    return result


def load_network(path: Path | None = None) -> dict[str, list[NetworkEdge]]:
    raw = _read_json(path or DATA_DIR / "province_network_v1.json")
    if not isinstance(raw, dict) or not isinstance(raw.get("edges"), dict):
        raise ValueError("province network must contain an edges object")
    return {
        source: [NetworkEdge.model_validate(edge) for edge in edges]
        for source, edges in raw["edges"].items()
    }


def load_enterprise_archetypes(
    path: Path | None = None,
) -> dict[EnterpriseArchetype, EnterpriseArchetypeDefinition]:
    raw = _read_json(path or DATA_DIR / "enterprise_archetypes_v2.json")
    if not isinstance(raw, list):
        raise ValueError("enterprise archetypes must be a JSON array")
    definitions = [EnterpriseArchetypeDefinition.model_validate(item) for item in raw]
    result = {item.archetype: item for item in definitions}
    if set(result) != set(EnterpriseArchetype):
        raise ValueError("enterprise archetypes must contain exactly six frozen types")
    if abs(sum(item.weight for item in result.values()) - 1.0) > 1e-6:
        raise ValueError("enterprise archetype weights must sum to 1")
    return result


def _blend(base: float, province_value: float, *, base_weight: float = 0.72) -> float:
    return _clamp(base_weight * base + (1 - base_weight) * province_value)


def build_enterprise_profiles(
    provinces: dict[str, ProvinceProfile] | None = None,
    archetypes: dict[EnterpriseArchetype, EnterpriseArchetypeDefinition] | None = None,
) -> dict[str, EnterpriseGroupProfile]:
    province_profiles = provinces or load_profiles()
    definitions = archetypes or load_enterprise_archetypes()
    groups: dict[str, EnterpriseGroupProfile] = {}
    for province_code, province in sorted(province_profiles.items()):
        for archetype, definition in definitions.items():
            enterprise_id = f"{province_code}:{archetype.value}"
            groups[enterprise_id] = EnterpriseGroupProfile(
                enterprise_id=enterprise_id,
                province_code=province_code,
                archetype=archetype,
                display_name=definition.display_name,
                weight=definition.weight,
                equipment_age_pressure=_blend(
                    definition.equipment_age_pressure, province.transition_pressure
                ),
                digital_readiness=_blend(
                    definition.digital_readiness, province.digital_infrastructure
                ),
                green_transition_pressure=_blend(
                    definition.green_transition_pressure, province.transition_pressure
                ),
                financing_constraint=_blend(
                    definition.financing_constraint, 1 - province.credit_access
                ),
                collateral_capacity=_blend(
                    definition.collateral_capacity, province.fiscal_capacity
                ),
                cash_flow_resilience=_blend(
                    definition.cash_flow_resilience, province.economic_scale
                ),
                export_exposure=definition.export_exposure,
                data_quality=definition.data_quality,
            )
    if len(groups) != 186:
        raise ValueError(f"expected 186 enterprise groups, got {len(groups)}")
    return groups


def load_enterprise_profiles(
    path: Path | None = None,
) -> dict[str, EnterpriseGroupProfile]:
    raw = _read_json(path or DATA_DIR / "enterprise_groups_v2.json")
    if not isinstance(raw, list):
        raise ValueError("enterprise groups must be a JSON array")
    profiles = [EnterpriseGroupProfile.model_validate(item) for item in raw]
    result = {item.enterprise_id: item for item in profiles}
    if len(profiles) != 186 or len(result) != 186:
        raise ValueError("enterprise group snapshot must contain 186 unique IDs")
    expected = build_enterprise_profiles()
    if result != expected:
        raise ValueError("enterprise group snapshot differs from deterministic V2 generation")
    return result


def enterprise_profiles_by_province(
    profiles: dict[str, EnterpriseGroupProfile] | None = None,
) -> dict[str, list[EnterpriseGroupProfile]]:
    groups: dict[str, list[EnterpriseGroupProfile]] = {}
    for profile in (profiles or load_enterprise_profiles()).values():
        groups.setdefault(profile.province_code, []).append(profile)
    for items in groups.values():
        items.sort(key=lambda item: item.archetype.value)
    return groups


def load_scenario_policy(path: Path | None = None) -> PolicySchema:
    raw = _read_json(path or DATA_DIR / "scenarios" / "equipment_renewal_default.json")
    if not isinstance(raw, dict):
        raise ValueError("scenario must be a JSON object")
    return PolicySchema.model_validate(raw["policy"])
