from typing import Protocol

from simulation.data import NetworkEdge
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
)
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics


class LLMProvider(Protocol):
    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralPolicyDirective: ...

    async def generate_province_action(
        self,
        *,
        profile: ProvinceProfile,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
    ) -> ProvinceAction: ...

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        actions: dict[str, ProvinceAction],
    ) -> list[CentralInterventionProposal]: ...

    async def generate_central_review(self, comparison: ComparisonResult) -> CentralReview: ...
