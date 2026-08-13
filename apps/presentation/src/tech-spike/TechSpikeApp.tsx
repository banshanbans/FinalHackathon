import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GlobeIntro } from "./GlobeIntro";
import { EVENT_AFTER_FRAME, FRAME_LABELS } from "./presentationData";
import { SvgProvinceMap } from "./SvgProvinceMap";
import type { FrameMetric, PresentationMapCollection, TechSpikeTelemetry } from "./types";
import { WebglProvinceMap } from "./WebglProvinceMap";

const EMPTY_METRIC: FrameMetric = {
  fps: 0,
  p95FrameMs: 0,
  droppedFrameRatio: 0,
  sampleCount: 0,
};

function useFrameMetric(active: boolean) {
  const [metric, setMetric] = useState<FrameMetric>(EMPTY_METRIC);
  useEffect(() => {
    if (!active) return;
    let animationFrame = 0;
    let previous = performance.now();
    let lastReport = previous;
    const samples: number[] = [];
    const tick = (now: number) => {
      samples.push(now - previous);
      previous = now;
      if (now - lastReport >= 1000 && samples.length) {
        const ordered = [...samples].sort((left, right) => left - right);
        const mean = samples.reduce((sum, value) => sum + value, 0) / samples.length;
        const p95 = ordered[Math.min(ordered.length - 1, Math.floor(ordered.length * 0.95))];
        setMetric({
          fps: Number((1000 / mean).toFixed(1)),
          p95FrameMs: Number(p95.toFixed(2)),
          droppedFrameRatio: Number(
            (samples.filter((value) => value > 25).length / samples.length).toFixed(3),
          ),
          sampleCount: samples.length,
        });
        samples.length = 0;
        lastReport = now;
      }
      animationFrame = requestAnimationFrame(tick);
    };
    animationFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrame);
  }, [active]);
  return metric;
}

export function TechSpikeApp() {
  const searchParams = new URLSearchParams(window.location.search);
  const initialRenderer = searchParams.get("renderer");
  const skipInitialIntro = searchParams.get("intro") === "0";
  const [renderer, setRenderer] = useState<"webgl" | "svg">(
    initialRenderer === "svg" ? "svg" : "webgl",
  );
  const [collection, setCollection] = useState<PresentationMapCollection | null>(null);
  const [frame, setFrame] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(
    window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [introRunId, setIntroRunId] = useState(1);
  const [introActive, setIntroActive] = useState(!skipInitialIntro && initialRenderer !== "svg");
  const [selected, setSelected] = useState<{ code: string; name: string } | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [deckLoaded, setDeckLoaded] = useState(false);
  const [webglVersion, setWebglVersion] = useState("待检测");
  const [lastError, setLastError] = useState<string | null>(null);
  const [introError, setIntroError] = useState<string | null>(null);
  const frameMetric = useFrameMetric(autoPlay || introActive);
  const telemetryRef = useRef<TechSpikeTelemetry>({
    renderer,
    mapLoaded: false,
    deckLoaded: false,
    featureCount: 0,
    currentFrame: frame,
    webglVersion,
    geometryHash: "",
    frameMetric,
    lastError: null,
  });

  useEffect(() => {
    let active = true;
    void fetch("/assets/china-presentation-map.geojson")
      .then((response) => {
        if (!response.ok) throw new Error(`GEOJSON_${response.status}`);
        return response.json() as Promise<PresentationMapCollection>;
      })
      .then((value) => {
        if (!active) return;
        const simulationCount = value.features.filter(
          (item) => item.properties.included_in_simulation,
        ).length;
        const contextCount = value.features.filter(
          (item) => item.properties.region_role === "territory-context",
        ).length;
        if (simulationCount !== 31 || contextCount !== 3) {
          throw new Error("PRESENTATION_MAP_INCOMPLETE");
        }
        setCollection(value);
      })
      .catch((error: unknown) => {
        setLastError(error instanceof Error ? error.message : "地图资源加载失败");
        setRenderer("svg");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!autoPlay) return;
    const timer = window.setInterval(
      () => setFrame((current) => (current + 1) % FRAME_LABELS.length),
      reducedMotion ? 1100 : 1500,
    );
    return () => window.clearInterval(timer);
  }, [autoPlay, reducedMotion]);

  useEffect(() => {
    telemetryRef.current = {
      renderer,
      mapLoaded: renderer === "svg" ? Boolean(collection) : mapLoaded,
      deckLoaded: renderer === "svg" ? false : deckLoaded,
      featureCount: collection?.features.filter(
        (item) => item.properties.included_in_simulation,
      ).length ?? 0,
      currentFrame: frame,
      webglVersion,
      geometryHash: collection?.metadata.source_geometry_sha256 ?? "",
      frameMetric,
      lastError,
    };
    window.__POLICYSCOPE_TECH_SPIKE__ = telemetryRef.current;
  }, [collection, deckLoaded, frame, frameMetric, lastError, mapLoaded, renderer, webglVersion]);

  const handleReady = useCallback((version: string) => {
    setMapLoaded(true);
    setDeckLoaded(true);
    setWebglVersion(version);
  }, []);

  const handleMapError = useCallback((message: string) => {
    setLastError(message);
    setRenderer("svg");
  }, []);

  const handleIntroError = useCallback((message: string) => {
    setIntroError(message);
    setIntroActive(false);
  }, []);

  const handleIntroComplete = useCallback(() => {
    setIntroActive(false);
  }, []);

  const handleSelect = useCallback((code: string, name: string) => {
    setSelected({ code, name });
  }, []);

  const eventActive = frame > EVENT_AFTER_FRAME;
  const currentConclusion = useMemo(() => {
    if (eventActive) return "油价上涨压力情景已进入后续决策与资源重配。";
    if (frame === 0) return "同源 A/B 方案已冻结，等待七轮推演。";
    return "当前帧只展示已冻结行动，动画不补算业务结果。";
  }, [eventActive, frame]);

  return (
    <main className={`tech-spike ${reducedMotion ? "reduced-motion" : ""}`}>
      <header aria-hidden={introActive} className="top-hud">
        <div>
          <strong>13110</strong>
          <span>全景推演厅 · M33.3 开场镜头</span>
        </div>
        <nav aria-label="展示模式">
          <button className="active" type="button">地图验证</button>
          <button disabled type="button">章节回放</button>
          <button disabled type="button">结果对照</button>
        </nav>
        <div className="hud-status">
          <button
            className="replay-intro"
            disabled={renderer === "svg" || introActive}
            onClick={() => {
              setIntroError(null);
              setIntroRunId((value) => value + 1);
              setIntroActive(true);
            }}
            type="button"
          >
            重播地球开场
          </button>
          <span className={lastError ? "status-dot error" : "status-dot"} />
          {lastError ? "SVG 容错" : introError ? "开场已跳过" : "本地资产"}
        </div>
      </header>

      <section className="map-stage">
        {collection && renderer === "webgl" ? (
          <WebglProvinceMap
            collection={collection}
            frame={frame}
            onError={handleMapError}
            onReady={handleReady}
            onSelect={handleSelect}
            reducedMotion={reducedMotion}
            selectedCode={selected?.code ?? null}
          />
        ) : null}
        {renderer === "svg" ? (
          <SvgProvinceMap
            frame={frame}
            onSelect={handleSelect}
            selectedCode={selected?.code ?? null}
          />
        ) : null}
        {!collection && !lastError ? <div className="loading-state">正在校验31省几何…</div> : null}

        {collection && renderer === "webgl" && introActive ? (
          <GlobeIntro
            collection={collection}
            onComplete={handleIntroComplete}
            onError={handleIntroError}
            reducedMotion={reducedMotion}
            runId={introRunId}
          />
        ) : null}

        <aside aria-hidden={introActive} className="narrative-panel">
          <span className="eyebrow">冻结帧 {frame + 1}/{FRAME_LABELS.length}</span>
          <h1>{FRAME_LABELS[frame]}</h1>
          <p>{currentConclusion}</p>
          <div className={`event-summary ${eventActive ? "active" : ""}`}>
            <span>突发事件</span>
            <strong>国际冲突情景下油价上涨</strong>
            <small>{eventActive ? "已作用 · 中等强度" : "车企初步响应后触发"}</small>
          </div>
          <small className="scenario-note">机制实验情景，不代表现实战争或价格预测。</small>
        </aside>

        <aside aria-hidden={introActive} className="tech-panel">
          <span className="eyebrow">渲染技术门禁</span>
          <div className="renderer-toggle" role="group" aria-label="地图渲染器">
            <button
              className={renderer === "webgl" ? "active" : ""}
              onClick={() => {
                setLastError(null);
                setRenderer("webgl");
              }}
              type="button"
            >
              WebGL
            </button>
            <button
              className={renderer === "svg" ? "active" : ""}
              onClick={() => setRenderer("svg")}
              type="button"
            >
              SVG 容错
            </button>
          </div>
          <dl>
            <div><dt>省域绑定</dt><dd>{collection?.features.filter((item) => item.properties.included_in_simulation).length ?? 0}/31</dd></div>
            <div><dt>版图上下文</dt><dd>{collection?.features.filter((item) => item.properties.region_role === "territory-context").length ?? 0}/3</dd></div>
            <div><dt>deck.gl 弧线</dt><dd>{deckLoaded ? "已加载" : "待加载"}</dd></div>
            <div><dt>实时 FPS</dt><dd>{frameMetric.fps || "采样中"}</dd></div>
            <div><dt>P95 帧耗时</dt><dd>{frameMetric.p95FrameMs || "—"} ms</dd></div>
            <div><dt>WebGL</dt><dd>{renderer === "svg" ? "已降级" : webglVersion}</dd></div>
          </dl>
          <label className="motion-toggle">
            <input
              checked={reducedMotion}
              onChange={(event) => setReducedMotion(event.target.checked)}
              type="checkbox"
            />
            低动效模式
          </label>
          {selected ? <p className="selected-province">已选：{selected.name} · {selected.code}</p> : null}
        </aside>

        <div aria-hidden={introActive} className="map-legend">
          <span>干预方案更低</span>
          <i />
          <span>干预方案更高</span>
          <em>单位：模拟指数变化</em>
        </div>
      </section>

      <section aria-hidden={introActive} className="timeline" aria-label="可拖动冻结帧时间轴">
        <button
          className="play-button"
          onClick={() => setAutoPlay((value) => !value)}
          type="button"
        >
          {autoPlay ? "暂停" : "播放"}
        </button>
        <div className="timeline-track">
          <input
            aria-label="选择冻结业务帧"
            max={FRAME_LABELS.length - 1}
            min="0"
            onChange={(event) => {
              setAutoPlay(false);
              setFrame(Number(event.target.value));
            }}
            step="1"
            type="range"
            value={frame}
          />
          <div className="frame-nodes" aria-hidden="true">
            {FRAME_LABELS.map((label, index) => (
              <span className={index <= frame ? "passed" : ""} key={label} title={label} />
            ))}
          </div>
          <span
            aria-label="事件触发点"
            className={`event-marker ${eventActive ? "active" : ""}`}
            style={{ left: `${((EVENT_AFTER_FRAME + 0.5) / (FRAME_LABELS.length - 1)) * 100}%` }}
          />
          <div className="timeline-labels">
            <strong>{FRAME_LABELS[frame]}</strong>
            <span>连续拖动 · 松手吸附冻结帧</span>
          </div>
        </div>
        <button
          className="reset-button"
          onClick={() => {
            setAutoPlay(false);
            setFrame(0);
          }}
          type="button"
        >
          复位
        </button>
      </section>
    </main>
  );
}
