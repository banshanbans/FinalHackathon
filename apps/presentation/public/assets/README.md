# Presentation map assets

- `china-presentation-map.geojson` 是由冻结分析 SVG 确定性生成的 WebGL 展示投影，包含 31 个 `simulation-province` 和香港、澳门、台湾 3 个 `territory-context`。
- `china-analysis-map.svg` 是源 SVG 的逐字节副本，用于 WebGL 不可用时的兼容渲染。
- GeoJSON 仅用于画面渲染，不是测距、面积、空间分析或现实地理主张的数据源。
- 每个省保留源路径 SHA-256；根级 metadata 保留源几何和源 SVG SHA-256。
- `svg-to-web-mercator-render-v2-aspect-locked` 按源路径宽高比反算经度跨度，确保 MapLibre Web Mercator 中不发生横向拉伸。
- 三次贝塞尔曲线固定采样 24 段；校验器拒绝低于该精度的展示资产，并复核 SVG 与 Web Mercator 宽高比一致。
- 港澳台保持中性轮廓与名称展示，不接收帧指标、事件覆盖、交互或缺失值语义；当前仿真范围仍严格为 31 省。

生成与校验：

```bash
.venv/bin/python scripts/build_presentation_map.py
.venv/bin/python scripts/validate_presentation_map.py
```
