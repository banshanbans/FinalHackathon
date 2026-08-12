from datetime import datetime
from typing import Literal

from pydantic import Field, JsonValue, field_validator, model_validator

from simulation.domain_constants import POLICY_SHARE_PATHS
from simulation.models.base import DomainModel
from simulation.models.common import ApprovalStatus, ExpectedDirection, ReviewMode
from simulation.models.policy import PolicySchema


class CentralSubsidyDirective(DomainModel):
    schema_version: Literal["central-subsidy-directive-v1"] = "central-subsidy-directive-v1"
    directive_id: str = "directive_nev_v3"
    policy: PolicySchema
    policy_objectives: list[str] = Field(min_length=1, max_length=5)
    hard_constraints: list[str] = Field(default_factory=list, max_length=8)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)
    public_summary: str = Field(min_length=1, max_length=240)
    requires_human_approval: Literal[True] = True
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT


class PolicyFieldChange(DomainModel):
    path: str
    from_value: JsonValue
    to_value: JsonValue

    @field_validator("path")
    @classmethod
    def path_is_an_active_v3_policy_lever(cls, value: str) -> str:
        if value not in POLICY_SHARE_PATHS:
            raise ValueError(f"unsupported V3 policy field path: {value}")
        return value

    @model_validator(mode="after")
    def values_are_valid_shares(self) -> "PolicyFieldChange":
        if isinstance(self.from_value, bool) or isinstance(self.to_value, bool):
            raise ValueError("policy share changes must use numeric values")
        if not isinstance(self.from_value, (int, float)) or not isinstance(
            self.to_value, (int, float)
        ):
            raise ValueError("policy share changes must use numeric values")
        if not 0 <= float(self.from_value) <= 1 or not 0 <= float(self.to_value) <= 1:
            raise ValueError("policy share changes must stay within 0–1")
        return self


class CentralInterventionProposal(DomainModel):
    schema_version: Literal["central-intervention-proposal-v3"] = "central-intervention-proposal-v3"
    proposal_id: str = "proposal_nev_share_adjustment_v3"
    proposed_policy: PolicySchema
    parameter_changes: list[PolicyFieldChange] = Field(min_length=1, max_length=3)
    expected_directions: dict[str, ExpectedDirection] = Field(min_length=1, max_length=6)
    tradeoffs: list[str] = Field(default_factory=list, max_length=5)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)
    public_summary: str = Field(min_length=1, max_length=300)
    requires_human_approval: Literal[True] = True
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT

    @field_validator("parameter_changes")
    @classmethod
    def changed_paths_are_unique(cls, value: list[PolicyFieldChange]) -> list[PolicyFieldChange]:
        paths = [item.path for item in value]
        if len(paths) != len(set(paths)):
            raise ValueError("intervention proposal cannot repeat a policy field")
        return value


class CentralIntervention(DomainModel):
    schema_version: Literal["central-intervention-v3"] = "central-intervention-v3"
    intervention_id: str
    approved_policy: PolicySchema
    approved_changes: list[PolicyFieldChange] = Field(min_length=1, max_length=3)
    approved_at: datetime
    approved_by: Literal["user"] = "user"
    approval_status: Literal[ApprovalStatus.APPROVED] = ApprovalStatus.APPROVED


class InterventionRejection(DomainModel):
    schema_version: Literal["intervention-rejection-v1"] = "intervention-rejection-v1"
    rejected_at: datetime
    rejected_by: Literal["user"] = "user"
    reason: str = Field(min_length=1, max_length=200)
    approval_status: Literal[ApprovalStatus.REJECTED] = ApprovalStatus.REJECTED


class ReviewFinding(DomainModel):
    title: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=320)
    evidence_refs: list[str] = Field(min_length=1, max_length=10)
    tradeoff: str | None = Field(default=None, max_length=200)


class CentralReview(DomainModel):
    schema_version: Literal["central-review-v3"] = "central-review-v3"
    review_id: str = "central_review_v3"
    review_mode: ReviewMode
    findings: list[ReviewFinding] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(min_length=1, max_length=5)
    public_summary: str = Field(min_length=1, max_length=500)


CentralPolicyDirective = CentralSubsidyDirective
