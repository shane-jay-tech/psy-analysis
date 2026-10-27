"""skip/skipif 门禁体检 — 「每条 skip 有可解释理由」＋「门禁不得因环境误判跳过本应运行的质量测试」。

对应信箱单 20260925-120710-6784：
「检查 pytest skipif 不因环境误判而跳过本应运行的质量测试。
 验收：每条 skip 有可解释理由；关键质量测试在目标环境实际运行。」

四条机械判据（都可复算，不靠人读文档）：

1. `test_every_skip_or_xfail_gate_carries_a_non_empty_reason`
   —— 扫 `tests/*.py` 的 AST，任何 skipif / xfail / mark.skip / importorskip / pytest.skip
   都必须带非空 `reason`。无因 skip 当场红。
2. `test_capability_gate_*_agrees_with_independent_probe`
   —— 每个「能力型」门禁的判定值，与一个**独立探针**（子进程真 import／真渲染／真跑 node）对账。
   只有"门禁说缺、独立探针证明能用"这个方向才是本单要抓的**环境误判**（= 白跳掉质量测试）；
   反方向（门禁说能用、实际跑不了）会红不会跳，属另一种病，不在此钉。
3. `test_structure_based_gates_point_at_paths_that_exist`
   —— 条件是"仓库里某个文件在不在"的 skipif 本质不是环境判据：文件被改名/删除时
   它会把回归变成静默 skip（"绿但零覆盖"）。本条把它转成**当场红**。
4. `test_benchmark_gate_covers_only_the_heavy_tests`
   ＋ `test_no_file_level_benchmark_pytestmark_anywhere`
   —— `conftest` 的 `--run-benchmark` 门禁按"用例有没有 benchmark 标记"起作用，
   一旦标记开在**文件级** `pytestmark` 上，整件（含不碰 key、不联网的纯本地用例）会被一起挡掉。
   两条合起来把"作用域只准盖住重测试"钉成机械判据：文件级标记直接红，
   逐例标记但盖错对象的，按"被白挡的离线用例数"跳数报红。
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- #
# 共用工具
# --------------------------------------------------------------------------- #

def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _has_reason(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "reason":
            val = kw.value
            if isinstance(val, ast.Constant):
                return bool(str(val.value).strip())
            return True  # f-string / 变量拼接：非空即算带因（内容由人核）
    name = _dotted(call.func)
    if name in ("pytest.skip", "pytest.xfail"):
        return bool(call.args)
    if name == "pytest.importorskip":
        return len(call.args) >= 2
    return False


def _is_gate_call(call: ast.Call) -> bool:
    name = _dotted(call.func)
    return "skipif" in name or "xfail" in name or name.endswith("mark.skip")


def _iter_gate_sites():
    """AST 轨普查：(相对件名, 行号, 类型, ast.Call|None)。含 pytestmark 里嵌的 skipif。"""
    for path in sorted(TESTS.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:  # 解析不了的件不该存在于 tests/，交给收集期报
            continue
        for node in ast.walk(tree):
            for d in getattr(node, "decorator_list", []):
                if isinstance(d, ast.Call) and _is_gate_call(d):
                    yield path.name, d.lineno, "decorator", d
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
            ):
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Call) and _is_gate_call(sub):
                        yield path.name, sub.lineno, "pytestmark", sub
                    elif isinstance(sub, ast.Attribute) and _dotted(sub).endswith("mark.skip"):
                        yield path.name, sub.lineno, "pytestmark-bare", None
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                name = _dotted(node.value.func)
                if name in ("pytest.skip", "pytest.importorskip", "pytest.xfail"):
                    yield path.name, node.lineno, "call:" + name, node.value


def _subprocess_imports(module: str) -> bool:
    """独立探针：换个进程真 import 一次（不受本进程 sys.modules 污染）。"""
    r = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True, text=True, encoding="utf-8",
    )
    return r.returncode == 0


# --------------------------------------------------------------------------- #
# 1. 每条 skip 都要有可解释理由
# --------------------------------------------------------------------------- #

def test_every_skip_or_xfail_gate_carries_a_non_empty_reason():
    sites = list(_iter_gate_sites())
    py_files = len(list(TESTS.glob("*.py")))
    assert sites, f"扫了 {py_files} 份件却一个门禁都没找到 ⇒ 普查器本身坏了"
    offenders = [
        f"{name}:{line} [{kind}]"
        for name, line, kind, call in sites
        if call is None or not _has_reason(call)
    ]
    assert not offenders, (
        f"{py_files} 份测试件里共 {len(sites)} 处 skip/xfail 门禁，"
        f"其中 {len(offenders)} 处没有非空 reason ⇒ 无法解释的跳过：{offenders}"
    )


# --------------------------------------------------------------------------- #
# 2. 能力型门禁 × 独立探针对账（环境误判哨兵）
# --------------------------------------------------------------------------- #

def _kaleido_gate_says_missing():
    mod = importlib.import_module("tests.test_docx_export")
    return mod._kaleido_installed() is False


def _kaleido_can_actually_render():
    from src.visualization.paper_export import to_paper_png
    import plotly.graph_objects as go

    try:
        png = to_paper_png(
            go.Figure(go.Bar(x=["A", "B"], y=[1.0, 2.0])),
            palette="grayscale", width_px=400, height_px=300,
        )
    except Exception:
        return False
    return isinstance(png, bytes) and png[:8] == b"\x89PNG\r\n\x1a\n"


def _playwright_gate_says_missing():
    mod = importlib.import_module("tests.test_e2e_v52_paths")
    return mod._playwright_available() is False


def _node_gate_says_missing():
    mod = importlib.import_module("tests.test_script_generator_title_escaping")
    return mod.NODE is None


def _node_can_actually_run():
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True)
    except OSError:
        return False
    return r.returncode == 0


def _cjk_gate_says_missing():
    mod = importlib.import_module("tests.test_questionnaire_export_pdf_positive")
    return mod._HAS_CJK_FONT is False


def _cjk_font_file_is_usable():
    from src.visualization.fonts import find_chinese_font

    p = find_chinese_font()
    return bool(p) and os.path.isfile(p) and os.path.getsize(p) > 1024


def _pillow_gate_says_missing():
    """`test_docx_export.small_png_bytes` 里的 `try: from PIL import Image` 分支。"""
    return importlib.util.find_spec("PIL") is None


CAPABILITY_GATES = [
    ("kaleido 渲染", _kaleido_gate_says_missing, _kaleido_can_actually_render, "kaleido"),
    ("playwright", _playwright_gate_says_missing,
     lambda: _subprocess_imports("playwright"), "playwright"),
    ("node 解析器", _node_gate_says_missing, _node_can_actually_run, "node"),
    ("中文字体", _cjk_gate_says_missing, _cjk_font_file_is_usable, "cjk_font"),
    ("Pillow", _pillow_gate_says_missing, lambda: _subprocess_imports("PIL"), "pillow"),
]


@pytest.mark.parametrize(
    "label,gate_says_missing,capability_available",
    [(a, b, c) for a, b, c, _ in CAPABILITY_GATES],
    ids=[d for _, _, _, d in CAPABILITY_GATES],
)
def test_capability_gate_agrees_with_independent_probe(label, gate_says_missing,
                                                      capability_available):
    """环境误判定义：门禁判"依赖不可用"，而独立探针实测该能力可用 ⇒ 白跳一批质量测试。"""
    missing = gate_says_missing()
    works = capability_available()
    assert not (missing and works), (
        f"{label}：门禁判『不可用』所以会 skip 相关用例，"
        f"但独立探针实测『可用』⇒ 属环境误判，该用例本应在目标环境运行。"
        f"请改门禁判据（别放宽成恒不跳）。"
    )
    if not missing and label == "kaleido 渲染":
        assert works, (
            "kaleido 门禁说可用、真渲染却失败 ⇒ 门禁与能力脱节（CI 形态），"
            "见 docs/insights/psy-skipif-reality-20260924.md §二.3"
        )


# --------------------------------------------------------------------------- #
# 3. 结构型 skipif：判据写的是"仓库里有没有这个文件"
# --------------------------------------------------------------------------- #

def _structure_gate_targets():
    out = []
    for name, line, kind, call in _iter_gate_sites():
        if call is None or not call.args:
            continue
        src = ast.unparse(call.args[0])
        if ".exists()" not in src:
            continue
        for node in ast.walk(call.args[0]):
            if isinstance(node, ast.Call) and _dotted(node.func).endswith("joinpath") and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    out.append((name, line, src, arg.value))
    return out


def test_structure_based_gates_point_at_paths_that_exist():
    """结构型 skipif 命中路径必须存在——文件被改名时它会把回归变成静默 skip。"""
    targets = _structure_gate_targets()
    py_files = len(list(TESTS.glob("*.py")))
    if not targets:
        # s1028-06 翻正：全仓 exists() 型结构门禁已绝迹（14 份 skipif 件全部改判据/
        # importorskip，grep exists() 0 命中实测）——空普查＝健康态（没有"文件在不在"
        # 型跳过判据，就不存在改名导致静默 skip 的面）。若未来重新引入，恢复逐路径核查。
        pytest.skip(f"现役 {py_files} 份测试件无 exists() 型结构门禁＝普查为空属健康态")
    missing = [
        f"{name}:{line} -> {rel}"
        for name, line, _src, rel in targets
        if not (REPO / Path(rel)).exists()
    ]
    assert not missing, (
        "以下 skipif 用『仓库文件在不在』当跳过判据，而该文件现已不在仓库里 ⇒ "
        f"对应用例会静默 skip：{missing}"
    )


# --------------------------------------------------------------------------- #
# 4. benchmark 门控的作用域：按"标记真正盖住哪些用例"计账
# --------------------------------------------------------------------------- #

#: 被 benchmark 门住、却**不需要** LLM key／网络的用例数（＝作用域开错的债）。
#: 现值 1 = `test_socratic_quality.py::test_socratic_quality_replay_offline`
#: （自带函数级标记，但内部 `monkeypatch.delenv(BENCHMARK_LLM_API_KEY)` 且断言真实调用数为 0，
#:  属"离线可跑却被基准门禁挡着"的残留；是否放它进默认跑法要由基准班确认，故保留在册）。
#: 历史上这个数是 **23**（两件都挂文件级 `pytestmark` ⇒ 24 例一起被门住），
#: 由信箱单 20260925-120712-d507 摘除文件级标记、改逐例标记后降到 1。
BENCHMARK_GATED_KEY_FREE_ITEMS = 1


def _benchmark_gated_tests(path: Path) -> list[str]:
    """返回被 benchmark 门禁盖住的用例名（模块级／类级／函数级任一标记即算）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def marked(node) -> bool:
        return any("benchmark" in ast.unparse(d) for d in node.decorator_list)

    module_level = any(
        isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets)
        and "benchmark" in ast.unparse(n.value)
        for n in tree.body
    )
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_") and (module_level or marked(node)):
                out.append(node.name)
        elif isinstance(node, ast.ClassDef):
            class_level = marked(node)
            for sub in node.body:
                if (isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and sub.name.startswith("test_")
                        and (module_level or class_level or marked(sub))):
                    out.append(f"{node.name}::{sub.name}")
    return out


def _gated_tests_needing_key(path: Path) -> list[str]:
    """门禁盖住的用例里，函数体真的读 BENCHMARK_LLM_API_KEY 的那些。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    gated = {n.split("::")[-1] for n in _benchmark_gated_tests(path)}
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in gated:
            body = ast.unparse(n)
            if "BENCHMARK_LLM_API_KEY" in body and "delenv" not in body:
                hits.append(n.name)
    return hits


def test_benchmark_gate_covers_only_the_heavy_tests():
    """验收「benchmark 只包住重测试，不把整套质量测试模块静默跳过」。

    机械口径：门禁盖住的用例数 － 真需 LLM key 的用例数 ＝ 被白挡的离线用例数。
    该差值必须等于在册常量（现值 1，来历见常量注释）。
    退回文件级 `pytestmark` ⇒ 差值当场跳回两位数；继续乱加函数级标记 ⇒ 同样跳。
    """
    gated_files = ["test_socratic_quality.py", "test_socratic_benchmark.py"]
    gated = {f: _benchmark_gated_tests(TESTS / f) for f in gated_files}
    total_gated = sum(len(v) for v in gated.values())
    needs_key = sum(len(_gated_tests_needing_key(TESTS / f)) for f in gated_files)
    key_free = total_gated - needs_key
    assert key_free == BENCHMARK_GATED_KEY_FREE_ITEMS, (
        f"benchmark 门禁现盖住 {total_gated} 例、其中真需 key {needs_key} 例 ⇒ "
        f"被白挡的离线用例 {key_free} 例 ≠ 在册 {BENCHMARK_GATED_KEY_FREE_ITEMS}。"
        f"逐件明细：{gated}。若你收窄／扩大了标记作用域，请同步本常量，"
        "并重取 docs/TESTING.md 的在册 passed/skipped 数。"
    )


def test_no_file_level_benchmark_pytestmark_anywhere():
    """文件级 benchmark 标记＝"整套模块静默跳过"的载体，禁止复活。"""
    offenders = []
    for path in sorted(TESTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for n in getattr(tree, "body", []):
            if (isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets)
                    and "benchmark" in ast.unparse(n.value)):
                offenders.append(f"{path.name}:{n.lineno}")
    assert not offenders, (
        f"出现文件级 benchmark 标记 ⇒ 该件所有用例会被 --run-benchmark 门连带挡掉："
        f"{offenders}。请逐例挂 @pytest.mark.benchmark。"
    )

