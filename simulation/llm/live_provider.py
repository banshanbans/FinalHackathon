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
from simulation.models.experiment import ExperimentConfig
from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile, ProvinceState
from simulation.models.world import ComparisonResult, NationalMetrics

ModelT = TypeVar("ModelT", bound=BaseModel)


class LiveLLMProvider:
    """OpenAI-compatible structured provider with one repair and deterministic fallback."""

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
        schema = response_type.model_json_schema()
        messages = [
            {
                "role": "system",
                "content": (
                    "你是PolicyScope中的结构化策略Agent。只返回JSON，不生成现实预测，"
                    "不得输出长思维链。输出必须符合给定JSON Schema。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"instruction": instruction, "input": payload, "schema": schema},
                    ensure_ascii=False,
                ),
            },
        ]
        invalid_content = ""
        invalid_error = ""
        for attempt in range(2):
            if attempt == 1:
                messages.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "repair": "上一响应未通过校验，请只返回修复后的JSON。",
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
                content = response.choices[0].message.content or "{}"
                return response_type.model_validate_json(content)
            except (ValidationError, json.JSONDecodeError, ValueError, RuntimeError) as error:
                invalid_content = locals().get("content", "")
                invalid_error = str(error)
            except Exception:
                break
        return await fallback()

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralPolicyDirective:
        return await self._structured(
            model=self.central_model,
            instruction="根据用户目标和限定模板形成待人工审批的中央政策指令。",
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
        state: ProvinceState,
        policy: PolicySchema,
        phase: Phase,
        related: list[NetworkEdge],
        neighbor_actions: dict[str, ProvinceAction],
    ) -> ProvinceAction:
        async def fallback_action() -> ProvinceAction:
            action = await self.fallback.generate_province_action(
                profile=profile,
                state=state,
                policy=policy,
                phase=phase,
                related=related,
                neighbor_actions=neighbor_actions,
            )
            return action.model_copy(update={"run_mode": "fallback", "fallback_used": True})

        action = await self._structured(
            model=self.province_model,
            instruction="依据本省画像、当前状态和相关省公开动作选择结构化执行策略。",
            payload={
                "profile": profile.model_dump(mode="json"),
                "state": state.model_dump(mode="json"),
                "policy": policy.model_dump(mode="json"),
                "phase": phase.value,
                "related": [edge.model_dump(mode="json") for edge in related],
                "neighbor_actions": {
                    code: item.model_dump(mode="json") for code, item in neighbor_actions.items()
                },
            },
            response_type=ProvinceAction,
            fallback=fallback_action,
        )
        allowed_targets = {edge.target for edge in related}
        if (
            action.province_code != profile.province_code
            or not set(action.target_provinces) <= allowed_targets
        ):
            return await fallback_action()
        return action.model_copy(update={"run_mode": "live"})

    async def generate_intervention_proposals(
        self,
        *,
        policy: PolicySchema,
        metrics: NationalMetrics,
        states: dict[str, ProvinceState],
        actions: dict[str, ProvinceAction],
    ) -> list[CentralInterventionProposal]:
        class ProposalList(BaseModel):
            proposals: list[CentralInterventionProposal]

        async def fallback_proposals() -> ProposalList:
            proposals = await self.fallback.generate_intervention_proposals(
                policy=policy,
                metrics=metrics,
                states=states,
                actions=actions,
            )
            return ProposalList(proposals=proposals)

        result = await self._structured(
            model=self.central_model,
            instruction="基于结构化全国态势提出最多3个待用户审批的政策参数干预选项。",
            payload={
                "policy": policy.model_dump(mode="json"),
                "metrics": metrics.model_dump(mode="json"),
                "states": {code: state.model_dump(mode="json") for code, state in states.items()},
                "actions": {
                    code: action.model_dump(mode="json") for code, action in actions.items()
                },
            },
            response_type=ProposalList,
            fallback=fallback_proposals,
        )
        return result.proposals[:3]

    async def generate_central_review(self, comparison: ComparisonResult) -> CentralReview:
        return await self._structured(
            model=self.central_model,
            instruction="只引用对照JSON中的事实，生成不超过5条收益、代价与限制并存的中央复盘。",
            payload=comparison.model_dump(mode="json", exclude={"central_review"}),
            response_type=CentralReview,
            fallback=lambda: self.fallback.generate_central_review(comparison),
        )
