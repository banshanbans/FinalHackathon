# ADR-374：DeepSeek 输出质量门禁与默认 Luna 缓存重建

状态：Implemented and publicly verified
日期：2026-08-14
范围：M34 DeepSeek Provider、季度 Orchestrator、M35 公网默认干预路径

## 问题

早期 DeepSeek 输出虽然通过当时的结构校验并被写入 Luna 缓存，但没有满足互动层的完整语义：`engagement=initiate` 可以没有消息，`monitor|ignore` 可以没有不行动原因，交易消息可以同时包含多个对手，跨季度待回应会话也没有被正确授权。旧验证只统计调用和 fallback，没有检查消息、会话和互动一致性，因此出现“全线没有记录但缓存命中”的假健康状态。

## 决策

1. Luna 决策缓存升级为 `m34-luna-cache-envelope-v3`，语义上下文升级为 `m34-live-authorized-context-v3`。
2. 非 legacy 缓存必须包含 `quality_contract=m34-decision-quality-v1`；缺失、哈希不符或输出重新校验失败时一律视为 miss，不得回放。
3. 只有通过 Schema、身份、消息授权、会话状态、资源额度和互动一致性校验的 live 输出才能原子回写缓存；fallback 继续不写入 Luna。
4. `initiate` 必须发送合法消息；`respond` 必须回应授权消息或待处理会话并发送合法回应；`monitor|ignore` 不得发消息且必须说明不行动原因。
5. 交易消息只能有一个对手；新提议不得复用既有 session；回应只能引用授权的 pending session；省级与车企消息、资源及产能目标必须满足当期剩余额度。
6. Inbox 只把 pending session 授权给当前接收方，并公开最新待回应消息；修复轮同时得到主体身份、授权消息、授权会话和剩余额度。对于没有可回应会话或消息额度已经耗尽的情况，修复提示必须明确改成合法 `revise`。
7. 互动一致性校验保留在 Orchestrator 边界，不加入持久化模型的 Pydantic 全局校验，以保证既有运行快照仍可只读加载。

## 缓存处置

- 原有 831 个决策缓存已可恢复地隔离到 `quarantine/decisions-pre-quality-v3-20260814`。
- 首轮修复期间产生、仍未满足完整接收方授权的 75 个缓存已隔离到 `quarantine/decisions-fix4-recipient-gap-20260814`。
- 两批文件均未删除，也不会被活动 `decisions` 命名空间读取。

## 公网验证

- 生产镜像：`policyscope-m35-api:20260814-deepseek-fix13`。
- 冷缓存实验：`exp_m34_44819eaa0dcd`，默认原始方案 `95/90/85`、干预方案 `96/93/82`，Q1–Q4 共 530 次主体调用，0 fallback。
- 冷跑互动：原始方案 267 个决策、93 条消息、46 个会话；干预方案 263 个决策、104 条消息、52 个会话；98 个会话全部结算。
- 两分支 `empty_initiates=0`、`unexplained_passive=0`。
- 热缓存复验：`exp_m34_cb7ae06bfad4`，全部计数与冷跑一致，仍为 530 次调用、0 fallback；活动缓存文件数保持 `1487 → 1487`。
- 公网健康：`run_mode=cache`、`cache_miss_mode=live`；容器 `healthy`、重启次数 0。
- 定向回归：Ruff 通过，Provider、Orchestrator、Presentation Projection 与 API 共 23 项测试通过。

冷跑日志中的少量首次/二次领域校验告警已由修复轮消解；最终无 `ERROR`、Traceback、Provider 连接失败或 fallback。后续默认缓存验收必须同时检查调用、fallback、消息、会话、空发起、无理由被动决策和缓存文件数，不能只用“调用成功”作为完成证据。
