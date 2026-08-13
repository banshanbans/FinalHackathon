import type { PresentationMapCollection, ProvinceFeature } from "./types";

export const FRAME_LABELS = [
  "方案冻结",
  "省级初始行动",
  "车企初步 Top-K",
  "省级竞争反制",
  "车企报价",
  "省级回应",
  "车企最终重配",
  "环境结算",
] as const;

export const EVENT_AFTER_FRAME = 2;

export function frameDelta(code: string, frame: number): number {
  const numericCode = Number(code);
  const wave = Math.sin(numericCode * 0.63 + frame * 0.91);
  const trend = Math.cos(numericCode * 0.17 - frame * 0.54) * 0.38;
  return Number(((wave + trend) * (2.2 + frame * 0.62)).toFixed(2));
}

export function applyFrame(
  source: PresentationMapCollection,
  frame: number,
): PresentationMapCollection {
  return {
    ...source,
    features: source.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        delta: feature.properties.included_in_simulation
          ? frameDelta(feature.properties.province_code, frame)
          : 0,
        frame,
      },
    })),
  };
}

function ringBounds(feature: ProvinceFeature): [number, number, number, number] {
  const points = feature.geometry.coordinates.flat(2);
  return [
    Math.min(...points.map((point) => point[0])),
    Math.min(...points.map((point) => point[1])),
    Math.max(...points.map((point) => point[0])),
    Math.max(...points.map((point) => point[1])),
  ];
}

export function provinceCenter(feature: ProvinceFeature): [number, number] {
  const [west, south, east, north] = ringBounds(feature);
  return [(west + east) / 2, (south + north) / 2];
}

export function buildArcs(source: PresentationMapCollection, frame: number) {
  const byCode = new Map(
    source.features.map((feature) => [feature.properties.province_code, feature]),
  );
  const routes = [
    ["11", "13", "competition"],
    ["31", "34", "competition"],
    ["44", "42", "topk"],
    ["51", "50", "coordination"],
    ["61", "41", "topk"],
    ["32", "37", "competition"],
    ["33", "36", "coordination"],
    ["43", "45", "topk"],
    ["22", "23", "coordination"],
    ["53", "52", "competition"],
  ] as const;
  return routes.flatMap(([sourceCode, targetCode, kind], index) => {
    const sourceFeature = byCode.get(sourceCode);
    const targetFeature = byCode.get(targetCode);
    if (!sourceFeature || !targetFeature) return [];
    return [
      {
        id: `${kind}-${sourceCode}-${targetCode}`,
        source: provinceCenter(sourceFeature),
        target: provinceCenter(targetFeature),
        kind,
        active: index <= frame + 2,
      },
    ];
  });
}
