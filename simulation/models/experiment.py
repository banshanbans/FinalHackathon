from datetime import UTC, datetime

from pydantic import Field

from simulation.models.base import DomainModel
from simulation.models.central import CentralIntervention, CentralPolicyDirective
from simulation.models.common import BranchKind, ExperimentStatus, Phase, RunMode


class ExperimentConfig(DomainModel):
    schema_version: str = "experiment-config-v2"
    objective: str = Field(min_length=3, max_length=500)
    scenario_id: str = "equipment_renewal_default"
    seed: int = 20260812
    run_mode: RunMode = RunMode.FAKE
    data_version: str = "equipment-renewal-profiles-v3"
    mechanism_version: str = "equipment-renewal-env-v2"
    prompt_version: str = "equipment-renewal-agents-v3"
    model_version: str = "fake-v3"


class ExperimentRecord(DomainModel):
    schema_version: str = "experiment-record-v2"
    experiment_id: str
    config: ExperimentConfig
    directive: CentralPolicyDirective
    status: ExperimentStatus = ExperimentStatus.AWAITING_APPROVAL
    current_phase: Phase = Phase.T0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Checkpoint(DomainModel):
    schema_version: str = "checkpoint-v2"
    checkpoint_id: str
    experiment_id: str
    branch_id: str
    phase: Phase
    state_hash: str
    world_state_json: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Branch(DomainModel):
    schema_version: str = "branch-v2"
    branch_id: str
    experiment_id: str
    kind: BranchKind
    parent_checkpoint_id: str
    intervention: CentralIntervention | None = None
    current_phase: Phase = Phase.T3
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
