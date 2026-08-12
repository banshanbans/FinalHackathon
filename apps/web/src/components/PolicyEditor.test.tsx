import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Policy } from "../types";
import { PolicyEditor } from "./PolicyEditor";

const policy: Policy = {
  schema_version: "policy-v3",
  policy_id: "nev_trade_in_cost_sharing_v3",
  domain: "nev_subsidy_and_industrial_layout",
  reference_policy_year: 2025,
  input_mode: "absolute",
  west_central_share: 0.95,
  central_central_share: 0.9,
  east_central_share: 0.85,
  share_adjustments: { west: 0, central: 0, east: 0 },
  consumer_subsidy_standard_version: "v1",
  eligibility_rule_version: "v1",
  primary_goal: "reduce_regional_gap",
  status: "draft",
  mechanism_version: "nev-policy-env-v1",
};

describe("PolicyEditor", () => {
  it("warns but does not block a non-monotonic regional ordering", () => {
    const onChange = vi.fn();
    const { rerender } = render(<PolicyEditor onChange={onChange} policy={policy} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("西部 12 省中央承担比例"), {
      target: { value: "80" },
    });
    const changed = onChange.mock.calls[0][0] as Policy;
    rerender(<PolicyEditor onChange={onChange} policy={changed} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/允许继续用于机制实验/);
    expect(screen.getByLabelText("西部 12 省中央承担比例")).toBeEnabled();
  });
});
