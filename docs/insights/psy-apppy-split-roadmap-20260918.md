# psy app.py 页面控制器拆分路线图（s918-06 只读前置）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读路线图，未改 app.py（git diff --stat 为空 ✓）。

## 实测
- `wc -l app.py` → **2670 行**。
- 已迁移样例：deliverable_center_panel.py（app.py:2652 接线，:2617-2660 区段）。

## 候选控制器清单（函数名/行区间/session_state 键依赖；每片 ≤400 行）

| # | 片区 | 行区间 | 行数 | 依赖 session_state 键（实测） | 备注 |
|---|---|---|---|---|---|
| 0 | 模块头+imports | 1-75 | 75 | — | 保留于 app.py |
| 1 | _get_onboarding_text | 76-152 | 77 | 0 | 可直接抽 utils |
| 2 | _build_homework_package | 153-221 | 69 | 0 | 可抽（作业包文本生成） |
| 3 | _generate_method_description | 222-351 | 130 | 0 | 可抽 |
| 4 | _autosave_current_workspace | 352-382 | 31 | _autosave_last_error、_workspace_last_saved | 接 autosave_bg |
| 5 | PAGE 心理学研究工具（主工具页） | 383-943 | 561 | 10 键：_clear_session_confirm/_last_logged_mode/_pending_undergrad_mode/_session_reset_notice/_workspace_import_handled/_workspace_last_saved/_ws_export_json/_ws_export_ts 等 | 超 400 → 再切「工作台头/导出/模式切换」两片 |
| 6 | PAGE 数据分析 | 944-1748 | 805 | 3 键：_analysis_cache_key/_recipe_prefill_text/_upload_error | **最大片，超 400×2** → 先切「上传与缓存」再切「分析渲染」 |
| 7 | PAGE 问卷设计 + 设置侧栏 | 1749-2580 | 832 | 1 键：q_request_input | **混装**：问卷设计 vs 语言/LLM 状态/使用指南侧栏（:1771-1800）应拆两个控制器 |
| 8 | PAGE 文献与选题 | 2581-2616 | 36 | 0 | 小片直迁 |
| 9 | PAGE 交付包导出中心 | 2617-2660 | 44 | analysis_output | **已迁移样例**（deliverable_center_panel，:2652 接线）——后续片的模板 |
| 10 | PAGE 研究模板中心 | 2661-2670 | 10 | 0 | 小片直迁 |

行区间总和 2595＋头部 75＝2670 ✓ 全覆盖。

## 撞车风险位
- 片 5/6/7 的 session_state 键与 _autosave_current_workspace（片 4）共享 `_workspace_last_saved`——抽取时该键读写需集中在一处。
- 片 7 混装问卷+侧栏：拆分顺序必须先拆侧栏（无状态依赖）再拆问卷，避免中间态双写。
- 片 9 已迁移面板与片 6 数据分析共享 `analysis_output`——交付中心依赖分析产物，拆分时保持只读引用。

## 迁移顺序建议（每步 ≤400 行、可独立回退）
① 片 1-3（纯函数，零风险热身）→ ② 片 8+10（小片）→ ③ 片 7 拆侧栏 → ④ 片 7 拆问卷 → ⑤ 片 5 切两片 → ⑥ 片 6 切三片。模板＝片 9 的 deliverable_center_panel 模式。
