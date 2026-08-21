import type { PresentationEventCatalogEntry } from "./contracts";

export type MacroTick = "Q1" | "Q2" | "Q3" | "Q4";
export type InteractionWave = "wave_0" | "wave_1" | "wave_2";
export type BranchScope = "both" | "treatment_only";
export type BranchView = "control" | "treatment" | "delta";
export type CausalBeatId = "focus" | "observe" | "decide" | "action" | "response" | "settle";
export type PresentationWorldLandmarkKind = "battery_capability" | "industrial_facility";

export interface PresentationWorldLandmark {
  schema_version: "presentation-world-landmark-v1";
  landmark_id: string;
  kind: PresentationWorldLandmarkKind;
  province_code: string;
  province_name: string;
  node_count: number;
  node_names: string[];
  data_quality: "proxy";
}

export interface PresentationWorldLandmarks {
  schema_version: "presentation-world-landmarks-v1";
  items: PresentationWorldLandmark[];
}

export interface M34EventSelection {
  selectionId: string;
  template: PresentationEventCatalogEntry;
  scheduledTick: MacroTick;
  releaseWave: InteractionWave;
  branchScope: BranchScope;
  intensity: "low" | "medium" | "high";
  advanceNotice: boolean;
}

export interface M34Configuration {
  operationId: string;
  westShare: number;
  centralShare: number;
  eastShare: number;
  events: M34EventSelection[];
}

export interface M34Policy {
  policy_id: string;
  west_central_share: number;
  central_central_share: number;
  east_central_share: number;
  [key: string]: unknown;
}

export interface M34Interpretation {
  interpretation_id: string;
  source_text: string;
  policy_goals: string[];
  policy_tools: string[];
  recommended_metrics: string[];
  ambiguities: string[];
  public_summary: string;
  status: "awaiting_confirmation" | "confirmed";
  executable_policy: M34Policy;
  [key: string]: unknown;
}

export interface M34World {
  schema_version: "world-state-v10";
  product_version: "v3_2_m34";
  experiment_id: string;
  status: string;
  interpretation: M34Interpretation;
  design: {
    experiment_type: "policy_comparison" | "policy_stress_test" | "event_counterfactual";
    control_policy: M34Policy;
    treatment_policy: M34Policy;
    event_plans: Array<{
      event_plan_id: string;
      template_id: string;
      name: string;
      scheduled_tick: MacroTick;
      release_wave: InteractionWave;
      branch_scope: BranchScope;
    }>;
  } | null;
  branches: Partial<Record<"control" | "treatment", { completed_ticks: MacroTick[] }>>;
  central_call_count: number;
  central_review: string | null;
  versions: Record<string, string>;
}

export interface SharedScale {
  metric_id: string;
  absolute_min: number;
  absolute_max: number;
  difference_bound: number;
  low_label: string;
  midpoint_label: string;
  high_label: string;
}

export interface M34TimelineNode {
  node_id: string;
  sequence: number;
  kind: "policy" | "event" | "wave" | "settlement" | "comparison";
  tick: MacroTick | null;
  wave: InteractionWave | null;
  title: string;
  timeline_position: number;
  interaction_count: number;
  fallback_count: number;
  source_event_ids: string[];
  source_hash: string;
}

export interface M34Timeline {
  schema_version: "presentation-timeline-v4";
  experiment_id: string;
  product_version: "v3_2_m34";
  status: string;
  current_node_id: string;
  nodes: M34TimelineNode[];
  completed_ticks: MacroTick[];
  shared_scale: SharedScale;
  disclaimer: string;
  source_world_hash: string;
}

export interface NationalMetrics {
  regional_development_gap: number;
  central_fiscal_burden: number;
  local_fiscal_pressure: number;
  nev_demand: number;
  new_investment_concentration: number;
  industrial_agglomeration: number;
}

export interface PresentationSubjectV4 {
  subject_ref: string;
  subject_type: "province" | "automaker" | "event" | "environment";
  subject_id: string;
  display_name: string;
}

export interface PresentationCausalBeatV4 {
  beat: CausalBeatId;
  label: string;
  headline: string;
  detail: string;
  status: "completed" | "active" | "pending" | "not_applicable";
}

export interface PresentationActionV4 {
  kind: string;
  label: string;
  summary: string;
  state: string;
  state_label: string;
  message_id: string | null;
}

export interface PresentationMetricChangeV5 {
  metric_id: "regional_development_gap" | "local_fiscal_pressure";
  label: string;
  current_value: number;
  quarterly_change: number | null;
}

export interface PresentationProvinceChangeV5 {
  province_code: string;
  province_name: string;
  current_value: number;
  quarterly_change: number | null;
}

export interface PresentationSettlementV5 {
  contributed: boolean;
  contribution: number;
  result_summary: string;
  direct_contribution_label: string;
  province_changes: PresentationProvinceChangeV5[];
  national_changes: PresentationMetricChangeV5[];
  attribution_note: string;
}

export interface PresentationSpotlightV5 {
  spotlight_id: string;
  branch_id: "control" | "treatment";
  tick: MacroTick;
  wave: InteractionWave;
  session_id: string;
  actor: PresentationSubjectV4;
  counterpart: PresentationSubjectV4;
  objective: string;
  strongest_constraint: string;
  observed_facts: string[];
  engagement_label: string;
  decision_summary: string;
  alternatives: string[];
  opportunity_costs: string[];
  reconsideration_conditions: string[];
  action: PresentationActionV4;
  response: PresentationActionV4 | null;
  settlement: PresentationSettlementV5;
  beats: PresentationCausalBeatV4[];
  fallback: boolean;
  evidence_refs: string[];
}

export type PresentationSpotlightV4 = PresentationSpotlightV5;

export interface PresentationGameEdgeV5 {
  edge_id: string;
  branch_id: "control" | "treatment";
  source: PresentationSubjectV4;
  target: PresentationSubjectV4;
  relation: "proposal" | "counteroffer" | "accepted" | "settled" | "rejected" | "deferred" | "invalid" | "event_impact";
  relation_label: string;
  line_style: "solid" | "dashed" | "thick" | "faded" | "pulse";
  weight: number;
  summary: string;
  session_id: string | null;
  reveal_order: number;
  message_order: number;
  evidence_refs: string[];
}

export interface M34BranchFrame {
  branch_id: "control" | "treatment";
  label: string;
  tick: MacroTick | null;
  national_metrics: NationalMetrics;
  province_values: Array<{ province_code: string; value: number | null }>;
  game_edges: PresentationGameEdgeV5[];
  spotlights: PresentationSpotlightV5[];
  fallback_count: number;
}

export interface M34Frame {
  schema_version: "presentation-frame-v5";
  frame_id: string;
  experiment_id: string;
  sequence: number;
  kind: M34TimelineNode["kind"];
  tick: MacroTick | null;
  wave: InteractionWave | null;
  chapter_label: string;
  question: string;
  title: string;
  summary: string;
  wave_label: string | null;
  branches: Record<"control" | "treatment", M34BranchFrame>;
  divergences: Array<{
    divergence_id: string;
    divergence_type: "control_only" | "treatment_only" | "state_changed" | "decision_changed";
    participants: PresentationSubjectV4[];
    control_state_label: string;
    treatment_state_label: string;
    control_decision_summary: string;
    treatment_decision_summary: string;
    summary: string;
  }>;
  shared_scale: SharedScale;
  event_plan_ids: string[];
  disclaimer: string;
  evidence_refs: string[];
  source_hash: string;
}

export interface M34Draft {
  experimentId: string;
  configuration: M34Configuration;
  interpretation: M34Interpretation;
}
