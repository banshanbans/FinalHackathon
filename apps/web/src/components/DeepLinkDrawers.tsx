import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { policyScopeApi } from "../api/client";
import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import { Icon } from "./Icon";

export function DeepLinkDrawers() {
  const flow = usePolicyScopeContext(); const location = useLocation(); const navigate = useNavigate();
  const query = new URLSearchParams(location.search); const company = query.get("company"); const evidence = query.get("evidence");
  const companyQuery = useQuery({ queryKey: ["automaker-detail-v1", flow.world?.experiment_id, company], queryFn: () => policyScopeApi.getAutomakerDetail(flow.world!.experiment_id, company!), enabled: Boolean(flow.world && company) });
  const evidenceQuery = useQuery({ queryKey: ["evidence-v3", flow.world?.experiment_id, evidence], queryFn: () => flow.loadEvidence(evidence!), enabled: Boolean(flow.world && evidence) });
  const close = (key: "company" | "evidence") => { const next = new URLSearchParams(location.search); next.delete(key); navigate(`${location.pathname}${next.size ? `?${next}` : ""}`, { replace: true }); };
  if (!company && !evidence) return null;
  return <div className="v3-drawer-layer" onMouseDown={() => close(company ? "company" : "evidence")}>
    <aside className="v3-drawer" onMouseDown={(event) => event.stopPropagation()}>
      <button className="v3-drawer-close" onClick={() => close(company ? "company" : "evidence")} type="button"><Icon name="close" /></button>
      {company && <>{companyQuery.isLoading ? <p>正在加载车企画像…</p> : companyQuery.data ? <><span className="v3-kicker">全国性车企 Agent</span><h2>{companyQuery.data.profile.display_name}</h2><p className="v3-disclaimer">{companyQuery.data.disclaimer}</p><div className="v3-mini-stats"><div><small>销量规模基线</small><strong>{(companyQuery.data.profile.sales_scale_index * 100).toFixed(0)}</strong></div><div><small>资金韧性基线</small><strong>{(companyQuery.data.profile.liquidity_index * 100).toFixed(0)}</strong></div><div><small>产能利用基线</small><strong>{(companyQuery.data.profile.capacity_utilization_index * 100).toFixed(0)}</strong></div></div>{Object.entries(companyQuery.data.actions).map(([branch, action]) => action && <section className="v3-drawer-section" key={branch}><h3>{branch === "control" ? "原始方案" : "干预方案"}</h3><p>{action.summary}</p><strong>31 省投入组合 · {action.facility_actions.length} 项设施动作</strong><ul>{action.facility_actions.map((item) => <li key={item.province_code}>{flow.profiles.find((p) => p.province_code === item.province_code)?.short_name} · {item.action}</li>)}</ul></section>)}</> : <p>车企详情不可用。</p>}</>}
      {evidence && <><span className="v3-kicker">Replay / Audit / Evidence</span><h2>方法与证据</h2><p className="v3-disclaimer">Checkpoint 用于恢复和分支，Replay 用于事件恢复，Audit 用于行为追溯。</p>{evidenceQuery.isLoading ? <p>正在加载…</p> : <pre>{JSON.stringify(evidenceQuery.data ?? { evidence_id: evidence, formula: "nev-policy-env-v1", note: "模拟指数口径" }, null, 2)}</pre>}</>}
    </aside>
  </div>;
}
