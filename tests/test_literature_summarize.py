"""逐篇摘要模块测试（summarize.py）：维度解析、主题、截断、LLM 兜底、批量跳过。

注意：LLMResponse.ok 是只读属性（由 content/cancelled/error 推导），不能作为构造参数传入。
"""

from src.literature_review.ingest import IngestedDoc
from src.literature_review.models import LiteratureItem
from src.literature_review.summarize import summarize_paper, summarize_papers
from src.llm_gateway.gateway import LLMResponse, LLMUnavailableError


def _make_doc(full_text="一些用于测试的文献正文内容。", abstract="原文摘要内容"):
    item = LiteratureItem(key="test_key", title="测试文献", abstract=abstract)
    return IngestedDoc(item=item, full_text=full_text, extraction_ok=True,
                       warnings=[], source_filename="t.txt")


def test_six_dimensions_parsed(monkeypatch):
    resp = "研究问题：RQ\n理论框架：TF\n方法：M\n样本：S\n主要发现：F\n局限：L"
    monkeypatch.setattr("src.literature_review.summarize.llm_chat",
                        lambda *a, **kw: LLMResponse(content=resp))
    result = summarize_paper(_make_doc())
    assert result.ok
    assert result.structured["研究问题"] == "RQ"
    assert len(result.structured) == 6


def test_topic_adds_relevance(monkeypatch):
    captured = {}

    def fake(messages, **kw):
        captured["user"] = messages[1]["content"]
        return LLMResponse(content="研究问题：RQ\n与主题相关性：高")

    monkeypatch.setattr("src.literature_review.summarize.llm_chat", fake)
    result = summarize_paper(_make_doc(), topic="工作压力")
    assert "工作压力" in captured["user"]
    assert result.structured.get("与主题相关性") == "高"


def test_truncation(monkeypatch):
    captured = {}

    def fake(messages, **kw):
        captured["user"] = messages[1]["content"]
        return LLMResponse(content="研究问题：RQ")

    monkeypatch.setattr("src.literature_review.summarize.llm_chat", fake)
    summarize_paper(_make_doc(full_text="A" * 20000), max_chars=12000)
    assert "...[中间内容已省略]..." in captured["user"]


def test_llm_unavailable_fallback(monkeypatch):
    def boom(*a, **kw):
        raise LLMUnavailableError("service down")

    monkeypatch.setattr("src.literature_review.summarize.llm_chat", boom)
    result = summarize_paper(_make_doc())
    assert not result.ok
    assert "摘要兜底" in result.structured
    assert "原文摘要内容" in result.structured["摘要兜底"]


def test_batch_skips_failed_extraction(monkeypatch):
    doc = _make_doc()
    doc.extraction_ok = False
    calls = []
    monkeypatch.setattr("src.literature_review.summarize.llm_chat",
                        lambda *a, **kw: calls.append(1) or LLMResponse(content="x"))
    results = summarize_papers([doc])
    assert len(results) == 1
    assert not results[0].ok
    assert "文件解析失败" in results[0].error
    assert calls == []  # 未调用 LLM
