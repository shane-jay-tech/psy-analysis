# psy 报告字段统一 v1 · alpha／omega／项目数／样本量／置信区间

- 信箱单：`20260925-120658-c36e`（风险档 B／工作类型 docs）
- 执行班：`qoder-executor-20260925-1300-psy67`，2026-09-25
- 字段口径版本：**`psy-analysis/report-fields/v1`**（单一事实源 `src/output/report_fields.py:REPORT_FIELDS_VERSION`）
- 基线 HEAD（改前取证钉短号）：**`fe763a4`**

> 🔴 **本文件统一"字段叫什么、怎么写、缺了怎么报"，不动任何统计数值结论。**
> α／ω／k／N／CI 的数值一律原样搬运；本班**未修改**任何既有渲染件，
> 因此现网报告里的每一个数字与改前逐字相同。

## 一、v1 统一字段表

| 族 | 统一字段名 | 类型 | 渲染写法 | 现存别名（普查所得，全部收敛到左列） |
|---|---|---|---|---|
| Cronbach's α | `alpha` | `float` | `α = 0.8125` | `alpha` |
| McDonald's ω | `omega` | `float` | `ω = 0.83` | `omega_value`、`mcdonald_omega` |
| 项目数 | `n_items` | `int` | `项目数 k = 12` | `item_count`、`n_factors_items`；文案面另有「题目数／题量／题目数量／总题量」 |
| 样本量 | `n_cases` | `int` | `有效样本 N = 240` | `n_obs`、`sample_size`、`total_n`、`n`；文案面「样本量 N =／N ≥」 |
| 置信区间 | `ci`（端点对 `ci_lower`/`ci_upper`） | `(float, float)` | `95% CI = [0.76, 0.855]` | `effect_size_ci_lower`/`_upper`、`rmsea_ci_lower`/`_upper`、`effect_size_ci`（**字符串形态**）、文案面「95% CI／90% CI」 |

规则：① 一名一义，`alpha` 不得再当"通用主指标"复用于 ω/CR/r/κ；② 计数族（k、N）写成整数，不写成小数；
③ CI 一律成对数值端点，不接受 `"0.76~0.855"` 这类字符串；④ 缺任何一项必须出提示（见 §三）。

## 二、改前实况普查（可复算）

探针：`D:\code\tmp\qoder-executor-20260925-1300-psy67\probe_c36e_fields.py`（只读，`src/**.py`＋`tests/*.py` 文本，未触 `data/`）

| 族 | 命中件数 | 命中次数 |
|---|---|---|
| alpha | 49 | 452 |
| omega | 16 | 107 |
| 项目数（5 种书写） | 35 | 444 |
| 样本量（含中文文案，8 种书写） | 68 | 443 |
| 置信区间（≥6 种书写） | 29 | 251 |

**"一名多用"直证**（这是本族最大的口径问题）：`src/analysis/reliability.py:12`

```
alpha: float    # 通用主指标（α/ω/CR/r/κ 等都填这里方便统一渲染）
omega_value: Optional[float] = None
```

⇒ 同一个 `alpha` 键在 `test_type="mcdonald_omega"` 时装的其实是 ω。
统一字段名可以做（本班已在 `report_fields.py` 定口径），
但**"该把哪个数填进 alpha"这件事本身就是分歧**，见 §四。

## 三、"输出缺字段提示"—— 改前不成立

现网用**占位符**冒充"已报告"，探针在 `src/**.py` 实测 **74 处**，样例：

```
src/analysis/sem.py:138-140            se_raw = row.get("Std. Err", "-")   / "z-value" / "p-value"
src/analysis/result_card.py:1082       from_var = path.get("from", path.get("predictor", "?"))
src/questionnaire/report_generator.py:62   f"   - 题目数：{dim.get('item_count', '-')} 题"
src/experiment_design/design_engine.py:579 f"{m.get('items','?')}题，α = {m.get('alpha','待定')}"
src/experiment_design/preregistration.py:451  f"- 计划样本量 N = {n.get('total', '?')}。"
```

⇒ `α = 待定`、`N = ?` 这类行**在报告里看起来是一格数据**，即"伪完整"。
契约（本班实现于 `src/output/report_fields.py`，测试件 `tests/test_output_report_fields.py`
实测 **24 例全绿**：18 个用例函数，其中 1 个带 7 例参数化）：

- 缺键／`None`／`NaN`／类型不符 ⇒ 一律进 `MissingField`，渲染成独立一行 `⚠ 缺字段：α 未提供（已尝试键 alpha）`；
- **绝不**输出 `-`／`?`／`待定` 占位；
- `collect_report_fields()` 返回 `(取到, 缺失)` 两集，对请求字段**互斥全覆盖** ⇒ 调用方只要两段都渲染就不可能伪完整。

## 四、"模板不自动替用户判断可接受阈值"—— 改前不成立，且本班**不擅自改**

实测 `src/**.py` 里阈值自动判定 **27 处**，密度最高的是信度族：

```
src/analysis/reliability.py:75   warning += f"⚠ α={alpha} 低于可接受水平（0.60）。"
src/analysis/reliability.py:119  warning="" if sb_r >= 0.70 else f"⚠ 分半信度={sb_r:.3f}，低于可接受水平（0.70）。"
src/analysis/reliability.py:176  warning = f"⚠ ω={omega} 低于可接受水平（0.60）。"
src/output/reasoning.py:293      "分半信度 ≥ 0.70 为可接受。…"
src/paper_writer/defense_qa.py:85 "低于可接受标准（<.70），不建议直接使用"
src/output/interpretation.py:377 level = "不可接受"
```

阈值本身已收口到单一来源 `src/analysis/reliability_bands.py`（s920-05），
但**"是否该由模板把档位说成结论"从未收口**。若按卷宗第一句直接把判读删掉，会撞到 4 份在册钉住件：

| 钉住件 | 行数 | 命中「可接受／优秀／良好／阈值」 |
|---|---|---|
| `tests/test_psychology_report_format_golden.py` | 290 | 23 |
| `tests/test_reliability_bands.py` | 125 | 18 |
| `tests/test_output_reasoning.py` | 237 | 8 |
| `tests/test_defense_qa.py` | 324 | 3 |

⇒ 这是"改判据文案＝改报告结论"的邻域，**不在 docs 单授权内**，两案交回主班裁（见 result 遗留问题 1）。
本班的中立面做法：`report_fields.py` **不 import** `reliability_bands` 的档位标签，
用例 `test_renderer_emits_no_band_labels` 直接拿 `RELIABILITY_BANDS ∪ {UNACCEPTABLE}` 的标签集逐条比对，
α 取 0.35／0.62／0.74／0.95 四档代表值渲染，断言**任何档位标签都不出现在渲染面**。

## 五、另一处口径分歧：末位舍入（登记，不裁）

```
$ .venv/Scripts/python.exe -c "print(round(0.8125,3), f'{0.8125:.3f}', round(0.8135,3))"
0.812 0.812 0.814
```

`src/analysis/reliability.py` 内 `round(` 出现 **30 次**（含 `round(alpha, 3)`），
即现仓报告末位由 Python 二进制浮点的 half-even 行为决定：**0.8125→0.812 而 0.8135→0.814**。
"统一字段"若要顺带统一位数，就必须选一种舍入规则 ⇒ 那会改动 α 的**读数**，本班不做。
`report_fields.py` 因此默认 `decimals=None`（原样搬运），显式给位数时被断言等于 `str(round(x, 3))`，
不引入第二种规则。

## 六、复算命令

```
cd /d/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe \
  D:/code/tmp/qoder-executor-20260925-1300-psy67/probe_c36e_fields.py          # rc=0，读数见 §二～§五
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_output_report_fields.py -q
                                                                                # 24 passed / rc=0
```

## 七、落地边界（未接线面）

`report_fields.py` 目前**零调用点**（除自身测试）。把 5 族字段从既有渲染件迁过来，
需要同时决定：① `ReliabilityResult.alpha` 的"通用主指标"用法是否拆名（拆名会改变渲染来源映射）；
② 74 处占位符是否换成提示行（会改变交付包与 docx／zip 导出的文本面，触本仓导出清单门禁）；
③ 阈值判读的去留（§四）。三处都在统计结论／新增入口邻域，本班一律不擅动。
