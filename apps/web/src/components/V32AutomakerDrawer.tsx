import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { v32Api } from "../api/v32Client";
import { useV32 } from "../context/V32Context";
import { productLabel } from "../productLabels";
import type { AutomakerDetailV32 } from "../v32Types";
import { Icon } from "./Icon";

export function V32AutomakerDrawer() {
  const flow = useV32();
  const location = useLocation();
  const navigate = useNavigate();
  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const automakerId = params.get("company");
  const branchKey = params.get("branch") ?? "control";
  const [detail, setDetail] = useState<AutomakerDetailV32 | null>(null);
  useEffect(() => { if (!automakerId || !flow.world) { setDetail(null); return; } void v32Api.automaker(flow.world.experiment_id, automakerId).then(setDetail); }, [automakerId, flow.world]);
  if (!automakerId) return null;
  const close = () => { const next = new URLSearchParams(location.search); next.delete("company"); navigate(`${location.pathname}${next.size ? `?${next}` : ""}`); };
  const branch = detail?.branches[branchKey];
  const final = branch?.final_action;
  const decisionCounts = final?.province_signals.reduce<Record<string, number>>((counts, item) => ({ ...counts, [item.decision]: (counts[item.decision] ?? 0) + 1 }), {}) ?? {};
  const provinceName = (code: string) => flow.profiles.find((item) => item.province_code === code)?.short_name ?? "相关省份";
  return <div className="v32-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><aside className="v32-company-drawer">
    <header><div><span className="v32-quality proxy">模拟基线</span><h2>{detail?.profile.display_name ?? "车企"}</h2></div><button aria-label="关闭" onClick={close} type="button"><Icon name="close" /></button></header>
    {!detail ? <div className="route-loader"><span className="spinner" /></div> : <div className="v32-drawer-content">
      <section><span className="v32-eyebrow">行动概览</span><h3>{final?.primary_commitment ?? "等待行动生成"}</h3><div className="v32-resource-grid"><div><strong>{decisionCounts.expand ?? 0}</strong><span>扩大渠道</span></div><div><strong>{decisionCounts.maintain ?? 0}</strong><span>维持投入</span></div><div><strong>{decisionCounts.reduce ?? 0}</strong><span>收缩投入</span></div></div></section>
      <section><span className="v32-eyebrow">省企合作</span><div className="v32-coordination-records">{branch?.enterprise_matches.length ? branch.enterprise_matches.map((item) => <div key={item.match_id}><b className={item.status}>{provinceName(item.province_code)}</b><strong>{productLabel(item.status)}</strong></div>) : <div className="v3-empty">暂无合作结果。</div>}</div></section>
      <section><span className="v32-eyebrow">产能意向</span><div className="v32-facility-list">{final?.facility_actions.length ? final.facility_actions.map((item) => <div key={item.province_code}><strong>{provinceName(item.province_code)}</strong><span>{productLabel(item.action)}</span></div>) : <div className="v3-empty">暂无产能调整。</div>}</div></section>
    </div>}
  </aside></div>;
}
