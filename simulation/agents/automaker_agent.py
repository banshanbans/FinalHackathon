from simulation.llm.base import LLMProvider
from simulation.models.automaker import AutomakerAction, AutomakerProfile, AutomakerState
from simulation.models.common import Phase
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceAction, ProvinceProfile


class AutomakerAgent:
    def __init__(self, profile: AutomakerProfile, provider: LLMProvider):
        self.profile = profile
        self.provider = provider

    async def decide(
        self,
        *,
        state: AutomakerState,
        province_profiles: dict[str, ProvinceProfile],
        province_actions: dict[str, ProvinceAction],
        policy: PolicySchema,
        phase: Phase,
        previous_action: AutomakerAction | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> AutomakerAction:
        action = await self.provider.generate_automaker_action(
            profile=self.profile,
            state=state,
            province_profiles=province_profiles,
            province_actions=province_actions,
            policy=policy,
            phase=phase,
            previous_action=previous_action,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if action.automaker_id != self.profile.automaker_id:
            raise ValueError("provider returned an action for a different automaker")
        return action
