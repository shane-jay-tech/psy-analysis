import json

import numpy as np
import pandas as pd
import pytest

from src.experiment_design import jspsych_data_importer as importer


def make_jsdata(df):
    return importer.JsPsychData(
        raw_df=df.copy(),
        trial_df=df.copy(),
        subject_ids=df.get("subject", pd.Series(["unknown"])).dropna().unique().tolist(),
        n_subjects=df.get("subject", pd.Series(["unknown"])).nunique(),
        n_trials_total=len(df),
        trial_types=df.get("trial_type", pd.Series(dtype=str)).dropna().unique().tolist(),
    )


def test_parse_csv_detects_v7_drops_empty_internal_columns_and_converts_seconds(tmp_path):
    path = tmp_path / "v7.csv"
    pd.DataFrame(
        {
            "subject": ["s1", "s1", "s2"],
            "sender": ["plugin", "plugin", "plugin"],
            "trial_type": ["congruent", "empty", "incongruent"],
            "response": ["left", "", "right"],
            "rt": [0.5, 0.0, 0.8],
            "stimulus": ["a", "b", "c"],
            "data": [json.dumps({"condition": "A"}), "", json.dumps({"condition": "B"})],
        }
    ).to_csv(path, index=False, encoding="utf-8-sig")

    parsed = importer.parse_jspsych_csv(str(path))

    assert parsed.metadata["jspsych_version"] == "v7"
    assert parsed.metadata["dropped_empty_trials"] == 1
    assert parsed.metadata["dropped_internal_cols"] == ["stimulus"]
    assert parsed.subject_ids == ["s1", "s2"]
    assert parsed.n_subjects == 2 and parsed.n_trials_total == 2
    assert parsed.trial_types == ["congruent", "empty", "incongruent"]
    assert "data_condition" in parsed.trial_df
    rt_col = importer._JSPsych_COLUMN_MAP["rt"]
    assert parsed.trial_df[rt_col].tolist() == [500.0, 800.0]
    assert any("1000" in warning or warning for warning in parsed.warnings)


def test_parse_csv_detects_v6_and_can_keep_empty_rows(tmp_path):
    path = tmp_path / "v6.csv"
    pd.DataFrame(
        {
            "worker_id": ["w1"],
            "plugin": ["html-keyboard-response"],
            "trial_type": ["html-keyboard-response"],
            "response": [np.nan],
            "rt": [np.nan],
        }
    ).to_csv(path, index=False)

    parsed = importer.parse_jspsych_csv(str(path), drop_empty_trials=False)

    assert parsed.metadata["jspsych_version"] == "v6"
    assert parsed.metadata["subject_col"] == "worker_id"
    assert parsed.n_trials_total == 1
    assert any("v6" in warning for warning in parsed.warnings)


def test_parse_csv_warns_when_subject_column_is_missing(tmp_path):
    path = tmp_path / "anonymous.csv"
    pd.DataFrame({"trial_type": ["task"], "response": ["yes"], "rt": [500]}).to_csv(
        path, index=False
    )

    parsed = importer.parse_jspsych_csv(str(path))

    assert parsed.subject_ids == ["unknown"]
    assert parsed.n_subjects == 1
    assert parsed.warnings


def test_parse_jsonl_keeps_valid_lines_reports_invalid_and_converts_rt(tmp_path):
    path = tmp_path / "trials.jsonl"
    path.write_text(
        json.dumps({"subject": "s1", "trial_type": "a", "rt": 0.25})
        + "\nnot-json\n"
        + json.dumps({"subject": "s2", "trial_type": "b", "rt": 0.5})
        + "\n",
        encoding="utf-8",
    )

    parsed = importer.parse_jspsych_json(str(path))

    assert parsed.n_subjects == 2 and parsed.n_trials_total == 2
    assert parsed.metadata["format"] == "jsonl"
    assert parsed.warnings
    rt_col = importer._JSPsych_COLUMN_MAP["rt"]
    assert parsed.trial_df[rt_col].tolist() == [250.0, 500.0]


def test_parse_jsonl_rejects_file_without_valid_trials(tmp_path):
    path = tmp_path / "invalid.jsonl"
    path.write_text("not json\n", encoding="utf-8")

    with pytest.raises(ValueError):
        importer.parse_jspsych_json(str(path))


@pytest.mark.parametrize(("agg_func", "expected"), [("mean", 200.0), ("median", 200.0)])
def test_to_wide_format_aggregates_trials_by_subject_and_condition(agg_func, expected):
    df = pd.DataFrame(
        {
            "subject": ["s1", "s1", "s1", "s2"],
            "trial_type": ["a", "a", "b", "a"],
            "rt": [100, 300, 500, 400],
        }
    )

    wide = importer.to_wide_format(make_jsdata(df), agg_func=agg_func)

    assert wide.columns.tolist() == ["subject", "a", "b"]
    assert wide.loc[wide["subject"] == "s1", "a"].iloc[0] == expected


def test_to_wide_format_validates_required_and_aggregate_columns():
    missing_pivot = make_jsdata(pd.DataFrame({"subject": ["s1"], "rt": [100]}))
    missing_value = make_jsdata(pd.DataFrame({"subject": ["s1"], "trial_type": ["a"]}))

    with pytest.raises(ValueError):
        importer.to_wide_format(missing_pivot)
    with pytest.raises(ValueError):
        importer.to_wide_format(missing_value)


def test_extract_condition_variables_includes_explicit_json_and_split_factors():
    df = pd.DataFrame(
        {
            "subject": ["s1", "s1"],
            "condition": ["control", "control"],
            "data_difficulty": ["easy", "hard"],
            "trial_type": ["congruent_left", "incongruent_right"],
        }
    )

    conditions = importer.extract_condition_variables(make_jsdata(df))

    assert set(conditions.columns) == {
        "subject",
        "condition",
        "data_difficulty",
        "factor_A",
        "factor_B",
    }
    assert conditions["factor_A"].tolist() == ["congruent", "incongruent"]


def test_extract_condition_variables_returns_original_when_no_conditions_exist():
    df = pd.DataFrame({"value": [1, 2]})
    pd.testing.assert_frame_equal(importer.extract_condition_variables(make_jsdata(df)), df)


def test_summary_stats_reports_counts_moments_and_accuracy():
    df = pd.DataFrame(
        {
            "trial_type": ["a", "a", "b"],
            "rt": [100, 300, "500"],
            "correct": [1, 0, 1],
        }
    )

    summary = importer.get_summary_stats(make_jsdata(df))

    a = summary[summary["trial_type"] == "a"].iloc[0]
    assert a["N"] == 2 and a["M"] == 200
    assert any(column not in {"trial_type", "N", "M", "SD"} for column in summary.columns)


def test_summary_stats_validates_group_and_value_columns():
    with pytest.raises(ValueError):
        importer.get_summary_stats(make_jsdata(pd.DataFrame({"trial_type": ["a"]})))
    with pytest.raises(ValueError):
        importer.get_summary_stats(make_jsdata(pd.DataFrame({"rt": [100]})))


@pytest.mark.parametrize(
    ("columns", "expected"),
    [(["subject", "participant_id"], "subject"), (["PROLIFIC_PID"], "PROLIFIC_PID"), (["x"], None)],
)
def test_detect_subject_column_uses_priority_order(columns, expected):
    assert importer._detect_subject_column(pd.DataFrame(columns=columns), "subject") == expected


def test_flatten_json_handles_dict_nested_invalid_and_empty_values():
    warnings = []
    df = pd.DataFrame(
        {
            "data": [
                {"condition": "a", "nested": {"x": 1}},
                "not-json",
                "",
            ],
            "rt": [1, 2, 3],
        }
    )

    flattened = importer._flatten_json_data_column(df, warnings)

    assert flattened.loc[0, "data_condition"] == "a"
    assert json.loads(flattened.loc[0, "data_nested"]) == {"x": 1}
    assert flattened.loc[1, "data"] == "not-json"
    assert flattened.loc[2, "data"] == ""


def test_drop_empty_trials_applies_all_supported_response_time_columns():
    df = pd.DataFrame(
        {
            "response": ["ok", "", "ok", "ok"],
            "rt": [100, 100, 0, 100],
            "reaction_time": [1, 1, 1, np.nan],
        }
    )

    filtered = importer._drop_empty_trials(df, [])

    assert filtered.index.tolist() == [0]


def test_rt_conversion_handles_seconds_milliseconds_and_non_numeric_values():
    warnings = []
    seconds = importer._detect_and_convert_rt(pd.DataFrame({"rt": [0.2, 1.5]}), warnings)
    milliseconds = importer._detect_and_convert_rt(pd.DataFrame({"rt": [200, 1500]}), [])
    invalid = importer._detect_and_convert_rt(pd.DataFrame({"rt": ["bad"]}), [])

    assert seconds["rt"].tolist() == [200.0, 1500.0]
    assert warnings
    assert milliseconds["rt"].tolist() == [200, 1500]
    assert invalid["rt"].tolist() == ["bad"]


def test_trial_timeline_filters_first_or_named_subject_and_sorts():
    elapsed = importer._JSPsych_COLUMN_MAP["time_elapsed"]
    df = pd.DataFrame(
        {
            "subject": ["s1", "s1", "s2"],
            elapsed: [300, 100, 200],
            "value": [3, 1, 2],
        }
    )
    jsdata = make_jsdata(df)

    first = importer.get_trial_timeline(jsdata)
    named = importer.get_trial_timeline(jsdata, subject="s2")

    assert first["value"].tolist() == [1, 3]
    assert named["value"].tolist() == [2]


def test_jspsych_summary_truncates_long_trial_type_lists():
    jsdata = importer.JsPsychData(
        raw_df=pd.DataFrame(),
        trial_df=pd.DataFrame(),
        subject_ids=["s1"],
        n_subjects=1,
        n_trials_total=6,
        trial_types=list("abcdef"),
    )

    assert jsdata.summary().endswith("...")
