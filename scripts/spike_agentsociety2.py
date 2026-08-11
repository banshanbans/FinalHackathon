#!/usr/bin/env python3
"""Bounded AgentSociety2 capability probe; never used by the MVP runtime."""

import asyncio
import json
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from agentsociety2 import EnvBase, ReplayWriter, tool
from agentsociety2.storage.workspace_state import atomic_write_text


class PolicyScopeSpikeEnv(EnvBase):
    """Minimal shared policy environment for the optional-runtime spike."""

    def __init__(self):
        super().__init__()
        self.actions: dict[int, float] = {}

    @tool(readonly=False)
    def submit_policy_action(self, agent_id: int, intensity: float) -> dict[str, float]:
        self.actions[agent_id] = intensity
        return {"aggregate": round(sum(self.actions.values()), 4)}

    @tool(readonly=True, kind="observe")
    def observe_policy(self, agent_id: int) -> dict[str, float | int]:
        return {
            "agent_id": agent_id,
            "own_intensity": self.actions.get(agent_id, 0),
            "aggregate": round(sum(self.actions.values()), 4),
        }

    async def step(self, tick: int, t) -> None:
        self.t = t

    async def to_workspace(self, workspace_path: Path | None = None) -> None:
        await super().to_workspace(workspace_path)
        assert self._workspace_root is not None
        atomic_write_text(
            self._workspace_root / "state.json",
            json.dumps({"actions": self.actions}, sort_keys=True),
        )

    async def restore(self, workspace_path: Path) -> bool:
        self._bind_workspace(workspace_path)
        state_path = self._workspace_root / "state.json"
        if not state_path.exists():
            return False
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.actions = {int(key): float(value) for key, value in payload["actions"].items()}
        return True


async def main() -> None:
    started_at = perf_counter()
    with TemporaryDirectory(prefix="policyscope-agentsociety-") as raw_dir:
        root = Path(raw_dir)
        environment = PolicyScopeSpikeEnv()
        first = environment.submit_policy_action(agent_id=1, intensity=0.4)
        second = environment.submit_policy_action(agent_id=2, intensity=0.6)
        observation = environment.observe_policy(agent_id=1)
        shared_environment = (
            first["aggregate"] == 0.4
            and second["aggregate"] == 1.0
            and observation["aggregate"] == 1.0
        )

        checkpoint_dir = root / "checkpoint"
        await environment.to_workspace(checkpoint_dir)
        restored = await PolicyScopeSpikeEnv.from_workspace(checkpoint_dir)
        checkpoint_restore = restored.actions == environment.actions

        replay_dir = root / "replay"
        writer = ReplayWriter(replay_dir)
        await writer.init()
        await writer.write("policy_events", {"step": 1, "agent_id": 1, "intensity": 0.4})
        await writer.write("policy_events", {"step": 1, "agent_id": 2, "intensity": 0.6})
        await writer.close()
        replay_rows = sum(
            len(path.read_text(encoding="utf-8").splitlines())
            for path in replay_dir.glob("policy_events.*.jsonl")
        )

        result = {
            "distribution_version": version("agentsociety2"),
            "import_version": __import__("agentsociety2").__version__,
            "mcp_constraint": ">=1.29,<2",
            "llm_key_required_at_import": True,
            "install": True,
            "shared_environment": shared_environment,
            "checkpoint_restore": checkpoint_restore,
            "replay_append": replay_rows == 2,
            "replay_rows": replay_rows,
            "decision": "CONDITIONAL_GO_OPTIONAL_ONLY",
            "elapsed_seconds": round(perf_counter() - started_at, 4),
        }
        if not all(
            result[key]
            for key in ("install", "shared_environment", "checkpoint_restore", "replay_append")
        ):
            raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
