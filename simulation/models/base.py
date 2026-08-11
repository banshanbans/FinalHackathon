from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Strict base class for persisted simulation contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FrozenDomainModel(DomainModel):
    """Strict immutable contract used for approved inputs and checkpoints."""

    model_config = ConfigDict(extra="forbid", frozen=True)
