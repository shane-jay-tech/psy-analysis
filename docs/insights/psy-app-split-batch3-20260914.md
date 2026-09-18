# psy app.py 第三批拆分（d914-23 / 20260913-181024-5993 后续，2026-09-14）

## 已拆

1. **重依赖预热块**：app.py 原 :336-352（`_preload_heavy_deps` + `_heavy_preload_started` session 门 + daemon 线程启动）→ `src/ui/heavy_preload.py`（`preload_heavy_deps` + `start_heavy_preload_once`）。导入时机未变（全部 import 仍在函数体内执行，时机=线程启动时=原语义）；session 键 `_heavy_preload_started` 保持。app.py 2670 → 2667 行（净 -3，本块 -17/+14）。
2. **autosave 收敛确认**：`_autosave_current_workspace` 已是单点函数（app.py:352），调用点仅 2 处（:1015/:1319）——按规格「已收敛则只补注释与调用点对照」处理，docstring 补调用点映射，未移动。

## 验证（junitxml 计数，汇总行被吞问题的可靠替代）

`python -m pytest tests -q --tb=no --ignore=<两个浏览器文件> --junitxml`：**2625 tests = 2591 passed + 15 failed + 34 skipped - 15 failures 全部为 test_golden_stats_v2 域 sklearn 1.9.1×factor_analyzer 0.5.1 环境漂移（d913b-48 基线同口径，非本批引入）**。0 errors。`python -c ast.parse` 语法过。

## 遗留问题

- sklearn 漂移与浏览器 e2e 两域非绿为环境/依赖项（d913b-48 已立案），非本批回归。
- app.py 侧栏快捷模型选择器块（~15 行）与剩余 UI 编排仍可继续批拆，留第四批。
