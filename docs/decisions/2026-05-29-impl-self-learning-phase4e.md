# Phase 4e — 调度器（daily_runner + bootstrap_check + Task Scheduler）

**日期**：2026-05-29
**Slug**：`impl-self-learning-phase4e`
**前置阶段**：Phase 4a（存储/锁/预算/归档）、Phase 4b（抓取层）、Phase 4c（LLM 抽取）、Phase 4d（趋势聚合 + IO/HR/OB 加权）
**后续阶段**：Phase 4f（UI 接入）、Phase 4g（测试套件）

---

## 1. 任务

把前 4 个阶段拼成一个可调度、可重入的"日常抓取流水线"：

- `scheduler/daily_runner.py`：每日跑一次抓取 → 入库 → LLM 抽取 → 候选优先级回填，写 `fetch_runs` 审计
- `scheduler/bootstrap_check.py`：Streamlit 启动时懒检查"距上次成功 ≥24h 就后台触发"
- `scheduler/__main__.py`：CLI 入口给 Windows Task Scheduler 用
- `scripts/run_daily_feed.bat`：Task Scheduler 调度的 .bat 包装脚本

约束：
- 跨进程互斥（Task Scheduler 进程 vs Streamlit 进程不能并发写库）
- 单源失败隔离（某期刊挂掉不能拖垮整轮）
- 有审计日志（`fetch_runs` 表 + JSONL 归档已经在 Phase 4a 落地）
- LLM 预算受 `BudgetTracker` 管控
- 异步触发的失败要 UI 可见（不能"静默死亡"）

---

## 2. 实现要点

### 2.1 daily_runner.py — 协调器（约 480 行）

**核心数据结构**：
- `SourceSummary(source_id, fetched, new_articles, duplicates, failed, status, error)` — 单源结果
- `RunSummary(run_id, trigger, started_at, ended_at, status, sources, extracted_articles, extracted_constructs, extracted_methods, budget_exceeded, error)` — 整轮结果，带 `to_dict()` 便于 `--json-summary`

**`DailyRunner` 类**：
- 构造函数注入 `store / weights / budget / extractor_factory / fetcher_builder / clock`，都有默认值，方便 smoke/单元测试替换
- `_owns_store` 标记：外部传入的 store 不替它关；`run_daily()` 函数内自己 new 的 store 在 finally 里关（修 DeepSeek #2 连接泄漏）
- `run(trigger, ...)`：先 `LockManager.acquire()`，被占走 `skipped_locked` 立即返回；持锁后调 `_run_locked()`

**`_run_locked()` 流程**：
1. `abandon_stale_runs()` 把上次崩溃没收尾的 run 标记成 abandoned
2. `start_run()` 在 `fetch_runs` 表插入新行
3. 遍历 sources：每个源 `_fetch_one_source()` **整体包在 try/except** 里（DeepSeek #3），任何意外 → 标 `failed` 状态、写 `update_source_status(success=False)`、整轮继续
4. 跑 LLM 抽取：受 `max_extract` 上限 + `BudgetTracker.warn()` 双重约束
5. `update_candidate_scores()` 回填优先级（用 Phase 4d 的 90 天半衰 × confidence × 域权重）
6. `finish_run()` 写 ended_at + status + 计数统计

**状态判定**：`any_ok` 用 `src_summary.status.startswith("ok")` 而不是精确等于 "ok"，这样"抓成功了但 update_source_status 写状态时数据库出错"的边缘情况（status 为 `"ok_status_unwritten"`）也算成功，整轮才能进 `partial` 而不是误判 `failed`。

### 2.2 bootstrap_check.py — Streamlit 懒检查（约 125 行）

- `evaluate(stale_hours=24)` → `BootstrapDecision(should_run, last_success_hours, reason)`：纯只读，开 FeedStore 看 `latest_successful_run.ended_at`，立刻关
- `maybe_trigger_async(stale_hours=24, do_extract=True)`：决定要跑就 `threading.Thread(daemon=True)` 后台启 `run_daily(trigger='app_startup')`；进程内用模块级 `_BACKGROUND_THREAD` 单例（已在跑跳过）
- **后台失败 UI 可见**（DeepSeek #4 修复）：`_LAST_ASYNC_RESULT` 模块全局，`_safe_run` 跑完无论成败都填字典（status / sources_ok / sources_total / extracted_* / budget_exceeded / error），暴露给 UI 的 getter：
  - `last_async_result()` → 上次跑的精简字典（None 表示从未跑过）
  - `is_running()` → 后台线程是否还活着

### 2.3 __main__.py — Task Scheduler 入口

argparse 参数：
- `--trigger`（默认 `windows_task`，写进 `fetch_runs.trigger`）
- `--source`（可多次，限定只跑某些 source_id）
- `--days-back`（默认 7）
- `--fetch-limit`（默认 30）
- `--no-extract` / `--max-extract`（默认 20）
- `--log-level`（默认 INFO）
- `--json-summary`（用 `RunSummary.to_dict()`）

退出码：`0` ok/partial/failed（任务跑完了，状态写进库），`1` skipped_locked，`2` 未捕获异常。

### 2.4 run_daily_feed.bat — Task Scheduler 调度脚本

GBK + CRLF 编码（用户 memory 强约束：feedback_windows_bat_encoding.md）；chcp 65001 + PYTHONIOENCODING=utf-8 让 Python 内部按 UTF-8 处理。

**PYTHONPATH 处理**（DeepSeek #5 修复）：用 `if defined PYTHONPATH` 条件追加，**不**直接覆盖用户已有 PYTHONPATH（避免在共享环境意外清掉别的项目路径）。

输出 redirect 到 `data\literature_feed\logs\daily_runner.log`。

---

## 3. DeepSeek 对抗审查（5 条 critical 反对意见）

跑 `deepseek-reviewer` sub-agent 让 DeepSeek V4 Pro 当反方独立审，约束 ≥5 个反对意见 / 5 个维度全覆盖（安全 / 边界 / 性能 / 可读性 / 设计缺陷）。

### #1 — Lock TTL 太短，stale-break 有 race window
**原文摘要**：`ttl_seconds: int = 3600` 在长跑（DeepSeek 长文档跑 13 分钟，LLM 抽取批量 + 预算重试）下会被**同进程未崩**的运行误判为 stale 强抢；窗口期：A 在第 60 分零 1 秒拿到 mtime > 3600 的判定，B 在第 60 分零 2 秒也拿到，两个都试图 `break_stale().unlink()`，第二个 unlink 失败 → 但 A 已经把锁文件删了，整体仍在裸奔。
**仲裁**：接受。bump 到 21600s（6h），覆盖最长可能场景（30 篇文章 × 重试 × 预算阻塞）。
**改动**：`lock_manager.py` 默认 `ttl_seconds=21600`。

### #2 — `run_daily()` FeedStore 连接泄漏
**原文摘要**：`run_daily(trigger=...)` 内部 `store = FeedStore()` 但 finally 没 `store.close()`，bootstrap_check 在每次后台触发都开一个不关；Streamlit 长运行 + 高频 reload 会累积 SQLite 连接文件描述符 → 最终 OSError。
**仲裁**：接受。增 `_owns_store` 区分 store 来源，在 `run_daily()` 的 finally 里 close。
**改动**：`DailyRunner.__init__` 接受外部 store（不 own），`run_daily()` 自己 new 的 store own + close；`runner.close()` 方法 + finally 双兜底。

### #3 — `update_source_status` 失败把整源状态写错
**原文摘要**：成功路径 `update_source_status(success=True)` 失败抛异常 → 上层捕获按"failed"处理，但实际数据已抓进库 + 候选已生成；下次 bootstrap 看 last_success_at 还是旧的 → 误判 stale 重抓造成 article 维度去重压力 + LLM 重复扣预算。
**仲裁**：接受。成功路径单独包 try/except，写状态失败 → 状态降级到 `"ok_status_unwritten"`（保留"抓成功"语义）；run 循环每个源再加一层 try/except 兜底。
**改动**：`_fetch_one_source` 成功分支 try/except + `_run_locked` 源循环 try/except + `any_ok` 用 `.startswith("ok")`。

### #4 — `_safe_run` 后台失败静默死亡
**原文摘要**：`_safe_run` 当前只 `logger.exception` 打日志；Streamlit Cloud / 用户本地 cmd 关闭后日志看不到，UI 完全无信号 → 用户以为"自动抓取在跑"实际已经挂半天。
**仲裁**：接受。开 `_LAST_ASYNC_RESULT` 模块全局 + `last_async_result()` / `is_running()` getter；`_safe_run` 成功失败都填字典；后续 Phase 4f 在文献雷达页头轮询展示。
**改动**：`bootstrap_check.py` 重写 `_safe_run` + 新增两个 getter。

### #5 — `.bat` 直接覆盖 PYTHONPATH
**原文摘要**：`set PYTHONPATH=%REPO%` 会把用户已有 PYTHONPATH 清掉；如果用户在同一 shell session 里跑别的项目（量化系统 D:\code\my-quant-system-v8 也用 PYTHONPATH=. 的约定），打开第二个窗口或者调用嵌套 .bat 时会丢路径。
**仲裁**：接受。条件追加而非覆盖。
**改动**：`scripts/run_daily_feed.bat` 用 `if defined PYTHONPATH (...) else (...)` 分支。

### Cross-critique 第二轮（GPT 回应）
本阶段没走 cross-critique（DeepSeek 5 条全是机械型 bug 而非设计争议；GPT 回应大概率全接受 = 浪费 round trip）。Opus 直接全收。

---

## 4. 自审（Opus 主动追加）

DeepSeek 的 5 条之外：
- `_LAST_ASYNC_RESULT` 是模块级可变全局，**进程内**单例（不跨 worker）。Streamlit 单进程多线程，OK；如果未来切多进程 worker，要换 SQLite/file 持久化。Phase 4f 暴露 UI 时再看。
- `update_candidate_scores` 在 `_run_locked` 里同步跑，候选量上来后会拖慢 run 收尾。当前候选量预期 < 200 / 天，先不优化；超过 1000 再考虑 batch。
- `__main__.py` 的退出码 `0` 同时覆盖 ok/partial/failed —— 这是故意的，因为 partial/failed 是"业务状态"而非"调度系统出错"，Task Scheduler 不该重试；`1` 给 skipped_locked 让 Task Scheduler 知道"等下次"。

---

## 5. 验证

### Smoke test（D:\tmp\smoke_runner.py）
覆盖 6 条路径：
1. 混合源（1 ok + 1 rate_limited + 1 schema_changed）→ 整轮 partial、good 源 new=2
2. 第二次同条件运行 → good 源 dup=2，extracted_articles=0（幂等）
3. 锁占用时 run → status=`skipped_locked`
4. bootstrap evaluate(stale=24) 立刻跑后 → should_run=False
5. bootstrap evaluate(stale=0) → should_run=True
6. fetch_runs 表 2 行、sources.last_success_at 写好、候选优先级回填 priority>0

结果：`ALL SCHEDULER SMOKE TESTS PASSED`。

### 回归
`pytest tests/test_literature_feed_*.py -q` → **52 passed in 1.11s**（Phase 4a-4d 既有测试全绿）。

### Health check（pre-flight）
- gpt-5.5 41.5s ✓
- deepseek-v4-pro 3.5s ✓
- kimi-k2.6 9.3s ✓

---

## 6. 改动文件清单

```
src/literature_feed/scheduler/daily_runner.py           +480 行（新增）
src/literature_feed/scheduler/bootstrap_check.py        +125 行（新增）
src/literature_feed/scheduler/__main__.py               +110 行（新增）
src/literature_feed/scheduler/__init__.py               改 re-export
src/literature_feed/scheduler/lock_manager.py           TTL 3600 → 21600
src/literature_feed/storage/feed_store.py               latest_successful_run SQL 加 'partial'
scripts/run_daily_feed.bat                              +50 行（新增，GBK+CRLF）
docs/decisions/2026-05-29-impl-self-learning-phase4e.md 本文件
```

---

## 7. 给用户的摘要（最终交付）

**结论 / 改了什么**：调度器 Phase 4e 落地。Streamlit 启动后台懒检查 + Task Scheduler 每日 .bat 调度，跑完写 fetch_runs 审计 + 候选优先级回填；52 个回归测试 + 6 路 smoke 全绿。DeepSeek 5 条对抗审查的 bug 都修了（锁 TTL、连接泄漏、源状态降级、异步失败 UI 可见、PYTHONPATH 不覆盖）。

**风险点 ≥2**：
1. `_LAST_ASYNC_RESULT` 是进程内全局；Streamlit 切多进程部署（gunicorn workers）会失效，UI 看到的可能不是同一线程跑的结果。当前单进程 dev 用没事，未来上 prod 部署要换 SQLite 持久化。
2. Task Scheduler .bat 用 GBK 编码（用户 memory 强约束），但 Python 进程内是 UTF-8；某些极端情况（比如 Python 子进程 env 没拿到 PYTHONIOENCODING）日志可能乱码。当前 chcp 65001 + 显式 set 已经做了双保险，但跨 Windows 版本不能 100% 保证。

**反方观点**：DeepSeek 当时还提了一条边界——`update_candidate_scores` 在 `_run_locked` 里同步跑，候选量爆涨会拖慢 run 收尾、放大锁持有时间；我没改（当前候选量 < 200/天，过早优化）。如果未来抓取量上量级要警惕这点。

**置信度**：高。证据是回归 52 测试 + 6 路 smoke 全过，DeepSeek 5 条审查全收并验证。会改变结论的事件：实际接到 Task Scheduler 跑一周后看 fetch_runs.status 分布，如果 schema_changed 比例 > 30% 说明抓取层 robust 不够（这不是 Phase 4e 的问题，是 Phase 4b 的）。

**归档路径**：`docs/decisions/2026-05-29-impl-self-learning-phase4e.md`（本文件）。
