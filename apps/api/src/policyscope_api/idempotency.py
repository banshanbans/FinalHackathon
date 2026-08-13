from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable
from hashlib import sha256
from pathlib import Path
from typing import TypeVar, cast
from uuid import uuid4

ResponseT = TypeVar("ResponseT")


class IdempotencyConflictError(ValueError):
    pass


class PersistentIdempotencyRepository:
    """Small JSON repository with per-operation single-flight and restart recovery."""

    def __init__(self, root: Path, *, ttl_seconds: int = 7 * 24 * 60 * 60) -> None:
        self.root = root
        self.ttl_seconds = ttl_seconds
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    @staticmethod
    def _identity(scope: str, key: str) -> str:
        return sha256(f"{scope}\0{key}".encode()).hexdigest()

    async def _lock_for(self, identity: str) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(identity, asyncio.Lock())

    async def execute(
        self,
        *,
        scope: str,
        key: str,
        payload_hash: str,
        operation: Callable[[], Awaitable[ResponseT]],
    ) -> ResponseT:
        identity = self._identity(scope, key)
        lock = await self._lock_for(identity)
        async with lock:
            record = await asyncio.to_thread(self._read, identity)
            if record is not None:
                if record["payload_hash"] != payload_hash:
                    raise IdempotencyConflictError("同一 Idempotency-Key 不能用于不同请求。")
                return cast(ResponseT, record["response"])
            response = await operation()
            await asyncio.to_thread(
                self._write,
                identity,
                {
                    "schema_version": "idempotency-record-v1",
                    "payload_hash": payload_hash,
                    "created_at_epoch": time.time(),
                    "response": response,
                },
            )
            return response

    def _path(self, identity: str) -> Path:
        return self.root / f"{identity}.json"

    def _read(self, identity: str) -> dict[str, object] | None:
        path = self._path(identity)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError("IDEMPOTENCY_RECORD_INVALID") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "idempotency-record-v1"
            or not isinstance(payload.get("payload_hash"), str)
            or not isinstance(payload.get("created_at_epoch"), (int, float))
            or "response" not in payload
        ):
            raise RuntimeError("IDEMPOTENCY_RECORD_INVALID")
        if time.time() - float(payload["created_at_epoch"]) > self.ttl_seconds:
            return None
        return payload

    def _write(self, identity: str, payload: dict[str, object]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(identity)
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            directory_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary_path.unlink(missing_ok=True)
