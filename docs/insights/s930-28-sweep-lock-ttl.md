# sweep 抢锁顺序与双 TTL 口径对照材料

> 产出单：s930-28（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-49 遗留（s923-12 问题 3/4/5 挂账：sweep 抢锁之后/TTL 3600 与锁 TTL 21600 互不指认/run 死因不可再分）。
> **零改动**；scheduler 面只读。

## 一、抢锁顺序实况（s923-12 问题 3 复核）

`daily_runner.py` docstring 自述流程（:13-22）＋代码实证：

```
1. LockManager.acquire() 独占锁（冲突即退出）——:249-258 _LockedCtx
2. store.abandon_stale_runs() 清卡住的旧 run
3. store.start_run() 记 fetch_run_id
4-6. 抓取/抽取/回填
7. finish_run()
```

**「sweep 抢锁之后」形状复核**：abandon_stale_runs（:2 步）在抢锁**之后**执行＝只有拿到锁的进程才有资格把别家的 running 标 abandoned——顺序本身安全（无锁清理竞态）；「问题 3」的挂账点若指「abandon 发生在锁内才安全」——**现实现已满足**（docstring 顺序与 _LockedCtx 包裹实证一致）。

## 二、双 TTL 口径对照（s923-12 问题 4 复核）

| TTL | 值 | 位置 | 管辖对象 | 语义 |
|---|---|---|---|---|
| 锁 TTL | **21600s（6h）** | lock_manager.py:54（「daily run + LLM 抽取最坏情况也用不到」） | lock 文件 mtime 陈旧度 ⇒ stale 强抢判据 | 「进程死锁多久后允许别人抢锁」 |
| run TTL | **3600s（1h）** | feed_store.py:321 `abandon_stale_runs(ttl_seconds=3600)` | fetch_runs 表 running 行的 started_at ⇒ abandoned 标记 | 「run 记录多久没动静后标记放弃」 |

**互不指认实锤**：两常量各自字面量、无引用关系；语义上管辖不同对象（锁文件 vs DB 行）**并非必须同值**——真正的口径缺口是「**1h run TTL < 6h 锁 TTL** 的倒挂」：run 记录 1h 即被标 abandoned（但持锁进程还在跑，最长 6h）⇒ abandoned 标记是**乐观猜测**（进程可能活着）；若 abandoned 后有重建/重跑逻辑，会与持锁进程并发。现状无害的前提＝abandoned 仅是**标记**（不触发重建）——需在材料里点名为「隐含依赖」。

## 三、run 进程死因不可再分（s923-12 问题 5 复核）

fetch_runs 表仅有 status/started_at/ended_at/summary/error——**abandoned 与 crash 不可区分**（进程被杀时不留 error，ended_at 为空直到下一轮 abandon 扫描补写——补写的 ended_at 是**扫描时刻**非死因时刻）。现状＝时间精度损失（死因时刻漂移最多一个扫描间隔）。

## 四、三挂账的处置材料（不实施）

| 挂账 | 处置选项 | 建议 |
|---|---|---|
| 问题 3 抢锁顺序 | 现状已安全；补 docstring 一句「abandon 在锁内执行＝顺序保证」 | 零码注释级 |
| 问题 4 双 TTL | ①互指注释（两常量互引「另一口径见 feed_store:321/lock_manager:54」）②若怕 abandoned 乐观猜测误判，把 run TTL 提到 ≥锁 TTL（3600→21600）或 abandoned 触发逻辑加「锁已释放」前置 | 注释级＋可选行为面（人工） |
| 问题 5 死因不可再分 | run 行加 heartbeat 列（进程周期 touch）⇒ abandoned 时可区分「心跳停=crash」vs「心跳在=活进程被误标」 | schema 变更，独立小单 |

**隐含依赖警示**：只要 abandoned 标记不触发任何自动重建，「双 TTL 倒挂」就只是记账精度问题——**上重建/重跑逻辑之前必须先统一双 TTL 或加心跳**（否则重建与活进程并发）。
