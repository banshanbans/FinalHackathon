export type Phase = "T0" | "T1" | "T2" | "T3" | "T4" | "T5";
export type RunMode = "live" | "cache" | "fake" | "fallback";
export type DataQuality = "verified" | "proxy" | "demo";
export type Participation = "participate" | "conditional" | "wait" | "decline";
export type EnterpriseArchetype =
  | "large_state_owned"
  | "large_private"
  | "technology_sme"
  | "traditional_sme"
  | "high_energy_industrial"
  | "export_manufacturer";

export interface InstrumentMix {
  direct_subsidy: number;
  interest_subsidy: number;
  financing_guarantee: number;
}

export interface TechnologyMix {
  digital: number;
  green: number;
  general: number;
}

export interface Policy {
  schema_version: "policy-v2";
  policy_id: string;
  domain: string;
  support_intensity: number;
  local_match_requirement: number;
  instrument_mix: InstrumentMix;
  sme_preference: number;
  regional_support_bias: number;
  technology_mix: TechnologyMix;
  mechanism_version: string;
}

export interface CentralDirective {
  directive_id: string;
  policy: Policy;
  policy_objectives: string[];
  hard_constraints: string[];
  public_summary: string;
  requires_human_approval: true;
  approval_status: "draft" | "approved" | "rejected";
}

export interface ProvinceProfile {
  province_code: string;
  name: string;
  short_name: string;
  region_group: "east" | "central" | "west" | "northeast";
  economic_scale: number;
  fiscal_capacity: number;
  industrial_diversity: number;
  advanced_manufacturing_base: number;
  digital_infrastructure: number;
  green_energy_base: number;
  sme_density: number;
  credit_access: number;
  transition_pressure: number;
  fiscal_conservatism: number;
  data_quality: DataQuality;
  source_year: number;
}

export interface ProvinceState {
  province_code: string;
  phase: Phase;
  enterprise_participation_index: number;
  equipment_renewal_willingness_index: number;
  sme_financing_accessibility_index: number;
  industrial_upgrade_index: number;
  fiscal_pressure_index: number;
  last_action_id: string | null;
}

export interface ProvinceAction {
  action_id: string;
  province_code: string;
  phase: Phase;
  implementation_intensity: number;
  local_match_ratio: number;
  instrument_mix: InstrumentMix;
  sme_preference: number;
  regional_delivery_focus: number;
  technology_mix: TechnologyMix;
  requested_central_support: number;
  reason_codes: string[];
  public_summary: string;
  run_mode: string;
  fallback_used: boolean;
}

export interface ProvinceFeedback {
  feedback_id: string;
  province_code: string;
  phase: "T3";
  implementation_assessment: string;
  priority_enterprise_groups: string[];
  requested_central_support: number;
  reason_codes: string[];
  evidence_refs: string[];
  public_summary: string;
  run_mode: string;
  fallback_used: boolean;
}

export interface EnterpriseArchetypeDefinition {
  archetype: EnterpriseArchetype;
  display_name: string;
  weight: number;
  equipment_age_pressure: number;
  digital_readiness: number;
  green_transition_pressure: number;
  financing_constraint: number;
  collateral_capacity: number;
  cash_flow_resilience: number;
  export_exposure: number;
  data_quality: DataQuality;
}

export interface EnterpriseGroupProfile extends EnterpriseArchetypeDefinition {
  enterprise_id: string;
  province_code: string;
  source_year: number;
}

export interface EnterpriseGroupState {
  enterprise_id: string;
  province_code: string;
  phase: Phase;
  participation_score: number;
  renewal_willingness: number;
  financing_accessibility: number;
  upgrade_progress: number;
  last_action_id: string | null;
}

export interface EnterpriseAction {
  action_id: string;
  enterprise_id: string;
  province_code: string;
  archetype: EnterpriseArchetype;
  phase: Phase;
  participation: Participation;
  upgrade_type: "digital" | "green" | "general" | "none";
  financing_choice:
    | "self_funded"
    | "direct_subsidy"
    | "interest_subsidy"
    | "guarantee_loan"
    | "none";
  investment_intensity: number;
  requested_support: number;
  reason_codes: string[];
  public_summary: string;
}

export interface EnterpriseAggregate {
  province_code: string;
  participation_index: number;
  renewal_willingness_index: number;
  sme_financing_accessibility_index: number;
  industrial_upgrade_index: number;
  participation_counts: Record<Participation, number>;
}

export interface MechanismContribution {
  enterprise_id: string;
  province_code: string;
  phase: Phase;
  policy_match: number;
  direct_subsidy: number;
  interest_subsidy: number;
  financing_guarantee: number;
  sme_preference: number;
  regional_support: number;
  financing_constraint: number;
  fiscal_cost: number;
}

export interface NationalMetrics {
  schema_version: "national-metrics-v2";
  enterprise_participation_index: number;
  equipment_renewal_willingness_index: number;
  sme_financing_accessibility_index: number;
  industrial_upgrade_index: number;
  local_fiscal_pressure_index: number;
  regional_gap_index: number;
}

export type NationalMetricKey = Exclude<keyof NationalMetrics, "schema_version">;

export interface PolicyFieldChange {
  path: string;
  from_value: string | number | boolean | null;
  to_value: string | number | boolean | null;
}

export interface InterventionProposal {
  proposal_id: string;
  proposed_policy: Policy;
  parameter_changes: PolicyFieldChange[];
  target_metrics: string[];
  expected_directions: Record<
    string,
    "increase" | "decrease" | "may_increase" | "may_decrease"
  >;
  tradeoffs: string[];
  evidence_refs: string[];
  public_summary: string;
  approval_status: "draft" | "approved" | "rejected";
}

export interface CentralIntervention {
  intervention_id: string;
  proposal_id: string;
  approved_policy: Policy;
  parameter_changes: PolicyFieldChange[];
  approved_at: string;
  approved_by: "user";
  approval_status: "approved";
}

export interface CentralReview {
  review_id: string;
  review_mode: "comparison" | "single_branch";
  findings: Array<{
    title: string;
    summary: string;
    evidence_refs: string[];
    tradeoff: string | null;
  }>;
  limitations: string[];
  public_summary: string;
}

export interface WorldState {
  schema_version: "world-state-v2";
  experiment_id: string;
  branch_id: string;
  parent_checkpoint_id: string | null;
  phase: Phase;
  status:
    | "draft"
    | "awaiting_approval"
    | "ready"
    | "running"
    | "awaiting_intervention"
    | "completed"
    | "failed";
  run_mode: RunMode;
  policy: Policy;
  directive: CentralDirective;
  national_metrics: NationalMetrics;
  province_profiles: Record<string, ProvinceProfile>;
  province_states: Record<string, ProvinceState>;
  province_actions: Record<string, ProvinceAction>;
  province_feedback: Record<string, ProvinceFeedback>;
  enterprise_profiles: Record<string, EnterpriseGroupProfile>;
  enterprise_states: Record<string, EnterpriseGroupState>;
  enterprise_actions: Record<string, EnterpriseAction>;
  enterprise_aggregates: Record<string, EnterpriseAggregate>;
  contributions: Record<string, MechanismContribution>;
  fallback_provinces: string[];
  intervention_proposals: InterventionProposal[];
  intervention_decision: "approved" | "approved_control_unchanged" | "rejected" | null;
  approved_intervention: CentralIntervention | null;
  central_review: CentralReview | null;
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
  enterprise_participation_delta: number;
  renewal_willingness_delta: number;
  sme_financing_accessibility_delta: number;
  fiscal_pressure_delta: number;
}

export interface ComparisonResult {
  schema_version: "comparison-v2";
  experiment_id: string;
  checkpoint_id: string;
  control_branch_id: string;
  treatment_branch_id: string;
  policy_diff: PolicyFieldChange[];
  national_metrics: Record<NationalMetricKey, MetricDelta>;
  province_deltas: ProvinceDelta[];
  action_migrations: Array<{
    from_participation: Participation;
    to_participation: Participation;
    count: number;
  }>;
  enterprise_group_changes: Array<{
    archetype: EnterpriseArchetype;
    participation_delta: number;
    renewal_willingness_delta: number;
    financing_accessibility_delta: number;
  }>;
  mechanism_totals: Record<string, number>;
  top_improved: string[];
  top_pressured: string[];
  central_review: CentralReview | null;
}

export interface EvidenceRecord {
  evidence_id: string;
  kind: string;
  quality: DataQuality;
  source: string;
  source_url?: string;
  source_year?: number;
  unit?: string;
  transformation?: string;
  missing_value_handling?: string;
  data_version?: string;
  mechanism_version?: string;
  prompt_version?: string;
  model_version?: string;
  app_version?: string;
  seed?: number;
  parent_checkpoint_id?: string | null;
  [key: string]: unknown;
}

export interface SimulationEvent {
  event_id: string;
  type: string;
  experiment_id: string;
  branch_id: string;
  phase: Phase;
  timestamp: string;
  schema_version: "event-v2";
  payload: Record<string, unknown>;
}
