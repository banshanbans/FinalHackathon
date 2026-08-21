# 13110 Roadshow Design QA

## Enterprise display to live Earth return — 2026-08-14

- Source visual truth: the existing original WebGL Earth and sphere-attached China layer in `src/visuals/GlobeStage.tsx`.
- Implementation evidence: `qa/enterprise-to-earth-midpoint.png` and `qa/earth-return-china-on-globe-final.png`.
- Three-state comparison: `qa/enterprise-to-earth-storyboard.png`.
- Viewport: 1280 × 720 CSS pixels at 1×.

### Required fidelity surfaces

- Typography: enterprise typography exits before the Earth becomes dominant; no presentation headline is added over the final globe.
- Spacing/layout: the portal originates at the center-display area and expands until the cabin is fully removed. The terminal Earth returns to the established right-dominant orbital composition with black negative space.
- Colors/tokens: the bridge uses only the established policy teal rim; the final atmosphere, Blue Marble and China teal match the original shader/material tokens.
- Image quality: the terminal is the original local 4096 × 2048 Blue Marble texture and validated China texture rendered by the same Canvas. No raster Earth, duplicate Canvas or remote asset is introduced.
- Copy/content: the returned China layer retains complete national context; no company logo, real-world forecast or new claim appears.

### Comparison history

- Pass 1 — blocked by new scope: the sequence stopped at the enterprise Agent display and had no return to the Earth visual.
- Fix: added a separate return signal to the existing GlobeStage, a center-display portal timeline, radial cabin removal and reverse China projection.
- Pass 2 — passed: the midpoint and terminal captures show one uninterrupted takeover from the dark enterprise cabin to the live Earth, with China visibly restored on the sphere.

### Browser and build verification

- Real wheel input reaches `earth-return`; one Canvas remains mounted, `scrollY = 0`, horizontal overflow = 0 and the vehicle layer reaches opacity 0.
- Browser console errors/warnings: none.
- `npm run verify` passes 7 unit tests, TypeScript strict, boundary scans, production build, Sites artifact preparation and 4 Sites worker tests.
- P0/P1/P2 findings: none.

final result: passed

---

## Frontal province close-up and enterprise super-screen — 2026-08-14

- User distance/crop reference: `/Users/carrey/Desktop/Screenshot 2026-08-14 at 00.38.27.png` (2384 × 1692).
- Province visual truth: `references/sichuan-province-agent-option3.png`.
- Frontal production target: `public/assets/policy-road/province-agent-frontal-close.png`.
- Province-in-cabin target: `public/assets/policy-road/high-pylon-province-from-nev-interior.png`.
- Browser evidence: `qa/province-frontal-close-final.png`, `qa/province-to-cabin-direct.png`, `qa/enterprise-super-screen-dark-window.png`.
- Source/implementation comparison: `qa/user-close-vs-province-frontal.png`; the source was normalized to 1280 × 720 for distance comparison, implementation is 1280 × 720 CSS pixels at 1×.

### Required fidelity surfaces

- Typography: the frontal province frame preserves option 3's cyan hierarchy, six fingerprint axes and experiment-persona terminology. The enterprise screen retains the established 600/400 Inter-system hierarchy.
- Spacing/layout: the province billboard fills a comparable near-camera area to the user screenshot while correcting perspective to an almost frontal view. Only the screen, thin support and restrained black negative space remain. The enterprise terminal frame enlarges to `1.72×`, leaving only enough steering wheel/windshield to prove cabin location.
- Colors/tokens: black environment, restrained teal semantics and white ink remain unchanged. A 0.78 exterior shade lowers only the windshield world during the enterprise focus.
- Image quality: frontal billboard and province-cabin continuity use local raster assets; no hand-drawn screen, vehicle or remote image was introduced.
- Copy/content: province state remains `本次实验省级决策画像`; enterprise state uses simulation-safe actions and contains no real-world prediction, amount, promise or logo.

### Comparison history

- Pass 1 — blocked: the province change happened at the distant oblique road view, contrary to the requested close and frontal presentation.
- Fix: added a 1.62× national-screen approach followed by a long blurred cross-orientation into the generated frontal province target.
- Pass 2 — blocked: the initial sequence restored the nationwide billboard before the cabin entered.
- Fix: removed the province-to-national reversal; the cabin edge and full-cabin sources now retain the province Agent content through the windshield.
- Pass 3 — passed: the province terminal is close/frontal, the next state directly returns to the province-content cabin, and the enterprise terminal is a `1.72×` super-screen with the exterior darkened.

### Browser and build verification

- Real wheel input verified the close province endpoint, direct province-to-cabin pullback and dark-window enterprise endpoint.
- Final browser state retains one Canvas, `scrollY = 0`, no horizontal overflow and no console errors/warnings.
- `npm run verify` passes 7 unit tests, TypeScript strict, boundary scans, production build, Sites artifact preparation and 4 Sites worker tests.
- P0/P1/P2 findings: none.

final result: passed

---

## Apple continuity refinement — 2026-08-14

- Selected source visual: `references/sichuan-province-agent-option3.png`.
- Screen-content source: `public/assets/policy-road/sichuan-province-agent-screen-source.png`.
- Aligned cabin source: `public/assets/policy-road/high-pylon-from-nev-interior-aligned.png`.
- Implementation states: `qa/province-screen-only-transition-final.png`, `qa/cabin-return-feathered-midpoint.png`, `qa/enterprise-agent-zoom-140-final.png`.
- Equal-size visual comparison: `qa/option3-screen-only-comparison.png`.
- Source normalization: 1487 × 1058 cropped and normalized to 1280 × 720; implementation captures are 1280 × 720 CSS pixels at 1×.

### Required fidelity surfaces

- Typography: the selected cyan/white hierarchy, six-axis labels and lower-left 600-weight statement remain consistent; cabin and enterprise text retain the established Inter/system stack and tight Apple-like tracking.
- Spacing/layout: the province image is perspective-mapped inside the original LED quadrilateral. The billboard frame, mast, sky, horizon and road remain owned by the unchanged base photograph. The enterprise terminal frame keeps a visible steering wheel, windshield and road around the enlarged center display.
- Colors/tokens: true black, restrained policy teal and white ink remain unchanged. The screen resolve changes blur/exposure only and introduces no decorative color or glass treatment.
- Image quality: the screen content and cabin are project-owned raster assets. No CSS-drawn province, cabin, placeholder or remote request is used. Feather masks affect transition visibility only.
- Copy/content: the province portrait remains explicitly `本次实验省级决策画像`; enterprise copy remains simulation-safe and contains no logo, real amount, forecast or commitment.

### Comparison history

- Pass 1 — blocked: the province state crossfaded a complete alternate road photograph, so the billboard, mast and environment appeared to change together.
- Fix: retained the original road photograph as the only physical world and perspective-mapped the selected province content through a polygon mask limited to the existing LED face. Added a slow blur/brightness resolve and separate lower-left copy crossfade.
- Pass 2 — blocked: the first cabin edge treatment exposed a hard central rectangle and a long double-road dissolve.
- Fix: removed the opaque container background and exterior scale change; feathered separate A-pillar/dashboard masks first, delayed the full aligned-cabin resolve, and shortened the final exterior crossfade.
- Pass 3 — passed: `qa/province-screen-only-transition-final.png` shows complete option-3 content while the physical scene remains fixed; `qa/cabin-return-feathered-midpoint.png` shows the cabin framing entering without a hard page boundary; `qa/enterprise-agent-zoom-140-final.png` shows the stronger `1.40×` approach with cabin context retained.

### Browser and build verification

- Real wheel input traversed all three revised segments in the in-app browser.
- Terminal state: `enterprise-agent`; one Canvas; `scrollY = 0`; horizontal overflow = 0.
- Browser errors/warnings: none.
- `npm run verify` passes 7 unit tests, TypeScript strict, boundary scans, production build, Sites artifact preparation and 4 Sites worker tests.
- P0/P1/P2 findings: none.

final result: passed

---

## Option 3 province-to-enterprise continuation — 2026-08-14

- Selected visual truth: `references/sichuan-province-agent-option3.png`.
- Exact-road production composite: `public/assets/policy-road/sichuan-province-agent-portrait.png`.
- Browser implementation evidence: `qa/province-agent-browser.png` and `qa/enterprise-agent-browser.png`.
- Same-viewport source comparison: `qa/province-agent-comparison-1440x768.png`.
- State chain: `policy-signal → province-agent → vehicle-interior → enterprise-agent`.

### Fidelity and continuity

- The settled high-pylon frame now keeps the eyebrow and statement in the lower-left road negative space. Nothing remains in the lower-right.
- Continued wheel input changes the same physical LED surface into the selected Sichuan experiment persona. The visible hierarchy matches option 3: province silhouette, six decision axes, peer observation/competition signals, battery-node context and purchase-willingness proxy.
- The selected concept was recomposited onto the existing road frame, preserving the current screen, single mast, wet expressway, horizon and camera geometry. The electronic-screen change therefore reads as content inside one location rather than a new slide.
- The province portrait exits back through the aligned national screen. Cabin and exterior then overlap for 2.65–2.75 timeline units while one quintic pullback settles from `1.28×` to `1×`; there is no opaque page wipe or route change.
- The final camera move enlarges the whole cabin world to `1.16×` around the center-display region. Steering wheel, windshield, billboard and road remain visible, so the enterprise Agent surface is still clearly inside the vehicle.
- Enterprise content uses only simulation-safe language: 10 simulation subjects, 31 province-level market-input entries, 0–3 capacity-action targets, and `真实数据基线 / 模拟车企行动`. There are no logos, real amounts, forecasts or commitments.

### Browser and build verification

- In-app browser reached the settled road frame, province Agent frame and enterprise Agent terminal frame through real wheel input. Reverse frames use the same paused timelines.
- One persistent WebGL Canvas remains mounted; native document scrolling remains locked.
- Browser console contains no error or warning; all observed assets are local.
- `npm run verify` passes 7 unit tests, TypeScript strict, boundary scans, production build, Sites artifact preparation and 4 Sites worker tests.
- P0/P1/P2 findings: none.

final result: passed

---

## M36 13110 product-reveal pass

- Opening source visual truth: `references/orbital-precision.png`.
- Terminal composition reference: `../../outputs/m35-presentation-design/qa-interaction-1920x1080.png`.
- Opening implementation: `qa/implementation-1440x1024-13110-opening.png`.
- Historical focus implementation: `qa/implementation-1440x1024-13110-lift.png`.
- Terminal implementation: `qa/implementation-1440x1024-13110-terminal.png`.
- Responsive terminal evidence: `qa/implementation-1280x720-13110-terminal.png`, `qa/implementation-1920x1080-13110-terminal.png`.
- Latest wheel-safe opening: `qa/implementation-1920x1080-13110-opening-wheel-fix.jpg`.
- Latest wheel-safe terminal: `qa/implementation-1920x1080-13110-terminal-wheel-fix.jpg`.
- Real-wheel sequence: `qa/wheel-virtual-stability-final.jpg`.
- Camera-first transition storyboard: `qa/camera-focus-storyboard.jpg`.
- Single-dolly nonlinear storyboard: `qa/apple-dolly-storyboard.jpg`.
- Complete national geography evidence: `qa/china-complete-with-south-china-sea.png`.
- Combined opening comparison: `qa/source-vs-13110-opening.png`.
- Combined terminal comparison: `qa/m35-vs-13110-terminal.png`.
- CSS comparison viewport: 1440 × 1024 at deviceScaleFactor 1 for the selected opening; 1920 × 1080 at deviceScaleFactor 1 for the causal-stage handoff.
- Source and implementation pixels are equal within each combined comparison; no density normalization was required.
- States: settled orbital product reveal, continuous camera approach to China, and stable causal handoff.

### Full-view comparison evidence

The opening preserves the approved Apple-inspired composition: full-bleed black canvas, restrained descriptor and action, monumental typography on the left, and a single locally textured globe cropped on the right. `13110` replaces the historical headline as the product-memory anchor without changing the one-subject hierarchy.

The terminal deliberately does not reproduce the full M35 interface. It matches the handoff geometry needed by the independent opening: a centered national map, the same causal question at the top, and a dark stage ready for M35 to add its left chain, right game panel and quarterly rail. The `1 / 31 / 10` typography remains part of the reveal and does not become a card grid.

### Focused evidence

- Fonts and typography: system/Inter display stack, 600-weight `13110`, tight tracking and 17px action copy preserve the source's hierarchy. Chinese labels use the local Noto/system fallback with no remote font request.
- Spacing and layout rhythm: the left copy stays within the first third in Scene 00; the terminal map owns the center and the three identity columns align along the lower stage edge. 1280 × 720 and 1920 × 1080 captures show no horizontal overflow or core-copy clipping.
- Colors and tokens: true black, `#f5f5f7` ink, restrained teal geography and one action blue remain unchanged. No dashboard cards, decorative gradient or glass panel was introduced.
- Image quality and assets: the 4096 × 2048 local NASA Blue Marble and frozen 34-feature vector geography remain the only hero assets. The transition retains one WebGL Canvas; China remains attached to the globe while the camera approaches it.
- Copy and content: all public surfaces use `13110`, `新能源汽车产业协同推演`, `让政策影响，被看见。`, `进入年度推演`, and the approved `1 / 31 / 10` explanation. Browser title, accessibility region and error state no longer expose the historical public brand.

### Interaction and browser verification

- CTA travel is deliberately paced at about 7.2 seconds; scroll and keyboard Enter use the same master progress.
- In-app browser verified the settled opening, CTA transition, keyboard transition, 1280 × 720 layout, 1920 × 1080 layout, persistent single Canvas and terminal state.
- Browser console errors: none.
- All observed production requests were local; source and production boundary scans reject remote URLs, `/api` and cross-application imports.

### Comparison history

#### Pass 1 — blocked

- P1: public metadata, error copy and the opening content contract still exposed the historical product name.
- P1: the two-scene contract could not explain the `13110` naming or establish a terminal causal-stage composition.
- P2: the native button behavior did not provide an explicit shared Enter/Space handler across browser surfaces.

#### Pass 2 — passed

- Replaced every public brand surface with `13110` while preserving the internal package/history identifier.
- Upgraded the validated content contract to four scenes and added the restrained `1 / 31 / 10` identity reveal.
- Extended the one-Canvas timeline to about 7.2 seconds and added an M35-grounded terminal question without importing Presentation runtime code.
- Added explicit Enter/Space handling, reduced-motion terminal behavior and responsive terminal verification.
- Post-fix combined comparisons show no actionable P0/P1/P2 mismatch for the approved independent-opening scope.

#### Pass 3 — blocked after user review

- P1: the user's physical mouse still produced crash-like dark flashes even though the fixed Canvas and ScrollTrigger path did not remount React.
- Root cause: native document displacement continued to involve the macOS scrolling compositor, while the postprocessing composer swapped an additional multisampled framebuffer under GPU pressure.

#### Pass 4 — passed

- Replaced native document scrolling with viewport-locked virtual wheel progress. Wheel input now changes a target consumed by one GSAP ticker; `scrollY` remains `0` and document height equals viewport height throughout the shot.
- Removed the postprocessing composer and multisampled offscreen buffers. The existing atmosphere shader supplies direct rim lighting, and DPR is capped at 1.5 below 2K and 1 at 2K/4K.
- `qa/wheel-virtual-stability-final.jpg` shows four real downward-wheel states from the opening through the stable terminal frame with one persistent Canvas and no black compositor rectangle.
- A 36-input rapid reversal stress run retained one Canvas, zero document displacement and no console error. The dedicated Playwright wheel regression and all six existing interaction/responsive checks pass: 7/7.
- No actionable P0/P1/P2 finding remains for the approved opening and wheel path.

#### Pass 5 — passed after camera-direction review

- P1 user finding: the prior transition read as the China map moving toward the audience instead of the viewpoint travelling toward China.
- Removed the overlay's radial lift entirely. During the first two thirds of the transition, the China geometry remains at the globe radius while the camera advances from `z=8.45` toward the surface and the globe is reframed around China.
- Delayed the spherical-to-national projection until after the close approach, so projection alignment is a handoff rather than the dominant movement cue.
- Renamed the active semantic scene and public chapter from “中国浮起” to “聚焦中国”; the accessibility status now says “镜头正在推进并聚焦中国”.
- `qa/camera-focus-storyboard.jpg` shows the globe edge expanding out of frame, the surface detail enlarging beneath the attached China layer, and the final national-map alignment. The map does not translate forward as an independent object.
- The camera-first revision preserves zero native page displacement, one persistent Canvas and the wheel-safe renderer. Unit/build/Sites checks and all 7 browser tests pass.

#### Pass 6 — passed after single-dolly review

- P1 user finding: the camera push was followed by an apparent second zoom during projection settling, and the overall velocity still felt generically eased rather than Apple-like.
- Removed the model-space zoom entirely: globe position, rotation and scale are now constant throughout the shot, with scale locked to exactly `1`.
- Removed the late camera pullback. The camera follows one monotonic dolly path from the orbital frame toward the China surface point; the projection resolves at the same depth and apparent footprint.
- Replaced stacked GSAP and renderer easing with one quintic ease-in-out whose endpoint velocity and acceleration are both zero. This creates a restrained opening, decisive middle acceleration and long soft terminal settle without a second movement beat.
- `qa/apple-dolly-storyboard.jpg` records the middle, late and terminal frames. China's apparent footprint increases monotonically across all three frames; there is no shrink or renewed scale-up at the handoff.
- In-app browser inspection showed one continuous visual approach. Strict TypeScript, 6 unit tests, production/Sites builds and all 7 browser tests pass with one persistent Canvas and no native page displacement.

#### Pass 7 — passed after national-map completeness review

- P1 user finding: the national frame needed an explicit one-China presentation and a visible South China Sea islands locator.
- Preserved Taiwan, Hong Kong and Macao inside the same validated national map collection as non-simulation territory context; they remain visually present without being counted among the 31 province simulation subjects.
- Added a restrained `南海诸岛` locator derived from the repository's frozen Ministry of Natural Resources `GS(2016)1609` standard-map snapshot. The asset is local, presentation-only and does not introduce invented coordinates or runtime map requests.
- `qa/china-complete-with-south-china-sea.png` verifies Taiwan and the South China Sea locator remain visible in the stable causal-stage frame without obscuring the main national silhouette or `1 / 31 / 10` identity typography.
- Strict TypeScript, 6 unit tests, production/Sites builds and all 7 browser tests pass. The browser contract now explicitly asserts the South China Sea image and caption.

### Follow-up polish

- P3: profile sustained 4K playback on the exact competition laptop; the independent test suite validates layout and production behavior but not hardware-specific frame time.

final result: passed

---

## Map-to-road-to-cabin continuity — 2026-08-13

- Source visual truths: `public/assets/policy-road/high-pylon-policy-signal.png` and `public/assets/policy-road/high-pylon-from-nev-interior.png`.
- Implementation terminal capture: `qa/map-road-cabin-06-cabin-final.png`.
- Six-frame motion evidence: `qa/map-road-cabin-storyboard.jpg`.
- Map/screen overlap evidence: `qa/map-road-bridge-mid.png`.
- Normalized cabin source: `qa/vehicle-interior-source-normalized-1440x1024.png`.
- Side-by-side terminal comparison: `qa/vehicle-interior-source-vs-implementation.png`.
- Viewport and density: 1440 × 1024 CSS pixels at 1×. Source 1536 × 1024 center-cropped to 1440 × 1024; implementation 1440 × 1024 pixels.
- State: reversible `causal-handoff → policy-signal → vehicle-interior` sequence.

### Required fidelity surfaces

- Fonts and typography: causal-stage text and `1 / 31 / 10` exit before physical screen structure becomes legible. The exterior statement also exits before the cabin foreground arrives, so no presentation copy floats inside the vehicle.
- Spacing and layout rhythm: the live national map remains dominant at the handoff; the screen edge, support, high mast and road become readable in that order. The cabin then enters only from the outer and lower edges while the windshield keeps the exterior sightline open.
- Colors and tokens: both assets retain the same near-black world, restrained cyan geography and sparse wet-road reflection. No new dashboard color, ambient strip, gradient or action control appears.
- Image quality and asset fidelity: the exterior and cabin frames are local 1536 × 1024 production assets. The terminal implementation is pixel-aligned with the normalized source; no CSS-drawn vehicle, placeholder or remote asset is used.
- Copy and content: the screen continues to show the complete national context and South China Sea inset. No real amount, probability, vehicle logo, enterprise promise or commercial offer appears.

### Comparison history

- Pass 1 — blocked by user review: the complete road image took over too early, reading as a hard slide change.
- Fix: initialize the exterior image at `3.05×` with a tight screen-face crop, overlap it with the live national map, expand the crop over a 6.4-unit quintic pullback, and delay the live globe fade until the overlap is established.
- Pass 2 — passed: `qa/map-road-bridge-mid.png` visibly contains the live map as the dominant layer while the physical signal-screen face appears beneath it; there is no full-frame page swap.
- Pass 3 — passed: the exterior continues to `0.84×` while the cabin composite enters at `1.34×` and settles to `1×`. The same pylon and road stay aligned through the windshield.

### Browser verification

- Forward wheel input reaches `vehicle-interior`; eight reverse events return to `causal-handoff`, proving the complete continuation is reversible.
- 1280 × 720, 1920 × 1080 and 3840 × 2160 all keep `scrollY = 0`, one WebGL Canvas, full-viewport vehicle imagery and no horizontal overflow.
- Rapid wheel-driven keyframe capture produced no black compositor frame, missing image, geometry reset or console error.

### Findings

- P0/P1/P2: none.
- P3: the cross-media handoff is deliberately cinematic rather than physically simulated 3D parallax; the current vertical slice prioritizes stable reversible playback on the competition machine.

final result: passed

---

## 13110 Roadshow / “同一个圆”到地球的连续揭示

> QA date: 2026-08-13
> Scope: funding-pool edge → ratio ring → concentric ripple → atmospheric rim → live WebGL Earth
> Source grounding: `references/funding-pool-concept.png` and `public/assets/cockpit/nev-cockpit-selected.png`
> Final result: **passed**

### Evidence

| State | Evidence |
|---|---|
| Five-state continuity storyboard | `qa/one-circle-earth-storyboard.jpg` |
| Funding pool | `qa/circle-01-pool.png` |
| Ratio ring | `qa/circle-02-ratio.png` |
| Policy ripple | `qa/circle-03-ripple.png` |
| Atmospheric rim | `qa/circle-04-atmosphere.png` |
| Live Earth reveal | `qa/circle-05-earth-reveal.png` |
| Funding reference comparison | `qa/funding-source-comparison.jpg` |
| Earth reference comparison | `qa/circle-earth-reference-comparison.jpg` |

### Final review

- One persistent `.circle-bridge` now owns the visible edge across the funding, ratio, ripple and atmospheric states. The individual content containers draw no competing circle borders.
- At the funding state, the shared edge is `140.28px` and aligned to the `100份` pool. It moves and grows to `216.72px` around `85/15` without disappearing, making the pool edge literally become the ratio ring.
- The ripple state keeps the shared core edge at `187.43px` and emits two reversible concentric rings. Browser inspection records outer scale `1.5446` / opacity `0.3192` and far scale `1.8034` / opacity `0.1224`.
- The same edge then recenters and expands to `260.20px`; its border becomes atmospheric cyan and its shadow reaches `13.55px` while the WebGL globe begins behind it.
- At the next scroll state the shared edge opacity reaches `0` while the globe reaches `0.9929`, revealing the local live Earth precisely where the atmospheric rim was. No page, image or duplicate globe replaces the circle.
- Forward scrolling reaches `causal-handoff`; reverse scrolling restores `cockpit`, bridge opacity `0`, globe opacity `0`, one persistent Canvas, zero native page displacement, no horizontal overflow and zero browser errors/warnings.
- `npm test` (7 tests), TypeScript strict, boundary scan, production build, Sites artifact preparation and Sites worker tests pass.

### Findings

- P0/P1/P2/P3: none.

final result: passed

---

## 13110 Roadshow / 长滚动节奏与三档比例滑块

> QA date: 2026-08-13
> Scope: longer wheel travel and synchronized `85/15 → 90/10 → 95/5` narrative slider
> Final result: **passed**

### Evidence

| State | Evidence |
|---|---|
| Three-state slider storyboard | `qa/ratio-slider-storyboard.jpg` |
| East preset / initial thumb | `qa/slider-85-15.png` |
| Central preset / midpoint thumb | `qa/slider-90-10.png` |
| West preset / terminal thumb | `qa/slider-95-5.png` |

### Final review

- Wheel normalization changed from `1800px` with a `0.14` event cap to `4200px` with a `0.065` cap. A 420px test wheel impulse now needs 16 meaningful steps to traverse the master sequence instead of roughly eight, giving each animation beat more physical travel and finer scrubbing control.
- The ratio page keeps all three regional presets visible while one large value, rail fill, thumb and active row change together.
- Inspected midpoint state shows only `90/10` visible at opacity `0.9985`, the fill at `0.4648`, and the thumb at the middle position. The terminal state shows only `95/5` at opacity `1`, fill `0.9996`, and the thumb at the final marker.
- The slider is driven by the same paused GSAP master timeline and reverses exactly with upward scroll. It is not a form input and does not alter simulation data.
- Full-browser verification used 18 forward and 18 reverse 420px impulses: the forward path reaches `causal-handoff`, the reverse path restores `cockpit`, one Canvas remains mounted, native `scrollY` stays `0`, horizontal overflow is absent, and browser errors/warnings are zero.
- `npm test` (7 tests), TypeScript strict, boundary scan, production build, Sites artifact preparation and Sites worker tests pass.

### Findings

- P0/P1/P2/P3: none.

final result: passed

---

## 13110 Roadshow / 分段车舱推进与固定屏幕叙事

> QA date: 2026-08-13
> Scope: cockpit-only illumination → synchronized screen illumination and stopped approach → fixed-camera explainer → final Earth flight
> Selected source: `public/assets/cockpit/nev-cockpit-selected.png` plus the user-approved staged motion specification
> Final result: **passed**

### Evidence

| State | Evidence |
|---|---|
| Source / implementation comparison | `qa/staged-reference-comparison.jpg` |
| Six-beat staged-motion storyboard | `qa/staged-cockpit-storyboard.jpg` |
| Dark start | `qa/staged-00-dark.png` |
| Cockpit half-illumination, screen black | `qa/staged-01-cabin-half.png` |
| Synchronized remaining light + first approach | `qa/staged-02-screen-and-approach.png` |
| Fixed-camera funding page | `qa/staged-03-funding-fixed.png` |
| Fixed-camera ratio page | `qa/staged-04-ratio-fixed.png` |
| Fixed-camera ripple question | `qa/staged-05-ripple-fixed.png` |
| Approved final Earth flight | `qa/staged-06-final-flight.png` |
| Full Earth after cockpit exit | `qa/staged-07-earth.png` |

### Final review

- The first wheel interval changes only cabin exposure: the cockpit reaches half illumination while the display remains completely black and the camera remains at `1×`.
- The next interval starts the display and remaining cabin illumination together. The cockpit uses the same quintic nonlinear ease to approach `1.48×`; the framing still visibly includes the wheel, seats, dash and center console, so it has not exited the cabin.
- After the approach settles, funding, ratio and ripple captures all report the exact same `matrix(1.48, 0, 0, 1.48, 0, 0)` cockpit transform. Page transformations therefore occur at a fixed camera position rather than continuing an accidental zoom.
- The final flight begins only after the ripple question. Its inspected midpoint reports `2.1754×`, proving a separate second dolly from the held `1.48×` frame toward the original `3.234×` cockpit-exit endpoint.
- The WebGL Earth begins at the matching `0.4576×` aperture scale and reaches `1×` with the cockpit, keeping one centered spatial move and the same persistent Canvas.
- Full forward scrolling reaches `causal-handoff`; reverse scrolling restores `cockpit`, cockpit scale `1×`, globe opacity `0`, one Canvas, zero native page displacement, zero overflow and zero browser errors/warnings.
- `npm test` (7 tests), TypeScript strict, boundary scan, production build, Sites artifact preparation and Sites worker tests pass.

### Findings

- P0/P1/P2/P3: none.

final result: passed

---

## 13110 Roadshow / 国补科普“同一个圆”滚动叙事

> QA date: 2026-08-13
> Scope: `apps/roadshow` dark cockpit → consumer subsidy → shared funding → ratio ring → policy ripple → retained Earth
> Selected visual target: approved “同一个圆” direction, grounded by `references/funding-pool-concept.png`
> Final result: **passed**

### Evidence

| State | Evidence |
|---|---|
| Selected funding-pool reference | `references/funding-pool-concept.png` |
| Required source / implementation comparison | `qa/funding-source-comparison.jpg` |
| Six-beat continuous storyboard | `qa/subsidy-one-circle-storyboard.jpg` |
| Dark cockpit | `qa/subsidy-00-dark.png` |
| Familiar consumer subsidy | `qa/subsidy-01-shopping.png` |
| Central + local → 100-share pool | `qa/subsidy-02-funding-pool.png` |
| Three-tier ratio ring | `qa/subsidy-03-ratio.png` |
| Ignition question / ripple | `qa/subsidy-04-ripple.png` |
| Circle-to-Earth handoff | `qa/subsidy-05-earth-handoff.png` |
| Retained Earth stage | `qa/subsidy-06-earth.png` |

### Final review

- The center display begins fully black. No content autoplays; every state is owned by the same smoothed wheel progress and reverses on upward scroll.
- The first readable beat uses a generic notebook purchase surface with `国家补贴 20%`, avoiding JD branding, copied marketplace chrome, or an automaker logo.
- The subsidy label does not turn into a monetary claim. `中央承担 85份 + 地方承担 15份 → 消费补贴资金 100份` communicates a ratio example without presenting real fiscal amounts.
- The pool remains the sole circular subject and becomes the policy ratio ring. West `95/5`, central `90/10`, and east `85/15` appear as three independent presets and are never normalized or summed together.
- The ignition beat changes `85/15` to `90/10` and reveals only four propagation domains—财政空间、地方政策、企业行动、产业布局—without pretending to show a simulated result.
- The ring then hands off to the existing live WebGL Earth inside the same physical center-display aperture. The cockpit layer and the single persistent Canvas share the subsequent dolly; there is no route change, duplicate globe, video, or page-like transition.
- The implementation comparison keeps the selected reference's near-black cockpit, cyan fiscal semantics, two-source composition, circular pool and sparse Apple-like hierarchy. The production display is intentionally smaller than the generated concept because it respects the exact transparent aperture of the selected cockpit asset.
- Browser verification at 1280×720 completes `cockpit → consumer → funding → ratio → ripple → orbital → China → causal-handoff`, returns cleanly to `cockpit`, keeps `scrollY=0`, reports no horizontal overflow, one Canvas throughout, and no console errors or warnings.
- `npm test` (7 tests), TypeScript strict, boundary scan, production build, Sites artifact preparation, and Sites worker tests pass.

### Findings

- P0/P1/P2: none.
- P3: at distant stage viewing, the supporting microcopy is intentionally secondary; the large ratios, 20%, 100份 and ignition question carry the spoken narrative.

final result: passed

---

## 13110 Roadshow / NEV Cockpit One-Shot Prelude

> QA date: 2026-08-13
> Scope: `apps/roadshow` wheel-driven dark cockpit → black display → display illumination → center-display dolly → live Earth → China focus
> Selected visual target: ideation option 1
> Final result: **passed**

### Evidence

| State | Evidence |
|---|---|
| Selected source visual | `public/assets/cockpit/nev-cockpit-selected.png` |
| Source / implementation comparison | `qa/scroll-reference-comparison.jpg` |
| Six-beat wheel-driven storyboard | `qa/scroll-driven-storyboard.jpg` |
| Dark cockpit / black display | `qa/scroll-00-dark-cockpit.png` |
| Cabin revealed, display still black | `qa/scroll-01-cabin-reveal.png` |
| Display-on threshold | `qa/scroll-02-screen-on.png` |
| Center-display dolly | `qa/scroll-03-dolly.png` |
| Live-Earth stage | `qa/scroll-04-earth-stage.png` |
| China-focus terminal stage | `qa/scroll-05-end-stage.png` |
| Reverse-scroll return | `qa/scroll-06-reversed-start.png` |

### Final review

- The first rendered frame is a nearly black cockpit with the center display fully black; loading copy remains screen-reader-only and creates no visible pre-roll flash.
- The cockpit is a local, attribution-recorded image asset with no vehicle logo. Its center display is a transparent 16:9 aperture, not a second screenshot or video surface.
- The same persistent React Three Fiber Canvas is visible inside the display, scales with the camera move, and takes over the viewport without a route change, page swap, or cross-faded duplicate Earth.
- Nothing autoplays. One smoothed master progress value owns cockpit reveal, display ignition, dolly, Earth and China focus; upward wheel input reverses the same frames instead of restarting or crossfading.
- Cabin illumination and the dolly use Apple-like nonlinear motion: restrained initial response, a decisive middle move, and a long soft settle at each scroll target.
- The settled first Earth scene contains no `13110` wordmark, slogan, hero copy, or CTA block. Only the restrained chapter rail remains.
- The selected source and implementation were compared together at the same 16:9 state. Cockpit geometry, display position, black level, and center-screen subject alignment remain faithful; the implementation intentionally begins with a slightly smaller live Earth so the dolly has visible spatial travel.
- Browser verification at 1280×720 reports a 1280×720 CSS Canvas backed by a 1920×1080 renderer, no horizontal overflow, no data error state, a stable causal-handoff endpoint, and a clean reverse-scroll return to `cockpit` with Canvas opacity `0`.
- `npm test` (7 tests), TypeScript strict, boundary scan, production build, Sites artifact preparation, and Sites worker tests all pass.

### Findings

- P0/P1/P2: none.
- P3: the photographic cockpit asset is authored at 16:9 and intentionally optimized for the roadshow stage ratio; non-16:9 windows remain functional but are not the cinematic master framing.

final result: passed

---

## Historical vertical-slice QA

- Source visual truth: `references/orbital-precision.png`
- Implementation orbital capture: `qa/implementation-1440x1024-orbital-final.png`
- Transition storyboard: `qa/continuous-transition-storyboard.png`
- Wheel stability sequence: `qa/wheel-stability-final.png`
- Scroll compositor before/after: `qa/wheel-flash-before-after.png`
- Implementation lift midpoint: `qa/motion-china-lift-mid-final.png`
- Implementation unfolded terminal frame: `qa/motion-china-unfolded-final.png`
- Combined comparison: `qa/source-vs-implementation-final.png`
- Viewport: 1440 × 1024 CSS pixels, deviceScaleFactor 1.
- Source normalization: generated source 1487 × 1058 normalized to 1440 × 1024.
- Implementation pixels: 1440 × 1024.
- State: Scene 00 settled orbital frame, continuous lift midpoint, and Scene 01 unfolded terminal frame.

## Full-view comparison evidence

The combined comparison confirms the selected composition is retained: black full-bleed stage, left-aligned restrained brand, monumental two-line 600-weight headline, one blue pill action, and a dominant globe cropped on the right. The implementation intentionally uses the verified 34-feature geography and a locally rendered NASA Blue Marble texture instead of reproducing the generated mock's invented terrain.

## Focused evidence

- Typography: system/Inter-style sans, 600 display weight, tight tracking and two-line wrap match the source hierarchy. The punctuation and exact approved Chinese copy are preserved.
- Spacing: copy remains in the left third; the globe occupies about 70% of the stage and is cropped at top/right; the chapter line anchors the lower-left edge.
- Colors: true-black canvas, white ink, PolicyScope teal geography, warm Beijing pulse and one action-blue control follow the selected direction.
- Image quality: the globe uses a local 4096 × 2048 NASA texture, antialiased WebGL geometry, DPR control and source-derived vector boundaries. No placeholder, CSS-drawn globe or remote image remains.
- Copy: `PolicyScope / 政策涟漪`, `让政策影响，被看见。`, and `进入推演` match the frozen content.
- Interaction: CTA and scroll both drive one GSAP-controlled spatial shot. The 31-province texture begins on the sphere, lifts toward the camera, then unfolds while the same WebGL globe remains behind it. Keyboard focus and reduced-motion behavior are implemented.

## Comparison history

### Pass 1 — blocked

- P1: GeoJSON ring orientation caused the global exterior to receive the teal fill.
- P1: the original WebGL flat-map handoff exposed an opaque rectangular texture plane.
- Fixes: normalize every polygon ring to the smaller spherical area; replace the transparent WebGL plane with a D3-generated SVG layer from the same frozen GeoJSON.

### Pass 2 — passed

- Historical post-fix evidence showed the 31-province China overlay and a clean planar terminal state with no rectangular artifact; Pass 3 later superseded that separate handoff.
- No actionable P0/P1/P2 fidelity findings remain for this vertical-slice scope.

### Pass 3 — blocked after user review

- P1: the transition completed too quickly to read as a premium product-film camera move.
- P1: a separately entering flat SVG and chapter headline made Scene 01 feel like a new presentation slide.
- Fixes: extend CTA travel to roughly 5.4 seconds; remove the separate SVG and visible Scene 01 title; replace the handoff with a shader-driven spherical-to-planar China mesh inside the existing Canvas; retain the globe as spatial context behind the unfolded national map.

### Pass 4 — passed

- `qa/continuous-transition-storyboard.png` shows the same subject across the settled globe, visible lift midpoint and unfolded terminal frame.
- The browser contains exactly one WebGL canvas throughout the transition and no `.flat-china-map` handoff node.
- No actionable P0/P1/P2 motion-continuity findings remain.

### Pass 5 — blocked after user review

- P1: active wheel/trackpad scrubbing intermittently exposed a large black compositor invalidation rectangle over the WebGL scene.
- Root cause: a sticky GPU canvas was being recomposited during document scroll while Lenis-smoothed input also triggered repeated manual GSAP timeline seeking.
- Fixes: make the WebGL stage viewport-fixed; bind the transition with native `ScrollTrigger` `scrub: true`; keep Lenis as the sole scroll-position smoother; remove per-update `tweenTo`/manual timeline chasing; prevent redundant semantic-stage store updates; keep the opaque globe material out of transparent sorting.

### Pass 6 — passed

- `qa/wheel-flash-before-after.png` visibly records the black invalidation frame before the fix and the intact frame at the same transition region afterward.
- `qa/wheel-stability-final.png` captures four consecutive real in-app wheel-input frames with one persistent Canvas and no black rectangle, page flash or geometry reset.
- No actionable P0/P1/P2 scrolling or compositor findings remain.

## Browser verification

- Primary CTA, deliberately paced transition, real wheel scrubbing, continuous single-canvas handoff, refresh replay, local-only requests and console state checked.
- Playwright viewports passed: 1280 × 720, 1920 × 1080, 2560 × 1440 and 3840 × 2160.
- Browser console errors: none in the final in-app-browser run and E2E assertion.

## Follow-up polish

- P3: add a subtler cloud/specular layer if a future iteration needs to approach the generated mock's atmospheric product-render finish.
- P3: profile sustained 4K frame time on the actual competition laptop; current 4K E2E validates layout and operation, not a hardware-specific FPS guarantee.

final result: passed

---

## High-pylon policy-signal vertical slice — 2026-08-13

- Source visual truth: `public/assets/policy-road/high-pylon-policy-signal.png`
- User structural reference: `/Users/carrey/Downloads/images.jpeg`
- Implementation screenshot: `qa/high-pylon-policy-signal-final-1440x1024.png`
- Normalized source: `qa/high-pylon-source-normalized-1440x1024.png`
- Side-by-side comparison: `qa/high-pylon-source-vs-implementation.png`
- Viewport and density: 1440 × 1024 CSS pixels at 1×; source 1536 × 1024 center-cropped to 1440 × 1024; implementation 1440 × 1024 pixels.
- State: terminal `policy-signal` frame after the reversible China-map pullback.

### Full-view and focused comparison

- Fonts and typography: one deliberate 600-weight two-line narrative statement sits in the lower-right road negative space. Its restrained 13px teal eyebrow and tight display tracking continue the established 13110 language.
- Spacing and layout rhythm: screen, single central mast, large air gap and curved road match the selected frame. The overlay does not obscure the mast, map, South China Sea inset or vanishing line.
- Colors and tokens: true black, near-black structure, white ink and `--teal` policy semantics remain consistent. No action blue, decorative gradient, glass surface or advertising color enters the frame.
- Image quality and asset fidelity: the selected 1536 × 1024 target is used as a local production asset with cover cropping only. There is no CSS-drawn billboard, placeholder, remote image or second Canvas.
- Copy and content: `31 个省级决策主体` and `同一项中央政策，正在发出不同信号。` avoid real amounts, enterprise claims, probabilities and commercial offers.

### Comparison history

- Pass 1 — blocked: the inherited chapter rail remained visible over the highway and read as presentation chrome rather than part of the physical reveal.
- Fix: the policy timeline now fades the chapter rail with the national-map identity labels before the screen structure emerges.
- Pass 2 — passed: the recaptured terminal frame has no collision or extra presentation chrome. Source and implementation were combined in one side-by-side image.

### Browser verification

- 24 forward wheel events reach the stable high-pylon terminal frame; six reverse events return to `china-focus`; subsequent forward input restores the terminal frame.
- The document remains viewport-locked at `scrollY = 0`, one WebGL Canvas remains mounted, and the policy image reaches `matrix(1, 0, 0, 1, 0, 0)`.
- 1280 × 720, 1920 × 1080 and 3840 × 2160 show no horizontal overflow or copy clipping.
- Browser console errors: none.

### Findings

- P0/P1/P2: none.
- P3: a future native 3D road environment could add parallax beyond this approved vertical slice.

final result: passed
# 2026-08-14 — Province label and Earth rim correction

- Province billboard close frame and cabin return frame now use the exact caption `本次实验同伴网络`; the prior `同侪网络` glyph is no longer present in either production asset.
- The WebGL atmosphere shader now uses `#63d5c7`, matching the 2D China map policy teal instead of the former blue rim.
- Visual evidence: `qa/province-companion-network-corrected.png` and `qa/teal-earth-rim-final.png`.
- `npm run verify`: passed (7 Vitest tests, production build/boundary checks, 4 Sites packaging tests).
- Existing Playwright suite was also run: its current assertions still target the pre-`earth-return` terminal composition and therefore report stale visibility/bounds failures; the wheel/no-remount regression test passed. The captured terminal screenshot confirms the corrected teal rim.

final result: passed
# 2026-08-14 — Four-arrow timeline control

- `ArrowRight` / `ArrowDown` advance and `ArrowLeft` / `ArrowUp` rewind the existing continuous GSAP virtual timeline.
- Key input preserves wheel-style smoothing, the viewport lock and the single persistent WebGL Canvas; it does not jump between chapters.
- Added unit coverage for all four key mappings and a focused browser journey covering right → left → down → up reversal.
- Verification: 8 Vitest tests passed; focused Playwright keyboard E2E passed; production build, boundary checks and 4 Sites packaging tests passed.

final result: passed
# 2026-08-14 — In-app browser keyboard focus

- The `.roadshow` stage now takes keyboard focus as soon as validated content is ready and recaptures it on pointer-down.
- This prevents the Codex browser panel chrome from retaining arrow-key focus while preserving a visually invisible focus treatment.
- Verified directly in the Codex in-app browser: active element was `.roadshow`; one `ArrowRight` advanced `cockpit → consumer`.
- Verification: 8 Vitest tests passed; focused four-arrow Playwright E2E passed.

final result: passed
# 2026-08-14 — Cross-platform offline roadshow package

- Added a universal macOS package (Apple Silicon + Intel) with a native local server and a Windows x64 package using the built-in PowerShell runtime.
- Both packages contain the complete production site, local maps, Blue Marble texture, policy-road imagery, double-click launcher and Chinese operator guide.
- No Node, npm, Python, repository checkout, business API or internet connection is required on the presentation computer.
- Verified the packaged macOS binary is universal; packaged HTML, JavaScript, GeoJSON and WebP assets returned HTTP 200 with correct MIME types; both archives passed SHA-256 verification.

final result: passed
# 2026-08-14 — Precision keyboard step in the first half

- Direction-key events now advance or rewind by `0.05` while the target progress is below the story midpoint (`1.56`), then use `0.1` for the second half.
- The change applies symmetrically to right/down and left/up while preserving the existing GSAP smoothing.
- Verification: 8 Vitest tests passed; focused reversible four-arrow Playwright E2E passed; production build and both offline packages were regenerated successfully.

final result: passed
