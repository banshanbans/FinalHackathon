import { useNavigate } from "react-router-dom";

import { Icon } from "../components/Icon";
import { useV32 } from "../context/V32Context";
import { productLabel } from "../productLabels";

export default function V32ParticipantsPage() {
  const flow = useV32();
  const navigate = useNavigate();
  const world = flow.world;
  if (!world) return <div className="v3-empty-page"><h2>尚未创建实验</h2></div>;
  return <div className="v32-page"><header className="v32-heading"><div><span className="v32-eyebrow">参与主体</span><h1>31 个省份与 10 家车企</h1></div><span className="v32-quality proxy">模拟基线</span></header>
    <section className="v3-card v32-participant-section"><div className="v3-card-title"><Icon name="account_balance" /><div><small>省份</small><h2>省份方案</h2></div></div><div className="v32-province-grid">{flow.profiles.map((item) => { const action = world.branches.control.province_final_actions[item.province_code]; return <button key={item.province_code} onClick={() => navigate(`/experiments/${world.experiment_id}/provinces/${item.province_code}`)} type="button"><strong>{item.short_name}</strong><span>{item.policy_region === "west" ? "西部" : item.policy_region === "central" ? "中部" : "东部"}</span><small>{action ? productLabel(action.primary_policy_focus) : "等待方案生成"}</small></button>; })}</div></section>
    <section className="v3-card v32-participant-section"><div className="v3-card-title"><Icon name="directions_car" /><div><small>车企</small><h2>车企行动</h2></div></div><div className="v32-automaker-grid">{flow.automakers.map((item) => { const action = world.branches.control.automaker_final_actions[item.automaker_id]; return <button key={item.automaker_id} onClick={() => navigate(`${location.pathname}?company=${item.automaker_id}`)} type="button"><span className="v32-company-mark">{item.display_name.slice(0, 1)}</span><span><strong>{item.display_name}</strong><small>{action?.primary_commitment ?? "等待行动生成"}</small></span><Icon name="chevron_right" /></button>; })}</div></section>
  </div>;
}
