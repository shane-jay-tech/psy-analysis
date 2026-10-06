"""s922-121：文献矩阵启发式抽取（LLM 旁路路径）离线钉桩。

对象是 `src/literature_review/matrix.py` 的三个模块级私有函数
（`:204 _safe_json_parse` / `:231 _extract_main_finding` / `:249 _extract_limitations`）
以及 `auto_fill_abstract_info` 在 `use_llm=False`（默认）下的纯正则路径。

全部为**纯函数直调**，不注入任何 LLM 测试替身，不导入 requests/httpx。
最后一个用例用**子进程**断言 `sys.modules` 里没有网络栈模块
（同进程断言会因别的测试先导而过假绿）。

行为读数取自开工前实测，命令原文：
    .venv/Scripts/python.exe -c "from src.literature_review.matrix import \\
        create_matrix, auto_fill_abstract_info, _extract_main_finding as MF, \\
        _extract_limitations as ML, _safe_json_parse as JP; ..."
关键实测值：
    MF('') -> ''
    MF('本研究招募大学生 120 名。结果表明，社交焦虑与自尊显著负相关。局限为横断面设计。')
        -> '结果表明，社交焦虑与自尊显著负相关'
    MF 超长 -> len == 120
    ML('未来研究可采用纵向追踪设计以检验因果方向。') -> ''    # 「未来」不在关键词表
    JP('{}') -> {}（真值假但非 None）；JP('{\"a\": 1,}') -> None
"""
import pathlib
import subprocess
import sys

import pytest

from src.literature_review.matrix import (
    DEFAULT_DIMENSIONS,
    _extract_limitations,
    _extract_main_finding,
    _safe_json_parse,
    auto_fill_abstract_info,
    create_matrix,
)
from src.literature_review.models import LiteratureItem

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# 含小数的量值夹具：pd02 之前会被半角句号切走（实测原样保留，勿手改文案），
# 修复后 β=0.45 应完整存活——本夹具同时是「旧缺陷态」的对照物。
ABSTRACT_WITH_DECIMAL = (
    "本研究招募大学生 120 名，n=120。结果表明，社交焦虑与自尊显著负相关（β=0.45）。"
    "本研究的局限在于横断面设计。"
)


# ---------------------------------------------------------------- 主要发现

class TestExtractMainFinding:

    def test_empty_abstract_returns_empty_string(self):
        # 边界①：空摘要
        assert _extract_main_finding("") == ""

    def test_captions_clause_with_indication_keyword(self):
        out = _extract_main_finding(
            "本研究招募大学生 120 名。结果表明，社交焦虑与自尊显著负相关。局限为横断面设计。")
        assert out == "结果表明，社交焦虑与自尊显著负相关"

    def test_discovery_keyword_captured(self):
        assert _extract_main_finding("我们做了实验。研究发现，中介效应显著。") == "研究发现，中介效应显著"

    def test_sentences_shorter_than_ten_chars_are_skipped(self):
        # 「结果显示」仅 4 字被跳过，落到下一句
        assert _extract_main_finding("结果显示。结果表明这一路径成立。") == "结果表明这一路径成立"

    def test_no_keyword_falls_back_to_head_of_abstract(self):
        # 回退分支取 abstract 前 120 字，**保留句末标点**（与命中分支不同口径）
        out = _extract_main_finding("本文综述了社交焦虑的干预研究进展。")
        assert out == "本文综述了社交焦虑的干预研究进展。"

    def test_english_abstract_matched_case_insensitively(self):
        # 边界②：纯英文摘要
        out = _extract_main_finding(
            "A study of 200 cases. The results showed a strong link between anxiety and self-esteem.")
        assert out == "The results showed a strong link between anxiety and self-esteem"

    def test_overlong_abstract_truncated_to_120_chars(self):
        # 边界③：超长摘要
        out = _extract_main_finding("结果表明，" + "甲" * 500)
        assert len(out) == 120
        assert out.startswith("结果表明，")

    def test_decimal_statistic_survives_sentence_split(self):
        # pd02 修复态（2026-09-23）：本用例原先钉的是**缺陷态** `…（β=0`（半角句号把量值截断）。
        # 现切句器把「半角句点后紧跟数字」判为量值本体而非句末标点，β=0.45 完整留存。
        out = _extract_main_finding(ABSTRACT_WITH_DECIMAL)
        assert out == "结果表明，社交焦虑与自尊显著负相关（β=0.45）"

    def test_ordinary_english_period_still_splits(self):
        # 反向守门：句点后不接数字时照旧按句末标点切，防止守卫被写宽成「半角句点一律不切」。
        out = _extract_main_finding(
            "This study enrolled 120 cases. Results showed a reliable negative link here.")
        assert out == "Results showed a reliable negative link here"


# ---------------------------------------------------------------- 局限

class TestExtractLimitations:

    def test_empty_abstract_returns_empty_string(self):
        assert _extract_limitations("") == ""

    def test_captures_ju_xian_sentence(self):
        assert _extract_limitations("结果稳健。本研究的局限在于样本来自单一高校。") == "本研究的局限在于样本来自单一高校"

    def test_future_word_alone_is_not_a_limitation(self):
        # s1006-02 配方②二元组扩充后翻正：「未来研究/future research」二元组入列 ⇒
        # 「未来研究可…」句命中是配方本意（矿源实锤「未来研究需要…」漏检）。
        # 「未来」单词仍不算：二元组要求「未来研究」连缀，单词「未来」不满足。
        assert _extract_limitations("未来研究可采用纵向追踪设计以检验因果方向。") == "未来研究可采用纵向追踪设计以检验因果方向"
        assert _extract_limitations("未来的方向尚不明确。") == ""

    def test_no_minimum_length_filter(self):
        # 与 _extract_main_finding 的关键差异：局限分支不做 len<10 过滤
        assert _extract_limitations("局限很多。另一句较长的话在这里出现。") == "局限很多"

    def test_english_limitation_keyword(self):
        # 边界②：纯英文摘要
        out = _extract_limitations(
            "Findings were robust. Some limitations include self-report bias in this study.")
        assert out == "Some limitations include self-report bias in this study"

    def test_no_hit_returns_empty_string(self):
        assert _extract_limitations("本文综述了干预进展。") == ""

    def test_overlong_limitation_truncated_to_120_chars(self):
        # 边界③：超长摘要
        assert len(_extract_limitations("本研究的局限在于" + "乙" * 500)) == 120


# ---------------------------------------------------------------- 脏 JSON 容错

class TestSafeJsonParse:

    def test_plain_object_parses(self):
        assert _safe_json_parse('{"a": 1}') == {"a": 1}

    def test_markdown_fence_stripped(self):
        assert _safe_json_parse('```json\n{"a": 1, "b": [2, 3]}\n```') == {"a": 1, "b": [2, 3]}

    def test_prose_around_object_is_ignored(self):
        assert _safe_json_parse('Here is the answer: {"a": 1} hope it helps!') == {"a": 1}

    def test_empty_text_returns_none(self):
        assert _safe_json_parse("") is None

    def test_trailing_comma_returns_none(self):
        assert _safe_json_parse('{"a": 1,}') is None

    def test_truncated_object_returns_none(self):
        assert _safe_json_parse('{"a": 1') is None

    def test_object_braceless_text_returns_none(self):
        assert _safe_json_parse("totally not json") is None

    def test_empty_object_is_dict_not_none(self):
        # 调用方须用 `is None` 判失败，不能用真值判断
        out = _safe_json_parse("{}")
        assert out == {} and out is not None


# ---------------------------------------------------------------- 无 key / 断网可用性

class TestHeuristicPathWithoutLlm:

    def test_auto_fill_offline_populates_all_default_dimensions(self):
        item = LiteratureItem(
            key="k1", title="X 与 Y 的相关研究", authors=["张三"], year=2022,
            abstract=ABSTRACT_WITH_DECIMAL, relevance_score=0.8)
        matrix = create_matrix([item])
        assert matrix.dimensions == DEFAULT_DIMENSIONS
        res = auto_fill_abstract_info(item, matrix)
        assert res["method"] == "regex"
        assert set(res["extracted"]) == set(DEFAULT_DIMENSIONS)
        assert matrix.get_cell("k1", "主要发现") == _extract_main_finding(ABSTRACT_WITH_DECIMAL)
        assert matrix.get_cell("k1", "局限") == _extract_limitations(ABSTRACT_WITH_DECIMAL)

    def test_empty_abstract_short_circuits_to_regex_method(self):
        item = LiteratureItem(
            key="k2", title="空摘要", authors=["李四"], year=2023, abstract="", relevance_score=0.5)
        matrix = create_matrix([item])
        assert auto_fill_abstract_info(item, matrix) == {"extracted": {}, "method": "regex"}

    def test_import_and_heuristics_pull_in_no_network_module(self):
        # 判据「断网时矩阵仍可用」的子进程自证（同进程断言必假绿）
        child = (
            "import sys\n"
            "from src.literature_review.matrix import (\n"
            "    _extract_limitations, _extract_main_finding, _safe_json_parse)\n"
            "assert _extract_main_finding('结果表明，路径成立。')\n"
            "assert _extract_limitations('本研究的局限在于样本量。')\n"
            "assert _safe_json_parse('{\"a\": 1}') == {'a': 1}\n"
            "leftover = [m for m in ('requests', 'httpx', 'urllib3') if m in sys.modules]\n"
            "print('NET[' + ','.join(leftover) + ']')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", child],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
            encoding="utf-8", timeout=120,
        )
        assert proc.returncode == 0, proc.stderr[-400:]
        assert "NET[]" in proc.stdout, proc.stdout


@pytest.mark.parametrize("text", ["", "x", "没有关键词的一段中文描述内容"])
def test_main_finding_never_raises_on_awkward_input(text):
    out = _extract_main_finding(text)
    assert isinstance(out, str) and len(out) <= 120
