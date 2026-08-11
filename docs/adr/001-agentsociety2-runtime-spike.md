# ADR-001：AgentSociety2 运行时 Spike

- 日期：2026-08-12
- 版本：`agentsociety2==2.8.4`
- 结论：`CONDITIONAL_GO_OPTIONAL_ONLY`
- MVP 主运行时：Asyncio（不变）

## 验证结果

在隔离的 Python 3.12 临时环境中完成了以下探针：

| 探针 | 结果 | 说明 |
|---|---|---|
| macOS arm64 安装与导入 | 条件通过 | 默认会解析到不兼容的 `mcp==2.0.0`；固定 `mcp>=1.29,<2` 后可导入 |
| 共享环境 | 通过 | 自定义 `EnvBase` 可让两个 Agent ID 读写同一聚合状态 |
| 检查点恢复 | 通过 | `to_workspace` + `from_workspace` 可恢复自定义环境状态 |
| Replay | 通过 | `ReplayWriter` 可追加并读取分片 JSONL，两条记录完整 |

复现命令：

```bash
python3.12 -m venv /tmp/policyscope-agentsociety-spike
/tmp/policyscope-agentsociety-spike/bin/pip install 'agentsociety2==2.8.4' 'mcp>=1.29,<2'
AGENTSOCIETY_LLM_API_KEY=spike-only /tmp/policyscope-agentsociety-spike/bin/python scripts/spike_agentsociety2.py
```

## 决策

AgentSociety2 的核心扩展点可用，因此保留为后续研究型 Adapter 的候选；本轮不把它接入 MVP 关键路径，原因如下：

1. 依赖树包含 Ray、FAISS、DuckDB、SciPy、Pandas、LiteLLM、Mem0 等，远大于当前确定性运行时。
2. 默认依赖解析会安装 `mcp==2.0.0`，随后因缺少 `mcp.server.fastmcp` 在导入时失败；项目的可选依赖已显式限定 `<2`。
3. 即使只导入 `EnvBase`，框架也要求存在 `AGENTSOCIETY_LLM_API_KEY`；Spike 使用不会发起请求的占位值。
4. PolicyScope 已有不可变 T3 检查点、同源 A/B、审批门禁和事件 Replay，直接迁移会重复实现并增加演示风险。
5. Spike 只验证了 `EnvBase` 级共享状态，没有验证 32 Agent 的分布式延迟、取消语义和完整分支隔离。
6. 框架分发版本与包内版本不一致，需要在正式接入前固定兼容性测试。

后续只有在 32 Agent 压测、分支隔离、取消/超时和 Replay 对齐全部通过后，才实现正式 `AgentSociety2SimulationAdapter`。当前 `AsyncioSimulationAdapter` 是唯一生产可用实现。
