# psy post_hoc_power 四处同型兜底 census（只读落档 · 2026-09-25 实测）

- 班：`qoder-executor-20260924-2341-psy34`（信箱单 `s924-05`，主班 `qoder-main-drain-20260924-2341` 收口）
- 性质：**只读 census**。生产码／测试件／配置／数据库零改动；统计域红线按"只登记实现在算什么、口径是什么"执行，
  本档**不产出"样本量应该是多少"的结论**，所有 n 值均为「求解器当前返回了什么」或「该函数自身判据下的口径读数」。
- 盘面绑定（读数只对这一态负责）：

```
$ git -C D:/code/psy-analysis rev-parse --short HEAD          → 86fcf2f（2026-09-25T00:1x 现取）
$ sha256sum src/experiment_design/power_analysis.py           → 5338a84b3e7364073163ae203de98311c8e7d4082449949a25d4f87322454bbf
$ sha256sum src/analysis/post_hoc_power.py                    → ee8cdb6e025e5f5c6bff2709e96d86b11aa884205c40587c832b169a06a474e4
$ git -C D:/code/psy-analysis log --oneline -- src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py
                                                                → ec45485（两文件自建仓以来各零改动）
$ wc -l src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py → 404 / 316
```

  ⚠ 同仓另有写位兄弟班 `...-psy33` 在途（`app.py`／`pytest.ini`／`requirements-lock.txt`／`tests/conftest.py`
  ＋两份测试件），本班未触碰；本班两件被测文件在工作树里是干净的（`git status --porcelain` 现值 8 项，无一属它们）。

## 1. 卷宗前提逐条实测（含否证）

| # | 卷宗／来账前提 | 实测 | 命令 |
|---|---|---|---|
| 1 | 4 处同型兜底在 `src/analysis/post_hoc_power.py`（卷宗 :17 锚点写该文件） | ❌ **否证**：四处 `hi=2000/3000/5000/2000` 的兜底**全部在 `src/experiment_design/power_analysis.py`**；post_hoc 文件里连 `2000/3000/5000` 三个常量都不存在 | `$ rg -n "2000\|3000\|5000" src/analysis/post_hoc_power.py` → 0 命中（rc=1）；`$ rg -n "n_lo, n_hi = \|N_lo, N_hi = " src/experiment_design/power_analysis.py` → 6 命中 |
| 2 | 锚点 `post_hoc_power.py:164「        except Exception:」` | ❌ **否证（错 1 行）**：该串在 :165，:164 是 `r_max = float(arr_abs)`；该文件零改动 ⇒ 不是漂移而是**投递时就错** | `$ sed -n '164,166p' src/analysis/post_hoc_power.py` |
| 3 | 「与**已落地** t 族 A′ 哨兵逐处对照」 | ❌ **否证：A′ 尚未落地**。`solved` 关键字在两文件 0 命中；`PowerResult` 无新字段；落地单 `s924-04` 今 00:40 才投、`inbox/s924-04.task.md` 仍在（未认领）。现存的 t 族资产是 s922-12 的**现状钉桩**（`*_bracket_ceiling`，3 函数 8 实例），不是哨兵 | `$ rg -n "\bsolved\b" src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py` → 0；`$ rg -n "bracket_ceiling" tests/test_power_analysis.py` → 4 命中 |
| 4 | 来账 `done/s923-03.result.md` 的 4 处行号（`:166-167/:209-210/:240-241/:286-287`） | ✅ 成立：与磁盘逐字对位（本班表 2 用 `n_lo` 起算的 4 行区间口径，同一批点） | `$ sed -n '163,167p;206,210p;237,241p;283,287p' src/experiment_design/power_analysis.py` |
| 5 | s923-03 的相关族读数（r=0.05 → 上界 3000、`actual_power=0.782177`） | ✅ 复现，逐位相同 | 见 §3 命令 |
| 6 | 来账「另 3 处零命中」 | ⚠️ **需收窄**：只在 Cohen 三档基准的采样点上零命中；本班实测出每族的**命中分界**（§4），分界以下必命中，已抓到 9 个命中样本 | `tmp/s924-05/probe_fallback_census.py` |

## 2. 四处行号表 ＋ 每处 `sed -n` 实测摘录（完成标准①）

| 处 | 位置（`power_analysis.py`） | 兜底语句 | 上界语义 | 所属求解函数／分发名 |
|---|---|---|---|---|
| ① ANOVA（单因素与重复测量**共用一枚**） | `:163-167` | `:167 n = n_hi` | 2000 = **每组** n | `_solve_n_for_anova_f:136` ← `calculate_sample_size("anova"/"rm_anova")` |
| ② 相关 | `:206-210` | `:210 n = n_hi` | 3000 = 总 n | `_solve_n_for_correlation:186` ← `"correlation"` |
| ③ 卡方 | `:237-241` | `:241 n = n_hi` | 5000 = 总 n | `_solve_n_for_chisq:226` ← `"chisq"` |
| ④ 多因素 | `:283-287` | `:287 n_per = n_hi` | 2000 = 每组 n_per ⇒ `required_n` 假数为 `2000×k` | `_solve_n_for_factorial_anova:257` ← `"factorial"` |

```
$ sed -n '163,167p' src/experiment_design/power_analysis.py     # ①
    n_lo, n_hi = k + 1, 2000
    try:
        n = brentq(f, n_lo, n_hi, maxiter=100)
    except ValueError:
        n = n_hi

$ sed -n '206,210p' src/experiment_design/power_analysis.py     # ②
    n_lo, n_hi = 5, 3000
    try:
        n = brentq(f, n_lo, n_hi, maxiter=100)
    except ValueError:
        n = n_hi

$ sed -n '237,241p' src/experiment_design/power_analysis.py     # ③
    n_lo, n_hi = df + 2, 5000
    try:
        n = brentq(lambda n: power_at_n(n) - power, n_lo, n_hi, maxiter=100)
    except ValueError:
        n = n_hi

$ sed -n '283,287p' src/experiment_design/power_analysis.py     # ④
    n_lo, n_hi = 2, 2000
    try:
        n_per = brentq(lambda n: power_at_n(n) - power, n_lo, n_hi, maxiter=100)
    except ValueError:
        n_per = n_hi
```

t 族对照面（**同一手，两枚，形态不同**）：

```
$ sed -n '80,85p' src/experiment_design/power_analysis.py
        n_lo, n_hi = 2, 2000
        try:
            n = brentq(f, n_lo, n_hi, maxiter=100)
            n = int(np.ceil(n))
        except ValueError:
            n = int(np.ceil(n_hi))
$ sed -n '114,118p' src/experiment_design/power_analysis.py
        N_lo, N_hi = 4, 4000
        try:
            N = brentq(f, N_lo, N_hi, maxiter=100)
        except ValueError:
            N = N_hi
```

⇒ 全模块同型兜底共 **6 枚**（2 枚 t 族 ＋ 本班 4 枚），另有 t 族之外的第 7 个隐性差异点：①②③④的 `n = int(np.ceil(n))`
与 `actual = power_at_n(n)` 落在 try **之外**（①的 :169/:171、③的 :243/:244），而 t 族配对枚把 `ceil` 包在 try **之内**（:82）。

## 3. 触发机制：两型 ValueError，不是同一枚雷

`brentq` 的 `except ValueError` 在两类成因下都会落兜底，而四处 sibling 与 t 族**分属不同型**：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s924-05/probe_trigger_reach.py   # 原文摘录见 tmp/s924-05/probe3_out.json
paired_t d=0.30 hi=2000    ｜brentq → ValueError: The function value at x=2000.0 is NaN; solver cannot continue.
independent_t d=0.50 hi=4000｜brentq → ValueError: The function value at x=3148.421214196654 is NaN; solver cannot continue.
correlation r=0.05 hi=3000  ｜brentq → ValueError: f(a) and f(b) must have different signs
anova f=0.01 k=2 hi=2000    ｜brentq → ValueError: f(a) and f(b) must have different signs
chisq w=0.02 df=1 hi=5000   ｜brentq → ValueError: f(a) and f(b) must have different signs
chisq df=6000 区间颠倒       ｜brentq → ValueError: f(a) and f(b) must have different signs
correlation r=0.30 hi=3000  ｜brentq → 正常返回 84.9276（对照组：说明本探针的复刻式与生产式同解）
```

- **t 族＝中途 NaN 型**：上界端点本身是达标的（`power_at_上界=1.0`），是迭代途中 `scipy.stats.nct.cdf` 在大 df＋大 ncp 处吐 NaN 才炸。
- **①②③④＝上界不足型**：`power_at_n(n_hi) < 0.80` ⇒ 区间两端同号。这四处**没有 NaN 通路**（`ncf/ncx2/norm` 在该量级保持有限；
  实测 77 个 sibling 采样点（另 8 个 t 族对照点）`报告含nan` 全为 False，见 §4 的 `n_上界NaN透出` 列）。
- 另有第三形态只在 ③ 出现：**区间上下界颠倒**（`n_lo = df + 2` 由入参决定，df 够大时 `n_lo > n_hi`）——
  实测 `_solve_n_for_chisq(0.30, 6000, …)` 返回 `required_n=5000`，**小于该函数自己声明的下限 6002**，且不打任何异常。
  `$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from src.experiment_design.power_analysis import _solve_n_for_chisq as s;r=s(0.30,6000,0.80,0.05);print(r.required_n,r.actual_power)"` → `5000 0.998916`

## 4. 命中边界与假数方向（每族一个"本模块自身判据"的分界点）

分界点＝ `power_at_n(n_hi)` 恰等于 0.80 的入参（对分求根 45 次，纯实现事实，**不是建议值**）。
"自检最小达标 n"＝ 用被测源码里逐字照抄的 `power_at_n` 做变步长整数扫描取首个达标 n；
**尺子自证**：同一函数先复现 s922-12 归档的 t 族值，逐位相符 ⇒ 没有另起一把尺子。

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s924-05/probe_fallback_census.py   # 写出 tmp/s924-05/probe_out.json
RULER: {"independent d=0.3":{"scan":351,"archived":351},"d=0.5":{"scan":128,"archived":128},"d=0.8":{"scan":52,"archived":52},
        "paired d=0.3":{"scan":90,"archived":90},"d=0.4":{"scan":52,"archived":52},"d=0.5":{"scan":34,"archived":34}}   # 6/6 逐位相符
HIT_BOUNDARY: anova_between f*(k=2)=0.044318 / f*(k=3)=0.040102 / f*(k=6)=0.032740
              correlation r*=0.051131 | chisq w*(df=1)=0.039620 / w*(df=4)=0.048858 | factorial f*(2x2)=0.031326
```

| 处 | 采样点数 | 命中上界 | 上界 NaN 透出 | 报告打 ✅ | 命中样本（效应量／返回／本模块口径自检 n） | 假数方向 |
|---|---|---|---|---|---|---|
| ① ANOVA 组间（f∈{0.01,0.05,0.10,0.15,0.25,0.40}×k∈{2,3,4,6}） | 24 | **4** | 0 | 20 | f=0.01×k=2/3/4/6 → 每组 2000；自检 39247／32119／27261／21385 | **欠配**（上界 < 自检） |
| ①′ rm_anova（共用同一枚） | 12 | **2** | 0 | 10 | f=0.01×k=2/3 → 2000；自检 19625／16060 | 欠配 |
| ② correlation（r 8 点） | 8 | **5** | 0 | 4 | r=0.05→3000（自检 3138）／0.04→3000（4904）／0.03→3000（8719）／0.02→3000（19620）／0.01→3000（78487） | 欠配 |
| ③ chisq（w 5 档×df∈{1,2,4}） | 15 | **3** | 0 | 12 | w=0.02×df=1/2/4 → 5000；自检 19623／24087／29839 | 欠配（另有 §3 的"低于自身下限"型） |
| ④ factorial（f 6 档×design∈{2x2,2x3,2x2x2}） | 18 | **3** | 0 | 15 | f=0.01 → `required_n` 8000／12000／16000（=2000×k）；每组自检 19623／16059／9812 | 欠配 |
| t 族对照（d∈{0.20,0.30,0.50,0.80}×配对/独立） | 8 | **6** | **2** | **8** | 独立 d=0.3/0.5/0.8→4000（自检 351/128/52）；配对 d=0.3/0.5/0.8→2000（自检 90/34/15） | **过配**（上界 ≫ 自检） |

⇒ 两型假数的**报告症状相反**：t 族 `actual_power=1.0`（或 NaN）而 6/6 全打「✅ 实际效力达到目标水平」——错在数不在判；
①②③④的 `actual_power` 多数 < 0.78 ⇒ 打 ⚠（判定其实说了真话），**唯一例外是 ②r=0.05**：`actual_power=0.782177 ≥ 0.80−0.02`
⇒ 落 `:380` 的 else 分支打「✅」＝与 t 族同型的假绿透出，且它同时是四处中离 Cohen「小效应」基准最近的一处（r 基准 0.10 / 分界 0.0511）。

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from src.experiment_design.power_analysis import _solve_n_for_correlation as s,format_power_report as f;r=s(0.05,0.80,0.05);print(r.required_n,r.actual_power,'✅' if '✅' in f(r) else '⚠')"
3000 0.7821774262264485 ✅
```

## 5. 消费面：四处假数各自能从哪张嘴出去（实测端到端）

链路（行号现取）：

```
$ rg -n "estimate_post_hoc|post_hoc_power" src/ app.py scripts/ | rg -v "^src/analysis/post_hoc_power.py"
src/analysis/runner.py:33   from . import post_hoc_power as _post_hoc_power
src/analysis/runner.py:966      ph = _post_hoc_power.estimate_post_hoc(output)
src/analysis/runner.py:970      output["post_hoc_power"] = None      ← 第 3 层裸 except（:965 try / :969 except Exception）
src/ui/renderers.py:86      def render_post_hoc_power(output: dict)   ← :98-106 st.info("…建议样本量 n≈{n_need}…")
src/ui/undergrad_wizard.py:3100  render_post_hoc_power(output)
src/experiment_design/design_engine.py:685 def _auto_power_analysis(...)  ← :689 correlation / :691,:701 t_test /
                                                                              :693,:699 factorial / :695,:697 rm_anova
src/experiment_design/design_engine.py:571 → :157  与 src/ui/experiment_design_ui.py:289 → format_power_report
$ rg -c "quick_sample_size|calculate_sample_size|experiment_design.power_analysis" app.py → 无命中（rc=1；rg 显式给路径，rc=1＝"零命中"而非"文件不存在"）
  双轨复核（AST 轨）：`.venv/Scripts/python.exe -c "import ast;t=ast.parse(open('app.py',encoding='utf-8').read());print([n.lineno for n in ast.walk(t) if isinstance(n,(ast.Name,ast.Attribute)) and getattr(n,'id',getattr(n,'attr','')) in ('calculate_sample_size','quick_sample_size','format_power_report','PowerResult')])"` → `[]`
  ＋同轨扫 `ImportFrom` 里 module 含 `power` 者 → `[]`
$ .venv/Scripts/python.exe -c "from src.analysis.post_hoc_power import _TEST_TYPE_MAP as m;print(len(m))" → 11 个 test_type
```

端到端实测（合成 in-memory `output`，零库零文件；命令＝`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s924-05/probe_trigger_reach.py`，
读数＝`tmp/s924-05/probe3_out.json` 的 `reachability` 节）：

| 入口 test_type → pa_test | post_hoc 实际吐出 | 结论 |
|---|---|---|
| `one_way_anova`（η²=0.0001→f=0.01，observed_n=90） | `needs_more_n=True, n_needed_for_080=2000` | ① **可达**，且 `required_n` 是**每组**数，而 `observed_n` 是**总** N（`post_hoc:281` 直接比大小）→ 单位不同源 |
| `welch_anova`（η²=0.05） | `needs_more_n=False, n_needed_for_080=65` | ① 可达，常规档不命中 |
| `repeated_anova`（η²=0.0001） | `n_needed_for_080=2000` | ①′ 与单因素共用一枚兜底，同样可达 |
| `pearson_corr`（max\|r\|=0.05，n=120） | `n_needed_for_080=3000, needs_more_n=True` | ② **可达且真会命中**（命中前提是矩阵里最大的 \|r\| 也 < 0.0511） |
| `spearman_corr`（0.30） | `n_needed_for_080=85, needs_more_n=False` | ② 可达，常规档不命中 |
| `chi_square_independence`（w=0.02） | `n_needed_for_080=5000` | ③ 可达（⚠ 口径见下） |
| `chi_square_gof`（w=0.02） | `n_needed_for_080=5000` | ③ 可达 |
| `two_way_anova`（η²=0.05） | **`None`** | ④ **从 post_hoc 不可达**：`_TEST_TYPE_MAP` 映射到 `factorial`，而 `estimate_post_hoc` 的 if/elif 链（:245-273）**没有 factorial 分支** ⇒ `:274 else: return None` |
| `independent_ttest`（d=0.5） | `n_needed_for_080=4000` | t 族对照：过配假数同样能走到 UI |

③ 的口径事实（**只登记，不判"该用哪个"**）：独立性检验的 `result.effect_size` 存的是 **Cramér's V**
（`src/analysis/chi_square.py:75-76 effect_size=round(float(cramers_v),4), effect_size_name="Cramer's V"`），
gof 存的才是 **Cohen's w**（`:139-140`）；而 `post_hoc_power.py:171 w = getattr(result,"effect_size",None)` 原样透传给
`_solve_n_for_chisq`（其 docstring `:229` 写 "lambda = N * w^2"），标签函数 `:315` 又写成 `"Cohen's w / Cramer's V"` 二合一。
⇒ 独立性检验这条路上"喂进求解器的量"与"求解器声明的口径"不同源，且 V 系统性 ≤ w ⇒ 更容易掉进 §4 的 w* 分界以下。交主班进待人工。

④ 的另一半不可达原因：仓内唯一会打到 `factorial` 的两个调用点把效应量**写死** `effect_size=0.25`
（`design_engine.py:693/:699`）⇒ 现网零触发；`quick_sample_size("factorial")` 缺省 d=0.5 亦不命中（实测 `n_total=36`）。

## 6. 与 t 族 A′ 的逐处对照：可迁移要点／不可迁移原因（完成标准②）

A′ 的现行定义（唯一出处，未落地）＝ `docs/insights/psy-power-solver-redesign-20260923.md:193-216`（`solved: bool`＋`failure_reason`，报告遇 `solved=False` 走"无法求解"分支）。
它的**硬前置**在两处吞点：`post_hoc_power.py:244-275`（`try` 包住 5 个 `calculate_sample_size` 调用，`except Exception: return None`）
＋ `runner.py:965-970`（再包一层 `except Exception → None`）；本班 AST 轨实测 post_hoc 全文共有 **9 处** `except Exception`
（handler 行 `:60/:69/:88/:94/:113/:141/:165/:227/:275`），设计稿只点了 `:275` 一枚。

```
$ .venv/Scripts/python.exe -c "import ast;t=ast.parse(open(r'src/analysis/post_hoc_power.py',encoding='utf-8').read());print(sorted([(n.lineno,n.handlers[0].lineno) for n in ast.walk(t) if isinstance(n,ast.Try)]))"
$ rg -c "calculate_sample_size\(" src/analysis/post_hoc_power.py → 5   # 正则轨；AST 轨同 5（:246/:250/:254/:262/:266）
```

| 处 | 一行结论 |
|---|---|
| ① ANOVA `:163-167` | **可迁移**，但要两点连坐：a) `failure_reason` 与 t 族**不同因**（本模块自身判据的"上界不足"vs t 族"中途 NaN"），共用一条文案会把两种病说成一种；b) 该族 `required_n` 单位是**每组**，post_hoc `:281` 拿总 N 与之比 ⇒ 光加 `solved` 字段仍留着单位错配，哨兵只能声明"没解出来"、管不了"解出来的单位和谁比"。收益面：一枚覆盖 `anova`＋`rm_anova` 两个分发名、4 个 test_type。 |
| ② 相关 `:206-210` | **最该先迁的一处**：四处里唯一"现网可达＋实测命中＋报告仍打 ✅"三者齐（`r=0.05→3000`、`actual=0.782177` 过 `:380` 判据），迁移成本与 t 族同形（同一枚 `except ValueError`）。要点：哨兵必须**同时**让 `:380` 判据读到，否则 ✅ 通道原样保留。不可迁移部分＝无（该族无 NaN 通路，`power_at_n` 用 `norm`）。 |
| ③ 卡方 `:237-241` | **可迁移但需先裁决第二形态**：`n_lo=df+2` 由入参决定 ⇒ 存在"区间颠倒"这一**不同性质**的 ValueError（实测 df=6000 时返回 5000，低于自身下限 6002）。A′ 若把两因合并成一个 `solved=False`，会把"入参越界"（该抛 `ValueError` 提示调用方）与"上界不够"（该报"无法求解"）混成一条；且消费面的 V/w 口径问题（§5）在哨兵之下**不会自动消失**。 |
| ④ 多因素 `:283-287` | **技术可迁移、现网无收益**：post_hoc 无 `factorial` 分支＋design_engine 两处硬编码 f=0.25 ⇒ 双重不可达。排序结论：若后续有人给 `estimate_post_hoc` 补 `factorial` 分支（那是**新开**一条到本兜底的通路），必须**先**给 `:283-287` 上哨兵再开分支，否则等于新辟一条无看守通路；顺序反过来就是一次自伤。 |

## 7. 现成看守面（双轨普查，供 s924-04／后续补哨兵单对照）

```
$ .venv/Scripts/python.exe -m pytest tests/test_power_analysis.py -q --collect-only 2>&1 | tail -1 → 55 tests collected in 2.20s   # 在册 55 基线未变（仅收集，未跑断言）
$ rg -n "bracket_ceiling" tests/test_power_analysis.py → 4 命中，全在 t 族（:237 独立 3 参／:247 配对 3 参／:255 NaN 2 参／:328 缺省 1）
$ rg -n "_solve_n_for_(anova_f|correlation|chisq|factorial_anova)" tests/ → 12 命中，其中参数点：anova 组间 (0.25,3)(0.10,2)(0.40,4)、rm (0.25,3,0.5)(0.10,2,0.5)(0.40,4,0.7)、corr (0.10)(0.30)(0.50)、chisq (0.10,1)(0.30,1)(0.10,4)(0.50,2)、factorial 四例全部固定 f=0.25
```

⇒ **四处 sibling 兜底在 55 例夹具里零覆盖**：每族被钉的效应量都落在 §4 分界之外
（corr 最小 0.10 > r*=0.0511；chisq 最小 w=0.10 > w*=0.0396；anova 最小 f=0.10 > f*=0.0443；factorial 连 f 都不参数化）。
`tests/test_post_hoc_power.py` 另有 7 处 `def test`（正则轨；AST 轨顶层 test 函数 0 ⇒ 该类全在 class 内），钉的是"不显示 achieved_power／键集"契约，无一钉上界。

## 8. 红线与零改动自证（完成标准③）

- 未改任何生产码／测试件／配置；未跑全量套件（同仓有写位兄弟班，纪律档 §九／十）；只跑过 `--collect-only`（2.20s，仅收集）。
- 未写库：`data/literature_feed/` 三件套 mtime 仍 `feed.sqlite 09-23 12:15 / -wal 09-23 12:16 / -shm 09-23 12:15`（本班未启 app、未跑 `AppTest`、未 import 任何 feed 模块 ⇒ 无需 `LITERATURE_FEED_DATA_ROOT` 守卫，此为否证性自证：`$ ls -la data/literature_feed`）。
- 不变量逐位未动：`$ for f in data/benchmark_history/*; do sha256sum $f | cut -c1-8; done` → `3d83f7e9 / dff47515 / 092d61b0 / 909b4799`，与纪律档 §四在册值相同。
- `git diff --cached --name-only` = 0；未 add、未 commit。
- 统计红线：本档所有 n 值都是"求解器返回了什么"或"该函数自身判据下首个达标 n"，**不构成对外效力分析结论、不指定"应该是多少"**；未改任何判据、未为凑判据动生产码。
- 在册红未碰：台账 81（`test_export_gate_global_scan`）／182／194／198／205⑥ 一律未消、未碰；本单不涉导出/下载/凭据/UI 入口 ⇒ 未加跑 `-k "download_buttons or export_gate"`。

## 9. 待订正清单（交主班进待人工台账；本班未改他班在册档）

| # | 在册件与位置 | 在册写法 | 磁盘现值（现取命令） |
|---|---|---|---|
| 1 | `zcode-bridge/inbox/s924-05.task.md:17` | 锚点 `src/analysis/post_hoc_power.py:164「        except Exception:」`，并把 4 处兜底暗示在同文件 | 该串在 `:165`；4 处兜底实为 `src/experiment_design/power_analysis.py:163-167/206-210/237-241/283-287`。两文件自建仓 ec45485 起零改动 ⇒ 属**投递即错**，非漂移。`sed -n '164,166p' src/analysis/post_hoc_power.py` |
| 2 | 同卷宗「做什么」段 | 「与**已落地** t 族 A′ 哨兵逐处对照」 | A′ 未落地：`rg -n "\bsolved\b" src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py` → 0；落地单 `s924-04` 仍在 `inbox/` |
| 3 | `docs/insights/psy-power-solver-redesign-20260923.md:180` | 「`post_hoc_power.py:244-276`：**6 处** `calculate_sample_size`」 | **5 处**（正则轨 `rg -c` = 5；AST 轨 5，双轨一致：:246/:250/:254/:262/:266） |
| 4 | `docs/insights/psy-power-solver-redesign-20260923.md:181` | 「`design_engine.py:685-693`（`_auto_power_analysis`）」 | 函数体到 `:701`（七个 return：:689/:691/:693/:695/:697/:699/:701）`rg -n "return calculate_sample_size" src/experiment_design/design_engine.py` |
| 5 | `zcode-bridge/done/s923-03.result.md:56` 与 `:144` | 「另 3 处（ANOVA／卡方／多因素）**零命中**」 | 应收窄为"在 Cohen 三档基准采样点上零命中"：实测分界 f*(k=2)=0.044318、w*(df=1)=0.039620、f*(2x2)=0.031326，分界以下必命中（本班 9 个命中样本，§4） |
| 6 | `src/analysis/post_hoc_power.py:315` 标签＋ `:171` 透传 | 效果量名 `"Cohen's w / Cramer's V"`；把 `result.effect_size` 直接当 w 传 | **口径待人工**：独立性检验的 `result.effect_size` 是 Cramér's V（`src/analysis/chi_square.py:75-76`），gof 才是 Cohen's w（`:139-140`）；求解器声明口径见 `power_analysis.py:229`。本班不动、不判该用哪个 |

## 10. 复算配方（下一班照抄即可）

```
# 1) 盘面绑定（先做：确认自己看到的还是同一态）
cd D:/code/psy-analysis && git rev-parse --short HEAD && sha256sum src/experiment_design/power_analysis.py
# 2) 行号表逐处摘录
sed -n '163,167p;206,210p;237,241p;283,287p;80,85p;114,118p' src/experiment_design/power_analysis.py
# 3) 全网格 census（77＋8 个测点，含尺子自证）——脚本是临时件，tmp/ 已 gitignore，可能已被清；重建见脚本头注释
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s924-05/probe_fallback_census.py
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s924-05/probe_trigger_reach.py
# 4) 端到端可达性（合成 output，零库）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys,types,pandas as pd;sys.path.insert(0,'.');from src.analysis.post_hoc_power import estimate_post_hoc as e;o={'test_type':'pearson_corr','result':types.SimpleNamespace(corr_matrix=pd.DataFrame([[1,.05],[.05,1]]),n_matrix=pd.DataFrame([[300,120],[120,300]]),effect_size=None)};print(e(o))"
# 5) 看守面基线
.venv/Scripts/python.exe -m pytest tests/test_power_analysis.py -q --collect-only 2>&1 | tail -1
```

⚠ 两条本机坑复用记录（下传给同仓下一班）：
① 本探针必须带 `PYTHONIOENCODING=utf-8` 才不把 `⚠/✅` 崩在 gbk（psy 与 kaoyan 相反，kaoyan 侧禁带）；
② `json.dumps` 对 `np.int64` 直接 TypeError ⇒ numpy 标量要在 `default=` 里显式转 int/float。

## 9.1 勘误落实记录（s927-62 追加 · 2026-09-29T05:0x 现取 · 纯插入，上文一字未改）

- 追加班：`qoder-executor-20260929-0450-psy102`（信箱单 `s927-62`）；HEAD `4d3608e`。
- 开工前置自检：`git status --porcelain -- docs/insights/psy-power-sibling-fallback-census-20260924.md` → **0 行（干净）**，
  `docs/insights/psy-power-solver-redesign-20260923.md` → 同样 0 行 ⇒ 两档的「工作树 == HEAD」成立，本记录只报单值。
- 删除数自证：本档以「纯插入」形态追加，`git diff --numstat` 的**删除列必须为 0**（插行数与验收读数见 `zcode-bridge/outbox/s927-62.result.md` 证据节）。

| # | §9 原条目 | 本次复核读数（命令 → 值） | 落点与状态 |
|---|---|---|---|
| 1 | `s924-05.task.md:17` 锚点「`post_hoc_power.py:164 except Exception:`」，且暗示 4 处兜底在同文件 | `sed -n '164,166p' src/analysis/post_hoc_power.py` → `:165` 才是 `except Exception:`（**§9 结论复验成立**）；<br>🔴 但 §9 记的四处兜底行号 `power_analysis.py:163-167/206-210/237-241/283-287` **已过期**：现读 `rg -n "n_lo, n_hi" src/experiment_design/power_analysis.py` → `:201 (k+1,2000)`／`:244 (5,3000)`／`:275 (df+2,5000)`／`:321 (2,2000)`，另有 `:104` 的 t 族（A′ 落地后整体后移约 38 行） | 勘误行只能追加在**本档**（任务书在信箱域 `done/s924-05.task.md`，卷宗「禁止事项」列信箱只读 ⇒ 本班不改）；<br>⇒ 本档 §2 行号表与 §1 的现值读数一并进入**历史态**，引用前须按上列命令现取 |
| 2 | 同卷宗「做什么」段的前提「与**已落地** t 族 A′ 哨兵逐处对照」不成立（§9 现值：`solved` 0 命中、`s924-04` 仍在 inbox） | `rg -c "\bsolved\b" src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py` → **16 ／ 9**（rc=0，不再是 0）；<br>`git log --oneline -1 -- src/analysis/post_hoc_power.py` → `2f08c60 feat(psy): s924-04＋s924-16 两单同归本笔（power 求解 A′ 拒答口径落地…）`；<br>`ls D:/code/zcode-bridge/done/s924-04.task.md` → 存在（已不在 inbox） | 🔴 **§9 第 2 条本身已被现实推翻**：A′ 于 `2f08c60` 落地、`solved` 哨兵已在两文件（`power_analysis.py:35-36` 定义、`:108/:111` 赋值）。<br>本班不改 §1/§6 正文，只在此登记：**以「A′ 未落地」为前提的全部段落（含本档 §6 的「不可迁移原因」列）现均失效**，重述属另单 |
| 3 | 设计稿 `psy-power-solver-redesign-20260923.md:180` 写「`post_hoc_power.py:244-276`：**6 处** `calculate_sample_size`」 | `rg -c "calculate_sample_size\(" src/analysis/post_hoc_power.py` → **5**（§9 结论复验成立）；`sed -n '180p'` 现文仍作「6 处」⇒ 错值未被任何人订正 | ✅ 已在设计稿档末追加勘误行（同档纯插入，见该档 §末「勘误（s927-62）」） |
| 4 | 设计稿 `:181` 写「`design_engine.py:685-693`（`_auto_power_analysis`）」，§9 订正为「实为 `:685-701`」 | `rg -n "def _auto_power_analysis" src/experiment_design/design_engine.py` → **`:755`**；`rg -n "return calculate_sample_size"` → **7 处**：`:759/:761/:763/:765/:767/:769/:771`<br>⇒ 「7 处」这个**数量**订正复验成立，但 §9 给的行号 `:689-701` **也已是历史值**（该件经 `7d1f05f s927-72`／`2f08c60 s924-04` 改写） | ✅ 已在设计稿档末追加勘误行，并写明「行号一律现取，勿抄 §9」 |
| 5 | `done/s923-03.result.md:56` 与 `:144` 的「另 3 处（ANOVA／卡方／多因素）零命中」应收窄 | `sed -n '56p;144p'` 逐字复现：`:56`「- 3.3 另外三个同型兜底点（ANOVA 9 点／卡方 12 点／多因素 4 点）实测**零命中**——列出来是为了"连坐修"而非"已坏"。」；`:144`「7. **同型兜底另 3 处…**今天零命中，但是同一枚未爆的雷；」 | ⛔ **不落笔**：目标是信箱域历史结果件（卷宗「禁止事项」＋波次 brief §A：信箱内容只读、改它＝改历史留痕）。<br>本班把「收窄口径」原文誊进本记录即完成可执行部分，实际回写请主班裁（待人工台账项） |
| 6 | 效果量口径：喂进求解器的是 Cramér's V 而声明是 Cohen's w（§9 锚点 `post_hoc_power.py:315` 标签＋`:171` 透传、`chi_square.py:75-76`／`:139-140`、`power_analysis.py:229`） | 复核**成立但锚点漂移**：`src/analysis/post_hoc_power.py:171` `w = getattr(result, "effect_size", None)` ✓ 原样透传；<br>标签二合一行现读 `post_hoc_power.py:353` `return "Cohen's w / Cramer's V"`（§9 记 `:315`）；<br>`chi_square.py:75-76` `effect_size=round(float(cramers_v),4)` / `effect_size_name="Cramer's V"` ✓、`:140` `effect_size_name="Cohen's w"`（gof 侧，§9 记 `:139-140` ✓）；<br>求解器声明口径行现读 `power_analysis.py:267`「lambda = N * w^2, 其中 w 是 Cohen's w 效应量」（§9 记 `:229`） | ⛔ **不落笔且不改码**：这是**统计口径**归属（V 当 w 用会算错 `lambda = N·w²`），红线＝只出材料不下判定；<br>本班不改 `post_hoc_power.py:353` 的标签、不裁该用哪个，**登记为主班待人工**；引用行号按本列现值 |

### 本次追加的三条硬结论（供主班收账）

1. **§9 的 6 条里只有 3 条还能直接落笔**（#3、#4 落设计稿；#1 落本档），**2 条撞信箱只读域**（#1 的任务书本体、#5），**1 条撞统计口径红线**（#6）。
2. **§9 自身正在老化**：#2 已被 `2f08c60` 推翻、#1/#4/#6 的行号已漂 ⇒ 本档任何行号引用前必须现取，`## 10. 复算配方` 第 2 步的 `sed -n '163,167p;…'` 区间**同样过期**（现读见 #1 列）。
3. 本档 §8 的「零改动自证」基线随同老化：它记的是 2026-09-25 的盘面；本笔追加后该档自身变成「被后班追加过」的状态，形态＝纯插入。

