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
const approvedWorld = {
  schema_version: "world-state-v2",
  experiment_id: "exp-approved",
  branch_id: "control",
  parent_checkpoint_id: "checkpoint-t3",
  phase: "T5",
  status: "completed",
  run_mode: "cache",
  policy,
  directive: {
    directive_id: "directive-approved",
    policy,
    policy_objectives: ["equipment_renewal"],
    hard_constraints: ["human_approval_required"],
    public_summary: "中央政策已完成审批。",
    requires_human_approval: true,
    approval_status: "approved",
  },
  national_metrics: {
    schema_version: "national-metrics-v2",
    enterprise_participation_index: 50,
    equipment_renewal_willingness_index: 50,
    sme_financing_accessibility_index: 50,
    industrial_upgrade_index: 50,
    local_fiscal_pressure_index: 50,
    regional_gap_index: 50,
  },
  province_profiles: {},
  province_states: {},
  province_actions: {},
  province_feedback: {},
  enterprise_profiles: {},
  enterprise_states: {},
  enterprise_actions: {},
  enterprise_aggregates: {},
  contributions: {},
  fallback_provinces: [],
  intervention_proposals: [],
  intervention_decision: null,
  approved_intervention: null,
  central_review: null,
  versions: {
    data: "test-data",
    mechanism: "test-mechanism",
    prompt: "test-prompt",
    model: "test-model",
    app: "test-app",
  },
  seed: 20260812,
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
      const payload = url.includes("/experiments/exp-approved/state") ? approvedWorld : url.includes("/meta/provinces") ? profiles : url.includes("/meta/enterprise-archetypes") ? [] : url.includes("/meta/default-policy") ? policy : { status: "ok", runtime: "asyncio", run_mode: "cache", version: "0.2.0" };
      return Promise.resolve({ ok: true, json: () => Promise.resolve(payload) });
    }));
  });

  it("shows production Chinese copy and the approval-first workflow", async () => {
    renderApp();
    expect(await screen.findByText(/配置制造业设备更新政策/)).toBeInTheDocument();
    expect(screen.getByText(/用于政策方案比较/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成结构化政策草案/ })).toBeInTheDocument();
    expect(screen.getByText(/人工审批控制/)).toBeInTheDocument();
    expect(screen.queryByText("READY")).not.toBeInTheDocument();
    expect(screen.queryByText("情景实验")).not.toBeInTheDocument();
  });

  it("redirects unknown routes to the new experiment route", async () => {
    renderApp("/unknown");
    expect(await screen.findByText(/中央政策配置/)).toBeInTheDocument();
  });

  it("does not offer duplicate approval for an approved directive", async () => {
    localStorage.setItem("policyscope.active-experiment.v2", "exp-approved");
    renderApp();

    expect(await screen.findByText("中央政策已审批")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /进入实时推演/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /批准并启动省企推演/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("slider").every((input) => input.hasAttribute("disabled"))).toBe(true);
  });
});
