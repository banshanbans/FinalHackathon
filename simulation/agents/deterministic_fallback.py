from simulation.llm.fake_provider import FakeLLMProvider


class DeterministicFallbackProvider(FakeLLMProvider):
    """Named fallback used when a live or cached decision cannot be produced."""

    run_mode = "fallback"
