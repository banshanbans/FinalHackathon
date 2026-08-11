import type {
  Branch,
  CentralIntervention,
  ComparisonResult,
  EnterpriseArchetypeDefinition,
  EvidenceRecord,
  Policy,
  ProvinceProfile,
  RunMode,
  WorldState,
} from "../types";

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
  /\/$/,
  "",
);
const API_ROOT = configuredBase ? `${configuredBase}/api` : "/api";

export class ApiError extends Error {
  status: number;
  errorCode: string;

  constructor(status: number, errorCode: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

function idempotencyKey(operation: string) {
  return `${operation}:${crypto.randomUUID()}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: { error_code?: string; message?: string } | string;
    } | null;
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ?? `请求失败（${response.status}）`;
    const code = typeof detail === "object" ? detail?.error_code ?? "REQUEST_FAILED" : "REQUEST_FAILED";
    throw new ApiError(response.status, code, message);
  }
  return response.json() as Promise<T>;
}

const keyed = (operation: string): HeadersInit => ({
  "Idempotency-Key": idempotencyKey(operation),
});

export const policyScopeApi = {
  health: () =>
    request<{ status: string; runtime: string; run_mode: RunMode; version: string }>(
      "/health",
    ),

  listProvinces: () => request<ProvinceProfile[]>("/meta/provinces"),

  listEnterpriseArchetypes: () =>
    request<EnterpriseArchetypeDefinition[]>("/meta/enterprise-archetypes"),

  defaultPolicy: () => request<Policy>("/meta/default-policy"),

  createExperiment: (objective: string, runMode: RunMode) =>
    request<WorldState>("/experiments", {
      method: "POST",
      headers: keyed("create-experiment"),
      body: JSON.stringify({ objective, run_mode: runMode }),
    }),

  getState: (experimentId: string, branchId = "control") =>
    request<WorldState>(
      `/experiments/${experimentId}/state?branch_id=${encodeURIComponent(branchId)}`,
    ),

  approveDirective: (experimentId: string, policy: Policy) =>
    request<WorldState>(`/experiments/${experimentId}/directive/approve`, {
      method: "POST",
      headers: keyed("approve-directive"),
      body: JSON.stringify({ policy }),
    }),

  runExperiment: (experimentId: string, phase: "T3" | "T5", branchId = "control") =>
    request<WorldState>(`/experiments/${experimentId}/run`, {
      method: "POST",
      headers: keyed(`run-${branchId}-${phase}`),
      body: JSON.stringify({ until_phase: phase, branch_id: branchId }),
    }),

  approveIntervention: (experimentId: string, proposalId: string, policy: Policy) =>
    request<CentralIntervention>(
      `/experiments/${experimentId}/interventions/${proposalId}/approve`,
      {
        method: "POST",
        headers: keyed("approve-intervention"),
        body: JSON.stringify({ policy }),
      },
    ),

  rejectIntervention: (experimentId: string, proposalId: string, reason: string) =>
    request<WorldState>(
      `/experiments/${experimentId}/interventions/${proposalId}/reject`,
      {
        method: "POST",
        headers: keyed("reject-intervention"),
        body: JSON.stringify({ reason }),
      },
    ),

  createBranch: (experimentId: string, interventionId: string) =>
    request<Branch>(`/experiments/${experimentId}/branches`, {
      method: "POST",
      headers: keyed("create-branch"),
      body: JSON.stringify({ intervention_id: interventionId }),
    }),

  runBranch: (branchId: string) =>
    request<WorldState>(`/branches/${branchId}/run`, {
      method: "POST",
      headers: keyed(`run-${branchId}-T5`),
      body: JSON.stringify({ until_phase: "T5" }),
    }),

  compare: (experimentId: string) =>
    request<ComparisonResult>(`/experiments/${experimentId}/compare`),

  evidence: (experimentId: string, evidenceId: string) =>
    request<EvidenceRecord>(
      `/experiments/${experimentId}/evidence/${encodeURIComponent(evidenceId)}`,
    ),

  replay: (experimentId: string) =>
    request<Array<Record<string, unknown>>>(`/experiments/${experimentId}/replay`),

  streamUrl: (experimentId: string) => `${API_ROOT}/experiments/${experimentId}/stream`,
};
