import { geoEquirectangular, geoPath, type GeoProjection } from "d3-geo";
import { CanvasTexture, LinearFilter, SRGBColorSpace } from "three";
import type { RoadshowFeatureCollection, RoadshowMapFeature } from "../contracts";
import { featureForD3 } from "./geo";

interface TextureSpec {
  width: number;
  height: number;
  projection: GeoProjection;
  fillSimulated: string;
  fillContext: string;
  stroke: string;
  lineWidth: number;
}

function drawFeature(
  context: CanvasRenderingContext2D,
  path: ReturnType<typeof geoPath>,
  feature: RoadshowMapFeature,
  spec: TextureSpec,
): void {
  context.beginPath();
  path(featureForD3(feature) as never);
  context.fillStyle =
    feature.properties.region_role === "simulation-province" ? spec.fillSimulated : spec.fillContext;
  context.fill("evenodd");
  context.strokeStyle = spec.stroke;
  context.lineWidth = spec.lineWidth;
  context.stroke();
}

function createTexture(collection: RoadshowFeatureCollection, spec: TextureSpec): CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = spec.width;
  canvas.height = spec.height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器无法创建地图纹理");
  context.clearRect(0, 0, spec.width, spec.height);
  context.lineJoin = "round";
  context.lineCap = "round";
  const path = geoPath(spec.projection, context);
  for (const feature of collection.features) drawFeature(context, path, feature, spec);
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.minFilter = LinearFilter;
  texture.magFilter = LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

export function createGlobeOverlayTexture(collection: RoadshowFeatureCollection): CanvasTexture {
  const width = 4096;
  const height = 2048;
  return createTexture(collection, {
    width,
    height,
    projection: geoEquirectangular().translate([width / 2, height / 2]).scale(width / (2 * Math.PI)),
    fillSimulated: "rgba(45, 193, 181, .84)",
    fillContext: "rgba(45, 193, 181, .38)",
    stroke: "rgba(194, 255, 247, .72)",
    lineWidth: 2.4,
  });
}

export const chinaLiftBounds = {
  longitudeMin: 72,
  longitudeMax: 136,
  latitudeMin: 16,
  latitudeMax: 55,
} as const;

export function createChinaLiftTexture(collection: RoadshowFeatureCollection): CanvasTexture {
  const width = 2048;
  const height = 1248;
  const longitudeCenter = (chinaLiftBounds.longitudeMin + chinaLiftBounds.longitudeMax) / 2;
  const latitudeCenter = (chinaLiftBounds.latitudeMin + chinaLiftBounds.latitudeMax) / 2;
  const longitudeSpan = chinaLiftBounds.longitudeMax - chinaLiftBounds.longitudeMin;
  const scale = width / ((longitudeSpan * Math.PI) / 180);

  return createTexture(collection, {
    width,
    height,
    projection: geoEquirectangular()
      .center([longitudeCenter, latitudeCenter])
      .translate([width / 2, height / 2])
      .scale(scale),
    fillSimulated: "rgba(34, 168, 158, .92)",
    fillContext: "rgba(34, 168, 158, .46)",
    stroke: "rgba(187, 255, 247, .88)",
    lineWidth: 2.6,
  });
}
