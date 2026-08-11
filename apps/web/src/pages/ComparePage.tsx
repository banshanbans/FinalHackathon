import { lazy, Suspense, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { Icon } from "../components/Icon";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";

const ProvinceMap = lazy(() => import("../components/ProvinceMap").then((module) => ({ default: module.ProvinceMap })));
const METRIC_LABELS: Record<string, string> = {
  enterprise_participation_index: "企业参与",
  equipment_renewal_willingness_index: "设备更新意愿",
  sme_financing_accessibility_index: "SME 融资可达性",
  industrial_upgrade_index: "产业升级",
  local_fiscal_pressure_index: "地方财政压力",
  regional_gap_index: "区域差距",
};
const ARCHETYPE_LABELS: Record<string, string> = { large_state_owned: "大型国有制造", large_private: "大型民营制造", technology_sme: "科技型 SME", traditional_sme: "传统制造 SME", high_energy_industrial: "高耗能工业", export_manufacturer: "出口制造" };
const PARTICIPATION_LABELS: Record<string, string> = { participate: "参与", conditional: "条件参与", wait: "观望", decline: "拒绝" };
const MECHANISM_LABELS: Record<string, string> = { policy_match: "政策匹配", direct_subsidy: "直接补贴", interest_subsidy: "贷款贴息", financing_guarantee: "融资担保", sme_preference: "SME 倾斜", regional_support: "区域支持", financing_constraint: "融资约束", fiscal_cost: "财政成本" };
const signed = (value: number) => `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;

export default function ComparePage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const world = flow.world;
  const comparison = flow.comparison;
  const loadComparison = flow.loadComparison;
  const isSingle = world?.phase === "T5" && world.central_review?.review_mode === "single_branch";
  useEffect(() => {
    const comparisonReady =
      world?.intervention_decision?.startsWith("approved") ||
      world?.central_review?.review_mode === "comparison";
    if (world?.phase === "T5" && comparisonReady && !comparison && !flow.busyLabel) {
      void loadComparison().catch(() => undefined);
    }
  }, [world?.experiment_id, world?.phase, world?.intervention_decision, world?.central_review?.review_mode, comparison, flow.busyLabel, loadComparison]);
  const selectedCode = searchParams.get("province") ?? "41";
  const select = (code: string) => { const next = new URLSearchParams(searchParams); next.set("province", code); setSearchParams(next); };
  const controlValues = useMemo(() => Object.fromEntries(Object.entries(flow.control?.province_states ?? world?.province_states ?? {}).map(([code, state]) => [code, state.enterprise_participation_index])), [flow.control?.province_states, world?.province_states]);
  const treatmentValues = useMemo(() => Object.fromEntries(Object.entries(flow.treatment?.province_states ?? {}).map(([code, state]) => [code, state.enterprise_participation_index])), [flow.treatment?.province_states]);
  if (!world || world.phase !== "T5") return <div className="card empty-state page-empty"><Icon name="difference" /><h2>尚无 T5 结果</h2><p>先完成 T3 人类决定，并运行可用分支至 T5。</p><button className="primary-button" onClick={() => navigate(world ? `/experiments/${world.experiment_id}/intervention` : "/experiments/new")} type="button">返回审批流程</button></div>;
  if (isSingle) return <div className="single-review page-stack"><header className="page-heading"><div><span className="eyebrow">T5 · 单线复盘</span><h1>原始方案完成结算</h1><p>用户在 T3 拒绝干预，因此没有创建干预方案，也没有伪造 A/B 差异。</p></div><span className="state-pill completed">单分支完成</span></header><section className="metric-grid six">{Object.entries(world.national_metrics).filter(([, value]) => typeof value === "number").map(([key, value]) => <article className="metric-card" key={key}><span>{METRIC_LABELS[key]}</span><strong>{Number(value).toFixed(1)}<small>/100</small></strong><p>原始方案 T5</p></article>)}</section>{world.central_review && <section className="card central-review"><div className="review-lead"><Icon name="psychology" /><div><span className="source-label model">国务院 Agent · 单线复盘</span><h2>{world.central_review.public_summary}</h2></div></div><div className="finding-grid">{world.central_review.findings.map((finding) => <article key={finding.title}><strong>{finding.title}</strong><p>{finding.summary}</p>{finding.tradeoff && <small>{finding.tradeoff}</small>}</article>)}</div><div className="limitations"><Icon name="info" />{world.central_review.limitations.join(" · ")}</div></section>}<DeepLinkDrawers /></div>;
  if (!comparison || !flow.control || !flow.treatment) return <div className="card empty-state page-empty"><span className="spinner" /><h2>正在准备同源对照</h2><p>读取两条分支的 T5 权威状态与结构化比较结果。</p></div>;

  return <div className="compare-page page-stack">
    <header className="page-heading compact-heading"><div><span className="eyebrow">T5 · 同源 A/B</span><h1>原始方案与干预方案机制对照</h1><p>共同父检查点 {comparison.checkpoint_id.slice(-12)}；数字为指数点变化，不是现实结果预测。</p></div><span className="state-pill completed">双分支完成</span></header>
    <section className="metric-grid six delta-grid">{Object.entries(comparison.national_metrics).map(([key, metric]) => { const lowerBetter = key.includes("pressure") || key.includes("gap"); const favorable = lowerBetter ? metric.delta <= 0 : metric.delta >= 0; return <article className="metric-card" key={key}><span>{METRIC_LABELS[key]}</span><strong className={favorable ? "positive" : "negative"}>{signed(metric.delta)}<small>指数点</small></strong><p>{metric.control.toFixed(1)} → {metric.treatment.toFixed(1)}</p></article>; })}</section>
    <section className="dual-map-grid">
      <article className="card comparison-map-card"><div className="card-heading"><div><span className="branch-label control">CONTROL</span><h2>原始方案</h2></div><span>企业参与指数</span></div><Suspense fallback={<div className="map-loading"><span className="spinner" /></div>}><ProvinceMap compact metricLabel="企业参与指数" onSelect={select} profiles={flow.profiles} selectedCode={selectedCode} values={controlValues} /></Suspense></article>
      <article className="card comparison-map-card"><div className="card-heading"><div><span className="branch-label treatment">TREATMENT</span><h2>干预方案</h2></div><span>企业参与指数</span></div><Suspense fallback={<div className="map-loading"><span className="spinner" /></div>}><ProvinceMap compact metricLabel="企业参与指数" onSelect={select} profiles={flow.profiles} selectedCode={selectedCode} values={treatmentValues} /></Suspense></article>
    </section>
    <div className="analysis-grid">
      <section className="card migration-card"><div className="card-heading"><div><span className="source-label environment">环境对照</span><h2>企业行动迁移</h2></div><span>{comparison.action_migrations.reduce((sum, item) => sum + item.count, 0)} 个企业群体</span></div><div className="migration-matrix">{comparison.action_migrations.map((item) => <div key={`${item.from_participation}-${item.to_participation}`}><span>{PARTICIPATION_LABELS[item.from_participation]}</span><Icon name="arrow_forward" /><strong>{PARTICIPATION_LABELS[item.to_participation]}</strong><b>{item.count}</b></div>)}</div></section>
      <section className="card group-change-card"><div className="card-heading"><div><span className="source-label environment">重点群体</span><h2>六类企业变化</h2></div></div>{comparison.enterprise_group_changes.map((item) => <div className="group-change-row" key={item.archetype}><strong>{ARCHETYPE_LABELS[item.archetype]}</strong><span>参与 {signed(item.participation_delta)}</span><span>更新 {signed(item.renewal_willingness_delta)}</span><span>融资 {signed(item.financing_accessibility_delta)}</span></div>)}</section>
      <section className="card mechanism-card"><div className="card-heading"><div><span className="source-label environment">机制归因</span><h2>贡献变化</h2></div></div>{Object.entries(comparison.mechanism_totals).map(([key, value]) => <div className="mechanism-row" key={key}><span>{MECHANISM_LABELS[key] ?? key}</span><i><b className={value < 0 ? "negative" : ""} style={{ width: `${Math.min(Math.abs(value) * 8, 100)}%` }} /></i><strong className={value < 0 ? "negative" : "positive"}>{signed(value)}</strong></div>)}</section>
      <section className="card ranking-card"><div className="card-heading"><div><span className="source-label environment">地区变化</span><h2>省域排行</h2></div></div><div className="ranking-columns"><div><strong>参与改善</strong>{[...comparison.province_deltas].sort((a, b) => b.enterprise_participation_delta - a.enterprise_participation_delta).slice(0, 5).map((item, index) => <span key={item.province_code}><i>{index + 1}</i>{item.province_name}<b>{signed(item.enterprise_participation_delta)}</b></span>)}</div><div><strong>财政承压</strong>{[...comparison.province_deltas].sort((a, b) => b.fiscal_pressure_delta - a.fiscal_pressure_delta).slice(0, 5).map((item, index) => <span key={item.province_code}><i>{index + 1}</i>{item.province_name}<b>{signed(item.fiscal_pressure_delta)}</b></span>)}</div></div></section>
    </div>
    {comparison.central_review && <section className="card central-review"><div className="review-lead"><Icon name="psychology" /><div><span className="source-label model">国务院 Agent · 比较复盘</span><h2>{comparison.central_review.public_summary}</h2></div></div><div className="finding-grid">{comparison.central_review.findings.map((finding) => <article key={finding.title}><strong>{finding.title}</strong><p>{finding.summary}</p>{finding.tradeoff && <small>{finding.tradeoff}</small>}</article>)}</div><div className="limitations"><Icon name="info" />{comparison.central_review.limitations.join(" · ")}</div></section>}
    <DeepLinkDrawers />
  </div>;
}
