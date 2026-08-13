# PolicyScope Presentation Hall

`apps/presentation` 是独立全景推演厅模块。M33.1 地图与动画、M33.2 只读投影 API 和 M33.3 正式大屏壳层均已通过；当前页面使用 GovSim Glass UI Kit，并由权威 Presentation Timeline/Frame 驱动。

实施边界：

- 正式入口：`/experiments/:id/present`。
- 旧 `apps/web` 在本模块验收前保持可用。
- 运行时只能消费后端 Presentation 投影和现有严格 DTO，不重算权威环境指标。
- 地图目标技术为本地 MapLibre/deck.gl，并保留 ECharts/SVG 兼容渲染。
- 全国地图展示完整保留香港、澳门和台湾轮廓；三地只作为版图上下文，当前推演、指标和交互范围仍为内地 31 省级行政区。
- 完整产品与交互契约见仓库根目录 `PRESENTATION_HALL_SPEC.md`。
- M33.2 接口：`GET /api/experiments/{id}/presentation/timeline` 与 `GET /api/experiments/{id}/presentation/frames/{frame_id}`。
- 没有实验 ID 时，入口页可通过真实 API 创建并运行带低强度油价上涨情景的演示实验；事件只代表机制实验假设。

## 本地运行

```bash
cd apps/presentation
npm install
npm run dev
```

- 同时运行根目录 `make dev-api`，Vite 会将 `/api` 代理到 `127.0.0.1:8000`。
- 正式深链为 `/experiments/:id/present`；根路径提供演示实验启动入口。
- 默认先播放约 4.5 秒深空地球旋转、拉近中国并接管全国地图的开场；主舞台顶部可重播，开场中可跳过，`?intro=0` 可直接进入全国地图。
- 系统启用“减少动态效果”时，开场自动改为不超过 1 秒的聚焦淡入。
- 正式壳层只消费 M33.2 冻结演示帧；拖动、播放和模式切换不补算业务状态。
- M33.1 验证结论见根目录 `M33_MAP_ANIMATION_TECH_VALIDATION.md`。
- M33.3 验证结论见根目录 `M33_PRESENTATION_SHELL_VALIDATION.md`。
