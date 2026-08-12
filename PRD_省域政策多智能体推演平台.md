# PolicyScope / 政策涟漪 PRD

> 产品副标题：新能源汽车补贴与产业布局多智能体推演台
> 文档版本：V3.0（已实现并通过 P0 验收）
> 更新日期：2026-08-12
> 当前状态：V3.0 公共契约、三级 Agent、确定性环境、年度同源 A/B、API、缓存与地图前端均已接通并完成 M20 验收

---

## 1. 执行摘要

PolicyScope V3.0 是一套面向中央层面政策制定、统筹与评估人员的新能源汽车补贴与产业空间布局机制实验台。核心研究问题是：

> 当中央调整汽车以旧换新补贴中西部、中部、东部的中央承担比例后，各省会如何调整消费端、固定成本和可变成本补贴，真实头部车企的模拟 Agent 又会如何调整销售投入与建厂/扩产选择，最终省际新能源汽车发展差距会扩大还是缩小？

V3.0 的主体链为：

```text
中央层面用户
  → 中央政策研判 Agent
  → 31 个省级 Agent
  → 10 家代表性真实头部车企 Agent
  → 确定性新能源汽车政策环境
```

中央改变制度约束，省级 Agent 在财政空间内自主配置地方工具，车企 Agent 比较 31 省政策 Offer、消费者需求、供应链距离和经营约束后做出模拟市场投入及产能布局选择。大模型只生成结构化策略；需求、财政、成本、投资、产业活动和区域差距均由确定性环境计算。

每个政策周期为一年。完整实验由“首年基线 + 年末一次人工干预 + 次年同源 A/B”组成：

```text
SETUP：中央设定三档承担比例并批准
  → Y1_Q1：31 省形成地方补贴策略
  → Y1_Q2：10 家车企形成全国销售与产能布局策略
  → Y1_Q3：环境传播需求、成本、供应链和财政影响
  → Y1_Q4：年度结算，省级复盘并冻结不可变检查点
  → YEAR1_REVIEW：中央 Agent 提议一次比例调整，用户批准/修改/拒绝
  → Y2_Q1–Y2_Q4：同一首年检查点派生原始方案/干预方案
  → COMPLETE：比较 ΔGap、财政代价、需求与产业空间变化
```

产品不预测现实车企未来销量、利润、投资金额、工厂选址或政策必然结果。真实企业数据只作为冻结基线；未来状态统一显示模拟指数、等级和相对变化。

---

## 2. 产品使命与核心问题

### 2.1 唯一核心用户

核心用户是中央层面的政策制定、财政统筹、产业协调与政策评估人员。用户本人不是仿真主体，始终拥有：

- 初始政策批准权。
- 首年年末干预的批准、修改和拒绝权。
- 是否创建干预方案的决定权。
- 对数据、版本、公式、Checkpoint 和局限的查阅权。

中央政策研判 Agent 是用户的决策支持助手，不代表现实中央机构，也不能自动发布或调整现实政策。

### 2.2 核心政策问题

默认参考政策为 2025 年汽车以旧换新资金分担口径：

| 地区档位 | 中央承担比例 | 地方承担比例 |
|---|---:|---:|
| 西部 | 95% | 5% |
| 中部 | 90% | 10% |
| 东部 | 85% | 15% |

用户可按绝对值输入新比例，也可基于默认值输入百分点调整。三个比例相互独立，不要求求和，不强制满足“西部 ≥ 中部 ≥ 东部”；偏离参考排序时系统必须警告，但允许作为机制实验继续。

系统要帮助用户回答：

1. 中央承担比例改变后，地方财政空间如何变化。
2. 各省如何在消费端、固定成本和可变成本补贴之间重新配置。
3. 车企为何在不同省份增加或减少销售投入。
4. 哪些省份更可能获得模拟建厂或扩产活动。
5. 固定成本补贴和可变成本补贴在何种规模或时间下发生效果反转。
6. 区域差距缩小是否伴随中央负担、地方压力或产业效率代价。

### 2.3 产品边界

PolicyScope 是机制实验与政策研判工具，不是现实宏观预测、招商推荐或企业选址系统。所有关键结果页固定显示：

> 研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。

---

## 3. V3.0 P0 范围

### 3.0 V3 契约快照

- 默认政策：西部 95%、中部 90%、东部 85%。
- 阶段：`SETUP → Y1_Q1 → Y1_Q2 → Y1_Q3 → Y1_Q4 → YEAR1_REVIEW → Y2_Q1 → Y2_Q2 → Y2_Q3 → Y2_Q4 → COMPLETE`。
- 十家车企：比亚迪、吉利、长安、上汽通用五菱、蔚来、奇瑞、零跑、赛力斯、小米汽车、理想汽车。
- 六项指标：区域发展差距、中央财政负担、地方财政压力、新能源汽车需求、新增投资集中度、产业集聚度。
- 版本：`policy-v3`、`province-profile-v4`、`province-persona-v2`、`province-action-v4`、`province-feedback-v4`、`automaker-profile-v1`、`automaker-action-v1`、`world-state-v4`、`comparison-v4`、`event-v4`。
- 路由：`/experiments/new`、`/experiments/:id/live`、`/experiments/:id/provinces/:provinceCode`、`/experiments/:id/intervention`、`/experiments/:id/compare`。

### 3.1 必须完成

- 1 个中央政策研判 Agent。
- 31 个省级政策 Agent。
- 10 家代表性真实头部车企的模拟 Agent。
- 1 个新能源汽车消费补贴与产业布局政策域。
- 西部/中部/东部三档中央承担比例。
- 省级消费端、固定成本、可变成本三类地方工具。
- 车企销售/渠道投入和建厂/扩产两类核心行为。
- 电池产业空间分布和省级新能源汽车 WTP 两类关键外生变量。
- 首年基线、年末一次人工干预、次年同源 A/B。
- ΔGap、财政负担、需求、投资集中度和产业集聚度。
- Checkpoint、Replay、Audit、Cache、Fallback 和 Evidence 深链。
- 中国大陆 31 个省级行政区离线矢量地图和地图图层切换。
- 五个正式路由、省级详情页和车企深链侧栏。

### 3.2 明确不做

- 消费者个人 Agent、经销商、城市、园区、银行或电池企业 Agent。
- 真实车企内部组织、董事会或单个车型数字孪生。
- 自由形式中央—地方—企业群聊。
- 省际自由合作、产业联盟或复杂招商博弈。
- 自动参数网格搜索、强化学习或“现实最优比例”求解。
- 现实销量、收入、利润、投资金额、财政金额和工厂落地预测。
- 未经许可的企业 Logo、商标资产或第一人称企业台词。
- 多次随机实验、置信区间和概率预测。
- P0 移动端、3D 地图和复杂飞线动画。

---

## 4. 主体与职责边界

### 4.1 中央政策研判 Agent

负责：

- `SETUP`：把用户目标转换为结构化 `CentralSubsidyDirective`。
- `YEAR1_REVIEW`：读取首年结构化结果，提出一个三档比例调整方案。
- `COMPLETE`：读取同源 A/B 结果并生成结构化复盘。
- 为建议与复盘提供可解析 Evidence Ref。

不得：

- 绕过用户审批发布政策或创建干预方案。
- 修改 WorldState、Checkpoint 或环境指标。
- 声称找到现实最优比例。
- 创造 Comparison 中不存在的数字。
- 把“待验证方向”写成已发生效果。

### 4.2 31 个省级 Agent

省级 Agent 的核心问题是：

> 中央承担比例改变了本省地方配套负担后，剩余财政空间应如何在消费端、固定成本和可变成本支持之间配置？

负责：

- 读取中央政策、本省冻结 Profile、稳定 Persona、地方财政空间、WTP、电池供应链距离和 Peer Policy 摘要。
- 选择地方支持强度及三类补贴份额。
- 从 `follow`、`differentiate`、`hold` 中选择 Peer 响应模式。
- 在首年年末读取车企与环境证据，生成复盘和下一年度调整意向，但不直接应用。
- 在次年两个分支中基于同一 Persona 和同一首年检查点重新决策。

不得：

- 写入最终需求、财政、投资、产业或 Gap 指标。
- 超过环境计算的地方财政上限。
- 修改其他省份状态。
- 在首年复盘阶段直接修改政策或检查点。
- 把车企投资或观望行为描述为省级政府决定。
- 代表现实省级政府发表立场。

### 4.3 10 家真实头部车企模拟 Agent

P0 固定名单如下；这是用户选定的代表性主体集合，不宣称严格等同于任一年度销量 Top 10：

| ID | 展示名 |
|---|---|
| `byd` | 比亚迪 |
| `geely` | 吉利 |
| `changan` | 长安 |
| `sgmw` | 上汽通用五菱 |
| `nio` | 蔚来 |
| `chery` | 奇瑞 |
| `leapmotor` | 零跑 |
| `seres` | 赛力斯 |
| `xiaomi_auto` | 小米汽车 |
| `li_auto` | 理想汽车 |

每个车企 Agent 是一个全国性主体，不按省复制为 310 个主体。每年一次结构化调用完整返回：

- 31 省销售/渠道投入强度组合。
- 0–3 个产能布局目标，动作仅允许 `new_plant`、`expand`、`delay`。
- 未列入产能目标的省份默认 `hold`。
- 原因码、风险等级、模拟 ROI 等级和最多 80 个汉字的公开摘要。

车企 Agent 读取公开数据派生的冻结经营画像、现有生产与渠道布局、各省 Offer、WTP、供应链距离和自身上一年度状态。

不得：

- 代表现实企业承诺投资、建厂或扩大销售。
- 输出未来现实销量、利润、收入、投资金额或具体工厂地址。
- 直接计算或修改省级、全国或分支结果。
- 使用未经许可的企业 Logo 或长思维链。

### 4.4 确定性新能源汽车政策环境

环境是结果状态转移的唯一权威，负责：

- 央地资金分担与地方财政空间。
- 消费补贴对 WTP 和需求的传导。
- 固定成本补贴对进入/扩产门槛的影响。
- 可变成本补贴对长期经营成本的影响。
- 电池供应链距离对物流成本的影响。
- 企业经营状态、ROI 和投资组合约束。
- 季度状态传播、年度结算和机制贡献。
- 省级发展指数、Gini、HHI 和六项中央指标。

相同输入、版本和 seed 必须得到相同结果。所有指标必须防止 NaN/Infinity，并裁剪到契约范围。

---

## 5. 地区档位与中央政策

### 5.1 三档省份

V3 使用汽车以旧换新财政分配口径，不使用国家统计局“东中西东北四大区域”口径：

| 档位 | 省份 | 数量 |
|---|---|---:|
| 东部 | 北京、天津、辽宁、上海、江苏、浙江、福建、山东、广东 | 9 |
| 中部 | 河北、山西、吉林、黑龙江、安徽、江西、河南、湖北、湖南、海南 | 10 |
| 西部 | 内蒙古、广西、重庆、四川、贵州、云南、西藏、陕西、甘肃、青海、宁夏、新疆 | 12 |

三档必须完整覆盖中国大陆 31 个省级行政区且不得重复。新疆生产建设兵团不作为额外省级 Agent。

### 5.2 `policy-v3`

核心字段：

```text
schema_version                  policy-v3
reference_policy_year           2025
input_mode                      absolute | delta
west_central_share              0–1, default 0.95
central_central_share           0–1, default 0.90
east_central_share              0–1, default 0.85
consumer_subsidy_standard_version
eligibility_rule_version
primary_goal                    reduce_regional_gap
status                          draft | awaiting_approval | approved
```

规则：

- 三项比例独立校验，不求和。
- `delta` 表示相对参考值的百分点调整；持久化时同时保存最终绝对值和原始调整。
- 非单调排序只产生明确警告，不阻断实验。
- 同一次 A/B 中，消费补贴资格规则和补贴标准保持不变。
- 干预方案唯一允许主动改变的字段是三档中央承担比例。

### 5.3 财政传导

中央承担比例只直接作用于消费端汽车以旧换新共担资金。环境先计算地方所需配套负担，再计算地方可用于自主政策的财政空间。省级 Agent 只能在该空间内配置消费端追加支持、固定成本支持和可变成本支持。

提高中央承担比例不是“免费增加补贴”：系统必须同步记录中央财政负担上升、地方配套负担下降及由此产生的地方策略变化。

---

## 6. 省级画像与行动

### 6.1 `province-profile-v4`

至少包含：

- 财政能力与财政刚性。
- 新能源汽车产业基础。
- 当前整车、零部件与研发活动基础。
- 消费市场规模与新能源汽车 WTP。
- 土地、人才、能源和物流成本代理。
- 电池供应链距离与可达性。
- 充电基础设施和城市化代理。
- 历史汽车消费与新能源渗透代理。
- Peer Group 归属与相似度。
- 每个字段的来源、年份、单位、转换和质量类别。

### 6.2 `province-persona-v2`

Persona 由冻结 Profile 与 Peer Network 确定性生成，不经过 LLM，在首年及所有次年分支中稳定。六项轴为：

1. 财政承载力。
2. 产业招商倾向。
3. 消费激活倾向。
4. 运营成本竞争力。
5. 供应链协同能力。
6. Peer 响应敏感度。

用户可见名称固定为“本次实验省级决策画像”，不得称为现实省份性格。

### 6.3 `province-action-v4`

```text
action_id
previous_action_id
province_code
phase                           Y1_Q1 | Y2_Q1
overall_support_intensity       0–1
subsidy_mix.consumer            0–1
subsidy_mix.fixed_cost          0–1
subsidy_mix.variable_cost       0–1
peer_response_mode              follow | differentiate | hold
observed_peer_codes             0–3
reason_codes
public_summary                  ≤ 80 汉字
run_mode
fallback_used
```

三类 `subsidy_mix` 之和必须为 1，不得静默归一化。`observed_peer_codes` 只能来自冻结 Peer Group。Action 只表达策略，不包含结果指标。

### 6.4 `province-feedback-v4`

在 `Y1_Q4` 产生，包含：

- 地方策略评价。
- 需求、车企销售投入和产能布局信号。
- 财政约束与主要机制阻力。
- 最多三项下一年度调整意向。
- 对中央三档比例的结构化建议。
- Evidence Ref、原因码和公开摘要。

Feedback 只记录复盘，不修改 Policy、Action、WorldState 或首年 Checkpoint。

---

## 7. 车企画像与行动

### 7.1 `automaker-profile-v1`

每家车企至少包含：

```text
automaker_id
display_name
baseline_year                  2025
sales_scale_index
sales_growth_index
profitability_index
liquidity_index
capacity_utilization_index
channel_coverage_by_province
production_footprint
product_segment_mix
technology_route_mix
expansion_posture              expansion | disciplined | defensive
data_quality                   verified | proxy
provenance
```

真实销量、财报和工厂资料只作为基线输入。不同企业和集团口径不完全一致时必须标记 `proxy` 并记录转换，不得伪造可比精度。缺少关键数据时不得用无来源 `demo` 值冒充真实企业事实。

### 7.2 `automaker-action-v1`

```text
action_id
previous_action_id
automaker_id
phase                           Y1_Q2 | Y2_Q2
province_market_actions[31]
  province_code
  sales_investment_intensity    0–1
  channel_strategy              expand | maintain | reduce
facility_actions                0–3
  province_code
  action                        new_plant | expand | delay
  investment_intensity          0–1
simulated_roi_band              low | medium | high
reason_codes
public_summary                  ≤ 80 汉字
run_mode
fallback_used
```

每个 Action 必须恰好覆盖 31 个不同省份的市场投入条目；产能布局目标最多三个。环境而非车企 Agent 计算投资、成本、需求和产业结果。

### 7.3 调用与失败处理

- 首年车企调用：10 次，每家一次。
- 次年双分支：20 次，每家每分支一次。
- 完整实验共 30 次车企调用。
- 第一次 Schema 失败可修复一次；再次失败时该车企整次全国组合进入确定性 fallback。
- Fallback 必须进入 WorldState、Event、Replay 和 Audit，不能伪装为 Live 决策。

---

## 8. 外生变量与 Peer Network

### 8.1 电池产业空间分布

冻结快照记录主要电池产业节点、节点能力代理、来源年份和省际距离矩阵。环境使用：

```text
battery_distance
  → logistics_cost_index
  → variable_cost_index
  → automaker_roi_index
```

地图节点只是数据可视化，不代表企业未来供应合同。

### 8.2 新能源汽车 WTP

每省 `willingness_to_pay_index` 为 0–1 代理指数，可综合新能源渗透、乘用车消费、收入、城镇化、充电基础设施和历史增长。所有组成字段必须保留 provenance 和转换方式。

### 8.3 Peer Provinces

Peer Network 依据经济体量、汽车产业结构、财政能力和市场需求相似度确定性生成 Top-K 相似省份。MVP 只允许观察、跟进、差异化或维持，不实现合作资金池、联盟或自由对话。

---

## 9. 时间机制、审批与同源 A/B

### 9.1 阶段枚举

V3 正式阶段为：

```text
SETUP
Y1_Q1
Y1_Q2
Y1_Q3
Y1_Q4
YEAR1_REVIEW
Y2_Q1
Y2_Q2
Y2_Q3
Y2_Q4
COMPLETE
```

V3 用户界面、API 和持久化对象不得继续用 T0–T5 表达当前主流程。V2/V2.1 历史说明可保留旧阶段名。

### 9.2 首年基线

- `SETUP`：中央 Agent 生成指令，用户批准后才能进入首年。
- `Y1_Q1`：31 个省级 Agent 生成地方行动。
- `Y1_Q2`：10 个车企 Agent 生成全国行动组合。
- `Y1_Q3`：环境传播需求、成本、供应链、财政和 Peer 效应。
- `Y1_Q4`：环境年度结算，31 省生成 Feedback，冻结不可变首年 Checkpoint。

### 9.3 年末干预

中央 Agent 在 `YEAR1_REVIEW` 读取首年结构化证据，提出一次三档比例调整。用户可以：

- 批准原建议。
- 修改三个比例后批准。
- 拒绝建议。

每个实验最多批准一次年末干预。未经批准不得创建干预方案。

### 9.4 次年分支

- 原始方案和干预方案必须来自同一不可变首年 Checkpoint。
- 原始方案保留首年中央承担比例。
- 干预方案只采用用户批准的三档比例。
- Profile、Persona、真实数据快照、机制版本、Prompt/模型版本和 seed 规则保持一致。
- 创建干预方案不得修改原始方案。
- 拒绝干预时只运行次年原始方案，不伪造 A/B。

### 9.5 调用预算

- 中央 Agent：3 次，分别位于 `SETUP`、`YEAR1_REVIEW`、`COMPLETE`。
- 省级 Agent：首年行动 31 次、首年复盘 31 次、次年双分支行动 62 次，共约 124 次。
- 车企 Agent：首年 10 次、次年双分支 20 次，共 30 次。
- Persona、环境计算、UI 刷新和地图切换不增加模型调用。

---

## 10. 指标与公式

### 10.1 省级发展指数

每省新能源汽车发展指数为：

```text
province_nev_development_index
  = 0.50 × demand_index
  + 0.50 × industry_activity_index
```

两个分项和合成结果均为 0–100 模拟指数。

### 10.2 区域发展差距

`Gap` 使用 31 省等权发展指数的 Gini，并归一到 0–100。所有省份指数完全相同时 Gap 为 0；输入非有限值时必须失败。

核心 A/B 比较为：

```text
ΔGap = Gap_treatment,Y2 − Gap_control,Y2
```

- `ΔGap < 0`：干预方案下省际差距缩小。
- `ΔGap > 0`：干预方案下省际差距扩大。
- `ΔGap ≈ 0`：在显示精度和机制阈值内影响有限。

### 10.3 六项中央指标

1. 区域发展差距指数。
2. 中央财政负担指数。
3. 地方财政压力指数。
4. 新能源汽车需求指数。
5. 新增投资集中度指数。
6. 产业集聚度指数。

全国需求按冻结的省级市场权重聚合；Gap 仍按省份等权计算，二者不得混用。

### 10.4 HHI

新增投资集中度和产业集聚度使用 31 省份额的归一化 HHI：

```text
normalized_hhi
  = ((Σ share_i² − 1/31) / (1 − 1/31)) × 100
```

新增投资集中度使用本期新增销售与产能投入分布；产业集聚度使用期末产业活动存量分布。

### 10.5 固定/可变成本临界点

环境分别计算一次性固定成本支持效果和随经营规模累积的可变成本支持效果：

```text
fixed_effect = fixed_support × entry_cost_sensitivity
variable_effect(q) = variable_support × cumulative_operating_scale(q)
```

临界点是 `variable_effect` 首次达到或超过 `fixed_effect` 的季度或规模指数。输出只使用季度、规模指数和机制贡献，不输出未来现实产量或金额。

### 10.6 表达规则

- 结果使用“指数/100”和“指数点变化”。
- 三档中央承担比例和三类工具份额可使用百分比。
- 不显示现实销量、收入、利润、投资金额和财政金额预测。
- 不显示显著性、概率或置信区间，除非后续版本真实定义并计算。

---

## 11. 环境机制与解释

每次状态更新至少生成以下机制贡献：

```text
central_share_relief
local_fiscal_constraint
consumer_subsidy_effect
fixed_cost_entry_effect
variable_cost_operating_effect
wtp_demand_effect
battery_logistics_effect
peer_policy_effect
automaker_financial_constraint
channel_investment_effect
facility_investment_effect
concentration_adjustment
```

机制贡献来自计算过程，不允许由 LLM 事后猜测。每个指标必须记录公式 ID、版本、输入、系数、未裁剪值、裁剪调整、最终值和守恒残差。

---

## 12. Provider、缓存与 Fallback

所有模型调用统一经过：

```text
LiveLLMProvider
CachedLLMProvider
FakeLLMProvider
```

缓存键必须覆盖所有影响输出的输入：Policy、Profile、Persona、上一行动、Peer 摘要、31 省 Offer、公司经营快照、数据/机制/Prompt/Schema/模型/app 版本、阶段、分支和 seed。

默认比赛场景必须有完整结构化缓存。Live 不得阻塞交付。任何 fallback 都必须显示主体、阶段、分支、原因和替代规则范围。

---

## 13. World、Comparison 与公共接口

### 13.1 版本

V3 目标契约固定为：

```text
policy-v3
province-profile-v4
province-persona-v2
province-action-v4
province-feedback-v4
automaker-profile-v1
automaker-action-v1
world-state-v4
comparison-v4
event-v4
```

现有 `audit-record-v1` 信封继续使用；新能源汽车公式使用新的版本化机制 ID。新旧契约不得静默混用。

### 13.2 `world-state-v4`

至少包含：

- 实验、分支、阶段、状态和审批。
- 初始政策、年末建议和获批干预。
- 31 省 Profile、Persona、Action、Feedback 和状态。
- 10 家车企 Profile、Action、行动谱系和状态。
- WTP、电池节点、Peer Network 和数据质量。
- 六项中央指标、省级发展指数和机制贡献。
- 数据、机制、Prompt、模型、Schema、app 版本和 seed。

已提交状态不可原地修改；分支拥有独立行动和状态谱系。

### 13.3 `comparison-v4`

首先返回：

- 三档中央承担比例 Diff。
- 同源首年 Checkpoint 证明。
- Control/Treatment 的 Gap 和 `ΔGap`。
- 六项中央指标的原始值、干预值和指数点差。

随后返回：

- 31 省三类补贴迁移。
- 31 省发展指数和财政压力变化。
- 10 家车企的销售投入迁移。
- 建厂、扩产、延迟和维持现状迁移。
- 投资集中度、产业集聚度和固定/可变成本临界点变化。
- 机制归因、重点受益/承压地区、中央复盘和 Evidence Ref。

### 13.4 REST

保留现有实验、审批、运行、分支、Compare、Replay、Audit 和 Evidence 资源路径，新增：

```text
GET /api/experiments/{id}/automakers/{automaker_id}
GET /api/meta/automakers
GET /api/meta/policy-regions
```

省级详情接口升级为 V3 语义。非法阶段转换返回 409，未审批操作返回 403 或稳定领域错误。

### 13.5 SSE

`event-v4` 至少覆盖：

```text
policy.directive.completed
policy.directive.approved
province.decision.started
province.decision.completed
province.decision.fallback
automaker.portfolio.started
automaker.portfolio.completed
automaker.portfolio.fallback
environment.quarter.completed
province.review.completed
checkpoint.year1.created
intervention.proposed
intervention.approved
branch.created
comparison.completed
```

Event ID 单调，支持 `Last-Event-ID`、去重和断线恢复。SSE 只通知事实，完整状态由 WorldState 获取。

### 13.6 Replay、Checkpoint、Audit 与 Evidence

- Checkpoint 用于首年冻结、恢复和分支。
- Replay 是 append-only 事实事件流，用于 SSE 恢复和时间线。
- Audit 是详细行为、机制和审批追溯，继续使用哈希链。
- Evidence 新增 `automaker:` 强类型引用，并继续支持 `audit:`、`action:`、`mechanism:`、`metric:`、`checkpoint:` 和 `comparison:`。
- 不保存 API Key、访问令牌、原始无效响应、`reasoning_content` 或模型长思维链。

---

## 14. 信息架构与页面

正式路由继续为：

```text
/experiments/new
/experiments/:id/live
/experiments/:id/provinces/:provinceCode
/experiments/:id/intervention
/experiments/:id/compare
```

深链参数：

```text
?company=<automaker-id>
?evidence=<evidence-ref>
?branch=control|treatment
```

### 14.1 中央政策设定

- 显示西部/中部/东部默认承担比例和省份清单。
- 支持绝对值与百分点调整两种输入模式。
- 非单调排序显示警告但允许批准。
- 显示政策参考年份、资格规则、补贴标准和实验边界。

### 14.2 全国 Live 地图

中国地图是主画布，默认图层为地方新能源汽车补贴支持强度。可切换：

- 消费端、固定成本、可变成本补贴。
- 消费者 WTP。
- 新能源产业基础和电池节点。
- 车企销售投入。
- 模拟建厂与扩产活动。

地图旁显示当前季度、中央三档比例、关键事件和六项中央指标摘要。任何图层切换都不得触发模型调用。

### 14.3 省级详情

信息顺序固定为：

```text
地方财政空间
  → 三类补贴配置
  → 本次实验省级决策画像
  → Peer Policy 响应
  → 10 家车企反馈
  → 需求、投资和机制结果
```

### 14.4 车企侧栏

`?company=` 展示冻结经营画像、数据质量、31 省销售投入组合、0–3 个产能目标、上一行动、模拟 ROI 等级和免责声明。企业名称可用文本展示，P0 不使用未经许可 Logo。

### 14.5 年末干预审批

保持“结构化证据 → 中央 Agent 建议 → 人工审批”三栏，Diff 只包含三档中央承担比例。明确说明只有批准后才能从首年 Checkpoint 创建干预方案。

### 14.6 次年 A/B

使用同几何、同指标、同色阶双地图。首先展示三档比例 Diff、同源证明、Gap 和 `ΔGap`，再展示财政、需求、投资、产业集聚、省级工具迁移和车企行为迁移。

---

## 15. 数据与来源

### 15.1 政策来源

- 默认 95%/90%/85% 来自[国家发展改革委 2025 年“两新”政策通知](https://zfxxgk.ndrc.gov.cn/web/iteminfo.jsp?id=20470)。
- 三档省份采用[财政部 2024 年汽车以旧换新补贴中央财政预拨资金表](https://www.ndrc.gov.cn/xwdt/ztzl/tddgmsbgxhxfpyjhx/gzdt/202406/t20240606_1386714.html)中的汽车专项分区。
- 文档必须称其为“2025 年政策参考基线”，不得暗示永久有效或等同于 2026 年现行政策。

### 15.2 省级数据

每个字段记录来源机构、URL、年份、单位、原值、转换、缺失处理和 `verified/proxy/demo`。31 省 WTP、产业基础、电池距离、财政能力和 Peer Network 必须通过完整性验证。

### 15.3 真实车企数据

优先使用企业年报、公告、官方销量、乘联分会/中汽协公开统计和可复核的政府资料。必须明确集团、品牌、合资公司和上市主体口径。真实名称不等于真实决策，任何模拟 Action 均标记“模拟”。

### 15.4 地图

继续使用经过来源、31 省绑定和几何签名校验的离线矢量地图。电池节点和车企活动是数据覆盖层，不修改行政区边界。

---

## 16. 非功能要求

- 相同输入、版本和 seed 产生相同结果。
- 单省或单车企失败不阻断其他主体，但阶段只有在完整合法或显式 fallback 后提交。
- Cache 模式必须离线跑完完整两年实验。
- SSE 重连不得重复应用事件。
- 地图更新不触发 Agent 调用。
- 所有真实主体、政策参考和结果均可追溯来源。
- 页面不得出现现实官方身份暗示、企业承诺或“最优政策”结论。

---

## 17. P0 验收标准

| 编号 | Given | When | Then |
|---|---|---|---|
| AC-01 | 用户打开新实验 | 查看默认政策 | 显示西/中/东 95%/90%/85% 和 2025 参考口径 |
| AC-02 | 用户输入任意 0–100% 比例 | 校验政策 | 独立接受三项值；非单调仅警告，不静默修改 |
| AC-03 | 初始政策未审批 | 请求首年运行 | API 明确拒绝 |
| AC-04 | 首年 Q1 完成 | 检查省级行动 | 31 省均有合法三类补贴组合或显式 fallback，份额和为 1 |
| AC-05 | 首年 Q2 完成 | 检查车企行动 | 10 家车企均覆盖 31 省市场行动，产能目标不超过 3 个 |
| AC-06 | 首年 Q4 完成 | 冻结状态 | 生成不可变首年 Checkpoint 和 31 省复盘 |
| AC-07 | 干预未批准 | 请求创建 Treatment | 服务层拒绝且不改变 Control |
| AC-08 | 干预已批准 | 创建双分支 | 两分支共享同一首年 Checkpoint，唯一主动差异为三档比例 |
| AC-09 | 次年完成 | 打开 Compare | 首先显示同源证明、Gap、ΔGap 和六项中央指标 |
| AC-10 | 查看车企活动 | 打开 `?company=` | 显示真实基线来源与明确模拟决策免责声明 |
| AC-11 | 查看固定/可变成本机制 | 打开 Evidence | 显示临界季度/规模指数和环境公式，不显示现实投资金额 |
| AC-12 | SSE 断线重连 | 携带 Last-Event-ID | 不重复应用事件并重新获取 WorldState |
| AC-13 | 任一主体进入 fallback | 查看状态和 Replay | 主体、阶段、分支、原因和规则接管范围均可见 |
| AC-14 | 查看三档元数据 | 验证完整性 | 东部 9、中部 10、西部 12，完整覆盖 31 省无重复 |
| AC-15 | 查看最终复盘 | 阅读结论 | 不出现现实最优比例、企业承诺或未来金额/销量预测 |

---

## 18. 风险与砍项顺序

| 风险 | 应对 |
|---|---|
| 真实企业数据口径不一致 | 冻结主体定义、逐字段 provenance、缺失项标 proxy |
| 真实名称导致模拟被误读 | 全站模拟标签、禁止第一人称和企业承诺、P0 不用 Logo |
| 产业布局机制过度复杂 | P0 只保留销售投入与 0–3 个产能目标 |
| 固定/可变成本缺乏可解释性 | 由环境输出显式临界季度/规模和贡献链 |
| 中央比例被误解为覆盖全部补贴 | 明确只直接作用消费端共担，再间接改变地方财政空间 |
| 两年流程过长 | 完整 Cache、季度聚合、结构化批量输出 |
| A/B 被随机性污染 | 同一首年 Checkpoint、版本和 seed 规则 |

时间不足时依次砍掉：高级地图动画、复杂排行、多种干预候选、车企细分筛选、Live 展示。不得砍掉三档比例、31 省、10 家车企、三类省级工具、两类企业行为、首年 Checkpoint、人工审批、同源 A/B、ΔGap、Cache/Fallback 和免责声明。

---

## 19. 文档与实现门禁

V2 已完成历史验收；V2.1 代码主体曾实现但最终验证未完成，现作为被 V3.0 取代的历史基线保留。用户于 2026-08-12 批准本契约并要求完成 V3.0 开发；M13–M20 现已完成，V3.0 进入冻结维护。

当前迁移必须遵守：

- 公共契约先于 Agent、环境、API 和前端迁移。
- V2.1 历史 DTO 不得通过字段别名或 UI 映射伪装成 V3。
- 只有实际实现并通过相应检查的里程碑可以标记完成。
- 后续只有在实现和验收证据同步更新时，才允许改变本冻结契约或扩展 P0 范围。
