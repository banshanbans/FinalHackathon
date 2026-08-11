from datetime import datetime
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import ApprovalStatus, ReviewMode
from simulation.models.policy import PolicySchema

ALLOWED_POLICY_PATHS = {
    "support_intensity",
    "local_match_requirement",
    "sme_preference",
    "regional_support_bias",
    "instrument_mix.direct_subsidy",
    "instrument_mix.interest_subsidy",
    "instrument_mix.financing_guarantee",
    "technology_mix.digital",
    "technology_mix.green",
    "technology_mix.general",
}


class CentralPolicyDirective(DomainModel):
    schema_version: str = "central-directive-v2"
    directive_id: str
    policy: PolicySchema
    policy_objectives: list[str] = Field(min_length=1, max_length=5)
    hard_constraints: list[str] = Field(default_factory=list, max_length=8)
    public_summary: str = Field(min_length=1, max_length=240)
    requires_human_approval: Literal[True] = True
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT


class PolicyFieldChange(DomainModel):
    path: str
    from_value: JsonValue
    to_value: JsonValue

    @model_validator(mode="after")
    def path_is_supported(self) -> "PolicyFieldChange":
        if self.path not in ALLOWED_POLICY_PATHS:
            raise ValueError(f"unsupported policy field path: {self.path}")
        return self


class CentralInterventionProposal(DomainModel):
    schema_version: str = "central-intervention-proposal-v2"
    proposal_id: str
    proposed_policy: PolicySchema
    parameter_changes: list[PolicyFieldChange] = Field(min_length=1, max_length=10)
    target_metrics: list[str] = Field(min_length=1, max_length=6)
    expected_directions: dict[str, Literal["increase", "decrease", "may_increase", "may_decrease"]]
    tradeoffs: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)
    public_summary: str = Field(min_length=1, max_length=300)
    requires_human_approval: Literal[True] = True
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT


class CentralIntervention(DomainModel):
    schema_version: str = "central-intervention-v2"
    intervention_id: str
    proposal_id: str
    approved_policy: PolicySchema
    parameter_changes: list[PolicyFieldChange] = Field(min_length=1, max_length=10)
    approved_at: datetime
    approved_by: Literal["user"] = "user"
    approval_status: Literal[ApprovalStatus.APPROVED] = ApprovalStatus.APPROVED


class ReviewFinding(DomainModel):
    title: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=320)
    evidence_refs: list[str] = Field(min_length=1, max_length=10)
    tradeoff: str | None = Field(default=None, max_length=200)


class CentralReview(DomainModel):
    schema_version: str = "central-review-v2"
    review_id: str
    review_mode: ReviewMode
    findings: list[ReviewFinding] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(min_length=1, max_length=5)
    public_summary: str = Field(min_length=1, max_length=500)
