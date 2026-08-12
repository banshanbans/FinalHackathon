from datetime import UTC, datetime
from typing import Literal

from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.central import CentralIntervention, CentralSubsidyDirective
from simulation.models.common import BranchKind, ExperimentStatus, Phase, RunMode


class ExperimentConfig(DomainModel):
    schema_version: Literal["experiment-config-v3"] = "experiment-config-v3"
    objective: str = Field(min_length=3, max_length=500)
    scenario_id: str = "nev_subsidy_default"
    seed: int = 20260812
    run_mode: RunMode = RunMode.FAKE
    data_version: str = "nev-baseline-2025-v1"
    mechanism_version: str = "nev-policy-env-v1"
    prompt_version: str = "nev-policy-agents-v1"
    model_version: str = "fake-v1"


class ExperimentRecord(DomainModel):
    schema_version: Literal["experiment-record-v3"] = "experiment-record-v3"
    experiment_id: str
    config: ExperimentConfig
    directive: CentralSubsidyDirective
    status: ExperimentStatus = ExperimentStatus.AWAITING_APPROVAL
    current_phase: Phase = Phase.SETUP
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Checkpoint(DomainModel):
    schema_version: Literal["checkpoint-v3"] = "checkpoint-v3"
    checkpoint_id: str
    experiment_id: str
    branch_id: str
    phase: Literal[Phase.YEAR1_REVIEW] = Phase.YEAR1_REVIEW
    state_hash: str
    world_state_json: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Branch(DomainModel):
    schema_version: Literal["branch-v3"] = "branch-v3"
    branch_id: str
    experiment_id: str
    kind: BranchKind
    parent_checkpoint_id: str
    intervention: CentralIntervention | None = None
    current_phase: Phase = Phase.YEAR1_REVIEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
