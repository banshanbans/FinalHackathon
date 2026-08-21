# 13110 Roadshow Design System

## Visual thesis

The roadshow behaves like a premium product reveal. The globe is the opening subject, China is the continuous spatial bridge, and `13110` is the product memory. The opening source of truth is `references/orbital-precision.png`; the terminal composition is grounded by the M35 causal stage.

## Tokens

- Canvas: `#000000`; elevated black: `#080b0e`.
- Primary ink: `#f5f5f7`; muted ink: `#86868b`.
- Policy teal: `#63d5c7`; boundary teal: `rgba(126, 231, 219, .64)`.
- The WebGL Earth's atmospheric rim uses the same `#63d5c7` policy teal as the 2D China map; do not reintroduce a separate blue halo.
- Keyboard control is spatial and reversible: right/down advances the continuous shot and left/up rewinds it through the same eased timeline.
- Action blue: `#0071e3`; focus blue: `#2997ff`.
- Display stack: `Inter, SF Pro Display, -apple-system, BlinkMacSystemFont, Noto Sans SC, sans-serif`.
- Display weight: 600; body weight: 400; no 500 weight.
- Display tracking: `-.045em`; body size: 17px with 1.47 line height.

## Composition

- Before Scene 00, begin in a nearly black premium Chinese new-energy-vehicle cockpit with its center display fully black. Mouse-wheel progress first brings the cockpit alone to half illumination. The remaining cockpit light and the first display page then rise together while a nonlinear approach enlarges the cabin to `1.48×` and stops before crossing the display. The camera stays fixed there while the subsidy pages transform. Only after the policy-ripple beat does the approved final dolly enter the live Earth and continue to China. The sequence never autoplays and reverses cleanly when scrolling upward. No vehicle logo or `13110` wordmark appears in this prelude or the first settled Earth frame.
- The center display now explains the core subsidy mechanism before Earth: a generic `国家补贴 20%` consumer moment sheds its shopping context; `中央承担 85份 + 地方承担 15份` forms a `100份` consumer-subsidy pool; that same circle becomes the three-tier ratio instrument, then the policy-ripple question, then Earth's atmosphere. Use no real fiscal amounts, marketplace brand, card feed, or page transition.
- The ratio beat is the one exception to the earlier no-slider rule: a single restrained spatial rail moves through `85/15 → 90/10 → 95/5` while all three regional presets remain visible and the active preset changes in sync. It is a scroll-scrubbed narrative instrument, not an editable dashboard control.
- The pool edge, ratio ring, ripple and atmospheric rim are the same persistent circular edge. It travels from the funding-pool position to the ratio position, generates two concentric ripples, then recenters and expands while its cyan edge gains atmospheric bloom. The WebGL Earth appears precisely behind that rim before the shared edge fades, revealing that the circle was becoming Earth rather than switching pages.
- Every chapter is a full-bleed rectangular viewport. Never place the whole app in a rounded card.
- Scene 00 keeps `13110`, the product descriptor and slogan on the left, with a monumental globe cropped on the right. The globe occupies roughly 70% of the viewport.
- Scene 01 pushes the camera toward China while the same geometry remains attached to the globe; the national projection is resolved only after the close approach.
- The national view always presents one complete China context: 31 simulation provinces plus Taiwan, Hong Kong and Macao as non-simulation territory context, with a restrained South China Sea islands inset derived from the same frozen Ministry of Natural Resources standard-map source.
- Scene 02 reveals `1 / 31 / 10` as large typography, never as dashboard cards.
- Scene 03 holds the national map while the causal-stage question appears, creating a compositional handoff to M35 without a runtime dependency.
- Use negative space as structure. No ornamental grids, glass panels, decorative gradients, dashboard navigation, KPI tiles, or stacked cards.
- Shadow and glow belong only to the geographic subject. Text and controls remain flat.
- The only primary control is a compact blue pill. Active controls scale to `.96`.

## Motion

- GSAP is the single motion director. Lenis supplies scroll input only.
- Camera motion is one continuous physical dolly with a quintic ease-in-out: zero velocity and acceleration at both endpoints, a decisive middle, and a long soft settle. The globe scale stays exactly `1`, the camera never pulls back, and the projection handoff preserves China's apparent size. Wheel position, not elapsed time or a CTA, owns every frame from the black cockpit to the stable causal handoff. Avoid continuous idle spectacle.
- The handoff from sphere to flat China must preserve screen-space position and silhouette continuity. Camera motion is the dominant cue; the map never flies toward the viewer as a detached layer.
- Continued wheel input after Scene 03 reveals the map as a very high roadside provincial policy-signal screen: one wide ultra-thin display, one tall central matte-black column, minimal rear support, large open air beneath, and a curved nighttime expressway. Never use a gantry or low multi-leg billboard.
- The policy-signal move is one reversible quintic pullback. Begin close enough that only the map reads, then reveal screen thickness, mast and road in that order; never cut to a new page.
- This scene may describe simulated policy signals only. It cannot contain real amounts, automaker logos, probabilities, commercial offers or incomplete national territory.
- The road reveal begins with the exterior image cropped to the signal-screen face and spatially overlapped with the live China map. The crop opens while the same image scales back; never fade in the complete road frame at once.
- After the full high-pylon view, continue the pullback into a generic premium new-energy-vehicle interior. Keep the exact pylon, map and road aligned through the windshield while the cabin frame arrives from the outer edges. No logo, instrument UI or new screen content appears.
- Before the cabin returns, the settled high-pylon electronic screen changes in place to the selected option-3 Sichuan `本次实验省级决策画像`. The six-axis decision fingerprint, authorized peer signals, battery-node context and purchase-willingness proxy remain inside a perspective-matched mask of the original LED face; billboard frame, mast, road and sky stay pixel-stable. The screen change uses a long exposure/defocus resolve rather than replacing the full photograph. The exterior narrative stays lower-left.
- The cabin return first feathers in only the A-pillars, dashboard and steering wheel from the outer/lower edges; the full aligned interior resolves only after that spatial frame is established. This prevents a hard page rectangle and shortens the unavoidable exterior-media dissolve. Once the cabin is established, a second quintic approach reaches `1.40×` around the center display while the steering wheel, windshield and road remain visible. The screen introduces `10 家车企模拟主体`, `31 省级市场投入` and `0—3 产能行动目标`. Use no real-company logos, predictions, amounts or commitments.
- The final approved sequence supersedes the two bullets above where they conflict: nationwide road screen → closer oblique national screen → frontal province Agent screen → direct pullback into a cabin that still shows the province screen → `1.72×` enterprise center-display approach with the exterior darkened. Do not restore a large nationwide-map image after the province Agent state.
- After the enterprise super-screen, the center display becomes a circular portal back to the original live Earth. The enterprise interface contracts and fades; a restrained cyan rim expands from the screen while the cabin peels away radially. The same persistent WebGL Canvas returns underneath, with China remorphing from the flat national footprint onto the globe surface. The endpoint is the original Earth composition with the complete China layer visibly attached—not a screenshot, second Canvas or route change.

## Responsive rule

- Preserve the globe as the dominant object at every supported desktop size.
- At 1280×720, reduce headline size before reducing the globe.
- At 4K, lock content geometry to a 1920px design coordinate system and use margin expansion rather than oversized type.

## Public copy

- Brand: `13110`.
- Descriptor: `新能源汽车产业协同推演`.
- Slogan: `让政策影响，被看见。`.
- Identity: `1 中央政策研判 / 31 省份模拟主体 / 10 车企模拟主体`.
- CTA: `进入年度推演`.
- Public UI must not display `PolicyScope`.
