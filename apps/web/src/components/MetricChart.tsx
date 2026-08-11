import { BarChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";

import type { ComparisonResult } from "../types";

const LABELS: Record<string, string> = {
  overall_policy_benefit: "综合收益",
  policy_accessibility: "政策可及性",
  innovation_vitality: "创新活力",
  employment_support: "就业支撑",
  regional_gap: "区域差距",
  fiscal_pressure: "财政压力",
  cooperation_density: "协作密度",
};

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export function MetricChart({ comparison }: { comparison: ComparisonResult }) {
  const entries = Object.entries(comparison.national_metrics).filter(([key]) => LABELS[key]);
  const option: EChartsCoreOption = {
    animationDuration: 700,
    grid: { left: 14, right: 16, top: 18, bottom: 16, containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: "#102432", borderColor: "#2a5266" },
    legend: { data: ["Control", "Treatment"], textStyle: { color: "#91a9b7" }, top: 0 },
    xAxis: {
      type: "value",
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: "rgba(108, 151, 170, .12)" } },
      axisLabel: { color: "#668397" },
    },
    yAxis: {
      type: "category",
      data: entries.map(([key]) => LABELS[key]),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#a8bdc8" },
    },
    series: [
      {
        name: "Control",
        type: "bar",
        data: entries.map(([, value]) => value.control),
        itemStyle: { color: "#476477", borderRadius: [0, 3, 3, 0] },
        barMaxWidth: 8,
      },
      {
        name: "Treatment",
        type: "bar",
        data: entries.map(([, value]) => value.treatment),
        itemStyle: { color: "#1fc8b1", borderRadius: [0, 3, 3, 0] },
        barMaxWidth: 8,
      },
    ],
  };
  return <ReactEChartsCore echarts={echarts} option={option} style={{ height: 300 }} />;
}
