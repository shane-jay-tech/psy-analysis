# psy Cohen η² 阈值复写点 census 与收敛裁决材料（只读）

- 单号：s924-61　班：`qoder-executor-20260925-0730-psy55`　日期：2026-09-25
- 性质：**只读 census ＋ 两案对比**。零代码改动、零测试改动、零写库。
- 🔴 **红线自约束**：本档只裁「哪几处各写了一份、值是否同形、谁是唯一真源、边界行为当下是什么」——**不判「0.01/0.06/0.14 这组数值本身对不对」**，也不建议任何数值变更。数值口径的取舍一律落 §五 交人工。

---

## 〇、先纠卷宗前提（1 处锚点漂移 ＋ 2 处口径低估 ＋ 1 处方向性否证）

| # | 卷宗前提 | 实测 | 结论 |
|---|---|---|---|
| 1 | 锚点 `power_analysis.py:40` | 现居 **:64** | 漂移 +24；余三锚（`psychology_report_format.py:40`／`interpretation.py:627`／`reasoning.py:101`）与 `learning_card.py:162/172` **逐字未漂** |
| 2 | 「以三种形态在**至少 5 处**复写」 | **13 处 / 9 文件**（三形态齐全：dict 指南表 2 行、元组表 1 行、硬编判分支 3 处共 9 个阈值字面量、纯文案 7 处） | 低估约 8 处 |
| 3 | 「另 `learning_card.py:162/172` 文案」 | 这两条成立，但**同级文案还有 5 条未列**：`reasoning.py:328`、`preregistration.py:306`、`undergrad_wizard.py:3121`、`section_writers.py:869` | 低估 |
| 4 | 「`interpretation.py` 用小于号开区间边界、`power_analysis.py` 无边界语义注记」⇒ 隐含"两者对 0.06 的归属可能不同" | 🔴 **否证**：`<` 与 `>=` 是**互补**而非冲突。运行时实测三处活判分支在 0.01/0.06/0.14 三个边界点上的**分档归属完全一致**（§二 读数表） | 边界语义不是问题点；**档位中文名不一致才是** |
| 5 | 单一来源案「以 `EFFECT_SIZE_GUIDE.eta_sq_p` 为准」 | 🔴 该表（含 `eta_sq`/`eta_sq_p` 两行）与 `EFFECT_BENCHMARKS["eta_sq"]` **在生产码里零读取**，是**三行死数据** | 收敛案的性质变了：不是"归位到既有真源"，而是"新建真源并迁入 3 处活判分支"（§四） |

复算命令：

```
$ rg -n --no-ignore -g '*.py' '0\.06' src/
$ rg -n --no-ignore -g '*.py' '0\.14' src/
$ rg -n --no-ignore -g '*.py' '0\.01' src/ | rg -i 'eta|η'
$ rg -c --no-ignore 'EFFECT_BENCHMARKS\["eta_sq"\]' src/        # => 无输出（0 处读取）
$ rg -n --no-ignore 'EFFECT_SIZE_GUIDE' src/ tests/
```

---

## 一、复写点清表（13 处 / 9 文件，按形态分组）

### 形态 A：dict 指南表（2 行，同文件相邻）

| # | 位置 | 字面量 | 生产读取 |
|---|---|---|---|
| A1 | `src/paper_writer/psychology_report_format.py:39` | `"eta_sq": {"小": 0.01, "中": 0.06, "大": 0.14},` | **0 处** |
| A2 | `src/paper_writer/psychology_report_format.py:40` | `"eta_sq_p": {"小": 0.01, "中": 0.06, "大": 0.14},` | **0 处** |

- 所属容器：`EFFECT_SIZE_GUIDE`（:37 起，8 个指标）。
- A1/A2 **值逐字相同**，且由 `tests/test_psychology_report_format_golden.py:234` 显式钉死 `EFFECT_SIZE_GUIDE["eta_sq"] == EFFECT_SIZE_GUIDE["eta_sq_p"]` ⇒ 这两行是**有意保留的同形双行**（η² 与偏 η² 共用 Cohen 档），不是漂移。
- 🔴 `EFFECT_SIZE_GUIDE` 在生产侧只被 `src/paper_writer/section_writers.py:14` **import 后从未引用**（`rg -c 'EFFECT_SIZE_GUIDE' src/paper_writer/section_writers.py` ⇒ **1**，即那行 import 本身），另经 `src/paper_writer/__init__.py:13/31` 再导出。真实读者只有测试件（:202 黄金快照、:217/:224/:227 参数化、:288 可变性探针）与 `tests/test_ui.py:235/252`。

### 形态 B：元组表（1 行）

| # | 位置 | 字面量 | 生产读取 |
|---|---|---|---|
| B1 | `src/experiment_design/power_analysis.py:64` | `"eta_sq": [(0.01, "小"), (0.06, "中"), (0.14, "大")],` | **0 处** |

- 所属容器：`EFFECT_BENCHMARKS`（:58 起，6 个指标）。消费函数 `_label_effect(value, benchmarks)`（:68-75）语义为 `>=` 升序取最后一个跨过档 ⇒ 下界**含边**。
- 🔴 但 `EFFECT_BENCHMARKS` 的 6 个调用点（`power_analysis.py:119/165/215/257/288/335`）只取 `cohens_d`/`cohens_f`/`r`/`cohens_w` ⇒ **`["eta_sq"]` 这一行从未被下标取用**（`rg -c 'EFFECT_BENCHMARKS\["eta_sq"\]' src/` ⇒ 0）。
- `power_analysis.py:64` 与 `psychology_report_format.py:39` 的**三档值逐字同形**（0.01/0.06/0.14 ↔ 小/中/大），只有容器形态不同。

### 形态 C：硬编判分支（3 处函数，各写 3 个阈值 ⇒ 9 个字面量）

| # | 位置 | 比较算子 | 底档措辞 | 输出形态 |
|---|---|---|---|---|
| C1 | `src/output/interpretation.py:627/629/631`（`_interpret_eta_sq`，def :625） | `<` | 「效应量很小。」 | **整句用户可见文案** |
| C2 | `src/analysis/validity.py:461/463/465`（`else` 即 anova/η² 分支，`effect_name = "η²"` 在 :438） | `>=` 降序 | 「极小」 | 裸档名 |
| C3 | `src/paper_writer/defense_qa.py:65/67/69`（`_classify_effect_size`，kind 判定在 :64） | `<` | 「可忽略」 | `(档名, 释义)` 二元组 |

⇒ **C1/C2/C3 才是唯一真正决定线上输出的三处**；A、B 五行表体目前是"看着像真源、其实没人读"的状态。
活判分支的调用侧证据：`_interpret_eta_sq` 被 `src/output/interpretation.py:162` 调用（报告行渲染）；`_classify_effect_size` 被 `src/paper_writer/defense_qa.py:131` 与 `:185` 调用；`validity.py` 的 `ef_level` 落进该函数的效度结论串。复算：

```
$ rg -n --no-ignore '_interpret_eta_sq|_classify_effect_size' src/
$ rg -n --no-ignore 'EFFECT_SIZE_GUIDE' src/paper_writer/section_writers.py   # => 1（只有 import 那行）
```

### 形态 D：用户可见文案（7 处，纯字面串）

| # | 位置 | 文本 |
|---|---|---|
| D1 | `src/output/reasoning.py:101` | `"计算效应量 η²（小=0.01, 中=0.06, 大=0.14）及其置信区间",` |
| D2 | `src/output/reasoning.py:328` | `"η²H 效应量：0.01小/0.06中/0.14大。"` |
| D3 | `src/output/learning_card.py:162` | `"5. 报告效应量η²（0.01小/0.06中/0.14大）",` |
| D4 | `src/output/learning_card.py:172` | `"η²": "…η²=0.06意味着6%的分数差异归因于分组"` |
| D5 | `src/experiment_design/preregistration.py:306` | `f"预期至少两组间差异具有中等效应量（η² ≥ 0.06）。"` |
| D6 | `src/ui/undergrad_wizard.py:3121` | `📏 <strong>η² (eta-squared)</strong>: 0.01=小, 0.06=中, 0.14=大`（UI HTML 说明块） |
| D7 | `src/paper_writer/section_writers.py:869` | `f"大效应量阈值（d > 0.8, r > 0.5, η² > 0.14），甚至超过了…"` |

- ⚠ **D7 所在文件此刻是兄弟班在途脏件**（`M src/paper_writer/section_writers.py`），行号读数可能漂移 ⇒ 主班引用前先 `rg -n '大效应量阈值' src/paper_writer/section_writers.py` 现取。
- 🔴 **字面量计数判据的适用面（本档已做 `ast` 复核，非默认成立）**：
  - A1/A2/B1 与 C1/C2/C3 的阈值经 `ast.walk` 确认为 **`ast.Constant` 数值字面量**（`psychology_report_format:39/40`、`power_analysis:64` 各读回 `[0.01, 0.06, 0.14]`；三处判分支的比较行同样读回三个 Constant）⇒ `rg` 口径对它们成立。
  - D 类 7 处：数值在**字符串常量内部**（`ast` 数值扫描返回 `NONE-ON-LINE`，符合预期），其中 D5/D7 还套在 f-string 里但 `{}` 插值的是别的字段、`0.06`/`0.14` 仍是硬写文本。
  - ⚠ **推论**：若将来有人把档位表改成 `.map()`／f-string 派生（`rg '0\.06'` 当场静默读 0），本 census 的判据必须换成**运行时取源**（import 表并按 8 个边界点实调，见 §二 复算命令）。
  ```
  $ PYTHONPATH=. .venv/Scripts/python.exe -B -c "
  import ast,io
  t=ast.parse(io.open('src/paper_writer/psychology_report_format.py',encoding='utf-8').read())
  print({n.lineno:n.value for n in ast.walk(t) if isinstance(n,ast.Constant) and n.lineno in (39,40)})"
  ```
- **字面命中 ≠ η² 复写点，须逐行归因**（纪律 §九.3／§十.3「双轨对到位并解释差额」）：
  - `rg '0\.06'` ⇒ **15 命中 ＝ 12 计入 ＋ 3 排除**。排除的 3 行是 CFA 拟合指标、与效应量无关：`sem.py:109`（`rmsea <= 0.06`）、`academic_literature.py:46`（`cfa_rmsea: 0.06`）、`llm_engine_premium.py:949`（RMSEA 文案）。
  - `rg '0\.14'` ⇒ **11 命中 ＝ 11 计入 ＋ 0 排除**（`section_writers.py:869` 同句带 d/r，但该句确含 `η² > 0.14`，计入 D7）。
  - `rg '0\.01' | rg -i 'eta|η'` ⇒ **8 命中**，对应 A1/A2/B1/C1(:627)/D1/D2/D3/D6 的 η² 侧行；C2/C3 的 0.01 字面量不含 η 字样故不在此列（已按位点入表）。`SIG_MARKS` 的 `0.01: "**"` 是 p 值档、非 η²，语义过滤已排除。
  - **计数单位**：C 类三处判分支各写 3 个阈值字面量，本档按"处"计 **3** 次而非按字面量计 9 次 ⇒ 总面 **13 处 / 9 文件**，不是 21 行。

---

## 二、边界语义实测（完成标准④）

三处活判分支在同一组边界点上的**运行时读数**（`_interpret_eta_sq` 与 `_classify_effect_size` 直接 import 调用；validity 的 `>=` 降序按其源码 :461-466 等价复现）：

| η² 取值 | C1 `interpretation._interpret_eta_sq` | C2 `validity`(anova/η²) | C3 `defense_qa._classify_effect_size` | 分档是否一致 |
|---|---|---|---|---|
| 0.0 | 效应量很小。 | 极小 | 可忽略 | ✅ 同档（措辞异） |
| 0.009 | 效应量很小。 | 极小 | 可忽略 | ✅ |
| **0.01** | 属于小效应量。 | 小 | 小 | ✅ **0.01 → 小** |
| 0.059 | 属于小效应量。 | 小 | 小 | ✅ |
| **0.06** | 属于中等效应量。 | 中 | 中等 | ✅ **0.06 → 中** |
| 0.139 | 属于中等效应量。 | 中 | 中等 | ✅ |
| **0.14** | 属于大效应量，组间差异具有重要的实际意义。 | 大 | 大 | ✅ **0.14 → 大** |
| 0.2 | 同上 | 大 | 大 | ✅ |

复算：

```
$ PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -B -c "
from src.output.interpretation import _interpret_eta_sq as I
from src.paper_writer.defense_qa import _classify_effect_size as C
def V(x):
    return '大' if x>=0.14 else '中' if x>=0.06 else '小' if x>=0.01 else '极小'
for v in (0.0,0.009,0.01,0.059,0.06,0.139,0.14,0.2):
    print(v, I(v), V(v), C(v,'eta_sq')[0])"
```

**结论（工程口径，不涉数值对错）**：

1. 🔴 **`0.06` 的归属在全仓三处活判分支上已经统一为「中」**，`0.01`→「小」、`0.14`→「大」同理。卷宗前提里"小于号开区间"与"含边 `>=`"两种写法**给出同一归属**——它们是互补写法（`x < b` 划上界 vs `x >= b` 划下界），不是两套边界。
   ⇒ 完成标准④要求的"现边界行为如实记录（含 0.06 归属）"读数为：**0.06 落「中」，且无处与之相反**。
2. ⚠ **真正不一致的是底档措辞与档位名词**：同一档在三处分别叫「效应量很小。／极小／可忽略」（底档）与「中等效应量／中／中等」（中档）。这是**输出层观感分叉**，与阈值数值无关。
3. `power_analysis.py:64` 的"无边界语义注记"确为事实（:57 只有 `# ── 效应量基准（Cohen的约定） ──` 一行注释，`_label_effect` docstring 为「给效应量打小/中/大标签」，均未说明含边/开区间），**但该行是死数据**（§一 B1），所以缺注记当前**不构成任何线上风险**；一旦按 §四 案 A 把它接活，缺注记立刻变成风险。

---

## 三、影响面分类：哪些能机械换引用、哪些不能

| 类别 | 点位 | 能否机械替换为表引用 | 阻碍点 |
|---|---|---|---|
| 判分支（可直接改） | C1 `interpretation.py:626-634` | **部分**：阈值可引表，但**返回值是整句文案**（4 句中文，含"组间差异具有重要的实际意义"这类非档名内容） ⇒ 只能"表供阈值＋句留本地"，或另建 档名→整句 映射 | 换纯引用会丢文案 |
| 判分支（可直接改） | C2 `validity.py:460-466` | ✅ **最干净**：裸档名「小/中/大/极小」，与 `EFFECT_BENCHMARKS` 元组表的 `(阈值, 档名)` 形状**同构**，可整段换成 `_label_effect` 式循环 | 仅"极小"这一档在两表里都不存在（表只有 3 档），需补底档约定 |
| 判分支（可直接改） | C3 `defense_qa.py:64-71` | ✅ 阈值可引表；但返回 `(档名, 释义)` 二元组，**释义文本不在任何表里** | 需扩表结构为三元组 |
| 用户可见文案（不可机械替换） | D1 D2 D3 D4 D5 D6 D7 | ❌ 全部是**给人读的教学/预注册/UI 说明文字**，句式、量纲表述、是否带 `≥` 各异（D5 甚至只引用中档下界一个数） | 只能用 `.format`/f-string 从表里插值，插值本身要重写文案 |
| 表体（本身即候选真源） | A1 A2 B1 | 不适用 ⇒ 三行值逐字同形，A1/A2 由测试钉死等值 | 需先决定谁是源（§四） |

⇒ **可机械收敛面 = 1 处（C2）；半机械 = 2 处（C1/C3，阈值可换、文本要留）；不可机械 = 7 处（D 类文案）**。这与"至少 5 处复写、换引用即可"的直觉差距很大。

---

## 四、两案对比

### 案 A：单一来源（把 `EFFECT_SIZE_GUIDE.eta_sq_p` 立为真源，其余点换引用）

| 项 | 实测估算 |
|---|---|
| 涉及文件 | **9 个**（psychology_report_format / power_analysis / interpretation / validity / defense_qa / reasoning / learning_card / preregistration / undergrad_wizard；再加在途件 `section_writers.py` ⇒ 10） |
| 需先做的准备 | `EFFECT_SIZE_GUIDE` **当前生产零读取** ⇒ 案 A 实质是"把它从死表接活"，需新增跨模块 import（`src/output` 与 `src/analysis` 反向依赖 `src/paper_writer`）——**引入分层依赖方向问题**，不是单纯去重 |
| 结构改造 | 现表是 `{小:0.01,中:0.06,大:0.14}`，容不下 C2/C3 需要的**底档**（极小/可忽略）与 C3 的**释义文本**、C1 的**整句文案** ⇒ 表必须扩形状 ⇒ 会同笔打断 `test_psychology_report_format_golden.py:202`（8 指标全等黄金快照）与 :217/:224/:227 参数化 |
| 文案面 | 7 处 D 类只能改写成插值模板，属**文案重写**，需内容复核（非机械） |
| 门禁风险 | `tests/test_psychology_report_format_golden.py` 是"盘上现值原样钉住"件（其 docstring :15 自述），扩表＝改钉桩基线；且 `tests/test_golden_stats.py` 系另有 `--freeze` 基线机制 ⇒ 🔴 **纪律 §十.2：需要 `--freeze` 重钉基线的单一律停在人工闸后** |
| 净收益 | 阈值字面量从 9（C 类）＋5（A/B 表）收敛到 3；边界语义获得唯一注记 |

### 案 B：分层收敛（先只收"表"与"判分支"，文案面降级为注记）

1. **B-1 只碰死数据**：`EFFECT_BENCHMARKS["eta_sq"]`（B1）当前 0 读取 ⇒ 要么删（但 `test_psychology_report_format_golden.py:234` 只管 A1/A2，B1 无钉桩，需先确认无测试钉 6 键集），要么**保留并补一行边界注记**（"含下界，`>=`"）。推荐**补注记**，零行为变更。
2. **B-2 统一档名而不是统一数值**：给 C1/C2/C3 的档位措辞建一个 `{档名: 中文整句}` 的**输出层映射**，三处判分支只产档名（小/中/大/极小），文案在各自出口渲染。这样**阈值数值一行都不动**（守红线），只消除 §二.2 的观感分叉。
3. **B-3 文案侧只加"同源"注记**：D1–D7 七处在源码里加一行 `# 与 EFFECT_SIZE_GUIDE.eta_sq 同步，改表须同批改此条`——注意纪律 §十.4/§十一.4：**若某判据要求"某字面串 0 命中"，注释含该串会自造命中**；η² 域当前无此类判据，但仍应优先在档里维护清单而不是往 7 个生产文件里撒注释。
4. 涉及文件：**2–3 个**（interpretation / validity / defense_qa，可选加 power_analysis 注记）；不碰 `EFFECT_SIZE_GUIDE` 表形状 ⇒ **不触发 `--freeze`、不改任何阈值数值**。

### 推荐：**案 B（B-1 ＋ B-2 优先，B-3 以本档清单替代撒注释）**；案 A 不推荐由执行手落地

理由：
1. 卷宗设想的"唯一真源" `EFFECT_SIZE_GUIDE.eta_sq_p` **在生产里是死表**（§一 A：读取 0 处），案 A 因此不是"归位"而是"新建真源＋跨层接线"，成本与风险都远高于清单给人的第一印象。
2. 案 A 必改 8 指标黄金快照（`test_psychology_report_format_golden.py:202`）并可能触发 `--freeze` ⇒ **按纪律 §十.2 属人工闸后事项，不在执行手授权内**。
3. 卷宗最担心的**边界语义其实已经一致**（§二 实测 0.01→小、0.06→中、0.14→大 三处同档），所以"边界口径统一"这条收益**已经存在，无需重构去换**。
4. 残余真缺陷只有两条，且都是低风险可单独闭：**(a) 底档措辞三样**（很小/极小/可忽略）、**(b) `EFFECT_BENCHMARKS["eta_sq"]` 是死行且无边界注记**。

---

## 五、必须交人工的出口（红线，本档一律未判）

| # | 事项 | 为什么不做 |
|---|---|---|
| 1 | 🔴 **0.01/0.06/0.14 这组 Cohen η² 基准是否适用于本仓各方法**（η² vs 偏 η² vs η²H 是否应共用同一组档；D2 的 η²H 与 D5 的预注册下界是否同口径） | **红线＝统计数值结论**。只做复写点收敛的工程裁决，不改任何数值、不判数值对错 |
| 2 | 🔴 **底档（η²<0.01）应叫"极小"还是"可忽略"，以及它算不算一档** | 这是**用户可见统计标签**的取舍，会改变报告文字的解释倾向 ⇒ 同属人工裁决 |
| 3 | 案 A 若落地需重钉 `tests/test_psychology_report_format_golden.py:202` 的 8 指标全等快照（可能连带 `--freeze`） | 纪律 §十.2「需 `--freeze` 重钉基线的单一律停在人工闸后」 |
| 4 | B-1 中"删除 `EFFECT_BENCHMARKS["eta_sq"]` 死行"的选项 | 删行＝改表键集，可能触发未识别的键集钉桩；且**改计数口径一律停手**（纪律 §五.4）。本档只推荐"补注记"这一非破坏形态 |
| 5 | `psychology_report_format.py` 的 `eta_sq`/`eta_sq_p` 双行是否合并成单行 | 由 `test_...golden.py:234` 显式钉为"必须等值"，合并＝翻已入库的产品决策；另需人工确认偏 η² 是否要有独立档位表 |
| 6 | D7 `section_writers.py:869` 行号 | 该件**此刻是兄弟班在途脏件**，本班只读引用；主班引用前请现取 |

---

## 六、完成标准对照（逐条实测）

| 标准 | 读数 | 判定 |
|---|---|---|
| ① 档内复写点清表与 `rg -n 0\.06 src/ --glob *.py` 实测逐条对得上 | §一 表内每条 A/B/C/D 位点均可被 `rg -n '0\.06'`／`'0\.14'`／`'0\.01'` 命中并逐字对应。逐行归因：`0.06` **15 命中＝12 计入＋3 排除**（`sem.py:109`、`academic_literature.py:46`、`llm_engine_premium.py:949`，均为 CFA/RMSEA 族）；`0.14` **11 命中＝11 计入＋0 排除**；`0.01` η 语境 **8 命中**。计数单位按"处"而非按字面量行 ⇒ **13 处 / 9 文件** | ✅（双轨：`rg` 字面轨 ＋ `ast`/运行时轨，差额逐行归因，未取单个总数） |
| ② 含两案对比与推荐案 | §四 案 A/案 B 各列 6 项成本读数＋推荐案 B 及 4 条理由 | ✅ |
| ③ `git status --porcelain` 仅该档新增 | 见 result「验收情况」③；净差集＝本档 1 份（其余为兄弟班在途件） | ✅（净差集口径） |
| ④ `interpretation.py:627-631` 现边界行为如实记录（含 0.06 归属） | §二 读数表：`< 0.01`→"效应量很小。"、`< 0.06`→"属于小效应量。"、`< 0.14`→"属于中等效应量。"、else→"属于大效应量，…"；**η²=0.06 落「中等」**，且与另两处活判分支同档 | ✅ |
