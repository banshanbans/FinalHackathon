import {
  Check,
  Lightning,
  Play,
  SlidersHorizontal,
  Sparkle,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { DemoConfiguration, DemoDraft } from "./api";
import type {
  EventBranchScope,
  EventIntensity,
  EventTriggerPoint,
  PresentationEventCatalog,
} from "./contracts";
import { eventFamilyLabel } from "./presentationLabels";
import { GlobeIntro } from "./tech-spike/GlobeIntro";
import type { PresentationMapCollection } from "./tech-spike/types";

type ConfigurationTab = "policy" | "event";
export type LaunchReviewStep = "configuration" | "interpretation" | "design" | "baseline";

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

function polygons(coordinates: unknown): number[][][][] {
  if (!Array.isArray(coordinates)) return [];
  if (
    coordinates.length
    && Array.isArray(coordinates[0])
    && Array.isArray(coordinates[0][0])
    && typeof coordinates[0][0][0] === "number"
  ) return [coordinates as number[][][]];
  return coordinates.flatMap(polygons);
}

function ChinaEntryMap({ collection }: { collection: PresentationMapCollection }) {
  const [minX, minY, maxX, maxY] = collection.bbox;
  const width = maxX - minX;
  const height = maxY - minY;
  const path = (coordinates: unknown) => polygons(coordinates)
    .map((polygon) => polygon
      .map((ring) => ring
        .map(([x, y], index) => `${index ? "L" : "M"}${((x - minX) / width * 1000).toFixed(2)},${((maxY - y) / height * 720).toFixed(2)}`)
        .join(" ") + " Z")
      .join(" "))
    .join(" ");

  return (
    <div className="entry-map" aria-label="全国政策全景推演地图">
      <svg role="img" viewBox="0 0 1000 720">
        <title>中国全国版图；港澳台作为版图上下文展示</title>
        {collection.features.map((feature) => (
          <path
            className={feature.properties.region_role}
            d={path(feature.geometry.coordinates)}
            key={feature.properties.province_code}
          />
        ))}
      </svg>
    </div>
  );
}

function ShareControl({ label, baseline, value, onChange }: {
  label: string;
  baseline: number;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="share-control">
      <span><b>{label}</b><small>参考 {baseline}%</small></span>
      <strong>{value}%</strong>
      <input
        aria-label={`${label}中央承担比例`}
        max={100}
        min={0}
        onChange={(event) => onChange(Number(event.target.value))}
        step={1}
        type="range"
        value={value}
      />
    </label>
  );
}

export function LaunchExperience({
  catalog,
  collection,
  introActive,
  introRunId,
  pending,
  error,
  draft,
  reviewStep,
  reducedMotion,
  onIntroComplete,
  onCreateDraft,
  onConfirmInterpretation,
  onConfirmDesign,
  onConfirmBaseline,
  onRetryCatalog,
}: {
  catalog: PresentationEventCatalog | null;
  collection: PresentationMapCollection;
  introActive: boolean;
  introRunId: number;
  pending: boolean;
  error: string | null;
  draft: DemoDraft | null;
  reviewStep: LaunchReviewStep;
  reducedMotion: boolean;
  onIntroComplete: () => void;
  onCreateDraft: (configuration: DemoConfiguration) => void;
  onConfirmInterpretation: () => void;
  onConfirmDesign: () => void;
  onConfirmBaseline: () => void;
  onRetryCatalog: () => void;
}) {
  const [showConfiguration, setShowConfiguration] = useState(!introActive);
  const [tab, setTab] = useState<ConfigurationTab>("policy");
  const [westShare, setWestShare] = useState(98);
  const [centralShare, setCentralShare] = useState(92);
  const [eastShare, setEastShare] = useState(86);
  const [eventEnabled, setEventEnabled] = useState(false);
  const [templateId, setTemplateId] = useState("oil_price_rise");
  const [triggerPoint, setTriggerPoint] = useState<EventTriggerPoint>("after_automaker_initial");
  const [intensity, setIntensity] = useState<EventIntensity>("low");
  const [advanceNotice, setAdvanceNotice] = useState(false);
  const [branchScope, setBranchScope] = useState<EventBranchScope>("both");

  useEffect(() => {
    if (introActive || showConfiguration) return;
    const timer = window.setTimeout(() => setShowConfiguration(true), reducedMotion ? 280 : 2000);
    return () => window.clearTimeout(timer);
  }, [introActive, reducedMotion, showConfiguration]);

  const defaultEvent = catalog?.templates.find((item) => item.template_id === "oil_price_rise")
    ?? catalog?.templates[0]
    ?? null;
  const selectedEvent = catalog?.templates.find((item) => item.template_id === templateId)
    ?? defaultEvent;
  const policyChanged = westShare !== 95 || centralShare !== 90 || eastShare !== 85;
  const validActiveDifference = !eventEnabled
    ? policyChanged
    : branchScope === "both"
      ? policyChanged
      : !policyChanged;
  const canLaunch = Boolean(
    !pending
    && validActiveDifference
    && (!eventEnabled || selectedEvent),
  );
  const policySummary = useMemo(
    () => `西部 ${westShare}% · 中部 ${centralShare}% · 东部 ${eastShare}%`,
    [centralShare, eastShare, westShare],
  );
  const operationId = useMemo(
    () => crypto.randomUUID(),
    [advanceNotice, branchScope, centralShare, eastShare, eventEnabled, intensity, selectedEvent?.template_id, triggerPoint, westShare],
  );

  const launch = () => {
    if (!canLaunch || (eventEnabled && !selectedEvent)) return;
    onCreateDraft({
      operationId,
      westShare: westShare / 100,
      centralShare: centralShare / 100,
      eastShare: eastShare / 100,
      event: eventEnabled ? selectedEvent ?? null : null,
      triggerPoint,
      intensity,
      branchScope,
      advanceNotice: eventEnabled && advanceNotice,
    });
  };
  const completeIntro = useCallback(() => onIntroComplete(), [onIntroComplete]);
  const dialogTitle = {
    configuration: "配置全国政策推演",
    interpretation: "确认中央政策解读",
    design: "确认 A/B 实验设计",
    baseline: "确认代理数据基线",
  }[reviewStep];
  const draftConfiguration = draft?.configuration;
  const eventCounterfactual = draftConfiguration?.event && draftConfiguration.branchScope === "treatment_only";
  const experimentTypeLabel = !draftConfiguration?.event
    ? "政策方案对照"
    : eventCounterfactual
      ? "事件反事实"
      : "政策压力测试";
  const activeDifference = eventCounterfactual
    ? "唯一主动差异：事件仅进入干预方案"
    : "唯一主动差异：东中西三档中央承担比例";

  return (
    <main className={`entry-stage ${showConfiguration ? "configuration-open" : ""}`}>
      <ChinaEntryMap collection={collection} />
      <div className="entry-vignette" />
      <header className="entry-brand">
        <Sparkle weight="fill" />
        <span><b>13110</b><small>新能源汽车政策全景推演厅</small></span>
      </header>
      {!introActive && !showConfiguration ? (
        <div className="entry-ready" aria-live="polite">
          <i />
          <span><b>全国政策网络已就绪</b><small>正在打开实验配置</small></span>
        </div>
      ) : null}

      {showConfiguration ? (
        <section aria-labelledby="configuration-title" aria-modal="true" className="configuration-dialog glass-panel" role="dialog">
          <header>
            <div>
              <small>{reviewStep === "configuration" ? "实验配置" : "人工确认门禁"}</small>
              <h1 id="configuration-title">{dialogTitle}</h1>
            </div>
            <span className="configuration-progress">{{ configuration: "01", interpretation: "02", design: "03", baseline: "04" }[reviewStep]} / 04</span>
          </header>

          {reviewStep === "configuration" ? <nav aria-label="实验配置选项" className="configuration-tabs">
            <button className={tab === "policy" ? "active" : ""} onClick={() => setTab("policy")} type="button">
              <SlidersHorizontal />政策比例
            </button>
            <button className={tab === "event" ? "active" : ""} onClick={() => setTab("event")} type="button">
              <Lightning />突发事件
              <span>{eventEnabled ? "已注入" : "可选"}</span>
            </button>
          </nav> : <div className="confirmation-sequence" aria-label="实验确认进度"><span className="done">政策输入</span><i /><span className={reviewStep !== "interpretation" ? "done" : "active"}>中央解读</span><i /><span className={reviewStep === "baseline" ? "done" : reviewStep === "design" ? "active" : ""}>A/B 设计</span><i /><span className={reviewStep === "baseline" ? "active" : ""}>基线确认</span></div>}

          <div className="configuration-body">
            {reviewStep === "configuration" ? (tab === "policy" ? (
              <div className="policy-configuration">
                <div className="configuration-lead">
                  <span>中央承担比例</span>
                  <b>{policySummary}</b>
                  <p>以 95% / 90% / 85% 为原始方案，配置干预方案的东中西中央承担比例。</p>
                </div>
                <div className="share-grid">
                  <ShareControl baseline={95} label="西部" onChange={setWestShare} value={westShare} />
                  <ShareControl baseline={90} label="中部" onChange={setCentralShare} value={centralShare} />
                  <ShareControl baseline={85} label="东部" onChange={setEastShare} value={eastShare} />
                </div>
                {!validActiveDifference ? <p className="configuration-warning">{branchScope === "treatment_only" && eventEnabled ? "事件反事实要求两方案政策比例完全相同。" : "干预方案至少需要有一档比例不同于原始方案。"}</p> : null}
                <button className="next-configuration" onClick={() => setTab("event")} type="button">
                  下一步：选择是否注入突发事件
                </button>
              </div>
            ) : (
              <div className="event-configuration">
                <label className="event-master-toggle">
                  <input checked={eventEnabled} onChange={(event) => setEventEnabled(event.target.checked)} type="checkbox" />
                  <span><b>注入突发事件</b><small>关闭时仅比较政策比例；开启后事件按冻结边界进入双方案。</small></span>
                  <em>{eventEnabled ? "已开启" : "已关闭"}</em>
                </label>
                <div aria-disabled={!eventEnabled} className={`event-options ${eventEnabled ? "enabled" : ""}`}>
                  <div className="event-catalog-grid">
                    {catalog?.templates.map((item, index) => (
                      <button
                        className={item.template_id === selectedEvent?.template_id ? "active" : ""}
                        disabled={!eventEnabled}
                        key={item.template_id}
                        onClick={() => setTemplateId(item.template_id)}
                        type="button"
                      >
                        <span>{String(index + 1).padStart(2, "0")}</span><b>{item.title}</b><small>{eventFamilyLabel(item.family)}</small>
                      </button>
                    ))}
                  </div>
                  <fieldset disabled={!eventEnabled}>
                    <legend>触发边界</legend>
                    <div className="config-options">{selectedEvent?.trigger_points.map((value) => <button className={triggerPoint === value ? "active" : ""} key={value} onClick={() => setTriggerPoint(value)} type="button">{TRIGGER_LABELS[value]}</button>)}</div>
                  </fieldset>
                  <fieldset disabled={!eventEnabled}>
                    <legend>事件作用范围</legend>
                    <div className="config-options">{selectedEvent?.branch_scopes.map((value) => <button className={branchScope === value ? "active" : ""} key={value} onClick={() => setBranchScope(value)} type="button">{SCOPE_LABELS[value]}</button>)}</div>
                  </fieldset>
                  <fieldset disabled={!eventEnabled}>
                    <legend>事件强度</legend>
                    <div className="config-options">{selectedEvent?.supported_intensities.map((value) => <button className={intensity === value ? "active" : ""} key={value} onClick={() => setIntensity(value)} type="button">{INTENSITY_LABELS[value]}</button>)}</div>
                  </fieldset>
                  <label className="notice-toggle"><input checked={advanceNotice} disabled={!eventEnabled || !selectedEvent?.advance_notice_supported} onChange={(change) => setAdvanceNotice(change.target.checked)} type="checkbox" /><span><b>提前通知省份与车企</b><small>将事件写入省级与车企当轮上下文</small></span></label>
                  {eventEnabled && selectedEvent ? <article className="selected-event-summary"><Check weight="bold" /><span><b>{selectedEvent.title}</b><small>{selectedEvent.description}</small></span></article> : null}
                </div>
              </div>
            )) : reviewStep === "interpretation" ? (
              <div className="launch-review">
                <article className="review-hero"><span>中央政策研判 Agent · 待确认</span><h2>{draft?.interpretation.public_summary}</h2><p>解读只形成结构化建议，未确认前不会冻结实验设计。</p></article>
                <div className="review-columns">
                  <section><small>政策目标</small>{draft?.interpretation.policy_goals.slice(0, 4).map((item) => <p key={item}>{item}</p>)}</section>
                  <section><small>可执行工具</small>{draft?.interpretation.policy_tools.slice(0, 4).map((item) => <p key={item}>{item}</p>)}</section>
                  <section><small>建议观察指标</small>{draft?.interpretation.recommended_metrics.slice(0, 4).map((item) => <p key={item}>{item}</p>)}</section>
                </div>
                {draft?.interpretation.ambiguities.length ? <div className="review-warning"><b>待澄清</b>{draft.interpretation.ambiguities.join(" / ")}</div> : null}
              </div>
            ) : reviewStep === "design" ? (
              <div className="launch-review">
                <article className="review-hero"><span>{experimentTypeLabel}</span><h2>{activeDifference}</h2><p>两个方案将从同一代理数据基线派生，其他输入保持一致。</p></article>
                <div className="design-review-grid">
                  <section><small>原始方案</small><b>95 / 90 / 85</b><p>2025 年政策参考基线</p></section>
                  <section className="treatment"><small>干预方案</small><b>{eventCounterfactual ? "95 / 90 / 85" : `${Math.round((draftConfiguration?.westShare ?? 0) * 100)} / ${Math.round((draftConfiguration?.centralShare ?? 0) * 100)} / ${Math.round((draftConfiguration?.eastShare ?? 0) * 100)}`}</b><p>{draftConfiguration?.event ? draftConfiguration.event.title : "不注入突发事件"}</p></section>
                </div>
                {draftConfiguration?.event ? <div className="frozen-event-review"><Lightning weight="fill" /><span><b>{draftConfiguration.event.title}</b><small>{TRIGGER_LABELS[draftConfiguration.triggerPoint]} · {INTENSITY_LABELS[draftConfiguration.intensity]} · {SCOPE_LABELS[draftConfiguration.branchScope]}</small></span></div> : null}
              </div>
            ) : (
              <div className="launch-review">
                <article className="review-hero"><span>代理数据基线 · 待确认</span><h2>确认后冻结同源 A/B 起点</h2><p>两分支共享相同的 2025 年政策参考基线、省份与车企画像；推演结果仍属模拟指数。</p></article>
                <div className="baseline-review-grid"><section><strong>31</strong><span>省级模拟主体</span></section><section><strong>10</strong><span>车企模拟主体</span></section><section><strong>1</strong><span>同一冻结基线</span></section></div>
                <div className="review-warning"><b>数据边界</b>当前 Fake 环境使用代理数据基线，不得解读为现实政府或企业的未来决定。</div>
              </div>
            )}
          </div>

          {reviewStep === "configuration" ? <footer>
            <div><span>原始方案</span><b>95 / 90 / 85</b></div>
            <div><span>干预方案</span><b>{westShare} / {centralShare} / {eastShare}</b></div>
            <div><span>突发事件</span><b>{eventEnabled ? selectedEvent?.title : "不注入"}</b></div>
            <button className="primary-action launch-action" disabled={!canLaunch} onClick={launch} type="button">
              {pending ? "正在生成中央解读…" : "生成中央政策解读"}<Play weight="fill" />
            </button>
          </footer> : <footer className="review-footer"><div><span>当前门禁</span><b>{dialogTitle}</b></div><div><span>下一步</span><b>{reviewStep === "interpretation" ? "A/B 实验设计" : reviewStep === "design" ? "代理数据基线" : "七轮同源推演"}</b></div><div /><button className="primary-action launch-action" disabled={pending || !draft} onClick={reviewStep === "interpretation" ? onConfirmInterpretation : reviewStep === "design" ? onConfirmDesign : onConfirmBaseline} type="button">{pending ? "正在冻结…" : reviewStep === "interpretation" ? "确认中央解读" : reviewStep === "design" ? "确认实验设计" : "确认基线并进入推演"}<Check weight="bold" /></button></footer>}
          {reviewStep === "configuration" && !validActiveDifference && tab === "event" && !error ? <div className="configuration-validation"><p>{branchScope === "treatment_only" && eventEnabled ? "仅干预方案受事件冲击时，两方案政策比例必须完全相同。" : "干预方案至少需要有一档比例不同于原始方案。"}</p><button onClick={() => setTab("policy")} type="button">返回政策比例</button></div> : null}
          {error ? <div className="configuration-error"><p className="error-copy">{error}</p>{reviewStep === "configuration" && !catalog ? <button onClick={onRetryCatalog} type="button">重新载入事件目录</button> : null}</div> : null}
        </section>
      ) : null}

      {introActive ? (
        <GlobeIntro
          collection={collection}
          onComplete={completeIntro}
          onError={completeIntro}
          reducedMotion={reducedMotion}
          runId={introRunId}
        />
      ) : null}
    </main>
  );
}
