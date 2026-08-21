import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.llm.m34_provider import M34CachedAgentProvider, M34LiveAgentProvider
from simulation.models.automaker import FacilityAction, ProvinceMarketAction
from simulation.models.common import ChannelStrategy, FacilityActionKind
from simulation.models.m34 import AutomakerQuarterAction, MacroTick
from simulation.services.replay import canonical_hash


class ProbeOutput(BaseModel):
    value: int


class ProbeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        content = '{"value": 0}' if len(self.calls) == 1 else '{"value": 1}'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class ProbeClient:
    def __init__(self) -> None:
        self.completions = ProbeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


class AlwaysInvalidCompletions:
    async def create(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"value": 0}'))]
        )


class AlwaysInvalidClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=AlwaysInvalidCompletions())


@pytest.mark.asyncio
async def test_live_provider_repairs_domain_validation_before_cache_write(tmp_path) -> None:
    client = ProbeClient()
    provider = M34LiveAgentProvider(
        client=client,  # type: ignore[arg-type]
        province_model="deepseek-v4-flash",
        automaker_model="deepseek-v4-flash",
        max_tokens=128,
        cache_dir=tmp_path,
    )

    def validate(value: ProbeOutput) -> None:
        if value.value != 1:
            raise ValueError("Q1 province decision must include province_action")

    result = await provider.resolve(
        kind="province_probe",
        instruction="返回合法的结构化行动。",
        authorized_context={"tick": "Q1"},
        response_type=ProbeOutput,
        fallback=lambda: ProbeOutput(value=-1),
        validate=validate,
    )

    assert result.value == 1
    assert len(client.completions.calls) == 2
    repair_messages = client.completions.calls[1]["messages"]
    assert repair_messages[-2]["role"] == "assistant"
    assert repair_messages[-2]["content"] == '{"value": 0}'
    assert "Q1 province decision must include province_action" in repair_messages[-1]["content"]
    cache_files = list(tmp_path.glob("province_probe_*.json"))
    assert len(cache_files) == 1
    envelope = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert envelope["schema_version"] == "m34-luna-cache-envelope-v3"
    assert envelope["quality_contract"] == "m34-decision-quality-v1"


def test_automaker_quarter_action_rejects_unknown_province_codes() -> None:
    invalid_codes = ["10", *MAINLAND_PROVINCE_CODES[1:]]

    with pytest.raises(ValidationError, match="authorized 31 provinces"):
        AutomakerQuarterAction(
            action_id="action_invalid_market",
            branch_id="control",
            tick=MacroTick.Q1,
            automaker_id="byd",
            province_market_actions=[
                ProvinceMarketAction(
                    province_code=code,
                    sales_investment_intensity=0.01,
                    channel_strategy=ChannelStrategy.MAINTAIN,
                )
                for code in invalid_codes
            ],
            public_summary="验证非法省份代码会在进入环境前被拒绝。",
        )


def test_automaker_quarter_action_rejects_unknown_facility_province() -> None:
    with pytest.raises(ValidationError, match="authorized mainland provinces"):
        AutomakerQuarterAction(
            action_id="action_invalid_facility",
            branch_id="control",
            tick=MacroTick.Q1,
            automaker_id="byd",
            province_market_actions=[
                ProvinceMarketAction(
                    province_code=code,
                    sales_investment_intensity=0.01,
                    channel_strategy=ChannelStrategy.MAINTAIN,
                )
                for code in MAINLAND_PROVINCE_CODES
            ],
            facility_actions=[
                FacilityAction(
                    province_code="10",
                    action=FacilityActionKind.DELAY,
                    investment_intensity=0.01,
                )
            ],
            public_summary="验证非法产能目标会在进入环境前被拒绝。",
        )


@pytest.mark.asyncio
async def test_live_provider_exposes_validation_exhaustion_reason(tmp_path) -> None:
    class FallbackOutput(BaseModel):
        value: int
        fallback_used: bool = False
        fallback_reason: str | None = None

    provider = M34LiveAgentProvider(
        client=AlwaysInvalidClient(),  # type: ignore[arg-type]
        province_model="deepseek-v4-flash",
        automaker_model="deepseek-v4-flash",
        max_tokens=128,
        cache_dir=tmp_path,
    )

    def validate(value: FallbackOutput) -> None:
        if value.value != 1:
            raise ValueError("expected repaired output")

    result = await provider.resolve(
        kind="province_probe",
        instruction="返回合法结构化行动。",
        authorized_context={"tick": "Q1"},
        response_type=FallbackOutput,
        fallback=lambda: FallbackOutput(
            value=-1,
            fallback_used=True,
            fallback_reason="fake_provider_deterministic_fallback",
        ),
        validate=validate,
    )

    assert result.fallback_used is True
    assert result.fallback_reason == ("live_provider_or_validation_exhausted:domain_validation")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_cached_provider_promotes_valid_legacy_inbox_cache(tmp_path) -> None:
    legacy_context = {
        "schema_version": "authorized-inbox-v1",
        "inbox_id": "inbox-1",
        "branch_id": "control",
        "tick": "Q1",
        "wave": "wave_0",
        "agent_kind": "province",
        "agent_id": "11",
        "message_ids": [],
        "public_policy_summary": "西部 95%、中部 90%、东部 85%。",
        "public_national_summary": None,
        "own_result_summary": None,
        "pending_session_ids": [],
        "visible_event_ids": [],
        "previous_decision_id": None,
        "context_hash": "context-1",
    }
    current_context = {
        "schema_version": "m34-live-authorized-context-v2",
        "inbox": legacy_context,
        "output_constraints": {"required_action": "province_action"},
        "visible_messages": [],
        "pending_sessions": [],
        "previous_action": None,
    }
    output = {"value": 7}
    legacy_key = M34CachedAgentProvider.cache_key(
        "province_probe",
        legacy_context,
        ProbeOutput,
        contract="m34-authorized-context-v1",
    )
    legacy_path = tmp_path / f"province_probe_{legacy_key}.json"
    legacy_path.write_text(
        json.dumps(
            {
                "schema_version": "m34-luna-cache-envelope-v1",
                "kind": "province_probe",
                "model": "deepseek-v4-flash",
                "input_hash": canonical_hash(legacy_context),
                "output_hash": canonical_hash(output),
                "output": output,
            }
        ),
        encoding="utf-8",
    )
    provider = M34CachedAgentProvider(tmp_path)

    result = await provider.resolve(
        kind="province_probe",
        instruction="返回合法结构化行动。",
        authorized_context=current_context,
        response_type=ProbeOutput,
        fallback=lambda: ProbeOutput(value=-1),
    )

    assert result.value == 7
    current_key = M34CachedAgentProvider.cache_key("province_probe", current_context, ProbeOutput)
    promoted = json.loads(
        (tmp_path / f"province_probe_{current_key}.json").read_text(encoding="utf-8")
    )
    assert promoted["schema_version"] == "m34-luna-cache-envelope-v2"
    assert promoted["output"] == output


@pytest.mark.asyncio
async def test_cached_provider_does_not_read_v2_cache_for_v3_context(tmp_path) -> None:
    context = {
        "schema_version": "m34-live-authorized-context-v3",
        "inbox": {"schema_version": "authorized-inbox-v1"},
    }
    output = {"value": 7}
    old_key = M34CachedAgentProvider.cache_key(
        "province_probe",
        context,
        ProbeOutput,
        contract="m34-live-authorized-context-v2",
    )
    (tmp_path / f"province_probe_{old_key}.json").write_text(
        json.dumps(
            {
                "schema_version": "m34-luna-cache-envelope-v2",
                "kind": "province_probe",
                "model": "deepseek-v4-flash",
                "input_hash": canonical_hash(context),
                "output_hash": canonical_hash(output),
                "output": output,
            }
        ),
        encoding="utf-8",
    )

    result = await M34CachedAgentProvider(tmp_path).resolve(
        kind="province_probe",
        instruction="返回合法结构化行动。",
        authorized_context=context,
        response_type=ProbeOutput,
        fallback=lambda: ProbeOutput(value=-1),
    )

    assert result.value == -1
