import type { PresentationMapCollection, ProvinceFeature } from "./tech-spike/types";

export type MapPoint = readonly [number, number];
export type MapRing = MapPoint[];
export type MapPolygon = MapRing[];

const EPSILON = 1e-9;

export const AUTOMAKER_LABELS: Readonly<Record<string, string>> = {
  byd: "比亚迪",
  geely: "吉利",
  changan: "长安",
  sgmw: "上汽通用五菱",
  nio: "蔚来",
  chery: "奇瑞",
  leapmotor: "零跑",
  seres: "赛力斯",
  xiaomi_auto: "小米汽车",
  li_auto: "理想汽车",
};

export function featurePolygons(feature: ProvinceFeature): MapPolygon[] {
  return feature.geometry.coordinates.map((polygon) => polygon.map(
    (ring) => ring.map((position) => [position[0], position[1]] as const),
  ));
}

function signedRingArea(ring: MapRing): number {
  let area = 0;
  for (let index = 0; index < ring.length - 1; index += 1) {
    const current = ring[index]!;
    const next = ring[index + 1]!;
    area += current[0] * next[1] - next[0] * current[1];
  }
  return area / 2;
}

function polygonArea(polygon: MapPolygon): number {
  if (!polygon[0]) return 0;
  return Math.abs(signedRingArea(polygon[0]))
    - polygon.slice(1).reduce((total, ring) => total + Math.abs(signedRingArea(ring)), 0);
}

export function largestFeaturePolygon(feature: ProvinceFeature): MapPolygon {
  const candidates = featurePolygons(feature);
  const polygon = [...candidates].sort((left, right) => polygonArea(right) - polygonArea(left))[0];
  if (!polygon?.[0]?.length) throw new Error(`省域 ${feature.properties.province_code} 缺少有效主体面`);
  return polygon;
}

function ringCentroid(ring: MapRing): MapPoint | null {
  let crossSum = 0;
  let longitudeSum = 0;
  let latitudeSum = 0;
  for (let index = 0; index < ring.length - 1; index += 1) {
    const current = ring[index]!;
    const next = ring[index + 1]!;
    const cross = current[0] * next[1] - next[0] * current[1];
    crossSum += cross;
    longitudeSum += (current[0] + next[0]) * cross;
    latitudeSum += (current[1] + next[1]) * cross;
  }
  if (Math.abs(crossSum) < EPSILON) return null;
  return [longitudeSum / (3 * crossSum), latitudeSum / (3 * crossSum)];
}

function pointOnSegment(point: MapPoint, start: MapPoint, end: MapPoint): boolean {
  const cross = (point[1] - start[1]) * (end[0] - start[0])
    - (point[0] - start[0]) * (end[1] - start[1]);
  if (Math.abs(cross) > EPSILON) return false;
  const dot = (point[0] - start[0]) * (end[0] - start[0])
    + (point[1] - start[1]) * (end[1] - start[1]);
  if (dot < -EPSILON) return false;
  const lengthSquared = (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2;
  return dot <= lengthSquared + EPSILON;
}

function pointInRing(point: MapPoint, ring: MapRing): boolean {
  let inside = false;
  for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index, index += 1) {
    const currentPoint = ring[index]!;
    const previousPoint = ring[previous]!;
    if (pointOnSegment(point, previousPoint, currentPoint)) return true;
    const crosses = (currentPoint[1] > point[1]) !== (previousPoint[1] > point[1]);
    if (!crosses) continue;
    const longitude = (previousPoint[0] - currentPoint[0])
      * (point[1] - currentPoint[1])
      / (previousPoint[1] - currentPoint[1])
      + currentPoint[0];
    if (point[0] < longitude) inside = !inside;
  }
  return inside;
}

export function pointInPolygon(point: MapPoint, polygon: MapPolygon): boolean {
  if (!polygon[0] || !pointInRing(point, polygon[0])) return false;
  return !polygon.slice(1).some((hole) => pointInRing(point, hole));
}

export function pointInFeature(point: MapPoint, feature: ProvinceFeature): boolean {
  return featurePolygons(feature).some((polygon) => pointInPolygon(point, polygon));
}

function segmentDistance(point: MapPoint, start: MapPoint, end: MapPoint): number {
  const lengthSquared = (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2;
  if (lengthSquared <= EPSILON) return Math.hypot(point[0] - start[0], point[1] - start[1]);
  const progress = Math.max(0, Math.min(1, (
    (point[0] - start[0]) * (end[0] - start[0])
    + (point[1] - start[1]) * (end[1] - start[1])
  ) / lengthSquared));
  return Math.hypot(
    point[0] - (start[0] + progress * (end[0] - start[0])),
    point[1] - (start[1] + progress * (end[1] - start[1])),
  );
}

function distanceToBoundary(point: MapPoint, polygon: MapPolygon): number {
  let distance = Number.POSITIVE_INFINITY;
  for (const ring of polygon) {
    for (let index = 0; index < ring.length - 1; index += 1) {
      distance = Math.min(distance, segmentDistance(point, ring[index]!, ring[index + 1]!));
    }
  }
  return distance;
}

export function featureRepresentativePoint(feature: ProvinceFeature): [number, number] {
  const polygon = largestFeaturePolygon(feature);
  const centroid = ringCentroid(polygon[0]!);
  if (centroid && pointInPolygon(centroid, polygon)) return [centroid[0], centroid[1]];

  const outerRing = polygon[0]!;
  const longitudes = outerRing.map((point) => point[0]);
  const latitudes = outerRing.map((point) => point[1]);
  const bounds = [
    Math.min(...longitudes), Math.min(...latitudes),
    Math.max(...longitudes), Math.max(...latitudes),
  ] as const;
  let bestPoint: MapPoint | null = null;
  let bestDistance = -1;
  const gridSize = 36;
  for (let row = 0; row < gridSize; row += 1) {
    for (let column = 0; column < gridSize; column += 1) {
      const point: MapPoint = [
        bounds[0] + (column + 0.5) / gridSize * (bounds[2] - bounds[0]),
        bounds[1] + (row + 0.5) / gridSize * (bounds[3] - bounds[1]),
      ];
      if (!pointInPolygon(point, polygon)) continue;
      const distance = distanceToBoundary(point, polygon);
      if (distance > bestDistance) {
        bestDistance = distance;
        bestPoint = point;
      }
    }
  }
  if (bestPoint) return [bestPoint[0], bestPoint[1]];
  const fallback = outerRing.find((point) => pointInPolygon(point, polygon));
  if (fallback) return [fallback[0], fallback[1]];
  throw new Error(`省域 ${feature.properties.province_code} 无法计算内部锚点`);
}

export function mercatorLatitude(latitude: number): number {
  const clamped = Math.max(-85.05112878, Math.min(85.05112878, latitude));
  const radians = clamped * Math.PI / 180;
  return Math.log(Math.tan(Math.PI / 4 + radians / 2));
}

export function projectMercator(
  point: MapPoint,
  bbox: readonly [number, number, number, number],
  canvasWidth = 1000,
  canvasHeight = 720,
): [number, number] {
  const [west, south, east, north] = bbox;
  const northY = mercatorLatitude(north);
  const southY = mercatorLatitude(south);
  return [
    (point[0] - west) / (east - west) * canvasWidth,
    (northY - mercatorLatitude(point[1])) / (northY - southY) * canvasHeight,
  ];
}

function pathSegmentLengths(points: readonly MapPoint[]): {
  lengths: number[];
  total: number;
} {
  const lengths: number[] = [];
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1]!;
    const current = points[index]!;
    const length = Math.hypot(current[0] - previous[0], current[1] - previous[1]);
    lengths.push(length);
    total += length;
  }
  return { lengths, total };
}

/**
 * Returns one stable sampled quadratic curve used by both Deck.gl and SVG.
 * Every animation position is derived from this polyline, so the moving point
 * cannot diverge from the visible relationship path.
 */
export function interactionCurve(
  source: MapPoint,
  target: MapPoint,
  revealOrder: number,
  steps = 40,
): MapPoint[] {
  const dx = target[0] - source[0];
  const dy = target[1] - source[1];
  const distance = Math.hypot(dx, dy);
  if (distance <= EPSILON) return [[source[0], source[1]], [target[0], target[1]]];
  const direction = revealOrder % 2 === 0 ? 1 : -1;
  const bend = Math.min(3.2, Math.max(0.32, distance * 0.17))
    * direction
    * (1 + Math.min(4, revealOrder) * 0.08);
  const control: MapPoint = [
    (source[0] + target[0]) / 2 - dy / distance * bend,
    (source[1] + target[1]) / 2 + dx / distance * bend,
  ];
  const sampleCount = Math.max(8, Math.floor(steps));
  return Array.from({ length: sampleCount + 1 }, (_, index) => {
    const progress = index / sampleCount;
    const remaining = 1 - progress;
    return [
      remaining * remaining * source[0]
        + 2 * remaining * progress * control[0]
        + progress * progress * target[0],
      remaining * remaining * source[1]
        + 2 * remaining * progress * control[1]
        + progress * progress * target[1],
    ] as MapPoint;
  });
}

export function pointAtPathProgress(
  points: readonly MapPoint[],
  progress: number,
): [number, number] {
  const first = points[0];
  if (!first) throw new Error("互动路径不能为空");
  if (points.length === 1 || progress <= 0) return [first[0], first[1]];
  const last = points[points.length - 1]!;
  if (progress >= 1) return [last[0], last[1]];
  const { lengths, total } = pathSegmentLengths(points);
  if (total <= EPSILON) return [last[0], last[1]];
  const targetDistance = progress * total;
  let elapsed = 0;
  for (let index = 0; index < lengths.length; index += 1) {
    const length = lengths[index]!;
    if (elapsed + length < targetDistance) {
      elapsed += length;
      continue;
    }
    const start = points[index]!;
    const end = points[index + 1]!;
    const local = length <= EPSILON ? 1 : (targetDistance - elapsed) / length;
    return [
      start[0] + (end[0] - start[0]) * local,
      start[1] + (end[1] - start[1]) * local,
    ];
  }
  return [last[0], last[1]];
}

export function pathAtProgress(
  points: readonly MapPoint[],
  progress: number,
): MapPoint[] {
  if (!points.length) return [];
  if (progress >= 1) return points.map((point) => [point[0], point[1]] as MapPoint);
  if (progress <= 0) return [[points[0]![0], points[0]![1]]];
  const endpoint = pointAtPathProgress(points, progress);
  const { lengths, total } = pathSegmentLengths(points);
  const targetDistance = progress * total;
  const partial: MapPoint[] = [[points[0]![0], points[0]![1]]];
  let elapsed = 0;
  for (let index = 0; index < lengths.length; index += 1) {
    const length = lengths[index]!;
    if (elapsed + length >= targetDistance) break;
    partial.push(points[index + 1]!);
    elapsed += length;
  }
  partial.push(endpoint);
  return partial;
}

export function polylineSvgPath(points: readonly MapPoint[]): string {
  return points.map((point, index) => (
    `${index === 0 ? "M" : "L"}${point[0].toFixed(2)},${point[1].toFixed(2)}`
  )).join(" ");
}

export function featurePath(
  feature: ProvinceFeature,
  bbox: readonly [number, number, number, number],
): string {
  return featurePolygons(feature).map((polygon) => polygon.map((ring) => ring.map((point, index) => {
    const [x, y] = projectMercator(point, bbox);
    return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ") + " Z").join(" ")).join(" ");
}

export function provinceAnchorMap(collection: PresentationMapCollection): Map<string, [number, number]> {
  return new Map(collection.features
    .filter((feature) => feature.properties.included_in_simulation)
    .map((feature) => [feature.properties.province_code, featureRepresentativePoint(feature)]));
}

export function featureBounds(feature: ProvinceFeature): [number, number, number, number] {
  const positions = featurePolygons(feature).flatMap((polygon) => polygon.flatMap((ring) => ring));
  const longitudes = positions.map((position) => position[0]!);
  const latitudes = positions.map((position) => position[1]!);
  return [Math.min(...longitudes), Math.min(...latitudes), Math.max(...longitudes), Math.max(...latitudes)];
}

export function automakerMapTrackPoints(
  automakerIds: readonly string[],
  provinceAnchors: ReadonlyMap<string, readonly [number, number]>,
): Map<string, [number, number]> {
  const presentationAnchors: Record<string, { provinceCode: string; offset: [number, number] }> = {
    byd: { provinceCode: "44", offset: [0, 0] },
    geely: { provinceCode: "33", offset: [-0.24, 0.16] },
    changan: { provinceCode: "50", offset: [-0.2, 0.14] },
    sgmw: { provinceCode: "45", offset: [0, 0] },
    nio: { provinceCode: "34", offset: [-0.24, 0.16] },
    chery: { provinceCode: "34", offset: [0.24, -0.16] },
    leapmotor: { provinceCode: "33", offset: [0.24, -0.16] },
    seres: { provinceCode: "50", offset: [0.2, -0.14] },
    xiaomi_auto: { provinceCode: "11", offset: [-0.08, 0.06] },
    li_auto: { provinceCode: "11", offset: [0.08, -0.06] },
  };
  return new Map(automakerIds.flatMap((id) => {
    const definition = presentationAnchors[id];
    const provinceAnchor = definition ? provinceAnchors.get(definition.provinceCode) : null;
    if (!definition || !provinceAnchor) return [];
    // These are stable cartographic anchors for simulated subjects. They group
    // the subject with a representative province and do not assert a real HQ,
    // facility, investment, or operational location.
    return [[id, [
      provinceAnchor[0] + definition.offset[0],
      provinceAnchor[1] + definition.offset[1],
    ] as [number, number]]];
  }));
}
