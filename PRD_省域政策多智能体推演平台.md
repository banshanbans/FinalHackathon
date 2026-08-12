# PolicyScope / 政策涟漪 PRD

> 产品副标题：制造业设备更新政企互动 Agent 推演台  
> 文档版本：V2.1（省级 Agent 主决策契约，已批准）
> 更新日期：2026-08-12  
> 目标周期：48 小时比赛产品  
> 当前状态：V2 基线已验收；V2.1 产品主体已实现，最终 E2E/Cache/Design QA 待恢复

---

## 1. 执行摘要

PolicyScope 是一套面向国务院层面政策制定、统筹与评估人员的政企互动机制实验台。用户从中央政策协调视角设定制造业设备更新目标、财政边界和政策工具，观察中国大陆 31 个省级 Agent 如何依据稳定、可解释的实验决策画像形成地方政策和省际策略，再由每省六类企业群体 Agent 以参与、融资、技改、观望或拒绝验证地方政策的市场响应。

省级 Agent 是地方层面的主决策主体，企业 Agent 是市场反馈与政策验证层。这里的“省份拟人化”不是角色扮演或虚构现实政府性格，而是让每个省级 Agent 具有由冻结数据确定的目标、资源约束、政策偏好、行动历史和省际策略。系统不把大模型生成的数字当作政策结果；所有企业群体状态、省级指标、全国指标、网络效应和机制贡献均由确定性的 `ChinaPolicyEnv` 计算。

完整闭环为：

```text
国务院层面用户设定目标与约束
  → 中央政策研判 Agent 生成结构化政策草案
  → 用户审批
  → 冻结 31 个省级 Agent 的实验决策画像
  → 31 个省级 Agent 制定地方工具与省际策略
  → 186 个企业群体 Agent 用行动验证地方政策
  → 确定性环境计算企业、省级和全国结果
  → 省级 Agent 复盘企业信号并提出调整意向
  → 中央政策研判 Agent 提出干预建议
  → 用户审批或拒绝
  → 从同一 T3 检查点建立 Control / Treatment
  → T5 先比较省级策略迁移，再比较企业行为、地区差异与机制贡献
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

- 用省级决策画像和结构化省际策略表达地方异质性，而不是把 31 省做成同一模板。
- 用企业群体 Agent 验证地方政策在不同市场约束下的可达性。
- 用结构化 Action 代替无约束群聊。
- 用确定性环境公开计算机制结果。
- 用用户审批确保 AI 不能替代中央决策。
- 用同源 A/B 让政策工具调整具有可比较性。
- 用证据引用、版本和 Replay 说明每个结果从何而来。

### 2.3 一句话定义

> 让国务院层面的政策统筹人员在政策落地前，看见不同省份为何选择不同地方策略、企业如何反馈，以及政策调整在当前机制假设下带来的全国权衡。

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
3. 观察 31 个省级 Agent 的决策画像、地方政策和省际策略。
4. 进入任一省级 Agent 详情页，追溯目标、约束、行动历史和调整原因。
5. 查看六类企业群体对地方政策的行动反馈和机制贡献。
6. 识别中小企业融资可达性、区域差距和财政压力告警。
7. 审批或拒绝中央 Agent 提出的结构化干预。
8. 比较原始方案与干预方案的省级策略迁移、企业行为迁移、指标差和代价。
9. 查看数据质量、版本、父检查点、seed 和证据引用。

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
- 31 个稳定、可解释、可追溯的省级实验决策画像。
- 省级地方工具、目标企业群体、省际策略、T3 调整意向和 T4 行动谱系。
- 企业行为、省级结果、全国指标和机制贡献。
- 中国大陆 31 省级行政区地图与独立省级 Agent 详情页。
- 省级策略迁移、企业行动迁移、A/B 对照、证据抽屉和中央复盘。
- REST、SSE、Checkpoint、Replay、Cache 和 Fallback。
- 默认场景可离线、可重复演示。

### 4.2 明确不做

- 园区、投资机构、公众或消费者 Agent。
- 现实企业或单家企业数字孪生。
- 每省数百家微观企业的逐一模型调用。
- 自然语言政企群聊或省际自由群聊。
- 头像、第一人称台词或戏剧化角色扮演式“省份人格”。
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

系统共包含 32 个政府侧 Agent 和 186 个企业群体 Agent。省级 Agent 是地方主决策者；企业群体不是省级 Agent 的替代者，而是检验其政策选择能否穿透市场约束的反馈层。

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

- 读取中央政策、本省 Profile、冻结的 `ProvinceDecisionPersona`、当前 State、上一行动和 Top-K 省际网络。
- 在允许范围内选择主要目标、决策姿态、地方实施强度、政策工具结构、目标企业群体和技术方向。
- 从合作联动、对标跟进、竞争争取和独立推进中选择结构化省际策略。
- T3 阅读企业与环境证据，输出地方策略评价、主要约束、调整意向和中央支持请求，但不修改政策。
- T4 在两个分支中使用同一决策画像，基于各自政策、上一行动、T3 反馈和邻省上一阶段行动重新决策。
- 让每次行动可追溯到稳定目标、约束、输入版本和历史行动，而不是仅展示一张静态文案卡。

不得：

- 直接写入企业或省级结果指标。
- 生成现实金额、就业人数或生产率预测。
- 修改其他省份状态。
- 选择 Top-K 网络之外的目标省份。
- 在 T3 直接应用调整意向或改变 Checkpoint。
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

企业 Agent 是市场反馈和政策验证层，负责：

- 根据中央政策、地方政策和自身约束选择参与方式。
- 选择技改类型、融资方式、投入强度和支持请求。
- 输出结构化原因码和不超过 80 个汉字的摘要。

不得：

- 自行计算投资结果、生产率、就业、财政收益或最终指数。
- 创造不在 Action Schema 中的政策工具。
- 访问其他企业群体的私有状态。
- 以现实企业口吻发表立场。

企业行为不能覆盖或替代省级决策。全国页、干预页和 A/B 页必须先呈现省级策略，再用企业行为解释地方政策在市场侧的穿透结果。

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
| `instrument_mix.interest_subsidy` | 0–1 | 0.35 | 贷款贴息比例 |
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
| T0 | 中央政策与画像冻结 | 中央 Agent 生成草案，用户确认；环境按数据和网络版本确定性生成 31 个省级决策画像 | 目标解析、政策参数、决策画像版本、数据/机制/模型版本、审批状态 |
| T1 | 省级策略决策 | 31 个省级 Agent 依据画像、地方状态、中央政策和 Top-K 邻省信息生成地方行动 | 地方目标、决策姿态、政策工具、目标企业和省际策略 |
| T2 | 企业行为反馈 | 每省一次批量调用生成六类企业 Action，环境计算第一轮结果 | 企业行动矩阵、融资约束、机制指标和告警 |
| T3 | 省级复盘、中央研判与审批 | 31 个省级 Agent 阅读企业与环境证据，生成策略评价、调整意向和中央支持请求；冻结检查点后中央 Agent 提出干预 | 省级调整意向、结构化证据、参数 Diff、待验证方向、代价和人工审批 |
| T4 | 双分支省企再响应 | Control/Treatment 中省级 Agent 先依据同一画像重新决策，企业群体再按各自地方政策响应 | 两分支省级行动谱系、企业行动和状态谱系 |
| T5 | 省级策略对照与中央复盘 | 环境完成结算，先计算省级策略迁移，再计算企业迁移和全国结果，中央 Agent 生成复盘 | 省级执行双地图、策略迁移、企业行为迁移、指标差、机制归因和局限 |

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

### 8.1 ProvinceProfile v3

`province-profile-v3` 保留 V2 画像字段，并补充 `rd_capacity`、`employment_pressure` 和 `cooperation_tendency`。所有字段使用 0–1 标准化值并保留来源、年份、转换方法和质量类别。LLM 不得生成或修改 Profile。

### 8.2 ProvinceDecisionPersona

`province-persona-v1` 是省级 Agent 在一个实验及其所有分支中稳定不变的决策画像。它由冻结的 31 省 Profile 和 Top-K 网络确定性生成，不增加模型调用。

| 轴 | 机器字段 | 原始分数公式 |
|---|---|---|
| 执行驱动力 | `execution_drive` | `0.35×fiscal_capacity + 0.25×advanced_manufacturing_base + 0.20×digital_infrastructure + 0.20×economic_scale` |
| 财政审慎度 | `fiscal_prudence` | `0.70×fiscal_conservatism + 0.30×(1−fiscal_capacity)` |
| SME 普惠倾向 | `sme_inclusiveness` | `0.40×sme_density + 0.35×(1−credit_access) + 0.25×employment_pressure` |
| 技术跃迁倾向 | `technology_ambition` | `0.40×advanced_manufacturing_base + 0.35×digital_infrastructure + 0.25×rd_capacity` |
| 绿色转型倾向 | `green_priority` | `0.50×transition_pressure + 0.30×green_energy_base + 0.20×(1−industrial_diversity)` |
| 区域协同倾向 | `cooperation_orientation` | `0.70×cooperation_tendency + 0.30×Top-K网络平均权重` |

生成规则：

- 六项原始分数分别转换为 31 省百分位，范围为 0–1；并列值使用平均排名。
- 最高轴决定 `primary_type`：`execution_driven`、`fiscally_prudent`、`inclusive_diffusion`、`technology_leap`、`green_transition`、`regional_collaboration`。
- 并列优先级固定为绿色转型、普惠扩散、技术跃迁、区域协同、财政审慎、执行攻坚。
- 第二高轴与主轴相差不超过 0.10 时写入 `secondary_type`，否则为空。
- `priority_goals` 按主类型、辅助类型顺序映射并去重：执行攻坚→设备更新，财政审慎→财政可持续，普惠扩散→SME 融资可达，技术跃迁→数字化升级，绿色转型→绿色设备更新，区域协同→跨区域协同；最终为 1–2 项。
- 六个约束分数固定为：财政不足=`1−fiscal_capacity`，融资不足=`1−credit_access`，转型压力=`transition_pressure`，数字基础薄弱=`1−digital_infrastructure`，就业压力=`employment_pressure`，产业单一=`1−industrial_diversity`。按分数降序选取最高两项；完全并列时按上述顺序决胜。
- `data_quality`：源 Profile 为 `demo` 时取 `demo`，其余统一取 `proxy`；用户可见标签固定为“本次实验决策画像”。
- 河南、广东、山西的验收主类型分别为普惠扩散型、技术跃迁型和绿色转型型，但不得硬编码最终结果或现实政府特征。

至少包含：

```text
province_code
axes                           six fields, each 0–1
primary_type
secondary_type                optional
priority_goals                1–2 enum values
key_constraints               exactly 2 enum values
profile_version
network_version
method_version
data_quality                  proxy | demo
public_summary                ≤ 80 汉字
```

### 8.3 ProvinceAction v3

`province-action-v3` 至少包含：

```text
action_id
previous_action_id            T1 可为空，T4 必填
province_code
phase                         T1 | T4
primary_goal
decision_posture              proactive | balanced | cautious
target_enterprise_groups      1–3 个不同企业类型
interprovincial_strategy      collaborate | benchmark | compete | independent
target_province_codes         0–2 个省份
implementation_intensity      0–1
local_match_ratio             0–1
instrument_mix                sum = 1
sme_preference                0–1
regional_delivery_focus       0–1
technology_mix                sum = 1
requested_central_support     0–1
reason_codes
public_summary                ≤ 80 汉字
run_mode
fallback_used
```

约束：

- `collaborate`、`benchmark`、`compete` 必须选择 1–2 个当前 Top-K 网络中的省份。
- `independent` 的 `target_province_codes` 必须为空。
- T4 使用与 T1 相同的 `ProvinceDecisionPersona`，并引用上一 Action。
- Action 只表达策略，不包含结果指标。

### 8.4 ProvinceFeedback v3

`province-feedback-v3` 仅在 T3 产生，至少包含：

```text
feedback_id
province_code
phase                         T3
strategy_assessment           effective | mixed | constrained
enterprise_signals            0–6 个结构化群体信号
priority_enterprise_groups    1–3 个不同企业类型
key_constraints               1–3 个约束枚举
adjustment_intents            0–3 项
requested_support_type        none | fiscal_space | credit_support
                               | guarantee_capacity | technical_service
                               | regional_coordination
requested_central_support     0–1
reason_codes
evidence_refs
public_summary                ≤ 80 汉字
run_mode
fallback_used
```

每个 `enterprise_signal` 使用 `{cohort_type, signal_type, severity, evidence_refs}`；`signal_type` 仅允许 `participation_barrier | financing_constraint | upgrade_mismatch | support_demand`，`severity` 仅允许 `low | medium | high`，不得携带结果指标。

每个 `adjustment_intent` 使用 `{path, direction, reason_code}`，其中 `direction` 仅允许 `increase | decrease | hold`；`path` 只允许 `implementation_intensity`、`local_match_ratio`、`instrument_mix.direct_subsidy`、`instrument_mix.interest_subsidy`、`instrument_mix.financing_guarantee`、`sme_preference`、`regional_delivery_focus`、`technology_mix.digital`、`technology_mix.green`、`technology_mix.general`。T3 只记录意向，不修改 Policy、ProvinceAction、WorldState 或父 Checkpoint。

`requested_central_support=0` 时 `requested_support_type` 必须为 `none`；强度大于 0 时类型不得为 `none`。

### 8.5 EnterpriseGroupProfile

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

### 8.6 EnterpriseAction

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

### 8.7 ProvinceState

至少包含：

- 企业参与指数。
- 设备更新意愿指数。
- SME 融资可达性指数。
- 产业升级指数。
- 就业稳定指数。
- 地方财政压力指数。
- 最近一次省级 Action ID。

### 8.8 EnterpriseGroupState

至少包含：

- 参与准备度。
- 融资可达性。
- 设备更新准备度。
- 数字化水平指数。
- 绿色转型水平指数。
- 就业稳定指数。
- 最近一次 EnterpriseAction ID。

### 8.9 NationalMetrics

P0 固定六项：

1. 企业参与指数。
2. 设备更新意愿指数。
3. SME 融资可达性指数。
4. 产业升级指数。
5. 地方财政压力指数。
6. 区域差距指数。

所有指标为 0–100 内部指数。A/B 显示“指数点变化”，不显示现实百分比。

### 8.10 WorldState

WorldState 是前端、Replay 和 Compare 的权威投影视图，至少包含：

```text
experiment / branch / checkpoint IDs
phase / status / run_mode
policy / directive
province_profiles / province_personas / province_states
province_actions / province_action_lineage / province_feedback
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

V2.1 运行时投影视图升级为 `world-state-v3`。决策画像在 T0 冻结并被 Control/Treatment 共享；省级行动谱系按分支隔离。企业与中央 Policy Schema 继续使用 V2。

### 8.11 ComparisonResult

`comparison-v3` 至少包含，且页面与 DTO 顺序先省级、后企业：

- 政策参数 Diff。
- 全国六项指标的 Control、Treatment 和 delta。
- 31 省指标差。
- 省级主要目标、决策姿态、地方工具、目标企业群体和省际策略迁移。
- 每个省级 Action 的 Control/Treatment 来源、上一 Action 和同源父检查点。
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
- 生成省级政策 Action，输入必须包含冻结决策画像、上一行动和 Top-K 网络摘要。
- 按省批量生成六类企业 Action。
- 生成 T3 `ProvinceFeedback` 和调整意向。
- 生成中央干预建议。
- 生成中央复盘。

`ProvinceDecisionPersona` 不经过 LLMProvider，必须由版本化确定性规则生成。省级 Action/Feedback 首次 Schema 失败允许修复一次，再失败时该省进入可见 deterministic fallback；不得丢省或跳过 T3 反馈。

企业批量输出规则：

1. 首次输出必须通过 Schema 和六类完整性校验。
2. 首次失败允许携带结构化错误修复一次。
3. 第二次失败整省进入 deterministic fallback。
4. Fallback 必须进入 WorldState、SSE 和 Replay。
5. 单省失败不得阻断其他省份。

缓存键必须包含所有影响输出的字段：Policy、Profile、Persona、State、上一行动、Top-K 网络摘要、企业反馈、Prompt 版本、模型、机制版本、分支、阶段和 seed。

默认比赛场景必须预生成完整缓存。不得把现场演示完全押在模型网络调用上。

Live 开发模式默认使用 DeepSeek OpenAI 兼容接口：中央、省级和企业模型必须可分别配置，当前均为 `deepseek-v4-flash`；超时 60 秒，并发上限 8，最大输出 4096 tokens。结构化调用使用 JSON Object 输出并显式关闭 thinking。这一配置不改变比赛默认 Cache 与 Fake 测试策略。

---

## 11. 信息架构与核心页面

正式前端采用五个路由和一个可深链证据抽屉：

```text
/experiments/new
/experiments/:id/live
/experiments/:id/provinces/:provinceCode
/experiments/:id/intervention
/experiments/:id/compare

?evidence=<evidence-ref>
```

V2 已交付的 `?province=41` 继续作为兼容深链，但必须导航至 `/experiments/:id/provinces/41`；它不再承载正式省级详情体验。

省级详情页允许 `?branch=control|treatment`：从 Live 进入时省略并使用当前活动分支；从 Compare 进入时必须显式传入分支，缺省按 `control` 处理。切换分支必须更新 URL，并可与 `?evidence=` 共存。

### 11.1 中央政策设定

- 用户目标输入。
- 中央 Agent 结构化解析。
- 完整政策参数编辑。
- 数据、机制、Prompt、模型和 seed。
- Draft、待审批和已审批状态。
- “确认中央政策并开始推演”主操作。

### 11.2 全国实时推演

- 真实 31 省矢量地图。
- 默认地图指标为地方执行强度，不再以企业参与指数作为默认层。
- 地图分为省级策略指标组和企业/环境结果指标组。
- 全国六项机制指标。
- T0–T5 时间轴。
- 省级决策优先的行动流，企业反馈和环境事件作为后续层。
- 省级姿态数量、主要目标分布、省际策略分布和中央支持请求摘要。
- 运行、阶段完成、fallback 和错误状态。
- 点击省份进入独立省级 Agent 详情页。

### 11.3 省级 Agent 详情页

必须回答：

- 该省在本次实验中的主/辅助决策类型和六项决策轴是什么。
- 它优先追求什么目标，受哪些资源约束。
- 省级 Agent 选择了什么决策姿态、地方工具和目标企业群体。
- 它选择合作、对标、竞争还是独立推进，目标省份与理由是什么。
- T3 看到哪些企业和环境信号，提出了什么调整意向与中央支持请求。
- T1 与各 T4 分支的行动如何变化，变化可追溯到哪次上一行动。
- 六类企业分别如何反馈该地方政策，环境如何把行动转换成指标。
- 当前 Profile、Persona、网络、数据质量和证据来源是什么。

页面信息顺序固定为：实验决策画像 → 目标与约束 → 当前地方决策 → 省际策略 → T3 调整意向 → 行动时间线 → 企业反馈证据 → 机制结果。

### 11.4 T3 干预审批

固定三栏：

```text
结构化证据 → AI 建议 → 人类审批
```

必须显示：

- 省级目标分布、中央支持请求、调整意向与省际策略聚类。
- 企业行为和环境指标作为省级复盘的结构化证据。
- 问题摘要但不预设“必须干预”。
- 参数 `from → to` Diff。
- 目标指标、待验证方向和可能代价。
- 父检查点、seed、数据和机制版本。
- 批准、修改和拒绝。
- “只有批准才创建 Treatment”的说明。

### 11.5 A/B 对照

- 同步 Control / Treatment 地图。
- 默认比较地方执行强度，首先展示省级目标、姿态、地方工具、目标企业和省际策略迁移。
- 政策 Diff 和公平性声明。
- 全国六项指标差。
- 企业行为迁移作为第二层结果。
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
GET  /api/experiments/{id}/provinces/{province_code}
GET  /api/experiments/{id}/stream
POST /api/experiments/{id}/interventions/{proposal_id}/approve
POST /api/experiments/{id}/branches
POST /api/branches/{id}/run
GET  /api/experiments/{id}/compare
GET  /api/experiments/{id}/replay
GET  /api/experiments/{id}/audit
GET  /api/experiments/{id}/audit/{record_id}
GET  /api/experiments/{id}/evidence/{evidence_id}
GET  /api/meta/provinces
GET  /api/meta/province-persona-types
GET  /api/meta/enterprise-archetypes
```

V2.1 将省级、World、Comparison 和 Event DTO 升级到 V3；`PolicySchema`、中央政策对象和企业领域对象继续使用 V2。创建实验、运行阶段和创建分支必须幂等或接受幂等键。

省级详情接口返回 `ProvinceAgentDetail`，至少包含 Profile、Persona、当前 State、按分支排列的 Action lineage、T3 Feedback、六类企业反馈摘要、机制贡献和 evidence refs。接口中的 `province_code` 必须是 31 省元数据中存在的代码。

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

`event-v3` 保持统一 Envelope 和恢复语义，新增或升级以下事实事件：

```text
province.persona.ready
province.decision.started
province.decision.completed
province.decision.fallback
province.adjustment_intent.completed
province.strategy.changed
enterprise.batch.started
enterprise.decision.completed
enterprise.decision.fallback
enterprise.aggregate.updated
province.feedback.completed
```

事件 ID 单调、支持 `Last-Event-ID`、客户端去重。SSE 只通知事实，完整状态通过 WorldState 获取。

### 12.3 Replay 与审计记录

- `replay.jsonl` 保持现有 `SimulationEvent[]` 事实流，供 SSE 恢复、前端去重、趋势和事件面板使用。
- `audit.jsonl` 为独立 append-only 记录，不取代 WorldState、Checkpoint 或 Replay。
- `audit-record-v1` 包含单调 sequence、实验/分支/阶段、主体、父记录、前一记录哈希和当前 SHA-256 哈希。并发调用必须使用实验级写锁。
- `agent-invocation-trace-v1` 记录规范化输入及哈希、实际角色模型、Prompt/Schema 版本、延迟、token usage、最多两次校验摘要、结构化输出及哈希、run mode、fallback 与输出对象 ID。
- `mechanism-explanation-v1` 记录公式 ID/版本、来源对象、输入与系数、逐项贡献、原值、未裁剪值、裁剪调整、最终值和守恒残差。
- `decision-gate-trace-v1` 记录两次人工审批、Checkpoint、Control/Treatment 派生、政策差异和分支隔离证明。
- 完成/fallback 事件在 payload 中附带 `audit_record_id`。Evidence 解析器支持 `audit:`、`action:`、`mechanism:`、`metric:`、`checkpoint:` 和 `comparison:`；未知 ID 返回稳定 404。
- 中央对照复盘必须在输入中获得可引用的 `comparison:` Evidence Ref 白名单。若结构合法但语义引用越界，当次复盘转为确定性 fallback，Compare 仍完成；审计只保存错误路径、无效输出哈希和 fallback 原因。
- 全部字段递归脱敏 `api_key`、Authorization、token、secret 和 `reasoning_content`。校验失败只保存错误码、字段路径和无效响应哈希，不保存原始无效响应、API Key 或模型长思维链。

---

## 13. 数据要求

### 13.1 省级数据

中国大陆 31 个省级行政区进入计算。港澳台不进入本次仿真，并在方法抽屉明确说明。

`province-profile-v3` 至少包含：

- 经济规模、财政能力、产业多样性和先进制造基础。
- 数字基础设施、绿色能源基础和绿色转型压力。
- SME 密度代理、信贷可达性和财政审慎度。
- 研发能力、就业压力和省际合作倾向。

Profile 和 Top-K 网络在 T0 生成 `province-persona-v1`。公式、百分位方法、并列优先级和类型映射必须进入版本化配置或纯函数，不得散落在 Prompt、前端或缓存文件中。Persona 的 provenance 必须引用 Profile、Network 和 method version。

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
- 单次 Live 模型调用默认超时 60 秒。
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
- 环境每次状态更新必须同时生成可反算的企业、省级和全国机制解释；守恒失败、NaN/Infinity 或越界时立即失败。

---

## 16. P0 验收标准

| 编号 | Given | When | Then |
|---|---|---|---|
| AC-01 | 用户输入设备更新目标 | 生成中央政策 | 返回合法 V2 指令，用户批准前不进入 T1 |
| AC-02 | 中央政策已批准 | 运行 T1 | 31/31 省拥有稳定 Persona，并产生合法 `province-action-v3` 或显式 fallback |
| AC-03 | T2 开始 | 企业批量决策 | 31 省各有且只有六类企业 Action |
| AC-04 | 企业输出非法 | 修复仍失败 | 整省使用 deterministic fallback，并在 UI/SSE/Replay 标记 |
| AC-05 | 用户点击河南 | 进入省级 Agent 详情 | 依次显示普惠扩散型画像、目标约束、地方决策、省际策略、行动历史和企业反馈 |
| AC-06 | T3 完成 | 省级与中央 Agent 研判 | 31 省均产生不修改政策的调整意向；中央页显示省级证据、参数 Diff、待验证方向和代价 |
| AC-07 | 干预未审批 | 请求创建分支 | API 明确拒绝，不改变 WorldState |
| AC-08 | 干预已审批 | 创建 Treatment | Control/Treatment 共享同一不可变父检查点 |
| AC-09 | T5 完成 | 打开 A/B | 先显示地方执行双地图和省级策略迁移，再显示企业迁移、六项指标、地区差和机制归因 |
| AC-10 | 查看中央复盘 | 点击证据 | 每条结论跳转到 Compare JSON 中存在的事实 |
| AC-11 | SSE 断线 | 带 Last-Event-ID 重连 | 不重复应用已处理状态 |
| AC-12 | 打开任一结果页 | 页面完成加载 | 可见机制实验免责声明和数据质量标签 |
| AC-13 | 查看河南/广东/山西 | 读取决策画像 | 主类型依次为普惠扩散型、技术跃迁型、绿色转型型，且均标注为实验画像 |
| AC-14 | 省级 Agent 选择省际目标 | 校验 Action | 非独立策略只允许 1–2 个 Top-K 省份；独立推进的目标列表为空 |
| AC-15 | T4 两分支完成 | 查看省级行动谱系 | 每个 T4 Action 引用上一行动，Persona 与父 T3 Checkpoint 保持一致 |

### 16.1 Demo Ready 产品定义

- 默认场景、固定 seed 和完整缓存准备就绪。
- 无网络可完成主流程。
- 31×6 企业群体完整。
- 31 个省级决策画像稳定、可追溯，三省重点验收类型正确。
- T3 调整意向不改变 Policy、行动或父 Checkpoint。
- 未审批路径和 fallback 路径已验证。
- Control/Treatment 分支隔离已验证。
- 五路由在 1440×900 完成 V2.1 Stitch 视觉 QA。
- 连续完成 3 次端到端运行。
- 不包含现实金额预测、现实百分比预测或“最优政策”结论。

---

## 17. 风险与砍项顺序

| 风险 | 应对 |
|---|---|
| 企业批量模型输出不完整 | 强 Schema、一次修复、整省 fallback、预生成缓存 |
| 省级与企业调用数量过多 | 分省批量企业调用、受控并发、默认 Cache |
| 企业行为同质化 | 六类 Profile、原因码、河南/广东/山西纵向测试 |
| 省份拟人化沦为标签或角色扮演 | 确定性六轴画像、目标/约束、行动谱系和结构化省际策略共同验收 |
| 省级 Agent 被企业卡片淹没 | Live、Intervention、Compare 和省级详情统一使用省级优先信息层级 |
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
- 31 个稳定决策画像、省际策略和 T3 调整意向。
- 独立省级 Agent 详情页及省级策略迁移。
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
- 31 个省级 Agent 在产品中表现出可解释、可追溯的目标、约束和策略差异。
- 企业反馈清楚服务于地方政策验证，而不是取代省级决策主线。
- 企业用行动而非聊天表达政策响应。
- 评委能在河南、广东和山西快速识别三种不同的实验决策逻辑。
- T5 能先解释省级策略如何迁移，再解释企业行为和环境结果如何变化。
- 至少能解释一个传统 SME 从 `wait` 转为 `conditional/participate` 的机制链。
- AI 在策略选择中发挥必要作用，结果计算仍由确定性环境承担。
- 用户审批是实际 API 门禁，不是前端装饰。
- 同源 A/B 能同时展示收益和代价。
- 产品视觉、内容和交互在 1440×900 下完整统一。
- 评委可以辨认数据质量、方法边界和持续扩展价值。

---

## 19. 文档门禁状态

V2 PRD 已获得用户批准并完成代码、测试、数据、API 和 React 前端迁移；V1 回滚点保留在 Git 提交 `12456a3`。

本次 V2.1 已将产品主线升级为“省级 Agent 主决策、企业 Agent 作市场反馈”。Schema、数据快照、Provider、仿真编排、API/SSE、默认 Cache 清单与五路由前端已实现；但最终 E2E、连续三次 Cache 和 Design QA **尚未完成**，不得提前声明 V2.1 验收通过。

当前冻结文档组为：

- `DEVELOPMENT_PLAN.md`
- `AGENTS.md`
- `STITCH_FRONTEND_SPEC.md`
- `README.md` 中的交付与运行说明

V2 产品 QA 结论继续有效，但不得用于声明 V2.1 已通过。根据用户确认的比赛发布规则，比赛版地图无额外合规审核门禁，可直接随 Web 产品上线；来源、审图号、省域绑定和几何校验记录继续保留。
