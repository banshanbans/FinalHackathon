from simulation.llm.base import LLMProvider
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics


class StateCouncilAgent:
    """Structured central policy agent; never applies policy without user approval."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def draft_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralPolicyDirective:
        return await self.provider.generate_central_directive(config, default_policy)

    async def analyze_and_propose(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        actions: dict[str, ProvinceAction],
    ) -> list[CentralInterventionProposal]:
        return await self.provider.generate_intervention_proposals(
            policy=policy,
            metrics=metrics,
            states=states,
            actions=actions,
        )

    async def review(self, comparison: ComparisonResult) -> CentralReview:
        return await self.provider.generate_central_review(comparison)
