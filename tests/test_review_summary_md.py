"""src/ui/literature_review_panel._build_review_summary_md 钉桩（s918-47）。

纯函数直调（合成条目，不渲染 Streamlit、不读真实库）。
锚点：src/ui/literature_review_panel.py:897（模块 957 行）。
"""
import re

from src.literature_review.models import GapAnalysis, LiteratureItem, ThemeCluster
from src.ui.literature_review_panel import _build_review_summary_md


def _item(n, rel=50, doi=""):
    return LiteratureItem(title=f"文献{n}", authors=[f"作者{n}"], year=2020 + n,
                          journal="心理学报", doi=doi, relevance_score=rel)


def _notes(kinds):
    from src.literature_review.models import ReadingNote
    return [ReadingNote(type=k) for k in kinds]


def _themes(n):
    return [ThemeCluster(theme_name=f"主题{i}", centroid_keywords=[f"kw{i}", "共现"],
                         summary=f"小结{i}") for i in range(n)]


def _gaps(n, with_direction=True):
    return [GapAnalysis(gap_description=f"缺口{i}",
                        suggested_direction=f"方向{i}" if with_direction else "") for i in range(n)]


def test_header_counts_sorting_and_fields_are_present():
    md = _build_review_summary_md("中介效应是否有调节作用？", [_item(1, rel=60), _item(2, rel=90)],
                                  [], [], [])

    assert md.startswith("# 文献综述草稿")
    assert "## 1. 研究问题" in md and "> 中介效应是否有调节作用？" in md
    assert "## 2. 文献列表（共 2 篇）" in md
    assert re.search(r"_生成时间：\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}_", md)
    # 按 relevance_score 降序，且字段逐条出现（作者·年份·标题斜体·期刊）
    lines = [l for l in md.splitlines() if l.startswith("- ")]
    assert lines[0].startswith("- 作者2 (2022). *文献2*. 心理学报.")
    assert lines[1].startswith("- 作者1 (2021). *文献1*.")


def test_doi_is_appended_only_when_present():
    md = _build_review_summary_md("", [_item(1, doi="10.1/x"), _item(2)], [], [], [])

    assert "https://doi.org/10.1/x" in md
    no_doi_line = [l for l in md.splitlines() if l.startswith("- 作者2 ")][0]
    assert "doi.org" not in no_doi_line
    assert "## 1. 研究问题" not in md          # 研究问题为空 ⇒ 整节不出现
    assert [l for l in md.splitlines() if l.startswith("## ")] == ["## 2. 文献列表（共 2 篇）"]


def test_missing_research_question_leaves_the_numbering_gapped():
    """现状：章节号是写死的 1/2/3/4/5，缺前置内容时**不会重排**，草稿里会出现「## 2.」开头。"""
    md = _build_review_summary_md("", [_item(1)], [], _themes(1), _gaps(1))

    assert "## 1." not in md
    assert "## 2. 文献列表" in md and "## 3. 主题小结（1 个主题）" in md
    assert "## 4. Gap 分析（1 个）" in md and "## 5." not in md
    assert "### 主题0" in md and "**关键词**：kw0, 共现" in md
    assert "**建议方向**：方向0" in md


def test_gap_without_suggested_direction_omits_the_hint_line():
    md = _build_review_summary_md("q", [], [], [], _gaps(2, with_direction=False))

    assert "## 4. Gap 分析（2 个）" in md
    assert "### Gap 1" in md and "### Gap 2" in md
    assert "建议方向" not in md


def test_notes_section_counts_by_type_most_common_first():
    md = _build_review_summary_md("q", [_item(1)], _notes(["疑问", "疑问", "方法"]), [], [])

    assert "## 5. 笔记摘要（3 条）" in md
    assert "- 疑问：2 条" in md and "- 方法：1 条" in md
    assert md.index("- 疑问：2 条") < md.index("- 方法：1 条")


def test_empty_lists_still_render_headers_without_any_placeholder():
    """任务书假设「空列表→占位分支」，实现里**没有占位文案**：只出「共 0 篇」标题＋空行。"""
    md = _build_review_summary_md("", [], [], [], [])

    assert "## 2. 文献列表（共 0 篇）" in md
    assert not any(l.startswith("- ") for l in md.splitlines())
    assert "暂无" not in md and "无" not in md.split("## 2.")[1].split("##")[0]


def test_list_is_capped_at_twenty_items_while_the_header_still_reports_the_true_count():
    """【现状缺陷钉桩】标题写「共 30 篇」，正文只渲染相关度前 20 条，**没有任何"其余省略"提示**
    ⇒ 直接拿这份草稿去交就会静默少 10 篇文献。"""
    items = [_item(i, rel=i) for i in range(1, 31)]

    md = _build_review_summary_md("q", items, [], [], [])

    body = [l for l in md.splitlines() if l.startswith("- ")]
    assert len(body) == 20
    assert "## 2. 文献列表（共 30 篇）" in md
    assert body[0].startswith("- 作者30 ")               # 降序取前 20
    assert body[-1].startswith("- 作者11 ")
    assert "省略" not in md and "其余" not in md
