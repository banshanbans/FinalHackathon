# PolicyScope Design QA

## V3.0 final result

> Contract: 新能源汽车补贴与产业布局地图推演
> QA date: 2026-08-12
> Runtime: React Router + V3 REST/SSE + 本地标准地图资源
> Data / mechanism / seed: `nev-baseline-2025-v1` / `nev-policy-env-v1` / `20260812`
> V3.0 final result: **passed**

契约快照：默认政策为西部 95%、中部 90%、东部 85%；阶段为 `SETUP → Y1_Q1 → Y1_Q2 → Y1_Q3 → Y1_Q4 → YEAR1_REVIEW → Y2_Q1 → Y2_Q2 → Y2_Q3 → Y2_Q4 → COMPLETE`；十家车企为比亚迪、吉利、长安、上汽通用五菱、蔚来、奇瑞、零跑、赛力斯、小米汽车、理想汽车；六项指标为区域发展差距、中央财政负担、地方财政压力、新能源汽车需求、新增投资集中度、产业集聚度。

版本矩阵：`policy-v3`、`province-profile-v4`、`province-persona-v2`、`province-action-v4`、`province-feedback-v4`、`automaker-profile-v1`、`automaker-action-v1`、`world-state-v4`、`comparison-v4`、`event-v4`。正式路由为 `/experiments/new`、`/experiments/:id/live`、`/experiments/:id/provinces/:provinceCode`、`/experiments/:id/intervention`、`/experiments/:id/compare`。

### 1. 方法与证据

- 使用真实 Chrome 和 Playwright 运行正式 React/FastAPI 路径，不发布 Stitch 静态 HTML 或 iframe。
- 主流程使用确定性 Fake Provider 完成三画布同源 A/B；拒绝干预单线在 1440×900 单独验证。
- 使用全新空缓存运行时真实触发 Cache miss，验证 31 省 fallback 范围；通过中断 SSE 验证 Reconnecting 状态。
- 截图目录为 `output/playwright/v3/`，当前验收矩阵共 30 张：三画布各 9 张主流程截图，另含 1440 宽的非单调警告、Reconnecting 和 Fallback。
- 地图数据为本地自然资源部标准地图衍生 SVG；自动校验原始校验和、31 个省级区域和几何签名。

### 2. 截图矩阵

| 页面/状态 | 1536×1024 | 1440×900 | 1280 |
|---|---:|---:|---:|
| New draft | Passed | Passed | Passed |
| New 非单调警告 | — | Passed | — |
| Live Y1_Q1 | Passed | Passed | Passed |
| Live Y1_Q2 + 车企覆盖层 | Passed | Passed | Passed |
| YEAR1_REVIEW | Passed | Passed | Passed |
| 省级详情 | Passed | Passed | Passed |
| 车企侧栏 | Passed | Passed | Passed |
| Evidence | Passed | Passed | Passed |
| 年末干预审批 | Passed | Passed | Passed |
| Compare completed | Passed | Passed | Passed |
| Fallback / Reconnecting | — | Passed | — |

主流程文件名固定为 `01-policy-draft.png` 至 `09-compare-complete.png`；可靠性截图为 `00-non-monotonic-warning.png`、`10-reconnecting.png` 和 `11-fallback.png`。Failed 使用与 API 稳定错误码相连的全局错误条，不隐藏失败或伪装为 Live 结果。

### 3. 验收结论

- 中国地图保持主视觉面积；1536、1440 和 1280 均无页面级水平滚动或核心遮挡。
- Live 的补贴、WTP、产业/电池与车企销售投入图层真实切换，不触发额外 Agent 调用。
- 河南省级页按“财政空间 → 三类补贴 → Peer → 车企反馈 → 机制结果”组织。
- 比亚迪侧栏验证了冻结经营画像、31 省投入组合、最多 3 个设施行动和模拟免责声明；十家主体均使用中性文本，无未经许可 Logo。
- Intervention 保持“证据 → 中央建议 → 人工审批”；拒绝路径只展示原始方案单线复盘。
- Compare 首先显示同源说明、三档比例 Diff 和 `ΔGap`，两张地图共享指标、范围与色阶；完成页刷新后可从分支目录和 API 恢复。
- 页面结果只用指数、等级和相对变化，没有现实销量、利润、投资金额、财政金额、企业承诺、官方身份暗示或“最优政策”结论。

### 4. 闭环问题

| Priority | Issue | Resolution |
|---|---|---|
| P0 | 多实验共用固定 Treatment ID，可能串接错误实验 | Treatment 改用每实验唯一不透明 ID，并加入分支隔离测试 |
| P1 | Compare 刷新后仅有 WorldState，无法恢复 Treatment | 新增分支目录接口，恢复 Control/Treatment 后自动加载 Comparison |
| P1 | 中央草案生成期间仍可编辑比例，异步返回可能覆盖输入 | 生成期间锁定输入，完成后再允许修改；非单调警告仍不阻断审批 |
| P1 | Cache miss 与 SSE 中断缺少独立视觉证据 | 增加显式 Fallback 范围和 Reconnecting 提示，并用真实运行状态截图 |

所有 P0/P1/P2 已闭环。V2/V2.1 结论未被用作 V3 证据。

---

## V2.1 superseded verification status

> Contract: 省级 Agent 主决策、六类合成企业群体作市场反馈
> Status: **implemented, final verification incomplete, superseded by V3.0 target**
> V2.1 final result: **pending redesign verification**

V2.1 独立省级 Agent 详情、五路由、高密度壳层和审计深链已实现，但按此前用户要求暂停了全量测试、两条 Playwright E2E、连续三次 Cache 与 1536×1024/1440×900/1280 截图比较。

V3.0 已成为新的目标产品主线，因此 V2.1 M12 不再是当前唯一下一步。除非用户明确要求恢复 V2.1 验证，否则：

- 保留现有 V2.1 代码和未完成状态。
- 不把 V2 历史通过结论套用于 V2.1。
- 不把 V2.1 页面解释为 V3 新能源汽车页面。
- 不因主线切换而把 V2.1 未完成项标为通过或失败。

`V2.1 final result: pending redesign verification`

---

## V2 historical result

> QA date: 2026-08-12
> Reference: `stitch_policyscope/**/screen.png` + `stitch_policyscope/policyscope/DESIGN.md` 的历史版本
> Runtime: React Router + real API/SSE + local assets
> V2 final result: **passed**

### 1. Historical scope and method

V2 的五张 Stitch 参考图曾与最终运行时状态并排检查：

| Reference | V2 runtime state | Historical result |
|---|---|---|
| `_1/screen.png` | T0 生成政策草案、等待审批 | Passed |
| `_2/screen.png` | T3 全国实时仿真 | Passed |
| `_3/screen.png` | 河南六类合成企业详情 | Passed |
| `_4/screen.png` | T3 证据、AI 建议和人类决策 | Passed |
| `a_b/screen.png` | T5 同源 A/B | Passed |

历史 QA 使用运行时浏览器截图、DOM 可访问性快照和真实 API 状态。静态 Stitch HTML 未通过 iframe 发布。

### 2. Historical visual and interaction result

- 浅色制度工作台、固定导航、蓝/青/靛语义色和紧凑证据排版符合 V2 批准方向。
- 创建、审批、阶段运行、河南详情、干预批准/拒绝、分支运行、Compare 和 Evidence 使用真实 API。
- 全国和 A/B 共享本地 ECharts SVG 地图。
- 原始方案/干预方案使用中性命名。
- 指数与指数点表达替代了现实预测。
- Loading、Empty、Running、Awaiting Approval、Completed、Fallback、Failure 和 Reconnecting 有明确状态。

### 3. Historical closed issues

| Priority | Issue | Resolution |
|---|---|---|
| P0 | 静态/假地图和 A/B 空白地图 | 使用同一来源记录的本地 ECharts SVG |
| P0 | 省域标注偏移和重复 | 修正全国底色路径，加入代码—几何签名校验 |
| P0 | 核心链接和审批静态 | 重建为 React Router + API/SSE |
| P1 | 刷新丢失分支完成状态 | 从 API 恢复 Comparison/单线状态 |
| P1 | Evidence 动作改变路由 | 保持当前路由和 query |
| P1 | 终态仍重开 SSE | 终态停止连接并保留 Replay |
| P2 | 路由切换保留滚动位置 | 增加路由级滚动恢复 |
| P2 | ECharts 单包过大 | 路由和 ECharts 懒加载拆包 |

### 4. Historical map result

V2 地图来自自然资源部标准地图 GS(2016)1609，已记录原始校验和、转换脚本、31 省完整性和省域几何签名。根据当时确认的比赛规则，V2 比赛版可使用该资产。

### 5. Historical final decision

`V2 final result: passed`

该结论只证明 V2 历史基线，不证明 V2.1 或 V3.0。
