import type { PickingInfo } from "@deck.gl/core";
import { IconLayer, PathLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";
import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useMemo, useRef, useState } from "react";

import type { PresentationCamera, PresentationMapFrame, PresentationOverlayKind, PresentationOverlayRecord } from "./contracts";
import type { PresentationWorldLandmark } from "./m34Contracts";
import { colorForValue, visualScaleForFrame } from "./mapScale";
import type { PresentationVisualScale } from "./mapScale";
import { heightMetersForValue } from "./presentationHeight";
import {
  AUTOMAKER_LABELS,
  automakerMapTrackPoints,
  featureBounds,
  featureRepresentativePoint,
  interactionCurve,
  pathAtProgress,
  pointAtPathProgress,
  provinceAnchorMap,
} from "./presentationGeometry";
import type { PresentationMapCollection } from "./tech-spike/types";
import {
  SOUTH_CHINA_SEA_BOUNDARY_GEOJSON_URL,
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

type Relation = NonNullable<PresentationOverlayRecord["relation_semantic"]>;

interface PathRecord {
  id: string;
  sessionId: string | null;
  sourceSubject: string;
  targetSubject: string;
  fullPath: Array<[number, number]>;
  path: Array<[number, number]>;
  kind: PresentationOverlayKind;
  weight: number;
  relation: Relation;
  lineStyle: NonNullable<PresentationOverlayRecord["line_style"]>;
  emphasized: boolean;
  revealOrder: number;
}

interface FlowPoint {
  id: string;
  position: [number, number];
  color: [number, number, number, number];
}

interface LandmarkNode extends PresentationWorldLandmark {
  position: [number, number];
  iconUrl: string;
  color: [number, number, number, number];
}

interface EventPoint {
  id: string;
  subjectRef: string;
  position: [number, number];
  weight: number;
}

interface SubjectNode {
  id: string;
  subjectRef: string;
  label: string;
  position: [number, number];
  kind: "province" | "automaker";
}

const ARC_COLORS: Record<PresentationOverlayKind, [number, number, number, number]> = {
  competition: [244, 92, 112, 220],
  negotiation: [245, 184, 95, 228],
  coordination: [54, 220, 197, 232],
  topk: [143, 125, 255, 220],
  event: [244, 173, 87, 230],
  automaker: [68, 194, 220, 220],
};

const RELATION_COLORS: Record<Relation, [number, number, number, number]> = {
  proposal: [244, 184, 95, 242],
  counteroffer: [168, 130, 255, 238],
  accepted: [76, 224, 213, 242],
  settled: [76, 224, 213, 255],
  rejected: [170, 94, 105, 124],
  deferred: [177, 142, 224, 170],
  invalid: [148, 92, 101, 105],
  event_impact: [246, 170, 76, 232],
};

maplibregl.setWorkerUrl(maplibreWorkerUrl);

function projection(
  frame: PresentationMapFrame,
  collection: PresentationMapCollection,
  focusProvinceCodes: ReadonlySet<string>,
) {
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
          focused: focusProvinceCodes.has(item.properties.province_code),
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

function heightColumnProjection(
  frame: PresentationMapFrame,
  collection: PresentationMapCollection,
  focusProvinceCodes: ReadonlySet<string>,
  visualScale?: PresentationVisualScale,
): GeoJSON.FeatureCollection<GeoJSON.Polygon> {
  const scale = visualScale ?? visualScaleForFrame(frame);
  const values = new Map(frame.province_values.map((item) => [item.province_code, item.value]));
  const hasFrozenDevelopmentValues = frame.province_values.some((item) => item.value != null && Number.isFinite(item.value));
  const interactionWeights = new Map<string, number>();
  for (const record of frame.overlay_records) {
    for (const subject of [record.source_subject, record.target_subject]) {
      const code = subjectProvinceCode(subject);
      if (code) interactionWeights.set(code, Math.max(interactionWeights.get(code) ?? 0, record.weight ?? 0.5));
    }
  }
  if (!interactionWeights.size) {
    focusProvinceCodes.forEach((code) => interactionWeights.set(code, 0.82));
  }
  const anchors = provinceAnchorMap(collection);
  return {
    type: "FeatureCollection",
    features: collection.features.flatMap((feature) => {
      if (feature.properties.region_role !== "simulation-province") return [];
      const code = feature.properties.province_code;
      const developmentValue = values.get(code);
      const interactionWeight = interactionWeights.get(code);
      const anchor = anchors.get(code);
      if (!anchor) return [];
      if (hasFrozenDevelopmentValues && (developmentValue == null || !Number.isFinite(developmentValue))) return [];
      if (!hasFrozenDevelopmentValues && interactionWeight == null) return [];
      const heightScale = hasFrozenDevelopmentValues
        ? scale
        : { domain: [0, 1], center: null, stops: [[0, "#1a5965"], [1, "#72ead8"]] } satisfies PresentationVisualScale;
      const value = hasFrozenDevelopmentValues ? developmentValue! : interactionWeight!;
      const halfWidth = 0.34;
      const halfHeight = 0.27;
      const focused = focusProvinceCodes.has(code);
      return [{
        type: "Feature",
        id: code,
        properties: {
          province_code: code,
          name: feature.properties.name,
          value,
          height: heightMetersForValue(value, heightScale) * (focused ? 1.2 : 1),
          color: focused ? "#f4bd69" : colorForValue(heightScale, value),
          focused,
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [anchor[0] - halfWidth, anchor[1] - halfHeight],
            [anchor[0] + halfWidth, anchor[1] - halfHeight],
            [anchor[0] + halfWidth, anchor[1] + halfHeight],
            [anchor[0] - halfWidth, anchor[1] + halfHeight],
            [anchor[0] - halfWidth, anchor[1] - halfHeight],
          ]],
        },
      } satisfies GeoJSON.Feature<GeoJSON.Polygon>];
    }),
  };
}

function subjectProvinceCode(subjectRef: string | null | undefined): string | null {
  return subjectRef?.startsWith("province:") ? subjectRef.slice(9) : null;
}

function subjectAutomakerId(subjectRef: string | null | undefined): string | null {
  return subjectRef?.startsWith("automaker:") ? subjectRef.slice(10) : null;
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
  focusSubjectRefs = [],
  automakerTrackIds = [],
  focusKey = "",
  interactionMode = false,
  onSessionSelect,
  onSubjectSelect,
  landmarks = [],
  showBatteryLandmarks = true,
  showIndustrialLandmarks = false,
  viewMode = "top",
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
  focusSubjectRefs?: string[];
  automakerTrackIds?: string[];
  focusKey?: string;
  interactionMode?: boolean;
  onSessionSelect?: (sessionId: string) => void;
  onSubjectSelect?: (subjectRef: string) => void;
  landmarks?: PresentationWorldLandmark[];
  showBatteryLandmarks?: boolean;
  showIndustrialLandmarks?: boolean;
  viewMode?: MapViewMode;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [flowClock, setFlowClock] = useState(0);
  const [drawProgress, setDrawProgress] = useState(1);
  const frameRef = useRef(frame);
  const visualScaleRef = useRef(visualScale);
  const viewModeRef = useRef(viewMode);
  const focusProvinceCodesRef = useRef<ReadonlySet<string>>(new Set());
  const selectedCodeRef = useRef(selectedCode);
  const appliedSelectedCodeRef = useRef<string | null>(null);
  const appliedFrameRef = useRef<string | null>(null);
  const onSelectRef = useRef(onSelect);
  const onErrorRef = useRef(onError);
  const onFatalRef = useRef(onFatal);
  const onCameraChangeRef = useRef(onCameraChange);
  const onSessionSelectRef = useRef(onSessionSelect);
  const onSubjectSelectRef = useRef(onSubjectSelect);
  const anchors = useMemo(() => provinceAnchorMap(collection), [collection]);
  const features = useMemo(() => new Map(collection.features.map(
    (feature) => [feature.properties.province_code, feature],
  )), [collection]);
  const provinceNames = useMemo(() => new Map(collection.features.map(
    (feature) => [feature.properties.province_code, feature.properties.name],
  )), [collection]);
  const focusProvinceCodes = useMemo(() => new Set(
    focusSubjectRefs.map(subjectProvinceCode).filter((code): code is string => Boolean(code)),
  ), [focusSubjectRefs]);
  const overlayRevealKey = frame.overlay_records.map((record) => record.overlay_id).join("|");
  const stableAutomakerIds = useMemo(() => automakerTrackIds.length
    ? Array.from(new Set(automakerTrackIds))
    : Array.from(new Set(frame.overlay_records.flatMap((record) => [
      subjectAutomakerId(record.source_subject), subjectAutomakerId(record.target_subject),
    ]).filter((id): id is string => Boolean(id)))), [automakerTrackIds, frame.overlay_records]);

  useEffect(() => {
    if (reducedMotion || !frame.overlay_records.some((record) => record.emphasized)) return;
    const timer = window.setInterval(() => setFlowClock((value) => (value + 0.025) % 1), 40);
    return () => window.clearInterval(timer);
  }, [frame.overlay_records.length, reducedMotion]);

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

  useEffect(() => { frameRef.current = frame; }, [frame]);
  useEffect(() => { visualScaleRef.current = visualScale; }, [visualScale]);
  useEffect(() => { viewModeRef.current = viewMode; }, [viewMode]);
  useEffect(() => { focusProvinceCodesRef.current = focusProvinceCodes; }, [focusProvinceCodes]);
  useEffect(() => { selectedCodeRef.current = selectedCode; }, [selectedCode]);
  useEffect(() => { onSelectRef.current = onSelect; }, [onSelect]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);
  useEffect(() => { onFatalRef.current = onFatal; }, [onFatal]);
  useEffect(() => { onCameraChangeRef.current = onCameraChange; }, [onCameraChange]);
  useEffect(() => { onSessionSelectRef.current = onSessionSelect; }, [onSessionSelect]);
  useEffect(() => { onSubjectSelectRef.current = onSubjectSelect; }, [onSubjectSelect]);

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
        const projected = projection(frameRef.current, collection, focusProvinceCodesRef.current);
        for (const feature of projected.features) {
          const code = feature.properties.province_code;
          const sourceId = `province-${code}`;
          map.addSource(sourceId, { type: "geojson", data: feature });
          map.addLayer({
            id: `province-underlay-${code}`,
            type: "fill",
            source: sourceId,
            paint: {
              "fill-color": [
                "case",
                ["==", ["get", "region_role"], "territory-context"],
                "#0a202a",
                "#101923",
              ],
              "fill-opacity": 1,
            },
          });
          map.addLayer({
            id: `province-fill-${code}`,
            type: "fill",
            source: sourceId,
            paint: {
              "fill-color": fillColorExpression(frameRef.current, visualScaleRef.current),
              "fill-color-transition": { duration: 420, delay: 0 },
              "fill-opacity": [
                "case",
                ["==", ["get", "region_role"], "territory-context"], 0.72,
                ["get", "focused"], 0.82,
                interactionMode ? 0.4 : 0.9,
              ],
            },
          });
          map.addLayer({
            id: `province-outline-${code}`,
            type: "line",
            source: sourceId,
            layout: { "line-cap": "round", "line-join": "round" },
            paint: {
              "line-color": feature.properties.region_role === "territory-context"
                ? "rgba(117,234,214,.76)"
                : "rgba(177,220,234,.62)",
              "line-width": feature.properties.region_role === "territory-context" ? 1.1 : 0.75,
            },
          });
          if (feature.properties.region_role !== "simulation-province") continue;
          map.addLayer({
            id: `province-selected-fill-${code}`,
            type: "fill",
            source: sourceId,
            paint: {
              "fill-color": "#f4d49b",
              "fill-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 0.08, 0],
            },
          });
          map.addLayer({
            id: `province-selected-glow-${code}`,
            type: "line",
            source: sourceId,
            layout: { "line-cap": "round", "line-join": "round" },
            paint: {
              "line-color": "#ffe2a5",
              "line-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 0.16, 0],
              "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 4.2, 0],
              "line-blur": 1.8,
            },
          });
          map.addLayer({
            id: `province-selected-outline-${code}`,
            type: "line",
            source: sourceId,
            layout: { "line-cap": "round", "line-join": "round" },
            paint: {
              "line-color": "#f7d99e",
              "line-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 1, 0],
              "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.1, 0],
            },
          });
        }
        map.addSource("south-china-sea-boundary", {
          type: "geojson",
          data: SOUTH_CHINA_SEA_BOUNDARY_GEOJSON_URL,
        });
        map.addLayer({
          id: "south-china-sea-boundary",
          type: "line",
          source: "south-china-sea-boundary",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": "#bceeed",
            "line-width": 1.55,
            "line-opacity": 0.9,
            "line-blur": 0.08,
          },
          metadata: {
            mapSource: "MNR-standard-map-GS2016-1609",
            positioning: "map-georeferenced",
            simulationScope: "none",
          },
        });
        map.addSource("province-height-columns", {
          type: "geojson",
          data: heightColumnProjection(frameRef.current, collection, focusProvinceCodesRef.current, visualScaleRef.current),
        });
        map.addLayer({
          id: "province-height-columns",
          type: "fill-extrusion",
          source: "province-height-columns",
          layout: { visibility: viewModeRef.current === "side" ? "visible" : "none" },
          paint: {
            "fill-extrusion-base": 0,
            "fill-extrusion-color": ["get", "color"],
            "fill-extrusion-height": ["get", "height"],
            "fill-extrusion-opacity": 0.9,
            "fill-extrusion-vertical-gradient": true,
          },
        });
        if (selectedCodeRef.current) {
          map.setFeatureState({ source: `province-${selectedCodeRef.current}`, id: selectedCodeRef.current }, { selected: true });
          appliedSelectedCodeRef.current = selectedCodeRef.current;
        }
        for (const feature of collection.features.filter((item) => item.properties.region_role === "territory-context")) {
          const code = feature.properties.province_code;
          const label = document.createElement("span");
          label.className = "territory-map-label";
          label.textContent = feature.properties.name;
          label.title = `${feature.properties.name}：中国版图展示，不参与本次推演计算`;
          label.setAttribute("aria-label", `${feature.properties.name}，中国版图展示，不参与推演`);
          const marker = new maplibregl.Marker({
            element: label,
            anchor: "left",
            offset: code === "81" ? [7, -8] : code === "82" ? [7, 9] : [8, 0],
          }).setLngLat(featureRepresentativePoint(feature)).addTo(map);
          territoryMarkers.push(marker);
        }
        const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
        overlayRef.current = overlay;
        map.addControl(overlay as unknown as maplibregl.IControl);
        map.fitBounds(
          [[collection.bbox[0], collection.bbox[1]], [collection.bbox[2], collection.bbox[3]]],
          { padding: 82, duration: 0 },
        );
        setMapReady(true);
      });
      const selectProvince = (event: MapMouseEvent) => {
        const hit = map.queryRenderedFeatures(event.point).find((item) => item.layer.id.startsWith("province-fill-"));
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
      map.on("click", selectProvince);
      map.on("moveend", publishCamera);
      return () => {
        active = false;
        map.off("click", selectProvince);
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
    if (!mapReady || !map?.isStyleLoaded()) return;
    const projected = projection(frame, collection, focusProvinceCodes);
    for (const feature of projected.features) {
      const code = feature.properties.province_code;
      const source = map.getSource(`province-${code}`) as maplibregl.GeoJSONSource | undefined;
      source?.setData(feature);
      map.setPaintProperty(`province-fill-${code}`, "fill-color", fillColorExpression(frame, visualScale));
      map.setPaintProperty(`province-fill-${code}`, "fill-opacity", [
        "case",
        ["==", ["get", "region_role"], "territory-context"], 0.72,
        ["get", "focused"], 0.82,
        interactionMode ? 0.4 : 0.9,
      ]);
    }
    const heightSource = map.getSource("province-height-columns") as maplibregl.GeoJSONSource | undefined;
    heightSource?.setData(heightColumnProjection(frame, collection, focusProvinceCodes, visualScale));
    if (map.getLayer("province-height-columns")) {
      map.setLayoutProperty("province-height-columns", "visibility", viewMode === "side" ? "visible" : "none");
    }
    const appliedViewFrame = `${frame.frame_id}:${viewMode}`;
    if (appliedFrameRef.current !== appliedViewFrame) {
      appliedFrameRef.current = appliedViewFrame;
      const camera = frame.map_projection.camera;
      map.easeTo({
        center: [camera.longitude, camera.latitude],
        zoom: camera.zoom - (viewMode === "side" ? 0.46 : 0),
        pitch: viewMode === "side" ? 58 : camera.pitch,
        bearing: viewMode === "side" ? -18 : camera.bearing,
        duration: reducedMotion ? 0 : 760,
      });
    }
  }, [collection, focusProvinceCodes, frame, interactionMode, mapReady, reducedMotion, viewMode, visualScale]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !interactionMode || focusProvinceCodes.size === 0) return;
    const codes = Array.from(focusProvinceCodes);
    const duration = reducedMotion ? 0 : codes.length > 1 ? 1600 : 1450;
    if (codes.length > 1) {
      const bounds = codes.reduce<maplibregl.LngLatBounds | null>((current, code) => {
        const feature = features.get(code);
        if (!feature) return current;
        const [west, south, east, north] = featureBounds(feature);
        const next = current ?? new maplibregl.LngLatBounds([west, south], [east, north]);
        next.extend([west, south]);
        next.extend([east, north]);
        return next;
      }, null);
      if (bounds) {
        const camera = map.cameraForBounds(bounds, { padding: { left: 290, right: 360, top: 110, bottom: 165 }, maxZoom: 5.2 });
        if (camera) map.easeTo({
          ...camera,
          zoom: Math.max(4.1, Math.min(4.78, (camera.zoom ?? 4.8) - (viewMode === "side" ? 0.42 : 0))),
          pitch: viewMode === "side" ? 58 : 0,
          bearing: viewMode === "side" ? -18 : 0,
          duration: reducedMotion ? 0 : duration,
        });
      }
      return;
    }
    const code = codes[0]!;
    const feature = features.get(code);
    const center = anchors.get(code);
    if (!feature || !center) {
      onErrorRef.current(`无法解析省域 ${code} 的地图锚点`);
      return;
    }
    const [west, south, east, north] = featureBounds(feature);
    const span = Math.max(east - west, north - south);
    const zoom = span > 16 ? 4.6 : span > 8 ? 4.85 : 5.2;
    map.easeTo({
      center,
      zoom: zoom - (viewMode === "side" ? 0.42 : 0),
      pitch: viewMode === "side" ? 58 : 0,
      bearing: viewMode === "side" ? -18 : 0,
      duration: reducedMotion ? 0 : duration,
      essential: true,
    });
  }, [anchors, features, focusKey, focusProvinceCodes, interactionMode, mapReady, reducedMotion, viewMode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const automakerCoordinates = automakerMapTrackPoints(stableAutomakerIds, anchors);
    const resolveSubject = (subjectRef: string | null): [number, number] | null => {
      const provinceCode = subjectProvinceCode(subjectRef);
      if (provinceCode) return anchors.get(provinceCode) ?? null;
      const automakerId = subjectAutomakerId(subjectRef);
      if (automakerId) return automakerCoordinates.get(automakerId) ?? null;
      if (subjectRef?.startsWith("event:")) return [104, 35];
      return null;
    };
    const unresolved: string[] = [];
    const paths = frame.overlay_records.flatMap<PathRecord>((record) => {
      const source = resolveSubject(record.source_subject);
      const target = resolveSubject(record.target_subject);
      if (!source || !target || !record.target_subject) {
        unresolved.push(record.label);
        return [];
      }
      const fullPath = interactionCurve(source, target, record.reveal_order ?? 0)
        .map((point) => [point[0], point[1]] as [number, number]);
      return [{
        id: record.overlay_id,
        sessionId: record.session_id ?? null,
        sourceSubject: record.source_subject,
        targetSubject: record.target_subject,
        fullPath,
        path: record.emphasized && drawProgress < 1
          ? pathAtProgress(fullPath, drawProgress).map((point) => [point[0], point[1]] as [number, number])
          : fullPath,
        kind: record.kind,
        weight: record.weight ?? 0.5,
        relation: record.relation_semantic ?? "proposal",
        lineStyle: record.line_style ?? "solid",
        emphasized: record.emphasized ?? false,
        revealOrder: record.reveal_order ?? 0,
      }];
    });
    if (unresolved.length) onErrorRef.current(`以下关系缺少可用锚点：${unresolved.join("；")}`);
    const flowPoints = reducedMotion ? [] : paths.filter((item) => item.emphasized).map<FlowPoint>((item) => {
      const progress = drawProgress < 1 ? drawProgress : flowClock;
      return {
        id: `flow:${item.id}`,
        position: pointAtPathProgress(item.fullPath, progress),
        color: RELATION_COLORS[item.relation] ?? ARC_COLORS[item.kind],
      };
    });
    const landmarkNodes = landmarks.flatMap<LandmarkNode>((landmark) => {
      if (landmark.kind === "battery_capability" && !showBatteryLandmarks) return [];
      if (landmark.kind === "industrial_facility" && !showIndustrialLandmarks) return [];
      const anchor = anchors.get(landmark.province_code);
      if (!anchor) return [];
      const isBattery = landmark.kind === "battery_capability";
      return [{
        ...landmark,
        position: [anchor[0] + (isBattery ? -0.13 : 0.13), anchor[1] + (isBattery ? 0.1 : -0.1)],
        iconUrl: isBattery
          ? "/assets/icons/battery-capability.svg"
          : "/assets/icons/industrial-facility.svg",
        color: isBattery ? [94, 230, 218, 235] : [246, 183, 94, 235],
      }];
    });
    const subjectRefs = Array.from(new Set([
      ...frame.overlay_records.flatMap((record) => [record.source_subject, record.target_subject]),
      ...stableAutomakerIds.map((id) => `automaker:${id}`),
    ].filter((value): value is string => Boolean(value))));
    const subjectNodes = subjectRefs.flatMap<SubjectNode>((subjectRef) => {
      const automakerId = subjectAutomakerId(subjectRef);
      if (automakerId) {
        const position = automakerCoordinates.get(automakerId);
        if (!position) return [];
        return [{ id: automakerId, subjectRef, label: `${AUTOMAKER_LABELS[automakerId] ?? automakerId} · 模拟`, position, kind: "automaker" }];
      }
      const provinceCode = subjectProvinceCode(subjectRef);
      if (!provinceCode) return [];
      const position = anchors.get(provinceCode);
      if (!position) return [];
      return [{ id: provinceCode, subjectRef, label: provinceNames.get(provinceCode) ?? provinceCode, position, kind: "province" }];
    });
    const eventPoints = frame.overlay_records.flatMap<EventPoint>((record) => {
      if (record.kind !== "event" || !record.source_subject.startsWith("event:")) return [];
      const target = resolveSubject(record.target_subject);
      return [{ id: record.overlay_id, subjectRef: record.source_subject, position: target ?? [104, 35], weight: record.weight ?? 0.5 }];
    });
    const selectPath = (info: PickingInfo<PathRecord>) => {
      const sessionId = info.object?.sessionId;
      if (sessionId) onSessionSelectRef.current?.(sessionId);
    };
    const selectNode = (info: PickingInfo<SubjectNode>) => {
      const subjectRef = info.object?.subjectRef;
      if (subjectRef) onSubjectSelectRef.current?.(subjectRef);
    };
    overlayRef.current?.setProps({
      getCursor: ({ isHovering }: { isHovering: boolean }) => isHovering ? "pointer" : "grab",
      layers: [
        new PathLayer<PathRecord>({
          id: `presentation-paths-${frame.frame_id}-${focusKey}`,
          data: paths,
          getPath: (item) => item.path,
          getColor: (item) => {
            const color = RELATION_COLORS[item.relation] ?? ARC_COLORS[item.kind];
            return item.emphasized ? color : [color[0], color[1], color[2], 72];
          },
          getWidth: (item) => item.emphasized ? (item.lineStyle === "thick" ? 5 + item.weight * 2 : 2.8 + item.weight * 2.5) : 1 + item.weight,
          widthMinPixels: 1.4,
          widthMaxPixels: 6,
          capRounded: true,
          jointRounded: true,
          pickable: true,
          onClick: selectPath,
        }),
        new ScatterplotLayer<FlowPoint>({
          id: `presentation-flow-${frame.frame_id}-${Math.round(flowClock * 40)}`,
          data: flowPoints,
          getPosition: (item) => item.position,
          getRadius: 38_000,
          getFillColor: (item) => item.color,
          radiusMinPixels: 3,
          radiusMaxPixels: 8,
          pickable: false,
        }),
        new IconLayer<LandmarkNode>({
          id: `presentation-landmarks-${frame.frame_id}-${showBatteryLandmarks}-${showIndustrialLandmarks}`,
          data: landmarkNodes,
          getPosition: (item) => item.position,
          getIcon: (item) => ({
            url: item.iconUrl,
            width: 64,
            height: 64,
            anchorX: 32,
            anchorY: 32,
            mask: true,
          }),
          getColor: (item) => item.color,
          getSize: 19,
          sizeMinPixels: 15,
          sizeMaxPixels: 24,
          billboard: true,
          pickable: true,
          onClick: (info) => {
            const code = info.object?.province_code;
            if (code) onSubjectSelectRef.current?.(`province:${code}`);
          },
        }),
        new TextLayer<LandmarkNode>({
          id: `presentation-landmark-counts-${frame.frame_id}-${showBatteryLandmarks}-${showIndustrialLandmarks}`,
          data: landmarkNodes,
          getPosition: (item) => item.position,
          getText: (item) => String(item.node_count),
          getColor: [235, 251, 251, 245],
          getSize: 9,
          getPixelOffset: [9, -9],
          getTextAnchor: "middle",
          getAlignmentBaseline: "center",
          billboard: true,
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
          pickable: true,
        }),
        new ScatterplotLayer<SubjectNode>({
          id: `presentation-subject-nodes-${frame.frame_id}-${focusKey}`,
          data: subjectNodes,
          getPosition: (item) => item.position,
          getRadius: (item) => item.kind === "automaker" ? 24_000 : 16_000,
          getFillColor: (item) => item.kind === "automaker" ? [36, 187, 207, 220] : [14, 25, 38, 220],
          getLineColor: (item) => item.kind === "automaker" ? [168, 239, 246, 245] : [244, 215, 158, 245],
          lineWidthMinPixels: 1.5,
          radiusMinPixels: 5,
          radiusMaxPixels: 10,
          stroked: true,
          pickable: true,
          onClick: selectNode,
        }),
        new TextLayer<SubjectNode>({
          id: `presentation-subject-labels-${frame.frame_id}-${focusKey}`,
          data: subjectNodes,
          getPosition: (item) => item.position,
          getText: (item) => item.label,
          getColor: [215, 244, 248, 230],
          getSize: 13,
          getPixelOffset: (item) => item.kind === "automaker" ? [11, 0] : [0, -14],
          getTextAnchor: (item) => item.kind === "automaker" ? "start" : "middle",
          getAlignmentBaseline: "center",
          fontFamily: "Noto Sans SC",
          characterSet: "auto",
          billboard: true,
          pickable: false,
        }),
      ],
    });
  }, [anchors, drawProgress, flowClock, focusKey, focusProvinceCodes, frame, landmarks, mapReady, provinceNames, reducedMotion, showBatteryLandmarks, showIndustrialLandmarks, stableAutomakerIds, viewMode, visualScale]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const previousCode = appliedSelectedCodeRef.current;
    if (previousCode && map.getSource(`province-${previousCode}`)) {
      map.setFeatureState({ source: `province-${previousCode}`, id: previousCode }, { selected: false });
    }
    if (selectedCode && map.getSource(`province-${selectedCode}`)) {
      map.setFeatureState({ source: `province-${selectedCode}`, id: selectedCode }, { selected: true });
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

  return <div
    aria-label={ariaLabel}
    className={`presentation-map branch-${frame.branch_role} view-${viewMode}`}
    data-automaker-anchor-mode="map"
    data-automaker-track-count={stableAutomakerIds.length}
    data-focus-key={focusKey}
    data-overlay-count={frame.overlay_records.length}
    data-selected-code={selectedCode ?? undefined}
    data-view-mode={viewMode}
    data-height-encoding={viewMode === "side" ? "province-nev-development-index" : undefined}
  >
    <div className="presentation-map-canvas" ref={containerRef} />
    <SouthChinaSeaInset />
  </div>;
}
