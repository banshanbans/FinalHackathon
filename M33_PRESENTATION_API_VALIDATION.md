# M33.2 演示投影 API 验证

> 日期：2026-08-13  
> 结论：通过；M33.3 其余独立大屏壳层可以开始接入。

## 1. 实现范围

- 新增纯只读 `PresentationProjectionService`，从 M32 `WorldStateV6`、冻结 Action、Comparison 和 Replay Event 投影演示时间轴。
- 新增 `GET /api/experiments/{id}/presentation/timeline`。
- 新增 `GET /api/experiments/{id}/presentation/frames/{frame_id}`。
- 不写 World、Action、Comparison、Replay 或 Audit，不增加 Agent 调用。

## 2. 冻结帧与事件节点

无事件的完整实验固定投影 10 个合法帧：

```text
政策输入
方案冻结
省级初始行动
车企初步 Top-K
省级竞争反制与协同
车企报价与反报价
省级反报价回应
车企最终确认与重配
环境结算
结果复盘
```

事件实验额外生成一个 `presentation-event-marker-v1` 和达到触发边界后的事件帧。事件位置只允许现有三个冻结边界；事件名称、强度、作用范围、机制通道、Evidence 和源哈希均来自已确认的 `EventPlan`。

## 3. 投影内容

- 省域值：中央承担比例、省级支持强度、车企平均销售投入、反报价接受数、发展指数和最终 A/B Delta。
- 覆盖层：竞争、协同、省企谈判、反报价回应、Top-K 重配、车企匹配和事件。
- 指标：环境结算六项中央指标；结果帧显示干预方案值与相对原始方案 Delta。
- 全国态覆盖层最多 10 条，排序稳定；缺失省份必须显式 `value=null, missing=true`。
- 每帧保留 Replay `source_event_ids`、Evidence 引用与确定性 `source_hash`。

## 4. 真实性与只读验证

- API 调用前后的 WorldState JSON 完全一致。
- 旧帧 `source_hash` 不因后续轮次完成而变化。
- 所有 `source_event_ids` 均可在对应实验 Replay 中找到。
- 未知帧稳定返回 `404 / PRESENTATION_FRAME_NOT_FOUND`。
- 只有实验完成并产生 Comparison 后才开放 `story` 与 `compare`；运行中只开放 `live`。

## 5. 检查结果

```text
simulation/tests                              48 passed
apps/api/tests                                 7 passed
M33.2 focused Schema/API/Replay               10 passed
focused Ruff                                   PASS
apps/presentation TypeScript typecheck         PASS
apps/presentation production build             PASS
git diff --check                               PASS
```

FastAPI 测试保留一条上游 `StarletteDeprecationWarning`，不影响接口行为。仓库全局 Ruff 仍会报告 M33.2 之外既有的 19 条格式/现代化问题；本次新增和直接修改文件的聚焦 Ruff 已通过。

## 6. 退出结论

`presentation-timeline-v1`、`presentation-frame-v1`、事件节点、互动覆盖层、Replay 映射、稳定错误语义和只读边界均已通过。M33.2 完成，下一阶段进入 M33.3：将正式全屏 HUD、GovSim Glass UI Kit、功能坞、浮层、三模式和底部时间轴接入这些权威投影。
