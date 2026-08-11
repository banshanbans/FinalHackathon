# PolicyScope 标准地图资产说明

## 来源

- 来源机构：中华人民共和国自然资源部标准地图服务系统。
- 当前服务入口：<https://bzdt.tianditu.gov.cn/>。
- 下载时使用的官方历史详情页：<http://bzdt.ch.mnr.gov.cn/browse.html?picId=%274o28b0625501ad13015501ad2bfc0045%27>。
- 地图名称：中国地图（各省着色），1:4800 万，64 开。
- 审图号：`GS(2016)1609号`。
- 原始资源 ID：`4o28b0625501ad13015501ad2bfc0045`。
- 下载日期：2026-08-12。
- 原始 EPS SHA-256：`48dcb75fce083d66ee58582368218413f28bbd39c803b75fde15390b1a0badf1`。

原始 EPS 保存在 `source/`。地图服务页面说明：直接使用标准地图应标注审图号；对地图内容进行编辑后公开使用，应依法履行地图审核程序。

## 转换与交互标注

正式 React 前端不使用浏览器截图或在线地图 CDN。转换流程为：

```bash
pstoedit -f 'svg:-standalone' -dt -flat 0.1 \
  source/4o28b0625501ad13015501ad2bfc0045.eps \
  /tmp/china-standard-map-unannotated.svg

python scripts/annotate_standard_map.py \
  /tmp/china-standard-map-unannotated.svg \
  apps/web/src/assets/maps/china-standard-map.svg
```

- `pstoedit 4.3`、`Ghostscript 10.07.1` 仅用于离线格式转换。
- 转换后的边界 path 未进行手工重绘、简化或坐标变换。
- `annotate_standard_map.py` 只为原图中 31 个大陆省级填色 path 增加稳定的 `name`、`data-code` 和 `id`，供 ECharts `registerMap` 识别。
- 港澳台保留在标准地图视觉中，但不带 `simulation-province` 标记，不进入仿真、指标着色或点击详情。
- 31 个交互 path 的几何摘要 SHA-256：`3f4d35ae47742f8e272ca23621c4ed79e7b188036bbf2c0cfc44e160b2fa4197`。

## 合规门禁

该资产可用于本仓库的内部开发、比赛现场演示与评审截图。任何面向公众的部署或传播，都必须在发布检查表中重新核对标准地图服务条款、审图号展示和编辑后地图审核要求；未完成核验时不得公开发布。

运行 `make validate-data` 会同时校验原始 EPS 哈希、31 省完整性、交互代码和转换后几何摘要。
