# 13110 文档导航

本目录集中管理 13110 的产品决策、前端与演示规范、验收记录和对外展示资产。根目录只保留产品与开发的核心入口。

## 核心入口

- [产品需求文档](../PRD_%E7%9C%81%E5%9F%9F%E6%94%BF%E7%AD%96%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E6%8E%A8%E6%BC%94%E5%B9%B3%E5%8F%B0.md)
- [开发计划](../DEVELOPMENT_PLAN.md)
- [Agent 与开发约束](../AGENTS.md)
- [项目 README](../README.md)

## 架构决策

- [ADR-001：AgentSociety2 运行时技术验证](./adr/001-agentsociety2-runtime-spike.md)
- [ADR-310：省际协同事件驱动](./adr/ADR-310-event-driven-interprovincial-coordination.md)
- [ADR-320：同源 A/B 与伪 Agent 防护](./adr/ADR-320-v32-upfront-ab-and-fake-agent.md)
- [ADR-330：上下文驱动的 Agent 协同](./adr/ADR-330-m30-context-driven-agent-coordination.md)
- [ADR-340：显式决策与互动画布](./adr/ADR-340-m31-explicit-decisions-and-interaction-canvas.md)
- [ADR-350：Presentation Hall 事件时间线](./adr/ADR-350-presentation-hall-event-timeline.md)
- [ADR-360：M34 季度事件驱动互动](./adr/ADR-360-m34-quarterly-event-driven-interaction.md)
- [ADR-370：M35 因果舞台](./adr/ADR-370-m35-presentation-causal-stage.md)
- [ADR-371：Agent 博弈地图几何](./adr/ADR-371-m351-presentation-agent-game-map-geometry.md)
- [ADR-372：Cache-first DeepSeek 与全国地图](./adr/ADR-372-m352-cache-first-deepseek-and-national-map.md)
- [ADR-373：默认预热缓存参数](./adr/ADR-373-m353-default-warm-cache-preset.md)
- [ADR-374：DeepSeek 质量门禁](./adr/ADR-374-m354-deepseek-cache-quality-gate.md)

## 产品与演示规范

- [Presentation Hall 规范](./specs/PRESENTATION_HALL_SPEC.md)
- [前端产品规范](./specs/STITCH_FRONTEND_SPEC.md)

## 验收记录

- [M33 地图与动画技术验证](./validation/M33_MAP_ANIMATION_TECH_VALIDATION.md)
- [M33 Presentation API 验证](./validation/M33_PRESENTATION_API_VALIDATION.md)
- [M33 Presentation Shell 验证](./validation/M33_PRESENTATION_SHELL_VALIDATION.md)
- [M33 Presentation 最终验收](./validation/M33_PRESENTATION_FINAL_VALIDATION.md)
- [M35 Cache-first、DeepSeek 与全国地图验收](./validation/M35_2_CACHE_DEEPSEEK_NATIONAL_MAP_VALIDATION.md)
- [Presentation Design QA](./validation/design-qa.md)
- [Roadshow Design QA](./validation/roadshow-design-qa.md)

## 图像资产

- `assets/readme/`：README 使用的两张实机截图。
- `assets/m35/`：M35 正式视觉基准与验收画面。

其他本地批量 QA 截图、原型、运行结果和比赛资料不进入 Git，但保留在开发者本机。
