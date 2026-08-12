import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { ProvinceMap } from "../components/ProvinceMap";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";

const labels: Record<string, string> = { regional_development_gap: "区域发展差距", central_fiscal_burden: "中央财政负担", local_fiscal_pressure: "地方财政压力", nev_demand: "新能源汽车需求", new_investment_concentration: "新增投资集中度", industrial_agglomeration: "产业集聚度" };

export default function ComparePage() {
  const flow = usePolicyScopeContext(); const navigate = useNavigate();
  if (!flow.world) return <div className="v3-empty-page"><h2>尚未创建实验</h2></div>;
  if (!flow.branch && flow.world.intervention_decision === "rejected") return <div className="v3-page"><div className="v3-page-heading"><div><span className="v3-kicker">单线复盘</span><h1>用户拒绝干预</h1><p>只运行了原始方案，不生成或伪造 A/B 比较。</p></div></div><section className="v3-card"><h2>原始方案次年结果</h2><div className="v3-kpis">{Object.entries(flow.world.national_metrics).filter(([key]) => key !== "schema_version").map(([key, value]) => <div key={key}><small>{labels[key] ?? key}</small><strong>{Number(value).toFixed(2)}</strong></div>)}</div></section></div>;
  if (!flow.comparison || !flow.control || !flow.treatment) return <div className="v3-empty-page"><Icon name="difference" /><h2>同源 A/B 尚未结算</h2><p>原始方案与干预方案将从同一首年检查点运行至次年年末。</p><button className="v3-primary" disabled={!flow.branch || Boolean(flow.busyLabel)} onClick={() => void flow.runComparison()} type="button">运行次年同源 A/B</button></div>;
  const result = flow.comparison; const controlValues = Object.fromEntries(Object.entries(flow.control.province_states).map(([code, state]) => [code, state.development_index])); const treatmentValues = Object.fromEntries(Object.entries(flow.treatment.province_states).map(([code, state]) => [code, state.development_index]));
  return <div className="v3-page"><div className="v3-page-heading"><div><span className="v3-kicker">COMPLETE · comparison-v4</span><h1>原始方案 / 干预方案</h1><p>同一色阶、同一首年 Checkpoint、同一 seed；ΔGap 为干预减原始。</p></div><div className={`v3-delta-gap ${result.delta_gap <= 0 ? "good" : "warn"}`}><small>ΔGap</small><strong>{result.delta_gap > 0 ? "+" : ""}{result.delta_gap.toFixed(3)}</strong><span>{result.delta_gap < 0 ? "差距缩小" : "差距扩大或不变"}</span></div></div>
    <div className="v3-policy-diff">{result.policy_diff.map((item) => <div key={item.path}><small>{item.path.replace("_central_share", "")}</small><strong>{(item.from_value * 100).toFixed(0)}% → {(item.to_value * 100).toFixed(0)}%</strong></div>)}</div>
    <div className="v3-compare-maps"><section className="v3-card"><h2>原始方案 · 省级发展指数</h2><ProvinceMap compact height={330} metricLabel="新能源汽车发展指数" onSelect={(code) => navigate(`/experiments/${flow.world!.experiment_id}/provinces/${code}?branch=control`)} profiles={flow.profiles} values={controlValues} /></section><section className="v3-card"><h2>干预方案 · 省级发展指数</h2><ProvinceMap compact height={330} metricLabel="新能源汽车发展指数" onSelect={(code) => navigate(`/experiments/${flow.world!.experiment_id}/provinces/${code}?branch=treatment`)} profiles={flow.profiles} values={treatmentValues} /></section></div>
    <section className="v3-card"><h2>六项中央指标权衡</h2><div className="v3-metric-table">{Object.entries(result.national_metrics).map(([key, item]) => <div key={key}><span>{labels[key] ?? key}</span><b>{item.control.toFixed(2)}</b><Icon name="arrow_forward" /><b>{item.treatment.toFixed(2)}</b><strong className={item.delta < 0 ? "down" : "up"}>{item.delta > 0 ? "+" : ""}{item.delta.toFixed(3)}</strong></div>)}</div></section>
    <section className="v3-card"><div className="v3-card-title"><Icon name="directions_car" /><div><small>车企模拟迁移</small><h2>10 家全国性 Agent</h2></div></div><div className="v3-transition-grid">{result.automaker_strategy_transitions.map((item) => <button key={item.automaker_id} onClick={() => navigate(`${location.pathname}?company=${item.automaker_id}`)} type="button"><strong>{item.display_name}</strong><span>{item.changed_province_allocations} 个省份投入变化</span><small>{item.facility_changes.length ? "设施动作变化" : "设施动作不变"}</small></button>)}</div></section>
  </div>;
}
