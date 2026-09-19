"""src/ui/items_upload_panel._safe_filename 钉桩（s918-45 起，s919-11 加固后翻正）。

只 import 这一个纯函数；除"控制字符剔除后真写一次文件"那条外**不落任何文件**，
且那一条写死在 `tmp_path` 下，绝不碰仓库目录。
锚点：src/ui/items_upload_panel.py:375 `_safe_filename`（模块现 631 行；此前仅出现在导出门禁白名单清单里）。
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
    # s919-11 加固：全空白也走兜底（改前 `title or "questionnaire"` 判的是"非空串"，
    # strip 之后才变空 ⇒ 产出 ".docx" 这种 Windows 坏名字）
    assert _safe_filename("   ", "docx") == "questionnaire.docx"
    assert _safe_filename("\t\n ", "docx") == "questionnaire.docx"


def test_edges_are_stripped_but_inner_spaces_kept():
    assert _safe_filename("  空格 标题  ", "md") == "空格 标题.md"


def test_long_titles_are_truncated_at_the_declared_cap():
    """s919-11 加固：超长按 `_SAFE_NAME_MAX` 截断（改前 200 字标题原样进文件名，撞 MAX_PATH）。
    截断值从模块常量读，不写死数字——上限改动只需改生产码，本用例自动跟随。"""
    from src.ui.items_upload_panel import _SAFE_NAME_MAX

    got = _safe_filename("标" * 200, "docx")

    assert len(got) == _SAFE_NAME_MAX + len(".docx")
    assert got == "标" * _SAFE_NAME_MAX + ".docx"
    assert not got[:-len(".docx")].endswith((".", " "))     # 不留尾点/尾空格


def test_extension_is_not_sanitized_at_all():
    """【现状·未修】清洗只作用于 title，`ext` 原样拼接
    ⇒ 传入含分隔符的 ext 时结果里**仍有斜杠**，清洗保证被绕过。
    两个调用点只传字面量 "docx"/"pdf"，故 s919-11 没顺手改（生产码 docstring 已写明这是接口约束）。"""
    assert _safe_filename("t", "../exe") == "t.../exe"
    assert _safe_filename("t", "a/b") == "t.a/b"
    assert _safe_filename("t", "") == "t."      # 空 ext 产出尾点，Windows 上是坏名字


@pytest.mark.parametrize("name", ["con", "NUL", "aux", "com1", "lpt9"])
def test_windows_reserved_device_names_get_a_suffix(name):
    """s919-11 加固（改前 `con`/`NUL` 原样输出，写盘会失败或写到设备）：
    保留名判定**不分大小写**，且按 `.` 前的首段判——Windows 连 `con.txt` 也拒收。"""
    got = _safe_filename(name, "docx")

    assert got.split(".")[0].lower() not in {"con", "prn", "aux", "nul", "com1", "lpt9"}
    assert got == f"{name}_.docx"


def test_reserved_check_does_not_touch_ordinary_names():
    """别把"正常包含 con 的词"误伤成保留名。"""
    assert _safe_filename("configuration", "docx") == "configuration.docx"
    assert _safe_filename("nulled", "docx") == "nulled.docx"


def test_dots_and_parent_references_are_harmless_only_because_the_slash_is_replaced():
    """`..` 本身不在清洗表内；安全靠的是 `/` 与 `\\` 被换掉这一事实。"""
    assert _safe_filename("..", "docx") == "...docx"
    assert _safe_filename("../etc/passwd", "txt") == ".._etc_passwd.txt"


def test_other_control_characters_are_dropped_and_the_name_is_openable(tmp_path):
    """s919-11 加固（改前 NUL 原样保留，`open()` 直接 ValueError——旧用例就是钉那句抛错）。
    现在剔除其余控制字符（< 0x20），并**真在 tmp_path 下写一次**证明名字可用；
    写盘限定在 tmp_path，不碰仓库目录。"""
    got = _safe_filename("a\x00b", "md")

    assert got == "ab.md"
    target = tmp_path / got
    target.write_text("ok", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "ok"

    assert _safe_filename("混\x00\x01\x1f合", "md") == "混合.md"
