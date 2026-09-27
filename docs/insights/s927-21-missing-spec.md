# s927-21 —— 缺失机制判定（MCAR／MAR／MNAR）三组件实现规格

- 班：`qoder-executor-20260928-0120-psy83`｜波次 40 文档／裁决材料位｜仓 `D:\code\psy-analysis`｜HEAD 现取＝`f0f3f73`（取证时 porcelain 12 件，本班收工时 14 件＝我的 2 枚新文档，无其它增减）
- 卷宗锚点：`20260925-154320-0b52.result.md`（卷宗写 `outbox/`，实际在 **`done/`**——按 brief §3 属路径搬家，不算失效）
- 🔴 **本件是规格，不是统计结论**。本班未跑任何机制检验、未产出任何 p 值／效应量读数，**不判定任何队列属 MCAR／MAR／MNAR**。规格里出现的历史数值一律标「锚点件读数，本班未复现」，其复核属人工闸。
- 零码改动：`src/` ／ `tests/` ／ `scripts/` 一行未动；零 git 写操作。

---

## 0. 现状复核（本班自己跑的只读命令，引前复点）

| 项 | 现值（本班实测） | 与锚点关系 |
|---|---|---|
| 机制检验实现 | 整词 `MCAR`/`MAR`/`MNAR`（`grep -rnw`，含 `src app.py tests scripts`）＝ **3 处命中，全为提示文案**：`data_quality.py:76`、`data_quality.py:202`、`cleaning_wizard.py:170`；Little 型检验／缺失指示关联／单调性检测 **0 处** | 复现锚点第 1 条 ✅（行号一致） |
| 在册含缺失格表件 | 本班重跑普查：**42 份 CSV，含 NaN 格 0 份** | 复现锚点第 2 条 ✅（命令见 §5） |
| **新增：sentinel 不可见**（本班新发现） | pandas 3.0.3 默认 `na_values` 下：`-9`／`?`／`无`／`缺失` **不识别为缺失**（`'NA'` 才是），且列 dtype 落 `str` | 锚点只说"无 sentinel 型缺失码"；本条补的是**即便真实回收数据带了中文哨兵，现有 loader 也看不见** |
| 缺失相关阈值口径 | `data_quality.py:74`（列缺失率 >15）、`:124`（listwise 损失 >15）、`:199`（总体 >15）vs `cleaning_wizard.py:135`（总体 `> 10.0`）、`:291` 文案又写 `> 15%` | 锚点第 4 条的 15/10 分歧**仍在**，行号已刷新 |
| `pairwise` 可达性 | `data_quality.py:21` 声明四策略，`:80-86` 的 `pairwise` 分支**只写 `description_zh`、不改数据、不记 meta 计数**；`runner.py:886` `getattr(plan,"missing_strategy","listwise")`，`AnalysisPlan`（`src/parser/intent_resolver.py`）无该字段 ⇒ 实际恒 listwise | 与横幅「pairwise 是假开关（`:38`/`:8` 一带）」相符，**准确行号＝`:21`／`:38`（docstring 承诺）／`:80-86`（空转分支）** |
| 可用依赖（`.venv` 实测） | `scipy 1.18.0`／`statsmodels 0.14.6`／`pingouin 0.6.1`／`numpy 2.5.1`／`pandas 3.0.3`／`semopy 2.3.11`／`sklearn 1.5.2` | ⚠ 三处版本与 `requirements-lock.txt` **不一致**（在途件写 numpy==2.3.5，HEAD 写 2.4.4，实装 2.5.1）⇒ 规格的依赖预算按**实装**写，禁新增安装（卷宗禁"下载安装依赖"） |

`assumptions.py` 内**无任何**缺失机制条目（grep 缺失/MCAR/missing ＝ 0 命中）⇒ 本组件若登记假设属**净新增面**（与 s927-24 的 placeholder 债相邻，见 §6）。

---

## 1. 组件 A —— 缺失指示 × 已观测变量关联矩阵（含 Holm 校正）

### A.1 目的与禁止项
- 目的：量化「某变量的缺失」与「每个其它已观测变量」的关联，作为**证据表**。
- 🔴 禁止：不得在本组件内输出机制标签（不写 `MCAR`/`MAR`/`MNAR` 字样到任何结果字段或文案）。文案只写「关联证据」；机制解读属人工／组件 B。

### A.2 输入
```
missingness_association_matrix(
    df: pd.DataFrame,                       # 原始数据，未经 handle_missing（必须在 runner.py:926 之前调用）
    target_cols: Optional[List[str]] = None,# 考察缺失的列；None＝所有 isna().any() 的列
    covariate_cols: Optional[List[str]] = None,  # None＝其余全部列，按 dtype 自动分数值／类别
    min_group_n: int = 20,                  # 任一层 n<20 ⇒ 该条不检验（见 A.5 边界）
    alpha: float = 0.05,                    # 仅用于 Holm 比较，不改判据语义
) -> MissingnessAssociationResult
```
- dtype 分类口径：`pd.api.types.is_numeric_dtype` 为数值；否则走类别支路。**先做哨兵归一**（§A.6），否则 §0 的中文／`-9` 哨兵会被当类别值参与 χ²。

### A.3 算法（逐 `(m, v)` 单元格）
| 观测变量型别 | 检验 | 效应量 |  scipy 入口（实测可用） |
|---|---|---|---|
| 数值 `v` | **Welch** t（`equal_var=False`，**不得**用合并方差） | `r_pb`＝point-biserial（＝`pearsonr(I_m, v)`，符号随方向）＋ SMD（`mean1-mean0` / `sqrt((s1²+s0²)/2)`，Hedges' g 小样本校正 J=1−3/(4·df−1) 可选，须显式 flag） | `scipy.stats.ttest_ind(..., equal_var=False)`、`scipy.stats.pointbiserialr` |
| 二值／多类别 `v` | 2×k 列联 χ²；**任一格期望频数 <5 ⇒ 自动切 Fisher 精确** | φ（2×2）／Cramér's V（r×k），V＝sqrt(χ²/(n·min(r−1,c−1))) | `scipy.stats.chi2_contingency`；`scipy.stats.fisher_exact` 在 1.18 **已支持 R×C**，返回 `SignificanceResult`（🔴 **无 `.oddsratio` 属性**，只有 2×2 才返回 `OddsRatioResult`——实现必须分支取属性，否则 AttributeError） |
| 有序／Likert 当序数处理 | 可选支路：Mann-Whitney U（`scipy.stats.mannwhitneyu`）＋ rank-biserial | — | 需 `ordinal_cols` 显式声明，默认**不启用**（避免与数值支路双报同一 p） |

指示变量：`I_m = df[m].isna().astype(int)`（1＝缺失层）。比较在**该 m 的完整子集外的其它列上进行，但每个 `v` 独立取自身非缺失行**（＝pairwise 观测量），故每条记录必须落 `n_missing_layer`／`n_observed_layer`／`v_usable_n` 三个 n（这是 §0 假开关问题的防护：不得假设统一 N）。

### A.4 Holm 校正口径（写死，不留给实现自由发挥）
1. **族的定义**：一个 `m`（缺失变量）＝ 一个族。跨 `m` **不合并**校正（不同缺失变量的问题族不同；若需全局族，必须显式传 `family_mode="global"` 并在报告里写明切换）。
2. 排序：族内 `p_raw` 升序（`p_i(1) ≤ … ≤ p_i(k)`），第 `j` 小的乘 `k − j + 1`，**单调取前缀最大值**：`p_holm(j) = max_{i ≤ j} min(1, (k − i + 1) · p_raw(i))`。
3. 🔴 **比较用未舍入 p**：校正与阈值判断在 float 上完成，报告时才格式化（3 位小数；<0.001 写 `<.001`）。锚点件那条 `p=0.0498` 正是"报告位与判定位混用＋单条未校正"造出的临界假象——规格的防护就是这条。
4. 拒绝判据：`p_holm ≤ alpha`。ties 按原顺序稳定排序（`kind="stable"`），并在测试里钉住 ties 场景。
5. **禁止**数据驱动地把 Holm 换成 FDR／Bonferroni；需要另一种口径＝改本规格走人工闸。
6. 族大小上限：`k > 50` 时在结果里挂 `family_large` 警告（提示报告会淹没），不自动降策略。

### A.5 输出契约
```
@dataclass
class MissingnessAssociationResult:
    rows: List[AssociationCell]      # 每格：m, v, kind("numeric"|"categorical"), test, stat,
                                     #   p_raw, p_holm, effect_name, effect_value,
                                     #   n_missing, n_observed, usable_n, skipped_reason
    families: Dict[str, List[str]]   # m -> 该族成员 (v) 顺序（校正可追溯）
    significant_cells: List[...]     # p_holm<=alpha 的子集引用，不复制数值
    sentinel_normalized: List[str]   # 哪些列做了哨兵归一（A.6）
    warnings: List[str]
    is_fallback: bool = False        # 沿用本仓降级透出约定（s924-12 案 B 同型）
    fallback_note: str = ""
    overall_missing_pct: float
    per_column_missing_pct: Dict[str, float]   # 🔴 分母＝该列 len(df)，与 report.missing_pct（全表数值格）并存，
                                               #   两套分母必须同时输出并各自命名（§0 阈值分歧的止血）
```
- `skipped_reason` 枚举：`no_missing_cells`（**本仓现状即此**）／`insufficient_n`／`zero_variance_layer`／`non_numeric_non_discrete`／`sentinel_unresolved`。跳过格仍要进 `rows`（`p_raw=None`），**不得静默消失**。
- 文案红线：`fit/summary_zh` 类字段不得出现"随机／非随机／MCAR／MAR／MNAR"字样，只能出现「与 X 存在／不存在达阈关联（Holm 校正后）」。

### A.6 前置：哨兵归一（本组件的第一个必修点）
`loader.py:47` 走 pandas 默认 `na_values`（grep 全仓 `na_values|keep_default_na` ＝ 0 命中）。真实问卷回收常见 `-9/-1/99/999` 与 `无/缺/缺失/N/A/?`。规格要求：
- 新增纯函数 `normalize_missing_sentinels(df, codes: List[str|int], per_column: Dict[str, List]) -> (df, meta)`，**默认关闭**（`codes=[]`），显式开启才替换；
- 每次替换必须落 `meta`（列、原值、命中行数），并在 UI 上要求二次确认——🔴 属"改写数据格"动作，不得静默；
- 不做的事：不猜（比如"这列有 99 就当成缺失"），不自动探测异常大值当哨兵。

### A.7 测试与校准（规格要求，不代写）
- 夹具走 §4 路 A 的合成三臂；钉的是**实现正确性**，不是机制结论：
  - MCAR 臂：`max |effect| < 0.10` 且**Holm 后显著格数 == 0**（阈值写进 `missingness_expected.json`，沿用「带宽一律读 json」纪律，见 s927-10 对这条纪律被稀释的取证）；
  - MAR 臂：驱动变量那条**必须**在 Holm 后仍显著，且非驱动变量不显著（溢出容忍写进 json）；
  - MNAR 臂：🔴 断言写成「已观测集上不得得出与 MCAR 可区分的结论」——即显著格数 == 0，**这是负向钉，防止实现把 MNAR 报成 MAR**；
  - 边界钉：`n0<20`、层内零方差、2×k 期望频数 <5 触发 Fisher、R×C 无 `.oddsratio`、ties 稳定序、`no_missing_cells` 时 `is_fallback=False` 且有明确文案。
- 回归保护：与 `data_quality_check()` 的输出并存对照（同夹具下两组件对同一 `missing_pct` 必须同值）。

---

## 2. 组件 B —— Little's MCAR 检验 ＋ M-pattern／单调性检验

### B.1 优先级与改动面判断（给主班裁）
| 子件 | 依赖 | 实现成本 | 识别力 | 建议 |
|---|---|---|---|---|
| B-2 单调性／M-pattern | **纯 numpy 集合运算，零统计依赖** | 低（~80 行） | 结构性前提，MAR-monotone 分析的必要条件 | 🟢 **先做这个**：无收敛风险、无正定风险 |
| B-1 Little's MCAR | EM + 正定求逆 + 模式合并 | 高（~250 行 + 校准模拟） | 整体单一原假设（"全为 MCAR"），**定位不了是哪个变量** | 🟠 二期；上线前先以 B-2 ＋ 组件 A 覆盖 |

### B.2 Little's MCAR（规格）
- **输入**：数值矩阵 `X (n×p)`（含 NaN），缺失模式列子集 `pattern_cols`（默认前 `min(p,15)` 个变量参与模式分组）。
- **算法**：
  1. 按观测模式分组 `j = 1..J`，`S_j` = 该模式观测到的变量下标集，`p_j = |S_j|`；
  2. EM 求 MVN `(μ, Σ)` 的 ML 估计：E-step 用截断正态条件矩 `E[x_u | x_o]`、`Cov[x_u | x_o]`（分区公式，`Σ_oo` 求逆）；M-step 更新 μ、Σ；
  3. 统计量 `Λ = Σ_j n_j (μ̄_{j,o} − μ̂_{o})ᵀ [ (1/N)Σ_j n_j S_{j,o} ]⁻¹ (μ̄_{j,o} − μ̂_{o})`，`df = Σ_j p_j − p`，`p = chi2.sf(Λ, df)`（**渐近口径须在文案写明"需大样本，模式格样本少时不可信"**）；
- **退化保护（缺一不得出 p）**：`p_j == 0` 的模式剔除；`n_j < p_j + 2` ⇒ 与相邻模式合并（合并次数上限 3，超则 `insufficient_pattern_n`）；`Σ_oo` 条件数 > 1e10 ⇒ `singular_covariance`；`J > n/3` ⇒ `too_many_patterns`；EM 未收敛（`|Δloglik| < 1e-8` 或 500 迭代）⇒ `em_not_converged`。全部落进 `warnings` 且 `is_fallback=True` ＋ `fallback_note`（与本仓案 B 透出约定同型——注意 s927-10 取证：本仓存在"缺列／默认值被当读数"的先例，**失败必须显式，不得落 0.0**）。
- **输出**：`Λ, df, p_raw, p_holm（族＝参与检验的模式子集，默认单条故不校正）, patterns 表 (模式串, n_j, p_j), μ̂, Σ̂ 摘要, status`。
- **🔴 口径**：`p` 小 ⇒ "拒绝全变量 MCAR"；`p` 大 ⇒ "**不足以拒绝**"，**不得**写成"支持 MCAR"（接受域语言是本组件最易越线处）。
- **校准要求**：类型 I 蒙特卡洛（MCAR 真值，seed 固定，B≥2000，α=.05 的拒绝率落在 json 带宽内）＋功效（MAR 线性掩码臂）。B=2000 的模拟成本要在 CI 预算里说明（建议 `integration` marker，不入默认 `testpaths` 快线）。

### B.3 M-pattern／单调性
- **输入**：布尔矩阵 `M = df.isna()`。
- **算法**：变量排序后检查存在一个置换使 `M[:,π(1)] ⊇ M[:,π(2)] ⊇ …`（行集合嵌套）；给出 (i) 是否单调 `is_monotone`，(ii) 违背对清单 `(a,b)` ＋ 四类计数 `n_{a&b}, n_{a&¬b}, n_{¬a&b}`（Herzner–Heden 型违背度量），(iii) 贪心置换下最大嵌套链长度。
- **输出**：`is_monotone: bool | None`（无可缺失列 ⇒ `None` ＋ `no_missing_cells`），`violations: List[...]`, `chain: List[str]`, `n_patterns: int`, `warnings`。
- **复杂度**：置换搜索指数级 ⇒ 规格限定 `p ≤ 12` 穷举、否则用贪心近似并落 `approx_permutation` 警告。
- **用途口径**：单调性是**后续 MAR-monotone 方法（如 Heckman 型 sequential modeling）的前提**，本身不判机制。

---

## 3. 组件 C —— MNAR 敏感性分析（只给区间，不给判定）

### C.1 立论前提（必须写进实现文案，否则用户会误读）
MNAR **不可由观测数据识别**（§1 MCAR/MAR/MNAR 三臂里，MNAR 臂在已观测集上与 MCAR 臂经验等价；锚点件为此留过一条 `p=0.0498` 的临界读数，本班不复现）。故本组件**唯一合法产出**是「给定 δ 假设下的估计量区间」，不是「是不是 MNAR」的答案。

### C.2 主形状：shift-pattern（δ 平移）敏感性
- **输入**：`df`、目标估计量类型（`mean`｜`correlation`｜`regression_coef`，后者复用 `src/analysis/regression.py` 既有出口）、`delta_grid: List[float] = [0.0, 0.25, 0.5, 0.75, 1.0]`（单位＝该变量观测 SD；SD 缺失时用 `MAD/1.349` 并落警告）、缺失模式表（B.3 复用）。
- **算法**（对每个 δ、每个含 `m` 缺失的模式 j）：δ 平移 `μ_j = μ_obs(m) − δ·SD(m)`（方向按"缺失者取值更低"的常规情形，`direction` 参数化，允许 +）⇒ 用**加权**混合重算目标估计量（相关／回归用 EM 型修正或简化"均值漂移 imputation"再算，口径二选一须写进 `method_note`，不得混用）；输出 `δ → estimate` 曲线、CI（`statsmodels` 已有 bootstrap 工具或自写 percentile，B=2000 固定 seed）、**break-even δ**（估计量穿越 0 或穿越预设实质阈值 `substantive_threshold` 的最小 δ）。
- **输出契约**：`sensitivity_table (δ, estimate, ci_low, ci_high, n_used)`、`breakeven_delta: float | None`、`direction`、`threshold`、`identifiable: Literal[False]`（🔴 **恒 False，硬编码**，防实现者加"判定"字段）、`warnings`。
- **文案模板**：「在『缺失者较观测均值低 δ 个标准差』的假设下，目标估计量为 …。该假设不可由本数据检验。」——不得出现"证实 MNAR"。
- **可选第二实现**（高风险双实现位，按 CLAUDE.md 的 sol 双实现纪律）：Heckman 型 selection model（`statsmodels` 无现成 MNAR selection ⇒ 需自写两步法／全信息似然）。**默认不排期**，仅当人工要求"要一个不是 shift-pattern 的形状"时启用。
- **边界**：`substantive_threshold` 必填（无阈值则不得给"稳健／不稳健"的任何语言）；缺失率 > 50% 的列 ⇒ `delta_unstable`，只出表不出 break-even。

---

## 4. 「数据可得性闸」的两条解锁路径（卷宗完成标准 ②）

现状闸：**42/42 在册表件零缺失格**（本班 §5 重跑）⇒ 三组件在任何在册数据上都会返回 `no_missing_cells`，**实现可以写完但永远得不到非空证据表**。

### 路 A：合成夹具先行（推荐，今天即可）
- 落点沿用本仓既有约定（`scripts/generate_cfa_sem_golden.py` ＋ `tests/fixtures/golden_stats/**` ＋ `*_expected.json`；该约定现被 `tests/test_cfa_sem_golden.py` 的沙箱可复现性钉桩复用）：
  - `scripts/generate_missingness_golden.py`（**源码内显式声明 seed**，与本仓既有钉「seed 是复现性唯一凭据」同型）；
  - `tests/fixtures/golden_stats/missingness/{mcar,mar,mnar,monotone,mixed}.csv` ＋ `missingness_expected.json`（带宽／期望显著格数／校准容差**全放 json**，测试侧零发明数字）；
  - 三臂掩码：MCAR＝均匀随机；MAR＝由已观测 `x1` 逻辑驱动；MNAR＝由 `y` 自身取值驱动；再加单调四变量臂（模式：`y1` 20%、`y2` 缺时 `y1` 必缺）；
  - 建议同时造一枚**中文哨兵臂**（`无/缺失/-9`）钉 A.6。
- 优点：实现正确性／边界／Holm 排序／Fisher 切换／EM 退化路径全部可测；零隐私；可 CI。
- 🔴 局限（必须写进文档与 UI）：**合成夹具只解锁"实现"，不解锁"结论"**。真实队列的机制判定仍需真实数据＋人工。
- 成本估计：夹具＋规格测试 ≈ 1 个单组件班次；无新依赖。

### 路 B：等真实回收数据（前置条件清单，缺一项就不算解锁）
1. **A.6 哨兵归一**落地（否则 pandas 默认口径下中文／`-9` 缺失不可见，本组件永远报"无缺失"——本班实测的新闸，见 §0）。
2. **调用位必须在 `handle_missing` 之前**：`runner.py:926` 已 listwise 删行；组件 A/B/C 的语义建立在"缺失格仍在"的原始 df 上，需新增入口（建议 `data_quality_check` 之后、UI 数据质量页挂"缺失机制体检"按钮），🔴 属改生产码 ⇒ 人工闸。
3. **`AnalysisPlan.missing_strategy` 字段缺失**（`src/parser/intent_resolver.py`，37 字段无该项）⇒ 若希望用户显式选 pairwise／MI，需补字段＋校验；同时 `data_quality.py:80-86` 的 pairwise **空转分支**要落实（要么真做 pairwise，要么从 `MissingStrategy` 里摘掉这个名字——🟠 文案承诺与实现不符属既存缺陷，与 s927-10 的"带宽比对降级"同类问题）。
4. **阈值口径统一**：15 vs 10 二选一或双写并命名（`data_quality.py:74/:124/:199` vs `cleaning_wizard.py:135/:291`）。
5. **隐私与写盘**：真实队列含个人信息 ⇒ 探针一律只读；不得把真实数据落 `tests/fixtures`；`data/` 被 gitignore＝无还原点（本域纪律）。用户库 `~/.psy_analysis` 现存 1 项目 4 行×2 列且 `n_missing=0`（锚点件读数），另锚点件遗留一处**索引悬空**（`index.json` 指 `fcc90a0fd0f4`、目录实际是 `9b2b71937e1d.json`）——本班未复核该状态、属人工核对项，登记不处置。
6. 到货后**全部读数重取**：三组件在新队列上的证据表才是可裁决材料。

### 建议组合
**A 先落地（把实现的正确性钉死）→ B 到货后只换数据、不换判据**；判据若要在 B 阶段变动，须回到本规格改口径并过人工闸，不允许在实现里就地放宽（这正是 s927-10 在 CFA 一侧取证到的失效模式）。

---

## 5. 取证命令（他人可原样重跑，全部只读）

```bash
cd /d/code/psy-analysis
git rev-parse --short HEAD                      # f0f3f73
.venv/Scripts/python.exe -c "整词计数"           # MCAR/MAR/MNAR：仅 3 处文案
# 在册表件缺失普查（本班自跑，非引用锚点）：
.venv/Scripts/python.exe -c "glob tests/fixtures/**|demo_projects/**|archive/**/data.csv → pd.read_csv → isna().sum()"
  → 在册 CSV 扫描数: 42   含 NaN 格文件数: 0
# 哨兵可见性（新发现）：
.venv/Scripts/python.exe -c "pd.read_csv(io.StringIO('a,b\n1,-9\n2,NA\n3,无\n4,?\n5,缺失'))"
  → b dtype: str | NaN 计数: 1 | 值: ['-9', nan, '无', '?', '缺失']
# R×C Fisher（API 陷阱取证）：
.venv/Scripts/python.exe -c "scipy.stats.fisher_exact([[3,7,10],[5,2,9]])"
  → SignificanceResult，hasattr(oddsratio)=False，p=0.2799（该数只是 API 探活，非数据结论）
grep -n "missing_strategy\|handle_missing" src/analysis/runner.py    # 886 / 926
grep -n "pairwise" src/analysis/data_quality.py                       # 21 / 38 / 80
grep -n "missing_pct > \|> 15\|> 10" src/analysis/data_quality.py src/ui/cleaning_wizard.py
grep -n "缺失\|MCAR\|missing" src/analysis/assumptions.py              # 0 命中
.venv/Scripts/python.exe -c "依赖版本"   # scipy 1.18.0 / statsmodels 0.14.6 / pingouin 0.6.1 / numpy 2.5.1 / pandas 3.0.3 / sklearn 1.5.2
```
本班**未**跑任何机制检验、未生成三臂读数；锚点件的 `r_pb=0.394 / SMD=−1.21 / p=0.0498` 等均标注为「锚点件读数，本班未复现」。零写自证：只读命令＋`isna()`／`read_csv` 内存操作；未打开任何 SQLite 连接；`data/` 未被触碰（前后 `find data -maxdepth 1 -type f -printf '%T@ %s %p\n'` diff 为空，与 s927-10 同一份采样）。

## 6. 接线触点（主班估改动面用；本班未动任何一件）

`src/analysis/method_ids.py`（新 id）→ `method_catalog.py::_m(...)`（aliases/table/card/level）→ 新模块 `src/analysis/missingness.py`（三组件同文件，A 先）→ `result_card.py::_CARD_BUILDERS` 注册 `_build_missingness` → `field_lineage.py::_spec`（效应量与 p 字段谱系，现有 `"chi2_p": "S3_p_value"`／`"srmr": "S24_fit_index"` 可对齐）→ `assumptions.py::_METHOD_ASSUMPTIONS`（🔴 现为**零条目**，登记属净新增；与 s927-24 的 placeholder 债同域，两单的登记口径须一致，否则一边写"已实算"一边写 placeholder）→ `runner.py` 分派＋UI 入口（`src/ui/cleaning_wizard.py` 或数据质量页）→ `pytest.ini` markers（校准模拟建议挂 `integration`，默认快线不跑）→ `tests/test_missingness_golden.py` ＋ `scripts/generate_missingness_golden.py`。

**回滚成本**：全部为新增文件＋注册表追加行，`git revert` 单提交即可；无迁移、无数据写、无 `data/` 触碰。若采纳 A.6 哨兵归一（会改写内存中的 df），必须保持"默认关闭＋显式 meta"，回滚＝关掉开关，不落盘。

## 7. 风险与遗留

1. **R1（🔴 最高）**：实现若把"缺列／默认值"当读数落 `0.0`——本仓已有先例（s927-10 取证到 `SEMOPY_FIT_MAP` 4 枚假 0 直达 UI／`effect_sizes`）。三组件的每个数值字段必须有"来源"标记（真算／缺项），缺项走 `None`＋warning，**不得落 0**。
2. **R2**：文案越界即触红线。测试里加一枚**措辞门禁**（正则扫 `MCAR|MAR|MNAR|随机缺失` 字样不得出现在渲染输出，`cleaning_wizard.py:170` 与 `data_quality.py:76/:202` 的既有文案属"提示"不属"结论"，需白名单区分）。
3. **R3**：Little's MCAR 的渐近前提（大样本、模式格充足）与本仓典型问卷样本量（n≈200 级、Likert 7 点，见 CFA 夹具）未必匹配；若强制实现，容易产出"看着像 p"的不可信值——这是 §B.1 建议先做单调性的理由。
4. **R4**：多重比较族定义一旦由实现者临时决定，判据就漂了（A.4 把族钉在"每个缺失变量"）。
5. **R5**：`requirements-lock.txt` 与实装 numpy 版本三向不一致（lock 在途 2.3.5／HEAD 2.4.4／实装 2.5.1）；夹具生成器的字节级可复现钉对 numpy RNG 敏感（`test_cfa_sem_golden.py:169-179` 自称的出口就是"版本漂移查 numpy/pandas"）⇒ 新夹具落地前应先由主班把 lock／实装对齐，否则新增可复现性钉会从第一天起就红。
6. 本班不裁：真实队列何时可得、是否补 `AnalysisPlan.missing_strategy` 字段、阈值取 15 还是 10、pairwise 落实还是摘名——均人工闸。
