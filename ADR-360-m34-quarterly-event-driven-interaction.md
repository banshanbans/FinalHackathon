# ADR-360：M34 季度事件驱动互动与年度时间轴

> 状态：Approved / Implementation active
> 日期：2026-08-13
> 取代：M32 固定七轮运行时；M33/M34 Presentation 旧投影仅作历史记录

## 1. 决策

V3.2 原地升级为 `v3_2_m34`。新实验使用 `exp_m34_*`，以四个宏观季度和季度内最多三波互动替代固定七轮：

```text
Q1–Q4 宏观 Tick
  → 授权 Inbox
  → wave_0 / wave_1 / wave_2
  → 季末确定性环境结算
  → Q4 同源 A/B 与中央年度复盘
```

逻辑时间固定为 `{tick, wave, sequence}`。它只表达模拟季度和因果顺序，不生成或暗示 Agent 的现实响应日期。

旧 `exp_m32_*` 不迁移、不加载、不删除；所有实验运行和展示接口稳定返回 HTTP 410 与 `LEGACY_V32_RUNTIME_UNSUPPORTED`。

## 2. 活动版本

| 对象 | 版本 |
|---|---|
| 实验设计 | `experiment-design-v2` |
| 事件计划 | `event-plan-v2` |
| 基线 | `baseline-snapshot-v3` |
| 季度检查点 | `tick-checkpoint-v1` |
| 授权收件箱 | `authorized-inbox-v1` |
| 互动消息 | `interaction-message-v1` |
| 主体季度决策 | `agent-tick-decision-v1` |
| 互动会话 | `interaction-session-v1` |
| 互动市场 | `interaction-market-v1` |
| 分支 | `branch-v9` |
| World | `world-state-v10` |
| Comparison | `comparison-v10` |
| SSE Event | `event-v10` |
| Runtime Snapshot | `runtime-snapshot-v2` |
| Presentation Frame | `presentation-frame-v3` |
| Presentation Timeline | `presentation-timeline-v3` |

缓存只能使用新的 `v3_2_m34_fake` 与 `v3_2_m34_luna` 命名空间，不得复用或改名 M30/M32 缓存。

## 3. 调度与权限

- Q1 `wave_0` 每分支恰好激活 31 个省级和 10 个车企主体。
- Q2–Q4 只有主体收到新授权消息、计划复评到期、结构化重新考虑条件成立、事件开始可见或存在未决事务时才激活。
- Scheduler 只判断是否存在新上下文；`ignore | monitor | initiate | respond | revise` 由主体输出。
- 每波先冻结所有 Inbox，再并发收集输出，最后统一冻结和清算。两个分支完成同一波后才可推进，消息不得跨分支。
- 每 Tick 最多 3 波、180 次调用、500 条消息；每对主体最多两次条件往返。触顶后保留最后合法状态并记录 `interaction_budget_exhausted`。
- 私有省际提议、省企资源包和反报价只投递交易双方；公开事件、政策与公开行动摘要按授权观察网络投递。

## 4. 交易与资源

交易状态固定为：

```text
proposed → countered | accepted | rejected | deferred
         → settled | withdrawn | expired | resource_invalid
```

只有 `settled` 交易进入环境贡献。年度省级财政资源包和车企全国市场、渠道、产能、管理资源包在基线冻结，季度间结转；季度行动只能重配剩余资源，不能重新获得完整预算。

省份每 Tick 最多发起 2 项省际提议和 2 项省企资源包。车企每 Tick 最多发起或回应 5 项省级合作意向。双方均可主动发起。

## 5. Agent、环境与缓存边界

- 中央 Agent 只在创建时生成一次结构化政策解读，并在 Q4 Comparison 后生成一次年度复盘；季度内不得修改政策或 WorldState。
- Live/Cache Prompt 不包含确定性候选行动。确定性候选只在 Fake、缓存缺失、模型失败、Schema 或资源校验失败时接管，并标记 fallback。
- 决策记录保存结构化观察、行动、替代项、机会成本、条件和 Evidence，不保存思维链。
- 环境以纯函数 `settle_quarter(previous_checkpoint, committed_actions, settled_interactions, active_events)` 每季结算并产生不可变 Checkpoint；Gap、HHI、财政、需求与产业结果仍只有环境可计算。
- Cache Replay 必须通过输出哈希校验；Fresh Live Run 不承诺位级复现。Fake 输出始终是 fallback，禁止写入 Luna 缓存。

## 6. API 与展示

- `POST /api/experiments` 默认且只接受 `product_version=v3_2_m34`。
- 设计使用 `event_plans[0..3]`；拒绝重复模板和相同 `conflict_group` 的互斥事件。
- `POST /api/experiments/{id}/run` 只接受 `until_tick`，按缺失前缀推进并保持幂等；倒退或越过门禁返回 409。
- 决策按 `branch_id/tick/wave/agent_id` 查询；新增 `/interactions` 查询消息、会话、匹配和资源重配。
- SSE 增加 `tick`、`wave`、`logical_sequence`、`message_id` 与 `session_id`。
- Presentation 时间轴显示一年四个季度区段。政策冻结、外生事件、有互动的 Wave、季度结算和年度比较形成聚合节点；固定显示“模拟季度与互动顺序，不代表现实响应日期”。

## 7. 否决方案

- 不并行保留 M32 七轮作为新实验模式。
- 不将旧 `exp_m32_*` 原地转换为 M34。
- 不引入 Microsoft Agent Framework、ADK 或 AutoGen；领域 Orchestrator 继续掌握权限、资源、屏障、持久化和确定性结算。
- 不用前端自由文本生成事件系数，不让 LLM 输出权威环境指标。
