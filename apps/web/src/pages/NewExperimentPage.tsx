import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { PolicyEditor } from "../components/PolicyEditor";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { Policy } from "../types";

export default function NewExperimentPage() {
  const flow = usePolicyScopeContext(); const navigate = useNavigate();
  const [objective, setObjective] = useState("比较三档中央承担比例变化对地方财政空间、新能源汽车需求与真实头部车企模拟布局的影响。");
  const [policy, setPolicy] = useState<Policy | null>(flow.world?.policy ?? flow.defaultPolicy);
  useEffect(() => setPolicy(flow.world?.policy ?? flow.defaultPolicy), [flow.defaultPolicy, flow.world?.policy]);
  const create = async () => { const next = await flow.createDraft(objective, flow.configuredRunMode); setPolicy(next.policy); };
  const approve = async () => { if (!flow.world || !policy) return; await flow.approveDirective(policy); navigate(`/experiments/${flow.world.experiment_id}/live`); };
  return <div className="v3-page">
    <div className="v3-page-heading"><div><span className="v3-kicker">SETUP · 中央政策配置</span><h1>新能源汽车补贴共担比例实验</h1><p>仅调整西部、中部、东部中央承担比例；补贴标准与资格规则保持冻结。</p></div><span className="v3-stage">人工审批门禁</span></div>
    <div className="v3-two-col">
      <section className="v3-card"><div className="v3-card-title"><Icon name="target" /><div><small>01 · 人工目标</small><h2>实验问题</h2></div></div><textarea aria-label="实验目标" className="v3-objective" onChange={(e) => setObjective(e.target.value)} value={objective} /><div className="v3-chip-row"><span>31 省级 Agent</span><span>10 家真实车企 Agent</span><span>一年基线 + 次年 A/B</span></div><button className="v3-primary" disabled={Boolean(flow.busyLabel)} onClick={() => void create()} type="button"><Icon name="auto_awesome" />{flow.world ? "重新生成中央草案" : "生成中央政策草案"}</button><p className="v3-muted">批准前不会启动省级或车企推演。</p></section>
      <section className="v3-card"><div className="v3-card-title"><Icon name="account_balance" /><div><small>02 · 中央 Agent 草案</small><h2>三档中央承担比例</h2></div><span className="v3-status">{flow.world?.directive.approval_status ?? "未生成"}</span></div>{policy ? <><PolicyEditor onChange={setPolicy} policy={policy} readOnly={Boolean(flow.busyLabel) || flow.world?.directive.approval_status === "approved"} />{flow.world && <div className="v3-agent-note"><strong>Agent 摘要</strong><p>{flow.world.directive.public_summary}</p></div>}<button className="v3-primary" disabled={!flow.world || Boolean(flow.busyLabel)} onClick={() => void approve()} type="button"><Icon name="verified_user" />批准并进入首年推演</button></> : <div className="v3-empty">等待生成政策草案</div>}</section>
    </div>
    <section className="v3-flow-strip">{["SETUP", "Y1_Q1 省级政策", "Y1_Q2 车企响应", "Y1_Q3 环境传播", "Y1_Q4 年度结算", "YEAR1_REVIEW", "Y2 同源 A/B"].map((item, i) => <div key={item}><b>{i + 1}</b><span>{item}</span></div>)}</section>
  </div>;
}
