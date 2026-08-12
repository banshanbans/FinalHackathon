import { useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { usePolicyScopeContext } from "../context/PolicyScopeContext";
import { RUN_MODE_LABELS, WORLD_STATUS_LABELS } from "../utils/display";
import { Icon } from "./Icon";

const workspaceTabs = [
  { route: "new", label: "政策设定", phase: "T0", icon: "tune" },
  { route: "live", label: "全国推演", phase: "T1–T3", icon: "monitoring" },
  { route: "provinces/41", label: "省级详情", phase: "省级 Agent", icon: "account_balance" },
  { route: "intervention", label: "干预审批", phase: "T3", icon: "rule" },
  { route: "compare", label: "方案对照", phase: "T4–T5", icon: "difference" },
] as const;

function routeEnabled(route: string, phase?: string, hasWorld = false, directiveApproved = false) {
  if (route === "new") return true;
  if (!hasWorld) return false;
  if (route === "live" || route.startsWith("provinces/")) return directiveApproved;
  if (route === "intervention") return phase === "T3" || phase === "T4" || phase === "T5";
  return phase === "T5";
}

export function AppShell() {
  const flow = usePolicyScopeContext();
  const location = useLocation();
  const navigate = useNavigate();
  const world = flow.world;
  const experimentBase = world ? `/experiments/${world.experiment_id}` : "/experiments/new";

  useEffect(() => window.scrollTo({ left: 0, top: 0, behavior: "auto" }), [location.pathname]);
  useEffect(() => {
    const provinceCode = new URLSearchParams(location.search).get("province");
    const experimentId = location.pathname.match(/^\/experiments\/([^/]+)\//)?.[1];
    if (!provinceCode || !experimentId) return;
    const params = new URLSearchParams(location.search);
    params.delete("province");
    const query = params.toString();
    navigate(`/experiments/${experimentId}/provinces/${provinceCode}${query ? `?${query}` : ""}`, { replace: true });
  }, [location.pathname, location.search, navigate]);

  const openEvidence = () => {
    if (!world) return;
    const params = new URLSearchParams(location.search);
    params.set("evidence", "method");
    navigate(`${location.pathname}?${params.toString()}`);
  };

  const tabTarget = (route: string) => route === "new" ? "/experiments/new" : `${experimentBase}/${route}`;
  const onLivePage = /\/live$/.test(location.pathname);
  const headerAction = onLivePage && world
    ? world.phase === "T3"
      ? <button className="primary-button" onClick={() => navigate(`${experimentBase}/intervention`)} type="button">进入干预审批<Icon name="arrow_forward" /></button>
      : world.phase === "T5"
        ? <button className="primary-button" onClick={() => navigate(`${experimentBase}/compare`)} type="button">查看结算结果<Icon name="arrow_forward" /></button>
        : <button className="primary-button" disabled={Boolean(flow.busyLabel) || world.directive.approval_status !== "approved"} onClick={() => void flow.runToT3()} type="button"><Icon name="play_arrow" />运行至 T3</button>
    : null;

  return (
    <div className="app-shell workspace-shell">
      <aside className="sidebar workspace-sidebar">
        <button className="brand" onClick={() => navigate("/experiments/new")} type="button">
          <span className="brand-symbol"><Icon name="account_tree" /></span>
          <span><strong>PolicyScope <em>V2.1</em></strong><small>政策涟漪 · 政企互动推演台</small></span>
        </button>
        <button className="sidebar-new-button" onClick={() => { flow.resetExperiment(); navigate("/experiments/new"); }} type="button"><Icon name="add" />新建推演</button>
        <div className="sidebar-section-label">当前工作台</div>
        <nav aria-label="主导航">
          {workspaceTabs.filter((item) => item.route !== "provinces/41").map((item) => {
            const enabled = routeEnabled(item.route, world?.phase, Boolean(world), world?.directive.approval_status === "approved");
            return enabled ? <NavLink className={({ isActive }) => isActive ? "active" : ""} key={item.route} to={tabTarget(item.route)}><Icon name={item.icon} /><span><strong>{item.label}</strong><small>{item.phase}</small></span></NavLink> : <span className="nav-disabled" key={item.route}><Icon name={item.icon} /><span><strong>{item.label}</strong><small>{item.phase}</small></span><Icon className="nav-lock" name="lock" /></span>;
          })}
        </nav>
        <div className="sidebar-recent">
          <span>最近访问</span>
          {world ? <button onClick={() => navigate(world.directive.approval_status === "approved" ? `${experimentBase}/live` : "/experiments/new")} type="button"><Icon name="history" /><span><strong>制造业设备更新推演</strong><small>{world.experiment_id.slice(-10)} · {world.phase}</small></span></button> : <p>创建推演后显示最近记录</p>}
        </div>
        <div className="sidebar-bottom">
          <button disabled={!world} onClick={openEvidence} type="button"><Icon name="database" />数据与证据</button>
          <div className="workspace-user"><span>研</span><div><strong>政策统筹人员</strong><small>国务院层面研判席</small></div></div>
        </div>
      </aside>

      <div className="app-main workspace-main">
        <header className="workspace-header">
          <div className="workspace-title">
            <h1>{flow.hydrating ? "正在加载政策推演" : world ? "制造业设备更新政策推演" : "配置制造业设备更新政策"}</h1>
            <div className="workspace-meta">
              {world ? <><span>推演 ID：{world.experiment_id.slice(-10)}</span><span>当前阶段：{world.phase}</span><span className={`state-pill ${world.status}`}>{WORLD_STATUS_LABELS[world.status] ?? world.status}</span><span className={`mode-badge ${world.run_mode}`}><i />{RUN_MODE_LABELS[world.run_mode]}</span><span className={`connection-pill ${flow.connectionState}`}>{flow.connectionState === "connected" ? "实时连接" : flow.connectionState === "reconnecting" ? "正在重连" : "状态已同步"}</span></> : <span>中央目标、政策参数与人工审批</span>}
            </div>
          </div>
          <div className="workspace-header-actions">
            <button className="secondary-button" disabled={!world} onClick={openEvidence} type="button"><Icon name="fact_check" />方法与证据</button>
            {headerAction}
          </div>
        </header>

        <div className="workspace-tabs">
          <nav aria-label="推演流程导航">
            {workspaceTabs.map((item) => {
              const enabled = routeEnabled(item.route, world?.phase, Boolean(world), world?.directive.approval_status === "approved");
              const provinceActive = item.route.startsWith("provinces/") && /\/provinces\//.test(location.pathname);
              return enabled ? <NavLink className={({ isActive }) => isActive || provinceActive ? "active" : ""} key={item.route} to={tabTarget(item.route)}>{item.label}<small>{item.phase}</small></NavLink> : <span className="tab-disabled" key={item.route}>{item.label}<small>{item.phase}</small></span>;
            })}
          </nav>
          {world && <div className="workspace-version">数据 {world.versions.data} · 机制 {world.versions.mechanism} · Seed {world.seed}</div>}
        </div>

        <div className="disclaimer"><Icon name="info" /><span>研判口径：结果为当前数据与机制参数下的模拟指数，用于政策方案比较。</span></div>
        {flow.error && <div className="error-banner"><Icon name="error" /><strong>操作失败</strong><span>{flow.error}</span></div>}
        {flow.busyLabel && <div className="busy-overlay"><span className="spinner" /><strong>{flow.busyLabel}</strong><small>阶段完成后统一提交结果并更新审计记录</small></div>}
        <main className="page-content workspace-content"><Outlet /></main>
      </div>
    </div>
  );
}
