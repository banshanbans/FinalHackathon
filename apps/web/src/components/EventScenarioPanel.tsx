import { useMemo, useState } from "react";

import type { EventIntensity, EventScenarioTemplate, EventTemplateId } from "../types";
import { Icon } from "./Icon";

const intensityLabels: Record<EventIntensity, string> = {
  low: "低 · 0.25",
  medium: "中 · 0.50",
  high: "高 · 0.75",
};

interface Props {
  templates: EventScenarioTemplate[];
  approvedId?: string | null;
  disabled?: boolean;
  onApprove: (template: EventTemplateId, intensity: EventIntensity) => Promise<unknown>;
}

export function EventScenarioPanel({ templates, approvedId, disabled, onApprove }: Props) {
  const [templateId, setTemplateId] = useState<EventTemplateId>(
    templates[0]?.template_id ?? "oil_price_rise",
  );
  const [intensity, setIntensity] = useState<EventIntensity>("medium");
  const selected = useMemo(
    () => templates.find((item) => item.template_id === templateId),
    [templateId, templates],
  );

  return <section className="v3-card v31-event-lab">
    <div className="v3-card-title"><Icon name="hub" /><div><small>Y2_Q3 · 一次人工审批门禁</small><h2>事件实验台</h2></div>{approvedId && <span className="v3-status">已锁定</span>}</div>
    <p className="v31-disclaimer">本事件为冻结机制参数下的情景实验，不代表现实事件、法规或价格走势预测。</p>
    <div className="v31-event-controls">
      <label>情景模板<select aria-label="情景模板" disabled={disabled || Boolean(approvedId)} onChange={(event) => setTemplateId(event.target.value as EventTemplateId)} value={templateId}>{templates.map((item) => <option key={item.template_id} value={item.template_id}>{item.title}</option>)}</select></label>
      <label>事件强度<select aria-label="事件强度" disabled={disabled || Boolean(approvedId)} onChange={(event) => setIntensity(event.target.value as EventIntensity)} value={intensity}>{Object.entries(intensityLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    </div>
    {selected && <div className="v31-mechanism-preview"><strong>{selected.title}</strong><p>{selected.description}</p><div className="v3-chip-row">{selected.mechanism_channels.map((item) => <span key={item}>{item}</span>)}</div></div>}
    <div className="v31-interaction-flow"><span>31 省首轮信号</span><Icon name="arrow_forward" /><span>授权 Peer 响应</span><Icon name="arrow_forward" /><span>双向协作匹配</span><Icon name="arrow_forward" /><span>环境统一传播</span></div>
    <button className="v3-primary" disabled={disabled || Boolean(approvedId) || !selected} onClick={() => void onApprove(templateId, intensity)} type="button"><Icon name="verified_user" />{approvedId ? "事件已批准且不可修改" : "批准并锁定事件"}</button>
  </section>;
}
