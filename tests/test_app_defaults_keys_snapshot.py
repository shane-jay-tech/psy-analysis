"""`app.py::_defaults` 会话键集快照钉桩（s922-112，拆分防丢键护栏）.

承重前提（docs/insights/psy-session-state-attr-read-census-20260921.md 结论 1）：
`app.py` 的模块级 `_defaults = {...}` 是 session_state 的**唯一启动补种表**，被
`st.session_state.<key>` 属性式读取的键里 18/20 依赖它落种。app.py 分片迁移（片 5–7）大量
搬动 session_state 读写，**丢一个补种键 = 整页 KeyError 级红**。本用例把 `_defaults` 键集钉成
快照：任何增删都翻红，并提示回写普查档。

取数口径（**绑磁盘实取、不锁魔数**）：
- `_defaults_keys()` 用 AST 现场解析 `app.py` 源码里的 `_defaults = {...}` 字面量（读工作树磁盘，不执行）；
- 判据是「集合等 / 有序表等 / 基数等」**三向互证**（kaoyan 三向等式风格）——三者互相独立，
  任一向破了都红；基数那一向同时兼作「无重复键」不变量；
- 唯一写死的数字是 `EXPECTED_DEFAULTS_KEYS == 27`，而 27 由 `len(EXPECTED_DEFAULTS_KEYS)` 现算，
  且上一条 `基数等` 已把它绑回磁盘实测值——不是游离魔数。

**为何不 `import app`**：import app.py 会执行整个 Streamlit 页面引导（`run_once_env_check` /
autosave atexit / 项目扫描），`tests/conftest.py::isolate_streamlit_app_test_storage` 的存在正是因为它
要重定向用户存储；而本用例只需 `_defaults` 的**键字面量**，AST 读同一份磁盘源码零副作用、等价、且不依赖隔离夹具。

普查结论 2 的反证见 `test_polished_draft_absence_is_a_noop_for_the_guard`：`polished_draft`
（及 `analysis_pipeline`）本就不在 `_defaults`，删除它们对快照零影响。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_PY = Path(__file__).resolve().parent.parent / "app.py"

# 普查 s922-04 结论 1 固化的当前实测键集（工作树 app.py `_defaults`，先 python -c 打印再排序固化）。
# 拆分若丢/增补种键，下面的三向等式会指认差异键，请同步回写普查档与本清单。
EXPECTED_DEFAULTS_KEYS: list[str] = [
    "_wizard_return",
    "analysis_history",
    "analysis_output",
    "archive_tag",
    "df",
    "env_status",
    "experiment_engine",
    "file_name",
    "inspector",
    "interactive_charts",
    "language",
    "meta",
    "onboarding_completed",
    "output_language",
    "paper_engine",
    "plan",
    "privacy_accepted",
    "questionnaire_design",
    "quick_entry",
    "quick_model_id",
    "show_quick_detail",
    "startup_check_done",
    "undergrad_mode",
    "undergrad_path",
    "undergrad_step",
    "undergrad_wizard_data",
    "workspace_saved",
]


def _defaults_keys() -> list[str]:
    """AST 提取 app.py 中模块级 `_defaults = {...}` 的字符串键（工作树磁盘，不执行 app.py）。"""
    tree = ast.parse(APP_PY.read_text(encoding="utf-8"), filename=str(APP_PY))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_defaults" for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            raise AssertionError("app.py 的 _defaults 不是 dict 字面量，快照需人工复核")
        keys: list[str] = []
        for k in node.value.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                keys.append(k.value)
            else:
                raise AssertionError(f"_defaults 含非字符串键 {ast.dump(k)!r}，快照需人工复核")
        return keys
    raise AssertionError("app.py 中找不到模块级 `_defaults = {...}`（分片可能把它搬走了——请核对是否仍为唯一补种点）")


def test_defaults_keys_match_snapshot_three_way() -> None:
    """三向等式：集合 / 有序表 / 基数 三条独立判据同时成立，任一向破都红。"""
    actual = _defaults_keys()
    expected = EXPECTED_DEFAULTS_KEYS

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    detail = f"缺失补种键={missing} 新增键={extra}"  # 丢键时直接给出是哪几个，省得再跑一遍定位

    assert set(actual) == set(expected), f"键集不符：{detail}"
    assert sorted(actual) == sorted(expected), f"排序键表不符：{detail}"
    assert len(actual) == len(expected), (
        f"基数不符（可能 _defaults 里有重复键）：{detail}"
    )
    # 基数即当前实测值（先跑 `python -c "import app;print(len(app._defaults))"` 打印再固化）。
    # 27 由 len(EXPECTED) 现算并被上面的基数等绑回磁盘，不是游离魔数。
    assert len(expected) == 27, "固化清单自身长度漂移（应与工作树实测 27 键一致）"


def test_key_removal_would_flip_the_guard() -> None:
    """元验证：证明主判据不是恒真——若分片误删任一补种键，三向等式必翻红。"""
    for probe in ("df", "_wizard_return"):
        assert probe in EXPECTED_DEFAULTS_KEYS, f"探针键 {probe} 已不在快照，本自测失效"
        dropped = [k for k in EXPECTED_DEFAULTS_KEYS if k != probe]
        assert set(dropped) != set(EXPECTED_DEFAULTS_KEYS)
        assert sorted(dropped) != sorted(EXPECTED_DEFAULTS_KEYS)
        assert len(dropped) == len(EXPECTED_DEFAULTS_KEYS) - 1


def test_polished_draft_absence_is_a_noop_for_the_guard() -> None:
    """反证（普查结论 2）：polished_draft / analysis_pipeline 本就不在 _defaults 表内，
    「删 polished_draft」对补种快照零影响——它靠函数内就地 in 守卫自补种，不归 _defaults 管。"""
    actual = set(_defaults_keys())
    assert "polished_draft" not in actual
    assert "analysis_pipeline" not in actual
    # 因为它不在表内，把它从快照里「删掉」是恒等操作；若有人把它塞进 _defaults，此断言即翻红。
    assert actual - {"polished_draft"} == actual


def test_every_expected_key_is_a_string_literal() -> None:
    """防呆：_defaults 的键必须全是字符串常量（AST 提取到非字符串会抛错），保证快照语义稳定。"""
    for key in _defaults_keys():
        assert isinstance(key, str)


if __name__ == "__main__":  # 允许脱离 pytest 快速自检
    _keys = _defaults_keys()
    print(f"_defaults 键数={len(_keys)}")
    print(sorted(_keys))
    raise SystemExit(0 if sorted(_keys) == sorted(EXPECTED_DEFAULTS_KEYS) else 1)
