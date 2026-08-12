export type Phase = "T0" | "T1" | "T2" | "T3" | "T4" | "T5";
export type RunMode = "live" | "cache" | "fake" | "fallback";
export type DataQuality = "verified" | "proxy" | "demo";
export type Participation = "participate" | "conditional" | "wait" | "decline";
export type ProvincePersonaType =
  | "execution_driven"
  | "fiscally_prudent"
  | "inclusive_diffusion"
  | "technology_leap"
  | "green_transition"
  | "regional_collaboration";
export type ProvincePriorityGoal =
  | "equipment_renewal"
  | "fiscal_sustainability"
  | "sme_financing_access"
  | "digital_upgrade"
  | "green_equipment_renewal"
  | "cross_regional_coordination";
export type ProvinceConstraint =
  | "fiscal_gap"
  | "financing_gap"
  | "transition_pressure"
  | "weak_digital_base"
  | "employment_pressure"
  | "industrial_concentration";
export type DecisionPosture = "proactive" | "balanced" | "cautious";
export type InterprovincialStrategy =
  | "collaborate"
  | "benchmark"
  | "compete"
  | "independent";
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
  schema_version: "province-profile-v3";
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
  rd_capacity: number;
  employment_pressure: number;
  cooperation_tendency: number;
  data_quality: DataQuality;
  source_year: number;
}

export interface ProvincePersonaAxes {
  execution_drive: number;
  fiscal_prudence: number;
  sme_inclusiveness: number;
  technology_ambition: number;
  green_priority: number;
  cooperation_orientation: number;
}

export interface ProvinceDecisionPersona {
  schema_version: "province-persona-v1";
  province_code: string;
  axes: ProvincePersonaAxes;
  primary_type: ProvincePersonaType;
  secondary_type: ProvincePersonaType | null;
  priority_goals: ProvincePriorityGoal[];
  key_constraints: ProvinceConstraint[];
  profile_version: string;
  network_version: string;
  method_version: string;
  data_quality: "proxy" | "demo";
  public_summary: string;
}

export interface ProvincePersonaTypeDefinition {
  type: ProvincePersonaType;
  display_name: string;
  axis: keyof ProvincePersonaAxes;
  priority_goal: ProvincePriorityGoal;
  visible_label: "本次实验决策画像";
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
  schema_version: "province-action-v3";
  action_id: string;
  previous_action_id: string | null;
  province_code: string;
  phase: Phase;
  primary_goal: ProvincePriorityGoal;
  decision_posture: DecisionPosture;
  target_enterprise_groups: EnterpriseArchetype[];
  interprovincial_strategy: InterprovincialStrategy;
  target_province_codes: string[];
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

export interface EnterpriseSignal {
  cohort_type: EnterpriseArchetype;
  signal_type:
    | "participation_barrier"
    | "financing_constraint"
    | "upgrade_mismatch"
    | "support_demand";
  severity: "low" | "medium" | "high";
  evidence_refs: string[];
}

export interface AdjustmentIntent {
  path: string;
  direction: "increase" | "decrease" | "hold";
  reason_code: string;
}

export interface ProvinceFeedback {
  schema_version: "province-feedback-v3";
  feedback_id: string;
  province_code: string;
  phase: "T3";
  strategy_assessment: "effective" | "mixed" | "constrained";
  enterprise_signals: EnterpriseSignal[];
  priority_enterprise_groups: EnterpriseArchetype[];
  key_constraints: ProvinceConstraint[];
  adjustment_intents: AdjustmentIntent[];
  requested_support_type:
    | "none"
    | "fiscal_space"
    | "credit_support"
    | "guarantee_capacity"
    | "technical_service"
    | "regional_coordination";
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
  schema_version: "world-state-v3";
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
  province_personas: Record<string, ProvinceDecisionPersona>;
  province_states: Record<string, ProvinceState>;
  province_actions: Record<string, ProvinceAction>;
  province_action_lineage: Record<string, ProvinceAction[]>;
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
  schema_version: "comparison-v3";
  experiment_id: string;
  checkpoint_id: string;
  control_branch_id: string;
  treatment_branch_id: string;
  policy_diff: PolicyFieldChange[];
  national_metrics: Record<NationalMetricKey, MetricDelta>;
  province_strategy_transitions: ProvinceStrategyTransition[];
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

export interface ProvinceStrategyTransition {
  province_code: string;
  province_name: string;
  persona_primary_type: ProvincePersonaType;
  control_action_id: string;
  treatment_action_id: string;
  changed: boolean;
  changes: Array<{
    path: string;
    from_value: unknown;
    to_value: unknown;
  }>;
}

export interface ProvinceNeighbor {
  province_code: string;
  province_name: string;
  weight: number;
}

export interface ProvinceEnterpriseEvidence {
  profile: EnterpriseGroupProfile;
  state: EnterpriseGroupState | null;
  action: EnterpriseAction | null;
  contribution: MechanismContribution | null;
}

export interface ProvinceAgentBranchSnapshot {
  branch_id: string;
  branch_kind: "control" | "treatment";
  phase: Phase;
  state: ProvinceState;
  current_action: ProvinceAction | null;
  action_lineage: ProvinceAction[];
  feedback: ProvinceFeedback | null;
  enterprise_groups: ProvinceEnterpriseEvidence[];
  mechanism_summary: Record<string, number>;
  evidence_refs: string[];
}

export interface ProvinceAgentDetail {
  schema_version: "province-agent-detail-v1";
  experiment_id: string;
  province_code: string;
  profile: ProvinceProfile;
  persona: ProvinceDecisionPersona;
  top_k_neighbors: ProvinceNeighbor[];
  branches: Partial<Record<"control" | "treatment", ProvinceAgentBranchSnapshot>>;
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
  audit_chain_valid?: boolean;
  audit_record?: AuditRecord;
  audit_records?: AuditRecord[];
  [key: string]: unknown;
}

export type AuditRecordType =
  | "agent_invocation"
  | "mechanism_explanation"
  | "decision_gate";

export interface ProviderAttemptTrace {
  attempt: number;
  status: "succeeded" | "validation_error" | "provider_error";
  latency_ms: number;
  error_code: string | null;
  validation_paths: string[];
  invalid_response_hash: string | null;
}

export interface AgentInvocationTrace {
  kind: "agent_invocation";
  actor_kind: string;
  actor_id: string;
  operation: string;
  run_mode: string;
  model: string;
  prompt_version: string;
  response_schema: string;
  input_hash: string;
  input_snapshot: unknown;
  attempts: ProviderAttemptTrace[];
  usage: {
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
  } | null;
  latency_ms: number;
  outcome: string;
  output_ids: string[];
  output_hash: string;
  output_snapshot: unknown;
  cache_key_hash: string | null;
  fallback_reason: string | null;
}

export interface MechanismExplanationTrace {
  kind: "mechanism_explanation";
  explanation_id: string;
  scope: "enterprise" | "province" | "national" | "comparison";
  subject_id: string;
  metric: string;
  formula_id: string;
  formula_version: string;
  source_refs: string[];
  terms: Array<{
    name: string;
    input_value: number;
    coefficient: number;
    contribution: number;
    source_ref: string | null;
  }>;
  previous_value: number | null;
  raw_value: number;
  clamp_min: number;
  clamp_max: number;
  clamp_adjustment: number;
  final_value: number;
  residual: number;
  unit: string;
}

export interface DecisionGateTrace {
  kind: "decision_gate";
  actor_kind: string;
  actor_id: string;
  operation: string;
  outcome: string;
  object_ids: string[];
  details: Record<string, unknown>;
}

export interface AuditRecord {
  schema_version: "audit-record-v1";
  record_id: string;
  sequence: number;
  experiment_id: string;
  branch_id: string;
  phase: Phase;
  timestamp: string;
  parent_record_ids: string[];
  previous_record_hash: string | null;
  record_hash: string;
  payload: AgentInvocationTrace | MechanismExplanationTrace | DecisionGateTrace;
}

export interface AuditListResponse {
  schema_version: "audit-list-v1";
  records: AuditRecord[];
  next_sequence: number | null;
}

export interface SimulationEvent {
  event_id: string;
  type: string;
  experiment_id: string;
  branch_id: string;
  phase: Phase;
  timestamp: string;
  schema_version: "event-v3";
  payload: Record<string, unknown>;
}
