from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import Phase, RunMode
from simulation.models.policy import PolicySchema


class CreateExperimentRequest(DomainModel):
    objective: str = Field(
        default="促进战略性新兴产业创新，同时兼顾区域均衡与财政效率。",
        min_length=3,
        max_length=500,
    )
    scenario_id: str = "strategic_industry_default"
    seed: int = 20260812
    run_mode: RunMode | None = None


class ApproveDirectiveRequest(DomainModel):
    policy: PolicySchema | None = None


class RunExperimentRequest(DomainModel):
    until_phase: Phase
    branch_id: str = "control"


class ApproveInterventionRequest(DomainModel):
    overrides: dict[str, float] = Field(default_factory=dict, max_length=5)


class CreateBranchRequest(DomainModel):
    intervention_id: str


class RunBranchRequest(DomainModel):
    until_phase: Phase = Phase.T5
