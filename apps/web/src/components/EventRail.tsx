import { useState } from "react";

import { EVENT_LABELS } from "../events";
import type { SimulationEvent } from "../types";
import { branchLabel } from "../utils/display";

export function EventRail({ events }: { events: SimulationEvent[] }) {
  const [mode, setMode] = useState<"province" | "all">("province");
  const ordered = mode === "province"
    ? events.filter((event) => event.type.startsWith("province."))
    : events;
  const visible = ordered.slice(-12).reverse();
  return (
    <aside className="event-rail panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">审计事件</span>
          <h3>实时执行记录</h3>
        </div>
        <div className="event-mode" role="group" aria-label="事件类型">
          <button className={mode === "province" ? "active" : ""} onClick={() => setMode("province")} type="button">省级决策</button>
          <button className={mode === "all" ? "active" : ""} onClick={() => setMode("all")} type="button">全部</button>
        </div>
      </div>
      <div className="event-list">
        {visible.length === 0 ? (
          <p className="empty-copy">{mode === "province" ? "省级决策将按事件 ID 顺序更新。" : "运行事件将在此实时更新。"}</p>
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
