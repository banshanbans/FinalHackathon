import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { Icon } from "../components/Icon";
import { PolicyEditor } from "../components/PolicyEditor";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { Policy } from "../types";
import { policyIsValid } from "../utils/policy";

const FIELD_LABELS: Record<string, string> = {
  support_intensity: "支持强度",
  local_match_requirement: "地方配套要求",
  sme_preference: "中小企业倾斜",
  regional_support_bias: "区域支持倾斜",
  "instrument_mix.direct_subsidy": "直接补贴",
  "instrument_mix.interest_subsidy": "贷款贴息",
  "instrument_mix.financing_guarantee": "融资担保",
  "technology_mix.digital": "数字化技改",
  "technology_mix.green": "绿色技改",
  "technology_mix.general": "基础技改",
};
const DIRECTION_LABELS: Record<string, string> = { increase: "可能上升", decrease: "可能下降", may_increase: "或有上升", may_decrease: "或有下降" };

export default function InterventionPage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const world = flow.world;
  const approvedDecision = world?.intervention_decision?.startsWith("approved") ?? false;
  const proposal = world?.intervention_proposals[0];
  const [policy, setPolicy] = useState<Policy | null>(proposal?.proposed_policy ?? null);
  const [rejectReason, setRejectReason] = useState("当前证据不足以支持调整，保留原始方案继续观察。 ");
  useEffect(() => { if (proposal?.proposed_policy) setPolicy(proposal.proposed_policy); }, [proposal?.proposed_policy]);
  const modified = useMemo(() => policy && proposal ? JSON.stringify(policy) !== JSON.stringify(proposal.proposed_policy) : false, [policy, proposal]);
  const openEvidence = (evidenceId: string) => { const next = new URLSearchParams(searchParams); next.set("evidence", evidenceId); setSearchParams(next); };
  if (!world || !proposal) return <div className="card empty-state page-empty"><Icon name="pending_actions" /><h2>尚无中央干预建议</h2><p>先完成 T1–T3 地方与企业推演。</p><button className="primary-button" onClick={() => navigate(world ? `/experiments/${world.experiment_id}/live` : "/experiments/new")} type="button">返回实时推演</button></div>;

  const approve = async () => {
    if (!policy) return;
    await flow.approveProposal(proposal.proposal_id, policy);
  };
  const reject = async () => { await flow.rejectProposal(proposal.proposal_id, rejectReason.trim()); };
  const complete = async () => { await flow.runComparison(); navigate(`/experiments/${world.experiment_id}/compare`); };
  const completeSingle = async () => { await flow.runSingleBranch(); navigate(`/experiments/${world.experiment_id}/compare`); };

  return <div className="intervention-page page-stack">
    <header className="page-heading compact-heading"><div><span className="eyebrow">T3 · 中央干预审批</span><h1>证据 → AI 建议 → 人类决定</h1><p>国务院 Agent 只能提出待验证建议；用户批准前，不会修改政策或创建干预方案。</p></div><span className={`state-pill ${world.intervention_decision ?? "awaiting"}`}>{approvedDecision ? "已批准" : world.intervention_decision === "rejected" ? "已拒绝" : "等待人类审批"}</span></header>
    <div className="intervention-columns">
      <section className="card evidence-column">
        <div className="column-number">01</div><span className="source-label environment">证据</span><h2>发生了什么</h2><p>来自省级反馈与确定性环境结算，不是模型自行猜测。</p>
        <div className="evidence-kpis"><div><span>传统 SME 观望</span><strong>{Object.values(world.enterprise_actions).filter((item) => item.archetype === "traditional_sme" && item.participation === "wait").length}</strong><small>个省级群体</small></div><div><span>地方请求支持</span><strong>{Object.values(world.province_feedback).filter((item) => item.requested_central_support >= .6).length}</strong><small>个省份</small></div><div><span>fallback</span><strong>{world.fallback_provinces.length}</strong><small>个省份</small></div></div>
        <div className="evidence-list-buttons">{proposal.evidence_refs.map((ref) => <button key={ref} onClick={() => openEvidence(ref)} type="button"><Icon name="description" /><span><strong>{ref}</strong><small>打开证据与版本信息</small></span><Icon name="open_in_new" /></button>)}</div>
        <button className="text-button" onClick={() => openEvidence("method")} type="button"><Icon name="science" />查看方法、seed 与父检查点</button>
      </section>
      <section className="card advice-column">
        <div className="column-number">02</div><span className="source-label model">国务院 Agent 建议</span><h2>调整政策工具组合</h2><div className="advice-summary"><Icon name="psychology" /><p>{proposal.public_summary}</p></div>
        <div className="change-table"><header><span>政策字段</span><span>原始方案</span><span>建议方案</span></header>{proposal.parameter_changes.map((change) => <div key={change.path}><strong>{FIELD_LABELS[change.path] ?? change.path}</strong><span>{String(change.from_value)}</span><Icon name="arrow_forward" /><span className="new-value">{String(change.to_value)}</span></div>)}</div>
        <div className="hypotheses"><strong>预期方向 <em>待验证</em></strong>{Object.entries(proposal.expected_directions).map(([metric, direction]) => <span key={metric}><Icon name="science" />{metric}<b>{DIRECTION_LABELS[direction]}</b></span>)}</div>
        <div className="tradeoffs"><strong>可能代价</strong>{proposal.tradeoffs.map((item) => <p key={item}><Icon name="warning" />{item}</p>)}</div>
      </section>
      <section className="card decision-column">
        <div className="column-number">03</div><span className="source-label human">人类审批</span><h2>决定是否创建干预方案</h2><p>可以直接批准、修改完整参数后批准，或拒绝并让原始方案单线运行至 T5。</p>
        {policy && <PolicyEditor compact onChange={setPolicy} policy={policy} />}
        <div className={`decision-state ${modified ? "modified" : ""}`}><Icon name={modified ? "edit" : "check_circle"}/><span><strong>{modified ? "已修改 AI 建议" : "当前采用 AI 建议"}</strong><small>服务端将重新校验完整 PolicySchema 并计算字段差异</small></span></div>
        {world.intervention_decision === null && <><button className="approve-button full" disabled={!policy || !policyIsValid(policy)} onClick={() => void approve()} type="button"><Icon name="verified_user" />{modified ? "批准修改后的方案" : "批准并创建干预方案"}</button><div className="reject-box"><label><span>拒绝原因</span><textarea aria-label="拒绝原因" onChange={(event) => setRejectReason(event.target.value)} value={rejectReason} /></label><button disabled={!rejectReason.trim()} onClick={() => void reject()} type="button"><Icon name="block" />拒绝建议，保留原始方案</button></div></>}
        {approvedDecision && <div className="decision-complete"><Icon name="account_tree" /><div><strong>同源分支已创建</strong><p>{flow.branch ? `两条分支从 ${flow.branch.parent_checkpoint_id.slice(-12)} 恢复，唯一主动差异是批准字段。` : "同源分支已经完成；可在方案对照页查看结构化结果。"}</p></div>{flow.branch && world.phase !== "T5" && <button className="primary-button full" onClick={() => void complete()} type="button">运行双分支至 T5<Icon name="arrow_forward" /></button>}</div>}
        {world.intervention_decision === "rejected" && <div className="decision-complete rejected"><Icon name="fork_right" /><div><strong>不创建干预方案</strong><p>用户决定已写入 Replay；Compare 接口不会伪造无差异分支。</p></div><button className="primary-button full" onClick={() => void completeSingle()} type="button">运行原始方案至 T5<Icon name="arrow_forward" /></button></div>}
      </section>
    </div>
    <DeepLinkDrawers />
  </div>;
}
