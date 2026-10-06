# -*- coding: utf-8 -*-
"""s1004-10：ast_return_census 单测——嵌套函数归属断言＋lambda 不收边界。"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from ast_return_census import census_source  # noqa: E402

SAMPLE = '''def outer(a):
    if a:
        return 1
    def inner(b):
        return 2
    return inner


class Kit:
    def method(self):
        return 3
'''


def test_nested_function_return_belongs_to_nested():
    rep = census_source(SAMPLE)
    assert rep["functions"]["outer"] == [3, 6]   # if 体与 body 直下两层都属 outer
    assert rep["nested"]["outer"] == ["inner"]
    assert rep["functions"]["outer.inner"] == [5]
    assert rep["functions"]["Kit.method"] == [11]


def test_lambda_return_not_collected():
    """lambda 边界：表达式即返回，按设计不收（docstring 已注明）。"""
    src = "def f():\n    g = lambda x: x\n    return g\n"
    rep = census_source(src)
    assert rep["functions"]["f"] == [3]      # 只有显式 return
    assert "lambda" not in str(rep["functions"])


def test_empty_and_multiple_returns():
    src = "def a():\n    pass\n\ndef b(x):\n    if x:\n        return 1\n    return 2\n    return 3\n"
    rep = census_source(src)
    assert rep["functions"]["a"] == []
    assert rep["functions"]["b"] == [6, 7, 8]   # 三条 return 都记（含不可达 8）
