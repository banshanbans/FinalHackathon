import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { PolicyEditor } from "../components/PolicyEditor";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { Policy } from "../types";
import { policyIsValid } from "../utils/policy";

const DEFAULT_OBJECTIVE = "在有限财政支持下推动制造业设备更新，提高中小企业参与度，并兼顾绿色转型、就业稳定和区域可达性。";

export default function NewExperimentPage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [objective, setObjective] = useState(DEFAULT_OBJECTIVE);
  const [policy, setPolicy] = useState<Policy | null>(flow.world?.policy ?? flow.defaultPolicy);

  useEffect(() => {
    if (flow.world?.policy) setPolicy(flow.world.policy);
    else if (flow.defaultPolicy) setPolicy(flow.defaultPolicy);
  }, [flow.defaultPolicy, flow.world?.policy]);

  const create = async () => {
    const next = await flow.createDraft(objective, flow.configuredRunMode);
    setPolicy(next.policy);
  };
  const approve = async () => {
    if (!flow.world || !policy) return;
    await flow.approveDirective(policy);
    navigate(`/experiments/${flow.world.experiment_id}/live`);
  };

  return (
    <div className="new-experiment-page page-stack">
      <header className="page-heading">
        <div><span className="eyebrow">T0 · 中央政策设定</span><h1>将政策目标转化为可审批参数</h1><p>国务院 Agent 负责结构化研判；只有用户批准后，地方和企业 Agent 才开始响应。</p></div>
        <div className="page-heading-status"><span className="status-dot" /><strong>{flow.world ? "草案待审批" : "等待创建"}</strong><small>人类最终控制</small></div>
      </header>
      <div className="creation-grid">
        <section className="card objective-card">
          <div className="card-heading"><span className="step-number">01</span><div><span className="source-label human">用户输入</span><h2>中央政策目标</h2></div></div>
          <label className="objective-field"><span>政策目标与约束</span><textarea aria-label="政策目标与约束" onChange={(event) => setObjective(event.target.value)} value={objective} /></label>
          <div className="objective-chips"><span><Icon name="manufacturing" />设备更新</span><span><Icon name="storefront" />SME 参与</span><span><Icon name="eco" />绿色转型</span><span><Icon name="balance" />区域可达性</span></div>
          <div className="mode-card"><div><Icon name="database" /><span><strong>现场运行：{flow.configuredRunMode.toUpperCase()}</strong><small>演示优先使用已审计缓存；fallback 会显式标记</small></span></div><span className="ready-pill">READY</span></div>
          <button className="primary-button full" disabled={Boolean(flow.busyLabel) || objective.trim().length < 3} onClick={() => void create()} type="button"><Icon name="auto_awesome" />{flow.world ? "重新生成政策草案" : "生成结构化政策草案"}<Icon name="arrow_forward" /></button>
        </section>
        <section className="card directive-card">
          <div className="card-heading"><span className="step-number">02</span><div><span className="source-label model">国务院 Agent</span><h2>结构化政策指令</h2></div><span className={`state-pill ${flow.world ? "awaiting" : "empty"}`}>{flow.world ? "待审批" : "未生成"}</span></div>
          {!flow.world || !policy ? <div className="empty-state tall"><Icon name="account_tree" /><strong>等待政策目标</strong><p>生成后将在这里显示完整 PolicySchema，而不是不可审计的自然语言建议。</p></div> : <>
            <div className="agent-summary"><Icon name="psychology" /><div><strong>结构化研判摘要</strong><p>{flow.world.directive.public_summary}</p></div></div>
            <PolicyEditor onChange={setPolicy} policy={policy} />
            <div className="constraints"><strong>硬约束</strong>{flow.world.directive.hard_constraints.map((item) => <span key={item}><Icon name="check_circle" />{item}</span>)}</div>
            {!policyIsValid(policy) && <div className="field-warning"><Icon name="warning" />政策工具组合与技术组合必须分别合计 100%。</div>}
            <div className="approval-footer"><div><Icon name="verified_user" /><span><strong>人工审批门禁</strong><small>批准的是当前完整 PolicySchema</small></span></div><button className="approve-button" disabled={!policyIsValid(policy)} onClick={() => void approve()} type="button">批准并启动推演<Icon name="arrow_forward" /></button></div>
          </>}
        </section>
      </div>
      <section className="process-strip">
        {["T0 中央设定", "T1 地方工具", "T2 企业响应", "T3 证据与审批", "T4 同源分支", "T5 结算复盘"].map((item, index) => <div className={index === 0 ? "active" : ""} key={item}><span>{index + 1}</span><strong>{item}</strong>{index < 5 && <Icon name="arrow_forward" />}</div>)}
      </section>
    </div>
  );
}
