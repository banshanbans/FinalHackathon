import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const profiles = Array.from({ length: 31 }, (_, index) => ({
  province_code: String(index + 11).padStart(2, "0"),
  name: `测试省${index + 1}`,
  short_name: `省${index + 1}`,
  region_group: "east",
  data_quality: index < 3 ? "verified" : "proxy",
  source_year: 2024,
}));

describe("PolicyScope shell", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(profiles),
    }));
  });

  it("shows the non-prediction disclosure and approval-first flow", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><App /></QueryClientProvider>);
    expect(screen.getByText(/这是机制推演，不是现实预测/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成中央政策草案/ })).toBeInTheDocument();
    expect(screen.getByText(/批准前不会启动省级推演/)).toBeInTheDocument();
  });
});
