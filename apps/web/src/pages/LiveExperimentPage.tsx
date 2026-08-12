import { lazy, Suspense, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { EventRail } from "../components/EventRail";
import { Icon } from "../components/Icon";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { NationalMetricKey } from "../types";
import { WORLD_STATUS_LABELS } from "../utils/display";

const ProvinceMap = lazy(() => import("../components/ProvinceMap").then((module) => ({ default: module.ProvinceMap })));

const METRICS: Array<{ key: NationalMetricKey; label: string; icon: string; inverse?: boolean }> = [
  { key: "enterprise_participation_index", label: "企业参与指数", icon: "groups" },
  { key: "equipment_renewal_willingness_index", label: "设备更新意愿", icon: "precision_manufacturing" },
  { key: "sme_financing_accessibility_index", label: "中小企业融资可达性", icon: "account_balance" },
  { key: "industrial_upgrade_index", label: "产业升级指数", icon: "trending_up" },
  { key: "local_fiscal_pressure_index", label: "地方财政压力", icon: "speed", inverse: true },
  { key: "regional_gap_index", label: "区域差距指数", icon: "conversion_path", inverse: true },
];

type MapMetric =
  | "implementation_intensity"
  | "local_match_ratio"
  | "requested_central_support"
  | "sme_inclusiveness"
  | "green_priority"
  | "enterprise_participation_index"
  | "equipment_renewal_willingness_index"
  | "sme_financing_accessibility_index"
  | "fiscal_pressure_index";

const MAP_METRIC_LABELS: Record<MapMetric, string> = {
  implementation_intensity: "地方执行强度",
  local_match_ratio: "地方配套强度",
  requested_central_support: "中央支持请求",
  sme_inclusiveness: "普惠倾向百分位",
  green_priority: "绿色倾向百分位",
  enterprise_participation_index: "企业参与指数",
  equipment_renewal_willingness_index: "设备更新意愿指数",
  sme_financing_accessibility_index: "中小企业融资可达性",
  fiscal_pressure_index: "地方财政压力指数",
};

export default function LiveExperimentPage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [mapMetric, setMapMetric] = useState<MapMetric>("implementation_intensity");
  const world = flow.world;
  const values = useMemo(() => {
    if (!world) return {};
    if (["implementation_intensity", "local_match_ratio", "requested_central_support"].includes(mapMetric)) {
      if (Object.keys(world.province_actions).length === 0) return {};
      return Object.fromEntries(Object.entries(world.province_actions).map(([code, action]) => [code, Number(action[mapMetric as "implementation_intensity" | "local_match_ratio" | "requested_central_support"]) * 100]));
    }
    if (mapMetric === "sme_inclusiveness" || mapMetric === "green_priority") {
      return Object.fromEntries(Object.entries(world.province_personas).map(([code, persona]) => [code, persona.axes[mapMetric] * 100]));
    }
    return Object.fromEntries(Object.entries(world.province_states).map(([code, state]) => [code, state[mapMetric as keyof typeof state] as number]));
  }, [mapMetric, world]);
  const activePhase = Number(world?.phase.slice(1) ?? 0);
  const openProvince = (provinceCode: string) => {
    if (!world) return;
    navigate(`/experiments/${world.experiment_id}/provinces/${provinceCode}?branch=control`);
  };
  if (!world) return <div className="card empty-state page-empty"><Icon name="lock" /><h2>暂无运行任务</h2><p>请先完成中央政策配置与审批。</p><button className="primary-button" onClick={() => navigate("/experiments/new")} type="button">返回政策配置</button></div>;

  const goIntervention = () => navigate(`/experiments/${world.experiment_id}/intervention`);
  return (
    <div className="live-page page-stack">
      <header className="page-heading compact-heading">
        <div><span className="eyebrow">全国制造业设备更新 · 执行监测</span><h1>31 省政策决策与企业反馈</h1><p>跟踪各省目标、执行工具、省际策略与企业行为信号。</p></div>
        <div className="live-actions"><span className={`state-pill ${world.status}`}>{WORLD_STATUS_LABELS[world.status] ?? "状态已更新"}</span>{world.phase === "T3" ? <button className="primary-button" onClick={goIntervention} type="button">审批中央干预<Icon name="arrow_forward" /></button> : <button className="primary-button" disabled={world.directive.approval_status !== "approved"} onClick={() => void flow.runToT3()} type="button"><Icon name="play_arrow" />启动推演至 T3</button>}</div>
      </header>
      <section className="metric-grid six">
        {METRICS.map((metric) => <article className="metric-card" key={metric.key}><div><Icon name={metric.icon} /><span>{metric.label}</span></div><strong>{world.national_metrics[metric.key].toFixed(1)}<small>/100</small></strong><p>{metric.inverse ? "约束指标，低值更优" : "全国加权值"}</p></article>)}
      </section>
      <div className="live-workspace">
        <section className="card national-map-card">
          <div className="card-heading"><div><span className="source-label model">省级 Agent 决策</span><h2>{MAP_METRIC_LABELS[mapMetric]}全国分布</h2></div><div className="map-tools"><label><span>地图指标</span><select aria-label="地图指标" onChange={(event) => setMapMetric(event.target.value as MapMetric)} value={mapMetric}><optgroup label="省级策略"><option value="implementation_intensity">地方执行强度</option><option value="local_match_ratio">地方配套强度</option><option value="requested_central_support">中央支持请求</option><option value="sme_inclusiveness">普惠倾向百分位</option><option value="green_priority">绿色倾向百分位</option></optgroup><optgroup label="企业与环境结果"><option value="enterprise_participation_index">企业参与指数</option><option value="equipment_renewal_willingness_index">设备更新意愿</option><option value="sme_financing_accessibility_index">中小企业融资可达性</option><option value="fiscal_pressure_index">地方财政压力</option></optgroup></select></label><span>{world.phase}</span></div></div>
          <div className="featured-provinces"><span>重点省份</span>{[["41", "河南·普惠融资"], ["44", "广东·技术与市场"], ["14", "山西·绿色转型"]].map(([code, label]) => <button key={code} onClick={() => openProvince(code)} type="button"><Icon name="location_on" />{label}</button>)}</div>
          <Suspense fallback={<div className="map-loading"><span className="spinner" />地图加载中…</div>}><ProvinceMap emptyMessage="等待省级决策" metricLabel={MAP_METRIC_LABELS[mapMetric]} onSelect={openProvince} profiles={flow.profiles} values={values} /></Suspense>
        </section>
        <EventRail events={flow.events} />
      </div>
      <section className="card timeline-card">
        <div className="card-heading"><div><span className="eyebrow">T0–T5</span><h2>政策推演进度</h2></div><span className="checkpoint-caption">随机种子 {world.seed} · {world.versions.mechanism}</span></div>
        <div className="phase-timeline">
          {["中央设定", "地方工具", "企业响应", "反馈与审批", "同源分支", "结算复盘"].map((label, index) => <div className={`${index < activePhase ? "done" : ""} ${index === activePhase ? "active" : ""}`} key={label}><span>{index < activePhase ? <Icon name="check" /> : `T${index}`}</span><strong>{label}</strong><small>{index === 3 ? "冻结检查点" : index === 4 ? "原始 / 干预" : ""}</small></div>)}
        </div>
      </section>
      {world.fallback_provinces.length > 0 && <div className="fallback-strip"><Icon name="warning" /><strong>{world.fallback_provinces.length} 个省份启用规则接管</strong><span>已纳入审计记录，运行结果可复现。</span></div>}
      <DeepLinkDrawers />
    </div>
  );
}
