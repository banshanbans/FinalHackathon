import { useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import { RUN_MODE_LABELS } from "../utils/display";
import { Icon } from "./Icon";

const navigation = [
  { route: "new", label: "政策设定", icon: "tune", phase: "T0" },
  { route: "live", label: "实时推演", icon: "monitoring", phase: "T1–T3" },
  { route: "intervention", label: "干预审批", icon: "rule", phase: "T3" },
  { route: "compare", label: "方案对照", icon: "difference", phase: "T4–T5" },
] as const;

function routeEnabled(route: (typeof navigation)[number]["route"], phase?: string, hasWorld = false) {
  if (route === "new") return true;
  if (!hasWorld) return false;
  if (route === "live") return true;
  if (route === "intervention") return phase === "T3" || phase === "T4" || phase === "T5";
  return phase === "T5";
}

export function AppShell() {
  const flow = usePolicyScopeContext();
  const location = useLocation();
  const navigate = useNavigate();
  const experimentBase = flow.world ? `/experiments/${flow.world.experiment_id}` : "/experiments/new";
  useEffect(() => {
    window.scrollTo({ left: 0, top: 0, behavior: "auto" });
  }, [location.pathname]);
  useEffect(() => {
    const provinceCode = new URLSearchParams(location.search).get("province");
    const experimentId = location.pathname.match(/^\/experiments\/([^/]+)\//)?.[1];
    if (!provinceCode || !experimentId) return;
    const params = new URLSearchParams(location.search);
    params.delete("province");
    const query = params.toString();
    navigate(
      `/experiments/${experimentId}/provinces/${provinceCode}${query ? `?${query}` : ""}`,
      { replace: true },
    );
  }, [location.pathname, location.search, navigate]);

  const openEvidence = () => {
    if (!flow.world) return;
    const params = new URLSearchParams(location.search);
    params.set("evidence", "method");
    navigate(`${location.pathname}?${params.toString()}`);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={() => navigate("/experiments/new")} type="button">
          <span className="brand-symbol"><Icon name="radar" /></span>
          <span><strong>PolicyScope</strong><small>政策涟漪</small></span>
        </button>
        <div className="sidebar-section-label">中央政策统筹工作台</div>
        <nav aria-label="主导航">
          {navigation.map((item) => {
            const enabled = routeEnabled(item.route, flow.world?.phase, Boolean(flow.world));
            const target = item.route === "new" ? "/experiments/new" : `${experimentBase}/${item.route}`;
            return enabled ? (
              <NavLink className={({ isActive }) => isActive ? "active" : ""} key={item.route} to={target}>
                <Icon name={item.icon} />
                <span><strong>{item.label}</strong><small>{item.phase}</small></span>
              </NavLink>
            ) : (
              <span className="nav-disabled" key={item.route}>
                <Icon name={item.icon} />
                <span><strong>{item.label}</strong><small>{item.phase}</small></span>
                <Icon className="nav-lock" name="lock" />
              </span>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <button onClick={() => { flow.resetExperiment(); navigate("/experiments/new"); }} type="button"><Icon name="restart_alt" />新建推演</button>
          <button disabled={!flow.world} onClick={openEvidence} type="button"><Icon name="database" />数据与审计</button>
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="breadcrumb"><span>制造业设备更新专项</span><Icon name="chevron_right" /><strong>{flow.world?.experiment_id ? `推演 ${flow.world.experiment_id.slice(-8)}` : "新建推演"}</strong></div>
          <div className="topbar-actions">
            {flow.world && <span className={`mode-badge ${flow.world.run_mode}`}><i />{RUN_MODE_LABELS[flow.world.run_mode]}</span>}
            <span className="scenario-badge">设备更新专项</span>
            <button aria-label="打开数据与审计" disabled={!flow.world} onClick={openEvidence} type="button"><Icon name="fact_check" /></button>
          </div>
        </header>
        <div className="disclaimer">
          <Icon name="info" />
          <span>研判口径：结果为当前数据与机制参数下的模拟指数，用于政策方案比较。</span>
        </div>
        {flow.error && <div className="error-banner"><Icon name="error" /><strong>操作失败</strong><span>{flow.error}</span></div>}
        {flow.busyLabel && <div className="busy-overlay"><span className="spinner" /><strong>{flow.busyLabel}</strong><small>阶段完成后统一提交结果并更新审计记录</small></div>}
        <main className="page-content"><Outlet /></main>
      </div>
    </div>
  );
}
