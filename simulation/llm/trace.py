from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from simulation.models.audit import ProviderAttemptTrace, TokenUsageTrace


@dataclass
class ProviderCallCapture:
    actual_model: str | None = None
    attempts: list[ProviderAttemptTrace] = field(default_factory=list)
    usage: TokenUsageTrace | None = None
    cache_key_hash: str | None = None
    cache_hit: bool | None = None
    fallback_reason: str | None = None


_ACTIVE_CAPTURE: ContextVar[ProviderCallCapture | None] = ContextVar(
    "policyscope_provider_call_capture",
    default=None,
)


@contextmanager
def capture_provider_call() -> Iterator[ProviderCallCapture]:
    capture = ProviderCallCapture()
    token = _ACTIVE_CAPTURE.set(capture)
    try:
        yield capture
    finally:
        _ACTIVE_CAPTURE.reset(token)


def active_provider_capture() -> ProviderCallCapture | None:
    return _ACTIVE_CAPTURE.get()


def set_provider_model(model: str) -> None:
    capture = active_provider_capture()
    if capture is not None:
        capture.actual_model = model


def add_provider_attempt(attempt: ProviderAttemptTrace) -> None:
    capture = active_provider_capture()
    if capture is not None:
        capture.attempts.append(attempt)


def set_provider_usage(usage: TokenUsageTrace) -> None:
    capture = active_provider_capture()
    if capture is not None:
        capture.usage = usage


def set_cache_trace(*, cache_key_hash: str, hit: bool) -> None:
    capture = active_provider_capture()
    if capture is not None:
        capture.cache_key_hash = cache_key_hash
        capture.cache_hit = hit
        capture.actual_model = "cache"


def set_provider_fallback(reason: str) -> None:
    capture = active_provider_capture()
    if capture is not None:
        capture.fallback_reason = reason
