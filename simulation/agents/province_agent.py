from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
from simulation.models.action import ProvinceAction
from simulation.models.common import Phase
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState


class ProvinceAgent:
    """A regional response proxy sharing one implementation across all provinces."""

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
    ) -> ProvinceAction:
        action = await self.provider.generate_province_action(
            profile=self.profile,
            state=state,
            policy=policy,
            phase=phase,
            related=related,
            neighbor_actions=neighbor_actions,
        )
        allowed_targets = {edge.target for edge in related}
        if action.province_code != self.profile.province_code:
            raise ValueError("provider returned an action for a different province")
        if not set(action.target_provinces) <= allowed_targets:
            raise ValueError("provider returned targets outside the province network")
        return action
