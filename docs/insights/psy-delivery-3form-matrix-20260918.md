# psy 交付三形态入口现状矩阵（s918-05 / KNOWN_ISSUES :104 前置输入）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读矩阵，供日间产品裁决。

## 锚点复核
- app.py:2652-2653 `render_deliverable_center_panel(st.session_state)` ✓
- src/output/zip_exporter.py ✓、scripts/release_gate.py ✓
- `python scripts/release_gate.py --help` 实测输出附卷（文末）——**发现：该脚本无 --help 语义，任何参数都直接跑 fast 自检（实测 2m20s，2830 passed / 1 failed [test_heavy_preload] / 60 skipped）**。

## 三形态 × 三属性矩阵（每格 file:line）

| 形态 | 入口函数 | 门禁 | 命名 |
|---|---|---|---|
| **草稿** | src/utils/autosave_bg.py:68 `_worker_loop`（触发：:4/:10 `trigger_autosave` 主线程引用级捕获→后台全量序列化） | 无质量门禁；自动保存（超阈值仅告警 :85-89，不阻断） | session 内快照，无用户可见命名规范 |
| **作业包** | src/output/zip_exporter.py:27 `build_deliverable_zip(bundle, mode="standard")`（paper_md :189 / ai_disclosure :207 / privacy_precheck :246 / reproducibility_manifest :259） | 无独立门禁（打包函数本身不校验质量）；bundle 由调用方构造 | mode 参数区分（standard/…），zip 内部结构由各 _generate_* 决定 |
| **正式交付** | app.py:2652-2653 `render_deliverable_center_panel`（UI 面板）；scripts/release_gate.py:48/60/87/110/122 五检查（unit_tests/zip_export/word_export/golden_stats/template_data） | release_gate 五检查全过才可交付（硬门禁） | 由 gate 校验模板与产物一致性（check_template_data :122） |

## 语义分叉点（供裁决）
1. **草稿无门禁、作业包无门禁、正式交付硬门禁**——三形态门禁强度不连续；草稿→作业包之间无「最低质量提示」。
2. **作业包与正式交付共用 build_deliverable_zip**，但作业包路径不跑 release_gate——同名 zip 可能出自未过门内容。
3. release_gate CLI 无 --help/参数语义，误触即 2 分 20 秒全量自检；且 incidental 发现 fast 自检当前 **1 failed（tests/test_heavy_preload.py::test_the_warmup_body_never_runs_in_this_process）**——正式交付门（check_unit_tests）若含该用例则当前**不可过门**，需日间确认。

## 附：release_gate.py --help 实测输出（截选）
```
==================================================
  Psy-Analysis 质量自检 [fast]
==================================================
  [单元+集成测试] FAIL (exit 1): …how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_heavy_preload.py::test_the_warmup_body_never_runs_in_this_process
===== 1 failed, 2830 passed, 60 skipped, 43 warnings in 140.99s (0:02:20) =====
```
