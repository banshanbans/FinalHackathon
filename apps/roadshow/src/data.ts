import {
  RoadshowContentSchema,
  RoadshowFeatureCollectionSchema,
  validateRoadshowMap,
  type RoadshowContentV3,
  type RoadshowFeatureCollection,
} from "./contracts";

export interface RoadshowData {
  content: RoadshowContentV3;
  map: RoadshowFeatureCollection;
}

function assetUrl(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`;
}

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(assetUrl(path));
  if (!response.ok) throw new Error(`静态资源读取失败：${path}`);
  return response.json() as Promise<unknown>;
}

export async function loadRoadshowData(): Promise<RoadshowData> {
  const [contentInput, mapInput] = await Promise.all([
    fetchJson("data/roadshow-content.json"),
    fetchJson("data/china-presentation-map.geojson"),
  ]);
  const content = RoadshowContentSchema.parse(contentInput);
  const map = validateRoadshowMap(RoadshowFeatureCollectionSchema.parse(mapInput));
  return { content, map };
}
