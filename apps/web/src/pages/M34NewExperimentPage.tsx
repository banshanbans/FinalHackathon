import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useM34 } from "../context/M34Context";

export default function M34NewExperimentPage() {
  const flow = useM34();
  const navigate = useNavigate();
  const [text, setText] = useState("比较西部 98%、中部 92%、东部 86% 的中央承担比例与 2025 年政策参考基线，按 Q1–Q4 进行年度同源推演。");
  const submit = async () => {
    const world = await flow.create(text);
    navigate(`/experiments/${world.experiment_id}/setup?step=interpretation`);
  };
  return <div className="v32-page v32-new-page"><header className="v32-heading"><div><span className="v32-eyebrow">M34 年度实验</span><h1>输入待研判的政策文本</h1></div></header><div className="v32-new-grid v32-new-grid-simple"><section className="v3-card v32-policy-input"><label htmlFor="policy-text">政策原文或研判设想</label><textarea id="policy-text" onChange={(event) => setText(event.target.value)} value={text} /><p>实验时间使用 Q1–Q4 与季度内逻辑 Wave，不生成现实响应日期。</p><button className="v3-primary" disabled={text.trim().length < 3 || Boolean(flow.busyLabel)} onClick={() => void submit()} type="button"><Icon name="arrow_forward" />生成中央政策解读</button>{flow.error ? <p className="v3-error">{flow.error}</p> : null}</section></div><section className="v3-flow-strip">{["政策输入", "中央解读", "年度设计", "基线确认", "Q1–Q4", "年度复盘"].map((item, index) => <div key={item}><b>{index + 1}</b><span>{item}</span></div>)}</section></div>;
}
