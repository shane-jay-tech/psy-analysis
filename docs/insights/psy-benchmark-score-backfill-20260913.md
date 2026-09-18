# psy 基准首跑分数档位补记＋调用台账与 cost_log 对账（b-50，2026-09-13，只读）

## 一、首跑分数复原：manual_score 全空——「分数从未评出」，不可复原

- 产物：`psy-analysis/data/benchmark_history/socratic_benchmark_20260909T192139Z.json`（version=v3.7，llm=relay/gpt-5.6-sol，n_cases=30，generated_at=2026-09-10T03:19:38）。
- results=30 条（stage 1–5 各 6 条），字段含 manual_score/manual_notes——**30/30 manual_score=None、error=无**：即首跑只完成了「出题+LLM 应答采集」，人工评分环节从未发生。
- 结论：**有几分=不可复原（不存在）**；「准不准」无从谈起，评分必须复跑评分环节（不需要重跑模型调用，llm_reply 全档在案）。
- 复跑前置步骤：①确定评分者与评分标准（manual_score/manual_notes 填法）；②从该 JSON 的 llm_reply 直接离线评分即可，无需再调模型；③若重跑采集：relay key 有效性核验 + 524 超时重试（本次 1 例 524）。

## 二、调用台账 ↔ cost_log 条数级对账

| 侧 | 条数 | 时间窗 | 模型 |
|---|---|---|---|
| `psy-analysis/data/benchmark_history/_relay_calls.jsonl` | **38**（37×200 + 1×524 超时） | 2026-09-10T03:01:31 → 03:19:38 | gpt-5.6-sol |
| 根仓 `data/cost_log.jsonl` 同时段 gpt-5.6-sol 条目 | **0** | 2026-09-10T03:00–03:20 过滤 | — |

- **差异 = 38 − 0 = 38 条**：shim（benchmark 直连 relay 的专用通道）不经 llm_call 记账链，cost_log 天然无痕。
- 比对命令：`python -c` 过滤 cost_log.jsonl 中含 `gpt-5.6-sol` 且 ts∈[03:00,03:20] 的行（脚本内联于本会话，未落盘不污染）。
- **不做任何金额估算**（红线遵守）。

## 三、shim 通道非长期性结论与复跑前置

- `_relay_calls.jsonl` 位置确认：在 psy 侧 `data/benchmark_history/` 内（rg 实证），属 benchmark 专用一次性 shim 产物——**不具长期性**：无记账、无重试策略、无配额护栏，不宜复用于任何生产调用链。
- 复跑前置：①评分标准定版（见§一）；②改走 `llm_call.py` 通道（自动记账 cost_log，模型=claude/gpt 角色 + model_override）或给 shim 补记账挂钩；③524 重试；④跑后把 relay_calls 与 cost_log 双向对账（本报告方法复用）。

## 四、证据路径汇总

- `psy-analysis/data/benchmark_history/socratic_benchmark_20260909T192139Z.json`（30 条 results）
- `psy-analysis/data/benchmark_history/_relay_calls.jsonl`（38 行）
- 根仓 `data/cost_log.jsonl`（0 条命中，过滤区间已述）
- 纪律：未调模型、未联网、未改两台账 ✓；条数级对账、零金额 ✓
