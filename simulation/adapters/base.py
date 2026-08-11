from typing import Protocol

from simulation.models.central import CentralIntervention
from simulation.models.common import Phase
from simulation.models.experiment import Branch, Checkpoint, ExperimentConfig
from simulation.models.world import WorldState


class SimulationAdapter(Protocol):
    async def initialize(self, config: ExperimentConfig) -> WorldState: ...

    async def run_phase(
        self, experiment_id: str, phase: Phase, branch_id: str = "control"
    ) -> WorldState: ...

    async def create_checkpoint(self, experiment_id: str, phase: Phase) -> Checkpoint: ...

    async def create_branch(
        self, checkpoint_id: str, intervention: CentralIntervention
    ) -> Branch: ...

    async def get_state(self, experiment_id: str, branch_id: str = "control") -> WorldState: ...

    async def close(self) -> None: ...
