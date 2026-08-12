from typing import Literal

from pydantic import Field, model_validator

from simulation.models.base import DomainModel


class MechanismTerm(DomainModel):
    name: str
    input_value: float
    coefficient: float
    contribution: float
    source_ref: str | None = None


class MechanismContribution(DomainModel):
    schema_version: Literal["mechanism-contribution-v4"] = "mechanism-contribution-v4"
    formula_version: str = "nev-policy-env-v1"
    province_code: str | None = Field(default=None, pattern=r"^\d{2}$")
    target_metric: str = Field(min_length=1)
    terms: list[MechanismTerm]
    raw_value: float
    clamp_adjustment: float = 0
    final_value: float = Field(ge=0, le=100)
    conservation_residual: float = Field(default=0, ge=-1e-6, le=1e-6)
    evidence_refs: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def formula_is_reconcilable(self) -> "MechanismContribution":
        if abs(sum(term.contribution for term in self.terms) - self.raw_value) > 1e-6:
            raise ValueError("mechanism terms must sum to the raw value")
        if abs(self.raw_value + self.clamp_adjustment - self.final_value) > 1e-6:
            raise ValueError("raw value plus clamp adjustment must equal final value")
        return self
