import { describe, expect, it } from "vitest";

import { EVENT_LABELS, SIMULATION_EVENT_TYPES } from "./events";

describe("V3 event contract", () => {
  it("subscribes to province, automaker and annual comparison facts", () => {
    expect(SIMULATION_EVENT_TYPES).toEqual(expect.arrayContaining([
      "province.decision.completed", "automaker.decision.completed",
      "province.feedback.completed", "comparison.completed",
    ]));
    expect(SIMULATION_EVENT_TYPES.some((item) => item.startsWith("enterprise."))).toBe(false);
  });

  it("uses readable non-predictive labels", () => {
    expect(EVENT_LABELS["automaker.decision.completed"]).toContain("模拟");
    expect(EVENT_LABELS["comparison.completed"]).toContain("A/B");
  });
});
