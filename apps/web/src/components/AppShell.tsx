import { useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useM34 } from "../context/M34Context";
import { Icon } from "./Icon";

const items = [
  ["new", "新建实验", "tune"],
  ["live", "实验运行", "map"],
  ["participants", "参与主体", "groups"],
  ["compare", "结果与对比", "difference"],
  ["methods", "方法与数据", "fact_check"],
] as const;

export function AppShell() {
  const flow = useM34();
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    window.scrollTo({ left: 0, top: 0, behavior: "auto" });
  }, [location.pathname]);
  const world = flow.world;
  const base = world ? `/experiments/${world.experiment_id}` : "/experiments";
  const openMethods = () => navigate(world ? `/experiments/${world.experiment_id}/methods` : "/experiments/new");
  return <div className="v3-app">
    <aside className="v3-sidebar">
      <div className="v3-brand"><span>PS</span><div><strong>PolicyScope</strong><small>政策涟漪</small></div></div>
      <nav>{items.map(([route, label, icon]) => <NavLink className={({ isActive }) => isActive ? "active" : ""} key={route} to={route === "new" ? "/experiments/new" : `${base}/${route}`}><Icon name={icon} /><span>{label}</span></NavLink>)}</nav>
    </aside>
    <main className="v3-main">
      <header className="v3-topbar"><div><span className="v3-live-dot" />新能源汽车补贴与产业布局推演</div><div className="v3-top-actions"><span>模拟结果，仅作方案比较</span>{world && <span className="v32-top-status">{world.status === "completed" ? "推演已完成" : "实验进行中"}</span>}<button onClick={openMethods} type="button"><Icon name="fact_check" />方法与数据</button></div></header>
      {flow.busyLabel && <div className="v3-progress"><span className="spinner" />{flow.busyLabel}</div>}
      {flow.error && <div className="v3-error"><Icon name="error" />{flow.error}</div>}
      <div className="v3-content"><Outlet /></div>
    </main>
  </div>;
}
