import hashlib
from uuid import uuid4

from simulation.models.experiment import Checkpoint
from simulation.models.world import WorldState


class CheckpointService:
    """Creates immutable serialized world-state checkpoints."""

    def create(self, state: WorldState, checkpoint_id: str | None = None) -> Checkpoint:
        world_json = state.model_dump_json()
        state_hash = hashlib.sha256(world_json.encode()).hexdigest()
        return Checkpoint(
            checkpoint_id=checkpoint_id or f"cp_{uuid4().hex[:14]}",
            experiment_id=state.experiment_id,
            branch_id=state.branch_id,
            phase=state.phase,
            state_hash=state_hash,
            world_state_json=world_json,
        )

    @staticmethod
    def restore(checkpoint: Checkpoint) -> WorldState:
        actual = hashlib.sha256(checkpoint.world_state_json.encode()).hexdigest()
        if actual != checkpoint.state_hash:
            raise ValueError("checkpoint integrity verification failed")
        return WorldState.model_validate_json(checkpoint.world_state_json)
