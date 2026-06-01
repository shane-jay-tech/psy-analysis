# N10 — 苏格拉底基准漂移观测

**日期**：2026-05-29
**模式**：Opus 单方实现 + 自审（小规模 CLI 工具，无需多模型协作）

## 现状

- `tests/test_socratic_quality.py --run-benchmark` 已存在，对 30 案例跑真实 LLM，输出 `tests/fixtures/_benchmark_reports/benchmark_<TS>.json`
- `scripts/evaluate_socratic_benchmark.py` 已有手动两参数对比 (`--baseline X --candidate Y`)
- **缺口**：每次跑完没人归档 / 没人对比上一次 / 漂移不可视

## 改动

### `scripts/evaluate_socratic_benchmark.py`（重写）
- 保留原 `--baseline / --candidate` 手动模式（兼容）
- 新增 `--track-drift` 模式：
  1. 找 `tests/fixtures/_benchmark_reports/` 里 mtime 最新的 `benchmark_*.json`
  2. 复制到 `data/benchmark_history/socratic_benchmark_<UTC_ISO>.json`（按 UTC 时间戳命名，字典序＝时间序）
  3. 找 history 里上一次归档 → 调用 `_compare_reports()` → 控制台打 + 写 markdown 到 `data/benchmark_history/_latest_drift.md`
  4. 首次跑（无 previous）只归档 + 写「仅记录起点」md

### `tests/test_socratic_drift_tracker.py`（新增）
10 个离线单测，覆盖 `_latest_report` / `_archive_to_history` / `_compare_reports`（improvement/regression/same 三档）/ `_track_drift`（无报告 / 首次 / 第二次对比）。
不调真实 LLM，全程 mock 报告 JSON。

## 不做 CI 集成

任务原描述提到「(3) 可选 CI 集成（GitHub Actions / 本地 cron）」。当前用户没 GitHub Actions 配置（这是私人单人项目，且仓库不在 GitHub）。Windows Task Scheduler 已被 v4.7 Phase 4e 占用了 `daily_runner`，再叠一份基准跑会挤压 LLM 月预算（基准跑一次 30 个 case，DeepSeek 估算 0.05 USD/次，每天跑会吃满月预算的 15%）。

**留给用户手动调起**：当 prompt 改完想观察影响时，
```bash
$env:BENCHMARK_LLM_API_KEY = '<key>'
pytest tests/test_socratic_quality.py --run-benchmark
python scripts/evaluate_socratic_benchmark.py --track-drift
# 看 data/benchmark_history/_latest_drift.md
```

## 自审 ≥3

1. **启发式覆盖率太粗**：`_has_dimension_keyword` 只查关键字，"概念明确"和"概念模糊"都算命中"概念"维度。
   - 缓解：md 报告本身写了"启发式覆盖率仅供粗略对比，最终质量需人工标注"，不会误导用户。
   - 长期：等 v5 真有人工标注数据后切到 `manual_score` 字段对比。

2. **改 prompt 后第一次跑会被记成"上一次归档"，下次跑漂移就以新 prompt 为基线**：用户可能误以为"我刚改的 prompt 反而是基准"。
   - 缓解：md 写明"上一次归档"路径，用户能看到时间戳，自己判断哪一份是 anchor。
   - 严格做法是给改 prompt 时打 git tag，让基线锚定 commit hash —— 但本项目还没强制 git，留 v4.8 再说。

3. **`data/benchmark_history/` 永远长**：每次跑都新加一份 ~50KB JSON，一年 365 份 = ~18MB。
   - 缓解：不大，且对漂移分析有价值。如果未来真嫌烦可加 `--prune-older-than 90d`。

## 风险 ≥2

1. **Windows mtime 精度只到秒**：连续两次跑（< 1s）`_archive_to_history` 用 UTC 秒级时间戳，会撞名覆盖 → 后跑的盖掉前一次。
   - 缓解：测试中已加 `time.sleep(1.1)` 验证避免冲突；实际场景两次基准跑间隔 ≥ 几分钟，不会撞。

2. **`_compare_reports` 假设 case_id 集合一致**：如果未来扩展 fixture 加新 case，老归档对比新归档时新 case 没基线 → 自动跳过（current behavior）。但这意味着扩 fixture 后第一份漂移报告会"假性持平"。
   - 缓解：扩 fixture 时主动 reset history 一次。这点写进 md 给用户提醒？暂没写，留观察。

## 反方观点

DeepSeek 如果在场可能会主张：「启发式覆盖率没意义，应该上 LLM-as-judge 或者人工 100% 标注，否则报告本身在制造假信号」。

回应：成立。但当前阶段：
- LLM-as-judge 又一次燃费 + 引入新模型偏差（裁判 LLM 自己也漂移）
- 人工 100% 标注：30 案例 × 反问质量评分 ≈ 半小时/次，用户单人维护，频率会塌
- 启发式 + 人类 manual_score 字段共存的"半自动"是可承受的折中

## 置信度

**高**。10 个单测 + 1 个 CLI smoke 都过。归档 + 对比逻辑覆盖到了所有分支（无报告 / 首次 / 第二次对比 / 报告损坏）。

会改变结论的证据：
- 用户实际跑一次后觉得 md 报告太薄 / 太啰嗦
- LLM 模型升级后启发式 keyword 失效（如 prompt 切英文输出）
- 多人协作场景下需要 git ref 锚定基线（当前是单人，不影响）

## 落地

- ✅ `scripts/evaluate_socratic_benchmark.py` 重写完毕
- ✅ `tests/test_socratic_drift_tracker.py` 10 测全绿
- ✅ `data/benchmark_history/` 由脚本首次跑时自动 mkdir
- ❌ 不做 CI（理由见上）
- 📝 用户手动跑法已写在脚本顶部 docstring
