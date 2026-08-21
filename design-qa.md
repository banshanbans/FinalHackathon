# PolicyScope Design QA

## 13110 M35.8 因果侧视镜头 Design QA

### 比较基线

- Source visual truth：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/causal-stage-reference.png`，1672×941 px；该图冻结主舞台结构、信息层级和视觉令牌，侧视镜头是用户批准的增量方向。
- WebGL implementation：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/implementation-side-view-webgl-1920x1080-final.png`，1912×1080 浏览器像素，1920×1080 CSS 视口，1× 密度。
- SVG compatibility implementation：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/implementation-side-view-svg-1920x1080.png`，1912×1080 浏览器像素，同一 Action 状态。
- Full-view comparison：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/side-view-source-vs-implementation-1920.png`；源图归一为 1912×1080 后与 WebGL 实现并排。
- Focused evidence：中央地图、右上“视角”入口、侧视状态、广东→浙江关系和右侧行动卡在 full-view 中均可读，无需另裁局部图。
- State：Q1 首次行动，干预方案，六段链“行动”，自动镜头解析为因果侧视；浏览器为 Codex in-app Browser。

### Findings

- P0/P1/P2：无未关闭问题。
- 可接受差异：侧视为增量叙事镜头，因此地图透视与参考图的俯视地图有意不同；顶栏、因果链、博弈台、时间轴、字体、色彩和内容密度仍沿用参考视觉。
- P3：深色低饱和底图在投影环境中依赖大屏亮度；当前 47° 俯仰已在保留侧视纵深的同时维持省界与关系线可辨性。

### 五项视觉表面

- Fonts / typography：Inter Variable + Noto Sans SC Variable 未变化；视角菜单使用既有 7–12 px 辅助层级，中文标签没有机器码或英文工程名泄漏。
- Spacing / layout rhythm：视角入口加入原探索工具坞，不新增常驻面板；1920×1080 与 1280×720 均满足 `scrollWidth <= innerWidth`、`scrollHeight <= innerHeight`，1280 菜单边界为 x=640–884、y=88–345，无画布裁切。
- Colors / tokens：菜单与状态沿用近黑海军蓝、Evidence teal 和现有玻璃边界；侧视不引入新的业务颜色，不改变提议/反报价/达成/拒绝语义。
- Image / asset fidelity：没有生成、改写或替换地图资产。WebGL 使用同一冻结 GeoJSON 的真实相机；SVG 使用同一省域路径的兼容透视；南海诸岛附图继续独立显示且不参与互动。
- Copy / content：入口固定为“自动镜头 / 全国俯视 / 因果侧视”；状态显示当前因果节拍；锁定理由明确说明差值、结算与年度比较使用全国俯视。

### Interaction / reliability

- 自动模式断言：决策=俯视、行动=侧视、回应=侧视、结算=俯视。
- 手动模式断言：行动帧选择全国俯视后保持俯视；重新选择自动镜头后按节拍恢复。
- 真值保护断言：差值视图、季度 Settlement Frame 和年度 Comparison Frame 强制返回俯视。
- WebGL 与 SVG 的 `data-view-mode` 都为 `side`；1920×1080 和 1280×720 无溢出，浏览器 console error/warning 为 0。
- TypeScript typecheck、31 省几何/视角规则测试与 Vite production build 通过。

### Comparison history

1. Pass 1：WebGL 使用 58° 俯仰且额外降低亮度，北部边界压缩、地图过暗；改为 47°、轻微缩小镜头并移除重复亮度滤镜。
2. Pass 2：手动侧视停在非行动节拍时状态标签仍显示“行动”；改为读取当前六段链中文标签。
3. Pass 3：1920 WebGL/SVG 和 1280 SVG 复测，无布局、交互或可访问性 P0/P1/P2。

### Implementation checklist

- [x] 自动/俯视/侧视三态与锁定规则。
- [x] WebGL 真实俯仰相机和 SVG 兼容透视。
- [x] 行动/回应自动切换，结算/差值/比较恢复俯视。
- [x] 1280/1920 画布、控制台、构建与规则测试。

final result: passed

---

## M35.13 中国地图地理锚定南海断续线 Design QA

> QA date: 2026-08-14
> Scope: `/experiments/:id/present` 中国地图本体、地理锚定南海断续线与左下角固定南海诸岛附图。

### Evidence and normalization

- Source visual truth: `/Users/carrey/Desktop/WechatIMG79.jpg`；只使用其中台湾、海南与向南延伸断续线的版图相对关系，不复制微信界面、配色或文案。
- Focused comparison: `outputs/m35-presentation-design/m3513-source-vs-map-georeferenced.png`；参考图与实现地图同画布并排检查。
- National top view: `outputs/m35-presentation-design/m3513-map-georeferenced-before-1920x1080.png`。
- Panned map: `outputs/m35-presentation-design/m3513-map-georeferenced-pan-1920x1080.png`；中国版图与断续线接受同一次拖动，左下角附图保持画布固定。
- Zoomed map: `outputs/m35-presentation-design/m3513-map-georeferenced-zoom-1920x1080.png`；断续线与海南、台湾按同一比例缩放，无相对漂移。
- Side view: `outputs/m35-presentation-design/m3513-map-georeferenced-side-1920x1080.png`；断续线与地图共同接受 pitch/bearing，相对地理关系保持不变。
- Responsive view: `outputs/m35-presentation-design/m3513-map-georeferenced-1280x720.png`。
- Browser state: 年度比较、Q4 首次行动、干预方案；Codex in-app Browser，WebGL 正式渲染。
- Production proof: `policyscope-m35-web:20260814-south-sea-georef6` 健康；公网 JS 与本地生产构建 SHA-256 同为 `abc1668c43426547d352028f616e6c70293436b5a00b25242e5d1fec6678def2`，公网 GeoJSON 返回 HTTP 200。

### Required fidelity surfaces

- Fonts and typography: 本轮不改变工作台 Inter + Noto Sans SC、字号、行高或文案层级；参考图中的省名文字不是本轮可复制 UI 资产。
- Spacing and layout rhythm: 主地图断续线从台湾、海南下方向南延伸，属于地图地理内容；左下角标准附图仍固定在画布坐标，并与右下角图例分区。
- Colors and tokens: 保留产品深色地图和青色制图语义；断续线使用高对比青白色而非参考图白底灰线，以保证深色舞台可见性。
- Image quality and asset fidelity: 断续线不是手绘、CSS 图案或屏幕贴片，而是从冻结自然资源部 GS(2016)1609 标准地图黑色制图路径机械分离为 46 个 GeoJSON 要素；WebGL 与 SVG 兼容图共用同一来源。
- Copy and content: 没有新增解释性文案；31 省模拟范围和港澳台/南海诸岛版图边界保持原产品口径。

### Comparison history

1. 旧实现把主地图断续线做成独立 CSS 绝对定位层，拖动中国地图时其屏幕坐标不变，导致与海南、台湾的相对位置漂移，记为 P1。
2. 移除主地图 CSS 覆盖层，将同一官方路径机械转换为地理坐标 GeoJSON，并加入 MapLibre 地图源；SVG 兼容图把同源矢量放入 `fallback-geography` 相机变换组。
3. 年度结算/比较镜头改为完整全国视角，避免聚焦省份错误裁掉版图南部。拖动、缩放、全国俯视与立体侧视复测均显示版图和断续线共同变换；左下角附图继续固定。P0/P1/P2：无。

### Follow-up polish

- P3：参考图使用白底细灰线，产品为深色演示舞台；当前青白高对比处理是投影可读性适配，不改变官方路径形状。

final result: passed

---

## M35.14 南海断续线线型与位置修正 Design QA

> QA date: 2026-08-14
> Scope: `/experiments/:id/present` 中国地图本体的南海断续线线型、台湾/海南相对位置、地图相机联动与左下角固定附图。

### Evidence and normalization

- Source visual truth: `/Users/carrey/Desktop/WechatIMG79.jpg`；检查台湾东侧、海南南侧和向南延伸的 U 形版图关系。
- Regression visual: `/Users/carrey/Desktop/Screenshot 2026-08-14 at 16.57.31.png`；旧实现的粗重 I/锤形填充符号记录为 P1。
- Focused comparison: `outputs/m35-presentation-design/m3514-source-vs-slender-map.png`。
- National top view: `outputs/m35-presentation-design/m3514-slender-national-1920x1080.png`。
- Southeast zoom: `outputs/m35-presentation-design/m3514-slender-southeast-zoom-1920x1080.png`。
- Panned map: `outputs/m35-presentation-design/m3514-slender-pan-1920x1080.png`；版图与断续线共同移动，左下角附图保持视口固定。
- Side view: `outputs/m35-presentation-design/m3514-slender-side-clean-1920x1080.png`；12 段边界线与地图共同接受 pitch/bearing，形成完整 U 形关系。

### Required fidelity surfaces

- Line shape: 不再把 46 条官方填充路径直接绘制为粗重符号；按 12 个官方断续符号分组，以协方差主轴机械生成一条细长中心线，MapLibre 使用 `round` cap/join。
- Position: 展示地理范围校准为经度 `106.0–127.5`、纬度 `6.0–26.0`；东侧从台湾以东向南延伸，底部经过南海深处，西侧回到海南西南方向。
- Camera behavior: GeoJSON `LineString` 与中国地图共用平移、缩放、俯仰、旋转、分支和 A/B 相机变换；左下角标准附图继续采用画布固定坐标。
- Asset fidelity: 中心、方向和分组来自冻结 GS(2016)1609 黑色路径；没有增加手绘点、CSS 虚线图案或屏幕固定贴片。
- Product boundary: 不新增交互、文案或模拟语义，仍不进入 31 省指标、事件、Agent、关系线和比较计算。

### Comparison history

1. 旧实现直接渲染 46 条官方填充路径，单个断续符号由 3–4 个路径组成，组合后在深色地图上表现为粗重 I/锤形，记为 P1。
2. 改为对 12 个官方符号组机械求取主轴中心线，并把地图图层从 fill + line 改为单一圆头 line；线型恢复为细长断续边界。
3. 以项目台湾、海南实际几何校准 U 形展示范围；全国俯视、东南放大、拖动和立体侧视并排复测后，P0/P1/P2：无。

### Follow-up polish

- P3：深色舞台继续使用青白色而非参考图灰色，以保证投影距离下可见；不改变符号中心与方向。

final result: passed

final result: passed

---

## V3.2 / M30 verification status

> Contract: 前置直接 A/B 与上下文驱动的省级 Agent 自主协作
> QA date: 2026-08-13
> Runtime: React Router + V3.2 REST/SSE + 本地标准地图资源
> Data / mechanism / seed: `nev-m29-2025-v2` / `nev-policy-env-v4` / `20260812`
> M30 mock / fallback result: **passed**
> M30 Luna cache result: **pending — 当前环境未配置 API Key**

正式 React/FastAPI 运行时已走通政策对比、政策压力测试和事件反事实。六步旅程在刷新后可恢复；两分支同轮门禁、3A 全量冻结后才进入 3B、DecisionTrace v2、代理数据标签、SSE 重连与结论优先 Compare 均由 Playwright 或契约测试覆盖。当前结果来自显式规则故障兜底，不标记为 Luna 生成结果。

| 检查项 | 当前状态 |
|---|---|
| 六步旅程与五项导航 | Passed |
| 三种实验唯一主动差异 | Passed |
| Live 三栏、初始/最终切换与选中省份有限关系 | Passed |
| Province / Automaker 决策记录 | Passed |
| 每省 3 个 Peer 行动、10 家车企评价 | Passed |
| 双分支 226 次主体调用与 3A/3B 屏障 | Passed |
| 自主合作与网外对象证据通路 | Passed：关系是软先验，代码扫描无序号、相邻或固定名单配对 |
| 全国资源迁移与机会成本 | Passed：最终轮真实守恒转移，画面显示 0.04/0.08 最大变化 |
| Compare 结论优先、Methods 工程证明 | Passed |
| 主页面机器码与禁止文案扫描 | Passed |
| SSE 重连、Replay、Audit、Evidence | Passed |
| 三画布无遮挡与无横向滚动 | Passed：每次截图前校验 `scrollWidth <= innerWidth` |

截图目录为 `output/playwright/v32/chromium-{1536,1440,1280}/`。每个画布包含 Live ready/complete、Province、Automaker、Compare、Methods 六张主旅程截图；1440 另含政策压力测试、事件反事实与 SSE 重连，共 21 张。视觉复核发现并修复了省级企业信号空卡和车企迁移显示为零的问题；最终省级页面列出 10 家反馈主体，Compare 显示实际资源让渡。Methods 继续允许显示模型、版本、哈希、fallback 与 Replay 技术字段。

全量证据：`make test` 为 48 项 Python 测试和 5 项前端测试；`make test-sim` 41 项、`make test-api` 7 项；6 项 Playwright 实际通过。三类独立 M30 fallback 缓存各包含双分支五轮、226 次调用和 164 条 DecisionTrace；Ruff、格式、ESLint、TypeScript 构建、M29 的 4,527 条事实/711 项特征/282 条关系边、31 省数据和标准地图校验通过。当前省级与车企派生字段仍明确标记为 `proxy`。

独立 `gpt-5.6-luna` Codex 线程已完成只读 mock 编排审阅：确认 620 条企业评价、62 条提议、62 条响应和 13 个匹配，并定位了缓存命名歧义与演示链第 4 幕关联不足；主线程已将缓存容器改为中性 `v32-m30-agent-cache-v1`，并让资源迁移优先从入选合作双方中选择、复用同一 Match 证据引用，相关 API/缓存测试通过。

由于本机没有 `POLICYSCOPE_LLM_API_KEY`，尚未生成或验收 226 次真实 `gpt-5.6-luna` Provider 输出；因此不得恢复“V3.2 完成并冻结”的表述。现场可稳定回放当前明确标记的 fallback 演示缓存，不会在 Schema 上冒充 Luna。真实 Luna 缓存仍是唯一外部条件项。

---

## V3.1 verification status

> Contract: 事件驱动省际协同增量
> QA date: 2026-08-12
> Runtime: React Router + V3.1 REST/SSE + 本地标准地图资源
> Data / mechanism / seed: `nev-baseline-2025-v1` / `nev-policy-env-v2` / `20260812`
> V3.1 final result: **passed**

正式 React/FastAPI 运行时已分别走通政策干预与事件反事实，并在 1536×1024、1440×900、1280 三画布验证 Y2_Q3 事件实验台、`event_exposure` 与 `province_interaction` 图层、省级事件链、模式化 Compare 和不可逆审批状态。

冻结证据：

| 检查项 | 当前状态 |
|---|---|
| New 两模式选择 | Passed |
| Intervention 政策/事件分流 | Passed |
| Live Y2_Q2 事件实验台 | Passed |
| 事件暴露与省际交互图层 | Passed |
| Province 事件信号/响应/协作 | Passed |
| Compare 唯一主动差异证明 | Passed |
| 两条完整 E2E | Passed：两种模式均覆盖三画布 |
| 三画布无遮挡与无横向滚动 | Passed：E2E 逐画布校验 `scrollWidth` |
| 禁止现实预测式文案扫描 | Passed：正式前端零命中 |

补充可靠性证据：完整缓存矩阵为 2 种模式 × 5 个模板 × 3 档强度，共 30 个场景、2047 个去重缓存对象；连续三轮政策模式均为 281 hit / 0 miss，事件模式均为 219 hit / 0 miss。`make test`、`make lint`、`make validate-data` 和 `make smoke` 均通过。V3.0 的 passed 结论只证明冻结基线，未被用来替代本节证据。

三画布关键截图位于 `output/playwright/v3/chromium-{1536,1440,1280}/`：`09-compare-complete.png`、`12-event-lab.png` 和 `13-event-counterfactual-compare.png`。1280 画布路由切换已恢复到页面顶部；地图、事件审批和 ΔGap 摘要没有核心遮挡。

---

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

---

## 13110 M35.1 Agent 博弈叙事与地图几何 Design QA

### 比较基线

- Source visual truth：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/causal-stage-reference.png`，1672×941 px。
- Runtime implementation：`http://127.0.0.1:4173/experiments/exp_m34_adc34e2efdc8/present?intro=0`。
- WebGL 证据：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/m351-webgl-final-1280x721.png`，1280×720 CSS px，浏览器截图按 1× CSS 像素归一化。
- SVG 证据：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/m351-svg-1920x1081.png`；同一 Action 状态，强制 `mapFallback=1`。
- Full-view comparison：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/m351-source-vs-webgl-final.png`。实现截图等比归一为 1672×941 后与视觉目标并排。
- Focused comparison：`/Users/carrey/Desktop/决赛/outputs/m35-presentation-design/m351-focused-source-vs-webgl-final.png`，比较主体地图、连接与右侧博弈面板。
- State：Q1 Wave 0，Action，第 1/3 组省企互动；干预方案。

### Findings

- P0/P1/P2：无未关闭问题。
- 可接受差异：参考图保留历史品牌位和固定全国镜头；正式实现按已批准契约使用“13110”，并在 Action 中飞向当前省份。两项均为产品契约差异，不是视觉回归。
- P3：大省聚焦时仍会压缩全国上下文，但当前缩放受 4.6–5.2 限制，车企固定节点与右侧 Spotlight 始终可见；后续可按演示者偏好微调停留时长。

### 五项视觉表面

- Fonts / typography：Inter Variable + Noto Sans SC Variable 与既有因果舞台一致；标题、阶段、正文和 7–9 px 辅助信息层级稳定，四画布无关键文本裁切。
- Spacing / layout rhythm：顶栏、因果链、地图、右侧博弈台和年度时间轴维持参考比例；1280×721、1920×1081、2560×1440、3840×2160 均满足 `scrollWidth <= innerWidth`、`scrollHeight <= innerHeight`，时间轴未越界。
- Colors / tokens：继续使用近黑海军蓝、青色主体、琥珀提议、紫色反报价和低透明红色拒绝；互动阶段非相关热力降低，焦点关系成为第一视觉层。
- Image / asset fidelity：未重写冻结 GeoJSON、源 SVG 或生成脚本；WebGL 与 SVG 复用同一 Mercator 投影、主体 Polygon 和内部代表点。31 个省级锚点均通过点在面内断言，SVG 31 省 + 港澳台 3 个版图上下文完整。
- Copy / content：DECIDE 展示实际选择、替代项、机会成本与重新考虑条件；SETTLE 明确分开直接贡献和季度共享变化；19 个时间节点字段泄漏扫描未发现 snake_case、Schema、Checkpoint、`null` 或四类机器枚举。

### Interaction / reliability

- 三组关系的可见数按 `0 → 1 → 2 → 3` 递增，焦点按“贵州—长安 → 新疆—奇瑞 → 河北—上汽通用五菱”切换，结束后回到用户原 Spotlight。
- WebGL 和 SVG 均支持连接按 Session 选择、车企节点选择和普通省份探索；选中轮廓与基础填色使用完全相同的 `d`。
- Settlement 验证为直接贡献 `+0.035`，Q1 只显示形成值；A/B 差值页显示中文映射且无后端字段泄漏。
- 默认开场仍存在跳过按钮；`?intro=0` 直接进入配置对话框。开场资源与 `GlobeIntro` 校验和保持实施前值。
- 最终浏览器控制台错误 0；WebGL 与 SVG 强制回退均可加载。

### Comparison history

1. Pass 1：发现车企端点使用地图外固定经纬度，省份端点来自全部顶点均值；替换为省域主体面内部代表点和视口固定车企轨道。
2. Pass 2：发现逐条序列的绘制进度绑定 Spotlight 焦点，第一条连接在延迟显示时没有重新绘制；改为绑定可见 Overlay ID 序列，并复测 `0/1/2/3`。
3. Pass 3：发现普通省份探索高亮可能与当前 Session 不一致、选中填充压过热力；互动时改由当前 Spotlight 省份承载选中语义，并将选中填充降至 0.08。Post-fix 证据为 `m351-source-vs-webgl-final.png`。

### Implementation checklist

- [x] Presentation Frame v5、季度共享变化与四类 A/B 分歧。
- [x] Mercator SVG、31 省内部锚点、同源选中描边和车企屏幕轨道。
- [x] 三组互动逐条揭示、镜头飞行、Session/主体拾取与自动播放等待。
- [x] WebGL、SVG、字段泄漏、四画布和开场保护验证。
- [x] Presentation typecheck/build、几何测试、仿真/API 专项与 lint。

final result: passed

---

## M33.3 Globe Intro Design QA

> QA date: 2026-08-13
> Scope: M33.3 开场镜头先行子项，不代表完整大屏壳层验收。

### Evidence and tested state

| Item | Evidence |
|---|---|
| Source visual truth | `https://earth-map-kohl.vercel.app/`；本地截图 `outputs/m33-globe-intro/reference-earth-map-1920x1080.png` |
| Runtime implementation | `http://127.0.0.1:4180/`；`outputs/m33-globe-intro/policyscope-globe-intro-1920x1080.png` |
| Side-by-side comparison | `outputs/m33-globe-intro/source-vs-implementation.png` |
| Primary viewport | 1920×1080 CSS px，deviceScaleFactor 1，开场 approach/中国聚焦状态 |
| Fallback viewport | 1366×768 CSS px，deviceScaleFactor 1，开场 approach/中国聚焦状态 |
| Performance viewport | 3840×2160 CSS px，主舞台交接后连续播放 |

全屏构图已覆盖本子项全部关键区域：左侧标题、右侧地球、中国高亮、底部进度和跳过操作，因此不需要额外裁切图作为判断依据。

### Visual comparison

- Typography：本地 Inter + Noto Sans SC，双行主标题层级清楚；1920×1080 与 1366×768 均无裁切、溢出或被地球遮挡。
- Spacing and layout rhythm：保持参考页的左文案、右主视觉、底部进度关系；地球放大后仍保留足够深空负空间，并与接管后的全国地图焦点一致。
- Color and token fidelity：使用近黑海军蓝、克制青色中国焦点、少量琥珀阶段提示；没有引入新闻直播红或企业品牌色。
- Asset fidelity：使用 MapLibre 真实 globe 投影、本地 Natural Earth 矢量陆地和冻结 31 省几何。相对参考页的照片级卫星纹理，PolicyScope 有意采用证据可追溯的制度化矢量表达；未使用截图仿制、远程瓦片、CDN 或 iframe。
- Copy：文案只表达机制推演与中国焦点，不出现现实战争、价格、投资承诺或权威业务结果。

### Interaction and reliability

- 自动播放：约 4.5 秒完成 orbit → approach → handoff，并卸载开场图层交接全国主舞台。
- 跳过与重播：开场可立即跳过，主舞台“重播地球开场”可再次进入完整序列。
- Reduced motion：关闭旋转与长距离飞行，在 1 秒内完成中国聚焦与淡入交接。
- Browser console：错误 0，警告 0。
- 4K：交接后 60.1 FPS，P95 17.7 ms。

### Iteration history

1. 第一轮地球比例偏小且夜面过暗；提高初始/推进 zoom，并重新平衡大气、海洋和方向光后复测。
2. 第一轮回调引用不稳定导致开场提前卸载；稳定完成与错误回调后，重新验证正常序列、跳过、重播和低动效。
3. 修复后生成 1920×1080、1366×768 与源参考并排证据，未发现 P0/P1/P2 视觉或交互缺陷。

### Findings

- P0/P1/P2：无。
- P3：实现有意不复制参考页的卫星栅格纹理，以保持离线、可追溯和政策演示语义；不影响开场目标。

final result: passed

---

## M35 / 13110 Presentation Causal Stage Design QA

> QA date: 2026-08-13
> Scope: `apps/presentation` only; M34 runtime remains the simulation source of truth.
> Selected visual target: “因果舞台”
> Final result: **passed**

### Evidence

| State / canvas | Evidence |
|---|---|
| Selected source visual | `outputs/m35-presentation-design/causal-stage-reference.png` |
| Same-state implementation | `outputs/m35-presentation-design/implementation-interaction-final-1672x941.png` |
| Required side-by-side comparison | `outputs/m35-presentation-design/source-vs-implementation-final.png` |
| 1920×1080 WebGL | `outputs/m35-presentation-design/qa-interaction-1920x1080.png` |
| 2560×1440 WebGL | `outputs/m35-presentation-design/qa-interaction-2560x1440.png` |
| 3840×2160 WebGL | `outputs/m35-presentation-design/qa-interaction-3840x2160-full.png` |
| 1280×720 SVG compatibility renderer | `outputs/m35-presentation-design/qa-fallback-1280x720.png` |
| Annual A/B result | `outputs/m35-presentation-design/implementation-annual-1440x810.png` |

### Comparison and iteration history

1. First implementation preserved the selected composition but rendered all top interactions at once. This made the map look like a network overview instead of one legible game. The final map filters to the current server-selected Spotlight and reveals its path only at Action / Response / Settle.
2. The first replay projection leaked the same quarter's completed settlement into earlier Wave frames. Projection now uses only the previous immutable checkpoint until the settlement node; Q1 Wave frames begin without future province results.
3. The first annual frame reused an empty interaction panel. It now presents a six-metric, source-derived A/B table with original, treatment and change columns plus same-origin proof.
4. Delta initially reused the treatment Spotlight. It now displays only explicitly projected divergences and zero mixed-branch relation edges.
5. Province and automaker subjects initially used bare IDs that the map could not resolve. All map subjects now use typed references and Chinese display names; the main DOM leak scan returns zero raw enums, schema names, hashes or legacy brand strings.
6. The reference uses more narrative text in the left spine than the first implementation. The final spine shows both each beat headline and a two-line causal detail while retaining the selected vertical rhythm.

### Final review

- Visual hierarchy matches the selected causal-stage direction: compact top HUD, six-beat left spine, restrained national map, one primary game panel and a full-year Q1–Q4 rail.
- The public brand is `13110` throughout the active Presentation surface and browser title. PolicyScope remains only in code/history.
- A 10-second first-view check can identify the quarter, actor, counterpart, reason, actual response and current world contribution status.
- Proposal, counteroffer, accepted/settled, rejected and event relations use semantic color plus text/state; SVG compatibility retains equivalent line semantics.
- One annual domain is shared across both branches and all quarters. Difference mode uses a symmetric domain and does not display a one-sided game.
- Policy comparison, policy stress and event counterfactual completed runtimes were exercised. Event frames show Event → authorized subject → reevaluation → pending settlement rather than a marker-only story.
- Browser checks at 1920×1080, 2560×1440 and 3840×2160 report `scrollWidth == innerWidth` and `scrollHeight == innerHeight`; the 1280×720 SVG renderer is also fully operable.
- A fresh in-app Browser session reports zero errors and zero warnings. Presentation projection/API tests, Ruff, TypeScript and production build pass.

### Findings

- P0/P1/P2: none.
- P3: the generated reference uses a decorative automaker halo and two simultaneous directional lines; the implementation keeps the real neutral subject marker and reveals one authorized relation per causal beat to preserve runtime truth. This is an intentional truthfulness difference, not a fidelity defect.

final result: passed

---

## M33 Entry Journey Reorder QA

> QA date: 2026-08-13
> Scope: root entry globe, nationwide-map handoff, policy/event configuration dialog

### Evidence

- Source visual truth: `/Users/carrey/Desktop/Screenshot 2026-08-13 at 08.15.55.png`（用户在当前对话中提供的 2048×974 参考图；本地名义路径在验收时已不可读取，但对话原图可见）。
- Implementation intro: `outputs/m33-entry-flow/approach-2048x974.png`.
- Implementation policy configuration: `outputs/m33-entry-flow/config-policy-final-1280x720.png`.
- Implementation event configuration: `outputs/m33-entry-flow/config-event-2048x974.png`.
- Comparison viewport: source and intro implementation both 2048×974 CSS px, device scale factor 1; no density normalization required.
- State: China approach/highlight phase immediately before nationwide-map handoff; configuration captures use the post-handoff modal state.

### Full-view comparison

The source and implementation captures were reviewed together in the current visual context. Both use a dominant deep-space globe, a left-aligned oversized three-line display heading, a dark navy/teal palette, highlighted China geometry and a Beijing focus point. The implementation intentionally starts with a wider global view, then reaches the source-like China-dominant composition at the recorded approach frame. The product-aligned copy is “从新能源汽车补贴 / 进入全国政策 / 全景推演厅”.

No separate crop was required: the 2048×974 full-view captures keep the headline, China outline, globe rim, Beijing light point and progress rail large enough for direct inspection. The configuration dialog was separately captured because it is a new interaction state described by the user rather than present in the source screenshot.

### Required fidelity surfaces

- Fonts and typography: Inter Variable + Noto Sans SC Variable remain local; the heading weight, negative tracking, line height and three-line wrapping preserve the source hierarchy without truncation.
- Spacing and layout: headline begins at the same left visual axis, globe remains the dominant right-side object, and the configuration dialog stays inside 1280×720 and 2048×974 without document scrolling.
- Colors and tokens: near-black space, slate land, teal China highlight and warm Beijing focus remain consistent with the source and existing GovSim tokens.
- Image quality and assets: globe and geography use local MapLibre/Natural Earth/validated national geometry; no screenshot map, placeholder illustration or remote raster asset was introduced.
- Copy and content: the title uses the user-approved wording. Configuration leads with east/central/west policy ratios; event injection is visibly optional and defaults off.
- Icons and states: Phosphor icons remain consistent; policy/event tabs, sliders, enabled/disabled event catalogue, checkboxes, loading and submit states are implemented.
- Accessibility and responsiveness: dialog semantics, field labels, visible disabled state, keyboard-focusable native inputs and reduced-motion timing are retained. Automated 1280, 1080p, 2K and 4K tests pass.
- Review gates: central interpretation, A/B active difference and proxy-baseline confirmation remain in the same spatial dialog, with explicit progress and no raw Checkpoint ID, seed or hash on the main surface. Evidence: `outputs/m33-entry-flow/confirm-interpretation-1280x720.png`, `confirm-design-1280x720.png` and `confirm-baseline-1280x720.png`.

### Comparison history

1. Initial policy-dialog capture placed the compact ratio controls at the top of an otherwise tall body, leaving an imbalanced lower dead zone at 1280×720 (`outputs/m33-entry-flow/config-policy-1280x720.png`). Classified P2 spacing drift.
2. The policy configuration content was vertically centered while the event configuration retained scroll-safe top alignment. Post-fix evidence is `outputs/m33-entry-flow/config-policy-final-1280x720.png`; viewport and document dimensions are both exactly 1280×720 and browser console error/warning count is zero.

### Findings

- P0/P1/P2: none remaining.
- P3: the MapLibre/deck.gl production chunk warning remains an engineering optimization item; it does not create a visible entry-flow regression.

final result: passed

### China map completeness addendum

- WebGL 主图与 SVG 兼容图均显示香港、澳门、台湾的冻结轮廓/比例标记及名称；浏览器实测为 31 个可交互省域和 3 个非交互 `territory-context`。
- 港澳台不接收指标填色、缺失值纹理、hover 选中、键盘焦点或点击详情。状态栏和方法面板明确区分“全国版图完整 / 31 省计算”。
- SVG 兼容图新增视口等比约束，1280×720 下完整落在 HUD 与时间轴之间，三处版图上下文均未被遮挡。
- P0/P1/P2/P3：无。

---

## M33.3 Full Presentation Shell Design QA

> QA date: 2026-08-13
> Scope: `/experiments/:id/present` 正式全景推演壳层、事件帧与真实时间轴。

### Evidence and tested state

| Item | Evidence |
|---|---|
| Source visual truth | `outputs/m33-globe-intro/reference-earth-map-1280x720.png`（Earth Map 空间叙事与悬浮控制语言） |
| Runtime implementation | `outputs/m33-globe-intro/m33-shell-event-1280x720-v2.jpg` |
| Same-input comparison | `outputs/m33-globe-intro/m33-shell-reference-comparison-2560x720.jpg` |
| Secondary viewport | `outputs/m33-globe-intro/m33-shell-1366x768.jpg` |
| Primary state | 低强度“国际冲突情景下油价上涨”事件帧；Story 模式；Side Sheet 收起 |
| Pixel / viewport | 1280×720 CSS px 与 1366×768 CSS px；devicePixelRatio 2；本地 IAB |

### Visual comparison

- 两图保持相同空间语法：近黑主舞台、顶部中央悬浮分段控制、左侧短叙事、右侧垂直圆角工具坞和底部宽时间轴；PolicyScope 的全国省域图取代参考页地球是业务状态差异，不是构图偏差。
- 地图始终是主内容，玻璃只作用 HUD、叙事、单指标、工具坞、Popover、Timeline 与 Sheet；没有 SaaS 卡片矩阵或大面积内容模糊。
- Inter + Noto Sans SC、近黑海军蓝、青色主语义、少量琥珀事件色与紫色差值色形成清晰层级；事件未使用新闻直播红。
- 1280×720 与 1366×768 均无裁切、核心遮挡或页面级滚动。1366×768 实测 `scrollWidth/scrollHeight` 与 viewport 完全一致。

### Interaction and data truth

- 真实 API 创建 V3.2 同源 A/B 压力测试；事件、11 个冻结帧、省域值、覆盖层和六指标均来自 M33.2 DTO。
- 右侧事件面板显示 LOW、双方案和 `relative_use_cost / wtp_demand`；事件时间轴节点可跳转。
- 时间轴点击与拖动吸附、播放/暂停、前后帧、四档速度和复位通过；一次拖动从 01/11 到 07/11 并同步“车企报价与反报价”。
- 地图点击命中山西并显示 Context Popover；结果模式打开六指标 Delta Sheet；同时只保留一个主面板。
- Browser console：error 0，warning 0。

### Iteration history

1. 第一轮正式壳层完成后，参考图与实现并排显示构图关系已一致；保留矢量中国地图而非复制卫星地球纹理，以满足本地资产和业务真实性边界。
2. 第一轮时间轴透明 range 覆盖了节点按钮；提高节点交互层级，并加入 pointer capture 与位置吸附，随后复测节点点击和实际拖动。
3. 第一版演示事件为 medium，确定性预算校验拒绝该组合；改用合法 low 强度并保留 `scenario_assumption`，重新运行后事件帧和结果完整冻结。
4. 最终重新执行 1280×720/1366×768 截图、同画布对照、核心交互与 console 检查，未发现 P0/P1/P2。

### Findings

- P0/P1/P2：无。
- P3：无；后续 M33.4–M33.6 已在最终 QA 中补齐。

final result: passed

---

## M33.4–M33.6 Final Presentation Hall Design QA

> QA date: 2026-08-13
> Scope: 事件与七轮闭环、五幕路演、结果 A/B、降级与高分辨率冻结。

### Evidence

| Canvas / state | Evidence |
|---|---|
| 1280×720 功能 E2E | `apps/web/e2e/presentation-m33.spec.ts`：七轮、SSE、断网、五幕、键盘、Delta/A-B、连续播放、SVG 降级 |
| 1920×1080 | `outputs/m33-resolution/presentation-1080p.png` |
| 2560×1440 | `outputs/m33-resolution/presentation-2k.png` |
| 3840×2160 | `outputs/m33-resolution/presentation-4k.png` |
| 开场北京光点 | `outputs/m33-globe-intro/beijing-focus-corrected-1280x720.jpg` |
| SVG 宽高比校准 | `outputs/m33-globe-intro/svg-aspect-corrected-1280x720.jpg` |

### Final review

- 五项事件目录在启动屏清晰可选，强度、触发边界、对照范围和提前通知不离开大屏；情景免责语可见且无新闻化战争视觉。
- 七轮运行每轮只有一个主命令，SSE 更新后左侧叙事、地图、事件帧与时间轴一致；断网期间最后冻结帧不消失。
- 五幕回放保留固定章节标签，并使用后端动态摘要作为主标题；键盘单步、跨幕、播放和复位无焦点陷阱。
- Compare 的 Delta 单图为默认，同步 A/B 切换后两图保持同镜头和选择；结果 Sheet 首先显示 Gap、财政代价、受益/承压省份和三机制链。
- 1080p、2K、4K 无页面级滚动或核心越界；4K 仅放大悬浮 UI，不缩放或修改地图几何。
- WebGL 容错展示 `SVG COMPAT`，仍覆盖 31 省并保留点击/键盘可达；Fake 彩排明确显示 `FAKE / FALLBACK`。

### Findings

- P0/P1/P2/P3：无。
- 非阻塞工程提示：Vite 仍报告主包体积建议，不影响本地演示、交互或冻结契约。

final result: passed

---

## Latest QA result — 13110 M35.1

完整证据、比较历史与五项视觉表面见本文件“13110 M35.1 Agent 博弈叙事与地图几何 Design QA”章节。最终复测覆盖 WebGL、SVG、三组逐条关系、四画布、字段泄漏、默认开场、跳过开场和实验深链；P0/P1/P2 均为 0。

final result: passed
# 13110 M35.9 立体数据侧视 Design QA

> QA date: 2026-08-14
> Scope: `/experiments/:id/present` 行动/回应阶段的立体数据沙盘。

## Evidence

- Source visual truth: `/Users/carrey/Downloads/IMG_1661.HEIC`，4032×3024；参考其深色斜视数据城市、竖向高差和中心主舞台构图，不复制照片中的第三方界面。
- WebGL implementation: `outputs/m35-presentation-design/implementation-height-side-view-webgl-final-v2.jpg`。
- SVG compatibility implementation: `outputs/m35-presentation-design/implementation-height-side-view-national-final.jpg`。
- Q1 pre-settlement semantic state: `outputs/m35-presentation-design/implementation-height-side-view-final.jpg`。
- Browser viewport: in-app Browser default 1280×720 CSS px，device scale 1；Q2 首次行动、干预方案、行动 beat。

## Findings and comparison history

1. 第一轮只改变地图 pitch，缺少真实高度编码，属于 P1；已改为 MapLibre `fill-extrusion` 与 SVG 兼容柱体。
2. Q1 首次行动尚无冻结发展指数，直接显示 31 省柱体会伪造数据，属于 P1；改为仅对当前互动主体显示“当前互动强度（展示权重）”。Q2 起 31 省已有冻结值后，自动切为“新能源汽车发展指数”。
3. 初始 WebGL 高度过低，视觉仍接近平面，属于 P2；提高高度域并保持统一色阶，最终形成参考图可见的全国高低错落。
4. Typography、HUD、左右因果链/主体面板、时间轴与原 Presentation 设计系统保持不变；高度层没有引入远程资产、未改变权威地图填色、结算或差值语义。
5. TypeScript、31 省几何/视角/高度映射测试、生产构建和 `git diff --check` 通过。Vite 仅保留既有大包体积提示。

## Residual P3

- 参考照片的建筑密度来自城市级数据；当前产品只有省级权威指标，因此保持 31 根省域柱体，不用虚构城市楼群追求表面相似。

final result: passed

---
