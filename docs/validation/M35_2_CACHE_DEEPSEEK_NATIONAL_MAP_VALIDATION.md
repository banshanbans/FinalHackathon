# M35.2 Cache-first / DeepSeek / 全国地图验收记录

日期：2026-08-13
公网：`https://final.socialdog.cn`
验证实验：`exp_m34_64538c5bf0bc`

## 结论

M35.2 公网服务已按 `Cache-first → DeepSeek miss 补齐 → 校验后持久化回写 → 显式 fallback` 运行。修改中央承担比例的全新实验完成双分支 Q1，南海诸岛附图在 WebGL 和 SVG 回退画布中均可见且不参与 31 省计算。

## 公网运行证据

- Health：`run_mode=cache`，`cache_miss_mode=live`，API `version=0.6.0`。
- 后端权威版本：`product_version=v3_2_m34`，`schema_version=world-state-v10`。
- Provider：省级与车企均报告 `cache-first:deepseek-v4-flash`。
- A/B 参数：原始方案 `95/90/85`；干预方案 `95/91/84`。
- 双分支 Q1：HTTP 200；每边 `completed_ticks=[Q1]`，均有 Q1 Checkpoint。
- 行动完整性：每边 31 个省级行动、10 个车企全国行动；车企行动必须恰好覆盖冻结的官方 31 省代码。
- Cache 写入：以该实验 Baseline 冻结时间 `2026-08-13T12:53:33Z` 为界，Q1 新增 21 条经校验的 DeepSeek Cache；其余合法决策命中既有 Cache。公网持久卷最终共 300 条。
- Fallback：只有 DeepSeek 两次输出仍未通过完整校验时才接管，并记录 `live_provider_or_validation_exhausted`；fallback 结果不写入缓存。

## 专项检查

```text
.venv/bin/pytest -q simulation/tests/test_m34_provider.py simulation/tests/test_m34.py
9 passed

.venv/bin/ruff check simulation/llm/m34_provider.py simulation/models/m34.py \
  simulation/services/m34_orchestrator.py simulation/tests/test_m34_provider.py
All checks passed
```

新增边界测试覆盖：

- DeepSeek 业务校验失败后进行一次结构化修复，只有修复后的合法输出可写 Cache。
- 车企全国行动拒绝“31 个不重复但不属于官方 31 省”的代码集合。
- 产能目标拒绝非授权省份代码。
- 行动和消息必须匹配授权 branch/tick/wave/sender/recipient。
- Live 输出两次耗尽后暴露准确 fallback 原因。

## 地图边界

- 31 省进入 Agent、色阶、互动、指标和比较。
- 港澳台仅作为不可交互的国家版图上下文。
- 南海诸岛直接复用冻结标准地图附图，在 WebGL 与 SVG 回退模式显示，不可 hover、点击、聚焦，也不进入环境计算。
