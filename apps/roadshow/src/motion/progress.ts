import type { RoadshowStage } from "../store";

export const STORY_PROGRESS_MAX = 3.12;

export function clampSceneProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function clampStoryProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(STORY_PROGRESS_MAX, Math.max(0, value));
}

/**
 * Quintic ease-in-out for the physical camera move. Zero velocity and
 * acceleration at both ends create one decisive move with a long soft settle.
 */
export function appleCameraProgress(value: number): number {
  const progress = clampSceneProgress(value);
  return progress * progress * progress * (progress * (progress * 6 - 15) + 10);
}

export function stageForProgress(
  value: number,
): Extract<RoadshowStage, "orbital" | "china-focus" | "identity-reveal" | "causal-handoff"> {
  const progress = clampSceneProgress(value);
  if (progress >= 0.94) return "causal-handoff";
  if (progress >= 0.72) return "identity-reveal";
  if (progress >= 0.06) return "china-focus";
  return "orbital";
}

/** Maps the complete cockpit-to-causal-stage scroll sequence. */
export function stageForMasterProgress(value: number): RoadshowStage {
  const progress = clampStoryProgress(value);
  if (progress >= 2.66) return "earth-return";
  if (progress >= 2.24) return "enterprise-agent";
  if (progress >= 1.76) return "vehicle-interior";
  if (progress >= 1.28) return "province-agent";
  if (progress >= 1.01) return "policy-signal";
  if (progress >= 0.975) return "causal-handoff";
  if (progress >= 0.91) return "identity-reveal";
  if (progress >= 0.7) return "china-focus";
  if (progress >= 0.53) return "orbital";
  if (progress >= 0.47) return "ripple";
  if (progress >= 0.31) return "ratio";
  if (progress >= 0.19) return "funding";
  if (progress >= 0.07) return "consumer";
  return "cockpit";
}

export function progressDeltaForWheel(deltaY: number, deltaMode = 0): number {
  if (!Number.isFinite(deltaY) || deltaY === 0) return 0;
  const pixels = deltaMode === 1 ? deltaY * 16 : deltaMode === 2 ? deltaY * 800 : deltaY;
  const direction = Math.sign(pixels);
  return direction * Math.min(0.065, Math.max(0.008, Math.abs(pixels) / 4200));
}

/** Maps presentation keys onto the same reversible virtual timeline. */
export function progressDeltaForKeyboard(key: string, currentProgress = 0): number {
  const step = clampStoryProgress(currentProgress) < STORY_PROGRESS_MAX / 2 ? 0.05 : 0.1;
  if (key === "ArrowRight" || key === "ArrowDown" || key === "PageDown" || key === " ") return step;
  if (key === "ArrowLeft" || key === "ArrowUp" || key === "PageUp") return -step;
  return 0;
}
