import type {
  EventBranchScope,
  EventIntensity,
  EventTriggerPoint,
  PresentationEventCatalog,
  PresentationEventCatalogEntry,
  PresentationFrame,
  PresentationComparison,
  PresentationSummary,
  PresentationTimeline,
  PresentationWorldState,
  SimulationRound,
} from "./contracts";

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
const API_ROOT = configuredBase ? `${configuredBase}/api` : "/api";

export interface DemoInterpretation {
  schema_version: "policy-interpretation-v1";
  interpretation_id: string;
  source_text: string;
  policy_goals: string[];
  target_subjects: string[];
  policy_tools: string[];
  execution_period: string;
  core_constraints: string[];
  ambiguities: string[];
  unmodeled_clauses: string[];
  event_design_hints: string[];
  recommended_metrics: string[];
  public_summary: string;
  status: "awaiting_confirmation" | "confirmed";
  [key: string]: unknown;
}

interface V32State {
  experiment_id: string;
  status: string;
  interpretation: DemoInterpretation;
}

interface DemoPolicy {
  schema_version?: "policy-v4";
  policy_id: string;
  reference_policy_year?: 2025;
  west_central_share: number;
  central_central_share: number;
  east_central_share: number;
  data_quality?: "scenario_assumption";
}

export interface BaselineMetadata {
  data_version: string;
  province_count: number;
  automaker_count: number;
}

export interface DemoConfiguration {
  operationId: string;
  westShare: number;
  centralShare: number;
  eastShare: number;
  event: PresentationEventCatalogEntry | null;
  triggerPoint: EventTriggerPoint;
  intensity: EventIntensity;
  branchScope: EventBranchScope;
  advanceNotice: boolean;
}

export interface DemoDraft {
  experimentId: string;
  configuration: DemoConfiguration;
  interpretation: DemoInterpretation;
}

function policyFromConfiguration(configuration: DemoConfiguration): DemoPolicy {
  return {
    policy_id: "interpreted-treatment",
    west_central_share: configuration.westShare,
    central_central_share: configuration.centralShare,
    east_central_share: configuration.eastShare,
  };
}

function draftedInterpretation(
  interpretation: DemoInterpretation,
  configuration: DemoConfiguration,
): DemoInterpretation {
  return {
    ...interpretation,
    executable_policy: policyFromConfiguration(configuration),
    public_summary: `可执行中央参数为西部 ${Math.round(configuration.westShare * 100)}%、中部 ${Math.round(configuration.centralShare * 100)}%、东部 ${Math.round(configuration.eastShare * 100)}%；其他条款已分类为省级内生决策、事件提示或暂未建模。`,
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as
      | { detail?: { message?: string } | string }
      | null;
    const detail = payload?.detail;
    throw new Error(
      typeof detail === "string" ? detail : detail?.message ?? `请求失败（${response.status}）`,
    );
  }
  return response.json() as Promise<T>;
}

const keyed = (name: string) => ({ "Idempotency-Key": `m33:${name}:${crypto.randomUUID()}` });

function designPayload(draft: DemoDraft) {
  const configuration = draft.configuration;
  const eventCounterfactual = Boolean(
    configuration.event && configuration.branchScope === "treatment_only",
  );
  return {
    experiment_type: configuration.event
      ? configuration.branchScope === "both"
        ? "policy_stress_test"
        : "event_counterfactual"
      : "policy_comparison",
    control_policy: {
      policy_id: "control",
      west_central_share: 0.95,
      central_central_share: 0.9,
      east_central_share: 0.85,
    },
    treatment_policy: {
      policy_id: "treatment",
      west_central_share: eventCounterfactual ? 0.95 : configuration.westShare,
      central_central_share: eventCounterfactual ? 0.9 : configuration.centralShare,
      east_central_share: eventCounterfactual ? 0.85 : configuration.eastShare,
    },
    event_plan: configuration.event ? {
      schema_version: "event-plan-v1",
      event_plan_id: `event-${configuration.event.template_id}-${draft.experimentId}`,
      template_id: configuration.event.template_id,
      name: configuration.event.title,
      description: configuration.event.description,
      trigger_point: configuration.triggerPoint,
      advance_notice: configuration.advanceNotice,
      informed_agent_types: configuration.advanceNotice ? ["province", "automaker"] : [],
      affected_subjects: configuration.event.affected_subjects,
      mechanism_channels: configuration.event.mechanism_channels,
      branch_scope: configuration.branchScope,
      intensity: configuration.intensity,
      data_quality: "scenario_assumption",
      evidence_refs: configuration.event.provenance_refs,
    } : null,
  };
}

export const presentationApi = {
  eventCatalog: () => request<PresentationEventCatalog>("/meta/presentation-event-catalog"),
  timeline: (experimentId: string) =>
    request<PresentationTimeline>(`/experiments/${experimentId}/presentation/timeline`),
  summary: (experimentId: string) =>
    request<PresentationSummary>(`/experiments/${experimentId}/presentation-summary`),
  comparison: (experimentId: string) =>
    request<PresentationComparison>(`/experiments/${experimentId}/compare`),
  state: (experimentId: string) =>
    request<PresentationWorldState>(`/experiments/${experimentId}/state`),
  frame: (experimentId: string, frameId: string) =>
    request<PresentationFrame>(`/experiments/${experimentId}/presentation/frames/${frameId}`),
  streamUrl: (experimentId: string) => `${API_ROOT}/experiments/${experimentId}/stream`,
  run: (experimentId: string, untilRound: SimulationRound) =>
    request(`/experiments/${experimentId}/run`, {
      method: "POST",
      headers: keyed(`run-${untilRound}`),
      body: JSON.stringify({ until_round: untilRound }),
    }),
  async createDemoDraft(configuration: DemoConfiguration): Promise<DemoDraft> {
    const created = await request<V32State>("/experiments", {
      method: "POST",
      headers: { "Idempotency-Key": `m33:create:${configuration.operationId}` },
      body: JSON.stringify({
        policy_text: `请评估将西部、中部、东部中央承担比例调整为 ${Math.round(configuration.westShare * 100)}%、${Math.round(configuration.centralShare * 100)}%、${Math.round(configuration.eastShare * 100)}%，并与 2025 年政策参考基线 95%、90%、85% 对照。`,
        product_version: "v3_2_m32",
        seed: 20260812,
      }),
    });
    return {
      experimentId: created.experiment_id,
      configuration,
      interpretation: draftedInterpretation(created.interpretation, configuration),
    };
  },
  async confirmDemoInterpretation(draft: DemoDraft): Promise<void> {
    await request(`/experiments/${draft.experimentId}/interpretation`, {
      method: "PUT",
      body: JSON.stringify({ ...draft.interpretation, status: "confirmed" }),
    });
  },
  async confirmDemoDesign(draft: DemoDraft): Promise<void> {
    await request(`/experiments/${draft.experimentId}/design`, {
      method: "PUT",
      body: JSON.stringify(designPayload(draft)),
    });
  },
  async baselineMetadata(): Promise<BaselineMetadata> {
    return request<BaselineMetadata>("/meta/v32/baseline");
  },
  async confirmDemoBaseline(draft: DemoDraft): Promise<string> {
    const baseline = await request<BaselineMetadata>("/meta/v32/baseline");
    await request(`/experiments/${draft.experimentId}/baseline/confirm`, {
      method: "POST",
      body: JSON.stringify({
        confirm_data_snapshot: true,
        expected_data_version: baseline.data_version,
      }),
    });
    return draft.experimentId;
  },
};
