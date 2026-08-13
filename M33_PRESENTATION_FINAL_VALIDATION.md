# M33 全景推演厅最终验收

> 日期：2026-08-13  
> 状态：M33.0–M33.6 complete / frozen  
> 正式入口：`/experiments/:id/present`

## 产品退出结果

- 开场光点固定为北京 `[116.4074, 39.9042]`；全国交接镜头继续使用中国构图中心，两者职责分离。
- WebGL GeoJSON 与冻结 SVG 保持相同 Web Mercator 宽高比，贝塞尔曲线采样 24 段，31 省及港澳台版图上下文的源路径哈希可追溯。
- `presentation-event-catalog-v1` 完整暴露五项事件、三触发边界、三档强度、两分支范围和情景免责语。
- 七轮在同一大屏逐轮推进；SSE 通知后重读权威 Timeline/Frame，Last-Event-ID 从上一事件之后严格恢复且不重复。
- Story 读取 `presentation-summary-v1` 五幕；Compare 默认显示权威 Delta，可切换同步 A/B，并显示 Gap、财政代价、受益/承压省份和三条机制链。
- 空格、左右、`Shift+左右`、`Home|R`、`Esc` 遥控，四档变速、全屏和一键复位完整可用。
- 断网保留最后完整帧；WebGL 失效切换本地全国版图 SVG（31 个计算省域 + 港澳台版图上下文）；本地 fake 演练显示 `FAKE / FALLBACK`，不冒充 Luna 缓存。

## 缺陷修复

### 车企全国市场预算量化溢出

事件矩阵首次执行时，四位小数冻结后的 31 省强度和可能比未舍入总预算高出数个万分位，触发 `automaker national market budget exceeded`。修复在初步缩放和最终重配后都执行确定性守恒校正：只消除量化溢出，不改变排名、名额或事件机制。

## 自动化证据

| 检查 | 结果 |
|---|---|
| `make test` | 62 Python/API passed；5 Vitest passed |
| `make lint` | Ruff check/format、ESLint、`apps/web` TypeScript/Vite build passed |
| `make validate-data` | 31 省、10 车企、M29 事实/关系/177 需求、标准地图 passed |
| M33 聚焦测试 | 23 passed：契约、五事件矩阵、SSE 恢复、API |
| Presentation build | TypeScript strict + Vite production build passed |
| Presentation map validation | 31 个计算省域 + 港澳台 3 个版图上下文；SHA-256 `8ec7a72376f5f483b46a2a5ccbe65af29e34e46afb21942e3878309e664cff82` |
| 1280×720 正式 E2E | 1 passed：七轮、事件、SSE、断网、五幕、遥控、Delta/A-B、连续播放、SVG 降级 |
| 分辨率 E2E | 1920×1080、2560×1440、3840×2160：3 passed |
| 禁止文案扫描 | 无现实最优、企业承诺、政府立场、未来现实金额/销量或伪置信度 |

## 视觉证据

- `outputs/m33-globe-intro/beijing-focus-corrected-1280x720.jpg`
- `outputs/m33-globe-intro/svg-aspect-corrected-1280x720.jpg`
- `outputs/m33-resolution/presentation-1080p.png`
- `outputs/m33-resolution/presentation-2k.png`
- `outputs/m33-resolution/presentation-4k.png`

## 非阻塞提示

- Starlette TestClient 报告 `httpx` 过渡期弃用警告，不影响当前 62 项测试结果。
- Presentation 主包包含 MapLibre/deck.gl，Vite 继续给出大 chunk 性能建议；本轮没有为了压制警告修改业务边界或远程资产策略。

final result: passed
