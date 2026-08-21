import { create } from "zustand";

export type RoadshowStage =
  | "loading"
  | "cockpit"
  | "consumer"
  | "funding"
  | "ratio"
  | "ripple"
  | "orbital"
  | "china-focus"
  | "identity-reveal"
  | "causal-handoff"
  | "policy-signal"
  | "province-agent"
  | "vehicle-interior"
  | "enterprise-agent"
  | "earth-return"
  | "error";

interface RoadshowState {
  stage: RoadshowStage;
  setStage: (stage: RoadshowStage) => void;
}

export const useRoadshowStore = create<RoadshowState>((set) => ({
  stage: "loading",
  setStage: (stage) => set((state) => (state.stage === stage ? state : { stage })),
}));
