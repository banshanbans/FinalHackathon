import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EventRail } from "./components/EventRail";
import { SIMULATION_EVENT_TYPES } from "./events";
import type { SimulationEvent } from "./types";

function provinceEvent(type: string, eventId: string): SimulationEvent {
  return {
    event_id: eventId,
    type,
    experiment_id: "exp-province-events",
    branch_id: "control",
    phase: "T1",
    timestamp: "2026-08-12T00:00:00Z",
    schema_version: "event-v3",
    payload: { province_code: "41" },
  };
}

describe("province decision event contract", () => {
  it("subscribes to the province event names emitted by the backend", () => {
    expect(SIMULATION_EVENT_TYPES).toEqual(
      expect.arrayContaining([
        "province.decision.started",
        "province.decision.completed",
        "province.decision.fallback",
        "province.persona.ready",
        "province.adjustment_intent.completed",
        "province.strategy.changed",
      ]),
    );
    expect(SIMULATION_EVENT_TYPES).not.toEqual(
      expect.arrayContaining([
        "agent.decision.started",
        "agent.decision.completed",
        "agent.decision.fallback",
      ]),
    );
  });

  it("renders readable labels for province decision events", () => {
    render(
      <EventRail
        events={[
          provinceEvent("province.decision.started", "evt-1"),
          provinceEvent("province.decision.completed", "evt-2"),
          provinceEvent("province.decision.fallback", "evt-3"),
        ]}
      />,
    );

    expect(screen.getByText("省级智能体开始决策")).toBeInTheDocument();
    expect(screen.getByText("省级策略已生成")).toBeInTheDocument();
    expect(screen.getByText("省级策略已降级")).toBeInTheDocument();
  });
});
