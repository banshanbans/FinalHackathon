import { ArcLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";
import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useMemo, useRef, useState } from "react";

import type { PresentationCamera, PresentationMapFrame, PresentationOverlayKind } from "./contracts";
import { visualScaleForFrame } from "./mapScale";
import type { PresentationVisualScale } from "./mapScale";
import type { PresentationMapCollection } from "./tech-spike/types";

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
}

interface ArcRecord {
  id: string;
  source: [number, number];
  target: [number, number];
  kind: PresentationOverlayKind;
  weight: number;
}

interface EventPoint {
  id: string;
  position: [number, number];
  weight: number;
}

interface SubjectNode {
  id: string;
  label: string;
  position: [number, number];
}

const AUTOMAKER_NODES: Record<string, SubjectNode> = Object.fromEntries(
  [
    ["byd", "比亚迪"],
    ["geely", "吉利"],
    ["changan", "长安"],
    ["sgmw", "上汽通用五菱"],
    ["nio", "蔚来"],
    ["chery", "奇瑞"],
    ["leapmotor", "零跑"],
    ["seres", "赛力斯"],
    ["xiaomi_auto", "小米汽车"],
    ["li_auto", "理想汽车"],
  ].map(([id, label], index) => [id, {
    id,
    label: `${label} · 模拟`,
    position: [129, 49 - index * 3] as [number, number],
  }]),
);

const ARC_COLORS: Record<PresentationOverlayKind, [number, number, number, number]> = {
  competition: [244, 92, 112, 220],
  negotiation: [245, 184, 95, 228],
  coordination: [54, 220, 197, 232],
  topk: [143, 125, 255, 220],
  event: [244, 173, 87, 230],
  automaker: [68, 194, 220, 220],
};

maplibregl.setWorkerUrl(maplibreWorkerUrl);

function coordinatePairs(value: unknown): [number, number][] {
  if (
    Array.isArray(value)
    && value.length === 2
    && typeof value[0] === "number"
    && typeof value[1] === "number"
  ) {
    return [[value[0], value[1]]];
  }
  return Array.isArray(value) ? value.flatMap(coordinatePairs) : [];
}

function featureCenter(feature: PresentationMapCollection["features"][number]): [number, number] {
  const valid = coordinatePairs(feature.geometry.coordinates).filter(
    (point) => Number.isFinite(point[0]) && Number.isFinite(point[1]),
  );
  if (!valid.length) throw new Error(`省域 ${feature.properties.province_code} 缺少有效坐标`);
  const sum = valid.reduce<[number, number]>(
    (current, point) => [current[0] + point[0], current[1] + point[1]],
    [0, 0],
  );
  return [sum[0] / valid.length, sum[1] / valid.length];
}

function projection(frame: PresentationMapFrame, collection: PresentationMapCollection) {
  const values = new Map(frame.province_values.map((item) => [item.province_code, item]));
  return {
    ...collection,
    features: collection.features.map((item) => {
      const value = values.get(item.properties.province_code);
      return {
        ...item,
        properties: {
          ...item.properties,
          value: item.properties.included_in_simulation ? (value?.value ?? 0) : 0,
          missing: item.properties.included_in_simulation ? (value?.missing ?? true) : false,
        },
      };
    }),
  } satisfies GeoJSON.FeatureCollection;
}

function fillColorExpression(
  frame: PresentationMapFrame,
  visualScale?: PresentationVisualScale,
): maplibregl.ExpressionSpecification {
  const scale = visualScale ?? visualScaleForFrame(frame);
  const valueExpression = [
    "interpolate",
    ["linear"],
    ["get", "value"],
    ...scale.stops.flatMap(([value, color]) => [value, color]),
  ] as unknown as maplibregl.ExpressionSpecification;
  return [
    "case",
    ["==", ["get", "region_role"], "territory-context"],
    "#12343e",
    ["get", "missing"],
    "#111b29",
    valueExpression,
  ] as unknown as maplibregl.ExpressionSpecification;
}

export function PresentationMap({
  collection,
  frame,
  reducedMotion,
  selectedCode,
  onSelect,
  onError,
  ariaLabel = "全国省域推演地图",
  cameraSync,
  onCameraChange,
  onFatal,
  visualScale,
}: {
  collection: PresentationMapCollection;
  frame: PresentationMapFrame;
  reducedMotion: boolean;
  selectedCode: string | null;
  onSelect: (selection: ProvinceSelection) => void;
  onError: (message: string) => void;
  ariaLabel?: string;
  cameraSync?: PresentationCamera;
  onCameraChange?: (camera: PresentationCamera) => void;
  onFatal?: (message: string) => void;
  visualScale?: PresentationVisualScale;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const frameRef = useRef(frame);
  const visualScaleRef = useRef(visualScale);
  const selectedCodeRef = useRef(selectedCode);
  const appliedSelectedCodeRef = useRef<string | null>(null);
  const onSelectRef = useRef(onSelect);
  const onErrorRef = useRef(onError);
  const onFatalRef = useRef(onFatal);
  const onCameraChangeRef = useRef(onCameraChange);
  const centers = useMemo(
    () => new Map(
      collection.features
        .filter((item) => item.properties.included_in_simulation)
        .map((item) => [item.properties.province_code, featureCenter(item)]),
    ),
    [collection],
  );

  useEffect(() => {
    frameRef.current = frame;
  }, [frame]);

  useEffect(() => {
    visualScaleRef.current = visualScale;
  }, [visualScale]);

  useEffect(() => {
    selectedCodeRef.current = selectedCode;
  }, [selectedCode]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    onFatalRef.current = onFatal;
  }, [onFatal]);

  useEffect(() => {
    onCameraChangeRef.current = onCameraChange;
  }, [onCameraChange]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let active = true;
    setMapReady(false);
    const territoryMarkers: maplibregl.Marker[] = [];
    try {
      const map = new maplibregl.Map({
        container: containerRef.current,
        style: {
          version: 8,
          sources: {},
          layers: [{ id: "space", type: "background", paint: { "background-color": "#030812" } }],
        },
        center: [frame.map_projection.camera.longitude, frame.map_projection.camera.latitude],
        zoom: frame.map_projection.camera.zoom,
        pitch: frame.map_projection.camera.pitch,
        bearing: frame.map_projection.camera.bearing,
        minZoom: 2.1,
        maxZoom: 7,
        attributionControl: false,
        renderWorldCopies: false,
        canvasContextAttributes: { antialias: true, preserveDrawingBuffer: true },
      });
      mapRef.current = map;
      map.on("error", (event: maplibregl.ErrorEvent) => active && onErrorRef.current(event.error?.message ?? "地图渲染失败"));
      const canvas = map.getCanvas();
      const loseContext = (event: Event) => {
        event.preventDefault();
        onFatalRef.current?.("WebGL 上下文中断，已切换兼容地图。");
      };
      canvas.addEventListener("webglcontextlost", loseContext);
      map.on("load", () => {
        if (!active) return;
        map.addSource("provinces", { type: "geojson", data: projection(frameRef.current, collection), promoteId: "province_code" });
        map.addLayer({
          id: "province-halo",
          type: "line",
          source: "provinces",
          filter: ["==", ["get", "region_role"], "simulation-province"],
          paint: { "line-color": "rgba(67,188,220,.18)", "line-width": 9, "line-blur": 7 },
        });
        map.addLayer({
          id: "province-fill",
          type: "fill",
          source: "provinces",
          paint: {
            "fill-color": fillColorExpression(frameRef.current, visualScaleRef.current),
            "fill-color-transition": { duration: 420, delay: 0 },
            "fill-opacity": [
              "case",
              ["==", ["get", "region_role"], "territory-context"], 0.72,
              0.9,
            ],
          },
        });
        map.addLayer({
          id: "province-selected-fill",
          type: "fill",
          source: "provinces",
          filter: ["==", ["get", "region_role"], "simulation-province"],
          paint: {
            "fill-color": "#f4d49b",
            "fill-opacity": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              0.3,
              0,
            ],
            "fill-opacity-transition": { duration: 260, delay: 0 },
          },
        });
        map.addLayer({
          id: "province-outline",
          type: "line",
          source: "provinces",
          paint: {
            "line-color": [
              "case",
              ["==", ["get", "region_role"], "territory-context"],
              "rgba(117,234,214,.76)",
              "rgba(177,220,234,.62)",
            ],
            "line-width": [
              "case",
              ["==", ["get", "region_role"], "territory-context"], 1.1,
              0.8,
            ],
          },
        });
        map.addLayer({
          id: "province-selected-outline",
          type: "line",
          source: "provinces",
          filter: ["==", ["get", "region_role"], "simulation-province"],
          paint: {
            "line-color": "#f7d99e",
            "line-opacity": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              1,
              0,
            ],
            "line-width": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              2.2,
              0,
            ],
            "line-blur": 0.35,
            "line-opacity-transition": { duration: 220, delay: 0 },
            "line-width-transition": { duration: 220, delay: 0 },
          },
        });
        if (selectedCodeRef.current) {
          map.setFeatureState(
            { source: "provinces", id: selectedCodeRef.current },
            { selected: true },
          );
          appliedSelectedCodeRef.current = selectedCodeRef.current;
        }
        for (const feature of collection.features.filter(
          (item) => item.properties.region_role === "territory-context",
        )) {
          const code = feature.properties.province_code;
          const label = document.createElement("span");
          label.className = "territory-map-label";
          label.textContent = feature.properties.name;
          label.title = `${feature.properties.name}：中国版图展示，不参与本次推演计算`;
          label.setAttribute(
            "aria-label",
            `${feature.properties.name}，中国版图展示，不参与推演`,
          );
          const marker = new maplibregl.Marker({
            element: label,
            anchor: "left",
            offset: code === "81" ? [7, -8] : code === "82" ? [7, 9] : [8, 0],
          })
            .setLngLat(featureCenter(feature))
            .addTo(map);
          territoryMarkers.push(marker);
        }
        const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
        overlayRef.current = overlay;
        map.addControl(overlay as unknown as maplibregl.IControl);
        map.fitBounds([[collection.bbox[0], collection.bbox[1]], [collection.bbox[2], collection.bbox[3]]], { padding: 82, duration: 0 });
        setMapReady(true);
      });
      const selectProvince = (event: MapMouseEvent) => {
        const hit = map.queryRenderedFeatures(event.point, { layers: ["province-fill"] })[0];
        const code = hit?.properties?.province_code as string | undefined;
        if (!code || hit?.properties?.region_role !== "simulation-province") return;
        const value = frameRef.current.province_values.find((item) => item.province_code === code)?.value ?? null;
        const bounds = map.getCanvas().getBoundingClientRect();
        onSelectRef.current({
          code,
          name: String(hit.properties?.name ?? code),
          value,
          x: bounds.left + event.point.x,
          y: bounds.top + event.point.y,
        });
      };
      map.on("click", "province-fill", selectProvince);
      map.on("mouseenter", "province-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "province-fill", () => { map.getCanvas().style.cursor = ""; });
      const publishCamera = () => {
        const center = map.getCenter();
        onCameraChangeRef.current?.({
          longitude: center.lng,
          latitude: center.lat,
          zoom: map.getZoom(),
          pitch: map.getPitch(),
          bearing: map.getBearing(),
        });
      };
      map.on("moveend", publishCamera);
      return () => {
        active = false;
        map.off("click", "province-fill", selectProvince);
        map.off("moveend", publishCamera);
        canvas.removeEventListener("webglcontextlost", loseContext);
        territoryMarkers.forEach((marker) => marker.remove());
        map.remove();
        mapRef.current = null;
        overlayRef.current = null;
        setMapReady(false);
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "地图初始化失败";
      onErrorRef.current(message);
      onFatalRef.current?.(message);
      return undefined;
    }
  }, [collection]);

  useEffect(() => {
    const map = mapRef.current;
    if (
      !mapReady
      || !map?.isStyleLoaded()
      || !map.getSource("provinces")
      || !map.getLayer("province-fill")
    ) return;
    const source = map.getSource("provinces") as maplibregl.GeoJSONSource | undefined;
    source?.setData(projection(frame, collection));
    map.setPaintProperty("province-fill", "fill-color", fillColorExpression(frame, visualScale));
    const camera = frame.map_projection.camera;
    map.easeTo({ center: [camera.longitude, camera.latitude], zoom: camera.zoom, pitch: camera.pitch, bearing: camera.bearing, duration: reducedMotion ? 0 : 760 });

    const arcs = frame.overlay_records.flatMap<ArcRecord>((record) => {
      const sourceCode = record.source_subject.startsWith("province:") ? record.source_subject.slice(9) : null;
      const targetCode = record.target_subject?.startsWith("province:") ? record.target_subject.slice(9) : null;
      const sourceAutomaker = record.source_subject.startsWith("automaker:")
        ? record.source_subject.slice(10)
        : null;
      const targetAutomaker = record.target_subject?.startsWith("automaker:")
        ? record.target_subject.slice(10)
        : null;
      const sourceCenter = sourceCode
        ? centers.get(sourceCode)
        : sourceAutomaker
          ? AUTOMAKER_NODES[sourceAutomaker]?.position
        : record.source_subject.startsWith("event:")
          ? [104, 35] as [number, number]
          : undefined;
      const targetCenter = targetCode
        ? centers.get(targetCode)
        : targetAutomaker
          ? AUTOMAKER_NODES[targetAutomaker]?.position
          : undefined;
      if (!sourceCenter || !targetCenter) return [];
      return [{ id: record.overlay_id, source: sourceCenter, target: targetCenter, kind: record.kind, weight: record.weight ?? 0.5 }];
    });
    const subjectNodes = Array.from(new Set(frame.overlay_records.flatMap((record) => [
      record.source_subject.startsWith("automaker:") ? record.source_subject.slice(10) : null,
      record.target_subject?.startsWith("automaker:") ? record.target_subject.slice(10) : null,
    ]).filter((value): value is string => Boolean(value))))
      .flatMap((automakerId) => AUTOMAKER_NODES[automakerId] ? [AUTOMAKER_NODES[automakerId]!] : []);
    const eventPoints = frame.overlay_records.flatMap<EventPoint>((record) => {
      if (record.kind !== "event" || !record.source_subject.startsWith("event:")) return [];
      const targetCode = record.target_subject?.startsWith("province:")
        ? record.target_subject.slice(9)
        : null;
      return [{
        id: record.overlay_id,
        position: targetCode ? centers.get(targetCode) ?? [104, 35] : [104, 35],
        weight: record.weight ?? 0.5,
      }];
    });
    overlayRef.current?.setProps({
      layers: [
        new ArcLayer<ArcRecord>({
          id: `presentation-arcs-${frame.frame_id}`,
          data: arcs,
          getSourcePosition: (item) => item.source,
          getTargetPosition: (item) => item.target,
          getSourceColor: (item) => ARC_COLORS[item.kind],
          getTargetColor: (item) => ARC_COLORS[item.kind],
          getWidth: (item) => 1.2 + item.weight * 2.3,
          greatCircle: true,
          widthMinPixels: 1.5,
          widthMaxPixels: 5,
          pickable: false,
        }),
        new ScatterplotLayer<EventPoint>({
          id: `presentation-event-points-${frame.frame_id}`,
          data: eventPoints,
          getPosition: (item) => item.position,
          getRadius: (item) => 18_000 + item.weight * 52_000,
          getFillColor: [244, 173, 87, 104],
          getLineColor: [255, 205, 128, 235],
          lineWidthMinPixels: 2,
          radiusMinPixels: 9,
          radiusMaxPixels: 34,
          stroked: true,
          pickable: false,
        }),
        new ScatterplotLayer<SubjectNode>({
          id: `presentation-automaker-nodes-${frame.frame_id}`,
          data: subjectNodes,
          getPosition: (item) => item.position,
          getRadius: 20_000,
          getFillColor: frame.branch_role === "control" ? [42, 51, 116, 0] : [36, 187, 207, 205],
          getLineColor: frame.branch_role === "control" ? [132, 145, 255, 240] : [168, 239, 246, 235],
          lineWidthMinPixels: 1.5,
          radiusMinPixels: 5,
          radiusMaxPixels: 9,
          stroked: true,
          pickable: false,
        }),
        new TextLayer<SubjectNode>({
          id: `presentation-automaker-labels-${frame.frame_id}`,
          data: subjectNodes,
          getPosition: (item) => item.position,
          getText: (item) => item.label,
          getColor: [215, 244, 248, 230],
          getSize: 11,
          getPixelOffset: [9, 0],
          getTextAnchor: "start",
          getAlignmentBaseline: "center",
          billboard: true,
          pickable: false,
        }),
      ],
    });
  }, [centers, collection, frame, mapReady, reducedMotion, visualScale]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map?.getSource("provinces")) return;
    const previousCode = appliedSelectedCodeRef.current;
    if (previousCode && previousCode !== selectedCode) {
      map.setFeatureState({ source: "provinces", id: previousCode }, { selected: false });
    }
    if (selectedCode) {
      map.setFeatureState({ source: "provinces", id: selectedCode }, { selected: true });
    }
    selectedCodeRef.current = selectedCode;
    appliedSelectedCodeRef.current = selectedCode;
  }, [mapReady, selectedCode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !cameraSync) return;
    const center = map.getCenter();
    const changed = Math.abs(center.lng - cameraSync.longitude) > 1e-5
      || Math.abs(center.lat - cameraSync.latitude) > 1e-5
      || Math.abs(map.getZoom() - cameraSync.zoom) > 1e-5
      || Math.abs(map.getPitch() - cameraSync.pitch) > 1e-5
      || Math.abs(map.getBearing() - cameraSync.bearing) > 1e-5;
    if (changed) map.jumpTo({
      center: [cameraSync.longitude, cameraSync.latitude],
      zoom: cameraSync.zoom,
      pitch: cameraSync.pitch,
      bearing: cameraSync.bearing,
    });
  }, [cameraSync]);

  return <div aria-label={ariaLabel} className={`presentation-map branch-${frame.branch_role}`} data-selected-code={selectedCode ?? undefined} ref={containerRef} />;
}
