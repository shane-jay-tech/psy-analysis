# -*- coding: utf-8 -*-
"""s1004-26：script_generator 五处未转义写点收口（pd01 遗留）——敌对样例＋node 解析门。

覆盖写点（改前行号）：:171（被试间 conditions 数组）、:406-410/:444（拉丁方
counterbalanceOrders）、:413（被试内 conditions 数组）、:740（likert 题目文本）、
:749（指导语文本，原只转 " 与换行）——全部并轨 pd01 的 escape_js_string
（_JS_STRING_SUBS，\\ 最先）。

⚠ 接线警示：generate_jspsych_script 在仓内**零生产调用方**（rg 复核在案，
2026-10-05 实测仅本测试件与定义体）——接线 UI/导出面时必须复用本转义函数族，
禁止另写一套（pd01 原判）。

node 验收用临时 .js 只落 tmp/ 沙盒（沿 pd01 惯例），不写 data/ 或真实产物目录。
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.experiment_design.script_generator import (
    convert_instructions_to_jspsych,
    convert_items_to_jspsych_likert,
    escape_js_string,
    generate_jspsych_script,
)

NODE = shutil.which("node")
SANDBOX = Path(__file__).resolve().parents[1] / "tmp" / "s1004_26_node_check"

# 敌对条件名/题目文本：引号、反斜杠、反引号、${}、</script>
HOSTILE = 'A"; alert(1); //</script><script>alert(1)</script>'
HOSTILE_BACKTICK = "B`tick`${7*7}\\path"


def _inline_js(page: str) -> str:
    blocks = re.findall(r"<script>(.*?)</script>", page, re.S)
    assert blocks, "内联脚本块被打坏"
    return "\n".join(blocks)


def _node_check(js: str):
    if not NODE:
        pytest.skip("node 不在场")
    SANDBOX.mkdir(parents=True, exist_ok=True)
    f = SANDBOX / "check.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, f"node --check 解析失败：{r.stderr[:300]}"


def test_between_subjects_hostile_condition_escaped():
    """:171 写点——敌对条件名经 escape_js_string，原始串不得裸出现在 name: "..." 内。"""
    out = generate_jspsych_script(
        {"id": "e26", "name": "转义", "design_type": "between_subjects"},
        conditions=[HOSTILE, "B"],
    )
    js = out.js_content or _inline_js(out.html_content)
    assert HOSTILE not in js  # 原始敌对串不得裸插
    assert 'name: "A\\"; alert(1)' not in js or '\\"' in js  # 引号已转义形态在册


def test_within_subjects_hostile_condition_and_orders_escaped():
    """:413 + :406-410 写点——被试内 conditions 与拉丁方 counterbalanceOrders 同防。"""
    out = generate_jspsych_script(
        {"id": "e26w", "name": "转义", "design_type": "within_subjects"},
        conditions=[HOSTILE_BACKTICK, "B"],
    )
    js = out.js_content or _inline_js(out.html_content)
    assert HOSTILE_BACKTICK not in js  # 原始串（含反引号/${）不得裸插
    assert "\\`" in js and "\\${" in js  # 反引号与 ${ 已转义形态在册


def test_likert_item_text_escaped():
    """:740 写点——题目文本敌对注入不得破坏 prompt: "..." 结构。"""
    items = [{"text": '题干"; alert(1); "`${x}`\\', "index": 1}]
    out = convert_items_to_jspsych_likert(items)
    assert '`alert(1)`' not in out.replace("\\`", "")  # 原始反引号不得裸插
    assert '\\"' in out  # 引号转义在册


def test_instructions_full_charset_escape():
    """:749 写点——原只转 " 与换行；现走 _JS_STRING_SUBS 全族（含 \\ 最先、反引号/${/<）。"""
    out = convert_instructions_to_jspsych([{"text": 'a"b\\c`d${e}<f>\ng'}])
    assert '`d${e}' not in out.replace("\\`", "").replace("\\${", "")  # 原始反引号/${ 不得裸插
    assert "\\u003c" in out  # < 已按 JS 上下文 Unicode 转义（断 </script> 破出）


def test_backslash_escapes_first_order():
    """转义顺序断言（\\ 最先）：字面 反斜杠+n 不得被二次解释成换行序列。"""
    value = "x" + chr(92) + "ny"  # x \ n y（反斜杠为真字符）
    out = escape_js_string(value)
    assert out == "x" + chr(92) * 2 + "ny"  # \ → \\ 且 n 保持字面
    assert chr(10) not in out  # 无真实换行引入


def test_generated_script_passes_node_parse():
    """解析门：敌对条件名/题目/指导语产物整体过 node --check（node 在场时）。"""
    out = generate_jspsych_script(
        {"id": "e26n", "name": "转义", "design_type": "within_subjects"},
        conditions=[HOSTILE, HOSTILE_BACKTICK],
    )
    js = out.js_content or _inline_js(out.html_content)
    _node_check(js)
    _node_check(convert_items_to_jspsych_likert(
        [{"text": HOSTILE, "index": 1}]).strip().rstrip(";"))
    _node_check(convert_instructions_to_jspsych([{"text": HOSTILE_BACKTICK}]))
