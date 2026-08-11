import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
)
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics

ModelT = TypeVar("ModelT", bound=BaseModel)


class CachedLLMProvider:
    """Replayable provider with explicit deterministic fallback on cache miss."""

    def __init__(self, cache_dir: Path, fallback: LLMProvider, *, write_through: bool = True):
        self.cache_dir = cache_dir
        self.fallback = fallback
        self.write_through = write_through
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(kind: str, payload: object) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return f"{kind}_{hashlib.sha256(raw.encode()).hexdigest()}"

    async def _get_or_create(
        self,
        *,
        kind: str,
        payload: object,
        model_type: type[ModelT],
        generate: Callable[[], Awaitable[ModelT]],
    ) -> ModelT:
        path = self.cache_dir / f"{self._key(kind, payload)}.json"
        if path.exists():
            cached = model_type.model_validate_json(path.read_text(encoding="utf-8"))
            if isinstance(cached, ProvinceAction):
                cached = cached.model_copy(update={"run_mode": "cache", "fallback_used": False})
            return cached
        result = await generate()
        if isinstance(result, ProvinceAction):
            result = result.model_copy(update={"run_mode": "fallback", "fallback_used": True})
        if self.write_through:
            path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralPolicyDirective:
        payload = {
            "config": config.model_dump(mode="json"),
            "policy": default_policy.model_dump(mode="json"),
        }
        return await self._get_or_create(
            kind="central_directive",
            payload=payload,
            model_type=CentralPolicyDirective,
            generate=lambda: self.fallback.generate_central_directive(config, default_policy),
        )

    async def generate_province_action(
        self,
        *,
        profile: ProvinceProfile,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
    ) -> ProvinceAction:
        payload = {
            "profile": profile.model_dump(mode="json"),
            "state": state.model_dump(mode="json"),
            "policy": policy.model_dump(mode="json"),
            "phase": phase.value,
            "related": [edge.model_dump(mode="json") for edge in related],
            "neighbor_actions": {
                code: action.model_dump(
                    mode="json",
                    exclude={"run_mode", "fallback_used"},
                )
                for code, action in sorted(neighbor_actions.items())
            },
        }
        return await self._get_or_create(
            kind="province_action",
            payload=payload,
            model_type=ProvinceAction,
            generate=lambda: self.fallback.generate_province_action(
                profile=profile,
                state=state,
                policy=policy,
                phase=phase,
                related=related,
                neighbor_actions=neighbor_actions,
            ),
        )

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        actions: dict[str, ProvinceAction],
    ) -> list[CentralInterventionProposal]:
        payload = {
            "policy": policy.model_dump(mode="json"),
            "metrics": metrics.model_dump(mode="json"),
            "states": {code: state.model_dump(mode="json") for code, state in states.items()},
            "actions": {code: action.model_dump(mode="json") for code, action in actions.items()},
        }
        key = self._key("central_intervention", payload)
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [CentralInterventionProposal.model_validate(item) for item in raw]
        result = await self.fallback.generate_intervention_proposals(
            policy=policy, metrics=metrics, states=states, actions=actions
        )
        if self.write_through:
            path.write_text(
                json.dumps(
                    [item.model_dump(mode="json") for item in result],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return result

    async def generate_central_review(self, comparison: ComparisonResult) -> CentralReview:
        return await self._get_or_create(
            kind="central_review",
            payload=comparison.model_dump(mode="json", exclude={"central_review"}),
            model_type=CentralReview,
            generate=lambda: self.fallback.generate_central_review(comparison),
        )
