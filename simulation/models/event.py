from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, JsonValue

from simulation.models.base import DomainModel
from simulation.models.common import Phase


class EventEnvelope(DomainModel):
    schema_version: Literal["event-v4"] = "event-v4"
    event_id: str
    type: str
    experiment_id: str
    branch_id: str
    phase: Phase
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, JsonValue] = Field(default_factory=dict)
