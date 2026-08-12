import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { ProvinceMap } from "../components/ProvinceMap";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";

const layers = { support: "地方支持强度", consumer: "消费端补贴", fixed: "固定成本补贴", variable: "可变成本补贴", wtp: "消费者 WTP", industry: "产业基础 / 电池节点", automaker: "车企销售投入" } as const;

export default function LiveExperimentPage() {
  const flow = usePolicyScopeContext(); const navigate = useNavigate(); const [layer, setLayer] = useState<keyof typeof layers>("support");
  const world = flow.world;
  const values = useMemo(() => Object.fromEntries(flow.profiles.map((profile) => {
    const action = world?.province_actions[profile.province_code]; const state = world?.province_states[profile.province_code];
    const automaker = world ? Object.values(world.automaker_actions).map((item) => item.province_market_actions.find((x) => x.province_code === profile.province_code)?.sales_investment_intensity ?? 0) : [];
    const value = layer === "support" ? (action?.overall_support_intensity ?? 0) * 100 : layer === "consumer" ? (action?.subsidy_mix.consumer ?? 0) * 100 : layer === "fixed" ? (action?.subsidy_mix.fixed_cost ?? 0) * 100 : layer === "variable" ? (action?.subsidy_mix.variable_cost ?? 0) * 100 : layer === "wtp" ? profile.willingness_to_pay_index * 100 : layer === "industry" ? (1 - profile.battery_supply_distance_index) * 50 + profile.nev_industry_base * 50 : automaker.length ? automaker.reduce((a, b) => a + b, 0) / automaker.length * 100 : state?.demand_index ?? 0;
    return [profile.province_code, value];
  })), [flow.profiles, layer, world]);
  if (!world) return <div className="v3-empty-page"><Icon name="tune" /><h2>尚未创建实验</h2><button onClick={() => navigate("/experiments/new")} type="button">前往政策设定</button></div>;
  const metrics = world.national_metrics;
  const yearOneCanContinue = ["SETUP", "Y1_Q1", "Y1_Q2", "Y1_Q3", "Y1_Q4"].includes(world.phase);
  return <div className="v3-page">
    <div className="v3-page-heading"><div><span className="v3-kicker">{world.phase} · 原始方案</span><h1>全国新能源汽车政策态势</h1><p>地图默认展示地方新能源汽车支持强度，所有结果单位均为指数 / 100。</p></div>{yearOneCanContinue && <button className="v3-primary" onClick={() => void flow.runYearOne()} type="button"><Icon name="play_arrow" />{world.phase === "SETUP" ? "运行首年四季度" : "继续至首年复盘"}</button>}{world.phase === "YEAR1_REVIEW" && <button className="v3-primary" onClick={() => navigate(`/experiments/${world.experiment_id}/intervention`)} type="button">进入干预审批</button>}</div>
    <div className="v3-kpis">{[["区域发展差距", metrics.regional_development_gap], ["中央财政负担", metrics.central_fiscal_burden], ["地方财政压力", metrics.local_fiscal_pressure], ["新能源汽车需求", metrics.nev_demand], ["新增投资集中度", metrics.new_investment_concentration], ["产业集聚度", metrics.industrial_agglomeration]].map(([label, value]) => <div key={String(label)}><small>{label}</small><strong>{Number(value).toFixed(1)}</strong><span>指数 / 100</span></div>)}</div>
    <div className="v3-live-grid"><section className="v3-card v3-map-card"><div className="v3-layer-tabs">{Object.entries(layers).map(([key, label]) => <button className={layer === key ? "active" : ""} key={key} onClick={() => setLayer(key as keyof typeof layers)} type="button">{label}</button>)}</div><ProvinceMap emptyMessage="运行 Y1_Q1 后显示地方政策" metricLabel={layers[layer]} onSelect={(code) => navigate(`/experiments/${world.experiment_id}/provinces/${code}`)} profiles={flow.profiles} values={values} /></section>
      <aside className="v3-card"><div className="v3-card-title"><Icon name="directions_car" /><div><small>全国性主体</small><h2>10 家车企 Agent</h2></div></div><p className="v3-disclaimer">冻结资料只作为基线；模拟动作不代表真实车企承诺。</p><div className="v3-company-list">{flow.automakers.map((item) => <button key={item.automaker_id} onClick={() => navigate(`${location.pathname}?company=${item.automaker_id}`)} type="button"><span>{item.display_name}<small>{item.data_quality} · {item.baseline_year}</small></span><Icon name="chevron_right" /></button>)}</div></aside>
    </div>
  </div>;
}
