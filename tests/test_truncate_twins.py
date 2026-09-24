"""s923-42：psy 两处 `_truncate` 孪生实现的同构钉桩（只加测试，不合并实现）。

被钉的两份实现（2026-09-24 开工实测，锚点无漂移）：
    A = src/questionnaire/academic_literature.py:453  def _truncate(text: str, max_len: int) -> str
    S = src/literature_review/summarize.py:51         def _truncate(text: str, max_chars: int) -> str
    复核命令（本件不引入第三方依赖，可直接复算）：
        .venv/Scripts/python.exe -c "import inspect;from src.questionnaire import academic_literature as A;\\
from src.literature_review import summarize as S;print(inspect.getsourcelines(A._truncate)[1], inspect.getsourcelines(S._truncate)[1])"

来源与分工（开工前 rg 实测）：
- zcode-bridge/done/s922-143-kbsearch-offline.result.md 明写这两份「按『不做顺手改动』未纳入本件，
  若需一并钉桩请另开单」——本件就是那张「另开的单」。
- tests/test_kb_search_offline.py:30 钉的是**第三份**同名实现 `src/questionnaire/kb_search.py:354`，
  它与 A 行为等价但**对象不同**。该文件由同仓另一路写位在途修改，故本件**刻意不 import kb_search**
  （见 TestIsolationFromInflightFiles），避免把别人的在途状态引进本桩。
- 开工前全仓 tests/ 对这两份实现**零直接覆盖**：`rg -n "_truncate" tests/` 的 25 处命中全在
  test_kb_search_offline.py（打的是 K）；S 只被 test_literature_summarize.py:41 间接扫到一句
  「marker 在不在」，A 连间接面都没有。

判别性设计（本件的重点，不是随手堆断言）：
1) 每个断言都通过**模块属性**在调用期取函数（`AL._truncate(...)`），不 `from ... import _truncate`，
   这样「改一处」只会翻那一处的桩；变异自证正是靠 setattr 换实现来做的。
2) 归属锁（TestOwnershipLocks）钉住「两份不是同一个对象、源文件不同、参数名不同」，
   专拦「顺手合并成一份共享 helper」——合并后行为桩可能全绿，只有归属锁会红。
3) 分叉点各写成**配对桩**（同一输入下两行的期望值同时出现），任何一侧改口径都会红。

现状钉（**钉的是「现在这样」，不是「应该这样」**）：本件把两处已知可疑行为按现状钉死并在用例名里点名，
便于将来真要改时先红一次、逼一次复核；不代表它们已被裁决为缺陷。
"""
import ast
import inspect

import pytest

from src.literature_review import summarize as SM
from src.questionnaire import academic_literature as AL

# S 的中间省略标记（len 实测 17，S 的输出恒比预算多这么多）
SMARKER = "\n...[中间内容已省略]...\n"
# A 的尾部省略号（A 的输出恒比预算多 3）
A_SUFFIX = "..."


def _param_names(fn):
    return tuple(inspect.signature(fn).parameters)


def _ann_str(annotation):
    """统一 annotate 口径：A 无 `from __future__ import annotations`（拿到真类型），
    S 有（拿到字符串 'str'）。两边都归一成类型名字面串，才能写「同构」桩。"""
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation))


def _ann(fn, name):
    return _ann_str(inspect.signature(fn).parameters[name].annotation)


# ===========================================================================
# 归属与参数名锁：拦「合并实现」与「改签名」
# ===========================================================================

class TestOwnershipLocks:
    """孪生＝两个独立对象。合并成一份共享实现时本组必红（行为桩可能仍全绿）。"""

    def test_the_two_truncates_are_distinct_objects_in_distinct_files(self):
        assert AL._truncate is not SM._truncate
        a_file = inspect.getsourcefile(AL._truncate)
        s_file = inspect.getsourcefile(SM._truncate)
        assert a_file != s_file
        assert a_file.replace("\\", "/").endswith("src/questionnaire/academic_literature.py")
        assert s_file.replace("\\", "/").endswith("src/literature_review/summarize.py")

    def test_each_truncate_is_defined_in_its_own_module(self):
        assert inspect.getsourcefile(AL._truncate) == AL.__file__
        assert inspect.getsourcefile(SM._truncate) == SM.__file__

    def test_budget_param_name_diverges_max_len_vs_max_chars(self):
        """任务书点名的参数名差异：A 用 max_len，S 用 max_chars。"""
        assert _param_names(AL._truncate) == ("text", "max_len")
        assert _param_names(SM._truncate) == ("text", "max_chars")
        # 反向自证：各自的桩不能被另一份满足
        assert "max_chars" not in _param_names(AL._truncate)
        assert "max_len" not in _param_names(SM._truncate)

    def test_annotations_are_isomorphic_str_int_to_str(self):
        for fn in (AL._truncate, SM._truncate):
            sig = inspect.signature(fn)
            assert _ann(fn, "text") == "str"
            assert _ann(fn, "max_len" if fn is AL._truncate else "max_chars") == "int"
            assert _ann_str(sig.return_annotation) == "str"

    def test_no_default_values_on_either_twin(self):
        """两份都无默认值 ⇒ 预算必须显式传；加了默认值等于改调用方面。"""
        for fn in (AL._truncate, SM._truncate):
            assert [p.default for p in inspect.signature(fn).parameters.values()] == [
                inspect.Parameter.empty,
                inspect.Parameter.empty,
            ], fn.__module__


# ===========================================================================
# 三形态对照（任务书点名：超长截断 / 短文原样 / 空串）
# ===========================================================================

class TestThreeShapesConvergence:
    """三形态里唯一收敛的两态：空串与「不超过预算」。"""

    def test_empty_string_returns_empty_on_both_twins(self):
        assert AL._truncate("", 100) == ""
        assert SM._truncate("", 100) == ""

    @pytest.mark.parametrize("budget", [0, 1, 5, 100])
    def test_short_text_passes_through_verbatim_on_both_twins(self, budget):
        """短文原样：A 清洗后仍短（纯 ASCII 无空白，清洗是恒等），S 直接 len<=budget。"""
        text = "abc"[: max(0, min(3, budget))]
        assert len(text) <= budget
        assert AL._truncate(text, budget) == text
        assert SM._truncate(text, budget) == text

    def test_exact_budget_length_does_not_truncate_on_both_twins(self):
        """边界：A 用 `len > max_len`、S 用 `len <= max_chars` 提前 return ⇒ 恰等预算都不截。"""
        text = "x" * 10
        assert AL._truncate(text, 10) == text
        assert SM._truncate(text, 10) == text
        assert AL._truncate(text, 9) != text
        assert SM._truncate(text, 9) != text


class TestThreeShapesOverlongDivergence:
    """超长态是最主要的分叉：A 只截头补 `...`；S 头 6 成 + 尾 4 成、中间塞省略标记。"""

    def test_academic_truncate_is_head_only_with_ellipsis(self):
        assert AL._truncate("y" * 11, 10) == "y" * 10 + A_SUFFIX

    def test_summarize_truncate_is_head_and_tail_around_middle_marker(self):
        assert SM._truncate("y" * 11, 10) == "y" * 6 + SMARKER + "y" * 4

    def test_overlong_pair_diverges_on_the_same_input(self):
        """配对桩：同一输入两个期望值同时钉 ⇒ 任一份被改成另一份的口径就红。"""
        a_got = AL._truncate("y" * 11, 10)
        s_got = SM._truncate("y" * 11, 10)
        assert a_got != s_got
        assert (len(a_got), len(s_got)) == (13, 27)
        assert SMARKER in s_got and A_SUFFIX in a_got
        assert A_SUFFIX not in s_got.split(SMARKER)[0]  # S 的头段不补省略号

    def test_output_length_arithmetic_budget_plus_suffix_vs_marker(self):
        """长度口径：A = max_len + 3；S = max_chars + 17（省略标记本身的长度）。"""
        assert len(SMARKER) == 17
        for budget in (10, 100, 1000):
            assert len(AL._truncate("z" * (budget * 3), budget)) == budget + len(A_SUFFIX)
            assert len(SM._truncate("z" * (budget * 3), budget)) == budget + len(SMARKER)

    def test_summarize_head_ratio_is_floor_of_60_percent_not_round(self):
        """budget=11 ⇒ int(11*0.6)=6 头、5 尾。改成 round()/0.5 都会红这一条。"""
        out = SM._truncate("k" * 100, 11)
        assert out == "k" * 6 + SMARKER + "k" * 5
        assert out.startswith("k" * 6) and out.endswith("k" * 5)


# ===========================================================================
# 行为分叉：清洗面（A 有、S 无）
# ===========================================================================

class TestCleaningDivergence:
    """A 去 HTML 标签 + 折叠空白，S 原样不动。两处的预算口径也因此不同源：
    A 的 max_len 作用于**清洗后**的串，S 的 max_chars 作用于**原始**串。"""

    def test_html_tag_stripping_diverges_on_same_input(self):
        raw = "<p>hello <b>world</b></p>"
        assert AL._truncate(raw, 100) == "hello world"
        assert SM._truncate(raw, 100) == raw

    def test_whitespace_collapse_diverges_and_can_empty_the_value(self):
        """纯空白：A 折叠成 "" ⇒ 值被清空；S 原样返回。这是 A 侧的真实信息丢失面。"""
        raw = "\n\t  \n"
        assert AL._truncate(raw, 100) == ""
        assert SM._truncate(raw, 100) == raw
        assert AL._truncate("a   b\n\tc", 100) == "a b c"
        assert SM._truncate("a   b\n\tc", 100) == "a   b\n\tc"

    def test_academic_html_regex_eats_angle_bracket_comparisons(self):
        """现状钉：<[^>]+> 会把「a < b and c > d」当成标签吃掉中段（现存缺陷，非本单裁决）。"""
        raw = "a < b and c > d"
        assert AL._truncate(raw, 100) == "a d"
        assert SM._truncate(raw, 100) == raw

    def test_budget_applies_after_cleaning_on_academic_but_on_raw_on_summarize(self):
        """A：标签不计入预算；S：标签照算。同一输入喂两边会给出不同长度。"""
        raw = "<p>" + "a" * 5 + "</p>"
        assert AL._truncate(raw, 5) == "aaaaa"          # 清洗后恰等预算 ⇒ 不截
        assert SM._truncate(raw, 5) == "<p>" + SMARKER + "p>"  # 原始 11 字 > 5 ⇒ 头2尾3


# ===========================================================================
# 入参健壮性分叉 + 非 ASCII
# ===========================================================================

class TestInputRobustnessDivergence:
    def test_none_input_converges_to_empty_on_academic_but_raises_on_summarize(self):
        """A 的 `if not text` 兜住了 None；S 的 len(None) 直接 TypeError。"""
        assert AL._truncate(None, 100) == ""
        with pytest.raises(TypeError):
            SM._truncate(None, 100)

    def test_cjk_is_counted_in_characters_on_both_twins(self):
        """两份都是 len() 计数（码点非字节），但截断形态仍分叉。"""
        raw = "中文" * 5
        assert AL._truncate(raw, 3) == "中文中" + A_SUFFIX
        assert SM._truncate(raw, 3) == "中" + SMARKER + "中文"


# ===========================================================================
# 预算下限的现状钉（含两处可疑行为，改名即红，逼一次复核）
# ===========================================================================

class TestSmallBudgetCurrentBehaviour:
    """极小预算下两份都会「输出比预算长」；S 在 max_chars=0 时更把全文原样带出来
    （`tail_len = 0` ⇒ `text[-0:]` 是整串而非空串）。按现状钉，不判定对错。"""

    def test_zero_budget_academic_yields_bare_ellipsis(self):
        assert AL._truncate("abc", 0) == A_SUFFIX

    def test_zero_budget_summarize_leaks_whole_text_via_negative_zero_slice(self):
        assert SM._truncate("abc", 0) == SMARKER + "abc"
        assert "abc" in SM._truncate("abc", 0)  # 预算 0 却保住全文

    def test_budget_of_one_diverges_tail_only_vs_marker_plus_last_char(self):
        assert AL._truncate("abc", 1) == "a" + A_SUFFIX
        assert SM._truncate("abc", 1) == SMARKER + "c"

    def test_both_twins_can_return_more_characters_than_the_budget(self):
        for budget in (0, 1, 10):
            text = "q" * 30
            assert len(AL._truncate(text, budget)) > budget
            assert len(SM._truncate(text, budget)) > budget


# ===========================================================================
# 与在途件的隔离（本仓同刻另有写位在改 src/questionnaire/kb_search.py）
# ===========================================================================

class TestIsolationFromInflightFiles:
    """第三份同名 `_truncate` 在 kb_search.py:354，与 A 行为等价。本桩必须与它解耦：
    它被改坏时本件不得变红，它被合并时本件也不替它背书。"""

    def test_neither_twin_module_imports_kb_search(self):
        for mod in (AL, SM):
            tree = ast.parse(inspect.getsource(mod))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported += [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module)
            assert not any("kb_search" in name for name in imported), (mod.__name__, imported)

    def test_source_bodies_are_two_different_implementations(self):
        """源码形态自证：两份不是同一实现的别名（合并/转发都会红这一条）。
        第三份孪生 kb_search.py:354 的行为刻意**不**在此断言，免得把在途改动引进本桩。
        注意：源码里拿到的是**转义字面**（反斜杠 + n），不是 SMARKER 那个真换行串，
        所以这里按标记内的中文子串切，别写成 `SMARKER in s_src`（必假红）。"""
        a_src = inspect.getsource(AL._truncate)
        s_src = inspect.getsource(SM._truncate)
        assert a_src != s_src
        assert "text[:max_len]" in a_src and "中间内容已省略" not in a_src
        assert "中间内容已省略" in s_src and "max_len" not in s_src
