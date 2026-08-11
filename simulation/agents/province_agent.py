from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
from simulation.models.action import ProvinceAction
from simulation.models.common import Phase
from simulation.models.enterprise import EnterpriseAction, EnterpriseAggregate
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceFeedback, ProvinceProfile, ProvinceState


class ProvinceAgent:
    """Province policy response and T3 feedback proxy."""

    def __init__(self, profile: ProvinceProfile, provider: LLMProvider):
        self.profile = profile
        self.provider = provider

    async def decide(
        self,
        *,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceAction:
        action = await self.provider.generate_province_action(
            profile=self.profile,
            state=state,
            policy=policy,
            phase=phase,
            related=related,
            neighbor_actions=neighbor_actions,
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
        state: ProvinceState,
        aggregate: EnterpriseAggregate,
        enterprise_actions: list[EnterpriseAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback:
        result = await self.provider.generate_province_feedback(
            profile=self.profile,
            state=state,
            aggregate=aggregate,
            enterprise_actions=enterprise_actions,
            policy=policy,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if result.province_code != self.profile.province_code:
            raise ValueError("provider returned feedback for a different province")
        return result
