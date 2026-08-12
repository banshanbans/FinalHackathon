import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { PolicyEditor } from "../components/PolicyEditor";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { ComparisonMode, Policy } from "../types";

export default function NewExperimentPage() {
  const flow = usePolicyScopeContext(); const navigate = useNavigate();
  const [objective, setObjective] = useState("比较三档中央承担比例变化对地方财政空间、新能源汽车需求与真实头部车企模拟布局的影响。");
  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>("policy_intervention");
  const [policy, setPolicy] = useState<Policy | null>(flow.world?.policy ?? flow.defaultPolicy);
  useEffect(() => setPolicy(flow.world?.policy ?? flow.defaultPolicy), [flow.defaultPolicy, flow.world?.policy]);
  const create = async () => { const next = await flow.createDraft(objective, flow.configuredRunMode, comparisonMode); setPolicy(next.policy); };
  const approve = async () => { if (!flow.world || !policy) return; await flow.approveDirective(policy); navigate(`/experiments/${flow.world.experiment_id}/live`); };
  return <div className="v3-page">
    <div className="v3-page-heading"><div><h1>新能源汽车补贴共担比例实验</h1></div></div>
    <div className="v3-two-col">
      <section className="v3-card"><div className="v3-card-title"><Icon name="target" /><div><small>01 · 人工目标</small><h2>实验问题</h2></div></div><textarea aria-label="实验目标" className="v3-objective" onChange={(e) => setObjective(e.target.value)} value={objective} /><div className="v31-mode-picker"><button className={comparisonMode === "policy_intervention" ? "active" : ""} onClick={() => setComparisonMode("policy_intervention")} type="button"><strong>政策干预</strong><span>比例不同 · 两分支事件相同</span></button><button className={comparisonMode === "event_counterfactual" ? "active" : ""} onClick={() => setComparisonMode("event_counterfactual")} type="button"><strong>事件反事实</strong><span>政策相同 · 仅干预分支注入事件</span></button></div><div className="v3-chip-row"><span>31 省级 Agent</span><span>两轮省际交互</span><span>同源双分支</span></div><button className="v3-primary" disabled={Boolean(flow.busyLabel)} onClick={() => void create()} type="button"><Icon name="auto_awesome" />{flow.world ? "重新生成中央草案" : "生成中央政策草案"}</button></section>
      <section className="v3-card"><div className="v3-card-title"><Icon name="account_balance" /><div><small>02 · 中央 Agent 草案</small><h2>三档中央承担比例</h2></div><span className="v3-status">{flow.world?.directive.approval_status ?? "未生成"}</span></div>{policy ? <><PolicyEditor onChange={setPolicy} policy={policy} readOnly={Boolean(flow.busyLabel) || flow.world?.directive.approval_status === "approved"} />{flow.world && <div className="v3-agent-note"><strong>Agent 摘要</strong><p>{flow.world.directive.public_summary}</p></div>}<button className="v3-primary v3-approval-action" disabled={!flow.world || Boolean(flow.busyLabel)} onClick={() => void approve()} type="button"><Icon name="verified_user" />批准并进入首年推演</button></> : <div className="v3-empty">等待生成政策草案</div>}</section>
    </div>
    <section className="v3-flow-strip">{["政策设定", "全国推演", "省级详情", "干预审批", "方案对照"].map((item, i) => <div key={item}><b>{i + 1}</b><span>{item}</span></div>)}</section>
  </div>;
}
