# s927-47 · chi2 区间 [60,120] vs 实测 44.511：多模型复核请求材料（2026-09-28）

> 🔴 **状态：待多模型复核（统计红线，本班不判）**。本文只整理两读数的出处、条件、自由度与口径差异，
> **不下**「哪个读数对」「模型是否拟合良好」「区间该改成多少」的任何结论；不改判据阈值、不改
> `cfa_expected.json`、不动 `tests/test_cfa_sem_golden.py:269` 那枚恒真式（已在册待人工，见 §8）。
>
> 班：`qoder-executor-20260928-1700-psy95`（只读路）· 仓 `D:\code\psy-analysis`
> · HEAD `63d96c871a805516d889cf897213a62a53f446cf`（2026-09-28 16:45:02 +0800，本班 `git log -1` 现取）
> · 工作树 12 枚他班在途件（含 `src/analysis/cfa.py`／`tests/test_cfa_sem_golden.py`）⇒ 本班全程未碰
> · 取证环境：`.venv/Scripts/python.exe`（Python 3.12.9）· semopy 2.3.11 · pandas 3.0.3 · numpy 2.5.1
> · 探针：`D:\code\tmp\qoder-executor-20260928-1700-psy95\probe_chi2.py`（内存复算，零写盘）

---

## 1. 问题陈述（一句话＋为什么现在「没人钉着这件事」）

`s923-08` 遗留条原文（`zcode-bridge/done/s923-08.result.md:62`，本班现点逐字）：

> 需多模型裁决（统计红线，本单不判）：`chi2_range [60,120]` vs semopy MLW 实测 44.511 的差异如何定论（`chi2/df=0.927<1` 是线索）。

即：**在册金标准给的是 chi2 落在 60～120 之间，而本机 semopy 在同一份夹具上算出 44.511（在区间下方）**。

复核请求要回答的不是「44.511 对不对」，而是**这两枚数字是不是同一个口径量出来的同一样东西**。

当前盘面上没有任何一版代码在做这个双端比较（本班 `git show` 现点）：

| 版本 | 位置 | 对 `chi2_range` 的实际用法 | 效果 |
|---|---|---|---|
| HEAD 已入库 | `tests/test_cfa_sem_golden.py:263`／`:264` | `assert chi2 < chi2_range[0]`、`assert chi2_df != df` | 钉的是「拟合链必失败 ⇒ chi2=0、df=0」的**旧降级现状**，区间只作为「上界要小于 60」的反向参照 |
| 工作树在途（未提交） | `tests/test_cfa_sem_golden.py:269` | `assert chi2 > chi2_range[0] * 0` | 右端恒 0 ⇒ **恒真式**，`60` 与 `120` 都不再参与比较（该条已登记待人工，见 §8） |

⇒ 结论性事实（覆盖面观察，非统计判断）：**差异本身在两个版本里都没有断言承载**，所以它只能靠人工/多模型裁决收口，不能靠测试转绿收口。

---

## 2. 读数 A：区间 `[60, 120]` 的出处（在册证据全部列尽）

唯一出处是这一枚夹具，**仓内无第二处**（本班全仓 `grep -rn "chi2_range"`：命中仅 `cfa_expected.json:7` 与 `tests/test_cfa_sem_golden.py:269` 两处，其余全在 docs 转述）：

`tests/fixtures/golden_stats/psychometrics/cfa_expected.json`（HEAD 与工作树同字节）

```json
{
  "method": "cfa",
  "description": "4因子12题CFA金标准 — 200样本",
  "reference_tool": "R lavaan 0.6-18",
  "model_spec": "F1 =~ q1 + q2 + q3; F2 =~ q4 + q5 + q6; F3 =~ q7 + q8 + q9; F4 =~ q10 + q11 + q12",
  "expected": { "chi2_range": [60, 120], "df": 48, "CFI_min": 0.92, "TLI_min": 0.90,
                "RMSEA_max": 0.08, "SRMR_max": 0.08, "loadings_min": 0.50, "loadings_max": 0.95 },
  "tolerance": { "CFI": 0.05, "TLI": 0.05, "RMSEA": 0.03, "SRMR": 0.03 }
}
```

谱系与缺口（本班现取，逐条给命令可复算）：

1. **入库轨迹**：`git log --format=... -- tests/fixtures/golden_stats/psychometrics/cfa_expected.json` ⇒ **仅一笔** `097a657`（2026-07-14 12:25:39，message `chore: checkpoint existing work before coverage audit`）。
   该笔是全仓「既有工作批量 checkpoint」（`git log --max-parents=0` 显示真正的初版库提交是 `ec45485` 2026-06-01），⇒ **数字是随旧账一起进来的，仓内没有留下任何推导记录**。
   `git log -S"chi2_range"` 全历史只此一笔触及该文件 ⇒ 区间字面量**从未被改过**（也没有被改回来的痕迹）。
2. **自述口径**：`reference_tool: "R lavaan 0.6-18"`。但本机/本仓**无法复算 lavaan 侧**（本班实测）：
   - `which R`／`which Rscript` ⇒ 均 `no R`；
   - `import rpy2` ⇒ `ModuleNotFoundError`；`grep -c rpy2 requirements.txt requirements-lock.txt` ⇒ **0**；
   - 全仓 `*.R` 文件中含 `lavaan` 字样的 **0 个**；`grep -rn "lavaan"` 在非 venv 命中里只有本 json 的 `reference_tool` 字段、两份 docs 转述、以及 `src/output/learning_card.py:623/630/819/824` 的**教学文案**（「需要 SPSS AMOS 或 R 的 lavaan 包」）。
   ⇒ **区间侧至今没有可复算入口**，复核者只能按「人写的带」还是「工具输出」两种解释之一来处理（§6 两假说）。
3. **区间所依附的模型/样本**：`description` 自称 200 样本、4 因子 12 题，与在册夹具实际形状**自述一致**（§3），所以区间**看起来**是针对这份夹具的；但「看起来针对」不等于「由这份夹具算出」（无推导记录可查）。
4. **配套缺口（既存、非本次引入）**：`tolerance` 段四个键在 cfa 侧从未被任何断言消费（`s923-08` 稿 §3 已登记同一事实）。

---

## 3. 读数 B：实测 `44.511` 的条件（三次取证的时间线＋本班复算）

数据条件（两枚读数共享的「夹具面」，本班实测）：

- `tests/fixtures/golden_stats/psychometrics/cfa.csv`：`shape (200, 12)`、dtype 全 `int64`、值域 `[1, 7]`、NaN 0 个；
  size 5040 B、mtime 2026-07-04 18:45:41、sha256 `b938952c06a5e407bdef8fced8d38f1c9088f3046cca9d2d8952b5c65328fb7b`（`certutil` 与探针 `sha256` 两种取法同值，前 8 位 `b938952c`）。
- **谱系复证（本班新增一条硬证）**：按 `scripts/generate_cfa_sem_golden.py` 的口径（`np.random.seed(42)` → 4 因子 Cholesky 相关 → 载荷 0.65～0.85 → `observed*1.2+4.0` → `round` → `clip(1,7)`）在内存重算，
  **整数化后的矩阵与在册 `cfa.csv` 逐元素全等**（探针输出 `连续版与整数版是否等同在册夹具: True`）
  ⇒ 夹具就是 seed 42 那条 RNG 流经 **1–7 整数 Likert 变换**后的产物；变换前那份**连续**数据是另一份数据（§5 轴 3 用得上）。
- 模型式：`_build_model_syntax`（`src/analysis/cfa.py:98-115`）产出的就是 4 行 `=~` ＋ 6 行因子两两 `~~`，与 json 的 `model_spec` 同构（本班探针直接以该式调用 semopy，读数与生产入口逐位相同）。

`44.511` 的三次取证（口径**不完全相同**，逐条标清）：

| 次序 | 时间/班 | 取数方式 | 结果 |
|---|---|---|---|
| ① | 2026-09-23 `s923-08`（`psy-cfa-obj-fix-design-20260923.md:39`） | **绕开生产码**，内存直调 `fit(df, obj='MLW')`。当时生产 `cfa.py` 仍是 `obj='ML'` ⇒ 走生产路径拿不到任何真值 | chi2 44.511／DoF 48／CFI 1.004933／TLI 1.006783／RMSEA 0／AIC 59.55489／BIC 158.504411／chi2 p-value 0.616606 |
| ② | 2026-09-28 01:20 前后 `s927-10`（`s927-10-golden-coupling.md:133`） | 经**当时在途**的 `src/analysis/cfa.py`（`estimator="MLW"`） | `chi2= 44.511  df= 48.0  cfi= 1.005  tli= 1.007  rmsea= 0.0  srmr= 0.0  aic= 59.555  bic= 158.504` |
| ③ | **本班（2026-09-28 17:0x）** | 两条并做：直调 semopy MLW＝44.511002／DoF 48／p 0.616606／chi2 Baseline 773.21878／DoF Baseline 66；经工作树 `cfa.py` 生产入口＝`chi2 44.511, chi2_df 48.0` | 与 ①② 逐位相符；比值 `chi2/chi2_df = 0.9273125`（＝线索里那个 0.927） |

🔴 **本班新坐实的一条条件（前人不曾写清）**：`44.511` **不在 HEAD 上**。用 `git show HEAD:src/analysis/cfa.py` 导到沙盒内存加载后跑同一夹具，得到的是
`estimator='ML'` → `chi2 0.0`／`chi2_df 0`／`is_fallback True`／warning `⚠ semopy模型拟合失败：'ML is unknown objective function.'`
⇒ **「区间 60-120 vs 实测 44.511」这条对比，成立的前提是那枚尚未提交的 MLW 修复被接受**；两枚读数目前一枚在册、一枚在途。
（探针同一条输出里还有一句 `效度指标附加失败：attempted relative import with no known parent package`，**是本人单文件 exec 的产物**，不是仓内缺陷——与 `s927-10` §3.2 自报过的同类瑕疵同形，真实 pytest 下 `warnings == []`。）

支撑读数：本班跑 `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_cfa_sem_golden.py -q` ⇒ **19 passed**（即恒真式当前不拦任何事）；
门禁族单列加跑 `pytest tests -q -k "download_buttons or export_gate"` ⇒ **1 failed / 19 passed / 1 skipped**，
唯一红是已在册的 `test_all_download_buttons_accounted_for`（断言体 `['src/ui/questionnaire_panel.py'] == []`），本班零改动、未消红、未挂 NEEDS_MIGRATION、未写白名单。

---

## 4. 自由度核对（卷宗点名要说的第三件事）

- 在册 `df: 48`；实测 `DoF: 48`（semopy 与生产入口两路同值）⇒ **两读数的名义自由度相同**，`s923-08` 稿 §3 的「df 不用动」在本班复算下**成立**。
- ⚠ 但本班实测到一条会削弱「df 相同 ⇒ 口径相同」这条推断的读数：**同一份数据、同一个模型式，换六种目标函数（MLW/ULS/GLS/WLS/DWLS/FIML）`DoF` 恒为 48、`DoF Baseline` 恒为 66**，而 `chi2` 从 16.24 一路摆到 83.26（§5 轴 1 表）。
  即 `DoF` 不随目标函数变化 ⇒ **df 相等不构成同口径的证据**，只能作为「模型识别式相同」的证据。（这是读数观察，不是判断。）
- `DoF Baseline 66` ＝ 78 个协方差矩 − 12 个独立变量模型的 12 个参数 ⇒ semopy 报的 df 走的是**协方差矩**账本；均值/截距是否进入似然（以及 lavaan 默认 `meanstructure=TRUE` 的账法是否同一本）**本班无法从仓内证据判定**，列为交回问题（§7 问 2）。

---

## 5. 口径差异清单（本班只列轴、只给读数，**不选轴**）

**轴 1 · 估计量/目标函数（差异最大，全部为本班同一份数据上的实测）**

| semopy `obj` | chi2 | DoF | chi2 p | CFI | TLI | RMSEA | 是否落 `[60,120]` 内 |
|---|---|---|---|---|---|---|---|
| `MLW`（生产现用；`"ML"` 的别名映射目标） | 44.511002 | 48 | 0.616606 | 1.004933 | 1.006783 | 0.0 | 否（低于下界） |
| `WLS` | 64.290408 | 48 | 0.058074 | 0.943162 | 0.921848 | 0.041297 | **是** |
| `ULS` | 76.329993 | 48 | 0.005738 | 0.993680 | 0.991310 | 0.054460 | **是** |
| `GLS` | 83.259245 | 48 | 0.001203 | 0.918926 | 0.888523 | 0.060756 | **是** |
| `DWLS` | 18.292907 | 48 | 0.999969 | 1.032136 | 1.044187 | 0.0 | 否 |
| `FIML` | 16.238743 | 48 | 0.999995 | −0.613467 | −1.218517 | 0.0 | 否 |
| （参照）lavaan `estimator="ML"` | **本机不可复算**（无 R／无 rpy2／无 .R 脚本） | — | — | — | — | — | — |

⇒ 待复核的关键观察：**区间 [60,120] 与「同一份数据上的另外三种 semopy 目标函数读数」是相容的**。这把「差异到底来自工具还是来自估计量」这个问题从修辞变成了可判定的具体选择。（本行不下判断。）

**轴 2 · 数据变换：整数 1–7 Likert vs 变换前的连续值（同 seed 42、同模型、同 obj=MLW）**

| 数据 | chi2 | DoF | p | CFI |
|---|---|---|---|---|
| 在册 `cfa.csv`（round＋clip 后，整数） | 44.511002 | 48 | 0.616606 | 1.004933 |
| 同一生成链**变换前**的连续矩阵 | 39.623355 | 48 | 0.799908 | 1.010780 |

⇒ 整数化把 chi2 往上推（本班只报方向与数值）；两份都不是 60 以上 ⇒ 若区间声称基于「同一份 200 样本 4 因子模型」，**光换数据形态解释不通**（此句仍属可判定问题，不是结论）。

**轴 3 · 样本量口径**：在册自述 n=200、夹具实为 200 行；本班另测 n=100 子集 ⇒ chi2 38.322195、DoF 48、p 0.839864。⇒ 区间不是 n 造成的（n 减半只会让 chi2 同向变化，不会进入 60～120 的上半段）。

**轴 4 · 字段可信度（复核者必须知道的既有缺陷）**：生产入口给出的 `chi2_p` 是 **0.0**，而 semopy 自己的 `chi2 p-value` 是 **0.616606**；`srmr` 是 **0.0**，而 semopy 2.3.11 的 `calc_stats` **根本不输出 SRMR 列**（本班对六种 obj 逐一试，`SRMR` 全为 `<列不存在>`）。
⇒ 「实测 44.5」这一侧的**伴随字段**有已在册的假 0 缺陷（§8），复核时请以 `calc_stats` 原值为准，别把 `chi2_p=0` 读成「拟合被拒绝」。（该缺陷的定性本身也已在册待人工，本班不重复判。）

---

## 6. 两假说并列（**都不判**，各自给「什么数据能区分」）

**H1 · 区间是外来的经验带，与本机实测不可比 ⇒ 该重估区间**
支撑事实：①区间随 `097a657` 批量 checkpoint 进来，仓内**零推导记录**、零 lavaan 脚本、零 R 依赖（§2.1／§2.2）；
②`[60,120]` 宽度为 2 倍、下界恰为「约 df 的 1.25 倍」，形状更像**人为写的经验带**而不是同一次拟合的输出（形状观察，不作判断）；
③实测侧 44.511 三次复现逐位一致（§3 表 ①②③），且能在 HEAD 之外被任何人在本机复算。
可区分它的证据：`cfa_expected.json` 生成时刻的原始 lavaan 输出（若历史文档／论文模板里存在）、或任何注明 n／估计器／是否连续计分的一手记录。

**H2 · 两读数同数据同模型，差异来自估计器／矩口径不同 ⇒ 44.511 只是六种读数之一**
支撑事实：①`df` 两侧同为 48、模型式两侧同构（§4）；②同一份数据只换 `obj` 就能覆盖 16.2～83.3，其中 WLS/ULS/GLS 三种**就落在 [60,120] 内**（§5 轴 1）；
③lavaan 默认 ML 与 semopy `MLW` 是否同缩放、是否含均值结构，仓内**无人核对过**（`s923-08` §1 只证到「`ML` 不是 semopy 的合法名字，`MLW` 是 Wishart 形式 ML」这一步）。
可区分它的证据：在同一份 `cfa.csv` 上真跑一次 lavaan（需 R 环境）并把 `chisq/df/p/CFA/TLI/RMSEA/SRMR` 与 `estimator`、`meanstructure`、`missing` 三项设置原样贴回；
或给出 semopy 与 lavaan 之间 chi2 缩放（n 与 n−1）／矩矩阵取法的官方口径对照，据此判断「44.511 换算后是否可能落进 60 以上」。

⇒ **两假说的处置完全不同**（H1 ⇒ 重估金标准数字；H2 ⇒ 金标准不动、要动的是「生产该用哪个 obj／该报哪个数」），
所以交回人工时必须**先裁口径、后动数字**。本班明确不选边。

---

## 7. 提请多模型复核的三个具体问题（可直接进 GPT／第二模型流程）

1. 在册 `chi2_range [60, 120]` 的 `reference_tool: R lavaan 0.6-18` 与实测侧的 semopy 2.3.11 `MLW`，**在 chi2 的缩放因子（n 还是 n−1）与矩矩阵（是否含均值结构）上是否等价**？若不等价，`44.511` 是否有任何一条换算路径能进入 `[60,120]`？
2. 4 因子 12 题、n=200、整数 1–7 计分（可视作连续亦可视作有序）时，lavaan `ML` 与 semopy `MLW/ULS/GLS/WLS/DWLS` 之中，**哪一种是本仓该对外报的口径**？该选择的依据是否要求把 `estimator` 默认值（工作树现为 `"MLW"`）再改一次？（默认值本身在途未提交，见 §3 🔴 条。）
3. 若两假说之一成立，`tests/test_cfa_sem_golden.py` 该以什么形状承载这条带宽：**双端比较并显式钉「失守」**（文件头纪律所要求）还是**换成与在册区间无关的结构性钉桩**？现在两个版本都没有双端比较（§1 表）。

需要复核方补的数据（本班无法在只读＋无 R 环境下产出）：lavaan 侧原样输出；`cfa_expected.json` 的历史一手凭据（若有）；有序计分（polychoric／WLSMV 族）是否属于本仓口径。

---

## 8. 已在册待人工项（引用即可，本班未动）

- `tests/test_cfa_sem_golden.py:269` 恒真式 ＋ semopy 缺列假 0：见 `D:\code\docs\insights\drain-20260923-pending-human.md`
  第 187 行（波次 40／40b 收账段 ⓑ 条）首登记，第 188 行 ⓖ、第 189 行 ⓗ 继续挂账 ⇒ 本班只引用、未改判据、未挂 NEEDS_MIGRATION、未写白名单。
- `data/literature_feed` 相关在册项（台账 89／166／179）与本单无交集，本班未连库。

## 9. 本单未做（红线自陈）

未改 `cfa_expected.json`、未改 `src/analysis/cfa.py`（他班在途件）、未改 `tests/test_cfa_sem_golden.py`（含 :269）、
未跑任何写库脚本、未 `git add`／`commit`／`stash`／`checkout`／`restore`；本文所有数字均为**读取与内存复算**结果；
未对「模型是否拟合良好」「区间该是多少」「44.511 与 60 谁对」发表任何判断。
