# -*- coding: utf-8 -*-
r"""script_generator 题名转义（台账 #69 案 A）：两上下文分别转义的行为钉桩＋敌对输入实测。

**锚点（开工实测，HEAD 03c5626）**：`src/experiment_design/script_generator.py` 里
`{title}` 的裸插值写点共 **10 处**（改前 `grep -n "{title}"` 读数），分属四类上下文：

| 上下文 | 写点（改前行号） | 危险序列 | 转义函数 |
|---|---|---|---|
| HTML 文本／RCDATA | `<title>` :103 / :345 / :532 | `<` `>` `&` | `escape_html_text` |
| JS 字符串（双引号） | `title: "…"` :130 / :364 / :551 | `"` `\` 换行 以及 **`</script`** | `escape_js_string` |
| JS 模板字符串里的 HTML | `<h2>…</h2>` :163 / :391 / :561 | 上述全部 ＋ `` ` `` `${` | `escape_html_in_js`（先 HTML 后 JS） |
| HTML 注释 | generic 桩 :644 | `-->` `--!>` `<!--` | `escape_html_comment` |

**为什么两上下文的规则不能合一**（M2 变异把这条钉成可翻红的判据）：
JS 上下文里的 `</script` 由 **HTML 分词器**先看见、不看 JS 语法 ⇒ `<` 必须换成 `\u003c`
这类 Unicode 转义；而 HTML 实体转义**完全不碰** `` ` `` 与 `${`，拿它顶替 JS 转义
＝把题名变成活的模板插值、把模板字符串提前闭合。

零网络、零 Streamlit。敌对题名产物只在内存里拼装；node 验收用的临时 `.js`
只落 `tmp/20260924-0045-pd01/node_check/`（沙盒），**不写 `data/`、不写任何真实项目产物目录**。
"""
from __future__ import annotations

import html as html_mod
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GEN_SRC = REPO / "src" / "experiment_design" / "script_generator.py"
SANDBOX = REPO / "tmp" / "20260924-0045-pd01" / "node_check"

from src.experiment_design.script_generator import (  # noqa: E402
    escape_html_comment,
    escape_html_in_js,
    escape_html_text,
    escape_js_string,
    generate_jspsych_script,
)

NODE = shutil.which("node")

# ── 敌对题名：' " < > </script> \ 反引号 ${} 换行/制表/U+2028/U+2029 注释终止符 ──
PROBES: dict[str, str] = {
    "script_breakout": 'A": alert(1); //</script><script>alert(document.cookie)</script>',
    "quote_and_tag": "B'><img src=x onerror='alert(1)>",
    "backtick_interp": 'C\\backslash"quote\'${7*7}`tick`',
    "comment_terminator": "D<!-- x --><svg/onload=alert(1)>--!>",
    "line_terminators": "E\nnl\ttab\u2028ls\u2029ps\r",
}

FULL_PAGES = {
    "survey": {"design_type": "survey"},
    "questionnaire": {"design_type": "questionnaire"},
    "between_subjects": {"design_type": "between_subjects"},
    "within_subjects": {"design_type": "within_subjects"},
}


def _gen(design_type: str, title: str):
    design = {"id": "esc", "name": "转义回归", "design_type": design_type}
    return generate_jspsych_script(design, conditions=["A", "B"], experiment_title=title)


# ────────────────────────────── 解析侧小工具（判据用，不执行 JS）

def _inline_js(page: str) -> str:
    blocks = re.findall(r"<script>(.*?)</script>", page, re.S)
    assert len(blocks) == 1, f"内联脚本块数量={len(blocks)}（题名把 <script> 结构打坏了）"
    return blocks[0]


_JS_UNESCAPE_MAP = {
    "n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0",
    "\\": "\\", '"': '"', "'": "'", "`": "`", "$": "$", "/": "/",
}


def _js_unescape(s: str) -> str:
    """按 JS 字符串字面量的转义规则还原（判据：转义可逆、且**没有过度转义**）。"""
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "\\" or i + 1 >= len(s):
            out.append(ch)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt == "u":
            assert re.fullmatch(r"[0-9a-fA-F]{4}", s[i + 2:i + 6]), f"非法 \\u 转义：{s[i:i + 8]!r}"
            out.append(chr(int(s[i + 2:i + 6], 16)))
            i += 6
            continue
        out.append(_JS_UNESCAPE_MAP.get(nxt, nxt))
        i += 2
    return "".join(out)


def _js_double_quoted(page: str, key: str) -> str:
    """取 `key: "…"` 的字面量原文，**转义感知**：`\\"` 不算闭合。"""
    m = re.search(rf'{key}: "((?:[^"\\\n]|\\.)*)"', page)
    assert m, f"未找到 {key} 的完整双引号字面量 ⇒ 串被题名提前闭合"
    return m.group(1)


def _h2_template_literal(js: str) -> str:
    m = re.search(r"<h2>(.*?)</h2>", js, re.S)
    assert m, "未找到欢迎页 <h2> 片段"
    return m.group(1)


def assert_title_safely_embedded(page: str, title: str) -> None:
    """**核心判据**（改前必红、改后必绿；M1／M2 变异也必须红）：

    ① 题名不得以裸串出现在内联脚本里；② `<script`／`</script` 数量仍配平（无提前终结）；
    ③ `<title>` 元素内无裸 `<` `>`，且实体解码**恰好**还原题名（防过度转义）；
    ④ JS 双引号字面量可转义感知取出、解码链 JS→HTML 后**恰好**等于题名；
    ⑤ 模板字符串里的 `<h2>` 片段同上，且不得残留活的 `${` 插值（这条专杀少了 JS 层的「合一写法」）。
    """
    js = _inline_js(page)
    assert title not in js, f"题名裸串仍在内联脚本里 ⇒ 未转义：{title!r}"
    assert page.count("<script") == page.count("</script"), (
        page.count("<script"), page.count("</script"), "script 标签配平被打破"
    )

    m = re.search(r"<title>(.*?)</title>", page, re.S)
    assert m, "缺 <title> 元素"
    head = m.group(1)
    assert "<" not in head and ">" not in head, f"<title> 内仍有裸标签字符：{head!r}"
    assert html_mod.unescape(head) == title, f"<title> 往返不等：{html_mod.unescape(head)!r} != {title!r}"

    assert html_mod.unescape(_js_unescape(_js_double_quoted(page, "title"))) == title, (
        f"EXPERIMENT_CONFIG.title 往返不等（{title!r}）⇒ 转义漏字符或过度转义"
    )
    h2 = _h2_template_literal(js)
    assert "${" not in h2.replace("\\${", ""), f"模板字符串里残留活的插值：{h2!r}"
    assert html_mod.unescape(_js_unescape(h2)) == title, (
        f"模板字符串 <h2> 往返不等（{title!r}）⇒ 混合上下文漏了一层转义"
    )


def _exec_variant(source_text: str, modname: str) -> dict:
    """在**真包上下文**里 exec 一份源码文本（`_gen_within_subjects` 有相对 import）。

    ⚠️ 必须挂一个真 `ModuleType` 进 `sys.modules`：`@dataclass` 会去
    `sys.modules[cls.__module__].__dict__` 取全局表，挂了裸 dict 就
    `AttributeError: 'dict' object has no attribute '__dict__'`（本文件第一版撞在这里）。
    """
    fqname = f"src.experiment_design.{modname}"
    mod = types.ModuleType(fqname)
    mod.__package__ = "src.experiment_design"
    mod.__file__ = str(GEN_SRC)
    sys.modules[fqname] = mod
    try:
        exec(compile(source_text, f"<{modname}>", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(fqname, None)
    return mod.__dict__


def _node_check(js: str, name: str) -> subprocess.CompletedProcess:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    f = SANDBOX / f"{name}.js"
    f.write_text(js, encoding="utf-8")
    return subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True, encoding="utf-8")


# ══════════════════════════════════════════ 1. 两上下文各自的规则（单元级）


def test_js_context_escapes_delimiters_and_not_entities():
    r"""上下文 1（JS 字符串）：转义定界符/转义符/插值，并把 `<` 变成 \u003c；**不碰 &**。"""
    assert escape_js_string('a"b') == 'a\\"b'
    assert escape_js_string("a'b") == "a\\'b"
    assert escape_js_string("a`b") == "a\\`b"
    assert escape_js_string("a${b}c") == "a\\${b}c"
    assert escape_js_string("a\\b") == "a\\\\b"
    assert escape_js_string("</script>") == "\\u003c/script\\u003e"
    assert escape_js_string("\n\t\r") == "\\n\\t\\r"
    assert escape_js_string("\u2028") == "\\u2028"
    assert escape_js_string("\u2029") == "\\u2029"
    assert escape_js_string("x & y") == "x & y", "JS 上下文不该做实体转义（& 不是 JS 定界符）"


def test_html_context_escapes_entities_and_ampersand_first():
    """上下文 2（HTML 文本）：& 必须最先，否则 &lt; 会被二次转成 &amp;lt;。"""
    assert escape_html_text("<b>") == "&lt;b&gt;"
    assert escape_html_text("\"'") == "&quot;&#39;"
    assert escape_html_text("&") == "&amp;"
    assert escape_html_text("&lt;") == "&amp;lt;", "& 未最先转 ⇒ 实体会被吞并"
    assert escape_html_text("a\\b") == "a\\b", "HTML 上下文不该转义反斜杠"
    assert escape_html_text("a`b${c}") == "a`b${c}", "HTML 上下文不碰 JS 插值 ⇒ 两层不能互相顶替"


def test_two_contexts_are_not_interchangeable():
    """「合一写法必错」的正面否证：同一条敌对题名在两个上下文里的正确产物不同。"""
    hostile = PROBES["script_breakout"]
    js_out, html_out = escape_js_string(hostile), escape_html_text(hostile)
    assert js_out != html_out
    assert '\\"' in js_out and "&quot;" not in js_out, "JS 侧必须产出反斜杠转义而非实体"
    assert "&quot;" in html_out and '\\"' not in html_out, "HTML 侧必须产出实体而非反斜杠"
    assert "\\u003c" in js_out and "&lt;" in html_out
    # 用 HTML 转义顶替 JS 转义 ⇒ 反引号与 ${ 活着 ⇒ 模板字符串可被破（M2 变异负责翻红）
    assert "`" in escape_html_text(PROBES["backtick_interp"])
    assert "${7*7}" in escape_html_text(PROBES["backtick_interp"])
    js_tick = escape_js_string(PROBES["backtick_interp"])
    assert "`" not in js_tick.replace("\\`", ""), f"仍有未转义反引号：{js_tick!r}"
    assert "${" not in js_tick.replace("\\${", ""), f"仍有未转义插值：{js_tick!r}"


def test_html_comment_context_only_kills_terminators():
    """上下文 3（HTML 注释）：`-->`／`<!--` 是唯一破出，转义后体内不再有 `<` `>`。"""
    escaped = escape_html_comment(PROBES["comment_terminator"])
    assert "<" not in escaped and ">" not in escaped
    assert "-->" not in escaped and "--!>" not in escaped
    assert html_mod.unescape(escaped) == PROBES["comment_terminator"], "注释转义须可逆"


def test_mixed_context_orders_html_then_js():
    r"""先 HTML 后 JS：反序会得到 `\&quot;`（JS 失去转义语义）⇒ 顺序本身要被钉住。"""
    src = 'a"b`c${d}\\e<f>'
    out = escape_html_in_js(src)
    assert out == 'a&quot;b\\`c\\${d}\\\\e&lt;f&gt;', out
    assert html_mod.unescape(_js_unescape(out)) == src
    assert escape_js_string(escape_html_text(src)) == out, "混合上下文＝escape_html_in_js 的定义序"


# ══════════════════════════════════════════ 2. 端到端：敌对题名 × 四个整页分支


@pytest.mark.parametrize("branch", list(FULL_PAGES))
@pytest.mark.parametrize("label", list(PROBES))
def test_hostile_title_stays_inside_all_contexts(branch, label):
    """完成标准 2：5 条敌对题名 × 4 个整页分支 = 20 组，核心判据全过。"""
    title = PROBES[label]
    assert_title_safely_embedded(_gen(branch, title).html_content, title)


@pytest.mark.parametrize("label", list(PROBES))
def test_generated_inline_script_still_parses_by_node(label):
    """完成标准 2「产物仍须是合法可解析脚本」：拿 node 的 JS 解析器验收，不是自说自话。"""
    if NODE is None:
        pytest.skip("本机无 node，跳过外部解析器验收（纯 Python 判据见上一条）")
    title = PROBES[label]
    for branch in FULL_PAGES:
        js = _inline_js(_gen(branch, title).html_content)
        r = _node_check(js, f"{branch}_{label}")
        assert r.returncode == 0, f"{branch}×{label} 产物不可解析：{r.stderr[:400]}"


def test_ordinary_title_is_untouched_byte_for_byte():
    """零回归面：中文／字母／空格题名不加任何转义（否则既有断言会全线漂红）。"""
    for plain in ("心理学实验", "问卷实验", "Stroop 效应 研究", "A/B 设计"):
        assert escape_js_string(plain) == plain
        assert escape_html_text(plain) == plain
        assert escape_html_comment(plain) == plain
        assert f'"{plain}"' in _gen("survey", plain).html_content


def test_plain_title_products_are_identical_to_pre_change():
    """既有产物形状不变：默认标题下 <title>／EXPERIMENT_CONFIG.title／<h2> 与改前一致。"""
    page = _gen("survey", "心理学实验").html_content
    assert "<title>心理学实验</title>" in page
    assert 'title: "心理学实验",' in page
    assert "<h2>心理学实验</h2>" in page


# ══════════════════════════════════════════ 3. generic 桩（注释上下文）


@pytest.mark.parametrize("label", list(PROBES))
def test_generic_stub_comment_cannot_be_closed_early(label):
    """`_gen_generic` 的 :644 写点在 HTML 注释里 ⇒ 题名带的 `-->` 不得成为真终止符。"""
    title = PROBES[label]
    stub = _gen("unsupported_type", title).html_content
    prefix = "<!-- jsPsych script for "
    suffix = " -->\n<!-- Generic template - please customize -->"
    assert stub.startswith(prefix) and stub.endswith(suffix), stub
    body = stub[len(prefix): len(stub) - len(suffix)]
    assert "-->" not in body and "--!>" not in body and "<!--" not in body, f"注释体内有活终止符：{body!r}"
    assert "<" not in body and ">" not in body
    assert html_mod.unescape(body) == title, f"注释转义须可逆（不得吞题名字符）：{body!r}"


# ══════════════════════════════════════════ 4. 判别力自证（本套件不是空转）


def test_teeth_M1_identity_escape_is_caught():
    """变异 M1：把 10 处写点的转义函数全换成恒等（＝改前实现）⇒ 核心判据必须红。"""
    source = GEN_SRC.read_text(encoding="utf-8")
    mutated = source
    for call in ("escape_js_string(title)", "escape_html_text(title)",
                 "escape_html_in_js(title)", "escape_html_comment(title)"):
        assert call in mutated, f"写点模板失效：{call}"
        mutated = mutated.replace(call, "_raw(title)")
    assert mutated.count("_raw(title)") == 10, mutated.count("_raw(title)")
    ns = _exec_variant(mutated, "_m1_identity")
    ns["_raw"] = lambda v: v
    page = ns["generate_jspsych_script"](
        {"id": "m", "name": "n", "design_type": "survey"}, experiment_title=PROBES["script_breakout"]
    ).html_content
    with pytest.raises(AssertionError) as exc:
        assert_title_safely_embedded(page, PROBES["script_breakout"])
    msg = str(exc.value)
    assert any(k in msg for k in ("题名裸串", "配平", "内联脚本块数量", "提前闭合")), msg


def test_teeth_M2_merged_escaping_is_caught():
    """变异 M2（「合一写法」）：JS 模板上下文改用 HTML 实体转义 ⇒ 必须红。

    这就是两上下文规则不同的机读证据：HTML 转义不碰反引号，模板字符串被破出。
    """
    source = GEN_SRC.read_text(encoding="utf-8")
    mutated = source.replace("escape_html_in_js(title)", "escape_html_text(title)")
    assert mutated != source
    ns = _exec_variant(mutated, "_m2_merged")
    page = ns["generate_jspsych_script"](
        {"id": "m", "name": "n", "design_type": "survey"}, experiment_title=PROBES["backtick_interp"]
    ).html_content
    with pytest.raises(AssertionError):
        assert_title_safely_embedded(page, PROBES["backtick_interp"])
    # 同一份变异产物交给 node：反引号破出后连脚本都解析不了（外部解析器独立佐证）
    if NODE is not None:
        r = _node_check(_inline_js(page), "m2_merged")
        assert r.returncode != 0, "M2 变异居然还能解析 ⇒ 判据或 node 校验收了空"


def test_teeth_escaped_page_is_not_over_escaped():
    """反向判别：不许用「把题名丢掉／截断」来蒙过往返判据。"""
    page = _gen("survey", PROBES["quote_and_tag"]).html_content
    js = _inline_js(page)
    assert "B&#39;" in js and "img" in js, "题名内容被吃掉了（转义≠丢弃）"
    # survey 分支把题名写进 2 个脚本内上下文（EXPERIMENT_CONFIG.title ＋ 指导语 <h2>），一处都不能少
    assert js.count("onerror") == 2, js.count("onerror")
    assert js.count("\\u003cimg") == 1 and js.count("&lt;img") == 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([str(Path(__file__).relative_to(REPO)), "-q"]))
