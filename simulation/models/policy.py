from typing import Literal

from pydantic import Field, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import PolicyInputMode, PolicyStatus, PrimaryGoal

WEST_REFERENCE_SHARE = 0.95
CENTRAL_REFERENCE_SHARE = 0.90
EAST_REFERENCE_SHARE = 0.85


class RegionalShareAdjustments(DomainModel):
    west: float = Field(default=0, ge=-1, le=1)
    central: float = Field(default=0, ge=-1, le=1)
    east: float = Field(default=0, ge=-1, le=1)


class PolicySchema(DomainModel):
    schema_version: Literal["policy-v3"] = "policy-v3"
    policy_id: str = "nev_trade_in_cost_sharing_v3"
    domain: Literal["nev_subsidy_and_industrial_layout"] = "nev_subsidy_and_industrial_layout"
    reference_policy_year: Literal[2025] = 2025
    input_mode: PolicyInputMode = PolicyInputMode.ABSOLUTE
    west_central_share: float = Field(default=WEST_REFERENCE_SHARE, ge=0, le=1)
    central_central_share: float = Field(default=CENTRAL_REFERENCE_SHARE, ge=0, le=1)
    east_central_share: float = Field(default=EAST_REFERENCE_SHARE, ge=0, le=1)
    share_adjustments: RegionalShareAdjustments = Field(default_factory=RegionalShareAdjustments)
    consumer_subsidy_standard_version: str = "nev-trade-in-standard-2025-reference-v1"
    eligibility_rule_version: str = "nev-trade-in-eligibility-2025-reference-v1"
    primary_goal: PrimaryGoal = PrimaryGoal.REDUCE_REGIONAL_GAP
    status: PolicyStatus = PolicyStatus.DRAFT
    mechanism_version: str = "nev-policy-env-v1"

    @model_validator(mode="after")
    def validate_input_mode(self) -> "PolicySchema":
        adjustments = self.share_adjustments
        if self.input_mode is PolicyInputMode.ABSOLUTE:
            if any(
                abs(value) > 1e-9
                for value in (adjustments.west, adjustments.central, adjustments.east)
            ):
                raise ValueError("absolute input mode requires zero share adjustments")
        else:
            expected = (
                WEST_REFERENCE_SHARE + adjustments.west,
                CENTRAL_REFERENCE_SHARE + adjustments.central,
                EAST_REFERENCE_SHARE + adjustments.east,
            )
            actual = (self.west_central_share, self.central_central_share, self.east_central_share)
            if any(abs(left - right) > 1e-9 for left, right in zip(expected, actual, strict=True)):
                raise ValueError("delta input mode shares must equal reference plus adjustments")
        return self

    @property
    def ordering_warnings(self) -> list[str]:
        if self.west_central_share >= self.central_central_share >= self.east_central_share:
            return []
        return ["当前比例偏离西部≥中部≥东部的参考排序；允许继续用于机制实验。"]

    def central_share_for_region(self, region: object) -> float:
        value = getattr(region, "value", region)
        shares = {
            "west": self.west_central_share,
            "central": self.central_central_share,
            "east": self.east_central_share,
        }
        try:
            return shares[str(value)]
        except KeyError as exc:
            raise ValueError(f"unknown policy region: {value}") from exc
