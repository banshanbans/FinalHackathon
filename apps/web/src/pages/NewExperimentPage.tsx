import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { PolicyEditor } from "../components/PolicyEditor";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import type { Policy } from "../types";
import { RUN_MODE_LABELS } from "../utils/display";
import { policyIsValid } from "../utils/policy";

const DEFAULT_OBJECTIVE = "在有限财政支持下推动制造业设备更新，提高中小企业参与度，并兼顾绿色转型、就业稳定和区域可达性。";
const HARD_CONSTRAINT_LABELS: Record<string, string> = {
  instrument_mix_sum_to_1: "政策工具合计 100%",
  technology_mix_sum_to_1: "技术组合合计 100%",
  human_approval_required: "中央政策须人工审批",
  no_real_world_forecast: "不输出现实经济预测",
};

export default function NewExperimentPage() {
  const flow = usePolicyScopeContext();
  const navigate = useNavigate();
  const [objective, setObjective] = useState(DEFAULT_OBJECTIVE);
  const [policy, setPolicy] = useState<Policy | null>(flow.world?.policy ?? flow.defaultPolicy);
  const approvalStatus = flow.world?.directive.approval_status;
  const isDraft = approvalStatus === "draft";
  const isApproved = approvalStatus === "approved";
  const isRejected = approvalStatus === "rejected";
  const statusLabel = !flow.world
    ? "待配置"
    : isApproved
      ? "中央政策已审批"
      : isRejected
        ? "政策草案已退回"
        : "政策草案待审";
  const directiveLabel = !flow.world
    ? "未生成"
    : isApproved
      ? "已审批"
      : isRejected
        ? "已退回"
        : "待审批";
  const directiveClass = !flow.world
    ? "empty"
    : isApproved
      ? "approved"
      : isRejected
        ? "rejected"
        : "awaiting";

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
    if (!isDraft) {
      navigate(`/experiments/${flow.world.experiment_id}/live`);
      return;
    }
    await flow.approveDirective(policy);
    navigate(`/experiments/${flow.world.experiment_id}/live`);
  };

  return (
    <div className="new-experiment-page page-stack">
      <header className="page-heading">
        <div><span className="eyebrow">T0 · 中央政策配置</span><h1>配置制造业设备更新政策</h1><p>设定全国目标、政策工具与地方约束，审批后进入省企响应推演。</p></div>
        <div className="page-heading-status"><span className="status-dot" /><strong>{statusLabel}</strong><small>{isApproved ? "审批状态已同步" : "人工审批控制"}</small></div>
      </header>
      <div className="creation-grid">
        <section className="card objective-card">
          <div className="card-heading"><span className="step-number">01</span><div><span className="source-label human">目标配置</span><h2>中央政策目标</h2></div></div>
          <label className="objective-field"><span>政策目标与约束</span><textarea aria-label="政策目标与约束" onChange={(event) => setObjective(event.target.value)} value={objective} /></label>
          <div className="objective-chips"><span><Icon name="manufacturing" />设备更新</span><span><Icon name="storefront" />中小企业参与</span><span><Icon name="eco" />绿色转型</span><span><Icon name="balance" />区域可达性</span></div>
          <div className="mode-card"><div><Icon name="database" /><span><strong>运行模式：{RUN_MODE_LABELS[flow.configuredRunMode]}</strong><small>默认场景、数据与离线推演资源已就绪</small></span></div><span className="ready-pill">已就绪</span></div>
          <button className="primary-button full" disabled={Boolean(flow.busyLabel) || objective.trim().length < 3} onClick={() => void create()} type="button"><Icon name="auto_awesome" />{isApproved || isRejected ? "生成新的政策草案" : flow.world ? "重新生成政策草案" : "生成结构化政策草案"}<Icon name="arrow_forward" /></button>
        </section>
        <section className="card directive-card">
          <div className="card-heading"><span className="step-number">02</span><div><span className="source-label model">中央研判智能体</span><h2>{isApproved ? "已审批政策参数" : "政策参数草案"}</h2></div><span className={`state-pill ${directiveClass}`}>{directiveLabel}</span></div>
          {!flow.world || !policy ? <div className="empty-state tall"><Icon name="account_tree" /><strong>待生成政策草案</strong><p>完成目标配置后，生成可审批的政策参数。</p></div> : <>
            <div className="agent-summary"><Icon name="psychology" /><div><strong>{isApproved ? "审批结果" : isRejected ? "退回结果" : "研判摘要"}</strong><p>{isApproved ? "当前政策已完成审批，参数已锁定并用于本次省企推演。" : isRejected ? "当前草案已退回，请重新生成政策草案后再提交审批。" : flow.world.directive.public_summary}</p></div></div>
            <PolicyEditor onChange={setPolicy} policy={policy} readOnly={!isDraft} />
            <div className="constraints"><strong>硬约束</strong>{flow.world.directive.hard_constraints.map((item) => <span key={item}><Icon name="check_circle" />{HARD_CONSTRAINT_LABELS[item] ?? item}</span>)}</div>
            {isDraft && !policyIsValid(policy) && <div className="field-warning"><Icon name="warning" />政策工具组合与技术组合必须分别合计 100%。</div>}
            <div className="approval-footer"><div><Icon name={isApproved ? "task_alt" : isRejected ? "cancel" : "verified_user"} /><span><strong>{isApproved ? "审批已完成" : isRejected ? "草案已退回" : "审批确认"}</strong><small>{isApproved ? "政策参数已锁定，可继续查看推演" : isRejected ? "请生成新的政策草案" : "提交当前完整政策参数"}</small></span></div>{!isRejected && <button className="approve-button" disabled={Boolean(flow.busyLabel) || (isDraft && !policyIsValid(policy))} onClick={() => void approve()} type="button">{isApproved ? "进入实时推演" : "批准并启动省企推演"}<Icon name="arrow_forward" /></button>}</div>
          </>}
        </section>
      </div>
      <section className="process-strip">
        {["T0 中央配置", "T1 地方执行", "T2 企业响应", "T3 干预决策", "T4 双方案运行", "T5 结算复盘"].map((item, index) => <div className={index === 0 ? "active" : ""} key={item}><span>{index + 1}</span><strong>{item}</strong>{index < 5 && <Icon name="arrow_forward" />}</div>)}
      </section>
    </div>
  );
}
