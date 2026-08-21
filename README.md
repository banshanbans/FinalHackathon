# 13110

**抖音 AI 创变者计划 2026 北京全国总决赛作品**

> 面向中央政策统筹场景的新能源汽车产业协同多智能体推演平台

13110 把一项政策调整放入可审计的同源 A/B 模拟环境，让中央、31 个省级 Agent 和 10 家代表性车企模拟 Agent 在约束中动态互动，并把策略、消息、环境结算与年度差异连成可回放的证据链。

`PolicyScope` 仅作为仓库中的代码标识和历史版本名保留；当前对外产品名为 **13110**。

## 30 秒看懂产品

| | 内容 |
|---|---|
| 目标用户 | 中央政策统筹、产业政策研究与跨区域协同分析团队 |
| 核心问题 | 一项政策变量如何经由地方财政、消费需求、企业行动与产业布局层层传导 |
| 产品输出 | 同一基线下 Control / Treatment 两条路径的主体决策、互动记录、季度结算、年度对比与审计证据 |
| 使用价值 | 在政策讨论前显式暴露传导假设、主体反应与权衡，支持方案比较，不替代现实预测 |

## 实机截图

### 季度主体互动

![13110 季度主体互动实机截图](./docs/assets/readme/interaction.jpg)

中央政策信号、省域 Agent、车企 Agent、跨主体连线、因果链和季度章节在同一张可回放画布中展示。

### 年度同源 A/B 对比

![13110 年度 A/B 对比实机截图](./docs/assets/readme/annual-comparison.jpg)

年度结果对比的是模拟指标和相对变化，并保留从指标回到季度决策、消息和证据的追溯路径。

## 产品闭环

```text
政策参数输入与审批
  ↓
中央 Agent 结构化解读 / 实验设计
  ↓
冻结 Baseline 与不可变 Checkpoint
  ↓
派生 Control / Treatment 两条同源分支
  ↓
Q1—Q4 条件激活的省级 / 车企 Agent 互动
  ↓
每季度确定性环境结算 + 不可变 Checkpoint
  ↓
Q4 年度 Comparison / 中央复盘
  ↓
Replay / Audit / Evidence
```

Q1 每个分支激活 31 个省级主体和 10 个车企主体；Q2—Q4 只在收到新授权消息、计划复评到期、事件可见或仍有未决事务时激活。每个季度最多 3 波互动，并有调用、消息和往返次数上限，避免无界对话。

## 同源 A/B：只改一个主动变量

13110 不是“重新随机跑两遍”。Control 和 Treatment 从同一个不可变 Checkpoint 派生，冻结数据基线、主体画像、环境版本与事件条件，只允许用户审批的政策变量不同。

```text
                  Same Checkpoint
                  /             \
                 /               \
          Control World     Treatment World
             原始方案            干预方案
                 \               /
                  \             /
                 Compare 相对差异
```

当前默认基线参考为西部 / 中部 / 东部 `95% / 90% / 85%`，比赛预热的 Treatment 初始参数为 `96% / 93% / 82%`。三项是独立中央承担比例，不求和；预热参数只为稳定展示路径，不是现实最优比例或政策建议。

## Agent 与确定性环境的分工

| 层 | 负责 | 不负责 |
|---|---|---|
| 中央 Agent | 生成结构化政策解读与 Q4 年度复盘 | 不绕过用户审批，不修改权威 WorldState |
| 省级 Agent | 在财政空间、产业基础、需求和供应链约束下选择地方策略、发起或回应互动 | 不直接生成宏观结果 |
| 车企 Agent | 分配 31 省销售 / 渠道资源，并提出有上限的建厂、扩产或延迟行动 | 不代表真实企业计划或承诺 |
| 确定性环境 | 校验行动、去重、结算区域差距、财政压力、需求、资源迁移与产业集中度 | 不把模型文本当作环境事实 |
| 前端投影 | 只读渲染 World、Action、Interaction、Comparison 和 Evidence | 不从文案或动画反推业务结果 |

Agent 输出的 `DecisionTrace v3` 保存结构化行动、理由、备选、机会成本和重新考虑条件，但不保存或展示模型私有思维链。

## 关键产品取舍

- **从“多角色聊天”到“可结算行动”：** 自由文本不能直接改变世界，只有通过 Schema、身份、授权、会话状态和资源额度校验的行动才能提交。
- **从“看最终 KPI”到“看传导过程”：** 季度消息、会话、策略与环境变化全部关联到逻辑时间和证据。
- **稳定演示不等于伪造实时：** 默认采用 Cache-first；缓存未命中时由 DeepSeek 生成结构化决策，强校验后原子回写，模型或校验耗尽才显式 fallback。
- **演示可视化与业务事实分离：** 全国地图、主体连线和因果动画只表达已提交事实；切换视角不触发新模型调用。
- **质量优先于“全部看起来像 AI”：** 指标、差值、资源守恒与评估口径由确定性代码管理。

## 当前 M34 / M35 能力

### M34：动态季度互动运行时

- `Q1 | Q2 | Q3 | Q4` 逻辑时间与 `wave_0 | wave_1 | wave_2` 因果顺序；
- 主体按消息、计划到期、事件和未决事务动态激活；
- 双向发起、报价 / 回应 / 结算会话状态机；
- 跨帧合并、资源守恒、每季度纯函数结算与 Q4 年度对比；
- REST / SSE 中携带 `tick`、`wave`、`logical_sequence`、`message_id` 和 `session_id`。

### M35：全景因果舞台

- `apps/presentation` 是当前唯一产品界面；`apps/web` 仅作为历史研究工作台保留；
- 从地球开场、全国主体博弈到季度互动与年度 A/B 结果的单画布路径；
- 基于冻结标准地图的 31 省计算图层与港澳台、南海诸岛非计算上下文；
- WebGL 主路径、SVG 兼容渲染、低动效与多分辨率适配；
- 只读 Presentation Projection 与原始 World / Action / Comparison 哈希稳定性边界。

`apps/roadshow` 是独立的开场叙事层，只包含自有静态素材和可逆滚动动效，不导入模拟运行时状态或 API。

## 技术架构

```mermaid
flowchart LR
    User[政策统筹用户] --> Presentation[13110 Presentation]
    Presentation --> API[FastAPI REST / SSE]
    API --> Orchestrator[季度编排器]
    Orchestrator --> Central[中央 Agent]
    Orchestrator --> Provinces[31 省级 Agents]
    Orchestrator --> OEMs[10 车企 Agents]

    Central --> Gate[Schema / 授权 / 资源门禁]
    Provinces --> Gate
    OEMs --> Gate
    Gate --> Env[确定性季度环境]
    Env --> State[World / Checkpoint / Comparison]
    State --> Projection[只读 Presentation Projection]
    Projection --> Presentation

    Orchestrator <--> Cache[Cache-first / DeepSeek miss / explicit fallback]
    State --> Audit[Replay / Audit / Evidence]
```

主要技术栈：Python 3.11+、FastAPI、Pydantic、React、TypeScript、MapLibre / deck.gl、SSE、Pytest、Vitest 与 Playwright。

## 稳定性与验证证据

默认预热参数的完整年度路径已做冷缓存与热缓存双重复验：

- 冷跑和热跑均完成 Q1—Q4，每次实测共 **530 次主体调用、0 fallback**；
- Control 产生 267 条决策、93 条消息、46 个会话；Treatment 产生 263 条决策、104 条消息、52 个会话；98 个会话全部结算；
- 热跑复验期间缓存文件数保持 `1487 → 1487`，证明默认路径没有隐式增量或未命中；
- M35 已覆盖 1280、1080p、2K、4K 画布、WebGL / SVG 降级、开场、深链、回放、控制台和字段泄漏扫描。

**530 是该默认完整年度路径在动态条件激活后的已验证实测值，不是系统的固定调用预算，也不代表任意参数组合都会产生相同调用量。**

仓库门禁覆盖 Python / API / React 单元测试、Ruff 与前端构建、31 省数据与地图校验、Presentation Playwright E2E，以及 roadshow 的 Vitest、Sites Worker 和隔离构建检查。历史证据参见 [验收记录](./docs/validation/) 与 [Design QA](./docs/validation/design-qa.md)。

## 快速启动

环境要求：Python 3.11+、Node.js 20+。

```bash
make setup
```

分别在两个终端启动 API 和当前 Presentation 产品界面：

```bash
make dev-api
```

```bash
make dev-presentation
```

```text
Presentation:  http://localhost:4180
API:           http://localhost:8000
```

`make dev-api` 默认使用确定性 `fake` Provider，适合本地开发与回归。Cache-first + live miss 需按 [`.env.example`](./.env.example) 配置服务端环境；密钥不得进入前端或 Git。

独立 roadshow 可选本地启动：

```bash
cd apps/roadshow
npm ci
npm run dev
```

## 仓库目录

```text
apps/
  api/             FastAPI、REST / SSE 与运行时投影
  presentation/    当前 13110 产品界面
  roadshow/        独立开场叙事与离线启动源码
  web/             历史研究工作台，非当前产品界面
simulation/        Agent、编排、互动机制与确定性环境
data/              冻结数据基线与场景输入
config/            实验与运行配置
docs/
  adr/             架构与产品决策记录
  specs/           前端与 Presentation 规范
  validation/      M33 / M35 验收与 Design QA
  assets/          README 实机图与 M35 正式验收画面
scripts/           数据校验、缓存、地图与展示构建工具
deploy/m35/        M35 部署配置
```

完整文档索引见 [`docs/README.md`](./docs/README.md)。

## 研究边界

13110 是**机制推演与方案比较工具**，不是现实预测系统或政策自动决策器。

- 不输出未来真实 GDP、就业、投资金额、产能或销量预测；
- 不代表现实政府部门、地方政府或企业的真实行为；
- 现实数据主要用于冻结基线和主体上下文，派生敏感度与机制字段按 proxy / scenario assumption 管理；
- 模拟时间是 Q1—Q4 逻辑时间，不暗示现实主体的响应日期或速度；
- 产品的价值是帮助研究者比较机制、定位分歧并追溯证据，最终判断仍由人做出。
