import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { policyScopeApi } from "../api/client";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type {
  AgentInvocationTrace,
  AuditRecord,
  EvidenceRecord,
  MechanismExplanationTrace,
} from "../types";
import { QUALITY_LABELS } from "../utils/display";
import { Icon } from "./Icon";

type AuditTab = "behavior" | "mechanism" | "versions";

const EVIDENCE_KIND_LABELS: Record<string, string> = {
  method_and_versions: "运行方法与版本",
  simulation_evidence: "推演证据",
  agent_behavior: "Agent 行为追溯",
  mechanism_evidence: "环境机制解释",
  decision_gate: "审批与分支审计",
};

const OPERATION_LABELS: Record<string, string> = {
  draft_directive: "生成中央政策草案",
  derive_persona: "生成实验决策画像",
  decide_province_action: "省级 Agent 决策",
  decide_enterprise_batch: "六类企业批量响应",
  review_enterprise_feedback: "省级复盘与调整意向",
  propose_intervention: "中央干预建议",
  review_single_branch: "中央单线复盘",
  review_comparison: "中央 A/B 复盘",
  approve_central_directive: "用户批准中央政策",
  approve_intervention: "用户批准干预建议",
  reject_intervention: "用户拒绝干预建议",
  freeze_checkpoint: "冻结 T3 Checkpoint",
  derive_treatment_branch: "派生干预方案分支",
  compare_control_and_treatment: "同源方案对照",
};

const OUTCOME_LABELS: Record<string, string> = {
  succeeded: "校验通过",
  repaired: "修复后通过",
  fallback: "规则接管",
  cache_hit: "缓存命中",
  cache_miss: "缓存缺失并接管",
  rejected: "已拒绝",
};

function shortHash(value: string | null | undefined) {
  return value ? `${value.slice(0, 12)}…${value.slice(-8)}` : "—";
}

function DrawerFrame({ title, kicker, children, onClose }: { title: string; kicker: string; children: React.ReactNode; onClose: () => void }) {
  return <div className="drawer-backdrop" role="presentation"><aside aria-label={title} className="deep-drawer audit-drawer"><header><div><span>{kicker}</span><h2>{title}</h2></div><button aria-label="关闭抽屉" onClick={onClose} type="button"><Icon name="close" /></button></header><div className="drawer-body">{children}</div></aside></div>;
}

function AuditRecordCard({ record, onOpen }: { record: AuditRecord; onOpen: (recordId: string) => void }) {
  const payload = record.payload;
  const operation = "operation" in payload ? payload.operation : payload.formula_id;
  const outcome = "outcome" in payload ? payload.outcome : "succeeded";
  return <article className={`audit-record-card ${payload.kind}`}>
    <header><Icon name={payload.kind === "agent_invocation" ? "psychology" : payload.kind === "mechanism_explanation" ? "function" : "verified_user"} /><div><strong>{OPERATION_LABELS[operation] ?? operation}</strong><small>{record.phase} · {record.branch_id === "control" ? "原始方案" : "干预方案"} · #{record.sequence}</small></div><span className={`audit-outcome ${outcome}`}>{OUTCOME_LABELS[outcome] ?? outcome}</span></header>
    <button onClick={() => onOpen(record.record_id)} type="button">查看完整记录<Icon name="arrow_forward" /></button>
  </article>;
}

function BehaviorPanel({ records, onOpen }: { records: AuditRecord[]; onOpen: (recordId: string) => void }) {
  const behaviors = records.filter((item) => item.payload.kind === "agent_invocation" || item.payload.kind === "decision_gate");
  if (behaviors.length === 0) return <div className="audit-empty"><Icon name="hourglass_empty" /><strong>暂无行为记录</strong><p>Agent 完成结构化决策或用户执行审批后，将在此形成可追溯链。</p></div>;
  return <div className="audit-timeline">{behaviors.slice().reverse().map((record) => <AuditRecordCard key={record.record_id} onOpen={onOpen} record={record} />)}</div>;
}

function MechanismFormula({ trace }: { trace: MechanismExplanationTrace }) {
  return <section className="mechanism-explanation-card">
    <header><div><span>{trace.scope.toUpperCase()}</span><strong>{trace.metric}</strong><small>{trace.formula_id} · {trace.formula_version}</small></div><div><b>{trace.final_value.toFixed(4)}</b><small>{trace.unit}</small></div></header>
    <div className="mechanism-equation"><span>原值 {trace.previous_value ?? "—"}</span><span>公式值 {trace.raw_value.toFixed(4)}</span><span>裁剪 {trace.clamp_adjustment >= 0 ? "+" : ""}{trace.clamp_adjustment.toFixed(4)}</span><strong>残差 {trace.residual.toFixed(6)}</strong></div>
    <div className="mechanism-terms"><div><b>输入项</b><b>输入</b><b>系数</b><b>贡献</b></div>{trace.terms.map((term) => <div key={`${term.name}:${term.source_ref ?? "local"}`}><span>{term.name}</span><span>{term.input_value.toFixed(4)}</span><span>× {term.coefficient.toFixed(4)}</span><strong>{term.contribution >= 0 ? "+" : ""}{term.contribution.toFixed(4)}</strong></div>)}</div>
  </section>;
}

function MechanismPanel({ records }: { records: AuditRecord[] }) {
  const explanations = records.filter((item): item is AuditRecord & { payload: MechanismExplanationTrace } => item.payload.kind === "mechanism_explanation");
  if (explanations.length === 0) return <div className="audit-empty"><Icon name="function" /><strong>暂无机制解释</strong><p>环境结算后，将展示公式输入、系数、逐项贡献、裁剪和守恒残差。</p></div>;
  return <div className="mechanism-explanation-list">{explanations.slice(-12).reverse().map((item) => <MechanismFormula key={item.record_id} trace={item.payload} />)}</div>;
}

function InvocationDetail({ trace }: { trace: AgentInvocationTrace }) {
  return <div className="invocation-detail">
    <dl><div><dt>主体</dt><dd>{trace.actor_kind} / {trace.actor_id}</dd></div><div><dt>操作</dt><dd>{OPERATION_LABELS[trace.operation] ?? trace.operation}</dd></div><div><dt>实际模型</dt><dd>{trace.model}</dd></div><div><dt>运行结果</dt><dd>{OUTCOME_LABELS[trace.outcome] ?? trace.outcome}</dd></div><div><dt>Prompt / Schema</dt><dd>{trace.prompt_version} / {trace.response_schema}</dd></div><div><dt>耗时</dt><dd>{trace.latency_ms.toFixed(1)} ms</dd></div><div><dt>输入哈希</dt><dd>{shortHash(trace.input_hash)}</dd></div><div><dt>输出哈希</dt><dd>{shortHash(trace.output_hash)}</dd></div><div><dt>Token</dt><dd>{trace.usage?.total_tokens ?? "—"}</dd></div></dl>
    {trace.attempts.length > 0 && <section className="validation-attempts"><strong>结构化校验</strong>{trace.attempts.map((attempt) => <div key={attempt.attempt}><span>第 {attempt.attempt} 次</span><b>{attempt.status}</b><small>{attempt.error_code ?? `${attempt.latency_ms.toFixed(1)} ms`}</small></div>)}</section>}
    <details><summary>结构化输入快照</summary><pre>{JSON.stringify(trace.input_snapshot, null, 2)}</pre></details><details><summary>结构化输出快照</summary><pre>{JSON.stringify(trace.output_snapshot, null, 2)}</pre></details>
  </div>;
}

function VersionPanel({ evidence, selected }: { evidence: EvidenceRecord; selected: AuditRecord | null }) {
  return <div className="version-audit-panel">
    <div className={`chain-status ${evidence.audit_chain_valid ? "valid" : "invalid"}`}><Icon name={evidence.audit_chain_valid ? "verified" : "warning"} /><div><strong>{evidence.audit_chain_valid ? "审计哈希链完整" : "审计哈希链未验证"}</strong><p>每条记录包含前序哈希与自身哈希，用于发现运行记录被修改的情况。</p></div></div>
    <dl><div><dt>数据版本</dt><dd>{evidence.data_version ?? "—"}</dd></div><div><dt>机制版本</dt><dd>{evidence.mechanism_version ?? "—"}</dd></div><div><dt>Prompt 版本</dt><dd>{evidence.prompt_version ?? "—"}</dd></div><div><dt>模型版本</dt><dd>{evidence.model_version ?? "—"}</dd></div><div><dt>应用版本</dt><dd>{evidence.app_version ?? "—"}</dd></div><div><dt>随机种子</dt><dd>{evidence.seed ?? "—"}</dd></div><div><dt>父检查点</dt><dd>{evidence.parent_checkpoint_id ?? "未派生"}</dd></div>{selected && <><div><dt>记录编号</dt><dd>{selected.record_id}</dd></div><div><dt>记录哈希</dt><dd>{shortHash(selected.record_hash)}</dd></div><div><dt>前序哈希</dt><dd>{shortHash(selected.previous_record_hash)}</dd></div></>}</dl>
    <div className="method-note"><Icon name="science" /><p>Agent 只选择结构化策略；指标与机制贡献由版本化确定性环境计算。系统不保存或展示模型长思维链。</p></div>
  </div>;
}

function EvidenceDrawer({ evidenceId, onClose, onOpen }: { evidenceId: string; onClose: () => void; onOpen: (recordId: string) => void }) {
  const flow = usePolicyScopeContext();
  const experimentId = flow.world?.experiment_id;
  const [tab, setTab] = useState<AuditTab>("behavior");
  useEffect(() => setTab("behavior"), [evidenceId]);
  const evidenceQuery = useQuery({ queryKey: ["evidence-v1", experimentId, evidenceId], queryFn: () => policyScopeApi.evidence(experimentId!, evidenceId), enabled: Boolean(experimentId) });
  const auditQuery = useQuery({ queryKey: ["audit-drawer-v1", experimentId], queryFn: () => policyScopeApi.audit(experimentId!, { limit: 100 }), enabled: Boolean(experimentId), staleTime: 15_000 });
  const record = evidenceQuery.data;
  const selected = record?.audit_record ?? null;
  const records = useMemo(() => {
    const items = [...(auditQuery.data?.records ?? []), ...(record?.audit_records ?? [])];
    if (selected) items.push(selected);
    return [...new Map(items.map((item) => [item.record_id, item])).values()];
  }, [auditQuery.data?.records, record?.audit_records, selected]);
  const title = evidenceId === "method" ? "方法、行为与机制审计" : selected ? OPERATION_LABELS["operation" in selected.payload ? selected.payload.operation : selected.payload.formula_id] ?? evidenceId : evidenceId;
  const error = evidenceQuery.error instanceof Error ? evidenceQuery.error.message : null;
  return <DrawerFrame kicker="数据与审计" onClose={onClose} title={title}>
    {!record && !error && <div className="drawer-loading"><span className="spinner" />正在读取证据与审计链…</div>}
    {error && <div className="fallback-notice"><Icon name="error" /><div><strong>证据不可用</strong><p>{error}</p></div></div>}
    {record && <>
      <div className="evidence-summary"><Icon name={record.audit_chain_valid ? "verified" : "fact_check"} /><div><span className={`quality-pill ${record.quality}`}>{QUALITY_LABELS[record.quality]}</span><h3>{EVIDENCE_KIND_LABELS[record.kind] ?? record.kind}</h3><p>{record.source}</p></div></div>
      <div className="audit-tabs" role="tablist"><button aria-selected={tab === "behavior"} className={tab === "behavior" ? "active" : ""} onClick={() => setTab("behavior")} role="tab" type="button">行为链</button><button aria-selected={tab === "mechanism"} className={tab === "mechanism" ? "active" : ""} onClick={() => setTab("mechanism")} role="tab" type="button">机制链</button><button aria-selected={tab === "versions"} className={tab === "versions" ? "active" : ""} onClick={() => setTab("versions")} role="tab" type="button">版本与来源</button></div>
      {tab === "behavior" && (selected?.payload.kind === "agent_invocation" ? <InvocationDetail trace={selected.payload} /> : <BehaviorPanel onOpen={onOpen} records={records} />)}
      {tab === "mechanism" && <MechanismPanel records={selected?.payload.kind === "mechanism_explanation" ? [selected] : records} />}
      {tab === "versions" && <VersionPanel evidence={record} selected={selected} />}
    </>}
  </DrawerFrame>;
}

export function DeepLinkDrawers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const evidence = searchParams.get("evidence");
  const close = () => { const next = new URLSearchParams(searchParams); next.delete("evidence"); setSearchParams(next, { replace: true }); };
  const open = (recordId: string) => { const next = new URLSearchParams(searchParams); next.set("evidence", `audit:${recordId}`); setSearchParams(next, { replace: true }); };
  return <>{evidence && <EvidenceDrawer evidenceId={evidence} onClose={close} onOpen={open} />}</>;
}
