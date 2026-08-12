import json
from datetime import date
from pathlib import Path

from pydantic import Field

from simulation.catalog import automaker_catalog, policy_region_catalog
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.automaker import (
    AutomakerProfile,
    ProductionFootprint,
    ProvinceChannelCoverage,
)
from simulation.models.base import DomainModel
from simulation.models.common import DataQuality, ExpansionPosture
from simulation.models.policy import PolicySchema
from simulation.models.provenance import ProvenanceRecord
from simulation.models.province import ProvinceDecisionPersona, ProvinceProfile
from simulation.models.scenario import ProvinceInteractionEdge, ProvinceInteractionNetwork
from simulation.models.world import BatteryIndustryNode, ProvinceBatteryAccess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PROVINCE_SOURCE_URL = "https://www.stats.gov.cn/sj/ndsj/"
PROVINCE_MECHANISM_FIELDS = (
    "fiscal_capacity",
    "fiscal_rigidity",
    "nev_industry_base",
    "vehicle_manufacturing_base",
    "components_base",
    "rd_activity",
    "market_scale",
    "willingness_to_pay_index",
    "land_cost_index",
    "talent_cost_index",
    "energy_cost_index",
    "logistics_cost_index",
    "battery_supply_distance_index",
    "charging_infrastructure_index",
    "urbanization_index",
    "vehicle_consumption_index",
    "nev_penetration_index",
    "intelligent_driving_readiness_index",
    "regulatory_execution_capacity_index",
    "oil_price_sensitivity_index",
    "supply_chain_complementarity_index",
    "peer_province_codes",
)


class NetworkEdge(DomainModel):
    target: str = Field(pattern=r"^\d{2}$")
    weight: float = Field(ge=0, le=1)


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def load_network(path: Path | None = None) -> dict[str, list[NetworkEdge]]:
    raw = _read_json(path or DATA_DIR / "province_network_v1.json")
    if not isinstance(raw, dict) or not isinstance(raw.get("edges"), dict):
        raise ValueError("province network must contain an edges object")
    network = {
        source: [NetworkEdge.model_validate(edge) for edge in edges]
        for source, edges in raw["edges"].items()
    }
    if set(network) != set(MAINLAND_PROVINCE_CODES):
        raise ValueError("province network must contain the frozen 31 provinces")
    for source, edges in network.items():
        targets = [edge.target for edge in edges]
        if not 3 <= len(edges) <= 5 or len(targets) != len(set(targets)) or source in targets:
            raise ValueError(f"invalid peer network for {source}")
        if not set(targets) <= set(MAINLAND_PROVINCE_CODES):
            raise ValueError(f"{source} references an unknown province")
    return network


def load_interaction_network() -> ProvinceInteractionNetwork:
    """Separate observation permission from reciprocal collaboration eligibility."""

    network = load_network()
    directed = {(source, edge.target) for source, related in network.items() for edge in related}
    return ProvinceInteractionNetwork(
        edges=[
            ProvinceInteractionEdge(
                source_province_code=source,
                target_province_code=edge.target,
                observation_weight=edge.weight,
                coordinate_eligible=(edge.target, source) in directed,
            )
            for source, related in sorted(network.items())
            for edge in related
        ]
    )


def _province_provenance(field_name: str, quality: DataQuality) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_name="国家统计年鉴框架与 PolicyScope V2.1 冻结省级代理画像",
        source_url=PROVINCE_SOURCE_URL,
        source_year=2024,
        retrieved_at=date(2026, 8, 12),
        original_unit="normalized composite proxy",
        original_value=f"province_profiles_v3.json inputs for {field_name}",
        transformation="由冻结省级标准化字段按 V3 机制公式确定性投影，不解释为官方统计值。",
        missing_value_handling="任一必需输入缺失时生成失败，不做运行时填补。",
        quality=quality,
    )


def build_province_profiles(path: Path | None = None) -> dict[str, ProvinceProfile]:
    raw = _read_json(path or DATA_DIR / "province_profiles_v3.json")
    if not isinstance(raw, list):
        raise ValueError("province profile source must be a JSON array")
    source = {str(item["province_code"]): item for item in raw if isinstance(item, dict)}
    if set(source) != set(MAINLAND_PROVINCE_CODES):
        raise ValueError("province profile source must contain the frozen 31 provinces")
    catalog = policy_region_catalog()
    network = load_network()
    profiles: dict[str, ProvinceProfile] = {}
    for code in MAINLAND_PROVINCE_CODES:
        item = source[code]
        scale = float(item["economic_scale"])
        fiscal = float(item["fiscal_capacity"])
        diversity = float(item["industrial_diversity"])
        manufacturing = float(item["advanced_manufacturing_base"])
        digital = float(item["digital_infrastructure"])
        green = float(item["green_energy_base"])
        credit = float(item["credit_access"])
        rigidity = float(item["fiscal_conservatism"])
        rd = float(item["rd_capacity"])
        quality = DataQuality.PROXY
        values = {
            "fiscal_capacity": fiscal,
            "fiscal_rigidity": rigidity,
            "nev_industry_base": _clamp(0.45 * manufacturing + 0.30 * diversity + 0.25 * rd),
            "vehicle_manufacturing_base": manufacturing,
            "components_base": _clamp(0.55 * diversity + 0.45 * manufacturing),
            "rd_activity": rd,
            "market_scale": scale,
            "willingness_to_pay_index": _clamp(0.35 * scale + 0.35 * digital + 0.30 * credit),
            "land_cost_index": _clamp(0.55 * scale + 0.25 * digital + 0.20 * fiscal),
            "talent_cost_index": _clamp(0.45 * rd + 0.30 * digital + 0.25 * scale),
            "energy_cost_index": _clamp(0.65 * (1 - green) + 0.35 * scale),
            "logistics_cost_index": _clamp(0.55 * (1 - digital) + 0.45 * (1 - scale)),
            "battery_supply_distance_index": _clamp(
                0.55 * (1 - manufacturing) + 0.45 * (1 - green)
            ),
            "charging_infrastructure_index": _clamp(0.65 * digital + 0.20 * scale + 0.15 * credit),
            "urbanization_index": _clamp(0.55 * scale + 0.45 * digital),
            "vehicle_consumption_index": _clamp(0.45 * scale + 0.30 * credit + 0.25 * digital),
            "nev_penetration_index": _clamp(0.45 * digital + 0.30 * green + 0.25 * scale),
            "intelligent_driving_readiness_index": _clamp(
                0.45 * rd + 0.35 * digital + 0.20 * manufacturing
            ),
            "regulatory_execution_capacity_index": _clamp(
                0.40 * digital + 0.35 * fiscal + 0.25 * rd
            ),
            "oil_price_sensitivity_index": _clamp(
                0.45 * scale + 0.35 * (1 - green) + 0.20 * (1 - digital)
            ),
            "supply_chain_complementarity_index": _clamp(
                0.40 * diversity + 0.35 * manufacturing + 0.25 * green
            ),
        }
        profiles[code] = ProvinceProfile(
            province_code=code,
            name=catalog[code].name,
            short_name=catalog[code].short_name,
            policy_region=catalog[code].policy_region,
            peer_province_codes=[edge.target for edge in network[code]],
            data_quality=quality,
            provenance={
                field: _province_provenance(field, quality) for field in PROVINCE_MECHANISM_FIELDS
            },
            **values,
        )
    return profiles


def load_profiles(path: Path | None = None) -> dict[str, ProvinceProfile]:
    if path is None:
        return build_province_profiles()
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise ValueError("province profiles must be an array")
    profiles = [ProvinceProfile.model_validate(item) for item in raw]
    result = {item.province_code: item for item in profiles}
    if len(result) != 31:
        raise ValueError("province profiles must contain 31 unique provinces")
    return result


_AUTOMAKER_BASELINES = {
    "byd": (0.98, 0.92, 0.88, 0.90, 0.92, ExpansionPosture.EXPANSION, ("44", "61", "34")),
    "geely": (0.86, 0.82, 0.72, 0.78, 0.81, ExpansionPosture.EXPANSION, ("33", "50", "43")),
    "changan": (0.82, 0.76, 0.69, 0.74, 0.79, ExpansionPosture.DISCIPLINED, ("50", "34", "42")),
    "sgmw": (0.78, 0.60, 0.62, 0.66, 0.76, ExpansionPosture.DISCIPLINED, ("45", "37")),
    "nio": (0.58, 0.55, 0.38, 0.61, 0.58, ExpansionPosture.DEFENSIVE, ("34", "31")),
    "chery": (0.84, 0.85, 0.68, 0.72, 0.83, ExpansionPosture.EXPANSION, ("34", "32")),
    "leapmotor": (0.62, 0.88, 0.57, 0.64, 0.72, ExpansionPosture.EXPANSION, ("33",)),
    "seres": (0.63, 0.90, 0.51, 0.59, 0.74, ExpansionPosture.DISCIPLINED, ("50",)),
    "xiaomi_auto": (0.55, 0.96, 0.43, 0.93, 0.68, ExpansionPosture.EXPANSION, ("11",)),
    "li_auto": (0.68, 0.70, 0.75, 0.86, 0.70, ExpansionPosture.DISCIPLINED, ("11", "32")),
}

_AUTOMAKER_URLS = {
    "byd": "https://www.bydglobal.com/cn/InvestorNotice.html",
    "geely": "https://www.geelyauto.com.hk/financial_statements/",
    "changan": "https://www.changan.com.cn/",
    "sgmw": "https://www.sgmw.com.cn/",
    "nio": "https://ir.nio.com/financials/annual-reports",
    "chery": "https://www.chery.cn/",
    "leapmotor": "https://ir.leapmotor.com/",
    "seres": "https://www.seres.cn/",
    "xiaomi_auto": "https://ir.mi.com/financial-information/annual-reports",
    "li_auto": "https://ir.lixiang.com/financials/annual-reports",
}


def _automaker_provenance(automaker_id: str, field_name: str) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_name=f"{automaker_catalog()[automaker_id].display_name}公开披露与官网资料",
        source_url=_AUTOMAKER_URLS[automaker_id],
        source_year=2025,
        retrieved_at=date(2026, 8, 12),
        original_unit="public disclosure / normalized baseline",
        original_value=f"frozen 2025 baseline for {field_name}",
        transformation="公开资料仅用于构造 0–1 冻结基线；模拟期不生成现实销量、利润或投资金额。",
        missing_value_handling="缺失口径采用透明代理映射并标记 proxy。",
        quality=DataQuality.PROXY,
    )


def load_automaker_profiles() -> dict[str, AutomakerProfile]:
    provinces = load_profiles()
    catalog = automaker_catalog()
    profiles: dict[str, AutomakerProfile] = {}
    provenance_fields = (
        "liquidity_index",
        "sales_scale_index",
        "sales_growth_index",
        "product_segment_mix",
        "profitability_index",
        "production_footprint",
        "technology_route_mix",
        "capacity_utilization_index",
        "channel_coverage_by_province",
    )
    for position, automaker_id in enumerate(AUTOMAKER_IDS):
        scale, growth, profit, liquidity, capacity, posture, footprints = _AUTOMAKER_BASELINES[
            automaker_id
        ]
        coverage = [
            ProvinceChannelCoverage(
                province_code=code,
                coverage_index=_clamp(
                    0.30
                    + 0.45 * provinces[code].market_scale
                    + 0.18 * scale
                    + ((position + int(code)) % 7) / 100
                ),
            )
            for code in MAINLAND_PROVINCE_CODES
        ]
        profiles[automaker_id] = AutomakerProfile(
            automaker_id=automaker_id,
            display_name=catalog[automaker_id].display_name,
            entity_scope="全国性真实车企模拟 Agent；经营资料为冻结基线，未来动作仅为机制实验输出。",
            sales_scale_index=scale,
            sales_growth_index=growth,
            profitability_index=profit,
            liquidity_index=liquidity,
            capacity_utilization_index=capacity,
            channel_coverage_by_province=coverage,
            production_footprint=[
                ProductionFootprint(
                    province_code=code,
                    role="mixed",
                    baseline_note="公开资料归纳的冻结经营布局",
                    provenance_ref="production_footprint",
                )
                for code in footprints
            ],
            product_segment_mix={"mass_market": 0.55, "premium": 0.25, "commercial_or_other": 0.20},
            technology_route_mix={"bev": 0.65, "phev_or_erev": 0.30, "other": 0.05},
            expansion_posture=posture,
            data_quality=DataQuality.PROXY,
            provenance={
                field: _automaker_provenance(automaker_id, field) for field in provenance_fields
            },
        )
    return profiles


def load_battery_industry_nodes() -> dict[str, BatteryIndustryNode]:
    nodes = {
        "34": BatteryIndustryNode(
            province_code="34", node_strength=0.90, node_type="battery_and_vehicle"
        ),
        "44": BatteryIndustryNode(
            province_code="44", node_strength=1.00, node_type="battery_and_vehicle"
        ),
        "32": BatteryIndustryNode(
            province_code="32", node_strength=0.82, node_type="battery_supply_chain"
        ),
        "51": BatteryIndustryNode(
            province_code="51", node_strength=0.75, node_type="battery_materials"
        ),
        "50": BatteryIndustryNode(
            province_code="50", node_strength=0.78, node_type="vehicle_and_battery"
        ),
    }
    return nodes


def load_battery_access() -> dict[str, ProvinceBatteryAccess]:
    profiles = load_profiles()
    nodes = tuple(load_battery_industry_nodes())
    return {
        code: ProvinceBatteryAccess(
            province_code=code,
            nearest_node_code=min(nodes, key=lambda node: abs(int(node) - int(code))),
            distance_index=profile.battery_supply_distance_index,
        )
        for code, profile in profiles.items()
    }


def build_province_personas() -> dict[str, ProvinceDecisionPersona]:
    from simulation.services.persona import build_province_personas

    return build_province_personas(load_profiles(), load_network())


def load_province_personas() -> dict[str, ProvinceDecisionPersona]:
    return build_province_personas()


def load_scenario_policy(path: Path | None = None) -> PolicySchema:
    if path is None:
        return PolicySchema()
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError("scenario must be a JSON object")
    return PolicySchema.model_validate(raw.get("policy", raw))
