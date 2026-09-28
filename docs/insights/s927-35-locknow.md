# s927-35 · `break_stale()` / `acquire()` 的 `now` 时钟接缝统一（s922-109 遗留 1 落地）

- 班：`qoder-executor-20260928-0340-psy88`（波次 44 写位）
- 收尾班：`qoder-executor-20260928-0405-psy89`（波次 44b，落 §5 的**方案 B**＋卷宗原口径的压线改写，详 §7）
- 仓／HEAD：`D:\code\psy-analysis` @ `4ad0664`（主班 `s927-*` 最后一次入库）；收尾班开窗时 `git rev-parse --short HEAD` 现取 = `b74aad8`
- 结果件：`zcode-bridge/outbox/s927-35.result.md`（psy88 标 **partial** → psy89 收尾后为 **done**，判据读数见 §7）

## 1. 这一单从哪来（锚点复核）

- `zcode-bridge/done/s922-109-lock-stale-boundary.result.md:156-158` 原文：
  「**双口径的根治出口未实施（行为改动，待放行）**：给 `break_stale()` / `acquire()` 加同款可选
  `now` 接缝，`:133`/`:147` 两条即可改压线写法、裕量随之取消。加接缝会改公开签名，且
  `daily_runner` 侧要连带复核——本波「只补现状桩」的口径下不动。」
  ⇒ 锚点**当时有效、现仍成立**：接缝此前只在 `is_stale` 上（s921-13），两个公开入口拿不到注入能力。
- 双口径实况（改前，`git show 4ad0664:src/literature_feed/scheduler/lock_manager.py`）：
  `is_stale:128` 有 `now`；`break_stale:157` 硬调 `self.is_stale()` 不带参；`acquire:101` →
  `_open_and_lock:170` 同样不带参。测试侧 `tests/test_lock_manager.py:133`（ttl=10 / `utime now-30`，
  裕量 20s）与 `:147`（ttl=5 / `utime now-60`，裕量 55s）只能靠真实时钟裕量写法。
- `daily_runner` 连带复核（锚点要求的那一半）：`src/literature_feed/scheduler/daily_runner.py:255`
  调 `self.runner.lock._open_and_lock()` **不带参** ⇒ 新增的是"可选"关键字参数，缺省 `None`，
  调用面零改动、行为零变化。全仓另一处 `acquire(` 属 `src/utils/concurrency.py` 的 `SessionLock`
  （会话内锁，`acquire(resource, holder_id, ttl)`，与文件锁无关），不在本单面。

## 2. 改了什么（生产码 1 枚、26 insert / 10 delete，纯签名＋docstring）

`src/literature_feed/scheduler/lock_manager.py`（改后行号）：

| 位置 | 改动 | 缺省行为 |
|---|---|---|
| `:101` `acquire(self, now: Optional[float] = None)` | 加可选接缝；`:112` 透传 `_open_and_lock(now=now)` | `None` ⇒ 走真实时钟，与旧版逐字一致 |
| `:166` `break_stale(self, now: Optional[float] = None)` | 加可选接缝；`:175` `if not self.is_stale(now=now)` | 同上（旧版就是 `self.is_stale()` 不带参，`now=None` 落回 `time.time()`） |
| `:186` `_open_and_lock(self, now: Optional[float] = None)` | 内部件同步接参；`:191-192` `is_stale(now=now)` → `break_stale(now=now)` | 同上，且两侧**共用同一个读数**（旧版两次调 `is_stale` 各取一次 `time.time()`） |

**判据本体一字未动**：`:157` `stale = age > self.ttl_seconds`（`>` 的开闭、`age_min` 截断文案、
告警条件、`exists()`／`stat()` 短路全部原样）。本单不属统计数值／效应量域，未下任何数值结论。

## 3. 压线用例（新档，既有测试件零改动）

`tests/test_lock_now_seam_boundary.py`（新增，10 例，零 sleep／零裕量／零真实时钟依赖）：

- 边界本体（题面点名的两档）：
  - `test_break_stale_exactly_at_ttl_does_not_delete` — **恰好未超时**（`now = mtime + ttl`）⇒ 不删档、内容保留；
  - `test_break_stale_one_ulp_past_ttl_deletes` — **恰好超时**（`math.nextafter` 上侧 1 ulp）⇒ 删档、二次调用 False；
  - `test_break_stale_integer_second_past_the_line_also_deletes` — 整数秒 `ttl+1` 同侧复测（生产 ttl 是整秒）；
  - `test_acquire_exactly_at_ttl_does_not_steal_the_file` / `test_acquire_one_ulp_past_ttl_steals_and_rewrites`
    — 同两档落到 `_open_and_lock` 的 stale 强抢路径，可观察副作用＝锁文件里的 marker 有没有被越界删掉。
- 向后兼容面（完成标准 ③）：`test_break_stale_default_now_still_reads_wall_clock`、
  `test_acquire_default_now_still_steals_on_wall_clock` — 不传 `now` 时真实时钟照旧说了算。
- 生效反证（接缝不是装饰）：`test_break_stale_forwards_the_injected_now_once`、
  `test_acquire_forwards_one_reading_to_both_sides` — 断言注入值原样抵达 `is_stale`，
  且全程**只有这一个读数**、没有偷偷回落 `time.time()`。
- 签名面：`test_the_two_entries_now_expose_the_seam` — 接缝存在、且缺省是 `None`。

隔离口径照 `tests/test_lock_manager.py:20-25`／`tests/test_lock_stale_boundary.py:39-44`：
autouse 桩挡掉 `ensure_dirs()`，锁文件一律落 `tmp_path` ⇒ **不写生产 `data/`**（`data/` 被 gitignore，无还原点）。

## 4. 读数（`.venv` 解释器，Python 3.12.9，定向文件列表）

```
$ .venv/Scripts/python.exe -m pytest tests/test_lock_now_seam_boundary.py -q
10 passed
$ .venv/Scripts/python.exe -m pytest tests/test_lock_now_seam_boundary.py tests/test_lock_manager.py \
    tests/test_lock_stale_boundary.py tests/test_lock_alert_log.py \
    tests/test_literature_feed_lock.py tests/test_literature_feed_scheduler.py -q
1 failed, 69 passed in 1.29s
FAILED tests/test_lock_manager.py::test_break_stale_and_acquire_expose_no_clock_seam
```

- 新档 10 例全绿 ⇒ 两边界用例绿（完成标准 ②）。
- 既有的 `tests/test_lock_manager.py:133`（裕量 20s）／`:147`（裕量 55s）**一字未动仍绿**；
  `tests/test_lock_stale_boundary.py` 19 例全绿；`test_lock_alert_log.py`／`test_literature_feed_lock.py`／
  `test_literature_feed_scheduler.py` 全绿 ⇒ 除 §5 那一枚外，锁域零回归。

## 5. 曾未闭合项：`tests/test_lock_manager.py` 的结构桩（**已由收尾班闭合，见 §7**）

> ✅ 2026-09-28 收尾班 `qoder-executor-20260928-0405-psy89`：主班复核后裁定**卷宗原口径优先**
> （卷宗「做什么」逐字要求"并改压线写法（:133/:147）"，横幅的"既有用例一字不改仍要绿"比卷宗窄），
> 且该桩自己的 docstring 早已写明"若哪天实现补了 `now` 参数，本用例会红——那是设计内翻正"。
> ⇒ 按下面 **方案 B** 翻转断言并补出处，同时把两条裕量用例改成压线写法。本节三个形状保留作裁决记录。

- 该桩断言 `inspect.signature(LockManager.break_stale).parameters == ["self"]`，
  即"签名里**没有** `now`"——加接缝必然把它翻红，这是**逻辑上不可回避**的，不是漏改。
- 它自己的 docstring 早已写明：「出口（属行为改动、本班不做）……若哪天实现补了 `now` 参数，
  本用例会红——**那是设计内翻正**」（`tests/test_lock_manager.py:305-306`）。
- 本班**没有**改这枚既有桩来凑绿：波次 44 横幅对 `s927-35` 明确写了「既有用例一字不改仍要绿
  （改既有桩来凑绿＝越界）」，而卷宗「做什么」又要求加接缝——两者在这枚桩上互斥，
  超出生产码的裁决面 ⇒ 按波次 42 §B3 停手落 `partial`，把处置形状写成可批：
  - **方案 A（最小，推荐）**：删除 `tests/test_lock_manager.py:299-313` 整条用例，
    同时把 `:293-298` 那段导引注释里"不能改走接缝写法"的理由改成"接缝已落地"。改动面 1 枚测试件、可回滚。
  - **方案 B**：把断言反转成正向签名钉（`["self", "now"]` ×2）——与本档
    `test_the_two_entries_now_expose_the_seam` 重复，若走 B 建议直接删 A 那条重复件。
  - **方案 C（不改测试件）**：保留红，登记为在册已知红 ⇒ 不推荐（锁域定向套件长期带红会掩掉真回归）。
  - 回滚成本：生产码是**加可选参数**，`git revert` 单文件即可，调用方零改动；测试件是新增档，删除即净。

## 6. 复现指令

```
cd /d D:\code\psy-analysis
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m pytest tests\test_lock_now_seam_boundary.py tests\test_lock_manager.py -q
```

未跑全量（约 399 s，并发归因不了，口径交主班收班统一取）。
⚠ 宽 `-k` 会撞上两枚 HEAD 同红的在册件（`test_backup_user_data`、
`test_export_gate_global_scan::test_all_download_buttons_accounted_for`），本单一律用定向文件列表。

## 7. 收尾记录（psy89，波次 44b）：§5 方案 B 落地＋两条裕量用例改压线

**只改 1 枚文件**：`tests/test_lock_manager.py`（`git diff --numstat` 现值 **78 insertions / 24 deletions**，
纯测试件；生产码 diff 仍是 psy88 的 26/10、`is_stale` 判据 `:157` 一字未动；
`tests/test_lock_stale_boundary.py`／`tests/test_lock_now_seam_boundary.py` **零改动**）。

1. `test_break_stale_deletes_only_when_stale`（原 :133 → 现 :136）：`ttl=10 / os.utime(now-30)`
   的 20 秒真实时钟裕量 ⇒ 改固定基准 `_FIXED_MTIME` ＋注入 `now`：
   `age == ttl` 不删（钉 `>` 非 `>=`）／`age = ttl+1` 删／二次调用不炸。**断言只紧不松**。
2. `test_acquire_steals_a_stale_lock`（原 :147 → 现 :162）：`ttl=5 / os.utime(now-60)` 的 55 秒裕量
   ⇒ 改注入 `now` 两侧同测，可观察副作用＝锁文件里的 marker 有没有被越界删掉
   （恰 `age==ttl` 保留、`age=ttl+1` 消失）；两相之间补一次 `os.utime` 复位（追加写会推进 mtime）。
3. 结构桩翻转（原 `test_break_stale_and_acquire_expose_no_clock_seam` :299 → 现
   `test_break_stale_and_acquire_expose_the_clock_seam` :343）：断言由"签名里没有 `now`"
   反转为 `is_stale`/`break_stale`/`acquire`/`_open_and_lock` **四者都含 `now` 且缺省 `None`**；
   docstring 写明"设计内翻正已兑现"＋出处（s927-35／本档 §5 方案 B／s922-109 遗留 1＋该桩自述原文）。
   为避免与新档 `test_the_two_entries_now_expose_the_seam` 纯重复，本桩额外钉**内部透传件
   `_open_and_lock` 也接了 `now`**（缺它则 `acquire` 注入的时钟到不了 stale 强抢路径）。
   ⚠ 桩件更名：全仓 `grep -rn "expose_no_clock_seam"`（`--include=*.py --include=*.md`）现只命中
   本档 §4 的历史读数行／本档 §7 的更名说明，＋翻转桩 docstring 里引用自己原名的那一行 ⇒ **零代码消费者**，
   更名不伤任何 `-k`/nodeid 选择面。
4. 块注释改准（现 :331-342）：原断"那两处**不能**改走接缝写法，因为入口根本没接 `now` 参数"已过期，
   现改成"接缝已落地、两条用例已压线化、裕量随之取消"。
5. 附带订正 2 处被 psy88 生产码 diff 位移的注释锚点（同件、纯注释，无行为影响）：
   文件头"判陈旧在 :128 起"→ `:137`（并保留 s922-10 的漂移叙述、追加 s927-35 订正一行）；
   `test_is_stale_boundary_…` docstring 里"钉住 `lock_manager.py:148`"→ `:157`。
   另把块注释里的 `:83` 换成例名（行号会漂，例名不会）。

### 判据读数（`.venv` ＝ Python 3.12.9，`PYTHONIOENCODING=utf-8`，定向文件列表，未跑全量）

| 件 | 收尾前 | 收尾后 |
|---|---|---|
| `tests/test_lock_manager.py` | 1 failed / 21 passed（22 例） | **22 passed**（22 例） |
| `tests/test_lock_stale_boundary.py` | 19 passed | **19 passed**（未改） |
| `tests/test_lock_now_seam_boundary.py` | 10 passed | **10 passed**（未改） |
| 三件合跑（卷宗判据口径） | **1 failed, 50 passed** | **51 passed, 0 failed**（rc=0） |
| 六件锁域合跑（+`test_lock_alert_log`／`test_literature_feed_lock`／`test_literature_feed_scheduler`） | 1 failed, 69 passed | **70 passed**（rc=0） |
| 另两枚 `LockManager` 测试消费者 | — | `test_instance_lock_alert_gap_pin.py` 12 passed；`test_lr_rerun_apptest.py` 8 passed |

⚠ `tests/test_lr_rerun_apptest.py` 不带沙盒环境变量时是 **8 errors**（该件自带文献库守卫，
setup 里断言 `LITERATURE_FEED_DATA_ROOT` 必须指向沙盒、否则拒跑），与本单无关；补上变量后 8 passed。
⇒ 未发现"裕量写法在别处还被依赖"的连带红，故未落 partial。

零写侧证（`data/` 被 gitignore、无还原点）：`data/literature_feed/locks/feed_fetch.lock` 仍为
104 B／mtime `Sep 23 12:15`（本班全程走 `tmp_path` ＋ autouse 挡 `ensure_dirs()`，沙盒 env 落 `D:\code\tmp\…`）。

### 复现指令（收尾后现值）

```
cd /d D:\code\psy-analysis
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m pytest tests\test_lock_manager.py tests\test_lock_stale_boundary.py tests\test_lock_now_seam_boundary.py -q
```

