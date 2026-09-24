"""src/ui/experiment_design_ui.py:225-413 「design 非空」分支覆盖（s923-40）。

来源：`zcode-bridge/done/s922-133-expengine-lazyinit.result.md` 遗留问题 3——
「手桩 _FakeST 只覆盖默认路径（未点任何按钮、eng.design is None）。
`eng.design is not None` 的分支（详情页 / Word 导出，:225-413）需要真实 ExperimentDesign
对象做桩，本单未覆盖——留给后续接线单」。本文件就是那张接线单。

用**真实** `ExperimentDesign`（`ExperimentDesignEngine.design_experiment()` 离线构造，
不触网、不调 LLM、不写盘）过手桩，钉：

- :225 分支边界（对照组：design 为 None 时整块一行不渲染）；
- :232-241 概览 metric + 五个页签；metric 的取值一律与**对象自身字段**比对，
  不写死数值 ⇒ 不钉任何统计结论（红线：统计数值结论不碰）；
- :243-285 研究框架页 / 被试页（含 :284 `n_groups > 1` 真分支）；
- :287-289 统计检验力详情：`power_result` 非空 → 该 expander 的**体内**就是
  `format_power_report` 全文；`power_result` 为 None（引擎 :150-154 的用户指定样本量路径）
  → 该 expander 不出现。**必须按容器路径取体**：`format_design_report()`（:356，📄 完整报告页）
  本身也内嵌同一份效力全文，所以「全文出现在渲染文本里」这种全局文本断言
  即使 :289 被掏空也照样绿——本文件实测并钉住了这个失明面（见
  `test_power_detail_expander_*` 与 `test_pin_discriminates_empty_power_report_mutant`）；
- :291-347 程序页：时间线 DataFrame 行数 == procedure.timeline 长度、列名逐字、随机化 expander；
- :352-364 完整报告页：`format_design_report()` 全文 + Markdown 下载锚链接（含文件名安全化）；
- :366-389 Word 导出区文案 / 研究者输入框 key / 完整度提示二择一（由现场重算的
  `count_protocol_placeholders(d) >= 3` 决定走哪支，不写死数字）；
- :391-413 生成与下载两个入口：未生成 ⇒ 下载入口不出现且失败对用户可见；工件在会话里 ⇒
  下载按钮出现、`data` 是**同一个字节对象**（`is` 护栏）、mime/key/文件名逐项对账，
  以及 :407-409 的缺省文件名分支。

在册缺陷登记（本单只测不改）：真实设计点「📄 生成实验程序文档」**必然失败**——
`src/output/docx_exporter.py:779` 把 `ethics`、`:807` 把 `notes`（数据类里是 `List[str]`）
当字符串喂给 `_add_paragraph_with_inline_format` ⇒ TypeError ⇒ UI 走 :400 的 except。
在册的 `tests/test_experiment_docx_export.py` 全部用 `SimpleNamespace(ethics="字符串")`，
所以那条路在它面前是绿的、在真实对象前是死的（「静默失明的绿」）。
本文件以 `xfail(strict=True)` 登记：修好那两行后本例会 XPASS 当场报警。

只加测试，不改 src/、不改 app.py。
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

STATE_KEY = "experiment_engine"
TAB_FRAME = "📖 研究框架"
TAB_SUBJECTS = "👥 被试与效力"
TAB_PROCEDURE = "🔬 实验程序"
TAB_ANALYSIS = "📊 分析计划"
TAB_REPORT = "📄 完整报告"
POWER_EXPANDER_LABEL = "📊 统计检验力分析详情"
RANDOM_EXPANDER_LABEL = "🎲 随机化方案"
WORD_HEADING = "#### 📄 下载实验程序文档（Word）"
WORD_BUTTON_LABEL = "📄 生成实验程序文档"
DOWNLOAD_LABEL = "⬇ 下载实验程序文档（Word）"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ARTIFACT_KEY = "_exp_protocol_docx"
FILENAME_KEY = "_exp_protocol_filename"
RESEARCHER_KEY = "exp_protocol_researcher"

#: 与 UI :239-241 的页签清单对账（磁盘实况，非卷宗转述）
TABS = [TAB_FRAME, TAB_SUBJECTS, TAB_PROCEDURE, TAB_ANALYSIS, TAB_REPORT]

DESIGN_KWARGS = dict(
    topic="考察不同情绪状态对大学生认知控制能力的影响",
    target_population="在校大学生",
    design_type_hint="被试间",
    ivs=["情绪状态"],
    dvs=["反应时"],
    n_subjects_hint=0,          # 0 = 走检验力分析 ⇒ power_result 非空（:287 真分支前提）
    power=0.80,
    effect_size_expected="medium",
)


# ═══════════════ 手桩：带**容器路径**的记录器 ═══════════════

class _Widget:
    """一次控件调用：api + 位置参数 + 关键字参数 + 当时所处的容器路径。"""

    __slots__ = ("api", "args", "kwargs", "path")

    def __init__(self, api, args, kwargs, path):
        self.api = api
        self.args = args
        self.kwargs = kwargs
        self.path = path

    def label(self):
        return self.args[0] if self.args else self.kwargs.get("label")

    def __repr__(self):
        return f"<{self.api} label={self.label()!r} path={self.path!r}>"


class _FakeSessionState:
    """SessionStateProxy 最小复刻：属性读缺键抛 AttributeError，属性/项写落字典。"""

    def __init__(self, initial=None):
        object.__setattr__(self, "_data", dict(initial or {}))

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError as exc:
            raise AttributeError(
                f"st.session_state has no attribute '{key}'. Did you forget to initialize it?"
            ) from exc

    def __setattr__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, *default):
        return self._data.pop(key, *default)


class _FakeCtx:
    """可 with 的容器桩；进入时把自己的标签压栈 ⇒ 子调用带上路径，能按体取文。"""

    def __init__(self, st, api, args, kwargs):
        self._st = st
        self._label = next((a for a in args if isinstance(a, str)), "") or ""
        if api:
            st._record(api, args, kwargs)

    def __enter__(self):
        if self._label:
            self._st._push(self._label)
        return self

    def __exit__(self, *exc):
        if self._label:
            self._st._pop()
        return False

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        st = object.__getattribute__(self, "_st")

        def _display(*args, **kwargs):
            st._record(name, args, kwargs)
            return None

        return _display


class _FakeST:
    """够渲染 design 非空全分支的手桩：只有 `pressed` 里的按钮标签返回 True。"""

    def __init__(self, session_state=None, pressed=()):
        object.__setattr__(self, "session_state", session_state or _FakeSessionState())
        object.__setattr__(self, "pressed", set(pressed))
        object.__setattr__(self, "widgets", [])
        object.__setattr__(self, "_stack", [])
        object.__setattr__(self, "sidebar", _FakeCtx(self, "sidebar", (), {}))

    # ── 记录与路径栈 ──
    def _record(self, api, args, kwargs):
        w = _Widget(api, tuple(args), dict(kwargs), tuple(self._stack))
        self.widgets.append(w)
        return w

    def _push(self, label):
        self._stack.append(label)

    def _pop(self):
        self._stack.pop()

    # ── 容器 ──
    def columns(self, spec, **kwargs):
        self._record("columns", (spec,), kwargs)
        n = spec if isinstance(spec, int) else len(spec)
        return [_FakeCtx(self, "", (), {}) for _ in range(n)]

    def tabs(self, labels, **kwargs):
        self._record("tabs", (tuple(labels),), kwargs)
        return [_FakeCtx(self, "tab", (l,), {}) for l in labels]

    def expander(self, *args, **kwargs):
        self._record("expander", args, kwargs)
        return _FakeCtx(self, "", args, kwargs)

    def spinner(self, *args, **kwargs):
        self._record("spinner", args, kwargs)
        return _FakeCtx(self, "", args, kwargs)

    # ── 布尔控件 ──
    def button(self, *args, **kwargs):
        self._record("button", args, kwargs)
        label = args[0] if args else kwargs.get("label", "")
        return label in self.pressed

    def checkbox(self, *args, **kwargs):
        self._record("checkbox", args, kwargs)
        return False

    def download_button(self, *args, **kwargs):
        self._record("download_button", args, kwargs)
        return False

    # ── 取值控件：中性值 ──
    def text_input(self, *args, **kwargs):
        self._record("text_input", args, kwargs)
        return kwargs.get("value", "") or ""

    def text_area(self, *args, **kwargs):
        self._record("text_area", args, kwargs)
        return kwargs.get("value", "") or ""

    def selectbox(self, *args, **kwargs):
        self._record("selectbox", args, kwargs)
        options = args[1] if len(args) > 1 else kwargs.get("options", [])
        return options[0] if options else None

    def slider(self, *args, **kwargs):
        self._record("slider", args, kwargs)
        return kwargs.get("value", args[3] if len(args) > 3 else 0)

    def number_input(self, *args, **kwargs):
        self._record("number_input", args, kwargs)
        return kwargs.get("value", 0)

    def rerun(self, *args, **kwargs):
        self._record("rerun", args, kwargs)
        raise AssertionError("design 非空分支里不该出现 st.rerun（:391-413 段没有重跑）")

    # ── 其余（title/markdown/info/metric/dataframe/...）：记录后 None ──
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _display(*args, **kwargs):
            self._record(name, args, kwargs)
            return None

        return _display

    # ── 点名查询 ──
    def of(self, api, *path_labels):
        """某 API 的调用；给了 path_labels 就只取**那些容器之内**的调用。"""
        return [
            w for w in self.widgets
            if w.api == api and all(p in w.path for p in path_labels)
        ]

    def labels_of(self, api, *path_labels):
        return [w.label() for w in self.of(api, *path_labels)]

    def body(self, *path_labels):
        """某容器体内的全部字符串型首参拼接（展示 + 提示类都算）。"""
        parts = []
        for w in self.widgets:
            if w.api in ("column", "tab", "expander", "spinner", "sidebar", "button",
                         "download_button", "checkbox", "columns", "tabs"):
                continue
            if all(p in w.path for p in path_labels):
                lab = w.label()
                if isinstance(lab, str):
                    parts.append(lab)
        return " \n ".join(parts)

    def any_text(self):
        return " \n ".join(str(w.label()) for w in self.widgets
                           if isinstance(w.label(), str))


# ═══════════════ 夹具 ═══════════════

@pytest.fixture(scope="module")
def real_design():
    """真实引擎产出的真实 ExperimentDesign（离线，不触网 / 不调 LLM / 不写盘）。"""
    from src.experiment_design import ExperimentDesignEngine

    eng = ExperimentDesignEngine()
    design = eng.design_experiment(**DESIGN_KWARGS)
    assert eng.design is design and design.procedure is not None
    return design


@pytest.fixture()
def render(monkeypatch, real_design):
    """render(design=..., pressed=..., extra_state=...) → fake_st（引擎槽=None，走 :19-20）。"""
    from src.ui import experiment_design_ui

    real_engine_cls = experiment_design_ui.ExperimentDesignEngine

    def go(design=None, pressed=(), extra_state=None):
        class _Engine(real_engine_cls):
            def __init__(self):
                super().__init__()
                self.design = design

        state = {STATE_KEY: None}
        state.update(extra_state or {})
        fake_st = _FakeST(session_state=_FakeSessionState(state), pressed=pressed)
        monkeypatch.setattr(experiment_design_ui, "st", fake_st)
        monkeypatch.setattr(experiment_design_ui, "ExperimentDesignEngine", _Engine)
        experiment_design_ui.render_experiment_design_ui()
        return fake_st

    return go


def _slot_st(design, extra_state=None, pressed=()):
    """建一个「槽里已有引擎、引擎带真实 design」的手桩（**不渲染**，供变异体自己调用）。"""
    from src.experiment_design import ExperimentDesignEngine

    eng = ExperimentDesignEngine()
    eng.design = design
    state = {STATE_KEY: eng}
    state.update(extra_state or {})
    return _FakeST(session_state=_FakeSessionState(state), pressed=pressed)


def _render_with_engine_slot(monkeypatch, design, extra_state=None, pressed=()):
    """真实实现 + 「槽里已放好引擎」的形态：渲染一次，返回 fake_st。"""
    from src.ui import experiment_design_ui

    fake_st = _slot_st(design, extra_state, pressed)
    monkeypatch.setattr(experiment_design_ui, "st", fake_st)
    experiment_design_ui.render_experiment_design_ui()
    return fake_st


MUTANT_POWER_BODY_EMPTIED = (
    "                    st.markdown(format_power_report(d.power_result))",
    "                    st.markdown('')",
)
MUTANT_DOWNLOAD_DATA_RECOPIED = (
    f'                    data=st.session_state["{ARTIFACT_KEY}"],',
    f'                    data=bytearray(st.session_state["{ARTIFACT_KEY}"]),',
)
#: 实测：CPython 里 `bytes(x)` 与 `x + b""` 都会**原样返回同一对象**（只有 bytearray 才真另拷）
#: ⇒ 变异体必须用 bytearray，否则「另拷一份」这个坏形态根本没被构造出来。


def _run_mutant(fake_st, replacement):
    """把 :225-413 里某个渲染点换成坏形态，用给定 fake_st 跑一次（内存变异，不落盘、不改生产码）。"""
    from src.ui import experiment_design_ui

    source = inspect.getsource(experiment_design_ui.render_experiment_design_ui)
    old, new = replacement
    assert source.count(old) == 1, f"变异靶点认不准（命中 {source.count(old)} 处）：{old}"
    namespace = dict(vars(experiment_design_ui))
    namespace["st"] = fake_st
    exec(compile(source.replace(old, new), f"<mutant:{old.strip()[:26]}>", "exec"), namespace)
    namespace["render_experiment_design_ui"]()


# ═══════════════ 一、分支边界（对照组） ═══════════════

def test_design_none_renders_no_detail_area_at_all(render):
    """ :225 的守卫：design 为 None ⇒ :226-413 整块不执行（s922-133 只钉到这里为止）。"""
    fake_st = render(design=None)

    assert fake_st.of("subheader") == [], "design 为 None 却渲染了标题区"
    assert fake_st.of("metric") == [], "design 为 None 却渲染了概览 metric"
    assert fake_st.of("tabs") == [], "design 为 None 却渲染了五个页签"
    assert fake_st.of("dataframe") == [], "design 为 None 却渲染了时间线表"
    assert fake_st.of("download_button") == [], "design 为 None 却出现了导出按钮"
    assert POWER_EXPANDER_LABEL not in fake_st.labels_of("expander")
    assert WORD_HEADING not in fake_st.any_text()
    assert fake_st.of("caption"), "对照组至少应走到 :25 的 caption，否则手桩根本没渲染"


# ═══════════════ 二、概览与页签（:228-241） ═══════════════

def test_overview_metrics_take_values_from_the_design_object_itself(render, real_design):
    """四枚 metric 的标签钉住，取值与对象自身字段比对——不写死任何数值。"""
    d = real_design
    fake_st = render(design=d)

    metrics = {w.label(): w for w in fake_st.of("metric", )}
    assert set(metrics) == {"设计类型", "模板", "样本量", "预计时长"}, f"概览 metric 变了：{list(metrics)}"
    assert metrics["设计类型"].args[1] == d.design_type_zh
    assert metrics["模板"].args[1] == d.template_name
    assert metrics["样本量"].args[1] == f"N = {d.n_subjects}"
    assert metrics["预计时长"].args[1] == f"{d.procedure.total_duration_min}分钟"

    assert fake_st.labels_of("subheader") == [f"📋 {d.title}"]
    assert fake_st.of("tabs")[0].args[0] == tuple(TABS)
    # 容器路径确实生效：:228 的 divider 在页签之外，:367 的那枚在 📄 完整报告体内
    assert len(fake_st.of("divider")) == 5, f"divider 总数变了：{fake_st.of('divider')}"
    assert len(fake_st.of("divider", TAB_REPORT)) == 1, "按容器路径筛 divider 失效"
    assert len(fake_st.of("divider", TAB_FRAME)) == 0


# ═══════════════ 三、研究框架页与被试页（:243-285） ═══════════════

def test_research_framework_tab_renders_background_hypotheses_and_vars(render, real_design):
    """det1 体内必须真的有背景、每条假设、IV/DV/控制变量（按容器路径取，不做全局文本匹配）。"""
    d = real_design
    body = render(design=d).body(TAB_FRAME)

    assert d.background and d.background in body
    for h in d.hypotheses:
        assert h in body, f"假设未渲染进 📖 研究框架：{h}"
    for iv in d.independent_vars:
        assert iv["name"] in body, f"自变量未渲染：{iv}"
        assert str(iv.get("levels")) in body, "自变量水平数未渲染"
    for dv in d.dependent_vars:
        assert dv["name"] in body, f"因变量未渲染：{dv}"
    for cv in d.control_vars:
        assert cv in body, f"控制变量未渲染：{cv}"


def test_subjects_tab_renders_criteria_and_grouping_line(render, real_design):
    """det2 体内有纳入/排除标准；:284 `n_groups > 1` 真分支的分组文案在场。"""
    d = real_design
    body = render(design=d).body(TAB_SUBJECTS)

    for c in d.inclusion_criteria:
        assert c in body, f"纳入标准未渲染：{c}"
    for c in d.exclusion_criteria:
        assert c in body, f"排除标准未渲染：{c}"
    assert d.target_population in body
    assert d.n_groups > 1, "夹具退化了：被试间模板应给出多组"
    assert f"**分组：** {d.n_groups}组，每组{d.n_per_group}人" in body, (
        ":285 的分组文案变了（n_groups>1 真分支）"
    )


# ═══════════════ 四、统计检验力详情（:287-289） ═══════════════

def test_power_detail_expander_body_is_the_full_power_report(render, real_design):
    """:287 真 → expander 出现，且**它的体内**就是 format_power_report 全文（不是别处的副本）。

    s924-04 连动（设计档 §5「连动 2 处」之一）：夹具 medium 效应量（d=0.5）的独立 t
    现在走 A′ 未解分支，锚点断言按 solved 条件化——哨兵态下体内必须是拒答报告、
    假数段整段缺席。
    """
    from src.experiment_design import format_power_report

    d = real_design
    assert d.power_result is not None, "夹具退化了：n_subjects_hint=0 应产出 power_result"
    report = format_power_report(d.power_result)

    fake_st = render(design=d)
    expander_labels = fake_st.labels_of("expander", TAB_SUBJECTS)
    assert POWER_EXPANDER_LABEL in expander_labels, (
        f"统计检验力详情 expander 缺席（或被挪出 👥 被试与效力页）：{expander_labels}"
    )
    body = fake_st.body(TAB_SUBJECTS, POWER_EXPANDER_LABEL)
    assert report in body, ":289 的效力全文不在该 expander 体内"
    if d.power_result.solved:
        for anchor in ("统计效力分析报告", "所需总样本量", "实际达到效力", "计算前提"):
            assert anchor in body, f"效力详情缺锚点词：{anchor}"
    else:
        for anchor in ("统计效力分析报告", "无法给出样本量建议", "计算前提"):
            assert anchor in body, f"未解哨兵报告缺锚点词：{anchor}"
        assert "所需总样本量" not in body and "✅" not in body, "假数段泄漏进了未解报告"


def test_power_report_text_also_lives_in_full_report_tab(render, real_design):
    """钉住「为什么必须按容器取体」：同一份效力全文也内嵌在 📄 完整报告页 ⇒ 全局文本断言会失明。"""
    from src.experiment_design import format_power_report

    d = real_design
    report = format_power_report(d.power_result)
    fake_st = render(design=d)

    assert report in fake_st.body(TAB_REPORT), "完整报告页不再内嵌效力段——本用例的失明面已变化"
    assert report not in fake_st.body(TAB_FRAME), "效力段跑进了 📖 研究框架页？归属需复核"


def test_power_detail_expander_absent_when_power_result_is_none(monkeypatch, real_design):
    """:287 假分支：引擎 :150-154（用户指定样本量）会置 power_result=None ⇒ 详情不出现。"""
    from src.experiment_design import ExperimentDesignEngine

    eng = ExperimentDesignEngine()
    d = eng.design_experiment(**{**DESIGN_KWARGS, "n_subjects_hint": 60})
    assert d.power_result is None, "引擎行为已变（:154 不再置 None），本对照组失效——请复核"
    assert d.procedure is not None and d.n_subjects == 60

    fake_st = _render_with_engine_slot(monkeypatch, d)
    assert POWER_EXPANDER_LABEL not in fake_st.labels_of("expander"), (
        "power_result 为 None 却渲染了检验力详情 ⇒ :287 守卫失效"
    )
    assert RANDOM_EXPANDER_LABEL in fake_st.labels_of("expander"), "对照：程序页应仍正常渲染"
    assert f"N = {d.n_subjects}" in fake_st.body(TAB_SUBJECTS)


# ═══════════════ 五、程序页与分析页（:291-350） ═══════════════

def test_procedure_tab_renders_materials_timeline_table_and_phases(render, real_design):
    """:292-324：材料 / 设备 / 时间线表（行数 == timeline 长度）/ 各阶段 expander。"""
    d = real_design
    fake_st = render(design=d)
    body = fake_st.body(TAB_PROCEDURE)

    frames = [w.args[0] for w in fake_st.of("dataframe", TAB_PROCEDURE)]
    assert len(frames) == 1, f"时间线表应恰好一张，实际 {len(frames)}"
    assert len(frames[0]) == len(d.procedure.timeline), (
        "时间线表行数与 procedure.timeline 不一致（列映射被改过？）"
    )
    assert list(frames[0].columns) == ["阶段", "开始(分钟)", "结束(分钟)", "时长(分钟)"]

    for m in d.materials:
        assert m["name"] in body, f"材料未渲染：{m}"
    for a in d.apparatus:
        assert a in body, f"设备未渲染：{a}"
    for phase in d.procedure.phases:
        assert (f"阶段{phase['phase']}: {phase['name']}"
                f"（{phase['duration_min']}分钟）") in fake_st.labels_of(
            "expander", TAB_PROCEDURE), f"阶段 expander 未渲染：{phase['phase']} {phase['name']}"
        assert phase["description"] in body, f"阶段说明未渲染：{phase['phase']}"

    assert RANDOM_EXPANDER_LABEL in fake_st.labels_of("expander", TAB_PROCEDURE)
    assert d.procedure.randomization["method"] in body
    assert not d.procedure.counterbalancing, "夹具退化了：被试间模板不该有平衡方案"
    assert "⚖ 顺序平衡方案" not in fake_st.labels_of("expander"), ":338 假分支被渲染了"


def test_analysis_tab_and_full_report_tab_render_their_sources(render, real_design):
    """det4 渲染 analysis_plan_detailed 原文；det5 渲染 format_design_report() 全文。"""
    from src.experiment_design import ExperimentDesignEngine

    eng = ExperimentDesignEngine()
    d = real_design
    eng.design = d
    report = eng.format_design_report()

    fake_st = render(design=d)
    assert d.analysis_plan_detailed in fake_st.body(TAB_ANALYSIS), "📊 分析计划页未渲染详细计划"
    assert report in fake_st.body(TAB_REPORT), "📄 完整报告页未渲染报告全文"
    assert any("生成/刷新报告" in str(l) for l in fake_st.labels_of("button", TAB_REPORT)), (
        ":354 的刷新按钮未出现在 📄 完整报告页内"
    )


def test_markdown_download_link_uses_sanitized_title(render, real_design):
    """:360-364：Markdown 导出链接的 base64 data URI 与安全化后的下载文件名。"""
    import base64

    from src.experiment_design import ExperimentDesignEngine

    eng = ExperimentDesignEngine()
    eng.design = real_design
    report = eng.format_design_report()

    fake_st = render(design=real_design)
    hrefs = [w for w in fake_st.of("markdown", TAB_REPORT)
             if isinstance(w.label(), str) and "download=" in w.label()]
    assert len(hrefs) == 1, f"Markdown 导出链接应恰好一条，实际 {len(hrefs)}"
    href = hrefs[0].label()
    assert hrefs[0].kwargs.get("unsafe_allow_html") is True
    title_safe = real_design.title.replace("/", "-").replace(":", "")
    assert title_safe and ":" not in title_safe, "标题里的冒号没被安全化掉"
    assert f'download="{title_safe}_实验设计方案.md"' in href
    assert "点击下载 Markdown 文件" in href
    payload = href.split("base64,", 1)[1].split('"', 1)[0]
    assert base64.b64decode(payload) == report.encode("utf-8"), "data URI 里的正文与报告全文不一致"


# ═══════════════ 六、Word 导出区（:366-389） ═══════════════

def test_word_export_section_anchors_and_completeness_hint(render, real_design):
    """Word 区标题 / 说明 / 研究者输入框 key 在场；完整度提示走哪支由现场重算决定。"""
    from src.output.docx_exporter import count_protocol_placeholders

    d = real_design
    fake_st = render(design=d)

    body = fake_st.body(TAB_REPORT)
    assert WORD_HEADING in body, "Word 区标题未渲染"
    captions = " ".join(str(w.label()) for w in fake_st.of("caption", TAB_REPORT))
    assert ".docx" in captions and "预注册附件" in captions, f"Word 区说明文案变了：{captions}"

    researchers = [w for w in fake_st.of("text_input", TAB_REPORT) if w.kwargs.get("key") == RESEARCHER_KEY]
    assert len(researchers) == 1, f"研究者姓名框（key={RESEARCHER_KEY}）缺席或重复：{len(researchers)}"
    assert WORD_BUTTON_LABEL in fake_st.labels_of("button", TAB_REPORT), "生成按钮未出现"

    # 提示文案里的待补项数必须与同一个函数重算的值同源——本用例不新增任何数值结论。
    n_missing = count_protocol_placeholders(d)
    warns = [str(w.label()) for w in fake_st.of("warning", TAB_REPORT)]
    oks = [str(w.label()) for w in fake_st.of("success", TAB_REPORT)]
    if n_missing >= 3:
        assert any("待补充事项清单" in t for t in warns), f"应出 warning 分支：n_missing={n_missing}"
        hint = warns
    else:
        assert any("文档完整度良好" in t for t in oks), f"应出 success 分支：n_missing={n_missing}"
        hint = oks
    assert hint and str(n_missing) in hint[0], (
        f"提示文案与 count_protocol_placeholders 重算值不同源：{hint} vs {n_missing}"
    )


# ═══════════════ 七、生成 / 下载两个入口（:391-413） ═══════════════

def test_download_button_hidden_until_artifact_exists(render, real_design):
    """没工件 ⇒ :403 守卫为假 ⇒ 下载入口不出现；且 :400 的 except 让失败对用户可见。"""
    fake_st = render(design=real_design, pressed=(WORD_BUTTON_LABEL,))

    assert ARTIFACT_KEY not in fake_st.session_state, (
        "工件已落会话——本用例的前提（真实设计导出必失败）已变化："
        "docx_exporter 的两处类型漂移若已修，请把本用例改成正向断言（见 xfail 那条）"
    )
    assert fake_st.of("download_button") == [], "工件不存在却出现了下载按钮"
    errors = [str(w.label()) for w in fake_st.of("error", TAB_REPORT)]
    assert any(t.startswith("生成失败：") for t in errors), (
        f":400 的 except 分支应把失败暴露给用户，实际 error={errors}"
    )


def test_download_button_uses_the_exact_artifact_object(render, real_design):
    """工件在会话里 ⇒ :404 出现，data 必须是**同一个字节对象**（`is` 护栏，防「另拷一份」）。"""
    artifact = b"PK\x03\x04fake-docx-bytes"
    fake_st = render(design=real_design, extra_state={
        ARTIFACT_KEY: artifact, FILENAME_KEY: "实验程序文档_测试.docx"})

    btns = fake_st.of("download_button", TAB_REPORT)
    assert len(btns) == 1, f"下载按钮应恰好一枚，实际 {len(btns)}"
    btn = btns[0]
    assert btn.label() == DOWNLOAD_LABEL
    assert btn.kwargs["data"] is artifact, "下载的数据不是会话里那个工件对象"
    assert btn.kwargs["data"] == artifact
    assert btn.kwargs["file_name"] == "实验程序文档_测试.docx"
    assert btn.kwargs["mime"] == DOCX_MIME
    assert btn.kwargs["key"] == "exp_protocol_dl"


def test_download_button_falls_back_to_default_filename(render, real_design):
    """:407-409 缺省分支：只有工件、没有文件名键时用「实验程序文档.docx」，且不偷偷写键。"""
    fake_st = render(design=real_design, extra_state={ARTIFACT_KEY: b"PK\x03\x04x"})

    btns = fake_st.of("download_button", TAB_REPORT)
    assert len(btns) == 1
    assert btns[0].kwargs["file_name"] == "实验程序文档.docx", (
        f"缺省文件名变了：{btns[0].kwargs['file_name']}"
    )
    assert FILENAME_KEY not in fake_st.session_state, "缺省分支不该写入文件名键"


@pytest.mark.xfail(
    raises=TypeError,
    strict=True,
    reason=(
        "在册缺陷（s923-40 登记，交人工裁决，本单不改生产码）："
        "docx_exporter.py:779 把 ethics、:807 把 notes（ExperimentDesign 里是 List[str]）"
        "直接喂给 _add_paragraph_with_inline_format(str) ⇒ TypeError ⇒ UI 侧 Word 导出永远失败。"
        "修好后本例变 XPASS 会当场报警，届时请同步翻 "
        "test_download_button_hidden_until_artifact_exists 的前提。"
    ),
)
def test_real_design_can_actually_be_exported_to_docx(real_design):
    """生产意图：真实设计应当能导出 .docx。现状不能 ⇒ 以 xfail(strict) 登记，不钉成绿灯。"""
    from src.output.docx_exporter import build_experiment_protocol_docx

    docx_bytes = build_experiment_protocol_docx(real_design, researcher="张三")
    assert isinstance(docx_bytes, bytes) and docx_bytes[:2] == b"PK"


# ═══════════════ 八、判别力自证：两种「静默失明的绿」必须被抓住 ═══════════════

def test_pin_discriminates_emptied_power_report_mutant(monkeypatch, real_design):
    """变异①：expander 标签仍在、体内换成空串 ⇒ 标签断言会假绿，本套件的**体内**断言判红。"""
    from src.experiment_design import format_power_report

    report = format_power_report(real_design.power_result)

    fake_st = _render_with_engine_slot(monkeypatch, real_design)
    assert report in fake_st.body(TAB_SUBJECTS, POWER_EXPANDER_LABEL)     # 真实实现通过

    empty_st = _slot_st(real_design)                                       # 变异体专用新桩
    _run_mutant(empty_st, MUTANT_POWER_BODY_EMPTIED)

    assert POWER_EXPANDER_LABEL in empty_st.labels_of("expander", TAB_SUBJECTS), (
        "变异体连 expander 都没渲染 ⇒ 靶点失效，本自证无效（应只掏空内容）"
    )
    assert report not in empty_st.body(TAB_SUBJECTS, POWER_EXPANDER_LABEL), (
        "掏空体内容的变异体竟仍通过体内断言 ⇒ 本套件的效力详情断言无判别力"
    )


def test_pin_discriminates_regenerated_artifact_download_mutant(monkeypatch, real_design):
    """变异②：下载 data 换成「内容相同的另一份字节」⇒ `==` 仍绿，本套件的 `is` 护栏判红。"""
    artifact = b"PK\x03\x04fake-docx-bytes"

    ok_st = _render_with_engine_slot(monkeypatch, real_design, {ARTIFACT_KEY: artifact})
    assert ok_st.of("download_button")[0].kwargs["data"] is artifact      # 真实实现通过

    copy_st = _slot_st(real_design, {ARTIFACT_KEY: artifact})               # 变异体专用新桩
    _run_mutant(copy_st, MUTANT_DOWNLOAD_DATA_RECOPIED)

    btns = copy_st.of("download_button")
    assert len(btns) == 1, "变异体没渲染出下载按钮，靶点失效"
    assert btns[0].kwargs["data"] == artifact, "变异体没生效（连内容都变了）"
    assert btns[0].kwargs["data"] is not artifact, (
        "另拷一份的变异体竟仍是同一对象 ⇒ 本套件的 is 护栏无判别力"
    )
