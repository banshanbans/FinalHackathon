import type { PresentationEventCatalog } from "./contracts";
import type {
  M34Configuration,
  M34Draft,
  M34Frame,
  M34Timeline,
  M34World,
  MacroTick,
} from "./m34Contracts";

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
const API_ROOT = configuredBase ? `${configuredBase}/api` : "/api";

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

function conflictGroup(templateId: string) {
  return templateId === "oil_price_rise" || templateId === "oil_price_fall"
    ? "oil-price-direction"
    : null;
}

function designPayload(draft: M34Draft) {
  const { configuration } = draft;
  const treatmentOnly = configuration.events.length > 0
    && configuration.events.every((item) => item.branchScope === "treatment_only");
  const control = {
    policy_id: "control",
    west_central_share: 0.95,
    central_central_share: 0.9,
    east_central_share: 0.85,
  };
  const treatment = treatmentOnly ? { ...control, policy_id: "treatment" } : {
    policy_id: "treatment",
    west_central_share: configuration.westShare,
    central_central_share: configuration.centralShare,
    east_central_share: configuration.eastShare,
  };
  return {
    schema_version: "experiment-design-v2",
    experiment_type: configuration.events.length === 0
      ? "policy_comparison"
      : treatmentOnly ? "event_counterfactual" : "policy_stress_test",
    control_policy: control,
    treatment_policy: treatment,
    event_plans: configuration.events.map((selection) => ({
      schema_version: "event-plan-v2",
      event_plan_id: `event-${selection.template.template_id}-${selection.selectionId}`,
      template_id: selection.template.template_id,
      name: selection.template.title,
      description: selection.template.description,
      conflict_group: conflictGroup(selection.template.template_id),
      scheduled_tick: selection.scheduledTick,
      release_wave: selection.releaseWave,
      branch_scope: selection.branchScope,
      advance_notice: selection.advanceNotice,
      informed_agent_types: selection.advanceNotice ? ["province", "automaker"] : [],
      affected_subjects: selection.template.affected_subjects,
      mechanism_channels: [
        ...selection.template.mechanism_channels,
        ...(selection.template.affected_subjects.includes("consumer") ? ["demand"] : []),
        ...(selection.template.affected_subjects.includes("supply_chain") ? ["industry"] : []),
      ],
      intensity: selection.intensity,
      data_quality: "scenario_assumption",
      evidence_refs: selection.template.provenance_refs,
    })),
    status: "confirmed",
  };
}

export const m34Api = {
  eventCatalog: () => request<PresentationEventCatalog>("/meta/presentation-event-catalog"),
  state: (experimentId: string) => request<M34World>(`/experiments/${experimentId}/state`),
  timeline: (experimentId: string) =>
    request<M34Timeline>(`/experiments/${experimentId}/presentation/timeline`),
  frame: (experimentId: string, frameId: string) =>
    request<M34Frame>(`/experiments/${experimentId}/presentation/frames/${frameId}`),
  streamUrl: (experimentId: string) => `${API_ROOT}/experiments/${experimentId}/stream`,
  run: (experimentId: string, untilTick: MacroTick) => request<M34World>(
    `/experiments/${experimentId}/run`,
    {
      method: "POST",
      headers: { "Idempotency-Key": `m34:run:${experimentId}:${untilTick}` },
      body: JSON.stringify({ until_tick: untilTick }),
    },
  ),
  async createDraft(configuration: M34Configuration): Promise<M34Draft> {
    const created = await request<M34World>("/experiments", {
      method: "POST",
      headers: { "Idempotency-Key": `m34:create:${configuration.operationId}` },
      body: JSON.stringify({
        product_version: "v3_2_m34",
        policy_text: `请评估西部 ${Math.round(configuration.westShare * 100)}%、中部 ${Math.round(configuration.centralShare * 100)}%、东部 ${Math.round(configuration.eastShare * 100)}% 的年度同源方案。`,
        seed: 20260812,
      }),
    });
    return {
      experimentId: created.experiment_id,
      configuration,
      interpretation: created.interpretation,
    };
  },
  confirmInterpretation: (draft: M34Draft) => request<M34World>(
    `/experiments/${draft.experimentId}/interpretation`,
    { method: "PUT", body: JSON.stringify({ ...draft.interpretation, status: "confirmed" }) },
  ),
  confirmDesign: (draft: M34Draft) => request<M34World>(
    `/experiments/${draft.experimentId}/design`,
    { method: "PUT", body: JSON.stringify(designPayload(draft)) },
  ),
  async confirmBaseline(draft: M34Draft) {
    const metadata = await request<{ data_version: string }>("/meta/v32/baseline");
    return request<M34World>(`/experiments/${draft.experimentId}/baseline/confirm`, {
      method: "POST",
      body: JSON.stringify({
        confirm_data_snapshot: true,
        expected_data_version: metadata.data_version,
      }),
    });
  },
};
