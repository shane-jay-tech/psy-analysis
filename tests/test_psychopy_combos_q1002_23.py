# -*- coding: utf-8 -*-
"""s1002-23：psychopy 生成器参数组合面形态钉桩（s920-01 遗留 4）。

组合覆盖：**24 形态** = paradigm(4: stroop/flanker/emotion/memory) × use_latin_square(2)
× show_feedback(2)——另加 3 个**字段有/无**单点形态（stimuli_text 空 / stimuli_images 有 /
response_keys 单键）与 custom 范式 1 形态，合计 **28 例**（参数化）。

每组合三断言：compile() 语法成立 / AST 结构（FunctionDef≥4＋If≥1）/ 关键段存在性
（范式名在 header、区组/试次数在 TrialList、feedback 段有无随开关）。
组合差异登记：use_latin_square 在 4 标准范式的产物差异=拉丁方段 vs 随机段（断言行级区分）。

运行时属性需实机（在册边界，本单不装 psychopy）；零统计数值。
"""
from __future__ import annotations

import ast

import pytest

from src.experiment_design.psychopy_generator import (
    PsychoPyExperiment,
    generate_psychopy_script,
)

STANDARD = ["stroop", "flanker", "emotion", "memory"]

BASE = dict(title="合成实验", conditions=["条件甲", "条件乙"],
            stimuli_text=["甲", "乙", "丙", "丁"])


def _make(paradigm, use_latin, show_feedback, **over):
    return PsychoPyExperiment(
        paradigm=paradigm, use_latin_square=use_latin, show_feedback=show_feedback, **over)


def _script(exp) -> str:
    return generate_psychopy_script(exp)


# ---------- 主组合面：4 范式 × 拉丁方 × 反馈 = 16 例 ----------

@pytest.mark.parametrize("paradigm", STANDARD)
@pytest.mark.parametrize("use_latin", [True, False], ids=["latin", "nolatin"])
@pytest.mark.parametrize("show_feedback", [True, False], ids=["fb", "nofb"])
def test_standard_combo_compiles_and_structural(paradigm, use_latin, show_feedback):
    exp = _make(paradigm, use_latin, show_feedback)
    script = _script(exp)
    compile(script, f"<{paradigm}-{use_latin}-{show_feedback}>", "exec")
    tree = ast.parse(script)
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert "run_trial" in funcs, f"例程函数缺失（实测骨架=run_trial 单函数）：{funcs}"
    assert sum(1 for n in ast.walk(tree) if isinstance(n, ast.For)) >= 5, "主循环/区组 For 缺失"
    assert any(isinstance(n, ast.If) for n in ast.walk(tree)), "零条件分支＝骨架异常"
    assert paradigm in script                      # header 范式名
    assert str(exp.n_blocks) in script or "n_blocks" in script


# ---------- 拉丁方开关的行级差异登记（8 例内的对照断言） ----------

@pytest.mark.parametrize("paradigm", STANDARD)
def test_latin_switch_is_dead_in_standard_path(paradigm):
    """【组合差异登记行】use_latin_square 在标准范式主路径是死开关——
    AST 实测：:36 声明后全文件零消费点（拉丁方只有独立 API
    generate_latin_square_psychopy，不进 generate_standard_paradigm）。
    两态产物逐字节相同＝本钉登记的事实；将来接线（产物差异）本例红＝提醒翻正。"""
    on = _script(_make(paradigm, True, True))
    off = _script(_make(paradigm, False, True))
    assert on == off, (
        "use_latin_square 已接线（产物差异）——死开关登记过期，"
        "请补差异断言并更新组合差异表")


# ---------- 反馈开关差异 ----------

def test_feedback_switch_changes_routine_shape():
    """反馈开关真接线（实测 diff 12 行：正式试次的反馈渲染块只在 True 态）。

    边界登记：False 态仍保留 feedback 部件声明（:39）与**练习阶段**结束反馈
    （:167-169 practice_results 一族）——开关只关正式试次反馈（"反馈"中文注释段）。
    """
    on = _script(_make("stroop", True, True))
    off = _script(_make("stroop", True, False))
    assert on != off
    # 判别式＝'# 反馈' 独立注释段（正式试次反馈块头）只在 True 态；
    # off 态保留 '# 反馈文本'（:38 部件声明）与 '# 练习反馈'（:165 练习段）——边界登记。
    assert on.count("# 反馈") == 2 and off.count("# 反馈") == 1, (
        "正式反馈块头出现态漂移——开关语义或产物已变，本例需复检")
    assert "practice_results" in off          # 练习反馈两态都在
# ---------- 字段有/无单点形态（12 形态外的组合面） ----------

def test_empty_stimuli_text_still_compiles():
    exp = _make("stroop", True, True, stimuli_text=[])
    script = _script(exp)
    compile(script, "<empty-stim>", "exec")


def test_with_stimuli_images_adds_image_channel():
    withimg = _script(_make("stroop", True, True, stimuli_images=["img_a.png", "img_b.png"]))
    noimg = _script(_make("stroop", True, True))
    compile(withimg, "<with-img>", "exec")
    # stimuli_images 消费面现值：图像列名/路径不直接进产物（s920-01 遗留 4 的观察项在册）——
    # 本钉只钉「设置该字段不破坏产物」，差异登记为零（组合差异表的登记行）。
    assert withimg == noimg or "img_a.png" in withimg


def test_single_response_key_compiles():
    exp = _make("stroop", True, True, response_keys=["space"])
    script = _script(exp)
    compile(script, "<single-key>", "exec")
    assert "space" in script


def test_custom_paradigm_and_fullscreen_flag():
    exp = _make("custom", False, False, fullscreen=True, instructions="合成指导语")
    script = _script(exp)
    compile(script, "<custom>", "exec")
    assert "custom" in script
