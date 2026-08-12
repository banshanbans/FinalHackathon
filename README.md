# PolicyScope / 政策涟漪

PolicyScope V3.1 是面向中央层面政策统筹人员的“新能源汽车补贴、产业布局与事件协同多智能体推演台”。V3.0 两年同源推演保持冻结；V3.1 新增冻结事件情景、31 省两轮信号/响应和双向协作传播。

> 研判口径：结果为当前数据、政策参数与机制版本下的模拟指数，用于方案比较，不代表现实政府或企业的未来决定。

## V3.1 当前能力

- 实验创建时选择“政策干预”或“事件反事实”，两个模式都从同一首年不可变 Checkpoint 派生双分支。
- 两分支完成 Y2_Q2 后，用户从 5 个冻结模板与 3 档强度中批准一次事件；未审批不能进入 Y2_Q3。
- 事件分支依次运行 31 省首轮信号、冻结授权 Peer 响应和双向协作匹配，再由确定性环境结算。
- 政策模式证明“只有比例不同、事件相同”；事件模式证明“政策相同、只有事件有无不同”。
- API 版本为 0.5.0，World/Comparison/Event 为 v5，机制版本为 `nev-policy-env-v2`。

## V3.0 冻结基线

V3.0 已完成从 V2.1 历史基线到新能源汽车政策域的全量迁移：

- `policy-v3`、年度阶段、省级/车企/World/Comparison/Event 契约已接通。
- 中央—31 省—10 家车企 Agent、确定性环境、审批和同源 A/B 已可端到端运行。
- REST/SSE、Checkpoint、Replay、Audit、Evidence、完整默认缓存和五路由地图前端已实现。
- 全量测试、两条 Playwright E2E、连续三次 Cache 和三画布 Design QA 已通过。
- V2/V2.1 仅作为历史实现保留，不再是当前可执行产品语义。

详细目标见 [V3.0 PRD](./PRD_省域政策多智能体推演平台.md)、[开发计划](./DEVELOPMENT_PLAN.md) 和 [前端规范](./STITCH_FRONTEND_SPEC.md)。

## V3.0 核心闭环

```text
中央用户设定西部/中部/东部承担比例
  → 中央政策研判 Agent 生成结构化指令
  → 用户批准
  → Y1_Q1：31 省配置消费端、固定成本、可变成本补贴
  → Y1_Q2：10 家车企模拟 Agent 生成全国销售和产能行动
  → Y1_Q3：环境传播需求、成本、供应链和财政影响
  → Y1_Q4：年度结算、31 省复盘、冻结首年 Checkpoint
  → YEAR1_REVIEW：中央 Agent 提议一次比例调整
  → 用户批准、修改或拒绝
  → 同一首年 Checkpoint 派生次年原始方案/干预方案
  → Y2_Q1–Y2_Q4：双分支重新响应和年度结算
  → COMPLETE：比较 ΔGap、财政、需求、投资集中度和产业集聚度
```

## 中央政策杠杆

V3.0 使用 2025 年汽车以旧换新政策作为参考基线：

默认政策为西部 95%、中部 90%、东部 85%。

| 地区档位 | 中央承担比例 | 省份数量 |
|---|---:|---:|
| 西部 | 95% | 12 |
| 中部 | 90% | 10 |
| 东部 | 85% | 9 |

- 用户可直接输入绝对值，也可输入相对参考值的百分点调整。
- 三项分别接受 0–100%，不求和。
- 系统不强制“西部 ≥ 中部 ≥ 东部”；偏离参考梯度时警告但允许实验。
- 三档比例只直接作用消费端汽车以旧换新共担资金，先改变地方配套负担，再间接改变省级自主财政空间。

默认比例依据[国家发展改革委 2025 年“两新”政策通知](https://zfxxgk.ndrc.gov.cn/web/iteminfo.jsp?id=20470)。具体省份档位采用[财政部 2024 年汽车以旧换新补贴中央财政预拨资金表](https://www.ndrc.gov.cn/xwdt/ztzl/tddgmsbgxhxfpyjhx/gzdt/202406/t20240606_1386714.html)中的汽车专项口径，不使用国家统计局四大区域口径。新疆生产建设兵团不作为额外省级 Agent。

## 三级 Agent

### 中央 Agent

- `SETUP`：生成初始三档承担比例指令。
- `YEAR1_REVIEW`：基于首年结果建议一次比例调整。
- `COMPLETE`：生成同源对照复盘。
- 只能建议，不能绕过用户审批或写入最终指标。

### 31 个省级 Agent

- 根据冻结 Profile、Persona、地方财政空间、WTP、电池供应链距离和 Peer Policy 配置地方支持。
- 三类地方工具为消费端、固定成本、可变成本补贴，份额必须合计为 100%。
- 常规 Q1 Peer 响应保持跟进、差异化或维持；V3.1 的 Y2_Q3 事件覆盖层新增受冻结网络约束的 `coordinate`，不提供自由群聊。

### 10 家真实头部车企模拟 Agent

固定代表性主体集合：

1. 比亚迪。
2. 吉利。
3. 长安。
4. 上汽通用五菱。
5. 蔚来。
6. 奇瑞。
7. 零跑。
8. 赛力斯。
9. 小米汽车。
10. 理想汽车。

该名单是用户选定的代表性集合，不宣称严格等同于某一年度销量 Top 10。每家是一个全国性 Agent，每年一次返回 31 省销售/渠道投入组合和最多 3 个模拟建厂、扩产或延迟目标。

真实销量、财报、产能和工厂布局只作为冻结基线。未来销量、利润、成本、投资与财政结果只显示模拟指数、等级和相对变化；不代表现实车企计划或承诺，P0 不使用未经许可 Logo。

## 时间、对照与指标

V3 阶段固定为：

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

首年 Q4 冻结不可变 Checkpoint。次年原始方案和干预方案从同一 Checkpoint 派生，唯一主动差异是用户批准的三档中央承担比例。拒绝干预时只运行次年原始方案，不伪造 A/B。

省级新能源汽车发展指数由需求指数和产业活动指数各占 50%。`Gap` 使用 31 省等权发展指数的归一化 Gini：

```text
ΔGap = Gap_treatment,Y2 − Gap_control,Y2
```

- `ΔGap < 0`：干预方案下区域差距缩小。
- `ΔGap > 0`：干预方案下区域差距扩大。
- `ΔGap ≈ 0`：在当前显示精度和机制阈值内影响有限。

固定六项中央指标：

1. 区域发展差距。
2. 中央财政负担。
3. 地方财政压力。
4. 新能源汽车需求。
5. 新增投资集中度。
6. 产业集聚度。

新增投资集中度和产业集聚度使用归一化 HHI。Agent 不计算上述指标，全部由确定性环境产生。

## V3 公共接口

当前版本为：

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

现有 `audit-record-v1` 信封继续使用。V3 保留实验、省级、审批、分支、Compare、Replay、Audit 和 Evidence 路径，并提供：

```text
GET /api/experiments/{id}/automakers/{automaker_id}
GET /api/experiments/{id}/branches
GET /api/meta/automakers
GET /api/meta/policy-regions
```

上述接口均已实现；边界对象使用版本化 V3 DTO。

## V3 路由与地图

正式路由继续为：

- `/experiments/new`
- `/experiments/:id/live`
- `/experiments/:id/provinces/:provinceCode`
- `/experiments/:id/intervention`
- `/experiments/:id/compare`

深链：

- `?company=<automaker-id>`：车企侧栏。
- `?evidence=<evidence-ref>`：行为链、机制链、版本与来源。
- `?branch=control|treatment`：分支上下文。

Live 使用中国地图主画布，默认显示地方新能源汽车补贴支持强度；可切换消费端、固定成本、可变成本、WTP、产业基础与车企销售投入等图层。Compare 使用同色阶双地图并优先展示 `ΔGap` 与三档比例差异。

## 当前可执行 V3.0 运行时

环境要求：Python 3.11+、Node.js 20+。

```bash
make setup
make dev-api
make dev-web
```

`make dev-api` 会显式锁定 `POLICYSCOPE_RUN_MODE=fake`；本地打开始终使用确定性 Mock Provider，不会调用线上模型。

前端：[http://localhost:5173/experiments/new](http://localhost:5173/experiments/new)
后端健康检查：[http://localhost:8000/api/health](http://localhost:8000/api/health)

运行模式：

- `fake`：确定性 Mock Provider，为本地启动的强制模式。
- `cache`：V3.0 默认演示缓存；预生成场景可 157/157 命中。
- `live`：线上部署模式，兼容结构化模型 Provider，失败时显式回退并记录范围。部署环境必须配置 `POLICYSCOPE_LLM_API_KEY`，并使用 `make start-api`（内部锁定 `POLICYSCOPE_RUN_MODE=live`）启动。

## 验证状态

- 27 项 Python/API 测试与 5 项前端组件测试通过。
- Ruff、格式检查、ESLint、TypeScript 构建、31 省数据和标准地图校验通过。
- Playwright Fake 矩阵为 6 passed、9 个按画布或运行模式设计跳过的重复用例；另有 1 个空缓存 Fallback 实测通过。
- 默认缓存预生成 157 个版本完整条目，连续三次完整流程均为 157/157 命中。
- 1536×1024、1440×900、1280 共 30 张正式运行时截图完成 Design QA，V3 `final result: passed`。
- V2 历史基线仍为 passed；V2.1 未完成验证记录保持历史状态，不沿用到 V3。

详细状态见 [开发计划](./DEVELOPMENT_PLAN.md) 和 [Design QA](./design-qa.md)。

## 文档导航

- [V3.1 产品需求文档](./PRD_省域政策多智能体推演平台.md)
- [V3.1 详细开发计划](./DEVELOPMENT_PLAN.md)
- [V3.1 正式前端规范](./STITCH_FRONTEND_SPEC.md)
- [ADR-310：事件驱动省际协同](./ADR-310-event-driven-interprovincial-coordination.md)
- [Design QA 状态](./design-qa.md)
- [开发 Agent 约束](./AGENTS.md)
- [设计令牌与地图语义](./stitch_policyscope/policyscope/DESIGN.md)
- [地图资源与合规记录](./apps/web/src/assets/maps/README.md)

## 当前唯一下一步

V3.0 继续冻结；V3.1 M21–M28 已完成。下一步按 [V3.1 省级数据采集清单](./docs/data/PROVINCE_PROFILE_DATA_REQUIREMENTS_V3_1.md) 启动 M29，补齐 31 省真实经济/产业/政策事实、真实节点与物流、省际产业链关系、四类事件敏感度原始输入和 10 家车企冻结基线。

V3.1 验证证据：30 个缓存场景生成 2047 个语义去重对象；政策模式连续三轮 281/281 命中，事件模式连续三轮 219/219 命中；两种完整流程均通过 1536×1024、1440×900、1280 画布与无水平滚动检查。当前派生敏感度仍按 `proxy` / `scenario_assumption` 使用，不能标记为真实 `verified` 数据。
