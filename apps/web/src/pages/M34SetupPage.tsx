import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { m34Client } from "../api/m34Client";
import { Icon } from "../components/Icon";
import { useM34 } from "../context/M34Context";
import type { M34Design, M34EventPlan, M34EventTemplate, M34Policy, MacroTick } from "../m34Types";

const TICKS: MacroTick[] = ["Q1", "Q2", "Q3", "Q4"];
const policy = (id: string, shares: [number, number, number]): M34Policy => ({ policy_id: id, west_central_share: shares[0], central_central_share: shares[1], east_central_share: shares[2] });

export default function M34SetupPage() {
  const flow = useM34();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const step = params.get("step") ?? "interpretation";
  const [shares, setShares] = useState<[number, number, number]>([.98, .92, .86]);
  const [templates, setTemplates] = useState<M34EventTemplate[]>([]);
  const [events, setEvents] = useState<Array<{ templateId: string; tick: MacroTick; wave: "wave_0" | "wave_1" | "wave_2" }>>([]);
  useEffect(() => { void m34Client.eventCatalog().then(setTemplates); }, []);
  if (!flow.world) return <div className="v3-empty-page"><h2>正在恢复实验…</h2></div>;
  const world = flow.world;
  const confirmDesign = async () => {
    const eventPlans: M34EventPlan[] = events.map((selection, index) => {
      const template = templates.find((item) => item.template_id === selection.templateId)!;
      return { schema_version: "event-plan-v2", event_plan_id: `event_web_${index}_${template.template_id}`, template_id: template.template_id, name: template.title, description: template.description, conflict_group: template.template_id.startsWith("oil_price_") ? "oil-price-direction" : null, scheduled_tick: selection.tick, release_wave: selection.wave, branch_scope: "both", advance_notice: false, informed_agent_types: [], affected_subjects: template.affected_subjects, mechanism_channels: [...template.mechanism_channels, "demand", "industry"], intensity: "medium", data_quality: "scenario_assumption", evidence_refs: template.provenance_refs };
    });
    const design: M34Design = { schema_version: "experiment-design-v2", experiment_type: eventPlans.length ? "policy_stress_test" : "policy_comparison", control_policy: policy("control", [.95, .90, .85]), treatment_policy: policy("treatment", shares), event_plans: eventPlans, status: "confirmed" };
    await flow.confirmDesign(design); setParams({ step: "baseline" });
  };
  return <div className="v32-page"><header className="v32-heading"><div><span className="v32-eyebrow">M34 实验设置</span><h1>{step === "interpretation" ? "确认中央政策解读" : step === "design" ? "设置年度季度方案" : "确认同源基线"}</h1></div></header>{step === "interpretation" ? <section className="v3-card v32-interpretation"><span className="v32-eyebrow">中央 Agent · 实验前唯一一次</span><h2>{world.interpretation.public_summary}</h2><ul>{world.interpretation.policy_goals.map((item) => <li key={item}>{item}</li>)}</ul><button className="v3-primary" onClick={() => void flow.confirmInterpretation().then(() => setParams({ step: "design" }))} type="button"><Icon name="check" />确认解读</button></section> : null}{step === "design" ? <div className="v32-design-grid"><section className="v3-card"><span className="v32-eyebrow">干预方案</span><div className="v32-policy-pair">{["西部", "中部", "东部"].map((label, index) => <label key={label}>{label}<input max="100" min="0" onChange={(event) => { const next = [...shares] as [number, number, number]; next[index] = Number(event.target.value) / 100; setShares(next); }} type="number" value={Math.round(shares[index]! * 100)} />%</label>)}</div><span className="v32-eyebrow">外生事件 {events.length} / 3</span>{events.map((event, index) => <div className="v32-event-design" key={`${event.templateId}-${index}`}><select onChange={(change) => setEvents(events.map((item, itemIndex) => itemIndex === index ? { ...item, templateId: change.target.value } : item))} value={event.templateId}>{templates.map((template) => <option disabled={events.some((item, itemIndex) => itemIndex !== index && item.templateId === template.template_id)} key={template.template_id} value={template.template_id}>{template.title}</option>)}</select><select onChange={(change) => setEvents(events.map((item, itemIndex) => itemIndex === index ? { ...item, tick: change.target.value as MacroTick } : item))} value={event.tick}>{TICKS.map((tick) => <option key={tick}>{tick}</option>)}</select><select onChange={(change) => setEvents(events.map((item, itemIndex) => itemIndex === index ? { ...item, wave: change.target.value as typeof item.wave } : item))} value={event.wave}>{["wave_0", "wave_1", "wave_2"].map((wave) => <option key={wave}>{wave}</option>)}</select><button onClick={() => setEvents(events.filter((_, itemIndex) => itemIndex !== index))} type="button">删除</button></div>)}<button disabled={events.length >= 3 || !templates.length} onClick={() => { const template = templates.find((item) => !events.some((event) => event.templateId === item.template_id)); if (template) setEvents([...events, { templateId: template.template_id, tick: "Q2", wave: "wave_0" }]); }} type="button">+添加事件</button></section><div className="v32-wide-action"><button className="v3-primary" onClick={() => void confirmDesign()} type="button"><Icon name="check" />确认季度设计</button></div></div> : null}{step === "baseline" ? <section className="v3-card"><span className="v32-quality verified">代理数据基线</span><h2>31 省、10 家车企与年度资源包已就绪</h2><p>资源在 Q1–Q4 之间结转，不在每季重置。</p><button className="v3-primary" onClick={() => void flow.confirmBaseline().then(() => navigate(`/experiments/${world.experiment_id}/live`))} type="button"><Icon name="play_arrow" />确认基线并进入推演</button></section> : null}{flow.error ? <p className="v3-error">{flow.error}</p> : null}</div>;
}
