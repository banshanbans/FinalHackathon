import { useEffect, useMemo, useState } from "react";

import type { PresentationMapFrame } from "./contracts";
import type { PresentationWorldLandmark } from "./m34Contracts";
import { colorForValue, visualScaleForFrame } from "./mapScale";
import type { PresentationVisualScale } from "./mapScale";
import { heightPixelsForValue } from "./presentationHeight";
import {
  AUTOMAKER_LABELS,
  automakerMapTrackPoints,
  featurePath,
  featureRepresentativePoint,
  interactionCurve,
  pathAtProgress,
  pointAtPathProgress,
  polylineSvgPath,
  provinceAnchorMap,
  projectMercator,
} from "./presentationGeometry";
import type { PresentationMapCollection } from "./tech-spike/types";
import {
  SOUTH_CHINA_SEA_BOUNDARY_CORNERS,
  SOUTH_CHINA_SEA_BOUNDARY_IMAGE_URL,
  SouthChinaSeaInset,
} from "./SouthChinaSeaInset";
import type { MapViewMode } from "./presentationView";

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
}

interface CameraTransform {
  scale: number;
  translateX: number;
  translateY: number;
}

const IDENTITY_CAMERA: CameraTransform = { scale: 1, translateX: 0, translateY: 0 };

function provinceCode(subjectRef: string | null | undefined): string | null {
  return subjectRef?.startsWith("province:") ? subjectRef.slice(9) : null;
}

function automakerId(subjectRef: string | null | undefined): string | null {
  return subjectRef?.startsWith("automaker:") ? subjectRef.slice(10) : null;
}

function transformPoint(
  point: readonly [number, number],
  camera: CameraTransform,
): [number, number] {
  return [
    point[0] * camera.scale + camera.translateX,
    point[1] * camera.scale + camera.translateY,
  ];
}

export function PresentationMapFallback({
  collection,
  frame,
  selectedCode,
  onSelect,
  ariaLabel = "全国省域兼容地图",
  visualScale,
  reducedMotion = false,
  focusSubjectRefs = [],
  automakerTrackIds = [],
  focusKey = "",
  interactionMode = false,
  onSessionSelect,
  onSubjectSelect,
  onError,
  landmarks = [],
  showBatteryLandmarks = true,
  showIndustrialLandmarks = false,
  viewMode = "top",
}: {
  collection: PresentationMapCollection;
  frame: PresentationMapFrame;
  selectedCode: string | null;
  onSelect: (selection: ProvinceSelection) => void;
  ariaLabel?: string;
  visualScale?: PresentationVisualScale;
  reducedMotion?: boolean;
  focusSubjectRefs?: string[];
  automakerTrackIds?: string[];
  focusKey?: string;
  interactionMode?: boolean;
  onSessionSelect?: (sessionId: string) => void;
  onSubjectSelect?: (subjectRef: string) => void;
  onError?: (message: string) => void;
  landmarks?: PresentationWorldLandmark[];
  showBatteryLandmarks?: boolean;
  showIndustrialLandmarks?: boolean;
  viewMode?: MapViewMode;
}) {
  const [camera, setCamera] = useState<CameraTransform>(IDENTITY_CAMERA);
  const [drawProgress, setDrawProgress] = useState(1);
  const [flowClock, setFlowClock] = useState(0);
  const values = useMemo(
    () => new Map(frame.province_values.map((item) => [item.province_code, item.value])),
    [frame.province_values],
  );
  const hasFrozenDevelopmentValues = useMemo(
    () => frame.province_values.some((item) => item.value != null && Number.isFinite(item.value)),
    [frame.province_values],
  );
  const scale = useMemo(() => visualScale ?? visualScaleForFrame(frame), [frame, visualScale]);
  const paths = useMemo(() => new Map(collection.features.map(
    (feature) => [feature.properties.province_code, featurePath(feature, collection.bbox)],
  )), [collection]);
  const provinceAnchors = useMemo(() => new Map(collection.features
    .filter((feature) => feature.properties.included_in_simulation)
    .map((feature) => [
      feature.properties.province_code,
      projectMercator(featureRepresentativePoint(feature), collection.bbox),
    ])), [collection]);
  const provinceGeoAnchors = useMemo(() => provinceAnchorMap(collection), [collection]);
  const focusProvinceCodes = useMemo(() => focusSubjectRefs
    .map(provinceCode)
    .filter((code): code is string => Boolean(code)), [focusSubjectRefs]);
  const interactionWeights = useMemo(() => {
    const result = new Map<string, number>();
    for (const record of frame.overlay_records) {
      for (const subject of [record.source_subject, record.target_subject]) {
        const code = provinceCode(subject);
        if (code) result.set(code, Math.max(result.get(code) ?? 0, record.weight ?? 0.5));
      }
    }
    if (!result.size) focusProvinceCodes.forEach((code) => result.set(code, 0.82));
    return result;
  }, [focusProvinceCodes, frame.overlay_records]);
  const activeAutomakerIds = useMemo(() => automakerTrackIds.length
    ? Array.from(new Set(automakerTrackIds))
    : Array.from(new Set(frame.overlay_records.flatMap((record) => [
      automakerId(record.source_subject), automakerId(record.target_subject),
    ]).filter((value): value is string => Boolean(value)))), [automakerTrackIds, frame.overlay_records]);
  const automakerGeoNodes = useMemo(
    () => automakerMapTrackPoints(activeAutomakerIds, provinceGeoAnchors),
    [activeAutomakerIds, provinceGeoAnchors],
  );
  const eventCenter: [number, number] = [104, 35];
  const southChinaSeaNorthWest = projectMercator(SOUTH_CHINA_SEA_BOUNDARY_CORNERS[0], collection.bbox);
  const southChinaSeaSouthEast = projectMercator(SOUTH_CHINA_SEA_BOUNDARY_CORNERS[2], collection.bbox);
  const overlayRevealKey = frame.overlay_records.map((record) => record.overlay_id).join("|");

  useEffect(() => {
    if (!focusProvinceCodes.length) return;
    const points = focusProvinceCodes
      .map((code) => provinceAnchors.get(code))
      .filter((point): point is [number, number] => Boolean(point));
    if (!points.length) {
      onError?.(`无法解析省域 ${focusProvinceCodes.join("、")} 的地图锚点`);
      return;
    }
    const center: [number, number] = [
      points.reduce((total, point) => total + point[0], 0) / points.length,
      points.reduce((total, point) => total + point[1], 0) / points.length,
    ];
    const targetScale = points.length > 1 ? 1.12 : 1.24;
    const target: CameraTransform = {
      scale: targetScale,
      translateX: 500 - center[0] * targetScale,
      translateY: 360 - center[1] * targetScale,
    };
    if (reducedMotion) {
      setCamera(target);
      return;
    }
    let animationFrame = 0;
    const startedAt = performance.now();
    const start = camera;
    const animate = (timestamp: number) => {
      const progress = Math.min(1, (timestamp - startedAt) / 1500);
      const eased = 1 - (1 - progress) ** 3;
      setCamera({
        scale: start.scale + (target.scale - start.scale) * eased,
        translateX: start.translateX + (target.translateX - start.translateX) * eased,
        translateY: start.translateY + (target.translateY - start.translateY) * eased,
      });
      if (progress < 1) animationFrame = requestAnimationFrame(animate);
    };
    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [focusKey, focusProvinceCodes, provinceAnchors, reducedMotion]);

  useEffect(() => {
    if (reducedMotion || !frame.overlay_records.some((record) => record.emphasized)) {
      setDrawProgress(1);
      return;
    }
    let animationFrame = 0;
    const startedAt = performance.now();
    setDrawProgress(0);
    const animate = (timestamp: number) => {
      const progress = Math.min(1, (timestamp - startedAt) / 800);
      setDrawProgress(1 - (1 - progress) ** 3);
      if (progress < 1) animationFrame = requestAnimationFrame(animate);
    };
    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [overlayRevealKey, reducedMotion]);

  useEffect(() => {
    if (reducedMotion || !frame.overlay_records.some((record) => record.emphasized)) return;
    const timer = window.setInterval(() => setFlowClock((value) => (value + 0.025) % 1), 40);
    return () => window.clearInterval(timer);
  }, [frame.overlay_records, reducedMotion]);

  const resolveGeoSubject = (subjectRef: string | null): [number, number] | null => {
    const code = provinceCode(subjectRef);
    if (code) return provinceGeoAnchors.get(code) ?? null;
    const automaker = automakerId(subjectRef);
    if (automaker) return automakerGeoNodes.get(automaker) ?? null;
    if (subjectRef?.startsWith("event:")) return eventCenter;
    return null;
  };
  const projectMapPoint = (point: readonly [number, number]): [number, number] => (
    transformPoint(projectMercator(point, collection.bbox), camera)
  );
  const resolveSubject = (subjectRef: string | null): [number, number] | null => {
    const point = resolveGeoSubject(subjectRef);
    return point ? projectMapPoint(point) : null;
  };
  const unresolved = frame.overlay_records.filter((record) => (
    !resolveSubject(record.source_subject) || !resolveSubject(record.target_subject)
  ));

  return <div
    aria-label={ariaLabel}
    className={`presentation-map fallback-map branch-${frame.branch_role} view-${viewMode} ${interactionMode ? "interaction-mode" : ""} ${selectedCode ? "selection-active" : ""}`}
    data-automaker-anchor-mode="map"
    data-focus-key={focusKey}
    data-finite-value-count={frame.province_values.filter((item) => item.value != null && Number.isFinite(item.value)).length}
    data-interaction-height-count={interactionWeights.size}
    data-overlay-count={frame.overlay_records.length}
    data-province-value-count={frame.province_values.length}
    data-selected-code={selectedCode ?? ""}
    data-view-mode={viewMode}
    data-height-encoding={viewMode === "side" ? "province-nev-development-index" : undefined}
  >
    <svg role="img" viewBox="0 0 1000 720">
      <title>中国全国版图兼容地图；31 省参与推演，港澳台仅作版图展示</title>
      <defs>
        <filter id="selected-province-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
        <marker id="fallback-arrow" markerHeight="6" markerWidth="7" orient="auto" refX="6" refY="3">
          <path d="M0,0 L6,3 L0,6 Z" fill="context-stroke" />
        </marker>
      </defs>
      <g className="fallback-geography" transform={`translate(${camera.translateX} ${camera.translateY}) scale(${camera.scale})`}>
        {collection.features.map((feature) => {
          const code = feature.properties.province_code;
          const context = feature.properties.region_role === "territory-context";
          const value = values.get(code) ?? null;
          const focused = focusProvinceCodes.includes(code);
          const select = (x: number, y: number) => onSelect({
            code,
            name: feature.properties.name,
            value,
            x,
            y,
          });
          const selected = selectedCode === code;
          return <g key={code}>
            {!context ? <path
              aria-hidden="true"
              className="province-underlay"
              d={paths.get(code)}
              fill="#101923"
              vectorEffect="non-scaling-stroke"
            /> : null}
            <path
              aria-label={`${feature.properties.name}${context ? "（版图展示，不参与推演）" : ""}`}
              className={`${context ? "territory-context" : "simulation-province"} ${focused ? "focused" : ""} ${selected ? "selected-base" : ""}`}
              d={paths.get(code)}
              fill={context ? "#12343e" : colorForValue(scale, value)}
              onClick={context ? undefined : (event) => select(event.clientX, event.clientY)}
              onKeyDown={context ? undefined : (event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                const bounds = event.currentTarget.getBoundingClientRect();
                select(bounds.left + bounds.width / 2, bounds.top + bounds.height / 2);
              }}
              tabIndex={context ? undefined : 0}
              vectorEffect="non-scaling-stroke"
            />
            {selected ? <>
              <path aria-hidden="true" className="selected-province-fill" d={paths.get(code)} vectorEffect="non-scaling-stroke" />
              <path aria-hidden="true" className="selected-province-glow" d={paths.get(code)} fill="transparent" filter="url(#selected-province-glow)" vectorEffect="non-scaling-stroke" />
              <path aria-hidden="true" className="selected-province-outline" d={paths.get(code)} fill="transparent" vectorEffect="non-scaling-stroke" />
            </> : null}
          </g>;
        })}
        {collection.features.filter((feature) => feature.properties.region_role === "territory-context").map((feature) => {
          const [x, y] = projectMercator(featureRepresentativePoint(feature), collection.bbox);
          const code = feature.properties.province_code;
          return <text
            aria-label={`${feature.properties.name}，中国版图展示，不参与推演`}
            className="territory-map-label"
            key={`label-${code}`}
            vectorEffect="non-scaling-stroke"
            x={x + 8}
            y={y + (code === "81" ? -7 : code === "82" ? 13 : 4)}
          >{feature.properties.name}</text>;
        })}
        <image
          aria-hidden="true"
          className="fallback-south-china-sea-boundary"
          data-map-source="MNR-standard-map-GS2016-1609"
          data-positioning="map-georeferenced"
          height={southChinaSeaSouthEast[1] - southChinaSeaNorthWest[1]}
          href={SOUTH_CHINA_SEA_BOUNDARY_IMAGE_URL}
          preserveAspectRatio="none"
          width={southChinaSeaSouthEast[0] - southChinaSeaNorthWest[0]}
          x={southChinaSeaNorthWest[0]}
          y={southChinaSeaNorthWest[1]}
        />
      </g>
      {viewMode === "side" ? <g className="fallback-height-columns" aria-label="省域新能源汽车发展指数高度">
        {frame.province_values.flatMap((item) => {
          const anchor = provinceGeoAnchors.get(item.province_code);
          const interactionWeight = interactionWeights.get(item.province_code);
          if (!anchor) return [];
          if (hasFrozenDevelopmentValues && (item.value == null || !Number.isFinite(item.value))) return [];
          if (!hasFrozenDevelopmentValues && interactionWeight == null) return [];
          const heightScale = hasFrozenDevelopmentValues
            ? scale
            : { domain: [0, 1], center: null, stops: [[0, "#1a5965"], [1, "#72ead8"]] } satisfies PresentationVisualScale;
          const heightValue = hasFrozenDevelopmentValues ? item.value! : interactionWeight!;
          const [x, y] = projectMapPoint(anchor);
          const focused = focusProvinceCodes.includes(item.province_code);
          const height = heightPixelsForValue(heightValue, heightScale) * (focused ? 1.2 : 1);
          return <g className={focused ? "focused" : ""} key={`height-${item.province_code}`}>
            <rect fill={focused ? "#f4bd69" : colorForValue(heightScale, heightValue)} height={height} rx="2" width="12" x={x - 6} y={y - height} />
            <path d={`M${x - 6},${y - height} l5,-5 h12 l-5,5 z`} fill="rgba(118,234,218,.52)" />
          </g>;
        })}
      </g> : null}
      <g className="fallback-overlays">
        {frame.overlay_records.flatMap((record) => {
          const source = resolveGeoSubject(record.source_subject);
          const target = resolveGeoSubject(record.target_subject);
          if (!source || !target) return [];
          const relation = record.relation_semantic ?? "proposal";
          const fullPath = interactionCurve(source, target, record.reveal_order ?? 0)
            .map(projectMapPoint);
          const visiblePath = record.emphasized && drawProgress < 1
            ? pathAtProgress(fullPath, drawProgress)
            : fullPath;
          const flowProgress = drawProgress < 1 ? drawProgress : flowClock;
          const flowPoint = pointAtPathProgress(fullPath, flowProgress);
          return <g key={record.overlay_id}>
            <path
              aria-label={record.label}
              className={`fallback-relation overlay-${record.kind} relation-${relation} ${record.emphasized ? "emphasized" : "background-relation"}`}
              d={polylineSvgPath(visiblePath)}
              markerEnd="url(#fallback-arrow)"
              onClick={() => record.session_id && onSessionSelect?.(record.session_id)}
              role={record.session_id ? "button" : undefined}
              tabIndex={record.session_id ? 0 : undefined}
              vectorEffect="non-scaling-stroke"
            />
            {record.emphasized && !reducedMotion ? <circle
              aria-hidden="true"
              className={`fallback-flow-point relation-${relation}`}
              cx={flowPoint[0]}
              cy={flowPoint[1]}
              r="4.5"
            /> : null}
          </g>;
        })}
        {landmarks.flatMap((landmark) => {
          if (landmark.kind === "battery_capability" && !showBatteryLandmarks) return [];
          if (landmark.kind === "industrial_facility" && !showIndustrialLandmarks) return [];
          const anchor = provinceGeoAnchors.get(landmark.province_code);
          if (!anchor) return [];
          const isBattery = landmark.kind === "battery_capability";
          const point = projectMapPoint([
            anchor[0] + (isBattery ? -0.13 : 0.13),
            anchor[1] + (isBattery ? 0.1 : -0.1),
          ]);
          return <g
            aria-label={`${landmark.province_name}${isBattery ? "电池能力" : "产业"}节点 ${landmark.node_count} 个，代理数据基线`}
            className={`fallback-landmark ${isBattery ? "battery" : "industrial"}`}
            key={landmark.landmark_id}
            onClick={() => onSubjectSelect?.(`province:${landmark.province_code}`)}
            role="button"
            tabIndex={0}
          >
            <circle cx={point[0]} cy={point[1]} r="12" />
            <image
              height="15"
              href={isBattery ? "/assets/icons/battery-capability.svg" : "/assets/icons/industrial-facility.svg"}
              width="15"
              x={point[0] - 7.5}
              y={point[1] - 7.5}
            />
            <text x={point[0] + 9} y={point[1] - 8}>{landmark.node_count}</text>
          </g>;
        })}
        {frame.overlay_records.some((record) => record.kind === "event") ? <circle
          className="event-pulse"
          cx={projectMapPoint(eventCenter)[0]}
          cy={projectMapPoint(eventCenter)[1]}
          r="11"
          vectorEffect="non-scaling-stroke"
        /> : null}
        {Array.from(automakerGeoNodes, ([id, anchor]) => {
          const point = projectMapPoint(anchor);
          return <g
          aria-label={`${AUTOMAKER_LABELS[id] ?? id}模拟主体`}
          className="automaker-subject-node"
          key={`automaker-node-${id}`}
          onClick={() => onSubjectSelect?.(`automaker:${id}`)}
          role="button"
          tabIndex={0}
        >
          <circle cx={point[0]} cy={point[1]} r="6" />
          <text x={point[0] + 11} y={point[1] + 4}>{AUTOMAKER_LABELS[id] ?? id} · 模拟</text>
        </g>;
        })}
        {frame.overlay_records.flatMap((record) => [record.source_subject, record.target_subject])
          .filter((subjectRef, index, items): subjectRef is string => Boolean(subjectRef) && items.indexOf(subjectRef) === index)
          .flatMap((subjectRef) => {
            const code = provinceCode(subjectRef);
            const point = resolveSubject(subjectRef);
            if (!code || !point) return [];
            return <g
              aria-label={`${collection.features.find((feature) => feature.properties.province_code === code)?.properties.name ?? code}互动主体`}
              className="province-subject-node"
              key={`province-node-${code}`}
              onClick={() => onSubjectSelect?.(subjectRef)}
              role="button"
              tabIndex={0}
            ><circle cx={point[0]} cy={point[1]} r="5" /></g>;
          })}
      </g>
      {unresolved.length ? <g className="map-anchor-error" role="alert">
        <rect height="34" rx="8" width="430" x="285" y="16" />
        <text x="500" y="38">{`关系锚点解析失败：${unresolved.length} 条连接未显示`}</text>
      </g> : null}
    </svg>
    <SouthChinaSeaInset />
    <span className="fallback-badge">SVG COMPAT</span>
  </div>;
}
