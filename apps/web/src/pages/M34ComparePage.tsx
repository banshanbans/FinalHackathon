import { useM34 } from "../context/M34Context";

const LABELS: Record<string, string> = { regional_development_gap: "区域发展差距", central_fiscal_burden: "中央财政负担", local_fiscal_pressure: "地方财政压力", nev_demand: "新能源汽车需求", new_investment_concentration: "新增投资集中度", industrial_agglomeration: "产业集聚度" };

export default function M34ComparePage() {
  const flow = useM34();
  if (!flow.world || !flow.comparison) return <div className="v3-empty-page"><h2>{flow.world?.status === "completed" ? "正在加载年度比较…" : "完成 Q1–Q4 后才能查看年度比较"}</h2></div>;
  const comparison = flow.comparison;
  return <div className="v32-page"><header className="v32-heading"><div><span className="v32-eyebrow">Q4 年度同源比较</span><h1>{comparison.conclusion}</h1></div></header><section className="v3-card"><div className="v32-share-summary"><b>唯一主动差异：{comparison.active_difference === "policy" ? "政策" : "事件"}</b><b>政策同源：{comparison.same_policy ? "是" : "否"}</b><b>事件同源：{comparison.same_event ? "是" : "否"}</b></div><div className="v32-kpi-grid">{Object.entries(comparison.national_metrics).map(([key, metric]) => <div key={key}><span>{LABELS[key] ?? key}</span><b>Δ {metric.delta > 0 ? "+" : ""}{metric.delta.toFixed(2)}</b><small>{metric.control.toFixed(2)} → {metric.treatment.toFixed(2)}</small></div>)}</div></section><section className="v3-card"><span className="v32-eyebrow">中央 Agent · 实验后唯一一次</span><h2>ΔGap {comparison.delta_gap > 0 ? "+" : ""}{comparison.delta_gap.toFixed(2)} · {comparison.gap_direction === "narrowed" ? "差距缩小" : comparison.gap_direction === "widened" ? "差距扩大" : "差距持平"}</h2><p>{comparison.central_review}</p><small>Fallback 记录 {comparison.fallback_count} 次；不解读为现实政府或企业的未来决定。</small></section></div>;
}
