import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { v32Api } from "../api/v32Client";
import { Icon } from "../components/Icon";
import { useV32 } from "../context/V32Context";
import { productLabel } from "../productLabels";
import type { ProvinceActionV5, ProvinceDetailV32 } from "../v32Types";

function Mix({ action }: { action: ProvinceActionV5 | null }) {
  if (!action) return <div className="v3-empty">等待方案生成。</div>;
  return <div className="v32-mix"><div><span>消费端</span><b style={{ width: `${action.subsidy_mix.consumer * 100}%` }} /><strong>{(action.subsidy_mix.consumer * 100).toFixed(1)}%</strong></div><div><span>固定成本</span><b style={{ width: `${action.subsidy_mix.fixed_cost * 100}%` }} /><strong>{(action.subsidy_mix.fixed_cost * 100).toFixed(1)}%</strong></div><div><span>可变成本</span><b style={{ width: `${action.subsidy_mix.variable_cost * 100}%` }} /><strong>{(action.subsidy_mix.variable_cost * 100).toFixed(1)}%</strong></div></div>;
}

export default function V32ProvincePage() {
  const { id = "", provinceCode = "" } = useParams();
  const flow = useV32();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const branchKey = params.get("branch") ?? "control";
  const [detail, setDetail] = useState<ProvinceDetailV32 | null>(null);
  useEffect(() => { setDetail(null); void v32Api.province(id, provinceCode).then(setDetail); }, [id, provinceCode, flow.world]);
  if (!detail) return <div className="route-loader"><span className="spinner" /><strong>正在加载省份方案…</strong></div>;
  const branch = detail.branches[branchKey];
  const final = branch.final_action;
  const provinceName = (code: string) => flow.profiles.find((item) => item.province_code === code)?.short_name ?? "相关省份";
  const companyName = (automakerId: string) => flow.automakers.find((item) => item.automaker_id === automakerId)?.display_name ?? "相关车企";
  const coordination = (branch.coordination_records ?? []).map((item) => {
    const counterpart = item.left_province_code === provinceCode ? item.right_province_code : item.left_province_code;
    return <div key={item.coordination_id}><b className={item.status}>{provinceName(counterpart)}</b><strong>{productLabel(item.status)}</strong></div>;
  });
  const competition = (branch.competition_outcomes ?? []).filter((item) => item.loser_province_code === provinceCode).map((item) => <div key={item.outcome_id}><b className="rejected">{provinceName(item.winner_province_code)}</b><strong>资源竞争未获支持</strong></div>);
  const enterprise = (branch.enterprise_matches ?? []).map((item) => <div key={item.match_id}><b className={item.status}>{companyName(item.automaker_id)}</b><strong>{productLabel(item.status)}</strong></div>);
  const counterResponses = (branch.counter_offers ?? []).map((offer) => {
    const response = (branch.counter_offer_responses ?? []).find((item) => item.counter_offer_id === offer.counter_offer_id);
    return <div key={offer.counter_offer_id}><b>{companyName(offer.automaker_id)}</b><strong>{response ? productLabel(response.decision) : "待确认"}</strong></div>;
  });
  return <div className="v32-page"><header className="v32-heading"><div><button className="v32-back" onClick={() => navigate(`/experiments/${id}/participants`)} type="button"><Icon name="arrow_back" />参与主体</button><h1>{detail.profile.short_name}方案表现</h1></div><div className="v32-segment"><button className={branchKey === "control" ? "active" : ""} onClick={() => setParams({ branch: "control" })} type="button">原始方案</button><button className={branchKey === "treatment" ? "active" : ""} onClick={() => setParams({ branch: "treatment" })} type="button">干预方案</button></div></header>
    <div className="v32-province-story v32-province-results">
      <section className="v3-card"><span className="v32-eyebrow">政策配置</span><div className="v32-action-head"><h2>{final ? productLabel(final.primary_policy_focus) : "等待方案生成"}</h2><span>{final ? `支持强度 ${(final.overall_support_intensity * 100).toFixed(1)}` : "—"}</span></div><Mix action={final} /></section>
      <section className="v3-card"><span className="v32-eyebrow">企业互动</span><div className="v32-coordination-records">{enterprise.length ? enterprise : <div className="v3-empty">暂无企业互动结果。</div>}</div></section>
      <section className="v3-card"><span className="v32-eyebrow">竞争与协同</span><div className="v32-coordination-records">{[...coordination, ...competition, ...counterResponses].length ? <>{coordination}{competition}{counterResponses}</> : <div className="v3-empty">暂无竞争或协同结果。</div>}</div></section>
      <section className="v3-card"><span className="v32-eyebrow">推演影响</span>{branch.state ? <div className="v32-outcome-grid"><div><strong>{branch.state.development_index.toFixed(1)}</strong><span>发展指数</span></div><div><strong>{branch.state.demand_index.toFixed(1)}</strong><span>需求指数</span></div><div><strong>{branch.state.industry_activity_index.toFixed(1)}</strong><span>产业活动</span></div><div><strong>{branch.state.fiscal_pressure_index.toFixed(1)}</strong><span>财政压力</span></div></div> : <div className="v3-empty">结果结算后显示影响。</div>}</section>
    </div>
  </div>;
}
