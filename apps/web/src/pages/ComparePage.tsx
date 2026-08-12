import { lazy, Suspense, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { Icon } from "../components/Icon";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import { PERSONA_TYPE_LABELS } from "../utils/display";

const ProvinceMap = lazy(() => import("../components/ProvinceMap").then((module) => ({ default: module.ProvinceMap })));
const METRIC_LABELS: Record<string, string> = {
  enterprise_participation_index: "企业参与",
  equipment_renewal_willingness_index: "设备更新意愿",
  sme_financing_accessibility_index: "中小企业融资可达性",
  industrial_upgrade_index: "产业升级",
  local_fiscal_pressure_index: "地方财政压力",
  regional_gap_index: "区域差距",
};
const ARCHETYPE_LABELS: Record<string, string> = { large_state_owned: "大型国有制造", large_private: "大型民营制造", technology_sme: "科技型中小企业", traditional_sme: "传统制造中小企业", high_energy_industrial: "高耗能工业", export_manufacturer: "出口制造" };
const PARTICIPATION_LABELS: Record<string, string> = { participate: "参与", conditional: "条件参与", wait: "观望", decline: "拒绝" };
const MECHANISM_LABELS: Record<string, string> = { policy_match: "政策匹配", direct_subsidy: "直接补贴", interest_subsidy: "贷款贴息", financing_guarantee: "融资担保", sme_preference: "中小企业倾斜", regional_support: "区域支持", financing_constraint: "融资约束", fiscal_cost: "财政成本" };
const signed = (value: number) => `${value >= 0 ? "+" : ""}${value.toFixed(1)}`;
const STRATEGY_FIELD_LABELS: Record<string, string> = {
  primary_goal: "主要目标",
  decision_posture: "决策姿态",
  target_enterprise_groups: "重点企业",
  interprovincial_strategy: "省际策略",
  target_province_codes: "关联省份",
  implementation_intensity: "地方执行强度",
  local_match_ratio: "地方配套",
  "instrument_mix.direct_subsidy": "直接补贴",
  "instrument_mix.interest_subsidy": "贷款贴息",
  "instrument_mix.financing_guarantee": "融资担保",
  sme_preference: "中小企业倾斜",
  regional_delivery_focus: "区域投放",
  requested_central_support: "中央支持请求",
};

export default function ComparePage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const world = flow.world;
  const comparison = flow.comparison;
  const loadComparison = flow.loadComparison;
  const isSingle = world?.phase === "T5" && world.central_review?.review_mode === "single_branch";
  const openEvidence = (evidenceId: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("evidence", evidenceId);
    setSearchParams(next);
  };
  useEffect(() => {
    const comparisonReady =
      world?.intervention_decision?.startsWith("approved") ||
      world?.central_review?.review_mode === "comparison";
    if (world?.phase === "T5" && comparisonReady && !comparison && !flow.busyLabel) {
      void loadComparison().catch(() => undefined);
    }
  }, [world?.experiment_id, world?.phase, world?.intervention_decision, world?.central_review?.review_mode, comparison, flow.busyLabel, loadComparison]);
  const controlValues = useMemo(() => Object.fromEntries(Object.entries(flow.control?.province_actions ?? world?.province_actions ?? {}).map(([code, action]) => [code, action.implementation_intensity * 100])), [flow.control?.province_actions, world?.province_actions]);
  const treatmentValues = useMemo(() => Object.fromEntries(Object.entries(flow.treatment?.province_actions ?? {}).map(([code, action]) => [code, action.implementation_intensity * 100])), [flow.treatment?.province_actions]);
  if (flow.hydrating) return <div className="card empty-state page-empty"><span className="spinner" /><h2>正在加载方案对照…</h2></div>;
  if (!world || world.phase !== "T5") return <div className="card empty-state page-empty"><Icon name="difference" /><h2>暂无 T5 结算结果</h2><p>请先完成 T3 干预决策并运行至 T5。</p><button className="primary-button" onClick={() => navigate(world ? `/experiments/${world.experiment_id}/intervention` : "/experiments/new")} type="button">返回干预决策</button></div>;
  if (isSingle) return <div className="single-review page-stack"><header className="page-heading"><div><span className="eyebrow">T5 · 单方案复盘</span><h1>原始方案结算结果</h1><p>干预建议已驳回，本次按单方案完成结算。</p></div><span className="state-pill completed">单方案已完成</span></header><section className="metric-grid six">{Object.entries(world.national_metrics).filter(([, value]) => typeof value === "number").map(([key, value]) => <article className="metric-card" key={key}><span>{METRIC_LABELS[key]}</span><strong>{Number(value).toFixed(1)}<small>/100</small></strong><p>原始方案 T5</p></article>)}</section>{world.central_review && <section className="card central-review"><div className="review-lead"><Icon name="psychology" /><div><span className="source-label model">中央研判智能体 · 单方案复盘</span><h2>{world.central_review.public_summary}</h2></div></div><div className="finding-grid">{world.central_review.findings.map((finding) => <article key={finding.title}><strong>{finding.title}</strong><p>{finding.summary}</p>{finding.tradeoff && <small>{finding.tradeoff}</small>}</article>)}</div><div className="limitations"><Icon name="info" />{world.central_review.limitations.join(" · ")}</div></section>}<DeepLinkDrawers /></div>;
  if (!comparison || !flow.control || !flow.treatment) return <div className="card empty-state page-empty"><span className="spinner" /><h2>双方案对照准备中</h2><p>正在加载 T5 结算结果。</p></div>;

  return <div className="compare-page page-stack">
    <header className="page-heading compact-heading"><div><span className="eyebrow">T5 · 双方案对照</span><h1>原始方案与干预方案对照</h1><p>父检查点 {comparison.checkpoint_id.slice(-12)} ｜ 变化单位：指数点</p></div><span className="state-pill completed">双方案已完成</span></header>
    <section className="comparison-proof-bar" aria-label="同源对照证明"><span><Icon name="lock" /><small>共用 T3 父检查点</small><strong>{comparison.checkpoint_id.slice(-12)}</strong></span><span><Icon name="difference" /><small>批准的主动差异</small><strong>{comparison.policy_diff.length} 个政策字段</strong></span><span><Icon name="database" /><small>数据 / 机制版本</small><strong>{world.versions.data} / {world.versions.mechanism}</strong></span><span><Icon name="casino" /><small>共用 Seed 规则</small><strong>{world.seed}</strong></span></section>
    <section className="metric-grid six delta-grid comparison-delta-strip">{Object.entries(comparison.national_metrics).map(([key, metric]) => { const lowerBetter = key.includes("pressure") || key.includes("gap"); const favorable = lowerBetter ? metric.delta <= 0 : metric.delta >= 0; return <article className="metric-card" key={key}><span>{METRIC_LABELS[key]}</span><strong className={favorable ? "positive" : "negative"}>{signed(metric.delta)}<small>指数点</small></strong><p>{metric.control.toFixed(1)} → {metric.treatment.toFixed(1)}</p></article>; })}</section>
    <section className="dual-map-grid">
      <article className="card comparison-map-card"><div className="card-heading"><div><span className="branch-label control">原始方案</span><h2>地方执行强度</h2></div><span>省级 Agent 决策</span></div><Suspense fallback={<div className="map-loading"><span className="spinner" /></div>}><ProvinceMap compact metricLabel="地方执行强度" onSelect={(code) => navigate(`/experiments/${world.experiment_id}/provinces/${code}?branch=control`)} profiles={flow.profiles} values={controlValues} /></Suspense></article>
      <article className="card comparison-map-card"><div className="card-heading"><div><span className="branch-label treatment">干预方案</span><h2>地方执行强度</h2></div><span>省级 Agent 决策</span></div><Suspense fallback={<div className="map-loading"><span className="spinner" /></div>}><ProvinceMap compact metricLabel="地方执行强度" onSelect={(code) => navigate(`/experiments/${world.experiment_id}/provinces/${code}?branch=treatment`)} profiles={flow.profiles} values={treatmentValues} /></Suspense></article>
    </section>
    <section className="card strategy-transition-card"><div className="card-heading"><div><span className="source-label model">省级 Agent 对照</span><h2>省级策略迁移</h2></div><span>{comparison.province_strategy_transitions.filter((item) => item.changed).length} / 31 省发生变化</span></div><div className="strategy-transition-table"><header><span>省份与画像</span><span>变化字段</span><span>原始方案</span><span>干预方案</span><span /></header>{comparison.province_strategy_transitions.map((transition) => <div className={transition.changed ? "changed" : "unchanged"} key={transition.province_code}><span><strong>{transition.province_name}</strong><small>{PERSONA_TYPE_LABELS[transition.persona_primary_type]}</small></span>{transition.changed ? <><span>{transition.changes.slice(0, 2).map((change) => STRATEGY_FIELD_LABELS[change.path] ?? change.path).join("、")}{transition.changes.length > 2 ? ` 等 ${transition.changes.length} 项` : ""}</span><span>{String(transition.changes[0]?.from_value ?? "—")}</span><span>{String(transition.changes[0]?.to_value ?? "—")}</span></> : <><span>策略保持</span><span>—</span><span>—</span></>}<button aria-label={`查看${transition.province_name}详情`} onClick={() => navigate(`/experiments/${world.experiment_id}/provinces/${transition.province_code}?branch=treatment`)} type="button"><Icon name="arrow_forward" /></button></div>)}</div></section>
    <div className="analysis-grid">
      <section className="card migration-card"><div className="card-heading"><div><span className="source-label environment">环境对照</span><h2>企业行动迁移</h2></div><span>{comparison.action_migrations.reduce((sum, item) => sum + item.count, 0)} 个企业群体</span></div><div className="migration-matrix">{comparison.action_migrations.map((item) => <div key={`${item.from_participation}-${item.to_participation}`}><span>{PARTICIPATION_LABELS[item.from_participation]}</span><Icon name="arrow_forward" /><strong>{PARTICIPATION_LABELS[item.to_participation]}</strong><b>{item.count}</b></div>)}</div></section>
      <section className="card group-change-card"><div className="card-heading"><div><span className="source-label environment">重点群体</span><h2>六类企业变化</h2></div></div>{comparison.enterprise_group_changes.map((item) => <div className="group-change-row" key={item.archetype}><strong>{ARCHETYPE_LABELS[item.archetype]}</strong><span>参与 {signed(item.participation_delta)}</span><span>更新 {signed(item.renewal_willingness_delta)}</span><span>融资 {signed(item.financing_accessibility_delta)}</span></div>)}</section>
      <section className="card mechanism-card"><div className="card-heading"><div><span className="source-label environment">机制归因</span><h2>贡献变化</h2></div><button className="text-button" onClick={() => openEvidence("comparison:current")} type="button"><Icon name="difference" />查看同源与守恒证明</button></div>{Object.entries(comparison.mechanism_totals).map(([key, value]) => <div className="mechanism-row" key={key}><span>{MECHANISM_LABELS[key] ?? key}</span><i><b className={value < 0 ? "negative" : ""} style={{ width: `${Math.min(Math.abs(value) * 8, 100)}%` }} /></i><strong className={value < 0 ? "negative" : "positive"}>{signed(value)}</strong></div>)}</section>
      <section className="card ranking-card"><div className="card-heading"><div><span className="source-label environment">地区变化</span><h2>省域排行</h2></div></div><div className="ranking-columns"><div><strong>参与改善</strong>{[...comparison.province_deltas].sort((a, b) => b.enterprise_participation_delta - a.enterprise_participation_delta).slice(0, 5).map((item, index) => <span key={item.province_code}><i>{index + 1}</i>{item.province_name}<b>{signed(item.enterprise_participation_delta)}</b></span>)}</div><div><strong>财政承压</strong>{[...comparison.province_deltas].sort((a, b) => b.fiscal_pressure_delta - a.fiscal_pressure_delta).slice(0, 5).map((item, index) => <span key={item.province_code}><i>{index + 1}</i>{item.province_name}<b>{signed(item.fiscal_pressure_delta)}</b></span>)}</div></div></section>
    </div>
    {comparison.central_review && <section className="card central-review"><div className="review-lead"><Icon name="psychology" /><div><span className="source-label model">中央研判智能体 · 对照复盘</span><h2>{comparison.central_review.public_summary}</h2></div></div><div className="finding-grid">{comparison.central_review.findings.map((finding) => <article key={finding.title}><strong>{finding.title}</strong><p>{finding.summary}</p>{finding.tradeoff && <small>{finding.tradeoff}</small>}</article>)}</div><div className="limitations"><Icon name="info" />{comparison.central_review.limitations.join(" · ")}</div></section>}
    <DeepLinkDrawers />
  </div>;
}
