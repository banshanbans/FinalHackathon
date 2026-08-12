from datetime import date

from pydantic import Field, HttpUrl

from simulation.models.base import FrozenDomainModel
from simulation.models.common import DataQuality


class ProvenanceRecord(FrozenDomainModel):
    source_name: str = Field(min_length=1, max_length=120)
    source_url: HttpUrl
    source_year: int = Field(ge=2000, le=2100)
    retrieved_at: date
    original_unit: str = Field(min_length=1, max_length=80)
    original_value: str | float | int | bool | None = None
    transformation: str = Field(min_length=1, max_length=300)
    missing_value_handling: str = Field(min_length=1, max_length=160)
    quality: DataQuality
