# M29 可信数据字段契约

## 原始事实 `raw_fact`

| 字段 | 含义 |
|---|---|
| `record_id` | 稳定记录 ID |
| `subject_type` | `province | automaker | facility | policy | route` |
| `subject_id` | 省份、车企或节点稳定 ID |
| `metric_code` | 稳定英文指标码 |
| `raw_value` | 原始值，不先压成 0–1 |
| `raw_unit` | 原始单位 |
| `reference_period` | 统计年份或有效期 |
| `statistical_scope` | 集团、品牌、基地、乘用车等口径 |
| `source_institution` | 来源机构 |
| `source_url` | 原始链接 |
| `source_title` | 表名、公告名或章节 |
| `accessed_at` | 获取日期 |
| `transformation` | 单位或口径转换 |
| `missing_handling` | 缺失处理 |
| `data_quality` | 机器层来源方式；对用户统一显示“可信数据” |
| `review_status` | `unreviewed | source_checked | accepted | rejected` |

## 省际关系 `relation_fact`

除通用来源字段外，至少包含：

- `source_province`、`target_province`。
- `relation_type`：材料、电芯、零部件、整车、研发、测试、园区、竞争、转移、物流或协议。
- `relation_direction`、`involved_entities`。
- `effective_start`、`effective_end`、`relation_status`。
- `evidence_scope`：实际供货、正式协议、合资、项目规划、媒体推断等。
- `cross_province_valid`。
- `strength_raw` 与后续版本化的强度计算方法。

Markdown 中的“强/中/弱”只保留为原始研究判断，不直接作为运行时权重。
