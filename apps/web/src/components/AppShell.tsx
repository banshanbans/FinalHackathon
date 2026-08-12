import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import { DeepLinkDrawers } from "./DeepLinkDrawers";
import { Icon } from "./Icon";

const items = [
  ["new", "政策设定", "tune"], ["live", "全国推演", "map"],
  ["provinces/41", "省级详情", "account_balance"],
  ["intervention", "干预审批", "rule"], ["compare", "方案对照", "difference"],
] as const;

export function AppShell() {
  const flow = usePolicyScopeContext();
  const location = useLocation();
  const navigate = useNavigate();
  const world = flow.world;
  const fallbackProvinceCount = world?.fallback_provinces.length ?? 0;
  const fallbackAutomakerCount = world?.fallback_automakers.length ?? 0;
  const base = world ? `/experiments/${world.experiment_id}` : "/experiments";
  const setEvidence = () => { const q = new URLSearchParams(location.search); q.set("evidence", "method:nev-policy-env-v1"); navigate(`${location.pathname}?${q}`); };
  return <div className="v3-app">
    <aside className="v3-sidebar">
      <div className="v3-brand"><span>PS</span><div><strong>PolicyScope</strong><small>政策涟漪 · V3.0</small></div></div>
      <nav>{items.map(([route, label, icon]) => <NavLink className={({ isActive }) => isActive ? "active" : ""} key={route} to={route === "new" ? "/experiments/new" : `${base}/${route}`}><Icon name={icon} /><span>{label}</span></NavLink>)}</nav>
      <div className="v3-side-note"><Icon name="science" /><p>研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。</p></div>
    </aside>
    <main className="v3-main">
      <header className="v3-topbar"><div><span className="v3-live-dot" />新能源汽车补贴与产业布局推演</div><div className="v3-top-actions"><span>{world?.phase ?? "SETUP"}</span><span>{flow.configuredRunMode.toUpperCase()}</span><button onClick={setEvidence} type="button"><Icon name="fact_check" />方法与证据</button></div></header>
      {flow.busyLabel && <div className="v3-progress"><span className="spinner" />{flow.busyLabel}</div>}
      {flow.error && <div className="v3-error"><Icon name="error" />{flow.error}</div>}
      {flow.connectionStatus === "reconnecting" && <div className="v3-runtime-notice reconnecting"><Icon name="sync_problem" /><strong>事件流正在重连</strong><span>完整状态仍以 WorldState 为准，恢复后会按 event_id 去重。</span></div>}
      {(fallbackProvinceCount > 0 || fallbackAutomakerCount > 0) && <div className="v3-runtime-notice fallback"><Icon name="offline_bolt" /><strong>确定性 Fallback 已接管</strong><span>{fallbackProvinceCount} 个省级主体 · {fallbackAutomakerCount} 家车企；原因与范围已写入 Action、Event、Replay 和 Audit。</span></div>}
      <div className="v3-content"><Outlet /></div>
    </main>
    <DeepLinkDrawers />
  </div>;
}
