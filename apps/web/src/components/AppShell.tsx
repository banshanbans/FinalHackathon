import { useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { usePolicyScopeContext } from "../context/PolicyScopeContext";
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
        <div className="sidebar-section-label">国务院政策推演台</div>
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
          <button onClick={() => { flow.resetExperiment(); navigate("/experiments/new"); }} type="button"><Icon name="restart_alt" />新建实验</button>
          <button disabled={!flow.world} onClick={openEvidence} type="button"><Icon name="database" />证据与方法</button>
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="breadcrumb"><span>制造业设备更新</span><Icon name="chevron_right" /><strong>{flow.world?.experiment_id ? `实验 ${flow.world.experiment_id.slice(-8)}` : "新实验"}</strong></div>
          <div className="topbar-actions">
            {flow.world && <span className={`mode-badge ${flow.world.run_mode}`}><i />{flow.world.run_mode.toUpperCase()}</span>}
            <span className="scenario-badge">情景实验</span>
            <button aria-label="打开证据抽屉" disabled={!flow.world} onClick={openEvidence} type="button"><Icon name="fact_check" /></button>
          </div>
        </header>
        <div className="disclaimer">
          <Icon name="info" />
          <span>这是在当前数据、参数与机制假设下的情景实验，不构成现实政策预测或决策建议。</span>
        </div>
        {flow.error && <div className="error-banner"><Icon name="error" /><strong>操作未完成</strong><span>{flow.error}</span></div>}
        {flow.busyLabel && <div className="busy-overlay"><span className="spinner" /><strong>{flow.busyLabel}</strong><small>阶段结果将原子提交并写入 Replay</small></div>}
        <main className="page-content"><Outlet /></main>
      </div>
    </div>
  );
}
