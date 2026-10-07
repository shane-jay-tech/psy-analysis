# f-string/隐式 str() 内嵌消费 AST 全量普查（s1007-28）

- 日期：2026-10-08 ｜ 上游：s1004-06 遗留（「AST 全量属另一单量级」）｜ 性质：只读普查零改码
- 口径：ast.JoinedStr 的 FormattedValue 内对 ExperimentDesign 13 个 List 字段名（research_questions/hypotheses/control_vars/inclusion/exclusion/apparatus/analysis_plan/ethics/references/notes/ivs/dvs/logs）的裸插值／.str 方法／str() 包裹，＋全仓 str() 包裹该字段名；src 面（tests 面不属消费族域）

## 总账

- **AST 命中 13 处/10 文件 → 真阳性 2 ／ 假阳性 11**（join/len 合法 List 语义）
- 分型：**高危消费（写入面）1** ／ 展示面 1 ／ 合法 List 语义 11

## 真阳性（2）

| 位点 | 形态 | 分型 | 说明 |
|---|---|---|---|
| src/experiment_design/preregistration.py:430 | `extracted["dependent_variables"] = str(dvs)` | **高危（写入面）** | List 经 str() 以 repr 形态（`['a', 'b']`）写入预注册抽取结果——下游消费该键即消费 repr 串；s1007-12 隐私审计同文件，修法建议 join(", ") 或原 List 直存（JSON 序列化自然保 List） |
| src/paper_writer/section_writers.py:321 | `f"\n{context.ethics}"` | 展示面 | List 裸插值进报告伦理节＝repr 形态展示（`['…']` 带括号引号）——**s930-06 ethics 已修例（docx_exporter:801）同族余部**，修法同款（`"\n".join(context.ethics)`） |

## 假阳性（11，合法 List 语义）

logistic_regression:143（len）／result_card:458（join，在途 M 件读侧注记）／llm_engine:168/:170（join×2）／interactive_qa:174（join×2）／paper_engine:98（len）／research_deliverable:99（str(len()) 计数）／section_writers:230（join）／literature_review_panel:1000（len）——join/len 为 List 正语义，不属族形态。

## 脚本（可复跑；FIELDS 为 13 字段名集）

```python
import ast
from pathlib import Path
FIELDS = {"research_questions","hypotheses","control_vars","inclusion_criteria","exclusion_criteria",
          "apparatus","analysis_plan","ethics","references","notes","ivs","dvs","logs"}
for p in sorted(Path('src').rglob('*.py')):
    tree = ast.parse(p.read_text(encoding='utf-8'))
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            for v in n.values:
                if isinstance(v, ast.FormattedValue):
                    names = ({x.id for x in ast.walk(v.value) if isinstance(x, ast.Name)}
                             | {x.attr for x in ast.walk(v.value) if isinstance(x, ast.Attribute)})
                    if names & FIELDS: print(p, n.lineno, sorted(names & FIELDS))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'str':
            if any(isinstance(x, ast.Name) and x.id in FIELDS for x in ast.walk(n)):
                print(p, n.lineno, 'str()')
```

## 遗留问题

- preregistration:430 与 section_writers:321 两处修法均零数值语义（字符串构造面），可作一枚微单收编（≈10 分钟）；是否修留主班（本单普查纪律零改码）。
- logs 字段（engine 自带）消费面在 engine 内部正常；app.py（ui 主文件）不在本轮 src rglob 外圈（在圈内已扫，零命中）。
