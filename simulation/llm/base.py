from typing import Protocol

from simulation.data import NetworkEdge
from simulation.models.automaker import AutomakerAction, AutomakerProfile, AutomakerState
from simulation.models.central import (
    CentralInterventionProposal,
    CentralReview,
    CentralSubsidyDirective,
)
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    ProvinceAction,
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
    ProvinceState,
)
from simulation.models.scenario import EventScenario, ProvinceEventResponse, ProvinceEventSignal
from simulation.models.world import ComparisonResult, NationalMetrics, WorldState


class LLMProvider(Protocol):
    run_mode: str

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralSubsidyDirective: ...

    async def generate_province_action(
        self,
        *,
        profile: ProvinceProfile,
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
    ) -> ProvinceAction: ...

    async def generate_automaker_action(
        self,
        *,
        profile: AutomakerProfile,
        state: AutomakerState,
        province_profiles: dict[str, ProvinceProfile],
        province_actions: dict[str, ProvinceAction],
        policy: PolicySchema,
        phase: Phase,
        previous_action: AutomakerAction | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> AutomakerAction: ...

    async def generate_province_feedback(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        automaker_actions: dict[str, AutomakerAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback: ...

    async def generate_province_event_signal(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        exposure: float,
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventSignal: ...

    async def generate_province_event_response(
        self,
        *,
        profile: ProvinceProfile,
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
    ) -> ProvinceEventResponse: ...

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        feedback: dict[str, ProvinceFeedback],
        automaker_actions: dict[str, AutomakerAction],
    ) -> list[CentralInterventionProposal]: ...

    async def generate_central_review(
        self, result: ComparisonResult | WorldState
    ) -> CentralReview: ...
