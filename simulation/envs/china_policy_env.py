import json
from copy import deepcopy
from pathlib import Path
from statistics import mean, pstdev

import yaml

from simulation.data import NetworkEdge
from simulation.models.action import MechanismContribution, ProvinceAction
from simulation.models.central import CentralIntervention
from simulation.models.common import (
    Industry,
    InteractionStrategy,
    Phase,
    RegionGroup,
    TalentStrategy,
)
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState
from simulation.models.world import NationalMetrics, NetworkEffect


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    if value != value or value in {float("inf"), float("-inf")}:
        raise ValueError("simulation produced a non-finite value")
    return round(max(minimum, min(maximum, value)), 4)


class ChinaPolicyEnv:
    """Deterministic, versioned environment that is the sole owner of result calculation."""

    def __init__(
        self,
        *,
        profiles: dict[str, ProvinceProfile],
        network: dict[str, list[NetworkEdge]],
        policy: PolicySchema,
        states: dict[str, ProvinceState] | None = None,
        mechanism_path: Path | None = None,
    ):
        self.profiles = profiles
        self.network = network
        self.policy = policy.model_copy(deep=True)
        self.states = states or self._initial_states(profiles)
        self.pending_actions: dict[str, ProvinceAction] = {}
        self.contributions: dict[str, MechanismContribution] = {}
        self.network_effects: list[NetworkEffect] = []
        default_path = (
            Path(__file__).resolve().parents[1] / "mechanisms" / "industry_policy_v1.yaml"
        )
        self.mechanism = yaml.safe_load(
            (mechanism_path or default_path).read_text(encoding="utf-8")
        )

    @staticmethod
    def _initial_states(profiles: dict[str, ProvinceProfile]) -> dict[str, ProvinceState]:
        states: dict[str, ProvinceState] = {}
        for code, profile in profiles.items():
            industry_mean = mean(
                [profile.ai_base, profile.advanced_manufacturing_base, profile.green_energy_base]
            )
            states[code] = ProvinceState(
                province_code=code,
                phase=Phase.T0.value,
                policy_benefit_index=45,
                innovation_index=clamp(25 + 35 * profile.rd_capacity + 20 * industry_mean),
                employment_index=clamp(46 - 8 * profile.employment_pressure),
                fiscal_pressure=clamp(22 + 30 * (1 - profile.fiscal_capacity)),
                policy_accessibility=clamp(38 + 18 * profile.fiscal_capacity),
                talent_attraction=clamp(28 + 58 * profile.talent_attractiveness),
                cooperation_stock=clamp(15 + 30 * profile.cooperation_tendency),
            )
        return states

    def get_province_observation(self, province_code: str) -> tuple[ProvinceProfile, ProvinceState]:
        return self.profiles[province_code], self.states[province_code]

    def submit_province_action(self, action: ProvinceAction) -> None:
        if action.province_code not in self.profiles:
            raise ValueError(f"unknown province {action.province_code}")
        allowed = {edge.target for edge in self.network[action.province_code]}
        if not set(action.target_provinces) <= allowed:
            raise ValueError("action targets provinces outside the configured network")
        self.pending_actions[action.province_code] = action

    @staticmethod
    def _industry_fit(profile: ProvinceProfile, action: ProvinceAction) -> float:
        scores = {
            Industry.AI: profile.ai_base,
            Industry.ADVANCED_MANUFACTURING: profile.advanced_manufacturing_base,
            Industry.GREEN_ENERGY: profile.green_energy_base,
        }
        return mean(scores[industry] for industry in action.priority_industries)

    def _regional_allocation(self, profile: ProvinceProfile) -> float:
        bias = self.policy.regional_bias
        if profile.region_group == RegionGroup.EAST:
            return max(0.65, 1 - max(0, bias) * 0.65 + max(0, -bias) * 0.20)
        capacity_equalizer = max(0, bias) * (1 - profile.fiscal_capacity) * 0.80
        return max(
            0.7,
            1 + max(0, bias) * 0.90 + capacity_equalizer - max(0, -bias) * 0.15,
        )

    def apply_direct_effects(self, phase: Phase) -> None:
        cfg = self.mechanism["direct_effects"]
        updates = self.mechanism["state_updates"]
        for code in sorted(self.pending_actions):
            action = self.pending_actions[code]
            profile = self.profiles[code]
            state = self.states[code]
            fit = self._industry_fit(profile, action)
            policy_match = cfg["policy_match_scale"] * fit * action.implementation_intensity
            central_support = (
                cfg["central_support_scale"]
                * (self.policy.central_budget_index / 100)
                * self._regional_allocation(profile)
                * (0.65 + 0.35 * action.requested_central_support)
            )
            local_investment = (
                cfg["local_investment_scale"]
                * action.local_budget_ratio
                * profile.fiscal_capacity
                * action.implementation_intensity
            )
            fiscal_cost = (
                cfg["fiscal_execution_cost_scale"]
                * action.local_budget_ratio
                * self.policy.local_match_requirement
                * (0.5 + (1 - profile.fiscal_capacity))
            )
            contribution = MechanismContribution(
                province_code=code,
                phase=phase,
                policy_match=round(policy_match, 4),
                central_support=round(central_support, 4),
                local_investment=round(local_investment, 4),
                fiscal_execution_cost=round(fiscal_cost, 4),
            )
            self.contributions[code] = contribution
            state.policy_benefit_index = clamp(state.policy_benefit_index + contribution.net_effect)
            state.innovation_index = clamp(
                state.innovation_index
                + policy_match * updates["innovation_from_match"]
                + local_investment * 0.25
            )
            state.employment_index = clamp(
                state.employment_index
                + action.implementation_intensity
                * profile.employment_pressure
                * updates["employment_from_execution"]
            )
            state.fiscal_pressure = clamp(
                state.fiscal_pressure + fiscal_cost * updates["fiscal_pressure_from_cost"]
            )
            state.policy_accessibility = clamp(
                state.policy_accessibility + central_support * updates["accessibility_from_support"]
            )
            talent_direction = {
                TalentStrategy.EXPAND: 1.0,
                TalentStrategy.RETAIN: 0.65,
                TalentStrategy.RESKILL: 0.55,
                TalentStrategy.STABLE: 0.20,
            }[action.talent_strategy]
            state.talent_attraction = clamp(
                state.talent_attraction
                + talent_direction * updates["talent_from_strategy"]
                + policy_match * 0.12
            )
            state.cooperation_stock = clamp(
                state.cooperation_stock
                + (
                    updates["cooperation_stock_from_action"]
                    if action.interaction_strategy == InteractionStrategy.COOPERATE
                    else 0
                )
            )
            state.last_action_id = action.action_id
            state.phase = phase.value

    def _edge_weight(self, source: str, target: str) -> float:
        return next(
            (edge.weight for edge in self.network.get(source, []) if edge.target == target),
            0,
        )

    def apply_network_effects(self, phase: Phase) -> None:
        cfg = self.mechanism["network_effects"]
        updates = self.mechanism["state_updates"]
        benefit_snapshot = {code: state.policy_benefit_index for code, state in self.states.items()}
        incoming_competition: dict[str, float] = {code: 0 for code in self.states}
        incoming_cooperation: dict[str, float] = {code: 0 for code in self.states}
        for source, action in self.pending_actions.items():
            for target in action.target_provinces:
                weight = self._edge_weight(source, target)
                if action.interaction_strategy == InteractionStrategy.COMPETE:
                    incoming_competition[target] += (
                        weight
                        * action.implementation_intensity
                        * self.profiles[source].talent_attractiveness
                    )
                    self.network_effects.append(
                        NetworkEffect(
                            source_province=source,
                            target_province=target,
                            effect_type="competition",
                            magnitude=round(incoming_competition[target], 4),
                        )
                    )
                elif action.interaction_strategy == InteractionStrategy.COOPERATE:
                    target_action = self.pending_actions.get(target)
                    mutual_factor = (
                        1.25
                        if target_action
                        and target_action.interaction_strategy == InteractionStrategy.COOPERATE
                        else 0.75
                    )
                    gain = (
                        weight
                        * mutual_factor
                        * self.policy.cooperation_incentive
                        * self.profiles[source].cooperation_tendency
                    )
                    incoming_cooperation[source] += gain
                    incoming_cooperation[target] += gain * 0.8
                    self.network_effects.append(
                        NetworkEffect(
                            source_province=source,
                            target_province=target,
                            effect_type="cooperation",
                            magnitude=round(gain, 4),
                        )
                    )

        for code, state in self.states.items():
            related = self.network.get(code, [])
            geographic = mean(
                [edge.weight * max(0, benefit_snapshot[edge.target] - 45) / 10 for edge in related]
                or [0]
            )
            cooperation = incoming_cooperation[code] * cfg["cooperation_scale"]
            competition = incoming_competition[code] * cfg["competition_scale"]
            spillover = geographic * cfg["geographic_spillover_scale"]
            coordination_cost = cooperation * cfg["coordination_cost_scale"]
            contribution = self.contributions.get(
                code, MechanismContribution(province_code=code, phase=phase)
            )
            contribution.cooperation_spillover = round(cooperation, 4)
            contribution.geographic_spillover = round(spillover, 4)
            contribution.competition_crowding_out = round(competition, 4)
            contribution.fiscal_execution_cost = round(
                contribution.fiscal_execution_cost + coordination_cost,
                4,
            )
            self.contributions[code] = contribution
            state.policy_benefit_index = clamp(
                state.policy_benefit_index
                + cooperation
                + spillover
                - competition
                - coordination_cost
            )
            state.innovation_index = clamp(
                state.innovation_index
                + cooperation * updates["innovation_from_cooperation"]
                + spillover * 0.18
                - competition * 0.20
            )
            state.talent_attraction = clamp(
                state.talent_attraction - competition * 0.42 + cooperation * 0.20
            )
            state.cooperation_stock = clamp(state.cooperation_stock + cooperation * 0.50)
            state.fiscal_pressure = clamp(
                state.fiscal_pressure + coordination_cost * updates["fiscal_pressure_from_cost"]
            )
            state.phase = phase.value

    def process_actions(
        self, actions: dict[str, ProvinceAction], phase: Phase
    ) -> tuple[dict[str, ProvinceState], dict[str, MechanismContribution]]:
        self.pending_actions = {}
        self.contributions = {}
        self.network_effects = []
        for action in actions.values():
            self.submit_province_action(action)
        self.apply_direct_effects(phase)
        self.apply_network_effects(phase)
        return deepcopy(self.states), deepcopy(self.contributions)

    def calculate_national_metrics(self) -> NationalMetrics:
        states = list(self.states.values())
        if not states:
            return NationalMetrics()
        benefits = [state.policy_benefit_index for state in states]
        accessibility = [state.policy_accessibility for state in states]
        innovation = [state.innovation_index for state in states]
        employment = [state.employment_index for state in states]
        fiscal = [state.fiscal_pressure for state in states]
        cooperation = [state.cooperation_stock for state in states]
        regional_benefit_means = [
            mean(
                self.states[code].policy_benefit_index
                for code, profile in self.profiles.items()
                if profile.region_group == region
            )
            for region in RegionGroup
            if any(profile.region_group == region for profile in self.profiles.values())
        ]
        positive_benefits = [max(0.01, value - 40) for value in benefits]
        total = sum(positive_benefits)
        hhi = sum((value / total) ** 2 for value in positive_benefits)
        normalized_hhi = ((hhi - 1 / len(states)) / (1 - 1 / len(states))) * 100
        return NationalMetrics(
            overall_policy_benefit=clamp(mean(benefits)),
            policy_accessibility=clamp(mean(accessibility)),
            innovation_vitality=clamp(mean(innovation)),
            employment_support=clamp(mean(employment)),
            regional_gap=clamp(pstdev(regional_benefit_means) * 4),
            fiscal_pressure=clamp(mean(fiscal)),
            cooperation_density=clamp(mean(cooperation)),
            industry_concentration=clamp(normalized_hhi),
        )

    def get_mechanism_contributions(self, province_code: str) -> MechanismContribution:
        return self.contributions[province_code]

    def apply_approved_intervention(self, intervention: CentralIntervention) -> PolicySchema:
        update: dict[str, float] = {}
        for field, change in intervention.parameter_changes.items():
            current = getattr(self.policy, field)
            if abs(current - change.from_value) > 1e-6:
                raise ValueError(f"intervention baseline mismatch for {field}")
            update[field] = change.to_value
        self.policy = self.policy.model_copy(update=update)
        return self.policy.model_copy(deep=True)

    def snapshot(self) -> str:
        payload = {
            "policy": self.policy.model_dump(mode="json"),
            "states": {code: state.model_dump(mode="json") for code, state in self.states.items()},
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def restore(
        cls,
        snapshot: str,
        *,
        profiles: dict[str, ProvinceProfile],
        network: dict[str, list[NetworkEdge]],
    ) -> "ChinaPolicyEnv":
        payload = json.loads(snapshot)
        return cls(
            profiles=profiles,
            network=network,
            policy=PolicySchema.model_validate(payload["policy"]),
            states={
                code: ProvinceState.model_validate(state)
                for code, state in payload["states"].items()
            },
        )
