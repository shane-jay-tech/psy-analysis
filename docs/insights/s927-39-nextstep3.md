# nextstep 三处反直觉行为 · 逐处治理/文档化裁决材料（s927-39 · 2026-09-28）

> 性质：**只读位出材料，零码改动**。`src/utils/next_step_engine.py` 与两枚测试件均未改（`git status --porcelain` 对这三件为空＝与 HEAD 同）。
> 上游需求出处：`zcode-bridge/done/s922-119-nextstep-engine-core.result.md:137-138`（遗留节）
> 「三处反直觉行为本件**只钉不改**，是否治理交主班：`analysis_recipe={}` 空字典即算『已推荐方法』（会少推 `get_method_recommendation`）；`paper_bundle` 为任意非 dict 无 `.sections` 对象即算『有论文草稿』；`consistency_issues` 非 list 时静默判未通过。前两条属**推荐漏项/虚高**，不涉统计数值，但会影响 UI 提示正确性。」

## 〇、锚点复核（两处漂移，已按盘修正）

| 前提 | 实测 | 判定 |
|---|---|---|
| 三处行号与语义 | `src/utils/next_step_engine.py:74-75 / :93-102 / :119-132`，读码逐字相符 | ✅ 成立（文件 392 行，与 s922-119 记录同长） |
| 钉桩件在世且仍绿 | `.venv/…python -m pytest tests/test_next_step_engine_core.py tests/test_next_step_panel.py -q` → **28 passed in 1.01s**（引擎文件 382 行／26 例） | ✅ 与 s922-119 记的 28/26 逐数相符，零漂移 |
| 🔴 **本班任务书把键名写错了**：横幅与卷宗引文写 `analysis_ready={}` | 盘上无 `analysis_ready` 这个键；真名 **`analysis_recipe`**（`next_step_engine.py:74`、`src/ui/state_keys.py:29`） | 按 w40-brief §9「以卷宗正文＋磁盘为准」⇒ 本文一律写 `analysis_recipe`；派单件正文的 `analysis_ready` 属誊写漂移，**不影响任务成立**，但别再据此 grep `analysis_ready`（零命中） |
| s922-119 的判据 4 旁证 | 引擎层用例不 import streamlit；`tests/test_next_step_panel.py` 用 monkeypatch **把引擎整体换掉** | ✅「面板有测、引擎无测」前提仍在（治理只需改引擎＋3 枚在册用例） |

## 一、三处现状复核（每处都给活体探针，纯内存、零写盘）

### 处 1 · `analysis_recipe={}` 也算「已推荐方法」——症状比卷宗写的更重

`next_step_engine.py:75`：`state["method_recommended"] = bool(recs) or recipe is not None`（只判 `is not None`）。

```
探针 A（引擎层）  ev({'analysis_recipe':{},'method_recommendations':[]}) → method_recommended True / analysis_done False
探针 A'（推荐层） ss={'df':[1], 'upstream_state':{…IV/DV…}, 'analysis_recipe':{}}
                 → recommend_next_steps 返回 ['run_analysis', 'collect_evidence']
```

⇒ 不是"少推一条"而已：`get_method_recommendation` 被吞掉的同时 **`run_analysis` 被顶上来**，而它的 `prerequisites` 明写「已获得方法推荐」（`:217`）——即**推荐项自己声称的前置并不成立**。规则 3（`:187-190`）与规则 4（`:205-208`）共用这一个 bool，所以一处判定同时造出"漏推＋虚开"两个症状。

可达性（本单新计数，决定定级）：全仓 `analysis_recipe` **只有一个生产写者** `src/ui/method_recommender_panel.py:194 session_state[_RECIPE_KEY] = recipe`，写的恒为 `AnalysisRecipe` dataclass 实例（非空容器）；`src/ui/session_reset.py:160-162` 用 `pop(key, None)` 清态 ⇒ 键缺席时 `get()` 回 `None`；`src/utils/workspace.py` 对这三个键**零引用**（自动保存/回灌不碰它们）。⇒ **当前生产路径不可达**，属"写者一旦改成 dict 序列化（如 JSON 回灌）即成真"的潜伏项。
附带口径问题：`:74` 直读书面量 `"analysis_recipe"`，而同仓已有常量 `ANALYSIS_RECIPE_KEY`（`state_keys.py:29`）与访问器 `get_analysis_recipe()`（`method_recommender_panel.py:201-203`）⇒ **常量旁路**（同型在册缺陷：假开关/字面量键）。

### 处 2 · 任意非 dict 无 `.sections` 的对象也算「有论文草稿」——外溢到三格

`next_step_engine.py:93-102`：`try: bool(paper_bundle.sections)` → `except AttributeError:` → 是 dict 则看 `sections`，**否则 `has_paper = True`**。

```
探针 B  ev({'paper_bundle': Junk()})            → paper_draft True / export_ready False / consistency_passed False
探针 B2 ev({'paper_bundle': Junk(), 'export_allowed': True}) → paper_draft True / export_ready True
```

⇒ 连锁面：`paper_draft` 参与规则 8（`:274-281` 抑制 `write_paper`）、规则 9（`:296-298` 推 `consistency_check`）、以及 `:136` 的 `has_content = result_cards or paper_draft` → **点亮 `export_ready` → 规则 11 `final_review`**。即一枚垃圾对象可把"有论文草稿 → 可导出交付包 → 建议最终审阅"三格一起虚高，卷宗只记了第一格。

可达性：全仓 grep（`app.py`＋`src/`＋`tests/`）**未找到任何生产写入 `session_state["paper_bundle"]` 的点**——读者有 4 处（`app.py:2325`、`deliverable_center_panel.py:58`、`export_gate.py:29/72`、`health_panel.py:116`），唯一写入者是测试件 `tests/test_e2e_resultcard_paperpreview.py:46`（写的是真 `PaperDraftBundle`）。⇒ 处 2 在生产上比处 1 更不可达；但**同一枚发现另有一层含义**：`paper_draft` 若在真实 App 里恒 False，则规则 8/9/10/11 四格（写论文/一致性/导出/最终审阅）**永不点亮**，那是另一个问题（见遗留 2，本单不代定性）。

跨模块口径分歧（本处最该治理的真正理由）——同一资产三种读法：

| 读法 | 位置 | 空/垃圾对象时 |
|---|---|---|
| `is not None` → 再看 `.sections`，**else True** | `next_step_engine.py:93-102` | **有** |
| `session_state.get("paper_bundle") is not None` | `src/utils/feedback_logger.py:133` | **有**（连 sections 都不看） |
| `if not paper and not cards` ⇒ 无 | `src/utils/readiness_scorer.py:227-231` | **无** |

⇒ 只治 `next_step_engine` 一处＝在已有的三种径上再刻第四种；真要修要抽公共谓词（属"资产谓词单源"议题，与在册 `_METHOD_ASSUMPTIONS` 登记不同域）。

### 处 3 · `consistency_issues` 非 list 静默判未通过——方向是 fail-closed

`next_step_engine.py:119-132`：`None` → False（当"未运行"）；`isinstance(list)` → 按有无 `level=="ERROR"` 判；**else → False**。

```
探针 C  ev({'consistency_issues':'abc'}) → False ；ev({'consistency_issues':None}) → False
```

⇒ 三处里唯一**不虚高**的一处：代价只是"跑过但形状不对时显示未通过、且无任何原因文案"（用户看到的一直是"去跑一致性检查"，多跑一次即自愈）。建议维持现状并只补文档串。

同族附带发现（不在卷宗三处内，本单新登记，非统计数值）：`readiness_scorer._score_consistency:248` 写的是 `issues = ss.get("consistency_issues", [])`，随后 `if issues is None: → 80「未运行检查」`——**键缺席时默认已是 `[]`，该分支只在显式写入 None 时可达**；缺席路径落到 `errors=[] / warns=[]` ⇒ **score 100、status good、detail「0 条警告」**。⇒ 同一状态（从未跑过一致性检查）下，readiness 面板说"100 分良好"，next-step 引擎说"未通过、去跑检查"，两面板互斥。这枚比处 3 本体更值得单开。

## 二、逐处两案（含最小修法与回滚成本）

| 处 | 案 α：治理 | 案 β：文档化（现状即钉桩） | 回滚成本 |
|---|---|---|---|
| 1 | 一行：`… or bool(recipe)`（并把 `:74` 的字面量键换 `ANALYSIS_RECIPE_KEY`，或径直走已有访问器 `get_analysis_recipe`）。改动面＝`next_step_engine.py` 一处表达式＋`tests/test_next_step_engine_core.py:180` 一枚在册用例改写 | 现状已被 `test_method_recommended_quirk_empty_recipe_still_counts` 钉住 ⇒ 不改即零风险；风险全在"哪天 recipe 变成 dict 序列化" | 极低（单文件、可 `git revert` 单笔） |
| 2 | 一行：`:102` 的 `has_paper = True` → `False`（与处 3 同向 fail-closed）。在册用例 `test_paper_draft_three_bundle_shapes:188` 需同步改写。**但**要连带裁：`feedback_logger:133` 与 `readiness_scorer:227` 两种口径跟不跟（不跟就是第四种径） | 同左：已被钉桩；且生产无写者 ⇒ 现网不发作 | 低（单行），**扩散成本高**（牵出"资产谓词单源"议题） |
| 3 | 可选：`else` 分支加一次性告警（`_alert_once` 同族已有件）或把非 list 视作 `None`（语义等价，仍是 False） | **推荐 β**：现状 fail-closed 是正解，文档串补一句"非 list 与未运行同为 False，不区分" | 不改即零 |

## 三、推荐（分档；本班不自取授权）

1. **处 3：文档化，不改码**（现状即正解；把"非 list→False"写进 docstring 一句）。
2. **处 1：治理，排"硬化档"不排"故障档"**——因为生产不可达，但改动只有一行且顺带消灭一枚常量旁路；**必与 `:180` 用例同批**，并保留一条反向断言（`{"a":1}` 仍 True）以免改过头。
3. **处 2：暂缓单点治理**，把它升进"资产谓词单源"议题一起裁（三读法已在世 ⇒ 单点改＝第四种径）；过渡期维持现状＋在册钉桩，并在 docstring 里明写「非 dict 无 `.sections` 的对象算『有草稿』」。
4. **本单新登记两条，请主班决定是否另开单**：① `readiness_scorer._score_consistency` 的 `[]` 默认使「未运行」分支近乎不可达、且与引擎读数互斥（第 3 节附带发现）；② `session_state["paper_bundle"]` 在 `app.py`＋`src/` 内**查无写入点** ⇒ 规则 8–11 四格是否常态不可达（属功能面，超出"反直觉行为"原卷宗，未定性）。
5. 排序建议：这三处**不抢**在册高风险（semopy 假 0 零告警＋SRMR 进 `effect_sizes`、`test_cfa_sem_golden.py:269` 恒真断言、缺失率前置闸）之前——它们不碰统计数值，也不影响判据，属"提示正确性"档。

## 四、复跑命令与零改动自证

```bash
cd D:/code/psy-analysis                       # HEAD fa3f41e（现取）
.venv/Scripts/python.exe -m pytest tests/test_next_step_engine_core.py tests/test_next_step_panel.py -q   # 28 passed
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
from src.utils.next_step_engine import evaluate_project_state as ev, recommend_next_steps as rec
class J: pass
print(ev({'analysis_recipe':{},'method_recommendations':[]})['method_recommended'])
print([s.step_id for s in rec({'df':[1],'upstream_state':{'candidate_vars':{'independent_vars':['x'],'dependent_vars':[]}},'analysis_recipe':{}})])
print({k:ev({'paper_bundle':J()})[k] for k in ('paper_draft','export_ready','consistency_passed')})
print({k:ev({'paper_bundle':J(),'export_allowed':True})[k] for k in ('paper_draft','export_ready')})
print(ev({'consistency_issues':'abc'})['consistency_passed'], ev({'consistency_issues':None})['consistency_passed'])"
grep -rn "analysis_recipe" --include=*.py app.py src/ tests/ | grep -v __pycache__      # 唯一生产写者＝method_recommender_panel.py:194
grep -rn "session_state.pop\|RESEARCH_SESSION_KEYS" src/ui/session_reset.py | head       # pop ⇒ 键缺席读回 None
grep -rn "(paper_bundle|PAPER_BUNDLE_KEY)…]…=[^=]" 全仓                                # 生产零写者，唯一写者是 tests/test_e2e_resultcard_paperpreview.py:46
git status --porcelain src/utils/next_step_engine.py tests/test_next_step_engine_core.py tests/test_next_step_panel.py   # 空
```

零改动自证：本班对 `psy-analysis` 只新增文档（s927-33／36 两份＋本档），`git status --porcelain` 由开工 12 项 → 收口 15 项，增量恰为本班三份 `??` 文档；8 枚在途 ` M`（`app.py`／`src/analysis/{__init__,cfa,result_card}.py`／`src/output/interpretation.py`／`tests/test_cfa_sem_golden.py`／`pytest.ini`／`requirements-lock.txt`）与另 4 枚 `??` 原样未动；`data/` 未碰；探针全为纯函数内存调用，无 AppTest、无写库。

## 五、遗留问题

1. 卷宗三处都在"提示正确性"档，**不涉统计数值**（s922-119 同判）；本文所有结论只到"可批形状"，改码须人工放行（横幅＝只读位）。
2. 「`paper_bundle` 生产零写者」是否等于"规则 8–11 常态不可达"，需跑一次 AppTest 真点一遍导出链才能定（`app.py` 本身就在 8 枚在途 ` M` 件之中，属别班/早先半成品）⇒ 本班不碰、不代定性。
3. 「资产谓词单源」若立案，范围至少含 `next_step_engine`／`feedback_logger`／`readiness_scorer`／`project_health`（后者 `:98-112` 又是 `hasattr` 系第四种写法）⇒ 改动面远大于"改一行 else False"，请勿按单行成本排期。
4. `test_next_step_engine_core.py` 对"阻断项填充顺序"绑的是当前实现语义（未阻断优先、槽满即止，`:384-390`）；若日后治理顺带改截断策略，`test_unblocked_fill_before_blocked` 与 `test_ties_keep_rule_definition_order` 会同批翻红——这是 s922-119 已登记的有意识护栏，本单复核仍在位。
