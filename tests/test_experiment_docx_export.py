"""实验程序文档 Word 导出测试。"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from docx import Document

from src.output.docx_exporter import build_experiment_protocol_docx


@pytest.fixture
def basic_design():
    """模拟 ExperimentDesign 数据类的轻量 namespace。"""
    return SimpleNamespace(
        title="情绪诱发对工作记忆的影响实验",
        target_population="大学生（18-25 岁）",
        design_type="between_subjects",
        design_type_zh="2×2 被试间因素设计",
        independent_vars=[
            {"name": "情绪诱发", "levels": ["积极", "消极"]},
            {"name": "任务难度", "levels": ["低", "高"]},
        ],
        dependent_vars=[{"name": "正确率"}, {"name": "反应时"}],
        control_vars=["年龄", "性别"],
        n_subjects=120,
        n_per_group=30,
        n_groups=4,
        inclusion_criteria=["右利手", "视力正常或矫正后正常"],
        exclusion_criteria=["有精神疾病史", "近期服用影响认知的药物"],
        ethics="本研究已获学校伦理委员会批准（编号 IRB-2026-001）。",
        materials=[
            {"name": "情绪图片库", "description": "选自 IAPS 标准图片"},
            {"name": "工作记忆任务", "description": "n-back 任务"},
        ],
        apparatus=["DELL 24 寸显示器", "标准 USB 键盘"],
        procedure="1. 知情同意；2. 情绪诱发；3. n-back 任务；4. 后测；5. 致谢。",
        analysis_plan="2×2 ANOVA 分析正确率与反应时",
        analysis_plan_detailed="使用 Python pingouin 包进行 2×2 被试间 ANOVA，"
                              "报告主效应、交互效应及偏 η²。",
        hypotheses=[
            "情绪诱发显著影响工作记忆",
            "任务难度调节情绪效应",
        ],
        research_questions=["情绪状态如何影响工作记忆容量？"],
        notes="预实验已招募 20 人验证流程。",
    )


def _doc_text(docx_bytes: bytes) -> str:
    doc = Document(io.BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def test_docx_returns_valid_bytes(basic_design):
    """生成的 .docx 应为有效字节流（zip 格式，PK 头）。"""
    docx_bytes = build_experiment_protocol_docx(basic_design)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 5000
    assert docx_bytes[:2] == b"PK"


def test_docx_contains_all_six_sections(basic_design):
    """六大节都应出现在文档中。"""
    docx_bytes = build_experiment_protocol_docx(basic_design)
    text = _doc_text(docx_bytes)
    for section in [
        "一、实验设计概述",
        "二、被试招募",
        "三、实验材料",
        "四、实验流程",
        "五、数据记录字段",
        "六、注意事项",
    ]:
        assert section in text, f"缺少节：{section}"


def test_docx_includes_design_data(basic_design):
    """设计的核心数据（标题、被试数、变量）应出现在文档。"""
    docx_bytes = build_experiment_protocol_docx(
        basic_design, researcher="李四", date="2026 年 5 月 17 日"
    )
    text = _doc_text(docx_bytes)
    assert basic_design.title in text
    assert "李四" in text
    assert "2026" in text
    assert "120" in text  # 被试数
    assert "大学生" in text  # 目标群体
    # 自变量、因变量
    assert "情绪诱发" in text or "工作记忆" in text


def test_docx_handles_minimal_design():
    """字段缺失/空时应优雅降级，不崩溃。"""
    minimal = SimpleNamespace(
        title="最小测试实验",
        target_population="",
        design_type="",
        independent_vars=[],
        dependent_vars=[],
        n_subjects=0,
    )
    docx_bytes = build_experiment_protocol_docx(minimal)
    text = _doc_text(docx_bytes)
    assert "最小测试实验" in text
    # 缺失的字段应有占位
    assert "待补充" in text or "未指定" in text or "（待指定）" in text


def test_docx_lists_inclusion_exclusion_criteria(basic_design):
    """纳入和排除标准应明确列出。"""
    docx_bytes = build_experiment_protocol_docx(basic_design)
    text = _doc_text(docx_bytes)
    assert "右利手" in text
    assert "精神疾病" in text


def test_docx_includes_ethics_section(basic_design):
    """伦理说明应在六中渲染。"""
    docx_bytes = build_experiment_protocol_docx(basic_design)
    text = _doc_text(docx_bytes)
    assert "伦理" in text
    assert "IRB" in text or "已获" in text


# --------------------------------------------------------------------------- #
# v2.9: 待补充事项清单
# --------------------------------------------------------------------------- #

def test_minimal_design_triggers_placeholder_checklist():
    """v2.9: 极简设计（缺失 ≥3 字段）→ 文档末尾应含「待补充事项清单」。"""
    minimal = SimpleNamespace(
        title="极简实验",
        target_population="",
        design_type="",
        independent_vars=[],
        dependent_vars=[],
        n_subjects=0,
        inclusion_criteria=[],
        exclusion_criteria=[],
        materials=[],
        apparatus=[],
        procedure="",
        ethics="",
        analysis_plan="",
        hypotheses=[],
        research_questions=[],
    )
    docx_bytes = build_experiment_protocol_docx(minimal)
    text = _doc_text(docx_bytes)
    assert "待补充事项清单" in text
    # 至少列出几条具体字段
    assert "建议补充" in text or "应包含" in text


def test_complete_design_does_not_trigger_checklist(basic_design):
    """v2.9: 字段填得较全的设计（<3 缺项）→ 不应出现待补清单。"""
    docx_bytes = build_experiment_protocol_docx(basic_design)
    text = _doc_text(docx_bytes)
    assert "待补充事项清单" not in text


def test_count_protocol_placeholders_matches_missing_fields():
    from src.output.docx_exporter import count_protocol_placeholders

    full_design = SimpleNamespace(
        title="t", target_population="人",
        independent_vars=[{"name": "iv1"}],
        dependent_vars=[{"name": "dv1"}],
        inclusion_criteria=["a", "b"],
        exclusion_criteria=["c"],
        materials=["m"], apparatus=["a"],
        procedure="step1", ethics="ok",
        analysis_plan="ANOVA",
        hypotheses=["H1"], research_questions=["RQ1"],
    )
    minimal = SimpleNamespace(
        title="t", target_population="",
        independent_vars=[], dependent_vars=[],
        inclusion_criteria=[], exclusion_criteria=[],
        materials=[], apparatus=[], procedure="", ethics="",
        analysis_plan="", hypotheses=[], research_questions=[],
    )
    assert count_protocol_placeholders(full_design) == 0
    assert count_protocol_placeholders(minimal) == 11  # 全部 11 个字段都缺
