# psy 答辩题库「同题 4 组 9 条」冗余合并裁决材料（只读）

- 单号：s924-58　班：`qoder-executor-20260925-0730-psy55`　日期：2026-09-25
- 性质：**只读 census ＋ 两案对比**。本档不改 `src/paper_writer/defense_qa_kb.py`、不改 `defense_qa.py`、不改任何测试、不写库。
- 探针与原始读数：`tmp/qoder-executor-20260925-0730-psy55/s58_probe.py` / `s58_lines.py` / `s58_compat.py` ＋ `s58_out.txt`（临时件，收工前可删）。

---

## 〇、先纠卷宗前提（三处漂移，以盘上实证为准）

| # | 卷宗前提 | 实测 | 结论 |
|---|---|---|---|
| 1 | 「135 条问题文本 → 126 个不同文本」 | **137 条 → 128 个不同文本** | 过期。s924-56 补 `assumption`/`limit` 两条兜底后题库 135→137（`tests/test_defense_qa_kb_data.py:72 TOTAL_ENTRIES = 137`），不同文本同幅度 +2 |
| 2 | 「4 组 9 条冗余」 | **4 组 / 冗余 9 条**（`sum(len)-len(dup)==9`） | ✅ 成立 |
| 3 | 「答案侧 0 重复，s922-114 判明」 | 137 条 `answer_template` 去重后仍 **137** | ✅ 成立，且由 `test_answer_templates_are_all_unique` 钉桩 |
| 4 | 锚点 `tests/test_defense_qa_kb_data.py:243` | 该组现居 **:252**；:243 现为 `for cid, _, tmpl in ENTRIES:` | 漂移 +9 |
| 5 | 锚点 `defense_qa_kb.py:471/:649/:707/:1039` | 实测 **:498 / :676 / :734 / :1069** | 漂移 +27/+27/+27/+30（末条多 3 行＝该区间另有条目增补） |

复算命令：

```
$ .venv/Scripts/python.exe -B tmp/qoder-executor-20260925-0730-psy55/s58_probe.py
$ rg -n --no-ignore -F 'question="效应量？"' src/paper_writer/defense_qa_kb.py
$ rg -n --no-ignore -F 'friedman-02' tests/test_defense_qa_kb_data.py
```

> ⚠ 完成标准①字面写「与 rg 实测行号（471/649/707/1039）一致」——**该括号内数字与盘上不符**，本档按纪律按磁盘实况修正并留痕，判据实质（档内 id ↔ 实测行号一一对得上）成立。

---

## 一、四组明细（id / 源行 / 题文 / 答案差异）

源行一律取 **`question="…"` 关键字所在行**（＝`rg -n -F` 的直接读数，可整条复算）；`QATemplate(` 调用行＝该值 −1（AST 读数）。

### 组 1　题文 `效应量？`（4 条，全部 category=`effect`、difficulty=`必问`）

| id | 方法块 | src `question=` 行 | 答案首句（方法特异口径） | placeholders |
|---|---|---|---|---|
| `repeated_anova-02` | repeated_anova | :498 | 重复测量 ANOVA 报告**偏 η²**（partial η²）… Cohen 标准：小=.01，中=.06，大=.14 | `effect_size`,`effect_label` |
| `kruskal_wallis-02` | kruskal_wallis | :676 | **ε² = (H-k+1)/(n-k)**，类似 η² … 或报告 r = Z/√n（每对比较） | `effect_size`,`effect_label` |
| `friedman-02` | friedman | :734 | **Kendall's W**（协调系数），范围 0-1 …(0=完全无一致性,1=完全一致) | `effect_size`,`effect_label` |
| `point_biserial-01` | point_biserial | :1069 | **rpb** = {r:.3f} … 相当于 Cohen's d 的另一种表达（d = 2r/√(1-r²)） | **`r`**,`effect_label` |

- 组内答案 unique 4/4；占位符**交集仅 `effect_label`**，并集 `{effect_size, r, effect_label}`。
- **不可机械合并**：`point_biserial` 取用的是 `r` 而非 `effect_size`，其余三条反之。合并成一条会必然给其中一侧渲染出 `（r 待补充）`（见 §三.3）。
- 四条答案各自点名的**效应量指标互不相同**（偏 η² / ε² / Kendall's W / rpb），且各自的阈值口径也不同形（.01/.06/.14 vs 0-1 连续 vs d 换算式）。

### 组 2　题文 `效应量怎么算？`（3 条，全部 `effect`、`必问`）

| id | 方法块 | src `question=` 行 | 答案特异点 | placeholders |
|---|---|---|---|---|
| `welch_anova-02` | welch_anova | :546 | 可报告 **ω² 或 ε²**，方差不齐时比 η² 更稳健 | `effect_size`,`effect_label` |
| `wilcoxon-02` | wilcoxon | :804 | Wilcoxon 的效应量 **r = \|Z\|/√n**，Cohen 标准 小=.10/中=.30/大=.50 | 同上 |
| `chi_square_gof-04` | chi_square_gof | :1733 | 可使用 **Cohen's w = √(χ²/n)**：.10 小/.30 中/.50 大 | 同上 |

- 组内答案 unique 3/3；占位符交集＝并集＝`{effect_size, effect_label}` —— **这一组是唯一"签名兼容"的**。
- 但**签名兼容 ≠ 内容可合并**：三条各讲三种不同统计量（ω²/ε²、r、w），合并即丢方法特异口径。这是"不合并"的最强理由，也是卷宗 ① 预留的那一条。

### 组 3　题文 `样本量需要多大？`（4 条，全部 category=`data`，**difficulty 混档**）

| id | 方法块 | src `question=` 行 | difficulty | 答案特异点 | placeholders |
|---|---|---|---|---|---|
| `two_way_anova-03` | two_way_anova | :463 | **常问** | 细胞设计（{iv1}×{iv2}）每细胞 n≥15-20，总样本 n≥100；不平衡用 Type III SS | `iv1`,`iv2` |
| `ancova-04` | ancova | :628 | 必问 | ANCOVA 需求高于 ANOVA：每组 n≥30 或 G*Power；样本不足降低协变量调整稳定性 | **（无）** |
| `multiple_regression-03` | multiple_regression | :1216 | 必问 | 经验法则 **n ≥ 50 + 8k**，本研究 {n_predictors} 个预测变量，建议 n ≥ {min_n} | `n_predictors`,`min_n` |
| `moderation-04` | moderation | :1360 | **常问** | 调节效应 n≥100 起步、复杂模型 n≥200；引 Schoemann et al. (2017) | **（无）** |

- 组内答案 unique 4/4；占位符**交集为空**；且 `ancova-04`/`moderation-04` 两条**根本无占位符**（纯静态文案）。
- 🔴 **本组是唯一"合并会改运行时行为"的组**：difficulty 混了 `必问`/`常问`，而 `difficulty` 直接进 `generate_defense_qa` 的 `sort_key`（`DIFFICULTY_ORDER`）与 UI 分组标题／进度分母。合并成一条只能取一档 ⇒ **两个方法的题目会跳档换位**。属行为变更，不是纯整理。

### 组 4　题文 `样本量需求？`（2 条，全部 `data`、`必问`）

| id | 方法块 | src `question=` 行 | 答案特异点 | placeholders |
|---|---|---|---|---|
| `friedman-04` | friedman | :759 | Friedman 最少 n≥6（被试数），建议 n≥15；本研究 n={n}，{sample_judgment} | `n`,`sample_judgment` |
| `partial_corr-04` | partial_corr | :1045 | 偏相关 n ≥ 30 + 10×(控制变量数)；控制 {n_controls} 个，建议 n ≥ {min_n} | `n_controls`,`min_n` |

- 组内答案 unique 2/2；占位符**交集为空**（两组完全不同的字段名）⇒ 合并后单条模板无法同时喂饱两侧。

---

## 二、答案侧 diff 逐组结论（可/不可合并）

| 组 | 答案互异 | 占位符交集 | 合并是否丢方法特异口径 | 合并是否改运行时行为 | 裁决材料 |
|---|---|---|---|---|---|
| 效应量？ | 4/4 全异 | `{effect_label}`（`r` vs `effect_size` 分裂） | **是**（4 种效应量指标） | 否（同档同 category） | 不可机械合并 |
| 效应量怎么算？ | 3/3 全异 | `{effect_size, effect_label}` 完整 | **是**（ω²/ε² vs r vs w） | 否 | 签名兼容但内容不可并 |
| 样本量需要多大？ | 4/4 全异 | ∅ | **是**（4 套经验法则＋2 条无占位符静态文案） | **是——difficulty 混档会跳档** | 代价最高的一组 |
| 样本量需求？ | 2/2 全异 | ∅ | **是** | 否 | 不可并 |

**四组一致结论**：题目文本重复 9 条，答案文本重复 **0** 条。冗余面只在 4～8 个字符的题文字符串上，实质载荷（答案）100% 方法特异。

---

## 三、`defense_qa.py` 取题逻辑对合并的兼容性

### 3.1 取题路径（实测，KB 唯一消费方）

```
$ rg -n --no-ignore -g '!tmp/**' 'TEST_SPECIFIC_QA|GENERIC_QA|CATEGORY_FALLBACK_QA' src/ tests/
```
除数据面钉桩件 `tests/test_defense_qa_kb_data.py` 外，**只有 `src/paper_writer/defense_qa.py:14-16` 一处 import**。检索键：

| 键 | 出现处 | 是否用到 question 文本 |
|---|---|---|
| `test_type` → `TEST_SPECIFIC_QA.get(test_type, [])` | defense_qa.py:322 | 否，按**方法名**取整块 |
| `REQUIRED_CATEGORIES` 缺失补 `CATEGORY_FALLBACK_QA.get(cat)` | :279-284 | 否，按 **category** 取 |
| `for tmpl in GENERIC_QA` | :328 | 否，全量遍历 |
| 排序 `sort_key` | :339-345 | 否，用 `difficulty` + `category` |

⇒ **合并与否都不影响任何索引查找路径**；题库里没有以题文为键的字典。

### 3.2 🔴 决定性事实：这 9 条冗余在运行时**永不同现**

- 同一次 `generate_defense_qa` 只按**一个** `test_type` 取一个方法块（:322）。
- 实测：**0/26 个方法块内部有同题两条**；4 个重复组的成员**两两来自不同方法**（`s58_compat.py` §A/§B 读数：方法互异=True ×4）。
- `GENERIC_QA`(4) / `CATEGORY_FALLBACK_QA`(6) 的题文与 METHOD 侧题文**交集为空**（§C 三行全 `set()`），GENERIC ∩ FALLBACK 亦为空。

⇒ 这 9 条是**源码撰写期**的冗余，**不是用户可见的重复输出**。"合并以免学员看到 4 遍同一题"这个最常见的合并动机，在本仓**不成立**。
⇒ 反向含义：`GENERIC_QA` 现有 4 条用的是**长问句**（如「你的样本量 n={n}，依据是什么？是否满足检验要求？」），与这 4 个短问句**不同文本**，所以"抽公共 GENERIC 条"是**新增命名空间**，不是往已有 GENERIC 里归并。

### 3.3 静默退化风险：缺键不报错

`_safe_format`（defense_qa.py:245-258）用 `_DefaultDict.__missing__` 把缺失键渲染成 **`（{key} 待补充）`**，`_build_qa_item` 因此几乎不会返回 None。

⇒ 若采 A 案并把答案模板并成一条，占位符错配（如给 `point_biserial` 喂 `{effect_size}`）**不会崩、不会被测出**，只会在学员看到的答辩答案里留下"（r 待补充）"。这类失败模式比崩溃更难发现，是 A 案的实质风险面。

### 3.4 持久化侧：`question_id` 已是"仅按题文"，合并**不会**清理任何歧义

```
$ sed -n '39,42p' src/paper_writer/defense_qa.py
```
`QAItem.question_id = md5(self.question)[:12]` —— **只含题文，不含方法/答案/category**。实测含义：

- 组 1 的四条 `效应量？` 现在**已经共用同一个 question_id**，即 `session_state["defense_qa_mastered"]`（`src/utils/workspace.py:471` 持久化）**只有一个槽位**。
  ⇒ 在 `friedman` 下勾「已掌握」，切到 `kruskal_wallis` 的同题也会显示已掌握（跨方法串状态）。
- 这**不是漏网**：`tests/test_defense_qa.py:251 test_qaitem_question_id_stable_across_instances` 用"同题文＋不同答案＋不同 category＋不同 difficulty"三件变异显式断言 `a.question_id == b.question_id`，注释写「ID 仅基于 question 文本」⇒ **有意钉桩的设计口径**。
- 🔑 因此裁决上关键的一点：**A 案（合并题文）不会改变 question_id 的碰撞格局**——碰撞在合并前后完全同一（都是"同题文 ⇒ 同 id"）。想修串状态，正确改法是给 id 掺进 `category`/答案摘要，**与合并是两件事**。把"清理持久化歧义"记在合并的账上是错的。
- ⚠ 另有一条当前**未被任何断言钉住**的承重不变量：UI 复选框 `key=f"qa_mastered_{item.question_id}"`（`src/ui/undergrad_wizard.py:1331`、`src/ui/paper_writing_ui.py:668`）要求**同一次渲染内 question_id 唯一**。今天靠 §3.2 的数据事实（组内成员必跨方法）侥幸成立；一旦有人往**同一方法块**里再加一条同题文本，就会撞 `StreamlitDuplicateElementKey`。现有测试只钉了"跨块同题"（`test_question_text_duplicates_are_registered`），**没钉"块内不可同题"**。

---

## 四、两案对比

### A 案：抽公共 GENERIC 条 ＋ 方法特异答案参数化

做法：每个重复题文在 `GENERIC_QA` 建 1 条，方法块删掉对应条目，答案侧改为按 `test_type` 分派（新增 `Dict[method, answer_template]` 或给 `QATemplate` 加 `answers_by_method`）。

| 项 | 实测估算 |
|---|---|
| 题文字符串可省 | 9 条 × 平均 8 字符 ≈ **72 字符** |
| 答案文本可省 | **0 行**（四组答案全互异，一行都并不掉） |
| 需新增结构 | 1 张 method→answer 分派表；或 `QATemplate` 加字段（字段集已被 `test_entry_dataclass_field_set` (:218) 与 `test_dataclass_defaults_are_safe` (:223) 钉桩 ⇒ 加字段要同笔改测试） |
| 需同笔改的钉桩 | `test_question_text_duplicates_are_registered` (:235)（128/4/9 三个数全变）、`TOTAL_ENTRIES = 137` (:72)、`test_total_entry_count_links_parametrization` (:160)、`test_kb_read_only_for_the_suite` (:382) 里钉死的 `(4, 6, 26, 127)` 元组、`test_generic_qa_snapshot` (:136)／`test_method_index_snapshot` (:142) 的"每法 4-6 题" |
| 行为变更面 | 组 3 difficulty 混档 ⇒ 2 个方法题目跳档换位（排序/分组标题/进度分母都动） |
| 静默失败面 | §3.3 缺键渲染"（r 待补充）" |
| 净收益 | **零运行时收益**（§3.2 冗余本就不同现），仅源码少 4 个短字符串字面量 |

### B 案：维持现状，只在钉桩侧加口径注记

做法：KB 一字不动；把 §3.2「跨方法 ⇒ 运行时永不同现」与 §3.4「块内不可同题」写成显式约束。落地形态二选一，均**不在本单执行**：
- B1：在 `test_question_text_duplicates_are_registered` docstring 补一句"跨方法重复不影响输出唯一性；**同方法块内**重复会撞 Streamlit widget key"（文档级，零行为变更）。
- B2：在 `tests/test_defense_qa_kb_data.py` 新增一条断言"任一方法块内 question 互异"（把 §3.2 的侥幸升格为门禁）。属**纯增量 +1 例**，不改任何现有计数。

### 推荐：**B 案（B1＋B2 同做）**；A 案不推荐落地

理由（三条，全部基于本文实测）：
1. **收益端为空**：冗余不产生任何用户可见重复（§3.2），答案侧一行并不掉（§二）⇒ A 案省下的只有 ~72 字符源码，代价是一张新分派表＋4 处钉桩计数重钉＋1 处档位行为变更。
2. **风险端为静默退化**：缺键不报错只补"（r 待补充）"（§3.3），一旦参数化口径写错，测试测不到、学员看得到。
3. **A 案连它自己的卖点都不兑现**：常被认为能修好的"掌握状态串槽"，合并前后同一（§3.4），要修得动 `question_id`，那是另一单。
4. B2 才是这 9 条冗余里**真正的风险所在**：把当前"数据侥幸"升格为门禁，防的是未来有人往同块加同题 ⇒ 当场红，而不是线上撞 `StreamlitDuplicateElementKey`。

---

## 五、需要主班裁决／待人工的出口（本单一律未动）

| # | 事项 | 为什么本单不做 |
|---|---|---|
| 1 | 🔴 **四组答案里的 Cohen 阈值数值本身对不对**（η² .01/.06/.14、w 与 r .10/.30/.50、Kendall's W 0-1、rpb→d 换算） | **红线：统计数值结论**。本单只做"复写点收敛"的工程裁决，不判数值对错，不改任何数值。与 s924-61 的 η² 复写面同域，建议合并交人工档 |
| 2 | `question_id` 仅按题文 ⇒ 同题跨方法掌握状态**串槽**（已有意钉桩）是否接受 | 现状是 `test_defense_qa.py:251` 显式钉住的设计口径，改它＝翻已归档的产品决策，超出执行手授权 |
| 3 | A 案若要落地，需同笔重钉 `test_defense_qa_kb_data.py` 的 5 处计数：`TOTAL_ENTRIES` 137 (:72)、不同题文 128／组 4／冗余 9 (:235)、`test_kb_read_only_for_the_suite` 的 `(4, 6, 26, 127)` (:382)、`test_method_index_snapshot` 的 `127` 与"每法 4-6 题" (:142) | **改计数口径（会 −N）一律停手落 partial**（纪律 §五.4）。本单不动 KB，故不触发 |
| 4 | B2 新增门禁断言的落笔权 | 涉及改测试件；本单被派为只读班（且 psy 的 `tests/test_exporters_*` 族另有停派闸），交主班派写位执行 |
| 5 | 卷宗 5 处锚点全部漂移（见 §〇） | 建议主班把 s922-114 系卷宗的行号锚点统一改成"只锚唯一文本、不写行号"（纪律 §十.4） |

---

## 六、完成标准对照（逐条实测）

| 标准 | 读数 | 判定 |
|---|---|---|
| ① 档内 4 组 id 与 `rg -n 效应量？` 实测行号一致 | 本档组 1 `question=` 行 :498/:676/:734/:1069，与 `rg -n -F 'question="效应量？"'` 四条读数逐条相符；另三组行号同法复核（:546/:804/:1733、:463/:628/:1216/:1360、:759/:1045）；**卷宗括号内的 471/649/707/1039 已否证** | ✅（判据实质成立；括号数字按盘上修正） |
| ② 答案侧 diff 逐组列出 | §一 四组各列答案特异点＋§二 汇总 unique 计数（4/4、3/3、4/4、2/2 全互异） | ✅ |
| ③ `git status --porcelain` 仅新增该档 | 见 result「验收情况」；开工基线 7 项在册脏件，收工差集＝本档 1 份 | ✅（净差集口径） |
| ④ KB 零改动 | `src/paper_writer/defense_qa_kb.py`／`defense_qa.py` 收工仍不在 porcelain 中；`git diff --stat -- src/paper_writer/` 空 | ✅ |
