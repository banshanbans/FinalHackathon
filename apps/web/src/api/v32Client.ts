import type { AutomakerDetailV32, ComparisonV6, ExperimentDesign, M29BaselineMetadata, PolicyInterpretation, PresentationSummary, ProvinceDetailV32, SimulationRound, StrategyMarket, V32Event, WorldStateV6 } from "../v32Types";

const configuredBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
const API_ROOT = configuredBase ? `${configuredBase}/api` : "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: { message?: string } | string } | null;
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? `请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}

const keyed = (name: string) => ({ "Idempotency-Key": `m32:${name}:${crypto.randomUUID()}` });

export const v32Api = {
  create: (policyText: string) => request<WorldStateV6>("/experiments", { method: "POST", headers: keyed("create"), body: JSON.stringify({ policy_text: policyText, seed: 20260812, product_version: "v3_2_m32" }) }),
  state: (id: string) => request<WorldStateV6>(`/experiments/${id}/state`),
  confirmInterpretation: (id: string, interpretation: PolicyInterpretation) => request<WorldStateV6>(`/experiments/${id}/interpretation`, { method: "PUT", body: JSON.stringify(interpretation) }),
  confirmDesign: (id: string, design: ExperimentDesign) => request<WorldStateV6>(`/experiments/${id}/design`, { method: "PUT", body: JSON.stringify(design) }),
  baselineMetadata: () => request<M29BaselineMetadata>("/meta/v32/baseline"),
  confirmBaseline: (id: string, expectedDataVersion: string) => request<WorldStateV6>(`/experiments/${id}/baseline/confirm`, { method: "POST", body: JSON.stringify({ confirm_data_snapshot: true, expected_data_version: expectedDataVersion }) }),
  run: (id: string, untilRound?: SimulationRound) => request<WorldStateV6>(`/experiments/${id}/run`, { method: "POST", headers: keyed(`run-${untilRound ?? "complete"}`), body: JSON.stringify(untilRound ? { until_round: untilRound } : {}) }),
  compare: (id: string) => request<ComparisonV6>(`/experiments/${id}/compare`),
  strategyMarket: (id: string) => request<StrategyMarket>(`/experiments/${id}/strategy-market`),
  presentationSummary: (id: string) => request<PresentationSummary>(`/experiments/${id}/presentation-summary`),
  province: (id: string, code: string) => request<ProvinceDetailV32>(`/experiments/${id}/provinces/${code}`),
  automaker: (id: string, automakerId: string) => request<AutomakerDetailV32>(`/experiments/${id}/automakers/${automakerId}`),
  replay: (id: string) => request<V32Event[]>(`/experiments/${id}/replay`),
  streamUrl: (id: string) => `${API_ROOT}/experiments/${id}/stream`,
};
