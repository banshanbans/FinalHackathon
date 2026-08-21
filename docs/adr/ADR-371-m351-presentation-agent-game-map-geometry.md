# ADR-371：M35.1 Agent 博弈叙事与地图几何

状态：Implemented
日期：2026-08-13
范围：`apps/presentation` 与 M34 Presentation 只读投影

## 决策

M35.1 将 Presentation Frame 升级为 `presentation-frame-v5`，Timeline 保持 `presentation-timeline-v4`。本次不修改 M34 Scheduler、Provider、Fake 数据、消息状态机、Checkpoint、WorldState、Comparison、普通 Web 前端或开场动画。

Frame v5 只补充展示所需事实：合法互动的直接环境贡献、参与省份与全国指标的季度共享变化、四类 A/B 分歧，以及关系的稳定揭示顺序。季度共享变化不得归因于单笔交易，Q1 只显示形成值。

## 地图与叙事

- WebGL 与 SVG 共用 `presentationGeometry.ts`：解析 MultiPolygon、选择最大主体面、计算内部代表点、验证点在面内并执行 Web Mercator 投影。
- 冻结 GeoJSON、源 SVG 与生成脚本保持不变；选中描边与基础填色复用同一几何。
- 车企使用视口固定节点轨道；移动地图时将屏幕点反投影为 Deck.gl 端点。
- Spotlight 稳定排名决定最多三组关系的顺序。Action 每组执行镜头聚焦、连接绘制和短暂停留；完成后回到用户原 Spotlight。自动播放等待整个序列。
- 互动阶段降低非相关省域热力层级；当前地图高亮、Spotlight、因果 Beat 与图例绑定同一 Session。
- Reduced Motion 一次显示全部合法关系，不执行长距离飞行、逐帧绘制或脉冲。

## 表达边界

DECIDE 必须显示实际选择、替代项、机会成本和重新考虑条件。SETTLE 固定分为“本次互动直接贡献”和“本季度共享变化”。拒绝、暂缓和资源非法明确显示“未进入环境贡献”。

A/B 分歧基于双侧完整 Session 集合的并集，类型为 `control_only`、`treatment_only`、`state_changed`、`decision_changed`；主舞台只显示中文映射与“未发生”，不显示机器枚举、`null` 或 snake_case。

## 保护门禁

`GlobeIntro`、`introVisible`、`launchPhase`、`PrelaunchControlBoard`、开场 handoff、`?intro=0`、reduced-motion 开场行为与共享地图资产不属于本变更。实施前后校验和及 `M34PresentationApp.tsx` 前 325 行哈希必须一致。

## 验收结果

- 31 个省份锚点全部位于有效省域内；Mercator 四边严格映射到 1000×720。
- WebGL 与 SVG 均支持 1/2/3 组逐条揭示、Session 选择、车企节点选择与省份探索。
- `make test`、`make test-sim`、`make test-api`、`make lint`、`make validate-data`、Presentation typecheck/build 与几何专项测试通过。
- Browser 验证四画布、WebGL、SVG、开场、跳过开场、深链、控制台错误和 19 帧字段泄漏；最终结果记录在 `docs/validation/design-qa.md`。
