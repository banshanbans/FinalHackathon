# PolicyScope V3.0 新能源汽车补贴与产业布局开发计划

> 对应 PRD：[PRD_省域政策多智能体推演平台.md](./PRD_省域政策多智能体推演平台.md)
> 前端规范：[STITCH_FRONTEND_SPEC.md](./STITCH_FRONTEND_SPEC.md)
> 计划版本：V3.0（已实现并通过 P0 验收）
> 更新日期：2026-08-12
> 当前门禁：M13–M20 已形成实现与验证证据；V3.0 进入冻结维护，新增范围需重新评审契约

---

## 1. V3.0 最终交付目标

V3.0 最终应形成一个可在本机稳定运行和演示的地图优先 Web 产品，完整跑通：

```text
中央层面用户设定西部/中部/东部中央承担比例
  → 中央政策研判 Agent 生成结构化指令
  → 用户批准
  → Y1_Q1：31 省配置消费端/固定成本/可变成本补贴
  → Y1_Q2：10 家真实头部车企模拟 Agent 生成全国市场与产能行动
  → Y1_Q3：确定性环境传播需求、成本、供应链和财政影响
  → Y1_Q4：年度结算、31 省复盘、冻结首年 Checkpoint
  → YEAR1_REVIEW：中央 Agent 提议一次比例调整
  → 用户批准、修改或拒绝
  → 同一首年 Checkpoint 派生次年原始方案/干预方案
  → Y2_Q1–Y2_Q4：省级与车企在双分支中重新响应
  → COMPLETE：比较 ΔGap、财政、需求、投资集中度与产业集聚度
```

完成标准不是只换文案或地图图层，而是：

- 三档比例是唯一中央主动政策杠杆。
- 央地分担先改变地方配套负担，再影响三类地方补贴配置。
- 31 个省级 Agent 有稳定画像、Peer 输入和结构化行动。
- 10 家真实头部车企各自是一个全国性模拟 Agent，不按省复制。
- 真实企业数据只作为冻结基线，未来结果只使用模拟指数和相对变化。
- 所有需求、财政、成本、投资、Gap 和 HHI 由确定性环境计算。
- 首年年末审批是实际服务端门禁。
- 次年两个分支来自同一不可变首年 Checkpoint。
- 中国地图是 Live 主画布，企业和产业信息使用可切换图层。
- 默认场景可用 Cache/Fallback 离线完成。

---

## 2. 历史基线与迁移定位

### 2.1 V2 已验收基线

V2 已完成制造业设备更新政策域的：

- FastAPI、React 和 Pydantic 工程。
- 31 省、六类合成企业群体、T0–T5、审批、Checkpoint、Replay 和同源 A/B。
- Fake/Cache/Live Provider、离线地图和四路由前端。
- `make test`、`make lint`、`make validate-data`、`make smoke`、连续三次 Cache 和历史 Design QA。

V1 回滚点继续保留在 Git 提交 `12456a3`。

### 2.2 V2.1 未完成验证基线

V2.1 已实现省级 Persona、V3 省级 DTO、审计链、五路由高密度前端和省级策略优先体验，但最终全量门禁、两条 E2E、连续三次 Cache 与新版截图 Design QA 未完成。

V3.0 已成为新的目标产品主线。除非用户另行要求，不再把恢复 V2.1 M12 作为当前下一步；V2.1 代码作为可回退和复用的历史实现保留，不能宣称通过最终验收。

### 2.3 V3.0 迁移性质

V3.0 不是文案换皮，而是以下公共契约迁移：

- 政策域：制造业设备更新 → 新能源汽车消费补贴与产业布局。
- 企业主体：每省六类合成企业 → 10 家全国性真实头部车企模拟 Agent。
- 时间：T0–T5 → 首年季度、年末干预、次年季度。
- 政策杠杆：工具结构 → 西部/中部/东部中央承担比例。
- 企业行动：参与/技改/融资 → 销售投入与建厂/扩产。
- 结果主线：省级策略与企业参与 → ΔGap 与产业空间重构。
- 视觉母版：KPI 驾驶舱 → 中国地图主画布与 GIS 图层。

因此不得通过兼容字段或前端映射把 V2.1 数据伪装成 V3.0。

---

## 3. 不可破坏的 V3.0 产品契约

### C-301 用户拥有两次审批权

初始中央指令未经批准不得进入首年；首年年末建议未经批准不得创建干预方案。中央 Agent 只能建议。

### C-302 三档比例是唯一主动 A/B 差异

默认西部/中部/东部中央承担比例为 95%/90%/85%。三项独立接受 0–100%，不求和；非单调只警告。次年干预方案唯一主动差异是用户批准的三项比例。

### C-303 央地分担只直接作用消费端共担资金

环境先计算地方配套负担和剩余财政空间；省级 Agent 再在消费端、固定成本、可变成本之间配置自主工具。不得写成中央比例直接覆盖三类地方补贴。

### C-304 省级 Agent 是地方政策主体

31 省依据冻结 Profile、Persona、财政空间、WTP、电池距离和 Peer Policy 选择三类补贴结构。省际 MVP 只观察、跟进、差异化或维持，不做自由合作。

### C-305 真实车企只作为模拟主体

固定 10 家：比亚迪、吉利、长安、上汽通用五菱、蔚来、奇瑞、零跑、赛力斯、小米汽车、理想汽车。真实数据只作基线，Action 不代表现实企业决定。

### C-306 Agent 只选择策略

中央、省级和车企 Agent 均不得生成最终需求、财政、投资、产业、Gap 或 HHI 指标。

### C-307 环境确定且可解释

相同 Policy、Profile、Action、版本和 seed 必须生成相同季度状态、年度结果和机制贡献。

### C-308 同源 A/B

次年原始方案和干预方案共享同一不可变首年 Checkpoint、数据快照、Persona、机制、模型/Prompt 版本和 seed 规则。

### C-309 地图是主画布

Live 和 Compare 使用同一离线 31 省矢量地图；三类补贴、WTP、电池节点、车企销售投入和模拟产能活动通过可切换图层呈现。

### C-310 不做现实预测或自动最优

不输出未来现实销量、利润、收入、投资金额、财政金额和具体工厂地址，不宣称找到现实最优比例。

---

## 4. 目标架构与依赖方向

```text
React Web
  → API Client / Hooks
    → FastAPI
      → Application Services
        → SimulationAdapter
          → Central / Province / Automaker Agents
          → Deterministic NEV Policy Environment
          → Checkpoint / Replay / Audit Storage
```

约束：

- Web 只消费 API DTO、WorldState、Comparison 和 Event，不重算权威结果。
- API 路由只做验证、审批检查、服务调用和响应映射。
- Orchestrator 负责阶段顺序和原子提交。
- Provider、环境和前端不得互相绕过应用服务。
- 现有 `AsyncioSimulationAdapter` 继续作为迁移基线，但不得泄漏 V2.1 旧 DTO。
- Checkpoint、Replay、Audit 分责保持不变。

---

## 5. V3.0 公共契约

### 5.0 一致性快照

- 默认政策：西部 95%、中部 90%、东部 85%。
- 阶段：`SETUP → Y1_Q1 → Y1_Q2 → Y1_Q3 → Y1_Q4 → YEAR1_REVIEW → Y2_Q1 → Y2_Q2 → Y2_Q3 → Y2_Q4 → COMPLETE`。
- 十家车企：比亚迪、吉利、长安、上汽通用五菱、蔚来、奇瑞、零跑、赛力斯、小米汽车、理想汽车。
- 六项指标：区域发展差距、中央财政负担、地方财政压力、新能源汽车需求、新增投资集中度、产业集聚度。
- 路由：`/experiments/new`、`/experiments/:id/live`、`/experiments/:id/provinces/:provinceCode`、`/experiments/:id/intervention`、`/experiments/:id/compare`。

### 5.1 版本矩阵

| 对象 | V3 目标版本 |
|---|---|
| 中央政策 | `policy-v3` |
| 省级 Profile | `province-profile-v4` |
| 省级 Persona | `province-persona-v2` |
| 省级 Action | `province-action-v4` |
| 省级 Feedback | `province-feedback-v4` |
| 车企 Profile | `automaker-profile-v1` |
| 车企 Action | `automaker-action-v1` |
| WorldState | `world-state-v4` |
| Comparison | `comparison-v4` |
| Event | `event-v4` |
| Audit 信封 | `audit-record-v1`，继续使用 |

旧 `EnterpriseAction` 和六类企业 DTO 不得作为 V3 车企 Action 复用。

### 5.2 阶段

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

### 5.3 LLMProvider

目标能力：

```python
class LLMProvider(Protocol):
    async def generate_central_directive(...) -> CentralSubsidyDirective: ...
    async def generate_province_action(...) -> ProvinceAction: ...
    async def generate_province_feedback(...) -> ProvinceFeedback: ...
    async def generate_automaker_portfolio(...) -> AutomakerAction: ...
    async def generate_intervention_proposal(...) -> CentralInterventionProposal: ...
    async def generate_central_review(...) -> CentralReview: ...
```

车企调用一次返回全国 31 省市场投入和最多三个产能目标。Persona、Gap、HHI 和环境指标不经过 Provider。

### 5.4 REST 增量

保留现有实验、审批、运行、分支、Compare、Replay、Audit 和 Evidence 路径，新增：

```text
GET /api/experiments/{id}/automakers/{automaker_id}
GET /api/meta/automakers
GET /api/meta/policy-regions
```

### 5.5 前端深链

```text
?company=<automaker-id>
?evidence=<evidence-ref>
?branch=control|treatment
```

---

## 6. 数据迁移计划

### 6.1 省级政策档位

必须提交并验证：

- 东部 9：北京、天津、辽宁、上海、江苏、浙江、福建、山东、广东。
- 中部 10：河北、山西、吉林、黑龙江、安徽、江西、河南、湖北、湖南、海南。
- 西部 12：内蒙古、广西、重庆、四川、贵州、云南、西藏、陕西、甘肃、青海、宁夏、新疆。
- 总数 31，无重复，无遗漏；新疆生产建设兵团不单列为 Agent。

### 6.2 省级 Profile

新增或重建：

- 财政能力与刚性。
- 新能源汽车产业基础。
- 市场需求与 WTP。
- 土地、人才、能源和物流成本代理。
- 充电基础设施。
- 电池供应链距离。
- Peer Group 相似度。

### 6.3 车企 Profile

固定 ID：

```text
byd
geely
changan
sgmw
nio
chery
leapmotor
seres
xiaomi_auto
li_auto
```

每家记录 2025 冻结基线、销量规模/增速、盈利和流动性代理、产能利用代理、渠道覆盖、生产布局、产品结构、技术路线、口径和 provenance。集团/品牌/上市主体口径必须显式说明。

### 6.4 外生变量

- 电池产业节点及能力代理。
- 省际/节点距离矩阵。
- 省级 WTP 组成字段。
- 省级 Peer Network。

### 6.5 质量规则

- 省级与外生字段可为 `verified/proxy/demo`。
- 真实车企关键字段只允许 `verified/proxy`；缺少事实时不得用无来源 demo 冒充。
- 所有字段保存来源、年份、单位、原值、转换和缺失处理。

---

## 7. 机制迁移计划

### 7.1 财政机制

```text
中央承担比例
  → 地方消费补贴配套负担
  → 地方剩余财政空间
  → 省级三类工具强度与结构
```

同时计算中央财政负担和地方财政压力，防止把更高中央比例表达成无代价改善。

### 7.2 需求机制

```text
消费端补贴 + WTP + 车企销售投入 + 渠道覆盖
  → demand_index
```

### 7.3 产业机制

```text
固定成本补贴
  → 进入/扩产门槛

可变成本补贴 + 人才/能源/物流成本 + 电池距离
  → 长期经营成本

企业经营状态 + 省级 Offer
  → simulated_roi_index
  → facility action effectiveness
```

### 7.4 固定/可变成本临界点

环境输出首个 `variable_effect >= fixed_effect` 的季度或规模指数，并记录完整机制解释，不输出现实产量或金额。

### 7.5 区域指标

- 省级发展指数 = 50% 需求 + 50% 产业活动。
- Gap = 31 省等权发展指数的归一化 Gini。
- ΔGap = 次年干预方案 Gap − 次年原始方案 Gap。
- 新增投资集中度和产业集聚度 = 归一化 HHI。

---

## 8. 任务依赖图

```text
DOC-300 V3 文档评审
  → ADR-300 V3 公共契约冻结
      → MODEL-300 Policy/阶段/省级/车企/World/Event
          ├─ DATA-300 三档省份、Profile、WTP、Peer
          ├─ DATA-301 十家车企与 provenance
          ├─ SIM-300 财政/需求/产业/Gap/HHI 机制
          └─ AI-300 中央/省级/车企 Provider
                → ORCH-300 两年阶段、审批和同源分支
                    → API-300 REST/SSE/Replay/Audit/Evidence
                        → WEB-300 地图主画布与五路由
                            → CACHE-300 完整默认场景
                                → QA-300 全量门禁与 Design QA
                                    → RELEASE-300 V3 冻结
```

关键路径：

```text
DOC-300 → ADR-300 → MODEL-300 → DATA/SIM/AI-300
→ ORCH-300 → API-300 → WEB-300 → CACHE-300 → QA-300 → RELEASE-300
```

---

## 9. V3.0 里程碑

### M13：文档评审与契约冻结

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| DOC-300 | 同步 PRD、计划、AGENTS、前端规范、DESIGN、README、Design QA | Complete | 用户方向确认 |
| DOC-301 | 七文档一致性与旧语义扫描 | Complete | DOC-300 |
| ADR-300 | 用户批准主体、阶段、Schema、指标和页面契约 | Complete | DOC-301 |

退出条件：

- 七份文档中的三档默认值、31 省档位、十家车企、阶段、指标、路由和版本完全一致。
- ADR-300 记录用户批准，后续状态按真实迁移进度更新。

### M14：领域 Schema 与数据

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| MODEL-300 | `policy-v3`、阶段和审批对象 | Complete | ADR-300 |
| MODEL-301 | 省级 Profile/Persona/Action/Feedback | Complete | MODEL-300 |
| MODEL-302 | Automaker Profile/Action | Complete | MODEL-300 |
| MODEL-303 | World/Comparison/Event v4 | Complete | MODEL-301, MODEL-302 |
| DATA-300 | 31 省档位、WTP、电池节点、距离和 Peer | Complete | MODEL-301 |
| DATA-301 | 10 家车企 2025 基线与 provenance | Complete | MODEL-302 |

退出条件：

- 31 省档位为 9/10/12 且无重复遗漏。
- 十家车企 ID 唯一，31 省市场行动契约完整。
- 所有真实数据有来源、年份、口径和质量标签。
- 新旧 DTO 不能静默混用。

### M15：Agent 与确定性环境

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| AI-300 | Fake/Cached 中央、省级、车企输出 | Complete | M14 |
| AI-301 | Live、修复一次和主体级 fallback | Complete | AI-300 |
| SIM-300 | 央地分担与地方财政空间 | Complete | M14 |
| SIM-301 | WTP、销售投入与需求机制 | Complete | SIM-300 |
| SIM-302 | 固定/可变成本、电池距离与 ROI | Complete | SIM-300 |
| SIM-303 | Gap、HHI、六指标和机制守恒 | Complete | SIM-301, SIM-302 |

退出条件：

- Agent 只输出 Action。
- 相同输入与 seed 完全确定。
- 固定/可变成本临界点可反算。
- 六项指标与机制贡献守恒。

### M16：两年 Orchestrator、审批与分支

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| ORCH-300 | `SETUP` 与首年 Q1–Q4 | Complete | M15 |
| ORCH-301 | 年末一次建议和人工审批 | Complete | ORCH-300 |
| ORCH-302 | 次年原始/干预双分支 | Complete | ORCH-301 |
| ORCH-303 | `comparison-v4` 与中央复盘 | Complete | ORCH-302 |
| AUDIT-300 | V3 行为、机制和门禁追溯 | Complete | ORCH-303 |

退出条件：

- 首年 Checkpoint 不可变。
- 未审批不得创建干预方案。
- 两分支唯一主动差异为三档比例。
- 拒绝后只运行原始方案，不伪造 A/B。
- 调用预算为中央 3、省级约 124、车企 30。

### M17：API、SSE、Replay 与 Evidence

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| API-300 | V4 DTO 和阶段错误码 | Complete | M16 |
| API-301 | 车企详情、元数据与地区档位接口 | Complete | API-300 |
| API-302 | Event v4、SSE 恢复和 Replay | Complete | API-300 |
| API-303 | Automaker/Mechanism Evidence 深链 | Complete | API-302, AUDIT-300 |

退出条件：

- API 可完成两年流程和拒绝路径。
- Last-Event-ID、去重和 WorldState 恢复可用。
- 完成/fallback 事件可追溯 Audit。

### M18：地图优先五路由前端

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| WEB-300 | V3 AppShell、季度阶段条和路由门禁 | Complete | M17 |
| WEB-301 | 三档比例输入与初始审批 | Complete | WEB-300 |
| WEB-302 | Live 地图主画布与 GIS 图层 | Complete | WEB-300 |
| WEB-303 | 省级详情 V3 信息层级 | Complete | WEB-302 |
| WEB-304 | `?company=` 车企侧栏 | Complete | WEB-302 |
| WEB-305 | 年末三栏审批 | Complete | WEB-300 |
| WEB-306 | 次年 A/B 双地图与 ΔGap | Complete | WEB-302, ORCH-303 |

退出条件：

- 五路由和车企/Evidence 深链可刷新恢复。
- Live 默认地图为地方新能源汽车补贴支持强度。
- 图层切换不触发模型调用。
- 所有真实车企行为显示模拟免责声明。

### M19：缓存、可靠性与可复现性

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| CACHE-300 | 默认首年和次年双分支缓存 | Complete | M16 |
| CACHE-301 | 缓存清单和键完整性 | Complete | CACHE-300 |
| REL-300 | 单省/单车企 fallback 与恢复 | Complete | CACHE-300 |
| REL-301 | 完整流程性能和断线恢复 | Complete | M17, M18 |

退出条件：

- 无网络可完成完整实验。
- 31 省和 10 家车企无静默缺失。
- Fallback 范围在 UI、World、Event、Replay、Audit 一致。

### M20：QA 与冻结

| ID | 工作 | 状态 | 依赖 |
|---|---|---|---|
| QA-300 | 领域、数据、Agent、机制和分支测试 | Complete | M19 |
| QA-301 | API/SSE/Replay/Audit 测试 | Complete | QA-300 |
| QA-302 | 五路由 E2E、可访问性和禁止文案 | Complete | M18, QA-301 |
| QA-303 | 1536×1024、1440×900、1280 Design QA | Complete | QA-302 |
| DEMO-300 | Cache 完整流程连续三次 | Complete | QA-303 |
| RELEASE-300 | 冻结数据、机制、模型和缓存 | Complete | DEMO-300 |

退出条件：

- 全部统一命令通过。
- 两条 E2E 和连续三次 Cache 通过。
- `design-qa.md` 的 V3 结果为 `passed`。
- 无现实预测、企业承诺、官方暗示或最优政策结论。

---

## 10. 前端交付契约

### 10.1 正式路由

```text
/experiments/new
/experiments/:id/live
/experiments/:id/provinces/:provinceCode
/experiments/:id/intervention
/experiments/:id/compare
```

```text
?company=<automaker-id>
?evidence=<evidence-ref>
?branch=control|treatment
```

### 10.2 页面目标

- New：三档比例、政策参考口径、输入模式和初始审批。
- Live：中国地图主画布、季度状态、图层、六指标摘要和事件流。
- Province：财政空间、三类工具、Peer、车企反馈和机制结果。
- Intervention：首年证据、三档建议和人工审批。
- Compare：同源双地图、Gap/ΔGap、财政与产业权衡。

### 10.3 地图图层

```text
local_subsidy_intensity
consumer_subsidy
fixed_cost_subsidy
variable_cost_subsidy
wtp
industry_base
battery_nodes
automaker_sales_activity
simulated_facility_activity
```

同一时刻只允许一个省域填色主图层；节点、工厂和企业活动作为可控覆盖层，避免视觉冲突。

---

## 11. 测试计划

### 11.1 领域与数据

- 95%/90%/85% 默认值与 0–100% 独立范围。
- 非单调梯度只警告，不自动修复。
- 东部 9、中部 10、西部 12，覆盖 31 省无重复。
- 十家车企 ID 和展示名唯一。
- 车企关键字段 provenance 与 `verified/proxy`。
- 三类省级补贴份额和为 1。
- 每家车企每次恰好覆盖 31 省，产能目标最多 3 个。
- Persona 和 Peer Network 确定性。

### 11.2 环境

- 央地分担、地方财政空间和中央/地方负担同时守恒。
- WTP、消费补贴和销售投入的需求贡献可反算。
- 电池距离进入物流成本。
- 固定/可变成本临界季度或规模指数可反算。
- 省级发展指数 50/50 公式。
- 31 省等权 Gini 与 ΔGap 符号。
- 归一化 HHI 边界。
- NaN/Infinity 拒绝与 0–100 clamp。

### 11.3 Agent 与 Provider

- 中央 3 次、省级约 124 次、车企 30 次预算。
- 合法输出、一次修复和第二次失败 fallback。
- 车企缓存键覆盖 31 省 Offer、经营画像和完整版本。
- 不产生 Schema 外字段或现实预测。
- 不保存长思维链和原始无效响应。

### 11.4 阶段与分支

- 初始未审批不能进入 `Y1_Q1`。
- 首年 Q1–Q4 顺序和原子提交。
- 首年 Checkpoint 不可变。
- 每个实验最多一次年末获批干预。
- 未审批不能创建 Treatment。
- 两分支同源且唯一主动差异为三档比例。
- 拒绝后只生成原始方案。

### 11.5 API 与前端

- 五路由、车企侧栏和 Evidence 深链恢复。
- 季度阶段门禁。
- 地图 31 省、所有图层和空值表达。
- 车企侧栏不使用未授权 Logo，模拟免责声明可见。
- Intervention 三栏审批。
- Compare 先显示同源、Gap、ΔGap，再显示其他结果。
- Loading/Empty/Running/Fallback/Failed/Reconnecting。
- 禁止现实金额、销量、利润预测、企业承诺、官方暗示和“最优政策”。

### 11.6 E2E

```text
创建实验并批准 95/90/85
→ 运行首年 Q1–Q4
→ 打开省级详情与任一车企侧栏
→ 查看首年 Checkpoint 和中央建议
→ 修改或批准三档比例
→ 运行次年原始/干预双分支
→ 查看双地图、ΔGap、财政与产业权衡
→ 打开机制 Evidence
```

另一路径覆盖拒绝干预后的次年原始方案单线结算。

---

## 12. 统一命令与发布门禁

继续保留：

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

V3 实现后必须让这些命令覆盖新领域；不得为了通过门禁跳过旧断言、隐藏 fallback 或硬编码结果。

---

## 13. 风险触发器与砍项

| 触发器 | 立即动作 |
|---|---|
| 公共 Schema 未冻结 | 停止代码迁移，先解决契约冲突 |
| 十家车企数据口径无法对齐 | 降为 proxy 并保留原始来源，不伪造精度 |
| 31 省财政机制不守恒 | 停止前端，实现并验证环境内核 |
| 两年流程耗时不可控 | 强制默认 Cache，保留透明 fallback |
| 地图图层互相冲突 | 保留单一主填色层，覆盖层按需切换 |
| Design QA 未通过 | 只修 P0/P1/P2，不增加角色和页面 |

砍项顺序：高级地图动画、复杂排行、多个中央建议、企业细分筛选、Live 展示。不可砍掉三档比例、31 省、十家车企、三类省级工具、两类车企行为、首年 Checkpoint、审批、同源 A/B、ΔGap、Cache/Fallback 和免责声明。

---

## 14. 当前状态

| 里程碑 | 状态 | 说明 |
|---|---|---|
| V2 历史基线 | Complete | 制造业设备更新 V2 已验收 |
| V2.1 实现 | Implemented, verification incomplete | 最终 E2E/Cache/Design QA 未完成 |
| M13 V3 文档 | Complete | 七文档一致性检查与 ADR-300 已完成 |
| M14 领域 Schema 与数据 | Complete | V3 版本矩阵、31 省三区口径、10 家车企和 provenance 已校验 |
| M15 Agent 与确定性环境 | Complete | 三级 Agent、年度行动、Gini/HHI、六项指标和机制贡献已实现 |
| M16 两年 Orchestrator、审批与分支 | Complete | 首年 Checkpoint、两次审批、拒绝单线和唯一分支 ID 已验证 |
| M17 API、SSE、Replay 与 Evidence | Complete | V3 REST/SSE、Replay、Audit 哈希链、Evidence 与元数据接口已接通 |
| M18 地图优先五路由前端 | Complete | 五路由、九类地图语义、车企侧栏、Evidence、Fallback 与重连状态已实现 |
| M19 缓存与可靠性 | Complete | 157 个版本完整缓存条目；连续三次 157/157 命中 |
| M20 QA 与冻结 | Complete | 全量测试、完整/拒绝/警告/重连/Fallback E2E、三画布 30 张截图与 Design QA 通过 |

### 当前唯一下一任务

保持 V3.0 P0 冻结；只有用户批准新的产品范围或契约变更后才进入下一里程碑。

---

## 15. V3.0 Definition of Done

- [x] V3.0 七份文档获得用户批准。
- [x] 新公共契约全部接通且不静默混用 V2.1 DTO。
- [x] 东部 9、中部 10、西部 12 的政策档位完整。
- [x] 31 个省级 Agent 和 10 家车企 Agent 均有合法输出或显式 fallback。
- [x] 真实车企数据有来源、年份、口径和质量标签。
- [x] 所有结果由确定性环境计算并带机制贡献。
- [x] 首年 Checkpoint、年末审批和次年同源分支不可绕过。
- [x] Gap、ΔGap、六项指标和 HHI 可反算。
- [x] 五个路由、车企侧栏和 Evidence 深链真实可用。
- [x] Live 和 Compare 使用地图主画布及真实 V3 DTO。
- [x] 默认场景完整离线缓存可用。
- [x] `make test`、`make lint`、`make validate-data`、`make smoke` 通过。
- [x] 两条 E2E 和 Cache 连续三次通过。
- [x] `design-qa.md` 的 V3 `final result` 为 `passed`。
- [x] 无现实预测、企业承诺、未授权 Logo、官方身份暗示或最优政策结论。
