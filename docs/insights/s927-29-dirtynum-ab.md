# s927-29 · dirtynum A＋B 施工记录（波次 43 写位班，2026-09-28）

档位＝代码写位。班名 `qoder-executor-20260928-0300-psy87`。开工 HEAD `fd78891`（主班最后入库）。
方案来源：`docs/insights/psy-dirtynum-rescore-material-20260921.md`（s922-05 材料单）§四 A/B ＋ §五 三条测试点。
**只落 A＋B；C 案（`models.py` 裸强转静默回退 0）属改数据统计口径＝红线，本班未动、未背书。**

## 一、两处施工（生产码共 19 增 4 删，两处各 ≤12 行）

| 处 | 文件:行（施工后） | 行数 | 做了什么 |
|---|---|---|---|
| A | `src/ui/literature_review_panel.py:760-772`（`_materialize_items`） | 12 行（含 docstring） | 列表推导改逐条 try；`ValueError`/`TypeError` ⇒ **跳过该条并累计**，末尾**恰好一条** `st.warning`（点名条目与原始异常）。好条目不再被脏条目连坐 |
| B | `src/ui/literature_review_panel.py:120-128`（主入口 rescore 段） | 8 行 | 调用包 `try/except Exception/finally`；失败降级为**一条 `st.error`**，`_lr_pending_rescore = False` 落在 **`finally`** |

B 的关键是 `finally`：材料单 §一 已证实现状「`try` 都不带 ⇒ 抛出即跳过落开关 ⇒ 每次 rerun 重新调用
LLM 打分器（永久重试，既逐帧红又逐帧烧积分）」。只加 `try` 不加 `finally` 的半修写法会被
`test_pending_flag_reset_is_second_statement_with_no_try_guard`（AST 结构钉桩）当场判红。

**未改动**：`_do_relevance_rescore`（`:198` 助手本体）保持「失败向上抛」的原语义 ⇒ s920-13 与 s922-105
里那两条「助手层异常逃逸且不写半成品」的钉桩**继续绿**，兜异常的位置只在主入口消费侧。

## 二、配套测试（3 条新测试点 ＋ 5 条在册钉桩翻正，零删例）

新增在 `tests/test_literature_review_panel_helpers.py`：

1. `test_materialize_one_dirty_row_keeps_the_good_ones_and_warns_once` —— §五 测试点 1（[好,脏,好] ⇒ 2 条＋1 告警）
2. `test_materialize_all_dirty_rows_yields_empty_list_with_single_warning` —— §五 测试点 2（[脏,脏] ⇒ `[]`＋**只一条**告警）
3. `test_main_entry_rescore_failure_degrades_to_one_error_and_clears_flag` —— §五 测试点 3（主入口不抛＋`st.error` 一次＋开关必为 False）
4. `test_materialize_non_dict_element_still_raises` —— A 案**边界否证**（只兜 ValueError/TypeError，非 dict 照旧抛；防将来把 except 放宽成 `Exception`）
5. 另把 s920-13 的 ④ 只钉不改桩 `test_materialize_coerces_numeric_strings_but_skips_garbage` 按注释翻正（改断言、留数字串对照半段）

在册冻结桩按其**文件头自述的出口**翻正（「A/B 合入时本档必须主动变红并按注释逐条翻正，禁止悄悄删桩」）：

- `tests/test_lr_dirty_number_frozen_pins.py`：② 两条 ＋ ③ 两条，共 4 条翻正
- `tests/test_lr_list_coercion_twins.py`：真值表 panel 行 dirty 格 `True→False`（非 dict 格仍 `True`）

## 三、红/绿留档（三态都在 `D:\code\tmp\qoder-executor-20260928-0300-psy87\`）

```
改前基线（生产码未动、测试也未动）    56 passed          s927-29-baseline-pre-edit.txt
改前红（测试已翻正＋新增，生产码未动） 9 failed, 51 passed  s927-29-RED-before-implementation.txt
改后绿（A＋B 落码）                   60 passed          s927-29-GREEN-after-implementation.txt
AppTest 端到端族（B 触及的主入口）      8 passed           s927-29-GREEN-apptest-family.txt
其余引用面板的定向件（7 个文件）        1 failed, 65 passed  ← 唯一那枚红是既有红，见 §五
```

9 枚红态逐条＝2 条新测试点 ＋ 1 条主入口新测试 ＋ 4 条冻结桩翻正 ＋ 1 枚真值表格 ＋ 1 条 ④ 桩翻正。
（新测试点 4「边界否证」改前即绿＝它钉的是"A 案不该放宽到 Exception"，属对照刀，不计入改前红。）

AppTest 族必须带沙盒环境变量才跑（`LITERATURE_FEED_DATA_ROOT` 是 import 期常量，monkeypatch 无效）：

```
LITERATURE_FEED_DATA_ROOT=D:/code/tmp/qoder-executor-20260928-0300-psy87/feed_root \
  .venv/Scripts/python.exe -m pytest tests/test_lr_rerun_apptest.py -q -p no:randomly   → 8 passed
```

## 四、红线自查（为什么这不算「统计数值与效应量结论」）

- 改的是**脏值处理面**（解析失败怎么办），不解析、不计算、不判定任何统计量或效应量；
  未 import、未改动 `src/analysis/*`，未跑任何统计脚本。
- **零数据写盘**：A 只读入参 dict 列表（新桩 `test_materialize_does_not_partially_mutate_the_session_list_when_it_raises`
  正面钉住「不改写 session 列表」）；B 只把 `lr_state["literature_items"]` 的写回留在成功路径上。
- 在册缺陷 `semopy` 缺列致 `chi2_p`/`srmr`/`rmsea_ci` 假 0 与 `result_card.py:1162-1164` 把 SRMR 送进
  `effect_sizes`（兄弟单 s927-10 查出）——**本班未顺手修、未碰其白名单**，`result_card.py` 仍是别人的在途件。
- 已入库金样/效应量读数：**未改变**。本班没动任何 `*golden*` 件，`_materialize_items` 全仓只有一个调用方
  （主入口 `:131`，grep 实测），其产物只进 UI 渲染，不进分析或效应量链路。

## 五、顺带发现（登记，不在本班范围）

1. 🔴 **s922-105 的一条冻结桩判据是恒真的**：旧 `test_main_entry_block_flag_stays_true_when_real_rescore_raises`
   断言的是外面那份 `session` dict，而 `_SessionSt.__init__` 做的是 `dict(initial)` **拷贝** ⇒
   「开关仍为 True」与代码实际改没改无关。本班翻正时把断言改读 `fake_st.session_state`（真身）才使这条判据第一次有效。
   同族先例＝`tests/test_cfa_sem_golden.py:269` 的 `* 0` 恒真断言。**只登记，未扩大改动。**
2. **既有红（与本班无关）**：`tests/test_export_gate_global_scan.py::test_all_download_buttons_accounted_for`
   红在 `src/ui/questionnaire_panel.py` 有 `st.download_button` 却不在 `WHITELIST_EXPORTS`。
   该件 ` M`／`??` 都不是（clean@HEAD），本班一行没碰它；扫描只按 `st.download_button` 行号，
   `literature_review_panel.py` 本就在白名单里 ⇒ **HEAD 版同红**，别归因给 s927-29。
3. **孪生漂移未闭合**：`src/literature_review/search.py:230`（爬虫/检索直转）与 `notes.py:157` 仍是
   「一条脏 ⇒ 整表弃」。s922-05 已警告「只修文献侧会出现文献容错、笔记/检索整表弃的新不一致」，
   本班范围只有 panel 侧 ⇒ 另开单。
4. 主入口 `render_literature_review` 现在只有 1 个 `try`（结构钉桩已把「多于 1 枚」判红）；
   面板内其它外部调用面（检索/导入/综述）仍是「一处异常整页红」，属 s922-05 遗留问题 4，未普查。
