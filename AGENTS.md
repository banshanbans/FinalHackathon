# AGENTS.md

本文件适用于当前目录及全部子目录，用于约束参与 PolicyScope V3.0 的 Codex、自动化开发 Agent 和人工开发者。

---

## 1. 当前阶段与工作门禁

PolicyScope V3.0 将目标产品迁移为：

> 面向中央层面政策统筹人员的“新能源汽车补贴与产业布局多智能体推演台”。

当前事实：

- V2 制造业设备更新产品已完成历史验收；V1 回滚基线保留在 Git 提交 `12456a3`。
- V2.1 的省级 Persona、V3 省级 DTO、审计链、五路由 React 前端已实现，但最终 E2E、连续三次 Cache 和新版 Design QA 未完成。
- V3.0 已取代 V2.1 成为目标产品主线；V3 把企业层改为 10 家真实头部车企模拟 Agent，把时间改为首年季度、年末干预和次年同源 A/B。
- 用户已于 2026-08-12 明确要求完成 V3.0 开发，产品契约已批准，代码迁移门禁解除。
- V3 领域契约、数据、三级 Agent、确定性环境、两年 Orchestrator、API/SSE、缓存和五路由前端已实现。
- M20 已完成全量测试、两条 Playwright E2E、连续三次 157/157 Cache 命中和三画布 Design QA；V3.0 当前为冻结维护状态。

如果用户后续明确改变门禁，以用户最新要求为准，并在同一变更中同步所有受影响文档。

---

## 2. 开始工作前的必读顺序

任何实现、重构、评审或测试开始前，必须依次完整阅读：

1. `AGENTS.md`
2. `PRD_省域政策多智能体推演平台.md`
3. `DEVELOPMENT_PLAN.md`
4. 与任务直接相关的 Schema、代码、测试和局部文档

涉及前端、地图、可视化、文案或交互时，还必须完整阅读：

5. `STITCH_FRONTEND_SPEC.md`
6. `stitch_policyscope/policyscope/DESIGN.md`
7. 与目标页面对应的 Stitch `screen.png`

不得只看 Stitch `code.html` 就开始实现。V2/V2.1 旧文档、代码和截图只能作为历史或视觉结构参考，不能覆盖 V3 已冻结语义。

---

## 3. 来源优先级

发生冲突时按以下顺序：

1. V3 PRD：产品语义、用户权限、主体、阶段、指标和验收。
2. 获批后的 V3 Schema/API：运行时数据真相。
3. `STITCH_FRONTEND_SPEC.md`：正式页面结构、交互、文案和状态。
4. `DESIGN.md` 与 Stitch `screen.png`：视觉令牌和布局参考。
5. Stitch `code.html`：仅用于测量，不是正式代码。
6. V2/V2.1 实现：迁移基线，不是 V3 契约来源。

实施顺序和任务状态以 `DEVELOPMENT_PLAN.md` 为准。V3 代码与冻结契约发生不一致时必须作为回归处理，不得静默退回 V2/V2.1 语义。

---

## 4. 项目使命与用户边界

核心用户是中央层面的政策制定、财政统筹、产业协调和政策评估人员。用户是最终政策操作者，不是仿真主体。

```text
用户设定西部/中部/东部中央承担比例
  → 中央政策研判 Agent 生成结构化指令
  → 用户批准
  → 首年 Q1：31 省配置三类地方补贴
  → 首年 Q2：10 家车企模拟 Agent 形成全国行动组合
  → 首年 Q3：确定性环境传播
  → 首年 Q4：结算、31 省复盘、冻结 Checkpoint
  → 中央 Agent 提议一次干预
  → 用户批准、修改或拒绝
  → 同一首年 Checkpoint 派生次年原始/干预方案
  → 次年完成后比较 ΔGap、财政、需求和产业布局
```

产品是机制实验和协同研判工具，不代表现实中央、地方政府或真实企业的立场，不提供现实招商或投资建议。

所有关键页面固定显示：

> 研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。

---

## 5. P0 主体与职责边界

### 5.1 中央政策研判 Agent

中央 Agent 必须真实参与并输出结构化对象：

- `SETUP`：`CentralSubsidyDirective`。
- `YEAR1_REVIEW`：`CentralInterventionProposal`。
- `COMPLETE`：`CentralReview`。

中央 Agent 只能建议：

- 不能直接写 WorldState。
- 不能绕过用户审批发布初始政策或创建干预方案。
- 不能创造 Comparison 中不存在的数字。
- 不能把预期方向当作已验证结果。
- 不能声称找到现实最优比例。
- 输出必须经过 Schema 校验、版本记录、证据引用、Cache/Fallback、Replay 和 Audit。

### 5.2 31 个省级 Agent

省级 Agent 是地方政策配置主体。每省拥有由 Profile 和 Peer Network 确定性生成、跨首年和次年分支稳定的 `ProvinceDecisionPersona`。

省级 Agent 负责：

- 在环境给定财政空间内选择总体支持强度。
- 配置消费端、固定成本、可变成本三类补贴份额。
- 观察冻结 Peer Group 的政策摘要。
- 选择 `follow`、`differentiate` 或 `hold` Peer 响应。
- 首年 Q4 复盘需求、车企和环境信号并提出调整意向。
- 次年在同一 Persona 下按分支政策重新决策。

不得：

- 计算或写入最终需求、财政、投资、产业、Gap 或 HHI。
- 超过环境给定的地方财政上限。
- 修改其他省份状态。
- 观察 Peer Group 之外的未授权私有状态。
- 在首年复盘直接应用调整意向。
- 把车企销售、建厂、扩产或延迟行为描述成省级政府决定。
- 代表现实地方政府发表立场。

### 5.3 10 家真实头部车企模拟 Agent

固定主体与 ID：

1. `byd`：比亚迪。
2. `geely`：吉利。
3. `changan`：长安。
4. `sgmw`：上汽通用五菱。
5. `nio`：蔚来。
6. `chery`：奇瑞。
7. `leapmotor`：零跑。
8. `seres`：赛力斯。
9. `xiaomi_auto`：小米汽车。
10. `li_auto`：理想汽车。

该名单是用户选定的代表性集合，不得写成严格销量 Top 10。

每家车企是一个全国性 Agent，不按省复制。每年一次调用必须完整返回：

- 31 省销售/渠道投入强度和渠道策略。
- 最多 3 个建厂、扩产或延迟投资目标。
- 未列入目标的省份默认为维持现状。
- 模拟 ROI 等级、原因码和不超过 80 个汉字的公开摘要。

不得：

- 冒充现实企业或使用第一人称承诺。
- 输出未来现实销量、利润、收入、投资金额、工厂地址或财政金额。
- 直接计算或修改省级、全国或分支结果。
- 使用未经许可的企业 Logo。
- 展示或保存模型长思维链。

### 5.4 确定性新能源汽车政策环境

环境是结果状态转移与机制贡献的唯一权威：

- 计算央地分担、地方配套负担和剩余财政空间。
- 计算消费补贴、WTP 和车企销售投入的需求影响。
- 计算固定成本补贴的进入/扩产效果。
- 计算可变成本补贴、人才/能源/物流和电池距离的经营效果。
- 计算固定/可变成本补贴临界季度或规模指数。
- 计算企业 ROI、季度状态、年度结果、Gini、HHI 和机制贡献。
- 相同输入、版本和 seed 必须得到相同结果。
- 指标必须防 NaN/Infinity，并 clamp 到约定范围。

LLM 只做策略选择，不得返回最终指标再由环境包装。

### 5.5 审批与同源分支

- 初始指令未经批准不得运行 `Y1_Q1`。
- 首年年末建议未经批准不得创建 Treatment。
- 用户可批准、修改或拒绝中央建议。
- 每个实验最多批准一次年末干预。
- Control/Treatment 必须从同一不可变首年 Checkpoint 派生。
- Treatment 创建不得改变 Control。
- 唯一主动差异是获批的西部/中部/东部中央承担比例。
- 拒绝后只运行次年 Control，不伪造 A/B。
- API 和服务层必须复核审批，不能只依赖前端。

### 5.6 Cache 与 Fallback

- 默认新能源汽车场景必须有完整预生成缓存。
- 不允许把比赛现场运行完全押在模型网络调用上。
- Fallback 必须展示主体、阶段、分支、原因和接管范围。
- Cache key 必须包含所有影响输出的输入和版本。

---

## 6. V3.0 P0 范围

### 6.0 V3 契约快照

- 默认政策：西部 95%、中部 90%、东部 85%。
- 阶段：`SETUP → Y1_Q1 → Y1_Q2 → Y1_Q3 → Y1_Q4 → YEAR1_REVIEW → Y2_Q1 → Y2_Q2 → Y2_Q3 → Y2_Q4 → COMPLETE`。
- 十家车企：比亚迪、吉利、长安、上汽通用五菱、蔚来、奇瑞、零跑、赛力斯、小米汽车、理想汽车。
- 六项指标：区域发展差距、中央财政负担、地方财政压力、新能源汽车需求、新增投资集中度、产业集聚度。
- 版本：`policy-v3`、`province-profile-v4`、`province-persona-v2`、`province-action-v4`、`province-feedback-v4`、`automaker-profile-v1`、`automaker-action-v1`、`world-state-v4`、`comparison-v4`、`event-v4`。
- 路由：`/experiments/new`、`/experiments/:id/live`、`/experiments/:id/provinces/:provinceCode`、`/experiments/:id/intervention`、`/experiments/:id/compare`。

必须做：

- 1 个中央 Agent、31 个省级 Agent、10 个真实车企模拟 Agent。
- 西部/中部/东部三档比例，默认 95%/90%/85%。
- 省级消费端、固定成本、可变成本三类工具。
- 车企销售投入与建厂/扩产两类行为。
- 省级 WTP、电池产业节点和 Peer Network。
- 首年基线、年末一次审批、次年同源 A/B。
- 31 省发展指数、归一化 Gini、六项中央指标和归一化 HHI。
- 五个路由、车企侧栏、Evidence 抽屉和地图图层。
- REST、SSE、Checkpoint、Replay、Audit、Cache 和 Fallback。
- 经来源和几何校验的离线 31 省地图。

暂不做：

- 消费者、经销商、电池企业、银行、园区、城市或部门 Agent。
- 真实车型级决策和单个工厂选址预测。
- 省际自由合作、联盟和群聊。
- 自动参数搜索或现实最优比例。
- 现实销量、利润、投资额、财政额和概率预测。
- 未经许可的企业 Logo。
- 移动端、3D 地图和复杂动画。

范围膨胀时按 `DEVELOPMENT_PLAN.md` 的砍项顺序保护主闭环。

---

## 7. 阶段规则

严格保持：

```text
SETUP
  → Y1_Q1
  → Y1_Q2
  → Y1_Q3
  → Y1_Q4
  → YEAR1_REVIEW
  → Y2_Q1
  → Y2_Q2
  → Y2_Q3
  → Y2_Q4
  → COMPLETE
```

具体规则：

- `SETUP`：中央生成和用户批准初始政策。
- `Y1_Q1`：31 省生成三类地方工具。
- `Y1_Q2`：10 家车企生成全国行动组合。
- `Y1_Q3`：环境传播，不新增 Agent 调用。
- `Y1_Q4`：环境结算，31 省生成 Feedback，冻结 Checkpoint。
- `YEAR1_REVIEW`：中央建议和人工审批。
- `Y2_Q1`：Control/Treatment 中 31 省分别重新决策。
- `Y2_Q2`：Control/Treatment 中 10 家车企分别重新决策。
- `Y2_Q3`：环境传播。
- `Y2_Q4`：环境年度结算。
- `COMPLETE`：生成 Comparison 和中央复盘。

V3 活动契约、API、UI 和持久化对象不得继续使用 T0–T5。历史说明可以保留旧阶段名，但必须明确属于 V2/V2.1。

完整调用预算固定为：

- 中央 3 次。
- 省级约 124 次：31 首年行动 + 31 首年复盘 + 62 次年双分支行动。
- 车企 30 次：10 首年 + 20 次年双分支。
- Persona、环境、地图和 UI 刷新不增加模型调用。

---

## 8. 中央政策与地区档位

### 8.1 `policy-v3`

- `reference_policy_year=2025`。
- `input_mode=absolute|delta`。
- `west_central_share`：0–1，默认 0.95。
- `central_central_share`：0–1，默认 0.90。
- `east_central_share`：0–1，默认 0.85。
- 三项独立，不求和。
- 非单调只警告，不自动修复或归一化。
- 持久化同时保存最终绝对值和相对参考值的 Diff。

### 8.2 三档省份

使用汽车以旧换新财政分配口径：

- 东部 9：北京、天津、辽宁、上海、江苏、浙江、福建、山东、广东。
- 中部 10：河北、山西、吉林、黑龙江、安徽、江西、河南、湖北、湖南、海南。
- 西部 12：内蒙古、广西、重庆、四川、贵州、云南、西藏、陕西、甘肃、青海、宁夏、新疆。

必须完整覆盖 31 省且无重复。新疆生产建设兵团不作为额外省级 Agent。不得使用国家统计局四大区域名单替换本政策专项口径。

### 8.3 传导边界

中央承担比例只直接作用消费端汽车以旧换新共担资金。环境先计算地方配套负担，再计算地方自主财政空间。省级 Agent 才能在该空间内配置三类地方工具。

---

## 9. 领域模型规则

### 9.1 强类型与版本

- Python 边界对象使用 Pydantic v2，TypeScript 使用严格类型。
- 核心路径禁止无约束 `dict[str, Any]` 和 `any`。
- 枚举使用稳定英文机器码，中文只用于展示。
- 可持久化对象包含 `schema_version`。
- ID 使用不透明字符串，时间戳使用 UTC ISO 8601。
- V3 目标版本固定为：

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

旧 V2/V2.1 DTO 不得静默转换为 V3。

### 9.2 省级 Persona

六轴：财政承载力、产业招商倾向、消费激活倾向、运营成本竞争力、供应链协同能力、Peer 响应敏感度。

Persona 必须：

- 由冻结 Profile 与 Peer Network 确定性生成。
- 在首年和次年所有分支中稳定。
- 不经过 LLM。
- 用户可见名固定为“本次实验省级决策画像”。
- 不解释为现实政府性格。

### 9.3 `province-action-v4`

必须包含：总体支持强度、三类补贴份额、Peer 响应模式、观察的 Peer、省份、原因码、摘要、上一 Action、模式和 fallback。

三类份额之和必须为 1，不合法时拒绝，不能静默归一化。观察省份只能来自冻结 Peer Group。

### 9.4 `automaker-profile-v1`

至少包含 2025 基线的销量规模/增速、盈利和流动性代理、产能利用、渠道覆盖、生产布局、产品与技术路线、扩张姿态、质量和 provenance。

真实车企关键字段只允许 `verified/proxy`。集团、品牌、合资公司和上市主体口径必须明确。

### 9.5 `automaker-action-v1`

每次必须：

- 恰好覆盖 31 个不同省份的市场投入条目。
- 每省包含 0–1 投入强度和 `expand|maintain|reduce`。
- 产能目标为 0–3 个，动作只允许 `new_plant|expand|delay`。
- 包含模拟 ROI 等级、原因码、摘要、run mode 和 fallback。
- 不包含最终结果指标。

### 9.6 World 与 Comparison

- `world-state-v4` 是前端和 Replay 的权威投影视图，提交后不得原地修改。
- Persona 与真实数据快照在同源分支共享；Action 和 State 谱系按分支隔离。
- `comparison-v4` 必须先显示三档比例、同源证明、Gap/ΔGap 和六项中央指标，再显示省级工具和车企行为迁移。

---

## 10. 指标与机制规则

### 10.1 省级发展指数

```text
province_nev_development_index
  = 0.50 × demand_index
  + 0.50 × industry_activity_index
```

### 10.2 Gap 与 ΔGap

- Gap 使用 31 省等权发展指数的归一化 Gini，范围 0–100。
- `ΔGap = Gap_treatment,Y2 − Gap_control,Y2`。
- ΔGap < 0 表示干预方案下差距缩小。

### 10.3 固定六项中央指标

1. 区域发展差距。
2. 中央财政负担。
3. 地方财政压力。
4. 新能源汽车需求。
5. 新增投资集中度。
6. 产业集聚度。

### 10.4 HHI

新增投资集中度和产业集聚度使用 31 省份额的归一化 HHI。不得由前端或 LLM 重算。

### 10.5 固定/可变成本临界点

环境计算可变成本累计效果首次达到固定成本一次性效果的季度或规模指数。结果使用季度和模拟规模指数，不输出未来现实产量或金额。

### 10.6 机制贡献

至少覆盖：

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

每次状态更新必须同时生成可反算机制解释。

---

## 11. 数据与真实主体规则

### 11.1 Provenance

每个字段记录：

- 来源机构和链接。
- 来源年份和获取日期。
- 原始单位和原值。
- 标准化或转换方法。
- 缺失值处理。
- `verified/proxy/demo` 质量类别。

质量类别不是置信度，不得显示伪百分比。

### 11.2 真实车企

- 优先企业年报、公告、官方销量、乘联分会/中汽协和政府资料。
- 必须区分集团、品牌、上市主体和合资公司口径。
- 真实名称只用于定义冻结模拟主体，不代表授权、背书或现实决策。
- P0 不使用未经许可 Logo。
- 缺少关键企业数据时标记 `proxy`，不得填充无来源 demo 并称为事实。

### 11.3 WTP 与电池节点

- WTP 是代理指数，不是现实支付意愿调查结论。
- 电池节点及能力、距离和来源必须冻结版本。
- LLM 不得运行时创造节点、企业工厂、Peer 边或真实销量。

### 11.4 数据验证

必须覆盖：

- 31 省唯一且齐全。
- 地区档位 9/10/12。
- 10 家车企唯一。
- 每家车企行动覆盖 31 省。
- WTP、电池、Peer 和 Profile 范围与 provenance。
- 地图范围与计算范围一致。

---

## 12. API、SSE、Replay、Checkpoint 与 Audit

### 12.1 REST

保留现有资源方向并新增：

```text
GET /api/experiments/{id}/automakers/{automaker_id}
GET /api/meta/automakers
GET /api/meta/policy-regions
```

创建实验、运行阶段和创建分支必须幂等或使用幂等键。非法阶段返回 409，未审批返回 403 或稳定领域错误。

### 12.2 SSE

`event-v4` 至少包含：

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

省级、车企、季度环境、Checkpoint、审批、分支和 Comparison 事件必须可区分。SSE 支持 Last-Event-ID、去重和断线恢复，只通知事实。

### 12.3 三类存储职责

- Checkpoint：首年恢复和分支。
- Replay：append-only 事实流、SSE 恢复和时间线。
- Audit：行为、机制和审批详细追溯，继续使用 `audit-record-v1` 哈希链。

不得混同三者。

### 12.4 Evidence

继续支持 `audit:`、`action:`、`mechanism:`、`metric:`、`checkpoint:`、`comparison:`，并新增 `automaker:`。未知 ID 返回稳定 404。

不得保存 API Key、Authorization、token、secret、原始无效响应、`reasoning_content` 或模型长思维链。

---

## 13. 前端强制规则

### 13.1 正式实现

- 品牌统一为“PolicyScope / 政策涟漪”。
- 保持浅色现代制度工作台、12 栅格、Inter + Noto Sans SC、蓝/青/靛语义色。
- 中国地图是主分析画布，不再以六张 KPI 卡作为页面主体。
- 正式前端继续使用 React、React Router、API hooks、SSE 和本地资源。
- 禁止 iframe 静态 HTML、运行时 CDN、截图地图和远程地图依赖。
- 图标使用本地资源，不用 emoji。

### 13.2 路由与深链

```text
/experiments/new
/experiments/:id/live
/experiments/:id/provinces/:provinceCode
/experiments/:id/intervention
/experiments/:id/compare

?company=<automaker-id>
?evidence=<evidence-ref>
?branch=control|treatment
```

### 13.3 地图图层

- 默认：地方新能源汽车补贴支持强度。
- 填色图层：消费端、固定成本、可变成本、WTP、产业基础。
- 覆盖图层：电池节点、车企销售活动、模拟建厂与扩产。
- 同一时刻只能有一个省域填色主图层。
- 图层切换不得触发模型调用。
- 图例显示指标、单位、季度和分支。

### 13.4 页面顺序

- New：三档比例与初始审批。
- Live：地图、季度、政策快照、事件和六指标摘要。
- Province：财政空间 → 三类补贴 → Persona → Peer → 车企反馈 → 机制。
- Company drawer：冻结画像 → 31 省投入 → 产能目标 → 数据与模拟边界。
- Intervention：证据 → 中央建议 → 人工审批。
- Compare：同源证明 → Gap/ΔGap → 六指标 → 省级/车企迁移。

### 13.5 表达底线

必须使用：

- “2025 年政策参考基线”。
- “模拟指数变化”。
- “待验证”。
- “原始方案 / 干预方案”。
- “本次实验省级决策画像”。
- “真实数据基线 / 模拟车企行动”。

禁止使用：

- “当前国家永久比例”。
- “现实最优比例 / 最佳方案 / 优化方案”。
- “某车企将建厂 / 承诺投资 / 决定扩产”。
- 未来现实销量、利润、投资额或财政金额。
- “国务院认为 / 某省政府决定”。
- 伪置信度和官方身份暗示。

---

## 14. Python 与 TypeScript 约定

### Python

- Python 3.11+，完整类型标注，Pydantic v2。
- 异步 I/O 使用 `async/await`，不阻塞事件循环。
- 环境计算优先纯函数或显式输入输出。
- 随机性通过 seed 注入，不使用模块级可变 WorldState。
- 不捕获宽泛异常后静默继续。

### TypeScript / React

- TypeScript strict，核心路径禁止 `any`。
- API 类型生成或严格同步。
- WorldState 不复制到多个不同步 store。
- 组件不直接 fetch，不重算 Gap、HHI 或环境结果。
- 所有页面和侧栏覆盖 loading、empty、error、fallback 和权限门禁。

---

## 15. 测试要求

### 15.1 领域与数据

- 三档默认值、范围、非单调警告和不求和。
- 地区档位 9/10/12 与 31 省完整性。
- 省级 Persona、Peer Network 和三类份额。
- 十家车企 ID、Profile 和 provenance。
- 每家车企每次覆盖 31 省，产能目标不超过 3。
- Schema 版本不得静默混用。

### 15.2 环境

- 央地分担和财政守恒。
- WTP、消费补贴、销售投入与需求贡献。
- 电池距离和物流成本。
- 固定/可变成本临界点。
- 50/50 省级发展指数。
- 等权 Gini、ΔGap 符号和归一化 HHI。
- 确定性、NaN/Infinity 和 clamp。

### 15.3 Agent 与 Provider

- 中央 3、省级约 124、车企 30 次预算。
- 合法输出、一次修复、再次失败 fallback。
- 车企全国组合的完整性。
- Cache key 完整输入和版本。
- 无现实预测、Schema 外字段和长思维链。

### 15.4 API、SSE 与分支

- 正常响应、非法阶段、未审批拒绝和错误码。
- 首年 Checkpoint 不可变。
- 每个实验最多一次获批干预。
- Control/Treatment 同源且唯一主动差异为三档比例。
- 拒绝路径不创建 Treatment。
- Last-Event-ID、去重、Replay、Audit 和 Evidence。

### 15.5 前端与 E2E

- 五路由和三类深链。
- 地图 31 省及所有图层。
- 车企侧栏明确模拟边界。
- 首年审批、年末三栏审批和次年双地图。
- Compare 首先显示 Gap、ΔGap 和同源证明。
- 禁止文案、未授权 Logo、现实金额和销量扫描。
- 1536×1024、1440×900、1280 无核心遮挡和水平滚动。

不得通过降低断言、跳过测试、硬编码结果或隐藏 fallback 让检查通过。

---

## 16. 开发工作流

接到实现任务时：

1. 确认 V3 文档是否已获用户批准。
2. 确认任务 ID、里程碑和依赖真实完成。
3. 阅读相关契约、代码、测试和视觉来源。
4. 检查工作树，保护用户和其他开发者的修改。
5. 先冻结共享 Schema，再更新测试和实现。
6. 运行与风险相称的最小完整检查。
7. 只有退出条件真实满足才更新计划状态。
8. 汇报改动、验证、剩余风险和唯一下一任务。

涉及主体数量或职责、阶段、Schema、审批、分支、指标或页面结构时，必须同步 PRD、计划、AGENTS 和前端规范。

并行开发时：

- 不同参与者认领不同文件或清晰边界。
- 公共 Schema 由单一负责人先冻结。
- 不同时大幅编辑同一文件。
- 共享接口变更必须在一个变更中更新调用方和契约测试。

---

## 17. 文件、安全与禁止捷径

- 保留 `.obsidian`、Stitch 原始文件、用户文档和 V2.1 代码。
- 不提交 `.env`、API Key、令牌或敏感材料。
- Runtime experiment、Replay 和大缓存默认忽略；默认演示缓存单独白名单。
- 不用破坏性 Git 命令覆盖用户修改。
- 未获批准前不升级依赖。

禁止：

- 用 V2.1 六类企业数据改名冒充十家真实车企。
- 把真实企业名称与无来源 demo 财务值组合成伪事实。
- 让 LLM 生成 Gap、HHI、销量、利润或投资额。
- 用两次独立实验冒充同源 A/B。
- 未审批自动应用年末建议。
- 缺省份或缺车企时静默继续。
- 在前端重算权威环境结果。
- 用截图、静态 HTML 或 CDN 冒充地图和正式前端。
- 在没有证据时宣称 V3 已实现、测试通过或 Design QA 通过。

---

## 18. 命令与完成定义

仓库统一命令继续为：

```bash
make setup
make dev
make dev-api
make dev-web
make test
make test-sim
make test-api
make lint
make validate-data
make demo
make smoke
```

V3 实现期间按里程碑运行与风险相称的检查；不得用局部通过结果宣称完整 V3 通过。V3 完成必须同时满足：

- 符合批准的 PRD 和职责边界。
- 相关测试存在并通过。
- 新数据带 provenance 和质量标签。
- Schema/API 变更更新所有调用方。
- 用户可见改动处理完整状态、单位和免责声明。
- 无新增秘密、无关修改或未追踪大文件。
- `DEVELOPMENT_PLAN.md` 对应退出条件真实满足。

---

## 19. 当前唯一下一步

保持 V3.0 P0 契约、缓存和 QA 证据冻结；只有用户批准新的产品范围、数据版本或机制版本后，才开始下一轮迁移。
