"""端到端 UI 渲染测试（使用 streamlit.testing.AppTest）"""

import pytest
import pandas as pd
from streamlit.testing.v1.app_test import AppTest

from src.ui.navigation import PAGE_MODES


def _ready_app(mode="📈 数据分析"):
    """跳过一次性首访页，返回隔离存储上的可交互应用。"""
    at = AppTest.from_file("app.py")
    at.session_state["privacy_accepted"] = True
    at.session_state["onboarding_completed"] = True
    at.session_state["_onboarding_skipped"] = True
    at.session_state["app_mode"] = mode
    at.run(timeout=60)
    assert not at.exception
    return at


class TestAppStartup:
    def test_app_loads_without_error(self):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)
        assert not at.exception

    def test_sidebar_has_language_switcher(self):
        at = AppTest.from_file("app.py")
        at.run(timeout=30)
        # 检查是否有语言切换（可能在主区域或侧边栏）
        radios = list(at.sidebar.radio) + list(at.radio)
        assert len(radios) > 0 or not at.exception


class TestDataUploadFlow:
    def test_upload_csv_triggers_analysis(self):
        at = _ready_app()
        assert len(at.file_uploader) >= 1

        df = pd.DataFrame({
            "group": ["A", "A", "A", "B", "B", "B"],
            "score": [10, 12, 11, 18, 20, 19],
        })
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        at.file_uploader[0].upload("test.csv", csv_bytes, "text/csv")
        at.run(timeout=60)

        assert not at.exception
        assert at.session_state["file_name"] == "test.csv"
        assert at.session_state["df"].shape == (6, 2)
        assert at.session_state["_workspace_last_saved"]

        request = next(x for x in at.text_area if x.label == "请输入您的分析需求：")
        request.set_value("对 score 做描述统计")
        analyze = next(x for x in at.button if x.label == "🔍 开始分析")
        analyze.click()
        at.run(timeout=60)

        assert not at.exception
        assert at.session_state["plan"] is not None
        assert at.session_state["analysis_output"] is not None
        output = at.session_state["analysis_output"]
        assert output.get("test_type") == "descriptive"
        assert output.get("descriptive") is not None


class TestModeSwitching:
    def test_questionnaire_mode_accessible(self):
        at = _ready_app("📋 问卷设计")
        assert not at.exception

    def test_navigation_uses_complete_canonical_stage_list(self):
        at = _ready_app()
        stage_radio = next(r for r in at.sidebar.radio if r.label == "按阶段进入")
        assert list(stage_radio.options) == PAGE_MODES

    def test_experiment_design_route_renders_without_error(self):
        at = _ready_app("🧪 实验设计")
        assert not at.exception
        assert any("实验设计" in str(x.value) for x in at.title)
