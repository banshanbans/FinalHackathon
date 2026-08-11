from enum import StrEnum


class Phase(StrEnum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"

    @property
    def order(self) -> int:
        return int(self.value[1:])


class RunMode(StrEnum):
    FAKE = "fake"
    CACHE = "cache"
    LIVE = "live"
    FALLBACK = "fallback"


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    READY = "ready"
    RUNNING = "running"
    AWAITING_INTERVENTION = "awaiting_intervention"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class BranchKind(StrEnum):
    CONTROL = "control"
    TREATMENT = "treatment"


class DataQuality(StrEnum):
    VERIFIED = "verified"
    PROXY = "proxy"
    DEMO = "demo"


class RegionGroup(StrEnum):
    EAST = "east"
    CENTRAL = "central"
    WEST = "west"
    NORTHEAST = "northeast"


class Industry(StrEnum):
    AI = "ai"
    ADVANCED_MANUFACTURING = "advanced_manufacturing"
    GREEN_ENERGY = "green_energy"


class Stance(StrEnum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CAUTIOUS = "cautious"


class TalentStrategy(StrEnum):
    EXPAND = "expand"
    RETAIN = "retain"
    RESKILL = "reskill"
    STABLE = "stable"


class InteractionStrategy(StrEnum):
    COMPETE = "compete"
    COOPERATE = "cooperate"
    OBSERVE = "observe"


class ReasonCode(StrEnum):
    HIGH_INDUSTRY_FIT = "HIGH_INDUSTRY_FIT"
    TRANSITION_PRIORITY = "TRANSITION_PRIORITY"
    HIGH_FISCAL_CAPACITY = "HIGH_FISCAL_CAPACITY"
    FISCAL_CONSTRAINT = "FISCAL_CONSTRAINT"
    TALENT_COMPETITION = "TALENT_COMPETITION"
    REGIONAL_COOPERATION = "REGIONAL_COOPERATION"
    EMPLOYMENT_PRESSURE = "EMPLOYMENT_PRESSURE"
    CENTRAL_SUPPORT_REQUEST = "CENTRAL_SUPPORT_REQUEST"
