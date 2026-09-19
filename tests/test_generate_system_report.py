"""scripts/generate_system_report.py 计数口径测试（s918-53）。

小文件一律 `tmp_path` 合成；`gather_metrics` 把 `PROJECT_ROOT`/`TESTS_DIR` 指向 tmp 树，
并把两个重依赖模块（`AnalysisRegistry`/`LEARNING_DB`）在 `sys.modules` 里换成桩，
**不 import 真分析注册表、不跑 pytest 收集**。这些数字是发布系统报告的口径来源。
锚点：:53 count_lines、:60 count_pattern、:68 gather_metrics（331 行）。
"""
import inspect
import sys
import types

import pytest

import scripts.generate_system_report as g


@pytest.fixture(autouse=True)
def _no_syspath_pollution(monkeypatch):
    """s919-17 幂等守卫：本模块每个用例都把 `PROJECT_ROOT` 换成自己的 tmp 树，
    而 `gather_metrics()` 仍会把"当前 `PROJECT_ROOT`"挂上 `sys.path`（s920-25 起改为
    `_ensure_project_on_path()`：只在缺席时挂，不再一次插两条）⇒ 没有这层守卫，tmp 路径
    仍会一路留在会话的 `sys.path` 里（无人回收）。
    做法是**换掉 sys.path 这个对象本身**（浅拷贝），teardown 由 monkeypatch 还原 ⇒ 用例内随便插都不外溢。
    """
    monkeypatch.setattr(sys, "path", list(sys.path))


@pytest.fixture
def tiny(tmp_path):
    def write(name, text):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p
    return write


def test_count_lines_counts_physical_lines(tiny):
    assert g.count_lines(tiny("three.py", "a\nb\nc\n")) == 3
    assert g.count_lines(tiny("noeol.py", "a\nb")) == 2          # 末行无换行仍算一行
    assert g.count_lines(tiny("empty.py", "")) == 0


def test_count_lines_returns_zero_for_missing_and_undecodable(tmp_path, tiny):
    assert g.count_lines(tmp_path / "nope.py") == 0
    raw = tmp_path / "binary.py"
    raw.write_bytes(b"\xff\xfe\x00\x01\n")                        # errors="ignore" 下不抛
    assert g.count_lines(raw) == 1


def test_count_pattern_uses_regex_on_the_whole_file(tiny):
    src = tiny("pkg.py", "class A:\n    pass\n\n\nclass B:\n    pass\n")
    assert g.count_pattern(src, r"(?m)^class ") == 2
    assert g.count_pattern(src, r"(?m)^class Z") == 0
    assert g.count_pattern(tiny("e.py", ""), r"class") == 0
    assert g.count_pattern(tiny("miss2.py", "x"), r"[") == 0        # 非法正则也走 except → 0


def test_function_counter_only_sees_module_and_one_level_defs(tiny):
    """发布口径：`^(?:    )?def ` 只认模块级与缩进 4 空格；嵌套更深的 def 不计。"""
    src = tiny("fn.py", "def top():\n    pass\n\n\nclass C:\n    def m(self):\n        pass\n"
                        "    def outer():\n        def inner():\n            pass\n")

    assert g.count_pattern(src, r"(?m)^(?:    )?def ") == 3


def test_iter_py_files_skips_the_excluded_dirs(tmp_path):
    for d in ["src", ".venv", "__pycache__", "node_modules", ".git", ".pytest_cache", "src/sub"]:
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "f.py").write_text("x", encoding="utf-8")
    (tmp_path / "src" / "notes.txt").write_text("x", encoding="utf-8")

    found = sorted(p.relative_to(tmp_path).as_posix() for p in g._iter_py_files(tmp_path))

    assert found == ["src/f.py", "src/sub/f.py"]


def _stub_heavy_imports(monkeypatch):
    reg = types.ModuleType("src.analysis.runner")
    reg.AnalysisRegistry = {"a": 1, "b": 2, "c": 3}
    card = types.ModuleType("src.output.learning_card")
    card.LEARNING_DB = {"k1": {}, "k2": {}}
    monkeypatch.setitem(sys.modules, "src.analysis.runner", reg)
    monkeypatch.setitem(sys.modules, "src.output.learning_card", card)


def test_gather_metrics_against_a_tmp_tree_has_every_key(tmp_path, monkeypatch):
    code = tmp_path / "repo"
    (code / "src" / "analysis").mkdir(parents=True)
    (code / "src" / "analysis" / "a.py").write_text("class A:\n    def m(self):\n        pass\n", encoding="utf-8")
    (code / "src" / "analysis" / "b.py").write_text("def f():\n    pass\n", encoding="utf-8")
    (code / "src" / "version.py").write_text("APP_VERSION_LABEL = 'tmp-v'\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_a.py").write_text("def test_one():\n    pass\n\nasync def test_two():\n    pass\n", encoding="utf-8")
    (tests / "helper.py").write_text("def x():\n    pass\n", encoding="utf-8")

    monkeypatch.setattr(g, "PROJECT_ROOT", code)
    monkeypatch.setattr(g, "TESTS_DIR", tests)
    _stub_heavy_imports(monkeypatch)

    m = g.gather_metrics()

    assert set(m) >= {"version", "total_files", "total_lines", "total_classes", "total_functions",
                      "modules", "test_files", "test_functions", "registered_methods",
                      "learning_cards", "dependencies"}
    assert m["total_files"] == 3 and m["total_lines"] == 6      # a.py + b.py + src/version.py
    assert m["total_classes"] == 1 and m["total_functions"] == 2
    assert m["test_files"] == 1
    # 口径漏洞：`(?m)^\s*def test_` 不认 `async def test_two` ⇒ 异步测试一律漏计（本单 tmp 文件里 2 个测试只数到 1）
    assert m["test_functions"] == 1
    assert m["modules"]["src/analysis"] == {"files": 2, "lines": 5}
    assert "src/ui" not in m["modules"]                  # tmp 树里没有的模块不进 breakdown
    assert m["registered_methods"] == 3 and m["learning_cards"] == 2
    assert m["dependencies"]["pandas"] is True


def test_gather_metrics_is_idempotent_for_sys_path_and_result(tmp_path, monkeypatch):
    """s920-25 翻正（原钉「单次调用插两条、重复调用累积到 4 条」）：现在最多一条，且两次结果全等。"""
    monkeypatch.setattr(g, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(g, "TESTS_DIR", tmp_path / "t")
    _stub_heavy_imports(monkeypatch)
    target = str(tmp_path)
    assert target not in sys.path

    first_metrics = g.gather_metrics()
    after_first = sys.path.count(target)
    second_metrics = g.gather_metrics()

    try:
        assert (after_first, sys.path.count(target)) == (1, 1), "仓根被重复累积（泄漏回来了）"
        assert first_metrics == second_metrics, "重复调用结果不一致 ⇒ 报告数会随调用次数漂"
    finally:
        while target in sys.path:
            sys.path.remove(target)


def test_gather_metrics_has_no_inline_sys_path_insert():
    """幂等性由 `_ensure_project_on_path()` 单点负责：函数体里不该再有裸 insert。

    只断"写法"不测行为的那一面：将来有人再加一句 `sys.path.insert(...)`，
    行为测要等到有人连调两次才红，这条静态测当场就红。
    """
    src = inspect.getsource(g.gather_metrics)
    assert "sys.path.insert" not in src
    assert src.count("_ensure_project_on_path()") == 2          # 版本段＋注册方法段，仍是两处需要


def test_real_repo_has_no_async_def_tests_yet():
    """口径哨兵（s918-53 遗留 1 的订正）：发布报告数测试函数用的是 `(?m)^\\s*def test_`，
    **不认 `async def test_`** ⇒ 今天全仓 0 条异步测试所以不咬人，
    一旦有人加 pytest-asyncio 用例，`test_functions` 就会**静默偏小**（报告的数比真的好少）。
    本用例把这份"静默"换成显式红：真出现异步测试时，必须同步改
    `scripts/generate_system_report.py` 的 count 口径（或本注释说明为何可以偏小）。
    只读文件文本，不收集测试、不 import 任何被测模块。
    """
    import re
    from pathlib import Path

    tests_dir = Path(g.__file__).resolve().parents[1] / "tests"
    pat = re.compile(r"(?m)^[ \t]*async[ \t]+def[ \t]+test_")
    hits = [p.name for p in sorted(tests_dir.glob("test_*.py"))
            if pat.search(p.read_text(encoding="utf-8", errors="ignore"))]

    assert hits == [], (
        f"仓库首次出现 async 测试：{hits}；"
        "generate_system_report 的 test_functions 口径会漏计它们 ⇒ 发布报告数字偏小。"
        "请把 count 模式改成同时认 async def，或在本用例里说明为何允许少计。"
    )
