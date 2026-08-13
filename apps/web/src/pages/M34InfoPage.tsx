import { useParams } from "react-router-dom";

import { useM34 } from "../context/M34Context";

export default function M34InfoPage({ kind }: { kind: "participants" | "methods" | "province" }) {
  const flow = useM34();
  const { provinceCode } = useParams();
  if (!flow.world) return <div className="v3-empty-page"><h2>正在恢复实验…</h2></div>;
  return <div className="v32-page"><header className="v32-heading"><div><span className="v32-eyebrow">M34</span><h1>{kind === "participants" ? "31 省与 10 家车企" : kind === "province" ? `省域结果 · ${provinceCode}` : "方法与数据"}</h1></div></header><section className="v3-card"><p>{kind === "methods" ? "时间权威为 Q1–Q4 和 Wave 0–2；最终指标只由确定性环境计算。" : "页面只展示方案、最终行动与结果；追溯字段统一收入方法与数据。"}</p><dl className="method-list"><div><dt>产品版本</dt><dd>v3_2_m34</dd></div><div><dt>世界契约</dt><dd>world-state-v10</dd></div><div><dt>中央调用</dt><dd>{flow.world.central_call_count} / 2</dd></div><div><dt>数据属性</dt><dd>代理数据基线</dd></div></dl></section></div>;
}
