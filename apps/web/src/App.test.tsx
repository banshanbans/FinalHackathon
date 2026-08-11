import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const profiles = Array.from({ length: 31 }, (_, index) => ({
  province_code: String(index + 11).padStart(2, "0"),
  name: `测试省${index + 1}`,
  short_name: `省${index + 1}`,
  region_group: "east",
  economic_scale: 0.5,
  fiscal_capacity: 0.5,
  industrial_diversity: 0.5,
  advanced_manufacturing_base: 0.5,
  digital_infrastructure: 0.5,
  green_energy_base: 0.5,
  sme_density: 0.5,
  credit_access: 0.5,
  transition_pressure: 0.5,
  fiscal_conservatism: 0.5,
  data_quality: index < 3 ? "verified" : "proxy",
  source_year: 2024,
}));
const policy = {
  schema_version: "policy-v2",
  policy_id: "equipment_renewal_v2",
  domain: "manufacturing_equipment_renewal",
  support_intensity: 70,
  local_match_requirement: 0.5,
  instrument_mix: { direct_subsidy: 0.45, interest_subsidy: 0.35, financing_guarantee: 0.2 },
  sme_preference: 0.6,
  regional_support_bias: 0,
  technology_mix: { digital: 0.4, green: 0.3, general: 0.3 },
  mechanism_version: "equipment-renewal-env-v2",
};

function renderApp(path = "/experiments/new") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

describe("PolicyScope V2 shell", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    const storage = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      key: (index: number) => [...storage.keys()][index] ?? null,
      get length() { return storage.size; },
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, String(value)),
    });
    vi.stubGlobal("fetch", vi.fn((request: RequestInfo | URL) => {
      const url = String(request);
      const payload = url.includes("/meta/provinces") ? profiles : url.includes("/meta/enterprise-archetypes") ? [] : url.includes("/meta/default-policy") ? policy : { status: "ok", runtime: "asyncio", run_mode: "cache", version: "0.2.0" };
      return Promise.resolve({ ok: true, json: () => Promise.resolve(payload) });
    }));
  });

  it("shows the State Council target, fixed disclosure, and approval-first flow", async () => {
    renderApp();
    expect(await screen.findByText(/将政策目标转化为可审批参数/)).toBeInTheDocument();
    expect(screen.getByText(/不构成现实政策预测或决策建议/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成结构化政策草案/ })).toBeInTheDocument();
    expect(screen.getByText(/人类最终控制/)).toBeInTheDocument();
  });

  it("redirects unknown routes to the new experiment route", async () => {
    renderApp("/unknown");
    expect(await screen.findByText(/中央政策设定/)).toBeInTheDocument();
  });
});
