# 2026-05-30 · /implement · Trending Weights（动态趋势加权层）

## 用户原始需求

> "文献抓取需要我每天启动应用才会进行吗，另外那个人力资源权重部分，我觉得可以根据抓取的前沿论文进行动态调整"

拆成两件事：
1. **A**：把抓取注册到 Windows Task Scheduler，不需要每天开 app。
2. **B**：让 domain_weights 跟着前沿论文动态走。

## 总指挥（Opus）拆解

A 已现场完成（`schtasks /Create /SC DAILY /TN PsyLiteratureFeed /TR run_daily_feed.bat /ST 09:00`，下次 2026/5/30 09:00）。

B 走 `/implement` 完整流程。设计要点：
- **不动 `domain_weights.yaml`**（保留专家先验）。
- 新增 `trending_weights.yaml`：30 天滚动窗口 / 90 天 baseline / multiplier_cap 1.2（+20% 上限）。
- spike_ratio = window_weighted / max(baseline_weighted, **1e-9**)；multiplier = 1.0 + min(cap-1, max(0, (spike-1)·0.05))。
- 公式 `priority = decay × confidence × (1 + domain_score) × (1 + method_score) × **(1 + trending_score)**`。
- Human-in-loop：UI 给"忽略 / 收入静态"按钮，`ignored / promoted / promoted_log` 跨重算保留。
- **promoted 加保底乘子**（cap 一半）—— 防止人工促入变成 no-op。
- 调度：每周一 + 文件 >7 天 旧 时重算；失败回退缓存 yaml。

## 阶段 1：GPT-5.5 Pro 主程序员（quick mode）

实现 8 个文件 + 28 测试：
- `src/literature_feed/trend/trending_weights.py`（新建 316 行：`TrendingEntry` / `TrendingWeights` dataclass + `compute_trending_weights` + `write/load_trending_yaml`）
- `src/literature_feed/trend/scorer.py`（priority 公式加 `trending_score` 入参）
- `src/literature_feed/trend/__init__.py`（导出符号）
- `src/literature_feed/scheduler/daily_runner.py`（trending 调度 + 失败回退）
- `src/literature_feed/scheduler/__main__.py`（`--compute-trending` 等 CLI 旗）
- `src/literature_feed/paths.py`（`TRENDING_WEIGHTS_PATH`）
- `src/literature_feed/ui/feed_panel.py`（趋势 Tab 增加 trending 编辑面板）
- `tests/test_trending_weights.py`（28 测试覆盖 dataclass、round-trip、compute、scorer 兼容、loader）

GPT 自审 3 条：(1) trending 没做"窗口太短样本不足"门槛 → 接受（多测试再说）；(2) 没做 promoted 保底 → 标记后续可加；(3) round 精度可能影响极端测试 → 接受。

## 阶段 2：DeepSeek V4 Pro 评审官（5 维度）

**0 critical, 4 high, 5 medium, 2 low**：

| 严重度 | 维度 | 问题 |
|---|---|---|
| HIGH | 功能 | scorer 把 raw 作者 keyword 直接送 trending lookup，没 canonicalize → 命中全 miss |
| HIGH | 边界 | `max(baseline, 1.0)` 让 baseline=0.5 这种小基线被夸大成 1，新词检不到 |
| HIGH | 功能 | `compute_trending_weights` 失败时直接抛，整条 pipeline 挂；无缓存回退 |
| HIGH | 功能 | promoted 只在 entries 加，但 multiplier=1.0（no-op），人工促入对分数没影响 |
| MED | 边界 | `_should_compute_trending` 短路判断 `getmtime() and (...)` 当 mtime=0 时 age 算成 0（误判不旧） |
| MED | 边界 | `load` 用 `or 1.3` 对 0 值会误覆盖 |
| MED | 健壮 | atomic write 没 fsync |
| MED | 默认值 | cap 默认应是 1.2 不是 1.3（与设计文档对齐） |
| MED | 测试 | `TestWriteLoadRoundTrip` 在测试文件里被定义两次（后者 shadows 前者） |
| LOW | 可读 | 部分注释里"30/90"应是"window/baseline" |
| LOW | 性能 | `is_ignored` / `is_promoted` 每次重算 set，可缓存 |

无 critical → 按 CLAUDE.md "二轮 cross-critique 仅 critical 触发" → **二轮跳过**，直接 Opus 仲裁落地。

## 阶段 3：Opus 仲裁与落地

**全部 4 high 接受**，**5 med 接受 4 条**（LOW 性能不接受 — `set` 重算开销远小于实例数）：

- HIGH #1：`scorer.update_candidate_scores` 在送 `trending.trending_score` 前对 `kw_list + hits` 全部走 `weights.canonical_for()`。
- HIGH #2：`daily_runner` 的 except 里加 `trending = load_default_trending()` fallback（缓存 yaml）。
- HIGH #3：`spike_ratio = window_weighted / max(baseline_weighted, 1e-9)`。
- HIGH #4：promoted 进窗口走公式后用 `max(multiplier, 1.0 + (cap-1)*0.5)` 保底；窗口外的 promoted-only 也用同一保底替代 `multiplier=1.0`。
- MED：`_should_compute_trending` 删除 `getmtime() and (...)` 短路；`load` 改用 `is not None`；写入 `os.replace` 前 `fsync`；module + dataclass + 函数签名的 cap 默认值 1.3 → 1.2；测试文件去重 `TestWriteLoadRoundTrip` 第二份。

## 验证

- 单测：`tests/test_trending_weights.py` — **28/28 passed**
- 全量回归：1426 baseline + 28 new = **1454 passed, 1 skipped**（74s）
- Task Scheduler：`PsyLiteratureFeed` Ready, 下次 2026/5/30 09:00:00 ✅

## 风险（≥2）

1. **Echo chamber**：trending 是从同一来源抓的论文里学来的，自我强化是潜在风险。当前用 cap 1.2（最多 +20%）+ 仅作为乘子（不删 domain_weights）+ human ignore/promote 按钮三条防线把它压住。最坏情况：某个会议季把单一关键词刷起来 → 用户看到点忽略即可。
2. **冷启动**：第一次跑没历史 baseline，所有词的 spike_ratio 接近 ∞（除以 1e-9），全部触顶 cap。这一周的 priority 会失真。缓解：Monday 重算 + >7 天 stale 重算意味着第二周开始 baseline 就有了；同时 multiplier 上限 1.2 决定"失真也只 +20%"。

## 反方观点

DeepSeek 隐含立场：这个模块对小流量个人用户**性价比可疑** —— 一个人用、每天文章数十篇量级，"动态加权"和"用户手动给 4 个新关键词"几乎等价，但前者多了 316 行代码 + 28 测试 + 一个 yaml 文件 + 一条 cron。如果用户后续觉得"调一调感受不到差别"，应该考虑直接关掉 `--compute-trending` 跑纯静态版。

## 置信度

**中**。代码层面正确（DeepSeek 找到的真 bug 都修了，全测试绿），但**业务价值要 4-6 周后才能验**：要看 promoted_log 累积频率、用户实际点击 ignore/promote 的次数。如果 4 周后用户从来没点过这两个按钮，说明趋势层没在用户的工作流里产生差异，可考虑收敛回静态。

## 归档

详细记录已存档：本文件
代码 diff：`src/literature_feed/trend/{trending_weights,scorer,__init__}.py` + `scheduler/{daily_runner,__main__}.py` + `paths.py` + `ui/feed_panel.py`
测试：`tests/test_trending_weights.py`（28 cases）
