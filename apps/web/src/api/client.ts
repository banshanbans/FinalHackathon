import type { AuditListResponse, AuditRecord, AuditRecordType, AutomakerDetail, AutomakerMeta, Branch, CentralIntervention, ComparisonResult, EvidenceRecord, Policy, ProvinceAgentDetail, ProvinceProfile, RunMode, SimulationEvent, WorldState } from "../types";

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
const API_ROOT = configuredBase ? `${configuredBase}/api` : "/api";

export class ApiError extends Error { constructor(public status: number, public errorCode: string, message: string) { super(message); } }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: { error_code?: string; message?: string } | string } | null;
    const detail = payload?.detail;
    throw new ApiError(response.status, typeof detail === "object" ? detail?.error_code ?? "REQUEST_FAILED" : "REQUEST_FAILED", typeof detail === "string" ? detail : detail?.message ?? `请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}
const keyed = (name: string) => ({ "Idempotency-Key": `${name}:${crypto.randomUUID()}` });

export const policyScopeApi = {
  health: () => request<{ status: string; run_mode: RunMode; version: string }>("/health"),
  listProvinces: () => request<ProvinceProfile[]>("/meta/provinces"),
  listAutomakers: () => request<AutomakerMeta[]>("/meta/automakers"),
  defaultPolicy: () => request<Policy>("/meta/default-policy"),
  createExperiment: (objective: string, runMode: RunMode) => request<WorldState>("/experiments", { method: "POST", headers: keyed("create"), body: JSON.stringify({ objective, run_mode: runMode }) }),
  getState: (id: string, branch = "control") => request<WorldState>(`/experiments/${id}/state?branch_id=${branch}`),
  approveDirective: (id: string, policy: Policy) => request<WorldState>(`/experiments/${id}/directive/approve`, { method: "POST", headers: keyed("approve-directive"), body: JSON.stringify({ policy }) }),
  runExperiment: (id: string, phase: Phase, branch = "control") => request<WorldState>(`/experiments/${id}/run`, { method: "POST", headers: keyed(`run-${branch}-${phase}`), body: JSON.stringify({ until_phase: phase, branch_id: branch }) }),
  approveIntervention: (id: string, proposalId: string, policy: Policy) => request<CentralIntervention>(`/experiments/${id}/interventions/${proposalId}/approve`, { method: "POST", headers: keyed("approve-intervention"), body: JSON.stringify({ policy }) }),
  rejectIntervention: (id: string, proposalId: string, reason: string) => request<WorldState>(`/experiments/${id}/interventions/${proposalId}/reject`, { method: "POST", headers: keyed("reject-intervention"), body: JSON.stringify({ reason }) }),
  listBranches: (id: string) => request<Branch[]>(`/experiments/${id}/branches`),
  createBranch: (id: string, interventionId: string) => request<Branch>(`/experiments/${id}/branches`, { method: "POST", headers: keyed("branch"), body: JSON.stringify({ intervention_id: interventionId }) }),
  runBranch: (branch: string) => request<WorldState>(`/branches/${branch}/run`, { method: "POST", headers: keyed(`run-${branch}`), body: JSON.stringify({ until_phase: "Y2_Q4" }) }),
  compare: (id: string) => request<ComparisonResult>(`/experiments/${id}/compare`),
  getProvinceDetail: (id: string, code: string) => request<ProvinceAgentDetail>(`/experiments/${id}/provinces/${code}`),
  getAutomakerDetail: (id: string, automakerId: string) => request<AutomakerDetail>(`/experiments/${id}/automakers/${automakerId}`),
  evidence: (id: string, evidenceId: string) => request<EvidenceRecord>(`/experiments/${id}/evidence/${encodeURIComponent(evidenceId)}`),
  audit: (id: string, filters: { recordType?: AuditRecordType; limit?: number } = {}) => { const query = new URLSearchParams(); if (filters.recordType) query.set("record_type", filters.recordType); if (filters.limit) query.set("limit", String(filters.limit)); return request<AuditListResponse>(`/experiments/${id}/audit?${query}`); },
  auditRecord: (id: string, recordId: string) => request<AuditRecord>(`/experiments/${id}/audit/${recordId}`),
  replay: (id: string) => request<SimulationEvent[]>(`/experiments/${id}/replay`),
  streamUrl: (id: string) => `${API_ROOT}/experiments/${id}/stream`,
};

type Phase = import("../types").Phase;
