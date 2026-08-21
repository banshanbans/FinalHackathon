import { describe, expect, it } from "vitest";
import {
  appleCameraProgress,
  clampSceneProgress,
  clampStoryProgress,
  progressDeltaForKeyboard,
  progressDeltaForWheel,
  STORY_PROGRESS_MAX,
  stageForMasterProgress,
  stageForProgress,
} from "./progress";

describe("roadshow scene progress", () => {
  it("clamps invalid and out-of-range progress", () => {
    expect(clampSceneProgress(Number.NaN)).toBe(0);
    expect(clampSceneProgress(-0.2)).toBe(0);
    expect(clampSceneProgress(0.45)).toBe(0.45);
    expect(clampSceneProgress(2)).toBe(1);
    expect(clampStoryProgress(4)).toBe(STORY_PROGRESS_MAX);
  });

  it("maps the master progress to the four semantic scenes", () => {
    expect(stageForProgress(0)).toBe("orbital");
    expect(stageForProgress(0.059)).toBe("orbital");
    expect(stageForProgress(0.06)).toBe("china-focus");
    expect(stageForProgress(0.719)).toBe("china-focus");
    expect(stageForProgress(0.72)).toBe("identity-reveal");
    expect(stageForProgress(0.939)).toBe("identity-reveal");
    expect(stageForProgress(0.94)).toBe("causal-handoff");
    expect(stageForProgress(1)).toBe("causal-handoff");
  });

  it("maps one continuous scroll from the dark cockpit to the causal stage", () => {
    expect(stageForMasterProgress(0)).toBe("cockpit");
    expect(stageForMasterProgress(0.07)).toBe("consumer");
    expect(stageForMasterProgress(0.19)).toBe("funding");
    expect(stageForMasterProgress(0.31)).toBe("ratio");
    expect(stageForMasterProgress(0.47)).toBe("ripple");
    expect(stageForMasterProgress(0.53)).toBe("orbital");
    expect(stageForMasterProgress(0.7)).toBe("china-focus");
    expect(stageForMasterProgress(0.91)).toBe("identity-reveal");
    expect(stageForMasterProgress(0.975)).toBe("causal-handoff");
    expect(stageForMasterProgress(1)).toBe("causal-handoff");
    expect(stageForMasterProgress(1.01)).toBe("policy-signal");
    expect(stageForMasterProgress(1.28)).toBe("province-agent");
    expect(stageForMasterProgress(1.76)).toBe("vehicle-interior");
    expect(stageForMasterProgress(2.24)).toBe("enterprise-agent");
    expect(stageForMasterProgress(2.66)).toBe("earth-return");
    expect(stageForMasterProgress(STORY_PROGRESS_MAX)).toBe("earth-return");
  });

  it("uses one nonlinear camera acceleration with a soft terminal settle", () => {
    expect(appleCameraProgress(0)).toBe(0);
    expect(appleCameraProgress(0.25)).toBeLessThan(0.25);
    expect(appleCameraProgress(0.5)).toBeCloseTo(0.5);
    expect(appleCameraProgress(0.75)).toBeGreaterThan(0.75);
    expect(appleCameraProgress(1)).toBe(1);
  });

  it("normalizes mouse and trackpad wheel input without large jumps", () => {
    expect(progressDeltaForWheel(0)).toBe(0);
    expect(progressDeltaForWheel(120)).toBeCloseTo(120 / 4200);
    expect(progressDeltaForWheel(-120)).toBeCloseTo(-120 / 4200);
    expect(progressDeltaForWheel(3, 1)).toBeCloseTo(48 / 4200);
    expect(progressDeltaForWheel(5000)).toBe(0.065);
  });

  it("uses precise arrow steps in the first half and larger steps in the second", () => {
    expect(progressDeltaForKeyboard("ArrowRight", 0)).toBe(0.05);
    expect(progressDeltaForKeyboard("ArrowDown", 1.55)).toBe(0.05);
    expect(progressDeltaForKeyboard("ArrowLeft", 0.8)).toBe(-0.05);
    expect(progressDeltaForKeyboard("ArrowUp", STORY_PROGRESS_MAX / 2)).toBe(-0.1);
    expect(progressDeltaForKeyboard("ArrowRight", 2.4)).toBe(0.1);
    expect(progressDeltaForKeyboard("Enter")).toBe(0);
  });
});
