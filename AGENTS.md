# AGENTS.md

本文件适用于当前目录及其全部子目录，用于约束参与 PolicyScope V2.1 的 Codex、自动化开发 Agent 和人工开发者。

---

## 1. 当前阶段与工作门禁

当前仓库已完成 V2 原地迁移和产品 QA；V1 回滚基线保留在 Git 提交 `12456a3`。V2.1 将产品主线升级为“省级 Agent 主决策、企业 Agent 作市场反馈”。目标产品仍是：

> 面向国务院层面政策统筹人员的“制造业设备更新政企互动 Agent 推演台”。

当前状态：

- V2 FastAPI、React、31 省 × 6 企业群体、审批、Checkpoint、Replay、A/B 与单线复盘已完成。
- V2 PRD、开发计划和 Stitch 规范已批准并冻结；公共 DTO 使用 `policy-v2`、`world-state-v2`、`comparison-v2` 和 `event-v2`。
- Fake/Cache/Live Provider 共用统一接口；默认演示为 Cache，测试为 Fake，Live 不得阻塞交付。
- Stitch 四路由、河南省企抽屉、证据抽屉和本地标准地图衍生 SVG 已交付，`design-qa.md` 为 `passed`。
- 全国地图已完成省域映射修正、几何签名和 31 省完整性校验；根据用户确认的比赛发布规则，比赛版可直接上线。
- V2.1 PRD、开发计划、Agent 约束和 Stitch 规范已获用户批准，代码迁移门禁已解除。
- V2.1 的 Persona、V3 DTO、Agent、仿真、API/SSE、默认缓存与五路由前端已实现；最终 E2E、连续三次 Cache 与 Design QA 尚未完成，不得沿用 V2 的通过结论。
- 当前阶段为 M12 验证待恢复；用户已明确要求暂不运行测试，不得提前将 V2.1 `design-qa.md` 标记为 `passed`。

如果用户在后续回合明确改变门禁，以用户最新要求为准，并在同一变更中同步所有受影响文档。

---

## 2. 开始工作前的必读顺序

任何实现、重构、评审或测试开始前，必须依次完整阅读：

1. `AGENTS.md`
2. `PRD_省域政策多智能体推演平台.md`
3. `DEVELOPMENT_PLAN.md`
4. 与任务直接相关的 Schema、代码、测试和局部文档

涉及前端、地图、可视化、文案或交互时，还必须在修改前完整阅读：

5. `STITCH_FRONTEND_SPEC.md`
6. `stitch_policyscope/policyscope/DESIGN.md`
7. 与目标页面对应的 Stitch `screen.png`

不得只看 Stitch 的 `code.html` 就开始实现。

---

## 3. 文档与视觉来源优先级

发生冲突时，按以下顺序判断：

1. PRD：产品语义、用户权限、阶段、指标和验收。
2. 领域 Schema / API：运行时数据真相。
3. `STITCH_FRONTEND_SPEC.md`：正式页面结构、交互、文案和状态。
4. `stitch_policyscope/policyscope/DESIGN.md` 与五张 `screen.png`：视觉基准。
5. Stitch `code.html`：仅用于测量和布局参考，不是正式运行代码。

实施顺序和任务状态以 `DEVELOPMENT_PLAN.md` 为准。代码与已批准契约不一致时，先判断是迁移未完成还是契约需要变更，不得静默用现有实现覆盖文档。

---

## 4. 项目使命与用户边界

核心用户是国务院层面的政策统筹、评估和跨区域协调人员。用户本人是最终政策操作者，不是仿真主体。

```text
用户输入中央目标
  → 中央政策研判 Agent 生成政策草案
  → 用户审批
  → 确定性冻结 31 个省级 Agent 的实验决策画像
  → 31 个省级 Agent 选择地方工具、目标企业和省际策略
  → 每省 6 类企业群体 Agent 反馈地方政策的市场响应
  → 确定性环境计算结果和机制贡献
  → 省级 Agent 复盘并提出不改变政策的调整意向
  → 中央 Agent 提出干预建议
  → 用户批准、修改或拒绝
  → 同一 T3 Checkpoint 派生 Control/Treatment
  → T5 先比较省级策略迁移，再比较企业行为、地区差异和政策代价
```

产品是机制实验和协同研判工具，不是宏观经济预测系统，不代表现实国务院、地方政府或企业的立场。

所有关键页面固定显示：

> 研判口径：结果为当前数据与机制参数下的模拟指数，用于政策方案比较。

---

## 5. P0 主体与不可妥协的职责边界

### 5.1 中央政策研判 Agent

中央 Agent 必须真实参与并输出结构化对象：

- T0：`CentralPolicyDirective`
- T3：`CentralInterventionProposal`
- T5：`CentralReview`

中央 Agent 只能建议：

- 不能直接写 WorldState。
- 不能绕过用户审批发布政策或创建 Treatment。
- 不能自称现实“国务院认为”或给出自动最优政策。
- 输出必须经过 Schema 校验、版本记录、证据引用、Cache/Fallback 和 Replay。

### 5.2 31 个省级主决策 Agent

省级 Agent 是地方层面的主决策主体。每省必须拥有一个由 Profile、Top-K 网络和版本化规则确定性生成的 `ProvinceDecisionPersona`，表达六项决策轴、主/辅助类型、优先目标和关键约束。Persona 在一个实验及其所有分支中稳定，不经过 LLM，不得解释为现实政府性格。

省级 Agent 生成主要目标、决策姿态、地方政策工具组合、执行强度、配套资源、目标企业群体、省际策略、中央支持请求和结构化摘要。非独立省际策略只能选择 1–2 个当前 Top-K 省份；独立推进不得包含目标省份。

T3 省级 Agent 只能生成地方策略评价、企业信号、主要约束、最多三项调整意向和中央支持请求。调整意向不得修改 Policy、ProvinceAction、WorldState 或父 Checkpoint。T4 必须使用同一 Persona，并引用上一 Action。

省级 Agent 不得：

- 计算或写入最终结果指标。
- 修改其他省份状态。
- 选择 Top-K 网络外的目标省份。
- 在 T3 直接应用调整意向。
- 输出现实 GDP、就业人数、投资金额或财政金额预测。
- 把企业的参与、观望或拒绝错误归因为省级立场。

### 5.3 186 个企业群体反馈 Agent

中国大陆 31 个省级行政区，每省固定六类企业群体：

1. 大型国有制造企业
2. 大型民营制造企业
3. 科技型 SME
4. 传统制造 SME
5. 高耗能工业企业
6. 出口制造企业

每个企业 Agent 只生成结构化策略：参与状态、更新类型、融资选择、投资强度、支持请求、原因码和最多 80 个汉字的公开摘要。

企业 Agent 是市场反馈和政策验证层，不能取代省级 Agent 的目标、地方工具或省际策略。全国、干预、对照和省级详情体验必须先呈现省级决策，再呈现企业反馈。

企业 Agent 不得：

- 输出投资金额、生产率增幅、就业人数或现实预测值。
- 直接计算或修改省级、全国或分支结果。
- 冒充现实企业或展示长思维链。

每省使用一次批量模型调用完整返回六类企业。第一次 Schema 失败可修复一次；再次失败时整省进入确定性 fallback，且 UI、Event、Replay 都必须显式标记。

### 5.4 确定性环境

`ChinaPolicyEnv` 是结果状态转移和机制贡献的唯一权威。LLM 只做策略选择。

- 相同输入、版本和 seed 必须得到相同结果。
- 每次状态更新必须同时生成机制贡献。
- 指标必须防 NaN/Infinity，并 clamp 到约定范围。
- 公式和权重放在版本化配置中，不散落为无名称常量。
- 机制贡献至少覆盖政策匹配、直接补贴、贷款贴息、融资担保、SME 倾斜、区域支持、融资约束和财政成本。

### 5.5 审批与同源 A/B

- T0 中央指令未经批准不得运行 T1。
- T3 建议未经批准不得创建 Treatment。
- 用户可批准、修改或拒绝中央建议。
- Control/Treatment 必须从同一不可变 T3 Checkpoint 派生。
- Treatment 创建不得改变 Control。
- 唯一主动差异是用户批准的政策字段。
- API 与服务层必须复核审批，不能只依赖前端按钮。

### 5.6 Cache 与 Fallback

- 默认设备更新场景必须有预生成结构化缓存。
- 不允许把现场运行完全押在模型网络调用上。
- Fallback 必须展示原因和范围，不能伪装成 Live 结果。
- Cache key 必须包含所有影响输出的输入、数据版本、机制版本、Prompt、模型和 seed。

---

## 6. V2.1 P0 范围

必须做：

- 1 个中央 Agent、31 个省级 Agent、186 个企业群体 Agent。
- 31 个稳定的实验决策画像、结构化省际策略、T3 调整意向和 T4 行动谱系。
- 1 个制造业设备更新政策域。
- T0–T5 阶段、两次人工审批、同源 A/B。
- 省级策略迁移、企业行动迁移、地区差异、财政压力和机制贡献。
- 五个核心路由、独立省级 Agent 详情页、方法与证据抽屉。
- 真实 API、SSE、Checkpoint、Replay、Cache、Fallback。
- 经来源和合规检查的离线 31 省矢量地图。

暂不做：

- 园区、投资机构、公众、城市、部门或真实公司主体。
- 自由形式 Agent 群聊或全国政策知识图谱。
- 头像、第一人称台词或戏剧化省份角色扮演。
- 多政策域和现实亿元、产值、GDP、就业预测。
- 自动替用户选择现实“最优政策”。
- P0 移动端和复杂高级地图动画。
- 路演脚本。

发现范围膨胀时，按 `DEVELOPMENT_PLAN.md` 的砍项顺序保护主闭环。

---

## 7. 阶段规则

严格保持以下顺序：

```text
T0 中央目标 → 中央结构化政策 → 用户审批 → 冻结31省实验决策画像
T1 31 个省级 Agent 生成目标、地方工具和省际策略
T2 31 次企业批量决策 → 186 个 Action → 环境计算
T3 31 个省级 Agent 生成复盘与调整意向 → 汇总证据 → 冻结 Checkpoint → 中央建议 → 用户审批/修改/拒绝
T4 Control/Treatment 中省级 Agent 先重新决策，企业主体再响应
T5 环境结算 → 省级策略迁移 → 企业行为迁移 → 全国 A/B → 中央复盘
```

不要把所有 Agent 简化为每轮统一调用，也不要因 UI 刷新或动画重复调用模型。

完整 A/B 调用预算保持中央 3 次、省级约 124 次、企业约 93 次分省批量调用；Persona 由确定性规则生成，不增加模型调用。

---

## 8. 领域模型规则

### 8.1 强类型与版本

- Python 边界对象使用 Pydantic v2；TypeScript 使用严格同步或生成类型。
- 核心路径禁止无约束 `dict[str, Any]` 和 `any`。
- 枚举使用稳定英文机器码，中文仅用于展示。
- 可持久化对象包含 `schema_version`。
- ID 使用不透明字符串；时间戳使用 UTC ISO 8601。
- 阶段使用 `T0`–`T5` 枚举，不伪装为现实月份或年份。

### 8.2 `PolicySchema`

参数必须与 PRD 一致：

- `support_intensity`：0–100，默认 70。
- `local_match_requirement`：0–1，默认 0.50。
- `instrument_mix`：直接补贴 0.45、贷款贴息 0.35、融资担保 0.20，总和为 1。
- `sme_preference`：0–1，默认 0.60。
- `regional_support_bias`：-1–1，默认 0。
- `technology_mix`：数字化 0.40、绿色 0.30、基础技改 0.30，总和为 1。

权重不合法必须拒绝，不能静默归一化。结构化目标不得包含自动生成的现实预测值。

### 8.3 省级 V3 契约

- `province-profile-v3` 补充研发能力、就业压力和合作倾向。
- `province-persona-v1` 六轴公式、31 省百分位、平均并列排名、类型优先级和三省验收结果必须与 PRD 完全一致。
- Persona 数据质量只能为 `proxy` 或 `demo`，用户可见名称固定为“本次实验决策画像”。
- `province-action-v3` 必须包含主要目标、决策姿态、1–3 个目标企业类型、省际策略、目标省份和 `previous_action_id`。
- `province-feedback-v3` 必须包含策略评价、企业信号、主要约束、最多三项调整意向、中央支持类型/强度和证据引用。
- Action/Feedback 不得包含结果指标；T3 adjustment path 必须使用冻结白名单。

### 8.4 `EnterpriseAction`

- `participation`：`participate` / `conditional` / `wait` / `decline`。
- `upgrade_type`：`digital` / `green` / `general` / `none`。
- `financing_choice`：`self_funded` / `direct_subsidy` / `interest_subsidy` / `guarantee_loan` / `none`。
- `investment_intensity`、`requested_support`：0–1。
- 原因码使用枚举，摘要最多 80 个汉字。
- 拒绝或无升级时的组合约束必须由 Schema 和环境测试共同覆盖。

### 8.5 `WorldState` 与 `ComparisonResult`

- WorldState 是前端和 Replay 的权威投影视图，提交后不得原地修改。
- 必须记录 Profile、State、Action、聚合结果、质量标签和完整版本信息。
- 全国指标固定为企业参与、设备更新意愿、SME 融资可达性、产业升级、地方财政压力、区域差距六项指数。
- `world-state-v3` 必须包含 Persona、ProvinceAction lineage 和 V3 Feedback；Persona 在同源分支中共享，行动谱系按分支隔离。
- `comparison-v3` 必须先包含省级目标、姿态、工具、目标企业和省际策略迁移，再包含企业动作迁移矩阵、重点企业群体变化、地区排行、机制贡献和中央复盘。

---

## 9. 架构边界

```text
React Web
  → API Client / Hooks
    → FastAPI
      → Application Services
        → SimulationAdapter
          → Agents / Environment / Storage
```

### Web

- 只消费 API DTO、WorldState 和 EventEnvelope。
- 不读取后端运行时对象，不在浏览器重算环境结果。
- 组件不直接 fetch，通过统一 API client/hooks。
- Server State 与局部 UI State 分离；事件按 `event_id` 去重。

### API 与服务

- 路由只做输入验证、审批检查、服务调用和响应映射。
- Prompt、公式、分支复制逻辑不得放在路由中。
- Orchestrator 负责阶段顺序；Checkpoint、Comparison、Replay 各自有明确服务边界。
- 非法阶段转换返回 409；未审批操作返回 403 或明确领域错误。
- 错误包含稳定 `error_code`，不泄漏内部堆栈。

### SimulationAdapter 与 LLMProvider

- `AsyncioSimulationAdapter` 是必须可用的基线。
- 可选运行时不得泄漏到领域 Schema、API DTO 或前端。
- 模型调用统一经过 `LiveLLMProvider`、`CachedLLMProvider`、`FakeLLMProvider`。
- React、API 路由、环境和数据脚本不得直接调用模型 SDK。

---

## 10. API、SSE、Replay 与 Checkpoint

- 现有 REST 资源路径尽量保持，省级/World/Comparison/Event DTO 升级到 V3，Policy 和企业领域对象继续使用 V2。
- 新增省级详情和 Persona 类型元数据接口；前端不得硬编码 Persona、策略或企业语义规则。
- 创建实验、运行阶段和创建分支必须幂等或使用幂等键。
- EventEnvelope 至少包含 `event_id`、`type`、`experiment_id`、`branch_id`、`phase`、`timestamp`、`schema_version` 和 `payload`。
- SSE 支持 `Last-Event-ID`、客户端去重和断线恢复。
- `event-v3` 中，省级事件至少包括 Persona 就绪、决策开始/完成/fallback、调整意向完成和策略迁移；企业事件继续包括批量决策开始、完成、fallback 和聚合更新。
- SSE 只通知事实；完整状态由 WorldState 获取。
- Replay 为 append-only JSONL，记录 Agent 结构化输出、校验、fallback、机制贡献、审批和版本。
- Checkpoint 用于恢复和分支，Replay 用于审计；两者不能混同。
- 不保存 API Key、访问令牌或模型长思维链。

---

## 11. 数据与指标规则

- 仿真范围为中国大陆 31 个省级行政区；港澳台不进入计算，并在方法页说明。
- 每个 Profile 字段记录来源、链接、年份、单位、转换、缺失处理和 `verified` / `proxy` / `demo`。
- 三种质量值是类别，不能显示伪置信度。
- 企业群体是合成类型，必须带 `demo` 或 `proxy` 标签及构造说明。
- 不得把内部指数描述为现实金额、增长率、GDP 或就业变化。
- 结果统一显示“指数/100”与“指数点变化”；只有真实政策参数占比可显示百分比。
- LLM 不得在运行时自由创造 Profile、企业群体或网络边。
- 数据修改必须执行 31 省、31 × 6 企业、范围、引用和 provenance 完整性检查。

---

## 12. Stitch 前端强制规则

### 12.1 正式实现方式

- 品牌统一为“PolicyScope / 政策涟漪”。
- 保持 Stitch 浅色“现代制度工作台”、12 栅格、Inter + Noto Sans SC、蓝/青/靛语义色。
- 正式前端继续使用 React、React Router、API hooks、SSE 和本地资源。
- 禁止 iframe 五个静态 HTML，禁止把 Stitch `code.html` 直接发布。
- 禁止运行时依赖 Google Fonts、Material CDN、Tailwind CDN 或远程地图资源。
- 图标使用项目本地 Material Symbols 类资源或既定本地图标库，不用 emoji 或手绘占位图形冒充。

### 12.2 核心路由与抽屉

- `/experiments/new`
- `/experiments/:id/live`
- `/experiments/:id/provinces/:provinceCode`
- `/experiments/:id/intervention`
- `/experiments/:id/compare`
- `?evidence=...`：方法与证据抽屉，显示质量、版本、seed、父检查点和引用。

旧 `?province=41` 只保留兼容导航，必须进入 `/experiments/:id/provinces/41`，不得继续作为正式省级详情容器。Live 默认地图指标固定为地方执行强度；Intervention 和 Compare 必须先展示省级策略，再展示企业反馈。

所有核心 CTA、路由、抽屉、加载、审批、失败、fallback 和断线恢复状态必须真实工作，禁止 `href="#"`。

### 12.3 地图

- 全国页和 A/B 页使用 ECharts 注册的真实 31 省 GeoJSON/SVG 矢量地图。
- 地图资源必须离线保存并记录来源、适用范围、版本、审图号或合规说明。
- 未通过地图检查时不得用浏览器截图、静态背景或抽象块状图替代。
- 地图只呈现 31 省仿真范围，图例必须显示指标名、单位、阶段和分支。

### 12.4 已知 Stitch 问题必须修复

- 静态导航、无效 CTA 和不可用抽屉。
- 假地图、A/B 空白地图和首屏内容遮挡。
- 品牌名称和中英文混用。
- 现实金额、伪精确百分比和伪置信度。
- 将企业 `wait` 错归因为省级行为。
- 提前把 Treatment 称作“优化方案”。
- 官方徽章、印章或“Official Institutional Use Only”等现实官方暗示。

Control/Treatment 展示名使用“原始方案/干预方案”。预期方向显示“待验证”。模型解释与环境计算必须用不同视觉标签。

### 12.5 画布与 Design QA

- 1440 × 900 是主验收画布，核心入口必须首屏可达。
- 1280 宽仍需可用；P0 不要求移动端。
- 交付前逐页、逐状态对五张源图与实现截图进行同画布视觉比较。
- 结果记录到 `design-qa.md`，修完所有 P0/P1/P2 后 `final result` 必须为 `passed`。

---

## 13. Python 与 TypeScript 约定

### Python

- Python 3.11+，完整类型标注，Pydantic v2。
- 异步 I/O 使用 `async`/`await`，不在事件循环中运行阻塞模型调用。
- 环境计算优先纯函数或显式输入输出，随机性通过显式 seed 注入。
- 不使用模块级可变 WorldState。
- 不捕获宽泛异常后静默继续；fallback 必须记录原因。

### TypeScript / React

- TypeScript strict，核心路径禁止 `any`。
- API 类型生成或严格同步，不在组件内复制领域枚举真相。
- WorldState 不得分散复制到多个不同步 store。
- 格式化、图表配置和领域数据转换集中管理。
- 新增页面和组件必须覆盖 loading、empty、error、fallback 和权限门禁。

---

## 14. 测试要求

### 领域与环境

- Persona 六轴公式、百分位、并列排名、类型映射、确定性和质量类别。
- 河南普惠扩散型、广东技术跃迁型、山西绿色转型型。
- Top-K 目标约束、独立策略空目标、T3 非变更和 T4 行动引用。
- 政策权重和为 1，范围和非法组合拒绝。
- 31 × 6 企业完整性，动作组合约束和摘要长度。
- 确定性、边界裁剪、机制贡献守恒。
- 同源 Checkpoint、分支隔离和唯一主动差异。

### Agent 与 Provider

- 省级 Action/Feedback 合法输出、一次修复、二次失败整省 fallback。
- 省级 Cache key 覆盖 Persona、上一行动、Top-K、企业反馈和全部版本。
- 每省批量返回六类企业且不可缺类、重复或越界。
- 合法输出、一次修复、二次失败 fallback。
- Cache key 覆盖政策、企业、Profile、模型、Prompt、版本和 seed。
- 不产生 Schema 外字段，不保存长思维链。

### API / SSE / Replay

- 正常响应、非法转换、未审批拒绝和稳定错误码。
- 企业事件、Last-Event-ID、去重和断线恢复。
- Replay、Checkpoint、版本和 fallback 完整性。

### 前端 / E2E

- 五路由门禁和核心状态，旧 `?province=` 兼容导航。
- 31 省可点击，河南详情页先显示 Persona/地方决策/省际策略，再显示六类企业反馈。
- Live 默认地方执行强度，审批链、双地图、省级策略迁移、企业迁移和证据抽屉。
- 禁止文案扫描、单位扫描和无效链接扫描。
- E2E 主路径：创建政策 → 批准 → T1–T3 → 河南省级详情 → 审批干预 → 双分支 → 省级策略 A/B、企业迁移与证据。

不得通过降低断言、跳过测试、硬编码结果或隐藏 fallback 让检查通过。

---

## 15. 开发工作流

接到实现任务时：

1. 确认文档门禁是否已解除。
2. 确认任务 ID、里程碑和依赖是否真实完成。
3. 阅读相关契约、代码、测试和视觉来源。
4. 检查工作树，保护用户和其他开发者的未提交修改。
5. 选择能产生可验证纵向价值的最小变更。
6. 先更新测试，再实现。
7. 运行与风险相称的最小完整检查。
8. 只有退出条件真实满足才更新计划状态。
9. 汇报改动、真实验证结果、剩余风险和唯一下一任务。

涉及 Agent 数量或职责、阶段、Schema、审批、分支、指标、P0/P1 或前端页面结构时，必须同步更新 PRD、开发计划和相关规范。

并行开发时：

- 不同参与者认领不同文件或清晰边界。
- 领域 Schema 由单一负责人先冻结，其他工作流消费。
- 不同时大幅编辑同一文件。
- 共享接口变更必须在一个变更中更新调用方和契约测试。

---

## 16. 文件、安全与禁止捷径

- 保留 `.obsidian`、Stitch 原始文件和用户文档；除非明确要求，不修改其配置或原图。
- 不提交 `.env`、API Key、令牌或敏感政策材料。
- Runtime experiment、Replay 和大缓存默认忽略；默认演示缓存单独白名单。
- 不用破坏性 Git 命令覆盖用户修改，不删除或移动用户文件来整理目录。
- 依赖升级必须有直接理由，冻结期不得升级。

禁止：

- 让 LLM 返回最终指标再包装为环境结果。
- 在前端硬编码河南或其他省份的最终结果。
- 用两次独立实验冒充 A/B。
- 未经审批自动应用中央建议。
- 省内六类企业缺失时静默继续。
- 用同一企业 Profile 只改名称冒充六类主体。
- 把 `demo` / `proxy` 数据称为真实统计数据。
- 用假地图、截图、静态 HTML 或 CDN 依赖冒充正式前端。
- 为动画推迟企业闭环、环境、分支或审批。
- 在没有证据时宣称性能、准确率、测试或 Design QA 通过。

---

## 17. 开发命令与完成定义

仓库目标命令：

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

V2 冻结基线的 `make test`、`make lint`、`make validate-data`、`make smoke` 和连续三次 Cache 产品流程均已实际通过。V2.1 主体已实现，但最终验证门禁未全部完成；恢复 QA 时必须重新运行与风险相称的门禁，不能沿用 V2 结论。

任务完成必须同时满足：

- 符合已批准 PRD 和职责边界。
- 相关测试存在并通过，错误和 fallback 被覆盖。
- 新数据带 provenance 和质量标签。
- Schema/API 变更已更新所有调用方。
- 用户可见改动处理完整状态、单位和免责声明。
- 没有新增秘密、无关修改或未追踪大文件。
- `DEVELOPMENT_PLAN.md` 对应退出条件真实满足。

V2.1 完成标准以 `DEVELOPMENT_PLAN.md` 的 V2.1 Definition of Done 为准，不得自行降低。

---

## 18. 当前唯一下一步

待用户恢复验证后执行 M12：运行全部门禁、两条 Playwright E2E、连续三次 Cache 流程及 1440×900/1280 截图对照。在此之前保持 `design-qa.md` 为 pending；比赛版地图上线决定不变。
