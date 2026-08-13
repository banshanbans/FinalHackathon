import type { PresentationEventCatalogEntry } from "./contracts";

export type MacroTick = "Q1" | "Q2" | "Q3" | "Q4";
export type InteractionWave = "wave_0" | "wave_1" | "wave_2";
export type BranchScope = "both" | "treatment_only";
export type BranchView = "control" | "treatment" | "delta";

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

export interface M34Policy {
  policy_id: string;
  west_central_share: number;
  central_central_share: number;
  east_central_share: number;
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
  branches: Partial<Record<"control" | "treatment", {
    completed_ticks: MacroTick[];
  }>>;
  central_call_count: number;
  central_review: string | null;
  versions: Record<string, string>;
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
  schema_version: "presentation-timeline-v3";
  experiment_id: string;
  product_version: "v3_2_m34";
  status: string;
  current_node_id: string;
  nodes: M34TimelineNode[];
  completed_ticks: MacroTick[];
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

export interface M34Frame {
  schema_version: "presentation-frame-v3";
  frame_id: string;
  experiment_id: string;
  sequence: number;
  kind: M34TimelineNode["kind"];
  tick: MacroTick | null;
  wave: InteractionWave | null;
  title: string;
  summary: string;
  disclaimer: string;
  branches: Record<"control" | "treatment", {
    branch_id: string;
    tick: MacroTick | null;
    national_metrics: NationalMetrics;
    checkpoint_id: string | null;
  }>;
  province_values: Array<{
    province_code: string;
    control: number | null;
    treatment: number | null;
    delta: number | null;
  }>;
  interactions: M34Interaction[];
  spotlight_session_ids: string[];
  event_plan_ids: string[];
  evidence_refs: string[];
  source_hash: string;
}

export interface M34Interaction {
  session_id: string;
  branch_id: string;
  tick: MacroTick;
  participants: string[];
  state: string;
  message_count: number;
  summary: string;
  fallback: boolean;
}

export interface M34InteractionMarket {
  schema_version: "interaction-market-v1";
  messages: Array<{
    message_id: string;
    branch_id: string;
    tick: MacroTick;
    wave: InteractionWave;
    kind: string;
    sender_id: string;
    recipient_ids: string[];
    transaction_state: string;
    public_summary: string;
  }>;
  sessions: M34Interaction[];
  fallback_count: number;
  budget_exhausted: boolean;
}

export interface M34Draft {
  experimentId: string;
  configuration: M34Configuration;
  interpretation: M34Interpretation;
}
