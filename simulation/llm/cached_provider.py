import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
from simulation.models.automaker import AutomakerAction, AutomakerProfile, AutomakerState
from simulation.models.central import (
    CentralInterventionProposal,
    CentralReview,
    CentralSubsidyDirective,
)
from simulation.models.common import Phase, RunMode
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import (
    ProvinceAction,
    ProvinceDecisionPersona,
    ProvinceFeedback,
    ProvinceProfile,
    ProvinceState,
)
from simulation.models.scenario import EventScenario, ProvinceEventResponse, ProvinceEventSignal
from simulation.models.world import ComparisonResult, NationalMetrics, WorldState

ModelT = TypeVar("ModelT", bound=BaseModel)


class ProposalList(BaseModel):
    proposals: list[CentralInterventionProposal]


class CachedLLMProvider:
    """Version-complete cache. Misses use an explicit deterministic fallback and write through."""

    run_mode = "cache"

    def __init__(self, cache_dir: Path, fallback: LLMProvider, *, write_through: bool = True):
        self.cache_dir = cache_dir
        self.fallback = fallback
        self.write_through = write_through
        self.accessed_cache_files: set[Path] = set()
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _semantic_payload(payload: object) -> object:
        """Remove delivery metadata that cannot affect a strategy decision."""
        if isinstance(payload, BaseModel):
            return CachedLLMProvider._semantic_payload(payload.model_dump(mode="json"))
        if isinstance(payload, dict):
            return {
                str(key): CachedLLMProvider._semantic_payload(value)
                for key, value in payload.items()
                if key
                not in {
                    "run_mode",
                    "fallback_used",
                    "fallback_reason",
                    "approved_at",
                }
            }
        if isinstance(payload, (list, tuple)):
            return [CachedLLMProvider._semantic_payload(item) for item in payload]
        return payload

    @staticmethod
    def _key(kind: str, payload: object) -> str:
        raw = json.dumps(
            CachedLLMProvider._semantic_payload(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return f"{kind}_{hashlib.sha256(raw.encode()).hexdigest()}"

    @staticmethod
    def _with_mode(value: ModelT, *, hit: bool) -> ModelT:
        if isinstance(
            value,
            (
                ProvinceAction,
                ProvinceFeedback,
                AutomakerAction,
                ProvinceEventSignal,
                ProvinceEventResponse,
            ),
        ):
            if hit:
                return value.model_copy(
                    update={
                        "run_mode": RunMode.CACHE,
                        "fallback_used": False,
                        "fallback_reason": None,
                    }
                )
            return value.model_copy(
                update={
                    "run_mode": RunMode.FALLBACK,
                    "fallback_used": True,
                    "fallback_reason": "cache_miss",
                }
            )
        return value

    async def _get_or_create(
        self,
        *,
        kind: str,
        payload: object,
        model_type: type[ModelT],
        generate: Callable[[], Awaitable[ModelT]],
    ) -> ModelT:
        path = self.cache_dir / f"{self._key(kind, payload)}.json"
        self.accessed_cache_files.add(path)
        if path.exists():
            self.cache_hits += 1
            return self._with_mode(
                model_type.model_validate_json(path.read_text(encoding="utf-8")), hit=True
            )
        self.cache_misses += 1
        result = self._with_mode(await generate(), hit=False)
        if self.write_through:
            path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralSubsidyDirective:
        payload = {
            "config": config.model_dump(mode="json"),
            "policy": default_policy.model_dump(mode="json"),
        }
        return await self._get_or_create(
            kind="central_directive_v3",
            payload=payload,
            model_type=CentralSubsidyDirective,
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
            "related": [x.model_dump(mode="json") for x in related],
            "neighbors": {
                k: v.model_dump(mode="json") for k, v in sorted(neighbor_actions.items())
            },
            "previous": previous_action.model_dump(mode="json") if previous_action else None,
            "feedback": feedback.model_dump(mode="json") if feedback else None,
            "seed": seed,
            "prompt_version": prompt_version,
            "model_version": model_version,
        }
        return await self._get_or_create(
            kind="province_action_v4",
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

    async def generate_automaker_action(
        self,
        *,
        profile: AutomakerProfile,
        state: AutomakerState,
        province_profiles: dict[str, ProvinceProfile],
        province_actions: dict[str, ProvinceAction],
        policy: PolicySchema,
        phase: Phase,
        previous_action: AutomakerAction | None,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> AutomakerAction:
        payload = {
            "profile": profile.model_dump(mode="json"),
            "state": state.model_dump(mode="json"),
            "province_profiles": {
                k: v.model_dump(mode="json") for k, v in sorted(province_profiles.items())
            },
            "province_actions": {
                k: v.model_dump(mode="json") for k, v in sorted(province_actions.items())
            },
            "policy": policy.model_dump(mode="json"),
            "phase": phase.value,
            "previous": previous_action.model_dump(mode="json") if previous_action else None,
            "seed": seed,
            "prompt_version": prompt_version,
            "model_version": model_version,
        }
        return await self._get_or_create(
            kind="automaker_action_v1",
            payload=payload,
            model_type=AutomakerAction,
            generate=lambda: self.fallback.generate_automaker_action(
                profile=profile,
                state=state,
                province_profiles=province_profiles,
                province_actions=province_actions,
                policy=policy,
                phase=phase,
                previous_action=previous_action,
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
        automaker_actions: dict[str, AutomakerAction],
        policy: PolicySchema,
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceFeedback:
        payload = {
            "profile": profile.model_dump(mode="json"),
            "persona": persona.model_dump(mode="json"),
            "state": state.model_dump(mode="json"),
            "action": current_action.model_dump(mode="json"),
            "automaker_actions": {
                k: v.model_dump(mode="json") for k, v in sorted(automaker_actions.items())
            },
            "policy": policy.model_dump(mode="json"),
            "seed": seed,
            "prompt_version": prompt_version,
            "model_version": model_version,
        }
        return await self._get_or_create(
            kind="province_feedback_v4",
            payload=payload,
            model_type=ProvinceFeedback,
            generate=lambda: self.fallback.generate_province_feedback(
                profile=profile,
                persona=persona,
                state=state,
                current_action=current_action,
                automaker_actions=automaker_actions,
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
        automaker_actions: dict[str, AutomakerAction],
    ) -> list[CentralInterventionProposal]:
        payload = {
            "policy": policy.model_dump(mode="json"),
            "metrics": metrics.model_dump(mode="json"),
            "states": {k: v.model_dump(mode="json") for k, v in sorted(states.items())},
            "feedback": {k: v.model_dump(mode="json") for k, v in sorted(feedback.items())},
            "automakers": {
                k: v.model_dump(mode="json") for k, v in sorted(automaker_actions.items())
            },
        }
        wrapper = await self._get_or_create(
            kind="central_proposals_v3",
            payload=payload,
            model_type=ProposalList,
            generate=lambda: self._proposal_wrapper(
                policy, metrics, states, feedback, automaker_actions
            ),
        )
        return wrapper.proposals

    async def generate_province_event_signal(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        exposure: float,
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventSignal:
        arguments = locals().copy()
        arguments.pop("self")
        return await self._get_or_create(
            kind="province_event_signal_v1",
            payload=arguments,
            model_type=ProvinceEventSignal,
            generate=lambda: self.fallback.generate_province_event_signal(**arguments),
        )

    async def generate_province_event_response(
        self,
        *,
        profile: ProvinceProfile,
        persona: ProvinceDecisionPersona,
        state: ProvinceState,
        current_action: ProvinceAction,
        scenario: EventScenario,
        own_signal: ProvinceEventSignal,
        peer_signals: dict[str, ProvinceEventSignal],
        related: list[NetworkEdge],
        seed: int,
        prompt_version: str,
        model_version: str,
    ) -> ProvinceEventResponse:
        arguments = locals().copy()
        arguments.pop("self")
        return await self._get_or_create(
            kind="province_event_response_v1",
            payload=arguments,
            model_type=ProvinceEventResponse,
            generate=lambda: self.fallback.generate_province_event_response(**arguments),
        )

    async def _proposal_wrapper(
        self, policy, metrics, states, feedback, automaker_actions
    ) -> ProposalList:
        return ProposalList(
            proposals=await self.fallback.generate_intervention_proposals(
                policy=policy,
                metrics=metrics,
                states=states,
                feedback=feedback,
                automaker_actions=automaker_actions,
            )
        )

    async def generate_central_review(self, result: ComparisonResult | WorldState) -> CentralReview:
        if isinstance(result, ComparisonResult):
            payload = {
                "schema_version": result.schema_version,
                "policy_diff": [item.model_dump(mode="json") for item in result.policy_diff],
                "delta_gap": result.delta_gap,
                "national_metrics": {
                    key: value.model_dump(mode="json")
                    for key, value in sorted(result.national_metrics.items())
                },
                "mechanism_totals": result.mechanism_totals,
                "top_improved": result.top_improved,
                "top_pressured": result.top_pressured,
            }
        else:
            payload = {
                "schema_version": result.schema_version,
                "review_mode": "single_branch",
                "policy": result.policy.model_dump(mode="json"),
                "national_metrics": result.national_metrics.model_dump(mode="json"),
                "intervention_decision": result.intervention_decision,
            }
        return await self._get_or_create(
            kind="central_review_v3",
            payload=payload,
            model_type=CentralReview,
            generate=lambda: self.fallback.generate_central_review(result),
        )
