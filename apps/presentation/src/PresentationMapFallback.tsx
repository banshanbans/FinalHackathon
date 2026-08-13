import { useMemo } from "react";

import type { PresentationMapFrame } from "./contracts";
import { colorForValue, visualScaleForFrame } from "./mapScale";
import type { PresentationVisualScale } from "./mapScale";
import type { PresentationMapCollection } from "./tech-spike/types";

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
}

const AUTOMAKER_NODES: Record<string, { label: string; position: readonly [number, number] }> = Object.fromEntries(
  [
    ["byd", "比亚迪"], ["geely", "吉利"], ["changan", "长安"],
    ["sgmw", "上汽通用五菱"], ["nio", "蔚来"], ["chery", "奇瑞"],
    ["leapmotor", "零跑"], ["seres", "赛力斯"], ["xiaomi_auto", "小米汽车"],
    ["li_auto", "理想汽车"],
  ].map(([id, label], index) => [id, { label: `${label} · 模拟`, position: [129, 49 - index * 3] as const }]),
);

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

export function PresentationMapFallback({ collection, frame, selectedCode, onSelect, ariaLabel = "全国省域兼容地图", visualScale }: {
  collection: PresentationMapCollection;
  frame: PresentationMapFrame;
  selectedCode: string | null;
  onSelect: (selection: ProvinceSelection) => void;
  ariaLabel?: string;
  visualScale?: PresentationVisualScale;
}) {
  const values = useMemo(() => new Map(frame.province_values.map((item) => [item.province_code, item.value])), [frame.province_values]);
  const scale = useMemo(() => visualScale ?? visualScaleForFrame(frame), [frame, visualScale]);
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
  const provinceCenters = useMemo(() => new Map(
    collection.features
      .filter((feature) => feature.properties.region_role === "simulation-province")
      .map((feature) => [feature.properties.province_code, center(feature.geometry.coordinates)]),
  ), [collection]);
  const projectPoint = ([longitude, latitude]: readonly [number, number]) => [
    ((longitude - minX) / width) * 1000,
    ((maxY - latitude) / height) * 720,
  ] as const;
  const eventCenter = [((104 - minX) / width) * 1000, ((maxY - 35) / height) * 720] as const;
  const activeAutomakerIds = Array.from(new Set(frame.overlay_records.flatMap((record) => [
    record.source_subject.startsWith("automaker:") ? record.source_subject.slice(10) : null,
    record.target_subject?.startsWith("automaker:") ? record.target_subject.slice(10) : null,
  ]).filter((value): value is string => Boolean(value))));
  return <div aria-label={ariaLabel} className={`presentation-map fallback-map branch-${frame.branch_role}`} data-overlay-count={frame.overlay_records.length} data-selected-code={selectedCode ?? ""}>
    <svg role="img" viewBox="0 0 1000 720">
      <title>中国全国版图兼容地图；31 省参与推演，港澳台仅作版图展示</title>
      {collection.features.map((feature) => {
        const code = feature.properties.province_code;
        const context = feature.properties.region_role === "territory-context";
        const value = values.get(code) ?? null;
        const select = (x: number, y: number) => onSelect({
          code,
          name: feature.properties.name,
          value,
          x,
          y,
        });
        return <path
          aria-label={`${feature.properties.name}${context ? "（版图展示，不参与推演）" : ""}`}
          className={`${context ? "territory-context" : "simulation-province"} ${selectedCode === code ? "selected" : ""}`}
          d={path(feature.geometry.coordinates)}
          fill={context ? "#12343e" : colorForValue(scale, value)}
          key={code}
          onClick={context ? undefined : (event) => select(event.clientX, event.clientY)}
          onKeyDown={context ? undefined : (event) => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            const bounds = event.currentTarget.getBoundingClientRect();
            select(bounds.left + bounds.width / 2, bounds.top + bounds.height / 2);
          }}
          tabIndex={context ? undefined : 0}
        />;
      })}
      <g aria-hidden="true" className="fallback-overlays">
        {frame.overlay_records.flatMap((record) => {
          const sourceCode = record.source_subject.startsWith("province:") ? record.source_subject.slice(9) : null;
          const targetCode = record.target_subject?.startsWith("province:") ? record.target_subject.slice(9) : null;
          const sourceAutomaker = record.source_subject.startsWith("automaker:") ? record.source_subject.slice(10) : null;
          const targetAutomaker = record.target_subject?.startsWith("automaker:") ? record.target_subject.slice(10) : null;
          const source = sourceCode
            ? provinceCenters.get(sourceCode)
            : sourceAutomaker && AUTOMAKER_NODES[sourceAutomaker]
              ? projectPoint(AUTOMAKER_NODES[sourceAutomaker].position)
              : record.source_subject.startsWith("event:")
                ? eventCenter
                : null;
          const target = targetCode
            ? provinceCenters.get(targetCode)
            : targetAutomaker && AUTOMAKER_NODES[targetAutomaker]
              ? projectPoint(AUTOMAKER_NODES[targetAutomaker].position)
              : null;
          if (!source || !target) return [];
          return <line className={`overlay-${record.kind} relation-${record.relation_semantic ?? "proposal"}`} key={record.overlay_id} x1={source[0]} x2={target[0]} y1={source[1]} y2={target[1]} />;
        })}
        {frame.overlay_records.some((record) => record.kind === "event") ? <circle className="event-pulse" cx={eventCenter[0]} cy={eventCenter[1]} r="11" /> : null}
        {activeAutomakerIds.flatMap((automakerId) => {
          const node = AUTOMAKER_NODES[automakerId];
          if (!node) return [];
          const [x, y] = projectPoint(node.position);
          return <g className="automaker-subject-node" key={`automaker-node-${automakerId}`}><circle cx={x} cy={y} r="5" /><text x={x + 9} y={y + 3}>{node.label}</text></g>;
        })}
      </g>
      {collection.features.filter((feature) => feature.properties.region_role === "territory-context").map((feature) => {
        const [x, y] = center(feature.geometry.coordinates);
        const code = feature.properties.province_code;
        return <text aria-label={`${feature.properties.name}，中国版图展示，不参与推演`} className="territory-map-label" key={`label-${code}`} x={x + 8} y={y + (code === "81" ? -7 : code === "82" ? 13 : 4)}>{feature.properties.name}</text>;
      })}
    </svg>
    <span className="fallback-badge">SVG COMPAT</span>
  </div>;
}
