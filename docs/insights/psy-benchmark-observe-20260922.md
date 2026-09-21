# psy #L3 benchmark 观测面对账事实表（s922-19，2026-09-22 只读）

> 2026-09-22 03:2x｜执行班 `qoder-executor-20260922-0000-psy3`｜**全程只读**：`data/benchmark_history/` 四个文件动单前后 sha256 全等（见 §7），仓库零改动、零提交。
> 用途：供 #L3（`KNOWN_ISSUES.md:60-63`「N10 苏格拉底基准 LLM-as-judge 漂移连续观测」）定去留。**本档不下统计结论、不评漂移**（统计结论域红线），只给事实与复跑命令。

## 1. 观测面现物清单

| 文件 | mtime | 字节 | sha256 前 16 |
|---|---|---|---|
| `_latest_drift.md` | 2026-09-10 03:21:39 | 296 | `3d83f7e94172f96f` |
| `_relay_calls.jsonl` | 2026-09-10 03:19:38 | 9370 | `dff475155797c62f` |
| `benchmark_backfill_draft.json` | 2026-09-16 01:21:06 | 18209 | `092d61b07350b2bb` |
| `socratic_benchmark_20260909T192139Z.json` | 2026-09-10 03:19:38 | 14643 | `909b479962e3fe0e` |

四个文件**全部被 `.gitignore:42` 的 `data/` 覆盖**，`git ls-files data/benchmark_history` 返回**空**——「9/16 草稿未入库」不是遗漏，是**结构性不能入库**（除非改 .gitignore 或换目录）。

## 2. 观测断档事实表（本单主产出）

| 项 | 9/19 那次核验（`psy-l3-drift-verify-20260918.md`） | 本次 9/22 03:2x 实测 | 变化 |
|---|---|---|---|
| 末次归档批次 | 仅 `socratic_benchmark_20260909…`（1 批） | 仍 **1 批**，目录内无任何新 `socratic_benchmark_*.json` | **未补一批** |
| 距今年数 | 「距今 10 天」（按 9/9 起算） | 末条 relay 观测 2026-09-10T03:19:38 → 现点 2026-09-22T03:26:35 ＝ **12.0 天**（12 天 0 小时） | +2 天，无进展 |
| 有观测的自然日数 | 1 | **1**（38 次调用全落在 2026-09-10，窗口 18.11 分钟、2.10 次/分钟） | 无进展 |
| 距「样本 ≥3 批再评漂移」门槛 | 差 2 批 | 仍差 **2 批** | 无进展 |
| CI | `.github/workflows` 不存在 | 同上（`ls .github` 无该子目录） | 无进展 |
| drift 单测 | 10 skipped（离线门） | **10 skipped in 0.06s**（同读数） | 无进展 |
| benchmark 全族 | 未测 | **18 passed / 35 skipped**（`-k "benchmark or sidecar or relay or shim or drift"`，9.84s） | 新读数 |

**断档根因已定位（不是「忘了跑」这么简单）**：写 `_relay_calls.jsonl` 的唯一生产者 `scripts/benchmark_relay_shim.py` 的 `LOG_PATH` 直到 9/22 才修对——提交 `eec95c3`（s922-09/A5 欠账）把它从 `scripts/data/benchmark_history/`（**该目录不存在**）改为仓根 `data/benchmark_history/`。即 **9/10 之后即便有人跑基准，观测也不会落到这个文件里**。修好之后至今（`eec95c3` 落地 ≈ 9/22 00:0x）还没有过一次带网实跑，所以 §2 的 12 天断档里**约 11.9 天是「结构上不可能产生观测」**。

## 3. relay 用量事实（只列数，不作成本结论）

```
按 model 聚合（全部 38 条）：
  gpt-5.6-sol  calls=38 ok=37 err=1 prompt=161106 completion=3129 total=164235
               cached=120320 reasoning=1771  首=2026-09-10T03:01:31.933848 末=2026-09-10T03:19:38.266844
  缓存命中率 cached/prompt = 74.7%      单次平均 total_tokens = 4322
非 2xx 明细：{"ts":"2026-09-10T03:11:28.399025","model":"gpt-5.6-sol","status":524,"usage":null}   # 1/38，中转 524
```
（观测面**只记 model/status/usage**，无 case_id、无耗时、无错误体——若 L3 要判「漂移」，这份日志的证据粒度撑不起逐题追溯，这是第 2 个结构性缺口。）

## 4. 9/16 草稿本体对账

```
artifact               = benchmark-manual-score-backfill-sidecar
source_file            = socratic_benchmark_20260909T192139Z.json
source_sha256(声明)     = 909b479962e3fe0e…c09c78
source_sha256(实测)     = 909b479962e3fe0e…c09c78   一致 ✓（草稿未漂移，源归档自 9/10 起未被改过）
n_entries / 实长        = 30 / 30 一致
manual_score_null_count = 30（实测 null 计数确为 30；非空 0 条）
manual_notes 非空        = 30 条，全部是「[离线预填] 维度覆盖 x/y…」式启发提示
stage 分布              = {1:6, 2:6, 3:6, 4:6, 5:6}
草稿行数                = 430
```
**关键**：源归档 `socratic_benchmark_20260909…json` 的 30 条 `results[i].manual_score` **本来就全是 null**。所以草稿的净增信息只有「离线启发式覆盖率预填」，**主观的启发性 60 分与跨阶段一致性 20 分仍未评**（草稿自己的 fixture docstring 写明离线规则不冒充可评、按 None 透传人工）。判据：删掉草稿不丢任何人工劳动（0 条人工分），保留草稿则为将来人工补评留了 30 条预填提示。

## 5. 引用面（谁还依赖这些文件）

- `_relay_calls.jsonl`：只有生产者 `scripts/benchmark_relay_shim.py:7,20`；**tests/ 与 src/ 零消费者**（本次 `rglob` 实测，除本单 tmp 脚本外无引用）。
- `socratic_benchmark_20260909T192139Z.json`：被 `tests/test_benchmark_backfill_sidecar.py:15` 与 `tests/fixtures/benchmark_backfill_draft.py`、`scripts/evaluate_socratic_benchmark.py:14,29` 读 ⇒ **源归档是测试依赖，不能删**。
- `benchmark_backfill_draft.json`（草稿本体）：测试用 `tmp_path` 隔离重跑 `--apply` 生成自己的 side-car，**不读 data/ 里这一份** ⇒ 草稿删或留都不影响 18 passed。
- 授权记录缺件：草稿 `generated_by` 自称依据 `docs/decisions/2026-09-15-psy-benchmark-scoring-baseline.md`，但该路径**不存在**（`ls docs/decisions` 只有 2 个文件；`git log --all -- <该路径>` 零命中，即从未入库）。**「9/15 授权」这句话在仓库内无可核证据**，L3 定去留前建议先补这条（要么补档，要么把 `generated_by` 的引用改指真存在的记录）。

## 6. 给 #L3 的三条出口（事实对齐，不代拍板）

| 出口 | 需要动的东西 | 代价与前置 |
|---|---|---|
| A 续观测 | 带网跑 ≥2 批基准（每批 30 题） | shim 路径已修好（`eec95c3`）⇒ 现在跑才会真落观测；单批实测 18.11 分钟 / 164,235 tokens / 38 次调用，模型 `gpt-5.6-sol` 属根配置「只留高风险双实现」档 ⇒ **成本与放行都要人工批**（本班不代跑，统计结论域） |
| B 收观测面 | 停 shim、`_relay_calls.jsonl` 归档为一次性日志 | 需先承认「12 天 0 新观测」＝这条腿不打算要了；`_latest_drift.md` 与 drift_tracker 10 例同批处置，否则留半截 |
| C 只留基建 | 源归档＋测试保留，删 9/16 草稿 | §4 已证草稿 0 条人工分，删除不丢人工劳动；但会丢 30 条离线预填提示，且 `generated_by` 的缺件引用随之消失（**建议先补 §5 那条授权证据再决定**） |

## 7. 零改动自证与复跑命令

```bash
# 动单前后各跑一次，两份输出 diff 为空（本次实测：SHA IDENTICAL）
cd /d/code/psy-analysis && sha256sum data/benchmark_history/*

# 断档与聚合（§3 全部数字可由这一行复现，纯只读）
.venv/Scripts/python.exe -c "
import json,collections,pathlib
rows=[json.loads(l) for l in pathlib.Path('data/benchmark_history/_relay_calls.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
a=collections.Counter(); t=collections.Counter()
for r in rows:
    u=r.get('usage') or {}; a['n']+=1; t[r['model']]+=1
    a['pt']+=u.get('prompt_tokens',0) or 0; a['ct']+=u.get('completion_tokens',0) or 0; a['tt']+=u.get('total_tokens',0) or 0
    a['ca']+=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0) or 0
print(dict(t), dict(a), 'cache_hit=%.1f%%'%(100*a['ca']/a['pt']), 'days=', len({r['ts'][:10] for r in rows}), 'last=', max(r['ts'] for r in rows))
"
# 实测输出：{'gpt-5.6-sol': 38} {'n': 38,'pt':161106,'ct':3129,'tt':164235,'ca':120320} cache_hit=74.7% days= 1 last= 2026-09-10T03:19:38.266844
# §4 草稿对账与 §5 引用面出自 tmp/s922-19-aggregate.py（执行班当班证据件，gitignore 内，收班前自删；需要长期复跑请把它转正到 scripts/）

# 观测/测试面读数
.venv/Scripts/python.exe -m pytest tests/test_socratic_drift_tracker.py -q          # 10 skipped
.venv/Scripts/python.exe -m pytest tests -k "benchmark or sidecar or relay or shim or drift" -q   # 18 passed / 35 skipped
git log --oneline -1 -- scripts/benchmark_relay_shim.py                              # eec95c3（路径修复）
git ls-files data/benchmark_history                                                  # 空
```

⚠️ 复跑注意（本分区新坑，已回报主班）：**必须用 `.venv/Scripts/python.exe`**。裸 `python` 走全局解释器（sklearn 1.9.1 vs `.venv` 的 1.5.2），psy 全量会假红 30 failed + 13 errors（`check_array() got an unexpected keyword argument 'force_all_finite'`）。本档的数字全部在 `.venv` 下取得。
