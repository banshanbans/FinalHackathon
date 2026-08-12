from types import SimpleNamespace

from simulation.data import load_scenario_policy
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.models.experiment import ExperimentConfig
from simulation.services.comparison import ComparisonService


class StubCompletions:
    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls = 0
        self.kwargs: list[dict[str, object]] = []

    async def create(self, **kwargs):
        self.kwargs.append(kwargs)
        content = self.contents[min(self.calls, len(self.contents) - 1)]
        self.calls += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def provider_with(contents: list[str]) -> tuple[LiveLLMProvider, StubCompletions]:
    completions = StubCompletions(contents)
    provider = LiveLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        central_model="central-test",
        province_model="province-test",
        fallback=FakeLLMProvider(),
    )
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return provider, completions


async def test_live_provider_repairs_invalid_output_once() -> None:
    fallback = FakeLLMProvider()
    config = ExperimentConfig(objective="测试结构化修复")
    policy = load_scenario_policy()
    valid = await fallback.generate_central_directive(config, policy)
    provider, completions = provider_with(["{}", valid.model_dump_json()])

    result = await provider.generate_central_directive(config, policy)

    assert result == valid
    assert completions.calls == 2


async def test_live_provider_falls_back_after_second_invalid_output() -> None:
    config = ExperimentConfig(objective="测试显式降级")
    policy = load_scenario_policy()
    provider, completions = provider_with(["{}", '{"still": "invalid"}'])

    result = await provider.generate_central_directive(config, policy)
    expected = await FakeLLMProvider().generate_central_directive(config, policy)

    assert result == expected
    assert completions.calls == 2


async def test_live_provider_disables_thinking_and_uses_enterprise_model() -> None:
    fallback = FakeLLMProvider()
    policy = load_scenario_policy()
    config = ExperimentConfig(objective="验证 DeepSeek 结构化参数")
    directive = await fallback.generate_central_directive(config, policy)
    provider, completions = provider_with([directive.model_dump_json()])

    await provider.generate_central_directive(config, policy)

    call = completions.kwargs[0]
    assert call["model"] == "central-test"
    assert call["response_format"] == {"type": "json_object"}
    assert call["max_tokens"] == 4096
    assert call["extra_body"] == {"thinking": {"type": "disabled"}}


async def test_comparison_review_prompt_supplies_exact_evidence_refs(tmp_path) -> None:
    fallback = FakeLLMProvider()
    from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter

    adapter = AsyncioSimulationAdapter(fallback, runtime_dir=tmp_path)
    comparison = await adapter.run_full_demo(ExperimentConfig(objective="验证复盘引用白名单"))
    assert comparison.central_review is not None
    provider, completions = provider_with([comparison.central_review.model_dump_json()])

    await provider.generate_central_review(comparison)

    user_payload = completions.kwargs[0]["messages"][1]["content"]
    assert "allowed_evidence_refs" in user_payload
    assert "comparison:national_metrics:sme_financing_accessibility_index" in user_payload
    assert "comparison:policy_diff" in user_payload
    ComparisonService.validate_review(comparison.central_review, comparison)
