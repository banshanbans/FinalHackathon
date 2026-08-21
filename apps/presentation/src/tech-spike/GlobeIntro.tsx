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

function provinceVisualAnchor(collection: PresentationMapCollection, provinceCode: string): [number, number] {
  const province = collection.features.find((item) => item.properties.province_code === provinceCode);
  const outerRings = province?.geometry.coordinates
    .map((polygon) => polygon[0])
    .filter((ring): ring is number[][] => Boolean(ring?.length)) ?? [];
  const centroid = (ring: number[][]) => {
    let signedArea = 0;
    let longitude = 0;
    let latitude = 0;
    for (let index = 0; index < ring.length; index += 1) {
      const current = ring[index]!;
      const next = ring[(index + 1) % ring.length]!;
      const cross = current[0]! * next[1]! - next[0]! * current[1]!;
      signedArea += cross;
      longitude += (current[0]! + next[0]!) * cross;
      latitude += (current[1]! + next[1]!) * cross;
    }
    return {
      area: signedArea / 2,
      point: Math.abs(signedArea) > Number.EPSILON
        ? [longitude / (3 * signedArea), latitude / (3 * signedArea)] as [number, number]
        : BEIJING_COORDINATES,
    };
  };
  return outerRings.map(centroid).sort((left, right) => Math.abs(right.area) - Math.abs(left.area))[0]?.point
    ?? BEIJING_COORDINATES;
}

type IntroPhase = "ready" | "orbit" | "approach" | "handoff";

maplibregl.setWorkerUrl(maplibreWorkerUrl);

export function GlobeIntro({
  collection,
  reducedMotion,
  runId,
  onComplete,
  onError,
  onHandoff,
}: {
  collection: PresentationMapCollection;
  reducedMotion: boolean;
  runId: number;
  onComplete: () => void;
  onError: (message: string) => void;
  onHandoff?: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const onHandoffRef = useRef(onHandoff);
  const [phase, setPhase] = useState<IntroPhase>("ready");

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    onHandoffRef.current = onHandoff;
  }, [onHandoff]);

  useEffect(() => {
    if (!containerRef.current) return;
    let active = true;
    let completed = false;
    let handedOff = false;
    const timers: number[] = [];

    const schedule = (callback: () => void, delay: number) => {
      timers.push(window.setTimeout(callback, delay));
    };
    const complete = () => {
      if (!active || completed) return;
      completed = true;
      onCompleteRef.current();
    };
    const handoff = () => {
      if (!active || handedOff) return;
      handedOff = true;
      setPhase("handoff");
      onHandoffRef.current?.();
    };

    try {
      const beijingVisualAnchor = provinceVisualAnchor(collection, "11");
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
                properties: {
                  name: "北京",
                  geographic_coordinates: BEIJING_COORDINATES,
                  visual_anchor_source: "province-11-centroid",
                },
                geometry: { type: "Point", coordinates: beijingVisualAnchor },
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
        onErrorRef.current(event.error?.message ?? "地球开场渲染失败");
      });
      schedule(complete, 6200);
      map.on("load", () => {
        if (!active) return;
        if (reducedMotion) {
          setPhase("approach");
          map.jumpTo({ center: [104.2, 35.8], zoom: 2.65, bearing: 0 });
          map.setPaintProperty("china-focus-fill", "fill-opacity", 0.72);
          map.setPaintProperty("china-focus-outline", "line-opacity", 0.82);
          schedule(handoff, 280);
          schedule(complete, 650);
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
            zoom: 3.42,
            bearing: 0,
            pitch: 8,
            duration: 3200,
            curve: 1.28,
            essential: true,
          });
        }, 820);
        schedule(handoff, 3900);
        schedule(complete, 4900);
      });
    } catch (error) {
      onErrorRef.current(error instanceof Error ? error.message : "地球开场初始化失败");
      complete();
    }

    return () => {
      active = false;
      timers.forEach((timer) => window.clearTimeout(timer));
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [collection, reducedMotion, runId]);

  return (
    <section
      aria-label="13110 地球开场"
      className={`globe-intro phase-${phase}`}
      data-phase={phase}
    >
      <div className="globe-map" ref={containerRef} />
      <div className="globe-copy" aria-live="polite">
        <span>13110</span>
        <h1>从新能源汽车补贴<br />进入全国政策<br />全景推演厅</h1>
        <p>{phase === "approach" || phase === "handoff" ? "正在锁定中国省域政策网络" : "正在建立全球情景视角"}</p>
      </div>
      <div className="globe-progress" aria-hidden="true">
        <i />
        <span>{phase === "approach" || phase === "handoff" ? "CHINA · COMPLETE MAP" : "GLOBAL VIEW"}</span>
      </div>
      <button className="skip-intro" onClick={() => onCompleteRef.current()} type="button">
        跳过开场
      </button>
    </section>
  );
}
