import type {
  NationalMetricKey,
  Participation,
  ProvincePriorityGoal,
  SimulationEvent,
  WorldState,
} from "../types";

export const NATIONAL_METRIC_KEYS: NationalMetricKey[] = [
  "enterprise_participation_index",
  "equipment_renewal_willingness_index",
  "sme_financing_accessibility_index",
  "industrial_upgrade_index",
  "local_fiscal_pressure_index",
  "regional_gap_index",
];

export interface MetricTrendPoint {
  phase: string;
  enterprise_participation_index?: number;
  equipment_renewal_willingness_index?: number;
  sme_financing_accessibility_index?: number;
  industrial_upgrade_index?: number;
  local_fiscal_pressure_index?: number;
  regional_gap_index?: number;
}

export function selectMetricTrend(events: SimulationEvent[]): MetricTrendPoint[] {
  const byPhase = new Map<string, MetricTrendPoint>();
  events.filter((event) => event.type === "environment.updated").forEach((event) => {
    const point: MetricTrendPoint = { phase: event.phase };
    NATIONAL_METRIC_KEYS.forEach((key) => {
      const value = event.payload[key];
      if (typeof value === "number" && Number.isFinite(value)) point[key] = value;
    });
    byPhase.set(event.phase, point);
  });
  return [...byPhase.values()].sort((left, right) => Number(left.phase.slice(1)) - Number(right.phase.slice(1)));
}

export function selectParticipationDistribution(world: WorldState) {
  const counts: Record<Participation, number> = { participate: 0, conditional: 0, wait: 0, decline: 0 };
  Object.values(world.enterprise_actions).forEach((action) => { counts[action.participation] += 1; });
  return counts;
}

export function selectProvinceGoalDistribution(world: WorldState) {
  const counts = new Map<ProvincePriorityGoal, number>();
  Object.values(world.province_actions).forEach((action) => {
    counts.set(action.primary_goal, (counts.get(action.primary_goal) ?? 0) + 1);
  });
  return [...counts.entries()].sort((left, right) => right[1] - left[1]);
}

export function selectProvinceStrategyDistribution(world: WorldState) {
  const counts = new Map<string, number>();
  Object.values(world.province_actions).forEach((action) => {
    counts.set(action.interprovincial_strategy, (counts.get(action.interprovincial_strategy) ?? 0) + 1);
  });
  return [...counts.entries()].sort((left, right) => right[1] - left[1]);
}

export function selectKeyEvents(events: SimulationEvent[]) {
  const priority = [
    "province.decision.fallback",
    "enterprise.batch.fallback",
    "province.adjustment_intent.completed",
    "central.intervention.proposed",
    "checkpoint.created",
    "province.decision.completed",
  ];
  const latestByType = new Map<string, SimulationEvent>();
  events.forEach((event) => {
    if (priority.includes(event.type)) latestByType.set(event.type, event);
  });
  return priority.flatMap((type) => latestByType.get(type) ?? []).slice(0, 4);
}
