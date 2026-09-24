# psy：method_catalog「别名集中」声明 vs 各层私有别名表 —— 裁决材料

- 信箱单：`s923-45`（卷宗命名产物日期 20260923，**实际执行与全部读数取自 2026-09-24 14:0x**，HEAD `2a06659`）
- 执行位：`qoder-executor-20260924-0955-psy26`（psy **文档位**，授权只到 `docs/decisions/**`＋`docs/insights/**`）
- 性质：**只读普查＋设计稿**。本档零产码改动（`src/`、`tests/` 一字未动），选哪案属人工。
- 复算配方：档内每条 `$ 命令原文` 均可在 `D:\code\psy-analysis` 下直接重跑；AST/探针脚本留在 `tmp/psy26/`（`tmp/` 已 gitignore，`.gitignore:29`），不落生产树。

---

## 〇、一页结论

**「哪个是权威别名表」这个问题本身要先收窄**：`apa_tables` 与 `apa_figures` 看着同族，实际处在**两种不同制度**下，因此"集中 vs 保留"不是对称二选一。

| 事实 | 读数 | 含义 |
|---|---|---|
| `apa_tables.generate_tables_from_card` 头部**已经** `resolve_method_id` | `src/output/apa_tables.py:765,768` | 该文件分支里的别名成员**永远命中不到＝死码**（实测 4 个：`:783/:805/:857`） |
| `apa_figures.generate_figures_from_card` 头部**不解析** | `src/output/apa_figures.py:562 method = card.get("method", "")` | 该文件分支里的别名成员**正在承重**（3 个：`:611/:625/:695`），删掉即回归 |
| figures 的分组大多**只列 canonical** | 9 个别名 id 落在未覆盖区 | 卡片带 legacy id 时**静默不产图**（今天就在漏，见 §三 3.1 表） |
| `result_card._CARD_BUILDERS` 是**全仓最大私有别名表** | 44 键里 14 个是目录别名键（`:1355-1400`） | 体量比卷宗点名的两文件大一个数量级，且被快照测试逐字钉死 |
| **执行层自己也在用别名当键** | `runner.py` 48 个 `@_register` 键中 6 个是 catalog 别名（`:156/:231/:403/:523/:549/:582`） | "集中"不只是清理展示层——**第三张别名表在执行层**，且它决定 `test_type` 的实际取值（§3.5） |

**推荐排序（仅排序，选择权在人工）**：

1. **案 C｜分层收口（推荐）**：先做"零行为风险"的 **16 行**（删 tables 4 个死成员＋给 figures 加 resolve 并把它的 3 个承重别名交给 resolve＋E 类 8 点改双向安全写法），`_CARD_BUILDERS` 与执行注册表**都不动**；**同时**把 figures 的静默丢图面用看守测试钉成显式豁免清单。改动面小、可分两笔独立回退、不翻快照红。
2. **案 A｜全量集中**：把 19 个含别名点/88 个别名字面量全部收敛到 catalog。收益是单一事实源成真，代价是**必翻** `test_result_card_registry_snapshot.py` 的 4 处快照断言与 `test_result_card_v2_methods.py` 的 6 个参数化用例（这些正是"把现状钉成断言"的两笔一体形态），且触导出面。
3. **案 B｜保留私有表＋只加看守**：生产码 0 行，但**等于承认 `method_catalog.py:1-7` 的 docstring 与现实不符**，要顺手把那句声明改成"仅执行层与卡片层集中，展示层允许私有表"。成本最低，代价是把"防各层自维护别名表"这条设计意图正式放弃。

⚠️ 三案**都**含一个与"集中"无关的独立缺陷修复项：figures 的 9 个别名静默丢图（§三 3.1）。它与选案解耦，建议单列。

---

## 一、前提复核（卷宗锚点与派单说法逐条实测）

| # | 卷宗/派单说法 | 实测命令 | 读数 | 结论 |
|---|---|---|---|---|
| 1 | `src/analysis/method_catalog.py:7`「maintaining its own alias list.」 | `$ sed -n '1,8p' src/analysis/method_catalog.py` | 第 7 行逐字为该句，属模块 docstring「Keeping that translation here prevents each layer from maintaining its own alias list.」的一部分 | **成立，0 漂移** |
| 2 | `src/output/apa_tables.py:783` 的三元组 | `$ sed -n '783p' src/output/apa_tables.py` | `    elif method in ("pearson_corr", "pearson_correlation", "spearman_corr"):` | **成立，逐字** |
| 3 | `src/output/apa_figures.py:611` 的四元组 | `$ sed -n '611p' src/output/apa_figures.py` | `    elif method in ("repeated_anova", "repeated_measures_anova", "mixed_anova", "paired_ttest"):` | **成立，逐字** |
| 4 | 派单提示：`method_catalog.py:70-71` 有 card 别名复用，"仅 binary 有专用卡"式说法要小心 | `$ sed -n '68,71p' src/analysis/method_catalog.py` | `:68 logistic_regression card=logistic_regression`／`:69 binary_logistic card=binary_logistic`／`:70 ordinal_logistic card=logistic_regression`／`:71 multinomial_logistic card=logistic_regression` | **成立**（70/71 确为复用）。但**说法要再修一层**，见下方"派单说法不足处" |
| 5 | 卷宗隐含前提：私有别名点主要是这两处 | AST 轨普查 | 全 `src/` 125 个字面量点/27 文件，其中 **51 点含别名字面量、88 个别名字面量** | **否证（低估）**：两文件只是冰山一角，最大一处是 `result_card.py:1355` 的 44 键注册表 |
| 6 | 隐含前提（卷宗"防止各层自维护别名表"要收口的对象是冗余）：别名＝历史遗留 | `runner.py` 注册键普查 | 48 个 `@_register` 键里 **6 个是目录别名**：`repeated_anova:156`、`chi_square_independence:231`、`mcdonald_omega:403`、`ave:523`、`discriminant_fl:549`、`discriminant_htmt:582`；`validity.py:170/224/300` 直接把 `test_type` 写成别名 | **否证**：这些别名是**现役执行 id**，不是待清理的残留（详见 §3.5） |

**派单说法不足处（引本节前必读）**：把"仅 binary 有专用卡"改成事实句要两步——`_CARD_BUILDERS` 里 `binary_logistic` **有键**，但它的值是 `_build_logistic_regression`，与 `logistic_regression` **共用同一个 builder 对象**（`$ .venv/Scripts/python.exe tmp/psy26/probe.py` 第 5 节）；`ordinal_logistic`/`multinomial_logistic` 无键、经 `card_id` 回落到同一函数。⇒ 准确说法是「**四型 logistic 共用一个卡片实现；binary 只有专属键、没有专属实现**」。连带一条：`validate_method_contracts({}, _CARD_BUILDERS)` 现值 **0 条错误**（`:139-155` 只查"声明的 card 目标是否注册"，查不出"目标只是别名复用"），所以**别拿契约校验 0 错当"卡已专用"的证据**。

---

## 二、双轨普查与差额解释（§九-3 要求：两轨对到位并解释差额）

### 2.1 正则轨（卷宗点名的式子）

```
$ rg -n 'pearson_correlation|repeated_measures_anova|mann_whitney_u' src/
（14 行 / 8 个文件）
src\output\apa_tables.py:783,811
src\output\apa_figures.py:611
src\upstream\semantic_alignment.py:63,94
src\analysis\runner.py:161
src\analysis\result_card.py:1360,1364,1373
src\utils\usage_logger.py:10
src\analysis\anova.py:304
src\analysis\method_catalog.py:45,54,58
```

真·私有别名点只有 **4 处**（`apa_tables:783/811`、`apa_figures:611`、`result_card:1360/1364/1373` 属同一注册表）。其余 10 行是假阳/无关：`runner.py:161` 与 `anova.py:304` 是**函数名** `repeated_measures_anova(...)`、`usage_logger.py:10` 是 docstring 举例、`method_catalog.py` 3 行是权威表本身、`semantic_alignment.py:63/94` 是自然语言关键词表（§三 3.3）。

### 2.2 AST 轨（补正则的三重盲区）

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/psy26/ast_census.py
catalog: known_total=75 canonical_total=52 alias_total=23
AST hits=125  files=27  含别名的点=51  别名字面量总数=88
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/psy26/classify.py
[A_分支匹配] 命中 19，含别名 6，文件 2
[B_注册表键] 命中 30，含别名 20，文件 17（别名键共 50）
[C_语义词表] 命中 11，含别名 5，文件 1
[D_其它集合] 命中 57，含别名 12，文件 14
[E_单点比较] 命中  8，含别名  8，文件 4
```

方法：装载真实 catalog（`canonical_id_map()` 得 75 个 id），对 `src/**/*.py`（排除 `method_catalog.py` 自身）AST 遍历，凡 `Tuple/List/Set/Dict键` 里有 **≥2 个已知 method id** 或 `Compare` 右侧是**别名字面量**即记点。

**差额解释（125 vs 14，必须两轨都跑）**：
1. 正则轨只按卷宗挑的 3 个串扫，而 catalog 有 **23** 个别名（`factorial_anova`/`rm_anova`/`mixed_effects`/`omega`/`ave`/`discriminant_fl`… 全未入式）；
2. 正则轨看不见**以别名为键的查表**（`i18n.py:14`、`guardrails.py:16`、`keyword_dict.py:6` 这类 dict 键）与**单点 `==` 判别**（`interpretation.py:478`、`defense_qa.py:235`）；
3. 反向也要解释：正则轨的 14 行里 10 行是假阳（函数名/docstring/权威表自身）。
⇒ **凡"全仓多少处"式判据，单轨必然给出错数**；本档的权威口径是 AST 轨的 125/51/88，正则轨读数只作对照。

---

## 三、全清单与逐点裁决

### 3.1 A 类·分支匹配（19 点，其中含别名 6 点）⇒ **本族核心，逐点定夺**

`apa_tables.py`（头已 resolve ⇒ 别名成员＝死码）：

| 点 | 字面量 | 别名字面量 | 实测判定 | 裁决 |
|---|---|---|---|---|
| `:783` | `pearson_corr, pearson_correlation, spearman_corr` | `pearson_correlation` | resolve 后必为 `pearson_corr` ⇒ 该成员**永不命中** | **删（纯死码）**；保留 `spearman_corr`＝**刻意的表分组**（catalog `table_group` 正是 `pearson_corr`，见 `:45-46`） |
| `:805` | `chi_square, chi_square_independence, chi_square_gof` | `chi_square_independence` | 同上，死成员 | **删死成员**；`chi_square_gof` 是独立 canonical，属分组语义**保留** |
| `:857` | `hlm, hierarchical_linear_model, mixed_effects` | 后两个 | 均 resolve 到 `hlm` ⇒ **两个死成员** | **删**（该分支可缩成 `== "hlm"`） |
| `:793/:799/:811/:817/:826/:835/:847/:870` | 全 canonical | 无 | 纯分组语义 | **保留**（它们表达"多种方法共用一种表式"，catalog 的 `table_group` 已能承载 ⇒ 长期可改走 `get_table_route_group`，属案 A 范围） |

`apa_figures.py`（头不 resolve ⇒ 别名成员＝承重）：

| 点 | 字面量 | 承重别名 | 裁决 |
|---|---|---|---|
| `:611` | `repeated_anova, repeated_measures_anova, mixed_anova, paired_ttest` | `repeated_anova`（＋ `mixed_anova`/`paired_ttest` 是分组） | 别名交给 resolve；**分组语义保留** |
| `:625` | `two_way_anova, factorial_anova` | `factorial_anova` | 同上 |
| `:695` | `efa, exploratory_factor_analysis` | `exploratory_factor_analysis` | 同上 |
| `:565/:580/:596/:639/:654/:668/:681/:708` | 全 canonical | 无 | **保留，但它们是静默丢图源**（下表） |

**独立缺陷（与选案解耦，建议单列一批）**——figures 的分支只列 canonical，卡片 `method` 是 legacy 别名时**不产图且零告警**：

| 分支 | 漏掉的别名（实测 `tmp/psy26/probe.py` 第 2 节） |
|---|---|
| `:565` | `descriptive_statistics`, `independent_t_test`, `mann_whitney_u` |
| `:596` | `pearson_correlation`, `spearman_correlation` |
| `:611` | `rm_anova`, `paired_t_test` |
| `:668` | `mcdonald_omega`, `omega` |

⇒ 共 **9 个别名 id**。这不是"私有表冗余"，而是**覆盖率破口**，且与 tables 行为不一致（同一张 legacy 卡：表出得来、图出不来）。别名进卡片的路径已实测在场：`result_card.py:64 method_id = output.get("test_type", …)` **原样写入、不解析**，并被 `tests/test_apa_figures_v2.py:251`（`"method": "repeated_anova"`）与 `tests/test_e2e_v52_paths.py:318,400`（`"method": "pearson_correlation"`）钉着。

### 3.2 B 类·以别名/方法 id 为键的注册表（30 点，含别名 20 点、别名键 50 个、17 文件）

| 位置 | 体量 | 性质 | 裁决建议 |
|---|---|---|---|
| `src/analysis/result_card.py:1355-1400` `_CARD_BUILDERS` | **44 键／14 个别名键／29 个 distinct builder** | 与 catalog `aliases` **逐条重复**；查表口 `:107-112` 已是三级兜底（原 id → `card_id` → `resolve_method_id`） | 探针实测：**14 个别名键删后行为全部等价**（"删后改变行为=0"，因 canonical 键均在且值同一函数对象）⇒ **该删**；但它被快照逐字钉死（§四 红名单），删之前必须人工批准翻快照 |
| `src/utils/i18n.py:14, :130`（27 键×2） | 含 `repeated_anova`/`chi_square_independence` | 中英文名案，**用户可见文案** | **保留**（展示层文案表，不是 id 翻译表）；但两表**自身互为副本**，是另一笔重复建设债 |
| `src/utils/guardrails.py:16`（26 键） | 同上 | 护栏文案表 | 保留语义、**键改走 resolve** 需在查表点加 1 行；列入案 A |
| `src/parser/keyword_dict.py:6`（33 键） | 同上 | **关键词→方法**，`tests/test_keyword_dict.py:16,27` 直接钉别名串 | **保留**（这是词表不是别名表，改它等于改 NLU 词典） |
| `src/output/interpretation.py:340, :457`＋`:478/:484/:491` | `mcdonald_omega`/`ave`/`discriminant_fl`/`discriminant_htmt` | 解释文案表＋**三处单点 `==` 判别** | 文案表保留；E 类单点判别**改 resolve**（新增别名时最容易静默漏的一类） |
| `src/output/learning_card.py:39`（48 键，6 别名）／`src/output/reasoning.py:40, :644`／`src/ui/quick_entries.py`（2 表＋8 组＋1 单点）／`src/ui/renderers.py`（3 单点）／`src/ui/app_pages_text.py`（2 表）／`src/paper_writer/defense_qa_kb.py:175`／`src/analysis/assumption_router.py:272`／`post_hoc_power.py:31`／`method_recommender.py:374` | 各处 1-8 点 | **id→文案/入口/路由**的查表 | 统一裁决＝「查表前 `resolve_method_id`，键只留 canonical」；**但每处都要人工确认该表是否接受用户手输 legacy 串**（`keyword_dict`/`intent_recognizer` 明确接受 ⇒ 不能机械照改） |

### 3.3 C 类·`src/upstream/semantic_alignment.py`（11 点，5 点含别名）⇒ **全部保留**

`:58-:102` 是"概念簇→方法"的语义词表（含 `"重复测量"`、`"rm_anova"` 这类**自然语言与缩写混列**，`:94`）。它承担的语义是"论文文本里出现这些说法时对齐到哪个方法"，catalog 里**没有对应字段**（`aliases` 只覆盖 id 级翻译）。把它并进 catalog 需要新增 `keywords` 维度，属**扩设计**，不是收口。

### 3.4 D 类·其它集合（57 点，12 点含别名，14 文件）⇒ **默认保留，两处点名**

绝大多数是"多方法共用一支处理"的分组语义（`undergrad_wizard.py` 12 点全 canonical、`runner.py:1004` 8 元集合、`professional_consistency.py:296,:753`）。点名两处需人工过目：
- `src/ui/quick_entries.py`：一类里最密（16 点、8 点含别名，含 `ave`/`discriminant_*`/`mcdonald_omega`），入口级；
- `src/questionnaire/intent_recognizer.py:508`：意图识别里出现 `chi_square_independence`，与 `keyword_dict` 同性质（接受用户口语）⇒ 倾向保留。

### 3.5 E 类·单点 `==` 判别（8 点，全含别名，4 文件）⇒ **裁决反转：这不是"冗余别名"，而是"执行层仍以别名作现役 id"**

点位：`interpretation.py:478,484,491`（`ave` / `discriminant_fl` / `discriminant_htmt`）、`renderers.py:341,344,349` 同族三串、`quick_entries.py` 1 点、`paper_writer/defense_qa.py:235`（`chi_square_independence`）。

原判据倾向"这类单串等值最脆、应改走 resolve"，**实测把因果翻了过来**：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "（tmp/psy26 内同型脚本）
runner @_register 键数 48 其中别名键: [(156,'repeated_anova'), (231,'chi_square_independence'), (403,'mcdonald_omega'), (523,'ave'), (549,'discriminant_fl'), (582,'discriminant_htmt')]
不在 catalog 的注册键: []
$ rg -n 'test_type="ave"|test_type="discriminant_fl"|test_type="discriminant_htmt"' src/analysis/validity.py
170:        test_type="ave",
224:        test_type="discriminant_fl",
300:        test_type="discriminant_htmt",
$ rg -n 'ave_cr|discriminant_validity' src/output/interpretation.py src/ui/renderers.py
（rc=1，两文件内 canonical 分支零命中）
```

⇒ 三点结论：
1. catalog 的 23 个别名里有 **6 个是执行注册表的现役键**（`runner.py:156/231/403/523/549/582`），结果对象的 `test_type` 直接就是别名串 ⇒ **"别名只是历史遗留、可整体收敛"这一隐含前提被否证**。
2. 因此 E 类分支今天**只认别名、不认 canonical**：给它喂 `ave_cr`／`discriminant_validity` 会掉进通用兜底文案（两文件内 canonical 分支零命中）。破口方向与 §3.1 figures 那侧**相反**。
3. 正确修法仍是"两侧都收"：`elif resolve_method_id(r.test_type) == "ave_cr":`（§五 第 4 段草图）——resolve 对别名与 canonical 同源，是唯一双向安全的写法；**只把字面量换成 canonical 而不加 resolve＝制造死分支**。

---

## 四、三案的改动面 / 红名单 / 迁移成本

### 4.1 改动面（行数按实测现值折算，不含测试改动）

| 案 | 生产码改动 | 涉及文件 | 现值射程 |
|---|---|---|---|
| **案 C 分层收口** | tables 删 4 死成员（**3 行**）＋ figures 头加 resolve（**2 行**）＋ figures 删 3 承重别名成员（**3 行**）＋ E 类 8 点改双向安全写法（**8 行**） ⇒ **约 16 行**；`_CARD_BUILDERS` 与执行注册表**都不动**（避开快照红与执行契约变更） | 6 件：`apa_tables.py`(875)、`apa_figures.py`(719)、`interpretation.py`(648)、`renderers.py`(757)、`quick_entries.py`(729)、`defense_qa.py`(1023) | 4,751 行现值内的 16 行 |
| **案 A 全量集中** | 案 C ＋ 删 `_CARD_BUILDERS` 14 别名键 ＋ 17 文件的 B 类别名键（50 键）与查表点加 resolve ⇒ **约 85-110 行**，且**必改测试** | **16 件**（A/B 含别名点并集） | 合计 **11,569 行**（16 文件现值相加） |
| **案 B 只加看守** | 生产码 **0 行**；改 `method_catalog.py:1-7` docstring 一句使其与现实一致 ＋ 新增看守测试 1 件 ＋ （可选）把 §3.1 的 9 别名丢图写成 KNOWN_ISSUES 行 | 1＋1 件 | — |

### 4.2 红名单（**本案最高风险项，全部实测过现值**）

现绿基线（本档取数时跑过，`$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_method_id_consistency.py tests/test_apa_figures_v2.py tests/test_analysis_result_card.py tests/test_result_card_registry_snapshot.py tests/test_apa_tables.py tests/test_apa_figure_templates.py -q` → **110 passed in 12.38s**；逐件收集数 9/35/11/23/16/16）：

| 断言 | 位置 | 哪案会翻 | 为什么不能"顺手改绿" |
|---|---|---|---|
| `len(_CARD_BUILDERS) == BASELINE_REGISTRY_KEY_COUNT`（基线 **44**） | `tests/test_result_card_registry_snapshot.py:121`（常量 `:38`） | **案 A** | 删别名键即改计数口径（−14）⇒ 纪律档 §五-4「改计数口径一律停手交人工」 |
| `sorted(_CARD_BUILDERS) == BASELINE_REGISTRY_KEYS`（44 个键名逐字列出，含 14 别名键） | 同上 `:125` | **案 A** | 键集快照，注释自陈"增删任一卡片模板必翻红" |
| `== BASELINE_ALIAS_GROUPS`（一个 builder 挂多键的别名组表） | 同上 `:144-148` | **案 A／任何"拆并别名"** | 组表本身就是私有别名表现值，等于把现状钉成契约 |
| `len(set(values)) == 29`／builder 名集合快照 | 同上 `:140-142` | 案 A（若拆 builder） | 同上 |
| `@pytest.mark.parametrize` 断言**别名键必须在注册表**：`factorial_anova`、`mann_whitney_u`、`wilcoxon_signed_rank`、`omega`、`exploratory_factor_analysis`、`repeated_anova` | `tests/test_result_card_v2_methods.py:310-327` | **案 A** | 6 个参数化用例把"别名即键"当契约；改法只能连生产码一起回退（两笔一体） |
| `"method": "repeated_anova"` 的卡必须产出 `method == "repeated_measures"` 图 | `tests/test_apa_figures_v2.py:249-257` | 案 A/C 若"删别名成员但不加 resolve" | **反向红**：这是 figures 别名承重的实证，也是案 C 必须"先加 resolve 再删成员"的顺序锁 |
| 表/图路由分组快照 | `tests/test_method_id_consistency.py:29-39`（`get_table_route_group` 逐条） | 案 A 若顺手合并 `table_group` | 现有断言 `pearson_corr/spearman_corr` 同组、`hlm` 三 id 同组，改组即红 |
| 导出/下载全局账本门 | `tests/test_export_gate_global_scan.py`（在册 **1 红**，台账 81；另有 `questionnaire_panel.py:826/838/865` 3 处命名门禁债） | 案 A/C（`apa_tables`/`apa_figures` 被 `docx_exporter.py`、`zip_exporter.py`、`professional_consistency.py`、`method_exposure.py` 消费） | 一旦新增产图面就可能改交付件数；**在册红不许自行消**（挂 `NEEDS_MIGRATION`＝绕门，加白名单＝替隐私分类签字） |

### 4.3 迁移成本（除行数外的真实成本）

1. **legacy 数据面**：catalog docstring 自陈别名存在的原因是"legacy execution id 已持久化在 workspace 里"⇒ 任何"只认 canonical"的改法都要回答**旧工作区恢复路径**（`load_workspace`/`professional_consistency.py:296`）是否已在上游统一 resolve。本档实测：`result_card.py:64` **不解析**，故卡片层以下仍是混合格式。
2. **双账本对齐**：`method_exposure.py:19-32` 用 catalog 反推"有卡/有表"集合，而 `result_card._CARD_BUILDERS` 是真值表；两者今日靠 `card_id` 巧合对齐（`validate_method_contracts` 0 错），删键或加键都会让它**从"看着一致"变成"必须一致"**。
3. **文案表不能机械照改**：`i18n.py`／`keyword_dict.py`／`semantic_alignment.py`／`intent_recognizer.py` 接受**用户手输 legacy 串**，改 resolve 会改变匹配语义（NLU 侧），需产品确认。
4. **执行契约不可顺带"改正"**：`runner.py` 那 6 个别名注册键（`:156/:231/:403/:523/:549/:582`）一旦被"顺手改成 canonical"，`test_type` 取值即变 ⇒ 下游按别名分支的 E 类点（§3.5）与 `validity.py:170/224/300` 的显式赋值、以及 workspace 里已持久化的 `test_type` 全部要同步迁移。**属第四张别名表，且是权威级最高的一张**，任何案都不该在本档未获批准前动它。
5. **工时粗估**（折进 claims 实耗另算）：案 B 约 0.5 人日；案 C 约 1 人日＋定向回归；案 A 约 3-4 人日＋快照翻案批准＋导出面全量复核。

---

## 五、最小施工 diff 草图（**只作材料，不落盘**）

案 C 的四段（案 A 前 3 段同理，多一批键删除）：

```python
# src/output/apa_figures.py:562  —— 顺序锁：必须先加 resolve，再删分支里的别名成员
  def generate_figures_from_card(card: dict) -> list[APAFigure]:
      figures = []
-     method = card.get("method", "")
+     from src.analysis.method_ids import resolve_method_id   # 与 apa_tables:765 同源
+     method = resolve_method_id(card.get("method", ""))
```

```python
# 同文件：删掉解析后永不命中的成员，分组语义留在原位
- elif method in ("repeated_anova", "repeated_measures_anova", "mixed_anova", "paired_ttest"):
+ elif method in ("repeated_measures_anova", "mixed_anova", "paired_ttest"):
- elif method in ("two_way_anova", "factorial_anova"):
+ elif method in ("two_way_anova",):          # factorial_anova 由 resolve 承接
- elif method in ("efa", "exploratory_factor_analysis"):
+ elif method in ("efa",):
```

```python
# src/output/apa_tables.py —— 头已 resolve，这 4 个成员是纯死码
- elif method in ("pearson_corr", "pearson_correlation", "spearman_corr"):
+ elif method in ("pearson_corr", "spearman_corr"):
- elif method in ("chi_square", "chi_square_independence", "chi_square_gof"):
+ elif method in ("chi_square", "chi_square_gof"):
- elif method in ("hlm", "hierarchical_linear_model", "mixed_effects"):
+ elif method == "hlm":
```

```python
# src/analysis/result_card.py —— E 类/文案表的统一姿势（案 A 才动 _CARD_BUILDERS）
- if method_id == "ave":                      # interpretation.py:478
+ if resolve_method_id(method_id) == "ave_cr":
```

⚠️ 施工提醒两条（都有历史事故面）：① **删别名成员会让"某别名串在 src/ 出现次数"类快照缩水**（本案 −4 至 −18 不等）⇒ 属改计数口径，动手前先拿人工批准；② 若某判据写成"该字面串在该文件 0 命中"，**连解释性注释也不能含该串**。

---

## 六、回归钉桩方案（案 C/A 都建议同批带上）

1. **单源看守（ratchet 式，防"绿而失明"）**：新增 `tests/test_method_alias_single_source.py`，用**与本档同一 AST 轨**扫 `src/`，规则＝「A 类分支匹配点与 E 类单点比较里不得出现 catalog 别名字面量」，豁免清单按文件＋行号写死并**只减不增**（现值基线：A 类 6 点／E 类 8 点）。仓内已有同型先例可照抄：`tests/audit_inplace_scan.py`（其 `:4` 注明来源于 insights 建议）。
2. **legacy 卡成对断言**：对 §3.1 那 9 个漏图别名，逐条断言「同一份夹具、`method` 分别填 canonical 与 alias，产出的图数量与 `figure.method` 必须相同」。这条**专治静默丢图**，且在案 C 之前必然是红的（先红后绿才有判别力）。
3. **注册表快照改造**（案 A 才需要）：把 `test_result_card_registry_snapshot.py` 的"44 键逐字快照"降级为**两条语义断言**——`set(values)` 的 builder 集合不变、以及"每个 catalog id 经 `_CARD_BUILDERS.get(id) or get(card_id) or get(resolve(id))` 都能命中"。这样删别名键不再翻计数红，同时保留"新增卡必须登记"的守门作用。**该降级属放宽既有判据 ⇒ 必须人工批准**，执行手不得自改。
4. **变异自证**：往 `METHOD_CATALOG` 临时加一个假方法＋两个假别名，看守测试必须红（证明它真有牙）；再跑一次只加别名不加键，`validate_method_contracts` 必须报"card target not registered"。
5. **交付面加跑清单**（ psy 仓规约）：改动 `apa_tables/apa_figures` 后除被点名片段外，加跑 `pytest tests -q -k "download_buttons or export_gate"`，撞在册红**如实留**、不自行消红。

---

## 七、需人工裁决的出口（本档一律未动）

1. **选案**（C / A / B）——本档给排序：C > A > B；理由＝C 用 16 行拿到"权威表成真"的主要收益，同时避开 4 处快照红。
2. **计数口径缩水批准**：案 A 的 `_CARD_BUILDERS` 44→30（−14 键）＋ 17 文件约 −50 别名键。纪律档规定这类改动执行手必须停手。
3. **是否允许 figures 新增产图面**：修 §3.1 破口会让此前"只出表不出图"的 legacy 卡开始出图 ⇒ 交付件数/体积变化，涉及导出面与 golden 族（`test_golden_delivery.py`、`test_deliverable_zip_export.py`、`test_template_golden_flows.py`、UI/playwright golden 流）。
4. **`binary_logistic` 要不要真专属卡**：现为"有键无实现"，catalog `:69` 声明与实现不一致但契约校验查不出（§一 #4）。
5. **NLU/文案表的边界**：`keyword_dict.py`、`semantic_alignment.py`、`intent_recognizer.py`、`i18n.py` 是否明确划为"catalog 不管辖的领域"，并把这条边界写进 `method_catalog.py` docstring（案 B 的最小正确形态）。
6. **执行层 6 个别名注册键是否保留**（§3.5／§4.3-4）：若人工裁"保留"，则 `method_catalog.py:1-7` 的"防止各层自维护别名表"只能改判为"仅规范展示层的 id 翻译，执行 id 允许以别名注册"；若裁"改 canonical"，需连带出 workspace 迁移方案与 §3.5 全部下游分支的同批改法。两向都超出执行手授权。
7. 待主班判断：`docs/insights/**` 无索引件与目录枚举哨兵（本档自证：`$ rg -n 'insights' tests/ src/ scripts/ | rg -i 'glob|iterdir|listdir|scandir|walk'` → **rc=1 零命中**；`docs/insights/*.md` 现值 **99** 份（本档落盘前实测，落盘后 100） ⇒ 本档为第 100 份）⇒ 新增本档**不需补索引**，未为此落 partial。
