from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import ApprovalStatus
from simulation.models.policy import PolicySchema


class CentralPolicyDirective(DomainModel):
    schema_version: str = "central-directive-v1"
    directive_id: str
    policy: PolicySchema
    policy_objectives: list[str] = Field(min_length=1, max_length=5)
    hard_constraints: list[str] = Field(default_factory=list, max_length=8)
    public_summary: str = Field(min_length=1, max_length=240)
    requires_human_approval: Literal[True] = True
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT


class ParameterChange(DomainModel):
    from_value: float
    to_value: float


class CentralInterventionProposal(DomainModel):
    schema_version: str = "central-intervention-proposal-v1"
    proposal_id: str
    parameter_changes: dict[str, ParameterChange] = Field(min_length=1, max_length=5)
    target_metrics: list[str] = Field(min_length=1, max_length=5)
    expected_directions: dict[str, Literal["increase", "decrease", "may_increase", "may_decrease"]]
    tradeoffs: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)
    public_summary: str = Field(min_length=1, max_length=300)
    requires_human_approval: Literal[True] = True
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT


class CentralIntervention(DomainModel):
    schema_version: str = "central-intervention-v1"
    intervention_id: str
    proposal_id: str
    parameter_changes: dict[str, ParameterChange] = Field(min_length=1, max_length=5)
    approved_at: datetime
    approved_by: Literal["user"] = "user"
    approval_status: Literal[ApprovalStatus.APPROVED] = ApprovalStatus.APPROVED

    @model_validator(mode="after")
    def only_supported_policy_fields(self) -> "CentralIntervention":
        supported = {
            "central_budget_index",
            "local_match_requirement",
            "regional_bias",
            "cooperation_incentive",
        }
        unsupported = set(self.parameter_changes) - supported
        if unsupported:
            raise ValueError(f"unsupported intervention fields: {sorted(unsupported)}")
        return self


class ReviewFinding(DomainModel):
    title: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=320)
    evidence_refs: list[str] = Field(min_length=1, max_length=10)
    tradeoff: str | None = Field(default=None, max_length=200)


class CentralReview(DomainModel):
    schema_version: str = "central-review-v1"
    review_id: str
    findings: list[ReviewFinding] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(min_length=1, max_length=5)
    public_summary: str = Field(min_length=1, max_length=500)
