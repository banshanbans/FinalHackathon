# M33.1 地图与动画技术验证

> 日期：2026-08-13  
> 结论：通过；M33.2 演示投影 API 可以开始。

## 1. 验证范围

本阶段只验证全景推演厅的地图与动画技术门禁，不接入运行时实验，也不重算任何权威业务结果。验证件位于 `apps/presentation`，冻结帧和突发事件均为明确标注的展示数据。

## 2. 实现结果

- 本地 MapLibre GL JS 6.3.0 渲染全国版图，其中 31 省参与填色、选择态和镜头定位，香港、澳门、台湾作为不参与计算的版图上下文展示。
- deck.gl 9.3.10 使用非交错 `MapboxOverlay` 绘制竞争/协同弧线；本地 worker 随 Vite 构建打包，无远程瓦片、CDN 或 iframe。
- 24 个冻结业务帧支持播放、暂停、连续拖动、节点吸附、事件节点和复位；帧间只改变展示值。
- “国际冲突情景下油价上涨”作为机制实验情景，固定显示非现实预测声明。
- WebGL 与 SVG 容错渲染共享同一帧、选择、时间轴和面板状态。
- 低动效模式可关闭路径动画和镜头飞行。

## 3. 几何谱系

| 项目 | 结果 |
|---|---|
| 冻结分析几何 SHA-256 | `2f6aea81b85e929df44aa83beb6c4dcf3fe8f14b8274506e62c6b836ac1c97d6` |
| WebGL 展示 GeoJSON SHA-256 | `8ec7a72376f5f483b46a2a5ccbe65af29e34e46afb21942e3878309e664cff82` |
| SVG 容错文件 SHA-256 | `9d56f8985027eb9c3e48fc7128b62c1f1c98569e30dbadaf4381756519ce8087` |
| 省域绑定 | 31/31 计算省域 + 港澳台 3/3 版图上下文，全部绑定同一冻结标准地图源 |
| 曲线处理 | 每段三次贝塞尔曲线固定采样 24 次，构建结果确定性一致 |
| 坐标边界 | 展示用 Web Mercator 合法范围且不越过声明 bbox |
| 使用边界 | 仅渲染；禁止用于距离、面积或现实空间分析 |

## 4. 浏览器与性能验证

验证环境为 Codex 内置 Chromium、WebGL 2.0；每次从本地开发服务器加载并连续播放到事件后帧。

| 画布 | 渲染器 | 结果 | 实时 FPS | P95 帧耗时 |
|---|---|---|---:|---:|
| 1920×1080 | MapLibre + deck.gl | 通过 | 60 | 17.6 ms |
| 3840×2160 | MapLibre + deck.gl | 通过 | 60 | 17.6 ms |
| 1920×1080 | SVG 容错 | 通过 | 不适用 | 不适用 |

额外检查：Delta 填色过渡可见、事件点与弧线可见、全国版图无缺失、港澳台不接受业务点击且不进入图例数值、时间轴播放/暂停与节点切换有效、低动效开关有效、SVG 模式保持业务控件可用。

## 5. 自动检查

```text
python scripts/validate_analysis_map.py        PASS
python scripts/validate_presentation_map.py    PASS
ruff check                                     PASS
npm run build                                  PASS
npm audit --audit-level=high                   0 vulnerabilities
```

Vite 生产构建仍提示主 JS chunk 大于 500 kB；这是 M33.3 接入运行时前必须处理的性能工程项，不阻塞本次地图能力门禁。

## 6. 退出结论

M33.1 的本地校验几何、31 省计算绑定、港澳台版图上下文、Delta、弧线、镜头、4K 帧率、低动效和 SVG 降级均已通过。下一阶段只进入 M33.2：实现 `presentation-timeline-v1` 与 `presentation-frame-v1` 只读投影 API；当前技术验证件不视为正式运行时页面。

## 7. 2026-08-13 轮廓校准补充验收

- 用户复核发现 WebGL 省域轮廓与冻结 SVG 存在可见比例偏差。根因是 v1 使用固定 `76–134` 经度跨度，未严格匹配源路径在 Web Mercator 下的宽高比，并且三次贝塞尔曲线仅采样 8 段。
- v2 按冻结 SVG 路径宽高比与 `18–54` 纬度 Mercator 高度反算经度跨度，消除约 3.75% 横向拉伸；曲线采样从 8 段提高为 24 段。
- 校验器新增源路径与 Web Mercator 宽高比等价断言，并拒绝低于 24 段的曲线资产；31 省代码、逐省路径哈希、源 SVG 与根几何哈希保持不变。
- 地球开场的光点由中国几何中心改为北京真实经纬度 `116.4074, 39.9042`；全国接管镜头仍以中国中心构图，不改变业务帧。
- 修正后地图生成校验、TypeScript strict 和生产构建通过，浏览器 console error/warning 均为 0。证据：`outputs/m33-globe-intro/beijing-focus-corrected-1280x720.jpg`、`outputs/m33-globe-intro/svg-aspect-corrected-1280x720.jpg`。

## 7. M33.3 开场镜头先行验证

用户于 2026-08-13 授权该独立壳层子项先行。实现使用本地 MapLibre globe、`world-atlas@2.0.2` 的 Natural Earth 公共领域陆地数据和已冻结的 31 省展示几何：开场约 4.5 秒完成地球旋转、拉近中国、31 省高亮和全国地图淡入接管。

- 1920×1080 和 1366×768 构图、文案、进度与跳过操作无裁切。
- 3840×2160 交接后连续播放实测 60.1 FPS、P95 17.7 ms。
- 自动交接、跳过、重播和 `prefers-reduced-motion` 不超过 1 秒交接均通过浏览器检查。
- 控制台错误 0、警告 0；生产构建和高危依赖审计通过。
- 视觉对照证据：`outputs/m33-globe-intro/source-vs-implementation.png`；完整 Design QA 见 `design-qa.md`。

本节只证明开场镜头子项完成，不改变 M33.2 仍为唯一下一阶段，也不将完整 M33.3 标记为完成。
