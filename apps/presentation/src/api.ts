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

interface V32State {
  experiment_id: string;
  interpretation: Record<string, unknown> & { status: string };
}

interface BaselineMetadata {
  data_version: string;
}

export interface DemoConfiguration {
  event: PresentationEventCatalogEntry;
  triggerPoint: EventTriggerPoint;
  intensity: EventIntensity;
  branchScope: EventBranchScope;
  advanceNotice: boolean;
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
  async createDemo(configuration: DemoConfiguration): Promise<string> {
    const created = await request<V32State>("/experiments", {
      method: "POST",
      headers: keyed("create"),
      body: JSON.stringify({
        policy_text: "西部 95%，中部 90%，东部 85%，促进新能源汽车消费与产业布局。",
        product_version: "v3_2_m32",
        seed: 20260812,
      }),
    });
    await request(`/experiments/${created.experiment_id}/interpretation`, {
      method: "PUT",
      body: JSON.stringify({ ...created.interpretation, status: "confirmed" }),
    });
    await request(`/experiments/${created.experiment_id}/design`, {
      method: "PUT",
      body: JSON.stringify({
        experiment_type: configuration.branchScope === "both"
          ? "policy_stress_test"
          : "event_counterfactual",
        control_policy: {
          policy_id: "control",
          west_central_share: 0.95,
          central_central_share: 0.9,
          east_central_share: 0.85,
        },
        treatment_policy: {
          policy_id: "treatment",
          west_central_share: configuration.branchScope === "both" ? 0.98 : 0.95,
          central_central_share: configuration.branchScope === "both" ? 0.92 : 0.9,
          east_central_share: configuration.branchScope === "both" ? 0.86 : 0.85,
        },
        event_plan: {
          schema_version: "event-plan-v1",
          event_plan_id: `event-${configuration.event.template_id}-${created.experiment_id}`,
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
        },
      }),
    });
    const baseline = await request<BaselineMetadata>("/meta/v32/baseline");
    await request(`/experiments/${created.experiment_id}/baseline/confirm`, {
      method: "POST",
      body: JSON.stringify({
        confirm_data_snapshot: true,
        expected_data_version: baseline.data_version,
      }),
    });
    return created.experiment_id;
  },
};
