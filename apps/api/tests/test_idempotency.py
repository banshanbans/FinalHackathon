import asyncio

import pytest
from policyscope_api.idempotency import (
    IdempotencyConflictError,
    PersistentIdempotencyRepository,
)


async def test_persistent_idempotency_is_single_flight_and_restart_safe(tmp_path) -> None:
    repository = PersistentIdempotencyRepository(tmp_path / "idempotency")
    calls = 0

    async def operation() -> dict[str, str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return {"experiment_id": "exp_m32_123456789abc"}

    first, second = await asyncio.gather(
        repository.execute(
            scope="create-experiment",
            key="stable-operation",
            payload_hash="same-payload",
            operation=operation,
        ),
        repository.execute(
            scope="create-experiment",
            key="stable-operation",
            payload_hash="same-payload",
            operation=operation,
        ),
    )
    assert first == second
    assert calls == 1

    restarted = PersistentIdempotencyRepository(tmp_path / "idempotency")
    restored = await restarted.execute(
        scope="create-experiment",
        key="stable-operation",
        payload_hash="same-payload",
        operation=operation,
    )
    assert restored == first
    assert calls == 1

    with pytest.raises(IdempotencyConflictError):
        await restarted.execute(
            scope="create-experiment",
            key="stable-operation",
            payload_hash="different-payload",
            operation=operation,
        )
