from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from simulation.services.replay import canonical_hash

ModelT = TypeVar("ModelT", bound=BaseModel)


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
    ) -> ModelT: ...


def _fallback_value(fallback: Callable[[], ModelT]) -> ModelT:
    value = fallback()
    fields = type(value).model_fields
    updates: dict[str, object] = {}
    if "fallback_used" in fields:
        updates["fallback_used"] = True
    if "fallback_reason" in fields and not getattr(value, "fallback_reason", None):
        updates["fallback_reason"] = "provider_or_validation_fallback"
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
    ) -> ModelT:
        del kind, instruction, authorized_context, response_type
        return _fallback_value(fallback)


class M34CachedAgentProvider:
    run_mode = "cache"

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def model_name_for(self, kind: str) -> str:
        del kind
        return "cached-luna-output"

    @staticmethod
    def cache_key(kind: str, authorized_context: object, response_type: type[BaseModel]) -> str:
        payload = {
            "kind": kind,
            "authorized_context": authorized_context,
            "schema": response_type.model_json_schema(),
            "contract": "m34-authorized-context-v1",
        }
        return canonical_hash(payload)

    async def resolve(
        self,
        *,
        kind: str,
        instruction: str,
        authorized_context: object,
        response_type: type[ModelT],
        fallback: Callable[[], ModelT],
    ) -> ModelT:
        del instruction
        key = self.cache_key(kind, authorized_context, response_type)
        path = self.cache_dir / f"{kind}_{key}.json"
        if not path.is_file():
            return _fallback_value(fallback)
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            output = envelope["output"]
            if envelope.get("input_hash") != canonical_hash(authorized_context):
                return _fallback_value(fallback)
            if envelope.get("output_hash") != canonical_hash(output):
                return _fallback_value(fallback)
            value = response_type.model_validate(output)
            expected = fallback()
            if not _same_identity(value, expected) or getattr(value, "fallback_used", False):
                return _fallback_value(fallback)
            return value
        except (KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError):
            return _fallback_value(fallback)


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
    ) -> None:
        self.client = client
        self.province_model = province_model
        self.automaker_model = automaker_model
        self.max_tokens = max_tokens
        self.cache_dir = cache_dir
        self.semaphore = semaphore or asyncio.Semaphore(16)

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
                    "现实承诺、精确响应日期或思维链。"
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
        for attempt in range(2):
            try:
                async with self.semaphore:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": response_type.__name__.lower(),
                                "strict": True,
                                "schema": response_type.model_json_schema(),
                            },
                        },
                        max_completion_tokens=self.max_tokens,
                    )
                value = response_type.model_validate_json(
                    response.choices[0].message.content or "{}"
                )
                expected = fallback()
                if not _same_identity(value, expected) or getattr(value, "fallback_used", False):
                    return _fallback_value(fallback)
                if self.cache_dir is not None:
                    key = M34CachedAgentProvider.cache_key(kind, authorized_context, response_type)
                    path = self.cache_dir / f"{kind}_{key}.json"
                    output = value.model_dump(mode="json")
                    envelope = {
                        "schema_version": "m34-luna-cache-envelope-v1",
                        "kind": kind,
                        "model": model,
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
                messages.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "repair": "修复上一响应，仅返回完整 JSON。",
                                "error_hash": hashlib.sha256(str(exc).encode()).hexdigest(),
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
            except Exception:
                break
            if attempt == 1:
                break
        return _fallback_value(fallback)


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
        )
    if run_mode == "cache":
        return M34CachedAgentProvider(cache_dir / "decisions")
    return M34FakeAgentProvider()
