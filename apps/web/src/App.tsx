import { useMemo, useState } from "react";

import { EventRail } from "./components/EventRail";
import {
  ActivityIcon,
  BranchIcon,
  ChevronIcon,
  CompareIcon,
  CouncilIcon,
  ShieldIcon,
} from "./components/Icons";
import { MetricChart } from "./components/MetricChart";
import { ProvinceMap } from "./components/ProvinceMap";
import { usePolicyScope, type ProductStage } from "./hooks/usePolicyScope";
import type {
  MechanismContribution,
  ProvinceAction,
  ProvinceProfile,
  ProvinceState,
  RunMode,
} from "./types";

const DEFAULT_OBJECTIVE = "促进战略性新兴产业创新，同时兼顾区域均衡与财政效率。";

const METRICS = [
  ["overall_policy_benefit", "综合政策收益"],
  ["policy_accessibility", "政策可及性"],
  ["innovation_vitality", "创新活力"],
  ["regional_gap", "区域差距"],
] as const;

const INDUSTRY_LABELS: Record<string, string> = {
  ai: "人工智能",
  advanced_manufacturing: "先进制造",
  green_energy: "绿色能源",
};

const PARAMETER_LABELS: Record<string, string> = {
  central_budget_index: "中央支持指数",
  local_match_requirement: "地方配套要求",
  regional_bias: "区域倾斜系数",
  cooperation_incentive: "省际协作激励",
};

const MECHANISM_LABELS: Record<keyof MechanismContribution, string> = {
  policy_match: "政策匹配",
  central_support: "中央支持",
  local_investment: "地方投入",
  cooperation_spillover: "协作溢出",
  geographic_spillover: "地理溢出",
  competition_crowding_out: "竞争挤出",
  fiscal_execution_cost: "执行成本",
};

const STAGES: Array<{ key: ProductStage; label: string; caption: string }> = [
  { key: "directive", label: "中央指令", caption: "生成与审批" },
  { key: "situation", label: "省域推演", caption: "T0 — T3" },
  { key: "intervention", label: "中央干预", caption: "用户审批" },
  { key: "compare", label: "A/B 复盘", caption: "T3 — T5" },
];

function modeLabel(mode: RunMode) {
  return { live: "LIVE 模型", cache: "CACHE 缓存", fake: "FAKE 确定性", fallback: "FALLBACK 降级" }[mode];
}

function format(value: number, digits = 1) {
  return Number(value).toFixed(digits);
}

function signed(value: number) {
  return `${value >= 0 ? "+" : ""}${format(value, 2)}`;
}

function deltaClass(metric: string, value: number) {
  if (Math.abs(value) < 0.005) return "neutral";
  const lowerIsBetter = metric === "regional_gap" || metric === "fiscal_pressure";
  return (value > 0) === lowerIsBetter ? "negative" : "positive";
}

function ProvinceDetail({
  profile,
  state,
  action,
  contribution,
}: {
  profile?: ProvinceProfile;
  state?: ProvinceState;
  action?: ProvinceAction;
  contribution?: MechanismContribution;
}) {
  if (!profile || !state) return <div className="empty-copy">选择省份查看详情。</div>;
  const provinceAction = action;
  return (
    <div className="province-detail">
      <div className="province-title">
        <div>
          <span className={`quality-tag ${profile.data_quality}`}>{profile.data_quality}</span>
          <h2>{profile.name}</h2>
        </div>
        <div className="score-orb"><strong>{format(state.policy_benefit_index)}</strong><span>收益指数</span></div>
      </div>
      <div className="mini-metrics">
        <div><span>可及性</span><strong>{format(state.policy_accessibility)}</strong></div>
        <div><span>创新</span><strong>{format(state.innovation_index)}</strong></div>
        <div><span>财政压力</span><strong>{format(state.fiscal_pressure)}</strong></div>
      </div>
      {provinceAction ? (
        <div className="strategy-card">
          <div className="card-kicker"><span>模型策略</span><em>{provinceAction.run_mode}</em></div>
          <p>{provinceAction.public_summary}</p>
          <div className="chips">
            <span>{provinceAction.stance}</span>
            <span>强度 {format(provinceAction.implementation_intensity * 100, 0)}</span>
            <span>{provinceAction.interaction_strategy}</span>
          </div>
        </div>
      ) : <p className="empty-copy compact">运行推演后显示该省策略。</p>}
      {contribution && (
        <div className="mechanism-block">
          <div className="card-kicker"><span>环境计算 · 机制贡献</span></div>
          {(Object.keys(MECHANISM_LABELS) as Array<keyof MechanismContribution>).map((key) => {
            const value = contribution[key];
            return (
            <div className="mechanism-row" key={key}>
              <span>{MECHANISM_LABELS[key]}</span>
              <i><b style={{ width: `${Math.min(Math.abs(value) * 18, 100)}%` }} /></i>
              <strong className={key.includes("cost") || key.includes("crowding") ? "negative" : ""}>
                {signed(key.includes("cost") || key.includes("crowding") ? -value : value)}
              </strong>
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function App() {
  const flow = usePolicyScope();
  const [objective, setObjective] = useState(DEFAULT_OBJECTIVE);
  const [selectedCode, setSelectedCode] = useState("44");
  const runMode: RunMode = flow.configuredRunMode;

  const selectedProfile = flow.profiles.find((item) => item.province_code === selectedCode);
  const selectedState = flow.world?.provinces[selectedCode];
  const selectedAction = flow.world?.actions[selectedCode];
  const selectedContribution = flow.world?.contributions[selectedCode];
  const proposal = flow.world?.intervention_proposals[0];
  const verifiedCount = flow.profiles.filter((item) => item.data_quality === "verified").length;

  const completedStage = useMemo(() => {
    if (flow.comparison) return 3;
    if (flow.intervention) return 2;
    if (flow.world?.phase === "T3") return 1;
    if (flow.world?.directive.approval_status === "approved") return 0;
    return -1;
  }, [flow.comparison, flow.intervention, flow.world]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><CouncilIcon /></span>
          <div><strong>PolicyScope</strong><span>省域政策多智能体推演平台</span></div>
        </div>
        <div className="topbar-meta">
          <span className="system-ready"><i /> SYSTEM READY</span>
          <span>{flow.world ? `EXP ${flow.world.experiment_id.slice(-8).toUpperCase()}` : "NO ACTIVE EXP"}</span>
          <span>{flow.world ? modeLabel(flow.world.run_mode) : modeLabel(runMode)}</span>
        </div>
      </header>

      <div className="disclaimer-bar">
        <ShieldIcon />
        <span>这是机制推演，不是现实预测。所有结果均为内部指数、相对变化与机制贡献，不映射现实 GDP 或就业比例。</span>
        <small>数据口径：{verifiedCount || 3} 省核验 + {31 - (verifiedCount || 3)} 省代理/演示</small>
      </div>

      <nav className="stage-nav" aria-label="实验阶段">
        {STAGES.map((item, index) => (
          <button
            className={`${flow.stage === item.key ? "active" : ""} ${index <= completedStage ? "complete" : ""}`}
            disabled={index > completedStage + 1}
            key={item.key}
            onClick={() => flow.setStage(item.key)}
          >
            <span>{index + 1}</span><div><strong>{item.label}</strong><small>{item.caption}</small></div>
          </button>
        ))}
      </nav>

      {flow.error && <div className="error-banner"><strong>操作未完成</strong><span>{flow.error}</span></div>}
      {flow.busyLabel && <div className="busy-overlay"><div className="loader" /><strong>{flow.busyLabel}</strong><span>状态将以原子阶段提交</span></div>}

      <main className="workspace">
        <section className="main-column">
          {flow.stage === "directive" && (
            <div className="directive-layout">
              <section className="panel objective-panel">
                <span className="eyebrow">POLICY OBJECTIVE</span>
                <h1>定义中央政策目标</h1>
                <p>国务院 Agent 将目标转换为结构化、可审批的政策指令，批准前不会启动省级推演。</p>
                <label htmlFor="objective">政策目标</label>
                <textarea id="objective" onChange={(event) => setObjective(event.target.value)} value={objective} />
                <div className="form-row">
                  <label>运行模式</label>
                  <div className="mode-switch">
                    {(["fake", "cache", "live"] as RunMode[]).map((mode) => (
                      <button className={runMode === mode ? "selected" : ""} disabled={runMode !== mode} key={mode}>{mode}</button>
                    ))}
                  </div>
                  <small className="mode-help">由后端 `POLICYSCOPE_RUN_MODE` 配置，实验中不可静默切换。</small>
                </div>
                <button className="primary-action" disabled={Boolean(flow.busyLabel) || objective.trim().length < 3} onClick={() => void flow.createDraft(objective, runMode)}>
                  <CouncilIcon /> 生成中央政策草案 <ChevronIcon />
                </button>
              </section>

              <section className="panel directive-card">
                <div className="panel-heading"><div><span className="eyebrow">STATE COUNCIL AGENT</span><h3>中央政策指令</h3></div><span className={`status-pill ${flow.world ? "pending" : "idle"}`}>{flow.world ? "待用户审批" : "等待生成"}</span></div>
                {flow.world ? (
                  <>
                    <div className="agent-message"><span className="agent-avatar"><CouncilIcon /></span><p>{flow.world.directive.public_summary}</p></div>
                    <div className="policy-grid">
                      <div><span>中央支持指数</span><strong>{format(flow.world.policy.central_budget_index, 0)}</strong></div>
                      <div><span>地方配套要求</span><strong>{format(flow.world.policy.local_match_requirement * 100, 0)}</strong><small>%</small></div>
                      <div><span>区域倾斜系数</span><strong>{format(flow.world.policy.regional_bias, 2)}</strong></div>
                      <div><span>省际协作激励</span><strong>{format(flow.world.policy.cooperation_incentive, 2)}</strong></div>
                    </div>
                    <div className="policy-section"><span>优先产业</span><div className="chips">{flow.world.policy.priority_industries.map((industry) => <b key={industry}>{INDUSTRY_LABELS[industry] ?? industry}</b>)}</div></div>
                    <div className="policy-section"><span>硬约束</span>{flow.world.directive.hard_constraints.map((item) => <p className="constraint" key={item}><ShieldIcon />{item}</p>)}</div>
                    <div className="approval-box"><div><strong>人工审批门禁</strong><span>批准后，31 个省级 Agent 才能读取中央指令。</span></div><button className="approve-button" onClick={() => void flow.approveDirective()}>批准并进入推演</button></div>
                  </>
                ) : <div className="empty-state"><CouncilIcon /><strong>尚无政策草案</strong><p>在左侧输入目标后，由国务院 Agent 生成。</p></div>}
              </section>
            </div>
          )}

          {flow.stage === "situation" && flow.world && (
            <>
              <section className="metric-strip">
                {METRICS.map(([key, label]) => <div className="metric-card" key={key}><span>{label}</span><strong>{format(flow.world!.national_metrics[key])}</strong><small>INDEX / 100</small></div>)}
                <button className="run-button" disabled={flow.world.phase === "T3"} onClick={() => void flow.runToT3()}><ActivityIcon />{flow.world.phase === "T3" ? "T3 已完成" : "运行至 T3"}</button>
              </section>
              <section className="situation-grid">
                <div className="panel map-panel">
                  <div className="panel-heading"><div><span className="eyebrow">NATIONAL SITUATION</span><h3>31 省政策响应态势</h3></div><div className="phase-chip"><i />{flow.world.phase}</div></div>
                  <ProvinceMap profiles={flow.profiles} states={flow.world.provinces} selectedCode={selectedCode} onSelect={setSelectedCode} />
                </div>
                <div className="panel province-panel">
                  <ProvinceDetail action={selectedAction} contribution={selectedContribution} profile={selectedProfile} state={selectedState} />
                </div>
              </section>
              {flow.world.phase === "T3" && proposal && (
                <button className="next-stage" onClick={() => flow.setStage("intervention")}><span><BranchIcon /><div><strong>国务院 Agent 已提出干预建议</strong><small>进入 T3 干预审批，创建可审计 Treatment 分支</small></div></span><ChevronIcon /></button>
              )}
            </>
          )}

          {flow.stage === "intervention" && flow.world && (
            <div className="intervention-layout">
              <section className="panel proposal-card">
                <div className="panel-heading"><div><span className="eyebrow">T3 POLICY REVIEW</span><h1>中央干预建议</h1></div><span className={`status-pill ${flow.intervention ? "approved" : "pending"}`}>{flow.intervention ? "用户已批准" : "待用户审批"}</span></div>
                {proposal ? <>
                  <div className="agent-message prominent"><span className="agent-avatar"><CouncilIcon /></span><div><strong>国务院 Agent 研判</strong><p>{proposal.public_summary}</p></div></div>
                  <div className="change-list">
                    {Object.entries(proposal.parameter_changes).map(([key, change]) => <div className="change-row" key={key}><span>{PARAMETER_LABELS[key] ?? key}</span><strong>{format(change.from_value, 2)}</strong><i>→</i><strong className="new-value">{format(change.to_value, 2)}</strong></div>)}
                  </div>
                  <div className="proposal-columns">
                    <div><span className="section-label">预期方向 · 待验证</span>{Object.entries(proposal.expected_directions).map(([key, value]) => <p key={key}><i className="direction-dot" />{key}：{value}</p>)}</div>
                    <div><span className="section-label">可能权衡</span>{proposal.tradeoffs.map((item) => <p key={item}><i className="tradeoff-dot" />{item}</p>)}</div>
                  </div>
                  <div className="approval-box intervention-approval"><div><strong>审批只创建 Treatment</strong><span>Control 保持原政策；两者从同一个不可变 T3 检查点继续。</span></div>{flow.intervention ? <span className="approved-mark"><ShieldIcon /> 已批准</span> : <button className="approve-button" onClick={() => void flow.approveProposal(proposal.proposal_id)}>批准此干预</button>}</div>
                </> : <div className="empty-state"><BranchIcon /><strong>尚无干预建议</strong><p>请先完成 T3 推演。</p></div>}
              </section>
              <section className="panel branch-preview">
                <span className="eyebrow">IMMUTABLE LINEAGE</span><h3>分支谱系</h3>
                <div className="lineage"><div className="checkpoint-node"><span>T3</span><strong>冻结检查点</strong><small>{flow.branch?.parent_checkpoint_id.slice(-10) ?? "审批后生成"}</small></div><i className="line-split" /><div className="branch-node control"><span>CONTROL</span><strong>原政策延续</strong><small>无干预</small></div><div className="branch-node treatment"><span>TREATMENT</span><strong>审批参数生效</strong><small>{flow.branch?.branch_id.slice(-12) ?? "等待创建"}</small></div></div>
                <div className="lineage-rule"><ShieldIcon /><p><strong>隔离保证</strong>两条分支共享父检查点，但状态对象、事件与后续行动互不污染。</p></div>
                <button className="primary-action full" disabled={!flow.branch} onClick={() => void flow.runComparison()}><CompareIcon />运行双分支至 T5<ChevronIcon /></button>
              </section>
            </div>
          )}

          {flow.stage === "compare" && flow.comparison && (
            <div className="compare-layout">
              <section className="compare-hero"><div><span className="eyebrow">CONTROL / TREATMENT</span><h1>A/B 机制效果对照</h1><p>同一 T3 检查点、独立分支演化。数值为内部指数，不是现实预测。</p></div><span className="checkpoint-badge">CHECKPOINT · {flow.comparison.checkpoint_id.slice(-10)}</span></section>
              <section className="compare-summary">
                {Object.entries(flow.comparison.national_metrics).filter(([key]) => ["overall_policy_benefit", "policy_accessibility", "regional_gap", "fiscal_pressure"].includes(key)).map(([key, metric]) => <div className="delta-card" key={key}><span>{({ overall_policy_benefit: "综合收益", policy_accessibility: "政策可及性", regional_gap: "区域差距", fiscal_pressure: "财政压力" } as Record<string, string>)[key]}</span><strong className={deltaClass(key, metric.delta)}>{signed(metric.delta)}</strong><small>Treatment − Control</small></div>)}
              </section>
              <section className="compare-grid">
                <div className="panel chart-panel"><div className="panel-heading"><div><span className="eyebrow">INDEX COMPARISON</span><h3>全国指标对照</h3></div></div><MetricChart comparison={flow.comparison} /></div>
                <div className="panel top-changes"><div className="panel-heading"><div><span className="eyebrow">PROVINCE DELTAS</span><h3>省域变化排行</h3></div></div><span className="section-label">收益改善 Top 5</span>{[...flow.comparison.province_deltas].sort((a, b) => b.policy_benefit_delta - a.policy_benefit_delta).slice(0, 5).map((item, index) => <div className="rank-row" key={item.province_code}><i>{index + 1}</i><strong>{item.province_name}</strong><span>{signed(item.policy_benefit_delta)}</span></div>)}<span className="section-label pressured">财政压力变化 Top 5</span>{[...flow.comparison.province_deltas].sort((a, b) => b.fiscal_pressure_delta - a.fiscal_pressure_delta).slice(0, 5).map((item, index) => <div className="rank-row pressure" key={item.province_code}><i>{index + 1}</i><strong>{item.province_name}</strong><span>{signed(item.fiscal_pressure_delta)}</span></div>)}</div>
              </section>
              {flow.comparison.central_review && <section className="panel central-review"><div className="review-header"><span className="agent-avatar"><CouncilIcon /></span><div><span className="eyebrow">STATE COUNCIL AGENT · T5</span><h2>中央复盘</h2><p>{flow.comparison.central_review.public_summary}</p></div></div><div className="finding-grid">{flow.comparison.central_review.findings.map((finding) => <article key={finding.title}><strong>{finding.title}</strong><p>{finding.summary}</p>{finding.tradeoff && <small>{finding.tradeoff}</small>}<code>{finding.evidence_refs[0]}</code></article>)}</div><div className="limitations"><ShieldIcon /><span>{flow.comparison.central_review.limitations.join(" · ")}</span></div></section>}
            </div>
          )}

          {flow.stage !== "directive" && !flow.world && <div className="panel empty-state"><CouncilIcon /><strong>请先创建实验</strong></div>}
          {flow.stage === "compare" && !flow.comparison && <div className="panel empty-state"><CompareIcon /><strong>尚无 A/B 结果</strong><p>审批 T3 干预并运行双分支后显示。</p></div>}
        </section>
        <EventRail events={flow.events} />
      </main>

      <footer><span>PolicyScope MVP · 环境公式 {flow.world?.versions.mechanism ?? "industry-policy-env-v1"}</span><span>数据质量在省级详情中显式标注</span></footer>
    </div>
  );
}

export default App;
