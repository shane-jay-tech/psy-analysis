"""v3.9 U5: PII 风险列检测测试。"""

import pandas as pd
import pytest

from src.utils.guardrails import detect_name_columns, detect_pii_columns


class TestDetectPIIColumns:
    def test_high_severity_phone(self):
        df = pd.DataFrame({"手机号": ["138-1234"], "年龄": [20]})
        result = detect_pii_columns(df)
        assert "手机号" in result["high"]
        assert result["any"] is True

    def test_high_severity_id_card(self):
        df = pd.DataFrame({"身份证": ["310..."], "score": [10]})
        result = detect_pii_columns(df)
        assert "身份证" in result["high"]

    def test_medium_severity_name_and_student_id(self):
        df = pd.DataFrame({"姓名": ["张三"], "学号": ["202301"], "score": [80]})
        result = detect_pii_columns(df)
        assert "姓名" in result["medium"]
        assert "学号" in result["medium"]

    def test_low_severity_subject_id(self):
        df = pd.DataFrame({"subject_id": ["s1", "s2"], "rt": [400, 500]})
        result = detect_pii_columns(df)
        assert "subject_id" in result["low"]

    def test_no_pii_returns_empty(self):
        df = pd.DataFrame({"焦虑": [1.2], "抑郁": [2.0]})
        result = detect_pii_columns(df)
        assert result["any"] is False
        assert result["high"] == [] and result["medium"] == [] and result["low"] == []

    def test_severity_priority_high_wins(self):
        """同时含 high 和 medium 关键词的列应归到 high。"""
        df = pd.DataFrame({"手机号_姓名": ["138 张三"]})
        result = detect_pii_columns(df)
        # 只在 high 出现一次（不重复归类）
        assert "手机号_姓名" in result["high"]
        assert "手机号_姓名" not in result["medium"]

    def test_email_detected_as_high(self):
        df = pd.DataFrame({"email": ["x@y.com"], "rt": [400]})
        result = detect_pii_columns(df)
        assert "email" in result["high"]

    def test_mixed_columns(self):
        df = pd.DataFrame({
            "身份证": ["a"], "姓名": ["b"], "subject": ["s1"], "焦虑分数": [3.0]
        })
        result = detect_pii_columns(df)
        assert result["high"] == ["身份证"]
        assert result["medium"] == ["姓名"]
        assert result["low"] == ["subject"]

    def test_legacy_detect_name_columns_still_works(self):
        """v3.9 后向兼容：旧 detect_name_columns 不能改变行为。"""
        df = pd.DataFrame({"姓名": ["a"], "score": [1]})
        cols = detect_name_columns(df)
        assert "姓名" in cols
