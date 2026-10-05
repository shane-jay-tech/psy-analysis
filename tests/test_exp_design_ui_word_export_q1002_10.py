# -*- coding: utf-8 -*-
"""s1002-10：experiment_design_ui 详情页/Word 导出分支补面（s922-133 遗留 3 的增量面）。

与兄弟件 test_experiment_design_ui_detail_branch.py（s923-40，17 例）的分工：
- 兄弟件已钉：详情页 det1-det5 渲染面、Word 导出区静态面、生成失败可见性、
  `is` 护栏、缺省文件名分支；真实设计点「生成」以 xfail(strict=True) 登记
  （「静默失明的绿」：SimpleNamespace 夹具面前绿、真实对象前死）。
- **本件增量（s1002-10 时点实况）**：s930-06 已修 ethics 消费点（:815 isinstance 分支），
  但 **notes 消费点 :851 仍直喂 List** ⇒ 真设计导出仍 TypeError（本件直探实测）。
  兄弟件那条 xfail 的「修好即 XPASS」报警到现在还没响——本件把「哪一半修了」钉成
  **分半断言**，notes 修复落地时本件先行转红提醒把兄弟件 xfail 翻正：
  ① ethics 侧：真设计的伦理段已能走通（s930-06 修复面回归钉，防回退）；
  ② notes 侧：xfail(strict=True) 配平登记（与兄弟件同型、点名单独立——notes 修复
    会同时 XPASS 两条，双保险提醒同步翻 :617 的正向断言）。
- 产物级断言（完成标准 3）：SimpleNamespace 最小桩直调 build_experiment_protocol_docx
  ⇒ bytes/PK 魔数/docx zip 成员（word/document.xml 在册）——桩级产物链，不依赖 notes 修复。

零 src 改动；零新增 st.* 宽桩（复用兄弟件 _FakeST）。
"""
from __future__ import annotations

import io
import zipfile
from types import SimpleNamespace

import pytest

from tests.test_experiment_design_ui_detail_branch import (  # 兄弟件手桩复用
    DESIGN_KWARGS, STATE_KEY,
    _FakeSessionState, _FakeST,
)

WORD_BUTTON_LABEL = "📄 生成实验程序文档"
ARTIFACT_KEY = "_exp_protocol_docx"
NOTES_XFAIL_REASON = (
    "s1002-10 配平登记：docx_exporter.py:851 仍把 notes（ExperimentDesign 里是 List[str]，"
    "design_engine.py:66 同源）直喂 _add_paragraph_with_inline_format ⇒ TypeError。"
    "ethics 侧已由 s930-06 修好（:815 isinstance 分支）。修好 notes 后本例 XPASS 当场报警，"
    "届时同步翻兄弟件 test_real_design_can_actually_be_exported_to_docx 与 "
    "test_download_button_hidden_until_artifact_exists 两处前提。"
)


@pytest.fixture(scope="module")
def real_design():
    from src.experiment_design import ExperimentDesignEngine

    eng = ExperimentDesignEngine()
    return eng.design_experiment(**DESIGN_KWARGS)


# ---------- ① ethics 侧修复面回归钉（s930-06 已修，防回退） ----------

def test_ethics_side_survives_real_list_but_notes_still_kills(real_design):
    """分半断言：ethics 过了、notes 仍炸 ⇒ 异常行号必须落在 notes 消费点之后。"""
    import sys
    import traceback
    from src.output.docx_exporter import build_experiment_protocol_docx

    try:
        build_experiment_protocol_docx(real_design)
        raise AssertionError("真设计已能整链导出——notes 修复落地了！请把本件 ② 翻正"
                             "并同步兄弟件两处前提（见 NOTES_XFAIL_REASON）")
    except TypeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        last = tb[-2]  # 帧链：本例 → build_experiment_protocol_docx → 消费点
        # ethics 消费点（:815 区域）已不是炸点；炸点须在 notes（:851 一带）
        assert last.lineno >= 820, (
            f"炸点漂移到 ethics 侧（{last.lineno}）＝s930-06 修复回退，先查 :815 分支")
        assert "notes" in (last.line or ""), (
            f"炸点不再是 notes 直喂行（{last.lineno}: {last.line}）——形态已变，本件需复检")


# ---------- ② notes 侧 xfail 配平登记（与兄弟件同型、独立点名单） ----------

@pytest.mark.xfail(strict=True, reason=NOTES_XFAIL_REASON)
def test_real_design_exports_after_notes_fix_will_xpass(real_design):
    from src.output.docx_exporter import build_experiment_protocol_docx

    blob = build_experiment_protocol_docx(real_design)
    assert blob[:4] == b"PK\x03\x04"


# ---------- ③ 产物级断言（SimpleNamespace 最小桩直调导出器） ----------

def _minimal_design():
    return SimpleNamespace(
        title="合成实验",
        target_population="大学生",
        design_type="between_subjects",
        design_type_zh="单因素被试间",
        independent_vars=[{"name": "光照", "levels": ["亮", "暗"]}],
        dependent_vars=[{"name": "反应时"}],
        control_vars=["时段"],
        n_subjects=60,
        n_per_group=30,
        n_groups=2,
        inclusion_criteria=["视力正常"],
        exclusion_criteria=[],
        ethics=["合成伦理句一。", "合成伦理句二。"],
        materials=[{"name": "合成材料", "description": "描述"}],
        apparatus=["显示器"],
        procedure="1. 知情同意；2. 实验。",
        analysis_plan="t 检验",
        analysis_plan_detailed="独立样本 t 检验（合成描述）。",
        hypotheses=["光照影响反应时"],
        research_questions=["光照如何影响反应时？"],
        # str 态：notes 修复前唯一可走全链的出口（兄弟件 SimpleNamespace 同口径）
        notes="合成注记（str 态）",
    )


def test_exporter_produces_valid_docx_bytes_and_zip_members():
    from src.output.docx_exporter import build_experiment_protocol_docx

    blob = build_experiment_protocol_docx(_minimal_design())
    assert isinstance(blob, (bytes, bytearray)) and blob[:4] == b"PK\x03\x04"
    with zipfile.ZipFile(io.BytesIO(bytes(blob))) as zf:
        names = zf.namelist()
        assert "word/document.xml" in names, f"docx 成员异常：{names[:6]}"
        body = zf.read("word/document.xml").decode("utf-8")
        assert "合成实验" in body and "合成伦理句一。" in body


# ---------- ④ UI 侧：design 置 None 变异刀（默认路径 vs 详情页路径） ----------

def _render(monkeypatch, design, pressed=()):
    from src.ui import experiment_design_ui

    real_engine_cls = experiment_design_ui.ExperimentDesignEngine

    class _Engine(real_engine_cls):
        def __init__(self):
            super().__init__()
            self.design = design

    fake_st = _FakeST(session_state=_FakeSessionState({STATE_KEY: None}), pressed=pressed)
    monkeypatch.setattr(experiment_design_ui, "st", fake_st)
    monkeypatch.setattr(experiment_design_ui, "ExperimentDesignEngine", _Engine)
    experiment_design_ui.render_experiment_design_ui()
    return fake_st


def test_design_none_mutation_hides_word_export_region(monkeypatch, real_design):
    """变异刀：design 置 None ⇒ 详情页/Word 导出区整个消失（默认路径），断言转红形态演示。"""
    fake_st = _render(monkeypatch, None, pressed=(WORD_BUTTON_LABEL,))
    assert fake_st.of("download_button") == []
    assert ARTIFACT_KEY not in fake_st.session_state
    # 详情页 det 区（design 非空才有）：材料标题不该出现在任何 tab 体内
    assert not any("实验材料" in str(b) for b in
                   [w.args[0] for w in fake_st.widgets if w.api == "markdown"]), (
        "design=None 却渲染了详情内容——变异无效，本件对分支无判别力")


def test_notes_list_form_raises_typeerror_until_fixed():
    """notes=List 态负例钉（:851 直喂）：修复落地时本例转红＝提醒同步翻 xfail 两条。"""
    import sys
    import traceback
    from src.output.docx_exporter import build_experiment_protocol_docx

    d = _minimal_design()
    d.notes = ["合成注记"]  # List 态
    try:
        build_experiment_protocol_docx(d)
        raise AssertionError("notes List 态已能导出＝:851 修复落地！请翻正本件 ② xfail"
                             "与兄弟件 test_real_design_can_actually_be_exported_to_docx")
    except TypeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        last = tb[-2]
        assert "notes" in (last.line or ""), (
            f"炸点漂移（{last.lineno}: {last.line}）——形态已变，本件需复检")
