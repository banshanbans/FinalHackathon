import { useEffect, useState } from "react";

import { v32Api } from "../api/v32Client";
import { useV32 } from "../context/V32Context";
import { productLabel } from "../productLabels";
import type { V32Event } from "../v32Types";

export default function V32MethodsPage() {
  const flow = useV32();
  const world = flow.world;
  const [replay, setReplay] = useState<V32Event[]>([]);
  useEffect(() => { if (world) void v32Api.replay(world.experiment_id).then(setReplay); }, [world]);
  if (!world) return <div className="v3-empty-page"><h2>尚未创建实验</h2></div>;
  const invocations = Object.values(world.branches).flatMap((branch) => branch.agent_invocations);
  const fallbackCount = invocations.filter((item) => item.fallback_used).length;
  const models = [...new Set(invocations.map((item) => item.model))];
  return <div className="v32-page"><header className="v32-heading"><div><span className="v32-eyebrow">方法与数据</span><h1>同源证明、版本、公式与运行记录</h1></div></header>
    <div className="v32-method-grid"><section className="v3-card"><span className="v32-eyebrow">同源证明</span><h2>两分支来自同一不可变基线快照</h2><dl><dt>原始方案父快照</dt><dd>{world.branches.control.parent_checkpoint_id}</dd><dt>干预方案父快照</dt><dd>{world.branches.treatment.parent_checkpoint_id}</dd><dt>基线哈希</dt><dd>{world.baseline?.state_hash}</dd><dt>固定 seed</dt><dd>{world.seed}</dd></dl></section>
      <section className="v3-card"><span className="v32-eyebrow">数据来源</span><h2>事实、代理特征与情景假设</h2>{world.baseline?.quality_counts.map((item) => <div className="v32-quality-row" key={item.quality}><strong>{productLabel(item.quality)}</strong><span>{item.field_count} 项记录</span><p>{item.explanation}</p></div>)}<p>{world.baseline?.missing_value_policy}</p><small>数据版本：{world.baseline?.data_version ?? "尚未确认"}</small></section>
      <section className="v3-card"><span className="v32-eyebrow">版本矩阵</span><dl>{Object.entries(world.versions).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}<div><dt>当前 World</dt><dd>{world.schema_version}</dd></div><div><dt>当前分支</dt><dd>branch-v6</dd></div></dl></section>
      <section className="v3-card"><span className="v32-eyebrow">资源与环境公式</span><div className="v32-formula"><code>省级发展指数 = 0.50 × 需求指数 + 0.50 × 产业活动指数</code><code>ΔGap = Gap干预方案 − Gap原始方案</code><code>省级工具投入 = 总体支持强度 × 工具份额 ≤ 单项上限</code><code>车企全国投入总量 ≤ 全国市场资源包</code><p>投资集中度、产业集聚度和合作贡献均由确定性环境结算，Agent 不直接生成指标。</p></div></section>
      <section className="v3-card"><span className="v32-eyebrow">Agent 调用与缓存口径</span><h2>{invocations.length || 226} 次结构化主体调用</h2><dl><div><dt>模型或回放来源</dt><dd>{models.join("、") || world.versions.province_model || "尚未运行"}</dd></div><div><dt>显式 fallback</dt><dd>{fallbackCount} 次</dd></div><div><dt>输入与输出哈希</dt><dd>逐次写入 Audit；主页不暴露技术字段</dd></div><div><dt>现场模式</dt><dd>优先回放独立 M30 验收缓存；缺失时明示规则接管</dd></div></dl></section>
    </div>
    <section className="v3-card"><span className="v32-eyebrow">Replay 事实流</span><div className="v32-replay-table">{replay.map((event) => <div key={event.event_id}><time>{new Date(event.timestamp).toLocaleTimeString("zh-CN")}</time><strong>{event.type}</strong><span>{event.round ? productLabel(event.round) : "旅程事件"}</span><code>{event.event_id}</code></div>)}</div></section>
  </div>;
}
