import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const profiles = Array.from({ length: 31 }, (_, index) => ({
  schema_version: "province-profile-v3",
  province_code: String(index + 11).padStart(2, "0"),
  name: index === 30 ? "河南省" : `测试省${index + 1}`,
  short_name: index === 30 ? "河南" : `省${index + 1}`,
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
  rd_capacity: 0.5,
  employment_pressure: 0.5,
  cooperation_tendency: 0.5,
  data_quality: index < 3 ? "verified" : "proxy",
  source_year: 2024,
}));
const persona = {
  schema_version: "province-persona-v1",
  province_code: "41",
  axes: {
    execution_drive: 0.5,
    fiscal_prudence: 0.4,
    sme_inclusiveness: 0.9,
    technology_ambition: 0.6,
    green_priority: 0.3,
    cooperation_orientation: 0.7,
  },
  primary_type: "inclusive_diffusion",
  secondary_type: null,
  priority_goals: ["sme_financing_access"],
  key_constraints: ["financing_gap", "employment_pressure"],
  profile_version: "province-profile-v3",
  network_version: "province-network-v1",
  method_version: "province-persona-method-v1",
  data_quality: "demo",
  public_summary: "本次实验中重点关注中小企业融资可达性。",
};
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
  schema_version: "world-state-v3",
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
  province_personas: { "41": persona },
  province_states: {},
  province_actions: {},
  province_action_lineage: {},
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
const provinceDetail = {
  schema_version: "province-agent-detail-v1",
  experiment_id: "exp-approved",
  province_code: "41",
  profile: profiles.find((item) => item.province_code === "41"),
  persona,
  top_k_neighbors: [{ province_code: "42", province_name: "湖北省", weight: 0.8 }],
  branches: {
    control: {
      branch_id: "control",
      branch_kind: "control",
      phase: "T3",
      state: {
        province_code: "41",
        phase: "T3",
        enterprise_participation_index: 55,
        equipment_renewal_willingness_index: 58,
        sme_financing_accessibility_index: 60,
        industrial_upgrade_index: 52,
        fiscal_pressure_index: 45,
        last_action_id: "action-41-t1",
      },
      current_action: {
        schema_version: "province-action-v3",
        action_id: "action-41-t1",
        previous_action_id: null,
        province_code: "41",
        phase: "T1",
        primary_goal: "sme_financing_access",
        decision_posture: "balanced",
        target_enterprise_groups: ["technology_sme", "traditional_sme"],
        interprovincial_strategy: "collaborate",
        target_province_codes: ["42"],
        implementation_intensity: 0.72,
        local_match_ratio: 0.48,
        instrument_mix: policy.instrument_mix,
        sme_preference: 0.7,
        regional_delivery_focus: 0.6,
        technology_mix: policy.technology_mix,
        requested_central_support: 0.5,
        reason_codes: ["SME_ACCESS_PRIORITY"],
        public_summary: "以普惠融资工具推动设备更新。",
        run_mode: "cache",
        fallback_used: false,
      },
      action_lineage: [],
      feedback: null,
      enterprise_groups: [],
      mechanism_summary: {},
      evidence_refs: ["method"],
    },
  },
};

function renderApp(path = "/experiments/new") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

describe("PolicyScope V2.1 shell", () => {
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
      const payload = url.includes("/experiments/exp-approved/provinces/41")
        ? provinceDetail
        : url.includes("/experiments/exp-approved/state")
          ? approvedWorld
          : url.includes("/meta/provinces")
            ? profiles
            : url.includes("/meta/enterprise-archetypes") || url.includes("/meta/province-persona-types")
              ? []
              : url.includes("/meta/default-policy")
                ? policy
                : { status: "ok", runtime: "asyncio", run_mode: "cache", version: "0.3.0" };
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

  it("uses the experiment id in the URL as the loading authority", async () => {
    localStorage.setItem("policyscope.recent-experiment.v3", "exp-other");
    renderApp("/experiments/exp-approved/live");

    expect(await screen.findByText("31 省政策决策与企业反馈")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/experiments/exp-approved/state"), expect.anything());
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/experiments/exp-other/state"), expect.anything());
  });

  it("renders the fifth route and preserves an unavailable treatment branch as empty", async () => {
    renderApp("/experiments/exp-approved/provinces/41?branch=treatment&evidence=method");

    expect(await screen.findByText("未创建干预方案")).toBeInTheDocument();
    expect(screen.getByText("河南省")).toBeInTheDocument();
    expect(screen.getByText("普惠扩散型")).toBeInTheDocument();
  });

  it("redirects the legacy province query to the province route", async () => {
    renderApp("/experiments/exp-approved/live?province=41&branch=control");
    expect(await screen.findByText("实验决策画像")).toBeInTheDocument();
    expect(screen.queryByLabelText("河南省")).not.toBeInTheDocument();
  });
});
