import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useV32 } from "../context/V32Context";

const metricLabels: Record<string, string> = { regional_development_gap: "区域发展差距", central_fiscal_burden: "中央财政负担", local_fiscal_pressure: "地方财政压力", nev_demand: "新能源汽车需求", new_investment_concentration: "新增投资集中度", industrial_agglomeration: "产业集聚度" };

export default function V32ComparePage() {
  const flow = useV32();
  const navigate = useNavigate();
  useEffect(() => { if (flow.world?.status === "completed" && !flow.comparison) void flow.loadComparison(); }, [flow]);
  const result = flow.comparison;
  if (!flow.world || flow.world.status !== "completed") return <div className="v3-empty-page"><Icon name="hourglass_empty" /><h2>推演尚未完成</h2><button onClick={() => navigate(`/experiments/${flow.world?.experiment_id ?? ""}/live`)} type="button">返回实验运行</button></div>;
  if (!result) return <div className="route-loader"><span className="spinner" /><strong>正在生成结果对比…</strong></div>;
  return <div className="v32-page v32-compare-page"><header className={`v32-conclusion ${result.gap_direction}`}><span className="v32-eyebrow">结果复盘</span><h1>{result.conclusion}</h1><div><span>受益省份 <strong>{result.top_beneficiaries.join("、")}</strong></span><span>承压省份 <strong>{result.top_pressured.join("、")}</strong></span></div></header>
    <section className="v32-answer-grid"><div className="v3-card"><small>Gap 方向</small><strong className={result.delta_gap <= 0 ? "good" : "warn"}>{result.delta_gap > 0 ? "+" : ""}{result.delta_gap.toFixed(2)}</strong><span>模拟指数点</span></div><div className="v3-card"><small>中央财政负担</small><strong>{result.national_metrics.central_fiscal_burden.delta > 0 ? "+" : ""}{result.national_metrics.central_fiscal_burden.delta.toFixed(2)}</strong><span>模拟指数变化</span></div><div className="v3-card"><small>受益省份</small><p>{result.top_beneficiaries.join("、") || "—"}</p></div><div className="v3-card"><small>承压省份</small><p>{result.top_pressured.join("、") || "—"}</p></div></section>
    <section className="v3-card"><div className="v3-card-title"><Icon name="analytics" /><div><small>六项中央指标</small><h2>原始方案 / 干预方案</h2></div></div><div className="v32-comparison-table"><div className="header"><span>指标</span><span>原始方案</span><span>干预方案</span><span>变化</span></div>{Object.entries(result.national_metrics).map(([key, item]) => <div key={key}><strong>{metricLabels[key] ?? "未知指标"}</strong><span>{item.control.toFixed(2)}</span><span>{item.treatment.toFixed(2)}</span><b className={item.delta <= 0 && key.includes("gap") ? "good" : ""}>{item.delta > 0 ? "+" : ""}{item.delta.toFixed(2)}</b></div>)}</div></section>
    <section className="v3-card"><div className="v3-card-title"><Icon name="directions_car" /><div><small>车企行动</small><h2>行动调整</h2></div></div><div className="v32-company-deltas">{result.automaker_deltas.map((item) => <button key={item.automaker_id} onClick={() => navigate(`${location.pathname}?company=${item.automaker_id}`)} type="button"><strong>{item.display_name}</strong><span>{item.changed_province_count} 个省份调整</span><small>{item.facility_changed ? "产能意向已调整" : "产能意向不变"}</small></button>)}</div></section>
    <div className="v32-method-link"><span>模拟推演结果，仅作方案比较。</span><button onClick={() => navigate(`/experiments/${result.experiment_id}/methods`)} type="button">方法与数据</button></div>
  </div>;
}
