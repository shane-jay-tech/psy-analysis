"""UI 状态层黄金路径测试。

验证通过 session_state 和面板函数组合的真实用户路径：
导航 → 数据 → 分析 → 结果卡 → 文献审核 → 论文预览 → 导出门禁。

不启动 Streamlit 运行时，通过模拟 session_state 验证状态流转。
"""

import sqlite3

import numpy as np
import pandas as pd
import pytest

from src.analysis.result_card import build_card_from_output
from src.ui.state_keys import (
    DATA_FRAME_KEY,
    ANALYSIS_CARDS_KEY,
    PAPER_BUNDLE_KEY,
    PAPER_DIFF_SELECTION_KEY,
    PROJECT_HEALTH_ISSUES_KEY,
    EXPORT_ALLOWED_KEY,
)
from src.ui.state_store import (
    PaperDiffSelectionState,
    get_diff_selection,
    save_diff_selection,
    append_result_card,
    get_result_cards,
    set_health_check_result,
    is_export_allowed,
)
from src.ui.export_gate import collect_project_state, run_export_gate
from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.utils.project_health import run_health_checks, has_blocking_issues


@pytest.fixture
def session_state():
    """模拟 Streamlit session_state 的 dict。"""
    return {
        DATA_FRAME_KEY: None,
        "meta": None,
        ANALYSIS_CARDS_KEY: [],
        PAPER_BUNDLE_KEY: None,
        PAPER_DIFF_SELECTION_KEY: None,
        PROJECT_HEALTH_ISSUES_KEY: None,
        EXPORT_ALLOWED_KEY: True,
    }


@pytest.fixture
def sample_df():
    np.random.seed(42)
    n = 60
    return pd.DataFrame({
        "id": range(1, n + 1),
        "gender": np.random.choice(["男", "女"], n),
        "anxiety": np.random.randint(1, 6, n),
        "self_esteem": np.random.randint(1, 6, n),
    })


class TestUIGoldenPath:
    """UI 状态层黄金路径。"""

    def test_step1_data_upload_updates_state(self, session_state, sample_df):
        """用户上传数据后 session_state 更新。"""
        session_state[DATA_FRAME_KEY] = sample_df
        session_state["meta"] = {"columns": list(sample_df.columns)}
        assert session_state[DATA_FRAME_KEY] is not None
        assert len(session_state[DATA_FRAME_KEY]) == 60

    def test_step2_analysis_produces_card(self, session_state, sample_df):
        """分析运行后结果卡被追加到 session_state。"""
        session_state[DATA_FRAME_KEY] = sample_df
        output = {
            "test_type": "descriptive",
            "test_name_zh": "描述统计",
            "results": {"mean": 3.0, "std": 1.1, "n": 60, "min": 1, "max": 5,
                        "skewness": 0.1, "kurtosis": -0.3},
        }
        card = build_card_from_output(output)
        append_result_card(session_state, card)
        assert len(get_result_cards(session_state)) == 1
        assert get_result_cards(session_state)[0].method_id == "descriptive"

    def test_step3_multiple_cards_accumulate(self, session_state):
        """多次分析结果卡累积。"""
        from dataclasses import dataclass

        @dataclass
        class MockCorr:
            r: float = -0.4
            p_value: float = 0.01
            n: int = 60

        outputs = [
            {"test_type": "descriptive", "test_name_zh": "描述统计",
             "results": {"mean": 3, "std": 1, "n": 60, "min": 1, "max": 5, "skewness": 0, "kurtosis": 0}},
            {"test_type": "pearson_corr", "test_name_zh": "Pearson 相关", "result": MockCorr()},
        ]
        for o in outputs:
            card = build_card_from_output(o)
            append_result_card(session_state, card)
        assert len(get_result_cards(session_state)) == 2

    def test_step4_paper_bundle_creation(self, session_state):
        """论文 Bundle 创建后写入 session_state。"""
        bundle = PaperDraftBundle(
            title="焦虑与自尊",
            sections={
                "introduction": PaperSection(name="引言", markdown="焦虑研究...", source="template"),
                "result": PaperSection(name="结果", markdown="M=3.0", source="data"),
            },
            source="template",
        )
        session_state[PAPER_BUNDLE_KEY] = bundle
        assert session_state[PAPER_BUNDLE_KEY].title == "焦虑与自尊"

    def test_step5_diff_selection_persists(self, session_state):
        """AI 差异选择写入后刷新不丢。"""
        sel = get_diff_selection(session_state)
        sel.record_section_choice("introduction", "revised")
        sel.record_section_choice("result", "original")
        sel.record_paragraph_choice("introduction", "0", "revised")
        save_diff_selection(session_state, sel)

        # 模拟"刷新"：重新读取
        sel2 = get_diff_selection(session_state)
        assert sel2.section_choices["introduction"] == "revised"
        assert sel2.section_choices["result"] == "original"
        assert sel2.paragraph_choices["introduction"]["0"] == "revised"

    def test_step6_diff_selection_batch_accept(self, session_state):
        """批量接受 AI 后状态正确。"""
        sel = get_diff_selection(session_state)
        keys = ["introduction", "method", "result", "discussion"]
        sel.accept_all_revised(keys)
        save_diff_selection(session_state, sel)

        sel2 = get_diff_selection(session_state)
        for k in keys:
            assert sel2.section_choices[k] == "revised"

    def test_step7_unconfirmed_detection(self, session_state):
        """检测未确认的 AI 修改。"""
        sel = get_diff_selection(session_state)
        sel.record_section_choice("introduction", "revised")
        save_diff_selection(session_state, sel)

        all_keys = ["introduction", "method", "result", "discussion"]
        assert sel.has_unconfirmed(all_keys) is True
        sel.accept_all_revised(all_keys)
        assert sel.has_unconfirmed(all_keys) is False

    def test_step8_health_check_no_data_blocks(self, session_state):
        """无数据时健康检查产生 ERROR，阻止导出。"""
        session_state[DATA_FRAME_KEY] = None
        state = collect_project_state(session_state)
        issues = run_health_checks(**state)
        assert has_blocking_issues(issues)

        set_health_check_result(session_state, [
            {"level": "ERROR", "message": "无数据"}
        ])
        allowed, reasons = is_export_allowed(session_state)
        assert allowed is False
        assert "无数据" in reasons[0]

    def test_step9_health_check_passes(self, session_state, sample_df):
        """数据就绪时健康检查通过。"""
        session_state[DATA_FRAME_KEY] = sample_df
        session_state["meta"] = {"columns": list(sample_df.columns)}
        state = collect_project_state(session_state)
        issues = run_health_checks(**state)
        assert not has_blocking_issues(issues)

    def test_step10_export_gate_blocks_on_unconfirmed_ai(self, session_state, sample_df):
        """有未确认 AI 修改时导出门禁阻止。"""
        session_state[DATA_FRAME_KEY] = sample_df
        session_state["meta"] = {"columns": list(sample_df.columns)}
        bundle = PaperDraftBundle(
            title="测试论文",
            sections={
                "introduction": PaperSection(name="引言", markdown="...", source="template"),
                "result": PaperSection(name="结果", markdown="M=3", source="data"),
            },
            source="template",
        )
        session_state[PAPER_BUNDLE_KEY] = bundle

        sel = PaperDiffSelectionState()
        sel.record_section_choice("introduction", "revised")
        # result 未确认
        session_state[PAPER_DIFF_SELECTION_KEY] = sel

        allowed, reasons, _ = run_export_gate(session_state)
        assert allowed is False
        assert any("未确认" in r for r in reasons)

    def test_step11_export_gate_passes(self, session_state, sample_df):
        """所有条件满足时导出门禁放行。"""
        session_state[DATA_FRAME_KEY] = sample_df
        session_state["meta"] = {"columns": list(sample_df.columns)}

        card = build_card_from_output({
            "test_type": "descriptive",
            "test_name_zh": "描述统计",
            "results": {"mean": 3, "std": 1, "n": 60, "min": 1, "max": 5, "skewness": 0, "kurtosis": 0},
        })
        append_result_card(session_state, card)

        bundle = PaperDraftBundle(
            title="完整论文",
            sections={
                "introduction": PaperSection(name="引言", markdown="研究背景...", source="template"),
                "method": PaperSection(name="方法", markdown="问卷法...", source="template"),
                "result": PaperSection(name="结果", markdown=card.apa_text, source="data"),
                "discussion": PaperSection(name="讨论", markdown="结果支持...", source="template"),
            },
            source="template",
        )
        session_state[PAPER_BUNDLE_KEY] = bundle

        allowed, reasons, _ = run_export_gate(session_state)
        assert allowed is True
        assert reasons == []

    def test_full_ui_golden_path(self, session_state, sample_df):
        """完整 UI 黄金路径：数据→分析→结果卡→论文→差异→健康→导出。"""
        # 1. 上传数据
        session_state[DATA_FRAME_KEY] = sample_df
        session_state["meta"] = {"columns": list(sample_df.columns)}

        # 2. 运行分析并生成结果卡
        card = build_card_from_output({
            "test_type": "pearson_corr",
            "test_name_zh": "Pearson 相关",
            "result": type("R", (), {"r": -0.4, "p_value": 0.01, "n": 60})(),
        })
        append_result_card(session_state, card)
        assert card.apa_text

        # 3. 生成论文 Bundle
        bundle = PaperDraftBundle(
            title="焦虑与自尊关系研究",
            sections={
                "introduction": PaperSection(name="引言", markdown="研究...", source="template"),
                "method": PaperSection(name="方法", markdown="问卷法...", source="template"),
                "result": PaperSection(name="结果", markdown=card.apa_text, source="data"),
                "discussion": PaperSection(name="讨论", markdown="支持...", source="template"),
            },
            source="template",
        )
        session_state[PAPER_BUNDLE_KEY] = bundle

        # 4. AI 差异选择（全部确认）
        sel = PaperDiffSelectionState()
        sel.accept_all_revised(list(bundle.sections.keys()))
        session_state[PAPER_DIFF_SELECTION_KEY] = sel

        # 5. 健康检查
        state = collect_project_state(session_state)
        issues = run_health_checks(**state)
        assert not has_blocking_issues(issues)

        # 6. 导出门禁
        allowed, reasons, _ = run_export_gate(session_state)
        assert allowed is True

        # 7. 验证导出内容
        from src.paper_writer.bundle_export import bundle_to_export_result
        result = bundle_to_export_result(bundle, format="markdown")
        assert card.apa_text in result.content
        assert "焦虑与自尊" in result.content
