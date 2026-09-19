"""src/visualization/fonts.py ＋ src/output/docx_styles.py 契约测试（s918-31）。

字体侧只测回退链与缓存（monkeypatch 文件系统可见性，不碰真实 Windows\\Fonts）；
样式侧钉常量现值。任务书提到的「matplotlib 缓存」与磁盘不符——本模块不 import matplotlib，
缓存是模块级 `_FONT_FAMILY`，按现状测。
"""
import os
from types import SimpleNamespace

import pytest

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


def test_returns_none_when_nothing_found_though_annotated_str(monkeypatch, tmp_path):
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
        ("Deng.ttf", "sans-serif"),
        ("msjh.ttc", "sans-serif"),
    ],
)
def test_family_name_mapping_only_knows_four_families(monkeypatch, tmp_path, filename, family):
    root = _fake_fs(monkeypatch, tmp_path, existing={filename})

    assert fnt.get_font_family() == family


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
    assert (ds.SPACE_BEFORE_HEADING_PT, ds.SPACE_AFTER_HEADING_PT, ds.SPACE_AFTER_BODY_PT) == (12, 6, 0)
    assert ds.FIRST_LINE_INDENT_CM == 0.74


def test_docx_apa7_margins_and_table_style_pinned():
    assert (ds.MARGIN_TOP_CM, ds.MARGIN_BOTTOM_CM) == (2.54, 2.54)
    assert (ds.MARGIN_LEFT_CM, ds.MARGIN_RIGHT_CM) == (3.18, 3.18)
    assert ds.TABLE_HEADER_FILL == "DDDDDD"
    assert ds.TABLE_BORDER_COLOR == "000000"
    assert ds.TABLE_BORDER_SIZE == 4
    assert (ds.FIG_PREFIX, ds.TABLE_PREFIX) == ("图", "表")
