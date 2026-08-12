import { lazy, Suspense, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { Icon } from "../components/Icon";
import { NationalMetricStrip, PolicySnapshot, StageTimeline } from "../components/WorkspacePanels";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { ProvinceProfile } from "../types";
import {
  selectKeyEvents,
  selectMetricTrend,
  selectParticipationDistribution,
  selectProvinceGoalDistribution,
  selectProvinceStrategyDistribution,
} from "../utils/dashboardSelectors";
import { EVENT_LABELS } from "../events";
import { PERSONA_TYPE_LABELS, POSTURE_LABELS, PRIORITY_GOAL_LABELS, STRATEGY_LABELS } from "../utils/display";

const ProvinceMap = lazy(() => import("../components/ProvinceMap").then((module) => ({ default: module.ProvinceMap })));
const MetricTrendChart = lazy(() => import("../components/DashboardCharts").then((module) => ({ default: module.MetricTrendChart })));
const EnterpriseParticipationChart = lazy(() => import("../components/DashboardCharts").then((module) => ({ default: module.EnterpriseParticipationChart })));
const ProvinceGoalChart = lazy(() => import("../components/DashboardCharts").then((module) => ({ default: module.ProvinceGoalChart })));

type MapMetric = "implementation_intensity" | "local_match_ratio" | "requested_central_support" | "sme_inclusiveness" | "green_priority" | "enterprise_participation_index" | "equipment_renewal_willingness_index" | "sme_financing_accessibility_index" | "fiscal_pressure_index";
const MAP_METRIC_LABELS: Record<MapMetric, string> = {
  implementation_intensity: "地方执行强度", local_match_ratio: "地方配套强度", requested_central_support: "中央支持请求", sme_inclusiveness: "普惠倾向百分位", green_priority: "绿色倾向百分位", enterprise_participation_index: "企业参与指数", equipment_renewal_willingness_index: "设备更新意愿指数", sme_financing_accessibility_index: "中小企业融资可达性", fiscal_pressure_index: "地方财政压力指数",
};

function profileByCode(profiles: ProvinceProfile[], code: string) { return profiles.find((profile) => profile.province_code === code); }

export default function LiveExperimentPage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const world = flow.world;
  const [mapMetric, setMapMetric] = useState<MapMetric>("implementation_intensity");
  const [selectedProvince, setSelectedProvince] = useState("41");

  const values = useMemo(() => {
    if (!world) return {};
    if (["implementation_intensity", "local_match_ratio", "requested_central_support"].includes(mapMetric)) return Object.fromEntries(Object.entries(world.province_actions).map(([code, action]) => [code, Number(action[mapMetric as "implementation_intensity" | "local_match_ratio" | "requested_central_support"]) * 100]));
    if (mapMetric === "sme_inclusiveness" || mapMetric === "green_priority") return Object.fromEntries(Object.entries(world.province_personas).map(([code, persona]) => [code, persona.axes[mapMetric] * 100]));
    return Object.fromEntries(Object.entries(world.province_states).map(([code, state]) => [code, state[mapMetric as keyof typeof state] as number]));
  }, [mapMetric, world]);

  const trend = useMemo(() => selectMetricTrend(flow.events), [flow.events]);
  const participation = useMemo(() => world ? selectParticipationDistribution(world) : { participate: 0, conditional: 0, wait: 0, decline: 0 }, [world]);
  const goals = useMemo(() => world ? selectProvinceGoalDistribution(world) : [], [world]);
  const strategies = useMemo(() => world ? selectProvinceStrategyDistribution(world) : [], [world]);
  const keyEvents = useMemo(() => selectKeyEvents(flow.events), [flow.events]);

  if (flow.hydrating) return <div className="card empty-state page-empty"><span className="spinner" /><h2>正在加载全国推演…</h2></div>;
  if (!world) return <div className="card empty-state page-empty"><Icon name="lock" /><h2>暂无运行任务</h2><p>请先完成中央政策配置与审批。</p><button className="primary-button" onClick={() => navigate("/experiments/new")} type="button">返回政策配置</button></div>;
  if (world.directive.approval_status !== "approved") return <div className="card empty-state page-empty"><Icon name="verified_user" /><h2>中央政策尚未审批</h2><p>批准完整政策参数后，才能启动 31 省政策决策与企业反馈。</p><button className="primary-button" onClick={() => navigate("/experiments/new")} type="button">返回政策审批</button></div>;

  const selectedProfile = profileByCode(flow.profiles, selectedProvince);
  const selectedAction = world.province_actions[selectedProvince];
  const selectedPersona = world.province_personas[selectedProvince];
  const selectedState = world.province_states[selectedProvince];

  return <div className="live-dashboard">
    <NationalMetricStrip world={world} />
    <div className="live-dashboard-grid">
      <section className="card dashboard-map-panel">
        <header><div><h2>31 省政策响应态势</h2><span>省级 Agent 决策</span></div><label><span>地图指标</span><select aria-label="地图指标" onChange={(event) => setMapMetric(event.target.value as MapMetric)} value={mapMetric}><optgroup label="省级策略"><option value="implementation_intensity">地方执行强度</option><option value="local_match_ratio">地方配套强度</option><option value="requested_central_support">中央支持请求</option><option value="sme_inclusiveness">普惠倾向百分位</option><option value="green_priority">绿色倾向百分位</option></optgroup><optgroup label="企业与环境结果"><option value="enterprise_participation_index">企业参与指数</option><option value="equipment_renewal_willingness_index">设备更新意愿</option><option value="sme_financing_accessibility_index">中小企业融资可达性</option><option value="fiscal_pressure_index">地方财政压力</option></optgroup></select></label></header>
        <div className="dashboard-map-body">
          <Suspense fallback={<div className="map-loading"><span className="spinner" />地图加载中…</div>}><ProvinceMap emptyMessage="等待省级决策" height={286} metricLabel={MAP_METRIC_LABELS[mapMetric]} onSelect={setSelectedProvince} profiles={flow.profiles} selectedCode={selectedProvince} values={values} /></Suspense>
          <aside className="province-focus-card"><header><div><strong>{selectedProfile?.name ?? "省份详情"}</strong><span>{selectedPersona ? PERSONA_TYPE_LABELS[selectedPersona.primary_type] : "等待画像"}</span></div><Icon name="verified" /></header>{selectedAction ? <dl><div><dt>主要目标</dt><dd>{PRIORITY_GOAL_LABELS[selectedAction.primary_goal]}</dd></div><div><dt>决策姿态</dt><dd>{POSTURE_LABELS[selectedAction.decision_posture]}</dd></div><div><dt>执行强度</dt><dd>{(selectedAction.implementation_intensity * 100).toFixed(0)} / 100</dd></div><div><dt>省际策略</dt><dd>{STRATEGY_LABELS[selectedAction.interprovincial_strategy]}</dd></div><div><dt>企业参与</dt><dd>{selectedState?.enterprise_participation_index.toFixed(1) ?? "—"}</dd></div></dl> : <div className="focus-empty">等待 T1 省级决策</div>}<button onClick={() => navigate(`/experiments/${world.experiment_id}/provinces/${selectedProvince}?branch=control`)} type="button">查看省级 Agent 详情<Icon name="arrow_forward" /></button></aside>
        </div>
      </section>
      <PolicySnapshot onOpen={() => navigate("/experiments/new")} policy={world.policy} />

      <section className="card dashboard-chart-panel"><header><h2>核心指标趋势</h2><span>{trend.length} 个真实阶段节点</span></header><Suspense fallback={<div className="chart-loading"><span className="spinner" /></div>}><MetricTrendChart points={trend} /></Suspense></section>
      <section className="card dashboard-chart-panel"><header><h2>企业参与结构</h2><span>企业群体 Agent</span></header><Suspense fallback={<div className="chart-loading"><span className="spinner" /></div>}><EnterpriseParticipationChart counts={participation} /></Suspense></section>
      <section className="card dashboard-chart-panel"><header><h2>省级主要目标分布</h2><span>{strategies.length > 0 ? `${strategies.map(([key, value]) => `${STRATEGY_LABELS[key as keyof typeof STRATEGY_LABELS]} ${value}`).join(" · ")}` : "等待省级决策"}</span></header><Suspense fallback={<div className="chart-loading"><span className="spinner" /></div>}><ProvinceGoalChart goals={goals} /></Suspense></section>
      <section className="card dashboard-key-events"><header><h2>关键事件</h2><span>{keyEvents.length}</span></header><div>{keyEvents.length > 0 ? keyEvents.map((event) => { const auditId = typeof event.payload.audit_record_id === "string" ? event.payload.audit_record_id : null; return <article className={auditId ? "has-audit" : ""} key={event.event_id}><Icon name={event.type.includes("fallback") ? "warning" : event.type.includes("checkpoint") ? "lock" : "account_tree"} /><div><strong>{EVENT_LABELS[event.type] ?? event.type}</strong><p>{typeof event.payload.summary === "string" ? event.payload.summary : `${event.phase} · ${event.branch_id === "control" ? "原始方案" : "干预方案"}`}</p></div>{auditId ? <button aria-label="查看行为追溯" onClick={() => navigate(`?evidence=audit:${auditId}`)} type="button"><Icon name="fact_check" /></button> : <small>{event.phase}</small>}</article>; }) : <div className="key-events-empty"><Icon name="hourglass_empty" />运行后显示关键事实</div>}</div></section>
      <StageTimeline world={world} />
    </div>
    {world.fallback_provinces.length > 0 && <div className="fallback-strip"><Icon name="warning" /><strong>{world.fallback_provinces.length} 个省份启用规则接管</strong><span>已纳入审计记录，运行结果可复现。</span></div>}
    <DeepLinkDrawers />
  </div>;
}
