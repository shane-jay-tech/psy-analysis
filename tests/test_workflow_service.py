"""src/paper_writer/workflow_service.py 特征化测试（s918-23）。

facade 层：注入 fake `PaperEngine` 记录调用序列，**零 LLM、零联网、零真实数据分析**。
只钉「字段默认值＋组装流顺序＋委托调用」，不评生成内容质量。
锚点：src/paper_writer/workflow_service.py:59 `generate_paper_quick`（现 131 行；s919-16 加了 df 类型守卫）。
"""
import pandas as pd
import pytest

import src.paper_writer.workflow_service as ws
from src.paper_writer.workflow_service import PaperResult, QuickPaperRequest


class FakeState:
    def __init__(self):
        self.reference_list = ["Ref A", "Ref B"]


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.state = FakeState()

    def set_topic(self, **kw):
        self.calls.append(("set_topic", kw))

    def set_methods(self, **kw):
        self.calls.append(("set_methods", kw))

    def set_discussion(self, **kw):
        self.calls.append(("set_discussion", kw))

    def set_data(self, df):
        self.calls.append(("set_data", df))

    def import_analysis_results(self, results):
        self.calls.append(("import_analysis_results", results))

    def add_user_literature(self, items):
        self.calls.append(("add_user_literature", items))

    def search_literature(self, keywords):
        self.calls.append(("search_literature", keywords))

    def generate_full_paper(self):
        self.calls.append(("generate_full_paper",))
        return {"引言": "正文", "方法": "方法学"}

    def assemble_manuscript(self):
        self.calls.append(("assemble_manuscript",))
        return "完整稿件"

    def get_logs(self):
        self.calls.append(("get_logs",))
        return ["log-1"]

    def generate_section(self, name):
        self.calls.append(("generate_section", name))
        return f"重写的 {name}"


@pytest.fixture
def engine(monkeypatch):
    made = {}

    def factory():
        made["instance"] = FakeEngine()
        return made["instance"]

    monkeypatch.setattr(ws, "PaperEngine", factory)
    return made


def test_request_defaults_are_the_declared_values():
    req = QuickPaperRequest()

    assert req.topic == "" and req.title_hint == ""
    assert req.participants_n == 0 and req.male_ratio == 0.5
    assert req.age_mean == 0.0 and req.age_sd == 0.0
    assert req.df is None and req.search_keywords is None
    assert req.analysis_results == {}


def test_request_default_lists_are_not_shared_between_instances():
    a, b = QuickPaperRequest(), QuickPaperRequest()

    a.research_questions.append("Q1")

    assert b.research_questions == []
    assert a.research_questions is not b.research_questions


def test_result_defaults_carry_no_engine():
    result = PaperResult()

    assert result.sections == {} and result.manuscript == ""
    assert result.reference_list == [] and result.logs == []
    assert result.engine is None


def test_full_request_drives_the_documented_call_order(engine):
    req = QuickPaperRequest(
        topic="压力与睡眠", title_hint="标题提示",
        research_questions=["Q1"], hypotheses=["H1"],
        participants_n=120, male_ratio=0.4, age_mean=21.5, age_sd=2.0,
        materials=["量表"], procedure="三步", ethics="已批", control_vars=["性别"],
        theoretical_contributions=["T"], practical_implications=["P"],
        limitations=["L"], future_directions=["F"],
        df=pd.DataFrame({"分数": [1.0, 2.0]}), analysis_results={"t": 1},
        user_literature=[{"t": "文"}],
        search_keywords=["stress"],
    )

    result = ws.generate_paper_quick(req)
    calls = engine["instance"].calls

    assert [c[0] for c in calls] == [
        "set_topic", "set_methods", "set_discussion", "set_data",
        "import_analysis_results", "add_user_literature", "search_literature",
        "generate_full_paper", "assemble_manuscript", "get_logs",
    ]
    assert calls[0][1] == {"topic": "压力与睡眠", "research_questions": ["Q1"],
                           "hypotheses": ["H1"], "title_hint": "标题提示"}
    assert calls[1][1]["participants_n"] == 120 and calls[1][1]["control_vars"] == ["性别"]
    assert calls[2][1]["theoretical"] == ["T"] and calls[2][1]["future"] == ["F"]
    assert calls[6][1] == ["stress"]
    assert isinstance(result, PaperResult)


def test_bare_request_skips_all_optional_stages(engine):
    ws.generate_paper_quick(QuickPaperRequest())

    kinds = [c[0] for c in engine["instance"].calls]
    assert kinds == ["set_topic", "set_methods", "set_discussion",
                     "generate_full_paper", "assemble_manuscript", "get_logs"]


@pytest.mark.parametrize("bad", ["DF", 42, [{"x": 1}], object()])
def test_non_dataframe_df_is_rejected_before_the_engine_is_built(engine, bad):
    """s919-16 类型守卫（s918-23「遗留 2」的收口）：改前 `df="DF"` 能一路混到 set_data。
    现在要求在**建引擎之前**就 TypeError——`engine` fixture 只在 `PaperEngine()` 被调用时才登记实例，
    所以"没有 instance"就是"没建引擎"的直接证据（守卫若写成"送进 set_data 再由引擎炸"，本断言会红）。"""
    req = QuickPaperRequest(df=bad)

    with pytest.raises(TypeError) as ei:
        ws.generate_paper_quick(req)

    assert "DataFrame" in str(ei.value) and type(bad).__name__ in str(ei.value)
    assert "instance" not in engine


@pytest.mark.parametrize("empty", [{}, None])
def test_falsy_analysis_results_skip_the_import_stage(engine, empty):
    req = QuickPaperRequest()
    req.analysis_results = empty

    ws.generate_paper_quick(req)

    assert "import_analysis_results" not in [c[0] for c in engine["instance"].calls]


def test_result_is_assembled_from_engine_outputs_and_keeps_the_instance(engine):
    result = ws.generate_paper_quick(QuickPaperRequest(topic="T"))
    inst = engine["instance"]

    assert result.sections == {"引言": "正文", "方法": "方法学"}
    assert result.manuscript == "完整稿件"
    assert result.reference_list == ["Ref A", "Ref B"]
    assert result.logs == ["log-1"]
    assert result.engine is inst


def test_regenerate_section_is_a_thin_delegate():
    fake = FakeEngine()

    assert ws.regenerate_section(fake, "讨论") == "重写的 讨论"
    assert fake.calls == [("generate_section", "讨论")]
