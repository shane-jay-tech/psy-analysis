"""src/ui/items_upload_panel._safe_filename 钉桩（s918-45）。

只 import 这一个纯函数；**不落任何文件**（断言只看返回字符串）。
锚点：src/ui/items_upload_panel.py:366（模块 610 行，此前仅出现在导出门禁白名单清单里）。
"""
import pytest

from src.ui.items_upload_panel import _safe_filename

ILLEGAL = ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']


@pytest.mark.parametrize("ch", ILLEGAL)
def test_each_illegal_character_becomes_an_underscore(ch):
    assert _safe_filename(f"a{ch}b", "md") == "a_b.md"


def test_a_whole_dirty_title_needs_no_illegal_char_to_survive():
    got = _safe_filename(r'报告: "全年" 版 <v2|final>*?/tmp\x00', "md")

    assert set(got) & set(ILLEGAL) == set()
    assert got.startswith("报告_") and got.endswith("_md.md".replace("_md", "md")) is False
    assert got.endswith(".md")


def test_blank_or_none_title_falls_back_to_questionnaire():
    assert _safe_filename("", "docx") == "questionnaire.docx"
    assert _safe_filename(None, "docx") == "questionnaire.docx"
    # 【现状缺陷】全空白**不走兜底**：`title or ...` 判的是"非空串"，strip 之后才变空
    assert _safe_filename("   ", "docx") == ".docx"


def test_edges_are_stripped_but_inner_spaces_kept():
    assert _safe_filename("  空格 标题  ", "md") == "空格 标题.md"


def test_long_titles_are_not_truncated_at_all():
    """【现状缺陷】无长度上限：200 字标题原样进文件名 ⇒ Windows 下极易撞 MAX_PATH。"""
    got = _safe_filename("标" * 200, "docx")

    assert len(got) == 205                       # 200 + "." + 4，函数不截
    assert got.startswith("标" * 200)


def test_extension_is_not_sanitized_at_all():
    """【现状缺陷】清洗只作用于 title，`ext` 原样拼接
    ⇒ 传入含分隔符的 ext 时结果里**仍有斜杠**，清洗保证被绕过。"""
    assert _safe_filename("t", "../exe") == "t.../exe"
    assert _safe_filename("t", "a/b") == "t.a/b"
    assert _safe_filename("t", "") == "t."      # 空 ext 产出尾点，Windows 上是坏名字


def test_windows_reserved_device_names_are_not_rejected():
    """【现状缺陷】con/prn/nul/com1 等保留名照原样输出，写盘时会失败或写到设备。"""
    assert _safe_filename("con", "docx") == "con.docx"
    assert _safe_filename("NUL", "md") == "NUL.md"


def test_dots_and_parent_references_are_harmless_only_because_the_slash_is_replaced():
    """`..` 本身不在清洗表内；安全靠的是 `/` 与 `\\` 被换掉这一事实。"""
    assert _safe_filename("..", "docx") == "...docx"
    assert _safe_filename("../etc/passwd", "txt") == ".._etc_passwd.txt"


def test_control_characters_other_than_newline_tab_are_left_in(tmp_path):
    """【现状缺陷】清洗表只列 \\n \\r \\t；NUL 等控制字符原样保留（真拿去 open() 会 ValueError）。"""
    got = _safe_filename("a\x00b", "md")

    assert got == "a\x00b.md"
    with pytest.raises(ValueError):
        open(got, "w")                           # 证明这不是纯观感问题
