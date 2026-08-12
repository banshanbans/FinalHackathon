from enum import StrEnum


class Phase(StrEnum):
    SETUP = "SETUP"
    Y1_Q1 = "Y1_Q1"
    Y1_Q2 = "Y1_Q2"
    Y1_Q3 = "Y1_Q3"
    Y1_Q4 = "Y1_Q4"
    YEAR1_REVIEW = "YEAR1_REVIEW"
    Y2_Q1 = "Y2_Q1"
    Y2_Q2 = "Y2_Q2"
    Y2_Q3 = "Y2_Q3"
    Y2_Q4 = "Y2_Q4"
    COMPLETE = "COMPLETE"

    @property
    def order(self) -> int:
        return list(type(self)).index(self)

    @property
    def year(self) -> int | None:
        if self in {self.Y1_Q1, self.Y1_Q2, self.Y1_Q3, self.Y1_Q4, self.YEAR1_REVIEW}:
            return 1
        if self in {self.Y2_Q1, self.Y2_Q2, self.Y2_Q3, self.Y2_Q4}:
            return 2
        return None


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
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"


class BranchKind(StrEnum):
    CONTROL = "control"
    TREATMENT = "treatment"


class DataQuality(StrEnum):
    VERIFIED = "verified"
    PROXY = "proxy"
    DEMO = "demo"


class PolicyRegion(StrEnum):
    EAST = "east"
    CENTRAL = "central"
    WEST = "west"


class PolicyInputMode(StrEnum):
    ABSOLUTE = "absolute"
    DELTA = "delta"


class PrimaryGoal(StrEnum):
    REDUCE_REGIONAL_GAP = "reduce_regional_gap"


class PeerResponseMode(StrEnum):
    FOLLOW = "follow"
    DIFFERENTIATE = "differentiate"
    HOLD = "hold"


class StrategyAssessment(StrEnum):
    EFFECTIVE = "effective"
    MIXED = "mixed"
    CONSTRAINED = "constrained"


class ProvinceSignalType(StrEnum):
    DEMAND = "demand"
    AUTOMAKER_SALES = "automaker_sales"
    FACILITY_ACTIVITY = "facility_activity"
    FISCAL_CONSTRAINT = "fiscal_constraint"
    MECHANISM_RESISTANCE = "mechanism_resistance"


class SignalDirection(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SignalSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdjustmentDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"


class ProvinceReasonCode(StrEnum):
    FISCAL_SPACE = "FISCAL_SPACE"
    FISCAL_CONSTRAINT = "FISCAL_CONSTRAINT"
    CONSUMER_DEMAND = "CONSUMER_DEMAND"
    INDUSTRY_BASE = "INDUSTRY_BASE"
    BATTERY_PROXIMITY = "BATTERY_PROXIMITY"
    OPERATING_COST = "OPERATING_COST"
    PEER_ALIGNMENT = "PEER_ALIGNMENT"
    PEER_DIFFERENTIATION = "PEER_DIFFERENTIATION"
    CENTRAL_SHARE_RELIEF = "CENTRAL_SHARE_RELIEF"


class ProvinceConstraint(StrEnum):
    FISCAL_RIGIDITY = "fiscal_rigidity"
    WEAK_CONSUMER_WTP = "weak_consumer_wtp"
    WEAK_INDUSTRY_BASE = "weak_industry_base"
    BATTERY_DISTANCE = "battery_distance"
    TALENT_COST = "talent_cost"
    ENERGY_COST = "energy_cost"
    LOGISTICS_COST = "logistics_cost"


class ProvincePersonaType(StrEnum):
    CONSUMPTION_ACTIVATOR = "consumption_activator"
    INDUSTRY_ATTRACTOR = "industry_attractor"
    OPERATING_COST_COMPETITOR = "operating_cost_competitor"
    SUPPLY_CHAIN_COORDINATOR = "supply_chain_coordinator"
    FISCALLY_PRUDENT = "fiscally_prudent"
    PEER_RESPONDER = "peer_responder"


class ChannelStrategy(StrEnum):
    EXPAND = "expand"
    MAINTAIN = "maintain"
    REDUCE = "reduce"


class FacilityActionKind(StrEnum):
    NEW_PLANT = "new_plant"
    EXPAND = "expand"
    DELAY = "delay"


class SimulatedRoiBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExpansionPosture(StrEnum):
    EXPANSION = "expansion"
    DISCIPLINED = "disciplined"
    DEFENSIVE = "defensive"


class AutomakerReasonCode(StrEnum):
    CONSUMER_WTP = "CONSUMER_WTP"
    SUBSIDY_SUPPORT = "SUBSIDY_SUPPORT"
    CHANNEL_COVERAGE = "CHANNEL_COVERAGE"
    INDUSTRY_BASE = "INDUSTRY_BASE"
    BATTERY_PROXIMITY = "BATTERY_PROXIMITY"
    OPERATING_COST = "OPERATING_COST"
    FINANCIAL_CONSTRAINT = "FINANCIAL_CONSTRAINT"
    CAPACITY_DISCIPLINE = "CAPACITY_DISCIPLINE"
    DEMAND_UNCERTAINTY = "DEMAND_UNCERTAINTY"


class ReviewMode(StrEnum):
    COMPARISON = "comparison"
    SINGLE_BRANCH = "single_branch"


class ExpectedDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    MAY_INCREASE = "may_increase"
    MAY_DECREASE = "may_decrease"
    UNCERTAIN = "uncertain"
