# 13110 V3.2 产品旅程与 Fake Agent 重构开发计划

> 对应 PRD：[PRD_省域政策多智能体推演平台.md](./PRD_省域政策多智能体推演平台.md)
> 前端规范：[docs/specs/STITCH_FRONTEND_SPEC.md](./docs/specs/STITCH_FRONTEND_SPEC.md)
> 计划版本：V3.2 M35（Presentation 因果舞台重建）
> 更新日期：2026-08-14
> 当前门禁：只以 `apps/presentation` 为产品界面，完成强类型展示投影、因果链、博弈层、分支隔离、字段泄漏扫描、三类 E2E 和四画布 Design QA

2026-08-14 公网维护项：Presentation 原始方案保持 `95%/90%/85%`，新建实验的干预方案预设保持 `96%/93%/82%`。旧缓存因早期互动校验缺口已隔离；`m34-decision-quality-v1` 门禁重建后，公网冷/热两次同语义全年度运行均为 530 次调用零 fallback，消息/会话完整，第二次缓存文件数 `1487→1487`，退出条件已满足。详见 `docs/adr/ADR-374-m354-deepseek-cache-quality-gate.md`。

---

## 0. V3.2 五个实施门禁

| 门禁 | 状态 | 退出条件 |
|---|---|---|
| G1 文档与 Schema | In Progress | PRD、计划、AGENTS、前端规范、README、ADR 和 M31 版本对象一致 |
| G2 解读与 Fake Agent | In Progress | 省企 0–2 资源包、明确接受/拒绝、31 省明确车企决定与 226 次调用通过契约测试 |
| G3 Orchestrator 与平台能力 | In Progress | Strategy Market v2、环境贡献、SSE、Replay、Audit 和 M31 缓存键一致 |
| G4 React 六步旅程 | In Progress | 差异地图、互动决策台、Province/Automaker 联动与三画布响应式通过 |
| G5 全量验收 | Reopened | M31 三类 E2E、全量命令、Luna 缓存、三画布 QA 与禁止文案扫描通过 |

M30 对象与缓存保持只读。M31 活动版本为 `baseline-snapshot-v2`、`province-resource-envelope-v2`、`province-action-v7`、`automaker-action-v4`、`decision-trace-v3`、`checkpoint-v6`、`branch-v7`、`world-state-v8`、`comparison-v8`、`event-v8`、`strategy-market-v2` 和 `nev-policy-env-v5`，使用独立 `v3_2_m31_*` 缓存命名空间。

### M31 显式决策与互动主画布门禁

| 任务 | 状态 | 验收点 |
|---|---|---|
| M31-1 契约与决策边界 | In Progress | 两类 0–2 提议互不占用；不发起、维持、接受、拒绝均可追溯；车企 31 省均为明确决定 |
| M31-2 环境与可追溯性 | In Progress | 每份资源包逐项响应、每车企最多 5 项接受、无效/拒绝零贡献、Cache/Audit/SSE 使用 M31 版本 |
| M31-3 互动主画布与地图 | In Progress | 差异地图默认、动态色阶、空值纹理、互动台和地图/详情/抽屉联动，无横向滚动 |
| M31-4 验收 | Pending | 三类实验、全量命令、缓存验证、三画布 QA、地图几何校验和禁止文案扫描通过 |

### M32 前端产品化与文案收敛

- 当前 React V3.2 页面遵循“方案、行动、结果优先”；方法与数据页是唯一技术审计入口。
- 省份详情收敛为政策配置、企业互动、竞争与协同、推演影响四张结果卡；Live、主体、车企侧栏、设置和结果页不展示内部规则或开发字段。
- 本轮不修改 API、Schema、推演或缓存；验收只要求前端构建与三画布人工检查。

### M30 上下文驱动互动门禁

| 任务 | 状态 | 验收点 |
|---|---|---|
| M30-1 资源与上下文 | Complete | M29 4,527 事实、711 特征、282 关系边作为输入；关系不直接决定行动 |
| M30-2 3A/3B 策略市场 | Complete | 31 省自主提议、全量冻结、逐项响应；网外对象可用且需证据 |
| M30-3 追溯与 API | Complete | 226 次主体调用、DecisionTrace v2、Strategy Market、Presentation Summary、Audit/Evidence |
| M30-4 产品展示 | Complete | Live、Province、Automaker、Compare、Methods 已接入真实运行对象 |
| M30-5 Luna 缓存与总验收 | In Progress | 全量命令、三类 E2E、fallback 缓存、三画布 QA 与独立 Luna 线程审阅已通过；真实 Luna Provider 缓存等待 API Key |

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
- `docs/validation/design-qa.md` 的 V3 结果为 `passed`。
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

运行模式入口固定为：

- `make dev-api`：本地开发，强制 `POLICYSCOPE_RUN_MODE=fake`。
- `make start-api`：线上部署默认 `POLICYSCOPE_RUN_MODE=cache` 与 `POLICYSCOPE_CACHE_MISS_MODE=live`，并要求部署环境安全注入 DeepSeek API Key。
- `cache`：本地仍只供预计算、回归和离线可复现验证；公网作为默认主链路，miss 时 DeepSeek 生成、强校验并回写，模型失败才显式 fallback。

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
- [x] `docs/validation/design-qa.md` 的 V3 `final result` 为 `passed`。
- [x] 无现实预测、企业承诺、未授权 Logo、官方身份暗示或最优政策结论。

---

## 16. V3.1 M21–M28 增量里程碑

| 里程碑 | 状态 | 退出证据 |
|---|---|---|
| M21 文档与 ADR | Complete | PRD、AGENTS、计划、前端规范、DESIGN、README、Design QA 与 ADR-310 同步；用户副本和 `prototypes/` 未覆盖 |
| M22 Schema、数据与网络 | Complete | V5 World/Comparison、5 模板、31 省四项代理字段与 provenance、观察/协作资格边验证 |
| M23 Provider 与两轮交互 | Complete | Fake/Cache/Live 支持信号与响应；Round 1 全量冻结后启动 Round 2；主体级 fallback |
| M24 事件环境 | Complete | 技术、法规、油价、电池、Peer 与双向协作贡献进入 `nev-policy-env-v2` |
| M25 Orchestrator 与审批 | Complete | `awaiting_event`、一次原子审批、两种同源模式及唯一主动差异校验 |
| M26 API/SSE/Audit/Evidence | Complete | 三个事件 REST、9 类 SSE、Replay、决策/机制 Audit、`scenario:`/`interaction:` |
| M27 五路由前端 | Complete | 模式选择、同政策确认、事件实验台、事件/交互图层、省级链与模式化 Compare |
| M28 Cache/E2E/Design QA | Complete | 30 场景/2047 对象缓存矩阵；连续三次 281/281 与 219/219 命中；两模式三画布 E2E、Design QA 与禁止文案扫描通过 |

V3.1 调用预算：政策干预模式 281 次；事件反事实模式 219 次，其中 Control 无事件不产生伪交互调用。缓存矩阵按公共首年语义输入去重，不按实验 ID 或审批时间重复。

### V3.1 后续数据任务状态

M29 已作为 V3.2 独立事实层完成；V3.1 代理字段和缓存仍只读保留，不回写 M29 结果。

### M29：省级真实事实层与 Peer 语义拆分（M28 后启动）

状态：Complete（2026-08-13）。活动数据版本为 `nev-m29-2025-v2`，快照哈希由基线元数据接口公开并纳入缓存键。

- 建立 31 省经济原始事实、产业结构原始事实与近 3–5 年历史政策证据表。
- 建立 31 省新能源汽车产业与市场基线、真实电池/整车节点、地理/物流距离矩阵和省际产业链关系。
- 补齐智驾、法规试点、油价/出行成本和供应链互补四类事件敏感度原始输入。
- 按集团、品牌、上市主体和生产基地口径补齐 10 家车企真实冻结基线。
- 每个派生指数保存输入字段、权重、方向、缩尾和归一化版本，支持从 UI Evidence 反查原值。
- Profile/Persona/Prompt 分离结构能力、历史偏好和当期响应，移除任何省份刻板性格捷径。
- 将观察、竞争和协作三类 Peer 网络拆分为独立版本、边和 provenance。
- 验收依据固定为 `docs/data/PROVINCE_PROFILE_DATA_REQUIREMENTS_V3_1.md`。

M29 v2 对用户统一显示“可信数据”；直接来源和具备合理置信度的跨来源推算均可使用。每条记录仍保存原值、单位、年份/有效期、机构、链接、统计口径、转换公式和方法版本。

验收结果：整合 292 个来源、4527 条可信事实、65 条政策事实、48 个产业节点、90 条省际关系、711 个派生特征和 1488 条公路/铁路距离；177 项需求全部为 `accepted_trusted`。V3.2 已接入 `province-profile-v6`、`automaker-profile-v2`、`province-relation-network-v3` 及 `fact:`/`feature:`/`relation:`/`source:` Evidence。

## 24. M32 / v9：省际竞争、闭环谈判与严格 Top-K 资源博弈

状态：In progress（2026-08-13）。M31 保持只读；M32 新建 `v3_2_m32` 运行、缓存和验收命名空间。

| 工作项 | 状态 | 退出证据 |
|---|---|---|
| M32.1 v9 Schema / 环境 | In progress | 可反算省级效用、竞争损失环境负机制、Top-K 配额与守恒、反报价状态机 schema 测试 |
| M32.2 七轮编排 / Audit | In progress | 双分支报价与回应冻结门禁、308 调用、Replay/Audit/Evidence 链路 |
| M32.3 API / 缓存分派 | In progress | `product_version=v3_2_m32`、v9 投影、独立缓存键、SSE 恢复与旧对象只读 |
| M32.4 Live / Province / Automaker / Compare | In progress | 竞争/协同/Top-K 地图链、谈判台、效用拆解与分支对比 |
| M32.5 全量验收 | Pending | 三类 E2E、缓存一致性、三画布 QA、地图几何、全量命令与禁止文案扫描 |

## 25. M33：独立全景推演厅

状态：M33 complete / frozen（2026-08-13）。独立大屏、事件与七轮闭环、五幕路演、结果对照和可靠性门禁均已完成；旧 `apps/web` 继续作为研究工作台和兼容入口保留。

| 阶段 | 状态 | 退出证据 |
|---|---|---|
| M33.0 契约冻结 | Complete | ADR-350、`docs/specs/PRESENTATION_HALL_SPEC.md`、PRD、计划、AGENTS、前端规范与 DESIGN 已同步；Pydantic/TypeScript 契约、回归与文档检查通过 |
| M33.1 地图与动画技术验证 | Complete | 本地校验几何、31 省绑定、Delta、弧线、镜头、1080p/4K 60 FPS、低动效和 SVG 降级通过；证据见 `docs/validation/M33_MAP_ANIMATION_TECH_VALIDATION.md` |
| M33.2 演示投影 API | Complete | 两个只读接口、10 个合法冻结帧、事件节点、六类覆盖层、Replay 映射、旧帧哈希稳定性和只读边界通过 Schema/API/Replay 测试；证据见 `docs/validation/M33_PRESENTATION_API_VALIDATION.md` |
| M33.3 独立大屏壳层 | Complete | 地球开场、全屏 HUD、GovSim Glass UI Kit、十入口功能坞、浮层/Side Sheet、三模式、真实 Timeline/Frame、事件节点、可拖动时间轴和省域联动通过；证据见 `docs/validation/M33_PRESENTATION_SHELL_VALIDATION.md` |
| M33.4 事件与七轮闭环 | Complete | 五项版本化事件目录、三触发边界、七轮单屏推进、SSE 恢复和资源守恒矩阵通过契约/API/E2E |
| M33.5 路演与结果 | Complete | 五幕摘要、单图 Delta、同步 A/B、三机制链、键盘遥控、全屏、四档变速与复位通过正式 E2E |
| M33.6 可靠性与冻结 | Complete | 1080p/2K/4K、连续播放、断网保帧、WebGL→SVG 降级、禁止文案、Fake/Fallback 标签、全量测试与 Design QA 通过 |

### M33.0 本轮工作

- 冻结单屏三模式和 `/experiments/:id/present`。
- 将突发事件升级为一级模块和版本化可扩展目录；现有五个模板继续作为首批正式模板。
- 冻结可拖动时间轴的业务帧、吸附、动画、键盘和真实性边界。
- 定义 Presentation DTO 与现有 API 映射，标出必须新增的只读投影接口。
- 保持七轮 Orchestrator、308 调用预算、同源 A/B、环境权威和 Evidence 边界不变。

### M33.0 退出门禁

只有以下条件全部满足才能进入 M33.1/M33.2：

1. 文档一致性检查通过。
2. Presentation DTO 进入 Pydantic 和 TypeScript 严格类型并有契约测试。
3. M32 车企详情的反报价响应过滤缺陷修复。
4. 用户可见事件文案不把示例战争、油价或法规写成现实预测。

退出结果：上述四项于 2026-08-13 全部通过。M33.1 为当前唯一下一阶段；在地图、动画与降级技术门禁通过前，不开始运行时页面。

### M33.1 退出结果

- 冻结标准地图已确定性生成只读 WebGL 展示 GeoJSON：31 个省域进入推演，香港、澳门、台湾作为非交互版图上下文；逐区域源路径哈希、根级几何哈希和声明 bbox 校验通过。
- MapLibre/deck.gl 本地渲染完成 Delta 填色、选择、事件点、弧线和镜头验证；无远程底图或运行时 CDN。
- 1920×1080 与 3840×2160 连续播放均实测 60 FPS、P95 17.6 ms；SVG 容错和低动效路径通过。
- 详细证据见 `docs/validation/M33_MAP_ANIMATION_TECH_VALIDATION.md`。该退出记录形成时，M33.2 是下一阶段；当前 M33.2–M33.6 均已完成。

### M33.2 退出结果

- `GET /presentation/timeline` 与 `GET /presentation/frames/{frame_id}` 已接入 M32 Orchestrator，且调用前后 WorldState 完全一致。
- 完整无事件实验投影政策输入、方案冻结、七轮和结果复盘共 10 帧；事件实验在合法触发边界增加 Marker 与 Event Frame。
- 省域值、竞争/协同/谈判/Top-K/车企/事件覆盖层、六项指标和 A/B Delta 均由已提交 DTO 投影，每帧保留 Replay 事件、Evidence 和稳定哈希。
- Simulation 48/48、API 7/7、M33.2 聚焦 10/10、前端类型与生产构建通过；详细证据见 `docs/validation/M33_PRESENTATION_API_VALIDATION.md`。
- 该退出记录形成时，M33.3 正式壳层是下一阶段；当前已完成并冻结。

### M33.3 开场镜头先行子项

- 用户于 2026-08-13 明确授权该可独立验证的壳层子项先行；当时不改变 M33.2 仍为业务接入前置门禁。
- 已实现本地 MapLibre 地球、Natural Earth 公共领域陆地几何、31 省中国高亮、约 4.5 秒旋转与拉近、淡入全国省域地图、跳过、重播和低动效交接。
- 1920×1080、1366×768 与 3840×2160 浏览器检查通过；4K 主舞台交接后实测 60.1 FPS、P95 17.7 ms，无控制台错误或警告。
- 本子项完成不等于 M33.3 全部完成。M33.2 现已通过，正式 HUD、功能坞、运行时浮层、三模式和权威时间轴可以开始接入。

### M33.3 视觉实现约束

- 建立 GovSim Glass UI Kit：Floating Glass Panel、Glass Pill/Chip、Floating Segmented Control、单指标 Metric Card、Context Popover、Timeline Rail、Command/Scenario Bar 与 Bottom/Side Sheet。
- 坚持“背景是主内容，玻璃只是工具”；地图可见面积保持 70%–80%，不使用玻璃卡片网格重建 SaaS Dashboard。
- 使用三级渐进披露：态势与动作 → 单项指标 → 方法、数据和 Evidence；Agent 博弈优先表现为地图动作、关系线和短标签，而不是日志墙。
- 产品定位保持 `Workbench = 操作复杂系统`、`World View = 看见复杂系统`；旧工作台保留研究用途，全景推演厅专注理解与路演。

### M33.3 退出结果

- `apps/presentation` 已切换为正式 `/experiments/:id/present`，并提供无实验 ID 时的真实演示实验启动流程。
- 根入口已重排为“地球开场 → 全国版图接管 → 约 2 秒后配置弹窗”；配置以东中西中央承担比例为首 Tab，突发事件为默认关闭的可选 Tab，无事件与有事件分别走真实 `policy_comparison` / `policy_stress_test` 设计。
- 根入口用户可见旅程收敛为“实验配置 → A/B 实验设计与唯一主动差异”两页。配置提交后顺序确认中央政策解读，设计确认后顺序冻结代理数据基线；原 API 门禁与幂等性保留。
- TanStack Query 分别读取 Timeline 与当前 Frame；地图值、覆盖层、事件节点、关键变化、六指标和哈希均来自 M33.2 冻结投影。
- GovSim Glass UI Kit、三模式、十入口工具坞、单主面板、Context Popover、Side Sheet 和地图主内容比例落地，未重建 SaaS 卡片网格。
- 时间轴的拖动吸附、播放/暂停、前后帧、节点跳转、变速和复位通过；突发事件帧和省域点击与当前帧联动。
- `npm run typecheck`、`npm run build`、1280×720/1366×768 浏览器交互、无溢出和 console 零错误/警告通过；视觉对照没有未闭环 P0/P1/P2。
- 详细证据见 `docs/validation/M33_PRESENTATION_SHELL_VALIDATION.md`；该退出记录形成时，M33.4 是下一阶段，当前 M33.4–M33.6 均已完成。
- 2026-08-13 用户复核后追加地图校准：开场光点改为北京真实经纬度；展示投影按冻结 SVG 宽高比锁定 Web Mercator，经度跨度不再造成横向拉伸，贝塞尔采样从 8 提升至 24，并加入几何回归门禁。

### M33.4–M33.6 最终退出结果

- `presentation-event-catalog-v1` 以五项冻结情景对外提供三个触发边界、三档强度和两种分支范围；五组高风险矩阵全部完成七轮。
- 七轮在同一大屏逐轮推进，SSE 只通知事实并支持 Last-Event-ID 恢复；断网时保留最后完整帧。
- Story 绑定后端五幕摘要；Compare 默认权威 Delta，可切换镜头、选择和值同步的 A/B 双世界，并展示 Gap、财政代价、受益/承压省份和三条机制链。
- WebGL 初始化或上下文失效时切换本地 SVG 兼容地图，31 省点击、时间轴和业务操作保留。
- 2026-08-13 追加全国版图完整性验收：WebGL、SVG 降级和旧工作台均从冻结标准地图带入香港、澳门、台湾；三者为非计算 `territory-context`，不改变 31 省 Agent、业务帧、指标或调用预算。
- 1920×1080、2560×1440、3840×2160 完整画布通过；详细命令与证据见 `docs/validation/M33_PRESENTATION_FINAL_VALIDATION.md` 和 `docs/validation/design-qa.md`。

### M33 用户复审回归封口

- 根据 2026-08-13 用户提供的 GPT-5.6 Pro 审查报告，已封口 MapLibre/地球实例生命周期、Live 新增帧顺序、省份/车企/事件主体渲染、动态且 A/B 共用色阶、错误重试、SVG 键盘、分支选择真值和事件暴露投影。
- V3.2 Runtime 使用按实验惰性恢复、同目录原子快照和异步落盘；重启后 World/Replay/Comparison/SSE 游标连续性已有 Orchestrator 与 API 回归。
- Presentation Frame V1 不具备逐轮 Control/Treatment 双分支关系谱系；当前 A/B Split 安全地不复用 Treatment overlay，并标注“双图仅展示分支结果值”。完整逐轮 A/B 关系必须以 Presentation V2 重新冻结 Schema/Timeline，不在 V1 静默扩展。

## 26. M34：Presentation Hall V2 完整博弈叙事

状态：Implementation active（2026-08-13）。M33 V1 已被 breaking upgrade 取代，只保留历史验收记录；M34 未完成完整门禁前不得重新标记冻结。

| 子项 | 状态 | 退出条件 |
|---|---|---|
| M34.0 V2 契约 | Complete | Timeline 轻量索引、同步双分支 Frame、Decision/Thread/Divergence/Spotlight Pydantic 与 TypeScript 契约冻结 |
| M34.1 真值投影 | Complete | 七轮同步帧、分支 Replay/Evidence 隔离、事件反事实暴露、跨轮 Thread、边际评估和稳定 Spotlight 通过聚焦测试 |
| M34.2 Live 体验 | Complete | 当前帧懒加载与相邻预取、Game Spotlight、六节拍、行动—回应轨、关键 A/B、全部决策索引与 SVG 语义落地 |
| M34.3 API/E2E | In progress | 纯政策与事件反事实入口通过；七轮叙事已跑通核心链路，完整浏览器矩阵仍需一次无外部中断的正式记录 |
| M34.4 四画布冻结 | In progress | 1366×768、1920×1080、3840×2160 已通过；2560×1440 截图已生成，仍需正式命令结果与禁止文案/地图几何封口 |

M34 保持 M32 七轮、308 次调用和 `world-state-v9` 不变。所有备选是只读决策时点边际评估，不创建权威 Action、World、Comparison 或 Replay；本期只开放 Live/Compare，自动路演和 TTS 后置。

## 27. M34：季度事件驱动 Agent 互动与年度时间轴

状态：Implementation complete / Freeze pending Luna（2026-08-13）。本节是当前唯一 M34 计划；第 26 节作为季度升级前的 Presentation 投影历史记录保留。

| 子项 | 状态 | 退出条件 |
|---|---|---|
| M34.0 文档与 Schema | Complete | ADR-360、PRD、计划、AGENTS、前端与 Presentation 契约一致；v2/v10/v3 Schema 与权限/预算测试冻结 |
| M34.1 季度运行时 | Complete | Q1 每分支 41 主体、Q2–Q4 条件激活、三波屏障、年度资源结转与消息预算通过 |
| M34.2 互动与环境 | Complete | 双向发起、完整交易状态机、四次纯函数季度结算、不可变 Checkpoint 与 Q4 Comparison 通过 |
| M34.3 Provider/API/SSE | Complete | Live Prompt 无确定性候选、一次修复、Cache 哈希、Fake 诚实 fallback、until_tick、interactions 与 Last-Event-ID 通过 |
| M34.4 Web/Presentation | Complete | 0–3 事件配置、下一季度 CTA、年度聚合时间轴、互动下钻与关键 Spotlight 完成 |
| M34.5 缓存与冻结 | In progress | 独立 Fake 缓存三类各三次一致、全量命令、三类 E2E、1920/2560/3840/回退画布 QA 已通过；真实 Luna 缓存等待 `POLICYSCOPE_LLM_API_KEY` |

实施顺序固定为：文档与 Schema → 旧实验 410/季度持久化 → Inbox/消息/调度屏障 → Provider 与季度环境 → REST/SSE → Presentation 与工作台 → 独立缓存和总验收。旧 `exp_m32_*` 只保留文件，不做转换或删除。

2026-08-13 原始冻结验收记录：`make test`（71 Python + 5 Web）、`make test-sim`（63）、`make test-api`（8）、`make lint`、`make validate-data`、`make test-e2e`（5）、`make test-e2e-presentation`（7）和 `make verify-cache-m34` 均通过；活动 M34 文件禁止文案扫描无命中。后续经用户授权完成公网 DeepSeek 接入与 `v3_2_m34_luna` 持久缓存，详见 M35.6 和 ADR-372。

## 28. M35：Presentation Narrative & Game Layer Rebuild

状态：Complete（2026-08-13）。用户已选定并验收“因果舞台”视觉稿；普通 Web 前端不进入本里程碑。

| 子项 | 状态 | 退出条件 |
|---|---|---|
| M35.0 契约与视觉目标 | Complete | ADR-370、PRD、计划、AGENTS、前端规范与 Presentation 规范一致；选定视觉稿进入仓库证据 |
| M35.1 Presentation View Model | Complete | Frame v4 提供逐分支 Story、六段链、主体前缀、事件影响、共享域和稳定 Spotlight；原始运行时字段不进入主舞台 |
| M35.2 因果舞台 | Complete | 顶部问题、左侧六段链、中央世界地图、右侧博弈台、底部四季度章节轨按视觉目标落地 |
| M35.3 Game Layer 与动画 | Complete | Province/Automaker/Event 关系可绘制；提议、反报价、回应、达成/拒绝与结算按因果节拍播放，低动效可用 |
| M35.4 A/B 与探索 | Complete | Control/Treatment 严格隔离，同域 A/B、差值、主体/事件探索和 Evidence 下钻一致 |
| M35.5 验收与启动 | Complete | Projection/DOM 单测、三类 E2E、字段泄漏扫描、1920/2560/3840/SVG QA 和 10 秒可理解性通过；API 与 Presentation 保持启动 |
| M35.6 Cache-first 公网链路 | Complete | 公网 health 为 `cache + live miss`；修改比例的全新实验完成双分支 Q1，合法 DeepSeek 输出回写持久卷，密钥不进镜像/缓存/日志；模型耗尽时显式 fallback |
| M35.7 全国版图补齐 | Complete | WebGL 与 SVG 容错均显示同一冻结标准地图的南海诸岛附图，且不进入 31 省计算或交互；1920×1080 本地与公网画布通过 |
| M35.8 因果侧视镜头 | Complete | Presentation 提供自动/俯视/侧视；行动/回应自动倾斜，结算/差值/年度比较锁定俯视；WebGL、SVG、低动效、测试和 1280/1920 画布 QA 通过 |
| M35.9 DeepSeek 缓存质量门禁 | Complete | v3 cache envelope 与互动一致性校验上线；旧缓存隔离；默认 96/93/82 冷/热全年均 530 次、零 fallback、消息/会话完整且缓存 1487→1487 |
| M35.10 南海诸岛标准地图内标注 | Complete | WebGL 与 SVG 共用的标准地图裁切内容固定于地图画布左下角，不跟随相机、分支或 A/B 视角移动，并与右下角图例分区；采用方角虚线框且无说明卡底色/阴影/外置标题，内部名称、岛礁与断续线继续来自 GS(2016)1609 冻结原件 |
| M35.11 中国地图南海断续线 | Complete | 中国地图本体按参考图比例显示从台湾、海南下方向南延伸的 GS(2016)1609 高对比南海断续线；左下角附图保持视口固定，主地图断续线已机械转换为 46 个地理坐标要素并与版图共用拖动、缩放、俯视、侧视的全部相机变换；WebGL 浏览器联动、SVG 变换组、1280/1920 画布、TypeScript、几何契约与生产构建通过，且不进入计算或交互 |
| M35.14 南海断续线线型与位置修正 | Complete | 移除 46 条官方填充字形直接上图造成的粗重 I/锤形轮廓；从同一 46 条冻结路径按 12 个官方断续符号分组机械求取主轴，生成 12 条细长圆头 LineString，并按项目台湾、海南几何校准东侧—南部—西侧 U 形展示范围；全国俯视、东南放大、拖动与立体侧视均保持地图地理锚定，左下角附图继续视口固定；TypeScript、几何契约与生产构建通过 |

实施顺序固定为：文档与视觉目标 → 后端强类型投影 → 前端显示映射 → 因果舞台 → Game Layer/动画 → A/B/Evidence → 专项验收与启动。M34 Orchestrator、消息权限、季度环境、Checkpoint、Comparison 和缓存不得为展示方便而修改。
