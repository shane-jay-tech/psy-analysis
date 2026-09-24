"""src/visualization/fonts.py ＋ src/output/docx_styles.py 契约测试（s918-31）。

字体侧只测回退链与缓存（monkeypatch 文件系统可见性，不碰真实 Windows\\Fonts）；
样式侧钉常量现值。任务书提到的「matplotlib 缓存」与磁盘不符——本模块不 import matplotlib，
缓存是模块级 `_FONT_FAMILY`，按现状测。
"""
import io
import os
import re
import zipfile
from types import SimpleNamespace

import pytest
from docx import Document
from docx.oxml.ns import qn

from src.output import docx_exporter
from src.output import docx_styles as ds
from src.visualization import fonts as fnt

ALL_CANDIDATES = [
    "msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc",
    "simkai.ttf", "msjh.ttc", "Deng.ttf", "Dengb.ttf",
]


@pytest.fixture(autouse=True)
def reset_font_cache(monkeypatch):
    monkeypatch.setattr(fnt, "_FONT_FAMILY", None)


def _fake_fs(monkeypatch, tmp_path, existing=(), glob_hits=()):
    """把 WINDIR 指到 tmp，并只让 `existing` 里的文件名「存在」。"""
    monkeypatch.setenv("WINDIR", str(tmp_path))
    real_exists = os.path.exists

    def exists(path):
        name = os.path.basename(str(path))
        return name in existing and real_exists(str(tmp_path))

    monkeypatch.setattr(fnt.os.path, "exists", exists)
    monkeypatch.setattr(fnt, "glob", SimpleNamespace(glob=lambda pattern: [str(tmp_path / "Fonts" / h) for h in glob_hits]))
    return tmp_path / "Fonts"


def test_priority_order_prefers_yahei_over_simhei(monkeypatch, tmp_path):
    root = _fake_fs(monkeypatch, tmp_path, existing={"msyh.ttc", "simhei.ttf"})

    assert fnt.find_chinese_font() == os.path.join(str(root), "msyh.ttc")


def test_falls_to_next_candidate_when_yahei_absent(monkeypatch, tmp_path):
    root = _fake_fs(monkeypatch, tmp_path, existing={"simhei.ttf", "simsun.ttc"})

    assert fnt.find_chinese_font() == os.path.join(str(root), "simhei.ttf")


def test_every_candidate_is_tried_in_declared_order(monkeypatch, tmp_path):
    _fake_fs(monkeypatch, tmp_path, existing=set())
    seen = []
    monkeypatch.setattr(fnt.os.path, "exists", lambda p: seen.append(os.path.basename(str(p))) or False)

    assert fnt.find_chinese_font() is None
    assert seen[: len(ALL_CANDIDATES)] == ALL_CANDIDATES


def test_wildcard_search_is_the_last_resort(monkeypatch, tmp_path):
    root = _fake_fs(monkeypatch, tmp_path, existing=set(), glob_hits=["msyh.ttc"])

    assert fnt.find_chinese_font() == os.path.join(str(root), "msyh.ttc")


def test_returns_none_when_nothing_found(monkeypatch, tmp_path):
    """旧名后缀「though_annotated_str」记的是注解与实现不符；s919-07 已把注解改成 Optional[str]，后缀失去意义。"""
    _fake_fs(monkeypatch, tmp_path, existing=set(), glob_hits=[])

    assert fnt.find_chinese_font() is None
    assert fnt.get_font_family() == "sans-serif"


@pytest.mark.parametrize(
    "filename,family",
    [
        ("msyh.ttc", "Microsoft YaHei"),
        ("msyhbd.ttc", "Microsoft YaHei"),
        ("simhei.ttf", "SimHei"),
        ("simsun.ttc", "SimSun"),
        ("simkai.ttf", "KaiTi"),
        ("Deng.ttf", "DengXian"),                  # s919-07 翻正（原钉 sans-serif＝方框现状）
        ("Dengb.ttf", "DengXian"),                 # 等线粗体同名族
        ("msjh.ttc", "Microsoft JhengHei"),        # s919-07 翻正（微软正黑体）
    ],
)
def test_family_name_mapping_covers_six_families(monkeypatch, tmp_path, filename, family):
    """族名字符串取自本机 Fonts 目录的 name 表 ID=1（fontTools 实测），不是猜的别名。"""
    root = _fake_fs(monkeypatch, tmp_path, existing={filename})

    assert fnt.get_font_family() == family


def test_only_unknown_font_falls_back_to_sans_serif(monkeypatch, tmp_path):
    """六个族名之外的字体仍须落回 sans-serif（翻正不能顺手放宽兜底）。"""
    _fake_fs(monkeypatch, tmp_path, existing={"arial.ttf"})

    assert fnt.get_font_family() == "sans-serif"


def test_find_chinese_font_annotation_is_optional():
    """`find_chinese_font()` 一直可能返回 None，注解 s919-07 起改为 Optional[str]。

    钉注解而非行为（行为由 `test_returns_none_when_nothing_found` 覆盖）：
    注解与实现不符会让调用方按 str 做字符串拼接而静默炸。
    """
    import typing

    ret = typing.get_type_hints(fnt.find_chinese_font)["return"]
    args = typing.get_args(ret)
    assert type(None) in args, f"返回注解应允许 None，实得 {ret}"


def test_chinese_font_name_is_cached_after_first_call(monkeypatch, tmp_path):
    _fake_fs(monkeypatch, tmp_path, existing={"simhei.ttf"})
    calls = []
    monkeypatch.setattr(fnt, "get_font_family", lambda: (calls.append(1), "SimHei")[1])

    assert fnt.get_chinese_font() == "SimHei"
    assert fnt.get_chinese_font() == "SimHei"
    assert len(calls) == 1


def test_family_mapping_lowercases_the_discovered_path(monkeypatch, tmp_path):
    """glob 可带回大写文件名（Windows 实际会），族名判定走 .lower()。"""
    _fake_fs(monkeypatch, tmp_path, existing=set(), glob_hits=["MSYH.TTC"])

    assert fnt.get_font_family() == "Microsoft YaHei"


def test_docx_latin_and_cjk_font_constants_pinned():
    assert ds.FONT_BODY_LATIN == "Times New Roman"
    assert ds.FONT_BODY_CJK == "宋体"
    assert ds.FONT_HEADING_LATIN == "Times New Roman"
    assert ds.FONT_HEADING_CJK == "黑体"


def test_docx_size_and_spacing_constants_pinned():
    assert (ds.SIZE_TITLE, ds.SIZE_H1, ds.SIZE_H2, ds.SIZE_H3) == (16, 14, 13, 12)
    assert (ds.SIZE_BODY, ds.SIZE_CAPTION, ds.SIZE_TABLE) == (12, 10.5, 10.5)
    assert ds.LINE_SPACING == 1.5
    # s924-24：原为一条三元组断言，拆成三条独立断言以便单点定位（s923-18 三案共同前置）。
    # 期望值零变化，仍是 12 / 6 / 0。
    assert ds.SPACE_BEFORE_HEADING_PT == 12, (
        f"标题段前距常量现值漂移：期望 12，实得 {ds.SPACE_BEFORE_HEADING_PT}"
    )
    assert ds.SPACE_AFTER_HEADING_PT == 6, (
        f"标题段后距常量现值漂移：期望 6，实得 {ds.SPACE_AFTER_HEADING_PT}"
    )
    assert ds.SPACE_AFTER_BODY_PT == 0, (
        f"正文段后距常量现值漂移：期望 0，实得 {ds.SPACE_AFTER_BODY_PT}"
    )
    assert ds.FIRST_LINE_INDENT_CM == 0.74


def test_docx_apa7_margins_and_table_style_pinned():
    assert (ds.MARGIN_TOP_CM, ds.MARGIN_BOTTOM_CM) == (2.54, 2.54)
    assert (ds.MARGIN_LEFT_CM, ds.MARGIN_RIGHT_CM) == (3.18, 3.18)
    assert ds.TABLE_HEADER_FILL == "DDDDDD"
    assert ds.TABLE_BORDER_COLOR == "000000"
    assert ds.TABLE_BORDER_SIZE == 4
    assert (ds.FIG_PREFIX, ds.TABLE_PREFIX) == ("图", "表")
