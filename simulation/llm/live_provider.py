import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from simulation.data import NetworkEdge
from simulation.llm.base import LLMProvider
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


class ProposalList(BaseModel):
    proposals: list[CentralInterventionProposal]


class LiveLLMProvider:
    """OpenAI-compatible V2.1 provider with one repair and deterministic fallback."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        central_model: str,
        province_model: str,
        fallback: LLMProvider,
        timeout_seconds: float = 12,
        max_concurrency: int = 16,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
        self.central_model = central_model
        self.province_model = province_model
        self.fallback = fallback
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _structured(
        self,
        *,
        model: str,
        instruction: str,
        payload: object,
        response_type: type[ModelT],
        fallback: Callable[[], Awaitable[ModelT]],
    ) -> ModelT:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "你是PolicyScope中的结构化策略Agent。只返回JSON；不生成现实金额、GDP、"
                    "就业或生产率预测；不输出长思维链。严格遵守输入中的JSON Schema。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": instruction,
                        "input": payload,
                        "schema": response_type.model_json_schema(),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        invalid_content = ""
        invalid_error = ""
        for attempt in range(2):
            if attempt:
                messages.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "repair": "上一响应未通过校验，仅返回修复后的完整JSON。",
                                "validation_error": invalid_error,
                                "invalid_response": invalid_content[:2000],
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
            try:
                async with self.semaphore:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.1,
                    )
                invalid_content = response.choices[0].message.content or "{}"
                return response_type.model_validate_json(invalid_content)
            except (ValidationError, json.JSONDecodeError, ValueError, RuntimeError) as error:
                invalid_error = str(error)
            except Exception:
                break
        return await fallback()

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralPolicyDirective:
        return await self._structured(
            model=self.central_model,
            instruction="将用户目标整理为待人工审批的制造业设备更新政策指令。",
            payload={
                "config": config.model_dump(mode="json"),
                "default_policy": default_policy.model_dump(mode="json"),
            },
            response_type=CentralPolicyDirective,
            fallback=lambda: self.fallback.generate_central_directive(config, default_policy),
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
        async def fallback_action() -> ProvinceAction:
            action = await self.fallback.generate_province_action(
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
            )
            return action.model_copy(update={"run_mode": "fallback", "fallback_used": True})

        result = await self._structured(
            model=self.province_model,
            instruction=(
                "依据本次实验决策画像、上一行动和Top-K关系选择地方目标、工具与省际策略；"
                "目标省份只能来自related；不得输出结果指标。"
            ),
            payload={
                "profile": profile.model_dump(mode="json"),
                "persona": persona.model_dump(mode="json"),
                "state": state.model_dump(mode="json"),
                "policy": policy.model_dump(mode="json"),
                "phase": phase.value,
                "related": [item.model_dump(mode="json") for item in related],
                "neighbor_actions": {
                    code: item.model_dump(mode="json") for code, item in neighbor_actions.items()
                },
                "previous_action": (
                    previous_action.model_dump(mode="json") if previous_action else None
                ),
                "feedback": feedback.model_dump(mode="json") if feedback else None,
                "seed": seed,
                "prompt_version": prompt_version,
                "model_version": model_version,
            },
            response_type=ProvinceAction,
            fallback=fallback_action,
        )
        if result.province_code != profile.province_code:
            return await fallback_action()
        return result.model_copy(update={"run_mode": "live"})

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
        async def fallback_batch() -> EnterpriseActionBatch:
            batch = await self.fallback.generate_enterprise_actions_batch(
                province_profile=province_profile,
                province_action=province_action,
                enterprise_profiles=enterprise_profiles,
                enterprise_states=enterprise_states,
                policy=policy,
                phase=phase,
                seed=seed,
                prompt_version=prompt_version,
                model_version=model_version,
            )
            return batch.model_copy(
                update={
                    "run_mode": "fallback",
                    "fallback_used": True,
                    "fallback_reason": "schema_or_provider_failure_after_repair",
                }
            )

        result = await self._structured(
            model=self.province_model,
            instruction=(
                "一次返回本省六类企业群体的独立行动。必须恰好六类；不得输出金额或最终指标。"
            ),
            payload={
                "province_profile": province_profile.model_dump(mode="json"),
                "province_action": province_action.model_dump(mode="json"),
                "enterprise_profiles": [
                    item.model_dump(mode="json") for item in enterprise_profiles
                ],
                "enterprise_states": {
                    key: item.model_dump(mode="json") for key, item in enterprise_states.items()
                },
                "policy": policy.model_dump(mode="json"),
                "phase": phase.value,
                "seed": seed,
                "prompt_version": prompt_version,
                "model_version": model_version,
            },
            response_type=EnterpriseActionBatch,
            fallback=fallback_batch,
        )
        if result.province_code != province_profile.province_code:
            return await fallback_batch()
        return result.model_copy(update={"run_mode": "live"})

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
        async def fallback_feedback() -> ProvinceFeedback:
            item = await self.fallback.generate_province_feedback(
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
            )
            return item.model_copy(update={"run_mode": "fallback", "fallback_used": True})

        result = await self._structured(
            model=self.province_model,
            instruction=(
                "基于当前地方行动、环境证据和六类企业行动生成结构化复盘与调整意向；"
                "调整意向不得直接修改政策或结果。"
            ),
            payload={
                "profile": profile.model_dump(mode="json"),
                "persona": persona.model_dump(mode="json"),
                "state": state.model_dump(mode="json"),
                "current_action": current_action.model_dump(mode="json"),
                "aggregate": aggregate.model_dump(mode="json"),
                "enterprise_actions": [item.model_dump(mode="json") for item in enterprise_actions],
                "policy": policy.model_dump(mode="json"),
                "seed": seed,
                "prompt_version": prompt_version,
                "model_version": model_version,
            },
            response_type=ProvinceFeedback,
            fallback=fallback_feedback,
        )
        if result.province_code != profile.province_code:
            return await fallback_feedback()
        return result.model_copy(update={"run_mode": "live"})

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        feedback: dict[str, ProvinceFeedback],
        enterprise_actions: dict[str, EnterpriseAction],
    ) -> list[CentralInterventionProposal]:
        async def fallback_proposals() -> ProposalList:
            proposals = await self.fallback.generate_intervention_proposals(
                policy=policy,
                metrics=metrics,
                states=states,
                feedback=feedback,
                enterprise_actions=enterprise_actions,
            )
            return ProposalList(proposals=proposals)

        result = await self._structured(
            model=self.central_model,
            instruction="基于T2证据提出最多3个待用户审批的完整政策参数方案。",
            payload={
                "policy": policy.model_dump(mode="json"),
                "metrics": metrics.model_dump(mode="json"),
                "states": {code: item.model_dump(mode="json") for code, item in states.items()},
                "feedback": {code: item.model_dump(mode="json") for code, item in feedback.items()},
                "enterprise_actions": {
                    key: item.model_dump(mode="json") for key, item in enterprise_actions.items()
                },
            },
            response_type=ProposalList,
            fallback=fallback_proposals,
        )
        return result.proposals[:3]

    async def generate_central_review(self, result: ComparisonResult | WorldState) -> CentralReview:
        return await self._structured(
            model=self.central_model,
            instruction="只引用输入JSON中的事实生成中央复盘，明确收益、代价与限制。",
            payload=result.model_dump(mode="json", exclude={"central_review"}),
            response_type=CentralReview,
            fallback=lambda: self.fallback.generate_central_review(result),
        )
