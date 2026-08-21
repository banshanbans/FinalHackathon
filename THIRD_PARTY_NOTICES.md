# 第三方材料与许可说明

13110 依赖开源软件、公开地理数据和研究资料。本文件用于集中说明边界，不改变各上游项目或数据源的原始许可。

## 软件依赖

- Python 依赖以 [`pyproject.toml`](./pyproject.toml) 为准，包括 FastAPI、Pydantic、Uvicorn、HTTPX 与 OpenAI Python SDK 等。
- Web、Presentation 与 Roadshow 依赖分别以各自的 `package.json` 和 `package-lock.json` 为准，包括 React、Vite、MapLibre GL JS、deck.gl、Three.js、GSAP、Vitest 与 Playwright 等。
- 字体包来自 Fontsource；图标来自 Phosphor Icons 或仓库中注明来源的本地资产。

分发构建产物前，应根据对应锁文件复核实际包含版本，并随产物保留各依赖要求的许可证和版权声明。

## 地图与地理数据

- 全国展示使用仓库冻结的省级几何与标准地图校验流程；数据来源、处理方法和校验口径记录在 [`docs/data/`](./docs/data/) 与相关 ADR 中。
- 世界地图上下文使用 Natural Earth 等上游公开地理材料时，应遵守其来源说明和许可条款。
- 地图只服务于模拟界面和研究表达，不改变行政区划与地图合规要求。

## 政策与研究数据

- 政策事实、主体背景和数据快照的来源与证据引用保存在 [`data/`](./data/) 和 [`docs/data/`](./docs/data/) 中。
- `proxy`、`scenario_assumption` 和模拟派生字段不是第三方事实，也不得作为现实统计结论再次分发。

## 13110 自有内容

除上述第三方材料外，13110 自有代码、设计、文案与比赛展示资产适用 [`NOTICE.md`](./NOTICE.md) 的保留全部权利声明。本仓库未授予 MIT、Apache-2.0 或其他开源许可。
