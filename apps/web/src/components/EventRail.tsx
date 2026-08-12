import { EVENT_LABELS } from "../events";
import type { SimulationEvent } from "../types";
import { branchLabel } from "../utils/display";

export function EventRail({ events }: { events: SimulationEvent[] }) {
  const visible = events.slice(-12).reverse();
  return (
    <aside className="event-rail panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">审计事件</span>
          <h3>实时执行记录</h3>
        </div>
        <span className="live-dot"><i /> 实时</span>
      </div>
      <div className="event-list">
        {visible.length === 0 ? (
          <p className="empty-copy">运行事件将在此实时更新。</p>
        ) : visible.map((event) => (
          <div className="event-item" key={event.event_id}>
            <i className={event.type.includes("fallback") ? "event-pin warning" : "event-pin"} />
            <div>
              <strong>{EVENT_LABELS[event.type] ?? event.type}</strong>
              <span>{event.phase} · {branchLabel(event.branch_id)}</span>
              {typeof event.payload.summary === "string" && <p>{event.payload.summary}</p>}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
