# PolicyScope / 政策涟漪

PolicyScope 是面向国务院层面政策统筹人员的“制造业设备更新政企互动 Agent 推演台”。产品用于观察中央政策、地方工具与企业行动如何相互作用，并通过同源 A/B 情景实验辅助跨区域研判。

> 这是在当前数据、参数与机制假设下的情景实验，不构成现实政策预测或决策建议。

## V2 最终产品闭环

```text
中央用户设定制造业设备更新目标
  → 中央政策研判 Agent 生成结构化政策
  → 用户审批
  → 31 个省级 Agent 选择地方政策工具
  → 每省 6 类企业群体 Agent 反馈行动，共 186 个企业主体
  → 确定性环境计算省级和全国指数
  → T3 中央 Agent 提出待验证干预
  → 用户批准、修改或拒绝
  → 同一不可变 Checkpoint 派生原始方案/干预方案
  → T5 比较企业行为迁移、地区差异、财政压力与机制贡献
```

中央 Agent 只能建议，不能代替用户改变政策。省级和企业 Agent 只选择策略，所有结果指标由确定性环境计算。

## 当前迁移状态

仓库已有可重复验证的 V1 回滚基线，V2 最终契约已经批准并进入原地迁移：

- 已有：FastAPI、Pydantic、React/Vite、31 省 Profile、中央/省级 Agent、确定性环境、REST、SSE、Replay、Checkpoint 和 A/B 基础实现。
- 尚未完成：六类企业群体 Schema、31 × 6 企业决策链、设备更新环境机制、企业动作迁移、四路由 Stitch 正式前端和真实 31 省矢量地图。
- 当前前端仍是 V1 深色单页工作台，不代表最终 Stitch 交付。
- V2 实现尚未完成前，不得宣称企业闭环和 Stitch 正式前端已经交付。

`FOUND-200` 已完成；`make test`、`make lint`、`make validate-data` 与 `make smoke` 均已通过。迁移采用原地升级，初始 Git 提交承担 V1 回滚点。

## 文档导航

- [V2 产品需求文档](./PRD_省域政策多智能体推演平台.md)
- [V2 详细开发计划](./DEVELOPMENT_PLAN.md)
- [Stitch 正式前端规范](./STITCH_FRONTEND_SPEC.md)
- [开发 Agent 约束](./AGENTS.md)
- [Stitch 视觉规范草稿](./stitch_policyscope/policyscope/DESIGN.md)
- [AgentSociety2 Spike 决策](./docs/adr/001-agentsociety2-runtime-spike.md)

文档优先级为：PRD → 领域 Schema/API → Stitch 正式前端规范 → Stitch `DESIGN.md` 与五张 `screen.png` → Stitch `code.html` 布局参考。

## 目标技术路线

- Python 3.11+、FastAPI、Pydantic v2
- React、TypeScript strict、Vite、React Router、ECharts
- Asyncio 仿真基线；AgentSociety2 仅为可选 Adapter
- Live / Cache / Fake 三类统一 LLM Provider
- JSONL Replay、不可变 T3 Checkpoint、同源 A/B
- 本地字体、图标与 31 省矢量地图资源，不依赖现场 CDN

## 目标前端结构

- `/experiments/new`：中央目标、结构化政策与审批
- `/experiments/:id/live`：31 省地图、六项全国指标、行动流与 T0–T5 时间轴
- `/experiments/:id/intervention`：证据 → AI 建议 → 人类审批
- `/experiments/:id/compare`：双地图、企业动作迁移、地区排行、机制归因与中央复盘
- `?province=41`：河南省企详情抽屉
- `?evidence=...`：方法与证据抽屉

Stitch 静态 HTML 只提供视觉和布局参考，正式产品必须使用 React、真实 API 与现有 SSE，不得 iframe 或直接发布静态页面。

## 现有 V1 本地启动方式

以下命令描述当前仓库的 V1 基线，不代表 V2 已完成。

```bash
make setup
make dev-api
make dev-web
```

前端默认地址为 [http://localhost:5173](http://localhost:5173)，后端健康检查为 [http://localhost:8000/api/health](http://localhost:8000/api/health)。

## 验证状态

V2 迁移前的实际基线结果：

- Python 测试：17 个通过，存在 1 个第三方弃用警告。
- Web 测试：1 个通过。
- `make test`：通过。
- `make lint`：通过；V1 Web 构建存在约 795 KB 单包警告，V2 将以路由和 ECharts 懒加载解决。
- `make validate-data`：通过。
- `make smoke`：通过。

目标命令集：

```bash
make test
make lint
make validate-data
make smoke
make demo
```

只有在对应迁移任务完成并实际复验后，才能更新上述状态。不得为通过检查跳过断言、静默 fallback 或硬编码结果。

## V1 模型运行模式

复制 `.env.example` 为 `.env` 后可配置 OpenAI 兼容服务：

```text
POLICYSCOPE_RUN_MODE=live
POLICYSCOPE_LLM_BASE_URL=...
POLICYSCOPE_LLM_API_KEY=...
POLICYSCOPE_CENTRAL_MODEL=...
POLICYSCOPE_PROVINCE_MODEL=...
```

- `fake`：确定性测试策略，不访问网络。
- `cache`：优先读取缓存，缺失时显式进入 fallback。
- `live`：调用模型，Schema 校验失败修复一次，再失败进入 fallback。

V2 将沿用统一 Provider 边界，并把企业群体、政策、Profile、Prompt、模型、版本和 seed 纳入缓存键。

## 数据与地图声明

- 仿真范围是中国大陆 31 个省级行政区，港澳台不进入计算。
- `verified`、`proxy`、`demo` 是数据质量类别，不代表置信度。
- 内部结果只显示“指数/100”和“指数点变化”；不得解释为现实 GDP、就业、投资或财政金额。
- 企业主体是六类合成企业群体，不代表现实公司。
- 当前 V1 前端使用省域示意布局；V2 必须替换为来源、版本与合规说明完整的离线 31 省矢量地图。

## 已知限制

- V1 实验状态保存在单进程内存中，尚不能在服务重启后自动恢复运行中实验。
- V1 尚无企业 Agent、企业聚合结果和企业行为迁移矩阵。
- V1 PolicySchema、指标和环境机制仍是旧政策域，不能只改文案冒充设备更新。
- Stitch 五个页面是静态视觉稿，导航、审批、地图和数据交互尚未接入正式应用。
- Live Provider 的结构化修复与 fallback 仅覆盖 V1 路径，V2 需要重新完成企业批量输出测试。
