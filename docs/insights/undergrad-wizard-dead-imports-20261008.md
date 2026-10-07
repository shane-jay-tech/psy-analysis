# undergrad_wizard 死 import 人工定性材料＋heavy_preload 销案登记（s1010-07 降级腿，只读零删）

- 日期：2026-10-08 ｜ 性质：**降级只读定性**（前置 s1007-20 材料未出，按任务书条款不删）；执行删腿待 s1007-20 出件后另接
- 在途锚：undergrad_wizard.py porcelain M（他班在途）——本单零触碰，行号按现值快照（较任务书锚 +1~+3 漂移已订正）

## 七名逐名三态判定

| 名（现值行） | 词边界计数 | 判定 | 判据 |
|---|---|---|---|
| generate_demo_engagement_data（:33） | 1 | **删**（待执行腿） | 仅 import 行，全文件零使用 |
| generate_demo_performance_data（:34） | 1 | **删** | 同上 |
| generate_demo_turnover_data（:35） | 1 | **删** | 同上 |
| generate_demo_360_review_data（:36） | 1 | **删** | 同上；同块 list_hr_datasets 计 2＝活（import 块保留） |
| generate_revised_with_questions（:145） | 1 | **删** | **锚点 txt=3 系 `_stream` 子串假象**：:266/:273 为 `generate_revised_with_questions_stream`（另一名），词边界后本名仅 :145 import 行 |
| bar_with_error（:1572、:1690） | 2（双 import 行） | **删×2** | 两处函数内 import 列表各含此名，零使用——**锚点 txt=2 系双 import 而非字符串引用** |
| io_mod（:2392） | 1 | **删** | `import io as io_mod` 函数内别名，下游 ：2403/:2412 直用 st.download_button 发原始字符串，无 BytesIO 需求，别名零使用 |

- 判据口径：`grep -cE '\b名\b'`（词边界，防子串假象）；七名全数「仅 import 行命中」。
- 删腿波及预估：4 处 import 块（demo_datasets_hr 四连块留 list_hr_datasets；paper_engine 块留 generate_reviewer_questions 计 2＝活；:1572/:1690 两图表 import 块需同块核 box_plot/scatter_with_regression 存活——**删腿执行时须逐块重核同块他名**）；io_mod 单行删。

## heavy_preload 销案登记（预判成立）

`:13-21` 九连（scipy.stats/statsmodels.api/pingouin/sklearn.cluster/factor_analyzer/openpyxl/jieba/semopy/kaleido）——docstring 自述「预热语义逐字保持：daemon 线程、进程内只起一次、**导入失败静默**——真正用到时会有明确的懒加载错误提示」，全数函数内 import＋`# noqa: F401`。**预判合法保留成立，登记销案**（AST txt=1 口径对其天然误报：预热件的本职就是「只 import 不使用」）。

## 复现

```
$ grep -cE '\b<名>\b' src/ui/undergrad_wizard.py   # 七名各 1（bar_with_error=2 双 import）
$ sed -n '13,25p' src/ui/heavy_preload.py           # noqa＋静默 docstring 实证
```
