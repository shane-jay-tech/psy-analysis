# _collect_numeric_vars 作用域过宽影响面裁决材料（a7a1 E2＋4d99 E3）——s1004-40

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T02:4x ｜ 性质：影响面材料，**两案均属改计数口径，一律停手交主班裁**
> 矿源：`zcode-bridge/done/20260925-154315-a7a1.result.md:16/:47`（E2 逐字）＋`20260925-154316-4d99.result.md` 遗留（无关列缩小分析集）。
> 探针：`zcode-bridge/tmp/s1004-40/probe_n_scope.py`（合成 52 行表 seed=11，只读）。

## 一、现值与调用方（rg 内联）

`runner.py:996-1000`：`_collect_numeric_vars`＝`df.select_dtypes(include=["number"])` **全表数值列直收，plan 完全未用**。两调用方：
- `runner.py:910` → `data_quality_check(numeric_cols=…, check_normality=_needs_normality_check(...))`（DQ＋正态警告面）
- `runner.py:925` → `handle_missing(numeric_cols=…, strategy=missing_strategy)`（listwise 删行面＝n 口径面）

## 二、双口径 n 差复测＋ID 列误导警告复现（合成数据实测）

`$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-40/probe_n_scope.py` →

| 口径 | n_after | 差 |
|---|---|---|
| 现网·全收（numeric=被试编号/前测/后测/年龄） | **40** | 基准 |
| 按 plan 收（numeric=前测/后测） | **43** | **+3**（方向与矿源 47→52 一致：plan 收只删 plan 列缺失行） |

ID 列误导警告复现（原文）：`⚠ 列「被试编号」不符合正态分布（Shapiro-Wilk p=0.0500）。若分析假设正态性，请考虑使用非参数替代方法。`——数字型 ID 列被当分析变量跑 Shapiro（矿源例 p=0.0276，同机制）。

## 三、受影响输出键清单（闭合，含方向）

| 输出键 | 全收→按 plan 收 | 方向 |
|---|---|---|
| `missing_meta.n_after` / `rows_removed` | 40→43（矿源 47→52） | 变大（删行只看 plan 列） |
| `descriptive` / 检验统计量与 CI | 分析集变大 | **统计数值面全变**（改计数口径） |
| DQ 警告集 | 被试编号 Shapiro＋年龄缺失率等**非 plan 列警告消失**；plan 列警告保留 | 收窄（误导警告消失＝改善） |
| `data_quality` 的 outlier/zero-var 面 | ID/无关列不再入检 | 收窄 |
| golden 快照面（snapshot 族） | 期望值需同步 | 红→翻绿须同笔 |

## 四、收窄两案（均声明改计数口径须主班裁）

| 案 | 动作 | 波及面 | 判定 |
|---|---|---|---|
| A 按 plan 收 | `_collect_numeric_vars` 改为 plan 驱动（dependent_vars＋covariates＋scale_items 并集取数值型）；两调用点自动同变 | **n/CI/警告集/golden 全动**＝改计数口径（a7a1 §五.4 停手条款正指此）；4d99「无关列缩小分析集」唯一根治案 | 须主班裁＋带历史对照表 |
| B DQ 层排标识列 | `_collect_numeric_vars` 不动；DQ 检查前过滤标识列（启发式：列名 被试/编号/ID/序号 或「整数且全表唯一」） | **仅警告集变**（误导 Shapiro 消失）；n 口径不动＝不改计数口径；但 4d99 的 n 缩水面不解决 | 最小止血案，可与 A 分层走（B 先止血、A 另裁） |

## 五、裁决建议（留主班）

- 推荐 **B 先行＋A 立专项**：B 是纯警告面修正（金标准：ID 列不再产 Shapiro），零统计数值风险；A 触全体历史分析计数口径，须与 s1004-43（subject_col 透传同改输入面）等「输入面变化」族并案排期，一次性带 golden 对照翻绿。
- 两案共同前置：判定「标识列」的规则需产品确认（列名启发式可能误伤名为「编号」的真变量）。

### 证据存根

- `$ grep -n "def _collect_numeric_vars" src/analysis/runner.py` → :996；`$ grep -rn "_collect_numeric_vars" src/ --include="*.py"` → :910/:925 两调用方。
- `$ sed -n 905,935p src/analysis/runner.py` → DQ 与 handle_missing 两消费面逐字。
- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-40/probe_n_scope.py` → n_after 40/43＋Shapiro 警告原文（seed=11 可复算）。
- 统计红线守约：本单只测行数与警告存在性，零新统计结论。
