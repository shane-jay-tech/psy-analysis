# -*- coding: utf-8 -*-
"""src/paper_writer/section_writers.py 段落生成器离线钉桩（s922-117）。

锚点复核（开工第一动作，磁盘实测）
--------------------------------
- `src/paper_writer/section_writers.py:18` = `class PaperContext:` —— **未漂移**。
- `src/paper_writer/section_writers.py:84` = `def write_abstract(context: PaperContext) -> str:` —— **未漂移**。
- 模块实测 996 行；writer 函数体位置：write_title :69 / write_abstract :84 / write_keywords :114 /
  write_introduction :146 / write_methods :216。

任务书前提的两处失真（按磁盘实况收窄，不据此判 failed）
------------------------------------------------
1. 任务书让构造「title/variables/sample_size 占位」的最小 PaperContext——**这三个字段名不存在**。
   实际字段是 `title_hint` / `topic` / `hypotheses` / `participants_n`（:21-27）。本件按真实字段构造。
2. 任务书说该模块「仅被 apa7_gate 测试间接覆盖」——`grep -rl section_writers tests/`（已剔 __pycache__）
   实测引用面是 **2 个文件**：`tests/test_psychology_report_format_golden.py`、`tests/test_ui.py`；
   **没有任何 apa7_gate 测试引用它**（`tests/` 下 apa7_gate 系测试件零命中 `section_writers`）。
   即「已有覆盖」是经由 `psychology_report_format` 常量的**间接**关系，段落生成器本体此前**零直接测试**。

离线证明（完成标准 2/3 的落点）
------------------------------
每个被测 writer 都断言输出含**当次注入的唯一标记串**（不同用例不同标记），证明不是模板硬编码；
另有两条离线门：① 运行时把 `src.llm_gateway*`／`openai` 在 sys.modules 里置 None 并给
`socket.socket`／`socket.create_connection` 装炸弹，任何取数/生成调用触发即红；
② 对被测 5 个函数做 AST 静态扫描，断言函数体内**没有** gateway/llm import。
（全模块唯一的 LLM 出口在 `write_discussion_deep`（:900 起，:938 `from src.llm_gateway.gateway import llm_chat`），
不在本件被测面内，故 :936-938 的可选深度讨论不属"段落生成器离线路径"。）

红线自查：本件只断言字符串结构与"是否注入了 context 的值"，**不改 src/paper_writer/section_writers.py、
不评任何统计口径、不产任何统计/医疗结论**；显著性星号、效应量等数值面一律不落到断言里。
"""

import ast
import inspect
import socket
import sys

import pytest

from src.paper_writer.section_writers import (
    PaperContext,
    write_abstract,
    write_introduction,
    write_keywords,
    write_methods,
    write_title,
)

# 被测面（任务书点名的四个 + 容错分支的 write_methods）
TESTED_WRITERS = (
    write_title,
    write_abstract,
    write_keywords,
    write_introduction,
    write_methods,
)

# 只允许在 write_discussion_deep 里出现的 LLM 出口模块（本件被测面必须零命中）
LLM_MODULE_PREFIXES = ("src.llm_gateway", "openai", "litellm", "anthropic")


@pytest.fixture
def offline_tripwire(monkeypatch):
    """运行期离线门：LLM 网关模块不可导入，socket 连接直接炸。"""
    for name in ("src.llm_gateway", "src.llm_gateway.gateway", "openai"):
        monkeypatch.setitem(sys.modules, name, None)

    def _boom(*_args, **_kwargs):
        raise AssertionError("离线钉桩失败：writer 调用链试图开网络")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    yield


def _imported_names(func) -> list:
    """AST 取出函数体内所有 import 的顶层/完整模块名。"""
    tree = ast.parse(inspect.getsource(func))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append(node.module or "")
    return found


def _hits_llm(name: str) -> bool:
    return any(name == p or name.startswith(p + ".") for p in LLM_MODULE_PREFIXES)


# ===========================================================================
# PaperContext 最小构造
# ===========================================================================

def test_paper_context_minimal_defaults():
    """最小 PaperContext 可零参构造，且任务书点名的三个字段名实际不存在（前提订正自证）。"""
    ctx = PaperContext()
    assert ctx.title_hint == ""
    assert ctx.topic == ""
    assert ctx.participants_n == 0
    assert ctx.analysis_results == {}
    for ghost in ("title", "variables", "sample_size"):
        assert not hasattr(ctx, ghost), f"PaperContext 不该有 {ghost} 字段（任务书前提用词失真）"


# ===========================================================================
# write_title
# ===========================================================================

def test_write_title_returns_injected_hint_verbatim():
    ctx = PaperContext(title_hint="TTL-MARKER-4d17")
    assert write_title(ctx) == "TTL-MARKER-4d17"


def test_write_title_fallback_chain_is_context_driven():
    # 无 title_hint：有假设 → 走「基于…的研究」包装；无假设 → 退回 topic；全空 → 兜底常量
    # 实测钉桩：section_writers.py:79 用 h1[:20] 硬截 20 字符，长假设会被切尾
    long_h = "HYPOTHESIS-MARKER-9c2a-and-its-very-long-tail"
    assert write_title(PaperContext(hypotheses=[long_h])) == f"基于{long_h[:20]}的研究"
    assert write_title(PaperContext(hypotheses=[long_h])) == "基于HYPOTHESIS-MARKER-9c的研究"
    short_h = "SHORT-MARKER-7e"
    assert write_title(PaperContext(hypotheses=[short_h])) == short_h, "≤20 字符时原样作题"
    topic_only = write_title(PaperContext(topic="TOPIC-MARKER-2f8b"))
    assert topic_only == "TOPIC-MARKER-2f8b"
    assert write_title(PaperContext()) == "心理学实证研究"


# ===========================================================================
# write_abstract
# ===========================================================================

def test_write_abstract_four_elements_and_marker():
    ctx = PaperContext(
        topic="ABSTOPIC-MARKER-6e13",
        hypotheses=["中介机制假设"],
        participants_n=317,
    )
    text = write_abstract(ctx)
    assert text, "摘要不得为空"
    for element in ("目的：", "方法：", "结果：", "结论："):
        assert element in text, f"摘要四要素缺 {element}"
    assert "ABSTOPIC-MARKER-6e13" in text
    assert "317名" in text, "样本量来自 context 注入，不得是硬编码占位"


def test_write_abstract_placeholder_when_sample_missing():
    ctx = PaperContext(topic="ABSTOPIC-MARKER-1ab4")
    text = write_abstract(ctx)
    assert "XXX名" in text, "participants_n 缺省时应回落到占位串"
    assert "ABSTOPIC-MARKER-1ab4" in text


# ===========================================================================
# write_keywords
# ===========================================================================

def test_write_keywords_inject_context_variables():
    ctx = PaperContext(
        analysis_results={
            "mediation_analysis": {
                "dependent_vars": ["KWDV-MARKER-73cf"],
                "independent_vars": ["KWIV-MARKER-5e91"],
            }
        }
    )
    kws = write_keywords(ctx)
    assert isinstance(kws, list) and kws
    assert "KWDV-MARKER-73cf" in kws
    assert "KWIV-MARKER-5e91" in kws
    assert "中介效应" in kws, "analysis_results 的 key 决定方法论关键词"


def test_write_keywords_cap_and_underscore_window():
    # 实测钉桩（section_writers.py:125 `dv[:2] + iv[:2]`）：下划线过滤发生在**取窗前两位之后**，
    # 因此第 3 个变量根本没进循环 —— 不是"被剔除"而是"从未被看到"。
    # 这是本件唯一一处与任务书直觉相反的读法，改码若放宽窗口本用例即红，属预期护栏。
    ctx = PaperContext(
        analysis_results={
            "corr_analysis": {
                "dependent_vars": ["_hidden1", "PLAIN-MARKER-08ad", "never-seen"],
                "independent_vars": [f"extra{i}" for i in range(6)],
            }
        }
    )
    kws = write_keywords(ctx)
    assert len(kws) <= 5, "关键词上限 5 个"
    assert not any(k.startswith("_") for k in kws), "下划线开头的变量名应被剔除"
    assert "PLAIN-MARKER-08ad" in kws
    assert "never-seen" not in kws, "dv 第 3 位在 [:2] 窗口外"
    assert "extra5" not in kws
    assert kws[-1] == "心理测量", "方法论兜底词恒在最后"


def test_write_keywords_underscore_slot_drops_nothing_extra():
    ctx = PaperContext(
        analysis_results={
            "ttest_analysis": {
                "dependent_vars": ["_hidden1", "_hidden2"],
                "independent_vars": [],
            }
        }
    )
    assert write_keywords(ctx) == ["心理测量"], "两位都被下划线吃掉时只剩兜底词"


# ===========================================================================
# write_introduction
# ===========================================================================

def test_write_introduction_structure_and_markers():
    ctx = PaperContext(
        topic="INTROROCKET-MARKER-3b77",
        hypotheses=["H1: HYP-MARKER-cc42"],
        research_questions=["RQ-MARKER-9f10"],
        control_vars=["CTRL-MARKER-1d23"],
    )
    text = write_introduction(ctx)
    for heading in ("## 1 引言", "### 1.1 研究背景", "### 1.2 文献综述与理论框架",
                    "### 1.3 现有研究不足", "### 1.4 本研究目的与假设"):
        assert heading in text, f"引言缺小节 {heading}"
    assert "INTROROCKET-MARKER-3b77" in text
    assert "HYP-MARKER-cc42" in text
    assert "RQ-MARKER-9f10" in text
    assert "CTRL-MARKER-1d23" in text, "控制变量应进研究缺口段"


def test_write_introduction_gap_fallback_without_control_vars():
    ctx = PaperContext(topic="GAPTOPIC-MARKER-52e9")
    text = write_introduction(ctx)
    assert "然而，" in text
    assert "理论框架不够整合" in text, "无控制变量/无中介时应走通用缺口句"
    assert "GAPTOPIC-MARKER-52e9" in text


# ===========================================================================
# write_methods —— 缺失 stats 的容错分支
# ===========================================================================

def test_write_methods_survives_missing_stats():
    ctx = PaperContext(topic="METH-MARKER-84d1")
    text = write_methods(ctx)  # analysis_results 为空 dict：不得抛异常
    assert "## 2 方法" in text
    assert "### 2.4 数据分析策略" in text
    assert "（1）首先" in text
    assert "（2）" not in text, "无分析结果时数据分析策略不应出现第 2 步"
    assert "XXX名被试" in text, "participants_n=0 应走占位分支"
    assert "量表信息待补充" in text, "materials 为空应走待补充分支"
    assert "METH-MARKER-84d1" in text or "（具体信息待补充" in text


def test_write_methods_materials_and_procedure_markers():
    ctx = PaperContext(
        participants_n=200,
        male_ratio=0.4,
        age_mean=21.5,
        age_sd=2.25,
        materials=[{"name": "MAT-MARKER-2c6f", "items": 12, "alpha": 0.87, "source": "SRC-MARKER-77aa"}],
        procedure="PROC-MARKER-90de",
        ethics="ETHICS-MARKER-5bff",
        analysis_results={"regression_analysis": {"result": None}},
    )
    text = write_methods(ctx)
    assert "MAT-MARKER-2c6f" in text
    assert "SRC-MARKER-77aa" in text
    assert "PROC-MARKER-90de" in text
    assert "ETHICS-MARKER-5bff" in text
    assert "200名被试" in text
    assert "（2）使用层次回归分析" in text, "analysis_results 的 key 决定策略步骤"


# ===========================================================================
# 离线门（完成标准 2「无 LLM 调用路径」的两条实证）
# ===========================================================================

def test_all_tested_writers_run_under_offline_tripwire(offline_tripwire):
    ctx = PaperContext(
        title_hint="OFF-TTL-6a01",
        topic="OFF-TOPIC-6a01",
        hypotheses=["OFF-HYP-6a01"],
        research_questions=["OFF-RQ-6a01"],
        participants_n=88,
        materials=[{"name": "OFF-MAT-6a01"}],
        analysis_results={"mediation_analysis": {"dependent_vars": ["OFF-DV-6a01"]}},
    )
    outputs = [w(ctx) for w in TESTED_WRITERS]
    assert all(outputs), "五个 writer 均须有输出"
    assert all("OFF-" in o if isinstance(o, str) else any("OFF-" in k for k in o) for o in outputs)


@pytest.mark.parametrize("func", TESTED_WRITERS, ids=lambda f: f.__name__)
def test_writer_source_has_no_llm_import(func):
    names = _imported_names(func)
    assert not any(_hits_llm(n) for n in names), f"{func.__name__} 体内出现 LLM 模块导入：{names}"


def test_module_llm_import_is_isolated_to_deep_discussion():
    """全模块唯一的 LLM 出口只在 write_discussion_deep —— 被测面之外的偏移要被本用例抓住。"""
    leaky = [
        f.__name__
        for f in TESTED_WRITERS
        if any(_hits_llm(n) for n in _imported_names(f))
    ]
    assert leaky == []
    src = inspect.getsource(sys.modules[write_title.__module__])
    assert "from src.llm_gateway.gateway import" in src, "深度讨论出口仍在，若被搬动需重估本件面"
    deep = ast.parse(src)
    holders = set()
    for node in ast.walk(deep):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.ImportFrom) and _hits_llm(sub.module or ""):
                    holders.add(node.name)
    assert holders == {"write_discussion_deep"}, f"LLM 导入泄漏到非深度讨论函数：{holders}"
