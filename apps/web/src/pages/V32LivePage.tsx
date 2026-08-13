import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { v32Api } from "../api/v32Client";
import { Icon } from "../components/Icon";
import { ProvinceMap, type ProvinceMapLink } from "../components/ProvinceMap";
import { useV32 } from "../context/V32Context";
import { productLabel } from "../productLabels";
import type { BranchRuntime, SimulationRound, StrategyMarket } from "../v32Types";

const M32_ROUNDS: SimulationRound[] = [
  "province_initial",
  "automaker_initial",
  "province_revision",
  "automaker_negotiation",
  "province_counter_response",
  "automaker_final",
  "environment_settlement",
];

const M31_ROUNDS: SimulationRound[] = [
  "province_initial",
  "automaker_initial",
  "province_revision",
  "automaker_final",
  "environment_settlement",
];

const roundLabels: Record<SimulationRound, string> = {
  province_initial: "省级初始行动",
  automaker_initial: "车企初步 Top-K",
  province_revision: "省级竞争反制与协同",
  automaker_negotiation: "车企报价与反报价",
  province_counter_response: "省级反报价回应",
  automaker_final: "车企最终确认与重配",
  environment_settlement: "环境结算",
};

const layers = {
  support: "地方支持强度",
  consumer: "消费端支持",
  fixed: "固定成本支持",
  variable: "可变成本支持",
  demand: "新能源汽车需求",
  industry: "产业活动",
} as const;

type Layer = keyof typeof layers;
type LedgerFilter = "all" | "active" | "inactive";
type LedgerView = "stage" | "competition" | "negotiation" | "coordination" | "province";
type OverlayKind = "competition" | "coordination" | "topk";

const LEDGER_PAGE_SIZE = 7;

function provinceName(profiles: Array<{ province_code: string; short_name: string }>, code: string) {
  return profiles.find((item) => item.province_code === code)?.short_name ?? "相关省份";
}

function changedProvinceCount(branch: BranchRuntime) {
  return Object.keys(branch.province_final_actions).filter((code) => {
    const initial = branch.province_initial_actions[code];
    const final = branch.province_final_actions[code];
    if (!initial || !final) return false;
    return initial.overall_support_intensity !== final.overall_support_intensity
      || initial.primary_policy_focus !== final.primary_policy_focus
      || initial.subsidy_mix.consumer !== final.subsidy_mix.consumer
      || initial.subsidy_mix.fixed_cost !== final.subsidy_mix.fixed_cost
      || initial.subsidy_mix.variable_cost !== final.subsidy_mix.variable_cost;
  }).length;
}

export default function V32LivePage() {
  const flow = useV32();
  const location = useLocation();
  const navigate = useNavigate();
  const branchParam = new URLSearchParams(location.search).get("branch");
  const [branchKey, setBranchKey] = useState(branchParam === "treatment" ? "treatment" : "control");
  const [layer, setLayer] = useState<Layer>("support");
  const [mapView, setMapView] = useState<"difference" | "branch">("difference");
  const [ledgerView, setLedgerView] = useState<LedgerView>("stage");
  const [ledgerFilter, setLedgerFilter] = useState<LedgerFilter>("all");
  const [ledgerPage, setLedgerPage] = useState(1);
  const [selectedProvince, setSelectedProvince] = useState<string>();
  const [focusCodes, setFocusCodes] = useState<string[]>([]);
  const [selectedLinkId, setSelectedLinkId] = useState<string>();
  const [market, setMarket] = useState<StrategyMarket | null>(null);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [overlays, setOverlays] = useState<Record<OverlayKind, boolean>>({ competition: true, coordination: true, topk: true });

  const world = flow.world;
  const branch = world?.branches[branchKey];
  const control = world?.branches.control;
  const treatment = world?.branches.treatment;

  useEffect(() => {
    if (!world || !world.branches.control.completed_rounds.includes("province_revision")) return;
    let active = true;
    setMarketError(null);
    void v32Api.strategyMarket(world.experiment_id)
      .then((result) => { if (active) setMarket(result); })
      .catch((reason: unknown) => { if (active) setMarketError(reason instanceof Error ? reason.message : "互动数据加载失败"); });
    return () => { active = false; };
  }, [world]);

  useEffect(() => {
    setLedgerFilter("all");
    setLedgerPage(1);
  }, [branchKey, ledgerView]);

  const setBranch = (nextBranch: string) => {
    setBranchKey(nextBranch);
    setSelectedProvince(undefined);
    setFocusCodes([]);
    setSelectedLinkId(undefined);
    const params = new URLSearchParams(location.search);
    params.set("branch", nextBranch);
    navigate(`${location.pathname}?${params.toString()}`, { replace: true });
  };

  const openCompany = (automakerId: string, provinceCode?: string) => {
    if (provinceCode) {
      setSelectedProvince(provinceCode);
      setFocusCodes([provinceCode]);
    }
    const params = new URLSearchParams(location.search);
    params.set("branch", branchKey);
    params.set("company", automakerId);
    navigate(`${location.pathname}?${params.toString()}`);
  };

  const valueFor = useCallback((currentBranch: typeof branch, code: string) => {
    const action = currentBranch?.province_final_actions[code] ?? currentBranch?.province_initial_actions[code];
    const state = currentBranch?.province_states[code];
    if (layer === "support") return action?.overall_support_intensity == null ? undefined : action.overall_support_intensity * 100;
    if (layer === "consumer") return action?.subsidy_mix.consumer == null ? undefined : action.subsidy_mix.consumer * 100;
    if (layer === "fixed") return action?.subsidy_mix.fixed_cost == null ? undefined : action.subsidy_mix.fixed_cost * 100;
    if (layer === "variable") return action?.subsidy_mix.variable_cost == null ? undefined : action.subsidy_mix.variable_cost * 100;
    if (layer === "demand") return state?.demand_index;
    return state?.industry_activity_index;
  }, [layer]);

  const values = useMemo(() => Object.fromEntries(flow.profiles.map((profile) => {
    const branchValue = valueFor(branch, profile.province_code);
    if (mapView === "branch") return [profile.province_code, branchValue];
    const treatmentValue = valueFor(treatment, profile.province_code);
    const controlValue = valueFor(control, profile.province_code);
    return [profile.province_code, treatmentValue == null || controlValue == null ? undefined : treatmentValue - controlValue];
  })), [branch, control, flow.profiles, mapView, treatment, valueFor]);

  if (!world || !branch) return <div className="v3-empty-page"><h2>尚未完成基线确认</h2><button onClick={() => navigate("/experiments/new")} type="button">新建实验</button></div>;

  const interactionBranch = market?.branches[branchKey] ?? branch;
  const isM32 = world.schema_version === "world-state-v9" && world.product_version === "v3_2_m32";
  const displayRounds = isM32 ? M32_ROUNDS : M31_ROUNDS;
  const prefixLength = displayRounds.findIndex((item) => !branch.completed_rounds.includes(item));
  const completed = displayRounds.slice(0, prefixLength === -1 ? displayRounds.length : prefixLength);
  const sequenceInvalid = branch.completed_rounds.some((item, index) => displayRounds[index] !== item);
  const nextRound = displayRounds.find((item) => !completed.includes(item));
  const visibleRound = nextRound ?? "environment_settlement";
  const completionRate = Math.round((completed.length / displayRounds.length) * 100);
  const competitionOutcomes = interactionBranch.competition_outcomes ?? [];
  const coordinationRecords = interactionBranch.coordination_records ?? [];
  const enterpriseMatches = interactionBranch.province_enterprise_matches ?? [];
  const counterOffers = interactionBranch.automaker_counter_offers ?? [];
  const counterResponses = interactionBranch.province_counter_offer_responses ?? [];
  const selectedProfile = flow.profiles.find((item) => item.province_code === selectedProvince);
  const selectedRelations = selectedProvince && world.relation_network
    ? world.relation_network.relations.filter((item) => item.source_code === selectedProvince || item.target_code === selectedProvince)
    : [];
  const selectedUtility = selectedProvince ? interactionBranch.province_utilities?.[selectedProvince] : undefined;
  const selectedLosses = selectedProvince
    ? competitionOutcomes.filter((item) => item.loser_province_code === selectedProvince)
    : [];
  const changedCount = changedProvinceCount(interactionBranch);

  const keyChanges = (() => {
    const changes: Array<{ kind: OverlayKind | "negotiation"; title: string; detail: string }> = [];
    const largestCompetition = [...competitionOutcomes].sort((left, right) => right.loss_index - left.loss_index)[0];
    if (largestCompetition) changes.push({
      kind: "competition",
      title: `${provinceName(flow.profiles, largestCompetition.loser_province_code)}未获${largestCompetition.resource_type === "channel_slot" ? "渠道" : "产能"}重点资源`,
      detail: `${provinceName(flow.profiles, largestCompetition.winner_province_code)}获选 · 竞争损失 ${largestCompetition.loss_index.toFixed(1)}`,
    });
    const matchedCoordination = [...coordinationRecords].filter((item) => item.status === "matched").sort((left, right) => right.contribution - left.contribution)[0];
    if (matchedCoordination) changes.push({
      kind: "coordination",
      title: `${provinceName(flow.profiles, matchedCoordination.left_province_code)}与${provinceName(flow.profiles, matchedCoordination.right_province_code)}达成协同`,
      detail: `环境贡献 ${matchedCoordination.contribution.toFixed(1)} 模拟指数`,
    });
    const acceptedCounter = counterResponses.find((item) => item.decision === "accept");
    const acceptedOffer = acceptedCounter && counterOffers.find((item) => item.counter_offer_id === acceptedCounter.counter_offer_id);
    if (acceptedCounter && acceptedOffer) changes.push({
      kind: "negotiation",
      title: `${provinceName(flow.profiles, acceptedCounter.province_code)}接受反报价`,
      detail: `${flow.automakers.find((item) => item.automaker_id === acceptedOffer.automaker_id)?.display_name ?? "相关车企"} · ${productLabel(acceptedOffer.required_policy_focus)}`,
    });
    if (changes.length < 3 && changedCount > 0) changes.push({ kind: "topk", title: `${changedCount} 个省份调整最终策略`, detail: "初始行动与最终行动已形成可追溯变化" });
    return changes.slice(0, 3);
  })();

  const allLinks: ProvinceMapLink[] = (() => {
    const competitionLinks = [...competitionOutcomes]
      .sort((left, right) => right.loss_index - left.loss_index)
      .map((item) => ({
        id: `competition-${item.outcome_id}`,
        sourceCode: item.winner_province_code,
        targetCode: item.loser_province_code,
        kind: "competition" as const,
        label: `${provinceName(flow.profiles, item.winner_province_code)}挤出${provinceName(flow.profiles, item.loser_province_code)} · 损失 ${item.loss_index.toFixed(1)}`,
      }));
    const coordinationLinks = [...coordinationRecords]
      .sort((left, right) => Number(right.status === "matched") - Number(left.status === "matched") || right.contribution - left.contribution)
      .map((item) => ({
        id: `coordination-${item.coordination_id}`,
        sourceCode: item.left_province_code,
        targetCode: item.right_province_code,
        kind: "coordination" as const,
        label: `${provinceName(flow.profiles, item.left_province_code)}与${provinceName(flow.profiles, item.right_province_code)} · ${productLabel(item.status)}`,
      }));
    const topKLinks = [...(interactionBranch.top_k_reallocations ?? [])]
      .map((item) => ({
        id: `topk-${item.reallocation_id}`,
        sourceCode: item.released_province_code,
        targetCode: item.recipient_province_code,
        kind: "topk" as const,
        label: `${flow.automakers.find((company) => company.automaker_id === item.automaker_id)?.display_name ?? "车企"}：${provinceName(flow.profiles, item.released_province_code)}释放名额 → ${provinceName(flow.profiles, item.recipient_province_code)}承接`,
      }));
    return [...competitionLinks, ...coordinationLinks, ...topKLinks];
  })();

  const overlayLinks = (() => {
    const relevant = allLinks.filter((link) => overlays[link.kind]
      && (!selectedLinkId || link.id === selectedLinkId)
      && (!selectedProvince || link.sourceCode === selectedProvince || link.targetCode === selectedProvince));
    const limited = selectedProvince || selectedLinkId ? relevant : relevant.slice(0, 10);
    return limited.map((link) => ({ ...link, selected: link.id === selectedLinkId }));
  })();

  const selectProvinceOnMap = (code: string) => {
    setSelectedProvince(code);
    setFocusCodes([code]);
    setSelectedLinkId(undefined);
    setLedgerView("province");
  };

  const clearFocus = () => {
    setSelectedProvince(undefined);
    setFocusCodes([]);
    setSelectedLinkId(undefined);
    if (ledgerView === "province") setLedgerView("stage");
  };

  const selectLink = (link: ProvinceMapLink) => {
    setSelectedLinkId(link.id);
    setSelectedProvince(undefined);
    setFocusCodes([link.sourceCode, link.targetCode]);
    setLedgerView(link.kind === "coordination" ? "coordination" : "competition");
  };

  const selectCompetition = (outcomeId: string) => {
    const outcome = competitionOutcomes.find((item) => item.outcome_id === outcomeId);
    if (!outcome) return;
    setSelectedProvince(undefined);
    setFocusCodes([outcome.winner_province_code, outcome.loser_province_code]);
    setSelectedLinkId(`competition-${outcome.outcome_id}`);
  };

  const selectCoordination = (coordinationId: string) => {
    const record = coordinationRecords.find((item) => item.coordination_id === coordinationId);
    if (!record) return;
    setSelectedProvince(undefined);
    setFocusCodes([record.left_province_code, record.right_province_code]);
    setSelectedLinkId(`coordination-${record.coordination_id}`);
  };

  const competitionFiltered = competitionOutcomes.filter(() => ledgerFilter !== "inactive");
  const negotiationItems = [
    ...counterOffers.map((offer) => ({
      id: offer.counter_offer_id,
      provinceCode: offer.province_code,
      automakerId: offer.automaker_id,
      title: `${provinceName(flow.profiles, offer.province_code)} ↔ ${flow.automakers.find((item) => item.automaker_id === offer.automaker_id)?.display_name ?? "车企"}`,
      detail: `反报价 · ${productLabel(offer.required_policy_focus)} · 渠道 ${(offer.required_channel_share * 100).toFixed(0)}%${counterResponses.find((item) => item.counter_offer_id === offer.counter_offer_id) ? ` · 省级${counterResponses.find((item) => item.counter_offer_id === offer.counter_offer_id)?.decision === "accept" ? "接受" : "拒绝"}` : " · 待回应"}`,
      active: counterResponses.some((item) => item.counter_offer_id === offer.counter_offer_id && item.decision === "accept"),
      state: counterResponses.find((item) => item.counter_offer_id === offer.counter_offer_id)?.decision ?? "counteroffer",
      opportunityCost: counterResponses.find((item) => item.counter_offer_id === offer.counter_offer_id)?.opportunity_cost || offer.opportunity_cost,
    })),
    ...enterpriseMatches.filter((match) => !counterOffers.some((offer) => offer.offer_id === match.offer_id)).map((match) => ({
      id: match.match_id,
      provinceCode: match.province_code,
      automakerId: match.automaker_id,
      title: `${provinceName(flow.profiles, match.province_code)} → ${flow.automakers.find((item) => item.automaker_id === match.automaker_id)?.display_name ?? "车企"}`,
      detail: match.summary,
      active: match.status === "matched",
      state: match.status,
      opportunityCost: "",
    })),
    ...Object.entries(interactionBranch.automaker_final_actions).flatMap(([automakerId, finalAction]) => {
      const initialAction = interactionBranch.automaker_initial_actions[automakerId];
      if (!initialAction) return [];
      const initialExpanded = new Set(initialAction.province_market_actions.filter((item) => item.channel_strategy === "expand").map((item) => item.province_code));
      return finalAction.province_market_actions
        .filter((item) => item.channel_strategy === "expand" && !initialExpanded.has(item.province_code))
        .map((item) => ({
          id: `reallocation-${automakerId}-${item.province_code}`,
          provinceCode: item.province_code,
          automakerId,
          title: `${flow.automakers.find((company) => company.automaker_id === automakerId)?.display_name ?? "车企"} → ${provinceName(flow.profiles, item.province_code)}`,
          detail: "最终确认后重配 Top-K 渠道名额",
          active: true,
          state: "reallocated",
          opportunityCost: finalAction.opportunity_costs[0] ?? "",
        }));
    }),
  ];
  const negotiationFiltered = negotiationItems.filter((item) => ledgerFilter === "all" || (ledgerFilter === "active" ? item.active : !item.active));
  const coordinationFiltered = coordinationRecords.filter((item) => ledgerFilter === "all" || (ledgerFilter === "active" ? item.status === "matched" : item.status !== "matched"));
  const currentItems = ledgerView === "competition" ? competitionFiltered : ledgerView === "negotiation" ? negotiationFiltered : ledgerView === "coordination" ? coordinationFiltered : [];
  const pageCount = Math.max(1, Math.ceil(currentItems.length / LEDGER_PAGE_SIZE));
  const safePage = Math.min(ledgerPage, pageCount);
  const pageStart = (safePage - 1) * LEDGER_PAGE_SIZE;
  const activeCount = ledgerView === "competition"
    ? competitionOutcomes.length
    : ledgerView === "negotiation"
      ? negotiationItems.filter((item) => item.active).length
      : coordinationRecords.filter((item) => item.status === "matched").length;
  const totalCount = ledgerView === "competition" ? competitionOutcomes.length : ledgerView === "negotiation" ? negotiationItems.length : coordinationRecords.length;
  const inactiveCount = totalCount - activeCount;
  const unit = ["support", "consumer", "fixed", "variable"].includes(layer) ? "个百分点" : "指数点";
  const tooltipDetails = Object.fromEntries(flow.profiles.map((profile) => {
    const action = branch.province_final_actions[profile.province_code] ?? branch.province_initial_actions[profile.province_code];
    return [profile.province_code, { strategy: action ? productLabel(action.response_mode) : undefined, dataQualityLabel: "代理数据基线" }];
  }));
  const runNext = async () => { if (nextRound) await flow.run(nextRound); else await flow.run(); };

  return <div className="v32-page v32-live-page">
    <header className="v32-heading">
      <div><span className="v32-eyebrow">{productLabel(world.design?.experiment_type ?? "")}</span><h1>全国推演</h1><small className="v32-heading-status">{world.status === "completed" ? "推演已完成" : `当前：${roundLabels[visibleRound]}`}</small></div>
      <div className="v32-heading-actions">{world.status !== "completed" ? <><button onClick={() => void runNext()} type="button"><Icon name="skip_next" />推进下一步</button><button className="v3-primary" onClick={() => void flow.run()} type="button"><Icon name="play_arrow" />完成推演</button></> : <button className="v3-primary" onClick={() => navigate(`/experiments/${world.experiment_id}/compare`)} type="button">查看结果对比</button>}</div>
    </header>

    <nav aria-label="推演进度" className={`v32-round-rail rounds-${displayRounds.length}`}>{displayRounds.map((item, index) => <button aria-current={item === nextRound ? "step" : undefined} className={completed.includes(item) ? "done" : item === nextRound ? "active" : ""} key={item} onClick={() => setLedgerView("stage")} type="button"><b>{completed.includes(item) ? "✓" : index + 1}</b><span>{roundLabels[item]}</span></button>)}</nav>
    {sequenceInvalid && <div className="v32-chain-warning" role="alert">运行进度记录不连续，已按最后一个连续完成轮次显示；请重新推进当前轮次。</div>}

    <div className="v32-live-toolbar"><div className="v32-branch-tabs">{Object.entries(world.branches).map(([key, item]) => <button className={branchKey === key ? "active" : ""} key={key} onClick={() => setBranch(key)} type="button"><span>{item.label}</span><small>{item.event_applied ? "含情景事件" : "常规情景"}</small></button>)}</div><div className="v32-segment"><button className={mapView === "difference" ? "active" : ""} onClick={() => setMapView("difference")} type="button">方案差异</button><button className={mapView === "branch" ? "active" : ""} onClick={() => setMapView("branch")} type="button">单方案</button></div></div>

    <section className="v3-card v32-stage-summary">
      <div className="v32-stage-progress"><span className="v32-eyebrow">当前阶段</span><h2>{world.status === "completed" ? "环境结算完成" : roundLabels[visibleRound]}</h2><div><b style={{ width: `${completionRate}%` }} /></div><small>{completed.length} / {displayRounds.length} 轮完成 · {completionRate}%</small></div>
      <div className="v32-key-changes"><span className="v32-eyebrow">关键变化</span>{keyChanges.length ? <div>{keyChanges.map((change) => <button key={`${change.kind}-${change.title}`} onClick={() => setLedgerView(change.kind === "competition" ? "competition" : change.kind === "coordination" ? "coordination" : change.kind === "negotiation" ? "negotiation" : "stage")} type="button"><i className={change.kind} /><span><strong>{change.title}</strong><small>{change.detail}</small></span></button>)}</div> : <p>当前轮次尚未产生可展示的结果，推进后将显示实际竞争、谈判与协同变化。</p>}</div>
    </section>

    <div className="v32-live-layout">
      <section className="v3-card v32-map-workspace">
        <div className="v32-map-toolbar"><label>填色图层<select aria-label="地图填色图层" onChange={(event) => setLayer(event.target.value as Layer)} value={layer}>{Object.entries(layers).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><div aria-label="地图覆盖层" className="v32-overlay-toggles">{(["competition", "coordination", "topk"] as OverlayKind[]).map((kind) => <button aria-pressed={overlays[kind]} className={`${kind}${overlays[kind] ? " active" : ""}`} key={kind} onClick={() => setOverlays((current) => ({ ...current, [kind]: !current[kind] }))} type="button">{kind === "competition" ? "竞争损失" : kind === "coordination" ? "省际协同" : "Top-K 资源流"}</button>)}</div>{(selectedProvince || focusCodes.length > 0) && <button className="v32-clear-focus" onClick={clearFocus} type="button"><Icon name="close" />恢复全国视图</button>}</div>
        <ProvinceMap emptyMessage="完成相应行动后显示全国分布" focusCodes={focusCodes} metricLabel={mapView === "difference" ? `${layers[layer]}（干预方案 − 原始方案）` : layers[layer]} mode={mapView === "difference" ? "difference" : "absolute"} onLinkSelect={selectLink} onSelect={selectProvinceOnMap} overlayLinks={overlayLinks} profiles={flow.profiles} selectedCode={selectedProvince} tooltipDetails={tooltipDetails} unit={unit} values={values} />
      </section>

      <aside className="v3-card v32-interaction-ledger">
        <div className="v32-ledger-head"><div><span className="v32-eyebrow">互动决策台</span><h2>{ledgerView === "stage" ? "阶段" : ledgerView === "competition" ? "竞争" : ledgerView === "negotiation" ? "谈判" : ledgerView === "coordination" ? "协同" : "省份"}</h2></div>{!["stage", "province"].includes(ledgerView) && <span>{totalCount} 项</span>}</div>
        <div className="v32-ledger-tabs">{(["stage", "competition", "negotiation", "coordination", "province"] as LedgerView[]).map((view) => <button aria-pressed={ledgerView === view} className={ledgerView === view ? "active" : ""} disabled={view === "province" && !selectedProvince} key={view} onClick={() => setLedgerView(view)} type="button">{view === "stage" ? "阶段" : view === "competition" ? "竞争" : view === "negotiation" ? "谈判" : view === "coordination" ? "协同" : "省份"}</button>)}</div>
        {marketError && <div className="v32-ledger-error"><Icon name="error" /><span>互动详情暂时不可用：{marketError}</span></div>}

        {ledgerView === "stage" && <div className="v32-stage-ledger"><strong>{roundLabels[visibleRound]}</strong><p>{world.status === "completed" ? "两个同源分支均已完成环境结算。" : `第 ${Math.min(completed.length + 1, displayRounds.length)} 轮待执行，页面展示已冻结的最新事实。`}</p><dl><div><dt>竞争结果</dt><dd>{competitionOutcomes.length}</dd></div><div><dt>有效协同</dt><dd>{coordinationRecords.filter((item) => item.status === "matched").length}</dd></div><div><dt>反报价</dt><dd>{counterOffers.length}</dd></div><div><dt>策略调整省份</dt><dd>{changedCount}</dd></div></dl><small>点击进度节点只切换信息视角，不伪造历史地图快照。</small></div>}

        {ledgerView === "province" && selectedProfile && <div className="v32-province-ledger"><div><span className="v32-quality proxy">代理数据基线</span><h3>{selectedProfile.short_name}</h3><p>{branch.province_final_actions[selectedProfile.province_code]?.summary ?? branch.province_initial_actions[selectedProfile.province_code]?.summary ?? "尚未生成省级行动。"}</p></div><dl><div><dt>观察关系</dt><dd>{selectedRelations.filter((item) => item.relation_type === "observation").length}</dd></div><div><dt>竞争关系</dt><dd>{selectedRelations.filter((item) => item.relation_type === "competition").length}</dd></div><div><dt>协同关系</dt><dd>{selectedRelations.filter((item) => item.relation_type === "coordination").length}</dd></div><div><dt>竞争损失</dt><dd>{(selectedUtility?.competition_loss ?? selectedLosses.reduce((sum, item) => sum + item.loss_index, 0)).toFixed(1)}</dd></div><div><dt>最终效用</dt><dd>{selectedUtility?.utility_index.toFixed(1) ?? "—"}</dd></div><div><dt>最终策略</dt><dd>{productLabel(branch.province_final_actions[selectedProfile.province_code]?.response_mode ?? branch.province_initial_actions[selectedProfile.province_code]?.response_mode ?? "")}</dd></div></dl><button className="v3-primary" onClick={() => navigate(`/experiments/${world.experiment_id}/provinces/${selectedProfile.province_code}?branch=${branchKey}`)} type="button">查看省份详情</button></div>}

        {["competition", "negotiation", "coordination"].includes(ledgerView) && <>
          <div aria-label="互动记录筛选" className="v32-ledger-counts"><button aria-pressed={ledgerFilter === "all"} className={ledgerFilter === "all" ? "active" : ""} onClick={() => { setLedgerFilter("all"); setLedgerPage(1); }} type="button">全部 {totalCount}</button><button aria-pressed={ledgerFilter === "active"} className={ledgerFilter === "active" ? "active" : ""} onClick={() => { setLedgerFilter("active"); setLedgerPage(1); }} type="button">生效 {activeCount}</button><button aria-pressed={ledgerFilter === "inactive"} className={ledgerFilter === "inactive" ? "active" : ""} onClick={() => { setLedgerFilter("inactive"); setLedgerPage(1); }} type="button">未生效 {inactiveCount}</button></div>
          <div className="v32-interaction-list">
            {ledgerView === "competition" && competitionFiltered.slice(pageStart, pageStart + LEDGER_PAGE_SIZE).map((item) => <button className={selectedLinkId === `competition-${item.outcome_id}` ? "selected" : ""} key={item.outcome_id} onClick={() => selectCompetition(item.outcome_id)} type="button"><span><b>{provinceName(flow.profiles, item.loser_province_code)} ← {provinceName(flow.profiles, item.winner_province_code)}</b><small>{flow.automakers.find((company) => company.automaker_id === item.automaker_id)?.display_name ?? "车企"} · {item.resource_type === "channel_slot" ? "渠道名额" : "产能名额"}</small><i>名次 {item.winner_rank} / {item.loser_rank} · 关系权重 {item.relation_weight.toFixed(2)}</i></span><em className="rejected">损失 {item.loss_index.toFixed(1)}</em></button>)}
            {ledgerView === "negotiation" && negotiationFiltered.slice(pageStart, pageStart + LEDGER_PAGE_SIZE).map((item) => <button key={item.id} onClick={() => openCompany(item.automakerId, item.provinceCode)} type="button"><span><b>{item.title}</b><small>{item.detail}</small>{item.opportunityCost && <i>机会成本：{item.opportunityCost}</i>}</span><em className={item.active ? "matched" : "rejected"}>{item.state === "counteroffer" ? "待回应" : item.state === "reallocated" ? "已重配" : productLabel(item.state)}</em></button>)}
            {ledgerView === "coordination" && coordinationFiltered.slice(pageStart, pageStart + LEDGER_PAGE_SIZE).map((item) => <button className={selectedLinkId === `coordination-${item.coordination_id}` ? "selected" : ""} key={item.coordination_id} onClick={() => selectCoordination(item.coordination_id)} type="button"><span><b>{provinceName(flow.profiles, item.left_province_code)} ↔ {provinceName(flow.profiles, item.right_province_code)}</b><small>{item.summary}</small><i>确定性贡献 {item.contribution.toFixed(1)} 模拟指数</i></span><em className={item.status}>{productLabel(item.status)}</em></button>)}
            {!currentItems.length && <div className="v3-empty">当前筛选下没有互动记录。</div>}
          </div>
          {currentItems.length > LEDGER_PAGE_SIZE && <nav aria-label="互动记录分页" className="v32-ledger-pagination"><button disabled={safePage === 1} onClick={() => setLedgerPage((page) => Math.max(1, page - 1))} type="button"><Icon name="chevron_left" />上一页</button><span>{safePage} / {pageCount} · 共 {currentItems.length} 项</span><button disabled={safePage === pageCount} onClick={() => setLedgerPage((page) => Math.min(pageCount, page + 1))} type="button">下一页<Icon name="chevron_right" /></button></nav>}
        </>}
      </aside>
    </div>

    {completed.includes("environment_settlement") && Object.keys(branch.province_states).length > 0 && <section className="v3-card v32-settlement-summary"><div><span className="v32-eyebrow">环境结算</span><h2>全国指标摘要</h2></div><div className="v32-metric-strip">{[["区域发展差距", branch.national_metrics.regional_development_gap], ["中央财政负担", branch.national_metrics.central_fiscal_burden], ["地方财政压力", branch.national_metrics.local_fiscal_pressure], ["新能源汽车需求", branch.national_metrics.nev_demand], ["新增投资集中度", branch.national_metrics.new_investment_concentration], ["产业集聚度", branch.national_metrics.industrial_agglomeration]].map(([label, value]) => <div key={String(label)}><small>{label}</small><strong>{Number(value).toFixed(1)}</strong><span>模拟指数</span></div>)}</div></section>}
  </div>;
}
