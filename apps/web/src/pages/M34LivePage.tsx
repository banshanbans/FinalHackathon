import { Link, useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useM34 } from "../context/M34Context";
import type { MacroTick } from "../m34Types";

const TICKS: MacroTick[] = ["Q1", "Q2", "Q3", "Q4"];
const METRICS = [
  ["regional_development_gap", "区域发展差距"],
  ["central_fiscal_burden", "中央财政负担"],
  ["local_fiscal_pressure", "地方财政压力"],
  ["nev_demand", "新能源汽车需求"],
  ["new_investment_concentration", "新增投资集中度"],
  ["industrial_agglomeration", "产业集聚度"],
] as const;

export default function M34LivePage() {
  const flow = useM34();
  const navigate = useNavigate();
  if (!flow.world) return <div className="v3-empty-page"><h2>{flow.busyLabel ?? "正在恢复季度实验…"}</h2></div>;
  const world = flow.world;
  const control = world.branches.control;
  const treatment = world.branches.treatment;
  const completed = control?.completed_ticks ?? [];
  const nextTick = TICKS.find((tick) => !completed.includes(tick)) ?? null;
  const run = async () => {
    if (!nextTick) return;
    const next = await flow.run(nextTick);
    if (next.status === "completed") navigate(`/experiments/${next.experiment_id}/compare`);
  };
  return <div className="v32-page"><header className="v32-heading"><div><span className="v32-eyebrow">M34 年度推演</span><h1>{nextTick ? `${nextTick} 待运行` : "Q4 年度结果已冻结"}</h1></div><div>{nextTick ? <button className="v3-primary" disabled={Boolean(flow.busyLabel)} onClick={() => void run()} type="button"><Icon name="play_arrow" />{completed.length ? `运行下一季度 ${nextTick}` : "运行 Q1"}</button> : <Link className="v3-primary" to={`/experiments/${world.experiment_id}/compare`}>查看年度比较</Link>}</div></header><section className="v3-flow-strip">{TICKS.map((tick) => <div className={completed.includes(tick) ? "done" : tick === nextTick ? "active" : ""} key={tick}><b>{tick}</b><span>{completed.includes(tick) ? "已冻结" : tick === nextTick ? "待运行" : "未到达"}</span></div>)}</section><div className="v32-design-grid"><section className="v3-card"><span className="v32-eyebrow">原始方案</span><h2>{completed.at(-1) ?? "同源基线"}</h2><div className="v32-kpi-grid">{METRICS.map(([key, label]) => <div key={key}><span>{label}</span><b>{control?.national_metrics[key].toFixed(2) ?? "—"}</b></div>)}</div></section><section className="v3-card"><span className="v32-eyebrow">干预方案</span><h2>{completed.at(-1) ?? "同源基线"}</h2><div className="v32-kpi-grid">{METRICS.map(([key, label]) => <div key={key}><span>{label}</span><b>{treatment?.national_metrics[key].toFixed(2) ?? "—"}</b></div>)}</div></section></div><section className="v3-card"><header className="v32-heading"><div><span className="v32-eyebrow">互动市场</span><h2>{flow.market?.messages.length ?? 0} 条消息 · {flow.market?.settled_count ?? 0} 条已结算</h2></div></header><div className="v32-event-stream">{flow.market?.messages.slice(-20).reverse().map((message) => <article key={message.message_id}><b>{message.branch_id === "control" ? "原始" : "干预"} · {message.tick} / {message.wave}</b><span>{message.sender_id} → {message.recipient_ids.join(" / ")}</span><p>{message.public_summary}</p></article>)}</div><p>模拟季度与互动顺序，不代表现实响应日期。Fake 运行的 fallback 计数：{flow.market?.fallback_count ?? 0}。</p></section>{flow.error ? <p className="v3-error">{flow.error}</p> : null}</div>;
}
