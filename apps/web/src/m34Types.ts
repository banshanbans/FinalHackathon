export type MacroTick = "Q1" | "Q2" | "Q3" | "Q4";
export type InteractionWave = "wave_0" | "wave_1" | "wave_2";

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
  public_summary: string;
  policy_goals: string[];
  policy_tools: string[];
  recommended_metrics: string[];
  status: "awaiting_confirmation" | "confirmed";
  executable_policy: M34Policy;
  [key: string]: unknown;
}

export interface M34EventPlan {
  schema_version: "event-plan-v2";
  event_plan_id: string;
  template_id: string;
  name: string;
  description: string;
  conflict_group: string | null;
  scheduled_tick: MacroTick;
  release_wave: InteractionWave;
  branch_scope: "both" | "treatment_only";
  advance_notice: boolean;
  informed_agent_types: Array<"province" | "automaker">;
  affected_subjects: Array<"province" | "automaker" | "consumer" | "supply_chain">;
  mechanism_channels: string[];
  intensity: "low" | "medium" | "high";
  data_quality: "scenario_assumption";
  evidence_refs: string[];
}

export interface M34Design {
  schema_version: "experiment-design-v2";
  experiment_type: "policy_comparison" | "policy_stress_test" | "event_counterfactual";
  control_policy: M34Policy;
  treatment_policy: M34Policy;
  event_plans: M34EventPlan[];
  status: "confirmed";
}

export interface NationalMetricsM34 {
  regional_development_gap: number;
  central_fiscal_burden: number;
  local_fiscal_pressure: number;
  nev_demand: number;
  new_investment_concentration: number;
  industrial_agglomeration: number;
}

export interface M34World {
  schema_version: "world-state-v10";
  product_version: "v3_2_m34";
  experiment_id: string;
  status: string;
  interpretation: M34Interpretation;
  design: M34Design | null;
  baseline: { data_version: string; checkpoint_id: string } | null;
  branches: Partial<Record<"control" | "treatment", {
    branch_id: string;
    label: string;
    completed_ticks: MacroTick[];
    national_metrics: NationalMetricsM34;
  }>>;
  central_call_count: number;
  central_review: string | null;
  versions: Record<string, string>;
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
  settled_count: number;
  fallback_count: number;
  budget_exhausted: boolean;
}

export interface M34Comparison {
  schema_version: "comparison-v10";
  delta_gap: number;
  gap_direction: "narrowed" | "widened" | "unchanged";
  conclusion: string;
  central_review: string;
  active_difference: "policy" | "event";
  same_policy: boolean;
  same_event: boolean;
  fallback_count: number;
  national_metrics: Record<string, { control: number; treatment: number; delta: number }>;
}

export interface M34EventTemplate {
  template_id: string;
  title: string;
  description: string;
  affected_subjects: M34EventPlan["affected_subjects"];
  mechanism_channels: string[];
  provenance_refs: string[];
}
