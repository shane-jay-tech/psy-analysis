# 心理学报规约接入第二批与 write_keywords 窗口裁决材料（s1002-44，只读）

- 承 s922-116 遗留 2／s922-117 遗留／s924-60 遗留 3。**现值订正**：s924-60 已让 WRITING_RULES（title 键）在 write_title 接入＝6 常量的「声明性资产」状态**部分破冰**——现值消费面＝WRITING_RULES 1 处真读（:88 `_title_rule_max_len`），其余 SECTION_ORDER/ABSTRACT_RULES/EFFECT_SIZE_GUIDE/SIG_MARKS/STAT_FORMATS 等**仍零消费**（仅 __init__ 再导出与本文件 import 块悬空）。

## 一、现值 rg 读数

| 面 | 读数 |
|---|---|
| 规约键引用面 | `WRITING_RULES`：定义 psych_report_format.py:49＋真读 section_writers.py:88 一处＋import/再导出 3 处零使用；`SECTION_ORDER`/`ABSTRACT_RULES`/`EFFECT_SIZE_GUIDE`：section_writers.py:17 import 后**零使用**（悬空 import，s922-116 登记态延续） |
| 截断点清单 | ①write_keywords :169 `dv[:2] + iv[:2]`（每分析最多 4 变量，第 3 位 DV/IV 失明）；②write_introduction :220 `e.title[:20]+"..."`（魔数 20＋ASCII 三点，与全角「…」钳制风格不一致——对照 :112 title 钳制用「…」） |

## 二、write_introduction 文献预览接规约表草案

规约表加键 `WRITING_RULES["lit_preview"] = {"max_chars": 20, "ellipsis": "…"}`：
- 修前：`…发现{e.title[:20]}...`（例：「工作投入对员工创...」＋半角三点悬在行中）
- 修后：`…发现{e.title[:max_chars]}{ellipsis}`（例：「工作投入对员工创造性行为…」——20 字处全角「…」）；ASCII "..." 消灭，与 title 钳制风格归一。
- 红名单：tests 钉 "..."（ASCII 三点）的快照例（`rg -n '\.\.\."' tests/test_section_writers_offline.py` 现取预估 ≤2 例同批）。

## 三、write_keywords 窗口修法与产出对照

修法：`dv[:2] + iv[:2]` → 全量候选＋截总长（keywords 目标 3-5 个的规约本就存在）：
```python
for var in dv + iv:            # 不再各自切 2
    if var and var not in keywords and not var.startswith("_"):
        keywords.append(var)
keywords = keywords[:5]        # 规约上限兜底
```
- 修前样例：DV=[工作投入, 敬业度, 活力] IV=[领导风格] ⇒ 关键词=[工作投入, 敬业度, 领导风格]——**「活力」（第 3 位 DV）永失**。
- 修后同例：=[工作投入, 敬业度, 活力, 领导风格]——4 键全入且未超 5。
- 红名单：钉 `[:2]` 窗口形态的既有例（`rg -n "dv\[:2\]" tests/` 现取预估 1 例）＋关键词顺序敏感断言可能重排。

## 四、EFFECT_SIZE_GUIDE 悬空 import 清理（施工顺带项）

section_writers.py:17 import 面含 EFFECT_SIZE_GUIDE/SIG_MARKS/STAT_FORMATS/ACADEMIC_PHRASES 四名，本文件零使用——施工时随本批接入顺带清理：真接入的留、仍未接入的从 import 行摘除（`__init__` 再导出面保留）。零风险（纯 import 行减法）。

## 五、零码改自证

rg/python 读码；本单零触碰 src/。
