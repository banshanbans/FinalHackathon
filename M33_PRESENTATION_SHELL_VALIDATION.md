# M33.3 独立大屏壳层验收

日期：2026-08-13  
结果：Passed

## 1. 实现范围

- `apps/presentation` 已从技术验证页切换为正式 `/experiments/:id/present` 全景推演厅。
- 首屏支持从真实 API 创建并完成一个 V3.2 同源 A/B 演示实验；默认演示包含低强度“国际冲突情景下油价上涨”共享事件。
- 页面只消费 `presentation-timeline-v1` 和 `presentation-frame-v1`；省域值、六指标、事件、覆盖层与哈希均来自 M33.2 只读投影。
- 保留约 4.5 秒深空地球旋转、拉近中国和全国地图交接；支持跳过、重播和低动效。
- 正式壳层包含顶部 HUD、三模式切换、左侧叙事浮层、单指标卡、右侧十入口工具坞、Context Popover、Side Sheet、图例和底部 Timeline Rail。
- 时间轴支持拖动吸附、节点跳转、事件节点、播放/暂停、前后帧、0.5×/1×/1.5×/2×与复位；拖动只切换合法冻结帧。
- 省域点击、事件、竞争、谈判、协同、车企、结果、方法与图层面板保持同一帧上下文；方法与 Evidence 信息不占据主地图。

## 2. 技术与真实性边界

- React 19 + TypeScript strict + TanStack Query + MapLibre 6 + deck.gl 9 + Phosphor Icons。
- 地图、字体、图标、GeoJSON 和 WebGL Worker 全部本地打包；无 CDN、远程瓦片、iframe 或截图地图。
- 运行时省域填色绑定 31 个 `province_values`；关系弧线只由 `overlay_records` 中合法省份端点生成。
- 突发事件标记为 `scenario_assumption`，演示文案不把战争或油价情景写成现实预测。
- UI 不重算 World、Gap、HHI、机制贡献或主体行动；结果面板直接显示后端冻结指标。

## 3. 验证

```text
npm run typecheck  Passed
npm run build      Passed
pytest M33 API / contract  9 passed
```

浏览器交互验证：

- 启动演示实验后进入不透明实验深链。
- 事件面板显示事件强度、双方案范围和机制通道；时间轴插入事件帧。
- 时间轴拖动从第 1 帧吸附至第 7 帧，叙事标题同步为“车企报价与反报价”。
- 播放/暂停、节点跳转和结果对照模式通过。
- 结果 Side Sheet 展示六项权威指标与 Delta。
- 点击地图命中山西并打开省域 Context Popover。
- 1366×768 页面尺寸与滚动尺寸均为 1366×768，无水平或垂直溢出。
- 浏览器 console：error 0，warning 0。

视觉证据：

- `outputs/m33-globe-intro/m33-shell-event-1280x720-v2.jpg`
- `outputs/m33-globe-intro/m33-shell-1366x768.jpg`
- `outputs/m33-globe-intro/m33-shell-reference-comparison-2560x720.jpg`
- 完整 Design QA 见 `design-qa.md` 的 “M33.3 Full Presentation Shell Design QA”。

## 4. 后续边界

M33.4 继续完成五项事件目录操作、三触发边界、七轮运行期 SSE 恢复和正式单屏 E2E。M33.5/M33.6 继续负责键盘遥控、同步 A/B、路演五幕、WebGL 运行时降级及 1080p/2K/4K 长时间可靠性冻结；这些后续项没有被本次 M33.3 验收提前标记为完成。
