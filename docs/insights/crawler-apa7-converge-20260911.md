# literature_crawler.to_apa7 收敛到 format_reference（2026-09-12 夜间执行班，任务 p911r-31）

> 执行：GLM-5.3-Flash 夜间执行班 sweep-20260911-2300。样板：`src/paper_writer/literature_manager.py:35 format_reference`（ecdb 收敛后单一定义源）。**未 commit；零联网；零写库。**

## 一、改动

`src/paper_writer/literature_crawler.py:46-53`：`CrawledReference.to_apa7` 的手工拼装（约 30 行）替换为——构造同字段 `LiteratureEntry`（key=派生探针键、year=str 化、is_chinese 透传、source 缺省 crossref）并委托 `format_reference()`。crawler 侧删除重复实现，格式单一定义源收敛到 literature_manager。

## 二、运行命令与结果

```
$ .venv/Scripts/python.exe -m pytest tests/test_crawler_apa7_converge.py -q
3 passed
$ .venv/Scripts/python.exe -m pytest -q tests/test_paper_writer.py tests/test_literature_format.py tests/test_citation_in_text.py
33 passed
```
（本单新增 3 测：publisher 缺失期刊分支、中文无斜体口径、>20 作者委托等价。）

## 三、中文斜体口径

**不受影响**：中文分支（is_chinese=True）在 format_reference 中本就无斜体标记（ecdb 已定「中文无斜体，保持现状」），实测输出 `温忠麟, 叶宝娟. (2014). 中介效应分析. 心理科学进展, 22(5), 731-745.` 无 `*`。

## 四、输出契约变化说明（等价性边界）

- **中文分支**：与旧实现逐字等价外的差异=期刊行结尾标点由旧「无句号」变为「.」（与 ecdb 收敛样板一致）；
- **英文分支**：新增期刊/卷的 Markdown 斜体（`*Journal*`）与 >20 作者 APA7 省略（前 19 + … + 末位）——旧 crawler 实现无此两特征；DOI 前导句点并入统一格式。此即「收敛」预期差异，下游消费（347 报告 apa7 字段→Markdown 渲染）兼容。
- publisher 缺失分支：CrawledReference 无 publisher 字段 → LiteratureEntry publisher=''，出版社分支自然不触发（有专项测试）。

## 五、遗留问题

- 若下游存在「纯文本渲染器」（不支持 Markdown 斜体），英文 apa7 的 `*` 需渲染端剥离（未发现此类消费点）；
- CrawledReference 无 publisher 字段，书籍类爬取条目如需出版社需先扩爬取结构（涉上游 API，超出本单）。
