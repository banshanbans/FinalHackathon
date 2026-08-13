import { MapChart } from "echarts/charts";
import { TooltipComponent, VisualMapComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import chinaAnalysisMapUrl from "../assets/maps/china-analysis-map.svg?url";
import type { ProvinceProfile } from "../types";

echarts.use([MapChart, TooltipComponent, VisualMapComponent, SVGRenderer]);

const MAP_NAME = "policyscope-china-analysis-map";
const TERRITORY_CONTEXT = ["香港", "澳门", "台湾"] as const;
let mapRegistration: Promise<void> | undefined;

export interface ProvinceMapLink {
  id: string;
  sourceCode: string;
  targetCode: string;
  kind: "competition" | "coordination" | "topk";
  label: string;
  selected?: boolean;
}

export interface ProvinceMapTooltipDetail {
  strategy?: string;
  dataQualityLabel?: string;
}

interface MapRegionGeometry { getCenter: () => number[]; }
interface MapCoordinateSystem {
  getRegion: (name: string) => MapRegionGeometry | undefined;
  dataToPoint: (point: number[]) => number[];
}
interface MapChartInstance {
  getHeight: () => number;
  getWidth: () => number;
  getModel: () => { getSeriesByIndex: (index: number) => { coordinateSystem?: MapCoordinateSystem } | undefined };
}

function ensureMapRegistered() {
  if (!mapRegistration) {
    mapRegistration = fetch(chinaAnalysisMapUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`MAP_ASSET_${response.status}`);
        return response.text();
      })
      .then((svg) => echarts.registerMap(MAP_NAME, { svg }));
  }
  return mapRegistration;
}

function quantile(values: number[], percentile: number) {
  const ordered = [...values].sort((left, right) => left - right);
  const index = (ordered.length - 1) * percentile;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower);
}

export function ProvinceMap({
  profiles,
  values,
  selectedCode,
  onSelect,
  compact = false,
  height,
  metricLabel = "地方支持强度",
  emptyMessage,
  mode = "absolute",
  unit = "指数点",
  overlayLinks = [],
  focusCodes = [],
  tooltipDetails = {},
  onLinkSelect,
}: {
  profiles: ProvinceProfile[];
  values: Record<string, number | null | undefined>;
  selectedCode?: string;
  onSelect?: (provinceCode: string) => void;
  compact?: boolean;
  height?: number;
  metricLabel?: string;
  emptyMessage?: string;
  mode?: "absolute" | "difference";
  unit?: string;
  overlayLinks?: ProvinceMapLink[];
  focusCodes?: string[];
  tooltipDetails?: Record<string, ProvinceMapTooltipDetail | undefined>;
  onLinkSelect?: (link: ProvinceMapLink) => void;
}) {
  const [mapState, setMapState] = useState<"loading" | "ready" | "error">("loading");
  const mapCanvasRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<MapChartInstance | undefined>(undefined);
  const [overlayGeometry, setOverlayGeometry] = useState<{
    width: number;
    height: number;
    anchors: Record<string, [number, number]>;
  }>({ width: 1, height: 1, anchors: {} });
  useEffect(() => {
    let active = true;
    void ensureMapRegistered()
      .then(() => active && setMapState("ready"))
      .catch(() => active && setMapState("error"));
    return () => { active = false; };
  }, []);
  const byName = useMemo(() => new Map(profiles.map((profile) => [profile.short_name, profile])), [profiles]);
  const updateOverlayGeometry = useCallback(() => {
    const chart = chartRef.current;
    const coordinateSystem = chart?.getModel().getSeriesByIndex(0)?.coordinateSystem;
    if (!chart || !coordinateSystem) return;
    const anchors: Record<string, [number, number]> = {};
    for (const profile of profiles) {
      const center = coordinateSystem.getRegion(profile.short_name)?.getCenter();
      if (!center) continue;
      const point = coordinateSystem.dataToPoint(center);
      if (Number.isFinite(point[0]) && Number.isFinite(point[1])) {
        anchors[profile.province_code] = [point[0], point[1]];
      }
    }
    setOverlayGeometry({ width: chart.getWidth(), height: chart.getHeight(), anchors });
  }, [profiles]);
  useEffect(() => {
    const container = mapCanvasRef.current;
    if (!container || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(() => requestAnimationFrame(updateOverlayGeometry));
    observer.observe(container);
    return () => observer.disconnect();
  }, [updateOverlayGeometry]);
  const focusSet = useMemo(() => new Set([...focusCodes, ...(selectedCode ? [selectedCode] : [])]), [focusCodes, selectedCode]);
  const focusActive = focusSet.size > 0;
  const numericValues = useMemo(
    () => profiles.map((profile) => values[profile.province_code]).filter((value): value is number => Number.isFinite(value)),
    [profiles, values],
  );
  const domain = useMemo(() => {
    if (!numericValues.length) return { min: 0, max: 1, legend: "等待数据" };
    if (mode === "difference") {
      const maximum = Math.max(...numericValues.map((value) => Math.abs(value)), 0.0001);
      return { min: -maximum, max: maximum, legend: `±${maximum.toFixed(2)} ${unit}` };
    }
    const low = quantile(numericValues, 0.05);
    const high = quantile(numericValues, 0.95);
    const padding = Math.max((high - low) * 0.08, 0.01);
    return { min: low - padding, max: high + padding, legend: `${low.toFixed(1)}–${high.toFixed(1)} ${unit}` };
  }, [mode, numericValues, unit]);
  const hasValues = numericValues.length > 0;
  const data = useMemo(() => [...profiles.map((profile) => {
    const value = values[profile.province_code];
    const missing = !Number.isFinite(value);
    const focused = focusSet.has(profile.province_code);
    const focusStyle = focusActive ? {
      borderColor: focused ? (profile.province_code === selectedCode ? "#17268f" : "#665ac6") : "#ffffff",
      borderWidth: focused ? 2 : 1,
      opacity: focused ? 1 : 0.3,
    } : {};
    return {
      name: profile.short_name,
      value: missing ? undefined : value,
      missing,
      provinceCode: profile.province_code,
      itemStyle: missing ? {
        areaColor: "#eef1f6",
        borderColor: focused ? "#665ac6" : "#cbd2df",
        borderType: "dashed",
        borderWidth: focused ? 2 : 1,
        opacity: focusActive && !focused ? 0.3 : 1,
        decal: { symbol: "rect", symbolSize: 2, color: "rgba(123,132,150,.22)", dashArrayX: [1, 1], dashArrayY: [2, 2], rotation: 0.7 },
      } : focusStyle,
    };
  }), ...TERRITORY_CONTEXT.map((name) => ({
    name,
    value: undefined,
    missing: false,
    territoryContext: true,
    itemStyle: {
      areaColor: "#dcecef",
      borderColor: "#51aeb0",
      borderWidth: 1.2,
      opacity: 1,
    },
  }))], [focusActive, focusSet, profiles, selectedCode, values]);
  const option = useMemo(() => ({
    animationDuration: 300,
    tooltip: {
      trigger: "item",
      borderColor: "#dfe3ef",
      backgroundColor: "rgba(255,255,255,.98)",
      textStyle: { color: "#172033", fontFamily: "Inter, Noto Sans SC" },
      formatter: (params: { name: string; value?: number; data?: { missing?: boolean; provinceCode?: string; territoryContext?: boolean } }) => {
        if (params.data?.territoryContext) {
          return `<strong>${params.name}</strong><br/>中国版图展示<br/>不参与本次 31 省推演`;
        }
        const detail = params.data?.provinceCode ? tooltipDetails[params.data.provinceCode] : undefined;
        const suffix = [detail?.strategy ? `当前策略：${detail.strategy}` : null, detail?.dataQualityLabel ?? "代理数据基线"].filter(Boolean).join("<br/>");
        if (!hasValues || params.data?.missing) return `<strong>${params.name}</strong><br/>暂无当前指标值<br/>${suffix}`;
        const value = Number(params.value ?? 0);
        const display = mode === "difference" ? `${value >= 0 ? "+" : ""}${value.toFixed(2)} ${unit}` : `${value.toFixed(1)} ${unit}`;
        return `<strong>${params.name}</strong><br/>${metricLabel} ${display}<br/>${suffix}`;
      },
    },
    visualMap: {
      min: domain.min,
      max: domain.max,
      calculable: false,
      orient: "horizontal",
      left: 14,
      bottom: 8,
      itemWidth: compact ? 96 : 148,
      itemHeight: 8,
      text: mode === "difference" ? ["干预方案更高", "原始方案更高"] : ["高", "低"],
      textGap: 8,
      textStyle: { color: "#536077", fontSize: 11 },
      inRange: { color: mode === "difference" ? ["#6552b8", "#f4f6fa", "#14888d"] : ["#e6e9ff", "#9eacff", "#4d5ed1"] },
      outOfRange: { color: "#eef1f6" },
    },
    series: [{
      type: "map",
      map: MAP_NAME,
      roam: false,
      selectedMode: false,
      nameProperty: "name",
      data,
      left: compact ? 8 : 20,
      right: compact ? 8 : 20,
      top: 8,
      bottom: 28,
      label: { show: false },
      itemStyle: { areaColor: "#eef1f6", borderColor: "#ffffff", borderWidth: 1.2 },
      select: { label: { show: false }, itemStyle: { areaColor: "#2638cc", borderColor: "#17268f", borderWidth: 2 } },
      emphasis: { label: { show: false }, itemStyle: { borderColor: "#202537", borderWidth: 2 } },
    }],
  }), [compact, data, domain, hasValues, metricLabel, mode, tooltipDetails, unit]);

  if (mapState === "loading") return <div className="map-loading"><span className="spinner" />正在加载分析地图…</div>;
  if (mapState === "error") return <div className="map-loading map-error">分析地图资源加载失败，请刷新后重试。</div>;
  return <div className={`province-map ${compact ? "compact" : ""}`}>
    <div className="province-map-canvas" ref={mapCanvasRef} style={{ height: height ?? (compact ? 250 : 460) }}>
    <ReactEChartsCore echarts={echarts} option={option} notMerge opts={{ renderer: "svg" }} style={{ height: "100%", width: "100%" }} onChartReady={(chart: unknown) => { chartRef.current = chart as MapChartInstance; requestAnimationFrame(updateOverlayGeometry); }} onEvents={{ click: (params: { name: string }) => { const profile = byName.get(params.name); if (profile && onSelect) onSelect(profile.province_code); } }} />
    {!!overlayLinks.length && <svg aria-label="省际竞争、协同与 Top-K 资源链" className="province-map-links" viewBox={`0 0 ${overlayGeometry.width} ${overlayGeometry.height}`}>
      <defs>
        <marker id="competition-arrow" markerHeight="6" markerUnits="strokeWidth" markerWidth="6" orient="auto" refX="5" refY="3" viewBox="0 0 6 6"><path d="M0,0 L6,3 L0,6 Z" /></marker>
        <marker id="topk-arrow" markerHeight="6" markerUnits="strokeWidth" markerWidth="6" orient="auto" refX="5" refY="3" viewBox="0 0 6 6"><path d="M0,0 L6,3 L0,6 Z" /></marker>
      </defs>
      {overlayLinks.map((link) => {
        const source = overlayGeometry.anchors[link.sourceCode];
        const target = overlayGeometry.anchors[link.targetCode];
        if (!source || !target) return null;
        const selectLink = () => onLinkSelect?.(link);
        return <line aria-label={link.label} className={`${link.kind}${link.selected ? " selected" : ""}`} key={link.id} markerEnd={link.kind === "coordination" ? undefined : `url(#${link.kind === "competition" ? "competition" : "topk"}-arrow)`} onClick={selectLink} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectLink(); } }} role={onLinkSelect ? "button" : undefined} tabIndex={onLinkSelect ? 0 : undefined} vectorEffect="non-scaling-stroke" x1={source[0]} x2={target[0]} y1={source[1]} y2={target[1]}><title>{link.label}</title></line>;
      })}
    </svg>}
    {!hasValues && <div className="map-empty-layer"><div><strong>{emptyMessage ?? "等待省级决策"}</strong><small>完成相应行动后显示全国分布</small></div></div>}
    </div>
    <div className="map-scale-note">动态色阶：{domain.legend} · 空值以纹理表示</div>
    {!compact && <div className="province-keyboard-list" aria-label="31 个省级行政区">{profiles.map((profile) => <button aria-pressed={profile.province_code === selectedCode} className={profile.province_code === selectedCode ? "selected" : ""} key={profile.province_code} onClick={() => onSelect?.(profile.province_code)} type="button">{profile.short_name}</button>)}</div>}
    <p className="map-source-note">分析底图：自然资源部标准地图 GS(2016)1609 衍生资源｜全国版图完整展示；31 省参与推演，港澳台不进入计算</p>
  </div>;
}
