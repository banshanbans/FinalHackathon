import { ArcLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";
import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "../../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";

import { applyFrame, buildArcs } from "./presentationData";
import type { PresentationMapCollection } from "./types";

interface ArcRecord {
  id: string;
  source: [number, number];
  target: [number, number];
  kind: "competition" | "coordination" | "topk";
  active: boolean;
}

const ARC_COLORS: Record<ArcRecord["kind"], [number, number, number, number]> = {
  competition: [239, 93, 110, 215],
  coordination: [52, 211, 193, 225],
  topk: [133, 119, 255, 225],
};

maplibregl.setWorkerUrl(maplibreWorkerUrl);

export function WebglProvinceMap({
  collection,
  frame,
  reducedMotion,
  selectedCode,
  onSelect,
  onReady,
  onError,
}: {
  collection: PresentationMapCollection;
  frame: number;
  reducedMotion: boolean;
  selectedCode: string | null;
  onSelect: (code: string, name: string) => void;
  onReady: (webglVersion: string) => void;
  onError: (message: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let active = true;
    try {
      const map = new maplibregl.Map({
        container: containerRef.current,
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "stage-background",
              type: "background",
              paint: { "background-color": "#07101f" },
            },
          ],
        },
        center: [105, 36],
        zoom: 3.1,
        pitch: 20,
        bearing: 0,
        minZoom: 2.1,
        maxZoom: 7,
        attributionControl: false,
        renderWorldCopies: false,
        canvasContextAttributes: { antialias: true, preserveDrawingBuffer: true },
      });
      mapRef.current = map;
      map.on("error", (event: maplibregl.ErrorEvent) => {
        if (active) onError(event.error?.message ?? "WebGL map error");
      });
      map.on("sourcedata", (event) => {
        if (!containerRef.current || !event.sourceId) return;
        containerRef.current.dataset.lastSourceEvent = JSON.stringify({
          id: event.sourceId,
          loaded: event.isSourceLoaded,
          type: event.sourceDataType,
        });
      });
      map.on("load", () => {
        if (!active) return;
        map.addSource("provinces", {
          type: "geojson",
          data: applyFrame(collection, 0),
          promoteId: "province_code",
        });
        map.addLayer({
          id: "province-glow",
          type: "line",
          source: "provinces",
          paint: {
            "line-color": "rgba(89, 180, 255, .22)",
            "line-width": 7,
            "line-blur": 5,
          },
        });
        map.addLayer({
          id: "province-fill",
          type: "fill",
          source: "provinces",
          paint: {
            "fill-color": [
              "case",
              ["==", ["get", "region_role"], "territory-context"],
              "#12343e",
              [
                "interpolate",
                ["linear"],
                ["get", "delta"],
                -10,
                "#6656c8",
                -2,
                "#253255",
                0,
                "#172638",
                2,
                "#155d66",
                10,
                "#22b9ad",
              ],
            ],
            "fill-opacity": [
              "case",
              ["==", ["get", "region_role"], "territory-context"],
              0.72,
              0.88,
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
              ["==", ["get", "province_code"], ""],
              "#f4d49b",
              ["==", ["get", "region_role"], "territory-context"],
              "rgba(117,234,214,.76)",
              "rgba(177, 212, 240, .72)",
            ],
            "line-width": [
              "case",
              ["==", ["get", "province_code"], ""],
              2.8,
              ["==", ["get", "region_role"], "territory-context"],
              1.1,
              0.9,
            ],
          },
        });
        map.addSource("event-origin", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: { type: "Point", coordinates: [105, 34] },
          },
        });
        map.addLayer({
          id: "event-origin",
          type: "circle",
          source: "event-origin",
          paint: {
            "circle-color": "#e6ad62",
            "circle-radius": 8,
            "circle-stroke-color": "#fff1d2",
            "circle-stroke-width": 2,
          },
        });
        const deckOverlay = new MapboxOverlay({
          interleaved: false,
          layers: [],
        });
        overlayRef.current = deckOverlay;
        map.addControl(deckOverlay as unknown as maplibregl.IControl);
        const bounds = collection.bbox;
        map.fitBounds(
          [
            [bounds[0], bounds[1]],
            [bounds[2], bounds[3]],
          ],
          { padding: 56, duration: 0 },
        );
        const context = map.getCanvas().getContext("webgl2") ?? map.getCanvas().getContext("webgl");
        const version = context?.getParameter(context.VERSION) as string | undefined;
        window.setTimeout(() => {
          if (!containerRef.current) return;
          containerRef.current.dataset.styleLayers = map
            .getStyle()
            .layers.map((layer) => layer.id)
            .join(",");
          containerRef.current.dataset.sourceFeatureCount = String(
            map.querySourceFeatures("provinces").length,
          );
          containerRef.current.dataset.provinceSourceLoaded = String(
            map.isSourceLoaded("provinces"),
          );
          containerRef.current.dataset.eventSourceLoaded = String(
            map.isSourceLoaded("event-origin"),
          );
          containerRef.current.dataset.renderedFeatureCount = String(
            map.queryRenderedFeatures().length,
          );
          containerRef.current.dataset.camera = JSON.stringify({
            center: map.getCenter().toArray(),
            zoom: map.getZoom(),
          });
          containerRef.current.dataset.eventPoint = JSON.stringify(map.project([105, 34]));
        }, 2000);
        setReady(true);
        onReady(version ?? "WebGL unavailable");
      });
      const selectProvince = (event: MapMouseEvent) => {
        const feature = map.queryRenderedFeatures(event.point, { layers: ["province-fill"] })[0];
        const code = feature?.properties?.province_code as string | undefined;
        const name = feature?.properties?.name as string | undefined;
        if (code && name && feature?.properties?.region_role === "simulation-province") onSelect(code, name);
      };
      map.on("click", "province-fill", selectProvince);
      return () => {
        active = false;
        map.off("click", "province-fill", selectProvince);
        map.remove();
        setReady(false);
        mapRef.current = null;
        overlayRef.current = null;
      };
    } catch (error) {
      onError(error instanceof Error ? error.message : "WebGL initialization failed");
      return undefined;
    }
  }, [collection, onError, onReady, onSelect]);

  useEffect(() => {
    const map = mapRef.current;
    if (
      !ready
      || !map?.isStyleLoaded()
      || !map.getSource("provinces")
      || !map.getLayer("province-fill")
      || !map.getLayer("province-outline")
    ) return;
    const source = map.getSource("provinces") as maplibregl.GeoJSONSource | undefined;
    source?.setData(applyFrame(collection, frame));
    map.setPaintProperty(
      "province-fill",
      "fill-opacity",
      ["case", ["==", ["get", "province_code"], selectedCode ?? ""], 1, 0.88],
    );
    map.setPaintProperty(
      "province-outline",
      "line-color",
      [
        "case",
        ["==", ["get", "province_code"], selectedCode ?? ""],
        "#f4d49b",
        ["==", ["get", "region_role"], "territory-context"],
        "rgba(117,234,214,.76)",
        "rgba(177, 212, 240, .72)",
      ],
    );
    const focusSequence: Array<[number, number, number]> = [
      [105, 36, 3.15],
      [112, 33, 3.45],
      [104, 30, 3.6],
      [116, 35, 3.5],
      [107, 38, 3.35],
      [101, 34, 3.5],
      [113, 29, 3.55],
      [105, 36, 3.15],
    ];
    const [longitude, latitude, zoom] = focusSequence[frame];
    map.easeTo({
      center: [longitude, latitude],
      zoom,
      pitch: frame === 0 || frame === 7 ? 18 : 27,
      bearing: frame % 2 === 0 ? -2 : 3,
      duration: reducedMotion ? 0 : 760,
    });
    const arcData = buildArcs(collection, frame) as ArcRecord[];
    overlayRef.current?.setProps({
      layers: [
        new ArcLayer<ArcRecord>({
          id: `province-arcs-${frame}`,
          data: arcData,
          getSourcePosition: (item) => item.source,
          getTargetPosition: (item) => item.target,
          getSourceColor: (item) => ARC_COLORS[item.kind],
          getTargetColor: (item) => ARC_COLORS[item.kind],
          getWidth: (item) => (item.active ? 2.4 : 0.65),
          getHeight: (item) => (item.active ? 0.42 : 0.12),
          opacity: 0.92,
          widthUnits: "pixels",
          pickable: true,
          updateTriggers: { getWidth: frame, getHeight: frame },
        }),
      ],
    });
  }, [collection, frame, ready, reducedMotion, selectedCode]);

  return <div aria-label="31 省 WebGL 技术验证地图" className="map-renderer" ref={containerRef} />;
}
