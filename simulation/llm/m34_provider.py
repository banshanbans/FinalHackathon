from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from simulation.services.replay import canonical_hash

ModelT = TypeVar("ModelT", bound=BaseModel)
LOGGER = logging.getLogger(__name__)
CACHE_CONTRACT_V1 = "m34-authorized-context-v1"
CACHE_CONTRACT_V2 = "m34-live-authorized-context-v2"
CACHE_CONTRACT_V3 = "m34-live-authorized-context-v3"
CACHE_QUALITY_CONTRACT = "m34-decision-quality-v1"


class M34AgentProvider(Protocol):
    run_mode: str

    def model_name_for(self, kind: str) -> str: ...

    async def resolve(
        self,
        *,
        kind: str,
        instruction: str,
        authorized_context: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
        validate: Callable[[ModelT], None] | None = None,
    ) -> ModelT: ...


def _fallback_value(fallback: Callable[[], ModelT], *, reason: str) -> ModelT:
    value = fallback()
    fields = type(value).model_fields
    updates: dict[str, object] = {}
    if "fallback_used" in fields:
        updates["fallback_used"] = True
    if "fallback_reason" in fields:
        updates["fallback_reason"] = reason
    return value.model_copy(update=updates) if updates else value


def _same_identity(value: BaseModel, expected: BaseModel) -> bool:
    fields = ("branch_id", "tick", "wave", "agent_kind", "agent_id")
    return all(
        getattr(value, field) == getattr(expected, field)
        for field in fields
        if field in type(expected).model_fields
    )


class M34FakeAgentProvider:
    run_mode = "fake"

    def model_name_for(self, kind: str) -> str:
        del kind
        return "deterministic-fallback"

    async def resolve(
        self,
        *,
        kind: str,
        instruction: str,
        authorized_context: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
        validate: Callable[[ModelT], None] | None = None,
    ) -> ModelT:
        del kind, instruction, authorized_context, response_type
        value = _fallback_value(fallback, reason="fake_provider_deterministic_fallback")
        if validate is not None:
            validate(value)
        return value


class M34CachedAgentProvider:
    run_mode = "cache"

    def __init__(
        self,
        cache_dir: Path,
        *,
        miss_provider: M34AgentProvider | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.miss_provider = miss_provider

    @property
    def miss_mode(self) -> str:
        return "live" if self.miss_provider is not None else "fallback"

    def model_name_for(self, kind: str) -> str:
        if self.miss_provider is not None:
            return f"cache-first:{self.miss_provider.model_name_for(kind)}"
        return "cached-output"

    async def _miss(
        self,
        *,
        kind: str,
        instruction: str,
        authorized_context: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
        validate: Callable[[ModelT], None] | None,
    ) -> ModelT:
        if self.miss_provider is None:
            value = _fallback_value(fallback, reason="cache_miss_without_live_provider")
            if validate is not None:
                validate(value)
            return value
        return await self.miss_provider.resolve(
            kind=kind,
            instruction=instruction,
            authorized_context=authorized_context,
            response_type=response_type,
            fallback=fallback,
            validate=validate,
        )

    @staticmethod
    def cache_key(
        kind: str,
        authorized_context: object,
        response_type: type[BaseModel],
        *,
        contract: str = CACHE_CONTRACT_V3,
    ) -> str:
        payload = {
            "kind": kind,
            "authorized_context": authorized_context,
            "schema": response_type.model_json_schema(),
            "contract": contract,
        }
        return canonical_hash(payload)

    @staticmethod
    def legacy_authorized_context(authorized_context: object) -> object | None:
        if not isinstance(authorized_context, dict):
            return None
        if authorized_context.get("schema_version") != "m34-live-authorized-context-v2":
            return None
        inbox = authorized_context.get("inbox")
        return inbox if isinstance(inbox, dict) else None

    def _promote_legacy_cache(
        self,
        *,
        kind: str,
        key: str,
        authorized_context: object,
        output: object,
    ) -> None:
        path = self.cache_dir / f"{kind}_{key}.json"
        envelope = {
            "schema_version": "m34-luna-cache-envelope-v2",
            "kind": kind,
            "model": "promoted-validated-v1-cache",
            "input_hash": canonical_hash(authorized_context),
            "output_hash": canonical_hash(output),
            "output": output,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    async def resolve(
        self,
        *,
        kind: str,
        instruction: str,
        authorized_context: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
        validate: Callable[[ModelT], None] | None = None,
    ) -> ModelT:
        key = self.cache_key(kind, authorized_context, response_type)
        candidates = [(key, authorized_context, False)]
        legacy_context = self.legacy_authorized_context(authorized_context)
        if legacy_context is not None:
            candidates.append(
                (
                    self.cache_key(
                        kind,
                        legacy_context,
                        response_type,
                        contract=CACHE_CONTRACT_V1,
                    ),
                    legacy_context,
                    True,
                )
            )
        for candidate_key, candidate_context, legacy in candidates:
            path = self.cache_dir / f"{kind}_{candidate_key}.json"
            if not path.is_file():
                continue
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                output = envelope["output"]
                if envelope.get("input_hash") != canonical_hash(candidate_context):
                    continue
                if envelope.get("output_hash") != canonical_hash(output):
                    continue
                if not legacy and envelope.get("quality_contract") != CACHE_QUALITY_CONTRACT:
                    continue
                value = response_type.model_validate(output)
                expected = fallback()
                if not _same_identity(value, expected) or getattr(value, "fallback_used", False):
                    continue
                if validate is not None:
                    validate(value)
                if legacy:
                    self._promote_legacy_cache(
                        kind=kind,
                        key=key,
                        authorized_context=authorized_context,
                        output=output,
                    )
                return value
            except (KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError):
                continue
        return await self._miss(
            kind=kind,
            instruction=instruction,
            authorized_context=authorized_context,
            response_type=response_type,
            fallback=fallback,
            validate=validate,
        )


class M34LiveAgentProvider:
    run_mode = "live"

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        province_model: str,
        automaker_model: str,
        max_tokens: int,
        cache_dir: Path | None = None,
        semaphore: asyncio.Semaphore | None = None,
        thinking_enabled: bool = False,
    ) -> None:
        self.client = client
        self.province_model = province_model
        self.automaker_model = automaker_model
        self.max_tokens = max_tokens
        self.cache_dir = cache_dir
        self.semaphore = semaphore or asyncio.Semaphore(16)
        self.thinking_enabled = thinking_enabled

    def model_name_for(self, kind: str) -> str:
        return self.automaker_model if kind.startswith("automaker") else self.province_model

    async def resolve(
        self,
        *,
        kind: str,
        instruction: str,
        authorized_context: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
        validate: Callable[[ModelT], None] | None = None,
    ) -> ModelT:
        model = self.model_name_for(kind)
        # The prompt deliberately contains only the frozen authorized inbox and public
        # contract. A deterministic candidate action is never disclosed to Live or Cache.
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "你是 PolicyScope V3.2 M34 的结构化策略主体。只使用授权 Inbox；"
                    "只返回符合 Schema 的 JSON；不得读取其他分支或私有交易；不得输出最终指标、"
                    "现实承诺、精确响应日期或思维链。必须逐字复制授权上下文中的 branch_id、"
                    "tick、wave、agent_kind、agent_id、inbox_id；fallback_used 必须为 false 且"
                    "fallback_reason 必须为 null。输出约束是硬约束；不发消息是合法选择，不得为"
                    "凑互动而创造未授权对象。省级 subsidy_mix 三项之和必须精确为 1，"
                    "overall_support_intensity 不得超过 remaining_policy_budget。车企必须恰好"
                    "覆盖 authorized_province_codes 的 31 省各一次，所有 sales_investment_intensity"
                    "之和不得超过 remaining_market_budget，facility_actions 数量不得超过"
                    "max_facility_targets。engagement=initiate 时必须至少发送一条合法消息；"
                    "engagement=respond 时必须读取并回应至少一条授权消息或 pending session；"
                    "engagement=monitor"
                    "或 ignore 时不得发消息，且必须填写 no_action_reason、alternatives、"
                    "opportunity_costs 与 reconsideration_conditions。发起交易消息时必须填写"
                    "唯一 session_id、transaction_state=proposed、且恰好包含一个对手的授权 "
                    "recipient_ids、logical_sequence=0、"
                    "resource_amount、public_summary 与 evidence_refs。当前输出消息数量不得超过"
                    "output_constraints 中相应的剩余消息额度；额度为 0 时不得发送对应消息。"
                    "只有 pending_sessions 中列出的 session_id 允许 respond；visible_messages"
                    "中不属于 pending_sessions 的观察消息只能关注，不能复用其 session_id。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": instruction,
                        "authorized_context": authorized_context,
                        "schema": response_type.model_json_schema(),
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]
        context_payload = authorized_context if isinstance(authorized_context, dict) else {}
        inbox_payload = context_payload.get("inbox", {})
        constraints_payload = context_payload.get("output_constraints", {})
        repair_authority = {
            "branch_id": inbox_payload.get("branch_id"),
            "tick": inbox_payload.get("tick"),
            "wave": inbox_payload.get("wave"),
            "agent_kind": inbox_payload.get("agent_kind"),
            "agent_id": inbox_payload.get("agent_id"),
            "inbox_id": inbox_payload.get("inbox_id"),
            "authorized_message_ids": inbox_payload.get("message_ids", []),
            "authorized_pending_session_ids": inbox_payload.get("pending_session_ids", []),
            "remaining_message_limits": {
                "interprovincial": constraints_payload.get("max_interprovincial_proposals"),
                "province_automaker": constraints_payload.get("max_province_automaker_packages"),
                "automaker_private": constraints_payload.get("max_automaker_private_messages"),
            },
        }
        last_failure = "provider_error"
        for attempt in range(4):
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
                raw_content = response.choices[0].message.content or "{}"
                value = response_type.model_validate_json(raw_content)
                expected = fallback()
                if not _same_identity(value, expected) or getattr(value, "fallback_used", False):
                    raise ValueError("response identity or fallback marker is invalid")
                if validate is not None:
                    validate(value)
                if self.cache_dir is not None:
                    key = M34CachedAgentProvider.cache_key(kind, authorized_context, response_type)
                    path = self.cache_dir / f"{kind}_{key}.json"
                    output = value.model_dump(mode="json")
                    envelope = {
                        "schema_version": "m34-luna-cache-envelope-v3",
                        "kind": kind,
                        "model": model,
                        "quality_contract": CACHE_QUALITY_CONTRACT,
                        "input_hash": canonical_hash(authorized_context),
                        "output_hash": canonical_hash(output),
                        "output": output,
                    }
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_suffix(".tmp")
                    temporary.write_text(
                        json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2),
                        encoding="utf-8",
                    )
                    temporary.replace(path)
                return value
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_failure = (
                    "schema_validation"
                    if isinstance(exc, (ValidationError, json.JSONDecodeError))
                    else "identity_validation"
                    if "identity" in str(exc)
                    else "domain_validation"
                )
                error_text = str(exc)
                error_code = error_text.split(":", 1)[0].splitlines()[0][:80]
                pending_ids = repair_authority["authorized_pending_session_ids"]
                message_limits = repair_authority["remaining_message_limits"]
                agent_kind = repair_authority["agent_kind"]
                repair_hint = "按 validation_error 修复全部冲突字段。"
                if error_code == "RESPOND_MESSAGE_REQUIRED":
                    can_respond = bool(pending_ids) and (
                        agent_kind != "automaker" or bool(message_limits.get("automaker_private"))
                    )
                    repair_hint = (
                        "保留 engagement=respond，并仅对 authorized_pending_session_ids 中的"
                        "一个会话发送一条合法回应。"
                        if can_respond
                        else "将 engagement 改为 revise，outgoing_messages 设为空，并填写"
                        " no_action_reason 与 reconsideration_conditions。"
                    )
                elif error_code == "UNAUTHORIZED_SESSION_RESPONSE":
                    repair_hint = (
                        "把回应的 session_id 改成 authorized_pending_session_ids 中的一个值；"
                        "若列表为空，则改为 revise 并清空 outgoing_messages。"
                    )
                elif error_code == "AUTOMAKER_MESSAGE_BUDGET_EXCEEDED":
                    repair_hint = (
                        "把 outgoing_messages 截至 automaker_private 剩余额度；若额度为 0，"
                        "改为 revise 并清空 outgoing_messages。"
                    )
                elif error_code == "TRANSACTION_SINGLE_COUNTERPART_REQUIRED":
                    repair_hint = "每条交易消息只保留一个授权 recipient_id。"
                LOGGER.warning(
                    "m34_live_validation_failed kind=%s model=%s attempt=%s stage=%s "
                    "error_code=%s error_hash=%s",
                    kind,
                    model,
                    attempt + 1,
                    last_failure,
                    error_code,
                    hashlib.sha256(error_text.encode()).hexdigest()[:16],
                )
                messages.append({"role": "assistant", "content": raw_content})
                messages.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "repair": (
                                    "修复你上一条 JSON。完整重发一个 JSON 对象，不要解释；"
                                    "严格复用原请求中的 authorized_context 与 output_constraints。"
                                ),
                                "repair_hint": repair_hint,
                                "validation_error": error_text[:4000],
                                "error_hash": hashlib.sha256(error_text.encode()).hexdigest(),
                                "repair_authority": repair_authority,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
            except Exception as exc:
                last_failure = f"provider_{type(exc).__name__.lower()}"
                LOGGER.warning(
                    "m34_live_provider_failed kind=%s model=%s attempt=%s stage=%s",
                    kind,
                    model,
                    attempt + 1,
                    last_failure,
                )
                break
            if attempt == 3:
                break
        return _fallback_value(
            fallback,
            reason=f"live_provider_or_validation_exhausted:{last_failure}",
        )


def build_m34_agent_provider(legacy_provider: object, cache_dir: Path) -> M34AgentProvider:
    run_mode = getattr(legacy_provider, "run_mode", "fake")
    if run_mode == "live" and all(
        hasattr(legacy_provider, field)
        for field in ("client", "province_model", "automaker_model", "max_tokens")
    ):
        return M34LiveAgentProvider(
            client=legacy_provider.client,
            province_model=legacy_provider.province_model,
            automaker_model=legacy_provider.automaker_model,
            max_tokens=legacy_provider.max_tokens,
            cache_dir=cache_dir / "decisions",
            semaphore=getattr(legacy_provider, "semaphore", None),
            thinking_enabled=getattr(legacy_provider, "thinking_enabled", False),
        )
    if run_mode == "cache":
        live_miss = getattr(legacy_provider, "fallback", None)
        miss_provider: M34AgentProvider | None = None
        if getattr(live_miss, "run_mode", None) == "live" and all(
            hasattr(live_miss, field)
            for field in ("client", "province_model", "automaker_model", "max_tokens")
        ):
            miss_provider = M34LiveAgentProvider(
                client=live_miss.client,
                province_model=live_miss.province_model,
                automaker_model=live_miss.automaker_model,
                max_tokens=live_miss.max_tokens,
                cache_dir=cache_dir / "decisions",
                semaphore=getattr(live_miss, "semaphore", None),
                thinking_enabled=getattr(live_miss, "thinking_enabled", False),
            )
        return M34CachedAgentProvider(
            cache_dir / "decisions",
            miss_provider=miss_provider,
        )
    return M34FakeAgentProvider()
