import type { Feature, FeatureCollection, MultiPolygon } from "geojson";

export interface ProvinceProperties {
  province_code: string;
  name: string;
  region_role: "simulation-province" | "territory-context";
  included_in_simulation: boolean;
  interactive: boolean;
  representation: "official-outline" | "official-scale-marker";
  source_path_sha256: string;
  source_subpath_count: number;
  render_vertex_count: number;
  delta?: number;
  frame?: number;
}

export type ProvinceFeature = Feature<MultiPolygon, ProvinceProperties>;

export interface PresentationMapCollection extends FeatureCollection<MultiPolygon, ProvinceProperties> {
  name: string;
  bbox: [number, number, number, number];
  metadata: {
    schema_version: "presentation-map-v2";
    source: string;
    source_geometry_sha256: string;
    simulation_geometry_sha256: string;
    source_svg_sha256: string;
    projection: string;
    render_only: true;
    distance_analysis_allowed: false;
    curve_sampling_steps: number;
    simulation_region_count: 31;
    territory_context_count: 3;
    territory_context_codes: ["71", "81", "82"];
  };
}

export interface FrameMetric {
  fps: number;
  p95FrameMs: number;
  droppedFrameRatio: number;
  sampleCount: number;
}

export interface TechSpikeTelemetry {
  renderer: "webgl" | "svg";
  mapLoaded: boolean;
  deckLoaded: boolean;
  featureCount: number;
  currentFrame: number;
  webglVersion: string;
  geometryHash: string;
  frameMetric: FrameMetric;
  lastError: string | null;
}

declare global {
  interface Window {
    __POLICYSCOPE_TECH_SPIKE__: TechSpikeTelemetry;
  }
}
