# s927-04 · 逐对 n 输出契约 与 非参数效应量 CI 补齐路径（设计稿，零码改动）

- 班：`qoder-executor-20260927-1820-psy76`（波次 22 只读采集位）
- 仓／cwd：`D:\code\psy-analysis`｜HEAD `6bf76af`｜开工 `git status --porcelain` 12 行
- 判据：①输出契约表 ②CI 补齐分步计划 ③零码改动 —— **本件只做设计，`src/` 一字节未写**
- 🔴 红线自证：本班**未选任何效应量数值／CI 方法／阈值**；§5 三处取值取舍全部写成给人拍的判断题

---

## 0. 版本基线（引前必读：本班读的关键件是「工作树版」）

| 件 | 与 HEAD 关系 | 依据 |
|---|---|---|
| `src/analysis/result_card.py` | 🔴 **脏件，未提交**：`git diff --numstat HEAD` = **180 加／13 删**；mtime `2026-09-26 11:47:36`；1,567 行 vs HEAD 1,400 行 | 本班实测 |
| `src/analysis/{anova,ttest,nonparametric,correlation,effect_size_ci,result_schema}.py` | ✅ 与 HEAD **零差**（`git diff --stat HEAD -- <六件>` 输出为空） | 本班实测 |
| `src/output/interpretation.py` | 脏件 2/2（波次 18 起停在闸外），**本班未读未碰**（本单不需要） | 在册登记＋本班零接触 |

🔴 **锚点前提的版本陷阱**：b040 那班的全部产出（`_build_corr_matrix_card`、`n 取值` 串、`fisher_z_ci` import、Cohen 大小解读）**只在 `result_card.py` 工作树版里，HEAD 里一枚都没有**（`git show HEAD:src/analysis/result_card.py | grep _build_corr_matrix_card` → 零命中）。
⇒ 本档所有「现状」读数在**该脏件被 revert／丢弃后即刻失效**；主班收班时请先决定 b040 是否入库，再决定本契约往哪一版对齐。
⚠ 另记一处**自报与盘上不符**：b040 结果件自述 `+173/−6`，盘上实测 `+180/−13`（差 7/7）——本班不判成因（可能是 b040 之后另有在途编辑），只登记。

---

## 1. 锚点（b040 卷宗背景三句）对账

| # | b040 原话（`done/20260925-120700-b040.result.md`） | 本班复算 | 判定 |
|---|---|---|---|
| A1 | 「矩阵 `n_matrix` 同值时已给单一 n」 | 合成 n=60 无缺失：`technical_notes[0] = 各变量对样本量 n = 60。` | **成立（仅工作树版）** |
| A2 | 「逐对样本量不等时可在 technical note 列 n 取值集合，最好逐对 n APA 串」 | 构造 z 缺 3 行／y 缺 2 行后：`n 取值 [55, 57, 58]。`；逐对 APA 串**只有头对**带 `（n = 58）`，其余两对的 n 在**任何导出面上都不存在** | **部分成立 ⇒ 缺口比 b040 说的更大**（见 §2） |
| A3 | 「非参数族效应量 CI 补齐……**其 dataclass 部分无 CI 字段，需先补统计层**」 | 🔴 **否证**：`NonParamResult` 第 16 行**就有** `effect_size_ci: Optional[str]`；且 mann_whitney／wilcoxon **已产出数值 CI 串**（实测 `'[-0.236, 0.32]'`／`'[-0.36, 0.36]'`），kruskal／friedman 产出散文占位串。真阻塞**不在统计层，在卡层的字段名接缝**（§4 表 T4） | **锚点前提不成立** ⇒ 分步计划 accordingly 重排（§6），按磁盘实况收窄，不据此判 failed |

⇒ 结论：**「补统计层」这一前置任务大半已在盘上完成了**；本单真正的活是「把统计层已有的东西接到卡层／导出层」＋「把 CI 这个**名字**的三种类型收敛成一种契约」。

---

## 2. 现状面：一次相关分析里 n 与 r 的**两条分叉通路**（实测数字）

同一份合成数据（60 行，`z` 缺 3 行、`y` 缺 2 行）：

| 通路 | 件:行 | n 的口径 | 读数 | r(x,y) |
|---|---|---|---|---|
| 统计层→结果卡 | `correlation.py:95-104` → `result_card.py:324-392` | **逐对成对删除** `n_matrix` | 头对 `（n = 58）`；note `n 取值 [55, 57, 58]` | **0.723** |
| APA 表格 | `src/output/apa_tables.py:87-123` | **整体删除后重算**（`df[vars].dropna()`） | 表注 `N = 55. *p < .05 …` | **0.7106** |
| 事后功效 | `post_hoc_power.py:99-115` `_extract_correlation_n` | 非对角 **min** | `55` | — |

⇒ 同一结论在同一份报告里会以 **三个 n（58／57／55）＋两个 r（0.723／0.711）** 出现，且 APA 表**不走分析结果、自己重算一遍**相关系数。这是「n 取值集合 vs 同值单 n」这条卷宗标题背后真正的病灶：**不是缺一种格式，是三条通路没有共同的分母口径**。

⚠ 附带登记（不修）：`_extract_correlation_n` 的行内注释写「取非对角线**最大**值（每对相关用的**最小** n）」——注释自相矛盾，代码走 `min`；且 `n_matrix` 含 NaN 时 `int(min([...]))` 会抛异常被 `except` 吞掉 ⇒ 静默返回 `0`。功效分析的输入 n 属统计数值面，本班不动。

---

## 3. 判据① · 逐对 n 输出契约（设计表）

### T1 · 何时给单 n / 给集合 / 给逐对 APA 串

| 规则 | 触发条件（可对代码判定的形式） | 输出形态 | 落点 | 现状 |
|---|---|---|---|---|
| R1 | 逐对 n 全相等（`\|{n_ij}\|==1`），且来源为**完整数据**（无成对删除） | `（n = 60）` 单值进 APA 串；note 再给一行「各变量对样本量 n = 60。」 | `apa_text` + `technical_notes` | ✅ 已有（工作树版） |
| R2 | 逐对 n 全相等但**存在被删除行**（分母 ≠ 原始行数） | 单值 + **必须并列原始行数**：`（n = 57，原始 60 行中 3 行含缺失）` | 同上 | ❌ 缺（现在无法区分「本来 57」与「60 删成 57」） |
| R3 | 逐对 n **不全等**（成对删除生效） | **逐对串**：每条 effect_sizes 项 `r(x, z)=0.721（95% CI […], n = 57）`；APA 头句仍只给头对；note 给**排序后的取值范围** | `to_markdown` 效应量行 + `technical_notes` | ◐ 部分：note 有 `[55, 57, 58]`（裸 Python list repr，不是人读串），**逐对 n 在导出面上完全丢失** |
| R4 | 逐对 n 集合基数 > 阈值（**阈值取值见 §5-J4，人拍**） | 折叠成 `n ∈ [55, 58]（3 个取值）` 而非逐个列出，避免 APA 串爆长 | `technical_notes` | ❌ 缺，且折叠阈值未定 ⇒ 本班不填数 |
| R5 | `n_matrix` 缺失或该格 NaN | 输出 `n 未记录`并**禁止**由 `df+1`/`N−k` 反推冒充实测 n | 同上 | ❌ 缺（现 `paired_ttest` 就在用 `df+1` 反推，见 R6） |
| R6 | 只有自由度可反推 n（配对 t） | 允许反推但**必须标注推得**：`配对样本量 n = 30（由 df = n−1 反推）` | `technical_notes` | ✅ 已有（`result_card.py:264`）——**R5/R6 的差别就是「反推」要不要挂标签**，本契约要求必须挂 |
| R7 | 报告级（多方法同框） | **分母口径一致性检查**：同一变量集合在「卡」与「APA 表」两侧的 n 若不等，必须显式印出「表按整体删除 N=55／卡按成对删除 n=57~58」 | `apa_tables` note + 卡 note | ❌ 缺（§2 病灶的收口规则） |

### T2 · 载体契约（n 放进哪个字段，才能既进导出又进闸）

| 面 | 建议契约（设计，不实现） | 兼容性论证 |
|---|---|---|
| `card.effect_sizes[]` 条目 | 增**可选**键 `n: int \| None`；单对方法同样填 | `to_markdown` 现在**不读** `n` 键（本班实测：`to_markdown` 函数体内 `'n'` 键读取 = `False`）⇒ 加键**不改任何既有输出**，只有渲染端显式支持后才显形＝零回归面 |
| `AnalysisResultCard` | 增 `n_report: dict`（`{"kind":"single\|set\|unknown", "values":[...], "source":"pairwise\|listwise\|df_inferred", "raw_rows":int}`） | 纯增量字段，`__post_init__` 不碰；快照类测试只钉 `_CARD_BUILDERS` 键集（44）⇒ 不受影响 |
| `result_schema.SAMPLE_SIZE_CARRIERS` | 现值 `('n','n_cases','n_obs','n_valid','sample_size')`。**实测两处空转**：① `n`／`n_valid` 在 `src/analysis/*.py` 的**任何 dataclass 里都不存在**（AST 普查，见 T3）；② 实际存在的 `n1`/`n2`/`n_matrix`/`n_total`/`n_complete`/`avg_cluster_size` **一律未登记** ⇒ `find_sample_size()` 对 mann_whitney／anova／ttest／corr_matrix **四种结果全部返回 `None`**（实测，四条 issue 逐字相同） | 扩元组＝改契约面，会牵动 `validate_result`/`enforce_result` 的 issue 计数与在册钉桩 ⇒ 属需人拍的范围题（§6 Step 2 单列） |

### T3 · n 字段登记普查（AST，`src/analysis/*.py` 顶层 dataclass）

| 字段名 | 是否在册载体 | 出现处 |
|---|---|---|
| `n_cases` | ✅ | `factor_analysis::EFAResult`、`reliability::ReliabilityResult`、`validity::ValidityResult` |
| `n_obs` | ✅ | `cfa::CFAResult`、`logistic_regression::LogisticResult`、`manova::MANOVAResult`、`sem::SEMResult` |
| `sample_size` | ✅ | `assumption_router::RouteDecision`、`method_recommender::ResearchDesignInput`、`result_schema::SchemaReport` |
| `n` / `n_valid` | ✅ 在册但**零声明** | —— 两个"名义载体"在本层没有任何宿主 |
| `n_matrix` | 🔴 未登记 | `correlation::CorrResult`（唯一的逐对 n 源） |
| `n_total` / `n_complete` | 🔴 未登记 | `data_quality::DataQualityReport`、`hlm::HLMResult` |
| `n_groups` / `n_items` / `n_factors` / `n_events` / `n_covariates` / `avg_cluster_size` | 🔴 未登记（且多数**不是样本量**，是维度） | 各类 |

⇒ 设计要点：**登记面必须区分「样本量」与「设计维度」两类 n**，否则把 `n_items` 塞进载体表会让 `find_sample_size` 给出题目数当样本量这种错分母。

---

## 4. 判据②前置 · CI 现状契约（一名三型，这才是补齐的真门槛）

### T4 · `effect_size_ci` 这个名字在本仓的三种类型（全部实测）

| 模块／件:行 | 声明类型 | 运行时实值 | 卡层取用方式 | 结果 |
|---|---|---|---|---|
| `ttest.py`（`independent_ttest`） | `effect_size_ci_lower/upper: Optional[float>` | `-1.159` / … | `getattr(...,_lower)` 两个 float | ✅ 正常渲染 |
| `chi_square.py::ChiSquareResult` | 同上 `_lower/_upper` | float | 同上 | ✅ 正常渲染 |
| `anova.py:16` | `effect_size_ci: Optional[str]` | **字符串** `'[0.486, 0.173]'` | `_build_one_way_anova` 走 `float(es_ci[0])`/`float(es_ci[1])`（要的是**下标可取的数值对**） | 🔴 对 str 下标拿到 `'['` 与 `'0'` → `ValueError` → **被 `except (TypeError,ValueError,IndexError): pass` 静默吞掉** ⇒ η² CI **从未进过 APA 串** |
| `nonparametric.py:16` | `effect_size_ci: Optional[str]` | mann_whitney `'[-0.236, 0.32]'`／wilcoxon `'[-0.36, 0.36]'`＝**数值串**；kruskal／friedman＝**散文串** | **卡层三个 builder 根本不读这个字段**（见 T5） | 🔴 统计层算了，卡层丢了 |
| `correlation.py::CorrResult` | `ci_low_matrix/ci_high_matrix: DataFrame` | 逐格 float | `_build_corr_matrix_card` 逐格读 | ✅ 唯一走通的矩阵面 |

### T5 · 非参数族卡层的「字段名接缝」：读的名字与有的名字**交集为空**

| builder | 它 `getattr` 的名字 | `NonParamResult` 实际有的 | 交集 | 卡的实测输出（合成数据） |
|---|---|---|---|---|
| `_build_mann_whitney` | `u_statistic`/`U`、`z_value`、`r_effect`/`rank_biserial`、`n1`、`n2` | `statistic`、`effect_size`、`effect_size_name`、`effect_size_ci`、`group_stats`（N 在 DataFrame 列里） | **∅** | `warnings=['Mann-Whitney U 检验结果缺少关键统计量']`，`apa_text=''`，`effect_sizes=[]` |
| `_build_wilcoxon` | `w_statistic`/`W`/`T`、`z_value`、`r_effect`、`n` | 同上（`statistic`、`effect_size`） | **∅** | `warnings=['Wilcoxon 检验结果缺少关键统计量']`，`effect_sizes=[]` |
| `_build_kruskal_wallis` | `h_statistic`/`H`、`df`、`eta_squared`/`epsilon_squared` | 同上（`statistic`、`effect_size`；`df` 无此字段） | **∅** | `warnings=['Kruskal-Wallis 检验结果缺少关键统计量']`，`effect_sizes=[]` |
| friedman | —— | —— | **注册表里根本没有这个键** | `warnings=["方法 'friedman' 暂无专用结果卡模板"]`，`technical_notes=['结果对象类型: NonParamResult']` |

⇒ 也就是说：**非参数四族今天的结果卡上没有任何效应量、没有 n、没有 CI**——不是"CI 缺字段"，是**整张卡在空转**。`KNOWN_ISSUES.md` 里也**没有** friedman 条目（grep 零命中），只在 :142 把 Mann-Whitney/Wilcoxon/Kruskal-Wallis 列为「完整支持」，把 friedman 漏在清单外。

---

## 5. 🔴 四道必须给人拍的判断题（本班一律不选案）

> 形状：每题给「各案后果 + 可复算入口 + 谁拍」。这些都是**效应量数值／CI 方法／阈值**面，命中 brief §4 红线，执行手不签。

**J1 · ANOVA η² 的 CI 上下界倒置且不含点估计。**
实测（`grp` 三组各 25，seed=7）：`η² = 0.3549`，`effect_size_ci = '[0.486, 0.173]'` —— 先验上界被标成下界。成因定位在 `src/analysis/anova.py:23-49 _eta_sq_ci`：`ncp_lower` 用 `ncf.ppf(α/2, …)` 求根、`ncp_upper` 用 `ppf(1−α/2, …)` 求根；对固定 λ 有 `ppf(α/2) < ppf(1−α/2)`，要令低分位等于观测 F 就需要**更大**的 λ ⇒ 两个根的角色互换。
- 案甲（交换两侧）：CI 变 `[0.173, 0.486]`，η² 落带内 ⇒ 但**这是对既有非中心 F 反解的重解释**，须与 R/`MBESS::ci.R2` 一类参考值对拍后才能签。
- 案乙（保留现值、只在卡上停止渲染）：输出更少但不再自相矛盾。
- 案丙（改数值对字段 `_lower/_upper`，与 ttest/chi_square 同型）：见 J3，属接口收敛。
- 复算入口：`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B D:/code/tmp/qoder-executor-20260927-1820-psy76/probe_s92704_b.py`（Q9/Q10）；或 `anova.one_way_anova(df,'score','grp').effect_size_ci`。
- 谁拍：统计口径＝人工；**且这是"要不要动数值"的决定，不是"要不要动显示"的决定**。
- ⚠ 现在这道缺陷在盘上是**隐形的**：正因为 J3 那个 `except: pass`，倒置的串从没被印出来过 ⇒ "修显示"会**第一次把它显形**，两件事必须同一批看，不能拆开先修显示。

**J2 · Mann-Whitney／Wilcoxon 的 r 与其 CI 的方法适配。**
实测两点：①`mann_whitney` 的 r 由 p 反解（`z = |norm.ppf(p/2)|`，`nonparametric.py:64-65`），⇒ 恒非负、且不是教科书说的秩双列相关，但 `effect_size_name` 写着「r (秩双列相关)」；②Wilcoxon 实测 `effect_size = -1.0` 而 `effect_size_ci = '[-0.36, 0.36]'` —— 因 `0 < abs(r) < 1` 的护栏在 |r|=1 时把 `z_r` 置 0，于是给出的是 **r=0 的 CI**，一个不含点估计、也不含 −1 的带。
- 案甲（改用真正秩双列相关 `1−2U/(n1·n2)` 作点值，CI 走对应公式）：点值会变号会变数，**影响所有历史报告的可比性**。
- 案乙（保持现点值，CI 改 bootstrap 或改置 `None`+说明）：不改点值，只改"有没有带"。
- 案丙（保持现状，仅在卡上标注方法名与推导式）：零数值变动，但把"CI 不含点值"这种形态继续留在盘上。
- 复算入口：`probe_s92704.py`（Q5、Q7）。
- 谁拍：方法学＋统计数值＝人工；kruskal／friedman 的两条散文串（「标准CI计算方法尚未确立／未知」）与本决策**同源**，请一并裁（是否统一走 bootstrap、b 取多少、用不用分位数法）。

**J3 · 卡层 `except …: pass` 让「有 CI」与「CI 解析失败」不可区分。**
`result_card.py:300-308`。后果：任何 CI 契约改动（§4 收敛、J1、J2）都**不会**翻红，只会静默少印一串字。
- 案甲（失败即 `card.warnings.append("效应量 CI 无法解析")`）：出声，但可能一次性叫醒一批存量卡 ⇒ 需先估受影响的在册钉桩数。
- 案乙（失败即抛）：最强，但属展示层行为面变更，会牵动 `test_analysis_result_card.py`（11 例）与 `test_result_card_v2_methods.py`（22 例）。
- 案丙（不动，改在 `result_schema` 侧加一条 issue）：与 §6 Step 2 合并做。
- 谁拍：展示层行为＋门禁形状＝主班与人工共同看；**本班倾向（仅登记为倾向，不构成裁决）：任何 CI 补齐批次都必须与 J3 同批，否则"补齐"不可证**。

**J4 · 逐对 n 折叠阈值（R4）。**
`n 取值 [55, 57, 58]` 三值可读，30 变量的矩阵就是几百值。折叠成范围还是逐个列、基数阈值取几，**是排版阈值不是统计量**，但会决定 APA 串长度与导出面行数。本班**不填数**，交主班连同 §2 的分母口径一起拍。

---

## 6. 判据② · CI 补齐分步计划（依赖顺序＋每步门禁影响面＋回滚成本）

> 前置事实（本班自己复点，不引用任何档）：
> **本仓没有 `--freeze` 机制。** 复点命令与读数：
> `git grep -in "freeze"` → 命中 17 行，其中 `.py` 文件 **0 命中**（`--freeze` 字面量只出现在 `docs/insights/*.md` 的引述里：`psy-eta-threshold-caliber.md:161/169/175/187`、`psy-instance-lock-clock-seam-20260925.md:136`、`psy-session-key-implicit-census-20260924.md:122`、`s927-03-star-caliber.md`）；非 `--freeze` 的 `freeze` 命中全是 `pip freeze`（`README.md:29`、`requirements*.txt`、`install.bat:68`）与 `requirements-freeze`（`psy-interpreter-caliber-20260915.md:16`）。
> `grep -rn -i "freeze" --include="*.py" .`（排 `.venv`/`node_modules`）→ **零输出**。
> `tests/conftest.py:57-63` 唯一 `pytest_addoption` = `--run-benchmark`；`pytest.ini`（在途脏件）`addopts = --strict-markers`，无自定义插件。
> `scripts/research_release_gate.py`（未跟踪在途件）既无 `freeze` 也无 `correlation`（本班 `git grep` 全域扫到该件，`freeze` 命中 0）。
> ⇒ **等价闸形态＝硬编码全等快照**：`tests/test_result_card_registry_snapshot.py` 的 `BASELINE_REGISTRY_KEY_COUNT = 44` + `BASELINE_REGISTRY_KEYS` 排序逐位比对；`tests/characterization_redline.py:50-51` 用 `pytest.approx` 钉 ttest 的两个 CI 浮点界。
> ⚠ 顺带否证一条在册话术：`psy-eta-threshold-caliber.md:161/175` 说「`test_golden_stats.py` 系另有 `--freeze` 基线机制」——**本仓复算不通过**（同上，`.py` 零命中）。

| Step | 做什么 | 硬依赖 | 门禁影响面（点名到件） | 回滚成本 | 权限 |
|---|---|---|---|---|---|
| **0** | 先定 b040 的 `result_card.py` 是否入库（§0） | —— | 不入库则本表全部对不上 | 低 | **主班收班** |
| **1** | 卡层名接缝对齐（T5 三处 getattr 改读 `statistic/effect_size/effect_size_name`＋`group_stats["N"]`；friedman 补一个 builder 或显式登记"无卡"） | Step 0 | 🔴 `test_result_card_registry_snapshot.py`：注册表键集 44 → **45**（加 friedman）⇒ 排序全等快照**必红**＝等价于重钉基线；`test_analysis_result_card.py`(11)/`test_result_card_v2_methods.py`(22) 断言集会变绿向 | 低（纯展示层，可整体 revert） | **人工闸**（改基线快照） |
| **2** | n 载体登记面收敛（T2/T3：`SAMPLE_SIZE_CARRIERS` 拆「样本量」与「设计维度」两组；`find_sample_size` 现在四条路径恒 `None`） | Step 1 的读数 | `result_schema.validate_result`/`enforce_result` 的 issue 计数面；凡钉 issue 的在册件 | 中 | 人工（契约面） |
| **3** | CI 类型收敛为**一种**：全仓改 `effect_size_ci_{lower,upper}: Optional[float]`，散文占位改 `None` + 单独 `ci_note` 字段（T4 三型归一） | Step 1；**J1/J2 必须先有裁决** | 🔴 `test_characterization_redline.py:50-51`（数值钉 ttest 界）、`test_effect_size_ci.py`（含 :98 那条 `0 <= lower <= upper` 不变量，**该不变量目前只覆盖卡方，不覆盖 ANOVA**）、`anova.py`/`nonparametric.py` 的字段改名面 | **高**（改名牵动 dataclass 字段名，且 `field_lineage` 登记表按字段名钉；`tests/test_analysis_field_lineage.py` 64 例含"锚点改名即红"） | **人工闸** |
| **4** | 逐对 n 进导出（R1–R7：`effect_sizes[]` 加 `n` 键＋`to_markdown` 渲染＋R7 分母一致性行） | Step 2 | `to_markdown` 不读 `n` ⇒ 加键零回归；渲染端一改，`test_e2e_resultcard_paperpreview.py` 与在册 **`download_button` AppTest 限制**（b040 已登记该件 1 例存量红）会撞上 | 低 | 执行手可做（但**输出串是人读的**，建议主班先看形状） |
| **5** | APA 表与卡**同源**（§2 病灶：`apa_tables.correlation_matrix_table` 不再自算 `pearsonr`，改吃 `CorrResult`） | Step 4 | 🔴 会改**表注里的 N**（55→逐对）与星号（现自算），`tests/test_apa_tables.py` 全量断言 + `test_export_gate_global_scan.py` 在册红一族 | **高**（改的是已出版表格的数值） | **人工闸** |

**排序理由**：1 → 2 → 3 不可交换（先让卡出声，再谈 n 口径，最后才动 CI 字段名——名字一改，Step 1 的读数要重取）；4/5 是导出面，必须等 3 定型，否则 J1/J2 一裁，串格式重写两遍。
**最短可见路径**：Step 1 单独做完，就能让"四族结果卡空转"这件事从 `warnings` 变成真卡片——**不碰任何统计数值**，是本表里唯一零数值风险的实质修复；但它仍要红一次注册表快照（friedman 键），所以还得过人工闸。

---

## 7. 零码改动自证

- 本班对 `D:\code\psy-analysis` 的**写入件数 = 0**：产物只有本档（`docs/insights/`），探针与日志全落 `D:\code\tmp\qoder-executor-20260927-1820-psy76\`。
- 探针解释器：`.venv/Scripts/python.exe -B`（`-B` 防写 `__pycache__`；`.gitignore:2` 虽已忽略，仍按"不在仓内留临时件"办）。
- 输入全为**合成 DataFrame**（`np.random.default_rng(seed)`），**未打开 `data/` 任何库**、未 import `app.py`、未跑 pytest。
- 收班前 `git status --porcelain` 与开工逐字节对照见结果件「证据」节。
- 禁动件零接触：`src/output/interpretation.py`（波次 18 脏件）未读未写；`app.py`／`pytest.ini`／`requirements-lock.txt`／`src/analysis/cfa.py`／`tests/test_cfa_sem_golden.py`／`src/analysis/_sklearn_compat.py`／`scripts/research_release_gate.py` 均未修改（`pytest.ini`／`research_release_gate.py` 只为 §6 的 `--freeze` 复点**读过**，未改）。

## 8. 复算入口

| 件 | 内容 |
|---|---|
| `D:\code\tmp\qoder-executor-20260927-1820-psy76\probe_s92704.py` → `out_s92704.txt` | Q1–Q3 单 n／n 集合／逐对 APA 现状；Q4–Q5 四族"统计层有值 vs 卡层空转"实据；Q6 27 个 dataclass 的 n/CI 普查；Q7 CI 串形态；Q8 `to_markdown` 不读 n 的论证 |
| `...\probe_s92704_b.py` → `out_s92704b.txt` | Q9 一名三型实测；Q10 `float(es_ci[0])` 对 str 抛 ValueError；Q11 ChiSquareResult 字段注解；Q12 n 载体登记面对照；Q13 `find_sample_size` 四条路径恒 None |
| 命令 | `cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B D:/code/tmp/qoder-executor-20260927-1820-psy76/probe_s92704.py` |

## 9. 遗留（交主班）

1. §0 的版本陷阱（b040 停在闸外）不解决，本档 §2–§6 的"现状"两说；请主班先定 Step 0。
2. J1/J2/J4 三条数值/阈值题＋Step 1/3/5 三道人工闸，已按 brief §4 只出形状。
3. `KNOWN_ISSUES.md` 的「非参数＝完整支持」条目（:142）与 T5 实测（四族卡全空转、friedman 无模板）**互相矛盾**，且该档不在本班写位——请主班或下批登记型单处理。
4. 本档未进任何 `docs/insights/` 索引登账件（每波一路才能碰的面）。
