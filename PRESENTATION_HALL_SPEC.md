# 13110 全景推演厅产品与交互契约

> 状态：M34 季度运行时升级实施中；旧七轮投影仅作历史记录
> 版本：Presentation Hall V3 / M34
> 日期：2026-08-13  
> 目标模块：`apps/presentation`  
> 正式入口：`/experiments/:id/present`

## 1. 决策摘要

13110 使用独立全屏前端“全景推演厅”。旧 `apps/web` 继续作为只读迁移基线和故障回退，不在原 SaaS 壳层内换皮。

全景推演厅必须在一个演示屏中完成：

```text
政策输入
  → 中央解读人工确认
  → A/B 实验设计与突发事件设置确认
  → 代理数据基线确认
  → 七轮推演
  → 章节回放
  → 结果对照
  → 方法与证据下钻
```

所有业务操作通过顶部 HUD、右侧功能坞、浮动 Tab、侧滑面板、模态窗和底部时间轴完成。主流程不得跳转到旧 SaaS 页面。

## 2. 来源优先级

冲突时按以下顺序处理：

1. V3.2 / M32 产品语义、Schema、审批和唯一主动差异规则。
2. 本文件的全景推演厅信息架构、事件与时间轴契约。
3. `STITCH_FRONTEND_SPEC.md` 的数据边界、文案和状态规则。
4. `stitch_policyscope/policyscope/DESIGN.md` 的品牌令牌。
5. Earth Map 参考页只提供全屏舞台、浮动控件、镜头和时间轴参考，不覆盖 PolicyScope 业务语义。
6. 旧 `apps/web` 只用于 API、类型、地图资产和异常处理参考。

## 3. 产品模式

### 3.1 实时推演 `live`

- 用户在单屏内创建实验、确认方案、设置事件并推进七轮。
- 时间轴只允许访问已经冻结的业务帧；未来帧禁用。
- SSE 只通知事实，收到事件后重新请求权威投影，不靠前端累加推断 WorldState。
- 推进期间锁定重复提交，显示当前主体完成数、fallback 和连接状态。

### 3.2 章节回放 `story`

- 完成实验后读取 `presentation-summary-v1` 的五幕叙事。
- 五幕固定为政策输入、企业反馈、省级互动、资源重配、政策结论。
- 每幕绑定一个或多个七轮业务帧、地图镜头、重点主体和 Evidence。
- 自动播放可以暂停、单步、变速、拖动和一键复位。

### 3.3 结果对照 `compare`

- 默认使用单图 Delta：`干预方案 − 原始方案`。
- 支持同步 A/B 双世界；两图镜头、指标、Hover 和选择保持同步。
- 结果模式先显示 Gap 方向、财政代价、受益/承压省份和三条机制链，再提供详细指标。

## 4. 单屏信息架构

### 4.1 顶部 HUD

- 左：13110、实验名称、实验类型。
- 中：`实时推演 / 章节回放 / 结果对照`。
- 右：分支、连接状态、播放、全屏、设置和一键复位。
- 不设置传统侧边导航，不展示页面级面包屑。

### 4.2 全国地图主舞台

- 占可见面积 70%–80%。
- 默认使用中国省域差异填色，当前无双分支结果时使用单方案绝对图。
- 覆盖层：竞争损失、反报价/省企谈判、省际协同、Top-K 资源流、突发事件传播、选定车企市场行动。
- 全国态默认最多显示 10 条关系；选中省份、企业或关系后展示完整关联链。
- 地图对象必须可点击、可键盘访问，并提供表格替代视图。

### 4.3 左侧叙事浮层

默认只显示：

- 当前阶段。
- 本阶段一句结论。
- 1–3 条关键变化。
- 事件发生时显示事件标题、强度和传播进度。

### 4.4 右侧功能坞

固定一级入口：

```text
方案
事件
省份
车企
竞争
谈判
协同
结果
方法
图层
```

一次只允许打开一个主面板。Evidence 可在主面板之上打开二级抽屉，但不得同时遮住整个地图。

### 4.5 底部时间轴

- 固定贴近屏幕底部，默认高度 88–112px。
- 显示业务帧、事件节点、当前进度、播放速度、拖动手柄和播放控制。
- 全屏模式下仍保持可达，不因侧栏展开而移动。

### 4.6 GovSim Glass UI Kit

全景推演厅采用“Apple-like spatial glass UI + Earth Map 式地图叙事 + Bloomberg 式信息密度控制”作为方向描述，但不复制第三方专有组件、资产或品牌。核心规则是：背景地图与互动传播是内容，玻璃只是工具。

首批组件固定为：

- `Floating Glass Panel`：当前省份、车企或事件的短上下文。
- `Glass Pill / Chip`：运行状态、轮次、变化方向和主体类型。
- `Floating Segmented Control`：全国、省份、企业、供应链等同层切换。
- `Metric Card`：一次只突出一个核心数字，解释文字降级。
- `Context Popover`：点击地图对象后就地反馈，不跳页。
- `Timeline Rail`：底部业务帧、事件节点与播放控制。
- `Command / Scenario Bar`：中央参数、实验状态与播放命令。
- `Bottom Sheet / Side Sheet`：完整政策、互动、指标、方法和 Evidence。

默认玻璃 Token：

```css
background: rgba(18, 18, 22, 0.55);
backdrop-filter: blur(24px) saturate(140%);
border: 1px solid rgba(255, 255, 255, 0.10);
box-shadow:
  0 12px 40px rgba(0, 0, 0, 0.22),
  inset 0 1px 0 rgba(255, 255, 255, 0.08);
border-radius: 22px;
```

玻璃表面可叠加极弱的纵向白色高光渐变，但不能依靠 `backdrop-filter` 单独形成层级。禁止用上述组件拼成规则卡片矩阵；常态仍须为地图保留 70%–80% 的舞台。

信息固定按三级渐进披露：

1. 地图态势、主体动作、短状态和一个大数字。
2. 点击后显示相关指标、竞争/协同对象和动作前后变化。
3. 展开 Sheet 后显示政策配置、结构化 Agent 理由、方法、数据与 Evidence。

旧工作台定位为 `Workbench = 操作复杂系统`；全景推演厅定位为 `World View = 看见复杂系统`。二者不能在视觉和信息密度上重新合并。

## 5. 突发事件一级模块

### 5.1 定位

突发事件是实验设计的一部分，不是装饰性新闻流。事件必须改变 Agent 可见上下文或确定性环境输入，并参与同源 A/B 证明。

页面固定显示：

> 本事件为机制实验情景，不代表现实战争、法规、价格或企业行为预测。

### 5.2 版本化事件目录

事件目录从“代码写死的五项枚举”升级为版本化注册表 `presentation-event-catalog-v1`。目录可以扩展，但每个模板必须具备：

```text
template_id
catalog_version
family
title
description
trigger_points
affected_subjects
mechanism_channels
supported_intensities
branch_scopes
advance_notice_supported
provenance_refs
mechanism_version
data_quality
disclaimer
```

新增模板的强制门禁：

1. 有稳定英文机器 ID 和中文展示名。
2. 绑定已实现的确定性机制通道，不能由前端填写影响系数。
3. 有来源、情景假设说明和数据质量标签。
4. 有 Schema、环境、分支隔离、Replay 和展示测试。
5. 不把现实新闻标题直接当作已验证输入。

### 5.3 首批内置模板

继续支持现有五项：

1. 西部电池节点能力升级（四川情景）。
2. 全国智驾能力升级。
3. L3 企业责任提高。
4. 国际冲突情景下油价上涨。
5. 油价回落。

“伊朗相关冲突升级导致油价上涨”作为第 4 项的用户输入示例或展示别名，系统内部仍使用中性的情景模板和冻结机制，不声称现实事件已经发生或预测其走势。

后续可扩展但尚未实现的候选类别包括：

- 电池材料价格骤升或骤降。
- 芯片、关键零部件或国际物流中断。
- 区域充电网络大面积故障。
- 极端天气与交通物流受阻。
- 新能源汽车安全监管收紧。
- 消费信心突然变化。
- 重大技术突破或基础设施集中投运。

候选类别在机制、数据和测试完成前只可显示为“尚未支持”，不得参与正式推演。

### 5.4 触发边界

V1 只开放当前 V3.2 已支持的三个冻结边界：

```text
推演开始前
省份初始行动后
车企初步响应后
```

事件发生后，后续轮次中的省份、车企和环境按 `EventPlan` 可见性规则重新评估。事件不能插入已经提交的业务帧，也不能修改历史 Action。

若未来开放“省级反制后、谈判后、反报价回应后”等晚期触发点，必须先更新 Orchestrator 调用预算、信息权限和事件可见性测试，不能只在时间轴添加一个图标。

### 5.5 A/B 规则

- `policy_comparison`：两方案政策不同，无事件。
- `policy_stress_test`：两方案政策不同，承受相同事件哈希。
- `event_counterfactual`：两方案政策相同，仅干预方案应用事件。
- 比较服务发现政策和事件同时构成未声明差异时拒绝生成结论。
- 事件的模板、强度、触发点、提前通知、作用主体和分支范围都进入语义哈希。

### 5.6 事件交互

事件面板包含：

- 模板浏览与类别筛选。
- 强度 `low / medium / high`。
- 触发边界。
- 是否提前通知省份或车企。
- 影响主体和机制通道预览。
- Control/Treatment 作用范围。
- 事件前后预期方向，必须标记“待验证”。
- 确认后的锁定状态与 Diff。

时间轴上的事件使用菱形节点；点击后地图显示影响起点、直接暴露主体、后续响应主体与机制传播，不使用新闻直播或警报跑马灯样式。

## 6. 可拖动时间轴与动画契约

### 6.1 业务锚点

时间轴固定包含：

```text
方案冻结
省级初始行动
车企初步 Top-K
省级竞争反制与协同
车企报价与反报价
省级反报价回应
车企最终确认与重配
环境结算
结果复盘
```

事件节点插入对应锚点之间，但不增加或改写七轮业务顺序。

### 6.2 拖动规则

- 时间轴是连续可拖动控件，使用 `0..1` 的视觉进度。
- 拖动过程中显示最近两个冻结帧之间的视觉过渡。
- 业务值、主体行动、匹配状态和指标只在冻结帧边界切换。
- 松手后吸附到最近的合法帧。
- Live 模式只能拖到已经完成的帧；Story 和 Compare 可访问全部已冻结帧。
- 拖动时自动暂停，松手后保持暂停，除非用户再次播放。
- 左右方向键逐帧移动，`Shift + 左右` 跳到上一/下一章节，空格播放或暂停。

### 6.3 动画语法

默认动画顺序：

```text
镜头聚焦
  → 省域填色过渡
  → 关系线绘制
  → 主体标记移动或脉冲
  → 关键变化浮层进入
  → 指标数字补间
```

建议默认时长：

- 镜头：600–900ms。
- 省域填色：350–500ms。
- 关系线：500–800ms。
- 浮层：180–260ms。
- 数字：300–450ms。

支持 `0.5x / 1x / 1.5x / 2x`，并提供“路演节奏”自动镜头。`prefers-reduced-motion` 下取消镜头飞行、路径绘制和大幅位移，只保留瞬时状态切换与短淡入。

### 6.4 真实性边界

- 动画可以补间颜色、透明度、镜头和路径绘制进度。
- 动画不得补算不存在的财政、需求、ROI、Gap、HHI 或主体决策。
- 任一过渡画面必须能够标明其前后两个 `frame_id`。
- 用户点击“定格”时显示最近的权威业务帧，而不是补间数值。

### 6.5 开场地球镜头

- 首次进入全景推演厅时播放约 3–5 秒的深空地球镜头：缓慢自转、向中国推进、点亮全国版图，并以构图连续的淡入交接全国省域推演地图；其中 31 省参与推演，香港、澳门、台湾保留为版图上下文。
- 地球使用本地打包的真实矢量陆地数据和 MapLibre globe 投影；开场光点固定锚定北京真实经纬度，中国高亮使用已校验的全国版图展示几何（31 个计算省域 + 港澳台版图上下文），不使用远程底图、运行时 CDN、iframe 或截图地图。
- MapLibre 展示 GeoJSON 必须与冻结 SVG 保持相同 Web Mercator 宽高比，曲线采样不少于 24 段；构建校验必须拒绝横向/纵向拉伸和低精度轮廓。
- 开场属于展示壳层，不对应 `presentation-frame-v1`，不得显示或改变业务值、主体行动、事件审批、分支结果或权威时间轴位置。
- 用户可随时“跳过开场”，进入主舞台后可“重播地球开场”。
- `prefers-reduced-motion` 下取消自转与长距离飞行，以不超过 1 秒的中国聚焦和短淡入完成交接。
- WebGL 初始化失败时立即交接现有全国兼容地图，不能阻塞业务操作。
- 无实验 ID 的根入口先播放该镜头，不显示前置事件目录。全国版图接管约 2 秒后自动弹出实验配置；第一 Tab 配置东中西中央承担比例，第二 Tab 选择是否注入突发事件。事件默认关闭，关闭时创建纯政策对比，开启时才冻结事件模板、触发点、强度和通知范围。
- 配置提交后不得在单个前端函数里自动确认所有门禁。根入口必须依次显示并由用户确认中央政策解读、实验类型与唯一主动差异、代理数据基线边界；基线确认后才进入七轮推演。网络丢失响应后重试相同确认必须语义幂等。

## 7. Presentation DTO 冻结草案

### 7.1 `presentation-timeline-v1`

```text
schema_version
experiment_id
product_version
status
current_frame_id
frames[]
event_markers[]
story_chapters[]
available_modes[]
source_world_hash
generated_at
```

### 7.2 `presentation-frame-v1`

```text
frame_id
sequence
kind = setup | round | event | settlement | comparison
branch_id
round
title
summary
frozen
map_projection
province_values[]
overlay_records[]
key_changes[]
metric_summary[]
focus_subjects[]
panel_refs[]
evidence_refs[]
source_event_ids[]
source_hash
```

`province_values`、`overlay_records` 和 `metric_summary` 都是后端对权威 DTO 的只读投影；前端不得从展示摘要反推或重算环境结果。

### 7.3 `presentation-event-marker-v1`

```text
marker_id
event_plan_id
template_id
title
family
intensity
trigger_point
timeline_position
branch_scope
advance_notice
affected_subjects[]
mechanism_channels[]
evidence_refs[]
source_hash
```

### 7.4 `presentation-overlay-record-v1`

```text
overlay_id
kind = competition | negotiation | coordination | topk | event | automaker
source_subject
target_subject
status
weight
label
style_semantic
evidence_refs[]
```

## 8. API 映射

### 8.1 直接复用

| 能力 | 现有接口 |
|---|---|
| 创建实验 | `POST /api/experiments` |
| 确认政策解读 | `PUT /api/experiments/{id}/interpretation` |
| 确认设计与事件 | `PUT /api/experiments/{id}/design` |
| 确认基线 | `POST /api/experiments/{id}/baseline/confirm` |
| 推进七轮 | `POST /api/experiments/{id}/run` |
| 当前权威状态 | `GET /api/experiments/{id}/state` |
| 互动市场 | `GET /api/experiments/{id}/strategy-market` |
| 省份详情 | `GET /api/experiments/{id}/provinces/{code}` |
| 车企详情 | `GET /api/experiments/{id}/automakers/{automaker_id}` |
| 结果 | `GET /api/experiments/{id}/compare` |
| 五幕路演摘要 | `GET /api/experiments/{id}/presentation-summary` |
| SSE | `GET /api/experiments/{id}/stream` |
| Replay / Audit / Evidence | 现有对应接口 |

### 8.2 新增只读投影接口

Phase 1 开发前必须冻结并实现：

```text
GET /api/experiments/{id}/presentation/timeline
GET /api/experiments/{id}/presentation/frames/{frame_id}
```

可选性能接口：

```text
GET /api/experiments/{id}/presentation/bootstrap
```

`bootstrap` 只聚合实验身份、当前帧、时间轴、当前地图投影和事件目录，不改变任何运行状态。

## 9. 前端技术边界

- 新建独立 `apps/presentation`，不导入旧 `AppShell`、页面组件或 SaaS CSS。
- React 19、TypeScript strict、Vite、TanStack Query、XState v5。
- MapLibre GL JS + deck.gl 作为主引擎；ECharts 保留指标图表。
- 地图、字体、图标、样式和演示资产本地打包，不依赖 CDN。
- 冻结 `china-standard-map.svg` 不修改；WebGL 数据必须由其校验过的 31 省几何以及香港、澳门、台湾版图上下文衍生。31 省标记为 `simulation-province`，港澳台标记为 `territory-context`。
- 保留现有 ECharts/SVG 省域地图为 WebGL 故障兼容模式。
- 前端不计算环境指标、不生成事件系数、不决定协作是否生效。

## 10. 路演可靠性

- 支持 1920×1080、2560×1440 和 3840×2160；不得页面级滚动。
- 常态目标接近 60 FPS；关系线过多时自动限流，不降采样省份结果。
- 支持全屏、播放、暂停、单步、变速、一键复位和低动效模式。
- API 断线时保留最后完整冻结帧，并显示重连状态。
- API 进程重启后必须按实验惰性恢复 World、Replay、Comparison 和 SSE Event 游标，不得因内存索引丢失误走历史产品路径。恢复真相使用同目录原子快照；旧 `state/replay/comparison` 文件只作兼容镜像。
- WebGL 初始化失败时切换兼容地图并保留时间轴、面板和业务操作。
- 离线彩排只能加载经过验证的 Replay/缓存；没有 Luna 输出时必须显示 Fake/Fallback，不得伪装。

## 11. Phase 0 退出条件

- [x] 独立模块边界、路由和三种模式已冻结。
- [x] 突发事件成为一级模块，目录改为可扩展注册表设计。

## 12. M33 最终冻结附录

- 事件目录为 `presentation-event-catalog-v1`，五项正式模板均支持 `low|medium|high`、三个冻结触发点和 `both|treatment_only`。
- Live 以同页“下一轮”命令推进七轮；SSE 支持 Last-Event-ID、断网保帧和恢复后重取权威 Timeline/Frame。
- Story 绑定 `presentation-summary-v1` 五幕；Compare 提供单图 Delta、同步 A/B、Gap/财政/受益承压摘要和三条权威机制链。
- 遥控键为空格、左右、`Shift+左右`、`Home|R`、`Esc`；运输控件提供四档速度、复位和全屏。
- WebGL 失效时使用同一冻结 GeoJSON 的本地 SVG 兼容渲染，保留 31 省键盘/点击可达与全部业务控件；港澳台继续显示轮廓与名称，但保持非聚焦、非点击、非计算。
- 正式验收画布为 1920×1080、2560×1440、3840×2160；具体证据见 `M33_PRESENTATION_FINAL_VALIDATION.md`。
- [x] 现有五个模板和后续候选类别边界已明确。
- [x] 三个现有触发点和未来晚期触发门禁已明确。
- [x] 可拖动时间轴、吸附、动画和真实性边界已冻结。
- [x] Presentation DTO 草案和 API 映射已完成。
- [x] DTO 进入 Pydantic/TypeScript Schema 并通过契约测试。
- [x] 车企详情反报价响应过滤缺陷修复并回归。
- [x] 离线标准地图进入 MapLibre/deck.gl 的技术验证完成。

M33.1 已于 2026-08-13 通过，证据见 `M33_MAP_ANIMATION_TECH_VALIDATION.md`；M33.2 只读投影 API 也已通过，证据见 `M33_PRESENTATION_API_VALIDATION.md`。M33.3 开场与运行时壳层、M33.4 事件闭环、M33.5 路演结果和 M33.6 可靠性验收现已全部完成并冻结。

## 13. M34 / Presentation V2 breaking upgrade

M34 直接替换主演示厅 V1 响应，不新增并行 v2 路由。`GET /presentation/timeline` 返回轻量 `presentation-timeline-v2` 帧索引，`GET /presentation/frames/{frame_id}` 返回完整 `presentation-frame-v2`；历史 World/Replay 不迁移，服务端按请求从冻结 M32 事实确定性重建。

七轮使用 `frame-round-{round}`，每个逻辑帧同步携带 Control/Treatment 分支投影与可选 Difference 投影。分支投影独立包含 31 省值、关系、指标、Replay ID、Evidence 和哈希；任一引用不得来自另一分支。事件反事实中 Control 暴露固定为零，Treatment 使用真实事件链。

完整博弈叙事新增四类只读结构：

1. `presentation-decision-moment-v1`：主体目标、约束、观察、实际选择、记录备选、机会成本、改变条件、实际回应与证据。
2. `decision-option-evaluation-v1`：合法性、决策时点评分、分项贡献、与实际选择差值、假设与证据。
3. `presentation-game-thread-v1`：竞争、协同、报价、反报价、接受/拒绝、匹配与重配的跨轮链。
4. `presentation-divergence-v1` 与 `presentation-spotlight-v1`：双分支首次分歧、镜头排序和可反算评分。

Live 只显示截至当前帧的冻结事实。行动产生时实际回应为“待回应”，下一轮冻结后补入真实回应，后续继续追加匹配、重配和结算。Spotlight 权重固定为 25/20/15/15/15/10，同分按轮次、主体、事实 ID 稳定排序，不能固定地区或读取未来 Gap。

左侧浮层改为 Game Spotlight，固定使用“聚焦 → 观察 → 选择板 → 实际行动 → 实际回应 → 取舍/分歧”。全国地图仍为主舞台；单图聚焦是常态，首次关键分歧与结算进入同步 A/B。Control 使用虚线/空心，Treatment 使用实线/实心，并保留文字分支标签。时间轴上方显示行动—回应轨；全部决策索引按需加载全帧并支持分支、主体和状态筛选。

M34 本期只开放 Live 和 Compare。M33 的 `presentation-summary-v1` 继续只读存在，但主演示厅不再依赖；自动 3–5 分钟路演、TTS 和 Luna 文案润色后置。

## 14. M34 / Presentation V3 年度时间轴

本节取代第 6、7、13 节中的固定七轮活动语义；旧结构只用于解释历史 `exp_m32_*` 投影，且相关 API 现统一返回 410。

- Timeline 为一年四季度区段，不再包含固定 `ROUND_SEQUENCE`。逻辑锚点为政策冻结、外生事件、有互动的 Wave、季度结算和年度比较。
- Frame 使用 `presentation-frame-v3`，Timeline 使用 `presentation-timeline-v3`。节点必须携带 `tick`、可选 `wave`、逻辑序号和源事实哈希。
- 同一 Wave 的公开/私有消息、提议、响应、反报价、状态迁移、资源重配与 fallback 由后端聚合；前端不能用网络返回顺序生成叙事。
- 年度轨固定显示 Q1、Q2、Q3、Q4 宽区段，Wave 按逻辑位置落点；所有画布显示“模拟季度与互动顺序，不代表现实响应日期”。
- 事件节点按 `scheduled_tick/release_wave` 放置；相同时点形成批次，按稳定 ID 展示但并行结算。
- 每个有互动的 Wave 选择 1–3 个后端稳定关键互动作为地图 Spotlight，其余在互动 Sheet 中按类别和状态下钻。
- 根入口支持 0–3 个事件；主操作为“运行 Q1 / 下一季度”。Live 只能到最后完整 Checkpoint，断线时不显示半波结果。

## 15. M35 / Presentation V4 因果舞台

`presentation-frame-v4` 是 M34 权威季度事实的只读展示投影。它不替换 `world-state-v10`、`interaction-market-v1` 或 `comparison-v10`，但它是 `apps/presentation` 主舞台唯一允许消费的帧对象。

### 15.1 Frame V4

```text
frame_id / experiment_id / sequence / kind / tick / wave
chapter { id, label, question }
branch_views {
  control {
    map_projection / province_values / metric_summary
    interactions[] / spotlight / event_impacts[]
  }
  treatment { ... }
}
comparison_view { shared_scale, divergences[], spotlight }
display_metadata { disclaimer, data_mode, fallback_count }
evidence_refs / source_hash
```

`spotlight` 固定包含：

```text
actor / counterpart
focus { objective, strongest_constraint }
observe { facts[], attended_messages[] }
decide { engagement, decision_summary, alternatives[], opportunity_costs[], reconsideration[] }
action { message_kind, summary, state }
response { actor, summary, state } | pending
settle { contributed, contribution, result_summary }
fallback
```

主体引用必须是 `province:`、`automaker:`、`event:` 或 `environment:` 前缀，并同时携带用户展示名。所有互动、消息、决策和事件在投影前按分支、季度、Wave 与权限过滤。

### 15.2 前端消费边界

- 主舞台不得再并行请求互动市场后自行组装因果；完整互动市场只服务 Evidence 下钻。
- 不得把 `frame.interactions` 的两分支合并后交给任一单分支地图。
- 不得使用运行时数组顺序表达先后；逻辑序号和 `reply_to_message_id` 决定消息链，Wave 内结算仍视为批次。
- 时间轴可保留逻辑 Wave 锚点，但用户文案使用“首次行动 / 条件回应 / 协议收敛”。

### 15.3 Design QA

源真相为 `outputs/m35-presentation-design/causal-stage-reference.png`。QA 必须比较同一 16:9 视口和同一互动状态，检查字体、布局、色彩、地图层级、主体节点、关系线、六段链、右侧博弈台、季度轨和全部用户文案。没有浏览器截图、主交互验证、console 检查和字段泄漏扫描时，`design-qa.md` 只能标记 `blocked`。
