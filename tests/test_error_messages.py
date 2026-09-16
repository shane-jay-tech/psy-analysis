# -*- coding: utf-8 -*-
"""error_messages.py 特征化测试（916p-a4-004，盲区补测：importers=0 真盲区）。

只固定现状行为，不评判文案好坏；不 import 下划线私有函数。
可复跑：.venv/Scripts/python.exe -m pytest tests/test_error_messages.py -q
"""
import src.utils.error_messages as em
from src.utils.error_messages import UserFriendlyError, format_error_for_streamlit


# ── UserFriendlyError 基础契约 ──

def test_default_severity_and_required_fields():
    """口径来源：src/utils/error_messages.py:19 severity 默认 'error'；四个必填字段。"""
    e = UserFriendlyError(what="w", why="y", impact="i", actions=["a"])
    assert e.severity == "error"
    assert (e.what, e.why, e.impact, e.actions) == ("w", "y", "i", ["a"])


def test_to_markdown_structure():
    """口径来源：src/utils/error_messages.py:23-32 四个固定小节标题＋actions 顺序编号。"""
    e = UserFriendlyError(what="W", why="Y", impact="I", actions=["做一", "做二", "做三"])
    md = e.to_markdown()
    lines = md.split("\n")
    assert lines[0] == "**发生了什么**: W"
    assert lines[1] == "**为什么会发生**: Y"
    assert lines[2] == "**会影响什么**: I"
    assert lines[3] == "**你可以怎么做**:"
    assert lines[4] == "  1. 做一"
    assert lines[6] == "  3. 做三"
    assert len(lines) == 4 + 3  # 4 个小节行 + actions 行数


def test_to_streamlit_dict_contract():
    """口径来源：src/utils/error_messages.py:34-40 键集 {type,title,detail}，detail==to_markdown()。"""
    e = UserFriendlyError(what="标题", why="原因", impact="影响", actions=["x"], severity="warning")
    d = e.to_streamlit_dict()
    assert set(d.keys()) == {"type", "title", "detail"}
    assert d["type"] == "warning"
    assert d["title"] == "标题"
    assert d["detail"] == e.to_markdown()


# ── 模板函数逐个特征化 ──

def test_table_generation_failed_template():
    """口径来源：src/utils/error_messages.py:44-57 warning 级、reason 拼入 why。"""
    e = em.table_generation_failed("CFA", "card-9", reason="字段缺失")
    assert isinstance(e, UserFriendlyError)
    assert e.severity == "warning"
    assert e.actions and len(e.actions) == 3
    assert "字段缺失" in e.why and "CFA" in e.what and "card-9" in e.why


def test_privacy_precheck_blocked_template():
    """口径来源：src/utils/error_messages.py:59-75 error 级、examples 前 3 个拼入 why。"""
    e = em.privacy_precheck_blocked(5, 2, ["key1", "key2", "key3", "key4"])
    assert e.severity == "error"
    assert "5 处敏感信息" in e.what and "2 处高风险" in e.what
    assert "key1" in e.why and "key3" in e.why and "key4" not in e.why  # 只取前 3
    assert "阻断" in e.impact  # 阻断语义在 impact（actions 为处置建议）


def test_llm_unavailable_template():
    """口径来源：src/utils/error_messages.py:77-91 warning 级、reason 拼入 why。"""
    e = em.llm_unavailable("网络中断")
    assert e.severity == "warning"
    assert "网络中断" in e.why
    assert len(e.actions) == 4


def test_pdf_unavailable_template():
    """口径来源：src/utils/error_messages.py:93-106 info 级（唯一 info 模板）。"""
    e = em.pdf_unavailable()
    assert e.severity == "info"
    assert "LibreOffice" in e.actions[0] or "LibreOffice" in e.why
    assert e.actions


def test_cfa_sem_not_converged_template():
    """口径来源：src/utils/error_messages.py:108-123 默认 reasons 兜底。"""
    e = em.cfa_sem_not_converged("ML")
    assert e.severity == "error" or e.why
    assert "ML" in e.what
    e2 = em.cfa_sem_not_converged("ML", ["样本太少"])
    assert "样本太少" in e2.why


def test_next_steps_empty_template():
    """口径来源：src/utils/error_messages.py:125-138。"""
    e = em.next_steps_empty()
    assert isinstance(e.actions, list) and e.actions
    assert e.severity in ("error", "warning", "info")


def test_export_missing_dependency_template():
    """口径来源：src/utils/error_messages.py:140-155 missing 参数出现在文案中。"""
    e = em.export_missing_dependency("python-docx")
    assert "python-docx" in (e.what + e.why)
    assert e.actions


# ── format_error_for_streamlit ──

def test_format_error_for_streamlit():
    """口径来源：src/utils/error_messages.py:157-160 streamlit 格式化。"""
    e = UserFriendlyError(what="W", why="Y", impact="I", actions=["a1"], severity="warning")
    out = format_error_for_streamlit(e)
    assert isinstance(out, str)


# ── 健壮性：空串/特殊字符不抛异常 ──

def test_empty_and_special_chars_no_throw():
    """口径来源：模板函数对空串/特殊字符容错（:44-160 全部 f-string 拼接，无校验抛错路径）。"""
    for fn, args in [
        (em.table_generation_failed, ("", "", "")),
        (em.llm_unavailable, ("",)),
        (em.cfa_sem_not_converged, ("", None)),
        (em.export_missing_dependency, ("",)),
    ]:
        e = fn(*args)
        assert isinstance(e, UserFriendlyError)
    weird = '引号"引号 emoji😀 <script>'
    e = UserFriendlyError(what=weird, why=weird, impact=weird, actions=[weird])
    md = e.to_markdown()
    assert weird in md
