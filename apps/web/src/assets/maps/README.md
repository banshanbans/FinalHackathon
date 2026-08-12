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
- 原图 path 0 为海洋背景，path 1 为全国底色轮廓，path 2..32 为 31 个大陆省级填色区域。`annotate_standard_map.py` 仅对 path 2..32 增加稳定的 `name`、`data-code` 和 `id`，供 ECharts `registerMap` 识别。
- 2026-08-12 复核发现旧脚本把全国底色轮廓误当为内蒙古，造成 31 个省域标注依次串位。现已修正路径起点，并为每个行政区代码增加独立几何 SHA-256 绑定校验。
- 港澳台保留在标准地图视觉中，但不带 `simulation-province` 标记，不进入仿真、指标着色或点击详情。
- 31 个交互 path 的几何摘要 SHA-256：`2f6aea81b85e929df44aa83beb6c4dcf3fe8f14b8274506e62c6b836ac1c97d6`。

## 比赛版发布状态

根据用户确认的比赛发布规则，比赛产品不设额外地图合规审核门禁，该资产可直接随比赛 Web 产品上线。源头地图、审图号、转换步骤和几何签名仍继续保留，用于资产追溯和回归校验。

运行 `make validate-data` 会同时校验原始 EPS 哈希、31 省完整性、交互代码、总几何摘要以及每个省域代码与几何路径的绑定关系。
