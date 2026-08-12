from simulation.data import NetworkEdge
from simulation.models.common import DataQuality, ProvinceConstraint, ProvincePersonaType
from simulation.models.province import ProvinceDecisionPersona, ProvincePersonaAxes, ProvinceProfile


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def build_province_personas(
    profiles: dict[str, ProvinceProfile], network: dict[str, list[NetworkEdge]]
) -> dict[str, ProvinceDecisionPersona]:
    personas: dict[str, ProvinceDecisionPersona] = {}
    type_order = list(ProvincePersonaType)
    for code, profile in profiles.items():
        peer_weight = sum(edge.weight for edge in network[code]) / len(network[code])
        axes = ProvincePersonaAxes(
            fiscal_capacity=profile.fiscal_capacity,
            industry_attraction=_clamp(
                0.45 * profile.nev_industry_base
                + 0.30 * profile.rd_activity
                + 0.25 * (1 - profile.land_cost_index)
            ),
            consumption_activation=_clamp(
                0.45 * profile.market_scale
                + 0.35 * profile.willingness_to_pay_index
                + 0.20 * profile.charging_infrastructure_index
            ),
            operating_cost_competitiveness=_clamp(
                1
                - (
                    0.30 * profile.land_cost_index
                    + 0.25 * profile.talent_cost_index
                    + 0.25 * profile.energy_cost_index
                    + 0.20 * profile.logistics_cost_index
                )
            ),
            supply_chain_coordination=_clamp(
                0.45 * (1 - profile.battery_supply_distance_index)
                + 0.35 * profile.components_base
                + 0.20 * profile.vehicle_manufacturing_base
            ),
            peer_response_sensitivity=_clamp(
                0.55 * peer_weight + 0.45 * (1 - abs(profile.market_scale - 0.5))
            ),
        )
        scores = {
            ProvincePersonaType.FISCALLY_PRUDENT: axes.fiscal_capacity,
            ProvincePersonaType.INDUSTRY_ATTRACTOR: axes.industry_attraction,
            ProvincePersonaType.CONSUMPTION_ACTIVATOR: axes.consumption_activation,
            ProvincePersonaType.OPERATING_COST_COMPETITOR: axes.operating_cost_competitiveness,
            ProvincePersonaType.SUPPLY_CHAIN_COORDINATOR: axes.supply_chain_coordination,
            ProvincePersonaType.PEER_RESPONDER: axes.peer_response_sensitivity,
        }
        ranked = sorted(scores, key=lambda item: (-scores[item], type_order.index(item)))
        constraints = sorted(
            {
                ProvinceConstraint.FISCAL_RIGIDITY: profile.fiscal_rigidity,
                ProvinceConstraint.WEAK_CONSUMER_WTP: 1 - profile.willingness_to_pay_index,
                ProvinceConstraint.WEAK_INDUSTRY_BASE: 1 - profile.nev_industry_base,
                ProvinceConstraint.BATTERY_DISTANCE: profile.battery_supply_distance_index,
                ProvinceConstraint.TALENT_COST: profile.talent_cost_index,
                ProvinceConstraint.ENERGY_COST: profile.energy_cost_index,
                ProvinceConstraint.LOGISTICS_COST: profile.logistics_cost_index,
            },
            key=lambda item: (
                -{
                    ProvinceConstraint.FISCAL_RIGIDITY: profile.fiscal_rigidity,
                    ProvinceConstraint.WEAK_CONSUMER_WTP: 1 - profile.willingness_to_pay_index,
                    ProvinceConstraint.WEAK_INDUSTRY_BASE: 1 - profile.nev_industry_base,
                    ProvinceConstraint.BATTERY_DISTANCE: profile.battery_supply_distance_index,
                    ProvinceConstraint.TALENT_COST: profile.talent_cost_index,
                    ProvinceConstraint.ENERGY_COST: profile.energy_cost_index,
                    ProvinceConstraint.LOGISTICS_COST: profile.logistics_cost_index,
                }[item]
            ),
        )[:3]
        personas[code] = ProvinceDecisionPersona(
            province_code=code,
            axes=axes,
            primary_type=ranked[0],
            secondary_type=ranked[1],
            key_constraints=constraints,
            data_quality=DataQuality.PROXY,
            summary=f"{profile.short_name}本次实验画像：{ranked[0].value}，重点约束为{constraints[0].value}。",
        )
    return personas
