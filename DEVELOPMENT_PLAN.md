# PolicyScope V2 详细开发计划

> 对应产品文档：[PRD_省域政策多智能体推演平台.md](./PRD_省域政策多智能体推演平台.md)  
> 前端规范：[STITCH_FRONTEND_SPEC.md](./STITCH_FRONTEND_SPEC.md)  
> 计划版本：V2.0（已批准实施版）  
> 更新日期：2026-08-12  
> 目标周期：从 V2 文档获批起 48 小时  
> 当前门禁：V2 原地迁移与产品 QA 已完成；公开发布仍受地图合规人工复核门禁约束

---

## 1. 最终交付目标

48 小时结束时，应存在一个可在本机稳定运行和演示的 Web 产品，完整跑通：

```text
国务院层面用户设定制造业设备更新目标
  → 中央政策研判 Agent 生成结构化政策
  → 用户批准
  → 31 个省级 Agent 选择地方政策工具
  → 31 个批量企业决策返回 186 个企业群体 Action
  → 确定性环境计算省企结果
  → T3 中央 Agent 提出干预
  → 用户批准或拒绝
  → 同一不可变检查点生成 Control / Treatment
  → T5 比较企业行为迁移、地区差异、财政压力和机制贡献
```

完成标准不是“页面看起来像 Stitch”，而是：

- 国务院用户视角在产品中明确且一致。
- 31 个省级 Agent 和 186 个企业群体 Agent 都有结构化、可追溯的输出。
- LLM 只选择策略，结果由确定性环境计算。
- 企业批量输出失败时可修复一次，再失败进入显式 fallback。
- 用户未审批前中央建议不能改变 WorldState。
- Control/Treatment 来自同一 T3 Checkpoint。
- 四个核心路由和两个抽屉真实可操作。
- 正式前端达到 Stitch 视觉规范，且修复已知语义和交互问题。
- 默认场景支持离线 Cache/Fallback。

---

## 2. V1 回滚基线与 V2 交付基线

### 2.1 V1 回滚基线

仓库已建立，不再按“代码尚未初始化”处理：

- Python/FastAPI/Pydantic 工程。
- React/TypeScript/Vite 工程。
- V1 Policy、Province、World、Event、Branch、Checkpoint Schema。
- `AsyncioSimulationAdapter`、省级 Agent、中央 Agent 和确定性环境。
- 31 省 Profile、Top-K 网络和数据验证脚本。
- REST、SSE、Replay、Checkpoint 和 A/B 基础实现。
- 单页 React 工作台、抽象省域图、行动流和 A/B 图表。
- Stitch 五张高保真页面和视觉规范草稿。

### 2.2 V1 已验证事实

2026-08-12 V2 迁移前基线检查：

- Python 测试：17 个通过，存在 1 个第三方弃用警告。
- Web 测试：1 个通过。
- `make test`：通过。
- `make lint`：通过；V1 Web 构建存在约 795 KB 单包警告，列入 V2 路由级拆包任务。
- `make validate-data`：通过，31 省数据完整。
- `make smoke`：通过，31 省同源 A/B 基线可重复运行。
- 当前 React UI 与 Stitch 视觉目标不一致。
- 当前地图是自绘示意图，不是 31 省行政区矢量地图。
- 当前代码没有企业群体领域模型和企业决策链。

V1 已冻结在 Git 提交 `6ea8e9d`，用于原地迁移的回滚，不再建立并行 V1/V2 运行时。

### 2.3 V2 已验证事实

2026-08-12 完成原地迁移后：

- 领域版本统一为 `policy-v2`、`world-state-v2`、`comparison-v2` 与 `event-v2`。
- 31 省 × 6 企业群体、企业批量 Agent、ProvinceFeedback、设备更新环境与八类机制贡献已接通。
- T0–T5、批准/修改/拒绝、同源 A/B、单线复盘、企业迁移、REST、SSE、Evidence 与 Replay 已跑通。
- React 已替换为四路由 Stitch 工作台和两个 query drawer；核心 CTA 使用真实 API。
- 本地 ECharts SVG 地图来自标准地图 GS(2016)1609，31 省代码和几何经过自动验证；公开发布仍需人工合规复核。
- 默认演示使用完整 Cache，测试使用 Fake，Live 为非阻断增强。
- 路由级页面与 ECharts 已拆包，消除 V1 单包约 795 KB 的构建警告。
- 冻结门禁：Python 24 项、Web 2 项、lint/build、数据与地图校验、Smoke 全部通过；Cache 完整 A/B 连续 3 次且两个分支均无 fallback 省份。

### 2.4 不可误标为现实能力

- V2 指数和行为只适用于当前数据、参数、机制版本与 seed，不是现实经济预测。
- 合成企业群体不代表现实企业，`verified/proxy/demo` 是质量类别而非置信度。
- Stitch 静态 HTML 仍只作为视觉参考，正式交付以 React/API 实现为准。
- 地图技术验证完成不等于公开发布合规批准；人工复核前不得移除发布阻断提示。

---

## 3. 不可破坏的 V2 产品契约

### C-01 用户是国务院层面政策统筹人员

中央 Agent 是研判助手，不代表现实国务院。所有中央政策发布和干预必须由用户审批。

### C-02 企业 Agent 是 P0 主体

每省固定六类企业群体，31 省必须形成 186 个独立 Action。企业群体代表合成类型，不代表现实公司。

### C-03 Agent 只选择策略

中央、省级和企业 Agent 均不得写入最终指标或生成现实经济预测。

### C-04 环境计算确定且可解释

相同 Policy、Profile、State、Action、版本和 seed 必须生成相同下一状态及机制贡献。

### C-05 审批不可绕过

未经批准的建议不得创建 Treatment；API 和服务层必须再次校验，不能只依赖前端按钮。

### C-06 A/B 同源且隔离

Control/Treatment 共享父检查点、数据版本、机制版本、Prompt/模型版本、seed 规则和剩余阶段数；唯一主动差异是批准的政策字段。

### C-07 默认演示可离线

中央、省级和企业批量 Action 均应预生成缓存。Fallback 必须可见并进入 Replay。

### C-08 Stitch 是视觉基准，不是运行时

正式前端在现有 React 工程中实现。不得 iframe 静态 HTML、依赖 Tailwind CDN 或用截图冒充地图和组件。

---

## 4. 目标依赖方向

```text
React Web
  → FastAPI DTO
    → Application Services
      → SimulationAdapter
        → Central / Province / Enterprise Agents
        → ChinaPolicyEnv
        → Storage / Replay
```

约束：

- Web 只消费 API DTO、WorldState、ComparisonResult 和 EventEnvelope。
- API 路由只做验证、权限/审批检查、服务调用和响应映射。
- Orchestrator 负责 T0–T5 顺序，Checkpoint/Comparison/Replay 分责。
- AgentSociety2 不得泄漏到领域模型、API 或前端。
- `AsyncioSimulationAdapter` 始终是可运行基线。
- 所有模型调用经过 LLMProvider。

---

## 5. V2 核心接口

### 5.1 LLMProvider

```python
class LLMProvider(Protocol):
    async def generate_central_directive(...) -> CentralPolicyDirective: ...
    async def generate_province_action(...) -> ProvinceAction: ...
    async def generate_enterprise_actions_batch(...) -> EnterpriseActionBatch: ...
    async def generate_intervention_proposals(...) -> list[CentralInterventionProposal]: ...
    async def generate_central_review(...) -> CentralReview: ...
```

`EnterpriseActionBatch` 必须：

- 绑定唯一省份和阶段。
- 恰好返回六类不同企业群体。
- 不含 Schema 外字段。
- 记录 run mode、模型、Prompt、输入哈希、校验和 fallback。

### 5.2 SimulationAdapter

保留现有公开能力并升级 DTO：

```python
initialize(config)
approve_directive(experiment_id, policy)
run_phase(experiment_id, phase, branch_id)
create_checkpoint(experiment_id, phase)
approve_intervention(experiment_id, proposal_id, overrides)
create_branch(checkpoint_id, intervention)
get_state(experiment_id, branch_id)
compare(experiment_id)
get_replay(experiment_id)
close()
```

### 5.3 ChinaPolicyEnv

增加：

```text
submit_province_action
submit_enterprise_action_batch
apply_policy_instrument_effects
apply_enterprise_constraints
aggregate_enterprise_groups
update_province_states
calculate_national_metrics
get_enterprise_contributions
apply_approved_intervention
snapshot / restore
```

### 5.4 EventEnvelope

沿用统一 Envelope，新增企业事件：

```text
enterprise.batch.started
enterprise.decision.completed
enterprise.decision.fallback
enterprise.aggregate.updated
province.feedback.completed
```

---

## 6. 数据与目录迁移

### 6.1 建议目录

```text
simulation/
  agents/
    central_policy_agent.py
    province_agent.py
    enterprise_group_agent.py
    deterministic_fallback.py
  envs/
    china_policy_env.py
  llm/
  models/
    policy.py
    central.py
    province.py
    enterprise.py
    action.py
    event.py
    world.py
  mechanisms/
    equipment_renewal_v2.yaml
  services/

data/
  province_profiles_v2.json
  enterprise_archetypes_v1.json
  enterprise_groups_v1.json
  provenance_v2.json
  scenarios/equipment_renewal_default.json

apps/web/src/
  routes/
  components/
  features/
  api/
  styles/
```

允许根据现有结构小幅调整，但不得打破依赖方向。

### 6.2 数据迁移原则

- V1 文件保留到 V2 验证通过，禁止破坏性覆盖。
- V2 数据使用新版本号和新场景 ID。
- 每省六类企业群体由版本化原型与省级 Profile 合成。
- 生成脚本必须显式 seed，生成结果提交前运行完整性验证。
- `verified/proxy/demo` 继续是类别，不转换为百分比置信度。

---

## 7. 任务依赖图

```text
DOC-200 V2 文档批准
  → FOUND-200 运行命令与基线修复
  → MODEL-200 Policy/Enterprise/World V2 Schema
       ├─ DATA-200 省级与企业群体数据
       ├─ AI-200 企业批量 Provider
       └─ SIM-200 设备更新确定性机制
             → SIM-201 河南纵向闭环
             → SIM-202 31省×6企业扩展
             → SIM-203 T0–T5 与同源分支
                   → API-200 DTO/SSE/Replay
                   → WEB-200 Stitch 路由与组件
                         → WEB-201 地图/抽屉/A-B
                               → QA-200 E2E + 视觉 QA
                               → RELEASE-200 冻结
```

关键路径：

```text
DOC-200 → FOUND-200 → MODEL-200 → SIM-200 → SIM-201
→ SIM-203 → API-200 → WEB-200 → WEB-201 → QA-200
```

---

## 8. 48 小时里程碑

时间从 V2 文档获得用户批准时开始计算。

### M0：契约冻结与基线修复（H0–H2）

任务：

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| DOC-200 | 用户批准 V2 PRD/计划/AGENTS/Stitch 规范 | 已完成 | 无 |
| FOUND-200 | 修复 `make validate-data` 与 `make smoke` 导入路径 | 已完成 | DOC-200 |
| FOUND-201 | 记录 V1 基线测试和迁移前快照 | 已完成 | DOC-200 |
| ADR-200 | 冻结 V2 Schema、枚举、事件和版本号 | 已完成 | DOC-200 |

退出条件：

- V1 基线命令可重复运行。
- V2 公共 Schema 和迁移策略无未决项。
- 不再修改产品范围和视觉来源。

### M1：V2 Schema 与数据（H2–H8）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| MODEL-200 | PolicySchema V2 与权重约束 | 已完成 | ADR-200 |
| MODEL-201 | Enterprise Profile/State/Action/Batch | 已完成 | ADR-200 |
| MODEL-202 | Province/World/Comparison V2 | 已完成 | MODEL-200, MODEL-201 |
| DATA-200 | 六类企业原型和 provenance | 已完成 | MODEL-201 |
| DATA-201 | 31×6 企业群体生成与验证 | 已完成 | DATA-200 |

必写测试：

- 工具结构和技术结构权重和为 1。
- EnterpriseAction 组合一致性。
- 每省恰好六类企业。
- 31×6 共 186 个唯一 ID。
- V1/V2 Schema 不被静默混用。

退出条件：

- Pydantic 可合法创建完整 V2 WorldState。
- 数据验证覆盖 31 省和 186 企业群体。

### M2：企业 Agent 与确定性环境（H8–H15）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| AI-200 | Fake/Cached 企业批量 Provider | 已完成 | MODEL-201 |
| AI-201 | EnterpriseGroupAgent 和整省 fallback | 已完成 | AI-200 |
| SIM-200 | 工具激励、融资约束和财政成本 | 已完成 | MODEL-202 |
| SIM-201 | 河南省六企业纵向闭环 | 已完成 | AI-201, SIM-200 |

纵向场景：

- 河南省级 Agent 偏向贴息和担保。
- 大型企业可直接参与。
- 科技型 SME 条件参与并申请融资。
- 传统 SME 因现金流/融资约束观望。
- 环境贡献能解释差异，不硬编码最终指数。

退出条件：

- 无 Web、无 Live 模型也能完成河南 T0–T3。
- 六类企业 Action 完整、合法、差异可解释。
- 机制贡献与状态变化在容差内一致。

### M3：31 省、阶段和分支（H15–H23）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| SIM-202 | 扩展至 31 省×6 企业 | 已完成 | SIM-201, DATA-201 |
| SIM-203 | V2 T0–T5 Orchestrator | 已完成 | SIM-202 |
| SIM-204 | T3 Checkpoint 与审批 | 已完成 | SIM-203 |
| SIM-205 | Control/Treatment 隔离 | 已完成 | SIM-204 |
| SIM-206 | 企业迁移与 A/B Comparison | 已完成 | SIM-205 |

分支测试：

- 两分支父检查点一致。
- 创建 Treatment 不改变 Control。
- Policy Diff 之外的配置一致。
- 两分支各有 186 个企业 Action 或显式 fallback。
- 行为迁移可追溯到同一企业群体 ID。

退出条件：

- CLI 可运行完整 V2 A/B。
- Compare JSON 包含全国、31 省、六类企业和机制贡献。

### M4：API、SSE、Replay（H23–H29）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| API-200 | REST 请求/响应升级到 V2 | 已完成 | MODEL-202, SIM-203 |
| API-201 | 企业类型元数据接口 | 已完成 | DATA-200 |
| API-202 | 企业 SSE 事件与恢复 | 已完成 | SIM-203 |
| STORE-200 | Replay/Checkpoint V2 | 已完成 | SIM-204 |
| API-203 | 稳定错误码与审批保护 | 已完成 | API-200 |

退出条件：

- API 可完成 T0–T5 和 A/B。
- SSE 可区分中央、省级、企业和环境事件。
- 未审批创建分支被服务层拒绝。
- Replay 可读取任一企业群体的 Action 和贡献。

### M5：Stitch React 前端（H29–H39）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| WEB-200 | Stitch Token、字体、图标、AppShell | 已完成 | DOC-200 |
| WEB-201 | 四路由和路由门禁 | 已完成 | WEB-200, API-200 |
| WEB-202 | 中央政策设定页 | 已完成 | WEB-201 |
| WEB-203 | 全国推演、真实地图、行动流 | 已完成 | WEB-201, API-202 |
| WEB-204 | 省企详情与证据抽屉 | 已完成 | WEB-203 |
| WEB-205 | 干预审批三栏页 | 已完成 | WEB-201 |
| WEB-206 | A/B 双地图与企业迁移 | 已完成 | WEB-203, SIM-206 |

退出条件：

- 四个 URL 可直接打开并受状态门禁保护。
- 所有核心 CTA 调用真实 API。
- 河南抽屉首屏显示六类企业、预警和中央研判入口。
- 全国页和 A/B 页使用离线矢量地图，不使用截图。
- 1440×900 无核心内容遮挡。

### M6：Live、缓存、可靠性与视觉 QA（H39–H45）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| AI-202 | Live 企业批量结构化输出 | 已完成 | AI-201 |
| AI-203 | 默认场景完整缓存 | 已完成 | AI-202 |
| QA-200 | 31×6 Smoke 和三模式测试 | 已完成 | AI-203 |
| QA-201 | 前端 E2E 与可访问性 | 已完成 | WEB-206 |
| QA-202 | Stitch Design QA 迭代 | 已完成 | WEB-206 |

退出条件：

- Live、Cache、Fallback 三种模式行为清楚。
- 31/31 省与 186/186 企业主体完整。
- `design-qa.md` 最终结果为 `passed`。
- 禁止文案和单位扫描通过。

### M7：产品冻结（H45–H48）

| ID | 工作 | 预计 | 依赖 |
|---|---|---:|---|
| DEMO-200 | 连续 3 次端到端产品运行 | 已完成 | M6 |
| QA-203 | 最终验收与已知限制 | 已完成 | DEMO-200 |
| RELEASE-200 | 冻结依赖、模型、机制和默认缓存 | 已完成 | QA-203 |
| BUFFER | 只修 P0 阻断问题 | 未使用 | 全部 |

冻结规则：

- H44 后不升级依赖、不换模型、不改核心公式。
- 只修主流程、数据正确性、合规表达和明显视觉阻断。
- 不增加产品角色、政策场景和新页面。

---

## 9. P0 Backlog

### 9.1 文档与底座

- [x] DOC-200 用户批准 V2 文档组
- [x] FOUND-200 修复统一命令
- [x] FOUND-201 记录 V1 基线
- [x] ADR-200 冻结 V2 Schema/API/Event

### 9.2 领域与数据

- [x] MODEL-200 PolicySchema V2
- [x] MODEL-201 企业领域模型
- [x] MODEL-202 World/Comparison V2
- [x] DATA-200 企业原型与 provenance
- [x] DATA-201 31×6 完整数据

### 9.3 Agent 与环境

- [x] AI-200 Fake/Cached 企业批量 Provider
- [x] AI-201 企业 Agent、修复与 fallback
- [x] AI-202 Live 企业批量 Provider
- [x] AI-203 默认缓存
- [x] SIM-200 设备更新环境机制
- [x] SIM-201 河南纵向闭环
- [x] SIM-202 31 省扩展
- [x] SIM-203 T0–T5
- [x] SIM-204 不可变 Checkpoint
- [x] SIM-205 分支隔离
- [x] SIM-206 A/B 与企业迁移

### 9.4 API 与存储

- [x] API-200 V2 REST DTO
- [x] API-201 企业元数据
- [x] API-202 企业 SSE
- [x] API-203 审批和错误码
- [x] STORE-200 V2 Replay

### 9.5 Stitch 前端

- [x] WEB-200 Design Token 与 AppShell
- [x] WEB-201 四路由门禁
- [x] WEB-202 中央政策页
- [x] WEB-203 全国推演与地图
- [x] WEB-204 省企/证据抽屉
- [x] WEB-205 干预审批页
- [x] WEB-206 A/B 对照页

### 9.6 QA 与冻结

- [x] QA-200 31×6 Smoke
- [x] QA-201 E2E/可访问性
- [x] QA-202 Design QA passed
- [x] QA-203 最终验收
- [x] DEMO-200 三次连续运行
- [x] RELEASE-200 产品冻结

---

## 10. 前端交付契约

### 10.1 正式路由

```text
/experiments/new
/experiments/:id/live
/experiments/:id/intervention
/experiments/:id/compare
```

抽屉由查询参数深链：

```text
?province=41
?evidence=<evidence-ref>
```

### 10.2 视觉来源映射

| 正式体验 | Stitch 来源 |
|---|---|
| 中央政策设定 | `_1/screen.png` |
| 全国实时推演 | `_2/screen.png` |
| 省企详情抽屉 | `_3/screen.png` 的内容层级 |
| T3 干预审批 | `_4/screen.png` |
| A/B 对照 | `a_b/screen.png` |

正式实现必须同时遵守 `STITCH_FRONTEND_SPEC.md` 中的修正规则。

### 10.3 地图交付门禁

- 使用 ECharts `registerMap` 注册项目本地矢量数据。
- 地图数据必须记录来源、许可、获取日期和必要审图信息。
- 与自然资源部标准地图服务提供的标准地图进行边界核对。
- 地图组件必须支持 31 省着色、选择、键盘焦点、图例和无障碍名称。
- 未完成合规检查时不得用截图、模糊底图或手绘轮廓冒充正式地图。

---

## 11. 测试计划

### 11.1 领域测试

- Policy 工具结构和技术结构权重。
- EnterpriseAction 枚举、组合和数值范围。
- 每省六类企业唯一性。
- 31×6 完整性。
- NaN/Infinity 防护和 0–100 clamp。
- 企业贡献、省级贡献与总变化一致。

### 11.2 Agent 测试

- Fake Provider 合法输出。
- 一次返回六类企业。
- 缺类、重复类、Schema 外字段被拒绝。
- 第一次失败修复一次。
- 第二次失败整省 fallback。
- 缓存键包含完整输入和版本。

### 11.3 分支与 API 测试

- 非法阶段转换。
- 未审批干预拒绝。
- Control/Treatment 父检查点一致。
- 创建 Treatment 不改变 Control。
- EventEnvelope V2 兼容。
- Last-Event-ID 去重。
- Replay 可恢复企业 Action。

### 11.4 前端测试

- 四路由状态门禁。
- 中央政策非法参数不能审批。
- 31 省可点击且当前阶段正确。
- 河南抽屉显示六类企业。
- 数据质量显示类别而非伪置信度。
- 预期方向显示“待验证”。
- 未审批不能创建 Treatment。
- A/B 两侧同一父检查点。
- 禁止现实金额、现实预测百分比和“优化方案”预判文案。
- Loading/Empty/Error/Fallback/断线状态。
- 键盘焦点、标签和色彩之外的状态表达。

### 11.5 E2E

```text
打开中央政策页
→ 生成并批准政策
→ 运行 T1–T3
→ 从地图打开河南省企详情
→ 验证六类企业和传统 SME 观望告警
→ 打开中央研判
→ 审批干预
→ 运行 Control/Treatment 到 T5
→ 查看双地图、企业迁移和证据抽屉
```

### 11.6 视觉 QA

- 1440×900 下逐页比较 Stitch 源图与正式实现。
- 1280 宽验证核心操作可用。
- 对字体、间距、颜色、图像/地图、图标和文案分别检查。
- 每次 P0/P1/P2 修复后重新截图比较。
- 根目录生成 `design-qa.md`，`final result` 必须为 `passed`。

---

## 12. 命令契约

保留以下统一入口：

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

M0 先修复脚本导入路径，再把 V2 验证接入相同命令。不得为通过测试而跳过断言或隐藏 fallback。

---

## 13. 风险触发器与砍项

| 触发器 | 立即动作 |
|---|---|
| H8 仍无 V2 完整 Schema | 停止前端开发，集中冻结模型和数据 |
| H15 河南六企业闭环未通 | 停止 Live Provider 和地图动效，修内核 |
| H23 尚无 31×6 A/B JSON | 暂停数据精修，优先分支和 Comparison |
| H29 API 不能运行到 T3 | 停止 Stitch 视觉实现，修主流程 |
| H39 四路由未连通 | 停止 P1 和动效，全员完成核心体验 |
| H42 Live 不稳定 | 默认强制 Cache，Live 标为实验模式 |
| H45 Design QA 未通过 | 只修 P0/P1/P2，不增加内容 |

砍项顺序：

1. 多个干预选项。
2. 复杂 Replay 页面。
3. 高级地图动画。
4. 复杂筛选器。
5. Live 企业展示，保留透明 Cache/Fallback。

不可砍掉：国务院用户、31 省、六类企业、结构化企业 Action、确定性环境、审批、同源 A/B、企业迁移、Stitch 四路由、免责声明。

---

## 14. 当前状态

| 里程碑 | 状态 | 说明 |
|---|---|---|
| 文档评审门禁 | Complete | V2 文档已经用户批准 |
| M0 基线修复 | Complete | V1 回滚提交 `6ea8e9d`；V2 契约冻结 |
| M1 V2 Schema/数据 | Complete | Policy V2、企业 Schema、31×6 数据和 provenance 完成 |
| M2 企业 Agent/环境 | Complete | 三 Provider、企业批量决策、fallback 和设备更新机制完成 |
| M3 阶段/A-B | Complete | T0–T5、审批/拒绝、同源分支与企业迁移完成 |
| M4 API/SSE | Complete | V2 DTO、幂等、企业事件、Evidence 与 Replay 完成 |
| M5 Stitch 前端 | Complete | 四路由、两抽屉、真实 API/SSE 和本地地图完成 |
| M6 可靠性/视觉 QA | Complete | Cache/Fake、两条浏览器 E2E 与 `design-qa.md` passed |
| M7 冻结 | Complete | 依赖、机制、默认缓存和产品边界冻结 |

### 当前唯一下一任务

保持默认 Cache 演示配置；如需公开部署，先完成标准地图使用与编辑后审核要求的人工合规复核。

---

## 15. V2 Definition of Done

- [x] V2 文档组获得用户批准。
- [x] 1 个中央 Agent、31 个省级 Agent、186 个企业群体 Agent 有合法输出或显式 fallback。
- [x] 所有结果由确定性环境计算并带机制贡献。
- [x] T3 Checkpoint 不可变，A/B 同源隔离。
- [x] 用户审批控制所有中央政策改变。
- [x] 四个正式路由和两个抽屉真实可操作。
- [x] 全国和 A/B 使用经过来源核验的 31 省矢量地图。
- [x] SSE 恢复和单省失败不破坏完整实验。
- [x] 默认场景有完整离线缓存。
- [x] 31×6 Smoke、分支隔离、核心 E2E 通过。
- [x] `design-qa.md` 为 `passed`。
- [x] 三次连续产品运行成功。
- [x] 数据质量、版本、seed、证据和免责声明可见。
- [x] README 与实际运行方式一致。
