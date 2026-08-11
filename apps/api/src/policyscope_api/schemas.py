from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import Phase, RunMode
from simulation.models.policy import PolicySchema


class CreateExperimentRequest(DomainModel):
    objective: str = Field(
        default=(
            "在有限财政支持下推动制造业设备升级，提高中小企业参与度，"
            "并兼顾绿色转型、就业稳定和区域可达性。"
        ),
        min_length=3,
        max_length=500,
    )
    scenario_id: str = "equipment_renewal_default"
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
    until_phase: Phase = Phase.T5
