"""src/experiment_design/psychopy_generator.py 特征化测试（s918-32）。

三范式脚本生成：纯字符串断言，**零执行生成脚本**（生成期也不 import psychopy）。
只锁现状不改算法；s918-32 钉的那条"产物过不了 compile()"缺陷已由 s919-01 修好并翻正为编译断言（见文末两例）。
"""
import random
import sys

import pytest

from src.experiment_design.psychopy_generator import (
    PsychoPyExperiment,
    generate_latin_square_psychopy,
    generate_psychopy_script,
    generate_standard_paradigm,
)


def _exp(**kw):
    base = dict(conditions=["c1", "c2", "c3"], n_trials_per_block=6, n_blocks=2, n_practice_trials=5)
    base.update(kw)
    return PsychoPyExperiment(**base)


@pytest.fixture
def stroop_script():
    return generate_psychopy_script(generate_standard_paradigm("stroop", n_trials_per_condition=4))


def test_all_three_paradigms_carry_psychopy_imports_and_skeleton(stroop_script):
    for paradigm in ("stroop", "flanker", "memory"):
        script = generate_psychopy_script(generate_standard_paradigm(paradigm, n_trials_per_condition=2))
        assert "from psychopy import visual, core, event, gui, data" in script
        assert "from psychopy.hardware import keyboard" in script
        assert "def run_trial(trial, trial_num):" in script
        assert "win.flip()" in script


def test_paradigm_condition_sets_differ_as_configured():
    assert generate_standard_paradigm("stroop").conditions == ["一致", "不一致", "中性"]
    assert generate_standard_paradigm("flanker").conditions == ["一致", "不一致"]
    assert generate_standard_paradigm("emotion").conditions == ["正性", "负性", "中性"]
    assert generate_standard_paradigm("memory").conditions == ["旧项目", "新项目"]


def test_config_numbers_are_injected_at_their_own_lines():
    script = generate_psychopy_script(_exp(n_practice_trials=7, n_blocks=4, iti_min=0.2, iti_max=0.9))

    assert "for i in range(7):" in script
    assert "for block in range(4):" in script
    assert "random.uniform(0.2, 0.9)" in script


def test_trials_per_block_divides_by_condition_count_and_drops_remainder():
    """6 试次 / 3 条件 = 2；36 / 5 条件 = 7（余数静默丢弃，实测共 35 次）。"""
    script = generate_psychopy_script(_exp(n_trials_per_block=36, conditions=["a", "b", "c", "d", "e"]))

    assert script.count("for _ in range(7):") == 5


def test_response_keys_and_data_dir_are_injected(stroop_script):
    script = generate_psychopy_script(
        _exp(response_keys=["1", "2"], data_dir="out/x", paradigm="flanker")
    )

    assert "keys = ['1', '2']" in script
    assert "data_file = f'out/x/subj_{subj_id}_flanker_" in script
    assert "data_file = f'data/subj_{subj_id}_stroop_" in stroop_script


def test_stimuli_fall_back_to_four_placeholders_when_none_given():
    script = generate_psychopy_script(_exp())

    assert script.count("刺激") >= 4
    assert "conditions = ['c1', 'c2', 'c3']" in script
    assert "random.shuffle(experimental_trials)" in script


def test_feedback_block_toggles_with_show_feedback():
    on = generate_psychopy_script(_exp(show_feedback=True, feedback_duration=0.7))
    off = generate_psychopy_script(_exp(show_feedback=False, feedback_duration=0.7))

    assert "core.wait(0.7)" in on
    assert "core.wait(0.7)" not in off


def test_empty_conditions_generate_no_inner_trial_loops():
    script = generate_psychopy_script(_exp(conditions=[]))

    assert "conditions = []" in script
    assert "for _ in range(" not in script


def test_latin_square_rotates_then_shuffles_beyond_the_base_rows():
    random.seed(7)

    rows = generate_latin_square_psychopy(["A", "B", "C"], n_subjects=6)

    assert rows[:3] == [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]]
    assert len(rows) == 6
    assert all(sorted(r) == ["A", "B", "C"] for r in rows)


def test_latin_square_with_one_condition_repeats_it_for_every_subject():
    assert generate_latin_square_psychopy(["solo"], n_subjects=3) == [["solo"], ["solo"], ["solo"]]


def test_unknown_paradigm_lists_supported_names():
    with pytest.raises(ValueError, match=r"未知范式 'nope'"):
        generate_standard_paradigm("nope")


def test_generating_a_script_never_imports_psychopy(stroop_script):
    assert "psychopy" not in sys.modules


def test_output_path_writes_the_same_string_it_returns(tmp_path):
    exp = _exp()
    target = tmp_path / "nested" / "run.py"

    returned = generate_psychopy_script(exp, output_path=str(target))

    assert target.read_text(encoding="utf-8") == returned


@pytest.mark.parametrize(
    "exp",
    [
        _exp(),
        _exp(show_feedback=False),
        _exp(paradigm="custom_x"),
        generate_standard_paradigm("stroop", n_trials_per_condition=2),
        generate_standard_paradigm("flanker", n_trials_per_condition=2),
        generate_standard_paradigm("memory", n_trials_per_condition=2),
    ],
    ids=["feedback_on", "feedback_off", "unknown_paradigm", "stroop", "flanker", "memory"],
)
def test_generated_script_compiles(exp):
    """s919-01 翻正（原钉「产物过不了 compile()，SyntaxError: unexpected indent」）。

    改后六种形态全部可编译。只 compile 不 exec——psychopy 不在依赖里，执行也不是本模块的契约
    （文件头那条"零执行生成脚本"仍然成立）。
    """
    compile(generate_psychopy_script(exp), "<generated>", "exec")


def test_injected_blocks_land_inside_run_trial_body():
    """钉本次修复的**形态**：函数顶格、插值块在函数体内再进一层（4 空格），块内再深一层（8）。

    注入列数弄错时 `compile()` 也会红（0 列会让后续函数体变成"意外缩进"），但报出来的是
    "unexpected indent at line N"，看不出是谁的锅；这条直接点名"哪一层该在第几列"。
    """
    lines = generate_psychopy_script(_exp(paradigm="stroop")).splitlines()

    assert "def run_trial(trial, trial_num):" in lines                       # 顶格
    assert "    if response:" in lines                                       # 判断块首行在体内（4 空格）
    assert "    if trial.get('is_practice'):" in lines                        # 反馈块同样在体内
    assert "        color_to_key = {'红': 'f', '绿': 'j', '蓝': 'f', '黄': 'j'}" in lines  # 再进一层（8）
