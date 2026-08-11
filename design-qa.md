# PolicyScope V2 Stitch Design QA

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
| P0 | Core Stitch links and approvals were static | Rebuilt as React Router + API/SSE actions |
| P1 | Result route refresh could lose branch completion state | Completed comparison and single-branch states now restore from API state |
| P1 | Global evidence action changed Compare to Live | Drawer now opens on the current route and preserves query state |
| P1 | Completed experiments could reopen SSE | SSE stops after terminal completion and retains replay state |
| P1 | New experiment did not clear active state | Reset action now clears context and returns to T0 |
| P2 | Page transitions retained the previous scroll position | Route-level scroll restoration added |
| P2 | Initial ECharts bundle produced a monolithic build warning | Routes and ECharts are lazy-loaded into separate chunks |

## 6. Remaining release gate

No P0, P1 or P2 product/design issue remains open. The following is a compliance release gate rather than a UI defect:

- The map is derived from the Natural Resources Ministry standard map GS(2016)1609 and passes source checksum, geometry checksum and 31-province annotation validation. Public deployment remains blocked until a human confirms the applicable standard-map attribution and edited-map review requirements. See `apps/web/src/assets/maps/README.md`.

## 7. Final decision

`final result: passed`

The implementation is visually aligned with Stitch, materially improves the original static references by making the flow truthful and operable, and satisfies the 1280 desktop constraint. The 1440 × 900 layout has more available space under the same grid and has no unresolved blocker.
