# psy 死 import 复扫——批#3 后现值 v2（s1025-08 材料）

- 生成：2026-10-26 19:5x+08 ｜ 单：s1025-08（只读材料单，**零删除——删除属裁决**）
- 上版：`artifacts/s-dead-imports.md`（s1023-11，2026-10-23，余 10 名）
- 复扫口径：`python tools/unused_import_census.py src --root . --json`（rc=0，快照 tmp/s1025-08/census-now.json）；逐名三面 grep -w（含 scripts/ 面；grep 不吃 .gitignore，无 data/ 漏检坑——s1025-04 前科防护）

## 1. 大盘现值（317→317，逐位零漂移）

| 读数 | reexport | suspect | string_ref | crossref | 合计 |
|---|---|---|---|---|---|
| s1023-11（10-23） | 102 | 199 | 8 | 8 | 317 |
| **本单 v2（10-26）** | 102 | 199 | **16** | **0（键缺席）** | **317** |

- **逐位对平：317/317 项 (file,line,name) 全同**——候选池零消化、零新增、零行漂移。
- 唯一漂移＝kind 归类：8 名 crossref→string_ref（池 8+8=16 守恒）。工具未变（`git log -- tools/unused_import_census.py` 唯一笔 9821b9f=s1010-39）；kind 判定依赖仓内他文件字符串引用面分布，s1023-11 后他单改档可翻动归类，**不动死活结论**（dead 判定以 usage=0＋三零人工复核为准）。

## 2. 现值清单（10 名全数在盘，零消化；计数与 v1 逐字一致）

| # | 文件:现取行 | 名 | census kind 现值（v1 值） | src/tests/scripts/tools | 本件唯一命中实测 |
|---|---|---|---|---|---|
| 1 | ui/literature_review_panel.py:26 | create_matrix | string_ref（crossref） | 2/13/0/0 | ✓ :26 import 行唯一 |
| 2 | ui/literature_review_panel.py:50 | search_summary | string_ref（crossref） | 2/0/0/0 | ✓ :50 唯一 |
| 3 | ui/literature_review_panel.py:55 | generate_gap_report | string_ref（crossref） | 2/0/0/0 | ✓ :55 唯一 |
| 4 | ui/undergrad_wizard.py:33 | generate_demo_engagement_data | string_ref（crossref） | 3/9/0/0 | ✓ :33 唯一 |
| 5 | ui/undergrad_wizard.py:34 | generate_demo_performance_data | string_ref（crossref） | 3/7/0/0 | ✓（同块） |
| 6 | ui/undergrad_wizard.py:35 | generate_demo_turnover_data | string_ref（crossref） | 3/8/0/0 | ✓（同块） |
| 7 | ui/undergrad_wizard.py:36 | generate_demo_360_review_data | string_ref（crossref） | 3/7/0/0 | ✓（同块） |
| 8 | ui/undergrad_wizard.py:145 | generate_revised_with_questions | string_ref（crossref） | 4/4/0/0 | ✓ :145 唯一 |
| 9 | ui/undergrad_wizard.py:1572+1690（双 import） | bar_with_error | suspect×2（同） | 5/8/0/0 | ✓ 两行均 import 行 |
| 10 | ui/undergrad_wizard.py:2392 | io_mod（import io as io_mod） | reexport（工具保守口径，同） | 1/0/0/0 | ✓ :2392 唯一 |

- **scripts 面 10/10 全零**（本单新增核验面，v1 结论维持）。
- tests/src 命中均为本体文件面（matrix.py/search.py/themes.py/demo_datasets_hr/paper_engine/renderers 等，v1 §表注同），非本件引用——不构成存活链。

## 3. 计数对平（s1011-14 三类）

- 已消化：**0** ｜ 仍引用（本件引用面存活）：**0** ｜ 仍死（建议删，待裁决）：**10**
- 对平：0+0+10 = **10** ✓（与 v1 余量一致，批#3 删腿仍未执行）

## 4. 处置建议（材料面，删除属裁决——与 v1 条款逐字继承，零翻案）

1. 批#3 删腿可全量执行：10 名三零维持（used=0/quoted=0/无转发链），s1010-07 七名定性无翻案，v2 三面复扫零新证据。
2. 删时同块重核纪律照旧（panel :26/:50/:55 块、wizard :33-36/:145/:1572/:1690 块，删单名须逐块重核同块他名存活，如 box_plot/scatter_with_regression 在 renderers 本件活）。
3. 行号以本档现取为准（与 v1 现取零漂移）；删腿开工仍以词边界 grep 现取兜底。
4. io_mod 维持「删」判（s1010-07 人工定性；工具 reexport 保守口径注记照旧）。
5. kind 漂移 8 名（crossref→string_ref）不影响裁决面，无需重审；若后续普查周期再现 kind 抖动，建议工具侧给 string_ref/crossref 判定一个稳定性注记（另单面，不急）。

## 复现

```bash
python tools/unused_import_census.py src --root . --json   # → totals 317（reexport102/suspect199/string_ref16）
grep -rn --include="*.py" -w create_matrix src/ tests/ scripts/ tools/   # 三面示例
grep -nw io_mod src/ui/undergrad_wizard.py   # → :2392 唯一命中
```
