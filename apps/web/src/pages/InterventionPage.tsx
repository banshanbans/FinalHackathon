import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { PolicyEditor } from "../components/PolicyEditor";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { Policy } from "../types";

export default function InterventionPage() {
  const flow = usePolicyScopeContext(); const navigate = useNavigate(); const proposal = flow.world?.intervention_proposals[0];
  const [policy, setPolicy] = useState<Policy | null>(proposal?.proposed_policy ?? null);
  useEffect(() => setPolicy(proposal?.proposed_policy ?? null), [proposal]);
  if (!flow.world) return <div className="v3-empty-page"><Icon name="lock_clock" /><h2>等待首年复盘</h2><button onClick={() => navigate("/experiments/new")} type="button">返回政策设定</button></div>;
  if (flow.world.comparison_mode === "event_counterfactual") {
    const confirm = async () => { await flow.confirmEventCounterfactual(); navigate(`/experiments/${flow.world!.experiment_id}/live`); };
    return <div className="v3-page"><div className="v3-page-heading"><div><span className="v3-kicker">YEAR1_REVIEW · 事件反事实</span><h1>同政策分支确认</h1></div></div><div className="v3-three-col">
      <section className="v3-card"><div className="v3-card-title"><Icon name="fact_check" /><div><small>01 · 首年 Checkpoint</small><h2>脆弱性证据</h2></div></div><div className="v3-evidence-metrics"><div><span>Gap</span><strong>{flow.world.national_metrics.regional_development_gap.toFixed(2)}</strong></div><div><span>地方财政压力</span><strong>{flow.world.national_metrics.local_fiscal_pressure.toFixed(2)}</strong></div><div><span>新能源汽车需求</span><strong>{flow.world.national_metrics.nev_demand.toFixed(2)}</strong></div></div></section>
      <section className="v3-card"><div className="v3-card-title"><Icon name="difference" /><div><small>02 · 唯一主动差异</small><h2>政策完全相同</h2></div></div><p className="v3-agent-summary">原始分支保持无事件基线，事件情景仅在干预分支 Y2_Q3 生效；两个分支共享同一首年不可变 Checkpoint。</p><div className="v3-chip-row"><span>policy_diff = 空</span><span>event_diff = 有无</span></div></section>
      <section className="v3-card"><div className="v3-card-title"><Icon name="verified_user" /><div><small>03 · 用户确认</small><h2>派生双分支</h2></div></div><button className="v3-primary" disabled={Boolean(flow.busyLabel)} onClick={() => void confirm()} type="button">确认同政策事件反事实</button></section>
    </div></div>;
  }
  if (!proposal || !policy) return <div className="v3-empty-page"><Icon name="lock_clock" /><h2>等待首年复盘与中央建议</h2><button onClick={() => navigate(`/experiments/${flow.world!.experiment_id}/live`)} type="button">返回全国推演</button></div>;
  const approve = async () => { await flow.approveProposal(proposal.proposal_id, policy); navigate(`/experiments/${flow.world!.experiment_id}/live`); };
  const reject = async () => { await flow.rejectProposal(proposal.proposal_id, "用户保留原始方案"); await flow.runSingleBranch(); navigate(`/experiments/${flow.world!.experiment_id}/compare`); };
  return <div className="v3-page"><div className="v3-page-heading"><div><span className="v3-kicker">YEAR1_REVIEW · 人工干预</span><h1>证据 → 中央建议 → 人工审批</h1></div></div><div className="v3-three-col">
    <section className="v3-card"><div className="v3-card-title"><Icon name="fact_check" /><div><small>01 · 首年 Checkpoint</small><h2>首年证据</h2></div></div><div className="v3-evidence-metrics"><div><span>Gap</span><strong>{flow.world.national_metrics.regional_development_gap.toFixed(2)}</strong></div><div><span>地方财政压力</span><strong>{flow.world.national_metrics.local_fiscal_pressure.toFixed(2)}</strong></div><div><span>新能源汽车需求</span><strong>{flow.world.national_metrics.nev_demand.toFixed(2)}</strong></div></div></section>
    <section className="v3-card"><div className="v3-card-title"><Icon name="psychology" /><div><small>02</small><h2>中央 Agent 建议</h2></div></div><p className="v3-agent-summary">{proposal.public_summary}</p><PolicyEditor onChange={setPolicy} policy={policy} />{proposal.tradeoffs.map((item) => <div className="v3-tradeoff" key={item}><Icon name="balance" />{item}</div>)}</section>
    <section className="v3-card"><div className="v3-card-title"><Icon name="verified_user" /><div><small>03 · 用户决策</small><h2>人工审批</h2></div></div><div className="v3-approval-options"><button className="v3-primary" onClick={() => void approve()} type="button">批准/修改后创建 A/B</button><button className="v3-secondary" onClick={() => void reject()} type="button">拒绝干预，仅运行原始方案</button></div></section>
  </div></div>;
}
