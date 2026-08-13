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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import { presentationApi } from "./api";
import type {
  EventBranchScope,
  EventIntensity,
  EventTriggerPoint,
  PresentationCamera,
  PresentationComparison,
  PresentationEventCatalog,
  PresentationEventCatalogEntry,
  PresentationFrame,
  PresentationMode,
  PresentationOverlayKind,
  PresentationTimeline,
  SimulationRound,
} from "./contracts";
import { PresentationMap } from "./PresentationMap";
import { PresentationMapFallback } from "./PresentationMapFallback";
import { GlobeIntro } from "./tech-spike/GlobeIntro";
import type { PresentationMapCollection } from "./tech-spike/types";

type DockPanel = "policy" | "event" | "province" | "automaker" | "competition" | "negotiation" | "coordination" | "result" | "method" | "layers";

interface ProvinceSelection {
  code: string;
  name: string;
  value: number | null;
  x: number;
  y: number;
}

const DOCK_ITEMS = [
  { id: "policy", label: "方案", Icon: SlidersHorizontal },
  { id: "event", label: "事件", Icon: Lightning },
  { id: "province", label: "省份", Icon: MapPin },
  { id: "automaker", label: "车企", Icon: Factory },
  { id: "competition", label: "竞争", Icon: Strategy },
  { id: "negotiation", label: "谈判", Icon: Handshake },
  { id: "coordination", label: "协同", Icon: CirclesThreePlus },
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

const ROUND_LABELS: Record<SimulationRound, string> = {
  province_initial: "省级初始行动",
  automaker_initial: "车企初步响应",
  province_revision: "省级策略调整",
  automaker_negotiation: "政企谈判",
  province_counter_response: "省级回应",
  automaker_final: "车企最终行动",
  environment_settlement: "环境结算",
};

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

function pathExperimentId() {
  const match = window.location.pathname.match(/\/experiments\/([^/]+)\/present/);
  return match?.[1] ?? new URLSearchParams(window.location.search).get("experiment");
}

function modeLabel(mode: PresentationMode) {
  return { live: "实时推演", story: "章节回放", compare: "结果对照" }[mode];
}

function panelOverlays(frame: PresentationFrame | undefined, kind: PresentationOverlayKind) {
  return frame?.overlay_records.filter((item) => item.kind === kind) ?? [];
}

interface LaunchSelection {
  event: PresentationEventCatalogEntry;
  triggerPoint: EventTriggerPoint;
  intensity: EventIntensity;
  branchScope: EventBranchScope;
  advanceNotice: boolean;
}

function LaunchScreen({ catalog, onLaunch, pending, error }: {
  catalog: PresentationEventCatalog;
  onLaunch: (selection: LaunchSelection) => void;
  pending: boolean;
  error: string | null;
}) {
  const defaultEvent = catalog.templates.find((item) => item.template_id === "oil_price_rise")
    ?? catalog.templates[0]!;
  const [templateId, setTemplateId] = useState(defaultEvent.template_id);
  const [triggerPoint, setTriggerPoint] = useState<EventTriggerPoint>("after_automaker_initial");
  const [intensity, setIntensity] = useState<EventIntensity>("low");
  const [branchScope, setBranchScope] = useState<EventBranchScope>("both");
  const [advanceNotice, setAdvanceNotice] = useState(false);
  const event = catalog.templates.find((item) => item.template_id === templateId) ?? defaultEvent;
  return (
    <main className="launch-stage">
      <div className="launch-orbit orbit-a" />
      <div className="launch-orbit orbit-b" />
      <section className="launch-console glass-panel">
        <div className="launch-copy">
          <span className="brand-kicker"><Sparkle weight="fill" /> PolicyScope / 政策涟漪</span>
          <h1>进入全国政策<br />全景推演厅</h1>
          <p>选择一项机制实验事件，然后在同一块大屏内逐轮推进双方案演化。</p>
          <div className="launch-facts"><span>31 省</span><span>10 家模拟车企</span><span>七轮互动</span></div>
          <article className="selected-event-card">
            <small>{event.family} / SCENARIO</small>
            <h2>{event.title}</h2>
            <p>{event.description}</p>
            <div>{event.mechanism_channels.map((channel) => <span key={channel}>{channel.replaceAll("_", " ")}</span>)}</div>
          </article>
          <p className="scenario-disclaimer">{event.disclaimer}</p>
        </div>
        <div className="launch-config">
          <div className="config-heading"><small>EVENT CATALOG</small><b>{String(catalog.templates.length).padStart(2, "0")} 项冻结情景</b></div>
          <div className="event-catalog-grid">
            {catalog.templates.map((item, index) => <button className={item.template_id === templateId ? "active" : ""} key={item.template_id} onClick={() => setTemplateId(item.template_id)} type="button"><span>{String(index + 1).padStart(2, "0")}</span><b>{item.title}</b><small>{item.family}</small></button>)}
          </div>
          <fieldset><legend>触发边界</legend><div className="config-options">{event.trigger_points.map((value) => <button className={triggerPoint === value ? "active" : ""} key={value} onClick={() => setTriggerPoint(value)} type="button">{TRIGGER_LABELS[value]}</button>)}</div></fieldset>
          <fieldset><legend>事件强度</legend><div className="config-options">{event.supported_intensities.map((value) => <button className={intensity === value ? "active" : ""} key={value} onClick={() => setIntensity(value)} type="button">{INTENSITY_LABELS[value]}</button>)}</div></fieldset>
          <fieldset><legend>对照范围</legend><div className="config-options">{event.branch_scopes.map((value) => <button className={branchScope === value ? "active" : ""} key={value} onClick={() => setBranchScope(value)} type="button">{SCOPE_LABELS[value]}</button>)}</div></fieldset>
          <label className="notice-toggle"><input checked={advanceNotice} disabled={!event.advance_notice_supported} onChange={(change) => setAdvanceNotice(change.target.checked)} type="checkbox" /><span><b>提前通知 Agent</b><small>将事件写入省级与车企当轮上下文</small></span></label>
          <button className="primary-action launch-action" disabled={pending} onClick={() => onLaunch({ event, triggerPoint, intensity, branchScope, advanceNotice })} type="button">
            {pending ? "正在冻结同源基线…" : "启动演示实验"}<Play weight="fill" />
          </button>
          {error ? <p className="error-copy">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}

function SideSheet({ panel, frame, timeline, catalog, comparison, selected, onClose }: {
  panel: DockPanel;
  frame: PresentationFrame;
  timeline: PresentationTimeline;
  catalog: PresentationEventCatalog;
  comparison: PresentationComparison | undefined;
  selected: ProvinceSelection | null;
  onClose: () => void;
}) {
  const config = DOCK_ITEMS.find((item) => item.id === panel)!;
  const overlays = panel === "competition" || panel === "negotiation" || panel === "coordination"
    ? panelOverlays(frame, panel)
    : frame.overlay_records;
  return (
    <aside className="side-sheet glass-panel" aria-label={`${config.label}详情`}>
      <header>
        <span className="sheet-icon"><config.Icon weight="duotone" /></span>
        <div><small>当前冻结帧</small><h2>{config.label}</h2></div>
        <button aria-label="关闭详情" className="icon-button" onClick={onClose} type="button"><X /></button>
      </header>
      {panel === "policy" ? <>
        <p className="sheet-lead">同源 A/B 政策承担比例</p>
        <div className="policy-grid"><b>原始方案</b>{timeline.frames[0]?.metric_summary.slice(0, 3).map((metric) => <span key={metric.metric_id}>{metric.label.slice(0, 2)} {metric.value.toFixed(0)}{metric.unit}</span>)}</div>
        <div className="policy-grid treatment"><b>干预方案</b><span>变化值</span><span>随结果帧</span><span>冻结展示</span></div>
      </> : null}
      {panel === "event" ? <>
        <p className="sheet-lead">{timeline.event_markers.length ? "当前实验事件已冻结，触发边界不可修改。" : "当前实验未配置突发事件。"}</p>
        {catalog.templates.map((item) => {
          const active = timeline.event_markers.find((marker) => marker.template_id === item.template_id);
          return <article className={`event-catalog-row ${active ? "active" : ""}`} key={item.template_id}><div><b>{item.title}</b>{active ? <span>ACTIVE</span> : null}</div><small>{item.description}</small>{active ? <em>{TRIGGER_LABELS[active.trigger_point]} · {INTENSITY_LABELS[active.intensity]} · {SCOPE_LABELS[active.branch_scope]}</em> : <em>{item.family} · 可用情景</em>}</article>;
        })}
        <p className="method-note">{catalog.templates[0]?.disclaimer}</p>
      </> : null}
      {panel === "province" ? <>
        <p className="sheet-lead">{selected ? selected.name : "点击地图选择省份"}</p>
        {selected ? <div className="metric-block"><small>{frame.map_projection.fill_metric}</small><strong>{selected.value?.toFixed(2) ?? "—"}</strong><span>{frame.map_projection.unit}</span></div> : <div className="empty-mini"><MapPin />省域行动将在此渐进展开</div>}
      </> : null}
      {panel === "automaker" ? <>
        <p className="sheet-lead">真实数据基线 / 模拟车企行动</p>
        {panelOverlays(frame, "automaker").slice(0, 6).map((item) => <article className="sheet-row" key={item.overlay_id}><b>{item.label}</b><span>{item.status}</span></article>)}
        {!panelOverlays(frame, "automaker").length ? <div className="empty-mini"><Factory />当前帧没有新增车企行动</div> : null}
      </> : null}
      {panel === "competition" || panel === "negotiation" || panel === "coordination" ? <>
        <p className="sheet-lead">{SEMANTIC_LABELS[panel]}只展示冻结关系，不补算新行动。</p>
        {overlays.slice(0, 8).map((item) => <article className="sheet-row" key={item.overlay_id}><b>{item.label}</b><span>{item.status}</span><small>{item.source_subject} → {item.target_subject ?? "全国"}</small></article>)}
        {!overlays.length ? <div className="empty-mini"><ShieldChevron />当前帧暂无该类关系</div> : null}
      </> : null}
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
        <div className="layer-choice active"><span className="layer-swatch" />{frame.map_projection.fill_metric}<small>{frame.map_projection.mode === "difference" ? "差值图层" : "绝对值图层"}</small></div>
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
  const [syncCamera, setSyncCamera] = useState<PresentationCamera | undefined>();
  const [fullscreen, setFullscreen] = useState(Boolean(document.fullscreenElement));
  const [mapFallback, setMapFallback] = useState(new URLSearchParams(window.location.search).get("mapFallback") === "1");

  useEffect(() => {
    let active = true;
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

  const eventCatalogQuery = useQuery({
    queryKey: ["presentation-event-catalog"],
    queryFn: presentationApi.eventCatalog,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const createDemo = useMutation({
    mutationFn: presentationApi.createDemo,
    onSuccess: (id) => {
      window.history.replaceState({}, "", `/experiments/${id}/present`);
      setExperimentId(id);
      setMode("live");
      setFrameIndex(0);
      setIntroActive(true);
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
  const summaryQuery = useQuery({
    queryKey: ["presentation-summary", experimentId],
    queryFn: () => presentationApi.summary(experimentId!),
    enabled: Boolean(experimentId && completed),
  });
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
  const embeddedFrame = timeline?.frames[Math.min(frameIndex, Math.max(0, timeline.frames.length - 1))];
  const frameQuery = useQuery({
    queryKey: ["presentation-frame", experimentId, embeddedFrame?.frame_id],
    queryFn: () => presentationApi.frame(experimentId!, embeddedFrame!.frame_id),
    enabled: Boolean(experimentId && embeddedFrame),
    placeholderData: embeddedFrame,
  });
  const frame = frameQuery.data ?? embeddedFrame;
  const branchFrames = useMemo(() => {
    if (!frame || !worldQuery.data || frame.kind !== "comparison") return null;
    const build = (branchId: "control" | "treatment") => ({
      ...frame,
      frame_id: `frame-${branchId}-synchronized-compare`,
      branch_id: branchId,
      title: branchId === "control" ? "原始方案" : "干预方案",
      map_projection: {
        ...frame.map_projection,
        mode: "absolute" as const,
        fill_metric: "province_nev_development_index",
      },
      province_values: Object.values(worldQuery.data.branches[branchId].province_states).map((item) => ({
        province_code: item.province_code,
        value: item.development_index,
        missing: false,
        data_quality: "proxy" as const,
      })),
    });
    return { control: build("control"), treatment: build("treatment") };
  }, [frame, worldQuery.data]);

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
    if (mode === "live") {
      const current = timeline.frames.findIndex((item) => item.frame_id === timeline.current_frame_id);
      setFrameIndex(current >= 0 ? current : timeline.frames.length - 1);
      setPlaying(false);
    }
    if (mode === "compare") {
      const comparison = timeline.frames.findIndex((item) => item.kind === "comparison");
      setFrameIndex(comparison >= 0 ? comparison : timeline.frames.length - 1);
      setPlaying(false);
      setPanel("result");
    }
  }, [mode, timeline]);

  useEffect(() => {
    if (mode !== "story" || !summaryQuery.data || !timeline?.story_chapters.length) return;
    const currentChapter = timeline.story_chapters.findIndex((item) =>
      item.frame_ids.includes(timeline.frames[frameIndex]?.frame_id ?? ""),
    );
    if (currentChapter < 0 || currentChapter >= summaryQuery.data.scenes.length) return;
  }, [frameIndex, mode, summaryQuery.data, timeline]);

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
        setFrameIndex((current) => {
          if (!event.shiftKey || !timeline?.story_chapters.length) {
            return Math.max(0, Math.min((timeline?.frames.length ?? 1) - 1, current + direction));
          }
          const starts = timeline.story_chapters
            .map((item) => timeline.frames.findIndex((candidate) => candidate.frame_id === item.frame_ids[0]))
            .filter((index) => index >= 0);
          const next = direction > 0
            ? starts.find((index) => index > current) ?? timeline.frames.length - 1
            : [...starts].reverse().find((index) => index < current) ?? 0;
          return next;
        });
      } else if (event.key === "Home" || event.key.toLowerCase() === "r") {
        setFrameIndex(0);
        setPlaying(false);
      } else if (event.key === "Escape") {
        setPanel(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [timeline?.frames, timeline?.story_chapters]);

  useEffect(() => {
    const update = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);

  const selectProvince = useCallback((value: ProvinceSelection) => {
    setSelected(value);
    if (panel === "province") setPanel("province");
  }, [panel]);

  const chapter = useMemo(() => timeline?.story_chapters.find((item) => item.frame_ids.includes(frame?.frame_id ?? "")), [frame?.frame_id, timeline?.story_chapters]);
  const scene = useMemo(() => {
    if (!chapter || !summaryQuery.data || !timeline) return null;
    const index = timeline.story_chapters.findIndex((item) => item.chapter_id === chapter.chapter_id);
    return summaryQuery.data.scenes[index] ?? null;
  }, [chapter, summaryQuery.data, timeline]);
  const providerLabel = {
    live: "LIVE AGENT",
    cache: "验证缓存",
    cached: "验证缓存",
    fake: "FAKE / FALLBACK",
    fallback: "FAKE / FALLBACK",
  }[worldQuery.data?.versions.agent_provider_mode ?? "fake"] ?? "FAKE / FALLBACK";
  const headlineMetric = frame?.metric_summary[0];
  const seekFromPointer = useCallback((clientX: number, track: HTMLDivElement) => {
    if (!timeline?.frames.length) return;
    const bounds = track.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - bounds.left) / bounds.width));
    setFrameIndex(Math.round(ratio * (timeline.frames.length - 1)));
    setPlaying(false);
  }, [timeline?.frames.length]);

  if (!experimentId) {
    if (eventCatalogQuery.isError) return <main className="loading-stage error"><Info /><h1>事件目录未就绪</h1><p>{eventCatalogQuery.error instanceof Error ? eventCatalogQuery.error.message : "请确认后端服务已启动"}</p><button className="primary-action" onClick={() => eventCatalogQuery.refetch()} type="button">重新载入</button></main>;
    if (eventCatalogQuery.isLoading || !eventCatalogQuery.data) return <main className="loading-stage"><span className="loader-ring" /><p>正在载入事件目录…</p></main>;
    return <LaunchScreen catalog={eventCatalogQuery.data} error={createDemo.error instanceof Error ? createDemo.error.message : null} onLaunch={(selection) => createDemo.mutate(selection)} pending={createDemo.isPending} />;
  }
  if (timelineQuery.isLoading || !collection || !eventCatalogQuery.data) return <main className="loading-stage"><span className="loader-ring" /><p>{collectionError ?? "正在载入全国冻结推演…"}</p></main>;
  if (timelineQuery.isError || eventCatalogQuery.isError || !timeline || !frame) return <main className="loading-stage error"><Info /><h1>演示数据未就绪</h1><p>{timelineQuery.error instanceof Error ? timelineQuery.error.message : "请确认后端实验可读"}</p><button className="primary-action" onClick={() => timelineQuery.refetch()} type="button">重新载入</button></main>;

  return (
    <main className={`presentation-shell mode-${mode} ${reducedMotion ? "reduced-motion" : ""}`}>
      {mode === "compare" && compareLayout === "split" && branchFrames ? <section className="split-compare-stage" aria-label="同步 A/B 双世界">
        <article><header><span>原始方案</span><b>CONTROL</b></header>{mapFallback ? <PresentationMapFallback ariaLabel="原始方案省域地图" collection={collection} frame={branchFrames.control} onSelect={selectProvince} selectedCode={selected?.code ?? null} /> : <PresentationMap ariaLabel="原始方案省域地图" cameraSync={syncCamera} collection={collection} frame={branchFrames.control} onCameraChange={setSyncCamera} onError={setCollectionError} onFatal={() => setMapFallback(true)} onSelect={selectProvince} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} />}</article>
        <article><header><span>干预方案</span><b>TREATMENT</b></header>{mapFallback ? <PresentationMapFallback ariaLabel="干预方案省域地图" collection={collection} frame={branchFrames.treatment} onSelect={selectProvince} selectedCode={selected?.code ?? null} /> : <PresentationMap ariaLabel="干预方案省域地图" cameraSync={syncCamera} collection={collection} frame={branchFrames.treatment} onCameraChange={setSyncCamera} onError={setCollectionError} onFatal={() => setMapFallback(true)} onSelect={selectProvince} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} />}</article>
      </section> : mapFallback ? <PresentationMapFallback collection={collection} frame={frame} onSelect={selectProvince} selectedCode={selected?.code ?? null} /> : <PresentationMap collection={collection} frame={frame} onError={setCollectionError} onFatal={() => setMapFallback(true)} onSelect={selectProvince} reducedMotion={reducedMotion} selectedCode={selected?.code ?? null} />}
      <div className="stage-vignette" />

      <header className="top-hud glass-bar" aria-hidden={introActive}>
        <div className="brand-lockup"><span className="brand-mark"><Sparkle weight="fill" /></span><div><strong>PolicyScope</strong><small>政策涟漪 · 全国全景推演</small></div></div>
        <nav className="segmented-control" aria-label="演示模式">
          {timeline.available_modes.map((item) => <button className={mode === item ? "active" : ""} key={item} onClick={() => setMode(item)} type="button">{modeLabel(item)}</button>)}
        </nav>
        <div className="hud-actions">{mode === "compare" ? <div className="compare-layout-toggle"><button className={compareLayout === "delta" ? "active" : ""} onClick={() => setCompareLayout("delta")} type="button">Δ 单图</button><button className={compareLayout === "split" ? "active" : ""} onClick={() => setCompareLayout("split")} type="button">A/B 同步</button></div> : null}<span className={`live-chip status-${streamStatus}`} title="SSE 事实流连接状态"><i /> {{ connecting: "CONNECTING", live: "LIVE", reconnecting: "RECONNECTING", offline: "OFFLINE", frozen: "FROZEN" }[streamStatus]}</span><button className="text-action" onClick={() => { setIntroRunId((current) => current + 1); setIntroActive(true); }} type="button"><ClockCounterClockwise />重播开场</button></div>
      </header>

      <section className="narrative-panel glass-panel" aria-hidden={introActive}>
        <div className="chapter-row"><span>{chapter?.title ?? `FRAME ${frame.sequence + 1}`}</span><b>{String(frameIndex + 1).padStart(2, "0")} / {String(timeline.frames.length).padStart(2, "0")}</b></div>
        <h1>{mode === "story" && scene ? scene.title : frame.title}</h1>
        <p>{mode === "story" && scene ? scene.summary : frame.summary}</p>
        <div className="change-list">{frame.key_changes.slice(0, 3).map((change) => <article key={change.change_id}><i className={`semantic-${change.semantic}`} /><div><b>{change.title}</b><span>{change.detail}</span></div></article>)}</div>
        {nextRound ? <button className="round-action" disabled={runRound.isPending} onClick={() => runRound.mutate({ id: experimentId, round: nextRound })} type="button"><span><small>NEXT ROUND</small><b>{runRound.isPending ? "正在冻结双分支事实…" : ROUND_LABELS[nextRound]}</b></span><SkipForward weight="fill" /></button> : null}
        {runRound.error instanceof Error ? <p className="round-error">{runRound.error.message}</p> : null}
      </section>

      {headlineMetric ? <aside className="metric-card glass-panel" aria-hidden={introActive}><small>{headlineMetric.label}</small><strong>{headlineMetric.value.toFixed(2)}</strong><span>{headlineMetric.unit}</span>{headlineMetric.delta != null ? <em>Δ {headlineMetric.delta > 0 ? "+" : ""}{headlineMetric.delta.toFixed(2)}</em> : null}</aside> : null}

      <nav className="tool-dock glass-panel" aria-label="推演工具" aria-hidden={introActive}>
        {DOCK_ITEMS.map(({ id, label, Icon }) => <button aria-label={label} className={panel === id ? "active" : ""} data-tooltip={label} key={id} onClick={() => setPanel((current) => current === id ? null : id)} type="button"><Icon weight={panel === id ? "fill" : "regular"} /></button>)}
      </nav>

      {panel ? <SideSheet catalog={eventCatalogQuery.data} comparison={comparisonQuery.data} frame={frame} onClose={() => setPanel(null)} panel={panel} selected={selected} timeline={timeline} /> : null}

      {selected && !panel ? <button className="province-popover glass-panel" onClick={() => setPanel("province")} style={{ left: `${Math.min(selected.x + 18, window.innerWidth - 310)}px`, top: `${Math.min(selected.y + 18, window.innerHeight - 190)}px` }} type="button"><small>省域态势</small><strong>{selected.name}</strong><span>{selected.value?.toFixed(2) ?? "—"} {frame.map_projection.unit}</span><em>展开详情 →</em></button> : null}

      <section className="timeline-rail glass-panel" aria-hidden={introActive}>
        <div className="transport-controls"><button aria-label="上一帧" disabled={frameIndex === 0} onClick={() => setFrameIndex((current) => Math.max(0, current - 1))} type="button"><SkipBack weight="fill" /></button><button aria-label={playing ? "暂停" : "播放"} className="play-button" onClick={() => setPlaying((current) => !current)} type="button">{playing ? <Pause weight="fill" /> : <Play weight="fill" />}</button><button aria-label="下一帧" disabled={frameIndex === timeline.frames.length - 1} onClick={() => setFrameIndex((current) => Math.min(timeline.frames.length - 1, current + 1))} type="button"><SkipForward weight="fill" /></button></div>
        <div className="timeline-track-wrap">
          <div className="timeline-labels"><span>{chapter?.title ?? "推演起点"}</span><b>{frame.kind === "comparison" ? "结果帧" : frame.round?.replaceAll("_", " · ") ?? "方案冻结"}</b></div>
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
            {timeline.frames.map((item, index) => <button aria-label={`跳转至 ${item.title}`} className={`${index <= frameIndex ? "passed" : ""} ${index === frameIndex ? "current" : ""}`} key={item.frame_id} onClick={() => { setFrameIndex(index); setPlaying(false); }} style={{ left: `${timeline.frames.length === 1 ? 0 : index / (timeline.frames.length - 1) * 100}%` }} type="button"><span>{index + 1}</span></button>)}
            {timeline.event_markers.map((event) => <i className="event-marker" key={event.marker_id} style={{ left: `${event.timeline_position * 100}%` }} title={event.title}><Lightning weight="fill" /></i>)}
            <input aria-label="拖动推演时间轴" max={timeline.frames.length - 1} min={0} onChange={(event) => { setFrameIndex(Number(event.target.value)); setPlaying(false); }} onInput={(event) => { setFrameIndex(Number(event.currentTarget.value)); setPlaying(false); }} step={1} type="range" value={frameIndex} />
          </div>
        </div>
        <div className="timeline-tools"><button onClick={() => setSpeed((current) => current === 2 ? 0.5 : current + 0.5)} title="0.5× / 1× / 1.5× / 2×" type="button">{speed.toFixed(1)}×</button><button aria-label="回到起点" onClick={() => { setFrameIndex(0); setPlaying(false); }} type="button"><Rewind /></button><button aria-label={fullscreen ? "退出全屏" : "进入全屏"} onClick={() => { if (document.fullscreenElement) void document.exitFullscreen(); else void document.documentElement.requestFullscreen(); }} type="button"><ArrowsOutLineHorizontal /></button></div>
      </section>

      <div className="map-legend" aria-hidden={introActive}><span>{frame.map_projection.fill_metric}</span><div><i /><i /><i /><i /><i /></div><small>{frame.map_projection.mode === "difference" ? "相对差值" : frame.map_projection.unit}</small></div>
      <div className="data-status" aria-hidden={introActive}><Buildings />代理数据基线 · {providerLabel} · 全国版图完整 / 31 省计算</div>

      {introActive ? <GlobeIntro collection={collection} onComplete={() => setIntroActive(false)} onError={() => setIntroActive(false)} reducedMotion={reducedMotion} runId={introRunId} /> : null}
      {collectionError ? <button className="map-error" onClick={() => setCollectionError(null)} type="button">{collectionError}<X /></button> : null}
      <button className="motion-toggle" onClick={() => setReducedMotion((current) => !current)} type="button">{reducedMotion ? "动效：简化" : "动效：完整"}</button>
      <div className="remote-hint" aria-hidden="true">空格 播放 · ←→ 单步 · Shift+←→ 切幕 · R 复位</div>
    </main>
  );
}
