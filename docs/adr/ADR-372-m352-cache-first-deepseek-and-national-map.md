# ADR-372：M35.2 Cache-first DeepSeek 补齐与全国版图完整性

状态：Implemented and publicly verified
日期：2026-08-13
范围：M34 Provider/Cache、M35 Presentation 地图、公网部署

## 1. 决策

公网演示的服务端默认运行模式改为 `cache`，缓存缺失策略改为 `live`。每次主体调用按以下顺序解析：

```text
语义缓存命中
  → 校验 input/output hash 与 Schema
  → 直接回放

语义缓存缺失或无效
  → DeepSeek Live Provider
  → Schema + 主体身份 + 授权上下文 + 资源守恒校验
  → 原子回写 v3_2_m34_luna/decisions
  → 提交合法主体行动

DeepSeek 超时、连接、输出或业务校验失败
  → 显式确定性 fallback
```

用户修改西部/中部/东部中央承担比例会改变授权上下文和缓存键，首次运行因此使用 DeepSeek 补齐；同一语义输入的后续运行直接命中回写缓存。前端不得选择 Provider。

## 2. 安全与诚实性

- DeepSeek API Key 只通过服务器 `0600` 环境文件注入，不进镜像、Git、缓存、Replay、Audit、SSE 或前端。
- Prompt 只包含冻结授权 Inbox、公开契约和 Schema，不包含确定性候选行动或模型长思维链。
- 只有 `fallback_used=false` 且通过完整校验的 DeepSeek 输出可写入 Luna 缓存。Fake/Fallback 不得写入。
- 缓存和 M34 实验快照使用独立持久卷，容器重建不丢失已补齐内容。
- 网络或模型失败不阻断整个季度，但主舞台/Evidence 必须如实显示 fallback 数量与原因范围。

## 3. 中国地图

Presentation 继续使用冻结自然资源部标准地图 `GS(2016)1609`。地图的视觉范围与模型计算范围严格分离：

- 31 个省级行政区是 `simulation-province`，进入 Agent、指标、色阶、事件和比较。
- 香港、澳门、台湾使用冻结轮廓与名称，作为不可交互的 `territory-context`。
- 南海诸岛附图必须在 WebGL 主地图和 SVG 兼容模式中都可见，且直接裁切同一冻结标准地图的官方附图区域，不手工重绘。
- 南海诸岛附图不可 hover、聚焦、点击或参与任何计算。

## 4. 验收

- 连通性探针证明部署模型支持 JSON Output。
- 专项测试证明 Cache Provider 在 miss 时构建 DeepSeek Live Provider，有效输出写回并可被立即回放。
- Presentation 类型、生产构建与地图几何校验通过。
- 1920×1080 的 WebGL 与 SVG 回退画布都能识别“南海诸岛”附图，不遮挡因果链、博弈台或季度轨。
- 公网 `/api/health` 报告 `run_mode=cache`，容器环境启用 `cache_miss_mode=live`，演示路由和 SSL 保持可用。

2026-08-13 公网验收记录：

- `https://final.socialdog.cn/api/health` 返回 `run_mode=cache`、`cache_miss_mode=live`。
- 新建实验 `exp_m34_64538c5bf0bc`，以原始方案 `95/90/85` 对比修改后的干预方案 `95/91/84`。
- 首次运行双分支 Q1 返回 HTTP 200；每个分支均生成 31 个省级行动、10 个车企全国行动和独立 Q1 Checkpoint。
- 以 Baseline 冻结时间 `2026-08-13T12:53:33Z` 为界，本次 Q1 新增 21 条经校验的 DeepSeek Cache；其余合法决策直接命中既有 Cache。公网持久卷最终共 300 条。
- DeepSeek 两次输出仍无法通过 Schema/授权/资源校验时，使用显式 `live_provider_or_validation_exhausted` fallback；fallback 不写缓存。
- WebGL 与 SVG 回退的 1920×1080 公网画布均通过南海诸岛附图检查。

## 5. 否决方案

- 不在前端用确定性规则“伪造”一份命中缓存。
- 不把每次请求强制改为 Live；已验证缓存仍是比赛现场的首选链路。
- 不使用简化点线、远程底图或手工绘制南海诸岛替代冻结标准地图附图。
