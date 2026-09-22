# psy #L2 论文双入口埋点方案设计稿（s922-127，2026-09-22，纯设计不落码）

> 班：`qoder-executor-20260922-0000-psy13`｜仓：`D:/code/psy-analysis`｜基线 HEAD `255042d`（含 s922-126 矩阵）
> 性质：**设计稿**。零生产码改动；未新增依赖；未跑任何 LLM；`logs/` 只读扫描。
> 「合并 / 降级 / 保留双入口」仍待用户拍板（`KNOWN_ISSUES.md:57`），本稿只兑现**保底动作**（`:58`「保留 → 至少加埋点」）。

---

## 0. 锚点复核（3 条，0 漂移）

| 任务书锚点 | 实测 | 结论 |
|---|---|---|
| `src/ui/paper_writing_ui.py:38` `def render_paper_writing_ui():` | 实测 **38** | ✅ |
| `src/ui/undergrad_wizard.py:3255` `# 步骤 7: 写入论文` | 实测 **3255** | ✅ |
| `KNOWN_ISSUES.md:56`「影响：`paper_writing_ui.py` (678 行独立 mode，2026-09-21 复测)…」 | 实测 **56**；且 `wc -l src/ui/paper_writing_ui.py` = **678** ⇒ 「678 行」这条**计数式前提本轮成立**（记录口径：`undergrad_wizard.py` 现值 3715 行） | ✅ |

---

## 1. 先证伪：双入口的真实拓扑不是「两条都调 PaperEngine」

`KNOWN_ISSUES.md:56` 原文：「两条最终都调 `PaperEngine` 生成论文，差别只是独立入口要重填一遍信息，wizard 入口已有数据」。**实测该句只覆盖一半**：

| 入口 | UI 层生成动作 | 实际后端 | 锚 |
|---|---|---|---|
| A 独立「📝 论文写作」 | `engine.generate_questions()` / `engine.generate_full_paper()` | **直接持有 `PaperEngine` 实例**，存 `st.session_state.paper_engine`（`:42`，重置 `:81`） | `paper_writing_ui.py:404`（按钮）→`:406`；`:453`（按钮）→`:456` |
| B wizard 第 7 步 **主路（默认）** | `method_text`/`result_text` **模板拼接**（从 `stat_info` 直接 f-string 出 t/F/r、效应量、CI） | **不调 `PaperEngine`、不调 LLM**；产物是屏上文本，靠人「复制到论文」（`:3471` caption、`:3476` success） | `undergrad_wizard.py:3373`（三 tab）→`:3440-3476`；持久化进 `wiz_data` 在 `:3479-3480` |
| B wizard 第 7 步 **可选支路** | `generate_paper_quick(req)` | `workflow_service` 内部**另建一个临时 `PaperEngine()`**（`workflow_service.py:79`）→ `engine.generate_full_paper()`（`:117`） | `undergrad_wizard.py:3483` 调 `_render_ai_paper_generation`（定义 `:1352`）→ 按钮 `:1364` → 调用 `:1378` |

⇒ 三个直接后果，全部影响埋点设计：

1. **入口 B 的主路是零 LLM 的模板直出**：只埋「AI 增强」按钮等于**只埋了少数派**，"使用率"读数会系统性偏向入口 A。判据：`:1356-1357` `if not is_llm_available(): return`——LLM 不可用时该 expander **整块不渲染**，主路照常出稿。
2. **两条路径不共享引擎实例**：A 用 session 里的长生命周期 `paper_engine`，B 的临时引擎在 `generate_paper_quick` 内建即弃 ⇒ **不能在 `PaperEngine` 里塞"入口来源"**，来源只能由调用侧（UI 层）作为参数传入事件。
3. **"是否用了 AI 版"是有状态可逆的**：`:1382-1385` 写入 `_ai_method_md`/`_ai_result_md`，`:1399` 「🔄 恢复使用模板版本」会 `pop` 掉 ⇒ 埋点必须记**动作**（采纳/回退），只记一次"生成"会把"生成后回退"读成"已采纳"。
4. 命名撞车（同族混淆，psy12 已警告的坑）：`src/ui/paper_writing_ui.py`（678 行 UI）≠ `src/paper_writer/paper_engine.py`（引擎，`class PaperEngine` @`:72`）≠ `src/ui/paper_preview_panel.py`（草稿导出，s922-126 的 C 入口）。本稿一律写全路径。

---

## 2. 复用证明：通道已存在，但**半数是死的**（完成标准 2）

任务书原样命令与其结果（**只有 1 行命中**——该命令设计不足以自证复用，留痕如下）：

```
$ rg -n 'def log_event|usage_hooks' src/utils/usage_logger.py src/utils/usage_hooks.py
src/utils/usage_logger.py:75:def log_event(event_type: str, **kwargs):
```
零命中的原因：`usage_hooks.py` 通篇不出现「usage_hooks」这个字串（它只在 `:3` 的 docstring 里自称「将 usage_logger 接入 app.py」）。加宽口径后才是真正的复用面：

```
$ rg -n 'def log_event|def log_error|def get_usage_summary|def get_error_summary|def set_enabled|def _log_dir|usage_logger|usage_hooks' src/utils/usage_logger.py src/utils/usage_hooks.py app.py
src/utils/usage_hooks.py:3:将 usage_logger 接入 app.py 的关键路径，记录 ≥12 类匿名化事件。
src/utils/usage_hooks.py:9:from src.utils.usage_logger import log_event, log_error
src/utils/usage_logger.py:7:    from src.utils.usage_logger import log_event, log_error, export_feedback_package
src/utils/usage_logger.py:29:def _log_dir() -> Path:
src/utils/usage_logger.py:64:def set_enabled(enabled: bool):
src/utils/usage_logger.py:75:def log_event(event_type: str, **kwargs):
src/utils/usage_logger.py:99:def log_error(error_type: str, **kwargs):
src/utils/usage_logger.py:123:def get_usage_summary(days: int = 7) -> dict:
src/utils/usage_logger.py:152:def get_error_summary(days: int = 7) -> dict:
app.py:54:from src.utils.usage_hooks import (
```

**复用契约（本稿不改一条，全部现成）**：

| 能力 | 锚 | 事实 |
|---|---|---|
| 写 | `usage_logger.py:75-96` | `log_event(event_type, **kwargs)` → 追加一行 JSON 到 `<LOG_DIR>/usage_events_YYYYMMDD.jsonl`；顶层固定键 `timestamp`（`isoformat(timespec="seconds")`，`:85`）＋`event`（`:86`），其余为 kwargs |
| 写（错误面） | `usage_logger.py:99-121` | `log_error(...)` → `error_events_YYYYMMDD.jsonl`，顶层键是 **`error` 而非 `event`**（`:111`） |
| 静默失败 | `usage_logger.py:95-96` | `except OSError: pass`——**写日志永不崩 UI，但也永不报警**；`_ensure_log_dir` 建目录失败时才经 `_alert_once`（`:41-46`）吱一声 |
| 目录解析 | `usage_logger.py:29-38` | 显式打桩 `_LOG_DIR` > 环境变量 `PSY_ANALYSIS_LOG_DIR` > `app_paths.LOG_DIR`（默认 **CWD 相对 `Path("logs")`**，`app_paths.py:27`） |
| 开关 | `usage_logger.py:64-72` | `set_enabled/is_enabled`，模块级 `_ENABLED = True`（`:25`） |
| 读（唯一的聚合器） | `usage_logger.py:123-150` | `get_usage_summary(days=7)` **只按 `entry["event"]` 分组计数**（`:140-141`），不读任何其它字段；`days` 实为**文件个数**（`:131 [-days:]`），日历上有空档时它报的 `period_days` 会小于真实跨度 |
| 导出面 | `usage_logger.py:181-215` | `export_feedback_package` 只写**聚合后的** `usage_summary.json`（`get_usage_summary(days=30)` @`:196`）＋`error_summary.json`＋环境诊断 ⇒ **payload 里的自定义字段不会进反馈包** |
| 测试隔离 | `tests/conftest.py:52` | `monkeypatch.setattr(usage_logger, "_LOG_DIR", tmp_path / "logs")` ⇒ 新埋点在测试里自动落 tmp，**不需要额外加开关**；`tests/test_privacy_archive_usage.py:194-222` 已把「开关关闭不写／`page_visit` 带不带 kwargs 都能记」钉住 |
| UI 层零直调 | `rg -n 'log_event|log_error' src/ui/` → **0 命中** | 现状所有 UI 事件都只经 `usage_hooks`，本稿维持这一层（**不在 UI 里直调 `log_event`**） |

**13 个 hook 的接线实况**（脚本：`src/**/*.py + app.py` 逐 hook 计调用点，排除 `def` 与 import 块）：

| hook | 定义 | 生产调用点 | 状态 |
|---|---|---|---|
| `on_page_visit` | `usage_hooks.py:12` | `app.py:310` | ✅ |
| `on_data_upload` | `:32` | `app.py:834` | ✅ |
| `on_analysis_execute` | `:42` | `usage_hooks.py:91`（`AnalysisTimer.__exit__`），使用点 `app.py:1125` | ✅ 间接 |
| `on_consistency_check` | `:52` | **0** | 💀 |
| `on_privacy_precheck` | `:57` | `app.py:2371` | ✅ |
| **`on_export`** | **`:62`** | **0** | 💀 **本稿要复活的正是它** |
| `on_error_display` | `:67` | `app.py:839`、`app.py:2403` | ✅ |
| `on_diagnosis_run` | `:72` | `app.py:637` | ✅ |
| `on_template_select` | `:17` | 0 | 💀 |
| `on_next_step_show` / `_click` | `:22` / `:27` | 0 / 0 | 💀 |
| `on_method_recommend` | `:37` | 0 | 💀 |
| `on_table_generate` | `:47` | 0 | 💀 |

⇒ **13 类里 7 类零调用**（含 `on_export`）。`usage_hooks.py:3` 自述「记录 ≥12 类匿名化事件」是**定义数**不是**接线数**：接线数 6。（本单不修，只在 §5 落点里把它们复活或明列为待清。）

**历史 schema 面**（`logs/usage_events_*.jsonl` 只读扫描：11 个文件、848 行；按红线只报**名集不报分布**）：

- 已出现过的 `event` 名：`analysis_execute`、`data_upload`、**`export`**、`next_step_show`、`page_visit`、`visit`
  ⇒ `export` 这个事件名**历史上真响过**（今天 `on_export` 已无人调），本稿延用它、**不另起 `export_execute`**；`visit` 是孤儿名（无任何载荷键），列入待清不入新表。
- 各事件的既有键集（＝新字段命名的对齐基准）：`export → {format, success, duration_ms}`；`page_visit → {page_id}` **但同时存在 `{page}` 老写法** ⇒ schema 已漂移，查询侧必须并集两键（§6）。
- 顶层键并集：`timestamp, event, column_count, duration_ms, file_type, format, method_id, page, page_id, priority, row_count, step_id, success`。**无一个自由文本字段**——这条是新增字段的硬约束（§4）。

---

## 3. 要回答的问题（埋点的唯一存在理由）

`KNOWN_ISSUES.md:57` 的决策问句是「独立 mode 到底有没有人用」。可被判定的三问：

- Q1 两个入口各自的**曝光 / 生成动作 / 产出被采纳**的漏斗量，能否分开统计？
- Q2 入口 B 内部，**模板直出 vs AI 增强**的占比（决定"合并"会不会砍掉 LLM 依赖面）？
- Q3 双入口的**导出侧**是否同构（与 s922-126 矩阵的 4 入口对齐，回答"门禁卡掉了多少次、卡在哪类原因"）？

**不回答**：不给任何使用率结论、不做显著性判断、不替用户决定合并方向（`KNOWN_ISSUES.md:58` 属"待拍板"）。

---

## 4. 事件字典（6 个 ≥ 完成标准要求的 4 个）

字段规范：`snake_case`；**一律不写入正文/标题/主题/文件名/用户输入**（`log_event` 明文落盘且 `export_feedback_package` 会打包外发）；`entry` 为受控枚举；未知值写 `"unknown"` 而非省略键（否则 §2 的聚合器读出来是缺列）。

公共字段（所有 6 个事件都带，由一个私有 helper 注入）：
`entry` ∈ {`paper_mode`, `wizard_step7`}｜`step`（wizard 侧固定 `7`；mode 侧填 tab 序号或 `"na"`）｜`ui_surface` ∈ {`independent_mode`, `wizard_template`, `wizard_ai`}。

| # | 事件名 | 触发点（实测 file:line） | 载荷字段（除公共 3 项） | 为什么落在这 |
|---|---|---|---|---|
| **E1** | `paper_entry_view` | A：`paper_writing_ui.py:38`（`render_paper_writing_ui()` 函数体首行后）；B：`undergrad_wizard.py:3257`（`elif step == 7:` 分支入口） | `llm_available: bool`（A 侧取 `src.llm_gateway.is_llm_available()`，B 侧即 `:1356` 判据）、`has_engine_state: bool`（A：`engine.state.generated_sections` 非空＝`paper_writing_ui.py:462`；B：`wiz_data.get("method_text")` 即 `:3479`） | 曝光面是**分母**；不埋它，Q1 只剩分子。`llm_available` 必须进曝光事件，否则 B 的 expander 未渲染期会被误读成"没人点" |
| **E2** | `paper_generate_request` | A：`paper_writing_ui.py:453`（`if st.button("🚀 生成完整论文初稿", key="gen_paper")` 为真、进入 spinner 前）；A 次级：`:404`（`key="gen_qa"` 生成确认问题）；B：`undergrad_wizard.py:1364`（`key="_ai_paper_gen"` 为真） | `action` ∈ {`full_paper`, `qa_questions`, `ai_paragraphs`}、`backend` ∈ {`engine_direct`, `workflow_quick`}、`gaps_present: bool`（A：`engine.get_gaps_summary()` 含 ❌/⚠ 的判断已在 `paper_writing_ui.py:449-451`，照抄其布尔化结果即可，不新增计算） | 请求点而非完成点：LLM 可能几十秒（`:454` spinner 文案自述「可能需要几十秒」、`:1365`「30-60 秒」），只有请求侧才能算"放弃率" |
| **E3** | `paper_generate_result` | A：`paper_writing_ui.py:456` 之后（成功）与 `:459` `except`（失败）；B：`undergrad_wizard.py:1378` 之后（成功）／`:1393` `else` 空结果／`:1395` `except` | `success: bool`、`duration_ms: int`、`sections_count: int`、`llm_used: bool`、`error_type: str`（`type(e).__name__`） | 对齐既有 `export` 事件的 `{format, success, duration_ms}` 三件套形状（§2 schema 面），读侧零改动即可聚合；`sections_count`/`llm_used` 回答 Q2 |
| **E4** | `paper_draft_variant_adopted` | B：`undergrad_wizard.py:1382-1385`（AI 文本写入 `_ai_method_md`/`_ai_result_md`）→ 记 `variant="ai"`；`:1399-1401`（「🔄 恢复使用模板版本」`pop` 两键）→ 记 `variant="template_revert"`；B 主路（无 AI 分支可进时）在 `:3474` 组装 `full_draft` 处记 `variant="template"` | `variant` ∈ {`template`, `ai`, `template_revert`}、`source_section` ∈ {`methods`, `results`, `both`} | 没有它，Q2 的分子分母都错——「生成了但回退」会被记成采纳。回退动作在 `:1400 pop`，与生成事件同为 UI 层，成本一行 |
| **E5** | `export`（**复活 `usage_hooks.py:62` 的 `on_export`**） | A 正式交付：`deliverable_center_panel.py:204` 按钮为真后、四种格式各自 `except`（`:223/:248/:260`）；C 草稿导出：`paper_preview_panel.py:121`／`:130`；B/D 向导正式出口：`undergrad_wizard.py:69`（`_render_official_download` 内，门禁已过）；B 作业包：`app_pages_text.py:154` | `format: str`（`md/docx/pdf/zip/html/csv`）、`success: bool`、`duration_ms: int`、`entry`、`gate_passed: bool` | `on_export` 已有形参 `(format, success, duration_ms)`，**零改签名**即可承接；`gate_passed` 是与 s922-126 矩阵的唯一桥梁（Q3） |
| **E6** | `export_gate_verdict` | `export_gate.py:101` `allowed = len(block_reasons) == 0` 之后、`return`（`:102`）前**一处落全族** | `allowed: bool`、`reason_codes: list[str]`（把 `block_reasons` 的 `[HEALTH_x]`/`[BUNDLE]`/`[UNCONFIRMED_AI]`/`[PRIVACY_HIGH]` **前缀码**单独收集，**不记 detail 文本**——detail 里可能含标题等自由文本）、`reason_count: int` | 单点覆盖 A/C/D 三入口（它们的门禁最终都汇到 `run_export_gate`，见 s922-126 §1 的 10 个命中）；比每入口各埋一次少 3 个落点、且不会漏 |

> E1–E6 共 6 个事件、14 个落点。事件名沿用既有小写单词风格（`page_visit`/`data_upload`/`export`），新增前缀统一 `paper_`／`export_`，与 §2 历史名集无冲突（除 `visit` 孤儿名外无重名）。

---

## 5. 落点清单（file:line × 动作，交给放行后的执行班）

| 落点 | 文件:行（实测） | 动作 | 备注 |
|---|---|---|---|
| L1 | `src/utils/usage_hooks.py`（新函数追加在 `:64` 之前） | 新增 `on_paper_entry_view / on_paper_generate_request / on_paper_generate_result / on_paper_draft_adopted / on_export_gate_verdict` | 全走 `log_event`；**不改 13 个既有 hook 的签名** |
| L2 | `src/ui/paper_writing_ui.py:38` 后 | E1（`entry="paper_mode"`） | 函数体第一行，避开 `:41-44` 的引擎初始化分支 |
| L3 | `:404`／`:453` 按钮分支内 | E2（`action="qa_questions"`／`"full_paper"`，`backend="engine_direct"`） | 按钮 `key` 已是稳定字面量（`gen_qa`/`gen_paper`），可直接当 `action` 派生源 |
| L4 | `:456` 后／`:459` except 内 | E3 | 成功分支现值 `:457 st.success`；失败分支 `:459-460` |
| L5 | `src/ui/undergrad_wizard.py:3257` 分支首行 | E1（`entry="wizard_step7"`, `step=7`） | |
| L6 | `:1364` 内 | E2（`action="ai_paragraphs"`, `backend="workflow_quick"`） | |
| L7 | `:1378` 后／`:1393` else／`:1395` except | E3 | `result.sections` 空即 `sections_count=0, success=False` |
| L8 | `:1382-1385` 写键处、`:1399-1401` `pop` 处、`:3474` 模板组装处 | E4（三种 `variant`） | 三个点必须齐全，否则 Q2 读数偏 |
| L9 | `src/ui/export_gate.py:101-102` 之间 | E6 | 一处覆盖三入口 |
| L10 | `src/ui/deliverable_center_panel.py:204`（＋`:223/:248/:260` 三个 except） | E5 | 格式取自 `:202` 的 `export_format` radio |
| L11 | `src/ui/paper_preview_panel.py:121/:130` | E5 | `:133` 那个按钮标签与扩展名不符（s922-126 §2 维度 5），埋点时按**实际 mime** 记 `format` |
| L12 | `src/ui/undergrad_wizard.py:69` | E5 | `_render_official_download` 的 4 个调用点（`:455/:777/:1538/:1658`）一次覆盖；建议把 `label` 之外再加一个 `artifact_key` 入参用于区分 |
| L13 | `src/ui/app_pages_text.py:154` | E5 | 作业包在门禁外（s922-126 §2 维度 2），`gate_passed=False` 语义不适用 ⇒ 该入口记 `gate_passed` 为 `"n_a"`，**不许伪造成 `True`** |
| L14 | `app.py:54-58` import 块 | 追加新 hook 名（若 UI 模块各自 import 则不需要） | 现状该 import 块已含 `on_export`（`app.py:57`），**import 了不接线的死代码正是本批要消掉的** |

**同时顺带接线（零新语义，只补死链）**：`on_export`（E5 复用）、`on_consistency_check`（现成调用点候选 `deliverable_center_panel.py:155` 已算出 `consistency_issues`，只差一次 `on_consistency_check(len(errs), warns)`）。其余 5 个 💀 hook（`template_select`/`next_step_show`/`next_step_click`/`method_recommend`/`table_generate`）**本批不复活、不清除**，交主班与 `usage_hooks.py:3` 的「≥12 类」表述一起裁决。

---

## 6. 数据面查询示意（完成标准 3：字段级，本班不代跑统计结论）

前提提醒（都在 §2 有锚）：① `get_usage_summary` 只看 `event`，**payload 字段它读不到**；② 因此"入口维度"能不能零改读侧回答，取决于**是否把入口编进事件名**——本稿选择**不编进事件名**（事件名保持稳定、`entry` 作字段），代价是 Q1/Q2 需要一个新读函数，见 6.3。③ 文件名 `usage_events_YYYYMMDD.jsonl`（`usage_logger.py:90`）＝按天轮转，跨天查询要 glob。

### 6.1 「谁在用两个入口」——Q1

```python
# 口径：一次扫描，按 (event, entry) 二元组计数；只出计数，不出结论
import json, glob, collections
c = collections.Counter()
for p in glob.glob("logs/usage_events_*.jsonl"):        # LOG_DIR 被重定向时改这里
    for line in open(p, encoding="utf-8"):
        if line.strip():
            e = json.loads(line)
            if e.get("event", "").startswith("paper_"):
                c[(e["event"], e.get("entry", "unknown"))] += 1
```
要**零改读侧**也能看，则把事件名按入口分裂（`paper_generate_request_mode` / `paper_generate_request_wizard`），`get_usage_summary`（`usage_logger.py:123`）即可直接分辨——代价是事件名翻倍、§4 的 `entry` 字段变成冗余。**这是唯一需要拍板的取舍，两案都成立。**

### 6.2 「模板直出 vs AI 采纳」——Q2

```python
# 需要字段：event == "paper_draft_variant_adopted" -> variant, source_section
# 问：进入第 7 步的人里，最终留在 AI 版的有几个？
num = 采纳 variant=="ai" 且 source_section=="both" 的次数
den = event=="paper_entry_view" 且 entry=="wizard_step7" 的次数
# 注意：E1 与 E4 都受 Streamlit 重跑放大（见 §7 R2），分子分母同幅放大才可比
```

### 6.3 需要新增的**读**（不是统计，只是取字段的能力）

`usage_logger.py` 现无任何"按字段聚合"的函数（`:123-150` 是唯一的）。建议追加一个只读 helper（与 `get_usage_summary` 同层、同样 `except OSError: pass` 不崩）：

```python
def get_event_field_counts(event: str, field: str, days: int = 7) -> dict[str, int]:
    """按事件名过滤后统计某个字段的取值分布。字段缺失归 "unknown"。"""
```
键名约定：`event` / `entry` / `action` / `backend` / `variant` / `format` / `success` / `gate_passed` / `reason_codes`。**`days` 语义与 `:123` 保持一致（文件个数）**，别在文档里把它说成日历天数（§2 已记此坑）。

### 6.4 与门禁联表——Q3

`export_gate_verdict.reason_codes` 与 `export.gate_passed` 用 `timestamp`＋同一次 rerun 的顺序对齐（**无 session/run id 可用**——见 §7 R3，这是本设计已知的最大弱点）：只能做"同日同事件名"的量级对账，不能做逐条 join。

---

## 7. 风险与红线（只登记，不改码）

- **R1 隐私最小化不可破**：`log_event` 明文 JSON、`export_feedback_package`（`usage_logger.py:181`）会把聚合包写到 `feedback_package/`。⇒ E6 只记**前缀码**不记 `block_reasons` 全文（后者含 `i.title: i.detail`，可能带论文标题）；任何事件不得带 `bundle.title`／`topic`／`filename`。既有 `export` 事件就带 `format` 不带文件名，新事件不得比它更松。
- **R2 Streamlit 重跑放大**：`render_*` 每次交互都重跑（例：`app.py:2320-2330` 的 tab 体内联渲染），E1「曝光」会被重复计数 ⇒ 埋点方案**只保证趋势可比**，不保证绝对人数；若要求去重，需要额外的 session 级"本次会话已记"标志（本稿不加，属拍板项 P1）。
- **R3 无关联 id**：`usage_logger.py:85` 的 `timestamp` 只到**秒**，且没有 session/run 级 id ⇒ §6.4 无法逐条 join；且"只到秒"与 s922-126 在册缺陷「`_archive_to_history` 时间戳只到秒 ⇒ 同秒两次归档静默覆盖」同族，**本单不修**，只把风险写进设计（要精确关联就得先加 id，属生产码改动）。
- **R4 静默失败**：`usage_logger.py:95-96 except OSError: pass` ⇒ 磁盘/权限出问题时事件**静默蒸发**，"使用率下降"可能只是日志没写成。上线时须配一条 `error_events` 侧的自检（或按 `logs/` 文件 mtime 人工核）。
- **R5 落盘根**：`LOG_DIR` 默认是 **CWD 相对 `Path("logs")`**（`app_paths.py:27`），非用户主目录 ⇒ 换启动目录就换日志根，历史面簿（s922-128 覆盖区）会看到"看似缺天"。属 s922-126 P5 同源问题，交人工。
- **R6 schema 漂移**：`page_visit` 同存 `page_id`（现值，`usage_hooks.py:14`）与 `page`（历史行）两写法，且有过无载荷的 `visit` 事件 ⇒ 新字段的查询必须给缺失兜底 `"unknown"`，不得假设老行有 `entry`。
- **红线自查**：本稿未改任何生产码、未跑 LLM、未读写被试数据、未给统计结论（§6 全是**待跑的查询形状**）；`logs/` 仅只读扫描、`data/` 未动。

---

## 8. 复算附录

```bash
cd /d/code/psy-analysis
rg -n 'def render_paper_writing_ui' src/ui/paper_writing_ui.py      # 38
rg -n '# 步骤 7: 写入论文' src/ui/undergrad_wizard.py                # 3255
rg -n 'F1 论文写作两入口合并|paper_writing_ui.py. \(678 行' KNOWN_ISSUES.md   # 54 / 56
wc -l src/ui/paper_writing_ui.py src/ui/undergrad_wizard.py          # 678 / 3715
rg -n 'engine\.generate_full_paper|engine\.generate_questions' src/ui/paper_writing_ui.py      # 406 / 456
rg -n 'generate_paper_quick' src/ui/undergrad_wizard.py             # 1369 import / 1378 调用
rg -n 'engine = PaperEngine\(\)|sections = engine\.generate_full_paper' src/paper_writer/workflow_service.py  # 79 / 117
rg -n 'def log_event|usage_hooks' src/utils/usage_logger.py src/utils/usage_hooks.py   # 见 §2，仅 1 命中
rg -n 'log_event|log_error' src/ui/                                            # 预期 0：UI 层不直调
rg -n 'on_export' app.py src/ tests/                                           # 生产 0（import app.py:57 / 定义 :62 / 测试直调 tests/test_usage_hooks.py:89）
rg -n '_LOG_DIR' tests/conftest.py                                             # 52：测试期隔离，新埋点不落真实 logs
# schema 面（只读，不改一字）：ls logs/usage_events_*.jsonl
```

**测试件引用口径**（按主班 08:33 补记执行）：本稿只按**单行 awk 复核**引用测试件，未整读任何测试文件；被引 4 件 `tests/conftest.py:52`、`tests/test_privacy_archive_usage.py:194/201/205/207`、`tests/test_usage_hooks.py:89`、`tests/test_export_naming_global.py` 全部 `git status --short tests/` ＋ `git diff --stat HEAD -- tests/` **双路零输出** ⇒ 与 HEAD 一致，非他班在途态（`tests/` 下 4 个 `??` 未跟踪件为开工基线在册件，本稿一字未引）。`tests/test_v163_acceptance.py` **本单未读、未引**。
