# ADR-310：V3.1 事件驱动省际协同与比较模式

状态：Accepted
日期：2026-08-12

## 决策

V3.1 保持 V3.0 顶层阶段，在 Y2_Q3 内增加一次实验级事件审批和两轮省际交互。每个实验创建时固定一种比较模式：

- `policy_intervention`：政策不同、事件相同。
- `event_counterfactual`：政策相同、Control 无事件、Treatment 有事件。

两种模式都从同一首年不可变 Checkpoint 派生双分支，不生成四分支。比较服务必须返回机器可校验的唯一主动差异证明，并在政策和事件同时不一致时拒绝结果。

事件只来自五模板冻结目录，强度为 0.25/0.50/0.75。两个分支完成 Y2_Q2 后进入 `awaiting_event`；未审批进入 Y2_Q3 返回 `EVENT_APPROVAL_REQUIRED`。事件批准是一次、原子且不可修改的用户决策。

Round 1 并发生成 31 个信号；只有全量提交或逐主体 fallback 后，Round 2 才读取授权 Peer 信号。`coordinate` 只有互选且协作资格边有效时才产生贡献，单向提议记录为 unmatched。事件响应是 Q3 覆盖层，不修改 Q1 Action。

## 理由

该设计可分别回答“政策比例变化后的抗冲击差异”和“相同政策下事件有无的净影响”，避免用四分支提高认知与计算复杂度，也避免顺序调用导致省级 Agent 观察未冻结信号。

## 结果

- 新增 v5 World/Comparison/Event 和 `nev-policy-env-v2`。
- 政策模式调用预算为 281，事件模式为 219；无事件 Control 不产生伪交互调用。
- Replay 记录事实顺序，Audit 记录 Agent、审批与机制，Checkpoint 只负责首年恢复和分支。
- 前端不新增路由，在现有五路由中加入模式选择、事件实验台、事件/交互图层、省级链和模式化 Compare。

## 后续数据约束

省级 Profile 的下一轮迁移遵守 `docs/data/PROVINCE_PROFILE_DATA_REQUIREMENTS_V3_1.md`：真实原始经济、产业、新能源汽车市场、节点/物流、历史政策、事件敏感度与车企基线为主层，0–1 指数为可反算派生层；Persona 由事实和历史政策证据约束，不写省份刻板性格；观察、竞争、协作 Peer 分开建模。该迁移按用户要求在 M28 之后启动，不得以当前 proxy 冒充 verified。
