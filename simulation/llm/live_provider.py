import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

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


class LiveLLMProvider:
    """OpenAI-compatible structured provider with one repair and explicit fallback."""

    run_mode = "live"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        central_model: str,
        province_model: str,
        fallback: LLMProvider,
        enterprise_model: str | None = None,
        automaker_model: str | None = None,
        timeout_seconds: float = 12,
        max_concurrency: int = 16,
        max_tokens: int = 4096,
        thinking_enabled: bool = False,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
        self.central_model = central_model
        self.province_model = province_model
        self.automaker_model = automaker_model or enterprise_model or province_model
        self.fallback = fallback
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_tokens = max_tokens
        self.thinking_enabled = thinking_enabled

    @staticmethod
    def _mode(value: ModelT, mode: RunMode, reason: str | None = None) -> ModelT:
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
            return value.model_copy(
                update={
                    "run_mode": mode,
                    "fallback_used": mode is RunMode.FALLBACK,
                    "fallback_reason": reason if mode is RunMode.FALLBACK else None,
                }
            )
        return value

    async def _structured(
        self,
        *,
        model: str,
        instruction: str,
        payload: object,
        response_type: type[ModelT],
        fallback: Callable[[], Awaitable[ModelT]],
    ) -> ModelT:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 PolicyScope 的结构化策略 Agent。只返回符合 Schema 的 JSON；"
                    "不生成现实销量、利润、投资、财政金额或政策预测；不输出长思维链。"
                    "省级产业偏好只能依据输入中的原始事实、派生特征、历史政策与 Evidence；"
                    "不得使用省份刻板印象，也不得把结构能力直接等同于现实政府立场。"
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
                    default=str,
                ),
            },
        ]
        last_error = ""
        for attempt in range(2):
            if attempt:
                messages.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "repair": "修复上一响应，仅返回完整 JSON。",
                                "validation_error": last_error[:1200],
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
                        max_tokens=self.max_tokens,
                        extra_body={
                            "thinking": {"type": "enabled" if self.thinking_enabled else "disabled"}
                        },
                    )
                content = response.choices[0].message.content or "{}"
                return self._mode(response_type.model_validate_json(content), RunMode.LIVE)
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc)
            except Exception as exc:
                last_error = type(exc).__name__
                break
        return self._mode(await fallback(), RunMode.FALLBACK, last_error or "provider_failure")

    async def generate_central_directive(
        self, config: ExperimentConfig, default_policy: PolicySchema
    ) -> CentralSubsidyDirective:
        return await self._structured(
            model=self.central_model,
            instruction="生成待人工审批的新能源汽车中央共担比例指令。",
            payload={"config": config, "default_policy": default_policy},
            response_type=CentralSubsidyDirective,
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
        arguments = locals().copy()
        arguments.pop("self")
        return await self._structured(
            model=self.province_model,
            instruction=(
                "依据已提供事实、历史政策证据和当期约束，自主选择地方总体支持强度"
                "与消费/固定/可变成本补贴份额；三项份额必须合计 1。"
            ),
            payload=arguments,
            response_type=ProvinceAction,
            fallback=lambda: self.fallback.generate_province_action(**arguments),
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
        arguments = locals().copy()
        arguments.pop("self")
        return await self._structured(
            model=self.automaker_model,
            instruction=(
                "为全国性车企分配 31 省销售/渠道投入，并选择最多 3 个新建、扩产或延迟目标。"
            ),
            payload=arguments,
            response_type=AutomakerAction,
            fallback=lambda: self.fallback.generate_automaker_action(**arguments),
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
        arguments = locals().copy()
        arguments.pop("self")
        return await self._structured(
            model=self.province_model,
            instruction="复盘首年财政、需求和车企响应，只输出调整意向，不修改状态。",
            payload=arguments,
            response_type=ProvinceFeedback,
            fallback=lambda: self.fallback.generate_province_feedback(**arguments),
        )

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
        return await self._structured(
            model=self.province_model,
            instruction=(
                "依据可引用事实、派生特征与历史政策证据评估冻结事件暴露并发布"
                "结构化省际政策信号；不得使用刻板标签或生成结果指标。"
            ),
            payload=arguments,
            response_type=ProvinceEventSignal,
            fallback=lambda: self.fallback.generate_province_event_signal(**arguments),
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
        return await self._structured(
            model=self.province_model,
            instruction=(
                "只读取授权 Peer 的冻结首轮信号，选择跟随、差异化、观望或协作响应；"
                "三类补贴调整量合计必须为零，不得生成结果指标。"
            ),
            payload=arguments,
            response_type=ProvinceEventResponse,
            fallback=lambda: self.fallback.generate_province_event_response(**arguments),
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
        arguments = locals().copy()
        arguments.pop("self")

        async def fallback_wrapper() -> ProposalList:
            return ProposalList(
                proposals=await self.fallback.generate_intervention_proposals(**arguments)
            )

        result = await self._structured(
            model=self.central_model,
            instruction="基于首年证据建议一次三档中央承担比例调整。",
            payload=arguments,
            response_type=ProposalList,
            fallback=fallback_wrapper,
        )
        return result.proposals

    async def generate_central_review(self, result: ComparisonResult | WorldState) -> CentralReview:
        return await self._structured(
            model=self.central_model,
            instruction="形成受证据约束的模拟机制复盘，不宣称现实最优。",
            payload=result,
            response_type=CentralReview,
            fallback=lambda: self.fallback.generate_central_review(result),
        )
