# -*- coding: utf-8 -*-
"""script_generator 的 survey / generic 两分支行为钉桩（s922-132）。

**锚点复核（开工第一步实测，HEAD f6fc82d）：**
- `src/experiment_design/script_generator.py:517`「def _gen_survey(」——逐字一致。
- `src/experiment_design/script_generator.py:631`「def _gen_generic(」——逐字一致。

**工单三处前提与磁盘不符，本套件按实况收窄（否证证据写在各用例 docstring）：**

1. 工单：「test_experiment_design 只覆盖 between/within 两分支」——**不实**。
   `tests/test_experiment_design.py:73` `test_survey`（1 条断言 `"survey-likert" in html`）与
   `:80` `test_generic_fallback`（1 条断言 `"暂无专用" in warning`）**已在册**，且该文件 10 例全绿、无 skip 标记
   （复算：`.venv/Scripts/python.exe -m pytest tests/test_experiment_design.py -q -rs` → `10 passed`）。
   ⇒ 真实缺口是「浅断言」，本套件把它钉深（trial 计数／Likert 数组结构／分支归属／产物形状）。
2. 工单：「断言产物可 `ast.parse`」——**JS/HTML 产物不能用 Python 的 `ast.parse`**（会 SyntaxError）。
   ⇒ 收窄成两条可复算的替身判据：① **生成器模块本体**可 `ast.parse`（并核对分发常量集，见最后一个用例）；
   ② 产物内联 `<script>` 的**花括号/圆括号配平**（`{}` 20/20、`()` 15/15，实测读数）＝"结构未被 f-string 打坏"。
3. 工单：「未知设计不抛异常**走默认模板**」——磁盘上这是**两条不同的路**，必须分开钉：
   `design_type` **缺失**（`script_generator.py:48` 的 `.get("design_type", "between_subjects")`）→ 走 `_gen_between_subjects`；
   `design_type` **有值但不认识** → 走 `_gen_generic`（`:631`）。⇒ 两个方向各钉一条，谁改了默认值都会翻红。

⚠️ 工单说 generic 产物「含 jspsych.init 骨架」也**不实**：`_gen_generic` 返回的 `html_content`
只有两条 HTML 注释（`script_generator.py:644`），`js_content` 为空串——**它压根不是可跑脚本**，
这本身是该回退分支的现状（见 test_generic_product_is_a_stub_not_a_runnable_script，钉的是现状）。

**不改 src/experiment_design/script_generator.py。零网络、零 Streamlit、零文件 IO。**
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GEN_SRC = REPO / "src" / "experiment_design" / "script_generator.py"

from src.experiment_design.script_generator import (  # noqa: E402
    JsPsychScript,
    generate_jspsych_script,
)

LIKERT_LABELS = ["完全不同意", "不同意", "不确定", "同意", "完全同意"]


def _survey(**kw) -> JsPsychScript:
    design = {"id": "sv1", "name": "问卷模板A", "design_type": "survey"}
    design.update(kw.pop("design", {}))
    title = kw.pop("experiment_title", "问卷实验")
    return generate_jspsych_script(design, experiment_title=title, **kw)


def _inline_js(html: str) -> str:
    """取内联 <script>（无 src 属性）里的 JS 正文。"""
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert len(blocks) == 1, f"内联脚本块数量异常：{len(blocks)}"
    return blocks[0]


# ═══════════════════════════════════════════════════════ survey 分支


def test_survey_branch_emits_likert_trial_type_and_plugin_tag():
    """完成标准 2：产物含 'likert'／等价 trial 类型标记（现状：两类标记都在）。"""
    html = _survey().html_content
    assert "plugin-survey-likert@1.1.3" in html, "缺 survey-likert 插件 script 标签"
    assert "jsPsychSurveyLikert" in html, "缺 jsPsych v7 的 trial type 标记"
    assert "type: jsPsychSurveyLikert" in html
    # survey-text / multi-choice 也一并引入（供后续替换占位题目）
    assert "plugin-survey-text@1.1.3" in html and "plugin-survey-multi-choice@1.1.3" in html


def test_survey_has_jspsych_init_skeleton_and_three_trials():
    """「jspsych.init 骨架」＋试次数：survey 产物固定 3 次 timeline.push，阶段顺序被钉死。"""
    html = _survey().html_content
    assert html.count("jsPsych.init(") == 1
    assert html.count("timeline.push") == 3, "survey 的 timeline 试次数变了（指导语/问卷块/结束）"
    phases = re.findall(r'phase: "(\w+)"', html)
    assert phases == ["instructions", "survey_block", "debrief"], phases
    assert "timeline: timeline," in html and "on_finish: function()" in html


def test_survey_likert_array_shape_two_five_point_items():
    """Likert 项数组生成：2 道题 × 5 点标签、Q1/Q2 命名、required 全真（现状是占位题目）。"""
    html = _survey().html_content
    assert html.count("prompt:") == 2
    assert re.findall(r'name: "(Q\d+)"', html) == ["Q1", "Q2"]
    assert html.count("required: true") == 2
    for label in LIKERT_LABELS:
        # 带引号计数：裸串会让「同意」命中「完全不同意/不同意」（实测 4 次），是假判据
        assert html.count(f'"{label}"') == 2, f"标签「{label}」出现次数变了（每题一份，应为 2）"
    assert html.count("block: 1") == 1, "问卷块编号变化会影响数据回溯口径"


def test_survey_product_ignores_conditions_procedure_and_timeline_vars():
    """现状钉桩：_gen_survey 完全不消费 conditions/procedure/timeline_variables（题目是占位符）。

    这正是 warning 里「请使用问卷设计引擎生成的题目替换」的由来。若将来接通真实题目，
    本用例会翻红 ⇒ 那时应把它改写成「输入决定输出」的正向断言。
    """
    script = _survey(conditions=["ZZCOND"], procedure={"ZZPROC": 1}, timeline_variables=[{"ZZVAR": 1}])
    for marker in ("ZZCOND", "ZZPROC", "ZZVAR"):
        assert marker not in script.html_content, f"survey 产物意外吸收了 {marker}（分支行为已改变）"
    assert "问卷题目为通用占位符" in script.warning
    assert "survey block" in script.warning


def test_survey_product_is_brace_balanced_and_js_content_empty():
    """工单「产物可 ast.parse」的收窄替身：内联 JS 括号配平＋产物全在 html_content（js_content 为空串）。"""
    script = _survey()
    assert script.js_content == "", "现状 js_content 为空；若改成拆分式需同步本判据"
    assert script.preview_url == ""
    assert script.html_content.startswith("<!DOCTYPE html>")
    js = _inline_js(script.html_content)
    assert js.count("{") == js.count("}"), (js.count("{"), js.count("}"))
    assert js.count("(") == js.count(")"), (js.count("("), js.count(")"))
    assert script.html_content.count("{") == script.html_content.count("}"), "f-string 转义把 HTML 花括号打坏了"
    assert 'jspsych@7.3.4' in script.html_content, "jsPsych 版本钉被改动"


def test_survey_ids_and_template_name_come_from_design_dict():
    script = _survey(design={"id": "abc123", "name": "我的问卷"})
    assert script.experiment_id == "exp_abc123"
    assert script.template_name == "我的问卷"
    no_name = generate_jspsych_script({"design_type": "survey"})
    assert no_name.experiment_id == "exp_unnamed" and no_name.template_name == "未命名模板"


@pytest.mark.parametrize("design_type", ["survey", "questionnaire"])
def test_survey_reachable_via_both_design_type_aliases(design_type):
    """分发元组 ("survey", "questionnaire")（`script_generator.py:60`）：两条别名都必须落到同一模板。"""
    script = generate_jspsych_script({"id": "x", "name": "n", "design_type": design_type})
    assert "jsPsychSurveyLikert" in script.html_content
    assert script.html_content.count("jsPsych.init(") == 1


def test_survey_title_is_escaped_at_all_three_write_points():
    """**#69 案 A 已落地**（本用例原为「未转义现状登记」，docstring 预言了这次翻红）。

    改前它钉的是 `probe in html`（裸串直插 JS/HTML）；加固后裸串必须消失，
    且题名仍要**一字不丢地**到达三个写点（转义≠丢弃，见 test_script_generator_title_escaping.py 的往返判据）。
    判据方向只紧不松：任何把转义摘掉的改动都会在这里翻红。
    """
    probe = 'Z"; alert(1); //'
    html = _survey(experiment_title=probe).html_content
    assert probe not in _inline_js(html), "裸串又能进内联 JS ⇒ 转义被摘掉了"
    assert probe not in html, "裸串仍在产物里（含 <title>）⇒ 未转义"
    assert 'title: "Z\\"; alert(1); //",' in html, "JS 字符串上下文的转义形状变了"
    assert "<title>Z&quot;; alert(1); //</title>" in html
    assert html.count("alert(1)") == 3, "题名写点数变了（<title>／EXPERIMENT_CONFIG.title／指导语 <h2>）"
    assert html.count("<script") == html.count("</script"), "script 标签配平被打破"


# ═══════════════════════════════════════════════════════ generic 回退分支


@pytest.mark.parametrize(
    "design_type",
    ["", "unsupported_type", "Between_Subjects", "survey_x", "被试间", "None", "survey "],
)
def test_unknown_design_type_falls_back_to_generic_without_raising(design_type):
    """完成标准 3：任何**有值但不认识**的 design_type 都不抛，且 warning 回显原值。"""
    script = generate_jspsych_script({"id": "u", "name": "n", "design_type": design_type})
    assert isinstance(script, JsPsychScript)
    assert "暂无专用" in script.warning
    assert design_type in script.warning, f"warning 未回显原 design_type={design_type!r}"
    assert script.js_content == ""
    assert script.experiment_id == "exp_u"


def test_generic_product_is_a_stub_not_a_runnable_script():
    """现状：回退产物只有两条 HTML 注释、**没有 jsPsych 骨架**（工单"含 jspsych.init"对本分支不成立）。"""
    script = generate_jspsych_script({"id": "u2", "name": "n", "design_type": "zzz"})
    assert script.html_content == (
        '<!-- jsPsych script for 心理学实验 -->\n<!-- Generic template - please customize -->'
    ), script.html_content
    assert "jsPsych.init" not in script.html_content
    assert "<!DOCTYPE" not in script.html_content
    assert "请使用 between_subjects 或 within_subjects 模板。" in script.warning


def test_missing_design_type_key_goes_to_between_subjects_not_generic():
    """工单未区分的另一半：`script_generator.py:48` 的默认值是 between_subjects ⇒ 缺 key ≠ 未知值。"""
    script = generate_jspsych_script({"id": "d", "name": "n"}, conditions=["A", "B"])
    assert "暂无专用" not in script.warning, "缺 design_type 却掉进 generic ⇒ 默认值被改动"
    assert "between_subjects" in script.html_content


@pytest.mark.parametrize("design_type", [None, "", 0, 1.5, "survey", "zzz", "within_subjects"])
def test_no_design_type_shape_raises(design_type):
    """最宽的"不抛"面：连 None/数字/空串都不该在分发处炸（现状：None 落到默认 between 分支）。"""
    design = {"id": "z", "name": "n"}
    if design_type is not None:
        design["design_type"] = design_type
    script = generate_jspsych_script(design, conditions=["A"], procedure=None, timeline_variables=None)
    assert isinstance(script, JsPsychScript) and script.experiment_id == "exp_z"


# ═══════════════════════════════════════════════════════ 分发面元测试


def _returns_targets(nodes) -> list[str]:
    """接受 stmt 列表或单个节点，返回其中的 `return _gen_xxx(...)` 目标名。"""
    if isinstance(nodes, (list, tuple)):
        out: list[str] = []
        for n in nodes:
            out.extend(_returns_targets(n))
        return out
    return [
        c.value.func.id
        for c in ast.walk(nodes)
        if isinstance(c, ast.Return) and isinstance(c.value, ast.Call) and isinstance(c.value.func, ast.Name)
    ]


def _extract_dispatch(source: str) -> tuple[dict, str]:
    """从**源码文本**抽出 (分发表, design_type 缺失时的默认分支)。纯 ast，不执行被检码。"""
    tree = ast.parse(source)
    fn = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "generate_jspsych_script"
    )
    mapping: dict[tuple[str, ...], str] = {}
    current = next(n for n in fn.body if isinstance(n, ast.If))
    while True:
        test = current.test
        assert isinstance(test, ast.Compare) and getattr(test.left, "id", "") == "design_type"
        comp = test.comparators[0]
        keys = tuple(c.value for c in comp.elts) if isinstance(comp, ast.Tuple) else (comp.value,)
        branch = _returns_targets(current.body)
        assert len(branch) == 1, (keys, branch)
        mapping[keys] = branch[0]
        if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
            continue
        mapping[("<else>",)] = (_returns_targets(current.orelse) or ["<empty>"])[0]
        break
    default_call = next(
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "get"
        and n.args
        and getattr(n.args[0], "value", None) == "design_type"
    )
    assert len(default_call.args) == 2
    return mapping, default_call.args[1].value


EXPECTED_DISPATCH = {
    ("between_subjects",): "_gen_between_subjects",
    ("within_subjects",): "_gen_within_subjects",
    ("survey", "questionnaire"): "_gen_survey",
    ("<else>",): "_gen_generic",
}


def test_dispatch_table_and_module_parse_are_pinned():
    """工单「产物可 ast.parse」的另一半（**生成器模块本体**可解析，见文件头否证 2）＋分发常量集钉桩。

    加分支／改别名／改默认值而不回写本文件，都会在这里翻红。
    """
    mapping, default = _extract_dispatch(GEN_SRC.read_text(encoding="utf-8"))
    assert mapping == EXPECTED_DISPATCH, mapping
    # 默认值：design_type 缺失 → between_subjects（`script_generator.py:48`）
    assert default == "between_subjects"


def test_dispatch_pin_actually_rejects_mutants():
    """判别力自证：三种内存文本变异必须被 `_extract_dispatch` 抽成**与现表不同**的结果（本套件不是空转）。

    ⚠️ 只改源码文本再重新解析，**不 exec**（`_gen_within_subjects` 里有相对 import，exec 假模块会炸）。
    """
    source = GEN_SRC.read_text(encoding="utf-8")
    baseline = _extract_dispatch(source)
    assert baseline == (EXPECTED_DISPATCH, "between_subjects"), baseline

    mutants = {
        "默认分支改成 within": source.replace(
            '.get("design_type", "between_subjects")', '.get("design_type", "within_subjects")'
        ),
        "questionnaire 别名被摘掉": source.replace('"survey", "questionnaire"', '"survey"'),
        "回退目标换成 survey": source.replace("return _gen_generic(", "return _gen_survey("),
    }
    for name, text in mutants.items():
        assert text != source, f"变异模板失效：{name}"
        assert _extract_dispatch(text) != baseline, f"{name} 未被发现 ⇒ 判据太松"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([str(Path(__file__).relative_to(REPO)), "-q"]))
