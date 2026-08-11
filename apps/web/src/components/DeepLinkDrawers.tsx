import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { EvidenceRecord } from "../types";
import { Icon } from "./Icon";

const ARCHETYPE_LABELS: Record<string, string> = {
  large_state_owned: "大型国有制造企业",
  large_private: "大型民营制造企业",
  technology_sme: "科技型 SME",
  traditional_sme: "传统制造 SME",
  high_energy_industrial: "高耗能工业企业",
  export_manufacturer: "出口制造企业",
};
const PARTICIPATION_LABELS: Record<string, string> = {
  participate: "参与",
  conditional: "条件参与",
  wait: "观望",
  decline: "拒绝",
};
const FINANCING_LABELS: Record<string, string> = {
  self_funded: "自筹",
  direct_subsidy: "直接补贴",
  interest_subsidy: "贴息贷款",
  guarantee_loan: "担保贷款",
  none: "无",
};
const UPGRADE_LABELS: Record<string, string> = {
  digital: "数字化",
  green: "绿色",
  general: "基础技改",
  none: "无",
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

function ProvinceDrawer({ code, onClose }: { code: string; onClose: () => void }) {
  const flow = usePolicyScopeContext();
  const profile = flow.world?.province_profiles[code] ?? flow.profiles.find((item) => item.province_code === code);
  const state = flow.world?.province_states[code];
  const action = flow.world?.province_actions[code];
  const feedback = flow.world?.province_feedback[code];
  const enterpriseProfiles = useMemo(
    () => Object.values(flow.world?.enterprise_profiles ?? {}).filter((item) => item.province_code === code),
    [code, flow.world?.enterprise_profiles],
  );

  return (
    <DrawerFrame kicker="省企联动详情" onClose={onClose} title={profile?.name ?? code}>
      <div className="drawer-meta-row">
        <span className={`quality-pill ${profile?.data_quality ?? "demo"}`}>{profile?.data_quality ?? "demo"}</span>
        <span>{state?.phase ?? "T0"}</span><span>省级代码 {code}</span>
      </div>
      {state && <div className="drawer-metrics">
        <div><span>企业参与</span><strong>{state.enterprise_participation_index.toFixed(1)}</strong><small>/100</small></div>
        <div><span>更新意愿</span><strong>{state.equipment_renewal_willingness_index.toFixed(1)}</strong><small>/100</small></div>
        <div><span>SME 融资可达性</span><strong>{state.sme_financing_accessibility_index.toFixed(1)}</strong><small>/100</small></div>
        <div><span>财政压力</span><strong>{state.fiscal_pressure_index.toFixed(1)}</strong><small>/100</small></div>
      </div>}
      {action && <section className="drawer-section"><div className="section-heading"><span className="source-label model">模型策略</span><strong>地方政策工具</strong></div><p>{action.public_summary}</p><div className="inline-facts"><span>执行强度 {(action.implementation_intensity * 100).toFixed(0)}%</span><span>地方配套 {(action.local_match_ratio * 100).toFixed(0)}%</span><span>SME 倾斜 {(action.sme_preference * 100).toFixed(0)}%</span></div></section>}
      {feedback && <section className="drawer-section"><div className="section-heading"><span className="source-label model">地方反馈</span><strong>{feedback.implementation_assessment}</strong></div><p>{feedback.public_summary}</p></section>}
      <section className="drawer-section enterprise-section"><div className="section-heading"><span className="source-label environment">环境计算</span><strong>六类企业群体响应</strong></div>
        <div className="enterprise-card-grid">
          {enterpriseProfiles.map((enterprise) => {
            const enterpriseAction = flow.world?.enterprise_actions[enterprise.enterprise_id];
            const enterpriseState = flow.world?.enterprise_states[enterprise.enterprise_id];
            const contribution = flow.world?.contributions[enterprise.enterprise_id];
            return <article className="enterprise-card" key={enterprise.enterprise_id}>
              <header><Icon name={enterprise.archetype.includes("sme") ? "factory" : "domain"} /><div><strong>{ARCHETYPE_LABELS[enterprise.archetype]}</strong><span className={`quality-pill ${enterprise.data_quality}`}>{enterprise.data_quality}</span></div></header>
              {enterpriseAction ? <>
                <div className={`participation ${enterpriseAction.participation}`}>{PARTICIPATION_LABELS[enterpriseAction.participation]}</div>
                <dl><div><dt>技改方向</dt><dd>{UPGRADE_LABELS[enterpriseAction.upgrade_type]}</dd></div><div><dt>融资选择</dt><dd>{FINANCING_LABELS[enterpriseAction.financing_choice]}</dd></div><div><dt>投入强度</dt><dd>{(enterpriseAction.investment_intensity * 100).toFixed(0)} / 100</dd></div></dl>
                <p>{enterpriseAction.public_summary}</p>
                {contribution && <small>机制净贡献 {Object.entries(contribution).filter(([, value]) => typeof value === "number").reduce((sum, [, value]) => sum + Number(value), 0).toFixed(2)} 指数点</small>}
              </> : <div className="enterprise-pending"><Icon name="hourglass_empty" />等待 T2 企业响应</div>}
              {enterpriseState && <div className="enterprise-state-line"><span>更新意愿</span><i><b style={{ width: `${enterpriseState.renewal_willingness}%` }} /></i><strong>{enterpriseState.renewal_willingness.toFixed(0)}</strong></div>}
            </article>;
          })}
        </div>
      </section>
      {flow.world?.fallback_provinces.includes(code) && <div className="fallback-notice"><Icon name="warning" /><div><strong>确定性 fallback 已启用</strong><p>该省企业批量结构化输出在一次修复后仍未通过校验，整省使用可审计的确定性结果。</p></div></div>}
    </DrawerFrame>
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
  return <DrawerFrame kicker="方法与证据" onClose={onClose} title={evidenceId === "method" ? "实验审计信息" : evidenceId}>
    {!record && !error && <div className="drawer-loading"><span className="spinner" />正在读取证据…</div>}
    {error && <div className="fallback-notice"><Icon name="error" /><div><strong>证据不可用</strong><p>{error}</p></div></div>}
    {record && <>
      <div className="evidence-summary"><Icon name="verified" /><div><span className={`quality-pill ${record.quality}`}>{record.quality}</span><h3>{record.kind}</h3><p>{record.source}</p></div></div>
      <dl className="evidence-list">
        {Object.entries(record).filter(([key]) => !["evidence_id", "kind", "quality", "source"].includes(key)).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "—")}</dd></div>)}
      </dl>
      <div className="method-note"><Icon name="science" /><p>模型解释用于形成策略；结果指标与机制贡献只由版本化环境计算。所有运行均记录 data、mechanism、prompt、model、app 版本与 seed。</p></div>
    </>}
  </DrawerFrame>;
}

export function DeepLinkDrawers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const province = searchParams.get("province");
  const evidence = searchParams.get("evidence");
  const close = (key: string) => {
    const next = new URLSearchParams(searchParams);
    next.delete(key);
    setSearchParams(next, { replace: true });
  };
  return <>{province && <ProvinceDrawer code={province} onClose={() => close("province")} />}{evidence && <EvidenceDrawer evidenceId={evidence} onClose={() => close("evidence")} />}</>;
}
