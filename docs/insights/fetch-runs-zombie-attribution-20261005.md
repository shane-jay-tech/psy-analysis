# fetch_runs 僵尸 running（TTL 未生效）与 daily_runner 运行面归因材料——s1004-36

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T10:4x ｜ 性质：真库只读，回收/补跑属写路径留主班
> 矿源：`zcode-bridge/done/20260925-154310-1b5e.result.md`＋`e00d.result.md` 两遗留逐字核对在册（勿重复裁 e00d 已注）。

## 一、现值查询（只读，与矿源对账）

`$ .venv/Scripts/python.exe -c "sqlite3.connect('file:data/literature_feed/feed.sqlite?mode=ro', uri=True)…SELECT status, COUNT(*) …GROUP BY status"` →

| status | 条数 |
|---|---|
| running | **2**（run 43 @2026-09-23T03:55:07Z、run 44 @04:15:30Z，ended_at 均 NULL） |
| abandoned | 8（最后一条 run 42 标记于 2026-09-23T03:55:07Z） |
| completed | 33 ｜ failed | 1 |

**与矿源逐字对账**：1b5e/e00d 所记「2 条 running 自 2026-09-23T04:15Z」**现值未变**（12 天未回收）。库文件：`data/literature_feed/feed.sqlite`（mtime 2026-09-23 12:15 本地＝最后一次写入即 run 44 起点）。⚠ 探针只读连接触碰了 `feed.sqlite-shm` 边车（mtime 更新为今日），**主库文件 mtime 未动＝零数据写**，如实留痕。

## 二、TTL 未生效链路图（每环 rg/实证）

```
fetch_runs 2 条僵尸（9/23T04:15Z 起）
  ↑ 不回收
abandon_stale_runs(ttl=3600) 仅一处调用＝daily_runner.py:291（流程第 2 步）
  ↑ 不跑
daily_runner 双触发设计（daily_runner.py:1-8 docstring）
  ├─ 腿1 Windows Task Scheduler：scripts/run_daily_feed.bat 在盘，
  │    但 bat 注释的注册建议（schtasks /Create /TN "PsyLiteratureFeed"）从未执行
  │    ⇒ $ schtasks /query 全表 grep → 无 PsyLiteratureFeed（仅有 kaoyan-news-daily/
  │      PsyWeeklyBackup/QuantDailyPipeline_v5 等无关项）【腿1 自始未注册或已被删】
  └─ 腿2 Streamlit 懒触发：bootstrap_check.maybe_trigger_async 定义在世（scheduler/__init__.py
       仅 re-export），app.py 与 src/ui 零调用【rg 实证】⇒ 腿2 从未接线
  ↑ 最后一次运行
9/23 11:55:07 本地（=03:55:07Z）：daily_runner 跑过一次——同一秒先 abandon run 42 再 start run 43
  （流程第 2→3 步顺序吻合），进程中断未 finish；12:15:30 本地（=04:15:30Z）第二次尝试 run 44 亦中断
  ⇒ locks/feed_fetch.lock mtime=2026-09-23 12:15:30 与 run 44 起点 Z+8h 精确吻合＝全链停摆时刻
  ⇒ 这两次调用的归属未定（无 TaskScheduler 项、logs/ 目录为空连 daily_runner.log 都没有＝非 bat 通路，疑手动）
```

**归因结论**：TTL 机制本身无 bug（9/23 前多批 abandoned 记录证明它正常工作过）——是 daily_runner 的**两条触发腿今天都不存在**（腿1 未注册、腿2 未接线），TTL 回收随之停摆 12 天；43/44 两僵尸正是最后一次运行自身中断的遗产。

## 三、处置两案（写库动作留主班）

| 案 | 动作 | 性质 |
|---|---|---|
| A 补跑回收（清尾部） | 跑一次 `store.abandon_stale_runs()`（或等价 SQL UPDATE 2 行）→ 43/44 标 abandoned | **写库**，人工放行；一次性 |
| B 修调度（结构） | ①按 bat 注释注册 `PsyLiteratureFeed` 计划任务（schtasks /Create，外部改状态，人工）；②app 启动面接线 `maybe_trigger_async()`（1-2 行，改被跟踪文件另开单） | 两腿至少活一腿，TTL 周期回收才能恢复 |

**建议 A+B 组合**：先 A 清 2 条僵尸，再 B 恢复周期（否则清完还会再积）。

### 证据存根

- 只读查询：`$ sqlite3(file:...feed.sqlite?mode=ro) SELECT…` → 2 running/8 abandoned/33 completed/1 failed（逐行输出见 §一）。
- 调用链：`$ grep -rn "abandon_stale_runs" src/literature_feed/` → 唯一调用 daily_runner.py:291；`$ sed -n 321,333p feed_store.py` → TTL 实现逐字。
- 腿1：`$ schtasks /query /fo LIST` 全表 → 无 PsyLiteratureFeed；`$ cat scripts/run_daily_feed.bat` → 注册建议在注释里。
- 腿2：`$ grep -rn "maybe_trigger_async" src/ app.py tests/` → 仅 __init__ re-export＋docstring，零消费方。
- 停摆时刻：`$ stat feed.sqlite locks/feed_fetch.lock` → 12:15:30 本地吻合 run 44 起点 Z+8h。
- 零写库声明：本单全程 mode=ro 连接；唯 -shm 边车 mtime 被只读连接触碰（已披露）。
