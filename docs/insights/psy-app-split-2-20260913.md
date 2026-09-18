# psy app 拆分第二批（d913a-43，2026-09-13）

任务：按第一批（d7bc1f4，隐私门→src/ui/pages/privacy_gate.py）同模式，将 app.py 启动副作用块函数化搬出，行为零变更。

## 搬出内容

本次搬出**两块**（任务要求至少一块）：

| 块 | 原位置 | 去向 | session_state 键（保持原样） |
|---|---|---|---|
| 启动时自动清理（文献缓存 7 天过期） | app.py:321-332 | `src/ui/startup_checks.py::run_once_startup_cleanup` | `has_auto_cleaned` |
| 启动时一键环境检查（v5.8 find_spec 自检 + toast） | app.py:334-345 | `src/ui/startup_checks.py::run_once_env_check` | `startup_check_done` / `env_status` |

- 函数体与原内联块**逐字等价**（含注释、异常吞咽、env_status=None 白屏保护语义）；仅把 `cleanup_literature_cache` / `run_startup_check` / `render_env_status_toasts` 改为函数内懒导入（三者中 memory_manager 本就被 app.py 顶层导入，行为无差）。
- app.py 行数 **2698 → 2686**（diff +6/-18）；调用点保持原顺序（隐私门之后、重依赖预热之前）。
- `src/utils/env_check` 顶层导入行未删（render_env_health_banner 仍在用，不动=最小 diff）。

## 测试结果（junitxml 精确计数）

全量 `python -m pytest -q --tb=no --junitxml`：**2663 = passed 2606 + failed 10 + errors 13 + skipped 34**（631s）。

**基线对照证明非绿项与本班零相关**：`git stash` 还原 app.py 至 HEAD 后单跑两个浏览器文件（test_playwright_golden_research_flow.py + test_e2e_v52_paths.py，恰为全部 23 个非绿项所在）＝**同样 13 errors + 10 failures**（45 用例逐一对应），stash pop 恢复。即全部非绿为**先于本班存在的浏览器 e2e 环境依赖**（需 live streamlit server:8501 / 浏览器），与搬出改动无关；其余 2640 用例（2606 passed + 34 skipped）与本班改动后全绿/跳过。

旁证：两轮全量跑的终端汇总行均被截断（atexit 钩子疑似 os._exit），junitxml 是唯一可靠计数来源——已记入遗留。

## 验收

- 目标块已搬出、主文件行数下降（-12）、行为零变更 ✓（逐字等价 + 基线对照）。
- 全量测试：2606 passed，23 个非绿项经基线对照证明 pre-existing 环境性，零新增失败 ✓。
- 任务禁令遵守：不 commit/push（改动留工作树）、不改业务语义、无接口变更。

## 遗留问题

- app.py 剩余可拆块：重依赖预热线程块（_preload_heavy_deps，约 350-371 行）、_autosave_current_workspace 等，留第三批。
- pytest 终端汇总行被吞（疑浏览器 e2e conftest 的 atexit 硬退出）——影响所有「看汇总行」的流程，建议日间定位（junitxml 可绕过）。
- 23 个浏览器 e2e 非绿需日间在带浏览器/server 的环境复跑定绿，非本班能闭环。
