import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { EvidenceRecord } from "../types";
import { QUALITY_LABELS } from "../utils/display";
import { Icon } from "./Icon";

const EVIDENCE_KIND_LABELS: Record<string, string> = {
  method_and_versions: "运行方法与版本",
  simulation_evidence: "推演证据",
};
const EVIDENCE_FIELD_LABELS: Record<string, string> = {
  experiment_id: "推演编号",
  source_url: "来源链接",
  source_year: "数据年份",
  unit: "指标单位",
  transformation: "处理方法",
  missing_value_handling: "异常处理",
  data_version: "数据版本",
  mechanism_version: "机制版本",
  prompt_version: "研判规则版本",
  model_version: "模型版本",
  app_version: "应用版本",
  seed: "随机种子",
  parent_checkpoint_id: "父检查点",
  description: "证据说明",
  disclaimer: "研判口径",
};

function DrawerFrame({ title, kicker, children, onClose }: { title: string; kicker: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="drawer-backdrop" role="presentation">
      <aside aria-label={title} className="deep-drawer">
        <header><div><span>{kicker}</span><h2>{title}</h2></div><button aria-label="关闭抽屉" onClick={onClose} type="button"><Icon name="close" /></button></header>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  );
}

function EvidenceDrawer({ evidenceId, onClose }: { evidenceId: string; onClose: () => void }) {
  const flow = usePolicyScopeContext();
  const loadEvidence = flow.loadEvidence;
  const [record, setRecord] = useState<EvidenceRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    loadEvidence(evidenceId).then((result) => active && setRecord(result)).catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "证据读取失败"));
    return () => { active = false; };
  }, [evidenceId, loadEvidence]);
  return <DrawerFrame kicker="数据与审计" onClose={onClose} title={evidenceId === "method" ? "运行审计信息" : evidenceId}>
    {!record && !error && <div className="drawer-loading"><span className="spinner" />正在读取证据…</div>}
    {error && <div className="fallback-notice"><Icon name="error" /><div><strong>证据不可用</strong><p>{error}</p></div></div>}
    {record && <>
      <div className="evidence-summary"><Icon name="verified" /><div><span className={`quality-pill ${record.quality}`}>{QUALITY_LABELS[record.quality]}</span><h3>{EVIDENCE_KIND_LABELS[record.kind] ?? record.kind}</h3><p>{record.source}</p></div></div>
      <dl className="evidence-list">
        {Object.entries(record).filter(([key]) => !["evidence_id", "kind", "quality", "source"].includes(key)).map(([key, value]) => <div key={key}><dt>{EVIDENCE_FIELD_LABELS[key] ?? key}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "—")}</dd></div>)}
      </dl>
      <div className="method-note"><Icon name="science" /><p>决策策略由智能体生成，指标与机制贡献由版本化环境统一测算。</p></div>
    </>}
  </DrawerFrame>;
}

export function DeepLinkDrawers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const evidence = searchParams.get("evidence");
  const close = (key: string) => {
    const next = new URLSearchParams(searchParams);
    next.delete(key);
    setSearchParams(next, { replace: true });
  };
  return <>{evidence && <EvidenceDrawer evidenceId={evidence} onClose={() => close("evidence")} />}</>;
}
