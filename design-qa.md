# PolicyScope V2 / V2.1 Stitch Design QA

## V2.1 status

> Contract: “省级 Agent 主决策、企业 Agent 作市场反馈”
> Status: **high-density redesign implemented; verification paused**
> V2.1 final result: **pending redesign verification**

V2.1 独立省级 Agent 详情路由以及 Live、Intervention 和 Compare 的省级优先信息层级已实现；全站已进一步按 `policyscope-dashboard-reference` 全国态势原型重构为高密度制度工作台。按用户要求，自动化测试、Playwright E2E 与截图比较当前暂停；本文件后续的 V2 `passed` 只证明历史基线，不代表 V2.1 新版视觉已通过。

V2.1 视觉门禁至少包括：

- Live 默认地图为地方执行强度，省级决策事件优先。
- 全局 244px/216px 壳层、双层顶栏、真实最近访问、五路由阶段门禁和生产级中文文案。
- Live 四层驾驶舱：六指标、地图+政策、三组真实派生图表+关键事件、T0–T5 时间线。
- Replay 趋势仅消费 `environment.updated`，SSE 增量按 `event_id` 去重；缺少节点时不插值。
- 页面使用 `province-persona-v1`、`province-profile-v3`、`province-action-v3`、`province-feedback-v3`、`world-state-v3`、`comparison-v3` 和 `event-v3`，不以 V2 前端静态推导替代。
- 五个正式路由覆盖中央政策、Live、省级详情、干预审批和 Compare；完整 A/B 预算仍为中央 3 次、省级约 124 次、企业约 93 次，Persona 不增加模型调用。
- 河南、广东、山西的实验决策画像、目标约束和省际策略页面。
- T3 先展示省级目标、支持请求与调整意向。
- A/B 先展示省级策略迁移，再展示企业行为迁移。
- 五路由在 1536 × 1024、1440 × 900 与 1280 宽的截图、可访问性、禁止文案和真实 API 状态检查。

只有 V2.1 实现完成、P0/P1/P2 全部关闭后，才能把上述结果改为 `passed`。

---

## V2 historical result

> QA date: 2026-08-12
> Reference: `stitch_policyscope/**/screen.png` + `stitch_policyscope/policyscope/DESIGN.md`
> Runtime: React Router + real API/SSE + local assets
> Final result: **passed**

## 1. Scope and method

The five Stitch reference screens were compared side-by-side with the final runtime states in the in-app browser:

| Reference | Runtime state | Result |
|---|---|---|
| `_1/screen.png` | T0 generated policy draft awaiting approval | Passed |
| `_2/screen.png` | T3 national live simulation | Passed |
| `_3/screen.png` | `?province=41` Henan enterprise drawer | Passed |
| `_4/screen.png` | T3 evidence → AI recommendation → human decision | Passed |
| `a_b/screen.png` | T5 source-identical A/B comparison | Passed |

The selected browser exposed a 1280 × 720 viewport. The entire flow passed on this stricter width and height without horizontal overflow (`scrollWidth = innerWidth = 1280`). The 1440 × 900 acceptance canvas uses the same grid with additional space; responsive breakpoint, component bounds and full-page captures were also checked. P0 is desktop-only.

QA used runtime browser screenshots, DOM accessibility snapshots and real API state. Static Stitch HTML was not iframe-embedded or published as product code.

## 2. Visual fidelity

- Light institutional workbench, fixed left navigation, restrained blue/teal/indigo semantics, white cards and compact evidence typography match the approved direction.
- Information hierarchy is consistent across four routes: task eyebrow, single H1, status gate, result cards and audit detail.
- Inter and Noto Sans SC are bundled locally; Material Symbols are also local. No runtime Google CDN is required.
- T3 preserves the required three-column evidence/recommendation/decision structure.
- A/B keeps neutral labels “原始方案 / 干预方案” and does not call the Treatment an “optimized” result.
- The official standard-map-derived SVG is denser than the Stitch illustrative map. This is an intentional compliance and product-truthfulness difference, not a fidelity defect.

## 3. Product truthfulness and interaction

- All four routes are deep-linkable and protected by experiment phase.
- Creation, approval, T1–T3 run, Henan drawer, intervention approval/rejection, branch run, compare and evidence actions call real APIs.
- Evidence and province drawers preserve the current route and other query parameters when opened/closed.
- 31 province regions are keyboard-addressable and use a single shared geometry and scale in national and A/B views.
- Henan shows all six enterprise groups, local tools, participation, upgrade type, financing choice and mechanism contribution.
- The approval path creates Treatment only after server-side approval; the rejection path creates no fake branch and completes a single-branch T5 review.
- Empty, loading, running, awaiting approval, approved, completed, fallback, failure and reconnecting states have explicit treatments.

## 4. Content and accessibility

- Chinese is primary; only T0–T5, Agent, Control/Treatment and audit machine identifiers remain where useful.
- Simulation outputs use `/100` and “指数点变化”. Percentage formatting is limited to real policy parameters.
- “待验证” distinguishes model hypotheses from environment results.
- Model strategy and deterministic environment calculations use separate visual labels.
- The scenario disclaimer is visible on every route.
- Interactive controls have semantic names; province regions have buttons and a keyboard list; status is expressed with text as well as color.
- Forbidden-copy scan found no real-world GDP, employment, investment amount or guaranteed-effect claim.

## 5. Closed issues

| Priority | Issue | Resolution |
|---|---|---|
| P0 | Static/fake map and blank A/B map | Replaced with one local, source-recorded ECharts SVG used by both views |
| P0 | Province regions were shifted by one source path and labels duplicated | Skipped the national fill path, bound every province code to an individual geometry signature, and retained only the source label layer |
| P0 | Core Stitch links and approvals were static | Rebuilt as React Router + API/SSE actions |
| P1 | Result route refresh could lose branch completion state | Completed comparison and single-branch states now restore from API state |
| P1 | Global evidence action changed Compare to Live | Drawer now opens on the current route and preserves query state |
| P1 | Completed experiments could reopen SSE | SSE stops after terminal completion and retains replay state |
| P1 | New experiment did not clear active state | Reset action now clears context and returns to T0 |
| P2 | Page transitions retained the previous scroll position | Route-level scroll restoration added |
| P2 | Initial ECharts bundle produced a monolithic build warning | Routes and ECharts are lazy-loaded into separate chunks |

## 6. Release status

No P0, P1 or P2 product/design issue remains open.

- The map is derived from the Natural Resources Ministry standard map GS(2016)1609 and passes the source checksum, aggregate geometry checksum, 31-province completeness check, and per-province code-to-geometry signature validation.
- Based on the competition release rule confirmed by the user, the competition build has no additional map-compliance release gate and may publish this asset directly. See `apps/web/src/assets/maps/README.md`.

## 7. Final decision

`final result: passed`

The implementation is visually aligned with Stitch, materially improves the original static references by making the flow truthful and operable, and satisfies the 1280 desktop constraint. The 1440 × 900 layout has more available space under the same grid and has no unresolved blocker.
