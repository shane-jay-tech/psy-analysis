# 问卷题目上传 → AI 预审 → 排版导出（v4.1）

- **日期**：2026-05-23
- **范围**：psy-analysis v4.1 新增"上传现有题目"工作流
- **协作模式**：单架构师直写（well-bounded scope，跳过 GPT/DeepSeek 多方）
- **关联 plan**：`C:\Users\31563\.claude\plans\dreamy-whistling-koala.md`

## 起因

用户在「📁 数据上传」上传 `.md` 问卷题目文件，触发
`Markdown 文件中未找到表格（GFM 管道格式）` 报错。根因：现有数据通道
只接收**已收集的被试数据**（要表格），不接受**题目文本本身**。

产品缺口：
- AI 题目预审 (`ai_content_review`) 只支持文本框粘贴
- 问卷设计模式是 LLM 反向生成题目，方向相反
- 用户手头题目已起草/部分定稿，需要：上传→预审→排版印发

## 决策

新增一条独立工作流，最少切口接入：

| 层 | 文件 | 行为 |
|---|---|---|
| 解析 | `src/questionnaire/items_loader.py`（新增） | `.md`/`.docx`/`.txt` → `ItemsDoc(title, instructions, items, reverse_indices, ...)` |
| 导出 Word | `src/output/docx_exporter.py:build_questionnaire_docx` | 三线表 + 编号填写区 + Likert 锚点 + 反向题 (R) 标记 |
| 导出 PDF | `src/questionnaire/exporters.py:build_questionnaire_pdf` | fpdf2 + CJK 字体 + 同布局 |
| UI | `src/ui/items_upload_panel.py`（新增） | 4 步：上传→编辑→可选 AI 预审→Likert/导出 |
| 入口 | `app.py` 「📋 问卷设计」加子模式 radio | 不破坏原 LLM 生成流程 |
| 友好提示 | `src/data/loader.py:load_markdown_table` | 报错文案指向新入口 |

## 解析策略

三格式统一抽题，按优先级：
1. **编号题**：`1. ` `1、` `1)` `1）` `(1)` `第1题` → 严格回归处理"1、第一道题"无空格场景
2. **列表项**：`- ` `* ` `+ `
3. **段落题**：无编号无 bullet，但 ≥3 条候选行时按段落抽
4. **标题/指导语**：标题取 `#` 或第一行；指导语取标题与第一题之间的段落

反向题识别：`(反向)` `(R)` `[R]` `（反向）` `reverse` 等多种变体。

`.docx`：读 paragraphs（不读 table），将 Heading 1/Title 样式映射为 `# `；
`.md`：剥离 GFM 管道表与代码块再解析。

## 关键修复

1. `_NUMBERED_RE` 初版要求题号后必须 `\s+`，对"1、第一道题"失败。
   改为三选一分隔符：`(?:[)）][.、)）\s]*|[.、][.、)）\s]*|\s+)` —
   要么是闭括号，要么是点/顿，要么是空白。
2. `docx_exporter.py` 有两个尾巴一样的函数，Edit 工具拒绝。
   写一次性脚本 `_append_questionnaire_docx.py` 追加 + 自删。
3. fpdf2 新版 `add_font(uni=True)` 已弃用，新代码移除该参数。

## 测试

- `tests/test_items_loader.py`（新增 19 测试）：三格式 × 编号/bullet/段落 ×
  反向题识别 × 边界（空文件/纯标题/错乱编号/中文编号样式）
- `tests/test_questionnaire_export.py`（新增 14 测试）：
  - `.docx` 输出 zip magic `PK\x03\x04`
  - PDF 输出 `%PDF` magic
  - 5/7 点 Likert × 自定义锚点 × header_meta × 反向题烟雾测
  - 入参校验（scale_points 范围 / anchors 长度）
  - 端到端集成：`.md` → 解析 → docx + pdf

回归：**1200 passed, 4 skipped**（baseline 1166，+34 新测试，0 新失败）。

## 不在本期范围

- 题目存档、题库管理、跨研究复用
- 上传题目 → 后续被试数据按题号自动匹配
- 真专家 CVI 评分矩阵接入（已有 `cvi` 检验，不混入预审流程）

## 风险与回退

- AI 预审使用 4 位同模型 persona，I-CVI/S-CVI 失去统计独立性 →
  UI 已显式标注"非正式 CVI，不可写入论文方法学，仅作题目修订工具"。
- PDF 依赖 `find_chinese_font()`，环境无中文字体时抛 RuntimeError；
  UI 已 fallback 到 Word 下载并提示。
- 子模式 radio 默认指向"AI 设计新问卷"，不改变老用户路径。
