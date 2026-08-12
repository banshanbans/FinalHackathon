---
name: PolicyScope
version: V3.0-implemented
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
