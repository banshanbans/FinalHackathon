from simulation.llm.base import LLMProvider
from simulation.models.automaker import AutomakerAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralReview,
    CentralSubsidyDirective,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceFeedback, ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics, WorldState


class StateCouncilAgent:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def draft_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralSubsidyDirective:
        return await self.provider.generate_central_directive(config, default_policy)

    async def analyze_and_propose(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        feedback: dict[str, ProvinceFeedback],
        automaker_actions: dict[str, AutomakerAction],
    ) -> list[CentralInterventionProposal]:
        return await self.provider.generate_intervention_proposals(
            policy=policy,
            metrics=metrics,
            states=states,
            feedback=feedback,
            automaker_actions=automaker_actions,
        )

    async def review(self, result: ComparisonResult | WorldState) -> CentralReview:
        return await self.provider.generate_central_review(result)
