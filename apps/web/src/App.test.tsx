import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function renderApp(path = "/experiments/new") {
  const client = new QueryClient({ defaultOptions: { queries: { retry:false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

describe("PolicyScope V3 shell", () => {
  afterEach(() => cleanup());
  beforeEach(() => vi.stubGlobal("fetch", vi.fn((request: RequestInfo | URL) => {
    const url=String(request); const payload=url.includes("/meta/provinces")?[]:url.includes("/meta/automakers")?[]:url.includes("/meta/event-scenarios")?[]:{status:"ok",run_mode:"fake",version:"0.6.0"};
    return Promise.resolve({ok:true,json:()=>Promise.resolve(payload)});
  })));

  it("shows the M34 quarterly A/B journey", async () => {
    renderApp();
    expect(await screen.findByText("输入待研判的政策文本")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "生成中央政策解读" })).toBeInTheDocument();
    expect(screen.getByText("参与主体")).toBeInTheDocument();
    expect(screen.getByText("结果与对比")).toBeInTheDocument();
    expect(screen.getAllByText("方法与数据")).toHaveLength(2);
    expect(screen.queryByText("干预审批")).not.toBeInTheDocument();
    expect(screen.queryByText("Y2_Q2")).not.toBeInTheDocument();
    expect(screen.getByText("Q1–Q4")).toBeInTheDocument();
  });

  it("redirects unknown routes to policy setup", async () => {
    renderApp("/not-a-route");
    expect(await screen.findByText("输入待研判的政策文本")).toBeInTheDocument();
  });
});
