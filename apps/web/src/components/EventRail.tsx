import type { SimulationEvent } from "../types";

const EVENT_LABELS: Record<string, string> = {
  "experiment.started": "实验已创建",
  "central.directive.completed": "中央草案已生成",
  "central.directive.approved": "中央指令已审批",
  "phase.started": "阶段开始",
  "phase.completed": "阶段完成",
  "agent.decision.started": "省级 Agent 开始决策",
  "agent.decision.completed": "省级策略已生成",
  "agent.decision.fallback": "省级策略已降级",
  "enterprise.batch.started": "企业批量决策开始",
  "enterprise.batch.completed": "六类企业响应完成",
  "enterprise.batch.fallback": "整省企业响应已降级",
  "enterprise.aggregate.updated": "企业群体指标已聚合",
  "province.feedback.completed": "地方反馈已形成",
  "environment.updated": "环境完成结算",
  "world_state.updated": "权威状态已提交",
  "central.intervention.proposed": "国务院提出干预建议",
  "central.intervention.approved": "干预已获用户批准",
  "central.intervention.rejected": "用户保留原始方案",
  "checkpoint.created": "T3 检查点已冻结",
  "branch.created": "Treatment 分支已创建",
  "experiment.completed": "A/B 对照与复盘已完成",
};

export function EventRail({ events }: { events: SimulationEvent[] }) {
  const visible = events.slice(-12).reverse();
  return (
    <aside className="event-rail panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">AUDIT STREAM</span>
          <h3>实时行动流</h3>
        </div>
        <span className="live-dot"><i /> LIVE</span>
      </div>
      <div className="event-list">
        {visible.length === 0 ? (
          <p className="empty-copy">实验创建后，策略、环境与审批事件会显示在这里。</p>
        ) : visible.map((event) => (
          <div className="event-item" key={event.event_id}>
            <i className={event.type.includes("fallback") ? "event-pin warning" : "event-pin"} />
            <div>
              <strong>{EVENT_LABELS[event.type] ?? event.type}</strong>
              <span>{event.phase} · {event.branch_id}</span>
              {typeof event.payload.summary === "string" && <p>{event.payload.summary}</p>}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
