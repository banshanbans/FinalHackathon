import type { PresentationMapFrame } from "./contracts";

const SEQUENTIAL_COLORS = ["#17293a", "#16505f", "#166f76", "#22bdae", "#75ead6"] as const;
const DIVERGING_COLORS = ["#7765d4", "#4c4778", "#17293a", "#176a70", "#75ead6"] as const;

export interface PresentationVisualScale {
  domain: readonly [number, number];
  stops: ReadonlyArray<readonly [number, string]>;
  center: number | null;
}

function quantile(values: number[], ratio: number) {
  if (!values.length) return 0;
  const position = (values.length - 1) * ratio;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return values[lower]!;
  const weight = position - lower;
  return values[lower]! * (1 - weight) + values[upper]! * weight;
}

function distinctDomain(minimum: number, maximum: number): [number, number] {
  if (Math.abs(maximum - minimum) > 1e-9) return [minimum, maximum];
  const padding = Math.max(0.5, Math.abs(minimum) * 0.05);
  return [minimum - padding, maximum + padding];
}

export function visualScaleForFrame(frame: PresentationMapFrame): PresentationVisualScale {
  const values = frame.province_values
    .flatMap((item) => item.value == null || !Number.isFinite(item.value) ? [] : [item.value])
    .sort((left, right) => left - right);
  if (frame.map_projection.mode === "difference") {
    const bound = Math.max(0.01, ...values.map((value) => Math.abs(value)));
    const points = [-bound, -bound / 2, 0, bound / 2, bound];
    return {
      domain: [-bound, bound],
      center: 0,
      stops: points.map((value, index) => [value, DIVERGING_COLORS[index]!] as const),
    };
  }

  const [minimum, maximum] = distinctDomain(quantile(values, 0.05), quantile(values, 0.95));
  const points = [
    minimum,
    minimum + (maximum - minimum) * 0.25,
    minimum + (maximum - minimum) * 0.5,
    minimum + (maximum - minimum) * 0.75,
    maximum,
  ];
  return {
    domain: [minimum, maximum],
    center: null,
    stops: points.map((value, index) => [value, SEQUENTIAL_COLORS[index]!] as const),
  };
}

export function visualScaleForFrames(frames: readonly PresentationMapFrame[]): PresentationVisualScale {
  const reference = frames[0];
  if (!reference) {
    return { domain: [0, 1], center: null, stops: SEQUENTIAL_COLORS.map((color, index) => [index / 4, color] as const) };
  }
  return visualScaleForFrame({
    ...reference,
    province_values: frames.flatMap((frame) => frame.province_values),
  });
}

export function colorForValue(scale: PresentationVisualScale, value: number | null) {
  if (value == null || !Number.isFinite(value)) return "#111b29";
  for (let index = 1; index < scale.stops.length; index += 1) {
    const [threshold] = scale.stops[index]!;
    if (value < threshold) return scale.stops[index - 1]![1];
  }
  return scale.stops.at(-1)?.[1] ?? "#111b29";
}

export function scaleLabel(scale: PresentationVisualScale) {
  const precision = Math.max(...scale.domain.map((value) => Math.abs(value))) < 10 ? 2 : 1;
  return `${scale.domain[0].toFixed(precision)} – ${scale.domain[1].toFixed(precision)}`;
}
