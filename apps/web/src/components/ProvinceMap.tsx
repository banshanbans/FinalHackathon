import { MapChart } from "echarts/charts";
import { TooltipComponent, VisualMapComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { useEffect, useMemo, useState } from "react";

import chinaStandardMapUrl from "../assets/maps/china-standard-map.svg?url";
import type { ProvinceProfile } from "../types";

echarts.use([MapChart, TooltipComponent, VisualMapComponent, SVGRenderer]);

const MAP_NAME = "policyscope-china-standard-map";
let mapRegistration: Promise<void> | undefined;

function ensureMapRegistered() {
  if (!mapRegistration) {
    mapRegistration = fetch(chinaStandardMapUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`MAP_ASSET_${response.status}`);
        return response.text();
      })
      .then((svg) => {
        echarts.registerMap(MAP_NAME, { svg });
      });
  }
  return mapRegistration;
}

const EXCLUDED_NAMES = new Set(["台湾", "香港", "澳门", "南海诸岛"]);

function metricColor(value: number) {
  if (value < 45) return "#e9ecff";
  if (value < 55) return "#cfd5ff";
  if (value < 65) return "#aeb8ff";
  if (value < 75) return "#6674ed";
  return "#2638cc";
}

export function ProvinceMap({
  profiles,
  values,
  selectedCode,
  onSelect,
  compact = false,
  height,
  metricLabel = "企业参与指数",
  emptyMessage,
}: {
  profiles: ProvinceProfile[];
  values: Record<string, number>;
  selectedCode?: string;
  onSelect?: (provinceCode: string) => void;
  compact?: boolean;
  height?: number;
  metricLabel?: string;
  emptyMessage?: string;
}) {
  const [mapState, setMapState] = useState<"loading" | "ready" | "error">("loading");
  useEffect(() => {
    let active = true;
    void ensureMapRegistered()
      .then(() => active && setMapState("ready"))
      .catch(() => active && setMapState("error"));
    return () => {
      active = false;
    };
  }, []);
  const byName = useMemo(
    () => new Map(profiles.map((profile) => [profile.short_name, profile])),
    [profiles],
  );
  const selectedName = profiles.find((item) => item.province_code === selectedCode)?.short_name;
  const hasValues = Object.keys(values).length > 0;
  const data = useMemo(
    () => [
      ...profiles.map((profile) => {
        const value = values[profile.province_code];
        const missing = value === undefined;
        return {
          name: profile.short_name,
          value: missing ? "-" : value,
          missing,
          itemStyle: {
            areaColor: missing ? "#edf0f5" : metricColor(value),
            color: missing ? "#edf0f5" : metricColor(value),
            borderColor: "#ffffff",
            borderWidth: 0.8,
          },
        };
      }),
      ...["台湾", "香港", "澳门", "南海诸岛"].map((name) => ({
        name,
        value: 0,
        itemStyle: { areaColor: "#e8ebf5", color: "#e8ebf5", borderColor: "#b9c1d6" },
        emphasis: { disabled: true },
      })),
    ],
    [profiles, values],
  );

  const option = useMemo(
    () => ({
      animationDuration: 350,
      tooltip: {
        trigger: "item",
        borderColor: "#dfe3ef",
        backgroundColor: "rgba(255,255,255,.98)",
        textStyle: { color: "#172033", fontFamily: "Inter, Noto Sans SC" },
        formatter: (params: { name: string; value?: number | string; data?: { missing?: boolean } }) => {
          if (EXCLUDED_NAMES.has(params.name)) return `${params.name}<br/>不进入本次 31 省计算`;
          if (!hasValues) return `<strong>${params.name}</strong><br/>等待省级决策`;
          if (params.data?.missing) return `<strong>${params.name}</strong><br/>暂无当前指标值`;
          return `<strong>${params.name}</strong><br/>${metricLabel} ${Number(params.value ?? 0).toFixed(1)} / 100`;
        },
      },
      visualMap: {
        min: 35,
        max: 85,
        calculable: false,
        orient: "horizontal",
        left: 12,
        bottom: 8,
        itemWidth: compact ? 88 : 122,
        itemHeight: 8,
        text: ["高", "低"],
        textGap: 8,
        textStyle: { color: "#677189", fontSize: 10 },
        inRange: { color: ["#e9ecff", "#aeb8ff", "#5d6cf0", "#2638cc"] },
        outOfRange: { color: "#e8ebf5" },
      },
      series: [
        {
          type: "map",
          map: MAP_NAME,
          roam: false,
          selectedMode: "single",
          selectedMap: selectedName ? { [selectedName]: true } : {},
          nameProperty: "name",
          data,
          left: compact ? 8 : 22,
          right: compact ? 8 : 22,
          top: 2,
          bottom: 22,
          label: {
            // Province labels are already part of the source artwork.
            // Rendering a second ECharts label layer creates duplicates and
            // produces poor auto-centering for narrow or multipart regions.
            show: false,
          },
          itemStyle: { areaColor: "#eef0ff", color: "#eef0ff", borderColor: "#ffffff", borderWidth: 1 },
          select: {
            label: { show: false },
            itemStyle: { areaColor: "#2737d5", color: "#2737d5", borderColor: "#111b8a", borderWidth: 1.8 },
          },
          emphasis: {
            label: { show: false },
            itemStyle: { areaColor: "#7480f5", color: "#7480f5", borderColor: "#ffffff" },
          },
        },
      ],
    }),
    [compact, data, hasValues, metricLabel, selectedName],
  );

  if (mapState === "loading") {
    return <div className="map-loading"><span className="spinner" />正在加载自然资源部标准地图矢量资源…</div>;
  }
  if (mapState === "error") {
    return <div className="map-loading map-error">标准地图资源加载失败，请刷新后重试。</div>;
  }

  return (
    <div className={`province-map ${compact ? "compact" : ""}`}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        notMerge
        opts={{ renderer: "svg" }}
        style={{ height: height ?? (compact ? 250 : 410), width: "100%" }}
        onEvents={{
          click: (params: { name: string }) => {
            const profile = byName.get(params.name);
            if (profile && onSelect) onSelect(profile.province_code);
          },
        }}
      />
      {!hasValues && <div className="map-empty-layer"><IconMessage message={emptyMessage ?? "等待省级决策"} /></div>}
      {!compact && (
        <div className="province-keyboard-list" aria-label="31 个省级行政区">
          {profiles.map((profile) => (
            <button
              aria-pressed={profile.province_code === selectedCode}
              className={profile.province_code === selectedCode ? "selected" : ""}
              key={profile.province_code}
              onClick={() => onSelect?.(profile.province_code)}
              type="button"
            >
              {profile.short_name}
            </button>
          ))}
        </div>
      )}
      <p className="map-source-note">
        底图：自然资源部标准地图 GS(2016)1609 ｜ 指标范围：中国大陆 31 个省级行政区
      </p>
    </div>
  );
}

function IconMessage({ message }: { message: string }) {
  return <div><span className="material-symbols-rounded" aria-hidden="true">hourglass_empty</span><strong>{message}</strong><small>地方行动提交后将显示全国分布</small></div>;
}
