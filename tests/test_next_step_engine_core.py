# -*- coding: utf-8 -*-
"""src/utils/next_step_engine.py 引擎层钉桩（s922-119，panel 之下的纯函数面）。

锚点复核（开工第一动作，磁盘实测，0 漂移）
----------------------------------------
- `:27 def evaluate_project_state(session_state: dict) -> dict[str, bool]:` —— 未漂移。
- `:358 def recommend_next_steps(` —— 未漂移（签名 `(session_state: dict, max_steps: int = 3)`）。
- `_build_rules` 实测在 `:146`（任务书未给行号，本件按盘上钉其 11 条规则）。

引用面实测（psy9 教训：派单叙述的引用面必须先 grep 再写判据）
------------------------------------------------------------
`grep -rl next_step_engine tests/ --exclude-dir=__pycache__` → **只有 1 个文件**
`tests/test_next_step_panel.py`（UI 面板层，靠 monkeypatch 把引擎函数整体换掉，
因此引擎自身的状态推断与规则表**此前零直接测试**）。任务书这条前提成立。

判据 4「引擎层用例不 import streamlit」的证法（两条，互为独立）
--------------------------------------------------------------
① 静态：本模块源码里 `streamlit` 零出现；
② 运行时：用 `sys.executable` 起一个干净子进程只 import 本模块，断言 `sys.modules` 里没有任何 streamlit 条目
   —— 这条才是硬证，因为在同一次 pytest 会话里 streamlit 早被别的件导入过，
   在本进程内断言「sys.modules 无 streamlit」必然是假绿。

本件顺带钉住三处**盘上真实但反直觉**的行为（未改码，见 result 遗留问题）：
`analysis_recipe={}` 空字典也算「已推荐方法」（:75 只判 is not None）；
`paper_bundle` 传入非 None 且既无 `.sections` 又不是 dict 的对象时 `paper_draft` 直接 True（:102 else 分支）；
`consistency_issues` 传非 list（如字符串）一律判未通过（:131-132）。

红线自查：本件只钉推荐引擎的布尔推断与排序截断，**不碰任何统计量、不碰医疗内容、不碰 app.py**。
"""

import subprocess
import sys
from pathlib import Path

import pytest

from src.utils.next_step_engine import (
    NextStep,
    _build_rules,
    evaluate_project_state,
    recommend_next_steps,
)

ENGINE_SRC = Path(sys.modules["src.utils.next_step_engine"].__file__)

ALL_ASSET_KEYS = {
    "data_loaded", "variables_defined", "method_recommended", "analysis_done",
    "result_cards", "figures_generated", "paper_draft", "evidence_collected",
    "consistency_passed", "export_ready",
}

RULE_STEP_IDS = [
    "upload_data", "define_variables", "get_method_recommendation", "run_analysis",
    "generate_result_cards", "generate_figures", "collect_evidence", "write_paper",
    "consistency_check", "export_deliverable", "final_review",
]


class _DF:
    """只有 __len__ 的最小「数据框」替身：引擎判据是 hasattr(df,'__len__') and len(df)>0。"""

    def __init__(self, rows):
        self._rows = rows

    def __len__(self):
        return len(self._rows)


class _Funnel:
    def __init__(self, cv):
        self.candidate_vars = cv


class _Workspace:
    def __init__(self, cv):
        self.funnel = _Funnel(cv)


class _Bundle:
    def __init__(self, sections):
        self.sections = sections


class _Store:
    def __init__(self, records):
        self.records = records


# 三档状态推断用的构造器
EMPTY_STATE = {}
DF_ONLY = {"uploaded_df": _DF([1, 2, 3])}
DF_PLUS_ANALYSIS = {
    "uploaded_df": _DF([1, 2, 3]),
    "analysis_output": {"t_test": {"result": "anything"}},
}

# 恰好点亮 4 条推荐的状态（截断判据用）：
# define_variables(p1) + generate_figures(p2) + collect_evidence(p2) + consistency_check(p2)
FOUR_CANDIDATE_STATE = {
    "uploaded_df": _DF([1, 2]),
    "analysis_output": {"a": 1},
    "analysis_cards": [{"c": 1}],
    "paper_bundle": _Bundle({"intro": "已有章节"}),
}


# ===========================================================================
# 档位 1：空会话
# ===========================================================================

def test_empty_state_all_false_and_keys_complete():
    state = evaluate_project_state(EMPTY_STATE)
    assert set(state) == ALL_ASSET_KEYS, "资产键面变了要同步本件与 panel 显示"
    assert all(v is False for v in state.values()), state
    assert all(isinstance(v, bool) for v in state.values()), "值必须是真 bool 而非真值对象"


def test_empty_state_recommends_upload_and_evidence():
    steps = recommend_next_steps(EMPTY_STATE)
    ids = [s.step_id for s in steps]
    assert ids[0] == "upload_data", "空会话第一条必是上传数据"
    assert "collect_evidence" in ids
    assert all(s.blocked is False for s in steps)


# ===========================================================================
# 档位 2：仅有 df
# ===========================================================================

def test_df_only_turns_on_exactly_data_loaded():
    state = evaluate_project_state(DF_ONLY)
    assert state["data_loaded"] is True
    others = {k: v for k, v in state.items() if k != "data_loaded"}
    assert not any(others.values()), f"只给 df 不该点亮别的资产：{others}"


def test_legacy_and_new_df_keys_are_equivalent_and_empty_df_does_not_count():
    assert evaluate_project_state({"df": _DF([1])})["data_loaded"] is True
    assert evaluate_project_state({"uploaded_df": _DF([1])})["data_loaded"] is True
    # 旧入口优先：uploaded_df 为空表时不再回落到 df（:45-47 的 `if df is None` 语义）
    assert evaluate_project_state({"uploaded_df": _DF([]), "df": _DF([1, 2])})["data_loaded"] is False
    assert evaluate_project_state({"uploaded_df": None, "df": _DF([1, 2])})["data_loaded"] is True
    assert evaluate_project_state({"df": object()})["data_loaded"] is False, "无 __len__ 的对象不算数据"


# ===========================================================================
# 档位 3：df + analysis_output
# ===========================================================================

def test_df_plus_analysis_turns_on_two_assets():
    state = evaluate_project_state(DF_PLUS_ANALYSIS)
    assert state["data_loaded"] is True
    assert state["analysis_done"] is True
    assert state["method_recommended"] is False, "有分析结果不等于有方法推荐"
    assert state["result_cards"] is False, "analysis_output 不点亮卡片"


def test_analysis_history_alone_also_counts_as_done():
    assert evaluate_project_state({"analysis_history": [{"a": 1}]})["analysis_done"] is True
    assert evaluate_project_state({"analysis_history": []})["analysis_done"] is False


# ===========================================================================
# 其余资产项的推断分支（逐条钉）
# ===========================================================================

def test_variables_defined_three_sources():
    assert evaluate_project_state({"upstream_state": {"candidate_vars": {"independent_vars": ["x"]}}})[
        "variables_defined"] is True
    assert evaluate_project_state({"upstream_state": {"candidate_vars": {"dependent_vars": ["y"]}}})[
        "variables_defined"] is True, "只有 DV 也算定义了变量"
    assert evaluate_project_state({"upstream_state": {"candidate_vars": {}}})["variables_defined"] is False
    assert evaluate_project_state({"upstream_state": "not-a-dict"})["variables_defined"] is False
    assert evaluate_project_state({"workspace": _Workspace({"independent_vars": ["x"]})})[
        "variables_defined"] is True, "workspace dataclass 通道（v3.5+）"
    assert evaluate_project_state({"workspace": object()})["variables_defined"] is False, \
        "workspace 缺 funnel 时被 AttributeError 兜住，不得抛"


def test_method_recommended_quirk_empty_recipe_still_counts():
    assert evaluate_project_state({"method_recommendations": [{"m": 1}]})["method_recommended"] is True
    assert evaluate_project_state({"method_recommendations": []})["method_recommended"] is False
    assert evaluate_project_state({"analysis_recipe": {"a": 1}})["method_recommended"] is True
    assert evaluate_project_state({"analysis_recipe": {}})["method_recommended"] is True, \
        "盘上只判 is not None（:75）：空 recipe 也算已推荐 —— 改判据前先改码"


def test_paper_draft_three_bundle_shapes():
    assert evaluate_project_state({"paper_bundle": _Bundle({"intro": "x"})})["paper_draft"] is True
    assert evaluate_project_state({"paper_bundle": _Bundle({})})["paper_draft"] is False
    assert evaluate_project_state({"paper_bundle": {"sections": [{"t": 1}]}})["paper_draft"] is True
    assert evaluate_project_state({"paper_bundle": {"sections": []}})["paper_draft"] is False
    assert evaluate_project_state({"paper_bundle": object()})["paper_draft"] is True, \
        "既无 sections 又非 dict 的对象直接算有草稿（:102 else）—— 钉住现状"
    assert evaluate_project_state({"paper_bundle": None})["paper_draft"] is False


def test_evidence_collected_two_channels():
    assert evaluate_project_state({"evidence_store": _Store([1])})["evidence_collected"] is True
    assert evaluate_project_state({"evidence_store": _Store([])})["evidence_collected"] is False
    assert evaluate_project_state({"evidence_store": [1, 2]})["evidence_collected"] is True, \
        "list 型 store 走 bool() 兜底（:112）"
    assert evaluate_project_state({"evidence_records": [{"r": 1}]})["evidence_collected"] is True
    assert evaluate_project_state({})["evidence_collected"] is False


def test_consistency_passed_levels():
    assert evaluate_project_state({})["consistency_passed"] is False, "未跑检查≠通过"
    assert evaluate_project_state({"consistency_issues": []})["consistency_passed"] is True
    assert evaluate_project_state({"consistency_issues": [{"level": "WARN"}]})["consistency_passed"] is True
    assert evaluate_project_state({"consistency_issues": [{"level": "ERROR"}]})["consistency_passed"] is False
    assert evaluate_project_state({"consistency_issues": ["not-a-dict"]})["consistency_passed"] is True
    assert evaluate_project_state({"consistency_issues": "weird"})["consistency_passed"] is False, \
        "非 list 一律未通过（:131-132）"


def test_export_ready_needs_flag_and_content():
    assert evaluate_project_state({"export_allowed": True})["export_ready"] is False, "有旗子没内容"
    assert evaluate_project_state({"export_allowed": True, "analysis_cards": [{"c": 1}]})["export_ready"] is True
    assert evaluate_project_state({"export_allowed": True, "paper_bundle": _Bundle({"s": 1})})["export_ready"] is True
    assert evaluate_project_state({"analysis_cards": [{"c": 1}]})["export_ready"] is False, "缺旗子不放行"


def test_evaluate_is_pure_and_does_not_mutate_input():
    payload = {"uploaded_df": _DF([1]), "analysis_cards": [{"x": 1}], "consistency_issues": None}
    before = dict(payload)
    first = evaluate_project_state(payload)
    assert payload == before, "引擎不得写回 session_state"
    assert first is not evaluate_project_state(payload)
    assert first == evaluate_project_state(payload), "同一输入必须同一输出"


# ===========================================================================
# 规则表
# ===========================================================================

def test_build_rules_shape_and_count():
    rules = _build_rules()
    assert len(rules) == 11
    for cond, factory in rules:
        assert callable(cond) and callable(factory)
        step = factory()
        assert isinstance(step, NextStep)
        assert step.step_id and step.title and step.page_target
        assert step.priority in (1, 2, 3), "priority 只有紧急/重要/可选三档"
        assert step.blocked is False, "工厂产物默认未阻断，blocked 由 recommend 赋值"


def test_build_rules_step_ids_unique_and_stable():
    rules = _build_rules()
    ids = [factory().step_id for _cond, factory in rules]
    assert len(ids) == len(set(ids)), f"规则 id 有重复：{ids}"
    assert ids == RULE_STEP_IDS, "规则定义顺序参与同优先级并列时的稳定排序"


def test_rule_condition_functions_return_bool_pair_on_empty_state():
    state = evaluate_project_state({})
    for cond, factory in _build_rules():
        pair = cond(state)
        assert isinstance(pair, tuple) and len(pair) == 2, f"{factory().__class__} 返回形状变了"
        recommend, blocked = pair
        assert isinstance(recommend, bool) and isinstance(blocked, bool), \
            f"{factory().step_id} 条件返回非 bool"


def test_rules_are_rebuilt_per_call_so_blocked_flag_does_not_leak():
    state = {"upstream_state": {"candidate_vars": {"independent_vars": ["x"]}}}
    first = recommend_next_steps(state)
    second = recommend_next_steps(state)
    assert [s.step_id for s in first] == [s.step_id for s in second]
    assert [s.blocked for s in first] == [s.blocked for s in second], "blocked 位跨调用泄漏"
    assert all(isinstance(s, NextStep) for s in first)


def test_blocked_step_appears_when_variables_without_data():
    steps = recommend_next_steps({"upstream_state": {"candidate_vars": {"dependent_vars": ["y"]}}})
    by_id = {s.step_id: s for s in steps}
    assert "get_method_recommendation" in by_id
    assert by_id["get_method_recommendation"].blocked is True, "缺数据时该方法推荐应被标阻断（:189）"


# ===========================================================================
# recommend_next_steps 排序与截断
# ===========================================================================

def test_default_max_steps_is_three():
    """选一个天然有 4 条候选的状态，才能证明默认 3 是**截断**而不是恰好 3 条。"""
    steps = recommend_next_steps(FOUR_CANDIDATE_STATE)
    assert len(steps) == 3
    wide = recommend_next_steps(FOUR_CANDIDATE_STATE, max_steps=10)
    assert [s.step_id for s in wide] == [s.step_id for s in steps] + ["consistency_check"], \
        "被截掉的应是规则序最后的第 4 条"


def test_max_steps_truncation_prefix_is_stable():
    state = FOUR_CANDIDATE_STATE
    seq1 = [s.step_id for s in recommend_next_steps(state, max_steps=1)]
    seq2 = [s.step_id for s in recommend_next_steps(state, max_steps=2)]
    seq3 = [s.step_id for s in recommend_next_steps(state, max_steps=3)]
    assert seq2[:1] == seq1 and seq3[:2] == seq2, "加大 max_steps 只能在尾部追加"
    assert recommend_next_steps(state, max_steps=0) == []


def test_priority_ordering_is_non_decreasing():
    steps = recommend_next_steps(FOUR_CANDIDATE_STATE, max_steps=9)
    prios = [s.priority for s in steps]
    assert prios == sorted(prios), f"未按 priority 升序：{prios}"
    assert prios[0] == 1 and prios[-1] == 2


def test_ties_keep_rule_definition_order():
    """同优先级下顺序由 _build_rules 的定义序决定（sort 稳定）。"""
    steps = recommend_next_steps(FOUR_CANDIDATE_STATE, max_steps=9)
    tail = [s.step_id for s in steps if s.priority == 2]
    assert tail == ["generate_figures", "collect_evidence", "consistency_check"]


def test_unblocked_fill_before_blocked():
    """未阻断项优先占位，剩余空间才给阻断项（:384-391）。

    无数据但有变量的状态里候选是 [upload_data(p1,未阻断), get_method_recommendation(p1,**阻断**),
    collect_evidence(p2,未阻断)]。实测排序把 p2 的未阻断项排在 p1 的阻断项**之前** ——
    这就是"阻断降级"的可观察证据。
    """
    state = {"upstream_state": {"candidate_vars": {"independent_vars": ["x"]}}}
    three = recommend_next_steps(state, max_steps=3)
    assert [s.step_id for s in three] == ["upload_data", "collect_evidence", "get_method_recommendation"]
    assert [s.blocked for s in three] == [False, False, True]
    two = recommend_next_steps(state, max_steps=2)
    assert [s.step_id for s in two] == ["upload_data", "collect_evidence"], "槽满即止，阻断项不进"
    one = recommend_next_steps(state, max_steps=1)
    assert [s.step_id for s in one] == ["upload_data"], "只有 1 个槽时也只能给未阻断项"


def test_all_done_state_recommends_final_review():
    steps = recommend_next_steps(
        {
            "uploaded_df": _DF([1, 2, 3]),
            "workspace": _Workspace({"independent_vars": ["x"], "dependent_vars": ["y"]}),
            "method_recommendations": [{"m": 1}],
            "analysis_output": {"a": 1},
            "analysis_cards": [{"c": 1}],
            "apa_figures": [{"f": 1}],
            "paper_bundle": _Bundle({"intro": "text"}),
            "evidence_store": _Store([{"e": 1}]),
            "consistency_issues": [{"level": "WARN"}],
            "export_allowed": True,
        },
        max_steps=5,
    )
    ids = [s.step_id for s in steps]
    assert "final_review" in ids, f"全就绪状态应推荐最终审阅，实得 {ids}"
    assert "upload_data" not in ids and "write_paper" not in ids
    assert all(s.page_target for s in steps)


# ===========================================================================
# 判据 4：引擎层与 streamlit 无关
# ===========================================================================

def test_engine_source_mentions_no_streamlit():
    src = ENGINE_SRC.read_text(encoding="utf-8")
    assert "streamlit" not in src
    assert "import" in src


def test_engine_module_imports_no_streamlit_in_clean_process():
    """子进程硬证：只 import 引擎模块，sys.modules 里不得出现 streamlit。"""
    code = (
        "import sys, src.utils.next_step_engine as e; "
        "assert e.evaluate_project_state({})['data_loaded'] is False; "
        "print(sorted(k for k in sys.modules if 'streamlit' in k))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ENGINE_SRC.parents[2]),  # 仓根：src 是命名空间包，-c 时 sys.path[0]=cwd
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert proc.stdout.strip() == "[]", f"引擎导入链拖进了 streamlit：{proc.stdout.strip()}"
