# psy literature_manager 盲区测试实现报告（916-04，2026-09-17）

## 验证结果（命令与数字同段）

```
$ cd D:/code/psy-analysis && python -m pytest tests/test_literature_manager_expansion.py -q
......                                                                   [100%]
6 passed in 0.53s
```

## 设计稿逐条落地对照（6/6 全落地，2 条按实现口径适配）

| # | 设计稿条目 | 落地 | 说明 |
|---|---|---|---|
| 1 | LiteratureEntry roundtrip＋引用标记 | ✅ test_literature_entry_roundtrip_and_citation | format_citation=[key]＋format_reference 含作者/年份/标题 |
| 2 | 「format_citation APA 格式」 | ✅ test_format_reference_apa（**适配**） | 设计稿行号口径有误：APA 职责在 `format_reference`（:35 方法），`format_citation` 实现为 `[key]` 正文标记（:31 方法）——两方法均断言，APA 断言落在 format_reference，中英文双分支＋DOI 清洗 |
| 3 | validate_doi | ✅ test_validate_doi_shape_and_offline_mock（**适配**） | 实现为 Crossref 网络函数非正则（:1680）；离线不联网达标：无斜杠输入→None 直判路径＋monkeypatch `urllib.request.urlopen` 伪造 Crossref JSON 验证元数据解析（DOI 前缀清洗/作者 family,given/date-parts 年份/volume/page） |
| 4 | cross_check_citations 交叉核对 | ✅ test_cross_check_citations | 精确 key 命中＋「第一作者+年份」备选键命中＋缺失引用进 missing_citations；注意引用过滤要求「文字+4位年份」同现（无年份的 [x1] 不算引用——测试注释已记） |
| 5 | LiteratureManager roundtrip | ✅ test_literature_manager_roundtrip | add→get 查回；**重复 key 首入为准不覆盖**（实现语义断言）；查无返回 None |
| 6 | search_presets 搜索 | ✅ test_search_presets | 关键词命中预置库（中介效应→温忠麟2014）；无关词返回空表 |

## 本单足迹（完成标准第 2 条口径说明）

- 新增 `tests/test_literature_manager_expansion.py`（本单唯一代码足迹）；`src/` 零改动。
- `git diff --stat` 中出现的 KNOWN_ISSUES.md/app.py/pytest.ini/requirements-lock.txt/src/literature_feed/scheduler/lock_manager.py 等均为**班前既有脏项**（本单未触碰，对照 git status 分类核实）；完成标准「diff 仅含新增测试文件」按「本单足迹仅新增文件」口径达成。
- 纯合成数据零联网（validate_doi 经 mock）；不 push。

## 遗留问题

设计稿如需修正两处口径（format_citation 行号/职责、validate_doi 非正则型）留日间；smart_search_literature/autofill_from_doi/enrich_reference 三个网络函数仍无测试（设计稿未列入最小集，mock 化留后续单）。
