import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "../../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import worldLandTopology from "world-atlas/land-110m.json";

import type { PresentationMapCollection } from "./types";

const WORLD_TOPOLOGY = worldLandTopology as unknown as Topology<{
  land: GeometryCollection;
}>;
const WORLD_LAND = feature(WORLD_TOPOLOGY, WORLD_TOPOLOGY.objects.land);
const BEIJING_COORDINATES: [number, number] = [116.4074, 39.9042];

type IntroPhase = "ready" | "orbit" | "approach" | "handoff";

maplibregl.setWorkerUrl(maplibreWorkerUrl);

export function GlobeIntro({
  collection,
  reducedMotion,
  runId,
  onComplete,
  onError,
}: {
  collection: PresentationMapCollection;
  reducedMotion: boolean;
  runId: number;
  onComplete: () => void;
  onError: (message: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [phase, setPhase] = useState<IntroPhase>("ready");

  useEffect(() => {
    if (!containerRef.current) return;
    let active = true;
    const timers: number[] = [];

    const schedule = (callback: () => void, delay: number) => {
      timers.push(window.setTimeout(callback, delay));
    };

    try {
      const map = new maplibregl.Map({
        container: containerRef.current,
        style: {
          version: 8,
          projection: { type: "globe" },
          sky: { "atmosphere-blend": 1 },
          light: {
            anchor: "viewport",
            color: "#d8f1ff",
            intensity: 0.82,
            position: [1.15, 120, 35],
          },
          sources: {
            "world-land": {
              type: "geojson",
              data: WORLD_LAND,
            },
            "china-focus": {
              type: "geojson",
              data: collection,
            },
            "beijing-focus": {
              type: "geojson",
              data: {
                type: "Feature",
                properties: { name: "北京" },
                geometry: { type: "Point", coordinates: BEIJING_COORDINATES },
              },
            },
          },
          layers: [
            {
              id: "space-ocean",
              type: "background",
              paint: { "background-color": "#020713" },
            },
            {
              id: "world-land",
              type: "fill",
              source: "world-land",
              paint: {
                "fill-color": "#17334b",
                "fill-opacity": 0.94,
              },
            },
            {
              id: "world-coast",
              type: "line",
              source: "world-land",
              paint: {
                "line-color": "rgba(109, 176, 207, .72)",
                "line-width": 0.75,
                "line-blur": 0.2,
              },
            },
            {
              id: "china-focus-fill",
              type: "fill",
              source: "china-focus",
              paint: {
                "fill-color": "#2bbdaf",
                "fill-opacity": 0.08,
              },
            },
            {
              id: "china-focus-outline",
              type: "line",
              source: "china-focus",
              paint: {
                "line-color": "rgba(118, 237, 223, .9)",
                "line-width": 0.8,
                "line-opacity": 0.16,
              },
            },
            {
              id: "beijing-pulse",
              type: "circle",
              source: "beijing-focus",
              paint: {
                "circle-color": "#f2cf91",
                "circle-radius": 5,
                "circle-stroke-color": "rgba(242, 207, 145, .34)",
                "circle-stroke-width": 10,
                "circle-opacity": 0.92,
              },
            },
          ],
        },
        center: [18, 12],
        zoom: 1.88,
        bearing: -18,
        pitch: 0,
        interactive: false,
        attributionControl: false,
        renderWorldCopies: false,
        canvasContextAttributes: { antialias: true },
      });
      mapRef.current = map;
      map.on("error", (event: maplibregl.ErrorEvent) => {
        if (!active) return;
        onError(event.error?.message ?? "地球开场渲染失败");
        onComplete();
      });
      map.on("load", () => {
        if (!active) return;
        if (reducedMotion) {
          setPhase("approach");
          map.jumpTo({ center: [104.2, 35.8], zoom: 2.65, bearing: 0 });
          map.setPaintProperty("china-focus-fill", "fill-opacity", 0.72);
          map.setPaintProperty("china-focus-outline", "line-opacity", 0.82);
          schedule(() => setPhase("handoff"), 520);
          schedule(onComplete, 880);
          return;
        }

        setPhase("orbit");
        map.easeTo({
          center: [58, 18],
          zoom: 2.02,
          bearing: 6,
          duration: 900,
          easing: (value) => value * (2 - value),
        });
        schedule(() => {
          if (!active) return;
          setPhase("approach");
          map.setPaintProperty("world-land", "fill-opacity", 0.68);
          map.setPaintProperty("china-focus-fill", "fill-opacity", 0.78);
          map.setPaintProperty("china-focus-outline", "line-opacity", 0.9);
          map.flyTo({
            center: [104.2, 35.8],
            zoom: 2.72,
            bearing: 0,
            pitch: 8,
            duration: 2750,
            curve: 1.28,
            essential: true,
          });
        }, 820);
        schedule(() => setPhase("handoff"), 3400);
        schedule(onComplete, 4050);
      });
    } catch (error) {
      onError(error instanceof Error ? error.message : "地球开场初始化失败");
      onComplete();
    }

    return () => {
      active = false;
      timers.forEach((timer) => window.clearTimeout(timer));
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [collection, onComplete, onError, reducedMotion, runId]);

  return (
    <section
      aria-label="PolicyScope 地球开场"
      className={`globe-intro phase-${phase}`}
      data-phase={phase}
    >
      <div className="globe-map" ref={containerRef} />
      <div className="globe-copy" aria-live="polite">
        <span>PolicyScope / 政策涟漪</span>
        <h1>从全球冲击<br />进入中国政策推演</h1>
        <p>{phase === "approach" || phase === "handoff" ? "正在锁定中国省域政策网络" : "正在建立全球情景视角"}</p>
      </div>
      <div className="globe-progress" aria-hidden="true">
        <i />
        <span>{phase === "approach" || phase === "handoff" ? "CHINA · COMPLETE MAP" : "GLOBAL VIEW"}</span>
      </div>
      <button className="skip-intro" onClick={onComplete} type="button">
        跳过开场
      </button>
    </section>
  );
}
