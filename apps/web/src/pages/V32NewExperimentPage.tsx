import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useV32 } from "../context/V32Context";

const examples = [
  { label: "区域协调", text: "以缩小新能源汽车区域发展差距为目标，西部中央承担 95%，中部 90%，东部 85%，兼顾地方财政压力、消费激活和产业布局。" },
  { label: "压力测试", text: "比较三档中央承担比例调整时的新能源汽车需求和产业布局，并加入智能网联能力升级情景。" },
  { label: "事件反事实", text: "保持西部 95%、中部 90%、东部 85% 的政策不变，检验 L3 企业责任提高对省级支持和车企模拟行动的影响。" },
] as const;

export default function V32NewExperimentPage() {
  const flow = useV32();
  const navigate = useNavigate();
  const [text, setText] = useState<string>(examples[0].text);
  const submit = async () => {
    const next = await flow.create(text);
    navigate(`/experiments/${next.experiment_id}/setup?step=interpretation`);
  };
  return <div className="v32-page v32-new-page">
    <header className="v32-heading"><div><span className="v32-eyebrow">新建实验</span><h1>输入待研判的政策文本</h1></div></header>
    <div className="v32-new-grid v32-new-grid-simple">
      <section className="v3-card v32-policy-input">
        <label htmlFor="policy-text">政策原文或研判设想</label>
        <textarea id="policy-text" onChange={(event) => setText(event.target.value)} value={text} />
        <div className="v32-example-row">{examples.map((item) => <button key={item.label} onClick={() => setText(item.text)} type="button">{item.label}</button>)}</div>
        <button className="v3-primary" disabled={text.trim().length < 3 || Boolean(flow.busyLabel)} onClick={() => void submit()} type="button"><Icon name="arrow_forward" />生成政策解读</button>
      </section>
    </div>
    <section className="v3-flow-strip">{["政策输入", "中央解读", "实验设计", "基线确认", "推演运行", "结果复盘"].map((item, index) => <div key={item}><b>{index + 1}</b><span>{item}</span></div>)}</section>
  </div>;
}
