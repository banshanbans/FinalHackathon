import {
  Buildings,
  Check,
  Database,
  Info,
  Lightning,
  ListBullets,
  MapPin,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  Sparkle,
  X,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  PresentationMapFrame,
  PresentationOverlayKind,
} from "./contracts";
import { m34Api } from "./m34Api";
import type {
  BranchView,
  M34Configuration,
  M34Draft,
  M34EventSelection,
  M34Frame,
  M34InteractionMarket,
  M34Timeline,
  M34World,
  MacroTick,
} from "./m34Contracts";
import { PresentationMap } from "./PresentationMap";
import { PresentationMapFallback } from "./PresentationMapFallback";
import { scaleLabel, visualScaleForFrame } from "./mapScale";
import type { PresentationMapCollection } from "./tech-spike/types";

type ReviewStep = "configuration" | "interpretation" | "design" | "baseline";
type Panel = "interactions" | "method" | "province";

const TICKS: MacroTick[] = ["Q1", "Q2", "Q3", "Q4"];
const TICK_LABELS: Record<MacroTick, string> = {
  Q1: "第一季度",
  Q2: "第二季度",
  Q3: "第三季度",
  Q4: "第四季度",
};
const WAVE_LABELS = { wave_0: "Wave 0", wave_1: "Wave 1", wave_2: "Wave 2" } as const;
const METRICS = [
  ["regional_development_gap", "区域发展差距"],
  ["central_fiscal_burden", "中央财政负担"],
  ["local_fiscal_pressure", "地方财政压力"],
  ["nev_demand", "新能源汽车需求"],
  ["new_investment_concentration", "新增投资集中度"],
  ["industrial_agglomeration", "产业集聚度"],
] as const;

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

function mapFrame(frame: M34Frame, view: BranchView): PresentationMapFrame {
  const metrics = frame.branches;
  const values = frame.province_values.map((item) => ({
    province_code: item.province_code,
    value: view === "control" ? item.control : view === "treatment" ? item.treatment : item.delta,
    missing: view === "control"
      ? item.control == null
      : view === "treatment" ? item.treatment == null : item.delta == null,
    data_quality: "proxy" as const,
  }));
  const spotlight = new Set(frame.spotlight_session_ids);
  const overlay_records = frame.interactions
    .filter((item) => spotlight.has(item.session_id))
    .map((item) => {
      const provincePair = item.participants.every((participant) => /^\d{2}$/.test(participant));
      const kind: PresentationOverlayKind = provincePair ? "coordination" : "negotiation";
      return {
        schema_version: "presentation-overlay-record-v2" as const,
        overlay_id: item.session_id,
        kind,
        source_subject: item.participants[0]!,
        target_subject: item.participants[1]!,
        status: item.state,
        weight: Math.min(1, 0.25 + item.message_count * 0.15),
        label: `${item.participants.join(" ↔ ")} · ${item.state}`,
        style_semantic: provincePair ? "coordination" as const : "evidence" as const,
        evidence_refs: [`session:${item.session_id}`],
      };
    });
  const metric_summary = METRICS.map(([key, label]) => {
    const control = metrics.control.national_metrics[key];
    const treatment = metrics.treatment.national_metrics[key];
    return {
      metric_id: key,
      label,
      value: view === "control" ? control : view === "treatment" ? treatment : treatment - control,
      unit: "模拟指数",
      delta: view === "delta" ? treatment - control : null,
      evidence_refs: frame.evidence_refs,
    };
  });
  return {
    schema_version: "presentation-branch-projection-v2",
    branch_role: view === "delta" ? "shared" : view,
    branch_id: view === "delta" ? null : view,
    label: view === "control" ? "原始方案" : view === "treatment" ? "干预方案" : "方案差值",
    frame_id: frame.frame_id,
    sequence: frame.sequence,
    kind: frame.kind === "policy" ? "setup" : frame.kind === "wave" ? "round" : frame.kind,
    round: null,
    title: frame.title,
    summary: frame.summary,
    map_projection: {
      mode: view === "delta" ? "difference" : "absolute",
      fill_metric: "province_nev_development_index",
      unit: "模拟指数",
      camera: { longitude: 104.5, latitude: 35.5, zoom: 3.35, pitch: 15, bearing: 0 },
      enabled_overlays: ["coordination", "negotiation"],
    },
    province_values: values,
    overlay_records,
    key_changes: [],
    metric_summary,
    evidence_refs: frame.evidence_refs,
    source_event_ids: frame.event_plan_ids,
    source_hash: frame.source_hash,
  };
}

function EventEditor({
  catalog,
  events,
  onChange,
}: {
  catalog: Awaited<ReturnType<typeof m34Api.eventCatalog>>;
  events: M34EventSelection[];
  onChange: (events: M34EventSelection[]) => void;
}) {
  const update = (index: number, patch: Partial<M34EventSelection>) => {
    onChange(events.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  };
  const add = () => {
    const template = catalog.templates.find(
      (item) => !events.some((selection) => selection.template.template_id === item.template_id),
    );
    if (!template || events.length >= 3) return;
    onChange([...events, {
      selectionId: crypto.randomUUID(),
      template,
      scheduledTick: "Q2",
      releaseWave: "wave_0",
      branchScope: "both",
      intensity: "medium",
      advanceNotice: false,
    }]);
  };
  return <div className="m34-event-editor">
    <header><span>外生事件 <b>{events.length} / 3</b></span><button disabled={events.length >= 3} onClick={add} type="button">+添加事件</button></header>
    {!events.length ? <div className="m34-empty-event">当前为无事件政策比较</div> : null}
    {events.map((selection, index) => <article key={selection.selectionId}>
      <div className="m34-event-title"><b>事件 {index + 1}</b><button aria-label="删除事件" onClick={() => onChange(events.filter((_, itemIndex) => itemIndex !== index))} type="button"><X /></button></div>
      <label><span>情景</span><select onChange={(event) => { const template = catalog.templates.find((item) => item.template_id === event.target.value); if (template) update(index, { template }); }} value={selection.template.template_id}>{catalog.templates.map((item) => <option disabled={events.some((candidate, candidateIndex) => candidateIndex !== index && candidate.template.template_id === item.template_id)} key={item.template_id} value={item.template_id}>{item.title}</option>)}</select></label>
      <div className="m34-event-grid">
        <label><span>季度</span><select onChange={(event) => update(index, { scheduledTick: event.target.value as MacroTick })} value={selection.scheduledTick}>{TICKS.map((tick) => <option key={tick} value={tick}>{tick}</option>)}</select></label>
        <label><span>释放 Wave</span><select onChange={(event) => update(index, { releaseWave: event.target.value as M34EventSelection["releaseWave"] })} value={selection.releaseWave}>{Object.entries(WAVE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label><span>分支范围</span><select onChange={(event) => update(index, { branchScope: event.target.value as M34EventSelection["branchScope"] })} value={selection.branchScope}><option value="both">双方案相同事件</option><option value="treatment_only">仅干预方案</option></select></label>
        <label><span>强度</span><select onChange={(event) => update(index, { intensity: event.target.value as M34EventSelection["intensity"] })} value={selection.intensity}><option value="low">低</option><option value="medium">中</option><option value="high">高</option></select></label>
      </div>
      <label className="m34-checkbox"><input checked={selection.advanceNotice} onChange={(event) => update(index, { advanceNotice: event.target.checked })} type="checkbox" />提前通知授权主体</label>
    </article>)}
  </div>;
}

function Launch({
  catalog,
  busy,
  error,
  draft,
  step,
  onConfigure,
  onAdvance,
}: {
  catalog: Awaited<ReturnType<typeof m34Api.eventCatalog>>;
  busy: boolean;
  error: string | null;
  draft: M34Draft | null;
  step: ReviewStep;
  onConfigure: (configuration: M34Configuration) => void;
  onAdvance: () => void;
}) {
  const [west, setWest] = useState(98);
  const [central, setCentral] = useState(92);
  const [east, setEast] = useState(86);
  const [events, setEvents] = useState<M34EventSelection[]>([]);
  const scopes = new Set(events.map((item) => item.branchScope));
  const hasOilConflict = events.some((item) => item.template.template_id === "oil_price_rise")
    && events.some((item) => item.template.template_id === "oil_price_fall");
  const policyChanged = west !== 95 || central !== 90 || east !== 85;
  const eventCounterfactual = events.length > 0 && scopes.size === 1 && scopes.has("treatment_only");
  const valid = scopes.size <= 1 && !hasOilConflict
    && (events.length === 0 ? policyChanged : eventCounterfactual ? !policyChanged : policyChanged);
  const submit = () => onConfigure({
    operationId: crypto.randomUUID(),
    westShare: west / 100,
    centralShare: central / 100,
    eastShare: east / 100,
    events,
  });
  const titles = {
    configuration: "配置年度实验",
    interpretation: "确认中央政策解读",
    design: "确认季度 A/B 设计",
    baseline: "确认代理数据基线",
  };
  return <main className="m34-launch">
    <header className="m34-launch-brand"><span><Sparkle weight="fill" /></span><div><b>PolicyScope</b><small>政策涟漪 · 全国政策全景推演厅</small></div></header>
    <section className="m34-config-card glass-panel">
      <header><div><small>M34 季度事件驱动</small><h1>{titles[step]}</h1></div><b>{["configuration", "interpretation", "design", "baseline"].indexOf(step) + 1} / 4</b></header>
      {step === "configuration" ? <div className="m34-config-body">
        <section className="m34-share-section"><h2>干预方案中央承担比例</h2>{[["西部", west, setWest, 95], ["中部", central, setCentral, 90], ["东部", east, setEast, 85]].map(([label, value, setter, baseline]) => <label key={label as string}><span><b>{label as string}</b><small>参考 {baseline as number}%</small></span><input max="100" min="0" onChange={(event) => (setter as (value: number) => void)(Number(event.target.value))} type="range" value={value as number} /><strong>{value as number}%</strong></label>)}</section>
        <EventEditor catalog={catalog} events={events} onChange={setEvents} />
      </div> : <div className="m34-review">
        {step === "interpretation" ? <><small>中央 Agent · 实验前唯一一次</small><h2>{draft?.interpretation.public_summary}</h2><div>{draft?.interpretation.policy_goals.map((item) => <span key={item}>{item}</span>)}</div></> : null}
        {step === "design" ? <><small>时间权威：Q1–Q4 + 季度内 Wave</small><h2>{draft?.configuration.events.length ? `${draft.configuration.events.length} 个冻结事件` : "无事件政策对照"}</h2><div>{draft?.configuration.events.map((item) => <span key={item.selectionId}>{item.template.title} · {item.scheduledTick} / {WAVE_LABELS[item.releaseWave]}</span>)}</div></> : null}
        {step === "baseline" ? <><small>同源 A/B 起点</small><h2>31 省 + 10 家车企的年度资源包将被冻结</h2><div><span>代理数据基线</span><span>季度之间结转，不重置预算</span><span>中央不在季度内干预</span></div></> : null}
      </div>}
      {!valid && step === "configuration" ? <p className="m34-validation">{hasOilConflict ? "油价上涨与回落属于互斥事件。" : scopes.size > 1 ? "同一实验中的事件分支范围必须一致。" : eventCounterfactual ? "事件反事实要求两方案政策完全相同。" : "政策比较要求干预方案至少一档不同。"}</p> : null}
      {error ? <p className="m34-validation">{error}</p> : null}
      <footer><div><span>原始方案</span><b>95 / 90 / 85</b></div><div><span>干预方案</span><b>{west} / {central} / {east}</b></div><div><span>事件</span><b>{events.length} 个</b></div><button disabled={busy || (step === "configuration" && !valid)} onClick={step === "configuration" ? submit : onAdvance} type="button">{busy ? "正在冻结…" : step === "configuration" ? "生成中央政策解读" : step === "baseline" ? "确认基线并进入推演" : "确认并继续"}<Check /></button></footer>
    </section>
  </main>;
}

export function M34PresentationApp() {
  const [experimentId, setExperimentId] = useState<string | null>(pathExperimentId);
  const [catalog, setCatalog] = useState<Awaited<ReturnType<typeof m34Api.eventCatalog>> | null>(null);
  const [collection, setCollection] = useState<PresentationMapCollection | null>(null);
  const [world, setWorld] = useState<M34World | null>(null);
  const [timeline, setTimeline] = useState<M34Timeline | null>(null);
  const [frame, setFrame] = useState<M34Frame | null>(null);
  const [market, setMarket] = useState<M34InteractionMarket | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const frameIndexRef = useRef(0);
  const frameSelectionRevisionRef = useRef(0);
  const [view, setView] = useState<BranchView>("delta");
  const [panel, setPanel] = useState<Panel | null>(null);
  const [selected, setSelected] = useState<ProvinceSelection | null>(null);
  const [draft, setDraft] = useState<M34Draft | null>(null);
  const [step, setStep] = useState<ReviewStep>("configuration");
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [mapFallback, setMapFallback] = useState(new URLSearchParams(location.search).get("mapFallback") === "1");
  const [error, setError] = useState<string | null>(null);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    void m34Api.eventCatalog().then(setCatalog).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "事件目录加载失败"));
    void fetch("/assets/china-presentation-map.geojson")
      .then((response) => response.json() as Promise<PresentationMapCollection>)
      .then(setCollection)
      .catch(() => setError("全国地图加载失败"));
  }, []);

  useEffect(() => { frameIndexRef.current = frameIndex; }, [frameIndex]);

  const refresh = useCallback(async (id: string, followLatest = true) => {
    const selectionRevision = frameSelectionRevisionRef.current;
    const [nextWorld, nextTimeline, nextMarket] = await Promise.all([
      m34Api.state(id), m34Api.timeline(id), m34Api.interactions(id),
    ]);
    const lastIndex = Math.max(0, nextTimeline.nodes.length - 1);
    const index = followLatest ? lastIndex : Math.min(frameIndexRef.current, lastIndex);
    const nextFrame = await m34Api.frame(id, nextTimeline.nodes[index]!.node_id);
    if (!followLatest && selectionRevision !== frameSelectionRevisionRef.current) return;
    setWorld(nextWorld);
    setTimeline(nextTimeline);
    setMarket(nextMarket);
    frameIndexRef.current = index;
    setFrameIndex(index);
    setFrame(nextFrame);
  }, []);

  useEffect(() => {
    if (!experimentId) return;
    void refresh(experimentId).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "实验加载失败"));
  }, [experimentId, refresh]);

  useEffect(() => {
    if (!experimentId) return;
    const stream = new EventSource(m34Api.streamUrl(experimentId));
    const update = () => { void refresh(experimentId, false); };
    [
      "interaction.wave.completed",
      "environment.quarter.completed",
      "comparison.completed",
      "baseline.confirmed",
    ].forEach((type) => stream.addEventListener(type, update));
    return () => stream.close();
  }, [experimentId, refresh]);

  useEffect(() => {
    if (!playing || !timeline || timeline.nodes.length < 2) return;
    const timer = window.setInterval(() => setFrameIndex((current) => {
      if (current >= timeline.nodes.length - 1) { setPlaying(false); return current; }
      return current + 1;
    }), reducedMotion ? 1500 : 2300);
    return () => clearInterval(timer);
  }, [playing, reducedMotion, timeline]);

  useEffect(() => {
    if (!experimentId || !timeline?.nodes[frameIndex]) return;
    let active = true;
    void m34Api.frame(experimentId, timeline.nodes[frameIndex]!.node_id)
      .then((nextFrame) => { if (active) setFrame(nextFrame); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "帧加载失败"); });
    return () => { active = false; };
  }, [experimentId, frameIndex, timeline]);

  const configure = async (configuration: M34Configuration) => {
    setBusy(true); setError(null);
    try { const next = await m34Api.createDraft(configuration); setDraft(next); setStep("interpretation"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "创建失败"); }
    finally { setBusy(false); }
  };
  const advance = async () => {
    if (!draft) return;
    setBusy(true); setError(null);
    try {
      if (step === "interpretation") { await m34Api.confirmInterpretation(draft); setStep("design"); }
      else if (step === "design") { await m34Api.confirmDesign(draft); setStep("baseline"); }
      else { await m34Api.confirmBaseline(draft); history.replaceState({}, "", `/experiments/${draft.experimentId}/present`); setExperimentId(draft.experimentId); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "确认失败"); }
    finally { setBusy(false); }
  };
  const completed = world?.branches.control?.completed_ticks ?? [];
  const nextTick = TICKS.find((tick) => !completed.includes(tick)) ?? null;
  const runNext = async () => {
    if (!experimentId || !nextTick) return;
    setBusy(true); setError(null);
    try { await m34Api.run(experimentId, nextTick); await refresh(experimentId); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "季度运行失败"); }
    finally { setBusy(false); }
  };
  const currentMapFrame = useMemo(() => frame ? mapFrame(frame, view) : null, [frame, view]);
  const visualScale = useMemo(() => currentMapFrame ? visualScaleForFrame(currentMapFrame) : null, [currentMapFrame]);
  const selectedValue = selected && currentMapFrame
    ? currentMapFrame.province_values.find((item) => item.province_code === selected.code)?.value ?? null
    : null;
  const nodeMessages = market?.messages.filter((message) => !frame?.tick || message.tick === frame.tick)
    .filter((message) => !frame?.wave || message.wave === frame.wave) ?? [];

  if (!catalog || !collection) return <main className="loading-stage"><span className="loader-ring" /><p>{error ?? "正在载入 M34 推演厅…"}</p></main>;
  if (!experimentId) return <Launch catalog={catalog} busy={busy} draft={draft} error={error} onAdvance={() => void advance()} onConfigure={(configuration) => void configure(configuration)} step={step} />;
  if (!timeline || !frame || !currentMapFrame || !world) return <main className="loading-stage"><span className="loader-ring" /><p>{error ?? "正在载入季度冻结事实…"}</p></main>;

  return <main className="presentation-shell m34-hall">
    {mapFallback ? <PresentationMapFallback collection={collection} frame={currentMapFrame} onSelect={setSelected} selectedCode={selected?.code ?? null} visualScale={visualScale ?? undefined} /> : <PresentationMap collection={collection} frame={currentMapFrame} onError={setError} onFatal={() => setMapFallback(true)} onSelect={setSelected} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} visualScale={visualScale ?? undefined} />}
    <div className="stage-vignette" />
    <header className="top-hud glass-bar"><div className="brand-lockup"><span className="brand-mark"><Sparkle weight="fill" /></span><div><strong>PolicyScope</strong><small>政策涟漪 · 年度季度推演</small></div></div><nav className="segmented-control" aria-label="地图方案"><button className={view === "control" ? "active" : ""} onClick={() => setView("control")} type="button">原始方案</button><button className={view === "treatment" ? "active" : ""} onClick={() => setView("treatment")} type="button">干预方案</button><button className={view === "delta" ? "active" : ""} onClick={() => setView("delta")} type="button">差值</button></nav><div className="hud-actions"><span className={`live-chip ${world.status === "completed" ? "status-frozen" : ""}`}><i />{world.status === "completed" ? "年度已冻结" : "事实流在线"}</span></div></header>
    <section className="narrative-panel glass-panel m34-narrative"><div className="chapter-row"><span>{frame.tick ? `${frame.tick} ${frame.wave ? WAVE_LABELS[frame.wave] : ""}` : "年度基线"}</span><b>{String(frameIndex + 1).padStart(2, "0")} / {String(timeline.nodes.length).padStart(2, "0")}</b></div><h1>{frame.title}</h1><p>{frame.summary}</p><div className="m34-fact-grid"><div><span>互动会话</span><b>{frame.interactions.length}</b></div><div><span>重点互动</span><b>{frame.spotlight_session_ids.length}</b></div><div><span>Fallback</span><b>{timeline.nodes[frameIndex]?.fallback_count ?? 0}</b></div></div>{nextTick ? <button className="round-action" disabled={busy} onClick={() => void runNext()} type="button"><span><small>{completed.length ? "下一季度" : "启动年度推演"}</small><b>{busy ? "正在冻结双分支…" : `运行 ${nextTick}`}</b></span><SkipForward weight="fill" /></button> : <div className="m34-central-review"><small>中央 Agent · 实验后唯一一次</small><p>{world.central_review}</p></div>}{error ? <p className="round-error">{error}</p> : null}</section>
    <nav className="tool-dock glass-panel" aria-label="推演工具"><button aria-label="互动" className={panel === "interactions" ? "active" : ""} data-tooltip="互动" onClick={() => setPanel(panel === "interactions" ? null : "interactions")} type="button"><ListBullets /></button><button aria-label="省份" className={panel === "province" ? "active" : ""} data-tooltip="省份" onClick={() => setPanel(panel === "province" ? null : "province")} type="button"><MapPin /></button><button aria-label="方法与数据" className={panel === "method" ? "active" : ""} data-tooltip="方法与数据" onClick={() => setPanel(panel === "method" ? null : "method")} type="button"><Database /></button></nav>
    {panel ? <aside className="side-sheet glass-panel m34-sheet"><header><span className="sheet-icon">{panel === "interactions" ? <Lightning /> : panel === "province" ? <MapPin /> : <Database />}</span><div><small>{frame.title}</small><h2>{panel === "interactions" ? "互动下钻" : panel === "province" ? "省域结果" : "方法与数据"}</h2></div><button className="icon-button" onClick={() => setPanel(null)} type="button"><X /></button></header>{panel === "interactions" ? <><p className="sheet-lead">当前节点全部提议、回应与反报价</p>{nodeMessages.map((message) => <article className="m34-message" key={message.message_id}><header><b><em>{message.branch_id === "control" ? "原始" : "干预"}</em>{message.sender_id} → {message.recipient_ids.join(" / ")}</b><span>{message.transaction_state}</span></header><p>{message.public_summary}</p><small>{message.tick} · {WAVE_LABELS[message.wave]} · {message.kind}</small></article>)}{!nodeMessages.length ? <div className="empty-mini"><Info />当前节点没有交易消息</div> : null}</> : null}{panel === "province" ? <><p className="sheet-lead">{selected?.name ?? "点击地图选择省份"}</p>{selected ? <div className="metric-block"><small>新能源汽车发展指数</small><strong>{selectedValue?.toFixed(2) ?? "—"}</strong><span>{view === "delta" ? "方案差值" : view === "control" ? "原始方案" : "干预方案"}</span></div> : null}</> : null}{panel === "method" ? <><dl className="method-list"><div><dt>时间权威</dt><dd>Q1–Q4 + Wave 0–2</dd></div><div><dt>数据属性</dt><dd>代理数据基线</dd></div><div><dt>世界契约</dt><dd>world-state-v10</dd></div><div><dt>中央调用</dt><dd>{world.central_call_count} / 2</dd></div><div><dt>Fallback</dt><dd>{market?.fallback_count ?? 0}</dd></div><div><dt>预算状态</dt><dd>{market?.budget_exhausted ? "已触发上限" : "未耗尽"}</dd></div><div><dt>帧哈希</dt><dd>{frame.source_hash.slice(0, 14)}…</dd></div></dl><p className="method-note">研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。</p></> : null}</aside> : null}
    <section className="timeline-rail glass-panel m34-timeline"><div className="transport-controls"><button disabled={frameIndex === 0} onClick={() => { const index = Math.max(0, frameIndex - 1); frameIndexRef.current = index; frameSelectionRevisionRef.current += 1; setFrameIndex(index); }} type="button"><SkipBack /></button><button className="play-button" onClick={() => setPlaying((value) => !value)} type="button">{playing ? <Pause /> : <Play />}</button><button disabled={frameIndex === timeline.nodes.length - 1} onClick={() => { const index = Math.min(timeline.nodes.length - 1, frameIndex + 1); frameIndexRef.current = index; frameSelectionRevisionRef.current += 1; setFrameIndex(index); }} type="button"><SkipForward /></button></div><div className="timeline-track-wrap"><div className="m34-quarter-bands">{TICKS.map((tick) => <span key={tick}>{tick}<small>{TICK_LABELS[tick]}</small></span>)}</div><div className="timeline-track"><div className="timeline-progress" style={{ width: `${timeline.nodes[frameIndex]!.timeline_position * 100}%` }} />{timeline.nodes.map((node, index) => <button aria-label={node.title} className={`${index <= frameIndex ? "passed" : ""} ${index === frameIndex ? "current" : ""} kind-${node.kind}`} key={node.node_id} onClick={() => { frameIndexRef.current = index; frameSelectionRevisionRef.current += 1; setFrameIndex(index); setPlaying(false); }} style={{ left: `${node.timeline_position * 100}%` }} title={`${node.title}${node.wave ? ` · ${WAVE_LABELS[node.wave]}` : ""}`} type="button"><span>{node.title}</span></button>)}</div><div className="timeline-labels"><span>{frame.title}</span><b>{timeline.disclaimer}</b></div></div><div className="timeline-tools"><button onClick={() => setPanel("method")} type="button"><Info /></button></div></section>
    {visualScale ? <div className="map-legend"><span>{view === "delta" ? "发展指数差值" : "发展指数"}</span><div>{visualScale.stops.map(([, color], index) => <i key={`${color}-${index}`} style={{ background: color }} />)}</div><small>{scaleLabel(visualScale)}</small></div> : null}
    <div className="data-status"><Buildings />代理数据基线 · {world.versions.agent_provider_mode === "live" ? "在线模型" : "FAKE / FALLBACK"} · 全国版图完整 / 31 省计算</div>
  </main>;
}
