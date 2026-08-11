import type {
  Branch,
  CentralIntervention,
  ComparisonResult,
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

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
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
      detail?: { message?: string } | string;
    } | null;
    const message =
      typeof payload?.detail === "string"
        ? payload.detail
        : payload?.detail?.message ?? `请求失败（${response.status}）`;
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export const policyScopeApi = {
  health: () =>
    request<{ status: string; runtime: string; run_mode: RunMode; version: string }>(
      "/health",
    ),

  listProvinces: () => request<ProvinceProfile[]>("/meta/provinces"),

  createExperiment: (objective: string, runMode: RunMode) =>
    request<WorldState>("/experiments", {
      method: "POST",
      body: JSON.stringify({ objective, run_mode: runMode }),
    }),

  approveDirective: (experimentId: string, policy?: Policy) =>
    request<WorldState>(`/experiments/${experimentId}/directive/approve`, {
      method: "POST",
      body: JSON.stringify({ policy: policy ?? null }),
    }),

  runExperiment: (experimentId: string, phase: "T3" | "T5", branchId = "control") =>
    request<WorldState>(`/experiments/${experimentId}/run`, {
      method: "POST",
      body: JSON.stringify({ until_phase: phase, branch_id: branchId }),
    }),

  approveIntervention: (experimentId: string, proposalId: string) =>
    request<CentralIntervention>(
      `/experiments/${experimentId}/interventions/${proposalId}/approve`,
      { method: "POST", body: JSON.stringify({ overrides: {} }) },
    ),

  createBranch: (experimentId: string, interventionId: string) =>
    request<Branch>(`/experiments/${experimentId}/branches`, {
      method: "POST",
      body: JSON.stringify({ intervention_id: interventionId }),
    }),

  runBranch: (branchId: string) =>
    request<WorldState>(`/branches/${branchId}/run`, {
      method: "POST",
      body: JSON.stringify({ until_phase: "T5" }),
    }),

  compare: (experimentId: string) =>
    request<ComparisonResult>(`/experiments/${experimentId}/compare`),

  streamUrl: (experimentId: string) => `${API_ROOT}/experiments/${experimentId}/stream`,
};
