from simulation.llm.base import LLMProvider
from simulation.models.action import ProvinceAction
from simulation.models.common import Phase
from simulation.models.enterprise import (
    EnterpriseActionBatch,
    EnterpriseGroupProfile,
    EnterpriseGroupState,
)
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile


class EnterpriseBatchAgent:
    """One batched call per province that must return all six enterprise groups."""

    def __init__(
        self,
        province_profile: ProvinceProfile,
        enterprise_profiles: list[EnterpriseGroupProfile],
        provider: LLMProvider,
    ):
        self.province_profile = province_profile
        self.enterprise_profiles = enterprise_profiles
        self.provider = provider

    async def decide(
        self,
        *,
        province_action: ProvinceAction,
        enterprise_states: dict[str, EnterpriseGroupState],
        policy: PolicySchema,
        phase: Phase,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> EnterpriseActionBatch:
        batch = await self.provider.generate_enterprise_actions_batch(
            province_profile=self.province_profile,
            province_action=province_action,
            enterprise_profiles=self.enterprise_profiles,
            enterprise_states=enterprise_states,
            policy=policy,
            phase=phase,
            seed=seed,
            prompt_version=prompt_version,
            model_version=model_version,
        )
        if batch.province_code != self.province_profile.province_code:
            raise ValueError("provider returned enterprise actions for a different province")
        return batch
