# -*- coding: utf-8 -*-
"""src/questionnaire/exporters.py 的 DOCX 主路径 + PDF 降级钉桩（s922-13）。

锚点（2026-09-22 复核，行号零漂移）：`export_to_docx` 在 :13、`export_to_pdf` 在 :259，
`_set_east_asian_font` 在 :238。补测前 tests/ 对 `export_to_docx` / `export_to_pdf` **符号级 0 命中**
（`tests/test_questionnaire_export.py` 只 import 了同文件的 `build_questionnaire_pdf`，:110-167 共 7 处），
两个主导出函数此前完全没有测试。

依赖实况（本机 .venv 实测，本单**未装任何依赖**）：python-docx 1.2.0 / fpdf / openpyxl / lxml 均在，
`C:\\Windows\\Fonts` 有中文字体 ⇒ `export_to_pdf` 的正常分支在这台机器上真能跑通，
所以它的**降级分支只能用 monkeypatch 模拟**（任务书「不装依赖」+「只读钉桩」两条一起满足）。

红线自约：design dict 全部是「合成构念/合成题干」这种一眼假的人造内容，不含任何真实被试数据、
不含任何统计数值结论；样本量/效应量相关的字面量一个都没写进 design。
"""
from __future__ import annotations

import io
import sys
import time
import zipfile

import pytest
from docx import Document
from docx.oxml.ns import qn

from src.questionnaire.exporters import _set_east_asian_font, export_to_docx, export_to_pdf

# 只有「被 design[...] 直接取用」的键才算必填（.get 的一律可选，见 test_definition_precedence_*）
_REQUIRED_KEYS = (
    "construct_name", "research_question", "template_used", "scale_config", "match_reason",
    "dimensions_used", "instructions", "items", "scoring", "psychometrics",
)


def minimal_design(**overrides) -> dict:
    """能走通 export_to_docx 主干的最小 dict（纯人造文案，2 题 1 维度含 1 反向题）。"""
    design = {
        "construct_name": "合成构念",
        "research_question": "合成研究问题？",
        "template_used": {"name": "合成题型"},
        "scale_config": {
            "points": 5, "n_items": 2, "n_dimensions": 1, "n_reverse": 1, "reverse_ratio": "50%",
            "anchors": ["完全不同意", "完全同意"],
        },
        "match_reason": "合成匹配理由",
        "dimensions_used": [{"name": "维度甲", "desc": "合成描述", "item_count": 2, "example": "合成示例"}],
        "instructions": "合成指导语",
        "items": [
            {"dimension": "维度甲", "reverse": False, "index": 1, "text": "合成题干一"},
            {"dimension": "维度甲", "reverse": True, "index": 2, "text": "合成题干二"},
        ],
        "scoring": "合成计分方式",
        "psychometrics": {"信度": "合成信度策略\n第二条", "效度": "合成效度策略"},
    }
    design.update(overrides)
    return design


def paragraphs_of(blob: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(blob)).paragraphs]


# ═════════════════ 一、export_to_docx 主干 ═════════════════
def test_minimal_design_exports_nonempty_bytes_that_is_a_docx_zip_with_document_xml():
    """任务的正题：非空 bytes + zip 容器里真有 word/document.xml（不是裸文本、不是空壳）。"""
    blob = export_to_docx(minimal_design())

    assert isinstance(blob, bytes) and len(blob) > 0
    assert blob[:2] == b"PK"                                     # OOXML = zip
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        assert "word/document.xml" in zf.namelist()
        assert zf.read("word/document.xml").startswith(b"<?xml")
        assert len(zf.namelist()) > 1                            # 不是只塞了一个文件
    assert len(paragraphs_of(blob)) > 0                          # 真能被 python-docx 再读回来


def _zip_member_table(blob: bytes) -> dict[str, tuple[tuple, bytes]]:
    """把 docx 容器拆成 {成员名: (zip 条目 date_time, 成员字节)}。

    `date_time` 是 zip **容器**字段（由 `time.localtime()` 落，非产物内容），
    读回时按 DOS 格式只有 **2 秒**粒度 ⇒ 它是"整包字节不确定"的唯一来源。
    """
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        return {info.filename: (info.date_time, zf.read(info.filename)) for info in zf.infolist()}


def _same_stamp_pair(design: dict) -> tuple[bytes, bytes, bool]:
    """取一对**容器时间戳相同**的产物，用于保住"整包字节全等"这条原口径。

    连调两次之间的构建耗时约几十毫秒，撞上 2 秒粒度边界的概率极低；
    重试 5 次仍取不到同戳配对就**显式失败**，不用 `assert True` 假装子断言跑过。
    """
    last: tuple[bytes, bytes] | None = None
    for _ in range(5):
        a, b = export_to_docx(design), export_to_docx(design)
        ta = {k: v[0] for k, v in _zip_member_table(a).items()}
        tb = {k: v[0] for k, v in _zip_member_table(b).items()}
        if ta == tb:
            return a, b, True
        last = (a, b)
    assert last is not None
    return last[0], last[1], False


def test_docx_output_is_byte_deterministic_for_the_same_design():
    """同一份 design 两次调用 ⇒ **XML 成员**逐字节相等；整包字节只在容器时间戳相同时才等。

    s923-20 改造（原口径来自 s922-13，被 s922-22 实测否证）：原先只写
    `assert export_to_docx(design) == export_to_docx(design)`，而 zip 条目的 `date_time`
    取当前时刻 ⇒ **跨秒整包必变**，该断言只在"两次调用落进同一个 2 秒槽"时成立，
    是一枚负载/时钟相关的偶发红（本机实测：`sleep(1.1)` 后 `bytes equal? False`，
    而 17 个成员的**内容**全部 `content_eq=True`）。
    ⇒ 拆成两层，两层都可复跑：
      ① **主断言**：强制 `time.sleep(1.1)` 跨秒后，比 `word/document.xml` 与
         `word/styles.xml` 逐字节相等（剔掉 zip 容器时间戳），并加严到"全成员内容相等"；
      ② **同秒子断言**（原字节口径保留）：另取一对容器时间戳相同的产物，断言整包字节全等
         —— 这才是"产物里没有落时间戳/随机名"的真正强口径。
    ③ **鉴别力自证**：换一个 design 再产一次，断言 `word/document.xml` **不相等**；
      若这条红了，说明成员比对失明（产物根本不随输入变），①②就成了恒真假绿。
    """
    design = minimal_design()

    # ── ② 同秒子断言：原"整包字节全等"口径，显式限定在容器时间戳相同的配对上 ──
    same_a, same_b, stamp_pair_found = _same_stamp_pair(design)
    assert stamp_pair_found, (
        "重试 5 次仍取不到容器时间戳相同的两次构建 —— 子断言本轮无法执行，"
        "宁可红也不要静默放过"
    )
    assert same_a == same_b, (
        "容器时间戳相同却整包不等 ⇒ 产物里混进了时间戳以外的非确定源"
        "（随机部件名 / dict 序 / 环境读数），原口径的『可拿去做回归比对』不成立"
    )

    # ── ① 主断言：强制跨秒，比 XML 成员（剔容器时间戳）──
    time.sleep(1.1)                                     # 跨秒：让整包字节断言必然不可依赖
    first = export_to_docx(design)
    time.sleep(1.1)                                     # 再跨一次，两次构建分处不同时刻
    second = export_to_docx(design)

    table_a, table_b = _zip_member_table(first), _zip_member_table(second)
    assert table_a.keys() == table_b.keys(), "两次构建的部件清单不一致"

    key_members = ("word/document.xml", "word/styles.xml")
    for name in key_members:
        assert name in table_a, f"容器缺成员 {name}（口径失效，不是绿）"
        assert table_a[name][1] == table_b[name][1], (
            f"{name} 跨秒后内容漂移：字节 {len(table_a[name][1])} vs {len(table_b[name][1])}，"
            f"date_time {table_a[name][0]} vs {table_b[name][0]}"
        )

    # 加严：全成员内容面确定（只有容器 date_time 允许不同）
    assert {k: v[1] for k, v in table_a.items()} == {k: v[1] for k, v in table_b.items()}, (
        "存在 document/styles 之外的成员跨秒漂移 ⇒ 需定位是哪个部件读了时钟"
    )

    # ── ③ 鉴别力自证：成员比对对"内容漂移"必须有反应 ──
    perturbed = _zip_member_table(export_to_docx(minimal_design(construct_name="另一合成构念")))
    assert perturbed["word/document.xml"][1] != table_a["word/document.xml"][1], (
        "换 design 而 document.xml 不变 ⇒ 成员比对失明，本用例的确定性断言全是恒真"
    )


def test_docx_body_carries_the_construct_dimensions_items_and_reverse_marks():
    """主干内容闭合：构念名、维度标题、题号题干、反向题标记、反向题清单都真进了正文。"""
    texts = paragraphs_of(export_to_docx(minimal_design()))
    joined = "\n".join(texts)

    assert any("—— 合成构念问卷" in t for t in texts)             # 封面副标题
    assert "维度 1：维度甲" in texts and "▎ 维度甲" in texts        # 维度结构 + 题目分组
    assert "Q1. 合成题干一" in texts
    assert "Q2. 合成题干二 【反向计分】" in texts                  # reverse=True 的标记
    assert "需反向计分的题目：Q2" in joined                        # 计分方式段的反向清单
    assert "合成研究问题？" in joined and "合成指导语" in joined and "合成计分方式" in joined
    assert "合成信度策略" in texts and "第二条" in texts            # psychometrics 按 \n 拆行
    assert "完全不同意" in texts and "完全同意" in texts            # scale_config.anchors 走 List Bullet


def test_docx_params_table_is_the_seven_row_two_column_grid():
    """技术参数表是正文里唯一的表：7 行 2 列，表头加粗，逐行取 template_used / scale_config。"""
    doc = Document(io.BytesIO(export_to_docx(minimal_design())))

    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert (len(table.rows), len(table.columns)) == (7, 2)
    cells = [[c.text for c in row.cells] for row in table.rows]
    assert cells[0] == ["参数", "设置"]
    assert cells[1] == ["题型", "合成题型"]
    assert [row[0] for row in cells] == ["参数", "题型", "量表点数", "总题量", "维度数", "反向题数", "预计用时"]
    assert cells[2][1] == "5 点 Likert" and cells[5][1] == "1 题（50%）"
    assert all(run.bold for c in table.rows[0].cells for p in c.paragraphs for run in p.runs)   # 表头加粗


@pytest.mark.parametrize("missing", _REQUIRED_KEYS)
def test_minimal_design_is_actually_minimal_every_required_key_is_indexed_directly(missing: str):
    """「最小」得是真的最小：少任一把必填键 ⇒ KeyError（而不是被 .get 静默兜住后输出半截报告）。
    这条同时把「哪些键是硬依赖」钉住：新增 `.get` 化会在这里红。"""
    design = minimal_design()
    del design[missing]

    with pytest.raises(KeyError):
        export_to_docx(design)


def test_optional_keys_are_all_skippable_and_the_anchors_list_may_be_absent():
    """可选项全缺（matched_construct / llm_* / anchors / example / item_count）仍要出稿，不许抛。"""
    design = minimal_design()
    del design["scale_config"]["anchors"]
    design["dimensions_used"][0].pop("example")
    design["dimensions_used"][0].pop("item_count")

    texts = paragraphs_of(export_to_docx(design))
    assert "题目数：- 题" in texts                                # dim.get('item_count', '-') 的缺省值
    assert not any("示例：" in t for t in texts)
    assert "Q1. 合成题干一" in texts


def test_definition_precedence_matched_construct_then_llm_then_fallback():
    """构念定义三级回退（:93-98）：matched_construct.definition > llm_definition > 兜底句。"""
    # ① 两者都有 ⇒ 取 matched_construct
    both = paragraphs_of(export_to_docx(minimal_design(
        matched_construct={"definition": "首选定义"}, llm_definition="次选定义")))
    assert "首选定义" in both and "次选定义" not in "\n".join(both)
    # ② 只有 llm ⇒ 落到次选
    only_llm = paragraphs_of(export_to_docx(minimal_design(llm_definition="次选定义")))
    assert "次选定义" in only_llm
    # ③ 都没有 ⇒ 兜底句（带构念名）
    fallback = paragraphs_of(export_to_docx(minimal_design()))
    assert "合成构念的操作性定义将基于文献综述确定。" in fallback


def test_reference_and_established_scale_sections_only_appear_when_supplied():
    """三条文献/量表分支：通用参考文献恒在，构念相关与 LLM 相关只在有数据时出现。"""
    plain = "\n".join(paragraphs_of(export_to_docx(minimal_design())))
    assert "测量学通用参考文献" in plain and "Nunnally" in plain
    assert "构念相关文献" not in plain and "LLM 生成的参考文献" not in plain
    assert "已有成熟量表参考" not in plain

    rich = "\n".join(paragraphs_of(export_to_docx(minimal_design(
        matched_construct={"references": ["构念文献甲"], "established_scales": ["成熟量表甲"]},
        llm_references=["LLM文献乙"], llm_established_scales=["LLM量表乙"]))))
    assert "构念相关文献" in rich and "1. 构念文献甲" in rich
    assert "LLM 生成的参考文献（请核实后再引用）" in rich and "1. LLM文献乙" in rich
    assert "已有成熟量表参考" in rich and "成熟量表甲" in rich and "LLM量表乙" in rich


# ═════════════════ 二、_set_east_asian_font 的成败两路（:238-251） ═════════════════
def test_set_east_asian_font_writes_the_eastasia_attribute_and_reuses_rpr():
    """成功路径：没有 rPr 就建一个，有了就复用并只改 w:eastAsia；第二次调用是覆盖不是叠套。"""
    doc = Document(io.BytesIO(export_to_docx(minimal_design())))
    style = doc.styles["Normal"]

    _set_east_asian_font(style, "黑体")
    rpr = style.element.find(qn("w:rPr"))
    assert rpr is not None and rpr.find(qn("w:rFonts")).get(qn("w:eastAsia")) == "黑体"

    _set_east_asian_font(style, "楷体")
    assert style.element.find(qn("w:rPr")) is rpr                # 同一个 rPr，没再插一个
    assert style.element.findall(qn("w:rPr")).count(rpr) == 1
    assert rpr.find(qn("w:rFonts")).get(qn("w:eastAsia")) == "楷体"


def test_set_east_asian_font_swallows_every_failure_and_returns_none():
    """回退分支钉桩：函数文档写死「不是关键功能，失败时静默回退」⇒ 任何异常都不许冒出到导出主路径。"""
    class NoElement:
        pass

    class ElementRaises:
        @property
        def element(self):
            raise RuntimeError("boom")

    for junk in (object(), NoElement(), None, "style", ElementRaises()):
        assert _set_east_asian_font(junk, "宋体") is None         # 不抛、返回 None


# ═════════════════ 三、export_to_pdf 的降级两路（:259-266，只读模拟） ═════════════════
def test_export_to_pdf_raises_named_runtime_error_when_no_cjk_font_is_found(monkeypatch):
    """无中文字体 ⇒ RuntimeError 且文案指明是字体问题；**在碰 design 之前**就抛，
    所以 UI 侧 `except Exception` 只会显示「导出失败：<字体文案>」，不会误报成数据问题。"""
    import src.visualization.fonts as fonts

    monkeypatch.setattr(fonts, "find_chinese_font", lambda: None)

    with pytest.raises(RuntimeError, match="未找到可用的中文字体文件，无法生成 PDF。"):
        export_to_pdf(minimal_design())

    # 抛在读取任何 design 键之前：空 dict 也是同一句字体错，而不是 KeyError
    with pytest.raises(RuntimeError, match="中文字体"):
        export_to_pdf({})


def test_export_to_pdf_propagates_import_error_when_the_renderer_is_missing(monkeypatch):
    """渲染器（fpdf）不在 ⇒ ImportError 直穿，交给调用方的 try 降级。零安装依赖，纯模拟。"""
    monkeypatch.setitem(sys.modules, "fpdf", None)               # sys.modules 里的 None ⇒ import 抛 ImportError

    with pytest.raises(ImportError):
        export_to_pdf(minimal_design())


def test_pdf_degradation_raises_rather_than_returning_empty_bytes(monkeypatch):
    """口径钉：降级发生在调用方，导出函数本身**只抛不回退空 bytes**。
    源码契约——`src/ui/questionnaire_panel.py:797` 的 `try` 把两个导出一起包住
    （docx :799-800 / pdf :807-808），`except Exception as e: st.error(f"❌ 导出失败：{e}")`
    在 :833-834。哪天有人把降级写进 `export_to_pdf`（返回 b""），UI 就会静默给一个空文件、
    except 分支永远走不到 —— 本例把那一步改成红的。"""
    import src.visualization.fonts as fonts

    monkeypatch.setattr(fonts, "find_chinese_font", lambda: None)

    with pytest.raises(Exception) as ei:
        export_to_pdf(minimal_design())
    assert not isinstance(ei.value, TypeError)                    # 不是签名漂移那一类错
    assert isinstance(ei.value, (RuntimeError, ImportError))
    assert "字体" in str(ei.value) or "fpdf" in str(ei.value)      # 真落在两条降级文案之一
    assert callable(fonts.find_chinese_font)                      # 接缝已由 monkeypatch 自动还原
