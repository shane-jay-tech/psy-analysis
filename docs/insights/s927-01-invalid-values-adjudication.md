# s927-01 · 问卷导入三条非法值静默计分缺陷：裁决材料（现网已改版，本单收窄为「已付成本核对＋未决剩余项」）

> 班次 `qoder-executor-20260927-1400-psy74`｜cwd `D:\code\psy-analysis`｜取数时刻 local **2026-09-27T13:49:55～13:53:47 +0800**（`date` 现取）
> 工作树现值：HEAD `11e536d`，`git status --porcelain` **12 行**（本班开工 13:45:23 与 13:43 取两次同值）
> 🔴 本班**零码改动**：未改任何计算代码／阈值／星标规则／golden 快照／期望卡，未写 `data/`（该层被 gitignore、无还原点），未提交。
> 卷宗要求的「统计域只出材料／不动数值」照办：本档里出现的每个数字都是**行数／格数／计数／源码字面量**，
> 凡涉及"哪个案更对"的结论一律写成**给人拍的判断题**（§四），本班不替统计签字。

---

## 一、锚点复核：卷宗的前提已经过期（否证留痕，不判 failed）

| # | 卷宗/锚点原述 | 磁盘实况（本班现取） | 处置 |
|---|---|---|---|
| 1 | 锚点路径 `zcode-bridge/outbox/20260925-120657-c47f.result.md` | outbox 查无此件，件在 `D:/code/zcode-bridge/done/`（10,348 B，mtime 09-25 16:51） | 按波次 19 共通指示 §3a 到 `done/` 取用，**内容原样可用**，不算缺陷 |
| 2 | 「三条非法值静默默认分缺陷需人工裁决，候选修法三选（执行手不自助）」 | **已由用户 2026-09-27 01:01 裁决并入库**：psy `6a12eb9`「越界作答不再当有效分数（r5 B1）」＋同批契约钉桩 `376e8c5`；台账 `D:/code/docs/decisions/2026-09-27-bridge-pending-approvals-r5.md:34/77` | 三案中的 **b) 与 c) 已同时落地**，**a) 未落地**（`import_cleaning.py:109-111` 仍是无校验线性变换，本班复算 `reverse_score(99,5,1) = -93.0`、`reverse_score(1e5,5,1) = -99994.0`）⇒ 本单实际待裁的是 §四 的剩余六问 |
| 3 | c47f §E2 读数：99 ⇒ 均分 **−44.0**；0 ⇒ **2.0**；"1e5" ⇒ **50002.0**；`detect_invalid_responses` ⇒ `False` | 同一输入在现 HEAD 复算（1-5 尺、Q1 为反向项）：`99 ⇒ mean 5.0 / sum 5.0`、`0 ⇒ 4.0 / 4.0`、`"1e5" ⇒ 4.0 / 4.0`，三例 `out_of_range_counts={"Q1":1}`；`detect_invalid_responses` 不传 `item_ranges` 时仍 `False`，传逐题项范围时 **True** | §E2 的三条"现网实况"读数**已失效**（改前实况已被修掉）。凡引 §E2 数字处一律标"改前"，本档新数全部现取 |
| 4 | 候选 c) 的代价描述：「最轻，但仍改变现网所有历史复算结果」 | 干净数据上是**恒等变换**：同一 `demo_projects/psychology_questionnaire_demo/data.csv`（sha256 `7b7b8971…`、`wc -l` 31 行＝表头＋30 例）过两套实现（现版 vs 改版前 git blob `194cfab9`），**维度得分 108 格中 0 格不等，最大绝对差 0.0**；`invalid_n` 两版同为 **3**（行 index `[4,11,27]`）、`valid_n` 同为 **27** | 该表述**过宽**：影响面 = **含越界单元格的那部分行/格**，不是"所有历史复算结果"。差集来源可机械界定（§三·c 的复算式） |

⚠ 另有一条在册外部实况与本单直接相关：HEAD 提交本身（`11e536d`，01:38:13）＝「demo 数据重造使'焦虑—自尊负相关'成立（r5 B4 甲案）」，
改了 `data.csv`(60 行)/`expected_analysis_cards.json`(12 行)/`WALKTHROUGH.md` ＋新增生成器 `scripts/gen_demo_questionnaire_data.py`（74 行，`seed=20260927`，sha256 `84892826…`）。
⇒ demo 现在是"为让结论成立而构造"的样例，**本档不据 demo 下任何统计结论**，只用它做"两套实现的恒等性"机械对照。

---

## 二、影响矩阵（三案 × 六个影响面；「已付」＝6a12eb9 已经花掉的代价）

图例：🟢 无影响｜🟡 局部/条件影响｜🔴 改变结论面｜✅ 已落地｜⬜ 未落地

| 影响面 | a) `reverse_score` 前按字典量尺校验并抛错 | b) `detect_invalid_responses` 增越界占比判据 | c) `compute_dimension_scores` 侧越界置 NaN |
|---|---|---|---|
| **无效样本数 `invalid_n`** | 🟢 不碰判据（抛错即中止，压根不出数） | 🔴✅ **已付**：新增"行含任一跃界即整行无效"（逐题项范围，`import_cleaning.py:184-192`）；不声明维度 ⇒ 🟢 完全 no-op（`item_ranges` 只由 `dimensions` 现取，`:219-231`） | 🟢 不改行级判定，只改**参与均分的格数** |
| **历史复算（维度分）** | 🟡 仅让"含越界的反向题"从"错答"变"报错" | 🟡 间接：无效行被整行剔除 ⇒ 历史报告的 N 变小 | 🔴✅ **已付但条件性**：数据不含越界 ⇒ 恒等（demo 108 格 0 差）；含越界 ⇒ 该行 mean/sum 变（实测 B 案：越界 1 枚 ⇒ `s_mean` 由"含 −93"变"仅由 Q2 贡献"） |
| **下游统计输入面（α／相关／检验）** | 🟡 阻断式：错数据不再进下游 | 🔴 改变进入下游的**样本集合**（不是权重）⇒ α／r／p 的 N 与个案都变 | 🔴 改变进入下游的**个案内取值**（越界格转缺失 ⇒ 均值成"有效格上的均值"，`min_count` 语义未改） |
| **契约／测试面** | 🔴 见 §三·a 清单（`_现网实况` 钉桩、默认参数错答钉桩会转红） | 🟡✅ 已付：`test_out_of_range_pipeline_20260927.py`（新增）、`test_e2e_qimport_upload.py:160` `_SUMMARY_KEYS` 三键 | 🟡✅ 已付：c47f 的三条实况钉桩按新口径翻转（6a12eb9 内 49 行改动） |
| **UI／交付包播报** | 🔴 面板 `questionnaire_import_panel.py:155-166` 无 try/except ⇒ 异常直穿成 Streamlit 红框 | 🟡✅ 日志多一步「越界值处置」（`:264-274`），随交付包 `data_cleaning_log` 出（`deliverable_center_panel.py:76-81`） | 🟡 同上一条（置空数写在同一步，`:293-301`） |
| **可回滚性** | 🟢 单函数、2 处调用点 | 🟡 新增可选参数，向后兼容（不传即改前行为） | 🔴 无开关：现网默认路径**已经改变**，回滚＝revert 提交 |

---

## 三、逐案显式破坏面清单（每条都给复算式；行号＝HEAD `11e536d` 工作树现值）

### a) `reverse_score` 前量尺校验并抛错 —— ⬜ 未落地，破坏面比看起来大

1. **同名不同物的两个 `reverse_score`**：`src/questionnaire/import_cleaning.py:109`（Series 版，2 处调用）与
   `src/data/transforms.py:98`（DataFrame 版，签名 `(df, items, scale_max, scale_min=1, suffix="_R")`）。
   `transforms.py:126` 是无校验 `total - to_numeric(...)`。**在 questionnaire 那份加校验＝只覆盖一半**；
   两份语义不同（Series↔DataFrame），统一签名会破 `tests/test_data_transforms.py:67/77` 的调用形状。
   复算：`grep -n "def reverse_score" src/` → 2 处（本班 13:47 现取）。
2. **面板异常面**：`src/ui/questionnaire_import_panel.py:155-166` 的按钮处理体没有 try/except
   ⇒ 抛错会直穿成 Streamlit 异常框（不是可解释的告警）。
   复算：`grep -n "try:" src/ui/questionnaire_import_panel.py` → **只有 `:50` 一枚**（在 `_render_upload` 里），
   清洗分支 `_render_cleaning`（`:132`）零命中。
3. **既有钉桩会转红（属预期红，但要一起改写）**：
   `tests/test_questionnaire_boundary_and_invalid_values.py:84`（`test_reverse_score_with_wrong_scale_args_is_a_silent_wrong_answer`，
   钉的就是"1-6 尺误用默认参数 ⇒ `[5.0, 0.0]`"这种静默错答）；同文件 `:164` 的 B1 新口径钉桩（99 置空后反向不再看到越界值）。
   复算：本班 13:53:47 三件合跑 **59 passed / 0 failed**（`test_out_of_range_pipeline_20260927.py`
   ＋`test_questionnaire_boundary_and_invalid_values.py`＋`test_demo_project_validation.py`）——这是 a) 的**改前基线**。
4. **越界定义本身要新代码**：`reverse_score` 拿不到字典（只收 `max_score/min_score` 两个标量），
   且 `ScaleDimension` 的量尺是**维度级**、同题项跨维度冲突时现实现"取交集＋warning 留痕"（`:224-229`）；
   在反向处再判一次越界＝第二套阈值来源，与本波 44a0 卷宗点名的"阈值三处各写一份"同族风险。
5. **收益面（诚实列出）**：唯一能拦住"合法但荒谬"数据的是它——c47f E2 第 5 行「字典声明缺失码撞合法值」
   （`missing_codes=("3",)` 于 1-5 尺）只在 `Codebook.conflicts()` 声明级拦，运行级无人拦（本班复算：`missing_codes`/`conflicts` 全仓 grep → **16 命中全在 `src/questionnaire/data_dictionary.py`，`src/ui/` 与 `app.py` 0 命中** ⇒ 字典声明从未参与导入运行时判据）。

### b) 越界占比判据 —— ✅ 已落地，但覆盖面被上游分桶卡住（本班现取的两处背离）

6. **口径背离**：行级判据遍历 `item_columns`（`:240` `for _col in item_cols:`），而 `item_columns` 由
   `_is_likert_column` 决定（`:85-106`：要求 `max ≤ 10` 且唯一值 ≤ 10）。含 99／1e5 的列**恰好因此被降级成人口学列**
   ⇒ 越界值把"发现自己的那只眼睛"关掉。实测（13:50:49，8 行×3 题合成表，Q1[0]=99）：
   `item_columns=['Q2','Q3']`、`demographic=['Q1']`、summary `out_of_range_cells=0`（原始面报 0）、
   而 `compute_dimension_scores(..., out_of_range_counts=)` 按 `dim.items` 遍历，仍报 `{'Q1': 1}`、
   summary `out_of_range_cells_after_filter=1` ⇒ **同一份数据里越界"发生了但原始口径看不见"**。
   B1 的评审 F-002 为消"重复计数"引入的单一口径，其代价正是这里：`out_of_range_cells=0` 与
   `out_of_range_cells_after_filter>0` **能同时成立**（现有钉桩 `tests/test_out_of_range_pipeline_20260927.py:88`
   `assert res.summary["out_of_range_cells_after_filter"] == 0` 只钉了反方向，拦不住这种）。
7. **`invalid_n` 会被分桶漂移反向挪动**：实测干净表 3 题项列 ⇒ `invalid_n=0`；把 Q1 塞 1 枚 99（Q1 因此降级）
   ⇒ `invalid_n=1`，而命中的是**既有**的 std=0/众数判据（行 6 上 Q2==Q3，在 2 列时 std=0、3 列时非 0）。
   ⇒ "增判据"与"改列集"两件事耦合：越界值先污染分桶、分桶再改变原有判据的输入 ⇒ 无效样本数的变化方向**不单调**，不能用"＋越界行数"预估。
8. **维度分列缺失 ⇒ 行级判据静默失明**：`item_ranges` 的键按 `dim.items` 声明，但计数与判据只在 `item_columns` 里取交集；
   维度里写了不存在的列（`compute_dimension_scores:131-132` 直接 `continue`）不报错，
   这与在册 C6（`docs/insights/psy-data-dictionary-20260925.md:47`）同源，本班实测：`reverse_items=["Q9"]`（Q9 不存在）
   ⇒ 不抛错、`invalid_n` 与不写时同为 3、`out_of_range_cells=0`。
9. **两条现网路径没接判据**：分析运行器 `src/analysis/runner.py:926` 走 `handle_missing`，
   `src/analysis/data_quality.py` 全文件**无 min/max／量表／越界概念**（grep 零命中）；
   顶部「数据上传」（`src/ui/upload_state.py:32` `session_state["df"]`）与问卷清洗产物
   （`session_state["questionnaire_cleaned_result"]`）是两个键，快捷入口（信度/效度/相关，
   `src/ui/quick_entries.py:242-276`）读前者 ⇒ b) 对下游 α／r 的影响**不是自动接线**，
   只有当人把清洗结果导出后再上传才会传导（这条否证了锚点里"连带影响下游输入面"的自动性表述，量级仍需人裁）。
10. **均值插补仍会把非法值喂进下游**：`data_quality.py:91` `fillna(result_df[col].mean())`，
    列均值含越界即被放大（c47f 实测 `[1,5,99999] → 填 33335.0`，本班 13:4x 复核该行为未变：源码逐字未动，
    `git log --oneline -- src/analysis/data_quality.py` 只有初始化提交 `ec45485`；文件 sha256 `cc525a13…`／300 行）。

### c) 计分侧置空 —— ✅ 已落地，语义副作用

11. **`*_sum` 失去量程语义**：置空后 sum 是"有效格之和"，与量表总分的通常含义不同；
    实测 99 例：`sum=5.0`（只有 Q2 贡献）。改后 `mean` 仍可读、`sum` 不再可比 ⇒ 下游若用 `*_sum` 当量表分即被静默改口径。
    复算：`sum` 列由 `dim_df.sum(axis=1)`（`:146`）产出，`min_count` 未设 ⇒ 全缺失行给 0.0 而非 NaN。
12. **反向题尺给错 ⇒ 整列静默清空（本班实测新行为，改前是"反向值全错但仍进均分"）**：
    对 1-6 尺的题声明 `min=1,max=5` ⇒ 6 被判越界，实测 `oob_counts={'Q6':3}`、`mean=4.0`（只剩 1..5 生效）。
    改前同输入 `mean=2.5`（6 被反向成 0）。**两版都不报错**，只有一版留计数 ⇒ 播报依赖 `out_of_range_counts` 是否被展示。
13. **无维度声明即整体 no-op**：不声明维度 ⇒ `compute_dimension_scores` 不被调用、`item_ranges` 为空 ⇒
    越界值照旧被反向并平均（实测 13:50:49 F 案：`dimensions=None` 时 `invalid_n=20/20`、`oob_cells=0`，
    且 99/1e5 那批行**不因此被剔**，全表无效是既有 std/众数判据在单列时的效应）。

---

## 四、剩余待裁的判断题（每条：两难 ＋ 可复算读数；本班不下统计结论）

> 统一复算底座（三套合成数据，均为个位数人造值，`data/` 零访问）：
> `D:\code\tmp\qoder-executor-20260927-1400-psy74\probe_s92701.py`／`probe2_s92701.py`／`probe3_s92701.py`／`ab_s92701.py`，
> 解释器 `D:\code\psy-analysis\.venv\Scripts\python.exe`，跑时 13:49:55～13:53:47。

| 编号 | 要人拍的问题 | 选「做」的后果 | 选「不做」的后果 | 复算读数 |
|---|---|---|---|---|
| **Q1** | 是否补 a)（反向/计分前的量尺校验，抛错还是告警）？ | `transforms.py` 那份要不要一起改＝是否统一签名（破 2 条既有测试形状）；面板需同批加异常处置，否则红框 | 越界值仍能在"未声明维度的列"上被静默平均；`Codebook` 的 `missing_codes` 声明继续零读者 | §三·a 全清单（1–5） |
| **Q2** | `_is_likert_column` 把含越界的列降级成人口学，算不算缺陷要单修？ | 修了才谈得上"判据覆盖面"；但 `_is_likert_column` 被多处复用（10 处命中），改判据＝改列集＝改 `invalid_n` | 保留现状＝b) 在真实脏数据上可能**一条都不触发**，且 summary 报 0 | §三·6/7（实测 `oob_cells=0 ⇄ after_filter=1/2`；`invalid_n` 0→1） |
| **Q3** | 越界判据要不要接到分析运行器／`handle_missing`（R2 工作区路径）？ | 需在 `data_quality.py` 引入"量尺"概念＝新参数面；直接影响下游 α／r 的输入个案 | 保持"问卷导入面严、分析面宽"的两级口径；传导只靠人导出再上传 | §三·9/10 |
| **Q4** | 越界置空后 `*_sum` 与 `mean` 的语义谁为准？ | 若视 `sum` 为量表总分 ⇒ 需 `min_count` 或改列名（动导出面） | 历史报告的 `*_sum` 与新报告不可比；c47f 的"实况钉桩"已按现行语义翻转 | §三·11（实测 `sum=5.0`／108 格 0 差） |
| **Q5** | 维度声明与真实量表不符（1-5 声明吃 1-6 数据）时，静默置空是否可接受？ | 改成抛错＝Q1 的一个具体子案；改成告警＝需新日志步 | 用户填错一个数字 ⇒ 一整列被清空且只在日志里留计数 | §三·12（实测 `oob_counts={'Q6':3}`） |
| **Q6** | 「越界值处置」这条日志文案/口径要不要再改（现在依赖列分桶）？ | 文案是逐字钉桩（`test_questionnaire_import_panel_render.py:250` 区），改文＝改测试；且该步随 `raw_out_of_range` 是否为空**条件性出现**（实测干净表 4 步、脏表也 4 步，因 Q1 被降级） | 交付包里"看不出越界发生过" | §三·6＋`export_cleaning_log`（`:326-347`） |

---

## 五、推荐（工程排序，非统计结论）与最强反对意见

**推荐·分阶段（卷宗口径"先校验后判据"，按磁盘实况重排）**

- **第 0 阶段（只补观测，零判据变更）**：让越界计数**不依赖分桶**——统计面从 `item_columns` 改按
  "维度声明 ∪ 列集"取（属计数面，不动任何行的处置），并把 `out_of_range_cells_after_filter > 0` 而
  `out_of_range_cells == 0` 这种背离态显式播报。收益：Q2/Q6 的判断从此有数可依；代价：日志步出现条件变。
- **第 1 阶段（先校验）**：在 `compute_dimension_scores` 内**声明级**校验（维度 min/max 与列实测范围明显冲突时
  记 `logger.warning`＋在 summary 落一条"疑似量尺声明错误"），**不抛错**；同时决定 Q1 的抛错口径是否覆盖
  `src/data/transforms.py:98` 那份。收益：拦住 §三·12 这类"填错一个数→整列清空"。
- **第 2 阶段（后判据）**：再谈"越界是否进无效样本数"（Q2/Q3）与是否给 `handle_missing` 接量尺（Q3）。
  这一段**必然改动统计输入面**（N 与个案），按卷宗红线交人工签字，本班不预判。

**最强反对意见（针对上面的排序，写足）**

1. **"零判据变更"是幻觉**：第 0 阶段改的是 `raw_out_of_range` 的覆盖面，而它同时喂 summary 与日志；
   若同时有人把"越界行剔除"接成以该计数为准（`:250` 已传 `item_ranges`），观测改动会顺带改判据＝一次改动跨两阶段，
   违反"先观测后判据"的分档初衷。反对者会主张：要么把计数与判据**拆成两个独立来源**再谈观测，要么一次改完。
2. **第 1 阶段的 warning 路径在这个仓里已被证明不解决问题**：`:228` 的冲突 warning 早已存在（跨维度不同尺取交集），
   而本次实测显示它**没有阻止**任何静默行为 ⇒ 再加一条 warning 属"把同一剂药加第二遍"，真正缺的是 Q1 的硬拦截或字典声明上运行级读者。
3. **分阶段会拉长"两套实现并存"的窗口**：`reverse_score` 两份、清洗两套（问卷导入 vs 清洗向导 `winsorize`）、
   两条数据路径（R1/R2）并存期间，任何一份报告的口径都可被质疑；反对者主张先做"路径归一"（Q3），
   否则校验加得越细，越容易只覆盖一条路。
4. **统计侧最硬的一条**：b) 已经上线＝`invalid_n` 的语义已经变了，此时再"补观测"等于**在动过判据之后才补证据**。
   若需要给出"B1 改动前后 α／r／N 的历史对照"，那是统计数值结论域：本班只交出**差集界定式**
   （差集＝含越界单元格的行；干净数据上恒等，demo 108 格 0 差），具体对照须人工放行后在受控数据上跑。

---

## 六、本班零改动自证

- 写动作只落在 `D:\code\tmp\qoder-executor-20260927-1400-psy74\`（4 份探针 .py ＋ 1 份 `import_cleaning_preB1.py` 只读副本，
  其 `git hash-object` = `194cfab97c7413717ee64b90c6fe199e9c9207cf` = `git show 6a12eb9^:src/questionnaire/import_cleaning.py`，证明副本未被改）。
- 本档写入路径 `docs/insights/s927-01-invalid-values-adjudication.md`（本班唯一入库类产物）；除此之外
  `git status --porcelain -- src/ tests/ demo_projects/ data/ pytest.ini app.py` 收班复点应与开工 12 行一致（见 result §验收）。
- 未跑全量套件（并发窗约束）；定向面只跑 3 个在册测试文件（59 passed）。
- `data/` 整层零访问（探针输入全部为仓内 git 跟踪的 demo CSV ＋ 内联合成表）；未开库、未建快照。
- 未 `git add`／`commit`／`stash`／`checkout`／`restore`；未动外部在途 12 枚脏件（`app.py`／`pytest.ini`／
  `requirements-lock.txt`／`src/analysis/{__init__,cfa,result_card}.py`／`src/output/interpretation.py`／
  `tests/test_cfa_sem_golden.py` ＋ 4 枚未跟踪件）的内容，仅作状态读数引用。
