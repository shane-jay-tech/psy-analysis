# psy 时敏断言专项清点（s920-24，wall clock 现算值做相等断言）

- 清点：2026-09-20 01:1x–01:3x。**只读为主，只修明确撞红的一条**（另有 1 条同类风险登记）。
- 锚点复核：`done/s919-21-psy-test-rename.result.md:79-81` 遗留 1 原文
  「凡是 `datetime.now()`/`time.time()` 出现在被测函数内部的测试，都该按『两侧留裕量』或『比语义不比字节』的写法复查一遍
  ——建议单开一做一单专项排查（本单只处理了撞上的两条）」⇒ 成立，本单就是那张专项排查单。

## 一、判据（先把"什么算时敏"说清，否则清点会退化成 grep 计数）

两条物理事实决定了风险方向，本单所有判定都由它们推出：

1. **测试侧的 `now()` 永远早于被测侧的 `now()`** ⇒ 两次读数之间"age"只增不减。
   所以：断"**已经**过期/已变化/超过阈值"的一侧天然安全；断"**还没**过期/仍相等"的一侧才是脆弱面，
   其安全度＝`阈值 − 测试构造的 age` 这个**剩余裕量**除以"两次读数之间的调度延迟"（GC、CPU 抢占、磁盘抖动）。
2. **整数截断方向**：被测函数若做 `int(secs/60)` 这类下取整，ε 只会把结果推到同一侧 ⇒ 单侧安全；
   若做四舍五入或字符串日期比较，则两侧都可能被 1 单位的漂移翻掉。

据此，"裕量 ≥ 数十秒"或"截断方向单侧安全"或"时间戳只是测试自己造的数据（不参与相等断言）"三种情形一律判**安全**，
只有"裕量在秒级以下且断言是相等/布尔"才判**待修**。

## 二、清点结果：tests/ 里涉时钟的 13 个文件逐条分类

```bash
cd /d/code/psy-analysis
grep -rn "datetime\.now()\|time\.time()\|date\.today()\|utcnow()\|monotonic()" tests --include="*.py"
```

| 文件:行 | 时钟怎么用 | 判定 | 依据 |
|---|---|---|---|
| `test_lock_manager.py:87-91` | `ttl=10`，mtime 拨到 `now-9` 断"不陈旧"；`now-15` 断"陈旧" | **待修 ⇒ 本单已修** | "不陈旧"侧裕量只有 **1 秒**（判据 1），全量跑一次 GC 就能翻红 |
| `test_lock_manager.py:102,111,130` | `now-30`(ttl10)／`now-60`(ttl5)／`now-5`(ttl1)，均断"已陈旧" | 安全 | 全在"只增"的一侧（判据 1），且裕量 20s/55s/4s |
| `test_workspace.py:410-428` | `humanize_elapsed(now-15min)==「15 分钟前」`等 4 条 | 安全 | `src/utils/workspace.py:817-825` 是 `int(secs/60)` **下取整** ⇒ ε 不会把 15 变成 14；"刚刚"门限 60s 而 ε<1s |
| `test_analyze_usage_logs.py:15,34-53` | 文件名用 `_day(offset)`，断 `load_events(days=N)` 命中集合 | 安全 | `scripts/analyze_usage_logs.py:24-27` 是 `file_date >= cutoff` 的**字符串日期同向比较**，测试与 SUT 的 `today` 即便跨午夜也是**同一天偏移**；实测用到的 offset 是 0/1/2/9 对 window 1/7，最差落到 8 vs 7 仍排除 ⇒ 无一项压在边界 |
| `test_literature_feed_trend.py:166,172-195,203-211` | `compute_recency_decay(x, ref_date=today)` | 安全 | **显式传 `ref_date`**，两侧同一个对象 ⇒ 无现算竞态；:179-181 的 `== 1.0` 走 None/空/非法分支不涉时钟 |
| `test_literature_feed_trend.py:274,282,354,360` | 造数据用 `today - days=200+i / 10+i / 5 / 3`，`window_days=30` | 安全 | `_seed_articles_and_keywords(n_old=2, n_new=3)` ⇒ 实际 day 距是 200/201 与 10/11/12，**离 30 窗口最远 18 天** ⇒ 跨午夜 1 天不改归属 |
| `test_literature_feed_lock.py:66` | mtime `now-7200`，`LockManager(ttl_seconds=3600)` 断陈旧 | 安全 | 裕量 3600 秒，单侧 |
| `test_lock_alert_log.py:47` | mtime `now-7200`，`ttl_seconds=1` 断告警 | 安全 | 裕量 7199 秒，单侧 |
| `test_instance_lock.py:71,95` | mtime `now-3600` 对 `DEFAULT_STALE_SECONDS=600`（`src/utils/instance_lock.py:22`） | 安全 | 一处断夺取、一处断"存活 pid 不夺"，两侧靠 pid 存活判定而非时间 ⇒ 时间只是陪衬，裕量 3000 秒 |
| `test_prune_archive.py:81` | `now-120*86400` 断被 `rule_raw` 列入 stale，且 dry-run 不删 | 安全 | 120 天 vs 阈值级差（数十倍），且新文件 age≈0 |
| `test_socratic_quality.py:93,97` | 往**合成的基准 JSON 里写**时间戳/`generated_at` | 安全 | 时间戳是造数据，后续断言不比它现算 |
| `test_ui.py:1236` | 工作区 fixture 里写 `_saved_at = now()` | 安全 | 断言只有 `"_saved_at" in loaded`（键存在），不比值 |
| `test_e2e_v52_paths.py:74`、`test_playwright_e2e.py:46`、`test_playwright_golden_research_flow.py:370` | `deadline = time.time()+N; while time.time()<deadline` | 安全 | 轮询超时，不是相等断言；最坏是变慢不是变红 |

⇒ 13 个文件里**只有 1 条**符合"待修"判据（已修）；另有 **1 条同类风险登记**（见 §四遗留 1，裕量 4 秒的单侧）。

## 三、修掉的那一条（psy 仓，本次提交）

`tests/test_lock_manager.py::test_is_stale_uses_margin_on_both_sides_of_ttl`：
`ttl_seconds=10 / mtime=now-9`（裕量 1 秒）→ **`ttl_seconds=100 / mtime=now-50`（裕量 50 秒）**，另一侧 `now-150`（裕量 50 秒）。
用例 docstring 同步写清两件事：(a) 为什么不注入时钟（`lmk.time` 就是全局 `time` 模块，psy 有后台 autosave 线程，
monkeypatch 它没有"只限本模块"的效果）；(b) **`>` 与 `>=` 的边界语义这条用例测不到**，要测必须给 SUT 加时钟接缝 ⇒ 登记为遗留 2。

自查：这条裕量 1 秒是**本会话我自己上午写下的**（`test_lock_manager.py` 的 s919-22/s919-21 收口），
当时的注释还写着"ttl 内 1 秒：必不陈旧"——"必"字不成立，正是锚点说的"同类风险仍在"的具体形态。

验证：`tests/test_lock_manager.py` 连跑 3 次 **13 passed**（0.26s／0.29s／1.70s，时长抖动本身说明调度延迟不可预算 ⇒ 1 秒裕量凭什么稳）。

## 四、遗留（登记，未做）

1. `test_lock_manager.py:130` 的 `ttl_seconds=1 / mtime=now-5`：裕量 4 秒、且在"只增"的单侧 ⇒ 今天判安全，
   但它是同一写法的下一批候选；若将来 `test_alert_fires_once_per_kind` 加断"未过期"一侧，就会立刻变脆弱。
2. **`>` 与 `>=` 无测**：`lock_manager.py:123` 的 `is_stale` 判定符号没有真值测。
   根治是给 SUT 一个时钟接缝（`def is_stale(self, *, now: float | None = None)`），
   这样边界能用 `now=ttl` 精确断言，不必再靠"留裕量"绕。属生产码签名改动，本单不动。
3. 同类清点在 **quant 仓**没做（本单 cwd 是 psy）。quant 侧已知有 `frozen_clock` 这套接缝
   （他班 q918-03 的 commit 里在用 ⇒ 说明该仓选的是"注入时钟"路线，比 psy 的"留裕量"更彻底），
   psy 要不要跟同款接缝，是 §四-2 的实现选型输入。

## 五、零改动范围自证

- 本文件＋`tests/test_lock_manager.py` 是全部改动；**未改任何生产码**、未改 `data/`、未删任何文件。
- 复现：
```bash
cd /d/code/psy-analysis
git show --stat --oneline HEAD          # 只含这两份文件
grep -rn "datetime\.now()\|time\.time()\|date\.today()" tests/test_lock_manager.py
for i in 1 2 3; do .venv/Scripts/python.exe -m pytest tests/test_lock_manager.py -q | tail -1; done
```
