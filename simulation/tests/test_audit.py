import json

import pytest

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.models.audit import (
    AgentInvocationTrace,
    AuditRecordType,
    MechanismExplanation,
)
from simulation.models.common import Phase
from simulation.models.experiment import ExperimentConfig


@pytest.mark.asyncio
async def test_agent_events_and_mechanisms_are_linked_to_hash_chained_audit(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="验证全链路行为追溯"))
    await adapter.approve_directive(world.experiment_id, world.policy)
    await adapter.run_to_phase(world.experiment_id, Phase.T2)

    agent_records = (
        await adapter.get_audit(
            world.experiment_id,
            record_type=AuditRecordType.AGENT_INVOCATION,
            limit=500,
        )
    ).records
    mechanism_records = (
        await adapter.get_audit(
            world.experiment_id,
            phase=Phase.T2,
            record_type=AuditRecordType.MECHANISM_EXPLANATION,
            limit=5000,
        )
    ).records

    assert any(
        isinstance(item.payload, AgentInvocationTrace)
        and item.payload.operation == "decide_province_action"
        for item in agent_records
    )
    assert any(
        isinstance(item.payload, AgentInvocationTrace)
        and item.payload.operation == "decide_enterprise_batch"
        for item in agent_records
    )
    assert len(mechanism_records) == 31 * 5 + 186 * 4 + 6
    for record in mechanism_records:
        assert isinstance(record.payload, MechanismExplanation)
        expected = round(max(0, min(100, record.payload.raw_value)), 4)
        assert abs(record.payload.final_value - expected) <= 1e-3
        assert abs(record.payload.residual) <= 1e-3

    events = await adapter.get_events(world.experiment_id)
    linked = [
        item
        for item in events
        if item.type in {"province.decision.completed", "enterprise.batch.completed"}
    ]
    assert linked
    assert all(isinstance(item.payload.get("audit_record_id"), str) for item in linked)
    assert adapter.replay.verify_audit_chain(world.experiment_id)


@pytest.mark.asyncio
async def test_audit_chain_detects_tampering_and_never_contains_sensitive_fields(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    world = await adapter.initialize(ExperimentConfig(objective="验证审计防篡改与脱敏"))
    path = tmp_path / "experiments" / world.experiment_id / "audit.jsonl"
    raw = path.read_text(encoding="utf-8")
    assert "api_key" not in raw.lower()
    assert "reasoning_content" not in raw.lower()

    lines = raw.splitlines()
    first = json.loads(lines[0])
    first["record_hash"] = "0" * 64
    lines[0] = json.dumps(first, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not adapter.replay.verify_audit_chain(world.experiment_id)
