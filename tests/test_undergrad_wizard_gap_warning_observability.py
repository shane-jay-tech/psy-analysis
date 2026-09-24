# -*- coding: utf-8 -*-
"""s924-39：`undergrad_wizard._collect_literature_gaps` 降级路径的告警观测钉桩。

背景：`zcode-bridge/done/s923-23.result.md` 遗留问题 2 点名「D3 类表现层缺口：脏值在页面上
表现为整块推荐文献消失、零日志」。本单（卷宗正文点名 `src/ui/undergrad_wizard.py` 里
`except Exception:` / `return []` 那一支）已补 `logger.warning`，本件钉三件事：

  ① 会抛进 handler 的那一类脏值 ⇒ **恰好 1 条 WARNING**、异常不外泄、仍返回空列表；
  ② 不抛的那几类（假值 / 错容器 / 列表内脏条目）⇒ **0 条告警**（没被"顺手加日志"污染）；
  ③ 行为不变：合法条目一条都不能少（含 dataclass 风格对象），脏 payload 原样透传。

脏值矩阵沿用 s923-23 的五类分法（假值 / dict / str / 不可迭代 / 列表内脏条目）。
⚠ 卷宗「五类各产生 1 条 warning」这句前提经实测否证：五类里只有「不可迭代」真的抛进
handler，其余四类不抛 ⇒ 本件按磁盘实况钉真值表（期望告警数逐类写死 1 或 0），
未为凑"5 类都告警"去改生产码。逐类读数见 `zcode-bridge/outbox/s924-39.result.md` 证据节。

判据单一真源在 `assert_gap_outcome`：pytest 用例与 `tmp/s924-39/run_mutants.py` 驱动器
跑同一个函数 ⇒ 驱动器里"哪一行参数在哪个变异体下翻红"就是本件对应用例翻红，两套不漂移。
"""
import ast
import logging
import pathlib

import pytest

import src.ui.undergrad_wizard as uw
import src.utils.workspace as wsp

LOGGER_NAME = "src.ui.undergrad_wizard"
WARN_PREFIX = "向导推荐文献渲染失败（整块降级为空）"
WARN_FORMAT = f"{WARN_PREFIX}: %s"
SRC_PATH = pathlib.Path(__file__).resolve().parents[1] / "src" / "ui" / "undergrad_wizard.py"


class _Opaque:
    """不可迭代且真值 ⇒ 生产环当场 TypeError（矩阵第 4 类：唯一会抛进 handler 的一类）。"""


class _GapObj:
    """dataclass 风格：不是 dict、靠属性带 gap_description（生产码的 else 分支）。"""

    def __init__(self, desc):
        self.gap_description = desc


# 每行 = (脏值, 期望告警条数, 期望返回, 期望出现在告警里的异常原文片段)
MATRIX = [
    pytest.param(None, 0, [], "", id="c1_falsy_none"),
    pytest.param("", 0, [], "", id="c1_falsy_empty_str"),
    pytest.param({}, 0, [], "", id="c1_falsy_empty_dict"),
    pytest.param({"keyA": 1, "keyB": 2}, 0, [], "", id="c2_dict_yields_keys"),
    pytest.param("abc", 0, [], "", id="c3_str_yields_chars"),
    pytest.param(5, 1, [], "'int' object is not iterable", id="c4_noniterable_int"),
    pytest.param(True, 1, [], "'bool' object is not iterable", id="c4_noniterable_bool"),
    pytest.param(3.14, 1, [], "'float' object is not iterable", id="c4_noniterable_float"),
    pytest.param(complex(1, 2), 1, [], "'complex' object is not iterable",
                 id="c4_noniterable_complex"),
    pytest.param(_Opaque(), 1, [], "'_Opaque' object is not iterable", id="c4_noniterable_object"),
    pytest.param([{"gap_description": ""}, "junk", None, 7], 0, [], "",
                 id="c5_list_dirty_entries_all_skipped"),
    pytest.param([{"gap_description": 5}], 0, [{"gap_description": 5}], "",
                 id="c5_list_dirty_payload_passthrough"),
    pytest.param([{"gap_description": "g1"}, {"gap_description": ""}], 0,
                 [{"gap_description": "g1"}], "", id="ctrl_list_good_entry_kept"),
    pytest.param([_GapObj("attr")], 0, [{"gap_description": "attr"}], "",
                 id="ctrl_non_dict_object_with_attr"),
]


def assert_gap_outcome(*, result, raised, records,
                       expect_warnings, expect_return, expect_in_message=""):
    """本件唯一判据（pytest 用例与变异驱动器共用）。"""
    assert raised is None, f"脏值不该让调用方看到异常，实际抛了 {type(raised).__name__}: {raised}"
    assert isinstance(result, list), f"降级出口必须仍是列表，实际 {result!r}"
    assert result == expect_return, f"返回值漂移：期望 {expect_return!r}，实际 {result!r}"
    assert len(records) == expect_warnings, (
        f"告警条数应为 {expect_warnings}，实际 {len(records)}："
        f"{[(r.name, r.levelname, r.getMessage()) for r in records]}"
    )
    if expect_warnings:
        rec = records[0]
        assert rec.name == LOGGER_NAME, f"告警必须挂在 {LOGGER_NAME}，实际来自 {rec.name}"
        assert rec.levelno == logging.WARNING, f"必须是 WARNING 级，实际 {rec.levelname}"
        msg = rec.getMessage()
        assert WARN_PREFIX in msg, f"告警文案漂移：{msg!r}"
        assert expect_in_message in msg, f"告警里丢了异常明细（%s 没带上 exc）：{msg!r}"


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def _collect_with(fn, dirty, monkeypatch=None):
    """跑一次 `fn`，把脏值塞进 gap_analysis，返回 (result, raised, 相关告警记录)。

    `src.utils.workspace.get_literature_review_state` 是在**调用时**被 import 的（函数体内
    import），所以替换源模块属性就能覆盖生产路径，不 stub 生产函数本身。
    """
    prev = getattr(wsp, "get_literature_review_state")

    def fake_state(*_a, **_k):
        return {"gap_analysis": dirty}

    if monkeypatch is not None:
        monkeypatch.setattr(wsp, "get_literature_review_state", fake_state)
    else:
        wsp.get_literature_review_state = fake_state

    handler = _ListHandler()
    root = logging.getLogger()
    prev_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    result = None
    raised = None
    try:
        result = fn()
    except BaseException as exc:  # noqa: BLE001 - 判据本身就是"异常不外泄"
        raised = exc
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)
        if monkeypatch is None:
            wsp.get_literature_review_state = prev
    records = [r for r in handler.records if r.name == LOGGER_NAME]
    return result, raised, records


def _row(dirty_id):
    return next(r for r in MATRIX if r.id == dirty_id)


# ─────────────────────────────── 一、真值表（生产码原函数） ───────────────────────────────

@pytest.mark.parametrize("dirty,expect_warnings,expect_return,expect_in_message", MATRIX)
def test_gap_dirty_matrix_observability(monkeypatch, caplog, dirty, expect_warnings,
                                        expect_return, expect_in_message):
    """五类脏值 × 降级路径的告警真值表（本单主判据：抛的那类 1 条、其余 0 条，全部不 raise）。"""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    result, raised, records = _collect_with(uw._collect_literature_gaps, dirty,
                                            monkeypatch=monkeypatch)
    assert_gap_outcome(result=result, raised=raised, records=records,
                       expect_warnings=expect_warnings, expect_return=expect_return,
                       expect_in_message=expect_in_message)


# ─────────────────────────────── 二、结构锚点（钉住"只加了观测"） ───────────────────────────────

def _func_node():
    tree = ast.parse(SRC_PATH.read_text(encoding="utf-8"))
    return next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "_collect_literature_gaps")


def test_handler_shape_is_warning_then_empty_list():
    """完成标准 ①③ 的结构面：handler 恰好两条语句 —— 先 logger.warning(…, exc)，再 return []。

    把 warning 挪出 handler、删掉 return []、改成 raise/return None，都会在这里就地翻红。
    """
    try_node = next(n for n in ast.walk(_func_node()) if isinstance(n, ast.Try))
    assert len(try_node.handlers) == 1
    h = try_node.handlers[0]
    assert ast.unparse(h.type) == "Exception"
    assert h.name == "exc", "告警要带异常明细 ⇒ handler 必须 as exc"
    assert len(h.body) == 2, [ast.unparse(s) for s in h.body]

    call = h.body[0].value
    assert isinstance(h.body[0], ast.Expr) and isinstance(call, ast.Call)
    assert ast.unparse(call.func) == "logger.warning"
    assert isinstance(call.args[0], ast.Constant) and call.args[0].value == WARN_FORMAT
    assert ast.unparse(call.args[1]) == "exc"
    assert isinstance(h.body[1], ast.Return) and ast.unparse(h.body[1].value) == "[]"


def test_logger_is_module_scoped_not_root():
    """告警挂在 `src.ui.undergrad_wizard` 上（不是 root）⇒ 运维侧能按模块筛日志。"""
    assert isinstance(uw.logger, logging.Logger)
    assert uw.logger.name == LOGGER_NAME


def test_producer_and_test_agree_on_warning_text():
    """文案锚点：生产码里的字面串必须与本件判据同源（防止两边各改一半）。"""
    assert f'"{WARN_FORMAT}"' in SRC_PATH.read_text(encoding="utf-8")


# ─────────────────────── 三、判别力自证（内存变异体，生产文件零改动） ───────────────────────

def _live_func_src() -> str:
    text = SRC_PATH.read_text(encoding="utf-8")
    seg = ast.get_source_segment(text, _func_node())
    assert seg is not None, "抽不到 _collect_literature_gaps 源码 ⇒ 锚点已漂"
    return seg


_WARN_STMT = f'        logger.warning("{WARN_FORMAT}", exc)\n'

_MUTATIONS = {
    "M1_drop_warning": lambda s: s.replace(_WARN_STMT, ""),
    "M2_info_level": lambda s: s.replace("logger.warning(", "logger.info("),
    "M3_root_logger": lambda s: s.replace("logger.warning(", "logging.warning("),
    "M4_warn_on_every_path": lambda s: s.replace(
        "        return result\n", _WARN_STMT + "        return result\n"),
    "M5_return_none": lambda s: s.replace("        return []", "        return None"),
    "M6_reraise": lambda s: s.replace("        return []", "        raise"),
    "M7_message_without_exc": lambda s: s.replace(
        f'logger.warning("{WARN_FORMAT}", exc)', f'logger.warning("{WARN_PREFIX}")'),
    "M8_drop_non_dict_branch": lambda s: s.replace(
        '                desc = getattr(g, "gap_description", "")', '                desc = ""'),
}


def _run_mutant(name, dirty):
    """把变异体在内存里 exec 后跑一遍共用判据，返回 (result, raised, records)。"""
    base = _live_func_src()
    mutated = _MUTATIONS[name](base)
    assert mutated != base, f"{name} 没命中任何文本 ⇒ 变异体本身是假的（锚点已漂）"
    ns = {"logging": logging, "logger": logging.getLogger(LOGGER_NAME)}
    exec(compile(mutated, f"<mutant {name}>", "exec"), ns)  # noqa: S102
    return _collect_with(ns["_collect_literature_gaps"], dirty)


# 逐刀点名的靶行：每一刀只杀这一行（其余行由下一条用例反向对照）
KNIVES = [
    ("M1_drop_warning", "c4_noniterable_int"),
    ("M2_info_level", "c4_noniterable_bool"),
    ("M3_root_logger", "c4_noniterable_float"),
    ("M4_warn_on_every_path", "c2_dict_yields_keys"),
    ("M5_return_none", "c4_noniterable_complex"),
    ("M6_reraise", "c4_noniterable_object"),
    ("M7_message_without_exc", "c4_noniterable_int"),
    ("M8_drop_non_dict_branch", "ctrl_non_dict_object_with_attr"),
]


@pytest.mark.parametrize("mutant,dirty_id", KNIVES,
                         ids=[f"{m}->{i}" for m, i in KNIVES])
def test_mutation_knife_turns_its_target_row_red(mutant, dirty_id):
    """每条变异刀都必须让 MATRIX 里点名的那一行按同一判据翻红 ⇒ 主判据不是恒真。"""
    dirty, expect_warnings, expect_return, expect_msg = _row(dirty_id).values
    result, raised, records = _run_mutant(mutant, dirty)
    with pytest.raises(AssertionError) as got:
        assert_gap_outcome(result=result, raised=raised, records=records,
                           expect_warnings=expect_warnings, expect_return=expect_return,
                           expect_in_message=expect_msg)
    assert got.value.args, f"{mutant} 在 {dirty_id} 上杀不动 ⇒ 该行是恒真例"


def test_silent_rows_are_the_only_ones_m1_leaves_green():
    """反向对照：M1（删掉告警）只杀"抛进 handler"那一类，四类不抛的脏值必须仍然满足判据。

    这条防止"判据在乱咬"式的假判别力：如果 M1 让所有行都红，说明期望告警数没逐类写死。
    """
    for dirty_id in ("c1_falsy_none", "c2_dict_yields_keys", "c3_str_yields_chars",
                     "ctrl_list_good_entry_kept"):
        dirty, expect_warnings, expect_return, expect_msg = _row(dirty_id).values
        assert expect_warnings == 0
        result, raised, records = _run_mutant("M1_drop_warning", dirty)
        assert_gap_outcome(result=result, raised=raised, records=records,
                           expect_warnings=expect_warnings, expect_return=expect_return,
                           expect_in_message=expect_msg)


def test_every_warn_row_asserts_exactly_one_warning():
    """计数面自证：本件确实有 ≥5 行在断言「1 条 warning」（卷宗判据 ② 的字面下限是 5）。"""
    warn_rows = [r.id for r in MATRIX if r.values[1] == 1]
    assert len(warn_rows) >= 5, warn_rows
    assert all(i.startswith("c4_") for i in warn_rows), warn_rows
