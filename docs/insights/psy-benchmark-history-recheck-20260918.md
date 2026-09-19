# psy `data/benchmark_history` 台账现状复核（s918-56，只读）

生成：2026-09-19 10:2x｜执行：Qoder 会话（班次 `qoder-rev-20260919-1020`，倒序尾部续班）
**只读**：本单未新增/修改/删除台账内任何文件，目录树前后一致（4 个文件，见下表）。零金额估算。

## 一句话结论

**台账没膨胀（09-13 至今只多 1 个文件），但两件事停滞了**：
① shim 通道 `_relay_calls.jsonl` 确认**再没被追加过**（行数与时间戳范围与 09-13 报告逐字一致，mtime 停在 09-10 03:19）；
② **人工评分一格未填**——主 JSON 与 side-car 草稿的 `manual_score` 空值率都是 **30/30 = 100%**，
09-13 那轮「分数档位补记」的提案到今天**没有落地**；漂移追踪也自 09-09 起**再没跑过第二次**。

## 二、四文件实测表（含与 09-13 报告的差异列）

| 文件 | 大小 | mtime | 今日实测 | 09-13 报告值 | 差异 |
|---|---|---|---|---|---|
| `socratic_benchmark_20260909T192139Z.json` | 14643 B | 09-10 03:19 | `n_cases=30`、`version=v3.7`、`llm=relay/gpt-5.6-sol`、`results` **30 条**、`manual_score` 空 **30（100%）** | 30 条 results（§四） | **条数一致**；空值率当时未记，今补为 100% |
| `_relay_calls.jsonl` | 9370 B | 09-10 03:19 | **38 行**；键 `ts/model/status/usage`；时间戳范围 **2026-09-10T03:01:31 → 03:19:38** | **38**（37×200＋1×524 超时），同范围 | **零差异 ⇒ shim 确未再追加**（另有 mtime 停在 09-10 佐证） |
| `_latest_drift.md` | 296 B | 09-10 03:21 | 指向 `socratic_benchmark_20260909T192139Z.json`，且自述「上一次归档：（无 — 这是第一次跑漂移追踪）」 | 该文件当时未纳入盘点 | **新增可见项**：漂移追踪**至今只有第一次**，`_latest_drift.md` 与实际唯一归档互指一致、无悬空指针 |
| `benchmark_backfill_draft.json` | 18209 B | **09-16 01:21** | `artifact=benchmark-manual-score-backfill-sidecar`、`n_entries=30`、`manual_score_null_count=30`、`source_file` 指主 JSON、`generated_by="backfill-draft.py --apply（20260915-130540-dd4d）"` | **不存在**（09-13 之后由 dd4d 单产出） | **台账自 09-13 唯一增量＝这个文件**；`source_sha256` 前 12 位 `909b479962e3` 与主 JSON **当前实算 sha 完全相同** ⇒ 原始基准确实没被改过 |

补充：目录内 **`.bak` 文件数 = 0** ⇒ 该 side-car 的 `--apply` **只跑过一次**（与 `s918-12` 刚钉的「首写不留 .bak、二次写才备份」语义吻合，可交叉印证）。

## 三、指向关系图（本次核过）

```
_latest_drift.md ──"当前归档"──▶ socratic_benchmark_20260909T192139Z.json  (30 results, manual_score 全空)
                                          ▲                    │
benchmark_backfill_draft.json ──source_file──┘                    │ source_sha256 == 实算 sha ✓
   (30 entries, null_count=30, 待人工填分)          原始 JSON 字节未变 ✓
```

## 四、判断与建议（本单不动手）

1. **shim 可以正式定性为"一次性产物"**：09-13 已判定「不具长期性：无记账、无重试、无配额护栏」，
   本次追加证据是**它确实再没被写过**。建议日间据此把「改走 `llm_call.py` 通道」这一条从"建议"变成待办单，
   否则下一个人还会以为它是活通道。
2. **补评链已就绪但没人填**：side-car 结构、幂等、字节不变守卫都已在 `s918-12/13` 钉过，
   `manual_score_null_count=30` 说明**卡在人工填分这一步**，而不是工具没好。
   要么排人工时间，要么明确"暂不补评"并把 side-car 归档，别让它一直以"待办"形态躺在台账里。
3. **漂移追踪事实上已停摆 10 天**：`_latest_drift.md` 停在 09-10，第二次归档从未产生
   （目录里只有那一个 `socratic_benchmark_*` 文件）。若漂移观测仍是目标，需要排一次实跑；
   若已放弃，应把 `_latest_drift.md` 的"下次跑完会自动对比"这句改成现状说明，避免误导。
4. 台账增长健康：**9 天净增 1 文件 / 18 KB**，无需清理动作。

## 五、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 四文件实测数字表 | 见第二节（大小/mtime/计数/与 09-13 差异四列齐） | `cd /d/code/psy-analysis && ls -l data/benchmark_history/ && wc -l data/benchmark_history/_relay_calls.jsonl` → 38 |
| 零文件变更 | 本单只读；`data/` 不在版本库内（`.gitignore` 有 `data/`），以 mtime 佐证：四个文件的 mtime 最晚为 **09-16 01:21**，均早于本单执行时刻（09-19 10:2x） | `cd /d/code/psy-analysis && ls -l --time-style=+%m-%d_%H:%M data/benchmark_history/` |
| 不越隐私界（自加门） | 只统计条数/空值率/sha 前缀，**未读取任何 `input`/`llm_reply` 正文** | 见第二节表格列的字段名（全部结构化元数据） |

## 遗留问题

1. 主 JSON 的 `manual_notes` 字段是否已被人写过内容，本单未读（属正文，隐私面）；
   只核了 `manual_score` 空值率这一结构化指标。
2. `generated_by` 里带的授权单号（20260915-130540-dd4d）指向 side-car 落盘的授权，本单未回溯核对该单原文。
3. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
