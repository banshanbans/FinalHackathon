from types import SimpleNamespace

from simulation.data import load_scenario_policy
from simulation.llm.fake_provider import FakeLLMProvider
from simulation.llm.live_provider import LiveLLMProvider
from simulation.models.experiment import ExperimentConfig


class StubCompletions:
    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls = 0

    async def create(self, **_kwargs):
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
