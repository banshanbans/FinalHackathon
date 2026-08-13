import { useMemo } from "react";

import type { PresentationFrame } from "./contracts";
import type { PresentationMapCollection } from "./tech-spike/types";

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
}

function polygons(coordinates: unknown): number[][][][] {
  if (!Array.isArray(coordinates)) return [];
  if (
    coordinates.length
    && Array.isArray(coordinates[0])
    && Array.isArray(coordinates[0][0])
    && typeof coordinates[0][0][0] === "number"
  ) return [coordinates as number[][][]];
  return coordinates.flatMap(polygons);
}

function color(value: number | null) {
  if (value == null) return "#111b29";
  if (value < -2) return "#6758c7";
  if (value < 0) return "#29385d";
  if (value < 20) return "#17293a";
  if (value < 60) return "#166873";
  if (value < 100) return "#22bdae";
  return "#75ead6";
}

export function PresentationMapFallback({ collection, frame, selectedCode, onSelect, ariaLabel = "全国省域兼容地图" }: {
  collection: PresentationMapCollection;
  frame: PresentationFrame;
  selectedCode: string | null;
  onSelect: (selection: ProvinceSelection) => void;
  ariaLabel?: string;
}) {
  const values = useMemo(() => new Map(frame.province_values.map((item) => [item.province_code, item.value])), [frame.province_values]);
  const [minX, minY, maxX, maxY] = collection.bbox;
  const width = maxX - minX;
  const height = maxY - minY;
  const path = (coordinates: unknown) => polygons(coordinates).map((polygon) => polygon.map((ring) => ring.map(([x, y], index) => `${index ? "L" : "M"}${((x - minX) / width * 1000).toFixed(2)},${((maxY - y) / height * 720).toFixed(2)}`).join(" ") + " Z").join(" ")).join(" ");
  const center = (coordinates: unknown) => {
    const points = polygons(coordinates).flat(2);
    const x = points.reduce((total, point) => total + point[0], 0) / points.length;
    const y = points.reduce((total, point) => total + point[1], 0) / points.length;
    return [((x - minX) / width) * 1000, ((maxY - y) / height) * 720] as const;
  };
  return <div aria-label={ariaLabel} className="presentation-map fallback-map">
    <svg role="img" viewBox="0 0 1000 720">
      <title>中国全国版图兼容地图；31 省参与推演，港澳台仅作版图展示</title>
      {collection.features.map((feature) => {
        const code = feature.properties.province_code;
        const context = feature.properties.region_role === "territory-context";
        const value = values.get(code) ?? null;
        return <path aria-label={`${feature.properties.name}${context ? "（版图展示，不参与推演）" : ""}`} className={`${context ? "territory-context" : "simulation-province"} ${selectedCode === code ? "selected" : ""}`} d={path(feature.geometry.coordinates)} fill={context ? "#12343e" : color(value)} key={code} onClick={context ? undefined : (event) => onSelect({ code, name: feature.properties.name, value, x: event.clientX, y: event.clientY })} tabIndex={context ? undefined : 0} />;
      })}
      {collection.features.filter((feature) => feature.properties.region_role === "territory-context").map((feature) => {
        const [x, y] = center(feature.geometry.coordinates);
        const code = feature.properties.province_code;
        return <text aria-label={`${feature.properties.name}，中国版图展示，不参与推演`} className="territory-map-label" key={`label-${code}`} x={x + 8} y={y + (code === "81" ? -7 : code === "82" ? 13 : 4)}>{feature.properties.name}</text>;
      })}
    </svg>
    <span className="fallback-badge">SVG COMPAT</span>
  </div>;
}
