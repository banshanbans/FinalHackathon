from math import isclose

from pydantic import Field, model_validator

from simulation.models.base import DomainModel
from simulation.models.common import Industry


class EvaluationWeights(DomainModel):
    innovation: float = Field(default=0.35, ge=0, le=1)
    employment: float = Field(default=0.25, ge=0, le=1)
    equity: float = Field(default=0.25, ge=0, le=1)
    fiscal_efficiency: float = Field(default=0.15, ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "EvaluationWeights":
        total = self.innovation + self.employment + self.equity + self.fiscal_efficiency
        if not isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"evaluation weights must sum to 1.0, got {total}")
        return self


class PolicySchema(DomainModel):
    schema_version: str = "policy-v1"
    policy_id: str = "strategic_industry_v1"
    domain: str = "strategic_emerging_industry"
    central_budget_index: float = Field(default=70, ge=0, le=100)
    local_match_requirement: float = Field(default=0.5, ge=0, le=1)
    regional_bias: float = Field(default=0, ge=-1, le=1)
    cooperation_incentive: float = Field(default=0.4, ge=0, le=1)
    evaluation_weights: EvaluationWeights = Field(default_factory=EvaluationWeights)
    priority_industries: list[Industry] = Field(
        default_factory=lambda: [
            Industry.AI,
            Industry.ADVANCED_MANUFACTURING,
            Industry.GREEN_ENERGY,
        ],
        min_length=1,
        max_length=3,
    )
    mechanism_version: str = "industry-policy-env-v1"
