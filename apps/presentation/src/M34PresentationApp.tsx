import {
  ArrowRight,
  Check,
  CubeFocus,
  Database,
  Eye,
  Info,
  Lightning,
  MapPin,
  Pause,
  Play,
  SlidersHorizontal,
  SkipBack,
  SkipForward,
  Sparkle,
  Target,
  X,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { PresentationMapFrame, PresentationOverlayKind } from "./contracts";
import { m34Api } from "./m34Api";
import type {
  BranchView,
  CausalBeatId,
  M34Configuration,
  M34Draft,
  M34EventSelection,
  M34Frame,
  M34Timeline,
  M34World,
  MacroTick,
  PresentationSpotlightV4,
  PresentationWorldLandmarks,
} from "./m34Contracts";
import { PresentationMap } from "./PresentationMap";
import { PresentationMapFallback } from "./PresentationMapFallback";
import { CACHED_TREATMENT_SHARES } from "./presentationDefaults";
import { mapViewLockReason, resolveMapView } from "./presentationView";
import type { MapViewPreference } from "./presentationView";
import type { PresentationVisualScale } from "./mapScale";
import { GlobeIntro } from "./tech-spike/GlobeIntro";
import type { PresentationMapCollection } from "./tech-spike/types";

type ReviewStep = "configuration" | "design";
type LaunchTab = "policy" | "event";
type LaunchPhase = "intro" | "controls" | "dialog";
type Panel = "evidence" | "province" | null;

const TICKS: MacroTick[] = ["Q1", "Q2", "Q3", "Q4"];
const BEAT_LABELS = ["关注", "观察", "决策", "行动", "回应", "结算"] as const;
const TICK_LABELS: Record<MacroTick, string> = {
  Q1: "政策落地", Q2: "主体互动", Q3: "调整扩散", Q4: "年度结算",
};
const WAVE_DISPLAY = {
  wave_0: "首次行动", wave_1: "条件回应", wave_2: "协议收敛",
} as const;
const BEAT_ICONS: Record<CausalBeatId, typeof Eye> = {
  focus: Target,
  observe: Eye,
  decide: Lightning,
  action: ArrowRight,
  response: Lightning,
  settle: Check,
};
const METRICS = [
  ["regional_development_gap", "区域发展差距"],
  ["central_fiscal_burden", "中央财政负担"],
  ["local_fiscal_pressure", "地方财政压力"],
  ["nev_demand", "新能源汽车需求"],
  ["new_investment_concentration", "新增投资集中度"],
  ["industrial_agglomeration", "产业集聚度"],
] as const;

function metricIcon(metricId: string): string | null {
  if (metricId === "central_fiscal_burden" || metricId === "local_fiscal_pressure") {
    return "/assets/icons/fiscal-pressure.svg";
  }
  if (metricId === "nev_demand") return "/assets/icons/consumer-demand.svg";
  return null;
}

function launchPolygons(coordinates: unknown): number[][][][] {
  if (!Array.isArray(coordinates)) return [];
  if (
    coordinates.length
    && Array.isArray(coordinates[0])
    && Array.isArray(coordinates[0][0])
    && typeof coordinates[0][0][0] === "number"
  ) return [coordinates as number[][][]];
  return coordinates.flatMap(launchPolygons);
}

function PrelaunchControlBoard({ collection, phase }: { collection: PresentationMapCollection; phase: LaunchPhase }) {
  const [minX, minY, maxX, maxY] = collection.bbox;
  const width = maxX - minX;
  const height = maxY - minY;
  const path = (coordinates: unknown) => launchPolygons(coordinates)
    .map((polygon) => polygon
      .map((ring) => ring
        .map(([x, y], index) => `${index ? "L" : "M"}${((x - minX) / width * 1000).toFixed(2)},${((maxY - y) / height * 720).toFixed(2)}`)
        .join(" ") + " Z")
      .join(" "))
    .join(" ");
  return <section aria-hidden="true" className={`prelaunch-board reveal-${phase}`}>
    <header className="prelaunch-hud"><div className="brand-lockup"><span><Sparkle weight="fill" /></span><div><strong>13110</strong><small>新能源汽车产业协同推演</small></div></div><div><small>决策问题</small><b>如何设计同源 A/B 政策实验？</b></div><nav><span>原始方案</span><span>干预方案</span><span>方案差值</span></nav></header>
    <aside className="prelaunch-spine"><small>因果链</small>{["关注政策目标", "观察同源基线", "决定实验变量", "主体开始行动", "回应与协商", "季度环境结算"].map((item, index) => <div key={item}><span>{index + 1}</span><b>{item}</b></div>)}</aside>
    <div className="prelaunch-map"><svg role="img" viewBox="0 0 1000 720"><title>全国政策推演主控地图</title>{collection.features.map((feature) => <path className={feature.properties.region_role} d={path(feature.geometry.coordinates)} key={feature.properties.province_code} />)}</svg><div><small>全国政策网络</small><b>31 省·10 家车企模拟主体</b></div></div>
    <aside className="prelaunch-game"><small>主体博弈台</small><h2>实验尚未冻结</h2><p>完成政策比例与事件设计后，主体互动将从 Q1 开始。</p><div><span>提议</span><span>反报价</span><span>回应</span><span>结算</span></div></aside>
    <footer className="prelaunch-timeline">{TICKS.map((tick) => <div key={tick}><b>{tick}</b><span>{TICK_LABELS[tick]}</span></div>)}</footer>
  </section>;
}

function frameBeats(frame: M34Frame) {
  if (frame.kind === "comparison") return [
    { beat: "focus", label: "关注", headline: "年度政策目标", detail: frame.question, status: "completed" },
    { beat: "observe", label: "观察", headline: "核对同源起点", detail: "两套方案共享冻结基线。", status: "completed" },
    { beat: "decide", label: "决策", headline: "比较六项指标", detail: "识别政策收益、代价与权衡。", status: "completed" },
    { beat: "action", label: "行动", headline: "定位主体分歧", detail: "追溯省份与车企模拟主体的不同选择。", status: "completed" },
    { beat: "response", label: "回应", headline: "读取世界反馈", detail: "最终指标仅由确定性环境计算。", status: "completed" },
    { beat: "settle", label: "结算", headline: "年度复盘冻结", detail: frame.summary, status: "completed" },
  ] as const;
  if (frame.kind === "settlement") return [
    { beat: "focus", label: "关注", headline: "本季度行动", detail: frame.question, status: "completed" },
    { beat: "observe", label: "观察", headline: "冻结互动结果", detail: "只读取本分支已授权事实。", status: "completed" },
    { beat: "decide", label: "决策", headline: "筛选合法交易", detail: "拒绝、过期与资源无效不进入贡献。", status: "completed" },
    { beat: "action", label: "行动", headline: "环境统一计算", detail: "同一季度批量清算，不依赖消息顺序。", status: "completed" },
    { beat: "response", label: "回应", headline: "世界状态变化", detail: "省域与全国模拟指数完成更新。", status: "completed" },
    { beat: "settle", label: "结算", headline: "季度事实冻结", detail: frame.summary, status: "completed" },
  ] as const;
  return [
    { beat: "focus", label: "关注", headline: "当前世界", detail: frame.summary, status: "active" },
    { beat: "observe", label: "观察", headline: "读取冻结事实", detail: frame.summary, status: "pending" },
    { beat: "decide", label: "决策", headline: "等待主体决策", detail: "当前节点没有新互动。", status: "pending" },
    { beat: "action", label: "行动", headline: "等待行动", detail: "当前节点没有新互动。", status: "pending" },
    { beat: "response", label: "回应", headline: "等待回应", detail: "当前节点没有新互动。", status: "pending" },
    { beat: "settle", label: "结算", headline: "环境结算", detail: frame.summary, status: "pending" },
  ] as const;
}

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
}

function pathExperimentId() {
  const match = window.location.pathname.match(/\/experiments\/([^/]+)\/present/);
  return match?.[1] ?? new URLSearchParams(window.location.search).get("experiment");
}

function visualScale(frame: M34Frame, view: BranchView): PresentationVisualScale {
  const scale = frame.shared_scale;
  if (view === "delta") {
    const bound = scale.difference_bound;
    return {
      domain: [-bound, bound], center: 0,
      stops: [
        [-bound, "#7565d4"], [-bound / 2, "#514a7d"], [0, "#182637"],
        [bound / 2, "#176f73"], [bound, "#75ead6"],
      ],
    };
  }
  const { absolute_min: min, absolute_max: max } = scale;
  return {
    domain: [min, max], center: null,
    stops: [
      [min, "#17293a"], [min + (max - min) * .25, "#16414d"],
      [min + (max - min) * .5, "#175762"], [min + (max - min) * .75, "#1a7777"],
      [max, "#65cabc"],
    ],
  };
}

function mapFrame(
  frame: M34Frame,
  view: BranchView,
  activeBeat: number,
  spotlight: PresentationSpotlightV4 | null,
): PresentationMapFrame {
  const control = frame.branches.control;
  const treatment = frame.branches.treatment;
  const source = view === "control" ? control : treatment;
  const values = source.province_values.map((item) => {
    const controlValue = control.province_values.find((candidate) => candidate.province_code === item.province_code)?.value ?? null;
    const treatmentValue = treatment.province_values.find((candidate) => candidate.province_code === item.province_code)?.value ?? null;
    const value = view === "delta"
      ? controlValue == null || treatmentValue == null ? null : treatmentValue - controlValue
      : item.value;
    return { province_code: item.province_code, value, missing: value == null, data_quality: "proxy" as const };
  });
  const edges = view === "delta" ? [] : source.game_edges.filter((edge) => {
    if (edge.relation === "event_impact") return activeBeat >= 1;
    if (edge.relation === "proposal") return activeBeat >= 3;
    if (edge.relation === "settled") return activeBeat >= 5;
    return activeBeat >= 4;
  });
  const overlay_records = edges.map((edge) => {
    const provincePair = edge.source.subject_type === "province" && edge.target.subject_type === "province";
    const kind: PresentationOverlayKind = edge.relation === "event_impact"
      ? "event" : provincePair ? "coordination" : "negotiation";
    return {
      schema_version: "presentation-overlay-record-v2" as const,
      overlay_id: edge.edge_id,
      kind,
      source_subject: edge.source.subject_ref,
      target_subject: edge.target.subject_ref,
      status: edge.relation_label,
      weight: edge.weight,
      label: `${edge.source.display_name} → ${edge.target.display_name} · ${edge.relation_label}`,
      style_semantic: edge.relation === "event_impact" ? "event" as const : provincePair ? "coordination" as const : "evidence" as const,
      relation_semantic: edge.relation,
      line_style: edge.line_style,
      emphasized: Boolean(spotlight && edge.session_id === spotlight.session_id),
      evidence_refs: edge.evidence_refs,
    };
  });
  const metric_summary = METRICS.map(([key, label]) => {
    const controlValue = control.national_metrics[key];
    const treatmentValue = treatment.national_metrics[key];
    return {
      metric_id: key, label,
      value: view === "control" ? controlValue : view === "treatment" ? treatmentValue : treatmentValue - controlValue,
      unit: "模拟指数", delta: treatmentValue - controlValue, evidence_refs: frame.evidence_refs,
    };
  });
  return {
    schema_version: "presentation-branch-projection-v2",
    branch_role: view === "delta" ? "shared" : view,
    branch_id: view === "delta" ? null : view,
    label: view === "control" ? "原始方案" : view === "treatment" ? "干预方案" : "方案差值",
    frame_id: frame.frame_id, sequence: frame.sequence,
    kind: frame.kind === "policy" ? "setup" : frame.kind === "wave" ? "round" : frame.kind,
    round: null, title: frame.title, summary: frame.summary,
    map_projection: {
      mode: view === "delta" ? "difference" : "absolute",
      fill_metric: "province_nev_development_index", unit: "模拟指数",
      camera: { longitude: 104.5, latitude: 35.5, zoom: 3.35, pitch: 12, bearing: 0 },
      enabled_overlays: ["coordination", "negotiation", "event"],
    },
    province_values: values,
    overlay_records,
    key_changes: [], metric_summary,
    evidence_refs: frame.evidence_refs, source_event_ids: frame.event_plan_ids,
    source_hash: frame.source_hash,
  };
}

function Launch({ catalog, collection }: {
  catalog: Awaited<ReturnType<typeof m34Api.eventCatalog>>;
  collection: PresentationMapCollection;
}) {
  const introEnabled = new URLSearchParams(location.search).get("intro") !== "0";
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [launchPhase, setLaunchPhase] = useState<LaunchPhase>(introEnabled ? "intro" : "dialog");
  const [introVisible, setIntroVisible] = useState(introEnabled);
  const [step, setStep] = useState<ReviewStep>("configuration");
  const [tab, setTab] = useState<LaunchTab>("policy");
  const [draft, setDraft] = useState<M34Draft | null>(null);
  const [shares, setShares] = useState({ ...CACHED_TREATMENT_SHARES });
  const [events, setEvents] = useState<M34EventSelection[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogTimerRef = useRef<number | null>(null);
  useEffect(() => () => {
    if (dialogTimerRef.current !== null) window.clearTimeout(dialogTimerRef.current);
  }, []);
  const revealControls = () => setLaunchPhase((phase) => phase === "intro" ? "controls" : phase);
  const finishIntro = () => {
    setIntroVisible(false);
    revealControls();
    if (dialogTimerRef.current !== null) window.clearTimeout(dialogTimerRef.current);
    dialogTimerRef.current = window.setTimeout(() => setLaunchPhase("dialog"), reducedMotion ? 120 : 900);
  };
  const addEvent = () => {
    const template = catalog.templates.find((item) => !events.some((event) => event.template.template_id === item.template_id));
    if (!template || events.length >= 3) return;
    setEvents([...events, {
      selectionId: crypto.randomUUID(), template, scheduledTick: "Q2", releaseWave: "wave_0",
      branchScope: "both", intensity: "medium", advanceNotice: false,
    }]);
  };
  const updateEvent = (index: number, patch: Partial<M34EventSelection>) => setEvents(
    events.map((event, itemIndex) => itemIndex === index ? { ...event, ...patch } : event),
  );
  const configure = async () => {
    setBusy(true); setError(null);
    try {
      const scopes = new Set(events.map((event) => event.branchScope));
      if (scopes.size > 1) throw new Error("同一实验的事件必须统一作用于双分支或仅干预方案。");
      const next = await m34Api.createDraft({
        operationId: crypto.randomUUID(), westShare: shares.west / 100,
        centralShare: shares.central / 100, eastShare: shares.east / 100, events,
      });
      setDraft(next);
      await m34Api.confirmInterpretation(next);
      setStep("design");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "创建实验失败"); }
    finally { setBusy(false); }
  };
  const advance = async () => {
    if (!draft) return;
    setBusy(true); setError(null);
    try {
      await m34Api.confirmDesign(draft);
      await m34Api.confirmBaseline(draft);
      window.location.assign(`/experiments/${draft.experimentId}/present`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "确认失败"); }
    finally { setBusy(false); }
  };
  const titles: Record<ReviewStep, string> = {
    configuration: "配置年度实验",
    design: "确认同源 A/B 设计",
  };
  return <main className="launch-stage launch-control-stage">
    <PrelaunchControlBoard collection={collection} phase={launchPhase} />
    {introVisible ? <GlobeIntro collection={collection} onComplete={finishIntro} onError={(message) => setError(message)} onHandoff={revealControls} reducedMotion={reducedMotion} runId={1} /> : null}
    {launchPhase === "dialog" ? <div className="launch-dim" /> : null}
    {launchPhase === "dialog" ? <section aria-labelledby="launch-dialog-title" aria-modal="true" className="launch-card launch-modal" role="dialog">
      <header><div><small>年度同源政策实验</small><h1 id="launch-dialog-title">{titles[step]}</h1></div><b>{step === "configuration" ? 1 : 2} / 2</b></header>
      {step === "configuration" ? <div className="launch-config-grid">
        <nav aria-label="实验配置" className="launch-tabs">
          <button className={tab === "policy" ? "active" : ""} onClick={() => setTab("policy")} type="button"><SlidersHorizontal /><span>政策比例</span></button>
          <button className={tab === "event" ? "active" : ""} onClick={() => setTab("event")} type="button"><Lightning /><span>突发事件</span>{events.length ? <b>{events.length}</b> : null}</button>
        </nav>
        <div className="launch-config-pane">
          {tab === "policy" ? <section><h2>干预方案中央承担比例</h2>{(["west", "central", "east"] as const).map((key, index) => <label className="share-row" key={key}><span>{["西部", "中部", "东部"][index]}</span><input max="100" min="0" onChange={(event) => setShares({ ...shares, [key]: Number(event.target.value) })} type="range" value={shares[key]} /><strong>{shares[key]}%</strong></label>)}</section> : null}
          {tab === "event" ? <section className="event-config"><header><h2>外生事件 <small>{events.length} / 3</small></h2><button onClick={addEvent} type="button">添加事件</button></header>{events.length ? events.map((selection, index) => <article key={selection.selectionId}><select onChange={(event) => { const template = catalog.templates.find((item) => item.template_id === event.target.value); if (template) updateEvent(index, { template }); }} value={selection.template.template_id}>{catalog.templates.map((template) => <option key={template.template_id} value={template.template_id}>{template.title}</option>)}</select><div><select aria-label="发生季度" onChange={(event) => updateEvent(index, { scheduledTick: event.target.value as MacroTick })} value={selection.scheduledTick}>{TICKS.map((tick) => <option key={tick}>{tick}</option>)}</select><select aria-label="释放阶段" onChange={(event) => updateEvent(index, { releaseWave: event.target.value as M34EventSelection["releaseWave"] })} value={selection.releaseWave}>{Object.entries(WAVE_DISPLAY).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button aria-label="删除事件" onClick={() => setEvents(events.filter((_, itemIndex) => itemIndex !== index))} type="button"><X /></button></div><div className="event-options"><select aria-label="事件作用范围" onChange={(event) => updateEvent(index, { branchScope: event.target.value as M34EventSelection["branchScope"] })} value={selection.branchScope}><option value="both">两套方案</option><option value="treatment_only">仅干预方案</option></select><select aria-label="事件强度" onChange={(event) => updateEvent(index, { intensity: event.target.value as M34EventSelection["intensity"] })} value={selection.intensity}><option value="low">低强度</option><option value="medium">中强度</option><option value="high">高强度</option></select><label><input checked={selection.advanceNotice} onChange={(event) => updateEvent(index, { advanceNotice: event.target.checked })} type="checkbox" />提前通知</label></div></article>) : <p>无事件时进行纯政策方案比较。</p>}</section> : null}
        </div>
      </div> : <div className="launch-review"><small>唯一主动差异</small><h2>{`原始方案 95 / 90 / 85，干预方案 ${shares.west} / ${shares.central} / ${shares.east}`}</h2></div>}
      {error ? <p className="launch-error">{error}</p> : null}
      <footer><span>原始方案 <b>95 / 90 / 85</b></span><span>干预方案 <b>{shares.west} / {shares.central} / {shares.east}</b></span><button disabled={busy} onClick={() => void (step === "configuration" ? configure() : advance())} type="button">{busy ? "正在确认…" : step === "configuration" ? "生成实验设计" : "确认并进入推演"}<ArrowRight /></button></footer>
    </section> : null}
  </main>;
}

function causalMapFrame(
  frame: M34Frame,
  view: BranchView,
  activeBeat: number,
  spotlight: PresentationSpotlightV4 | null,
  revealedCount: number,
): PresentationMapFrame {
  const base = mapFrame(frame, view, activeBeat, spotlight);
  if (view === "delta") return base;
  const source = view === "control" ? frame.branches.control : frame.branches.treatment;
  const sessions = new Map<string, typeof source.game_edges>();
  for (const edge of source.game_edges) {
    const key = edge.session_id ?? edge.edge_id;
    sessions.set(key, [...(sessions.get(key) ?? []), edge]);
  }
  const visibleEdges = Array.from(sessions.values())
    .map((edges) => [...edges].sort((left, right) => left.message_order - right.message_order))
    .sort((left, right) => (left[0]?.reveal_order ?? 0) - (right[0]?.reveal_order ?? 0))
    .flatMap((edges) => {
      const eventEdge = edges.find((edge) => edge.relation === "event_impact");
      if (eventEdge) return activeBeat >= 1 ? [eventEdge] : [];
      if (activeBeat < 3 || (edges[0]?.reveal_order ?? 0) >= revealedCount) return [];
      if (activeBeat === 3) return [edges.find((edge) => edge.relation === "proposal") ?? edges[0]!];
      return [edges.at(-1)!];
    });
  return {
    ...base,
    overlay_records: visibleEdges.map((edge) => {
      const provincePair = edge.source.subject_type === "province" && edge.target.subject_type === "province";
      const kind: PresentationOverlayKind = edge.relation === "event_impact"
        ? "event" : provincePair ? "coordination" : "negotiation";
      return {
        schema_version: "presentation-overlay-record-v2",
        overlay_id: edge.edge_id,
        kind,
        source_subject: edge.source.subject_ref,
        target_subject: edge.target.subject_ref,
        status: edge.relation_label,
        weight: edge.weight,
        label: `${edge.source.display_name} → ${edge.target.display_name} · ${edge.relation_label}`,
        style_semantic: edge.relation === "event_impact" ? "event" : provincePair ? "coordination" : "evidence",
        relation_semantic: edge.relation,
        line_style: edge.line_style,
        emphasized: Boolean(spotlight && edge.session_id === spotlight.session_id),
        session_id: edge.session_id,
        reveal_order: edge.reveal_order,
        message_order: edge.message_order,
        evidence_refs: edge.evidence_refs,
      };
    }),
  };
}

function automakerSubjectId(subjectRef: string): string | null {
  return subjectRef.startsWith("automaker:") ? subjectRef.slice(10) : null;
}

function SpotlightPanel({ spotlight, spotlights, spotlightIndex, onSpotlight, activeBeat, demoMode }: {
  spotlight: PresentationSpotlightV4 | null;
  spotlights: PresentationSpotlightV4[];
  spotlightIndex: number;
  onSpotlight: (index: number) => void;
  activeBeat: number;
  demoMode: boolean;
}) {
  if (!spotlight) return <section className="game-panel empty-game"><Target /><h2>等待主体互动</h2><p>当前节点没有新的交易关系，地图展示已冻结世界状态。</p></section>;
  const beat = spotlight.beats[activeBeat] ?? spotlight.beats[0]!;
  const isEvent = spotlight.actor.subject_type === "event";
  return <section className="game-panel">
    <header><small>当前互动阶段：{beat.label}</small><span className={`state-chip state-${spotlight.response?.state ?? spotlight.action.state}`}>{spotlight.response?.state_label ?? spotlight.action.state_label}</span></header>
    {spotlights.length > 1 ? <nav className="spotlight-switch" aria-label="本轮互动关系"><span>本轮 {spotlights.length} 组并行互动</span><div>{spotlights.map((item, index) => <button className={index === spotlightIndex ? "active" : ""} key={item.spotlight_id} onClick={() => onSpotlight(index)} type="button"><b>{index + 1}</b><small>{item.actor.display_name} ↔ {item.counterpart.display_name}</small></button>)}</div></nav> : null}
    <article className="question-card beat-panel beat-panel-0"><b>本季度关键问题</b><p>{isEvent ? `${spotlight.actor.display_name}进入授权上下文后，${spotlight.counterpart.display_name}会如何重新评估？` : `${spotlight.actor.display_name}如何在资源约束下与${spotlight.counterpart.display_name}形成可执行合作？`}</p></article>
    <article className="beat-panel beat-panel-1"><b>{isEvent ? "事件如何传导" : `${spotlight.actor.display_name}为何行动`}</b><ul><li>{spotlight.objective}</li><li>{spotlight.strongest_constraint}</li>{spotlight.observed_facts.slice(0, 2).map((item) => <li key={item}>{item}</li>)}</ul></article>
    <article className="decision-ledger beat-panel beat-panel-2">
      <header><div><small>实际选择</small><b>{spotlight.decision_summary}</b></div><span>{spotlight.engagement_label}</span></header>
      <div><section><small>考虑过的替代项</small>{spotlight.alternatives.slice(0, 3).length ? <ul>{spotlight.alternatives.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul> : <p>未记录其他可执行替代项。</p>}</section><section><small>机会成本</small>{spotlight.opportunity_costs.length ? <ul>{spotlight.opportunity_costs.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul> : <p>未产生额外资源占用。</p>}</section></div>
      <footer><small>重新考虑条件</small><p>{spotlight.reconsideration_conditions.join("；") || "需出现新的授权消息、事件或季度结果。"}</p></footer>
    </article>
    <article className="game-action action-proposal beat-panel beat-panel-3"><header><b>{spotlight.actor.display_name} → {spotlight.counterpart.display_name}</b><span>{spotlight.action.state_label}</span></header><strong>{spotlight.action.label}</strong><p>{spotlight.action.summary}</p></article>
    <article className="game-action action-response beat-panel beat-panel-4"><header><b>{spotlight.counterpart.display_name}的回应</b><span>{spotlight.response?.state_label ?? "等待回应"}</span></header><p>{spotlight.response?.summary ?? "对方将在后续逻辑节点读取授权消息并回应。"}</p></article>
    <article className={`settlement-ledger beat-panel beat-panel-5 ${spotlight.settlement.contributed ? "contributed" : "excluded"}`}>
      <section><header><b><img alt="" className="semantic-icon" src="/assets/icons/consumer-demand.svg" />本次互动直接贡献</b><span>{spotlight.settlement.contributed ? "已进入环境贡献" : "未进入环境贡献"}</span></header><strong>{spotlight.settlement.direct_contribution_label}</strong><p>{spotlight.settlement.result_summary}</p></section>
      <section><header><b><img alt="" className="semantic-icon" src="/assets/icons/fiscal-pressure.svg" />本季度共享变化</b><span>{spotlight.tick === "Q1" ? "形成值" : "较上季度"}</span></header><div className="quarterly-change-grid">{spotlight.settlement.province_changes.map((item) => <div key={item.province_code}><small>{item.province_name}</small><b>{item.current_value.toFixed(2)}</b><span>{item.quarterly_change == null ? "本季形成" : `${item.quarterly_change >= 0 ? "+" : ""}${item.quarterly_change.toFixed(2)}`}</span></div>)}{spotlight.settlement.national_changes.map((item) => <div key={item.metric_id}><small>{metricIcon(item.metric_id) ? <img alt="" className="semantic-icon" src={metricIcon(item.metric_id)!} /> : null}{item.label}</small><b>{item.current_value.toFixed(2)}</b><span>{item.quarterly_change == null ? "本季形成" : `${item.quarterly_change >= 0 ? "+" : ""}${item.quarterly_change.toFixed(2)}`}</span></div>)}</div><p className="attribution-note">{spotlight.settlement.attribution_note}</p></section>
    </article>
    <footer><span>若要改变决定</span><p>{spotlight.reconsideration_conditions[0] ?? "需出现新的授权消息、事件或季度结果。"}</p>{spotlight.fallback ? <b className="fallback-chip">{demoMode ? "演示编排" : "规则接管"}</b> : null}</footer>
  </section>;
}

function ComparisonPanel({ frame, view }: { frame: M34Frame; view: BranchView }) {
  const control = frame.branches.control;
  const treatment = frame.branches.treatment;
  const divergenceLabels = {
    control_only: "仅原始方案发生",
    treatment_only: "仅干预方案发生",
    state_changed: "互动状态改变",
    decision_changed: "主体决定改变",
  } as const;
  if (view === "delta" && frame.kind !== "comparison") return <section className="game-panel comparison-panel"><header><small>方案分歧</small><span className="state-chip">同源对照</span></header><article className="question-card"><b>本节点发生了什么不同？</b><p>{frame.divergences.length ? "两套方案中的主体回应已经出现可见分歧。" : "当前节点尚未形成可见的主体互动分歧。"}</p></article>{frame.divergences.map((item) => <article className={`divergence-row divergence-${item.divergence_type}`} key={item.divergence_id}><header><b>{item.participants.map((subject) => subject.display_name).join(" ↔ ")}</b><span>{divergenceLabels[item.divergence_type]}</span></header><div><section><small>原始方案</small><strong>{item.control_state_label}</strong><p>{item.control_decision_summary}</p></section><section><small>干预方案</small><strong>{item.treatment_state_label}</strong><p>{item.treatment_decision_summary}</p></section></div></article>)}<footer><span>比较边界</span><p>差值视图不混合展示任一分支的私有互动关系。</p></footer></section>;
  return <section className="game-panel comparison-panel"><header><small>年度同源 A/B</small><span className="state-chip">Q4 已冻结</span></header><article className="question-card"><b>干预方案带来了什么变化？</b><p>两套方案从同一基线出发，表格直接比较环境计算的六项年度模拟指数。</p></article><div className="comparison-table"><header><span>指标</span><span>原始</span><span>干预</span><span>变化</span></header>{METRICS.map(([key, label]) => { const left = control.national_metrics[key]; const right = treatment.national_metrics[key]; const delta = right - left; const icon = metricIcon(key); return <div key={key}><b>{icon ? <img alt="" className="semantic-icon" src={icon} /> : null}{label}</b><span>{left.toFixed(2)}</span><span>{right.toFixed(2)}</span><strong className={delta > 0 ? "positive" : delta < 0 ? "negative" : "neutral"}>{delta > 0 ? "+" : ""}{delta.toFixed(2)}</strong></div>; })}</div>{frame.divergences.length ? <article><b>主体行为分歧</b>{frame.divergences.slice(0, 2).map((item) => <p key={item.divergence_id}>{item.summary}</p>)}</article> : null}<footer><span>同源证明</span><p>唯一主动差异来自已批准政策或冻结事件范围；所有最终指标由确定性环境计算。</p></footer></section>;
}

export function M34PresentationApp() {
  const [experimentId] = useState<string | null>(pathExperimentId);
  const [catalog, setCatalog] = useState<Awaited<ReturnType<typeof m34Api.eventCatalog>> | null>(null);
  const [collection, setCollection] = useState<PresentationMapCollection | null>(null);
  const [landmarks, setLandmarks] = useState<PresentationWorldLandmarks | null>(null);
  const [showBatteryLandmarks, setShowBatteryLandmarks] = useState(true);
  const [showIndustrialLandmarks, setShowIndustrialLandmarks] = useState(false);
  const [mapViewPreference, setMapViewPreference] = useState<MapViewPreference>("auto");
  const [mapViewMenuOpen, setMapViewMenuOpen] = useState(false);
  const [world, setWorld] = useState<M34World | null>(null);
  const [timeline, setTimeline] = useState<M34Timeline | null>(null);
  const [frame, setFrame] = useState<M34Frame | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const frameIndexRef = useRef(0);
  const [view, setView] = useState<BranchView>("treatment");
  const [activeBeat, setActiveBeat] = useState(0);
  const [spotlightIndex, setSpotlightIndex] = useState(0);
  const [sequenceSpotlightIndex, setSequenceSpotlightIndex] = useState<number | null>(null);
  const [revealedCount, setRevealedCount] = useState(0);
  const [sequenceCancelled, setSequenceCancelled] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [panel, setPanel] = useState<Panel>(null);
  const [selected, setSelected] = useState<ProvinceSelection | null>(null);
  const [busy, setBusy] = useState(false);
  const [mapFallback, setMapFallback] = useState(new URLSearchParams(location.search).get("mapFallback") === "1");
  const [error, setError] = useState<string | null>(null);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const worldStatus = world?.status;

  useEffect(() => {
    void m34Api.eventCatalog().then(setCatalog).catch(() => setError("事件目录加载失败"));
    void m34Api.worldLandmarks().then(setLandmarks).catch(() => setError("世界状态节点加载失败"));
    void fetch("/assets/china-causal-map.geojson").then((response) => response.json() as Promise<PresentationMapCollection>).then(setCollection).catch(() => setError("全国地图加载失败"));
  }, []);
  const refresh = useCallback(async (id: string, followLatest = true) => {
    const [nextWorld, nextTimeline] = await Promise.all([m34Api.state(id), m34Api.timeline(id)]);
    const index = followLatest ? Math.max(0, nextTimeline.nodes.length - 1) : Math.min(frameIndexRef.current, nextTimeline.nodes.length - 1);
    const nextFrame = await m34Api.frame(id, nextTimeline.nodes[index]!.node_id);
    setWorld(nextWorld); setTimeline(nextTimeline); setFrame(nextFrame); setFrameIndex(index); frameIndexRef.current = index;
  }, []);
  useEffect(() => { if (experimentId) void refresh(experimentId).catch(() => setError("实验加载失败")); }, [experimentId, refresh]);
  useEffect(() => {
    if (!experimentId || !world || world.status === "completed") return;
    const stream = new EventSource(m34Api.streamUrl(experimentId));
    const update = () => void refresh(experimentId, false);
    ["interaction.wave.completed", "environment.quarter.completed", "comparison.completed", "baseline.confirmed"].forEach((type) => stream.addEventListener(type, update));
    return () => stream.close();
  }, [experimentId, refresh, worldStatus]);
  useEffect(() => {
    if (!experimentId || !timeline?.nodes[frameIndex]) return;
    let active = true;
    void m34Api.frame(experimentId, timeline.nodes[frameIndex]!.node_id).then((next) => { if (active) { setFrame(next); setActiveBeat(0); setSpotlightIndex(0); } }).catch(() => setError("帧加载失败"));
    return () => { active = false; };
  }, [experimentId, frameIndex, timeline]);
  useEffect(() => {
    if (!playing || !frame) return;
    const branchSpotlightCount = view === "delta"
      ? 0
      : Math.min(3, (view === "control" ? frame.branches.control : frame.branches.treatment).spotlights.length);
    const duration = activeBeat === 3 && !reducedMotion
      ? Math.max(1450, branchSpotlightCount * 2300 + 350)
      : reducedMotion ? 900 : 1450;
    const timer = window.setTimeout(() => {
      if (activeBeat < 5) setActiveBeat(activeBeat + 1);
      else if (timeline && frameIndex < timeline.nodes.length - 1) { const next = frameIndex + 1; frameIndexRef.current = next; setFrameIndex(next); setActiveBeat(0); }
      else setPlaying(false);
    }, duration);
    return () => window.clearTimeout(timer);
  }, [activeBeat, frame, frameIndex, playing, reducedMotion, timeline, view]);
  useEffect(() => {
    setSequenceCancelled(false);
    setSequenceSpotlightIndex(null);
    setRevealedCount(activeBeat > 3 || reducedMotion ? 3 : 0);
  }, [activeBeat, frame?.frame_id, reducedMotion, view]);
  useEffect(() => {
    if (!frame || view === "delta" || activeBeat !== 3 || reducedMotion || sequenceCancelled) return;
    const spotlights = (view === "control" ? frame.branches.control : frame.branches.treatment).spotlights.slice(0, 3);
    if (!spotlights.length) return;
    const timers: number[] = [];
    spotlights.forEach((_, index) => {
      timers.push(window.setTimeout(() => {
        setSequenceSpotlightIndex(index);
        setRevealedCount(index);
      }, index * 2300));
      timers.push(window.setTimeout(() => setRevealedCount(index + 1), index * 2300 + 1450));
    });
    timers.push(window.setTimeout(() => {
      setSequenceSpotlightIndex(null);
      setRevealedCount(spotlights.length);
    }, spotlights.length * 2300 + 100));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [activeBeat, frame, reducedMotion, sequenceCancelled, view]);

  if (!catalog || !collection) return <main className="loading-stage"><span className="loader-ring" /><p>{error ?? "正在载入推演厅…"}</p></main>;
  if (!experimentId) return <Launch catalog={catalog} collection={collection} />;
  if (!timeline || !frame || !world) return <main className="loading-stage"><span className="loader-ring" /><p>{error ?? "正在载入季度冻结事实…"}</p></main>;

  const branch = view === "control" ? frame.branches.control : frame.branches.treatment;
  const demoMode = world.versions.demo_narrative === "m35-showcase-v1";
  const safeSpotlightIndex = Math.min(spotlightIndex, Math.max(0, branch.spotlights.length - 1));
  const displayedSpotlightIndex = sequenceSpotlightIndex ?? safeSpotlightIndex;
  const spotlight = view === "delta" ? null : branch.spotlights[displayedSpotlightIndex] ?? null;
  const visibleRelationCount = reducedMotion || activeBeat > 3 ? 3 : revealedCount;
  const currentMapFrame = causalMapFrame(frame, view, activeBeat, spotlight, visibleRelationCount);
  const scale = visualScale(frame, view);
  const completed = world.branches.control?.completed_ticks ?? [];
  const nextTick = TICKS.find((tick) => !completed.includes(tick)) ?? null;
  const selectFrame = (index: number) => { frameIndexRef.current = index; setFrameIndex(index); setPlaying(false); };
  const runNext = async () => {
    if (!experimentId || !nextTick) return;
    setBusy(true); setError(null);
    try { await m34Api.run(experimentId, nextTick); await refresh(experimentId); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "季度运行失败"); }
    finally { setBusy(false); }
  };
  const selectedValue = selected ? currentMapFrame.province_values.find((item) => item.province_code === selected.code)?.value ?? null : null;
  const focusSubjectRefs = spotlight ? [spotlight.actor.subject_ref, spotlight.counterpart.subject_ref] : [];
  const automakerTrackIds = Array.from(new Set(branch.spotlights.slice(0, 3).flatMap((item) => [
    automakerSubjectId(item.actor.subject_ref),
    automakerSubjectId(item.counterpart.subject_ref),
  ]).filter((id): id is string => Boolean(id))));
  const spotlightProvinceCode = focusSubjectRefs
    .find((subjectRef) => subjectRef.startsWith("province:"))
    ?.slice(9) ?? null;
  const mapSelectedCode = spotlightProvinceCode ?? selected?.code ?? null;
  const focusKey = `${frame.frame_id}:${view}:${activeBeat}:${displayedSpotlightIndex}`;
  const mapViewContext = {
    frameKind: frame.kind,
    branchView: view,
    hasSpotlight: Boolean(spotlight),
  } as const;
  const mapViewMode = resolveMapView({
    ...mapViewContext,
    preference: mapViewPreference,
    activeBeat,
  });
  const mapViewLockedReason = mapViewLockReason(mapViewContext);
  const sideHeightLabel = currentMapFrame.province_values.some((item) => item.value != null && Number.isFinite(item.value))
    ? "新能源汽车发展指数"
    : "当前互动强度（展示权重）";
  const interruptSequence = (index: number) => {
    setSequenceCancelled(true);
    setSequenceSpotlightIndex(null);
    setRevealedCount(Math.min(3, branch.spotlights.length));
    setSpotlightIndex(index);
    setPlaying(false);
  };
  const selectSession = (sessionId: string) => {
    const index = branch.spotlights.findIndex((item) => item.session_id === sessionId);
    if (index >= 0) interruptSequence(index);
  };
  const selectSubject = (subjectRef: string) => {
    const index = branch.spotlights.findIndex((item) => item.actor.subject_ref === subjectRef || item.counterpart.subject_ref === subjectRef);
    if (index >= 0) interruptSequence(index);
  };

  return <main className={`presentation-shell causal-stage beat-${activeBeat} frame-${frame.kind} map-view-${mapViewMode}`} data-map-view={mapViewMode}>
    {mapFallback
      ? <PresentationMapFallback automakerTrackIds={automakerTrackIds} collection={collection} focusKey={focusKey} focusSubjectRefs={focusSubjectRefs} frame={currentMapFrame} interactionMode={Boolean(branch.spotlights.length && activeBeat >= 1 && activeBeat <= 4)} landmarks={landmarks?.items ?? []} onError={setError} onSelect={setSelected} onSessionSelect={selectSession} onSubjectSelect={selectSubject} reducedMotion={reducedMotion} selectedCode={mapSelectedCode} showBatteryLandmarks={showBatteryLandmarks} showIndustrialLandmarks={showIndustrialLandmarks} viewMode={mapViewMode} visualScale={scale} />
      : <PresentationMap automakerTrackIds={automakerTrackIds} collection={collection} focusKey={focusKey} focusSubjectRefs={focusSubjectRefs} frame={currentMapFrame} interactionMode={Boolean(branch.spotlights.length && activeBeat >= 1 && activeBeat <= 4)} landmarks={landmarks?.items ?? []} onError={setError} onFatal={() => setMapFallback(true)} onSelect={setSelected} onSessionSelect={selectSession} onSubjectSelect={selectSubject} reducedMotion={reducedMotion} selectedCode={mapSelectedCode} showBatteryLandmarks={showBatteryLandmarks} showIndustrialLandmarks={showIndustrialLandmarks} viewMode={mapViewMode} visualScale={scale} />}
    <div className="stage-vignette" />
    <header className="causal-hud">
      <div className="brand-lockup"><span><Sparkle weight="fill" /></span><div><strong>13110</strong><small>新能源汽车产业协同推演</small></div></div>
      <div className="decision-question"><small>本季度关键问题</small><b>{frame.question}</b></div>
      <nav className="branch-switch" aria-label="方案视图"><button className={view === "control" ? "active" : ""} onClick={() => { setView("control"); setSpotlightIndex(0); }} type="button">原始方案</button><button className={view === "treatment" ? "active" : ""} onClick={() => { setView("treatment"); setSpotlightIndex(0); }} type="button">干预方案</button><button className={view === "delta" ? "active" : ""} onClick={() => { setView("delta"); setSpotlightIndex(0); }} type="button">差值</button></nav>
      <span className="fact-status"><i />{world.status === "completed" ? "年度事实已冻结" : `${frame.chapter_label} · 事实流在线`}</span>
    </header>

    <aside className="causal-spine" aria-label="因果链">
      <header><small>{frame.chapter_label}</small><b>{spotlight ? `${spotlight.actor.display_name} ↔ ${spotlight.counterpart.display_name}` : frame.title}</b></header>
      <div className="beat-list">{(spotlight?.beats ?? frameBeats(frame)).map((beat, index) => {
        const Icon = BEAT_ICONS[beat.beat];
        return <button className={`${index === activeBeat ? "active" : ""} ${index < activeBeat ? "passed" : ""}`} key={beat.beat} onClick={() => { setActiveBeat(index); setPlaying(false); }} type="button"><span><Icon /></span><div><b>{beat.label}</b><small>{beat.headline}</small><p>{beat.detail}</p></div></button>;
      })}</div>
      {nextTick ? <button className="run-quarter" disabled={busy} onClick={() => void runNext()} type="button"><small>{completed.length ? "下一季度" : "启动年度推演"}</small><b>{busy ? "正在冻结双分支…" : `运行 ${nextTick}`}</b><SkipForward weight="fill" /></button> : null}
    </aside>

    <div className="map-story-label"><small>{branch.spotlights.length > 1 ? `本轮互动网络 · ${branch.spotlights.length} 组并行` : "当前互动关系"}</small><b>{spotlight ? `${spotlight.actor.display_name} ↔ ${spotlight.counterpart.display_name}` : "全国世界状态"}</b><div><span className="legend-line proposal" />提议 <span className="legend-line counter" />反报价 <span className="legend-line settled" />达成 <span className="legend-line rejected" />拒绝</div></div>

    {frame.kind === "comparison" || view === "delta" ? <ComparisonPanel frame={frame} view={view} /> : <SpotlightPanel activeBeat={activeBeat} demoMode={demoMode} onSpotlight={interruptSequence} spotlight={spotlight} spotlightIndex={displayedSpotlightIndex} spotlights={branch.spotlights} />}

    <nav className="compact-dock" aria-label="探索工具"><button className={panel === "province" ? "active" : ""} onClick={() => setPanel(panel === "province" ? null : "province")} type="button"><MapPin /><span>省份</span></button><button className={panel === "evidence" ? "active" : ""} onClick={() => setPanel(panel === "evidence" ? null : "evidence")} type="button"><Database /><span>证据</span></button><button aria-expanded={mapViewMenuOpen} aria-label={`视角：${mapViewMode === "side" ? "因果侧视" : "全国俯视"}`} className={mapViewMenuOpen || mapViewMode === "side" ? "active" : ""} onClick={() => setMapViewMenuOpen((value) => !value)} type="button"><CubeFocus /><span>视角</span></button></nav>
    {mapViewMenuOpen ? <aside className="map-view-menu" aria-label="地图视角"><header><div><small>地图视角</small><b>{mapViewMode === "side" ? "因果侧视" : "全国俯视"}</b></div><CubeFocus /></header><div role="radiogroup" aria-label="地图视角模式">{([
      ["auto", "自动镜头", "行动、回应侧视；其余俯视"],
      ["top", "全国俯视", "保持全国空间与色阶判断"],
      ["side", "立体数据侧视", "以省域发展指数编码柱体高度"],
    ] as const).map(([value, label, description]) => <button aria-checked={mapViewPreference === value} className={mapViewPreference === value ? "active" : ""} disabled={value === "side" && Boolean(mapViewLockedReason)} key={value} onClick={() => { setMapViewPreference(value); setMapViewMenuOpen(false); }} role="radio" type="button"><i /><span><b>{label}</b><small>{description}</small></span></button>)}</div><footer>{mapViewLockedReason ?? "只改变展示镜头，不改变业务帧与模拟结果"}</footer></aside> : null}
    {mapViewMode === "side" ? <div className="map-view-status"><CubeFocus /><span><small>{`柱高：${sideHeightLabel}`}</small><b>立体数据侧视 · {BEAT_LABELS[activeBeat] ?? "当前互动"}</b></span></div> : null}
    {panel ? <aside className="evidence-sheet"><header><div><small>{frame.chapter_label}</small><h2>{panel === "province" ? "省域探索" : "方法与证据"}</h2></div><button onClick={() => setPanel(null)} type="button"><X /></button></header>{panel === "province" ? <>{selected ? <div className="province-focus"><small>已选择省份</small><h3>{selected.name}</h3><strong>{selectedValue?.toFixed(2) ?? "—"}</strong><span>{view === "delta" ? "模拟指数变化" : "新能源汽车发展指数"}</span></div> : <p>点击地图中的省份，查看当前方案与季度的冻结结果。</p>}</> : <><dl><div><dt>时间语义</dt><dd>四个模拟季度与三次逻辑互动机会</dd></div><div><dt>数据属性</dt><dd>代理数据基线</dd></div><div><dt>世界计算</dt><dd>确定性季度环境</dd></div><div><dt>{demoMode ? "演示编排" : "规则接管"}</dt><dd>{branch.fallback_count} 个当前重点主体</dd></div></dl><p>研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。</p></>}</aside> : null}

    <section className="quarter-timeline">
      <div className="transport"><button disabled={frameIndex === 0} onClick={() => selectFrame(Math.max(0, frameIndex - 1))} type="button"><SkipBack /></button><button className="play" onClick={() => setPlaying(!playing)} type="button">{playing ? <Pause /> : <Play />}</button><button disabled={frameIndex === timeline.nodes.length - 1} onClick={() => selectFrame(Math.min(timeline.nodes.length - 1, frameIndex + 1))} type="button"><SkipForward /></button></div>
      <div className="quarter-track"><div className="quarter-bands">{TICKS.map((tick) => <span key={tick}><b>{tick}</b><small>{TICK_LABELS[tick]}</small></span>)}</div><div className="timeline-line"><i style={{ width: `${timeline.nodes[frameIndex]!.timeline_position * 100}%` }} />{timeline.nodes.map((node, index) => <button aria-label={node.title} className={`${index <= frameIndex ? "passed" : ""} ${index === frameIndex ? "current" : ""} node-${node.kind}`} key={node.node_id} onClick={() => selectFrame(index)} style={{ left: `${node.timeline_position * 100}%` }} title={node.title} type="button"><span>{node.title}</span></button>)}</div><footer><span>{frame.title}</span><b>{timeline.disclaimer}</b></footer></div>
    </section>

    <div className="semantic-scale"><header><span>{view === "delta" ? "模拟指数变化" : "新能源汽车发展指数"}</span><b>年度共享尺度</b></header><div className={`scale-bar ${view === "delta" ? "diverging" : "absolute"}`} />{view === "delta" ? <footer><span>干预方案较低</span><span>无变化</span><span>干预方案较高</span></footer> : <footer><span>{frame.shared_scale.low_label}</span><span>{frame.shared_scale.midpoint_label}</span><span>{frame.shared_scale.high_label}</span></footer>}</div>
    <div className="world-landmark-legend" aria-label="世界状态节点"><button aria-pressed={showBatteryLandmarks} className={showBatteryLandmarks ? "active" : ""} onClick={() => setShowBatteryLandmarks((value) => !value)} type="button"><img alt="" src="/assets/icons/battery-capability.svg" /><span>电池能力</span><b>{landmarks?.items.filter((item) => item.kind === "battery_capability").length ?? 0}</b></button><button aria-pressed={showIndustrialLandmarks} className={showIndustrialLandmarks ? "active" : ""} onClick={() => setShowIndustrialLandmarks((value) => !value)} type="button"><img alt="" src="/assets/icons/industrial-facility.svg" /><span>产业节点</span><b>{landmarks?.items.filter((item) => item.kind === "industrial_facility").length ?? 0}</b></button><small>代理数据基线 · 数量为冻结节点，非产能</small></div>
    <div className="data-boundary"><img alt="" src="/assets/icons/fiscal-pressure.svg" />代理数据基线 · {demoMode ? "Luna 叙事校准 / Fake 演示" : world.versions.agent_provider_mode === "live" ? "在线模型" : world.versions.agent_provider_mode === "cache" ? world.versions.agent_provider_miss_mode === "live" ? "缓存优先（缺失时 DeepSeek 补齐）" : "验证缓存（缺失时规则接管）" : "FAKE / FALLBACK"} · 31 省参与推演</div>
    {error ? <div className="stage-error"><Info />{error}<button onClick={() => setError(null)} type="button"><X /></button></div> : null}
  </main>;
}
