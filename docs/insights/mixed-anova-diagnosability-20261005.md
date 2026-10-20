# mixed_anova 小样本/畸形面板崩溃 定向报错裁决材料（a7a1 遗留）——s1004-44

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T02:3x ｜ 性质：复现取证＋方案材料，**不落生产码**
> 矿源：`zcode-bridge/done/20260925-154315-a7a1.result.md:117-135`（E3 逐字核对在册）＋:147 遗留 6。
> 探针脚本（合成数据、只读、零写盘）：`zcode-bridge/tmp/s1004-44/`（probe_verbatim.py＝a7a1 probe_sets.py o5/o6 段逐字复跑；probe_bal2.py＝E3-② 平衡对照复现）。

## 一、两崩溃形态复现（原数据形状＋原 run_analysis 路径，全部命中）

**① 畸形面板（重复单元格）**：a7a1 原始 long4（S1 出现两次 T2＋S2 带 T3，2 被试）逐字复跑 →
- `result=None`；`errors=['⚠ 完整数据仅6条记录…', '出现了意外错误：系统遇到了未预期的问题。']`
- 兜底文案原文锚点：`friendly_errors.py:188-195` 最终兜底（title=「出现了意外错误」，explanation=「系统遇到了未预期的问题。」）——**LinAlgError（Eigenvalues did not converge）未获定向诊断**，与 a7a1 读数一致。
- ⚠ 复现条件注记：同形状数据若被试数 ≥3×2 水平（我首轮直调探针）**不崩**——崩溃触发面是「被试数≤2×水平缺失/重复」的组合，非一切重复格；方案里的前置校验须按此宽度设计。

**② 平衡小样本（S1/S2×T1/T2 结构完全正确）**：→
- `result=None`；`errors=['⚠ 完整数据仅4条记录…', "分析过程出错：找不到指定的键/列：'F'"]`
- 兜底文案原文锚点：`friendly_errors.py:179-186` 类型标签兜底（KeyError→「分析过程出错：找不到指定的键/列」）——**技术真相是「每格 1 观测 ⇒ pingouin 返回表缺 F 列」，用户看到的是键/列错误**，与 a7a1 读数一致。

**RuntimeWarning 被吞路径（复现成功）**：两探针运行期 stderr 实测出现 `pingouin/parametric.py:574 RuntimeWarning: invalid value encountered in scalar divide`＋`pandas … Degrees of freedom <= 0`——而 `errors` 通道仅 2 条（无任何 warning 条目）。机理：warnings 非 exceptions，`runner.py` 的 `except Exception→friendly_explain` 链（:413 等）天然收不到；`output["errors"]` 无 warnings 域。

## 二、定向报错方案材料（三件套）

| 件 | 改法（行级） | 位置 |
|---|---|---|
| 1 前置校验（重复格） | mixed_anova 入口在 dropna 后断言 `clean.duplicated([subject, within]).any()` → `ValueError("混合设计ANOVA要求每个被试在每个组内水平只有一次观测，「{sub}×{w}」出现 N 次；请检查长表。")` | anova.py:616 dropna 后（between/within 水平校验旁） |
| 2 前置校验（每格观测数） | `clean.groupby([between, within]).size().min() >= 2` 不满足 → `ValueError("混合设计ANOVA要求每组×每水平至少 2 个观测（当前最小 X）。小样本请改用…或增加数据。")`——把 KeyError 'F' 的真相提前说破 | 同上 |
| 3 warning 通道 | runner 对 `pg.mixed_anova` 调用包 `warnings.catch_warnings(record=True)`，捕获条目以 `{"severity": "warning", "message": "统计库提示：<msg>"}` 并入 `output["errors"]`（或新增 `output["warnings"]` 域，由主班定） | runner.py:179 调用点（或 anova.py 内包） |

## 三、误伤面估算（既有绿件基线实测）

`$ pytest tests/test_assumption_router.py tests/test_assumption_route_count_pin.py tests/test_golden_stats_v2.py tests/test_keyword_dict.py tests/test_friendly_errors.py -q` → **108 passed rc=0**（27.63s，本班实测基线）。

- 4 件 mixed_anova 关联件（assumption_router/assumption_route_count_pin/golden_stats_v2/keyword_dict）现用数据均为合法形状 ⇒ 新前置校验不触发，预期零红；
- test_friendly_errors.py 断言的兜底文案不改（两新 ValueError 走 `_BACKUP_TRANSLATIONS` 之前的新模板位，原兜底链只增不改）⇒ 预期零红；
- 落地时必跑=上述 5 件＋`pytest -k mixed_anova`。

## 四、裁决建议（留主班，未实施）

- 推荐**件 1+2 先行**（纯前置校验、零统计数值面、报错文案即诊断），件 3 的通道形态（并入 errors vs 新域）属接口面，随主班拍板；
- 与 1b5e（export_feedback_package）同属「可诊断性/可观测」族，无代码交集可分批；
- 本单复现同时给 a7a1 的「能力边界读数」补了宽度注记（崩溃非一切畸形，见 §一 ⚠）——方案里校验文案已按宽度措辞。

### 证据存根

- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-44/probe_verbatim.py` → o5 通用兜底文案逐字＋RuntimeWarning stderr 复现。
- `$ .venv/Scripts/python.exe zcode-bridge/tmp/s1004-44/probe_bal2.py` → KeyError 'F' 兜底文案逐字。
- `$ sed -n 179,195p src/utils/friendly_errors.py` → 两级兜底原文；`$ sed -n 166,180p src/analysis/runner.py` → 分发面（grouping_var 缺列校验是唯一在世存在性校验）。
- `$ sed -n 594,640p src/analysis/anova.py` → mixed_anova 入口（between/within 水平数校验在世、重复格/每格观测数校验缺失）。
- `$ pytest <5 件> -q` → 108 passed（误伤面基线）。
- 禁令守约：零生产码改动（探针全在 zcode-bridge/tmp）。
