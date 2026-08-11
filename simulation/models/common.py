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


class EnterpriseArchetype(StrEnum):
    LARGE_STATE_OWNED = "large_state_owned"
    LARGE_PRIVATE = "large_private"
    TECHNOLOGY_SME = "technology_sme"
    TRADITIONAL_SME = "traditional_sme"
    HIGH_ENERGY_INDUSTRIAL = "high_energy_industrial"
    EXPORT_MANUFACTURER = "export_manufacturer"


class Participation(StrEnum):
    PARTICIPATE = "participate"
    CONDITIONAL = "conditional"
    WAIT = "wait"
    DECLINE = "decline"


class UpgradeType(StrEnum):
    DIGITAL = "digital"
    GREEN = "green"
    GENERAL = "general"
    NONE = "none"


class FinancingChoice(StrEnum):
    SELF_FUNDED = "self_funded"
    DIRECT_SUBSIDY = "direct_subsidy"
    INTEREST_SUBSIDY = "interest_subsidy"
    GUARANTEE_LOAN = "guarantee_loan"
    NONE = "none"


class ProvinceReasonCode(StrEnum):
    MANUFACTURING_BASE = "MANUFACTURING_BASE"
    FISCAL_CONSTRAINT = "FISCAL_CONSTRAINT"
    SME_ACCESS_PRIORITY = "SME_ACCESS_PRIORITY"
    GREEN_TRANSITION = "GREEN_TRANSITION"
    FINANCING_GAP = "FINANCING_GAP"
    REGIONAL_ACCESS = "REGIONAL_ACCESS"
    CENTRAL_SUPPORT_REQUEST = "CENTRAL_SUPPORT_REQUEST"


class EnterpriseReasonCode(StrEnum):
    POLICY_MATCH = "POLICY_MATCH"
    SUBSIDY_ATTRACTIVE = "SUBSIDY_ATTRACTIVE"
    CREDIT_ACCESS = "CREDIT_ACCESS"
    GUARANTEE_NEEDED = "GUARANTEE_NEEDED"
    CASH_FLOW_CONSTRAINT = "CASH_FLOW_CONSTRAINT"
    TECHNOLOGY_READINESS = "TECHNOLOGY_READINESS"
    GREEN_COMPLIANCE = "GREEN_COMPLIANCE"
    DEMAND_UNCERTAINTY = "DEMAND_UNCERTAINTY"
    SUPPORT_INSUFFICIENT = "SUPPORT_INSUFFICIENT"


class ReviewMode(StrEnum):
    COMPARISON = "comparison"
    SINGLE_BRANCH = "single_branch"
