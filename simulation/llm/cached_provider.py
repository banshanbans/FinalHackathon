import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
from simulation.llm.trace import set_cache_trace, set_provider_fallback
from simulation.models.action import ProvinceAction
from simulation.models.central import (
    CentralInterventionProposal,
    CentralPolicyDirective,
    CentralReview,
)
from simulation.models.common import Phase
from simulation.models.enterprise import (
    EnterpriseAction,
    EnterpriseActionBatch,
    EnterpriseAggregate,
    EnterpriseGroupProfile,
    EnterpriseGroupState,
)
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
    ProvinceState,
)
from simulation.models.world import ComparisonResult, NationalMetrics, WorldState

ModelT = TypeVar("ModelT", bound=BaseModel)


class CachedLLMProvider:
    """Version-complete replay cache with explicit deterministic miss fallback."""

    def __init__(self, cache_dir: Path, fallback: LLMProvider, *, write_through: bool = True):
        self.cache_dir = cache_dir
        self.fallback = fallback
        self.write_through = write_through
        self.accessed_cache_files: set[Path] = set()
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
        cache_key = self._key(kind, payload)
        path = self.cache_dir / f"{cache_key}.json"
        self.accessed_cache_files.add(path)
        if path.exists():
            set_cache_trace(cache_key_hash=cache_key.rsplit("_", 1)[-1], hit=True)
            cached = model_type.model_validate_json(path.read_text(encoding="utf-8"))
            if isinstance(cached, (ProvinceAction, ProvinceFeedback)):
                cached = cached.model_copy(update={"run_mode": "cache", "fallback_used": False})
            if isinstance(cached, EnterpriseActionBatch):
                cached = cached.model_copy(
                    update={
                        "run_mode": "cache",
                        "fallback_used": False,
                        "fallback_reason": None,
                    }
                )
            return cached
        set_cache_trace(cache_key_hash=cache_key.rsplit("_", 1)[-1], hit=False)
        set_provider_fallback("cache_miss")
        result = await generate()
        if isinstance(result, (ProvinceAction, ProvinceFeedback)):
            result = result.model_copy(update={"run_mode": "fallback", "fallback_used": True})
        if isinstance(result, EnterpriseActionBatch):
            result = result.model_copy(
                update={
                    "run_mode": "fallback",
                    "fallback_used": True,
                    "fallback_reason": "cache_miss",
                }
            )
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
            kind="central_directive_v2",
            payload=payload,
            model_type=CentralPolicyDirective,
            generate=lambda: self.fallback.generate_central_directive(config, default_policy),
        )

    async def generate_province_action(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
        previous_action: ProvinceAction | None,
        feedback: ProvinceFeedback | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceAction:
        payload = {
            "profile": profile.model_dump(mode="json"),
            "persona": persona.model_dump(mode="json"),
            "state": state.model_dump(mode="json"),
            "policy": policy.model_dump(mode="json"),
            "phase": phase.value,
            "related": [edge.model_dump(mode="json") for edge in related],
            "neighbor_actions": {
                code: action.model_dump(mode="json", exclude={"run_mode", "fallback_used"})
                for code, action in sorted(neighbor_actions.items())
            },
            "previous_action": (
                previous_action.model_dump(mode="json", exclude={"run_mode", "fallback_used"})
                if previous_action
                else None
            ),
            "feedback": (
                feedback.model_dump(mode="json", exclude={"run_mode", "fallback_used"})
                if feedback
                else None
            ),
            "seed": seed,
            "prompt_version": prompt_version,
            "model_version": model_version,
        }
        return await self._get_or_create(
            kind="province_action_v3",
            payload=payload,
            model_type=ProvinceAction,
            generate=lambda: self.fallback.generate_province_action(
                profile=profile,
                persona=persona,
                state=state,
                policy=policy,
                phase=phase,
                related=related,
                neighbor_actions=neighbor_actions,
                previous_action=previous_action,
                feedback=feedback,
                seed=seed,
                prompt_version=prompt_version,
                model_version=model_version,
            ),
        )

    async def generate_enterprise_actions_batch(
        self,
        *,
        province_profile: ProvinceProfile,
        province_action: ProvinceAction,
        enterprise_profiles: list[EnterpriseGroupProfile],
        enterprise_states: dict[str, EnterpriseGroupState],
        policy: PolicySchema,
        phase: Phase,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> EnterpriseActionBatch:
        payload = {
            "province_profile": province_profile.model_dump(mode="json"),
            "province_action": province_action.model_dump(
                mode="json", exclude={"run_mode", "fallback_used"}
            ),
            "enterprise_profiles": [item.model_dump(mode="json") for item in enterprise_profiles],
            "enterprise_states": {
                key: enterprise_states[key].model_dump(mode="json")
                for key in sorted(enterprise_states)
            },
            "policy": policy.model_dump(mode="json"),
            "phase": phase.value,
            "seed": seed,
            "prompt_version": prompt_version,
            "model_version": model_version,
        }
        return await self._get_or_create(
            kind="enterprise_batch_v2",
            payload=payload,
            model_type=EnterpriseActionBatch,
            generate=lambda: self.fallback.generate_enterprise_actions_batch(
                province_profile=province_profile,
                province_action=province_action,
                enterprise_profiles=enterprise_profiles,
                enterprise_states=enterprise_states,
                policy=policy,
                phase=phase,
                seed=seed,
                prompt_version=prompt_version,
                model_version=model_version,
            ),
        )

    async def generate_province_feedback(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        aggregate: EnterpriseAggregate,
        enterprise_actions: list[EnterpriseAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback:
        payload = {
            "profile": profile.model_dump(mode="json"),
            "persona": persona.model_dump(mode="json"),
            "state": state.model_dump(mode="json"),
            "current_action": current_action.model_dump(
                mode="json", exclude={"run_mode", "fallback_used"}
            ),
            "aggregate": aggregate.model_dump(mode="json"),
            "enterprise_actions": [item.model_dump(mode="json") for item in enterprise_actions],
            "policy": policy.model_dump(mode="json"),
            "seed": seed,
            "prompt_version": prompt_version,
            "model_version": model_version,
        }
        return await self._get_or_create(
            kind="province_feedback_v3",
            payload=payload,
            model_type=ProvinceFeedback,
            generate=lambda: self.fallback.generate_province_feedback(
                profile=profile,
                persona=persona,
                state=state,
                current_action=current_action,
                aggregate=aggregate,
                enterprise_actions=enterprise_actions,
                policy=policy,
                seed=seed,
                prompt_version=prompt_version,
                model_version=model_version,
            ),
        )

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        feedback: dict[str, ProvinceFeedback],
        enterprise_actions: dict[str, EnterpriseAction],
    ) -> list[CentralInterventionProposal]:
        payload = {
            "policy": policy.model_dump(mode="json"),
            "metrics": metrics.model_dump(mode="json"),
            "states": {code: state.model_dump(mode="json") for code, state in states.items()},
            "feedback": {
                code: item.model_dump(mode="json", exclude={"run_mode", "fallback_used"})
                for code, item in feedback.items()
            },
            "enterprise_actions": {
                key: item.model_dump(mode="json") for key, item in enterprise_actions.items()
            },
        }
        key = self._key("central_intervention_v2", payload)
        path = self.cache_dir / f"{key}.json"
        self.accessed_cache_files.add(path)
        if path.exists():
            set_cache_trace(cache_key_hash=key.rsplit("_", 1)[-1], hit=True)
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [CentralInterventionProposal.model_validate(item) for item in raw]
        set_cache_trace(cache_key_hash=key.rsplit("_", 1)[-1], hit=False)
        set_provider_fallback("cache_miss")
        result = await self.fallback.generate_intervention_proposals(
            policy=policy,
            metrics=metrics,
            states=states,
            feedback=feedback,
            enterprise_actions=enterprise_actions,
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

    async def generate_central_review(self, result: ComparisonResult | WorldState) -> CentralReview:
        if isinstance(result, ComparisonResult):
            volatile_fields = {
                "central_review",
                "experiment_id",
                "checkpoint_id",
                "control_branch_id",
                "treatment_branch_id",
            }
        else:
            volatile_fields = {
                "central_review",
                "experiment_id",
                "branch_id",
                "parent_checkpoint_id",
            }
        semantic_payload = result.model_dump(mode="json", exclude=volatile_fields)
        identity_payload = result.model_dump(mode="json", exclude={"central_review"})
        review = await self._get_or_create(
            kind="central_review_v2",
            payload=semantic_payload,
            model_type=CentralReview,
            generate=lambda: self.fallback.generate_central_review(result),
        )
        identity_raw = json.dumps(
            identity_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        review_id = f"review_{hashlib.sha256(identity_raw.encode()).hexdigest()[:12]}"
        return review.model_copy(update={"review_id": review_id})
