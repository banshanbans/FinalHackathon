import type { Policy } from "../types";

export function policyIsValid(policy: Policy) {
  const instruments = Object.values(policy.instrument_mix).reduce((sum, value) => sum + value, 0);
  const technologies = Object.values(policy.technology_mix).reduce((sum, value) => sum + value, 0);
  return Math.abs(instruments - 1) < 0.000001 && Math.abs(technologies - 1) < 0.000001;
}
