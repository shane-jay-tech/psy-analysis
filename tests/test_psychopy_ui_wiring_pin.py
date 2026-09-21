"""src/experiment_design/psychopy_generator.py 的 UI 接线面钉桩（s922-123）。

现状（psy-psychopy-reforder §六，本单实测复核）：`generate_psychopy_script` 只在
`src/experiment_design/__init__.py:32` 那个 import 块里被 re-export，`src/ui/**` 全部 40 个文件
加 `app.py` 对四个公开符号的引用点 **为 0**。**接线属日间决策**（要不要在 UI 里挂 PsychoPy 生成入口
是产品判断），本测试防止"无人知晓的半接线中间态"——谁在 UI 里 import 了这些符号而没走评审，这里当场红。

实现口径：
1. 接线面用 **ast 遍历现取**（`src/ui/**/*.py` + `app.py`），不是手抄文件清单；
2. 判据是**符号引用**（import 绑定名 / Name / Attribute / getattr 字面量 / 星号导入）而不是文本命中——
   `src/upstream/feasibility_check.py:169`、`:234`、`src/upstream/topic_funnel_kb.py:315` 三处含
   "PsychoPy" 字样（给用户看的文案），naive `grep -i psychopy` 会把它们算成接线（实测 3 假阳），
   ast 扫描这三处为 0 命中；
3. 判别力自证用**注入法**（`test_scanner_reports_every_injected_wiring_form`）＋**真实正对照**
   （`__init__.py` 的 re-export 必被扫出 4 条），保证扫描器不是空转返回 0。

🔴 派单前提否证（按实况收窄，未改任何 src/）：任务书写「6 范式×feedback」，实测
`generate_standard_paradigm` 的 `paradigm_configs` **只有 4 项**（stroop/flanker/emotion/memory，
见 `psychopy_generator.py:92-142`），传 'custom' 或未知串直接 `ValueError`（`:145-148`）。
12 形态＝6 个范式串 × 2 组 feedback 只能走 `PsychoPyExperiment` 直接构造（与本仓 s920-01 那两条
12 形态用例同路），本件照此实现并另立一条用例把「工厂只认 4 范式」钉住。
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: psychopy_generator 对外公开的四个符号（__init__ re-export 面）
PSYCHOPY_SYMBOLS = frozenset({
    "generate_psychopy_script",
    "PsychoPyExperiment",
    "generate_standard_paradigm",
    "generate_latin_square_psychopy",
})

#: 生成器模块本身与包 re-export 处——这两处是"定义/导出点"，不是"接线消费点"
OWNER_MODULE_PATH = "src/experiment_design/psychopy_generator.py"
REEXPORT_PATH = "src/experiment_design/__init__.py"


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:  # pragma: no cover - 只在 tmp_path 夹具下走到
        return path.as_posix()


def iter_wiring_surface_files() -> list[Path]:
    """接线面 = src/ui 下（含子目录）所有 .py ＋ 入口 app.py，现取不手抄。"""
    files = sorted((REPO_ROOT / "src" / "ui").rglob("*.py"))
    entry = REPO_ROOT / "app.py"
    assert entry.is_file(), "入口 app.py 不见了，接线面少一条腿"
    return files + [entry]


def classify(node: ast.AST, file_label: str) -> list[dict]:
    """单个 AST 节点 → 接线点列表（import 绑定 / Name / Attribute / getattr 字面量 / 星号导入）。"""
    lineno = getattr(node, "lineno", 0)          # Module 等容器节点没有 lineno
    where = {"file": file_label, "lineno": lineno}
    hits: list[dict] = []
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*" and (
                module.endswith("experiment_design") or "psychopy_generator" in module
            ):
                # 星号导入会把 generate_psychopy_script 悄悄绑进 UI 命名空间
                hits.append({**where, "kind": "star-import", "symbol": module})
            if "psychopy_generator" in module:
                hits.append({**where, "kind": "import-module", "symbol": alias.name})
            if alias.name in PSYCHOPY_SYMBOLS:
                hits.append({**where, "kind": "import-symbol", "symbol": alias.name})
    elif isinstance(node, ast.Import):
        for alias in node.names:
            if "psychopy_generator" in alias.name:
                hits.append({**where, "kind": "import-module", "symbol": alias.name})
    elif isinstance(node, ast.Name) and node.id in PSYCHOPY_SYMBOLS:
        hits.append({**where, "kind": "name", "symbol": node.id})
    elif isinstance(node, ast.Attribute) and node.attr in PSYCHOPY_SYMBOLS:
        hits.append({**where, "kind": "attribute", "symbol": node.attr})
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == "getattr" and len(node.args) >= 2:
        literal = node.args[1]
        if isinstance(literal, ast.Constant) and literal.value in PSYCHOPY_SYMBOLS:
            hits.append({**where, "kind": "dynamic", "symbol": literal.value})
    return hits


def scan_tree(tree: ast.AST, file_label: str) -> list[dict]:
    return [hit for node in ast.walk(tree) for hit in classify(node, file_label)]


def scan_wiring_refs(paths: list[Path]) -> list[dict]:
    """扫出 paths 里对 psychopy 生成器公开符号的引用点。"""
    return [
        hit
        for path in paths
        for hit in scan_tree(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path)), _rel(path)
        )
    ]


def scan_sources(*sources: str) -> list[dict]:
    """对内存里的源码字符串跑同一套扫描（注入法用，绝不往 src/ 落盘）。"""
    return [
        hit
        for idx, source in enumerate(sources)
        for hit in scan_tree(ast.parse(source, filename=f"<injected:{idx}>"), f"<injected:{idx}>")
    ]


# ═══════════════ 一、接线面本身（现状：零） ═══════════════


def test_wiring_surface_is_discovered_by_traversal_including_subpackages():
    files = iter_wiring_surface_files()
    rels = [_rel(p) for p in files]

    assert len(files) >= 40, f"接线面只剩 {len(files)} 个文件，遍历口径被改小了"
    assert "app.py" in rels
    assert "src/ui/experiment_design_ui.py" in rels, "实验设计 UI 不在面上＝用例失去对象"
    assert any("/pages/" in r for r in rels), "rglob 没吃到 src/ui/pages 子包（平铺遍历假绿）"
    assert not any(r.endswith(".pyc") or "__pycache__" in r for r in rels)


def test_ui_and_app_have_zero_psychopy_wiring_points():
    """当前断言命中数 0（判据 2）。红了就是有人在 UI 侧悄悄接线。"""
    hits = scan_wiring_refs(iter_wiring_surface_files())

    assert hits == [], f"UI 侧出现 PsychoPy 生成器接线点，未经日间评审：{hits}"


def test_no_star_import_could_silently_bind_the_generator():
    """星号导入是"看起来没接、其实接了"的通道：面上必须为 0。"""
    star_hits = [h for h in scan_wiring_refs(iter_wiring_surface_files()) if h["kind"] == "star-import"]

    assert star_hits == [], f"UI 侧存在星号导入，符号被隐式绑进命名空间：{star_hits}"


def test_whole_src_has_no_consumer_outside_owner_and_reexport():
    """扩到全 src/（248 个 .py）核一遍：命中只允许出现在定义处与 __init__ re-export 处。"""
    src_files = sorted((REPO_ROOT / "src").rglob("*.py"))
    hits = [h for h in scan_wiring_refs(src_files)
            if h["file"] not in (OWNER_MODULE_PATH, REEXPORT_PATH)]

    assert hits == [], f"src/ 里有 UI 之外的第二个消费方：{hits}"
    assert len(src_files) >= 200, f"src/ 只剩 {len(src_files)} 个文件，遍历被改小了"


# ═══════════════ 二、判别力自证（正样） ═══════════════


def test_scanner_reports_the_real_reexport_so_it_is_not_a_no_op():
    """真实正对照：包 __init__ 的 re-export 必被扫出来（4 条 import-symbol）。"""
    hits = scan_wiring_refs([REPO_ROOT / REEXPORT_PATH])
    symbol_hits = [h for h in hits if h["kind"] == "import-symbol"]

    assert {h["symbol"] for h in symbol_hits} == set(PSYCHOPY_SYMBOLS)
    assert len(symbol_hits) == 4
    assert {h["lineno"] for h in symbol_hits} == {32}, "re-export 行号漂移了，锚点与纪律档要同步更正"
    module_hits = [h for h in hits if h["kind"] == "import-module"]
    assert len(module_hits) == 4, "四条都从 psychopy_generator 导入才对"


@pytest.mark.parametrize(
    "source",
    [
        "from src.experiment_design import generate_psychopy_script\n",
        "from src.experiment_design.psychopy_generator import PsychoPyExperiment\n",
        "import src.experiment_design.psychopy_generator as gen\n\n"
        "def render():\n    return gen.generate_psychopy_script(None)\n",
        "def render(eng):\n    fn = getattr(eng, 'generate_standard_paradigm')\n    return fn('stroop')\n",
        "from src.experiment_design import *\n",
    ],
    ids=["import-symbol", "import-module-path", "module-attribute-call",
         "getattr-dynamic", "star-import"],
)
def test_scanner_reports_every_injected_wiring_form(source):
    """注入法自证：五种接线写法都要被扫出≥1 条（往内存里注，src/ 一个字节都不动）。"""
    hits = scan_sources(source)

    assert hits, f"扫描器漏掉了这种接线写法：{source!r}"


# ═══════════════ 三、12 形态冒烟（6 范式串 × feedback） ═══════════════

PARADIGM_STRINGS = ["stroop", "flanker", "emotion", "memory", "custom", "不存在的范式"]


def _script_for(paradigm: str, show_feedback: bool) -> str:
    from src.experiment_design.psychopy_generator import (
        PsychoPyExperiment,
        generate_psychopy_script,
    )

    return generate_psychopy_script(
        PsychoPyExperiment(title="测试实验", paradigm=paradigm, show_feedback=show_feedback)
    )


@pytest.mark.parametrize("show_feedback", [True, False], ids=["feedback_on", "feedback_off"])
@pytest.mark.parametrize("paradigm", PARADIGM_STRINGS)
def test_all_twelve_forms_parse_and_stay_in_the_line_band(paradigm, show_feedback):
    """判据 3：12 形态全部 ast.parse 成功，行数落 200-240（实测现值 209-229）。"""
    script = _script_for(paradigm, show_feedback)
    n_lines = len(script.splitlines())

    ast.parse(script, filename=f"<psychopy:{paradigm}:{show_feedback}>")   #  SyntaxError 即红
    assert 200 <= n_lines <= 240, f"{paradigm}/feedback={show_feedback} 行数 {n_lines} 出了 200-240"


def test_generator_factory_only_covers_four_paradigms_not_six():
    """🔴 前提否证落地：范式工厂只有 4 项，'custom'/未知串必须 ValueError——12 形态只能走构造器路。"""
    from src.experiment_design.psychopy_generator import generate_standard_paradigm

    for paradigm in ("stroop", "flanker", "emotion", "memory"):
        assert generate_standard_paradigm(paradigm, n_trials_per_condition=2).paradigm == paradigm

    for unknown in ("custom", "nope"):
        with pytest.raises(ValueError, match="未知范式"):
            generate_standard_paradigm(unknown)


# ═══════════════ 四、离线契约（子进程断言 sys.modules） ═══════════════


def test_generation_is_offline_but_the_package_reexport_is_live_in_a_fresh_process():
    """子进程法：同进程断言 sys.modules 必假绿，故在干净解释器里两头取证。

    - `src.experiment_design.psychopy_generator` **在** sys.modules：包 __init__ 的 re-export 是活的，
      所以"UI 侧零接线"这条钉桩有承重对象（不是给死代码立牌）；
    - `psychopy` **不在** sys.modules：连跑 12 形态也没碰第三方运行时。
    """
    probe = (
        "import sys\n"
        "import src.experiment_design as pkg\n"
        "from src.experiment_design.psychopy_generator import (\n"
        "    PsychoPyExperiment, generate_psychopy_script)\n"
        "for p in %r:\n"
        "    for fb in (True, False):\n"
        "        generate_psychopy_script(PsychoPyExperiment(title='t', paradigm=p, show_feedback=fb))\n"
        "print('PKG_OK', 'generate_psychopy_script' in dir(pkg))\n"
        "print('GEN_LOADED', 'src.experiment_design.psychopy_generator' in sys.modules)\n"
        "print('PSYCHOPY_ABSENT', 'psychopy' in sys.modules)\n"
    ) % (PARADIGM_STRINGS,)

    proc = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )

    assert proc.returncode == 0, proc.stderr[-800:]
    out = proc.stdout
    assert "PKG_OK True" in out
    assert "GEN_LOADED True" in out
    assert "PSYCHOPY_ABSENT False" in out, "生成期把 psychopy 运行时拽进来了（离线契约破了）"
