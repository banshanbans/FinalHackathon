import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, JsonValue

from simulation.models.audit import (
    AgentInvocationTrace,
    AuditListResponse,
    AuditPayload,
    AuditRecord,
    AuditRecordType,
    DecisionGateTrace,
    MechanismExplanation,
)
from simulation.models.common import Phase
from simulation.models.event import EventEnvelope
from simulation.models.world import WorldState

SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "access_token",
    "refresh_token",
    "secret",
    "reasoning_content",
}


def sanitize_for_audit(value: object) -> JsonValue:
    if isinstance(value, BaseModel):
        return sanitize_for_audit(value.model_dump(mode="json"))
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in SENSITIVE_KEYS or normalized.endswith("_api_key"):
                result[str(key)] = "[REDACTED]"
            else:
                result[str(key)] = sanitize_for_audit(item)
        return result
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_audit(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def canonical_hash(value: object) -> str:
    sanitized = sanitize_for_audit(value)
    raw = json.dumps(sanitized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class ReplayService:
    """Append-only JSONL replay plus latest state snapshots."""

    def __init__(self, runtime_dir: Path):
        self.runtime_dir = runtime_dir
        self._audit_lock = threading.RLock()

    def _experiment_dir(self, experiment_id: str) -> Path:
        path = self.runtime_dir / "experiments" / experiment_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, event: EventEnvelope) -> None:
        path = self._experiment_dir(event.experiment_id) / "replay.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def write_state(self, state: WorldState) -> None:
        path = self._experiment_dir(state.experiment_id) / f"state_{state.branch_id}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def read_events(self, experiment_id: str) -> list[EventEnvelope]:
        path = self._experiment_dir(experiment_id) / "replay.jsonl"
        if not path.exists():
            return []
        events: list[EventEnvelope] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(EventEnvelope.model_validate_json(line))
        return events

    def read_raw(self, experiment_id: str) -> list[dict[str, object]]:
        return [json.loads(item.model_dump_json()) for item in self.read_events(experiment_id)]

    def _audit_path(self, experiment_id: str) -> Path:
        return self._experiment_dir(experiment_id) / "audit.jsonl"

    def _read_audit_unlocked(self, experiment_id: str) -> list[AuditRecord]:
        path = self._audit_path(experiment_id)
        if not path.exists():
            return []
        records: list[AuditRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(AuditRecord.model_validate_json(line))
        return records

    def append_audit(
        self,
        *,
        experiment_id: str,
        branch_id: str,
        phase: Phase,
        payload: AuditPayload,
        parent_record_ids: list[str] | None = None,
    ) -> AuditRecord:
        return self.append_audits(
            experiment_id=experiment_id,
            branch_id=branch_id,
            phase=phase,
            items=[(payload, parent_record_ids or [])],
        )[0]

    def append_audits(
        self,
        *,
        experiment_id: str,
        branch_id: str,
        phase: Phase,
        items: list[tuple[AuditPayload, list[str]]],
    ) -> list[AuditRecord]:
        if not items:
            return []
        with self._audit_lock:
            existing = self._read_audit_unlocked(experiment_id)
            sequence = existing[-1].sequence if existing else 0
            previous_hash = existing[-1].record_hash if existing else None
            records: list[AuditRecord] = []
            for payload, parents in items:
                sequence += 1
                record_id = f"aud_{uuid4().hex[:16]}"
                timestamp = datetime.now(UTC)
                unsigned = {
                    "schema_version": "audit-record-v1",
                    "record_id": record_id,
                    "sequence": sequence,
                    "experiment_id": experiment_id,
                    "branch_id": branch_id,
                    "phase": phase.value,
                    "timestamp": timestamp.isoformat(),
                    "parent_record_ids": parents,
                    "previous_record_hash": previous_hash,
                    "payload": sanitize_for_audit(payload),
                }
                record_hash = canonical_hash(unsigned)
                record = AuditRecord(
                    record_id=record_id,
                    sequence=sequence,
                    experiment_id=experiment_id,
                    branch_id=branch_id,
                    phase=phase,
                    timestamp=timestamp,
                    parent_record_ids=parents,
                    previous_record_hash=previous_hash,
                    record_hash=record_hash,
                    payload=payload,
                )
                records.append(record)
                previous_hash = record_hash
            path = self._audit_path(experiment_id)
            with path.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(record.model_dump_json() + "\n")
            return records

    def read_audit(
        self,
        experiment_id: str,
        *,
        branch_id: str | None = None,
        phase: Phase | None = None,
        actor_kind: str | None = None,
        actor_id: str | None = None,
        record_type: AuditRecordType | None = None,
        outcome: str | None = None,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> AuditListResponse:
        with self._audit_lock:
            records = self._read_audit_unlocked(experiment_id)
        filtered: list[AuditRecord] = []
        for record in records:
            payload = record.payload
            if record.sequence <= after_sequence:
                continue
            if branch_id is not None and record.branch_id != branch_id:
                continue
            if phase is not None and record.phase != phase:
                continue
            if record_type is not None and payload.kind != record_type:
                continue
            if actor_kind is not None and getattr(payload, "actor_kind", None) != actor_kind:
                continue
            if actor_id is not None and getattr(payload, "actor_id", None) != actor_id:
                continue
            if outcome is not None and getattr(payload, "outcome", None) != outcome:
                continue
            filtered.append(record)
        page = filtered[:limit]
        next_sequence = page[-1].sequence if len(filtered) > limit and page else None
        return AuditListResponse(records=page, next_sequence=next_sequence)

    def get_audit_record(self, experiment_id: str, record_id: str) -> AuditRecord:
        with self._audit_lock:
            records = self._read_audit_unlocked(experiment_id)
        for record in records:
            if record.record_id == record_id:
                return record
        raise KeyError(f"audit record not found: {record_id}")

    def find_audit_by_object(self, experiment_id: str, object_id: str) -> AuditRecord:
        with self._audit_lock:
            records = self._read_audit_unlocked(experiment_id)
        for record in reversed(records):
            payload = record.payload
            if isinstance(payload, AgentInvocationTrace) and object_id in payload.output_ids:
                return record
            if isinstance(payload, DecisionGateTrace) and object_id in payload.object_ids:
                return record
            if isinstance(payload, MechanismExplanation) and object_id == payload.explanation_id:
                return record
        raise KeyError(f"audit object not found: {object_id}")

    def verify_audit_chain(self, experiment_id: str) -> bool:
        with self._audit_lock:
            records = self._read_audit_unlocked(experiment_id)
        previous_hash: str | None = None
        for record in records:
            if record.previous_record_hash != previous_hash:
                return False
            unsigned = {
                "schema_version": record.schema_version,
                "record_id": record.record_id,
                "sequence": record.sequence,
                "experiment_id": record.experiment_id,
                "branch_id": record.branch_id,
                "phase": record.phase.value,
                "timestamp": record.timestamp.isoformat(),
                "parent_record_ids": record.parent_record_ids,
                "previous_record_hash": record.previous_record_hash,
                "payload": sanitize_for_audit(record.payload),
            }
            if canonical_hash(unsigned) != record.record_hash:
                return False
            previous_hash = record.record_hash
        return True
