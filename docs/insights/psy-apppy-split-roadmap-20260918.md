# psy app.py 页面控制器拆分路线图（s918-06 只读前置）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读路线图，未改 app.py（git diff --stat 为空 ✓）。
>
> ⚠️ **2026-09-23 已由 s923-14 按 s922-18／s922-23／s922-103 三单实测回改。本文件下方「实测」与「候选控制器清单」两张表是 2026-09-19 当时盘态的留痕，不逐格改写；一切排单请以文末「## 修订记录 20260923」与其后的「实测校正表」为准。**

## 实测
- `wc -l app.py` → **2670 行**。〔**已失效**，s923-14 于 2026-09-23 11:26 现取：工作树 **2405 行**（`M app.py` 他班在途）／`git show HEAD:app.py` **2433 行**。该基线与任一 git 版本都对不上——s922-23 实测链路为 2698→2515→2487，本档 2670 从写下起就不可复算。来源：s922-18／s922-23 出口 C／s923-14〕
- 已迁移样例：deliverable_center_panel.py（app.py:2652 接线，:2617-2660 区段）。〔片 1-3 已由 **s922-18** 迁走，见修订记录 R1〕

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

行区间总和 2595＋头部 75＝2670 ✓ 全覆盖。〔**该自证已失效**：区间是按 2670 旧版标的，s922-23 判「roadmap 的行区间从一开始就不是可复现锚点」；且片 5/片 6 实测各被高估 93 行／285 行。来源：s922-23 出口 C／s923-14〕

## 实测校正表（2026-09-23，s923-14 依 s922-18／s922-23／s922-103 回写；现盘 app.py 工作树 2405 行）

| # | 片区 | **现盘真实区间** | 真实行数 | 依赖 session_state | **分类修正** | 来源单 |
|---|---|---|---|---|---|---|
| 4 | `_autosave_current_workspace` | `app.py:169-188` | **20**（s922-23 报 22＝含 :189 空行＋:190 注释的取数差） | 键面 **2 个**：`_autosave_last_error` 写于 :187；`_workspace_last_saved` 的**读侧在片 5 的 :325** ⇒ 跨片读写 | **不是纯函数**：有 `st.session_state` 写、依赖 app.py 模块级 `logger`。本档原「可抽」备注偏乐观 | s922-23 |
| 5 | ~~PAGE 心理学研究工具 383-943~~ → 实为**模块级侧边栏引导块** `with st.sidebar:` | `app.py:196-663` | **468**（现盘逐位复算：区间 468 行、`st.session_state` 出现 **65 处**，与 s922-23 完全一致） | 去重键 **26**（s922-23 口径；本档原记「10 键」**低估 2.5 倍**。s923-14 用更宽正则现测 30，多出的 4 项是 `_autosave_last_error`／`_pending_app_mode`／`_workspace_migration_info`／`questionnaire_design`，其中 `get`/`pop` 系正则伪键两口径都有） | **根本不是函数**，是运行期路由与会话引导本体：块内裸导出 `mode` 变量（:293 radio／:305 兜底），被下游 **7 个页面分支**（:738/:1549/:1556/:2314/:2345/:2353/:2397）直读；块内含 `st.download_button`（:355，要过导出门禁换桶）与 `st.stop()`（:481）。搬它＝改初始化顺序，风险面与「纯函数原名 re-export」完全不同 | s922-23 |
| 6 | PAGE 数据分析 —— **上传段**真实边界 | `app.py:738-957`（**220 行**，非本档原标的 944-1748／805 行；也非任务书旧锚 :921-1140，该锚已连续漂移 −183 行） | 220；`st.file_uploader` 在 **:772**，`_autosave_current_workspace(force=True)` 调用点在 **:835**（落在任何覆盖 :772 的连续块内） | 段内 `st.session_state` 26 处／去重键 9。⚠️ `_analysis_cache_key` **不在上传段**，实测在 **:1119/:1128**（属片 6b 渲染段）⇒ 本档原「3 键：_analysis_cache_key/_recipe_prefill_text/_upload_error」对上传段的归键是错的 | **不是「可并行的低风险续批」**：与片 4 存在硬先后依赖（见撞车风险位第 4 条）。另：AST 探针已证该块裸全局（`df`/`meta`/`inspector`/`n_rows`）真耦合 **0**，但干净性依赖 app.py 后续行的「读前自赋值」隐式约束（:991/:1080/:1186），重排即碎 | s922-103 |

复算命令（只读）：

```bash
wc -l app.py                                   # 2405（工作树，M app.py 属他班在途）
git show HEAD:app.py | wc -l                   # 2433
# 片 4 区间／键：python -c "import ast;t=ast.parse(open('app.py',encoding='utf-8').read());
#   [print(n.name,n.lineno,n.end_lineno) for n in t.body if isinstance(n,ast.FunctionDef)]"
# 片 5：sed -n '196p;663p' app.py ＋ grep -c 'st\.session_state' <(sed -n '196,663p' app.py)   # 65
# 片 6 上传段：grep -n '📈 数据分析\|st.file_uploader\|_analysis_cache_key\|_autosave_current_workspace(force' app.py
#   → 738 / 772 / 1119,1128 / 835
```

## 撞车风险位
- 片 5/6/7 的 session_state 键与 _autosave_current_workspace（片 4）共享 `_workspace_last_saved`——抽取时该键读写需集中在一处。
- 片 7 混装问卷+侧栏：拆分顺序必须先拆侧栏（无状态依赖）再拆问卷，避免中间态双写。
- 片 9 已迁移面板与片 6 数据分析共享 `analysis_output`——交付中心依赖分析产物，拆分时保持只读引用。
4. **【新增·s922-103 出口 A】片 4 是片 6a 的硬前置，两者不可并行。** `_autosave_current_workspace`（片 4，定义 `app.py:169`）的调用点 **:835 落在片 6 上传段 :738-957 内部**，而该段要达标（覆盖 :772 的 `st.file_uploader`）必然吞掉 :835。片 4 写的 `_autosave_last_error` 其读侧在 :325（片 5 引导块内）⇒ **先给 `_autosave_last_error`/`_workspace_last_saved` 定一个单一持有者（建议 `src/utils/autosave.py`，那里已有 `logger` 与 `trigger_autosave`），才谈得上片 6a**。本档原表把片 4 与片 6 并列成「可并行的低风险续批」是错的。

## 迁移顺序建议（每步 ≤400 行、可独立回退）

> ⚠️ **本节原排序已作废**，按 s922-18／s922-23 实测重写。原句「① 片 1-3（**纯函数**，零风险热身）」里只剩「片 1-3 已迁完」这部分还成立：s922-18 已把片 1-3 全部迁走，**app.py 里已不存在「第二批纯函数」**——现盘顶层 `def/class` 仅 2 处（`:21 class _DummyContext`、`:169 def _autosave_current_workspace`），片 4-7 全是模块级或有状态块。故「第二批纯函数＝片 4-5」这一排序前提不成立（s922-23 否证；注：**「第二批纯函数」这个字样本身在 s922-23 的派单前提里、不在本档原文里**，本档原文写的是「① 片 1-3（纯函数，零风险热身）」，s923-14 据实况只否证并改写了本档实际存在的那句，未虚构删除）。

新序（每步均可独立回退；规模一律现盘重取，勿沿用本档旧行号）：

1. **片 4（20 行）＋ 给 `_autosave_last_error`/`_workspace_last_saved` 定单一持有者** —— 与片 6a 并成一单做，别单独推进（s922-23 出口 A ＋ s922-103 出口 A 同判）。
2. **片 5（468 行）单列一单、换模板**：照 app.py 已有先例（`render_restore_prompt(st)`/`run_once_env_check()`/`ensure_active_project_on_first_visit()`/`render_onboarding_card()` 全是「同位置调用＋显式传 `st`＋保持初始化顺序」）改造成返回 `mode` 的函数，同步处理 :355 的 `st.download_button` 导出门禁换桶与 :481 的 `st.stop()` 语义。预算 ≥1 小时，验收判据取 `tests/test_e2e_ui.py` 的 AppTest 全脚本跑（唯一能抓住这条主路径漂移的现有测试）。
3. **片 6a 上传段（:738-957／220 行）走「回调注入」型**：签名 `render_analysis_upload_panel(session_state, *, autosave)`，app.py 把 `_autosave_current_workspace` 传下去——不搬片 4、不动初始化顺序，技术上今天即成立。回归面：`tests/test_upload_state.py` ＋ `tests/test_e2e_qimport_upload.py` 共 12 例（上传段唯一现有回归面）。
4. 片 7（问卷设计＋侧栏混装）先拆侧栏再拆问卷，避免中间态双写。
5. **阈值数字（40/25/150 等）一律按现场测算重设，不要沿用本档标注**——s922-18 的 2394、s922-23 的 1895、s922-103 的「净减 ≥150」三条已被分别证为出自失效锚点或不可安全达成。模板仍＝片 9 的 deliverable_center_panel 模式。

## 修订记录 20260923

| # | 修订处 | 依据（来源单） | 性质 |
|---|---|---|---|
| R0 | 「实测」节基线 2670 标注为失效，改挂现值 工作树 2405／HEAD 2433（2026-09-23 11:26 现取）。⚠️ **该现值是「HEAD＋他班未提交改动」的合并态**（现盘 `git diff --numstat app.py` = **+12/−40**，恰为 2433−2405；`app.py` 全程是本分区他班在途 ` M`，本班一字未动）⇒ 他班提交或回退后本数字会再变，**它不是不变量，引用前请现场 `wc -l app.py` 重取** | s922-23 出口 C ＋ s923-14 现场 `wc -l` | 基线回改 |
| R1 | 片 1-3 已迁移完毕，样例不再是「唯一已迁片」 | s922-18 | 状态回写 |
| R2 | 片 4 行区间 352-382／31 行 → **`app.py:169-188`／20 行**（s922-23 报 22 行，差 :189 空行＋:190 注释的取数口径），并去掉「纯函数」暗示；键面 2 个（`_autosave_last_error` 写 :187／`_workspace_last_saved` 读侧 :325 跨片）——本档原键清单**是准的**，错的只是分类备注 | s922-23 | 三处标注之一 |
| R3 | 片 5 由「PAGE 心理学研究工具 383-943／561 行／10 键」→ **「模块级侧边栏引导块 `app.py:196-663`／468 行／`st.session_state` 65 处／去重键 26」**，并登记它**不是函数**、裸导出 `mode` 被下游 7 分支直读、含 :355 导出按钮与 :481 `st.stop()`；原「10 键」低估 2.5 倍 | s922-23 | 三处标注之二 |
| R4 | **删除「第二批纯函数」排序建议**（实为改写本档实际存在的「① 片 1-3（纯函数，零风险热身）」句并作废整节旧序）；登记前提否证：该字样在本档原文里并不存在，出自 s922-23 派单前提 | s922-23 | 三处标注之三 |
| R5 | 片 6 上传段真实边界改 **`:738-957`／220 行**（原 944-1748／805 行），并登记 `_analysis_cache_key` 不在该段（实测 :1119/:1128）⇒ 本档原归键错误；旧任务书锚 :921-1140 已漂移 −183 行 | s922-103 | 边界回写 |
| R6 | 撞车风险位新增第 4 条：**片 4 是片 6a 硬前置**（:835 调用点被任何覆盖 :772 的连续块吞掉） | s922-103 出口 A（与 s922-23 出口 A 同判） | 依赖登记 |
| R7 | 迁移顺序按新事实重排为 5 步，并规定阈值数字一律现场重设 | s922-18／s922-23／s922-103 | 排序回写 |

> 未改动的部分：上方两张 2026-09-19 原表逐格保留为当时盘态留痕（含已失效的区间与「10 键」低估），只加校正、不追改历史。本档本次修订**只动这一个文件**，`app.py` 零改动。
