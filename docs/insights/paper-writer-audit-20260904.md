# 论文写作辅助模块质量审查（psy-C4，2026-09-04）

- 范围：src/paper_writer/（含 literature_manager.py 1997 行、literature_crawler.py 927 行、defense_qa_kb.py 1713 行、paper_engine.py 1126 行、section_writers.py 996 行）、src/literature_review/（11 文件）、与 src/literature_feed 的边界
- 方法：静态审读 + 5 个构造样例直调 format_reference 实测（构造数据，非真实文献）；零代码改动

## 1. 能力面清单

| 能力 | 实现位置 | 说明 |
|---|---|---|
| 论文结构模板 | paper_engine.py + section_writers.py | 按 IMRaD 变体（引言/方法/结果/讨论）驱动章节生成；模板硬编码在 section_writers 的生成函数内 |
| 引用管理（APA 格式化） | literature_manager.py:30-75（format_citation/format_reference）、:1558（format_reference_list） | LiteratureEntry dataclass + 中英双语 APA7 分支 |
| 文献抓取 | literature_crawler.py（CrossRef/CNKI 等源） | 带 Bot UA 与限速 |
| 文献去重 | literature_manager.py（key 机制）+ literature_review/matrix.py | key 去重为主，语义去重未见 |
| 相关性排序 | LiteratureEntry.relevance_note（:28，人工标注字段）+ 预置条目 relevance_note（:99-224） | **人工相关性说明，无自动相关度排序算法** |
| 答辩 QA 知识库 | defense_qa_kb.py：QATemplate dataclass，方法×6 类别×3 难度索引（:40-52），占位符填充 | 结构化模板库，非关键词检索 |
| 文献综述（另一模块） | src/literature_review/（ingest/matrix/themes/synthesize/completeness） | 独立的综述矩阵工具链 |

## 2. 逐项质量评审（好/缺/风险，附行号）

| 项 | 评价 | 证据与说明 |
|---|---|---|
| 模板学术规范性 | **缺**（结构性缺口） | 无时态规范提示（方法过去时/结果过去时/讨论现在时无检查）；无人称/批判性表述引导；section_writers 以填空式生成，不校验段落职能。对照 APA7 与通用写作要点：缺力度最大 |
| 引用格式化-多作者 | **风险** | 英文 >20 作者时全量罗列（实测样例 3：21 位作者全部列出），APA7 要求"前 19 位 + … + 末位"；无 et al. 规则（et al. 仅适用于正文引用，而正文用的是 [key] 体系，见下） |
| 引用格式化-卷期页/DOI | **好** | 实测样例 2：`…*Behavior Research Methods*, *46*(3), 664-687. https://doi.org/…` 卷斜体、期括号、页码、DOI 清洗均正确（literature_manager.py:56-75） |
| 引用格式化-中文适配 | **部分** | 实测样例 4：`温忠麟, 叶宝娟. (2014). …心理科学进展, 22(5), 731-745.` 无期刊斜体（中文惯例可接受）；多作者间未用中文顿号规范可再议；页码/卷期结构正确 |
| 书籍类条目 | **缺** | 实测样例 5：无 journal 字段时输出 `作者 (年). 标题.` ——**出版社（Publisher）丢失**，书籍条目不完整 |
| 正文引用标记 | **风险** | format_citation（:30）输出 `[k1]` 数字键样式——与 APA 正文 `(作者, 年份)` 体系不一致，导出正文的引用风格是自造的；导出前需一步 key→(Author,Year) 的替换（未在代码中看到） |
| 爬虫限速与合规 | **好** | Bot UA 自报（:131,:202,:418）、请求间 sleep 1.1s/:270,:435、结果上限 100（:194,:440）——来源合规意识良好 |
| defense_qa_kb 结构 | **风险（易过期）** | 1713 行纯模板数据硬编码；模板带 {占位符} 自适应，内容过期风险低，但**与 method_catalog 的方法清单人工同步**（新增统计方法时 QA 库需手补）；检索为结构化索引（类别×难度）而非语义匹配——查准但查不全 |

## 3. 引用格式化 5 样例实测输出

```
样例1（英文单作者）  ref: Bandura, A. (1997). Self-efficacy: The exercise of control. *Freeman*.
样例2（英文两作者+DOI）ref: Hayes, A. F., & Preacher, K. J. (2014). Statistical mediation analysis. *Behavior Research Methods*, *46*(3), 664-687. https://doi.org/10.3758/s13428-013-0432-x
样例3（英文21作者）  ref: Author1, X., …, Author21, X. (2020). …（全量罗列，无"…"省略规则）
样例4（中文两作者）  ref: 温忠麟, 叶宝娟. (2014). 中介效应分析：方法和模型发展. 心理科学进展, 22(5), 731-745.
样例5（书籍/无期刊） ref: Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests.（出版社丢失）
```

## 4. 与 src/literature_feed 的职责边界

边界**基本清晰**：literature_feed=文献抓取管道（fetchers/parsers/scheduler，喂知识库）；paper_writer.literature_crawler=论文写作场景的即时文献抓取（CrossRef/CNKI）。**概念重叠点**：两者都有"文献抓取+入库"，crawler 写 paper_writer 自己的 library，feed 写 data/literature_feed——数据层各自为政，存在同一篇文献两处存储的可能；去重逻辑互不共享。风险等级低（用途不同），但 crawler 可考虑复用 feed 的 parsers。

## 5. 改进建议（三档，带工作量）

| 档 | 建议 | 工作量 |
|---|---|---|
| 模板文案补全 | section_writers 增加时态/人称提示注释与检查清单；defense_qa_kb 顶部加"新增方法时同步本库"维护说明 | S |
| 功能 gap | format_reference 补：>20 作者省略规则、书籍 publisher 字段、中文标点规范化；导出前增加 [key]→(Author, Year) 的正文替换器 | M |
| 结构重构 | 统一 paper_writer.literature_library 与 literature_review/literature_feed 的文献数据层（单一 library 表 + 共享去重/相关性排序），crawler 复用 feed.parsers | L |
