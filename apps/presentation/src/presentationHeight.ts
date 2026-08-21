import type { PresentationVisualScale } from "./mapScale";

const MIN_HEIGHT_METERS = 90_000;
const MAX_HEIGHT_METERS = 1_180_000;

export function normalizedHeight(value: number | null, scale: PresentationVisualScale): number {
  if (value == null || !Number.isFinite(value)) return 0;
  const [minimum, maximum] = scale.domain;
  const span = maximum - minimum;
  if (!Number.isFinite(span) || Math.abs(span) < 1e-9) return 0.5;
  return Math.max(0, Math.min(1, (value - minimum) / span));
}

export function heightMetersForValue(value: number | null, scale: PresentationVisualScale): number {
  if (value == null || !Number.isFinite(value)) return 0;
  return MIN_HEIGHT_METERS + (MAX_HEIGHT_METERS - MIN_HEIGHT_METERS) * normalizedHeight(value, scale);
}

export function heightPixelsForValue(value: number | null, scale: PresentationVisualScale): number {
  if (value == null || !Number.isFinite(value)) return 0;
  return 18 + normalizedHeight(value, scale) * 96;
}
