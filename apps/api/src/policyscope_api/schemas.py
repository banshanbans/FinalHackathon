from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import Phase, RunMode
from simulation.models.policy import PolicySchema


class CreateExperimentRequest(DomainModel):
    objective: str = Field(
        default="比较西部、中部、东部中央承担比例变化对新能源汽车需求、地方财政空间和产业布局的模拟影响。",
        min_length=3,
        max_length=500,
    )
    scenario_id: str = "nev_subsidy_default"
    seed: int = 20260812
    run_mode: RunMode | None = None


class ApproveDirectiveRequest(DomainModel):
    policy: PolicySchema


class RunExperimentRequest(DomainModel):
    until_phase: Phase
    branch_id: str = "control"


class ApproveInterventionRequest(DomainModel):
    policy: PolicySchema


class RejectInterventionRequest(DomainModel):
    reason: str = Field(default="用户保留原始方案", min_length=1, max_length=200)


class CreateBranchRequest(DomainModel):
    intervention_id: str


class RunBranchRequest(DomainModel):
    until_phase: Phase = Phase.Y2_Q4
