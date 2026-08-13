import type {
  M34Comparison,
  M34Design,
  M34EventTemplate,
  M34InteractionMarket,
  M34Interpretation,
  M34World,
  MacroTick,
} from "../m34Types";

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
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? `请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}

export const m34Client = {
  create: (policyText: string) => request<M34World>("/experiments", {
    method: "POST",
    headers: { "Idempotency-Key": `m34:web:create:${crypto.randomUUID()}` },
    body: JSON.stringify({ policy_text: policyText, seed: 20260812, product_version: "v3_2_m34" }),
  }),
  state: (id: string) => request<M34World>(`/experiments/${id}/state`),
  confirmInterpretation: (id: string, value: M34Interpretation) => request<M34World>(
    `/experiments/${id}/interpretation`,
    { method: "PUT", body: JSON.stringify({ ...value, status: "confirmed" }) },
  ),
  confirmDesign: (id: string, value: M34Design) => request<M34World>(
    `/experiments/${id}/design`,
    { method: "PUT", body: JSON.stringify(value) },
  ),
  baselineMetadata: () => request<{ data_version: string }>("/meta/v32/baseline"),
  confirmBaseline: (id: string, dataVersion: string) => request<M34World>(
    `/experiments/${id}/baseline/confirm`,
    { method: "POST", body: JSON.stringify({ confirm_data_snapshot: true, expected_data_version: dataVersion }) },
  ),
  run: (id: string, tick: MacroTick) => request<M34World>(`/experiments/${id}/run`, {
    method: "POST",
    headers: { "Idempotency-Key": `m34:web:run:${id}:${tick}` },
    body: JSON.stringify({ until_tick: tick }),
  }),
  interactions: (id: string) => request<M34InteractionMarket>(`/experiments/${id}/interactions`),
  comparison: (id: string) => request<M34Comparison>(`/experiments/${id}/compare`),
  province: (id: string, code: string) => request<Record<string, unknown>>(`/experiments/${id}/provinces/${code}`),
  eventCatalog: async () => (await request<{ templates: M34EventTemplate[] }>("/meta/presentation-event-catalog")).templates,
  streamUrl: (id: string) => `${API_ROOT}/experiments/${id}/stream`,
};
