"""问卷导入清洗与量表计分测试。"""

import numpy as np
import pandas as pd
import pytest

from src.questionnaire.import_cleaning import (
    ColumnClassification,
    ScaleDimension,
    CleaningLogEntry,
    classify_columns,
    reverse_score,
    compute_dimension_scores,
    detect_invalid_responses,
    run_questionnaire_cleaning,
    export_cleaning_log,
)


@pytest.fixture
def sample_questionnaire_df():
    """模拟问卷星导出数据。"""
    np.random.seed(42)
    n = 50
    return pd.DataFrame({
        "序号": range(1, n + 1),
        "提交时间": ["2024-01-01 10:00"] * n,
        "用时(秒)": np.random.randint(30, 600, n),
        "性别": np.random.choice(["男", "女"], n),
        "年级": np.random.choice(["大一", "大二", "大三", "大四"], n),
        "Q1": np.random.randint(1, 6, n),
        "Q2": np.random.randint(1, 6, n),
        "Q3": np.random.randint(1, 6, n),
        "Q4": np.random.randint(1, 6, n),
        "Q5": np.random.randint(1, 6, n),
        "Q6": np.random.randint(1, 6, n),
        "Q7": np.random.randint(1, 6, n),
        "Q8": np.random.randint(1, 6, n),
    })


@pytest.fixture
def dimensions():
    return [
        ScaleDimension(name="焦虑", items=["Q1", "Q2", "Q3", "Q4"], reverse_items=["Q3"]),
        ScaleDimension(name="自尊", items=["Q5", "Q6", "Q7", "Q8"], reverse_items=["Q7", "Q8"]),
    ]


class TestColumnClassification:
    def test_identifies_metadata(self, sample_questionnaire_df):
        result = classify_columns(sample_questionnaire_df)
        assert "序号" in result.metadata_columns

    def test_identifies_timestamp(self, sample_questionnaire_df):
        result = classify_columns(sample_questionnaire_df)
        assert "提交时间" in result.timestamp_columns

    def test_identifies_demographic(self, sample_questionnaire_df):
        result = classify_columns(sample_questionnaire_df)
        assert "性别" in result.demographic_columns
        assert "年级" in result.demographic_columns

    def test_identifies_items(self, sample_questionnaire_df):
        result = classify_columns(sample_questionnaire_df)
        for q in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]:
            assert q in result.item_columns

    def test_all_columns_classified(self, sample_questionnaire_df):
        result = classify_columns(sample_questionnaire_df)
        all_cols = set(result.all_identified)
        expected = set(sample_questionnaire_df.columns)
        assert all_cols == expected


class TestReverseScore:
    def test_basic_reverse(self):
        s = pd.Series([1, 2, 3, 4, 5])
        rev = reverse_score(s, max_score=5, min_score=1)
        assert list(rev) == [5, 4, 3, 2, 1]

    def test_7point_scale(self):
        s = pd.Series([1, 4, 7])
        rev = reverse_score(s, max_score=7, min_score=1)
        assert list(rev) == [7, 4, 1]

    def test_preserves_nan(self):
        s = pd.Series([1, np.nan, 5])
        rev = reverse_score(s, max_score=5, min_score=1)
        assert rev.iloc[0] == 5
        assert pd.isna(rev.iloc[1])
        assert rev.iloc[2] == 1


class TestDimensionScoring:
    def test_basic_scoring(self, sample_questionnaire_df, dimensions):
        scored = compute_dimension_scores(sample_questionnaire_df, dimensions)
        assert "焦虑_mean" in scored.columns
        assert "焦虑_sum" in scored.columns
        assert "自尊_mean" in scored.columns
        assert "自尊_sum" in scored.columns
        assert len(scored) == len(sample_questionnaire_df)

    def test_reverse_items_applied(self, dimensions):
        df = pd.DataFrame({
            "Q1": [5, 5, 5],
            "Q2": [5, 5, 5],
            "Q3": [1, 1, 1],  # reverse: becomes 5
            "Q4": [5, 5, 5],
        })
        scored = compute_dimension_scores(df, [dimensions[0]])
        assert scored["焦虑_mean"].iloc[0] == pytest.approx(5.0)

    def test_missing_column_handled(self, dimensions):
        df = pd.DataFrame({"Q1": [3, 4], "Q2": [3, 4]})
        scored = compute_dimension_scores(df, [dimensions[0]])
        assert "焦虑_mean" in scored.columns

    def test_sum_equals_mean_times_count(self, sample_questionnaire_df, dimensions):
        scored = compute_dimension_scores(sample_questionnaire_df, dimensions)
        row0_mean = scored["焦虑_mean"].iloc[0]
        row0_sum = scored["焦虑_sum"].iloc[0]
        assert row0_sum == pytest.approx(row0_mean * 4, rel=0.01)


class TestInvalidDetection:
    def test_identical_responses_flagged(self):
        df = pd.DataFrame({
            "Q1": [3, 3, 1, 5],
            "Q2": [3, 3, 2, 4],
            "Q3": [3, 3, 3, 3],
            "Q4": [3, 3, 4, 2],
        })
        invalid = detect_invalid_responses(df, ["Q1", "Q2", "Q3", "Q4"])
        assert invalid.iloc[0] == True  # all 3s
        assert invalid.iloc[1] == True  # all 3s
        assert invalid.iloc[2] == False
        assert invalid.iloc[3] == False

    def test_duration_too_short_flagged(self):
        df = pd.DataFrame({
            "duration": [10, 200, 300, 50],
            "Q1": [1, 2, 3, 4],
            "Q2": [2, 3, 4, 5],
        })
        invalid = detect_invalid_responses(
            df, ["Q1", "Q2"], duration_column="duration", min_duration_seconds=60
        )
        assert invalid.iloc[0] == True  # 10s < 60s
        assert invalid.iloc[1] == False
        assert invalid.iloc[3] == True  # 50s < 60s

    def test_no_items_no_crash(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        invalid = detect_invalid_responses(df, [])
        assert len(invalid) == 3
        assert invalid.sum() == 0


class TestFullCleaning:
    def test_basic_pipeline(self, sample_questionnaire_df, dimensions):
        result = run_questionnaire_cleaning(
            sample_questionnaire_df,
            dimensions=dimensions,
            duration_column="用时(秒)",
            min_duration_seconds=60,
        )
        assert result.df_cleaned is not None
        assert result.df_scored is not None
        assert len(result.log) >= 3
        assert result.summary["original_n"] == 50
        assert result.summary["valid_n"] <= 50

    def test_cleaning_removes_invalid(self, dimensions):
        df = pd.DataFrame({
            "序号": [1, 2, 3],
            "性别": ["男", "女", "男"],
            "Q1": [3, 1, 5],
            "Q2": [3, 2, 4],
            "Q3": [3, 3, 3],
            "Q4": [3, 4, 2],
            "Q5": [3, 1, 5],
            "Q6": [3, 2, 4],
            "Q7": [3, 3, 3],
            "Q8": [3, 4, 2],
        })
        result = run_questionnaire_cleaning(df, dimensions=dimensions)
        assert len(result.df_cleaned) < 3

    def test_no_dimensions_still_works(self, sample_questionnaire_df):
        result = run_questionnaire_cleaning(sample_questionnaire_df)
        assert result.df_scored is None
        assert result.df_cleaned is not None

    def test_log_export_markdown(self, sample_questionnaire_df, dimensions):
        result = run_questionnaire_cleaning(sample_questionnaire_df, dimensions=dimensions)
        md = export_cleaning_log(result.log, format="markdown")
        assert "# 数据清洗日志" in md
        assert "列分类" in md
        assert "无效样本" in md

    def test_log_export_json(self, sample_questionnaire_df, dimensions):
        result = run_questionnaire_cleaning(sample_questionnaire_df, dimensions=dimensions)
        import json
        json_text = export_cleaning_log(result.log, format="json")
        data = json.loads(json_text)
        assert len(data) >= 3
        assert data[0]["step"] == "列分类"
