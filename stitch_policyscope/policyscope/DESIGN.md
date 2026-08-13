---
name: PolicyScope
version: V3.1-implemented
status: implemented-design-qa-passed
colors:
  surface: '#f8f9ff'
  surface-dim: '#c9dcf7'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dbe9ff'
  surface-container-highest: '#d1e4ff'
  on-surface: '#081d30'
  on-surface-variant: '#434655'
  inverse-surface: '#1f3246'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#5548e7'
  primary: '#5548e7'
  on-primary: '#ffffff'
  primary-container: '#e3e0ff'
  on-primary-container: '#211a70'
  inverse-primary: '#c4c0ff'
  secondary: '#006a63'
  on-secondary: '#ffffff'
  secondary-container: '#99efe5'
  on-secondary-container: '#006f67'
  tertiary: '#315da8'
  on-tertiary: '#ffffff'
  tertiary-container: '#d9e6ff'
  on-tertiary-container: '#0d2f68'
  warning: '#9a6700'
  warning-container: '#fff1c2'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  background: '#f7f8fb'
  on-background: '#081d30'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  display-md:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Noto Sans SC
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Noto Sans SC
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Noto Sans SC
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  metric-value:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  grid_columns: '12'
  gutter: 24px
  margin: 32px
  unit: 8px
  max_width: 1536px
map:
  primary_canvas_min_share: '58%'
  default_fill_layer: local_subsidy_intensity
  fill_layers:
    - local_subsidy_intensity
    - consumer_subsidy
    - fixed_cost_subsidy
    - variable_cost_subsidy
    - wtp
    - industry_base
  overlay_layers:
    - battery_nodes
    - automaker_sales_activity
    - simulated_facility_activity
---

## Brand & Product Character

PolicyScope / 政策涟漪 V3.0 is a map-first policy simulation workbench for comparing how central–local subsidy sharing may reshape provincial policy space, simulated automaker behavior, and the geographic distribution of China’s new-energy-vehicle development.

The product character remains **Modern Institutionalism**: rational, restrained, high-density and evidence-led. It must not look like an automotive consumer website, a corporate brand showcase, or a glowing “big data” wall. The interface should feel like a policy analysis instrument whose main surface is a working map.

This file is the visual source of truth for the implemented V3.0 runtime. The map-first five-route frontend passed the 1536×1024, 1440×900 and 1280 desktop QA matrix; V2.1 remains historical only.

## V3 Contract Snapshot

- Default policy: 西部 95%、中部 90%、东部 85%。
- Phases: `SETUP → Y1_Q1 → Y1_Q2 → Y1_Q3 → Y1_Q4 → YEAR1_REVIEW → Y2_Q1 → Y2_Q2 → Y2_Q3 → Y2_Q4 → COMPLETE`.
- Automakers: 比亚迪、吉利、长安、上汽通用五菱、蔚来、奇瑞、零跑、赛力斯、小米汽车、理想汽车。
- National metrics: 区域发展差距、中央财政负担、地方财政压力、新能源汽车需求、新增投资集中度、产业集聚度。
- Schema versions: `policy-v3`、`province-profile-v4`、`province-persona-v2`、`province-action-v4`、`province-feedback-v4`、`automaker-profile-v1`、`automaker-action-v1`、`world-state-v4`、`comparison-v4`、`event-v4`.
- Routes: `/experiments/new`、`/experiments/:id/live`、`/experiments/:id/provinces/:provinceCode`、`/experiments/:id/intervention`、`/experiments/:id/compare`.

## Source-of-Truth Colors

Color segments information by provenance rather than by automaker brand:

- **Deep Navy (`#202537`)**: structure, navigation and primary text.
- **Policy Indigo (`#5548E7`)**: central policy controls, active stages and primary actions.
- **Institutional Blue**: approved policy values, input diffs and user decisions.
- **Evidence Teal**: deterministic environment results, verified facts and mechanism evidence.
- **Agent Indigo**: provincial and automaker simulated actions and pending hypotheses.
- **Amber**: fiscal pressure, non-monotonic policy warnings and conditional states.
- **Restrained Red**: failures, rejection and severe data problems.

Do not assign permanent colors to BYD, Geely, NIO or other real automakers. Corporate brand palettes and logos are outside P0 and may imply endorsement or authorization.

## Typography

Use Inter for quantitative values, English labels, IDs and machine concepts. Use Noto Sans SC for Chinese prose and business labels. Headline hierarchy must remain compact enough for a dense map workbench, while body content should not fall below 14px except for secondary metadata and chart annotations.

## Layout & Map Priority

The interface uses a 12-column fluid grid with an 8px spacing system and 24px gutters.

1. **Global Shell**: 244px/216px sidebar plus a two-level header.
2. **Policy Phase Rail**: `SETUP → Y1 Q1–Q4 → YEAR1 REVIEW → Y2 Q1–Q4 → COMPLETE`.
3. **Map Analysis Canvas**: the China map occupies at least 58% of the primary content region on desktop.
4. **Context Rail**: current sharing ratios, quarter, agent progress and events.
5. **Secondary Analysis**: metrics, trends, transition tables and mechanism evidence below the map.

The six national metrics are a compact decision summary, not the dominant visual. White space should preserve map legibility and distinguish policy, agent and environment layers.

## Map Layer Grammar

Only one province fill layer may be active at a time:

- local subsidy intensity (default)
- consumer subsidy
- fixed-cost subsidy
- variable-cost subsidy
- willingness to pay
- industrial base

Overlay layers can be independently toggled:

- battery supply-chain nodes
- selected automaker sales activity
- simulated plant/expansion activity

Every China map keeps the national silhouette visually complete. Hong Kong,
Macao and Taiwan use the same frozen Ministry of Natural Resources map source
as a neutral `territory-context` layer. They remain visible and labelled but
never inherit the 31-province metric scale, missing-data texture, selection,
interaction glow or simulation semantics.

Battery nodes use neutral supply-chain icons. Automaker activity uses text labels, initials or neutral markers. Simulated plant activity must include a visible “模拟” state and must never be styled as a confirmed factory announcement.

## Elevation & Shapes

Elevation remains sparse:

- **Level 0**: `#F7F8FB` page background.
- **Level 1**: white card, 1px `#E6E9F1` border, soft low-opacity shadow.
- **Level 2**: hover, selected province and active layer.
- **Level 3**: automaker side panel and evidence drawer.

Use 12px card corners, 8px controls and pill status tags. Avoid glassmorphism, neon glow and decorative 3D effects.

## Core Components

- **Regional Share Editor**: west/central/east values, `95% / 90% / 85%` defaults, absolute/delta modes, independent validation and a non-blocking non-monotonic warning.
- **Quarter Phase Rail**: explicit year and quarter, with approval gates that cannot be skipped.
- **Map Layer Control**: separates fill layers from overlays and never triggers agent execution.
- **Province Focus Card**: fiscal space, three subsidy shares, peer response and result summary.
- **Automaker Simulation Card**: real-data baseline label, neutral company name, simulated ROI band and action summary; no logo.
- **Facility Activity Marker**: new plant, expansion or delay, always prefixed with simulated status.
- **Gap/Delta Card**: normalized Gap, `ΔGap = treatment − control`, direction and evidence link.
- **Mechanism Evidence**: central-share relief, local fiscal constraint, WTP, battery distance, fixed/variable cost, channel and facility effects.
- **Source Tags**: Central Policy, Provincial Strategy, Automaker Simulation, Environment Calculation, User Decision and Real-data Baseline.

## Content Boundaries

Required phrases include:

- “2025 年政策参考基线”
- “真实数据基线 / 模拟车企行动”
- “本次实验省级决策画像”
- “原始方案 / 干预方案”
- “模拟指数变化”

Forbidden content includes:

- a real-world optimum or “optimized plan” claim
- future real sales, profit, investment or fiscal amount forecasts
- automaker commitments or confirmed factory language
- official-government identity cues
- confidence percentages without a real statistical definition

## Responsive Desktop Behavior

- At 1536×1024 and 1440×900, the full map, active layer, phase, policy ratios and main CTA must be immediately reachable.
- At 1280px, the context rail may move below the map; the map cannot be clipped or replaced with a thumbnail.
- No page-level horizontal scrolling.
- Mobile is not a P0 deliverable.

## V3.1 Event Interaction Addendum

- Event Lab uses the existing white institutional card, indigo approval action and muted scenario disclaimer; event families do not introduce alarm-red or news-ticker styling.
- The interaction sequence is a compact four-step strip: event, province signal, authorized Peer response, coordination match. It must remain secondary to the China map.
- `event_exposure` uses the existing sequential indigo/teal scale. `province_interaction` uses response intensity for province fill; matched relations use success teal and unmatched proposals use amber text without a success line.
- Comparison proof is a four-cell evidence row before maps: active difference, parent Checkpoint, same policy, same event.
- Event counterfactual labels are “无事件基线 / 事件情景”; policy comparison labels remain “原始方案 / 干预方案”.
- Scenario approval is visually irreversible after submission: controls disabled, lock status visible, and no edit affordance.

## M33 Presentation Hall Addendum

The Presentation Hall is a separate full-screen surface, not a dark theme applied to the existing SaaS shell. It borrows the cinematic spatial hierarchy of the approved Earth Map reference while retaining PolicyScope's evidence-led product boundaries.

- The China map occupies 70–80% of the visible stage. Navigation becomes a floating HUD and a right-side tool dock; the permanent SaaS sidebar is removed.
- The palette shifts to near-black navy surfaces with restrained policy indigo, evidence teal, event amber and competition red. Color still encodes provenance and state, never automaker brands.
- Glass treatment is limited to HUD, timeline and floating panels. Text-bearing panels require sufficient opaque backing and WCAG AA contrast; decorative glow must not obscure province boundaries.
- The bottom timeline is a first-class control with a draggable thumb, frozen frame nodes, diamond event markers, speed controls and current-frame labeling.
- Motion follows a fixed grammar: camera, province fill, relation draw, subject marker, narrative panel, metric. Reduced-motion mode replaces spatial transitions with short fades.
- The opening is a single 3–5 second spatial sentence: a real vector globe rotates in deep space, the camera approaches China, all 31 provinces gain a restrained teal focus, and the flat national simulation map crossfades into the same focal area. It contains no business metrics or synthetic run state.
- Keep the opening skippable and replayable. Under `prefers-reduced-motion`, replace orbit and long camera travel with a sub-second focus-and-fade handoff.
- Use the GovSim Glass UI Kit as a spatial control language, not a page material. The map and live relationships stay visually dominant; glass is reserved for floating panels, pills, segmented controls, context popovers, the command/scenario bar, timeline rail, and sheets.
- Base glass token: `rgba(18,18,22,.55)`, `blur(24px) saturate(140%)`, `1px solid rgba(255,255,255,.10)`, `22px` radius, `0 12px 40px rgba(0,0,0,.22)` shadow, and a restrained inset/top-edge highlight. Use an extremely subtle vertical white highlight gradient for environmental light.
- Never arrange these surfaces into a dashboard card matrix. Preserve 70–80% of the stage for the map and reveal information progressively: spatial action first, one large metric second, detail and evidence only after an explicit click.
- Copy inside floating glass is aggressively compressed: subject, action label, one dominant value, one state chip. Long policy explanations and structured Agent rationale belong in a side or bottom sheet.
- Event scenes use amber/indigo emphasis and map propagation, not breaking-news tickers, sirens or war imagery. Geopolitical examples remain neutral simulation scenarios.
- MapLibre GL JS and deck.gl may be used only with locally packaged, provenance-preserving geometry derived from the frozen standard map. The verified ECharts/SVG map remains the compatibility renderer.
- Target presentation canvases are 1920×1080, 2560×1440 and 3840×2160, with 1536×864 and 1366×768 retained for operator fallback checks.
- M33 is frozen: high-resolution canvases scale the floating controls without scaling the map geometry; WebGL loss switches to the local 31-province SVG compatibility renderer; offline and fake rehearsals retain the last frozen frame and show `OFFLINE` / `FAKE / FALLBACK` explicitly.
