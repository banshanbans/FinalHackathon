export type PresentationMode = "live" | "compare";
export type PresentationFrameKind = "setup" | "round" | "event" | "settlement" | "comparison";
export type SimulationRound = "province_initial" | "automaker_initial" | "province_revision" | "automaker_negotiation" | "province_counter_response" | "automaker_final" | "environment_settlement";
export type PresentationOverlayKind = "competition" | "negotiation" | "coordination" | "topk" | "event" | "automaker";
export type EventTriggerPoint = "before_province_initial" | "after_province_initial" | "after_automaker_initial";
export type EventIntensity = "low" | "medium" | "high";
export type EventBranchScope = "both" | "treatment_only";
export type EventAffectedSubject = "province" | "automaker" | "consumer" | "supply_chain";

export interface PresentationCamera {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
}

export interface PresentationMapProjection {
  mode: "absolute" | "difference";
  fill_metric: string;
  unit: string;
  camera: PresentationCamera;
  enabled_overlays: PresentationOverlayKind[];
}

export interface PresentationProvinceValue {
  province_code: string;
  value: number | null;
  missing: boolean;
  data_quality: "verified" | "proxy" | "scenario_assumption";
}

export interface PresentationOverlayRecord {
  schema_version: "presentation-overlay-record-v2";
  overlay_id: string;
  kind: PresentationOverlayKind;
  source_subject: string;
  target_subject: string | null;
  status: string;
  weight: number | null;
  label: string;
  style_semantic: "policy" | "evidence" | "event" | "competition" | "coordination" | "neutral";
  evidence_refs: string[];
  relation_semantic?: "proposal" | "counteroffer" | "accepted" | "settled" | "rejected" | "deferred" | "invalid" | "event_impact";
  line_style?: "solid" | "dashed" | "thick" | "faded" | "pulse";
  emphasized?: boolean;
  session_id?: string | null;
  reveal_order?: number;
  message_order?: number;
}

export type BranchRole = "control" | "treatment";

export interface PresentationSubjectRef {
  subject_type: "province" | "automaker" | "event" | "policy" | "environment";
  subject_id: string;
  display_name: string;
}

export interface PresentationScoreComponent {
  component: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
  direction: "benefit" | "cost";
}

export interface PresentationOptionParameter {
  parameter: string;
  label: string;
  value: number;
  unit: string;
}

export interface DecisionOptionEvaluation {
  schema_version: "decision-option-evaluation-v1";
  option_id: string;
  label: string;
  option_type: "chosen" | "maintain" | "policy_shift" | "accept" | "reject" | "counteroffer" | "reallocate" | "no_action";
  feasible: boolean;
  infeasible_reasons: string[];
  score: number | null;
  delta_from_chosen: number | null;
  components: PresentationScoreComponent[];
  parameters: PresentationOptionParameter[];
  assumptions: string[];
  evidence_refs: string[];
}

export interface PresentationObservedSignal {
  source: PresentationSubjectRef;
  signal: string;
  evidence_refs: string[];
}

export interface PresentationActualResponse {
  response_id: string;
  actor: PresentationSubjectRef;
  action: string;
  status: string;
  evidence_refs: string[];
}

export interface PresentationDecisionMoment {
  schema_version: "presentation-decision-moment-v1";
  moment_id: string;
  trace_id: string;
  branch_role: BranchRole;
  branch_id: string;
  round: SimulationRound;
  actor: PresentationSubjectRef;
  objective: string;
  constraints: string[];
  observed_signals: PresentationObservedSignal[];
  actual_choice: string;
  action_changes: string[];
  recorded_alternatives: string[];
  rejected_alternatives: string[];
  opportunity_costs: string[];
  change_conditions: string[];
  option_evaluations: DecisionOptionEvaluation[];
  response_status: "not_applicable" | "pending" | "responded" | "settled";
  actual_responses: PresentationActualResponse[];
  affected_subjects: PresentationSubjectRef[];
  fallback_used: boolean;
  evidence_refs: string[];
}

export interface PresentationThreadBeat {
  beat_id: string;
  round: SimulationRound;
  label: string;
  status: "frozen" | "pending";
  subject: PresentationSubjectRef | null;
  fact_ref: string | null;
}

export interface PresentationGameThread {
  schema_version: "presentation-game-thread-v1";
  thread_id: string;
  branch_role: BranchRole;
  thread_type: "policy_response" | "competition" | "coordination" | "negotiation" | "topk" | "settlement";
  title: string;
  participants: PresentationSubjectRef[];
  resource_subject: PresentationSubjectRef | null;
  state: "action_frozen" | "awaiting_response" | "response_frozen" | "matched" | "rejected" | "settled";
  moment_ids: string[];
  beats: PresentationThreadBeat[];
  evidence_refs: string[];
}

export interface PresentationDivergence {
  schema_version: "presentation-divergence-v1";
  divergence_id: string;
  subject: PresentationSubjectRef;
  round: SimulationRound;
  dimension: "choice" | "action" | "target" | "response" | "topk" | "utility" | "result";
  control_summary: string;
  treatment_summary: string;
  magnitude: number;
  first_for_subject: boolean;
  evidence_refs: string[];
}

export interface PresentationSpotlightScore {
  divergence: number;
  response: number;
  scarcity: number;
  action_change: number;
  state_change: number;
  evidence: number;
  total: number;
}

export interface PresentationNarrativeBeat {
  beat: "focus" | "observe" | "options" | "action" | "response" | "tradeoff";
  title: string;
  detail: string;
  status: "frozen" | "pending";
}

export interface PresentationSpotlight {
  schema_version: "presentation-spotlight-v1";
  spotlight_id: string;
  rank: 1 | 2 | 3;
  label: string;
  primary_moment_id: string;
  thread_id: string | null;
  branch_role: BranchRole;
  score: PresentationSpotlightScore;
  narrative_beats: PresentationNarrativeBeat[];
  focus_subjects: PresentationSubjectRef[];
  evidence_refs: string[];
}

export interface PresentationKeyChange {
  change_id: string;
  title: string;
  detail: string;
  semantic: "policy" | "event" | "competition" | "negotiation" | "coordination" | "result";
  evidence_refs: string[];
}

export interface PresentationMetricSummary {
  metric_id: string;
  label: string;
  value: number;
  unit: string;
  delta: number | null;
  evidence_refs: string[];
}

export interface PresentationBranchProjection {
  schema_version: "presentation-branch-projection-v2";
  branch_role: "shared" | BranchRole;
  branch_id: string | null;
  label: string;
  map_projection: PresentationMapProjection;
  province_values: PresentationProvinceValue[];
  overlay_records: PresentationOverlayRecord[];
  key_changes: PresentationKeyChange[];
  metric_summary: PresentationMetricSummary[];
  evidence_refs: string[];
  source_event_ids: string[];
  source_hash: string;
}

export interface PresentationMapFrame extends PresentationBranchProjection {
  frame_id: string;
  sequence: number;
  kind: PresentationFrameKind;
  round: SimulationRound | null;
  title: string;
  summary: string;
}

export interface PresentationFrame {
  schema_version: "presentation-frame-v2";
  frame_id: string;
  sequence: number;
  kind: PresentationFrameKind;
  round: SimulationRound | null;
  title: string;
  summary: string;
  frozen: true;
  shared_projection: PresentationBranchProjection | null;
  branch_projections: Partial<Record<BranchRole, PresentationBranchProjection>>;
  difference_projection: PresentationBranchProjection | null;
  decision_moments: PresentationDecisionMoment[];
  interaction_threads: PresentationGameThread[];
  divergences: PresentationDivergence[];
  spotlights: PresentationSpotlight[];
  panel_refs: string[];
  evidence_refs: string[];
  source_event_ids: string[];
  source_hash: string;
}

export interface PresentationEventMarker {
  schema_version: "presentation-event-marker-v2";
  marker_id: string;
  event_plan_id: string;
  template_id: string;
  title: string;
  family: string;
  intensity: EventIntensity;
  trigger_point: EventTriggerPoint;
  timeline_position: number;
  branch_scope: EventBranchScope;
  advance_notice: boolean;
  affected_subjects: EventAffectedSubject[];
  mechanism_channels: string[];
  evidence_refs: string[];
  source_hash: string;
}

export interface PresentationEventCatalogEntry {
  schema_version: "presentation-event-catalog-entry-v1";
  template_id: string;
  catalog_version: "presentation-event-catalog-v1";
  family: string;
  title: string;
  description: string;
  trigger_points: EventTriggerPoint[];
  affected_subjects: EventAffectedSubject[];
  mechanism_channels: string[];
  supported_intensities: EventIntensity[];
  branch_scopes: EventBranchScope[];
  advance_notice_supported: boolean;
  provenance_refs: string[];
  mechanism_version: "nev-policy-env-v6";
  data_quality: "scenario_assumption";
  disclaimer: string;
}

export interface PresentationEventCatalog {
  schema_version: "presentation-event-catalog-v1";
  catalog_version: "presentation-event-catalog-v1";
  mechanism_version: "nev-policy-env-v6";
  templates: PresentationEventCatalogEntry[];
}

export interface PresentationFrameIndex {
  schema_version: "presentation-frame-index-v2";
  frame_id: string;
  sequence: number;
  kind: PresentationFrameKind;
  round: SimulationRound | null;
  title: string;
  spotlight_count: number;
  divergence_count: number;
  projection_roles: Array<"shared" | BranchRole>;
  source_hash: string;
}

export interface PresentationTimeline {
  schema_version: "presentation-timeline-v2";
  experiment_id: string;
  product_version: string;
  status: string;
  current_frame_id: string;
  frames: PresentationFrameIndex[];
  event_markers: PresentationEventMarker[];
  first_divergence_frame_id: string | null;
  available_modes: PresentationMode[];
  source_world_hash: string;
  generated_at: string;
}

export interface PresentationScene {
  scene: "policy_input" | "enterprise_feedback" | "province_coordination" | "resource_reallocation" | "policy_conclusion";
  title: string;
  summary: string;
  evidence_refs: string[];
}

export interface PresentationSummary {
  schema_version: "presentation-summary-v1";
  experiment_id: string;
  scenes: PresentationScene[];
}

export interface MetricComparison {
  control: number;
  treatment: number;
  delta: number;
}

export interface MechanismNode {
  node_type: "policy" | "agent_action" | "coordination_match" | "environment" | "metric";
  ref: string;
  label: string;
  contribution: number | null;
}

export interface MechanismChain {
  category: "positive" | "cost" | "reversal_risk";
  title: string;
  nodes: MechanismNode[];
  contribution_delta: number;
  evidence_refs: string[];
}

export interface PresentationComparison {
  schema_version: "comparison-v9";
  experiment_id: string;
  conclusion: string;
  gap_direction: "narrowed" | "widened" | "unchanged";
  delta_gap: number;
  national_metrics: Record<string, MetricComparison>;
  top_beneficiaries: string[];
  top_pressured: string[];
  fiscal_tradeoff: string;
  event_robustness: string;
  mechanism_chains: MechanismChain[];
  active_difference: "policy" | "event";
  same_policy: boolean;
  same_event: boolean;
}

export interface PresentationWorldState {
  schema_version: "world-state-v9";
  versions: Record<string, string>;
  design: {
    control_policy: {
      west_central_share: number;
      central_central_share: number;
      east_central_share: number;
    };
    treatment_policy: {
      west_central_share: number;
      central_central_share: number;
      east_central_share: number;
    };
  } | null;
  branches: Record<"control" | "treatment", {
    branch_id: string;
    label: string;
    province_states: Record<string, {
      province_code: string;
      development_index: number;
    }>;
  }>;
}
