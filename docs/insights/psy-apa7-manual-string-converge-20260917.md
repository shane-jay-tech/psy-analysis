# questionnaire 侧手工拼 APA7 串收敛核验＋现状钉测（916p-a4-005，2026-09-17）

## 一、调用链证据（≥2 跳，逐跳盘上可核）

**处 1：academic_literature.py:417**（函数 `_parse_crossref_item`，:379 起）
- :417 `ref_apa7 = f"{first_author} ({year}). {title}. {container}."` → :419 DOI 追加 ` https://doi.org/{doi}` → **:444** `"reference_apa7": ref_apa7`（返回 dict 字段）→ **:154** `s.get("reference_apa7", "")` 与 **:312/:334** `reference_apa7` → 进入 academic_references_apa7 通道 ✓

**处 2：kb_search.py:190**（函数 `_search_crossref`，:118 起）
- :190 `reference_str = f"{first_author} ({year}). {title}. {container}."` → :192 DOI 追加 ` doi:{doi}` → **:206** `"reference": reference_str` → results.append → search_literature（:29）返回链 ✓

两处均为**真旁路**（d913d-28 审计判定成立），且两处 DOI 后缀形态**互不一致**（处 1 ` https://doi.org/`；处 2 ` doi:`）。

## 二、同输入对照（输入字段/两串原文/逐字符结论）

输入：first_author="Smith, J."，year="2020"，title="Latent growth modeling"，container="Structural Equation Modeling"，doi="10.1080/10705511.2020.1"

```
手工拼串（academic_literature 形态）:
'Smith, J. (2020). Latent growth modeling. Structural Equation Modeling. https://doi.org/10.1080/10705511.2020.1'
收敛面 format_reference（LiteratureEntry.format_reference）:
'Smith, J. (2020). Latent growth modeling. *Structural Equation Modeling*. https://doi.org/10.1080/10705511.2020.1'
```

逐字符结论：**不一致**。差异位置=第 42 字符起：收敛面期刊名带斜体星号 `*Structural Equation Modeling*`，手工串无；有卷/期/页时收敛面还会加 `, *卷*(期), 页`（同样带星号）。kb_search 变体另有一处：DOI 前缀为 ` doi:` 而非 ` https://doi.org/`。

## 三、现状钉测（tests/test_apa7_manual_string_pin.py，4 用例全绿）

```
$ .venv\Scripts\python.exe -m pytest tests/test_apa7_manual_string_pin.py -q
4 passed in 0.62s
```

- 钉 1：academic_literature 手工形态（无斜体＋https DOI 前缀）。
- 钉 2：kb_search 手工形态（` doi:` 后缀——与处 1 不一致的实证）。
- 钉 3：手工串 ≠ format_reference（差异可见化，改码后本用例应改写为相等断言）。
- 钉 4：收敛面基线（斜体星号＋DOI 无尾句点）。

## 四、改码方案草案（只写进报告，不落盘改 src）

最小 diff（两处各改 3-5 行）：把手工 f-string 替换为委托 LiteratureEntry：

```python
# academic_literature.py:417 附近（kb_search.py:190 同理）
from src.paper_writer.literature_manager import LiteratureEntry
entry = LiteratureEntry(
    key=f"{first_author.split(',')[0]}{year}", authors=author_names, year=year,
    title=title, journal=container, doi=doi, is_chinese=False,
)
ref_apa7 = entry.format_reference()
```

影响面评估：调用点各 1 处（:417/:190）；消费方（:154/:312/:334/:206）只读字符串，斜体星号新增属展示增强；无既有测试锁定这两串（rg tests 零命中）——预计 0 测试变红；kb_search DOI 形态变更（` doi:`→URL）需同步检查下游渲染是否处理 URL。

## 五、验收对照

- ✅ ≥2 条调用链 file:line 证据（各 3 跳）。
- ✅ 同输入对照段：输入字段、两串原文、结论「不一致」＋差异位置。
- ✅ pin 测试 4 passed ≥2（同段）。
- ✅ git diff --stat -- src/ 非空部分为班前既有 lock_manager（a4-003 已盘点），本班 src 零新增。
- ✅ 不跑真实文献抓取、不联网、不调 LLM；不 push。
