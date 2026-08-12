# PolicyScope / 政策涟漪 PRD

> 产品副标题：制造业设备更新政企互动 Agent 推演台  
> 文档版本：V2.0（已批准最终产品契约）  
> 更新日期：2026-08-12  
> 目标周期：48 小时比赛产品  
> 当前状态：已批准，V2 原地迁移与产品验收已完成

---

## 1. 执行摘要

PolicyScope 是一套面向国务院层面政策制定、统筹与评估人员的政企互动机制实验台。用户从中央政策协调视角设定制造业设备更新目标、财政边界和政策工具，观察中国大陆 31 个省级响应 Agent 如何形成地方政策组合，以及每省六类企业群体 Agent 如何根据自身约束选择参与、融资、技改、观望或拒绝。

系统不把大模型生成的数字当作政策结果。中央、省级和企业 Agent 只负责结构化决策；所有企业群体状态、省级指标、全国指标、网络效应和机制贡献均由确定性的 `ChinaPolicyEnv` 计算。

完整闭环为：

```text
国务院层面用户设定目标与约束
  → 中央政策研判 Agent 生成结构化政策草案
  → 用户审批
  → 31 个省级响应 Agent 选择地方政策工具
  → 186 个企业群体 Agent 用行动反馈
  → 确定性环境计算企业、省级和全国结果
  → 中央政策研判 Agent 提出干预建议
  → 用户审批或拒绝
  → 从同一 T3 检查点建立 Control / Treatment
  → T5 比较企业行为迁移、地区差异、财政压力与机制贡献
```

产品不声称预测现实 GDP、就业人数、投资金额、企业收入或政策必然结果。它回答的是：

> 在给定数据、企业群体画像、政策参数、机制版本和随机种子的条件下，不同地方与企业群体可能如何响应；改变政策工具组合后，系统机制指标和行为结构会发生怎样的相对变化？

---

## 2. 赛题回应与产品价值

### 2.1 赛题问题

企业诉求、地方政府目标、中央政策工具、资源约束与执行过程相互交织。传统政策报告通常能描述现状，但难以让政策统筹者在同一体验中观察：

- 同一中央政策为何在不同地区形成不同地方工具组合。
- 大型企业和中小企业为何对同一政策产生不同反应。
- 直接补贴、贷款贴息和融资担保分别改变了哪些企业行为。
- 提高中小企业可达性是否会带来财政压力或产业升级速度方面的代价。
- 中途调整政策后，结果差异来自政策本身还是两次无关运行。

### 2.2 产品价值

PolicyScope 将复杂的政企反馈转化为可操作、可追溯的政策实验：

- 用省级和企业群体 Agent 表达异质决策，而不是生成统一结论。
- 用结构化 Action 代替无约束群聊。
- 用确定性环境公开计算机制结果。
- 用用户审批确保 AI 不能替代中央决策。
- 用同源 A/B 让政策工具调整具有可比较性。
- 用证据引用、版本和 Replay 说明每个结果从何而来。

### 2.3 一句话定义

> 让国务院层面的政策统筹人员在政策落地前，看见地方如何选择、企业如何行动，以及政策调整在当前机制假设下带来的全国权衡。

---

## 3. 目标用户与使用场景

### 3.1 唯一核心用户

国务院层面的政策制定、统筹与评估人员，包括承担跨部门政策协调、政策研究、执行监测和政策评估职责的工作人员。

用户不是被模拟主体。用户始终拥有以下权力：

- 确认或修改中央政策草案。
- 决定是否启动推演。
- 审批、修改或拒绝中央 Agent 的干预建议。
- 决定是否创建 Treatment。
- 查看证据、方法、版本和局限。

### 3.2 AI 与用户的边界

中央政策研判 Agent 是用户的决策支持助手，不代表现实国务院，不自动发布政策，不拥有审批权，也不得声称某方案是现实中的最优政策。

推荐用户可见措辞：

- “中央政策研判 Agent 在当前实验中建议”。
- “省级响应 Agent 选择”。
- “企业群体 Agent 在当前条件下采取”。
- “模拟指数变化”。
- “在当前数据、参数与机制假设下”。

禁止用户可见措辞：

- “国务院认为”。
- “某省政府决定”。
- “该政策一定有效”。
- “系统推荐的最优政策”。
- “预计 GDP/就业/投资将增长 X%”。

### 3.3 核心使用任务

1. 设定制造业设备更新的全国目标、政策工具和硬约束。
2. 审批中央 Agent 生成的结构化政策指令。
3. 观察 31 省地方政策选择和企业群体响应。
4. 下钻任一省份，查看六类企业的行动、原因和机制贡献。
5. 识别中小企业融资可达性、区域差距和财政压力告警。
6. 审批或拒绝中央 Agent 提出的结构化干预。
7. 比较原始方案与干预方案的行为迁移、指标差和代价。
8. 查看数据质量、版本、父检查点、seed 和证据引用。

---

## 4. 产品范围

### 4.1 P0 必须完成

- 1 个中央政策研判 Agent。
- 31 个省级响应 Agent。
- 每省 6 类企业群体 Agent，共 186 个企业主体。
- 1 个制造业设备更新政策域。
- T0–T5 六个抽象政策阶段。
- 中央政策审批和 T3 干预审批。
- 从同一不可变 T3 检查点派生 Control / Treatment。
- 企业行为、省级结果、全国指标和机制贡献。
- 中国大陆 31 省级行政区地图与省企详情。
- 企业行动迁移、A/B 对照、证据抽屉和中央复盘。
- REST、SSE、Checkpoint、Replay、Cache 和 Fallback。
- 默认场景可离线、可重复演示。

### 4.2 明确不做

- 园区、投资机构、公众或消费者 Agent。
- 现实企业或单家企业数字孪生。
- 每省数百家微观企业的逐一模型调用。
- 自然语言政企群聊。
- 任意政策域和任意自然语言政策的可信仿真。
- 企业迁移、裁员和复杂跨省招商博弈。
- 真实 GDP、就业人数、投资金额、企业收入或生产率预测。
- 具体月、季度、年度的预测时间轴。
- 自动替用户选择现实“最优政策”。
- 多次重复实验与置信区间，除非全部 P0 已完成。
- 路演脚本；产品文档只定义产品、交互和验收。

### 4.3 科学与表达边界

所有结果页固定显示：

> 研判口径：结果为当前数据与机制参数下的模拟指数，用于政策方案比较。

政策参数中的比例可以使用百分比展示；模拟结果统一使用 0–100 指数、指数点变化、类别或行为迁移，不得包装成现实金额和现实百分比。

---

## 5. Agent 与环境架构

### 5.1 主体结构

```text
国务院层面用户
  └─ 中央政策研判 Agent × 1
       └─ 省级响应 Agent × 31
            └─ 企业群体 Agent × 6 / 省
                 └─ ChinaPolicyEnv
```

系统共包含 32 个政府侧 Agent 和 186 个企业群体 Agent。

### 5.2 中央政策研判 Agent

负责：

- T0：把用户目标转换为 `CentralPolicyDirective`。
- T3：读取结构化全国指标、省级反馈、企业行为和机制告警，生成最多 3 个 `CentralInterventionProposal`；P0 默认只展示 1 个。
- T5：读取 A/B 结构化结果，生成 `CentralReview`。
- 为每项建议和结论提供结构化证据引用。

不得：

- 未经用户审批发布或改变政策。
- 直接写入 WorldState 结果字段。
- 创造 Compare JSON 中不存在的数字。
- 把预期方向描述为已发生结果。
- 代表现实国务院立场。

### 5.3 省级响应 Agent

负责：

- 读取中央政策、本省 Profile、当前 State 和有限的企业群体反馈。
- 在允许范围内选择地方实施强度、政策工具结构、中小企业倾斜和技术方向。
- T3 输出结构化地方反馈与中央支持请求。
- T4 在两个分支中基于各自政策重新响应。

不得：

- 直接写入企业或省级结果指标。
- 生成现实金额、就业人数或生产率预测。
- 修改其他省份状态。
- 使用未进入实验快照的实时外部事实。
- 声称代表现实省级政府。

### 5.4 企业群体 Agent

每省固定六类：

1. 大型国有制造企业。
2. 大型民营制造企业。
3. 科技型中小企业。
4. 传统制造中小企业。
5. 高耗能工业企业。
6. 出口制造企业。

每个企业群体拥有独立 Profile、State、Action 和历史，但代表一类合成企业群体，不代表现实企业。

负责：

- 根据中央政策、地方政策和自身约束选择参与方式。
- 选择技改类型、融资方式、投入强度和支持请求。
- 输出结构化原因码和不超过 80 个汉字的摘要。

不得：

- 自行计算投资结果、生产率、就业、财政收益或最终指数。
- 创造不在 Action Schema 中的政策工具。
- 访问其他企业群体的私有状态。
- 以现实企业口吻发表立场。

### 5.5 ChinaPolicyEnv

`ChinaPolicyEnv` 是所有结果状态转移的唯一权威：

- 接受合法 Policy、ProvinceAction 和 EnterpriseAction。
- 计算政策匹配、财政约束、工具激励、融资可达性和区域效应。
- 生成省级、企业群体和全国指标。
- 每次更新同时生成机制贡献。
- 相同输入、机制版本和 seed 必须得到相同结果。
- 所有结果必须防止 NaN/Infinity，并裁剪到约定范围。

---

## 6. 默认政策场景

### 6.1 场景名称

“制造业大规模设备更新与技术改造专项”

### 6.2 默认用户目标

> 在有限财政支持下推动制造业设备升级，同时提高中小企业参与度，兼顾绿色转型、就业稳定和区域政策可达性。

### 6.3 PolicySchema

| 字段 | 范围 | 默认值 | 含义 |
|---|---:|---:|---|
| `support_intensity` | 0–100 | 70 | 中央支持强度指数，不对应现实金额 |
| `local_match_requirement` | 0–1 | 0.50 | 地方配套要求 |
| `instrument_mix.direct_subsidy` | 0–1 | 0.45 | 直接补贴占政策工具结构的比例 |
| `instrument_mix.loan_interest_support` | 0–1 | 0.35 | 贷款贴息比例 |
| `instrument_mix.financing_guarantee` | 0–1 | 0.20 | 融资担保比例 |
| `sme_preference` | 0–1 | 0.60 | 对中小企业的结构性倾斜 |
| `regional_support_bias` | -1–1 | 0 | 负值偏东部，正值偏中西部和东北 |
| `technology_mix.digital` | 0–1 | 0.40 | 数字化设备更新权重 |
| `technology_mix.green` | 0–1 | 0.30 | 绿色设备更新权重 |
| `technology_mix.general` | 0–1 | 0.30 | 基础技改权重 |

约束：

- `instrument_mix` 三项之和必须为 1。
- `technology_mix` 三项之和必须为 1。
- 用户确认前政策只能处于 Draft。
- 所有可持久化对象包含 `schema_version`。
- P0 允许修改的干预字段仅限上述字段。

### 6.4 默认 T3 干预假设

中央政策研判 Agent 可建议但不能自动执行：

```text
直接补贴：0.45 → 0.30
贷款贴息：0.35 → 0.45
融资担保：0.20 → 0.25
区域支持倾斜：0.00 → 0.35
```

建议预期方向必须标记为“待验证”：

- 企业参与指数可能上升。
- SME 融资可达性可能上升。
- 区域差距可能下降。
- 地方财政压力可能上升。

用户批准后才能生成正式 `CentralIntervention` 并创建 Treatment。

---

## 7. T0–T5 产品流程

| 阶段 | 名称 | Agent / 环境行为 | 用户可见结果 |
|---|---|---|---|
| T0 | 中央政策设定 | 中央 Agent 生成草案，用户确认 | 目标解析、结构化参数、数据/机制/模型版本、审批状态 |
| T1 | 地方政策响应 | 31 个省级 Agent 生成地方政策工具组合 | 全国地图、地方行动、差异化原因 |
| T2 | 企业行为反馈 | 每省一次批量调用生成六类企业 Action，环境计算第一轮结果 | 企业行动矩阵、融资约束、机制指标和告警 |
| T3 | 地方反馈、中央研判与审批 | 31 个省级 Agent 生成 `ProvinceFeedback`，汇总证据并冻结检查点，中央 Agent 提出干预 | 省级反馈、证据、参数 Diff、待验证方向、代价和人工审批 |
| T4 | 双分支再响应 | Control/Treatment 中省级和企业主体独立响应 | 两分支行动和状态谱系 |
| T5 | 对照与复盘 | 环境完成结算，中央 Agent 生成复盘 | 双地图、指标差、行为迁移、机制归因、局限 |

阶段是抽象政策阶段，不映射现实季度或年度。

### 7.1 调用预算

默认完整实验允许：

- 中央政策研判 Agent：T0、T3、T5，共 3 次。
- 省级响应 Agent：T1、T3 和两个 T4 分支，共约 124 次。
- 企业群体 Agent：T2 每省 1 次批量调用，T4 每分支每省 1 次，共约 93 次批量调用；每次必须返回六类企业 Action。
- 默认演示优先使用已验证缓存；Live 模式并发受限流控制。
- UI 刷新、动画和页面切换不得重复触发模型调用。

---

## 8. 核心领域模型

### 8.1 ProvinceAction

至少包含：

```text
province_code
phase
implementation_intensity        0–1
instrument_mix                  sum = 1
sme_preference                  0–1
technology_mix                  sum = 1
requested_central_support       0–1
reason_codes
public_summary                  ≤ 80 汉字
run_mode
fallback_used
```

### 8.2 EnterpriseGroupProfile

每个企业群体 Profile 至少包含：

```text
enterprise_group_id
province_code
cohort_type
cohort_weight
capital_reserve
cash_flow_health
debt_pressure
equipment_age_pressure
digitalization_base
energy_intensity
financing_access
demand_expectation
employment_sensitivity
data_quality
provenance
```

所有模拟特征使用 0–1 标准化值。`cohort_weight` 仅用于群体聚合，不表示现实企业数量。

### 8.3 EnterpriseAction

```text
participation
  participate | conditional | wait | decline

upgrade_type
  digital | green | general | none

financing_choice
  self_funded | direct_subsidy | interest_subsidy
  | guarantee_loan | none

investment_intensity            0–1
requested_support               0–1
reason_codes
public_summary                  ≤ 80 汉字
run_mode
fallback_used
```

一致性约束：

- `decline` 时 `upgrade_type=none`、`financing_choice=none`、`investment_intensity=0`。
- `wait` 时 `upgrade_type=none`、`investment_intensity` 不得高于 0.2。
- `participate` 时 `upgrade_type` 不能为 `none`。
- 每省每阶段必须恰好包含六个不同 `cohort_type`。

### 8.4 ProvinceState

至少包含：

- 企业参与指数。
- 设备更新意愿指数。
- SME 融资可达性指数。
- 产业升级指数。
- 就业稳定指数。
- 地方财政压力指数。
- 最近一次省级 Action ID。

### 8.5 EnterpriseGroupState

至少包含：

- 参与准备度。
- 融资可达性。
- 设备更新准备度。
- 数字化水平指数。
- 绿色转型水平指数。
- 就业稳定指数。
- 最近一次 EnterpriseAction ID。

### 8.6 NationalMetrics

P0 固定六项：

1. 企业参与指数。
2. 设备更新意愿指数。
3. SME 融资可达性指数。
4. 产业升级指数。
5. 地方财政压力指数。
6. 区域差距指数。

所有指标为 0–100 内部指数。A/B 显示“指数点变化”，不显示现实百分比。

### 8.7 WorldState

WorldState 是前端、Replay 和 Compare 的权威投影视图，至少包含：

```text
experiment / branch / checkpoint IDs
phase / status / run_mode
policy / directive
province_profiles / province_states / province_actions
enterprise_profiles / enterprise_states / enterprise_actions
national_metrics
mechanism_contributions
network_effects
intervention_proposals / approved_intervention
central_review
data / mechanism / prompt / model / app versions
seed
```

已提交状态不可原地修改。分支必须拥有独立 state lineage。

### 8.8 ComparisonResult

至少包含：

- 政策参数 Diff。
- 全国六项指标的 Control、Treatment 和 delta。
- 31 省指标差。
- 六类企业群体差异。
- 企业行为迁移矩阵，例如 `wait → conditional → participate`。
- 重点改善、重点承压和变化最小的地区/群体。
- 企业层和省级机制贡献合计。
- 中央复盘与证据引用。

---

## 9. 环境机制

### 9.1 机制要求

至少实现：

- 政策—行业匹配。
- 设备更新压力与基础能力。
- 中央支持与地方配套。
- 直接补贴激励。
- 贷款贴息杠杆。
- 融资担保可达性。
- SME 倾斜。
- 区域支持倾斜。
- 企业现金流、债务和融资约束。
- 地方财政与执行成本。
- 数字化、绿色和基础技改方向匹配。

### 9.2 机制贡献

每次企业和省级状态更新必须生成：

```text
policy_match
direct_subsidy_incentive
interest_support_leverage
guarantee_access
sme_preference_effect
regional_support_effect
financing_constraint_loss
fiscal_execution_cost
```

贡献来自计算过程，不允许由 LLM 在结果生成后猜测。

### 9.3 确定性与边界

- 公式与权重全部放在版本化机制配置中。
- 随机性通过显式 seed/Random 实例注入。
- 相同输入和版本得到相同输出。
- 所有指数 clamp 到 0–100。
- 非有限值必须拒绝并记录错误，不得静默继续。

---

## 10. LLM Provider、缓存与失败处理

所有模型调用必须经过统一 Provider：

```text
LiveLLMProvider
CachedLLMProvider
FakeLLMProvider
```

Provider 公开能力至少包含：

- 生成中央政策指令。
- 生成省级政策 Action。
- 按省批量生成六类企业 Action。
- 生成中央干预建议。
- 生成中央复盘。

企业批量输出规则：

1. 首次输出必须通过 Schema 和六类完整性校验。
2. 首次失败允许携带结构化错误修复一次。
3. 第二次失败整省进入 deterministic fallback。
4. Fallback 必须进入 WorldState、SSE 和 Replay。
5. 单省失败不得阻断其他省份。

缓存键必须包含所有影响输出的字段：Policy、Profile、State、Prompt 版本、模型、机制版本、分支、阶段和 seed。

默认比赛场景必须预生成完整缓存。不得把现场演示完全押在模型网络调用上。

---

## 11. 信息架构与核心页面

正式前端采用四个路由和两个可深链抽屉：

```text
/experiments/new
/experiments/:id/live
/experiments/:id/intervention
/experiments/:id/compare

?province=41
?evidence=<evidence-ref>
```

### 11.1 中央政策设定

- 用户目标输入。
- 中央 Agent 结构化解析。
- 完整政策参数编辑。
- 数据、机制、Prompt、模型和 seed。
- Draft、待审批和已审批状态。
- “确认中央政策并开始推演”主操作。

### 11.2 全国实时推演

- 真实 31 省矢量地图。
- 全国六项机制指标。
- T0–T5 时间轴。
- 省级和企业群体行动流。
- 运行、阶段完成、fallback 和错误状态。
- 点击省份打开省企详情抽屉。

### 11.3 省企详情抽屉

必须回答：

- 该省的制造业、SME、财政和融资约束是什么。
- 省级 Agent 选择了什么地方工具。
- 六类企业分别采取了什么行动。
- 哪类企业发生观望或条件参与，原因是什么。
- 环境如何把行动转换成指标。
- 当前数据质量和来源是什么。

### 11.4 T3 干预审批

固定三栏：

```text
结构化证据 → AI 建议 → 人类审批
```

必须显示：

- 问题摘要但不预设“必须干预”。
- 参数 `from → to` Diff。
- 目标指标、待验证方向和可能代价。
- 父检查点、seed、数据和机制版本。
- 批准、修改和拒绝。
- “只有批准才创建 Treatment”的说明。

### 11.5 A/B 对照

- 同步 Control / Treatment 地图。
- 政策 Diff 和公平性声明。
- 全国六项指标差。
- 企业行为迁移。
- 地区和企业群体变化排行。
- 机制贡献。
- 中央复盘、限制和证据跳转。

Control/Treatment 用户可见名称为“原始方案/干预方案”，不得提前称干预方案为“优化方案”。

### 11.6 方法与证据抽屉

- 数据质量类别与 provenance。
- 指标定义和单位。
- 机制版本与参数摘要。
- 模型/Prompt/app 版本。
- seed、branch、parent checkpoint。
- Evidence Ref 对应的结构化事实。

视觉和交互细则以 `STITCH_FRONTEND_SPEC.md` 为准。

---

## 12. API、SSE 与 Replay

### 12.1 REST

现有资源路径尽量保持稳定：

```text
POST /api/experiments
GET  /api/experiments/{id}
POST /api/experiments/{id}/directive/approve
POST /api/experiments/{id}/run
GET  /api/experiments/{id}/state
GET  /api/experiments/{id}/stream
POST /api/experiments/{id}/interventions/{proposal_id}/approve
POST /api/experiments/{id}/branches
POST /api/branches/{id}/run
GET  /api/experiments/{id}/compare
GET  /api/experiments/{id}/replay
GET  /api/meta/provinces
GET  /api/meta/enterprise-archetypes
```

DTO 升级到 V2 Schema。创建实验、运行阶段和创建分支必须幂等或接受幂等键。

- 非法阶段转换返回 409。
- 未审批干预返回 403 或稳定领域错误。
- 错误响应包含稳定 `error_code`，不泄漏堆栈。

### 12.2 SSE

EventEnvelope 至少包含：

```text
event_id
type
experiment_id
branch_id
phase
timestamp
schema_version
payload
```

新增企业事件：

```text
enterprise.batch.started
enterprise.decision.completed
enterprise.decision.fallback
enterprise.aggregate.updated
province.feedback.completed
```

事件 ID 单调、支持 `Last-Event-ID`、客户端去重。SSE 只通知事实，完整状态通过 WorldState 获取。

### 12.3 Replay

- Append-only JSONL。
- 保存中央、省级和企业结构化输出。
- 保存校验、修复、fallback、环境贡献和版本。
- 保存审批和分支谱系。
- 不保存 API Key、模型长思维链和未授权材料。

---

## 13. 数据要求

### 13.1 省级数据

中国大陆 31 个省级行政区进入计算。港澳台不进入本次仿真，并在方法抽屉明确说明。

省级 Profile 至少新增：

- 制造业基础。
- SME 密度代理。
- 财政空间。
- 融资约束代理。
- 设备老化压力代理。
- 数字化基础。
- 能源强度/绿色转型压力。
- 就业压力。

### 13.2 企业群体数据

六类企业群体由版本化模板与省级 Profile 组合生成。不得声称代表现实企业数量或财务状态。

每个字段记录：

- 来源或 `demo` 声明。
- 来源年份。
- 单位。
- 标准化方法。
- 缺失值处理。
- `verified`、`proxy` 或 `demo`。

### 13.3 数据验证

更新数据后必须验证：

- 31 省代码唯一且齐全。
- 每省六类企业群体完整且唯一。
- 数值范围合法。
- 群体权重有效。
- provenance 完整。
- 地图与计算范围一致。

---

## 14. 前端视觉与可访问性原则

- 品牌统一为“PolicyScope / 政策涟漪”。
- 面向国务院用户的中央政策工作台，不使用仿官方徽章或“官方系统”措辞。
- 采用 Stitch 的浅色现代制度工作台风格。
- 全站中文优先，仅保留必要机器概念。
- 模型生成、环境计算、用户审批、数据事实使用不同标签。
- 状态不能只依靠颜色表达。
- 地图提供图例、指标、阶段、键盘焦点和表格替代。
- 结果单位必须明确为指数或指数点。
- 1440×900 为主验收画布，1280 宽仍可完成主流程。
- P0 不做移动端，但不得出现影响核心操作的横向裁切。

---

## 15. 非功能要求

### 15.1 性能

- 首个 SSE 事件 2 秒内出现。
- Cache 模式完整实验目标 20 秒内。
- Live 模式目标 120 秒内；超过则允许显式 fallback。
- 单次模型调用默认超时 12 秒。
- 地图状态更新后 500ms 内完成渲染。

### 15.2 稳定性

- 单省或单批企业失败不阻断整轮。
- 阶段只在所有 Action 合法且环境更新完成后原子提交。
- 刷新和 SSE 重连不重复应用事件。
- 默认场景无网络时可用 Cache/Fallback 完成。

### 15.3 可解释性

- 每个数字可追溯到环境字段和机制贡献。
- 每个 Agent Action 可追溯到输入哈希、Prompt、模型和校验状态。
- 每条中央建议和复盘可跳转到结构化证据。
- 不展示模型长思维链，只展示原因码和短摘要。

---

## 16. P0 验收标准

| 编号 | Given | When | Then |
|---|---|---|---|
| AC-01 | 用户输入设备更新目标 | 生成中央政策 | 返回合法 V2 指令，用户批准前不进入 T1 |
| AC-02 | 中央政策已批准 | 运行 T1 | 31/31 省产生合法地方 Action 或显式 fallback |
| AC-03 | T2 开始 | 企业批量决策 | 31 省各有且只有六类企业 Action |
| AC-04 | 企业输出非法 | 修复仍失败 | 整省使用 deterministic fallback，并在 UI/SSE/Replay 标记 |
| AC-05 | 用户点击河南 | 打开省企详情 | 首屏显示地方工具、六类企业行动、告警与机制贡献 |
| AC-06 | T3 完成 | 中央 Agent 研判 | 显示证据、参数 Diff、待验证方向和代价 |
| AC-07 | 干预未审批 | 请求创建分支 | API 明确拒绝，不改变 WorldState |
| AC-08 | 干预已审批 | 创建 Treatment | Control/Treatment 共享同一不可变父检查点 |
| AC-09 | T5 完成 | 打开 A/B | 显示双地图、六项指标、企业迁移、地区差和机制归因 |
| AC-10 | 查看中央复盘 | 点击证据 | 每条结论跳转到 Compare JSON 中存在的事实 |
| AC-11 | SSE 断线 | 带 Last-Event-ID 重连 | 不重复应用已处理状态 |
| AC-12 | 打开任一结果页 | 页面完成加载 | 可见机制实验免责声明和数据质量标签 |

### 16.1 Demo Ready 产品定义

- 默认场景、固定 seed 和完整缓存准备就绪。
- 无网络可完成主流程。
- 31×6 企业群体完整。
- 未审批路径和 fallback 路径已验证。
- Control/Treatment 分支隔离已验证。
- 1440×900 Stitch 视觉 QA 通过。
- 连续完成 3 次端到端运行。
- 不包含现实金额预测、现实百分比预测或“最优政策”结论。

---

## 17. 风险与砍项顺序

| 风险 | 应对 |
|---|---|
| 企业批量模型输出不完整 | 强 Schema、一次修复、整省 fallback、预生成缓存 |
| 省级与企业调用数量过多 | 分省批量企业调用、受控并发、默认 Cache |
| 企业行为同质化 | 六类 Profile、原因码、河南/广东/山东纵向测试 |
| 结果被理解为预测 | 指数化、固定声明、禁用现实金额、证据抽屉 |
| A/B 被随机性污染 | 同一 T3 检查点、相同版本、显式 seed 规则 |
| Stitch 静态稿被误当产品 | React/API 实现、核心 CTA 真实工作、设计 QA 门禁 |
| 地图来源或边界不合规 | 离线矢量资产 provenance、合规检查、禁止截图冒充组件 |
| 时间不足 | 按以下顺序砍项，保护闭环 |

时间不足时依次砍掉：

1. 多个中央干预备选，只保留一个。
2. 复杂 Replay 查询，只保留证据抽屉。
3. 高级地图动画。
4. 复杂筛选和多维排序。
5. Live 企业推理展示，默认使用透明 Cache。

不可砍掉：

- 国务院层面用户视角。
- 中央政策研判 Agent 的 T0/T3/T5。
- 31 个省级响应 Agent。
- 每省六类企业群体 Agent。
- 企业 Action 与确定性环境分离。
- 用户审批。
- T3 同源分支。
- A/B 企业行为迁移和机制归因。
- Cache/Fallback、数据标签和免责声明。

---

## 18. 成功指标

比赛产品成功需要同时满足：

- 用户无需解释即可理解自己位于中央政策协调席。
- 31 省和六类企业群体在产品中真实可见、可交互、可追溯。
- 企业用行动而非聊天表达政策响应。
- 至少能解释一个传统 SME 从 `wait` 转为 `conditional/participate` 的机制链。
- AI 在策略选择中发挥必要作用，结果计算仍由确定性环境承担。
- 用户审批是实际 API 门禁，不是前端装饰。
- 同源 A/B 能同时展示收益和代价。
- 产品视觉、内容和交互在 1440×900 下完整统一。
- 评委可以辨认数据质量、方法边界和持续扩展价值。

---

## 19. 文档门禁状态

本 V2 PRD 已获得用户批准，并已替代 V1“战略性新兴产业扶持、无企业主体”的产品契约。代码、测试、数据、API 和 React 前端已经按本契约完成原地迁移；V1 回滚点保留在 Git 提交 `12456a3`。

当前冻结文档组为：

- `DEVELOPMENT_PLAN.md`
- `AGENTS.md`
- `STITCH_FRONTEND_SPEC.md`
- `README.md` 中的交付与运行说明

产品 QA 已通过。根据用户确认的比赛发布规则，比赛版地图无额外合规审核门禁，可直接随 Web 产品上线；来源、审图号、省域绑定和几何校验记录继续保留。
