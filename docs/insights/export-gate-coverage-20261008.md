# export_gate「所有导出入口必须经此检查」全称命题抽验矩阵（s1010-08，零改码材料）

- 日期：2026-10-08 ｜ 性质：**只读矩阵＋两案材料，零改码**（补接线/docstring 订正均留主班裁）
- 锚点现值：export_gate.py:1 docstring 逐字「导出强制门禁 — 所有导出入口必须经此检查。」✓；`run_export_gate` 生产调用方 2 件 ✓（deliverable_center_panel:14/:170/:182、undergrad_wizard:54/:66）
- **实测总账：`st.download_button` 真钮位 33 处/13 件**（grep -rc 34 含 docx_exporter.py:4 docstring 提及已剔除）；**经门 9／子出口 16／真野出口 8** —— docstring 全称命题**不成立**（经门覆盖率 9/33 ≈ 27%）

## 门禁语义基线

- 门禁中心（deliverable_center_panel）：`:170/:182` 双调 run_export_gate，未过门不渲染导出 UI；交付物=research_deliverable_{mode} 的 md/docx/pdf/zip＋元数据 json（:195-264）。
- gate 状态面（collect_project_state）：has_data/variable_types_set/文献计数/paper_bundle/analysis_results —— 门禁实际覆盖的是**论文交付包链**。
- wizard 包装器（:66-76）：门禁失败清产物＋error＋不渲染按钮——正确的经门形态样板。

## 矩阵（33 处逐处）

### 经门（9 处/2 件）
| 位点 | 判定依据 |
|---|---|
| deliverable_center_panel:207/:217/:237/:254/:264 | 门禁中心体内，:170/:182 门禁下游，未过门整段不渲染 |
| undergrad_wizard:72 | 经门包装器本体（失败清产物不渲染钮） |
| undergrad_wizard:857/:2403/:2415 | wizard 页内导出（:66 页级门禁下游；**逐处行级核待窗**，按页级门禁下游暂记经门） |

### 子出口（16 处/7 件）——同内容可经门禁中心取得，此为旁路直出
| 件（处） | 位点 | 判定依据 |
|---|---|---|
| literature_review_panel（5） | :690/:720/:730/:746/:932 | 文献综述面产物入 paper_bundle（gate 状态面组成），综述正文亦可经中心包导出 |
| questionnaire_panel（3） | :829/:841/:868 | 问卷/数据面＝has_data 上游；**:827 邻位直调 export_to_docx 绕门为锚点实锤例** |
| paper_preview_panel（2） | :121/:130 | 论文稿预览＝paper_bundle 同内容预览直出 |
| result_card_panel（2） | :119/:129 | 结果卡＝analysis_results 面直出 |
| renderers（2） | :446/:661 | 图表交付＝论文图表链直出 |
| project_panel（1） | :269 | 项目面导出＝门禁状态源直出 |
| experiment_design_ui（1） | :404 | 实验设计＝研究设计链直出 |

### 真野出口（8 处/4 件）——产物不在 gate 状态面/交付包覆盖内，从未被门禁语义触及
| 件（处） | 位点 | 判定依据 |
|---|---|---|
| evidence_table_panel（4） | :100/:102/:201/:203 | 证据表 md/csv/bib/ris 自有产物，不入 bundle |
| items_upload_panel（2） | :334/:353 | 条目上传/模板日志导出，与交付包无关 |
| questionnaire_import_panel（1） | :192 | 清洗日志下载，数据卫生面非交付面 |
| app_pages_text（1） | :154 | 页面文本工具下载 |

（注：锚点「questionnaire_panel 3——含 :827 直调 export_to_docx 绕门」现值：:827 为 export_to_docx 调用行、:829/:841/:868 为三枚 download_button——直调与按钮并存同段，矩阵按按钮位计 3、直调另记一行证据。）

## 两案材料

### 案 A：措辞订正（纯 docstring，零行为）
`export_gate.py:1` 改限定语，如：「导出强制门禁 — **论文交付包链的正式出口**（deliverable_center/wizard 交付路径）必须经此检查；各面板旁路下载与本门禁无关。」
- 波及：1 行 docstring；测试零影响。优点：诚实反映现状；缺点：把旁路合法化措辞化。

### 案 B：补接线（行为变更，主班裁）
- 最小面＝真野出口 4 件 8 处接 run_export_gate（evidence_table/items_upload/questionnaire_import/app_pages_text——但其中清洗日志/上传日志类**是否应设门禁本身存疑**，门禁语义是「研究成熟度」不是「禁止一切下载」）。
- 完全面＝子出口 7 件 16 处一并接门（旁路直出全部收编到中心），UI 流程改变明显（面板内一键下载变成中心两步）。
- 测试波及：ui 面测试涉及下载路径的件（panel characteristic 系）需逐件回归；预估 6-10 件测试需随动。
- 建议：**先案 A 止谎，案 B 拆两单**（野出口接门单＋子出口收编单）另排；门禁语义扩展（哪些下载值得设门）由主班定口径。

## 复现

```
$ grep -rn 'run_export_gate\|render_export_gate' src --include=*.py | grep -v export_gate.py   # 调用方 2 件
$ grep -rn 'st\.download_button' src --include=*.py | grep -v '^src/output/docx_exporter'      # 真钮位 33
$ sed -n '1,54p' src/ui/export_gate.py                                                          # gate 语义与状态面
```

## 零改码声明

本单零代码改动；唯一产出＝本矩阵档。git status 除本档（untracked）外零新增改动。
