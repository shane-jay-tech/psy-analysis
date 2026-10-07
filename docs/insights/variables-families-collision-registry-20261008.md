# variables 字段族分案防撞登记（s1007-27）

- 日期：2026-10-08 ｜ 上游：s1007-02 遗留（「两族须分案防混淆」）｜ 性质：只读登记零改码

## 族 A：EvidenceRecord 四 list 字段（mutable aliasing 族）

- 定义：src/literature/evidence_record.py:13 类四字段——variables :21／measurement_tools :22／statistical_methods :23／tags :27
- 形态：**List[str]，对象共享（mutable aliasing）**——from_dict :57-59/:63 无拷贝直取、to_dict :38-44 同对象出（s1007-02 运行时实验四字段全 True 实锤）
- 读写矩阵：evidence_record.py 内 14 命中（定义 4＋to_dict 4＋from_dict 4＋消费 2）＋evidence_table_panel.py 构造 2 处/渲染 1 处＋tests 4 件 13 例（全 == 断言）
- 在案裁决：s924-64「补拷贝交人工点头」维持，两案波及已成文（s1007-02）

## 族 B：AnalysisResultCard.variables（dict 型同名族）

- 定义：src/analysis/result_card.py（AnalysisResultCard.variables，**dict 型**）
- 命中：**43 处/2 文件**（result_card.py＋src/ui/result_card_panel.py；grep `card\.variables`）
- 现值注：result_card.py 为 porcelain M 在途件（s1010 批起持续演进）——族 B 任何统一动作前须以落账后现值为准

## 分案理由（一句）

两族同名异型异域：族 A 是 literature 域 EvidenceRecord 的 List 别名语义问题（可变共享风险），族 B 是 analysis 域 AnalysisResultCard 的 dict 字段（无别名争议）——字段族统一若并案会把「拷贝语义修整」与「dict 键面治理」两类不相关改动搅在一起，故分案。

## 防撞约定

- 后续任何一方立项时，rg `variables` 全量命中必先按本档两族切分（EvidenceRecord 四字段 vs card.variables），禁跨族批量替换。
- rg 复现：`grep -rn 'card\.variables' src tests`（族 B）；`grep -n 'variables\|measurement_tools\|statistical_methods\|tags' src/literature/evidence_record.py`（族 A 本体）。
