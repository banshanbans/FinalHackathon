import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useV32 } from "../context/V32Context";
import { productLabel } from "../productLabels";
import type { EventPlan, ExperimentDesign, ExperimentType, PolicyV4 } from "../v32Types";

const makePolicy = (id: string, values: [number, number, number]): PolicyV4 => ({ schema_version: "policy-v4", policy_id: id, reference_policy_year: 2025, west_central_share: values[0], central_central_share: values[1], east_central_share: values[2], data_quality: "scenario_assumption" });
const shares = (policy: PolicyV4): [number, number, number] => [policy.west_central_share, policy.central_central_share, policy.east_central_share];

function ShareEditor({ title, value, onChange, disabled }: { title: string; value: [number, number, number]; onChange: (value: [number, number, number]) => void; disabled?: boolean }) {
  const labels = ["西部", "中部", "东部"];
  return <div className="v32-share-editor"><strong>{title}</strong>{value.map((item, index) => <label key={labels[index]}><span>{labels[index]}</span><input disabled={disabled} max={100} min={0} onChange={(event) => { const next = [...value] as [number, number, number]; next[index] = Number(event.target.value) / 100; onChange(next); }} type="number" value={Math.round(item * 100)} /><em>%</em></label>)}</div>;
}

export default function V32SetupPage() {
  const flow = useV32();
  const world = flow.world;
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const step = params.get("step") ?? "interpretation";
  const interpretation = world?.interpretation;
  const base = interpretation ? shares(interpretation.executable_policy) : [.95, .90, .85] as [number, number, number];
  const [experimentType, setExperimentType] = useState<ExperimentType>("policy_comparison");
  const [control, setControl] = useState<[number, number, number]>(base);
  const [treatment, setTreatment] = useState<[number, number, number]>([Math.min(1, base[0] + .02), Math.min(1, base[1] + .02), Math.min(1, base[2] + .01)]);
  const [eventTemplate, setEventTemplate] = useState("intelligent_driving_upgrade");
  const [trigger, setTrigger] = useState<EventPlan["trigger_point"]>("after_automaker_initial");
  const [advanceNotice, setAdvanceNotice] = useState(false);
  const [intensity, setIntensity] = useState<EventPlan["intensity"]>("medium");
  const selectedTemplate = useMemo(() => flow.eventTemplates.find((item) => item.template_id === eventTemplate), [eventTemplate, flow.eventTemplates]);
  if (!world || !interpretation) return <div className="v3-empty-page"><h2>尚未生成政策解读</h2><button onClick={() => navigate("/experiments/new")} type="button">返回新建实验</button></div>;

  const confirmInterpretation = async () => { await flow.confirmInterpretation(interpretation); setParams({ step: "design" }); };
  const confirmDesign = async () => {
    const eventNeeded = experimentType !== "policy_comparison";
    const left = makePolicy("policy_control_v32", control);
    const rightValues = experimentType === "event_counterfactual" ? control : treatment;
    const right = makePolicy("policy_treatment_v32", rightValues);
    const eventPlan: EventPlan | null = eventNeeded ? {
      schema_version: "event-plan-v1", event_plan_id: `event_${eventTemplate}_${intensity}`, template_id: eventTemplate,
      name: selectedTemplate?.title ?? "冻结情景", description: selectedTemplate?.description ?? "实验设计阶段冻结的情景假设。",
      trigger_point: trigger, advance_notice: advanceNotice, informed_agent_types: advanceNotice ? ["province", "automaker"] : [],
      affected_subjects: ["province", "automaker", "consumer", "supply_chain"], mechanism_channels: selectedTemplate?.mechanism_channels ?? ["scenario_mechanism"],
      branch_scope: experimentType === "event_counterfactual" ? "treatment_only" : "both", intensity, data_quality: "scenario_assumption",
      evidence_refs: selectedTemplate?.provenance_refs ?? ["scenario:v32-user-design"],
    } : null;
    const design: ExperimentDesign = { schema_version: "experiment-design-v1", experiment_type: experimentType, control_policy: left, treatment_policy: right, event_plan: eventPlan, status: "confirmed" };
    await flow.confirmDesign(design); setParams({ step: "baseline" });
  };
  const confirmBaseline = async () => { await flow.confirmBaseline(); navigate(`/experiments/${world.experiment_id}/live`); };

  return <div className="v32-page">
    <header className="v32-heading"><div><span className="v32-eyebrow">实验设置</span><h1>{step === "interpretation" ? "确认政策解读" : step === "design" ? "设置对比方案" : "数据准备完成"}</h1></div><div className="v32-setup-steps">{["政策解读", "对比方案", "开始推演"].map((item, index) => <span className={index === (step === "interpretation" ? 0 : step === "design" ? 1 : 2) ? "active" : ""} key={item}>{index + 1} {item}</span>)}</div></header>
    {step === "interpretation" && <div className="v32-interpret-grid"><section className="v3-card"><span className="v32-eyebrow">政策原文</span><p className="v32-source-text">{interpretation.source_text}</p><div className="v32-share-summary"><b>西部 {Math.round(base[0] * 100)}%</b><b>中部 {Math.round(base[1] * 100)}%</b><b>东部 {Math.round(base[2] * 100)}%</b></div></section><section className="v3-card v32-interpretation"><span className="v32-eyebrow">政策解读</span><h2>{interpretation.public_summary}</h2><div className="v32-field-list"><div><strong>政策目标</strong><ul>{interpretation.policy_goals.map((item) => <li key={item}>{item}</li>)}</ul></div></div><button className="v3-primary" onClick={() => void confirmInterpretation()} type="button"><Icon name="check" />确认并设置方案</button></section></div>}
    {step === "design" && <div className="v32-design-grid"><section className="v3-card"><span className="v32-eyebrow">实验类型</span><div className="v32-type-picker">{(["policy_comparison", "policy_stress_test", "event_counterfactual"] as ExperimentType[]).map((item) => <button className={experimentType === item ? "active" : ""} key={item} onClick={() => setExperimentType(item)} type="button"><strong>{productLabel(item)}</strong><span>{item === "policy_comparison" ? "政策对比" : item === "policy_stress_test" ? "相同事件下的方案比较" : "事件影响比较"}</span></button>)}</div><div className="v32-policy-pair"><ShareEditor onChange={setControl} title="原始方案" value={control} /><ShareEditor disabled={experimentType === "event_counterfactual"} onChange={setTreatment} title="干预方案" value={experimentType === "event_counterfactual" ? control : treatment} /></div></section>{experimentType !== "policy_comparison" && <section className="v3-card v32-event-design"><span className="v32-eyebrow">事件设置</span><label>事件<select onChange={(event) => setEventTemplate(event.target.value)} value={eventTemplate}>{flow.eventTemplates.map((item) => <option key={item.template_id} value={item.template_id}>{item.title}</option>)}</select></label><label>发生时点<select onChange={(event) => setTrigger(event.target.value as EventPlan["trigger_point"])} value={trigger}>{["before_province_initial", "after_province_initial", "after_automaker_initial"].map((item) => <option key={item} value={item}>{productLabel(item)}</option>)}</select></label><label>强度<select onChange={(event) => setIntensity(event.target.value as EventPlan["intensity"])} value={intensity}>{["low", "medium", "high"].map((item) => <option key={item} value={item}>{productLabel(item)}</option>)}</select></label><label className="v32-check"><input checked={advanceNotice} onChange={(event) => setAdvanceNotice(event.target.checked)} type="checkbox" />提前通知参与主体</label></section>}<div className="v32-wide-action"><button className="v3-primary" onClick={() => void confirmDesign()} type="button"><Icon name="check" />确认方案</button></div></div>}
    {step === "baseline" && <div className="v32-baseline-grid"><section className="v3-card"><span className="v32-quality verified">数据准备完成</span><h2>31 个省份与 10 家车企已就绪</h2><button className="v3-primary" disabled={!flow.baselineMetadata} onClick={() => void confirmBaseline()} type="button"><Icon name="play_arrow" />开始推演</button></section></div>}
  </div>;
}
