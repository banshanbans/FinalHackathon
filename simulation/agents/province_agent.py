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
