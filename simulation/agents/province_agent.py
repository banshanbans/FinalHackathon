from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
from simulation.models.automaker import AutomakerAction
from simulation.models.common import Phase
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    ProvinceAction,
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
    ProvinceState,
)
from simulation.models.scenario import EventScenario, ProvinceEventResponse, ProvinceEventSignal


class ProvinceAgent:
    def __init__(self, profile: ProvinceProfile, provider: LLMProvider):
        self.profile = profile
        self.provider = provider

    async def decide(
        self,
        *,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
        previous_action: ProvinceAction | None,
        feedback: ProvinceFeedback | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceAction:
        action = await self.provider.generate_province_action(
            profile=self.profile,
            persona=persona,
            state=state,
            policy=policy,
            phase=phase,
            related=related,
            neighbor_actions=neighbor_actions,
            previous_action=previous_action,
            feedback=feedback,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if action.province_code != self.profile.province_code:
            raise ValueError("provider returned an action for a different province")
        return action

    async def feedback(
        self,
        *,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        automaker_actions: dict[str, AutomakerAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback:
        result = await self.provider.generate_province_feedback(
            profile=self.profile,
            persona=persona,
            state=state,
            current_action=current_action,
            automaker_actions=automaker_actions,
            policy=policy,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if result.province_code != self.profile.province_code:
            raise ValueError("provider returned feedback for a different province")
        return result

    async def publish_event_signal(
        self,
        *,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        exposure: float,
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventSignal:
        result = await self.provider.generate_province_event_signal(
            profile=self.profile,
            persona=persona,
            state=state,
            current_action=current_action,
            scenario=scenario,
            exposure=exposure,
            related=related,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if result.province_code != self.profile.province_code:
            raise ValueError("provider returned an event signal for a different province")
        allowed = {edge.target for edge in related}
        if not set(result.proposed_peer_codes) <= allowed:
            raise ValueError("event signal references an unauthorized peer")
        return result

    async def respond_to_event(
        self,
        *,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        own_signal: ProvinceEventSignal,
        peer_signals: dict[str, ProvinceEventSignal],
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventResponse:
        result = await self.provider.generate_province_event_response(
            profile=self.profile,
            persona=persona,
            state=state,
            current_action=current_action,
            scenario=scenario,
            own_signal=own_signal,
            peer_signals=peer_signals,
            related=related,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if result.province_code != self.profile.province_code:
            raise ValueError("provider returned an event response for a different province")
        allowed = {edge.target for edge in related}
        if not set(result.observed_peer_codes) <= allowed:
            raise ValueError("event response observes an unauthorized peer")
        final_mix = current_action.subsidy_mix
        delta = result.subsidy_mix_delta
        values = (
            final_mix.consumer + delta.consumer,
            final_mix.fixed_cost + delta.fixed_cost,
            final_mix.variable_cost + delta.variable_cost,
        )
        if any(value < -1e-9 or value > 1 + 1e-9 for value in values):
            raise ValueError("event response would produce an invalid subsidy mix")
        return result
