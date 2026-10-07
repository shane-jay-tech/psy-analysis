# required_n→n_total 彻底切两案材料·终版（s1007-36，零改码）

- 日期：2026-10-08 ｜ 上游：s1004-05（2026-10-07，两案并列留主班，荐 B）｜ 本单＝终版复核＋触发判定
- 性质：零改码材料；终版裁决权在主班

## ①影响面终版（2026-10-08 现值复核）

| 面 | s1004-05 时点 | 现值 | 漂移说明 |
|---|---|---|---|
| src 读点 | 10 处（power 10） | **16 处**：power_analysis 10／design_engine 3／preregistration 2／post_hoc_power 1 | **+6**：s930-05 prereg n_total 管线接线新增 design_engine +1、preregistration +2、post_hoc_power +1（读点扩散＝双键期自然增长） |
| tests 断言 | 30 处（5 件） | **30 处（5 件）**：test_power_analysis／test_prereg_n_total_piping_s93005／test_design_engine_aprime_caller／test_power_analysis_four_family_underpower／test_ui | 计数不变、件分布换代（aprime_caller/test_ui 为新件） |
| golden/快照依赖 | 0 | **0** | 切换不破快照（结论维持） |

## ②触发时机现值核

- PowerResult dataclass 所在件 power_analysis.py：**porcelain 干净、无在途契约修订**（最近三笔＝s1010-05 import 清理／s1004-05 docstring／s927-61 哨兵，均非契约面）。
- 全仓无 dataclass 契约修订计划在途的登记（zcode-bridge 待派批无此项）。
- **判定：契约修订触发窗未至**。s1004-05 建议「下一版 dataclass 契约修订时并做」——现值下并做窗口不存在，两案继续挂起等待，或主班特批独立排窗。

## ③终版裁决表

| 维度 | 案 A 一次切 | 案 B 双写过渡（上游荐） |
|---|---|---|
| 动作 | PowerResult.required_n 字段改名 n_total＋src 16 读点随改＋tests 30 断言随改 | 新增 n_total 属性（真键），required_n 降 property 别名，一期后删别名 |
| 波及 | 46 触点单 commit | src 16＋新属性；tests 30 不随动 |
| 回滚链 | 单 commit revert | 删别名 commit revert（主切换可独立回退） |
| 风险 | 30 断言一次翻面、漏点即 AttributeError 面广 | 双键并存期语义漂移窗口（别名只读已消解） |
| 与现值适配 | 触点已从 40 涨到 46，一次切成本随时间上涨 | 每新增读点自动落新键，成本不随时间涨 |

**终版建议**：维持上游荐案 B；触发建议改口——原「契约修订时并做」的窗口经核不存在，改为主班**任一次主动触碰 power_analysis.py 契约面的排窗时并做**（或独立 10 分钟微单：加属性+别名≈+8 行）。

## 证据

```
$ grep -rn required_n src --include=*.py | wc -l        → 16
$ grep -rn required_n tests --include=*.py | wc -l      → 30
$ grep -rn required_n src --include=*.py | sed 's/:.*//' | sort | uniq -c
→ post_hoc_power 1／design_engine 3／power_analysis 10／preregistration 2
$ git status --porcelain -- src/experiment_design/power_analysis.py → 空（无在途契约修订）
```
