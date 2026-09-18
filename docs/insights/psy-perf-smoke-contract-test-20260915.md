# perf_smoke --json 契约回归测试补记（d914-73，2026-09-15）

- 任务 id：d914-73-psy-perfsmoke-contract-test
- 新增文件：`tests/test_perf_smoke_report.py`（5 个 test_ 函数；唯一生产侧 delta=0——`git diff --stat -- scripts/perf_smoke.py` 为空）
- 运行命令：`.venv\Scripts\python.exe -m pytest tests/test_perf_smoke_report.py -q -p no:cacheprovider` → **5 passed**（0.20s，退出码 0）

## 新增测试函数与覆盖契约

| 函数 | 覆盖契约 |
|---|---|
| `test_a_json_output_contract` | `--json` 输出可 json.loads；顶层键恰为 {timestamp, run_type, thresholds, results, summary}；全 OK 时 summary=={"warnings":0,"failures":0}；results 键=7 基准 |
| `test_b_no_history_writes_nothing` | `--no-history` 下 HISTORY_FILE 不落盘 |
| `test_c_time_it_warn_and_ok` | `_time_it` 阈值三态：200ms>100ms→WARN；50ms≤100ms→OK（perf_counter 用迭代器桩，无 sleep） |
| `test_d_time_it_failure_returns_none_and_marks_fail` | fn 抛 RuntimeError("boom") → status=FAIL、error=boom、返回 None |
| `test_e_failures_raise_system_exit` | 有 FAIL 时 main() 抛 SystemExit code=1 且不写历史 |

## 基线与收尾 passed 数

- 基线（本会话 2026-09-14 23:32 全量实测，d913d-24）：**2606 passed / 34 skipped / 25 failed / 13 errors**（系统 python 口径，含 sklearn 漂移族与 Playwright ERROR）
- 收尾（本会话 2026-09-15 03:5x 全量实测，`.venv` 解释器）：**2600 passed / 60 skipped / 0 failed**（2:53）
- 口径注记：两种解释器下 Playwright 依赖缺失分别表现为 ERROR（系统 python）与 SKIP（venv），故绝对数不同；venv 口径与 README「2586/60 量级」一致且 0 failed。新增 5 用例已计入 2600。
- 脚本本体 `scripts/perf_smoke.py` 未被修改（git diff --stat 空）；测试全程 stub 7 个基准函数，未写 `data/perf_history.jsonl`（HISTORY_FILE 均指向 tmp）。

## 遗留问题

- 无。perf_smoke 契约已固定：顶层结构、三态判定、FAIL 退出码、no-history 语义均有回归保护。
