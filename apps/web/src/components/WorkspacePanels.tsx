import type { ReactNode } from "react";

import type { NationalMetricKey, Policy, WorldState } from "../types";
import { Icon } from "./Icon";

const METRICS: Array<{ key: NationalMetricKey; label: string; icon: string; inverse?: boolean }> = [
  { key: "enterprise_participation_index", label: "企业参与指数", icon: "groups" },
  { key: "equipment_renewal_willingness_index", label: "设备更新意愿", icon: "precision_manufacturing" },
  { key: "sme_financing_accessibility_index", label: "中小企业融资可达性", icon: "account_balance" },
  { key: "industrial_upgrade_index", label: "产业升级指数", icon: "trending_up" },
  { key: "local_fiscal_pressure_index", label: "地方财政压力", icon: "speed", inverse: true },
  { key: "regional_gap_index", label: "区域差距指数", icon: "conversion_path", inverse: true },
];

export function Panel({ title, eyebrow, aside, children, className = "" }: { title: string; eyebrow?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`card workspace-panel ${className}`}><header>{eyebrow && <span>{eyebrow}</span>}<h2>{title}</h2>{aside && <div>{aside}</div>}</header>{children}</section>;
}

export function NationalMetricStrip({ world }: { world: WorldState }) {
  return <section className="metric-grid six workspace-metrics">{METRICS.map((metric) => <article className="metric-card" key={metric.key}><div className={`metric-icon ${metric.inverse ? "risk" : ""}`}><Icon name={metric.icon} /></div><div><span>{metric.label}</span><strong>{world.national_metrics[metric.key].toFixed(1)}<small>/100</small></strong><p>{metric.inverse ? "约束指标 · 低值更优" : `${world.phase} 全国加权值`}</p></div></article>)}</section>;
}

export function PolicySnapshot({ policy, onOpen }: { policy: Policy; onOpen?: () => void }) {
  return <section className="card policy-snapshot"><header><div><span>中央政策</span><h2>当前政策方案</h2></div>{onOpen && <button onClick={onOpen} type="button">查看政策</button>}</header><dl><div><dt>支持强度</dt><dd>{policy.support_intensity.toFixed(0)} / 100</dd></div><div><dt>地方配套要求</dt><dd>{(policy.local_match_requirement * 100).toFixed(0)}%</dd></div></dl><div className="policy-instruments"><span><Icon name="payments" />直接补贴<strong>{(policy.instrument_mix.direct_subsidy * 100).toFixed(0)}%</strong></span><span><Icon name="account_balance" />贷款贴息<strong>{(policy.instrument_mix.interest_subsidy * 100).toFixed(0)}%</strong></span><span><Icon name="verified_user" />融资担保<strong>{(policy.instrument_mix.financing_guarantee * 100).toFixed(0)}%</strong></span></div><dl className="compact"><div><dt>中小企业倾斜</dt><dd>{(policy.sme_preference * 100).toFixed(0)}%</dd></div><div><dt>区域支持偏向</dt><dd>{policy.regional_support_bias.toFixed(2)}</dd></div><div><dt>技术组合</dt><dd>数字化 {(policy.technology_mix.digital * 100).toFixed(0)}% · 绿色 {(policy.technology_mix.green * 100).toFixed(0)}% · 基础技改 {(policy.technology_mix.general * 100).toFixed(0)}%</dd></div></dl></section>;
}

export function StageTimeline({ world }: { world: WorldState }) {
  const active = Number(world.phase.slice(1));
  const labels = ["中央目标", "省级决策", "企业响应", "反馈与审批", "同源分支", "中央复盘"];
  return <section className="card workspace-timeline"><header><h2>政策推演时间线</h2><span>基于同一实验与 Checkpoint 的阶段推进</span></header><div>{labels.map((label, index) => <article className={index < active ? "done" : index === active ? "active" : ""} key={label}><i>{index < active ? <Icon name="check" /> : `T${index}`}</i><strong>{label}</strong><small>{index === 3 ? "冻结检查点" : index === 4 ? "原始 / 干预" : ""}</small></article>)}</div></section>;
}
