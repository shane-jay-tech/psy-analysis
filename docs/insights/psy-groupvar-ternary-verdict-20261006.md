# result_card :1412 三元式吞 group_var 裁决材料（s1002-42，2026-10-06，只读）

- 承 s922-122 遗留。**重大时点订正：主缺陷已被 pd02（2026-09-23）修复**——本单从「修法材料」转「现状核销＋残余面登记」。

## 一、修复态实锤（现值复测）

- 加括号修法已落地：`src/analysis/result_card.py:1412-1414` 现为
  `grouping = group_var_name or (card.variables.get("covariates", ["分组变量"])[0] if card.variables.get("covariates") else "分组变量")`
  ——三元式已收进括号，优先级坑消除。
- **复现对照**（本班实跑）：
  - 无 covariates ＋ group_var=["班级"] ⇒ `grouping='分组变量'`？**否**——经 build_card_from_output 全链路（result.group_var 先行）⇒ APA 文本「分组变量 class_id（12 组…）」（test_group_var_wins_without_covariates 正向断言绿）。
  - 矿源「group_var 被 or 吞」路径已不存在：group_var_name 非 None 时 or 短路直接生效。
- **钉桩翻正已完成**：矿源预判「改时 test_group_var_is_ignored_without_covariates 会红」——该例已由 pd02 同笔翻正为正向断言（docstring 载明修复态），无需本单再翻。

## 二、残余面（pd02 边界钉登记在案，未消）

`test_placeholder_still_used_when_nothing_is_known`：**既无 group_var 又无 covariates**（信息缺失态）时仍退回字面量占位 ⇒ APA 出「分组变量 分组变量（12 组…）」重复——pd02 刻意未扩到此层（占位文案口径属主班拍板面）。本单登记维持，处置选项：
- 甲：信息缺失态改单写「分组变量（12 组…）」（消重复，丢「占位未填」信号）；
- 乙：占位改「未指定分组变量」（消重复＋保留信号，文案变化最大）；
- 丙：维持现状（重复即「未配置」的可视提示）。
三选一交主班，均一行级。

## 三、同族「表达式优先级被吞」复查清单

- `set(...)[:3]` 同族点（psy10 记载）：result_card.py 内 `[:3]` 切片现值 **0 命中**（python 扫描 `[:3]` 零行）——该族点位已不在盘（可能随重构消失），psy10 记载过期。
- 本文件全文 `a or b if c else d` 形态扫描：:1412 一处（已修复）。同构风险面清零。

## 四、零码改自证

复现走 import 直算＋读既有钉桩例；src/ 零触碰。
