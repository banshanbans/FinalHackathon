# PolicyScope / 政策涟漪

PolicyScope V2 是面向国务院层面政策统筹人员的“制造业设备更新政企互动智能体推演台”。它用于观察中央政策、地方工具与企业行动如何相互作用，并通过同源方案推演呈现政策收益、区域差异与财政代价。

> 研判口径：结果为当前数据与机制参数下的模拟指数，用于政策方案比较。

## 已交付的 V2 闭环

```text
中央用户设定制造业设备更新目标
  → 中央政策研判 Agent 生成完整 PolicySchema
  → 用户审批
  → 31 个省级 Agent 选择地方政策工具
  → 每省 6 类企业群体 Agent 独立行动，共 186 个合成主体
  → 确定性环境计算省级与全国指数
  → T3 地方反馈、不可变 Checkpoint 与中央干预建议
  → 用户批准、修改或拒绝
  → 同源原始方案/干预方案，或拒绝后的原始方案单线结算
  → T5 企业行为迁移、地区排行、机制归因与中央复盘
```

中央 Agent 只能建议，不能绕过用户改变政策；省级和企业 Agent 只选择策略，所有结果指标由版本化环境计算。企业批量输出必须恰好覆盖六类主体，结构修复失败后整省进入显式 deterministic fallback，并写入状态、事件和 Replay。

## 当前交付状态

- 领域契约已统一升级为 `policy-v2`、`world-state-v2`、`comparison-v2` 和 `event-v2`。
- 已提交六类企业原型、31 × 6 企业群体、数据 provenance 和 `equipment_renewal_v2.yaml` 机制配置。
- T0–T5、审批/拒绝、同源 A/B、企业迁移、REST、SSE、Evidence、Replay、Cache/Fake/Live Provider 已接通。
- React 前端已替换为四路由 Stitch 工作台和两个可深链抽屉；全部核心 CTA 使用真实 API。
- 全国页与方案对照页共用本地 ECharts SVG 地图。资源源自自然资源部标准地图 GS(2016)1609，省域标注、来源、校验和转换过程见 [地图说明](./apps/web/src/assets/maps/README.md)。根据已确认的比赛发布规则，比赛版可直接上线该地图。
- 默认演示模式为 `cache`，测试模式为 `fake`，`live` 是可选增强且不构成交付依赖。
- V1 回滚点为 Git 提交 `12456a3`。

详细完成状态见 [开发计划](./DEVELOPMENT_PLAN.md) 和 [Design QA](./design-qa.md)。

## 产品路由

- `/experiments/new`：中央目标、结构化政策参数与人工批准。
- `/experiments/:id/live`：31 省地图、六项全国指标、行动流和 T0–T5 时间轴。
- `/experiments/:id/intervention`：证据 → AI 建议 → 人类审批。
- `/experiments/:id/compare`：双地图、企业行动迁移、地区排行、机制归因与中央复盘。
- `?province=41`：河南省企详情，展示六类企业的独立行动。
- `?evidence=method`：数据质量、版本、seed、父检查点和证据记录。

Stitch 的 `code.html` 只用于布局参考；正式产品是 React、真实 API、SSE 和本地资源实现，没有 iframe、假导航或运行时 CDN。

## 本地启动

环境要求：Python 3.11+、Node.js 20+。

```bash
make setup
make dev-api
make dev-web
```

前端：[http://localhost:5173/experiments/new](http://localhost:5173/experiments/new)
后端健康检查：[http://localhost:8000/api/health](http://localhost:8000/api/health)

也可以用 `make dev` 同时启动前后端。实验状态目前保存在 API 单进程内存中，服务重启后需要新建实验。

## 运行模式

复制 `.env.example` 为 `.env` 后配置：

```text
POLICYSCOPE_RUN_MODE=cache
POLICYSCOPE_LLM_BASE_URL=...
POLICYSCOPE_LLM_API_KEY=...
POLICYSCOPE_CENTRAL_MODEL=...
POLICYSCOPE_PROVINCE_MODEL=...
POLICYSCOPE_ENTERPRISE_MODEL=...
```

- `fake`：确定性测试 Provider，不访问网络。
- `cache`：默认演示模式；读取精选结构化缓存，缺失时显式 fallback。
- `live`：调用 OpenAI 兼容结构化模型；Schema 首次失败修复一次，再失败整省 fallback。

缓存键包含政策、企业/Profile、模型、Prompt、版本和 seed。完整 A/B 的模型调用预算为中央 3 次、省级约 124 次、企业约 93 次分省批量调用。

## 验证

```bash
make test
make lint
make validate-data
make smoke
make demo
```

V2 冻结门禁要求：

- Python 测试、Web 测试、Ruff、ESLint 和生产构建通过。
- 31 个省级行政区、186 个企业群体、provenance 和标准地图完整性通过。
- Smoke 覆盖 T0–T5、同源 A/B、企业迁移和无静默 fallback。
- Cache 模式完整流程连续运行三次。
- 浏览器端同时覆盖“批准并创建干预方案”和“拒绝后单线结算”两条 E2E。

2026-08-12 冻结结果：Python 24 项与 Web 2 项测试通过；Ruff、格式检查、ESLint、生产构建、31 × 6 数据校验、地图校验和 Smoke 均通过；Cache 完整 A/B 连续运行 3 次，两个分支均为 0 个 fallback 省份。仅保留 1 个来自 FastAPI TestClient 依赖的 Starlette 弃用警告，不影响运行结果。

## 数据、指标与地图边界

- 仿真范围是中国大陆 31 个省级行政区；港澳台不进入计算。
- `verified`、`proxy`、`demo` 是数据质量类别，不是置信度。
- 企业主体是六类合成企业群体，不代表现实公司。
- 结果仅显示“指数/100”和“指数点变化”，不得解释为现实 GDP、就业、投资、财政金额或生产率。
- 地图 EPS 转 SVG 时保留边界几何，省域填色路径以稳定代码和独立几何签名绑定，避免错标、串位或重复标签。

## 文档导航

- [V2 产品需求文档](./PRD_省域政策多智能体推演平台.md)
- [V2 详细开发计划](./DEVELOPMENT_PLAN.md)
- [Stitch 正式前端规范](./STITCH_FRONTEND_SPEC.md)
- [Design QA 结果](./design-qa.md)
- [开发 Agent 约束](./AGENTS.md)
- [地图资源与合规记录](./apps/web/src/assets/maps/README.md)
- [AgentSociety2 Spike 决策](./docs/adr/001-agentsociety2-runtime-spike.md)

## 已知限制

- 实验、Checkpoint 和 Replay 由当前 API 进程托管，尚未接入外部持久化数据库。
- `live` 模式依赖外部模型和网络，正式演示应保持 `cache`。
- 比赛版地图上线门禁已解除；地图来源、审图号、省域几何与 31 省完整性仍持续自动校验。
- P0 面向桌面端；1280 像素宽可完成主流程，不承诺移动端体验。
