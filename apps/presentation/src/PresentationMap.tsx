import { ArcLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";
import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useMemo, useRef } from "react";

import type { PresentationCamera, PresentationFrame, PresentationOverlayKind } from "./contracts";
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

function projection(frame: PresentationFrame, collection: PresentationMapCollection) {
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
}: {
  collection: PresentationMapCollection;
  frame: PresentationFrame;
  reducedMotion: boolean;
  selectedCode: string | null;
  onSelect: (selection: ProvinceSelection) => void;
  onError: (message: string) => void;
  ariaLabel?: string;
  cameraSync?: PresentationCamera;
  onCameraChange?: (camera: PresentationCamera) => void;
  onFatal?: (message: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const frameRef = useRef(frame);
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
    onCameraChangeRef.current = onCameraChange;
  }, [onCameraChange]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let active = true;
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
      map.on("error", (event: maplibregl.ErrorEvent) => active && onError(event.error?.message ?? "地图渲染失败"));
      const canvas = map.getCanvas();
      const loseContext = (event: Event) => {
        event.preventDefault();
        onFatal?.("WebGL 上下文中断，已切换兼容地图。");
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
            "fill-color": [
              "case",
              ["==", ["get", "region_role"], "territory-context"], "#12343e",
              ["get", "missing"], "#111b29",
              ["interpolate", ["linear"], ["get", "value"], -12, "#6758c7", -2, "#29385d", 0, "#17293a", 20, "#166873", 60, "#22bdae", 100, "#75ead6"],
            ],
            "fill-opacity": [
              "case",
              ["==", ["get", "region_role"], "territory-context"], 0.72,
              0.9,
            ],
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
      });
      const selectProvince = (event: MapMouseEvent) => {
        const hit = map.queryRenderedFeatures(event.point, { layers: ["province-fill"] })[0];
        const code = hit?.properties?.province_code as string | undefined;
        if (!code || hit?.properties?.region_role !== "simulation-province") return;
        const value = frameRef.current.province_values.find((item) => item.province_code === code)?.value ?? null;
        onSelect({ code, name: String(hit.properties?.name ?? code), value, x: event.point.x, y: event.point.y });
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
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "地图初始化失败";
      onError(message);
      onFatal?.(message);
      return undefined;
    }
  }, [collection, onError, onFatal, onSelect]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    const source = map.getSource("provinces") as maplibregl.GeoJSONSource | undefined;
    source?.setData(projection(frame, collection));
    map.setPaintProperty("province-outline", "line-color", [
      "case",
      ["==", ["get", "province_code"], selectedCode ?? ""], "#f4d49b",
      ["==", ["get", "region_role"], "territory-context"], "rgba(117,234,214,.76)",
      "rgba(177,220,234,.62)",
    ]);
    map.setPaintProperty("province-outline", "line-width", [
      "case",
      ["==", ["get", "province_code"], selectedCode ?? ""], 2.4,
      ["==", ["get", "region_role"], "territory-context"], 1.1,
      0.8,
    ]);
    const camera = frame.map_projection.camera;
    map.easeTo({ center: [camera.longitude, camera.latitude], zoom: camera.zoom, pitch: camera.pitch, bearing: camera.bearing, duration: reducedMotion ? 0 : 760 });

    const arcs = frame.overlay_records.flatMap<ArcRecord>((record) => {
      const sourceCode = record.source_subject.startsWith("province:") ? record.source_subject.slice(9) : null;
      const targetCode = record.target_subject?.startsWith("province:") ? record.target_subject.slice(9) : null;
      const sourceCenter = sourceCode ? centers.get(sourceCode) : undefined;
      const targetCenter = targetCode ? centers.get(targetCode) : undefined;
      if (!sourceCenter || !targetCenter) return [];
      return [{ id: record.overlay_id, source: sourceCenter, target: targetCenter, kind: record.kind, weight: record.weight ?? 0.5 }];
    });
    overlayRef.current?.setProps({
      layers: [new ArcLayer<ArcRecord>({
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
      })],
    });
  }, [centers, collection, frame, reducedMotion, selectedCode]);

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

  return <div aria-label={ariaLabel} className="presentation-map" ref={containerRef} />;
}
