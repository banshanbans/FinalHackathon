import json
from pathlib import Path

from simulation.models.event import EventEnvelope
from simulation.models.world import WorldState


class ReplayService:
    """Append-only JSONL replay plus latest state snapshots."""

    def __init__(self, runtime_dir: Path):
        self.runtime_dir = runtime_dir

    def _experiment_dir(self, experiment_id: str) -> Path:
        path = self.runtime_dir / "experiments" / experiment_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, event: EventEnvelope) -> None:
        path = self._experiment_dir(event.experiment_id) / "replay.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def write_state(self, state: WorldState) -> None:
        path = self._experiment_dir(state.experiment_id) / f"state_{state.branch_id}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def read_events(self, experiment_id: str) -> list[EventEnvelope]:
        path = self._experiment_dir(experiment_id) / "replay.jsonl"
        if not path.exists():
            return []
        events: list[EventEnvelope] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(EventEnvelope.model_validate_json(line))
        return events

    def read_raw(self, experiment_id: str) -> list[dict[str, object]]:
        return [json.loads(item.model_dump_json()) for item in self.read_events(experiment_id)]
