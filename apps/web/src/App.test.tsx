import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const policy = { schema_version:"policy-v3", policy_id:"nev_trade_in_cost_sharing_v3", domain:"nev_subsidy_and_industrial_layout", reference_policy_year:2025, input_mode:"absolute", west_central_share:.95, central_central_share:.90, east_central_share:.85, share_adjustments:{west:0,central:0,east:0}, consumer_subsidy_standard_version:"v1", eligibility_rule_version:"v1", primary_goal:"reduce_regional_gap", status:"draft", mechanism_version:"nev-policy-env-v1" };

function renderApp(path = "/experiments/new") {
  const client = new QueryClient({ defaultOptions: { queries: { retry:false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

describe("PolicyScope V3 shell", () => {
  afterEach(() => cleanup());
  beforeEach(() => vi.stubGlobal("fetch", vi.fn((request: RequestInfo | URL) => {
    const url=String(request); const payload=url.includes("/meta/provinces")?[]:url.includes("/meta/automakers")?[]:url.includes("/meta/default-policy")?policy:{status:"ok",run_mode:"cache",version:"0.4.0"};
    return Promise.resolve({ok:true,json:()=>Promise.resolve(payload)});
  })));

  it("shows the NEV approval-first contract", async () => {
    renderApp();
    expect(await screen.findByText("新能源汽车补贴共担比例实验")).toBeInTheDocument();
    expect(screen.getByText(/31 省级 Agent/)).toBeInTheDocument();
    expect(screen.queryByText(/批准前不会启动省级或车企推演/)).not.toBeInTheDocument();
    expect(screen.queryByText(/不代表现实政府或企业的未来决定/)).not.toBeInTheDocument();
    expect(screen.queryByText("SETUP · 中央政策配置")).not.toBeInTheDocument();
    expect(screen.queryByText("LIVE")).not.toBeInTheDocument();
    expect(screen.queryByText("人工审批门禁")).not.toBeInTheDocument();
    expect(screen.queryByText("Y1_Q1 省级政策")).not.toBeInTheDocument();
    expect(screen.getAllByText("政策设定")).toHaveLength(2);
    expect(screen.getAllByText("方案对照")).toHaveLength(2);
  });

  it("redirects unknown routes to policy setup", async () => {
    renderApp("/not-a-route");
    expect(await screen.findByText("新能源汽车补贴共担比例实验")).toBeInTheDocument();
  });
});
