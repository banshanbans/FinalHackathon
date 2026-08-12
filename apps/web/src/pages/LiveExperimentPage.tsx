import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { EventScenarioPanel } from "../components/EventScenarioPanel";
import { ProvinceMap } from "../components/ProvinceMap";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";

const layers = { support: "地方支持强度", consumer: "消费端补贴", fixed: "固定成本补贴", variable: "可变成本补贴", wtp: "消费者 WTP", industry: "产业基础 / 电池节点", automaker: "车企销售投入", event_exposure: "事件暴露度", province_interaction: "省际交互响应" } as const;

export default function LiveExperimentPage() {
  const flow = usePolicyScopeContext(); const navigate = useNavigate(); const [layer, setLayer] = useState<keyof typeof layers>("support");
  const world = flow.world;
  const values = useMemo(() => Object.fromEntries(flow.profiles.map((profile) => {
    const action = world?.province_actions[profile.province_code]; const state = world?.province_states[profile.province_code];
    const automaker = world ? Object.values(world.automaker_actions).map((item) => item.province_market_actions.find((x) => x.province_code === profile.province_code)?.sales_investment_intensity ?? 0) : [];
    const value = layer === "support" ? (action?.overall_support_intensity ?? 0) * 100 : layer === "consumer" ? (action?.subsidy_mix.consumer ?? 0) * 100 : layer === "fixed" ? (action?.subsidy_mix.fixed_cost ?? 0) * 100 : layer === "variable" ? (action?.subsidy_mix.variable_cost ?? 0) * 100 : layer === "wtp" ? profile.willingness_to_pay_index * 100 : layer === "industry" ? (1 - profile.battery_supply_distance_index) * 50 + profile.nev_industry_base * 50 : layer === "event_exposure" ? (world?.event_exposure_by_province[profile.province_code] ?? state?.event_exposure_index ?? 0) * 100 : layer === "province_interaction" ? (world?.province_event_responses[profile.province_code]?.response_intensity ?? 0) * 100 : automaker.length ? automaker.reduce((a, b) => a + b, 0) / automaker.length * 100 : state?.demand_index ?? 0;
    return [profile.province_code, value];
  })), [flow.profiles, layer, world]);
  if (!world) return <div className="v3-empty-page"><Icon name="tune" /><h2>尚未创建实验</h2><button onClick={() => navigate("/experiments/new")} type="button">前往政策设定</button></div>;
  const metrics = world.national_metrics;
  const yearOneCanContinue = ["SETUP", "Y1_Q1", "Y1_Q2", "Y1_Q3", "Y1_Q4"].includes(world.phase);
  const atEventGate = Boolean(flow.branch) && world.phase === "Y2_Q2";
  const runEventAndCompare = async () => { await flow.runComparison(); navigate(`/experiments/${world.experiment_id}/compare`); };
  return <div className="v3-page">
    <div className="v3-page-heading"><div><span className="v3-kicker">{world.phase} · 原始方案</span><h1>全国新能源汽车政策态势</h1></div>{yearOneCanContinue && <button className="v3-primary" onClick={() => void flow.runYearOne()} type="button"><Icon name="play_arrow" />{world.phase === "SETUP" ? "运行首年四季度" : "继续至首年复盘"}</button>}{world.phase === "YEAR1_REVIEW" && <button className="v3-primary" onClick={() => navigate(`/experiments/${world.experiment_id}/intervention`)} type="button">进入干预审批</button>}</div>
    <div className="v3-kpis">{[["区域发展差距", metrics.regional_development_gap], ["中央财政负担", metrics.central_fiscal_burden], ["地方财政压力", metrics.local_fiscal_pressure], ["新能源汽车需求", metrics.nev_demand], ["新增投资集中度", metrics.new_investment_concentration], ["产业集聚度", metrics.industrial_agglomeration]].map(([label, value]) => <div key={String(label)}><small>{label}</small><strong>{Number(value).toFixed(1)}</strong><span>指数 / 100</span></div>)}</div>
    {flow.branch && world.phase === "YEAR1_REVIEW" && <section className="v3-card v31-gate-callout"><div><small>次年双分支</small><h2>先运行至事件注入点</h2><p>两个分支将分别完成 Y2_Q1 省级决策和 Y2_Q2 车企行动，再停在人工事件门禁。</p></div><button className="v3-primary" disabled={Boolean(flow.busyLabel)} onClick={() => void flow.runToEventGate()} type="button">运行至 Y2_Q2</button></section>}
    {atEventGate && <EventScenarioPanel approvedId={flow.eventScenario?.scenario_id} disabled={Boolean(flow.busyLabel)} onApprove={flow.approveEvent} templates={flow.eventTemplates} />}
    {atEventGate && flow.eventScenario && <section className="v3-card v31-gate-callout"><div><small>事件已锁定</small><h2>{flow.eventScenario.title} · {flow.eventScenario.intensity}</h2><p>{world.comparison_mode === "policy_intervention" ? "同一事件将应用到原始方案与干预方案。" : "原始分支保持无事件，事件仅应用到干预分支。"}</p></div><button className="v3-primary" disabled={Boolean(flow.busyLabel)} onClick={() => void runEventAndCompare()} type="button">执行交互并生成比较</button></section>}
    <div className="v3-live-grid"><section className="v3-card v3-map-card"><div className="v3-layer-tabs">{Object.entries(layers).map(([key, label]) => <button className={layer === key ? "active" : ""} key={key} onClick={() => setLayer(key as keyof typeof layers)} type="button">{label}</button>)}</div><ProvinceMap emptyMessage="运行 Y1_Q1 后显示地方政策" metricLabel={layers[layer]} onSelect={(code) => navigate(`/experiments/${world.experiment_id}/provinces/${code}`)} profiles={flow.profiles} values={values} /></section>
      <aside className="v3-card"><div className="v3-card-title"><Icon name="directions_car" /><div><small>真实数据基线 · 模拟车企行动</small><h2>10 家车企 Agent</h2></div></div><div className="v3-company-list">{flow.automakers.map((item) => <button key={item.automaker_id} onClick={() => navigate(`${location.pathname}?company=${item.automaker_id}`)} type="button"><span>{item.display_name}<small>{item.data_quality} · {item.baseline_year}</small></span><Icon name="chevron_right" /></button>)}</div></aside>
    </div>
    {world.coordination_matches.length > 0 && <section className="v3-card"><div className="v3-card-title"><Icon name="hub" /><div><small>事件 → 信号 → Peer 响应 → 协作</small><h2>省际交互关系</h2></div></div><div className="v31-coordination-list">{world.coordination_matches.slice(0, 12).map((item) => <button key={item.match_id} onClick={() => navigate(`/experiments/${world.experiment_id}/provinces/${item.left_province_code}?evidence=interaction:${item.match_id}`)} type="button"><span>{flow.profiles.find((p) => p.province_code === item.left_province_code)?.short_name} ↔ {flow.profiles.find((p) => p.province_code === item.right_province_code)?.short_name}</span><b className={item.status}>{item.status === "matched" ? "已匹配" : "单向未匹配"}</b><small>贡献 {item.contribution.toFixed(2)}</small></button>)}</div></section>}
  </div>;
}
