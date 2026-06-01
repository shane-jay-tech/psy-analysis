"""实验设计系统测试"""
import pytest
from src.experiment_design.procedure_builder import (
    generate_latin_square,
    generate_balanced_latin_square,
    generate_full_counterbalancing,
)
from src.experiment_design.script_generator import (
    generate_jspsych_script,
    convert_items_to_jspsych_likert,
)


class TestLatinSquare:
    def test_standard_latin_square(self):
        for n in [2, 3, 4, 5, 6]:
            square = generate_latin_square(n)
            assert len(square) == n
            for row in square:
                assert sorted(row) == list(range(1, n + 1))
            for col in range(n):
                assert sorted(row[col] for row in square) == list(range(1, n + 1))

    def test_balanced_latin_square_even(self):
        for n in [2, 4, 6]:
            square = generate_balanced_latin_square(n)
            assert len(square) == n
            for row in square:
                assert sorted(row) == list(range(1, n + 1))
            for col in range(n):
                assert sorted(row[col] for row in square) == list(range(1, n + 1))

    def test_balanced_latin_square_odd(self):
        square = generate_balanced_latin_square(3)
        assert len(square) == 6  # 奇数：2倍行数
        square5 = generate_balanced_latin_square(5)
        assert len(square5) == 10

    def test_balanced_latin_square_first_row(self):
        """平衡拉丁方第一行应符合 Bradley 算法"""
        square = generate_balanced_latin_square(4)
        assert square[0] == [1, 2, 4, 3]

    def test_full_counterbalancing(self):
        result = generate_full_counterbalancing(["A", "B", "C"])
        assert len(result) == 6  # 3! = 6
        for perm in result:
            assert sorted(perm) == ["A", "B", "C"]


class TestJsPsychGenerator:
    def test_between_subjects(self):
        script = generate_jspsych_script(
            {"id": "test", "name": "测试", "design_type": "between_subjects"},
            conditions=["条件A", "条件B"],
            experiment_title="测试实验",
        )
        assert script.experiment_id == "exp_test"
        assert "between_subjects" in script.html_content
        assert "jsPsych" in script.html_content
        assert "条件A" in script.html_content
        assert len(script.warning) > 0

    def test_within_subjects(self):
        script = generate_jspsych_script(
            {"id": "wstest", "name": "被试内", "design_type": "within_subjects"},
            conditions=["A", "B", "C", "D"],
            experiment_title="被试内测试",
        )
        assert "within_subjects" in script.html_content
        assert "counterbalanceOrders" in script.html_content

    def test_survey(self):
        script = generate_jspsych_script(
            {"id": "survey", "name": "问卷", "design_type": "survey"},
            experiment_title="问卷调查",
        )
        assert "survey-likert" in script.html_content

    def test_generic_fallback(self):
        script = generate_jspsych_script(
            {"id": "unknown", "name": "未知", "design_type": "unsupported_type"},
            experiment_title="未知设计",
        )
        assert "暂无专用" in script.warning

    def test_item_conversion(self):
        items = [
            {"index": 1, "text": "我感到快乐"},
            {"index": 2, "text": "我对未来充满希望"},
        ]
        js = convert_items_to_jspsych_likert(items)
        assert "我感到快乐" in js
        assert "Q1" in js
        assert "Q2" in js
        assert "required: true" in js
