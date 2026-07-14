"""综述合成模块测试（synthesize.py）：编号一致性、主题注入、空输入、兜底、压缩。

注意：LLMResponse.ok 是只读属性，不能作为构造参数传入。
"""

from src.literature_review.summarize import PaperSummary
from src.literature_review.synthesize import synthesize_review
from src.llm_gateway.gateway import LLMResponse, LLMUnavailableError


def _make_summaries(n=3):
    return [
        PaperSummary(
            literature_key=f"k{i}", title=f"Paper {i}",
            structured={"研究问题": f"Q{i}", "主要发现": f"F{i}", "方法": f"M{i}", "局限": f"L{i}"},
            raw_text="", ok=True, error="",
        )
        for i in range(n)
    ]


def test_citation_numbering_consistent(monkeypatch):
    monkeypatch.setattr("src.literature_review.synthesize.llm_chat",
                        lambda *a, **kw: LLMResponse(content="正文提及 [1][2][3] 等。"))
    result = synthesize_review(_make_summaries(3))
    assert result.ok
    assert len(result.citation_map) == 3
    assert [c["index"] for c in result.citation_map] == [1, 2, 3]
    assert "[1][2][3]" in result.markdown
    assert "## 参考文献" in result.markdown


def test_topic_in_prompt(monkeypatch):
    captured = {}

    def fake(messages, **kw):
        captured["user"] = messages[1]["content"]
        return LLMResponse(content="综述正文")

    monkeypatch.setattr("src.literature_review.synthesize.llm_chat", fake)
    result = synthesize_review(_make_summaries(2), topic="工作压力")
    assert "工作压力" in captured["user"]
    assert "工作压力" in result.title


def test_empty_input():
    result = synthesize_review([])
    assert not result.ok
    assert "无有效文献摘要" in result.error


def test_llm_failure_fallback(monkeypatch):
    def boom(*a, **kw):
        raise LLMUnavailableError("error")

    monkeypatch.setattr("src.literature_review.synthesize.llm_chat", boom)
    result = synthesize_review(_make_summaries(3))
    assert not result.ok
    assert len(result.markdown) > 0
    assert "摘要清单" in result.markdown


def test_empty_llm_content_falls_back(monkeypatch):
    monkeypatch.setattr("src.literature_review.synthesize.llm_chat",
                        lambda *a, **kw: LLMResponse(content="   "))
    result = synthesize_review(_make_summaries(2))
    assert not result.ok
    assert "摘要清单" in result.markdown


def test_compression_warning(monkeypatch):
    # 每篇压缩行需足够长，使总量超过 24000 字符阈值
    big = "字" * 400
    summaries = [
        PaperSummary(
            literature_key=f"k{i}", title=f"Paper {i}",
            structured={"研究问题": big, "主要发现": big, "方法": big, "局限": big},
            raw_text="", ok=True, error="",
        )
        for i in range(30)
    ]
    monkeypatch.setattr("src.literature_review.synthesize.llm_chat",
                        lambda *a, **kw: LLMResponse(content="综述正文"))
    result = synthesize_review(summaries)
    assert any("文献过多" in w for w in result.warnings)
    # 截断后参与综述的篇数应少于 30
    assert len(result.citation_map) < 30
