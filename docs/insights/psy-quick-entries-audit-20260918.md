# quick_entries 快捷分析入口审计（只读，s918-27 附表）

生成：2026-09-19 00:4x（规划批次标 20260918）｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
配套测试：`tests/test_quick_entries_min.py`（6 passed）。本文件**只读盘产出**，`src/` 零改动。

## 一、总体结构

| 项 | 实测 | 复现命令 |
|---|---|---|
| 文件行数 | **727** | `wc -l src/ui/quick_entries.py` |
| 顶层函数 | **7 个**（无嵌套函数、无类） | AST 扫描，见下表 |
| `st.session_state.` 引用 | **21 处** | `grep -c "st.session_state\." src/ui/quick_entries.py` |
| `st.rerun()` / `st.stop()` | **5 / 0** | `grep -c "st.rerun()" …` |
| `st.form` / `form_submit_button` 合计 | **20 处** | `grep -c "st.form" src/ui/quick_entries.py` |
| `st.expander` | 4 处 | 同上换关键字 |
| 静默吞异常 `except Exception` | **2 处**（L608、L721） | `grep -n "except Exception" src/ui/quick_entries.py` |
| 锚点 | `:101` 原文 `def render_quick_entry_homepage(df: Optional[pd.DataFrame] = None):` 逐字命中；`_run_quick_analysis` 实测在 **:663**（任务书写 :663 ✓） | `sed -n '101p;663p' src/ui/quick_entries.py` |

## 二、函数分支清单（渲染侧）

| 函数 | 行 | 长度 | 入参 | 渲染面（`st.*`） |
|---|---|---|---|---|
| `render_quick_entry_homepage` | 101 | 47 | `df` | title/caption/divider/subheader/columns/container/markdown/expander/button/success/info ＋ `rerun`；骨架：`if cur_df is not None`(L108) → `for _ in range(rows_needed)`(L122) → `with st.expander("🔧 更多分析方法（28种完整列表）")`(L146) |
| `_render_full_method_list` | 150 | 39 | — | columns/markdown/button ＋ `rerun` |
| `render_quick_entry_detail` | 191 | 116 | — | title/columns/divider/markdown/caption/info/warning/**form**/selectbox/radio/multiselect/button ＋ `rerun` |
| `_render_reliability_form` | 309 | 115 | `df, numeric_cols, cat_cols` | form/number_input/multiselect/selectbox/text_input/error/caption/expander/button |
| `_render_validity_form` | 426 | 90 | `df, numeric_cols, cat_cols` | form/radio/number_input/multiselect/selectbox/text_input/error/caption/expander/button |
| `_render_ai_item_review_form` | 518 | 143 | `df, numeric_cols, cat_cols` | text_area/multiselect/radio/text_input/columns/divider/error/info/success/caption/expander/markdown |
| `_run_quick_analysis` | 663 | 65 | `df, test_type, dv, iv, dv_list, **plan_kwargs` | 仅 `spinner` ＋ `rerun`（**唯一非渲染逻辑单元**） |

## 三、`_run_quick_analysis` 的 6 个调用点（执行侧分支）

| 调用行 | 触发条件 | 传参 | 备注 |
|---|---|---|---|
| L273 | `if submitted and dv and iv` | `(df, test_method, dv, iv)` | 有变量非空守卫 |
| L293 | `if submitted and len(corr_vars) >= 2` | `(df, test_method, dv_list=corr_vars)` | 相关性：≥2 变量守卫 |
| **L297** | `else` 分支（**无守卫**） | `(df, entry["default_test"])` | 从「28 种完整列表」进入的方法**不带任何 dv/iv** 直接执行 ⇒ `dep_vars=[]` |
| L423 | 信度表单提交（`_render_reliability_form` 末段，该函数 L309-423） | `(df, …, dv_list=…)` | 相关/信度类 |
| L515 | 效度表单提交（`_render_validity_form` 末段，该函数 L426-515） | `(df, …, dv_list=…, iv=…)` | 效度类 |
| **L658** | AI 条目评审表单 | `(df, "ai_item_review", dv_list=dep_vars, **plan_kwargs)` | 外层 `with llm_status("正在调用 4 位 AI 专家评分", timeout_hint=60)` ⇒ **唯一花钱/联网的入口** |

## 四、审计发现（未修，供日间拍板）

1. **`_run_quick_analysis` 内联函数级 import 四个重模块**：`AnalysisPlan`(intent_resolver)、`run_analysis`(analysis.runner)、
   `build_apa7_report`(output.formatter)、`archive_analysis`(utils.archive_manager)。好处是页模块导入轻；代价是**任何一条路径都要等真跑到才暴露 import 错误**，
   且给「打桩隔离」留了口子（本单测试正是靠 patch 模块属性把归档挡在真实磁盘之外）。
2. **归档失败静默**（L721 `except Exception: pass`）：APA7 报告与归档写盘出错时**用户零提示**，
   分析结果照常显示 ⇒ 「我以为存了」。已钉为 `test_archiving_failure_is_swallowed_silently`（现状不抛）。
   建议至少 `st.warning` 一行——属行为变更，本单未动。
3. **KB 读取失败也静默**（L608 `except Exception: pass`）：`construct_kb.CONSTRUCTS` 取值异常时会走
   `st.info("ℹ️ KB 未命中（仅用用户定义）")`，把**代码异常伪装成业务未命中**，排查时会被误导。
4. **L297 无守卫直接执行**：完整列表进入的方法以 `dep_vars=[]` 调 `run_analysis`，
   是否必然产出可用结果未验（本单未跑该分支，避免对分析器下结论）。建议日间补一条契约：空 dv 应早退并提示选变量。
5. **`ai_item_review` 与本地统计共用同一执行函数**：联网/计费路径与纯本地路径之间**没有 dry-run 或确认闸**，
   表单点「提交」即调用 4 位 AI 专家评分。按成本纪律这类入口应有显式提示或二次确认——本单只在测试里刻意绕开。
6. 本文件此前 **tests 零命中**（现仅本单）；`grep -rln quick_entries tests/` 复现。

## 五、本单测试覆盖到哪一层

`tests/test_quick_entries_min.py` 6 例，全部只打 `_run_quick_analysis`（唯一非渲染单元），
用假 `st`（`spinner` 空上下文、`rerun` 以自定义异常终止、其余属性一访问即 `AssertionError` 防误触渲染）＋
合成 2 组 12 行数据（`分数`/`组别`）跑真 `run_analysis`，断言面：
`analysis_output` 键存在（9 个键）／`plan.test_type`／历史条目形状／`dv_list` 优先于 `dv`／
`quick_entry`＋`show_quick_detail` 在 rerun 前被清除／归档尝试 1 次／归档抛错被吞。
**数值只测存在性，不测显著性**（红线）。渲染侧 6 个函数**未测**——它们需要 AppTest 或 e2e，按 `s918-28` 同类路径处理。
