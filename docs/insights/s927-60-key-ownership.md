# s927-60｜`mean` / `reliability` 两键归属裁决材料（消费路径实测＋两案＋推荐＋diff 草案）

- 班次：`qoder-executor-20260929-0450-psy102`（信箱单 `s927-60`，只读／材料位）
- 取数现场：`D:\code\psy-analysis`，HEAD `4d3608e`（`git rev-parse --short HEAD`，2026-09-29T05:0x 现取）
- 上游锚点：`zcode-bridge/done/s924-22.result.md` 遗留问题①——「`mean` / `reliability` 两枚键的归属需要裁决：
  它们在 `i18n.TRANSLATIONS` 有、在 `TEST_NAMES_ZH` 没有，而 `get_test_name()` 的实现是『先走 `t()`，命中就返回译文，
  否则回落 `TEST_NAMES_ZH`』⇒ 这两枚其实**永远走不到 settings 表**」。
- 性质：**纯材料**。🔴 本班零代码改动、零表项增删（两案的 diff 只以草案形态存在于本档 §五，未落盘）；
  内存态模拟（§三）不落盘、不改磁盘字节。

## 〇、结论先说

1. **锚点全部复验成立**（HEAD `4d3608e`）：`TRANSLATIONS` zh 有 `mean:37`/`reliability:83`、en 有 `mean:153`/`reliability:199`；
   `TEST_NAMES_ZH` 无这两键（`rg '"(mean|reliability)":' config/settings.py` → **rc=1 零命中**）。
2. **两键在生产侧零消费者**：全树字面取键只有测试件（`tests/test_i18n.py` 的 5 处 `mean` ＋ 1 处 `reliability`）；
   `t()` 的**变量首参**全树实测 **0 处真命中**（唯一 2 处正则命中是 `learning_card.py:65` 字符串里的 `t(df)`，非调用）。
   ⇒ 「归属」之争的实际收益是**表义纯度**，不是显示正确性。
3. **两键都不是检验方法键**：`reliability` 是 `purpose` 域值（`method_recommender.py:31` 注释六值之一，
   `:266-267` 匹配、`:270` 推荐 → 落到的 `method_id` 是 `cronbach_alpha`）；`mean` 是统计量/列名
   （`jspsych_data_importer.py:288 agg_func="mean"`、`charts.py:63-64 table["mean"]`）。
   实测 `post_hoc_power._TEST_TYPE_MAP` 的 11 个 test_type 里两键**都不在**。
4. **两案实测代价**（内存态模拟＋钉桩面逐条）：案 A（补 `TEST_NAMES_ZH`）＝**界面零行为变化**、破 4 处 s924-22 钉桩需回写；
   案 B（删 `TRANSLATIONS` 冗余）＝**有可见行为变化**（`get_test_name('mean')` 由 `'均值'` 退化成蛇形 `'mean'`）、
   破 6 处断言含计数钉桩 `== 106`。
5. **推荐（卷宗限定二选一的前提下）＝案 A**，理由见 §四；
   同时如实登记：本班实测**第三条路更便宜**（换测试样本键，两表键集自然相等），见 §六——它是背景材料，不是本单推荐。

## 一、消费路径复核（完成标准①）

### 1.1 入口链（逐字实取）

```
config/settings.py:68-74   def get_test_name(test_type)
                             if t is not None:
                                 translated = t(test_type)
                                 if translated != test_type:     # ← i18n 命中即返回
                                     return translated
                             return TEST_NAMES_ZH.get(test_type, test_type)   # ← 回落才吃 settings
src/utils/i18n.py:249-266  def t(key, lang=None) → TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)
src/utils/i18n.py:269-271  def get_test_name_zh(test_type, lang=None) → return t(test_type, lang)   # 纯转发，永不碰 settings
```

复跑：`rg -n "def get_test_name\b" -A 8 config/settings.py`／`rg -n "def t\(" -A 18 src/utils/i18n.py`／
`rg -n "def get_test_name_zh" -A 4 src/utils/i18n.py`。

### 1.2 两键的键位（逐字）

| 键 | zh 侧 | en 侧 | settings 侧 |
|---|---|---|---|
| `mean` | `src/utils/i18n.py:37` `"mean": "均值",`（`# 统计术语` 段内） | `src/utils/i18n.py:153` `"mean": "Mean",` | **无此键**（rc=1） |
| `reliability` | `src/utils/i18n.py:83` `"reliability": "信度分析",`（夹在 `cfa:82` 与 `normality_test:84` 之间，**与方法键同段**） | `src/utils/i18n.py:199` `"reliability": "Reliability Analysis",` | **无此键**（rc=1） |

> 📌 一处值得裁决时注意的**段内位置差**（本班只登记）：`mean` 在 i18n 的「统计术语」段（与 `std` 同段），
> `reliability` 却在方法键段（与 `cfa`/`normality_test` 同段）——两键在 i18n 内部的自我归类就不一致。

### 1.3 消费者清单（全树，排除 `tmp/`）

| 消费位 | 形态 | 实测 |
|---|---|---|
| `tests/test_i18n.py:26` | `assert t("mean") == "Mean"` | 语言切换用例的样本键 |
| `tests/test_i18n.py:95/97/99` | `assert get_test_name_zh("mean") == "Mean"/"均值"/"均值"` | `lang=None` 回落会话语言的样本键 |
| `tests/test_i18n.py:105` | `assert get_test_name_zh("mean", "fr") == "均值"` | 不支持语言降级用例的样本键 |
| `tests/test_i18n.py:62` | `("reliability", "信度分析", "Reliability Analysis")` | `parametrize("key,zh,en",…)` 双语钉桩的第 8 行 |
| 生产件 | 字面 `t("mean")`／`get_test_name("mean")`／`…("reliability")` | **0 处** |
| 生产件 | `t(变量)` 变量首参 | **0 处真命中**（`learning_card.py:65` 是字符串里的 `t(df)`） |
| `TEST_NAMES_ZH` 遍历面 | `values()`/`keys()` 迭代 | **0 处**：只有 `settings.py:74` 与 `quick_entries.py:177` 两处 `.get()`；`app.py:33` import 后**未再使用** |

复跑：`rg -n '"(mean|reliability)":' src/utils/i18n.py config/settings.py`／
`rg -n -w "TEST_NAMES_ZH" -g '*.py' -g '!tmp/**' .`／
`rg -n "\bt\([a-zA-Z_][a-zA-Z0-9_]*\)" app.py src/ -g '*.py'`。

### 1.4 归属证据：两键不在方法 id 值域里

- `src/analysis/method_recommender.py:31`：`purpose: str = ""  # difference / correlation / prediction / mediation / moderation / reliability`
  ⇒ `reliability` 是**研究目的**域值；`:266-267 _match_reliability` 判 `d.purpose == "reliability"`，
  `:270 _rec_reliability` 推荐出的 `method_id` 是 `cronbach_alpha`（`tests/test_analysis_recipe.py:21` 钉
  `("reliability", {}, "cronbach_alpha")`），`:273` 展示名走硬编码 `primary_method_zh="Cronbach's α 信度分析"`（＝s924-11 的 T11 面，不吃 i18n）。
- `src/analysis/post_hoc_power.py` 的 `_TEST_TYPE_MAP` 现读 11 键：
  `chi_square_gof, chi_square_independence, independent_ttest, one_sample_ttest, one_way_anova, paired_ttest, pearson_corr, repeated_anova, spearman_corr, two_way_anova, welch_anova`
  ⇒ 不含 `mean`／`reliability`。复跑：
  `PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "from src.analysis.post_hoc_power import _TEST_TYPE_MAP as m;print(len(m), sorted(m))"` → `11 [...]`。
- `mean` 的实测身份是**聚合函数名/结果列名**：`jspsych_data_importer.py:288 agg_func: str = "mean"`、`:421 {"count": "N", "mean": "M", "std": "SD"}`、
  `charts.py:63-64 elif "mean" in table.columns`。

## 二、运行时实测（不是推断）

```
基线：get_test_name('mean') = '均值' ／ get_test_name('reliability') = '信度分析'
```
⇒ 两键当前**由 i18n 侧供值**，s924-22 说的「永远走不到 settings 表」复验成立。

## 三、两案的牵动面（内存态模拟，磁盘字节未变）

| 案 | 模拟做法 | 实测行为变化 | 实测破的钉桩（需回写） |
|---|---|---|---|
| **A 补 `TEST_NAMES_ZH`** | 运行时给 dict 补 `mean`/`reliability` 两键后复调 `get_test_name` | `get_test_name('mean')` 仍是 `'均值'`（i18n 先命中）⇒ **界面零变化**；`len(TEST_NAMES_ZH)` 48 → **50** | ①`tests/test_i18n.py:142 SETTINGS_TABLE_KEY_COUNT = 48`（`:234` 断言红）；②`:149-160` 交集锚点清单 9 枚 → 11 枚（`:221` 红）；③`:162 I18N_KEYS_MISSING_FROM_SETTINGS = ["mean","reliability"]` → `[]`（`:225` 差集向红）；④`:127-128` docstring 的内联读数（`48`/`交集 9、差集 2`）随之失真 |
| **B 删 `TRANSLATIONS` 冗余** | 运行时从 zh/en 各删两键 | `t('mean','zh')` → `'mean'`；`get_test_name('mean')` → **`'mean'`（蛇形键外泄）**；`get_test_name_zh('reliability','zh')` → `'reliability'`；zh/en 键数 106 → **104**（双语对称仍成立，实测 `set(zh)==set(en)` True） | ①`:112 len(TRANSLATIONS["zh"]) == 106`；②`:26`；③`:95`；④`:97`；⑤`:99`；⑥`:105`；⑦`:62` 的 `reliability` 行；（`:111` 双语键对称不破） |

复跑（不落盘，进程内改）：

```
$ PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "import config.settings as S;from copy import deepcopy;S.TEST_NAMES_ZH=deepcopy(S.TEST_NAMES_ZH);S.TEST_NAMES_ZH.update({'mean':'均值','reliability':'信度分析'});print(S.get_test_name('mean'),S.get_test_name('reliability'),len(S.TEST_NAMES_ZH))"
   → 均值 信度分析 50
$ PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "import src.utils.i18n as I, config.settings as S;
   [I.TRANSLATIONS[l].pop(k,None) for l in ('zh','en') for k in ('mean','reliability')];
   print(len(I.TRANSLATIONS['zh']), repr(I.t('mean','zh')), repr(S.get_test_name('mean')), repr(I.get_test_name_zh('reliability','zh')))"
   → 104 'mean' 'mean' 'reliability'
$ git status --porcelain        → 模拟前后逐字相同（4d3608e 基线 12 行，含本班 §产出 1 件 ??）
```

## 四、推荐（卷宗限定「补／删」二选一）＝案 A

理由（按可复算性排序）：

1. **行为面安全**：案 A 实测界面零变化；案 B 实测把 `get_test_name('mean')` 打成蛇形 `'mean'`——
   这正是 s924-11 记录的「`get_test_name_zh` 对不在 i18n 的键**原样吐回蛇形键**」那类缺陷的制造动作。
2. **回写量小且同向**：案 A 只回写 `tests/test_i18n.py` 的 3 个常量/清单＋1 段 docstring；
   案 B 要动 7 处断言，其中 5 处是拿 `mean` 当**语言切换样本键**的用途——删键等于逼着这些用例换样本键，改动面从「表」扩散到「测试语义」。
3. **不破计数门禁**：案 B 必改 `:112` 的 `== 106`（s920 系扩容门禁），而 s924-11 已点名这类精确计数钉桩在任何并轨下都要同步改字面数——多改一处就多一处将来误读成「并轨失败」的红。
4. **不撞他班在途件**：两案都只涉及 `config/settings.py`＋`src/utils/i18n.py`＋`tests/test_i18n.py`，
   全部**不在**本波 psy 禁碰名单（`app.py`/`pytest.ini`/`requirements-lock.txt`/`src/analysis/{__init__,cfa,result_card}.py`/`src/output/interpretation.py`/`tests/test_cfa_sem_golden.py`）内 ⇒ 放行即可排。
5. **代价如实报**：案 A 让 `TEST_NAMES_ZH` 收下两枚**非方法键**（表义被稀释），并且它们永远是死值（i18n 先命中）。
   若人工认为「settings 表是检验方法名专表、不得混入统计量名」，则案 A 的这条代价大于收益 ⇒ 请看 §六。

## 五、diff 草案（案 A；本班未落盘，仅供放行后另单执行）

```diff
--- a/config/settings.py
+++ b/config/settings.py
@@ TEST_NAMES_ZH（现 48 键，末段为「v3.7：效度方法新增」）
     "test_retest": "重测信度",
     "cohens_kappa": "Cohen's κ 评分者一致性",
     "fleiss_kappa": "Fleiss' κ 多评分者一致性",
+    # s924-22 差集归位（裁决=案 A）：两键运行时由 i18n 先命中，此处仅补齐键集，属死值
+    "mean": "均值",
+    "reliability": "信度分析",
     # v3.7：效度方法新增
     "cvi": "内容效度指数（CVI）",
```

```diff
--- a/tests/test_i18n.py
+++ b/tests/test_i18n.py
@@ -142 +142 @@
-SETTINGS_TABLE_KEY_COUNT = 48  # config/settings.py::TEST_NAMES_ZH
+SETTINGS_TABLE_KEY_COUNT = 50  # config/settings.py::TEST_NAMES_ZH（s927-60 案 A 落令后现取）
@@ I18N_KEYS_ALSO_IN_SETTINGS（9 枚 → 11 枚，按字典序插两枚）
-    "mann_whitney",
+    "mann_whitney",
+    "mean",
@@
     "paired_ttest",
     "pearson_corr",
+    "reliability",
     "welch_anova",
@@ -162 +162 @@
-I18N_KEYS_MISSING_FROM_SETTINGS = ["mean", "reliability"]
+I18N_KEYS_MISSING_FROM_SETTINGS = []   # 案 A 后差集清空；将来任何键再落回差集都会红
```

⚠ 三处必带项（执行单别漏）：
① 同批回写 `:127-128` docstring 里的内联读数（`48`／`交集 9、差集 2`／`11 枚`），否则注释与断言互相打脸；
② 落令后验收命令＝`PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_i18n.py -q`（预期 22 passed，本班未跑）；
③ `git diff --numstat` 应为 `config/settings.py +3/-0`、`tests/test_i18n.py +4/-2` 量级，出现**删除表项**即为执行跑偏。

## 六、登记但不推荐为「两案之一」的第三形态（供人工改判）

本班实测：**把测试里的样本键换成真方法键，两表键集自然闭合，且不动任何一张表**——
`mean`（语言切换样本）可换 `descriptive`（`tests/test_i18n.py:61` 已在用，settings/i18n 双边都有键）；
`reliability` 行可换 `cronbach_alpha`（`config/settings.py:25` 有键，i18n 侧 s924-11 实测**无此键** ⇒ 换它会落进差集，需一并裁决）。
代价＝只改测试件 6 行，两表一字不动；风险＝`cronbach_alpha` 不在 i18n，换完反而暴露新差集。
**卷宗把本题限定为「补／删」二选一，本班按限定推荐案 A**，此段仅作对照材料。

## 七、本班边界

- 零代码改动：`git diff --numstat` 现读 8 行**全部是他班在途 ` M` 件**（`app.py 12/40`、`pytest.ini 1/1`、`requirements-lock.txt 6/6`、
  `src/analysis/__init__.py 14/0`、`src/analysis/cfa.py 178/40`、`src/analysis/result_card.py 180/13`、
  `src/output/interpretation.py 2/2`、`tests/test_cfa_sem_golden.py 59/49`），本班逐件零接触；
  本班唯一产物是 `?? docs/insights/s927-60-key-ownership.md`。
- 未跑任何 pytest（§五 ② 那条命令留给执行单；全量更是禁跑）。
- 未碰 `app.py`（本班只读出 `:33` import 后未再使用这一事实）。
- 统计口径面零判定：本档不判「`均值`/`信度分析` 这两个译名对不对」，只裁「键该挂在哪张表」。
