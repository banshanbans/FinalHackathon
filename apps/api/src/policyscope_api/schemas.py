from typing import Annotated, Literal

from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.common import ComparisonMode, Phase, RunMode
from simulation.models.m34 import MacroTick
from simulation.models.policy import PolicySchema
from simulation.models.scenario import EventScenarioSelection


class CreateExperimentRequest(DomainModel):
    policy_text: str | None = Field(default=None, min_length=3, max_length=4000)
    product_version: Literal["v3_2_m34"] = "v3_2_m34"
    objective: str = Field(
        default="比较西部、中部、东部中央承担比例变化对新能源汽车需求、地方财政空间和产业布局的模拟影响。",
        min_length=3,
        max_length=500,
    )
    scenario_id: str = "nev_subsidy_default"
    seed: int = 20260812
    run_mode: RunMode | None = None
    comparison_mode: ComparisonMode = ComparisonMode.POLICY_INTERVENTION


class ApproveDirectiveRequest(DomainModel):
    policy: PolicySchema


class RunExperimentRequest(DomainModel):
    until_tick: MacroTick = MacroTick.Q4


class ConfirmBaselineRequest(DomainModel):
    confirm_data_snapshot: bool = True
    expected_data_version: str | None = None
    confirm_proxy_data: bool | None = None


class ApproveInterventionRequest(DomainModel):
    policy: PolicySchema


class RejectInterventionRequest(DomainModel):
    reason: str = Field(default="用户保留原始方案", min_length=1, max_length=200)


class PolicyInterventionBranchRequest(DomainModel):
    kind: Literal["policy_intervention"]
    intervention_id: str


class EventCounterfactualBranchRequest(DomainModel):
    kind: Literal["event_counterfactual"]


CreateBranchRequest = Annotated[
    PolicyInterventionBranchRequest | EventCounterfactualBranchRequest,
    Field(discriminator="kind"),
]


class ApproveEventScenarioRequest(EventScenarioSelection):
    pass


class RunBranchRequest(DomainModel):
    until_phase: Phase = Phase.Y2_Q4
