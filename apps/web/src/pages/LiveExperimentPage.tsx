import { lazy, Suspense, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { EventRail } from "../components/EventRail";
import { Icon } from "../components/Icon";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { NationalMetricKey } from "../types";

const ProvinceMap = lazy(() => import("../components/ProvinceMap").then((module) => ({ default: module.ProvinceMap })));

const METRICS: Array<{ key: NationalMetricKey; label: string; icon: string; inverse?: boolean }> = [
  { key: "enterprise_participation_index", label: "企业参与指数", icon: "groups" },
  { key: "equipment_renewal_willingness_index", label: "设备更新意愿", icon: "precision_manufacturing" },
  { key: "sme_financing_accessibility_index", label: "SME 融资可达性", icon: "account_balance" },
  { key: "industrial_upgrade_index", label: "产业升级指数", icon: "trending_up" },
  { key: "local_fiscal_pressure_index", label: "地方财政压力", icon: "speed", inverse: true },
  { key: "regional_gap_index", label: "区域差距指数", icon: "conversion_path", inverse: true },
];

export default function LiveExperimentPage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const world = flow.world;
  const values = useMemo(() => Object.fromEntries(Object.entries(world?.province_states ?? {}).map(([code, state]) => [code, state.enterprise_participation_index])), [world?.province_states]);
  const activePhase = Number(world?.phase.slice(1) ?? 0);
  const openProvince = (provinceCode: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("province", provinceCode);
    setSearchParams(next);
  };
  if (!world) return <div className="card empty-state page-empty"><Icon name="lock" /><h2>尚未创建实验</h2><p>先在政策设定页生成并批准中央指令。</p><button className="primary-button" onClick={() => navigate("/experiments/new")} type="button">前往政策设定</button></div>;

  const goIntervention = () => navigate(`/experiments/${world.experiment_id}/intervention`);
  return (
    <div className="live-page page-stack">
      <header className="page-heading compact-heading">
        <div><span className="eyebrow">全国制造业设备更新 · 实时推演</span><h1>31 省 × 6 类企业响应态势</h1><p>当前显示环境计算后的内部指数；点击省份查看六类企业的独立行动。</p></div>
        <div className="live-actions"><span className={`state-pill ${world.status}`}>{world.status === "awaiting_intervention" ? "等待中央审批" : world.status}</span>{world.phase === "T3" ? <button className="primary-button" onClick={goIntervention} type="button">进入干预审批<Icon name="arrow_forward" /></button> : <button className="primary-button" disabled={world.directive.approval_status !== "approved"} onClick={() => void flow.runToT3()} type="button"><Icon name="play_arrow" />运行至 T3</button>}</div>
      </header>
      <section className="metric-grid six">
        {METRICS.map((metric) => <article className="metric-card" key={metric.key}><div><Icon name={metric.icon} /><span>{metric.label}</span></div><strong>{world.national_metrics[metric.key].toFixed(1)}<small>/100</small></strong><p>{metric.inverse ? "数值越低表示约束越小" : "当前情景实验指数"}</p></article>)}
      </section>
      <div className="live-workspace">
        <section className="card national-map-card">
          <div className="card-heading"><div><span className="source-label environment">环境计算</span><h2>全国企业参与指数</h2></div><div className="map-tools"><button onClick={() => openProvince("41")} type="button"><Icon name="location_on" />查看河南</button><span>{world.phase}</span></div></div>
          <Suspense fallback={<div className="map-loading"><span className="spinner" />正在加载离线矢量地图…</div>}><ProvinceMap metricLabel="企业参与指数" onSelect={openProvince} profiles={flow.profiles} selectedCode={searchParams.get("province") ?? "41"} values={values} /></Suspense>
        </section>
        <EventRail events={flow.events} />
      </div>
      <section className="card timeline-card">
        <div className="card-heading"><div><span className="eyebrow">T0–T5</span><h2>实验时间轴</h2></div><span className="checkpoint-caption">seed {world.seed} · {world.versions.mechanism}</span></div>
        <div className="phase-timeline">
          {["中央设定", "地方工具", "企业响应", "反馈与审批", "同源分支", "结算复盘"].map((label, index) => <div className={`${index < activePhase ? "done" : ""} ${index === activePhase ? "active" : ""}`} key={label}><span>{index < activePhase ? <Icon name="check" /> : `T${index}`}</span><strong>{label}</strong><small>{index === 3 ? "冻结检查点" : index === 4 ? "原始 / 干预" : ""}</small></div>)}
        </div>
      </section>
      {world.fallback_provinces.length > 0 && <div className="fallback-strip"><Icon name="warning" /><strong>{world.fallback_provinces.length} 个省份使用企业批量 fallback</strong><span>已写入事件流与 Replay，不影响确定性重放。</span></div>}
      <DeepLinkDrawers />
    </div>
  );
}
