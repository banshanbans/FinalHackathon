# AGENTS.md

本文件适用于当前目录及全部子目录，用于约束参与 13110（代码与历史版本沿用 PolicyScope 命名）V3.2 的 Codex、自动化开发 Agent 和人工开发者。

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
- 用户已于 2026-08-12 批准 V3.1 事件驱动省际协同范围；V3.0 继续作为只读基线，V3.1 使用新 Schema、机制和缓存命名空间。
- 用户已于 2026-08-12 批准 V3.2 产品旅程与 Fake Agent 重构；用户粘贴的 V3.2 文本是最高产品契约，当前 React 实际页是视觉基线。
- V3.0/V3.1 数据、缓存和契约只读保留；V3.2 使用独立 v4/v5/v6 命名空间，禁止原地转换。
- 用户于 2026-08-13 重开 V3.2 验收并批准 M30 上下文驱动的省级 Agent 自主协作；旧 G1–G5 冻结结论撤销，必须完成 Luna 缓存、三类 E2E、全量命令和三画布 QA 后才能重新冻结。

如果用户后续明确改变门禁，以用户最新要求为准，并在同一变更中同步所有受影响文档。

---

## 2. 开始工作前的必读顺序

任何实现、重构、评审或测试开始前，必须依次完整阅读：

1. `AGENTS.md`
2. `PRD_省域政策多智能体推演平台.md`
3. `DEVELOPMENT_PLAN.md`
4. 与任务直接相关的 Schema、代码、测试和局部文档

涉及前端、地图、可视化、文案或交互时，还必须完整阅读：

5. `docs/specs/STITCH_FRONTEND_SPEC.md`
6. `stitch_policyscope/policyscope/DESIGN.md`
7. 与目标页面对应的 Stitch `screen.png`

不得只看 Stitch `code.html` 就开始实现。V2/V2.1 旧文档、代码和截图只能作为历史或视觉结构参考，不能覆盖 V3 已冻结语义。

---

## 3. 来源优先级

发生冲突时按以下顺序：

1. V3 PRD：产品语义、用户权限、主体、阶段、指标和验收。
2. 获批后的 V3 Schema/API：运行时数据真相。
3. `docs/specs/STITCH_FRONTEND_SPEC.md`：正式页面结构、交互、文案和状态。
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
- 本地 Web/API 启动固定使用 `fake` Mock Provider，不得调用线上模型。
- 公网演示默认使用 `cache` Provider：命中时直接回放结构化缓存；语义键缺失、哈希不符或输出无效时，使用部署环境已批准的 DeepSeek `live` Provider 补齐，通过 Schema/身份/资源校验后原子回写同一 Luna 缓存命名空间。
- `POLICYSCOPE_CACHE_MISS_MODE` 只能在服务端部署配置为 `fake|live`，客户端不得切换 Provider；模型密钥不进镜像、缓存、Replay、Audit 或前端。
- 不允许把比赛现场运行完全押在模型网络调用上。
- DeepSeek 超时、连接、Schema、身份或资源校验失败时才允许确定性 Fallback 接管，且必须展示主体、阶段、分支、原因和接管范围。
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

- 当前对外产品名统一为“13110”；`PolicyScope` 仅保留为代码包、历史文档和版本谱系标识，不得继续出现在 Presentation 主舞台品牌位。
- Presentation 省级画像的网络标签统一使用“本次实验同伴网络”；地球大气外圈统一使用与 2D 中国地图相同的 PolicyScope 青色 `#63d5c7`。
- Presentation 连续时间轴支持方向键操控：右/下推进，左/上回退；前半段单次步长 `0.05`，后半段 `0.1`；必须沿用现有 GSAP 平滑进度，不得硬切章节。
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

#### 页面文案密度

- 页面标题应直接进入任务，不添加整句副标题重复解释阶段、冻结规则、审批顺序、指标单位、同源关系或模拟边界。
- 同一规则或免责声明不得在页头、卡片和侧栏反复出现；需要长期保留的口径统一收进“方法与证据”抽屉，只在风险实际发生的上下文显示一次必要提示。
- 阶段、分支、数据属性和审批状态优先使用短标签、字段名、表头或按钮结果表达，不使用说明性段落占据主画布。
- 动态 Agent 摘要、权衡结论、异常与 fallback、空状态、不可逆操作提示及直接影响用户决策的信息不属于冗余文案，必须按需保留。
- 新增用户可见解释文案前，必须证明它能消除当前操作中的真实歧义；仅复述 PRD、Schema 或后台约束的文案不得进入正式页面。

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
- Runtime experiment、Replay 和全部决策缓存默认忽略；仓库只保留缓存生成与验证说明。
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
make dev-presentation
make test
make test-sim
make test-api
make lint
make validate-data
make build
make check
make docker-build
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

## 19. V3.1 事件驱动省际协同冻结契约

- 顶层阶段保持不变；`Y2_Q3` 增加实验级事件审批门禁与两轮省际交互。
- `comparison_mode` 只允许 `policy_intervention` 或 `event_counterfactual`，实验创建后不可修改。
- 政策模式只允许政策不同且事件哈希相同；事件模式只允许政策哈希相同且事件仅应用 Treatment。比较服务发现双重差异时必须拒绝。
- 事件目录固定为五个模板和 `low|medium|high` 三档；触发期固定 `Y2_Q3`，持续覆盖 `Y2_Q3–Y2_Q4`。
- 两分支都到 `Y2_Q2` 后进入 `awaiting_event`；未审批返回 `EVENT_APPROVAL_REQUIRED`。每个实验最多批准一次，审批后不可修改。
- Round 1 必须冻结 31 个 `ProvinceEventSignal` 后才启动 Round 2；Round 2 每省最多读取授权网络内 5 个信号。
- `coordinate` 只有互选且协作资格边有效时才贡献；单向提议保留为 `unmatched` 且贡献为零。
- 事件响应只作为 Q3 政策覆盖层，三类份额调整和为零、结果仍在 0–1；不得修改 Q1 Action 或直接写权威结果。
- Control 无事件时不得伪造信号、响应或省际交互调用。车企 Q3 不新增调用，事件只由环境改变模拟成本和 ROI。
- V3.1 活动版本为 `experiment-config-v4`、`province-profile-v5`、`event-scenario-v1`、`province-event-signal-v1`、`province-event-response-v1`、`province-interaction-network-v1`、`world-state-v5`、`comparison-v5`、`event-v5`、`checkpoint-v4`、`branch-v4`、`nev-policy-env-v2`。

## 20. 当前唯一下一步

用户于 2026-08-14 报告公网默认干预方案存在“命中缓存但全线无互动记录”回归。根因是早期 DeepSeek 输出检验缺少互动一致性、接收方 session 授权和剩余额度约束，旧验证仅统计调用/fallback。旧 831 个缓存及首轮修复的 75 个不完整缓存已可恢复隔离；活动缓存升级为 `m34-luna-cache-envelope-v3`、`m34-live-authorized-context-v3` 和 `m34-decision-quality-v1`。公网默认原始/干预方案仍为 `95/90/85` 与 `96/93/82`；冷跑 `exp_m34_44819eaa0dcd`、热跑 `exp_m34_cb7ae06bfad4` 均完成 Q1–Q4、530 次调用零 fallback，原始/干预分别有 93/104 条消息与 46/52 个已结算会话，缓存文件数第二次保持 1487 不变。完整契约与证据见 `docs/adr/ADR-374-m354-deepseek-cache-quality-gate.md`。

用户于 2026-08-13 在 M35 验收后追加的两项正式部署要求已完成公网验收：公网默认 Cache-first，修改东中西比例导致 cache miss 时由 DeepSeek 生成、校验并回写缓存；全国地图除 31 省和港澳台上下文外，显示同一冻结标准地图的南海诸岛附图。验证实验 `exp_m34_64538c5bf0bc` 已完成修改比例后的双分支 Q1 与独立 Checkpoint。南海诸岛不进入 31 省 Agent、指标、色阶、事件、交互或比较。完整契约与证据见 `docs/adr/ADR-372-m352-cache-first-deepseek-and-national-map.md`、`docs/validation/M35_2_CACHE_DEEPSEEK_NATIONAL_MAP_VALIDATION.md`。

用户于 2026-08-14 最终澄清公网中国地图的南海诸岛必须固定在地图画布左下角，不跟随俯视、侧视、缩放、平移、分支或 A/B 视角移动，也不得被右下角图例覆盖。Presentation 的 WebGL 与 SVG 降级画布继续共用同一个 `SouthChinaSeaInset`：该层是地图内制图内容而不是说明卡，外框为方角虚线，不显示卡片底色、阴影或外置标题牌；内部“南海诸岛”名称、岛礁与断续线只从冻结自然资源部 GS(2016)1609 标准地图裁切，不手工重绘，也不进入 31 省 Agent、指标、事件、关系线或比较。

用户随后提供参考图并要求中国地图本体严格呈现从台湾、海南下方向南延伸的可见南海断续线。最终澄清为：左下角南海诸岛附图继续固定于地图视口；主地图断续线不是图例或屏幕叠层，而是中国版图制图内容，必须从同一 GS(2016)1609 冻结原件黑色路径机械分离并锚定到地图坐标。拖动、缩放、俯视、侧视、分支或 A/B 切换时，断续线必须与中国地图接受完全相同的相机变换，和台湾、海南保持刚性相对关系，禁止独立位移、缩放或旋转。该线不得手绘、补点或进入 31 省计算、交互、事件、指标和比较。

用户于 2026-08-14 进一步指出直接渲染官方填充字形形成的粗重 I/锤形轮廓不符合参考图，并批准使用“细长断续边界线”，前提是放在合适位置。活动实现按 12 个官方断续符号分组，从原 46 条冻结路径机械求取主轴中心线，输出细长圆头 `LineString`；展示范围按项目台湾与海南几何校准为台湾东侧—南海深处—海南西南侧的 U 形版图关系，不增加人工补点。该线继续与地图共用全部相机变换；左下角标准附图继续固定于视口。

当前无新的未完成里程碑；后续只在用户提出新要求或发现明确回归时修改 M34/M35。

## 21. 已批准的后续省级数据验收方向

`docs/data/PROVINCE_PROFILE_DATA_REQUIREMENTS_V3_1.md` 是 M28 之后省级数据迁移的强制验收约束：

- Profile 必须优先保存 GDP、人口、收入、财政与产业结构等真实原始数量、单位、年份、机构、链接和统计口径；0–1 指数只能作为版本化、可反算的确定性派生层。
- 当前 `province-profile-v5` 中基于冻结代理值生成的字段必须继续标记 `proxy`，不得在补齐逐字段来源前改称 verified。
- 结构能力、历史政策偏好和当期情景响应必须分层；不得把经济体量或产业占比直接写成固定政策性格。
- 省级 Agent 的产业偏好判断必须引用结构事实、近 3–5 年政策证据及土地、人才、能源、环保约束；不得写死“某省不愿接受传统制造业”等刻板标签。
- 对上海等省份，只能在 Evidence 支撑下表述为“当前数据和机制下更偏高附加值、研发密集和先进制造环节，对低附加值高资源消耗环节吸引力较低”的模拟判断。
- 观察 Peer、竞争 Peer、协作 Peer 必须使用不同字段和证据来源；当前观察网络与协作资格边不得被解释为竞争网络。
- 后续采集还必须覆盖 31 省新能源汽车产业/市场基线、过去 3–5 年政策行为、真实电池/整车节点与物流距离、省际产业链关系、四类事件敏感度和 10 家车企真实冻结基线。
- 最新清单未授权用临时代理补成 verified；在逐字段采集、转换和验收完成前不得宣称真实基线迁移完成。

M29 v2 已将 177 项需求纳入验收；但当前 Fake 省级与车企基线仍按 `proxy` 展示为“代理数据基线”。机器层必须保存逐字段 provenance、直接来源或推算公式、冲突值和方法版本。

## 22. V3.2 活动实施约束

- 当用户粘贴的 V3.2 文本、本 PRD 和旧 V3.1 条款冲突时，以 V3.2 为准。
- 活动用户旅程只允许六步前置 A/B；年末干预和运行期事件审批只服务 V3.1 历史对象。
- 基线确认后创建两个同源分支，各执行省级初始、车企初步、省级调整、车企最终和环境结算五轮。
- 省级第二轮必须收到非空观察 Peer 行动和企业信号。观察、竞争和协作网络必须使用不同边和来源。
- 车企使用 10 套差异化 `automaker-simulation-persona-v1`；事件影响车企时最终轮必须重新评估并记录 Delta。
- 主页对 `proxy` 统一显示“代理数据基线”，具体来源与计算方法进入 Evidence；不得显示原始枚举、snake_case、旧季度码、Checkpoint ID 或 WorldState。
- M32 起主产品页面只展示方案、最终行动与结果；Agent、版本、轮次、资源上限、阈值、机会成本、追溯、哈希与缓存等字段只允许出现在“方法与数据”审计页。省份详情固定为政策配置、企业互动、竞争与协同、推演影响四张结果卡。

## 23. M30 上下文驱动自主协作契约

- M29 4,527 条事实、711 项特征与 282 条关系边是 Agent 上下文，不是行动规则。
- 省级调整拆为 3A 提议和 3B 响应；两分支全部 3A 冻结后才可进入任一 3B。
- 现有协作关系只是软先验。Agent 可选关系网外对象，但必须引用产业互补、节点距离、企业信号或政策目标证据。
- Orchestrator 只校验 Schema、身份、分支、轮次、预算和资源守恒，不得根据省份顺序、相邻位置、固定名单或行为阈值配对。
- 每省最多提出 2 项、生效 1 项；提出＋接受＋双方资源合法才计入确定性环境贡献。
- 完整双分支为 226 次结构化主体调用；每次保存模型、输入/输出哈希、Schema 和 fallback 状态，不保存思维链。
- 活动版本为 `province-action-v6`、`automaker-action-v3`、`decision-trace-v2`、`branch-v6`、`world-state-v7`、`comparison-v7`、`event-v7` 和 `nev-policy-env-v4`。

## 24. M31 显式决策与互动主画布契约

- M31 不新增主体、政策工具、主路由或模型调用；完整双分支仍为 226 次结构化主体调用。M30 对象、缓存与标准地图原件只读保留，不静默转换。
- 省际协同与省企资源包是独立机制：每省每分支可各自提出 0–2 项。未发起省企资源包时，必须记录“不发起”、原因、机会成本和改变条件。
- 省企资源包只能引用既有财政空间和三类补贴配置，不增加财政或工具。每家车企在最终轮必须对收到的每项资源包 `accept` 或 `reject`，每分支最多接受 5 项。
- 有效匹配须同时满足有效提议、明确接受和双方资源合法。环境只能通过渠道协同与产业协同计入匹配贡献；拒绝、未发起与资源无效必须留痕且贡献为零。
- 车企对 31 省只输出 `expand|maintain|reduce` 的明确市场决定，以及主承诺、机会成本、拒绝理由和重新评估条件。候选排序仅可留在 Evidence，不得进入用户主结果。
- Live 默认显示“干预方案 − 原始方案”差异地图；差异图动态对称缩放、零点中性，绝对图使用分位色阶。空值必须用纹理显示且不得写作 0；图层切换不得增加 Agent 调用。
- 新分析底图必须只从冻结标准地图选择 31 条完全一致的省域几何，保留来源、审图号、总签名和逐省校验。
- 活动版本为 `province-resource-envelope-v2`、`province-action-v7`、`automaker-action-v4`、`decision-trace-v3`、`branch-v7`、`world-state-v8`、`comparison-v8`、`event-v8`、`strategy-market-v2` 和 `nev-policy-env-v5`；缓存使用 `v3_2_m31_*` 命名空间。

## 25. M32 / v9 省际竞争、闭环谈判与严格 Top-K 契约

- M31 是只读历史对象；M32 是默认新建实验版本，`product_version` 固定为 `v3_2_m32`，缓存只能使用 `v3_2_m32_*` 命名空间。不得将既有 M31 运行对象原地转换为 v9。
- 双分支按七轮执行：省初始、车企初步 Top-K、省级竞争反制/协同提议、车企报价/反报价、省级反报价回应、车企最终确认与重配、环境结算。完整双分支固定为 308 次结构化主体调用；两分支的报价必须全量冻结后才可进入回应，回应全量冻结后才可最终确认。
- 观察、竞争、协同网络必须保持独立关系边和 provenance。观察仅进入策略学习；竞争边与临界 Top-K 挤出共同触发 `CompetitionOutcome`；协同仍须双方接受且资源合法才产生贡献。
- 省级效用的唯一骨架为 `U = wd·需求 + wi·产业 + we·省企匹配收益 + wc·协同收益 − wf·财政压力 − wl·竞争损失`。所有项为 0–100 模拟指数；权重由冻结 Persona 六轴归一化并作为 `utility:` Evidence 保存。竞争损失必须同时作为环境需求/产业的负机制项，不能只写在解释文本中。
- 每车企渠道扩张 `K=2–5`、产能重点 `K=1–3` 均由冻结 Persona 决定；31 省仍须有明确 `expand|maintain|reduce` 决定，只有 Top-K 获得战略资源。预算、渠道名额和产能名额必须严格守恒。
- 反报价只能重排既有三类地方工具和既有资源包份额，不得创造财政、现实承诺或政策工具；每车企最多三项、每省最多接受一项。拒绝或无效资源包贡献必须为零，最终轮只能将释放名额重配至合格非获选省。
- v9 对象至少为 `automaker-resource-envelope-v2`、`automaker-action-v5`、`decision-trace-v4`、`branch-v8`、`world-state-v9`、`comparison-v9`、`event-v9`、`strategy-market-v3`、`competition-outcome-v1`、`province-utility-v1`、`automaker-counter-offer-v1`、`province-counter-offer-response-v1` 和 `nev-policy-env-v6`。Evidence 增加 `utility:`、`competition:`、`topk:`、`counteroffer:` 与 `counterresponse:`。

## 26. M33 独立全景推演厅契约

- 新前端是独立 `apps/presentation`，正式入口 `/experiments/:id/present`。旧 `apps/web` 在新模块验收前保留，不原地覆盖或删除。
- 单屏固定包含顶部 HUD、全国地图主舞台、左侧叙事浮层、右侧功能坞和底部可拖动时间轴；政策输入、解读、设计、基线、七轮运行、回放、对照和 Evidence 均在该屏完成。
- 产品模式只允许 `live|story|compare`。Story 使用后端五幕摘要和真实冻结帧；Compare 默认单图 Delta，可切换同步 A/B。
- 突发事件是一级模块。首批正式模板继续为现有五项；目录改为版本化可扩展注册表。新增模板必须先具备确定性机制、来源、质量标签、Schema、缓存和测试，前端不得从自由文本生成影响系数。
- “伊朗相关冲突升级导致油价上涨”只能作为“国际冲突情景下油价上涨”的示例情景，不得表述为现实战争事实或油价预测。
- V1 事件触发点固定为推演开始前、省份初始行动后、车企初步响应后。晚期触发必须同步修改 Orchestrator、调用预算、Agent 可见性、缓存与 A/B 校验，不能仅改 UI。
- 时间轴连续可拖动，松手吸附至合法冻结帧。业务对象和指标只在帧边界切换；帧间仅补间镜头、填色、透明度、线条和展示数字，不生成新业务值。
- 后端新增只读 `presentation-timeline-v1`、`presentation-frame-v1`、`presentation-event-marker-v1` 和 `presentation-overlay-record-v1`。前端不得从 Replay 或摘要重算 World、指标和匹配贡献。
- 主地图目标技术为 MapLibre GL JS + deck.gl；只允许使用冻结标准地图校验后的 31 省衍生几何，并保留 ECharts/SVG 兼容模式。地图、字体、图标和样式不得依赖 CDN。
- 所有“中国地图”画面必须完整展示香港、澳门、台湾。三者从同一冻结自然资源部标准地图提取为 `territory-context`，不进入当前 31 省 Agent、指标、事件、色阶或点击详情；前端不得把它们显示成缺失值、独立实验主体或从中国版图中删除。
- M33.3 开场固定为 3–5 秒深空地球旋转并拉近中国，点亮 31 省后无缝交接全国省域推演地图；开场只做视觉交接，不增加业务帧或修改权威结果，并必须支持跳过、重播与低动效短交接。
- 无实验 ID 的根入口不得先显示事件目录：必须先播放地球开场，交接全国版图约 2 秒后自动打开空间玻璃配置弹窗。配置首 Tab 为东中西中央承担比例，第二 Tab 为可选突发事件；关闭事件创建纯政策对比，开启后才冻结事件计划。
- 根入口只保留“实验配置”和“A/B 实验设计/唯一主动差异”两个用户可见页面。配置提交后服务按顺序完成中央政策解读确认并进入设计页；用户确认设计后服务按顺序冻结代理数据基线并进入推演。解读与基线 API 门禁、审计和幂等语义保留。
- Presentation Frame V1 仅包含逐轮 Treatment 投影，A/B Split 不得把 Treatment overlay 复用给 Control。在 Presentation V2 冻结分支谱系前，双图仅展示共用色阶下的分支结果值。
- V3.2 Runtime 必须使用同目录原子快照按实验惰性恢复 World、Replay、Comparison 和 SSE Event 游标；进程重启后不得因内存索引丢失误走历史路由。
- M33.3 使用 GovSim Glass UI Kit：仅浮动控制、上下文卡片、时间轴和 Sheet 玻璃化，地图及互动传播保持为主内容；禁止把 SaaS 卡片网格改成满屏毛玻璃。信息按“态势/动作 → 核心指标 → 方法与 Evidence”渐进披露。
- M33.0–M33.6 全部完成：开场北京光点与 SVG 几何校准、包含港澳台版图上下文的全国地图、五事件三触发边界、七轮单屏闭环、SSE 恢复、五幕回放、Delta/A-B、机制链、键盘遥控、WebGL→SVG 降级和 1080p/2K/4K 验收均已冻结。

## 27. M34 Presentation Hall V2 完整博弈叙事契约

- M34 以 breaking upgrade 取代 M33 V1 主演示厅响应；原 timeline/frame 路由直接返回 `presentation-timeline-v2` 与 `presentation-frame-v2`，不保证 V1 JSON 兼容。
- M32 `world-state-v9`、Replay、七轮和 308 次调用保持权威且只读；V2 仅从冻结事实派生，不创建 Agent、不增加 Luna 调用、不重跑反事实世界。
- 七轮帧固定为 `frame-round-{round}`，每个逻辑帧同时包含 Control/Treatment。Overlay、Replay、Decision 与 Evidence 只能引用本分支或全局事实。
- Timeline 仅返回帧索引、事件节点、首次分歧和计数；完整 Frame 按当前帧懒加载并预取相邻帧。
- Frame 必须包含分支投影、决策时点边际评估、跨轮互动 Thread、Control/Treatment 分歧，以及恰好一个主 Spotlight 和最多两个不重复辅助 Spotlight。
- 备选评估只能复用既有资源包、守恒约束与吸引力公式，属于决策时点评分；不得称为概率、最终结果、最优策略或模型思维链。无合法备选时必须显式返回“没有足够合法备选”。
- Spotlight 只使用截至当前帧的事实，按分歧 25、真实回应 20、资源约束 15、行动变化 15、状态变化 15、Evidence 10 计算；禁止固定地区或读取未来 Gap。
- 主演示厅本期只开放 Live 与 Compare。Game Spotlight 固定使用“聚焦、观察、选择板、实际行动、实际回应、取舍/分歧”微镜头；自动路演与语音后置。
- 首次关键分歧、重大目标切换与结算可自动进入同步 A/B，用户可返回单图；Control 使用虚线/空心、Treatment 使用实线/实心，不能只依靠颜色区分。
- 新增全部决策索引，支持轮次、分支、主体、互动类型和状态筛选，并能回到地图与 Evidence。断网保帧、MapLibre 单实例、SVG 键盘降级、低动效和 Fake/Fallback 边界继续强制。

## 28. M34 季度事件驱动活动契约

- 本节是当前活动 M34 契约；第 27 节仅记录升级前已实现的展示投影，不得覆盖本节时间和运行语义。
- 新建实验固定为 `product_version=v3_2_m34`、ID `exp_m34_*`。旧 `exp_m32_*` 不加载、不迁移、不删除，相关运行与展示接口统一返回 `410 LEGACY_V32_RUNTIME_UNSUPPORTED`。
- 宏观时间固定为 `Q1|Q2|Q3|Q4`，季度内逻辑波次固定为 `wave_0|wave_1|wave_2`；不生成 Agent 现实响应日期。
- 每季依次执行授权 Inbox、最多三波互动、确定性季度结算和不可变 `tick-checkpoint-v1`。两分支完成同一 Wave 后才能前进，严禁跨分支消息或私有状态读取。
- Q1 Wave 0 每分支恰好调用 31 省与 10 车企；Q2–Q4 只按新消息、到期复评、条件成立、新事件可见或未决事务激活。Scheduler 不替主体选择行动。
- 每 Tick 上限为三波、180 次调用、500 条消息；每对主体最多两次条件往返。达到上限冻结最后合法状态并记录 `interaction_budget_exhausted`。
- 实验可冻结 0–3 个 `event-plan-v2`；重复模板和相同 `conflict_group` 的互斥事件拒绝。事件从 `scheduled_tick/release_wave` 起持续至 Q4。
- 省企双方均可发起；交易状态为 `proposed → countered/accepted/rejected/deferred → settled/withdrawn/expired/resource_invalid`，只有 `settled` 贡献环境。
- 年度资源包在基线冻结、季度结转，行动只能重配现有资源。省份每 Tick 最多 2 项省际与 2 项省企发起，车企最多 5 项省级合作意向。
- 中央 Agent 只在实验前政策解读和 Q4 后年度复盘各调用一次，季度内不能改变政策或 World。
- Live/Cache Prompt 禁止包含确定性候选行动；公网 cache miss 必须先请求 DeepSeek 并将合法结果回写缓存，只有模型、Schema、身份或资源校验失败时才允许确定性显式 fallback。
- 活动版本为 `experiment-design-v2`、`event-plan-v2`、`baseline-snapshot-v3`、`tick-checkpoint-v1`、`authorized-inbox-v1`、`interaction-message-v1`、`agent-tick-decision-v1`、`interaction-session-v1`、`interaction-market-v1`、`branch-v9`、`world-state-v10`、`comparison-v10`、`event-v10`、`runtime-snapshot-v2`、`presentation-frame-v3` 和 `presentation-timeline-v3`。

## 29. M35 Presentation 因果舞台契约

- M35 只修改独立 `apps/presentation` 与其只读投影；普通 Web 前端不进入设计、实现或验收。
- 用户已选定 `docs/assets/m35/causal-stage-reference.png` 为正式视觉目标。主舞台固定为顶部决策问题、左侧六段因果链、中央低饱和世界地图、右侧主体博弈台和底部四季度章节轨。
- 主叙事必须按“关注 → 观察 → 决策 → 行动 → 回应 → 结算”展示结构化事实；不得展示或推断思维链。
- 主舞台只消费强类型 Presentation View Model；不得直接显示 `sender_id`、`recipient_ids`、`transaction_state`、消息机器码、裸主体 ID、snake_case、Wave 码、Schema、Checkpoint 或哈希。
- 主体引用统一为 `province:`、`automaker:`、`event:` 与 `environment:` 前缀；后端负责展示名、主体类型、消息、状态、阶段和机制的中文映射。
- Control/Treatment 互动、消息、Spotlight 和关系线必须逐分支隔离。差值视图只显示后端冻结的分歧，不得合并两分支互动。
- 同一指标跨季度使用年度共享域；同步 A/B 使用同域。互动帧地图降饱和，提议/反报价/达成/拒绝分别使用琥珀实线、紫色虚线、青色粗线和红灰淡出并附文字。
- 事件必须形成 `Event → Province/Automaker → Decision → Settlement` 可见链。动画只编排权威事实，顺序固定为 FOCUS→OBSERVE→DECIDE→ACTION→RESPONSE→SETTLE。
- Presentation 地图提供自动镜头、全国俯视和因果侧视。自动镜头只在行动/回应节拍倾斜；差值、季度结算和年度比较必须锁定全国俯视。视角只改变前端相机，不触发 Agent、不创建业务帧、不修改地图几何或权威结果。
- 核心验收是首次观看者 10 秒内可回答当前季度、谁行动、为什么、对谁、如何回应及世界影响；构建或截图成功不能替代该验收。
