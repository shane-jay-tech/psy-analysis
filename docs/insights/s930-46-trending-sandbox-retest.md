# 台账 #194① trending_weights 沙盒复测报告

> 产出单：s930-46（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-66（#194①「裸跑真写 trending_weights.yaml」前提依赖 #94 未修，#94 已结案（2a06659 案 A 收口夹具污染）⇒ 前提需沙盒复测；真库只读）。
> **零码改动；真库 sha 前后一致（6bf5776b…）**；沙盒位于系统 tmp（任务书要求 tmp/ 下——系统 tmp 与仓内 tmp 同为「不入库沙盒」语义，如实注）。

## 一、写点与修复现状（读码）

- 唯一写点：`daily_runner.py:354` `write_trending_yaml(trending, TRENDING_WEIGHTS_PATH)`（trending 计算成功后触发；:357 except 兜底「trending failure must not fail the run」）；
- 触发闸：`_should_compute_trending()`（:409-423）＝yaml 缺失/超 7 天/周一；
- 路径源：`paths.py:31` `TRENDING_WEIGHTS_PATH = DATA_ROOT / "trending_weights.yaml"`——**DATA_ROOT 已受 LITERATURE_FEED_DATA_ROOT 环境变量重指**（#94 案 A 的沙盒机制本身）。

## 二、沙盒复测结果（两 phase，命令与产物入档）

| phase | 动作 | 读数 |
|---|---|---|
| 1 | `LITERATURE_FEED_DATA_ROOT=<tmp>` 下探 `fp.DATA_ROOT`/`fp.TRENDING_WEIGHTS_PATH`/`trend.TRENDING_WEIGHTS_PATH` | **三处全部指向沙盒**（`<tmp>/trending_weights.yaml`）——paths 模块层重指生效；沙盒产物空（未触发写，符合预期——只验证了路径解析未真跑 fetch） |
| 2 | 同 env 下探 `daily_runner.TRENDING_WEIGHTS_PATH`（**写点实际引用的名字**） | **同样落沙盒**＋「写点落沙盒? True」——#94 修法（案 A 删夹具污染模块名，保留 paths 重指机制）没有破坏「环境变量重指 → 写点跟随」链路 |

## 三、#194① 前提三选一结论

**前提已失效（部分）**：#194① 的「裸跑真写 trending_weights.yaml」针对的是**测试会话**（夹具污染把 DATA_ROOT 带回生产路径的形态）——#94 案 A 收口后，**paths 层与 daily_runner 写点双层都正确跟随 LITERATURE_FEED_DATA_ROOT**，测试环境重指后即使触发 trending 写，落点也是沙盒而非生产 data/。「裸跑真写生产 yaml」的**测试面前提不再成立**；残余风险面＝**非测试的裸跑**（无 LITERATURE_FEED_DATA_ROOT 的真实 daily run——那本来就是生产语义，写生产 yaml 是正确行为）。

**纪律不变**：data/ 无还原点的总纪律与「不动真库」照旧——本结论只销 #194① 的测试面前提，不授权任何真库写入。
