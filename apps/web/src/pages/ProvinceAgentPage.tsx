import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { policyScopeApi } from "../api/client";
import { DeepLinkDrawers } from "../components/DeepLinkDrawers";
import { Icon } from "../components/Icon";
import type { ProvinceAgentBranchSnapshot } from "../types";
import {
  ARCHETYPE_LABELS,
  CONSTRAINT_LABELS,
  PERSONA_AXIS_LABELS,
  PERSONA_TYPE_LABELS,
  POSTURE_LABELS,
  PRIORITY_GOAL_LABELS,
  QUALITY_LABELS,
  STRATEGY_LABELS,
  branchLabel,
} from "../utils/display";

const PARTICIPATION_LABELS = {
  participate: "参与",
  conditional: "条件参与",
  wait: "观望",
  decline: "拒绝",
} as const;
const FINANCING_LABELS = {
  self_funded: "自筹",
  direct_subsidy: "直接补贴",
  interest_subsidy: "贴息贷款",
  guarantee_loan: "担保贷款",
  none: "无",
} as const;
const UPGRADE_LABELS = {
  digital: "数字化",
  green: "绿色",
  general: "基础技改",
  none: "无",
} as const;
const INTENT_LABELS = { increase: "提高", decrease: "降低", hold: "保持" } as const;
const ASSESSMENT_LABELS = { effective: "实施有效", mixed: "效果分化", constrained: "实施受限" } as const;
const MECHANISM_LABELS: Record<string, string> = {
  policy_match: "政策匹配",
  direct_subsidy: "直接补贴",
  interest_subsidy: "贷款贴息",
  financing_guarantee: "融资担保",
  sme_preference: "中小企业倾斜",
  regional_support: "区域投放",
  financing_constraint: "融资约束",
  fiscal_cost: "财政成本",
};
const INTENT_PATH_LABELS: Record<string, string> = {
  implementation_intensity: "地方执行强度",
  local_match_ratio: "地方配套比例",
  "instrument_mix.direct_subsidy": "直接补贴权重",
  "instrument_mix.interest_subsidy": "贷款贴息权重",
  "instrument_mix.financing_guarantee": "融资担保权重",
  sme_preference: "中小企业倾斜",
  regional_delivery_focus: "区域投放强度",
  "technology_mix.digital": "数字化权重",
  "technology_mix.green": "绿色改造权重",
  "technology_mix.general": "基础技改权重",
};

function ActionSummary({ snapshot, provinceNames }: { snapshot: ProvinceAgentBranchSnapshot; provinceNames: Record<string, string> }) {
  const action = snapshot.current_action;
  if (!action) return <div className="empty-state compact"><Icon name="hourglass_empty" /><strong>等待省级决策</strong></div>;
  return <>
    <div className="decision-headline">
      <span><small>主要目标</small><strong>{PRIORITY_GOAL_LABELS[action.primary_goal]}</strong></span>
      <span><small>决策姿态</small><strong>{POSTURE_LABELS[action.decision_posture]}</strong></span>
      <span><small>省际策略</small><strong>{STRATEGY_LABELS[action.interprovincial_strategy]}</strong></span>
    </div>
    <p className="decision-summary">{action.public_summary}</p>
    <div className="tool-meter-grid">
      {[
        ["地方执行强度", action.implementation_intensity],
        ["地方配套", action.local_match_ratio],
        ["中小企业倾斜", action.sme_preference],
        ["区域投放", action.regional_delivery_focus],
      ].map(([label, value]) => <div key={String(label)}><span>{label}</span><i><b style={{ width: `${Number(value) * 100}%` }} /></i><strong>{(Number(value) * 100).toFixed(0)}%</strong></div>)}
    </div>
    <div className="strategy-targets"><Icon name="hub" /><span>{action.target_province_codes.length > 0 ? `关联省份：${action.target_province_codes.map((code) => provinceNames[code] ?? code).join("、")}` : "本省独立推进"}</span></div>
  </>;
}

export default function ProvinceAgentPage() {
  const { id, provinceCode } = useParams<{ id: string; provinceCode: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedBranch = searchParams.get("branch") === "treatment" ? "treatment" : "control";
  const detailQuery = useQuery({
    queryKey: ["province-agent-detail-v1", id, provinceCode],
    queryFn: () => policyScopeApi.getProvinceDetail(id!, provinceCode!),
    enabled: Boolean(id && provinceCode),
  });
  const detail = detailQuery.data;
  const snapshot = detail?.branches[requestedBranch];
  const provinceNames = useMemo(() => Object.fromEntries((detail?.top_k_neighbors ?? []).map((item) => [item.province_code, item.province_name])), [detail?.top_k_neighbors]);
  const chooseBranch = (branch: "control" | "treatment") => {
    const next = new URLSearchParams(searchParams);
    next.set("branch", branch);
    setSearchParams(next, { replace: true });
  };
  const openEvidence = (evidenceId: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("evidence", evidenceId);
    setSearchParams(next);
  };

  if (detailQuery.isLoading) return <div className="card page-empty empty-state"><span className="spinner" /><h2>正在加载省级 Agent 详情…</h2></div>;
  if (detailQuery.error || !detail) return <div className="card page-empty empty-state"><Icon name="error" /><h2>省级 Agent 详情不可用</h2><p>{detailQuery.error instanceof Error ? detailQuery.error.message : "请确认省级代码与推演编号。"}</p><button className="primary-button" onClick={() => navigate(`/experiments/${id}/live`)} type="button">返回全国推演</button></div>;

  return <div className="province-agent-page page-stack">
    <header className="province-hero">
      <button className="back-link" onClick={() => navigate(`/experiments/${id}/live`)} type="button"><Icon name="arrow_back" />31 省决策全景</button>
      <div className="province-title-row">
        <div className="province-mark"><Icon name="account_balance" /></div>
        <div><span className="eyebrow">省级 Agent · 本次实验决策画像</span><h1>{detail.profile.name}</h1><p>{detail.persona.public_summary}</p></div>
        <div className="province-status"><span className={`quality-pill ${detail.persona.data_quality}`}>{QUALITY_LABELS[detail.persona.data_quality]}</span><strong>{PERSONA_TYPE_LABELS[detail.persona.primary_type]}</strong><small>{detail.persona.secondary_type ? `辅助类型：${PERSONA_TYPE_LABELS[detail.persona.secondary_type]}` : "单一主类型"}</small></div>
      </div>
      <div className="branch-switch" role="group" aria-label="分支选择">
        <button className={requestedBranch === "control" ? "active" : ""} onClick={() => chooseBranch("control")} type="button">原始方案</button>
        <button className={requestedBranch === "treatment" ? "active" : ""} onClick={() => chooseBranch("treatment")} type="button">干预方案{!detail.branches.treatment && "（未创建）"}</button>
      </div>
    </header>

    {!snapshot ? <section className="card missing-branch-state"><Icon name="call_split" /><div><h2>未创建干预方案</h2><p>当前推演尚未完成 T3 干预审批，不会生成或伪造分支数据。</p></div><button onClick={() => chooseBranch("control")} type="button">查看原始方案</button></section> : <>
      <div className="province-primary-grid">
        <section className="card persona-card">
          <div className="card-heading"><div><span className="source-label environment">规则生成</span><h2>实验决策画像</h2></div><span className="phase-badge">T0 冻结</span></div>
          <div className="persona-axis-list">{Object.entries(detail.persona.axes).map(([axis, value]) => <div key={axis}><span>{PERSONA_AXIS_LABELS[axis as keyof typeof PERSONA_AXIS_LABELS]}</span><i><b style={{ width: `${value * 100}%` }} /></i><strong>{(value * 100).toFixed(0)}</strong></div>)}</div>
          <div className="persona-factors"><div><small>优先目标</small>{detail.persona.priority_goals.map((goal) => <span key={goal}>{PRIORITY_GOAL_LABELS[goal]}</span>)}</div><div><small>关键约束</small>{detail.persona.key_constraints.map((constraint) => <span className="constraint" key={constraint}>{CONSTRAINT_LABELS[constraint]}</span>)}</div></div>
          <p className="card-footnote">画像由当次 Profile 与省际网络确定性计算，不代表现实政府立场。</p>
        </section>
        <section className="card action-card">
          <div className="card-heading"><div><span className="source-label model">省级 Agent</span><h2>{branchLabel(snapshot.branch_id)}·当前地方决策</h2></div><span className="phase-badge">{snapshot.phase}</span></div>
          <ActionSummary provinceNames={provinceNames} snapshot={snapshot} />
          <div className="target-groups"><small>重点覆盖企业</small>{snapshot.current_action?.target_enterprise_groups.map((group) => <span key={group}>{ARCHETYPE_LABELS[group]}</span>)}</div>
        </section>
        <section className="card feedback-card">
          <div className="card-heading"><div><span className="source-label model">T3 地方复盘</span><h2>调整意向与中央支持请求</h2></div></div>
          {snapshot.feedback ? <><div className="feedback-summary"><strong>{ASSESSMENT_LABELS[snapshot.feedback.strategy_assessment]}</strong><span>中央支持强度 {(snapshot.feedback.requested_central_support * 100).toFixed(0)}%</span><p>{snapshot.feedback.public_summary}</p></div><div className="intent-list">{snapshot.feedback.adjustment_intents.length > 0 ? snapshot.feedback.adjustment_intents.map((intent) => <div key={intent.path}><Icon name={intent.direction === "increase" ? "arrow_upward" : intent.direction === "decrease" ? "arrow_downward" : "remove"} /><span>{INTENT_PATH_LABELS[intent.path] ?? intent.path}</span><strong>{INTENT_LABELS[intent.direction]}</strong></div>) : <p>本轮无需调整地方工具。</p>}</div></> : <div className="empty-state compact"><Icon name="hourglass_empty" /><strong>等待 T3 地方复盘</strong></div>}
        </section>
      </div>

      <section className="card lineage-card">
        <div className="card-heading"><div><span className="eyebrow">行动谱系</span><h2>地方决策时间线</h2></div><span>{snapshot.action_lineage.length} 条行动记录</span></div>
        <div className="action-lineage">{snapshot.action_lineage.map((action, index) => <article key={action.action_id}><span>{action.phase}</span><div><strong>{PRIORITY_GOAL_LABELS[action.primary_goal]}·{POSTURE_LABELS[action.decision_posture]}</strong><p>{action.public_summary}</p><small>{index === 0 ? "首轮地方决策" : `承接 ${action.previous_action_id}`}</small></div></article>)}</div>
      </section>

      <section className="card enterprise-evidence-card">
        <div className="card-heading"><div><span className="source-label environment">企业反馈证据</span><h2>六类企业群体响应</h2></div><span>{snapshot.enterprise_groups.length}/6 群体</span></div>
        <div className="enterprise-card-grid">{snapshot.enterprise_groups.map(({ profile, state, action, contribution }) => <article className="enterprise-card" key={profile.enterprise_id}><header><Icon name={profile.archetype.includes("sme") ? "factory" : "domain"} /><div><strong>{ARCHETYPE_LABELS[profile.archetype]}</strong><span className={`quality-pill ${profile.data_quality}`}>{QUALITY_LABELS[profile.data_quality]}</span></div></header>{action ? <><div className={`participation ${action.participation}`}>{PARTICIPATION_LABELS[action.participation]}</div><dl><div><dt>技改方向</dt><dd>{UPGRADE_LABELS[action.upgrade_type]}</dd></div><div><dt>融资选择</dt><dd>{FINANCING_LABELS[action.financing_choice]}</dd></div><div><dt>投入强度</dt><dd>{(action.investment_intensity * 100).toFixed(0)} / 100</dd></div></dl><p>{action.public_summary}</p>{contribution && <small>机制净贡献 {Object.entries(contribution).filter(([key, value]) => key !== "schema_version" && typeof value === "number").reduce((sum, [, value]) => sum + Number(value), 0).toFixed(2)} 指数点</small>}</> : <div className="enterprise-pending"><Icon name="hourglass_empty" />等待企业响应</div>}{state && <div className="enterprise-state-line"><span>更新意愿</span><i><b style={{ width: `${state.renewal_willingness}%` }} /></i><strong>{state.renewal_willingness.toFixed(0)}</strong></div>}</article>)}</div>
      </section>

      <div className="province-bottom-grid">
        <section className="card mechanism-card"><div className="card-heading"><div><span className="source-label environment">环境计算</span><h2>机制贡献汇总</h2></div><small>单位：指数点</small></div><div className="mechanism-list">{Object.entries(snapshot.mechanism_summary).map(([key, value]) => <div key={key}><span>{MECHANISM_LABELS[key] ?? key}</span><i className={value < 0 ? "negative" : "positive"}><b style={{ width: `${Math.min(100, Math.abs(value) * 8)}%` }} /></i><strong>{value > 0 ? "+" : ""}{value.toFixed(2)}</strong></div>)}</div></section>
        <section className="card neighbors-card"><div className="card-heading"><div><span className="source-label environment">省际网络</span><h2>Top-K 关联省份</h2></div></div><div className="neighbor-list">{detail.top_k_neighbors.map((neighbor) => <button key={neighbor.province_code} onClick={() => navigate(`/experiments/${id}/provinces/${neighbor.province_code}?branch=${requestedBranch}`)} type="button"><span>{neighbor.province_name}</span><strong>关联权重 {(neighbor.weight * 100).toFixed(0)}</strong><Icon name="arrow_forward" /></button>)}</div><div className="evidence-actions">{snapshot.evidence_refs.slice(0, 4).map((ref) => <button key={ref} onClick={() => openEvidence(ref)} type="button"><Icon name="fact_check" />{ref}</button>)}</div></section>
      </div>
    </>}
    <DeepLinkDrawers />
  </div>;
}
