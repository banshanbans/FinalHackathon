export type PresentationMode = "live" | "story" | "compare";
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
  schema_version: "presentation-overlay-record-v1";
  overlay_id: string;
  kind: PresentationOverlayKind;
  source_subject: string;
  target_subject: string | null;
  status: string;
  weight: number | null;
  label: string;
  style_semantic: "policy" | "evidence" | "event" | "competition" | "coordination" | "neutral";
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

export interface PresentationFrame {
  schema_version: "presentation-frame-v1";
  frame_id: string;
  sequence: number;
  kind: PresentationFrameKind;
  branch_id: string | null;
  round: SimulationRound | null;
  title: string;
  summary: string;
  frozen: true;
  map_projection: PresentationMapProjection;
  province_values: PresentationProvinceValue[];
  overlay_records: PresentationOverlayRecord[];
  key_changes: PresentationKeyChange[];
  metric_summary: PresentationMetricSummary[];
  focus_subjects: string[];
  panel_refs: string[];
  evidence_refs: string[];
  source_event_ids: string[];
  source_hash: string;
}

export interface PresentationEventMarker {
  schema_version: "presentation-event-marker-v1";
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

export interface PresentationStoryChapter {
  chapter_id: string;
  title: string;
  summary: string;
  frame_ids: string[];
  evidence_refs: string[];
}

export interface PresentationTimeline {
  schema_version: "presentation-timeline-v1";
  experiment_id: string;
  product_version: string;
  status: string;
  current_frame_id: string;
  frames: PresentationFrame[];
  event_markers: PresentationEventMarker[];
  story_chapters: PresentationStoryChapter[];
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
  branches: Record<"control" | "treatment", {
    branch_id: string;
    label: string;
    province_states: Record<string, {
      province_code: string;
      development_index: number;
    }>;
  }>;
}
