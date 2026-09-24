# psy `key=` 隐式注册面并入 session_state census（s924-33 · 只读）

- 班：`qoder-executor-20260925-0540-psy45`（波次 11 补派）· 2026-09-25 05:43 认领 · cwd `D:\code\psy-analysis`
- 前手锚：`zcode-bridge/done/s922-136-session-subscript-census.result.md:56`「`key=` 隐式注册面（`app.py`＋`src`＋`scripts` 内 **757 处 `key=` 实参**）本档未纳入判定…**93/119 两个分母在并入该面后会漂移**」——:56 逐字在盘。
- 同族档：`docs/insights/psy-session-state-ast-census-20260924.md`（`s924-21`，psy41 出，已入库）。本班**先复跑它的探针**（`tmp/qoder-executor-20260925-0450-psy41/probe_session_state.py`，逐字未改）→ `FILES_SCANNED 249 / AST_DISTINCT_KEYS 164 / AST_OCCURRENCES 719 / DYNAMIC 71 / DEFAULTS N=27 / STATE_KEYS_CONSTS 17` **六项逐位复现** ⇒ 本档与它零矛盾，增量只在"隐式键"这一面。
- 性质：**只读出稿**。零被跟踪文件改动、未 `add`、未 `commit`；探针与全部输出落 gitignored `tmp/qoder-executor-20260925-0540-psy45/`；零库接触。

## 0. 结论速览

1. 🔴 **锚上那个"757 处 `key=` 实参"不是实参数**。三入口现读：紧排字面串 `key=` **737 处**、宽口径 `\bkey\s*=` **758 处**（同一算法在 `bcb21f4`(9/23) 与 `HEAD`(9/25) 上**都读 758** ⇒ 那 −1 差不在盘上、在锚自己的口径里，量级对拍成立）。真·AST 实参只有 **701 处**，其中落在 `st.*` 调用上的仅 **353 处**——另外 **348 处**是 `LiteratureEntry(key=…)` 226、`other.attr` 69、`sorted(key=…)` 15 这类**与 session_state 无关**的调用。
2. **双轨闭合**（判据①的"差异归因"）：`737 ＝ 701（真实参）＋ 36（标识符后缀 `api_key=`/`sort_key=`/`primary_key=`）＋ 0（def 形参）＋ 0（串/注释内）＋ 0（其它）`，按 (行,列) 位置互斥切分，探针自证 `CLOSED True`。⇒ 与 psy41 那条「AST 26 与正则 30 各有伪命中、取单个数不算证据」同型复现。
3. **新分母**（判据②）：`119 → 375`、`93 → 349`、psy41 的 `164 → 420`；`_defaults` 对键面的覆盖率从 22.7%（27/119）塌到 **6.9%**（26/375）。`state_keys.py` 17 枚常量值在 `key=` 面被引用 **0 次** ⇒ widget 面的常量表覆盖率是 **0/265**，比 psy41 报的 8.5% 更空。
4. **仅由 `key=` 注册、三面都不在的键 256 枚**（判据③），全清单见 §5。`app_mode` 的卷宗说法**半否证**：「不在 `_defaults`」✓（27 键表内无它），「只由 widget `key=` 注册」✗——它同时有 **1 处** `key=` 注册（`app.py:293 st.radio`）＋ **7 处**直访（psy2 表：attr-write 6／safe-get 1）⇒ 隐式面给它的不是"唯一注册源"，而是"`_defaults` 之外又多一个来源"。
5. 🔴 **psy2 档里那颗 93 的撞车地雷**：`93` 在 s922-136 同时是「合并表访问点 65＋14＋5＋9＝93 点」与「键面 119−26＝93 个未登记键」两个互不相干的量。并入 `key=` 面后两义彻底分叉：未登记键数 `93 → 349`；若把 `st.*` 的 `key=` 当"注册点"并进点分母 → `93 → 446`（353 点）乃至 `794`（全 701 实参）。⇒ 今后引"93"必须带口径名，本档只重算**键面**那一义。
6. 🔴 **119 是假低，164 对**：`119 ⊂ 164` 严格成立（探针自证 `PSY2_SUBSET_OF_PSY41 True`），多的 45 枚＝**34 枚只经模块常量名触达**（psy2 无"常量回溯"）＋**11 枚只经局部别名 `session_state[...]` 触达**（psy2 的谓词是 `st.session_state` 直连，例 `src/ui/template_center_panel.py:194 session_state["current_file_name"] = file_name`——psy2 自己在遗留问题 #2 里讨论过这一行，却没把它算进 119）。⇒ 两档不是互相打脸，是 psy2 的键面天生少 45；本档一律以 164 为直访基线。
7. **隐式面的真实危害不是数量而是"没登记处"**：256 枚里 **14 枚在两个文件里各写一遍同一个字符串**（如 `_btn_regen_with_override` 在 `app.py:1986` 与 `src/ui/questionnaire_panel.py:557`；`_rp_override_*` 七枚全部是 app/panel 成对硬编码），**13 枚**在 `tests/` 里被字面引用（引用即测试面依赖，改名将红）。这正是 `src/ui/state_keys.py` 建档初衷要治的形态，但它在 widget 面覆盖率为 0。

## 1. 锚点与前提复核

| 锚／前提 | 实测 | 判定 |
|---|---|---|
| `done/s922-136…result.md:56` 那段"757 处未纳入判定／93、119 会漂移" | :56 逐字命中 | 成立（"757"这个词按实参读不成立，见 §2） |
| `src/ui/state_keys.py:9` `DATA_FRAME_KEY = "df"` | 盘态 **:8**；:9 是 `DATA_META_KEY = "meta"` | **复证 psy41 的否证**（同一 1 行漂，本班独立点到） |
| 隐含前提「`key=` 面与 session_state 面高度重叠」 | 265 枚 `st.*` 字面 key 里只有 **9 枚**与 psy41 的 164 直访键相交 | 🔴 **否证**：两面几乎不相交（重叠率 3.4%），所以"并入"是净加 256 而非小修 |
| 隐含前提「`app_mode` 只由 `key=` 注册」 | `app.py:293 st.radio key="app_mode"` ＋ 7 处直访 | **半否证**（不在 `_defaults` ✓／"只由" ✗） |
| psy41 的 164／27／17／719／71 | 现场复跑其探针，六项逐位相同；`app.py` 盘态 `sha8 6522fa5e`／2405 行未变 | 成立（可直接对拍，无时间漂移） |
| scope 差（psy41 无 `scripts`，psy2 与卷宗含 `scripts`） | `rg "session_state" scripts` → **0 处**（连词都不出现） | 无影响：`scripts` 对键面贡献 0，三入口口径与 app+src 同值 |

## 2. 三入口计数（判据①）

| 入口 | `rg -c "key="` 行和 | `rg -o` 出现数 | AST 轨 `key=` 实参 | 其中 callee＝`st.*` |
|---|---|---|---|---|
| `app.py` | 46 | 46 | 43 | 15 |
| `src/**/*.py` | 687（64 份文件） | 687 | 654 | 331 |
| `scripts/**/*.py` | 4（3 份文件） | 4 | 4 | 0（全部 `LiteratureEntry(key=…)`） |
| **合计** | **737** | **737** | **701** | **353** |

- `rg -c` 与 `rg -o` 同值 ⇒ 本仓无"同一行两处 `key=`"，两口径在 737 上重合（这一点不是普适规律，别外推）。
- **与 757 对拍**：现读紧排 737（−20）、宽口径 `\bkey\s*=` 758（＋1）。**差异归因一句**：锚那个数既不是 AST 实参、也不是紧排字面串，它落在"宽口径字面串"上（758），比真·实参多出的 57 处是 `key = ` **空排赋值形态**（如 `src/literature/bibtex_ris_io.py` 里成片的 `key = …`），而真·实参 701 里又确有 348 处与 session_state 无关——所以"757 处 `key=` 实参"这句**数量级对、语义不对**，本档一律用 701/353 两个数。

## 3. 双轨差额逐条归因（737 ⇄ 701，Δ＝36）

```
R=737  call_kwarg=701  def_param=0  assign=0  ident_suffix=36  in_string_or_comment=0  other=0  CLOSED True
```

- 36 处全部是**标识符后缀**形态：`api_key=`（`app.py:1834`、`:1853` …）、`sort_key=`、`primary_key=`、`monkey=` 类——正则把 `…_key=` 的前缀尾巴也数了进来，AST 轨按关键字名 `key` 天然不数。
- `def_param`／串内／注释内均为 **0**：说明本仓的 `key=` 伪命中只有"后缀"这一类，没有"注释里写 key="这种（§十一.4 那类自命中在本 scope 未出现）。
- 反向伪命中（AST 数得着、正则数不着）也测了：`key = ` 空排的 57 处里 AST 实参占 0 ⇒ 两轨在本单 scope 无"AST 独有价值"缺口，差额可全量归因，不留悬项。

## 4. 分母重算（判据②）

基线集合：`K119`＝psy2 探针现跑（119 枚，"裸字面点名"）、`K164`＝psy41 探针现跑（164 枚，AST 可归名直访）、`D27`＝`_defaults`、`SK17`＝`state_keys.py` 17 枚常量值、`KLIT`＝本档 `st.*` 的 `key=` 字面值（265 枚，其中 0 枚经常量名解析、72 处动态 f-string 未计入）。

| 量 | 旧值 | 并入 `KLIT` 后 | 净增 | 说明 |
|---|---|---|---|---|
| 键面（"被字面点名的键"，psy2 口径） | **119** | **375** | ＋256 | `K119 ∪ KLIT` |
| 未登记键数（＝旧"93"键面义） | **93** | **349** | ＋256 | `KLIT ∩ D27 ＝ ∅` ⇒ 分子与分母同增 256 |
| 直访键面（psy41 口径 `N_direct`） | **164** | **420** | ＋256 | `K164 ∪ KLIT`；本档推荐以此为主分母（119 假低，见 §0.6） |
| `_defaults` 覆盖率 | 22.7%（26/119） | **6.9%**（26/375）／6.2%（26/420） | −16pp | 27 枚里 `workspace_saved` 仍不在任何键面（psy41 的死键候选，本档复证不改判） |
| `state_keys` 覆盖率 | 8.5%（14/164，psy41） | **0/265 ⇒ 3.3%**（14/420） | — | 17 枚常量值在 `key=` 面 **0 次引用**：widget 面完全绕开常量表 |
| 点面（旧"93"点义，撞车项） | **93 点** | 446 点（＋353 注册点）／794 点（＋全部 701 实参） | — | 🔴 只登记不采：注册点不属"读侧风险"，A/B/C 分类对它是范畴错误，须新开一列（本档按 §五.4"纯增量"记，不改既有 93 点表） |

## 5. 仅由 `key=` 注册的键（判据③：256 枚全清单）

定义：`KLIT(265) − K164 − D27 − SK17` ＝ **256 枚**——widget 一旦渲染就往 `st.session_state` 里塞这个键，但全仓 `app+src+scripts` 无任何静态直访、也不在任何登记处。分布：

- 按 widget：`button` 105 站点、`text_input` 38、`selectbox` 33、`text_area` 27、`radio` 18、`checkbox` 14、`file_uploader` 10、`download_button` 10、`number_input` 9、`slider` 6、`toggle` 4、`data_editor` 4（＋`plotly_chart` 2、`chat_input` 1）⇒ 六成是**按钮 key**（按钮的 key 只用于"避免重复 ID/定位"，从不被读，属最纯的隐式面）。
- 按文件（前 8）：`src/ui/undergrad_wizard.py` 80、`src/ui/paper_writing_ui.py` 39、`app.py` 37、`src/ui/literature_review_panel.py` 20、`src/ui/items_upload_panel.py` 17、`src/ui/quick_entries.py` 16、`src/ui/experiment_design_ui.py` 15、`src/ui/questionnaire_panel.py` 15。
- 🔴 **跨文件成对硬编码 14 枚**（同一字符串在两个文件各写一遍，改名必漏一侧）：`_btn_regen_with_override`（`app.py:1986`／`questionnaire_panel.py:557`）、`_q_sub_mode_radio`（`app.py:1570`／`:71`）、`_rp_override_{fw,obj,pop,role,rt,subj,sum}` 七枚全部同型（app.py 19xx 段／panel 5xx 段）、`_lr_dl_review`（同文件两处）。
- **被 `tests/` 字面引用的 13 枚**（改名会红，属"事实上的契约"）：`_new_proj_name`、`_pii_hash_all`、`_q_sub_mode_radio`、`exp_protocol_dl`、`exp_protocol_researcher`、`file_uploader`、`import_analysis`、`method_multiplier`、`n_groups`、`paper_defense_qa_gen`、`rq_source_filter`、`rq_status_filter`、`workspace_loader`。
- 具名代表（含卷宗点名的 `app_mode` 的对照说明见 §0.4）：`_ai_paper_gen`、`_ai_paper_reset`、`_ai_trace_run`、`_clear_llm_traces`、`_funnel_stage{1_text,2_text,3_recognize,4_falsi,4_reflect,5_ask,5_rq}`、`_funnel_tier_picker`、`_items_dim_paste_text`、`_jspsych_pivot_{agg,cond}`…

256 枚全量（逗号序＝字典序；同一份内容在 `tmp/qoder-executor-20260925-0540-psy45/implicit_only_keys.txt` 一行一枚，便于 diff）：

```
_ai_paper_gen, _ai_paper_reset, _ai_trace_clear, _ai_trace_run, _btn_regen_with_override, _clear_llm_traces, _funnel_stage1_text, _funnel_stage2_text, _funnel_stage3_recognize, _funnel_stage4_falsi, _funnel_stage4_reflect, _funnel_stage5_ask, _funnel_stage5_rq, _funnel_tier_picker, _items_dim_paste_text, _jspsych_pivot_agg, _jspsych_pivot_cond, _jspsych_pivot_revert, _jspsych_pivot_run, _jspsych_pivot_sub, _jspsych_pivot_val, _lr_add_dim, _lr_dl_matrix, _lr_dl_notes, _lr_dl_review, _lr_do_search, _lr_drop_clear, _lr_drop_dl_docx, _lr_drop_run, _lr_drop_topic_input, _lr_drop_uploader, _lr_finish, _lr_identify_gap, _lr_lit_radio, _lr_mark_high, _lr_max_results, _lr_new_dim, _lr_review_upload, _lr_revise_rq, _lr_search_query, _new_proj_name, _new_proj_note, _pii_hash_all, _privacy_clear_cache, _q_sub_mode_radio, _quality_preview_close, _quality_warn_dismiss, _quick_model_picker, _rename_input, _rename_note, _reviewer_clear, _reviewer_confirm_revise, _reviewer_copy_draft, _reviewer_do_revise, _reviewer_gen_btn, _reviewer_revised_view, _reviewer_section, _rp_override_fw, _rp_override_obj, _rp_override_pop, _rp_override_role, _rp_override_rt, _rp_override_subj, _rp_override_sum, _sidebar_diag, _wizard_back_to_funnel, _wizard_to_literature_review, _ws_export_discard, add_user_lit, ai_review_construct_def, ai_review_construct_name, ai_review_items_cols, ai_review_items_text, ai_review_run, ai_review_src, analysis_goal, archive_filter_tag, archive_tag_input, back_to_home, back_to_list, back_to_main_home, bridge_experiment, bridge_survey, bridge_to_experiment, bridge_to_questionnaire, cancel_exp_design, cancel_lit_search, cancel_q_design, ck_r1, ck_r2, clear_recent_datasets, coll_batch_del, cr_n, cr_submit, defense_qa_gen, defense_qa_max, defense_qa_use_paper_aware, delivery_gen, delivery_include_figs, delivery_include_handbook, delivery_include_thesis, delivery_notes, delivery_palette, diff_all_original, diff_all_revised, dismiss_onboarding, dismiss_recipe, dl_history_clear, docx_generate, docx_include_chart, docx_include_qa, docx_palette, domain_weights_editor, example_type, exp_budget, exp_design_hint, exp_dvs, exp_effect, exp_ivs, exp_n_hint, exp_population, exp_power, exp_protocol_dl, exp_protocol_gen, exp_protocol_researcher, exp_topic, exp_use_llm_enhance, export_btn, export_format, export_paper, export_paper_docx_prep, export_paper_md, file_uploader, gen_exp_report, gen_paper, gen_qa, handbook_dl, handbook_gen, handbook_title, handbook_version, helper_goal, import_analysis, interactive_charts_toggle, items_construct_def, items_construct_name, items_editor, items_enable_ai_review, items_instr_input, items_meta_date, items_meta_project, items_meta_researcher, items_meta_version, items_run_ai_review, items_scale_points, items_show_id_field, items_title_input, items_upload_file, items_use_dim_mode, lang_select, large_file_cols, lit_file_upload, lit_search_kw, load_large_file, method_default_weight, method_multiplier, method_weights_editor, methods_file_upload, modify_recipe, n_groups, n_groups_nonpar, n_materials, ob_fallback, ob_load_demo, ob_run_demo, output_language_toggle, paper_age_m, paper_age_sd, paper_cvars, paper_defense_qa_gen, paper_defense_qa_max, paper_ethics, paper_export_fmt, paper_future, paper_hyp, paper_limit, paper_male, paper_method_select, paper_n, paper_p_desc, paper_pract, paper_proc, paper_rq, paper_theo, paper_title_hint, paper_topic, path_experiment, path_free, path_survey, pipe_clear, pipe_export, pipe_replay, pipe_save, polish_draft_btn, proj_export_btn, proj_import_uploader, relationship_type, reliability_method, request_input, reset_polish, reset_template, restart_onboarding, rq_min_rel, rq_source_filter, rq_status_filter, save_methods, save_qa, save_topic, search_lit_btn, sidebar_return_wizard, step3_back, step3_next, step4_back, step4_next, step5_back, step5_run, step6_back, step7_back, tr_t1, tr_t2, trending_action, trending_apply, trending_target_kw, ua_authors, ua_is_chinese, ua_journal, ua_relevance, ua_title, ua_year, use_recipe_btn, use_recipe_prefill, validity_method, wiz_confidence, wiz_corr_vars, wiz_dv, wiz_export_csv, wiz_export_html, wiz_free, wiz_iv, wiz_paper, wiz_rerun, wiz_snapshot, wiz_to_step7, wizard_file_uploader, workspace_loader, zip_gen, zip_palette
```

## 6. 复算命令（判据①②③④；🔴 本档是登记类文档，自己会进正则判据 ⇒ 一切计数一律限定 scope／排除本档）

```
# 前手两档探针现场双跑（逐字复用，不改一行）
$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/psy2_ss_keys.py > tmp/qoder-executor-20260925-0540-psy45/psy2keys.txt 2>&1; echo $?
0   且档内首三行：全仓被字面点名 119 / 其中在 _defaults 27 / 被点名但不在 _defaults 93
$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0450-psy41/probe_session_state.py > tmp/qoder-executor-20260925-0540-psy45/psy41_rerun.txt 2>&1; echo $?
0   AST_DISTINCT_KEYS 164 / AST_OCCURRENCES 719 / DYNAMIC 71（与 psy41 档内读数逐位相同 ⇒ 两档无矛盾）

# 本档两探针（key= 面 ＋ 差额归因）
$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0540-psy45/probe_key_implicit.py > tmp/qoder-executor-20260925-0540-psy45/k1.txt 2>&1; echo $?
0   KEY_KWARGS_TOTAL 701 / CALLEE_ST 353 / KEYLIT_ST_DISTINCT 265 / DENOM_119_NEW 375 / DENOM_93_NEW 349 / DENOM_164_NEW 420 / IMPLICIT_ONLY_KEYS 256
$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0540-psy45/probe_key_delta2.py > tmp/qoder-executor-20260925-0540-psy45/k3.txt 2>&1; echo $?
0   TOTAL R=737 call_kwarg=701 ident_suffix=36 CLOSED True

# 三入口计数（rg 轨；scope 限定 ⇒ 天然排除 docs/ 两档与本 tmp 探针）
$ cd D:/code/psy-analysis && rg -c "key=" app.py ; rg -c "key=" src | awk -F: '{s+=$NF} END{print s" files="NR}' ; rg -c "key=" scripts | awk -F: '{s+=$NF} END{print s" files="NR}'
46 / 687 files=64 / 4 files=3
$ cd D:/code/psy-analysis && rg -o -N "key=" app.py src scripts | wc -l
737
$ cd D:/code/psy-analysis && rg -o -N "\\bkey[[:space:]]*=" app.py src scripts | wc -l        # 宽口径（锚 757 的口径）
758
$ cd D:/code/psy-analysis && git grep -oE "\\bkey[[:space:]]*=" bcb21f4 -- app.py src scripts | wc -l   # 同式回读 9/23 盘态
758                                                                                             # ⇒ 758 不漂，锚的 −1 在口径不在盘

# 键面 scope 自检（scripts 无 session_state 一词）
$ cd D:/code/psy-analysis && rg -o -N "session_state" scripts | wc -l
0

# 判据④：零码改
$ cd D:/code/psy-analysis && git status --porcelain && git diff --numstat
# 收工 10 行 porcelain ＝ 5 行他班 M ＋ psy44 的 2 行 ＋ 本班两档；git diff --numstat 与开工逐字同（本班 0 行）
```

## 7. 自证与边界

- **两跑跨 HEAD 稳定**：三档探针（psy2 键面／psy41 直访面／本档两探针）在 05:43 与 05:53 各跑一次，期间主班代提交了 `469ae07`（psy44 的 `s924-29`＋`s924-30`）且 `src/paper_writer/citation_in_text.py` 被兄弟班改出 `M 1/1`——`AST_DISTINCT_KEYS 164`、`KEY_KWARGS_TOTAL 701`、`CALLEE_ST 353`、`KEYLIT_ST_DISTINCT 265`、`DENOM 375/349/420`、`IMPLICIT_ONLY 256`、`R=737 CLOSED True` **两跑逐字同值** ⇒ 本档所有读数不依赖单一 HEAD。
- **零改动**：本班只新增本档＋同班 `s924-31` 的 1 档；`git diff --numstat` 开工 05:43／收工 05:5x 本班侧 0 行（列出的 6 行全属他班在途：`app.py`/`pytest.ini`/`requirements-lock.txt`/`src/questionnaire/exporters.py`/`tests/test_questionnaire_export_pdf_positive.py`/`src/paper_writer/citation_in_text.py`）；未 `add`/`commit`/`checkout`/`restore`。
- **同仓并发**（§十二）：`s924-29/30`（psy44）在本班窗口内推进，其两件的在途态已按班名对上、零接触、未误报"第二写手"。
- **判据与实测冲突一律收窄不判 failed**：判据①的"757 量级对拍"给成三口径（737/758/701）并逐条归因；判据③"清单 ≥1 个具名（app_mode）"给成 256 枚全清单，同时**点名 app_mode 的"只由 key= 注册"不成立**。
- 未跑任何 pytest（本单纯静态）；未取 psy 全量数（只读位，§四.2）。无库接触 ⇒ 不涉 `data/kaoyan.db` 空库陷阱（台账 215④）。
- 红线自查：全程只读 UI 状态键名，未触鉴权／凭据／资金／统计结论／医疗数值；`_pii_hash_all` 等键名仅作为**字符串清单元素**出现，本班未读其生产者语义。
- 建议出口（**不在本单处置面**，交主班裁）：① 把 14 枚跨文件成对硬编码并入 `src/ui/state_keys.py` 是架构改动（牵动 6 文件）；② 256 枚隐式键里 13 枚已被 tests 事实契约化，若要收口应先补登记面而不是先改名；③ 本档与 psy41 的档都属"登记不处置"，两档合计登记键面已达 420，统一常量表覆盖率 3.3%——是否继续维持"常量表"这条路，属 §十.2 那类需要 `--freeze` 式裁决的方向题。
