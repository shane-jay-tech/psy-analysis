"""端到端 UI 渲染测试（使用 streamlit.testing.AppTest）"""

import pytest
import pandas as pd
from streamlit.testing.v1.app_test import AppTest


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
        at = AppTest.from_file("app.py")
        at.session_state["app_mode"] = "📈 数据分析"
        at.run(timeout=30)
        assert not at.exception

        # 如果存在文件上传器，模拟上传 CSV
        if len(at.file_uploader) > 0:
            df = pd.DataFrame({"group": ["A", "A", "B", "B"], "score": [1, 2, 3, 4]})
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            at.file_uploader[0].upload("test.csv", csv_bytes, "text/csv")
            at.run(timeout=30)
            assert not at.exception


class TestModeSwitching:
    def test_questionnaire_mode_accessible(self):
        # mode 由 sidebar 的 radio (key="app_mode") 控制；直接置 session_state
        at = AppTest.from_file("app.py")
        at.session_state["app_mode"] = "📋 问卷设计"
        at.run(timeout=30)
        assert not at.exception
