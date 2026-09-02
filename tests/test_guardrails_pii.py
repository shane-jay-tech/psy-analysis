"""v3.9 U5: PII 风险列检测测试。"""

import pandas as pd
import pytest

from src.utils.guardrails import (
    detect_name_columns,
    detect_pii_columns,
    redact_dataframe_for_storage,
)


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


class TestStorageRedaction:
    def test_high_risk_columns_are_dropped_and_identifiers_are_hashed(self):
        df = pd.DataFrame({
            "手机号": ["13800138000", "13900139000"],
            "姓名": ["张三", "李四"],
            "subject_id": ["P01", "P02"],
            "score": [10, 20],
        })

        redacted, report = redact_dataframe_for_storage(df)

        assert "手机号" not in redacted.columns
        assert redacted["姓名"].tolist() != df["姓名"].tolist()
        assert redacted["subject_id"].tolist() != df["subject_id"].tolist()
        assert redacted["score"].tolist() == [10, 20]
        assert report["dropped_high_risk_columns"] == ["手机号"]
        assert set(report["hashed_identifier_columns"]) == {"姓名", "subject_id"}
        assert df["姓名"].tolist() == ["张三", "李四"]

    def test_sensitive_content_inside_neutral_columns_is_redacted(self):
        df = pd.DataFrame({
            "备注": ["请联系13800138000", "邮箱 user@example.com", "普通说明"],
            "分数": [1, 2, 3],
        })

        redacted, report = redact_dataframe_for_storage(df)

        stored = " ".join(redacted["备注"].tolist())
        assert "13800138000" not in stored
        assert "user@example.com" not in stored
        assert "[REDACTED_PHONE]" in stored
        assert report["redacted_content_matches"]["备注:phone"] == 1
        assert df.loc[0, "备注"] == "请联系13800138000"

    def test_landline_requires_contact_context_to_avoid_numeric_id_false_positive(self):
        df = pd.DataFrame({"备注": ["编号01234567890", "座机：010-12345678"]})

        redacted, report = redact_dataframe_for_storage(df)

        assert redacted.loc[0, "备注"] == "编号01234567890"
        assert redacted.loc[1, "备注"] == "[REDACTED_LANDLINE]"
        assert report["redacted_content_matches"] == {"备注:landline": 1}
