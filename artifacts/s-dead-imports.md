# psy 死 import 批#3 后续核验——余 10 名现值清单（s1023-11 材料）

- 生成：2026-10-23T23:59+08 ｜ 单：s1023-11（只读材料单，**零删除——删除属裁决**）
- 上批口径：plan-0127 §二「死 import 批#3 余 10 名」；批#2（s1007-20，commit 6f5e9f5）16 候选删 6 名/5 件后余量；候选重建自 s1010-39 census 留档快照（tmp/s1010-39-census.json，generated_at 2026-10-08T02:28:49，先于批#2 删除 04:44:36）。
- 本单复扫：`python tools/unused_import_census.py src --root . --json`（rc=0）→ totals 406→**317**（reexport 176→102 / suspect 201→199 / string_ref 16→8 / crossref 13→8）；快照留档 tmp/s1023-11/census-now.json。
- 复扫工具：s1010-39 常驻普查工具（AST usage=0＋词边界＋全仓 alternation；kind=dead/reexport/string_ref/crossref/suspect 保护类优先，保守向）。

## 现值清单（10 名，对平 16−6=10 ✓；零消化）

| # | 文件:现行号（锚行号） | 名 | census kind 现值 | 本件 used | 本件 quoted | reexport 面 | 三面（src/tests/scripts） | 建议 |
|---|---|---|---|---|---|---|---|---|
| 1 | ui/literature_review_panel.py:26（锚:23） | create_matrix | crossref | 0 | 0 | 无转发 | src2/tests13/scripts0 | 删（tests 命中=src/literature_review/matrix.py 本体面，非本件） |
| 2 | ui/literature_review_panel.py:50（锚:47） | search_summary | crossref | 0 | 0 | 无转发 | src2/tests0/scripts0 | 删（他名=src/literature_review/search.py:252 本体） |
| 3 | ui/literature_review_panel.py:55（锚:52） | generate_gap_report | crossref | 0 | 0 | 无转发 | src2/tests0/scripts0 | 删（他名=src/literature_review/themes.py:363 本体） |
| 4 | ui/undergrad_wizard.py:33（锚:32） | generate_demo_engagement_data | crossref | 0 | 0 | 无转发 | src3/tests9/scripts0 | 删（s1010-07 已判删待执行腿；tests 命中=demo_datasets_hr 本体面） |
| 5 | ui/undergrad_wizard.py:34（锚:32） | generate_demo_performance_data | crossref | 0 | 0 | 无转发 | src3/tests7/scripts0 | 删（同上） |
| 6 | ui/undergrad_wizard.py:35（锚:32） | generate_demo_turnover_data | crossref | 0 | 0 | 无转发 | src3/tests8/scripts0 | 删（同上） |
| 7 | ui/undergrad_wizard.py:36（锚:32） | generate_demo_360_review_data | crossref | 0 | 0 | 无转发 | src3/tests7/scripts0 | 删（同上） |
| 8 | ui/undergrad_wizard.py:145（锚:143） | generate_revised_with_questions | crossref | 0 | 0 | 无转发 | src4/tests4/scripts0 | 删（s1010-07 判 1；他名=paper_engine.py:824 本体自用面） |
| 9 | ui/undergrad_wizard.py:1572+1690（锚:1571+1689，双 import） | bar_with_error | suspect×2 | 0 | 0 | 无转发 | src5/tests8/scripts0 | 删（双 import 行均死；存活对照=renderers.py:18+:507 本件自用活、charts.py:28 本体） |
| 10 | ui/undergrad_wizard.py:2392 | io_mod（`import io as io_mod`） | **reexport（工具保守口径）** | 0 | 0 | 无转发 | src1/tests0/scripts0 | 删（s1010-07 定性「删」：下游 :2403/:2412 直发字符串无 BytesIO；工具 reexport 判定系保护类保守口径，人工三零复核仍死） |

## 计数对平（按 s1011-14 完成标准三类）

- 已消化：**0**
- 仍引用（本件引用面存活）：**0**
- 仍死（建议删，待裁决）：**10**（panel 3 ＋ wizard 6 名/7 行含 io_mod）
- 对平：0+0+10 = **10** ✓（与批#2 余量一致）

## 处置建议（材料面，删除属裁决）

1. 批#3 删腿可全量执行：10 名全部三零（used=0/quoted=0/无真再输出链），与 s1010-07 七名定性（generate_demo_*_data×4＋generate_revised_with_questions＋bar_with_error＋io_mod）完全吻合，无翻案。
2. 删时同块重核纪律（s1010-07 遗留原文）：panel :26/:50/:55 所在 import 块、wizard :33-36/:145/:1572/:1690 各 import 块删单名时须逐块重核同块他名存活（如 box_plot/scatter_with_regression 在 renderers 本件活、wizard 双块内是否活需删时现取）。
3. 行号漂移留痕：锚行号（s1007-20/s1010-39 时点）与本单现取相差 +1～+3（import 块上方行变动），删腿开工以本档「现取行号」或词边界 grep 现取为准，勿按旧锚硬改。
4. census 工具口径注记：io_mod 现值 kind=reexport（工具保护类保守口径，与 s1010-07 人工定性「删」不一致）——工具 reexport 判定按「import 行同名符号存在」保护，不辨函数内 alias import 的实际引用；工具作防回流钉，删腿裁决以人工三零为准（与 s1010-39 遗留注记口径一致）。
5. 全仓大盘：406→317 项（-89），其中 reexport 176→102（-74）为主力下降面——批#1/批#2/批 A/B（s1010-05 删 47 名/27 件、s1007-20 删 6 名/5 件等）清后防回流钉读数收窄，方向健康；suspect 面 201→199 基本持平，属下一普查周期候选池。

## 复现

```bash
# 现值复扫（本单读数 317 项）
python tools/unused_import_census.py src --root . --json
# 逐名三面（示例）
grep -rn --include="*.py" -w create_matrix src/ tests/ scripts/ tools/
# 本件零引用精化（示例）
grep -nw create_matrix src/ui/literature_review_panel.py   # → :26 import 行唯一命中
```
