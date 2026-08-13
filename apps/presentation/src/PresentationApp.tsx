import {
  ArrowsOutLineHorizontal,
  Buildings,
  ChartLineUp,
  CirclesThreePlus,
  ClockCounterClockwise,
  Database,
  Factory,
  Handshake,
  Info,
  Stack,
  Lightning,
  MapPin,
  Pause,
  Play,
  Rewind,
  ShieldChevron,
  SkipBack,
  SkipForward,
  SlidersHorizontal,
  Sparkle,
  Strategy,
  X,
} from "@phosphor-icons/react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { presentationApi } from "./api";
import type { DemoDraft } from "./api";
import type {
  BranchRole,
  EventBranchScope,
  EventIntensity,
  EventTriggerPoint,
  PresentationCamera,
  PresentationComparison,
  PresentationEventCatalog,
  PresentationEventCatalogEntry,
  PresentationFrame,
  PresentationMapFrame,
  PresentationMode,
  PresentationOverlayKind,
  PresentationTimeline,
  PresentationWorldState,
  SimulationRound,
} from "./contracts";
import { PresentationMap } from "./PresentationMap";
import { PresentationMapFallback } from "./PresentationMapFallback";
import { LaunchExperience } from "./LaunchExperience";
import type { LaunchReviewStep } from "./LaunchExperience";
import { scaleLabel, visualScaleForFrame, visualScaleForFrames } from "./mapScale";
import {
  eventFamilyLabel,
  fillMetricLabel,
  mechanismChannelLabel,
  overlayStatusLabel,
  ROUND_LABELS,
} from "./presentationLabels";
import { GlobeIntro } from "./tech-spike/GlobeIntro";
import type { PresentationMapCollection } from "./tech-spike/types";

type DockPanel = "policy" | "event" | "province" | "automaker" | "competition" | "negotiation" | "coordination" | "decisions" | "result" | "method" | "layers";

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
  branchId?: "control" | "treatment";
}

const DOCK_ITEMS = [
  { id: "policy", label: "方案", Icon: SlidersHorizontal },
  { id: "event", label: "事件", Icon: Lightning },
  { id: "province", label: "省份", Icon: MapPin },
  { id: "automaker", label: "车企", Icon: Factory },
  { id: "competition", label: "竞争", Icon: Strategy },
  { id: "negotiation", label: "谈判", Icon: Handshake },
  { id: "coordination", label: "协同", Icon: CirclesThreePlus },
  { id: "decisions", label: "全部决策", Icon: Database },
  { id: "result", label: "结果", Icon: ChartLineUp },
  { id: "method", label: "方法", Icon: Database },
  { id: "layers", label: "图层", Icon: Stack },
] satisfies Array<{ id: DockPanel; label: string; Icon: typeof Stack }>;

const SEMANTIC_LABELS: Record<string, string> = {
  policy: "政策配置",
  event: "突发事件",
  competition: "省际竞争",
  negotiation: "政企谈判",
  coordination: "省际协同",
  result: "推演结果",
};

const ROUND_SEQUENCE: SimulationRound[] = [
  "province_initial",
  "automaker_initial",
  "province_revision",
  "automaker_negotiation",
  "province_counter_response",
  "automaker_final",
  "environment_settlement",
];

const BRANCH_RELATIONSHIP_PANELS = new Set<DockPanel>([
  "automaker",
  "competition",
  "negotiation",
  "coordination",
]);

const TRIGGER_LABELS: Record<EventTriggerPoint, string> = {
  before_province_initial: "省级首轮前",
  after_province_initial: "省级首轮后",
  after_automaker_initial: "车企首轮后",
};

const INTENSITY_LABELS: Record<EventIntensity, string> = {
  low: "低强度",
  medium: "中强度",
  high: "高强度",
};

const SCOPE_LABELS: Record<EventBranchScope, string> = {
  both: "双方案共同冲击",
  treatment_only: "仅干预方案冲击",
};

const SUBJECT_LABELS: Record<string, string> = {
  province: "省份",
  automaker: "车企",
  consumer: "消费端",
  environment: "确定性环境",
};

function pathExperimentId() {
  const match = window.location.pathname.match(/\/experiments\/([^/]+)\/present/);
  return match?.[1] ?? new URLSearchParams(window.location.search).get("experiment");
}

function modeLabel(mode: PresentationMode) {
  return { live: "实时推演", compare: "结果对照" }[mode];
}

function panelOverlays(frame: PresentationMapFrame | undefined, kind: PresentationOverlayKind) {
  return frame?.overlay_records.filter((item) => item.kind === kind) ?? [];
}

function mapFrame(
  frame: PresentationFrame,
  projection: PresentationFrame["shared_projection"],
): PresentationMapFrame | null {
  if (!projection) return null;
  return {
    ...projection,
    frame_id: frame.frame_id,
    sequence: frame.sequence,
    kind: frame.kind,
    round: frame.round,
    title: frame.title,
    summary: frame.summary,
  };
}

function regionalShares(world: PresentationWorldState | undefined) {
  const control = world?.design?.control_policy;
  const treatment = world?.design?.treatment_policy;
  if (!control || !treatment) return null;
  return {
    control: [
      control.west_central_share * 100,
      control.central_central_share * 100,
      control.east_central_share * 100,
    ],
    treatment: [
      treatment.west_central_share * 100,
      treatment.central_central_share * 100,
      treatment.east_central_share * 100,
    ],
  };
}

function DecisionIndex({ moments, threads }: {
  moments: PresentationFrame["decision_moments"];
  threads: PresentationFrame["interaction_threads"];
}) {
  const [branch, setBranch] = useState<"all" | BranchRole>("all");
  const [subject, setSubject] = useState<"all" | "province" | "automaker">("all");
  const [status, setStatus] = useState<"all" | "pending" | "responded" | "settled">("all");
  const [round, setRound] = useState<"all" | SimulationRound>("all");
  const [interaction, setInteraction] = useState<"all" | "competition" | "coordination" | "negotiation" | "topk">("all");
  const [evidenceMomentId, setEvidenceMomentId] = useState<string | null>(null);
  const interactionMoments = interaction === "all"
    ? null
    : new Set(threads.filter((item) => item.thread_type === interaction).flatMap((item) => item.moment_ids));
  const filtered = moments.filter((item) =>
    (branch === "all" || item.branch_role === branch)
    && (subject === "all" || item.actor.subject_type === subject)
    && (status === "all" || item.response_status === status)
    && (round === "all" || item.round === round)
    && (!interactionMoments || interactionMoments.has(item.moment_id)),
  );
  return <div className="decision-index">
    <p className="sheet-lead">全部决策轨迹 <b>{filtered.length}</b></p>
    <div className="decision-filters">
      <select aria-label="按分支筛选" onChange={(event) => setBranch(event.target.value as typeof branch)} value={branch}><option value="all">全部分支</option><option value="control">原始方案</option><option value="treatment">干预方案</option></select>
      <select aria-label="按主体筛选" onChange={(event) => setSubject(event.target.value as typeof subject)} value={subject}><option value="all">全部主体</option><option value="province">省份</option><option value="automaker">车企</option></select>
      <select aria-label="按回应状态筛选" onChange={(event) => setStatus(event.target.value as typeof status)} value={status}><option value="all">全部状态</option><option value="pending">待回应</option><option value="responded">已回应</option><option value="settled">已结算</option></select>
      <select aria-label="按轮次筛选" onChange={(event) => setRound(event.target.value as typeof round)} value={round}><option value="all">全部轮次</option>{ROUND_SEQUENCE.map((item) => <option key={item} value={item}>{ROUND_LABELS[item]}</option>)}</select>
      <select aria-label="按互动类型筛选" onChange={(event) => setInteraction(event.target.value as typeof interaction)} value={interaction}><option value="all">全部互动</option><option value="competition">竞争</option><option value="coordination">协同</option><option value="negotiation">谈判</option><option value="topk">重配</option></select>
    </div>
    <div className="decision-list">{filtered.map((item) => <article key={item.moment_id} tabIndex={0}>
      <header><b>{item.actor.display_name}</b><span>{item.branch_role === "control" ? "原始方案" : "干预方案"}</span></header>
      <p>{item.actual_choice}</p><footer><small>{ROUND_LABELS[item.round]} · {item.response_status === "pending" ? "待回应" : item.response_status === "settled" ? "已结算" : "已冻结"}</small><button onClick={() => setEvidenceMomentId((current) => current === item.moment_id ? null : item.moment_id)} type="button">Evidence {item.evidence_refs.length}</button></footer>
      {evidenceMomentId === item.moment_id ? <div className="decision-evidence" aria-label={`${item.actor.display_name} Evidence`}>{item.evidence_refs.length ? item.evidence_refs.map((ref) => <code key={ref}>{ref}</code>) : <span>当前决策没有额外 Evidence 引用</span>}</div> : null}
    </article>)}</div>
  </div>;
}

function GameSpotlight({ frame, selected, onSelect }: {
  frame: PresentationFrame;
  selected: number;
  onSelect: (index: number) => void;
}) {
  const spotlight = frame.spotlights[selected] ?? frame.spotlights[0];
  const [beatIndex, setBeatIndex] = useState(0);
  useEffect(() => setBeatIndex(0), [spotlight?.spotlight_id]);
  if (!spotlight) return <div className="spotlight-empty"><b>Game Spotlight</b><span>当前冻结帧尚无主体决策。</span></div>;
  const moment = frame.decision_moments.find((item) => item.moment_id === spotlight.primary_moment_id);
  const beat = spotlight.narrative_beats[beatIndex] ?? spotlight.narrative_beats[0];
  return <>
    <div className="spotlight-heading"><span>GAME SPOTLIGHT</span><b>{spotlight.score.total.toFixed(0)} / 100</b></div>
    <div className="spotlight-tabs" role="tablist">{frame.spotlights.map((item, index) => <button aria-selected={index === selected} className={index === selected ? "active" : ""} key={item.spotlight_id} onClick={() => onSelect(index)} role="tab" type="button">{item.rank === 1 ? "主镜头" : `辅助 ${item.rank - 1}`}<small>{item.label}</small></button>)}</div>
    <h1>{moment?.actor.display_name ?? spotlight.label}</h1>
    <p>{moment?.objective ?? frame.summary}</p>
    <div className="micro-beats" role="tablist" aria-label="微镜头节拍">{spotlight.narrative_beats.map((item, index) => <button aria-label={item.title} aria-selected={index === beatIndex} className={`${index === beatIndex ? "active" : ""} ${item.status}`} key={item.beat} onClick={() => setBeatIndex(index)} role="tab" type="button"><i />{item.title}</button>)}</div>
    {beat ? <article className={`beat-card ${beat.status}`}><small>{beat.status === "pending" ? "待回应" : "冻结事实"}</small><b>{beat.title}</b><p>{beat.detail}</p></article> : null}
    {beat?.beat === "options" && moment ? <div className="option-board">{moment.option_evaluations.map((option) => <div className={option.option_type === "chosen" ? "chosen" : ""} key={option.option_id}><span>{option.label}</span><b>{option.score == null ? "不可物化" : option.score.toFixed(1)}</b><small>{option.option_type === "chosen" ? "实际选择" : option.delta_from_chosen == null ? "决策时点评估" : `较实际 ${option.delta_from_chosen > 0 ? "+" : ""}${option.delta_from_chosen.toFixed(1)}`}</small></div>)}</div> : null}
  </>;
}

function SideSheet({ panel, frame, moments, threads, timeline, catalog, comparison, world, selected, onClose }: {
  panel: DockPanel;
  frame: PresentationMapFrame;
  moments: PresentationFrame["decision_moments"];
  threads: PresentationFrame["interaction_threads"];
  timeline: PresentationTimeline;
  catalog: PresentationEventCatalog;
  comparison: PresentationComparison | undefined;
  world: PresentationWorldState | undefined;
  selected: ProvinceSelection | null;
  onClose: () => void;
}) {
  const config = DOCK_ITEMS.find((item) => item.id === panel)!;
  const overlays = panel === "competition" || panel === "negotiation" || panel === "coordination"
    ? panelOverlays(frame, panel)
    : frame.overlay_records;
  const shares = regionalShares(world);
  return (
    <aside className="side-sheet glass-panel" aria-label={`${config.label}详情`}>
      <header>
        <span className="sheet-icon"><config.Icon weight="duotone" /></span>
        <div><small>当前冻结帧</small><h2>{config.label}</h2></div>
        <button aria-label="关闭详情" className="icon-button" onClick={onClose} type="button"><X /></button>
      </header>
      {panel === "policy" ? <>
        <p className="sheet-lead">同源 A/B 政策承担比例</p>
        {shares ? <>
          <div className="policy-grid"><b>原始方案</b><span>西部 {shares.control[0]}%</span><span>中部 {shares.control[1]}%</span><span>东部 {shares.control[2]}%</span></div>
          <div className="policy-grid treatment"><b>干预方案</b><span>西部 {shares.treatment[0]}%</span><span>中部 {shares.treatment[1]}%</span><span>东部 {shares.treatment[2]}%</span></div>
        </> : <div className="empty-mini"><SlidersHorizontal />实验设计尚未冻结</div>}
      </> : null}
      {panel === "event" ? <>
        <p className="sheet-lead">{timeline.event_markers.length ? "当前实验事件已冻结，触发边界不可修改。" : "当前实验未配置突发事件。"}</p>
        {catalog.templates.map((item) => {
          const active = timeline.event_markers.find((marker) => marker.template_id === item.template_id);
          return <article className={`event-catalog-row ${active ? "active" : ""}`} key={item.template_id}><div><b>{item.title}</b>{active ? <span>已冻结</span> : null}</div><small>{item.description}</small>{active ? <><em>{TRIGGER_LABELS[active.trigger_point]} · {INTENSITY_LABELS[active.intensity]} · {SCOPE_LABELS[active.branch_scope]}</em><div className="event-mechanism-tags"><span>影响主体：{item.affected_subjects.map((subject) => SUBJECT_LABELS[subject] ?? "其他主体").join(" / ")}</span><span>机制通道：{item.mechanism_channels.map(mechanismChannelLabel).join(" / ")}</span><span>结果方向：待验证</span></div></> : <em>{eventFamilyLabel(item.family)} · 可用情景</em>}</article>;
        })}
        <p className="method-note">{catalog.templates[0]?.disclaimer}</p>
      </> : null}
      {panel === "province" ? <>
        <p className="sheet-lead">{selected ? selected.name : "点击地图选择省份"}</p>
        {selected ? <div className="metric-block"><small>{fillMetricLabel(frame.map_projection.fill_metric)}</small><strong>{selected.value?.toFixed(2) ?? "—"}</strong><span>{frame.map_projection.unit}{selected.branchId ? ` · ${selected.branchId === "control" ? "原始方案" : "干预方案"}` : ""}</span></div> : <div className="empty-mini"><MapPin />省域行动将在此渐进展开</div>}
      </> : null}
      {panel === "automaker" ? <>
        <p className="sheet-lead">代理数据基线 / 模拟车企行动</p>
        {panelOverlays(frame, "automaker").slice(0, 6).map((item) => <article className="sheet-row" key={item.overlay_id}><b>{item.label}</b><span>{overlayStatusLabel(item.status)}</span></article>)}
        {!panelOverlays(frame, "automaker").length ? <div className="empty-mini"><Factory />当前帧没有新增车企行动</div> : null}
      </> : null}
      {panel === "competition" || panel === "negotiation" || panel === "coordination" ? <>
        <p className="sheet-lead">{SEMANTIC_LABELS[panel]}只展示冻结关系，不补算新行动。</p>
        {overlays.slice(0, 8).map((item) => <article className="sheet-row" key={item.overlay_id}><b>{item.label}</b><span>{overlayStatusLabel(item.status)}</span></article>)}
        {!overlays.length ? <div className="empty-mini"><ShieldChevron />当前帧暂无该类关系</div> : null}
      </> : null}
      {panel === "decisions" ? <DecisionIndex moments={moments} threads={threads} /> : null}
      {panel === "result" ? <>
        <p className="sheet-lead">{comparison?.conclusion ?? "结果只来自权威环境投影"}</p>
        {comparison ? <div className="compare-verdict"><span>GAP {comparison.gap_direction === "narrowed" ? "收窄" : comparison.gap_direction === "widened" ? "扩大" : "持平"}</span><strong>Δ {comparison.delta_gap > 0 ? "+" : ""}{comparison.delta_gap.toFixed(2)}</strong><small>{comparison.fiscal_tradeoff}</small><div><b>受益</b>{comparison.top_beneficiaries.slice(0, 3).join(" / ")}</div><div><b>承压</b>{comparison.top_pressured.slice(0, 3).join(" / ")}</div></div> : null}
        <div className="result-stack">{frame.metric_summary.map((metric) => <div key={metric.metric_id}><span>{metric.label}</span><strong>{metric.value.toFixed(2)} {metric.unit}</strong><small>{metric.delta == null ? "冻结值" : `Δ ${metric.delta > 0 ? "+" : ""}${metric.delta.toFixed(2)}`}</small></div>)}</div>
        {comparison?.mechanism_chains.slice(0, 3).map((chain) => <article className={`mechanism-chain ${chain.category}`} key={chain.title}><header><b>{chain.title}</b><span>{chain.contribution_delta > 0 ? "+" : ""}{chain.contribution_delta.toFixed(2)}</span></header><div>{chain.nodes.map((node, index) => <span key={`${node.ref}-${index}`}>{node.label}{index < chain.nodes.length - 1 ? <i>→</i> : null}</span>)}</div></article>)}
      </> : null}
      {panel === "method" ? <>
        <p className="sheet-lead">方法与数据</p>
        <dl className="method-list"><div><dt>数据属性</dt><dd>代理数据基线</dd></div><div><dt>计算范围</dt><dd>31 省；港澳台仅作中国版图展示</dd></div><div><dt>产品版本</dt><dd>{timeline.product_version}</dd></div><div><dt>帧哈希</dt><dd>{frame.source_hash.slice(0, 16)}…</dd></div><div><dt>世界哈希</dt><dd>{timeline.source_world_hash.slice(0, 16)}…</dd></div><div><dt>证据引用</dt><dd>{frame.evidence_refs.length}</dd></div></dl>
        <p className="method-note">研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。</p>
      </> : null}
      {panel === "layers" ? <>
        <p className="sheet-lead">当前地图投影</p>
        <div className="layer-choice active"><span className="layer-swatch" />{fillMetricLabel(frame.map_projection.fill_metric)}<small>{frame.map_projection.mode === "difference" ? "差值图层" : "绝对值图层"}</small></div>
        <div className="layer-choice"><ArrowsOutLineHorizontal />省际互动弧线<small>{frame.map_projection.enabled_overlays.length} 类已启用</small></div>
        <div className="layer-choice"><span className="layer-swatch territory" />中国版图上下文<small>港澳台显示轮廓，不着色、不交互、不参与计算</small></div>
      </> : null}
    </aside>
  );
}

export function PresentationApp() {
  const queryClient = useQueryClient();
  const [experimentId, setExperimentId] = useState<string | null>(pathExperimentId);
  const [collection, setCollection] = useState<PresentationMapCollection | null>(null);
  const [collectionError, setCollectionError] = useState<string | null>(null);
  const [mode, setMode] = useState<PresentationMode>("live");
  const [frameIndex, setFrameIndex] = useState(0);
  const [liveFrameQueue, setLiveFrameQueue] = useState<string[]>([]);
  const [playing, setPlaying] = useState(false);
  const [timelineDragging, setTimelineDragging] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [panel, setPanel] = useState<DockPanel | null>(null);
  const [selected, setSelected] = useState<ProvinceSelection | null>(null);
  const [reducedMotion, setReducedMotion] = useState(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [introRunId, setIntroRunId] = useState(1);
  const [introActive, setIntroActive] = useState(new URLSearchParams(window.location.search).get("intro") !== "0");
  const [streamStatus, setStreamStatus] = useState<"connecting" | "live" | "reconnecting" | "offline" | "frozen">("connecting");
  const [compareLayout, setCompareLayout] = useState<"delta" | "split">("delta");
  const [spotlightIndex, setSpotlightIndex] = useState(0);
  const [syncCamera, setSyncCamera] = useState<PresentationCamera | undefined>();
  const [fullscreen, setFullscreen] = useState(Boolean(document.fullscreenElement));
  const [mapFallback, setMapFallback] = useState(new URLSearchParams(window.location.search).get("mapFallback") === "1");
  const [demoDraft, setDemoDraft] = useState<DemoDraft | null>(null);
  const [launchReviewStep, setLaunchReviewStep] = useState<LaunchReviewStep>("configuration");
  const seenTimelineExperimentRef = useRef<string | null>(null);
  const seenLiveFrameIdsRef = useRef<Set<string>>(new Set());
  const previousModeRef = useRef<PresentationMode | null>(null);
  const autoSplitFrameIdsRef = useRef<Set<string>>(new Set());
  const mapFatal = useCallback(() => setMapFallback(true), []);
  const completeIntro = useCallback(() => setIntroActive(false), []);

  const loadCollection = useCallback(() => {
    let active = true;
    setCollectionError(null);
    void fetch("/assets/china-presentation-map.geojson").then((response) => {
      if (!response.ok) throw new Error(`地图资源加载失败（${response.status}）`);
      return response.json() as Promise<PresentationMapCollection>;
    }).then((value) => {
      if (!active) return;
      const simulationRegions = value.features.filter(
        (feature) => feature.properties.region_role === "simulation-province",
      );
      const contextCodes = new Set(
        value.features
          .filter((feature) => feature.properties.region_role === "territory-context")
          .map((feature) => feature.properties.province_code),
      );
      if (
        simulationRegions.length !== 31
        || contextCodes.size !== 3
        || !["71", "81", "82"].every((code) => contextCodes.has(code))
      ) {
        throw new Error("全国地图未完整覆盖 31 省及港澳台版图上下文");
      }
      setCollection(value);
    }).catch((error: unknown) => active && setCollectionError(error instanceof Error ? error.message : "地图加载失败"));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    return loadCollection();
  }, [loadCollection]);

  const eventCatalogQuery = useQuery({
    queryKey: ["presentation-event-catalog"],
    queryFn: presentationApi.eventCatalog,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const createDemoDraft = useMutation({
    mutationFn: presentationApi.createDemoDraft,
    onSuccess: (draft) => {
      setDemoDraft(draft);
      setLaunchReviewStep("interpretation");
    },
  });
  const confirmDemoInterpretation = useMutation({
    mutationFn: async () => {
      if (!demoDraft) throw new Error("尚未生成中央政策解读");
      await presentationApi.confirmDemoInterpretation(demoDraft);
    },
    onSuccess: () => setLaunchReviewStep("design"),
  });
  const confirmDemoDesign = useMutation({
    mutationFn: async () => {
      if (!demoDraft) throw new Error("尚未生成实验设计");
      await presentationApi.confirmDemoDesign(demoDraft);
    },
    onSuccess: () => setLaunchReviewStep("baseline"),
  });
  const confirmDemoBaseline = useMutation({
    mutationFn: async () => {
      if (!demoDraft) throw new Error("尚未生成实验基线");
      return presentationApi.confirmDemoBaseline(demoDraft);
    },
    onSuccess: (id) => {
      window.history.replaceState({}, "", `/experiments/${id}/present`);
      setExperimentId(id);
      setMode("live");
      setFrameIndex(0);
      setIntroActive(false);
    },
  });
  const timelineQuery = useQuery({
    queryKey: ["presentation-timeline", experimentId],
    queryFn: () => presentationApi.timeline(experimentId!),
    enabled: Boolean(experimentId),
    refetchInterval: false,
  });
  const timeline = timelineQuery.data;
  const completed = timeline?.status === "completed";
  const comparisonQuery = useQuery({
    queryKey: ["presentation-comparison", experimentId],
    queryFn: () => presentationApi.comparison(experimentId!),
    enabled: Boolean(experimentId && completed),
  });
  const worldQuery = useQuery({
    queryKey: ["presentation-world", experimentId],
    queryFn: () => presentationApi.state(experimentId!),
    enabled: Boolean(experimentId),
  });
  const completedRounds = useMemo(() => new Set(
    timeline?.frames.flatMap((item) => item.round ? [item.round] : []) ?? [],
  ), [timeline?.frames]);
  const nextRound = completed
    ? null
    : ROUND_SEQUENCE.find((item) => !completedRounds.has(item)) ?? null;
  const runRound = useMutation({
    mutationFn: ({ id, round }: { id: string; round: SimulationRound }) => presentationApi.run(id, round),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["presentation-timeline", experimentId] });
    },
  });
  const frameIndexItem = timeline?.frames[Math.min(frameIndex, Math.max(0, timeline.frames.length - 1))];
  const frameQuery = useQuery({
    queryKey: ["presentation-frame", experimentId, frameIndexItem?.frame_id],
    queryFn: () => presentationApi.frame(experimentId!, frameIndexItem!.frame_id),
    enabled: Boolean(experimentId && frameIndexItem),
    placeholderData: (previousFrame) => previousFrame,
  });
  const frame = frameQuery.data;
  useEffect(() => {
    if (!timeline || !experimentId) return;
    for (const index of [frameIndex - 1, frameIndex + 1]) {
      const neighbor = timeline.frames[index];
      if (!neighbor) continue;
      void queryClient.prefetchQuery({
        queryKey: ["presentation-frame", experimentId, neighbor.frame_id],
        queryFn: () => presentationApi.frame(experimentId, neighbor.frame_id),
        staleTime: Number.POSITIVE_INFINITY,
      });
    }
  }, [experimentId, frameIndex, queryClient, timeline]);

  const allFrameQueries = useQueries({
    queries: (panel === "decisions" && timeline && experimentId ? timeline.frames : []).map((item) => ({
      queryKey: ["presentation-frame", experimentId, item.frame_id],
      queryFn: () => presentationApi.frame(experimentId!, item.frame_id),
      staleTime: Number.POSITIVE_INFINITY,
    })),
  });
  const allDecisionMoments = useMemo(() => {
    const unique = new Map<string, PresentationFrame["decision_moments"][number]>();
    for (const query of allFrameQueries) {
      for (const moment of query.data?.decision_moments ?? []) {
        if (!moment.trace_id.startsWith("utility:")) unique.set(moment.moment_id, moment);
      }
    }
    return [...unique.values()].sort((left, right) => left.round.localeCompare(right.round) || left.moment_id.localeCompare(right.moment_id));
  }, [allFrameQueries]);
  const allInteractionThreads = useMemo(() => {
    const unique = new Map<string, PresentationFrame["interaction_threads"][number]>();
    for (const query of allFrameQueries) {
      for (const thread of query.data?.interaction_threads ?? []) unique.set(thread.thread_id, thread);
    }
    return [...unique.values()];
  }, [allFrameQueries]);

  const branchFrames = useMemo(() => {
    if (!frame?.branch_projections.control || !frame.branch_projections.treatment) return null;
    const control = mapFrame(frame, frame.branch_projections.control);
    const treatment = mapFrame(frame, frame.branch_projections.treatment);
    return control && treatment ? { control, treatment } : null;
  }, [frame]);
  const selectedSpotlight = frame?.spotlights[spotlightIndex] ?? frame?.spotlights[0];
  const activeRole: BranchRole = selectedSpotlight?.branch_role ?? "treatment";
  const singleMapFrame = useMemo(() => {
    if (!frame) return null;
    if (mode === "compare" && frame.difference_projection) return mapFrame(frame, frame.difference_projection);
    const mapped = mapFrame(frame, frame.shared_projection ?? frame.branch_projections[activeRole] ?? frame.branch_projections.treatment ?? null);
    const thread = selectedSpotlight?.thread_id
      ? frame.interaction_threads.find((item) => item.thread_id === selectedSpotlight.thread_id)
      : null;
    if (!mapped || !thread) return mapped;
    const subjects = new Set(thread.participants.map((item) => `${item.subject_type}:${item.subject_id}`));
    if (thread.resource_subject) subjects.add(`${thread.resource_subject.subject_type}:${thread.resource_subject.subject_id}`);
    const focused = mapped.overlay_records.filter((item) =>
      subjects.has(item.source_subject) || Boolean(item.target_subject && subjects.has(item.target_subject)),
    );
    return {
      ...mapped,
      overlay_records: focused,
      map_projection: {
        ...mapped.map_projection,
        enabled_overlays: [...new Set(focused.map((item) => item.kind))],
      },
    };
  }, [activeRole, frame, mode, selectedSpotlight]);
  const splitVisualScale = useMemo(
    () => branchFrames ? visualScaleForFrames([branchFrames.control, branchFrames.treatment]) : null,
    [branchFrames],
  );

  useEffect(() => {
    if (!experimentId || timeline?.status === "completed") {
      if (timeline?.status === "completed") setStreamStatus("frozen");
      return;
    }
    let opened = false;
    const source = new EventSource(presentationApi.streamUrl(experimentId));
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ["presentation-timeline", experimentId] });
      void queryClient.invalidateQueries({ queryKey: ["presentation-world", experimentId] });
    };
    const eventNames = [
      "baseline.confirmed",
      "branches.created",
      "round.completed",
      "province_initial.completed",
      "automaker_initial.completed",
      "province_revision.completed",
      "automaker_negotiation.completed",
      "province_counter_response.completed",
      "automaker_final.completed",
      "environment_settlement.completed",
      "comparison.completed",
      "cache.hit",
    ];
    eventNames.forEach((name) => source.addEventListener(name, refresh));
    source.addEventListener("heartbeat", () => setStreamStatus("live"));
    source.onopen = () => {
      opened = true;
      setStreamStatus("live");
    };
    source.onerror = () => setStreamStatus(navigator.onLine ? (opened ? "reconnecting" : "connecting") : "offline");
    const markOffline = () => setStreamStatus("offline");
    const markOnline = () => setStreamStatus("reconnecting");
    window.addEventListener("offline", markOffline);
    window.addEventListener("online", markOnline);
    return () => {
      source.close();
      window.removeEventListener("offline", markOffline);
      window.removeEventListener("online", markOnline);
    };
  }, [experimentId, queryClient, timeline?.status]);

  useEffect(() => {
    if (!timeline) return;
    const enteringMode = previousModeRef.current !== mode;
    if (mode === "live" && enteringMode) {
      const current = timeline.frames.findIndex((item) => item.frame_id === timeline.current_frame_id);
      setFrameIndex(current >= 0 ? current : timeline.frames.length - 1);
      setPlaying(false);
    }
    if (mode === "compare" && enteringMode) {
      const comparison = timeline.frames.findIndex((item) => item.kind === "comparison");
      setFrameIndex(comparison >= 0 ? comparison : timeline.frames.length - 1);
      setPlaying(false);
      setPanel("result");
    }
    previousModeRef.current = mode;
  }, [mode, timeline]);

  useEffect(() => {
    if (!timeline || !experimentId) return;
    const frameIds = timeline.frames.map((item) => item.frame_id);
    if (seenTimelineExperimentRef.current !== experimentId) {
      seenTimelineExperimentRef.current = experimentId;
      seenLiveFrameIdsRef.current = new Set(frameIds);
      setLiveFrameQueue([]);
      if (mode === "live") {
        const current = timeline.frames.findIndex((item) => item.frame_id === timeline.current_frame_id);
        setFrameIndex(current >= 0 ? current : timeline.frames.length - 1);
      }
      return;
    }
    const queued = frameIds.filter((frameId) => !seenLiveFrameIdsRef.current.has(frameId));
    seenLiveFrameIdsRef.current = new Set(frameIds);
    if (mode !== "live" || !queued.length) return;
    setLiveFrameQueue((existing) => [
      ...existing,
      ...queued.filter((frameId) => !existing.includes(frameId)),
    ]);
  }, [experimentId, mode, timeline]);

  useEffect(() => {
    if (mode !== "live" || !timeline || !liveFrameQueue.length) return;
    const nextFrameId = liveFrameQueue[0]!;
    const nextIndex = timeline.frames.findIndex((item) => item.frame_id === nextFrameId);
    if (nextIndex < 0) {
      setLiveFrameQueue((existing) => existing.slice(1));
      return;
    }
    setFrameIndex(nextIndex);
    const timer = window.setTimeout(() => {
      setLiveFrameQueue((existing) => existing.slice(1));
    }, (reducedMotion ? 900 : 1900) / speed);
    return () => window.clearTimeout(timer);
  }, [liveFrameQueue, mode, reducedMotion, speed, timeline]);

  useEffect(() => {
    setSpotlightIndex(0);
    if (!frame || !timeline || !branchFrames) return;
    if (timeline.frames[frameIndex]?.frame_id !== frame.frame_id) return;
    const keyDivergence = frame.frame_id === timeline.first_divergence_frame_id;
    const settlement = frame.kind === "settlement" || frame.kind === "comparison";
    if ((keyDivergence || settlement) && !autoSplitFrameIdsRef.current.has(frame.frame_id)) {
      autoSplitFrameIdsRef.current.add(frame.frame_id);
      setCompareLayout("split");
    }
  }, [branchFrames, frame, frameIndex, timeline]);

  useEffect(() => {
    if (!playing || !timeline?.frames.length) return;
    const timer = window.setInterval(() => {
      setFrameIndex((current) => {
        if (current >= timeline.frames.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, (reducedMotion ? 1800 : 2400) / speed);
    return () => window.clearInterval(timer);
  }, [playing, reducedMotion, speed, timeline?.frames.length]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, select, textarea") && event.key !== "Escape") return;
      if (event.code === "Space") {
        event.preventDefault();
        if (timeline?.frames.length) setPlaying((current) => !current);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault();
        const direction = event.key === "ArrowRight" ? 1 : -1;
        setPlaying(false);
        setLiveFrameQueue([]);
        setFrameIndex((current) => {
          return Math.max(0, Math.min((timeline?.frames.length ?? 1) - 1, current + direction));
        });
      } else if (event.key === "Home" || event.key.toLowerCase() === "r") {
        setFrameIndex(0);
        setPlaying(false);
        setLiveFrameQueue([]);
      } else if (event.key === "Escape") {
        setPanel(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [timeline?.frames]);

  useEffect(() => {
    const update = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);

  const selectProvince = useCallback((value: ProvinceSelection) => {
    setSelected(value);
  }, []);
  const selectControlProvince = useCallback((value: ProvinceSelection) => {
    setSelected({ ...value, branchId: "control" });
  }, []);
  const selectTreatmentProvince = useCallback((value: ProvinceSelection) => {
    setSelected({ ...value, branchId: "treatment" });
  }, []);

  const providerLabel = {
    live: "在线推演",
    cache: "验证缓存",
    cached: "验证缓存",
    fake: "FAKE / FALLBACK",
    fallback: "FAKE / FALLBACK",
  }[worldQuery.data?.versions.agent_provider_mode ?? "fake"] ?? "FAKE / FALLBACK";
  const headlineMetric = singleMapFrame?.metric_summary[0];
  const legendFrame = compareLayout === "split" && branchFrames ? branchFrames.control : singleMapFrame;
  const visualScale = useMemo(
    () => compareLayout === "split" && splitVisualScale
      ? splitVisualScale
      : singleMapFrame
        ? visualScaleForFrame(singleMapFrame)
        : null,
    [compareLayout, singleMapFrame, splitVisualScale],
  );
  const selectionFrame = selected?.branchId && compareLayout === "split" && branchFrames
    ? branchFrames[selected.branchId]
    : singleMapFrame;
  const displayedSelection = useMemo(() => {
    if (!selected || !selectionFrame) return selected;
    return {
      ...selected,
      branchId: compareLayout === "split" && branchFrames ? selected.branchId : undefined,
      value: selectionFrame.province_values.find((item) => item.province_code === selected.code)?.value ?? null,
    };
  }, [branchFrames, compareLayout, selected, selectionFrame]);
  const seekFromPointer = useCallback((clientX: number, track: HTMLDivElement) => {
    if (!timeline?.frames.length) return;
    const bounds = track.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - bounds.left) / bounds.width));
    setFrameIndex(Math.round(ratio * (timeline.frames.length - 1)));
    setPlaying(false);
    setLiveFrameQueue([]);
  }, [timeline?.frames.length]);

  if (!experimentId) {
    if (!collection && collectionError) return <main className="loading-stage error"><Info /><h1>全国地图未就绪</h1><p>{collectionError}</p><button className="primary-action" onClick={() => loadCollection()} type="button">重试地图</button></main>;
    if (!collection) return <main className="loading-stage"><span className="loader-ring" /><p>正在建立全球情景视角…</p></main>;
    const launchError = launchReviewStep === "configuration" && eventCatalogQuery.isError
      ? "突发事件目录未就绪；仍可创建纯政策对比，或重新载入目录。"
      : [createDemoDraft.error, confirmDemoInterpretation.error, confirmDemoDesign.error, confirmDemoBaseline.error]
        .find((value): value is Error => value instanceof Error)?.message ?? null;
    return <LaunchExperience catalog={eventCatalogQuery.data ?? null} collection={collection} draft={demoDraft} error={launchError} introActive={introActive} introRunId={introRunId} onConfirmBaseline={() => confirmDemoBaseline.mutate()} onConfirmDesign={() => confirmDemoDesign.mutate()} onConfirmInterpretation={() => confirmDemoInterpretation.mutate()} onCreateDraft={(selection) => createDemoDraft.mutate(selection)} onIntroComplete={completeIntro} onRetryCatalog={() => { void eventCatalogQuery.refetch(); }} pending={createDemoDraft.isPending || confirmDemoInterpretation.isPending || confirmDemoDesign.isPending || confirmDemoBaseline.isPending} reducedMotion={reducedMotion} reviewStep={launchReviewStep} />;
  }
  if (!collection && collectionError) return <main className="loading-stage error"><Info /><h1>全国地图未就绪</h1><p>{collectionError}</p><button className="primary-action" onClick={() => loadCollection()} type="button">重试地图</button></main>;
  if (timelineQuery.isError || frameQuery.isError || eventCatalogQuery.isError || worldQuery.isError) return <main className="loading-stage error"><Info /><h1>演示数据未就绪</h1><p>{timelineQuery.error instanceof Error ? timelineQuery.error.message : frameQuery.error instanceof Error ? frameQuery.error.message : eventCatalogQuery.error instanceof Error ? eventCatalogQuery.error.message : worldQuery.error instanceof Error ? worldQuery.error.message : "请确认后端实验可读"}</p><button className="primary-action" onClick={() => { void timelineQuery.refetch(); void frameQuery.refetch(); void eventCatalogQuery.refetch(); void worldQuery.refetch(); }} type="button">重新载入</button></main>;
  if (timelineQuery.isLoading || eventCatalogQuery.isLoading || worldQuery.isLoading || !collection || !eventCatalogQuery.data) return <main className="loading-stage"><span className="loader-ring" /><p>正在载入全国冻结推演…</p></main>;
  if (!timeline || !frame || !singleMapFrame) return <main className="loading-stage"><span className="loader-ring" /><p>正在载入当前博弈帧…</p></main>;
  const renderedLegendFrame = legendFrame ?? singleMapFrame;
  const panelFrame = panel === "province" && selectionFrame
    ? selectionFrame
    : compareLayout === "split" && branchFrames && panel && BRANCH_RELATIONSHIP_PANELS.has(panel)
      ? branchFrames[selected?.branchId ?? "control"]
      : singleMapFrame;

  return (
    <main className={`presentation-shell mode-${mode} ${reducedMotion ? "reduced-motion" : ""}`}>
      {compareLayout === "split" && branchFrames ? <section className="split-compare-stage" aria-label="同步 A/B 双世界">
        <article><header><span>原始方案</span><b>方案 A</b></header>{mapFallback ? <PresentationMapFallback ariaLabel="原始方案省域地图" collection={collection} frame={branchFrames.control} onSelect={selectControlProvince} selectedCode={selected?.code ?? null} visualScale={splitVisualScale ?? undefined} /> : <PresentationMap ariaLabel="原始方案省域地图" cameraSync={syncCamera} collection={collection} frame={branchFrames.control} onCameraChange={setSyncCamera} onError={setCollectionError} onFatal={mapFatal} onSelect={selectControlProvince} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} visualScale={splitVisualScale ?? undefined} />}</article>
        <article><header><span>干预方案</span><b>方案 B</b></header>{mapFallback ? <PresentationMapFallback ariaLabel="干预方案省域地图" collection={collection} frame={branchFrames.treatment} onSelect={selectTreatmentProvince} selectedCode={selected?.code ?? null} visualScale={splitVisualScale ?? undefined} /> : <PresentationMap ariaLabel="干预方案省域地图" cameraSync={syncCamera} collection={collection} frame={branchFrames.treatment} onCameraChange={setSyncCamera} onError={setCollectionError} onFatal={mapFatal} onSelect={selectTreatmentProvince} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} visualScale={splitVisualScale ?? undefined} />}</article>
      </section> : mapFallback ? <PresentationMapFallback collection={collection} frame={singleMapFrame} onSelect={selectProvince} selectedCode={selected?.code ?? null} /> : <PresentationMap collection={collection} frame={singleMapFrame} onError={setCollectionError} onFatal={mapFatal} onSelect={selectProvince} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} />}
      {compareLayout === "split" && branchFrames ? <div className="split-truth-note">同步冻结事实 · 原始方案虚线/空心 · 干预方案实线/实心</div> : null}
      <div className="stage-vignette" />

      <header className="top-hud glass-bar" aria-hidden={introActive}>
        <div className="brand-lockup"><span className="brand-mark"><Sparkle weight="fill" /></span><div><strong>13110</strong><small>新能源汽车政策全景推演</small></div></div>
        <nav className="segmented-control" aria-label="演示模式">
          {timeline.available_modes.map((item) => <button className={mode === item ? "active" : ""} key={item} onClick={() => { setLiveFrameQueue([]); setMode(item); }} type="button">{modeLabel(item)}</button>)}
        </nav>
        <div className="hud-actions">{branchFrames ? <div className="compare-layout-toggle"><button className={compareLayout === "delta" ? "active" : ""} onClick={() => { setSelected(null); setCompareLayout("delta"); }} type="button">单图聚焦</button><button className={compareLayout === "split" ? "active" : ""} onClick={() => { setSelected(null); setCompareLayout("split"); }} type="button">A/B 同步</button></div> : null}<span className={`live-chip status-${streamStatus}`} title="SSE 事实流连接状态"><i /> {{ connecting: "连接中", live: "在线", reconnecting: "重连中", offline: "离线", frozen: "已冻结" }[streamStatus]}</span><button className="text-action" onClick={() => { setIntroRunId((current) => current + 1); setIntroActive(true); }} type="button"><ClockCounterClockwise />重播开场</button></div>
      </header>

      <section className="narrative-panel glass-panel" data-frame-id={frame.frame_id} aria-hidden={introActive}>
        <div className="chapter-row"><span>{frame.title}</span><b>{String(frameIndex + 1).padStart(2, "0")} / {String(timeline.frames.length).padStart(2, "0")}</b></div>
        <GameSpotlight frame={frame} onSelect={setSpotlightIndex} selected={spotlightIndex} />
        {nextRound ? <button className="round-action" disabled={runRound.isPending || liveFrameQueue.length > 0} onClick={() => runRound.mutate({ id: experimentId, round: nextRound })} type="button"><span><small>下一轮</small><b>{runRound.isPending ? "正在冻结双分支事实…" : liveFrameQueue.length ? "正在顺序播放新增帧…" : ROUND_LABELS[nextRound]}</b></span><SkipForward weight="fill" /></button> : null}
        {runRound.error instanceof Error ? <p className="round-error">{runRound.error.message}</p> : null}
      </section>

      {headlineMetric ? <aside className="metric-card glass-panel" aria-hidden={introActive}><small>{headlineMetric.label}</small><strong>{headlineMetric.value.toFixed(2)}</strong><span>{headlineMetric.unit}</span>{headlineMetric.delta != null ? <em>Δ {headlineMetric.delta > 0 ? "+" : ""}{headlineMetric.delta.toFixed(2)}</em> : null}</aside> : null}

      <nav className="tool-dock glass-panel" aria-label="推演工具" aria-hidden={introActive}>
        {DOCK_ITEMS.map(({ id, label, Icon }) => <button aria-label={label} className={panel === id ? "active" : ""} data-tooltip={label} key={id} onClick={() => setPanel((current) => current === id ? null : id)} type="button"><Icon weight={panel === id ? "fill" : "regular"} /></button>)}
      </nav>

      {panel ? <SideSheet catalog={eventCatalogQuery.data} comparison={comparisonQuery.data} frame={panelFrame} moments={panel === "decisions" ? allDecisionMoments : frame.decision_moments} onClose={() => setPanel(null)} panel={panel} selected={displayedSelection} threads={panel === "decisions" ? allInteractionThreads : frame.interaction_threads} timeline={timeline} world={worldQuery.data} /> : null}

      {displayedSelection && !panel ? <button className="province-popover glass-panel" onClick={() => setPanel("province")} style={{ left: `${Math.min(displayedSelection.x + 18, window.innerWidth - 310)}px`, top: `${Math.min(displayedSelection.y + 18, window.innerHeight - 190)}px` }} type="button"><small>省域态势</small><strong>{displayedSelection.name}</strong><span>{displayedSelection.value?.toFixed(2) ?? "—"} {selectionFrame?.map_projection.unit ?? singleMapFrame.map_projection.unit}</span><em>展开详情 →</em></button> : null}

      {frame.interaction_threads.length ? <section className="thread-rail glass-panel" aria-label="行动回应轨"><header><b>行动—回应轨</b><span>{frame.interaction_threads.length} 条冻结互动</span></header><div>{frame.interaction_threads.slice(0, 8).map((thread) => <button key={thread.thread_id} onClick={() => setPanel(thread.thread_type === "competition" ? "competition" : thread.thread_type === "coordination" ? "coordination" : "negotiation")} type="button"><small>{thread.branch_role === "control" ? "原始" : "干预"}</small><b>{thread.title}</b>{thread.beats.map((beat) => <span className={beat.status} key={beat.beat_id}>{beat.label}</span>)}</button>)}</div></section> : null}

      <section className="timeline-rail glass-panel" aria-hidden={introActive}>
        <div className="transport-controls"><button aria-label="上一帧" disabled={frameIndex === 0} onClick={() => { setLiveFrameQueue([]); setFrameIndex((current) => Math.max(0, current - 1)); }} type="button"><SkipBack weight="fill" /></button><button aria-label={playing ? "暂停" : "播放"} className="play-button" onClick={() => { setLiveFrameQueue([]); setPlaying((current) => !current); }} type="button">{playing ? <Pause weight="fill" /> : <Play weight="fill" />}</button><button aria-label="下一帧" disabled={frameIndex === timeline.frames.length - 1} onClick={() => { setLiveFrameQueue([]); setFrameIndex((current) => Math.min(timeline.frames.length - 1, current + 1)); }} type="button"><SkipForward weight="fill" /></button></div>
        <div className="timeline-track-wrap">
          <div className="timeline-labels"><span>{selectedSpotlight?.label ?? frame.title}</span><b>{frame.kind === "comparison" ? "结果帧" : frame.round ? ROUND_LABELS[frame.round] : frame.kind === "event" ? "突发事件" : "方案冻结"}</b></div>
          <div
            className="timeline-track"
            onPointerDown={(event) => {
              if ((event.target as Element).closest("button")) return;
              setTimelineDragging(true);
              event.currentTarget.setPointerCapture(event.pointerId);
              seekFromPointer(event.clientX, event.currentTarget);
            }}
            onPointerMove={(event) => {
              if (timelineDragging) seekFromPointer(event.clientX, event.currentTarget);
            }}
            onPointerUp={(event) => {
              setTimelineDragging(false);
              event.currentTarget.releasePointerCapture(event.pointerId);
            }}
          >
            <div className="timeline-progress" style={{ width: `${timeline.frames.length === 1 ? 100 : frameIndex / (timeline.frames.length - 1) * 100}%` }} />
            {timeline.frames.map((item, index) => <button aria-label={`跳转至 ${item.title}`} className={`${index <= frameIndex ? "passed" : ""} ${index === frameIndex ? "current" : ""}`} key={item.frame_id} onClick={() => { setLiveFrameQueue([]); setFrameIndex(index); setPlaying(false); }} style={{ left: `${timeline.frames.length === 1 ? 0 : index / (timeline.frames.length - 1) * 100}%` }} type="button"><span>{index + 1}</span></button>)}
            {timeline.event_markers.map((event) => <i className="event-marker" key={event.marker_id} style={{ left: `${event.timeline_position * 100}%` }} title={event.title}><Lightning weight="fill" /></i>)}
            <input aria-label="拖动推演时间轴" max={timeline.frames.length - 1} min={0} onChange={(event) => { setLiveFrameQueue([]); setFrameIndex(Number(event.target.value)); setPlaying(false); }} onInput={(event) => { setLiveFrameQueue([]); setFrameIndex(Number(event.currentTarget.value)); setPlaying(false); }} step={1} type="range" value={frameIndex} />
          </div>
        </div>
        <div className="timeline-tools"><button onClick={() => setSpeed((current) => current === 2 ? 0.5 : current + 0.5)} title="0.5× / 1× / 1.5× / 2×" type="button">{speed.toFixed(1)}×</button><button aria-label="回到起点" onClick={() => { setLiveFrameQueue([]); setFrameIndex(0); setPlaying(false); }} type="button"><Rewind /></button><button aria-label={fullscreen ? "退出全屏" : "进入全屏"} onClick={() => { if (document.fullscreenElement) void document.exitFullscreen(); else void document.documentElement.requestFullscreen(); }} type="button"><ArrowsOutLineHorizontal /></button></div>
      </section>

      <div className="map-legend" aria-hidden={introActive}><span>{fillMetricLabel(renderedLegendFrame.map_projection.fill_metric)}</span><div>{visualScale?.stops.map(([, color], index) => <i key={`${color}-${index}`} style={{ background: color }} />)}</div><small>{visualScale ? `${scaleLabel(visualScale)} · ` : ""}{renderedLegendFrame.map_projection.mode === "difference" ? "相对差值" : renderedLegendFrame.map_projection.unit}</small></div>
      <div className="data-status" aria-hidden={introActive}><Buildings />代理数据基线 · {providerLabel} · 全国版图完整 / 31 省计算</div>

      {introActive ? <GlobeIntro collection={collection} onComplete={completeIntro} onError={completeIntro} reducedMotion={reducedMotion} runId={introRunId} /> : null}
      {collectionError ? <button className="map-error" onClick={() => setCollectionError(null)} type="button">{collectionError}<X /></button> : null}
      <button className="motion-toggle" onClick={() => setReducedMotion((current) => !current)} type="button">{reducedMotion ? "动效：简化" : "动效：完整"}</button>
      <div className="remote-hint" aria-hidden="true">空格 播放 · ←→ 单步 · R 复位</div>
    </main>
  );
}
