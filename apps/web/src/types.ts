export type Phase = "T0" | "T1" | "T2" | "T3" | "T4" | "T5";
export type RunMode = "live" | "cache" | "fake" | "fallback";

export interface ProvinceProfile {
  province_code: string;
  name: string;
  short_name: string;
  region_group: "east" | "central" | "west" | "northeast";
  data_quality: "verified" | "proxy" | "demo";
  source_year: number;
}

export interface ProvinceState {
  province_code: string;
  phase: string;
  policy_benefit_index: number;
  innovation_index: number;
  employment_index: number;
  fiscal_pressure: number;
  policy_accessibility: number;
  talent_attraction: number;
  cooperation_stock: number;
  last_action_id: string | null;
}

export interface ProvinceAction {
  action_id: string;
  province_code: string;
  phase: Phase;
  stance: "aggressive" | "balanced" | "cautious";
  implementation_intensity: number;
  local_budget_ratio: number;
  priority_industries: string[];
  talent_strategy: string;
  interaction_strategy: string;
  target_provinces: string[];
  requested_central_support: number;
  reason_codes: string[];
  public_summary: string;
  run_mode: string;
  fallback_used: boolean;
}

export interface MechanismContribution {
  policy_match: number;
  central_support: number;
  local_investment: number;
  cooperation_spillover: number;
  geographic_spillover: number;
  competition_crowding_out: number;
  fiscal_execution_cost: number;
}

export interface EvaluationWeights {
  innovation: number;
  employment: number;
  equity: number;
  fiscal_efficiency: number;
}

export interface Policy {
  policy_id: string;
  central_budget_index: number;
  local_match_requirement: number;
  regional_bias: number;
  cooperation_incentive: number;
  evaluation_weights: EvaluationWeights;
  priority_industries: string[];
  mechanism_version: string;
}

export interface CentralDirective {
  directive_id: string;
  policy: Policy;
  policy_objectives: string[];
  hard_constraints: string[];
  public_summary: string;
  approval_status: "draft" | "approved" | "rejected";
}

export interface ParameterChange {
  from_value: number;
  to_value: number;
}

export interface InterventionProposal {
  proposal_id: string;
  parameter_changes: Record<string, ParameterChange>;
  target_metrics: string[];
  expected_directions: Record<string, string>;
  tradeoffs: string[];
  evidence_refs: string[];
  public_summary: string;
  approval_status: "draft" | "approved" | "rejected";
}

export interface CentralIntervention {
  intervention_id: string;
  proposal_id: string;
  parameter_changes: Record<string, ParameterChange>;
  approval_status: "approved";
}

export interface NationalMetrics {
  overall_policy_benefit: number;
  policy_accessibility: number;
  innovation_vitality: number;
  employment_support: number;
  regional_gap: number;
  fiscal_pressure: number;
  cooperation_density: number;
  industry_concentration: number;
}

export interface WorldState {
  experiment_id: string;
  branch_id: string;
  parent_checkpoint_id: string | null;
  phase: Phase;
  status: string;
  run_mode: RunMode;
  policy: Policy;
  directive: CentralDirective;
  national_metrics: NationalMetrics;
  provinces: Record<string, ProvinceState>;
  actions: Record<string, ProvinceAction>;
  contributions: Record<string, MechanismContribution>;
  intervention_proposals: InterventionProposal[];
  approved_intervention: CentralIntervention | null;
  versions: {
    data: string;
    mechanism: string;
    prompt: string;
    model: string;
    app: string;
  };
  seed: number;
}

export interface Branch {
  branch_id: string;
  experiment_id: string;
  kind: "control" | "treatment";
  parent_checkpoint_id: string;
  current_phase: Phase;
}

export interface MetricDelta {
  control: number;
  treatment: number;
  delta: number;
}

export interface ProvinceDelta {
  province_code: string;
  province_name: string;
  policy_benefit_delta: number;
  accessibility_delta: number;
  fiscal_pressure_delta: number;
}

export interface CentralReview {
  review_id: string;
  findings: Array<{
    title: string;
    summary: string;
    evidence_refs: string[];
    tradeoff: string | null;
  }>;
  limitations: string[];
  public_summary: string;
}

export interface ComparisonResult {
  experiment_id: string;
  checkpoint_id: string;
  control_branch_id: string;
  treatment_branch_id: string;
  policy_diff: Record<string, Record<string, number>>;
  national_metrics: Record<string, MetricDelta>;
  province_deltas: ProvinceDelta[];
  mechanism_totals: Record<string, number>;
  top_improved: string[];
  top_pressured: string[];
  central_review: CentralReview | null;
}

export interface SimulationEvent {
  event_id: string;
  type: string;
  experiment_id: string;
  branch_id: string;
  phase: Phase;
  timestamp: string;
  payload: Record<string, unknown>;
}
