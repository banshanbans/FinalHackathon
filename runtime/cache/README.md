# 运行时缓存

此目录只保存本地或生产运行期间生成的模型决策缓存，缓存文件不进入 Git。

当前 M34 / M35 使用独立命名空间：

- `v3_2_m34_fake/`：显式 fake 回归缓存；
- `v3_2_m34_luna/`：经校验的 live / cache-first 决策缓存；
- 其他版本目录只属于对应历史实验，不得改名复用为当前缓存。

常用命令：

```bash
make precompute-m34
make precompute-m34-luna
make verify-cache-m34
make verify-cache-m34-luna
```

缓存未命中、模型响应和 fallback 必须保持显式；缓存不能替代冻结数据、确定性环境或验证证据。需要复现实验时，应从明确提交、固定配置、seed 和模型 / prompt 版本重新生成，不应依赖仓库中的历史 JSON 快照。
