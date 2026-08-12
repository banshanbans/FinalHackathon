import { BarChart, LineChart, PieChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";

import type { Participation, ProvincePriorityGoal } from "../types";
import type { MetricTrendPoint } from "../utils/dashboardSelectors";
import { PRIORITY_GOAL_LABELS } from "../utils/display";

echarts.use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const textStyle = { color: "#7b8498", fontFamily: "Inter Variable, Noto Sans SC", fontSize: 10 };

export function MetricTrendChart({ points }: { points: MetricTrendPoint[] }) {
  if (points.length === 0) return <div className="chart-empty"><span className="material-symbols-rounded">timeline</span><strong>等待环境结算</strong><p>每次环境更新后将增加一个真实阶段节点。</p></div>;
  const option: EChartsCoreOption = {
    animation: false,
    color: ["#5548e7", "#4d83ed", "#52b5dc", "#38a878"],
    tooltip: { trigger: "axis" },
    legend: { bottom: 0, icon: "roundRect", itemWidth: 10, itemHeight: 3, textStyle },
    grid: { left: 30, right: 12, top: 18, bottom: 34 },
    xAxis: { type: "category", data: points.map((point) => point.phase), axisLine: { lineStyle: { color: "#e4e7ef" } }, axisLabel: textStyle },
    yAxis: { type: "value", min: 0, max: 100, splitLine: { lineStyle: { color: "#edf0f4" } }, axisLabel: textStyle },
    series: ([
      { name: "企业参与", key: "enterprise_participation_index" },
      { name: "更新意愿", key: "equipment_renewal_willingness_index" },
      { name: "融资可达", key: "sme_financing_accessibility_index" },
      { name: "财政压力", key: "local_fiscal_pressure_index" },
    ] satisfies Array<{ name: string; key: Exclude<keyof MetricTrendPoint, "phase"> }>).map(({ name, key }) => ({ name, type: "line", smooth: true, symbolSize: 5, data: points.map((point) => point[key] ?? null) })),
  };
  return <ReactEChartsCore echarts={echarts} option={option} style={{ height: 205 }} />;
}

const PARTICIPATION_LABELS: Record<Participation, string> = { participate: "参与", conditional: "条件参与", wait: "观望", decline: "拒绝" };

export function EnterpriseParticipationChart({ counts }: { counts: Record<Participation, number> }) {
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  if (total === 0) return <div className="chart-empty"><span className="material-symbols-rounded">donut_large</span><strong>等待企业响应</strong><p>T2 形成 186 个企业群体行动后显示结构。</p></div>;
  const option: EChartsCoreOption = {
    animation: false,
    color: ["#5548e7", "#52b5dc", "#e9ae5d", "#aeb5c4"],
    tooltip: { trigger: "item", formatter: "{b}：{c} 个群体（{d}%）" },
    legend: { orient: "vertical", right: 8, top: "middle", icon: "circle", itemWidth: 8, itemHeight: 8, textStyle },
    series: [{ type: "pie", radius: ["48%", "72%"], center: ["34%", "52%"], label: { show: false }, data: Object.entries(counts).map(([key, value]) => ({ name: PARTICIPATION_LABELS[key as Participation], value })) }],
  };
  return <div className="donut-chart-wrap"><ReactEChartsCore echarts={echarts} option={option} style={{ height: 205 }} /><div className="donut-chart-center"><span>企业群体</span><strong>{total}</strong></div></div>;
}

export function ProvinceGoalChart({ goals }: { goals: Array<[ProvincePriorityGoal, number]> }) {
  if (goals.length === 0) return <div className="chart-empty"><span className="material-symbols-rounded">bar_chart</span><strong>等待省级决策</strong><p>T1 完成后显示主要目标分布。</p></div>;
  const shown = goals.slice(0, 6).reverse();
  const option: EChartsCoreOption = {
    animation: false,
    color: ["#6d62e8"],
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 92, right: 20, top: 12, bottom: 16 },
    xAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf0f4" } }, axisLabel: textStyle },
    yAxis: { type: "category", data: shown.map(([key]) => PRIORITY_GOAL_LABELS[key]), axisLine: { show: false }, axisTick: { show: false }, axisLabel: textStyle },
    series: [{ type: "bar", barWidth: 9, data: shown.map(([, value]) => value), itemStyle: { borderRadius: [0, 5, 5, 0] } }],
  };
  return <ReactEChartsCore echarts={echarts} option={option} style={{ height: 205 }} />;
}
