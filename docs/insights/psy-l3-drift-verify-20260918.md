# psy #L3 漂移观测真实状态核验＋KNOWN_ISSUES 订正稿（s918-02）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读核验，KNOWN_ISSUES.md 未改（订正稿留日间放行）。

## 实测
- `.venv/Scripts/python.exe -m pytest tests/test_socratic_drift_tracker.py -q` → **10 skipped in 0.05s**（0 passed / 0 failed）——套件存在且可收集，但全部用例带离线跳过门（无 LLM key/标记即 skip），**并非全 passed**。
- `data/benchmark_history/` 产物盘点：`_latest_drift.md`、`_relay_calls.jsonl`、`benchmark_backfill_draft.json`、`socratic_benchmark_20260909T192139Z.json`——**历史样本仅 9/9 一批（距今 10 天）**，无趋势曲线。

## 真实状态判定
#L3 既非「待开」也非「已闭环」：测试与数据目录已建（基建存在），但①CI 未接（:63 计划未落地）②样本断档 10 天③单测离线全跳——真实状态＝**「基建已建、观测未连续」**。

## KNOWN_ISSUES.md 订正稿（:60-63 与 :93，供日间放行）
`:60-63` 状态行订正为：
```
- **现状**：单测 10 例离线全跳（pytest tests/test_socratic_drift_tracker.py，2026-09-19 实测）；历史目录已建但仅 2026-09-09 一批样本，无趋势曲线；CI 未接。
- **计划**：接 CI 跑 `scripts/evaluate_socratic_benchmark.py`（或本地定时）＋记录趋势到 `D:\code\psy-analysis\data\benchmark_history\`；样本 ≥3 批后再评漂移。
```
`:93` 看板行订正为：
```
| 🟡 中 | #L3 N10 评分趋势观测 | v4.7 | 基建已建、观测未连续（旧：待开） |
```

## 遗留问题
- 单测的离线跳过门设计（是否应有无 key 的纯逻辑用例）待日间裁决。
- CI/定时接入与样本补跑（≥3 批）为日间项。
