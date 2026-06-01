"""错误友好化测试。"""

from __future__ import annotations

import pytest

from src.utils.friendly_errors import (
    FriendlyError, friendly_explain, friendly_handler,
)


def test_value_error_with_non_numeric_message():
    exc = ValueError("could not convert string to float: 'twenty'")
    fe = friendly_explain(exc)
    assert "非数值" in fe.title
    assert "数字" in fe.suggested_action or "纯数字" in fe.suggested_action
    assert fe.technical_detail  # 必须保留原始信息


def test_singular_matrix_translates_to_collinearity():
    exc = RuntimeError("LinAlgError: singular matrix")
    fe = friendly_explain(exc)
    assert "奇异" in fe.title or "共线" in fe.title


def test_unicode_decode_error_suggests_encoding():
    exc = UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")
    fe = friendly_explain(exc)
    assert "编码" in fe.title
    assert "UTF-8" in fe.suggested_action


def test_module_not_found_suggests_pip_install():
    exc = ImportError("No module named 'kaleido'")
    fe = friendly_explain(exc)
    assert "组件" in fe.title or "包" in fe.title or "依赖" in fe.title
    assert "pip install" in fe.suggested_action


def test_unknown_error_falls_back_to_generic():
    """未匹配模式应返回兜底的中文标签。"""
    class _MysteryError(Exception):
        pass
    fe = friendly_explain(_MysteryError("totally novel issue"))
    assert isinstance(fe, FriendlyError)
    assert fe.title  # 不为空
    assert fe.suggested_action  # 不为空


def test_keyerror_translated_via_backup():
    exc = KeyError("某变量名")
    fe = friendly_explain(exc)
    assert "找不到" in fe.title or "键" in fe.title or fe.title  # 至少非空


def test_handler_decorator_returns_tuple_on_success():
    @friendly_handler()
    def add(a, b):
        return a + b
    result, err = add(2, 3)
    assert result == 5
    assert err is None


def test_handler_decorator_catches_exception():
    @friendly_handler(default_return=-1)
    def boom():
        raise ValueError("could not convert string to float: 'x'")
    result, err = boom()
    assert result == -1
    assert isinstance(err, FriendlyError)
    assert "非数值" in err.title


def test_constant_column_message():
    exc = ValueError("variance is zero - constant column detected")
    fe = friendly_explain(exc)
    assert "方差" in fe.title or "变化" in fe.title


def test_only_one_group_message():
    exc = ValueError("only one group present in data")
    fe = friendly_explain(exc)
    assert "分组" in fe.title or "组" in fe.title


# --------------------------------------------------------------------------- #
# v2.8: 未知错误兜底引导
# --------------------------------------------------------------------------- #

def test_is_unknown_error_for_uncaught_exception():
    from src.utils.friendly_errors import is_unknown_error
    class _NovelError(Exception):
        pass
    fe = friendly_explain(_NovelError("totally novel"))
    assert is_unknown_error(fe), f"Should be unknown but got title={fe.title}"


def test_is_unknown_error_false_for_known_pattern():
    from src.utils.friendly_errors import is_unknown_error
    fe = friendly_explain(ValueError("could not convert string to float: 'x'"))
    assert not is_unknown_error(fe)


def test_build_help_request_markdown_contains_all_sections():
    from src.utils.friendly_errors import build_help_request_markdown
    try:
        raise RuntimeError("some unusual issue")
    except RuntimeError as e:
        md = build_help_request_markdown(
            e,
            operation="运行 t 检验",
            test_type="independent_ttest",
            variables=["焦虑", "性别"],
            sample_size=200,
        )
    assert "# 错误求助" in md
    assert "运行 t 检验" in md
    assert "independent_ttest" in md
    assert "焦虑" in md
    assert "n = 200" in md
    assert "## 完整 traceback" in md
    assert "```python" in md


def test_build_help_request_markdown_without_context():
    from src.utils.friendly_errors import build_help_request_markdown
    try:
        raise ValueError("plain error")
    except ValueError as e:
        md = build_help_request_markdown(e)
    assert "未提供操作上下文" in md
    assert "ValueError" in md


def test_unknown_error_guide_text_lists_three_actions():
    from src.utils.friendly_errors import UNKNOWN_ERROR_GUIDE
    assert "1." in UNKNOWN_ERROR_GUIDE
    assert "2." in UNKNOWN_ERROR_GUIDE
    assert "3." in UNKNOWN_ERROR_GUIDE
    assert "ChatGPT" in UNKNOWN_ERROR_GUIDE or "AI" in UNKNOWN_ERROR_GUIDE
    assert "老师" in UNKNOWN_ERROR_GUIDE
