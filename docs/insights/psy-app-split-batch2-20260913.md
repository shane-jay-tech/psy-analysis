# psy app 拆分第二批·行为等价断言补齐（d913b-48，2026-09-14）

任务：启动清理块与环境检查块函数化＋≥2 条行为等价断言＋全量 ≥2588 passed。

**同源说明**：本单与 d913a-43（本班 00:38 完成）互为孪生——两块函数化（src/ui/startup_checks.py、app.py 调用点替换、行为零变更+stash 基线对照）已由 a-43 落地。b-48 的增量＝**行为等价断言 ≥2 条**（a-43 任务书未要求），本班补齐。

## 增量交付

`tests/test_startup_checks.py`（4 条，全绿）：
1. `test_env_check_runs_once_then_gated`：调用序列断言——首跑 [check, toast(result)] 各一次、重跑零调用（startup_check_done 门等价于原内联块）。
2. `test_env_check_swallows_failure_and_keeps_none`：自检异常 → env_status=None 不外抛（v5.8 白屏保护语义等价）。
3. `test_cleanup_runs_once_then_gated`：清理首跑一次（7 天口径）、重跑零调用（has_auto_cleaned 门）。
4. `test_cleanup_swallows_exception`：清理异常静默（原 `except: pass` 等价）。

测试用 _FakeSessionState（in/属性双语义）对齐 streamlit session_state 行为；env_check/memory_manager 依赖全 monkeypatch。

## ⚠️ 全量口径与环境漂移披露

- 本班 a-43 时点（01:40）全量 junit：2663 = 2606 passed + 34 skipped + 23 非绿（全部在两个浏览器 e2e 文件，stash 基线证明先于本班存在）。
- 本单复跑（03:2x，排除两个浏览器文件）：2622 = **2573 passed** + 34 skipped + **15 failed**——新增失败集中在 test_golden_stats_v2 / test_reliability_extended / test_robustness / test_validity（统计 golden 域）。
- **根因＝环境依赖漂移，非代码回归**：`factor_analyzer 0.5.1` 调用 sklearn 的 `check_array(force_all_finite=...)`，该参数 sklearn 1.8 起移除，而环境现为 **sklearn 1.9.1**（a-43 时点同机同令通过——01:40 后 sklearn 被升级至 1.9.1，非本会话操作）。
- 基线复证：stash 掉本班全部 psy 改动后单跑同一用例**同样失败** → 与拆分/断言零相关。

## 验收对照

- ≥2 条行为等价断言 ✓（4 条）；原调用点已替换 ✓（a-43）；git diff 纯搬移 ✓（a-43 git diff -w 核对）。
- 全量 ≥2588：当前环境 2573 passed——**未达标的原因是 15 个环境漂移失败**（sklearn 1.9.1×factor_analyzer 0.5.1），本班代码自身 4 条新断言全绿、零新增失败有基线对照背书。
- 未 commit、未 push、零业务语义变更。

## 遗留问题（晨报必带）

1. **环境漂移修复（日间，需授权）**：`pip install "factor_analyzer>=0.5.3"`（兼容新 sklearn）或 `pip install "scikit-learn<1.8"` 二选一；修复后 golden 域 15 条应回绿、全量 passed 回 2588+。
2. sklearn 为何在 01:40–03:20 之间被升级（并行会话/计划任务/用户手动）需日间查——若夜间任务有自动 pip 行为属流程违规。
3. 浏览器 e2e 两文件 23 条非绿维持 a-43 结论（环境依赖，日间带浏览器复跑）。
