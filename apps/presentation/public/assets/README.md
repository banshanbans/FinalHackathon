# Presentation map assets

- `china-presentation-map.geojson` 是由冻结分析 SVG 确定性生成的 WebGL 展示投影，包含 31 个 `simulation-province` 和香港、澳门、台湾 3 个 `territory-context`。
- `china-analysis-map.svg` 是源 SVG 的逐字节副本，用于 WebGL 不可用时的兼容渲染。
- GeoJSON 仅用于画面渲染，不是测距、面积、空间分析或现实地理主张的数据源。
- 每个省保留源路径 SHA-256；根级 metadata 保留源几何和源 SVG SHA-256。
- `svg-to-web-mercator-render-v2-aspect-locked` 按源路径宽高比反算经度跨度，确保 MapLibre Web Mercator 中不发生横向拉伸。
- 三次贝塞尔曲线固定采样 24 段；校验器拒绝低于该精度的展示资产，并复核 SVG 与 Web Mercator 宽高比一致。
- 港澳台保持中性轮廓与名称展示，不接收帧指标、事件覆盖、交互或缺失值语义；当前仿真范围仍严格为 31 省。
- `china-standard-map.svg` 是同一冻结自然资源部标准地图的本地副本；Presentation 从其官方南海诸岛附图区域直接裁切显示，不手工重绘。该标准地图内容固定在地图画布左下角，不跟随地图相机、分支或 A/B 视角移动，并与右下角图例分区；使用方角虚线框，不使用说明卡底色、阴影或外置标题牌。内部“南海诸岛”名称、岛礁与断续线完全来自该冻结原件。
- `china-south-sea-standard-dashes.svg` 从同一冻结原件的黑色制图路径中机械分离南海断续线。左下角附图继续视口固定；主地图使用同一资产的地图坐标锚定层，随中国地图共同平移、缩放、俯仰和旋转，并始终与台湾、海南保持刚性相对关系。该线不手绘、不补点、不参与指标或交互计算。
- `china-south-sea-standard-dashes.geojson` 由同一生成脚本把上述 46 条官方黑色路径按 12 个断续符号分组，机械求取每组主轴并投影为 12 条细长圆头 `LineString`；保留逐路径 SHA-256、源裁切范围、展示锚定范围和 `simulation_scope=none`，供 MapLibre 与 SVG 兼容层共享相机语义。展示锚定范围按项目台湾、海南几何校准为东侧—南部—西侧 U 形关系，不增加人工补点。
- `china-south-sea-standard-overlay.svg` 由 `scripts/build_south_china_sea_overlay.py` 从上述冻结原件的南海区域机械提取黑色制图线与文字轮廓，背景透明；不得人工修改其路径。
- 南海诸岛附图只是中国全国版图上下文；不进入 31 省 Agent、指标色阶、事件覆盖、关系线、交互或比较计算。

生成与校验：

```bash
.venv/bin/python scripts/build_presentation_map.py
.venv/bin/python scripts/validate_presentation_map.py
```
