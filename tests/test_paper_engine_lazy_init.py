# -*- coding: utf-8 -*-
"""src/ui/paper_writing_ui.py:41 引擎懒初始化 ＋ :591 借数守卫 行为钉桩（s922-134）。

**锚点复核（开工第一步，2026-09-22）：**
- :41 「if st.session_state.paper_engine is None:」——与工单**逐字一致**（无漂移），:42 写回、
  :44 取用（本页唯一消费点）。
- 工单标的「:596 analysis_output 借数」磁盘实况为 **:591**（守卫原文逐字一致，仅行号差 5；
  工单引文缩进 8 空格、磁盘 4 空格 ⇒ 该块被去嵌套过一次）。按磁盘实况钉，**不在用例里硬编码行号**，
  只锚定文本（行号漂移不该判红，「原文被改写」才该判红）。

**钉的是行为，不是长相（与 s922-133 experiment_engine 同构）：**

1. 引擎槽为 None（生产首帧：app.py 的 _defaults 落 None）→ 建引擎并**写回会话**；
2. 槽里已有引擎 → **复用同一对象**（is 断言，构造计数必须为 0）——防 678 行大 mode 重构把「复用」
   改成「每帧重建」，那会丢引擎内状态（state / logs）；
3. 槽为 None 时重建，但**跨帧只建一次**；
4. **借数**（:591）：analysis_output 非空 且 引擎无结果 且 点了导入按钮 → 导入函数**恰好被调 1 次**，
   且落在会话里那个引擎上；桩复刻真实现写回 state.analysis_results 后**第二帧不再借**（一次性闭环）；
   反过来——引擎已有结果 / 没有 analysis_output → **一次都不调**（守卫两个合取项各自有效）。

实现口径（与既有桩同路，零网络、零 LLM、零真实会话）：
- 手桩 st（非 AppTest）：只替换 UI 模块属性 paper_writing_ui.st；假 st 的取值/容器语义沿用
  tests/test_paper_writing_ui_charac.py（s920-09）那套「宽容记录型」，**按钮默认 False**（否则会误入
  重置/导入分支把复用用例打成假红），只对点名的 key / label 为真。
- st.rerun() 抛 RerunRequested(BaseException)：真实 RerunException 的基类是 BaseException，
  except Exception 吞不掉——假 st 若只返回，会把「导入后重跑」这条尾巴钉歪。
- 判别力自证：把 :41 守卫在内存里变异成「每帧重建」后重跑，必须判红
  （test_pin_discriminates_per_frame_rebuild_mutant），保证本套件不是空转。

**变更（2026-09-23 夜间班 s922-134 复跑）**：本件由 2026-09-22 21:25 的日间班落盘但**未收单**，
      复跑时 `test_borrow_guard_discriminates_duplicate_import_mutant` **是红的**（`len(imported)==0`）。
      根因不是生产码，而是**桩位打错类**（:380 与 :460 把 `import_analysis_results` 打到 harness 的
      `_CountingEngine` 子类上，而被检对象 `seeded` 是 `real_engine_cls` 父类实例 ⇒ 桩根本没生效）。
      两处桩位已按 `real_engine_cls` 修正，并新增 `test_stub_must_target_the_seeded_instance_class`
      把这个"假靶"钉成断言。现况：**13 passed**。

**不改 src/ui/paper_writing_ui.py、不改 app.py。**
"""
from __future__ import annotations

import ast
import inspect
import socket
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PY_PATH = REPO_ROOT / "app.py"

STATE_KEY = "paper_engine"
OUTPUT_KEY = "analysis_output"
IMPORT_BUTTON_KEY = "import_analysis"

#: :41 守卫原文——变异体测试的替换靶点；被重构改写时本文件当场红（强制后来人更新钉桩）
GUARD_SOURCE = "if st.session_state.paper_engine is None:"
#: :591 借数守卫原文（两个合取项：有输出 且 引擎无结果）
BORROW_GUARD_SOURCE = (
    'if st.session_state.get("analysis_output") is not None '
    "and not engine.state.analysis_results:"
)
#: :598 借数调用原文——钉「一次调用」的落点
BORROW_CALL_SOURCE = "engine.import_analysis_results({test_type: output})"
#: :595 借数按钮原文（key 是用例点击的把手）
BORROW_BUTTON_SOURCE = 'st.button("📥 导入当前分析结果", key="import_analysis")'


# ═══════════════ 手桩：SessionStateProxy / 容器 / st ═══════════════

class RerunRequested(BaseException):
    """真实 st.rerun() 抛 RerunException，其基类是 **BaseException**
    （streamlit/runtime/scriptrunner_utils/exceptions.py）⇒ 业务代码里的 except Exception 吞不掉它。
    假 st 若只返回、或派生自 Exception，就会把「导入成功后重跑」这条尾巴钉歪。"""


class _FakeSessionState(dict):
    """Streamlit SessionStateProxy 最小复刻。

    属性读**缺键抛 AttributeError**（1.59.1 实测，不是返回 None），属性写落到字典——
    这正是 :41 属性式读取之所以安全 / 不安全的分水岭。
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(
                f"st.session_state has no attribute '{name}'. Did you forget to initialize it?"
            ) from exc

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        self.pop(name, None)


class _FakeCtx:
    """可 with 的容器桩（sidebar / tabs / columns / expander / spinner / container）。"""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeST:
    """够渲染 paper_writing_ui 默认路径的手桩（取值语义沿用 test_paper_writing_ui_charac.py）。

    按钮默认 **False**（用户没点），只有 clicked_keys 点名的 key / label 才为真；
    rerun 抛 RerunRequested；其余展示类 API 记录后返回 None。
    """

    def __init__(self, session_state=None, clicked_keys=()):
        self.session_state = session_state if session_state is not None else _FakeSessionState()
        self.calls = []
        self.clicked_keys = set(clicked_keys)
        self.sidebar = _FakeCtx()

    # ── 容器 ──
    def columns(self, spec, **kwargs):
        n = spec if isinstance(spec, int) else len(spec)
        return [_FakeCtx() for _ in range(n)]

    def tabs(self, labels, **kwargs):
        return [_FakeCtx() for _ in labels]

    def expander(self, *args, **kwargs):
        return _FakeCtx()

    def spinner(self, *args, **kwargs):
        return _FakeCtx()

    def container(self, *args, **kwargs):
        return _FakeCtx()

    def form(self, *args, **kwargs):
        return _FakeCtx()

    # ── 布尔控件：默认 False，只认点名的 key / label ──
    def button(self, *args, **kwargs):
        self.calls.append(("button", args, kwargs))
        key = kwargs.get("key")
        label = args[0] if args else None
        return bool((key and key in self.clicked_keys) or (label and label in self.clicked_keys))

    def checkbox(self, *args, **kwargs):
        return kwargs.get("value", False)

    def toggle(self, *args, **kwargs):
        return False

    def download_button(self, *args, **kwargs):
        return False

    def form_submit_button(self, *args, **kwargs):
        return False

    # ── 取值控件 ──
    def text_input(self, *args, **kwargs):
        return kwargs.get("value") or ""

    def text_area(self, *args, **kwargs):
        return kwargs.get("value") or ""

    def radio(self, *args, **kwargs):
        options = args[1] if len(args) > 1 else kwargs.get("options", [])
        return options[0] if options else None

    def selectbox(self, *args, **kwargs):
        options = args[1] if len(args) > 1 else kwargs.get("options", [])
        return options[0] if options else kwargs.get("value")

    def multiselect(self, *args, **kwargs):
        return []

    def slider(self, *args, **kwargs):
        if "value" in kwargs:
            return kwargs["value"]
        return args[3] if len(args) > 3 else (args[1] if len(args) > 1 else 0)

    def number_input(self, *args, **kwargs):
        return kwargs.get("value", 0)

    def file_uploader(self, *args, **kwargs):
        return None

    # ── 重跑：真实语义是抛（BaseException 系），不是返回 ──
    def rerun(self, *args, **kwargs):
        self.calls.append(("rerun", args, kwargs))
        raise RerunRequested()

    # ── 其余（展示类）：记录后返回 None ──
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _display(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return None

        return _display

    # ── 断言辅助 ──
    @property
    def names(self):
        return [c[0] for c in self.calls]

    def msgs(self, kind):
        return [str(c[1][0]) for c in self.calls if c[0] == kind and c[1]]

    def button_keys(self):
        return [c[2].get("key") for c in self.calls if c[0] == "button"]


# ═══════════════ 夹具 ═══════════════

@pytest.fixture()
def harness(monkeypatch):
    """UI 模块的 st 换成手桩；引擎构造装计数器。返回 (模块, fake_st, built, real_cls)。"""
    from src.ui import paper_writing_ui

    real_engine_cls = paper_writing_ui.PaperEngine          # 打桩前抓住真实类
    fake_st = _FakeST()
    built: list = []

    class _CountingEngine(real_engine_cls):
        def __init__(self):
            super().__init__()
            built.append(self)

    monkeypatch.setattr(paper_writing_ui, "st", fake_st)
    monkeypatch.setattr(paper_writing_ui, "PaperEngine", _CountingEngine)
    return paper_writing_ui, fake_st, built, real_engine_cls


def _app_defaults() -> dict:
    """按 app.py 磁盘实况用 AST 取 _defaults 字面量（不执行 app.py，不落任何副作用）。"""
    tree = ast.parse(APP_PY_PATH.read_text(encoding="utf-8"), filename=str(APP_PY_PATH))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_defaults" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    pytest.fail("app.py 里找不到模块级 _defaults 字面量——会话初始化表被搬走 / 改写了？")


def _apply_defaults(state: _FakeSessionState) -> None:
    """复刻 app.py 的落键循环（:116）：仅在缺键时补种。"""
    for key, val in _app_defaults().items():
        if key not in state:
            state[key] = val


def _render_source(ui) -> str:
    return inspect.getsource(ui.render_paper_writing_ui)


# ═══════════════ 一、必置前提：_defaults 必须有这两个键 ═══════════════

def test_app_defaults_seeds_paper_engine_and_analysis_output_slots():
    """ :41 的读点无外层守卫 ⇒ 唯一保险是 app.py 的 _defaults 无条件补种；补种没了就是整页红。"""
    defaults = _app_defaults()
    assert STATE_KEY in defaults, (
        f"app.py 的 _defaults 少了 {STATE_KEY}：paper_writing_ui.py:41 的属性式读取"
        "会退化成 AttributeError（键不存在），而该读点没有外层守卫"
    )
    assert defaults[STATE_KEY] is None, "初值必须是 None（懒初始化的触发值），否则首帧不会建引擎"
    assert OUTPUT_KEY in defaults and defaults[OUTPUT_KEY] is None, (
        "analysis_output 是借数守卫（:591）的输入键，必须由 _defaults 置 None"
    )

    app_src = APP_PY_PATH.read_text(encoding="utf-8")
    assert "for key, val in _defaults.items():" in app_src and (
        "if key not in st.session_state:" in app_src
    ), "app.py 的 _defaults 落键循环改了形状——「必置」保证需重新核对"


# ═══════════════ 二、懒初始化三态 ═══════════════

def test_none_slot_builds_engine_and_writes_back(harness):
    """态①（生产首帧）：槽为 None → 建引擎、写回会话、只建一次。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)                  # 复刻 app.py 启动补种
    assert fake_st.session_state[STATE_KEY] is None

    ui.render_paper_writing_ui()

    eng = fake_st.session_state[STATE_KEY]
    assert eng is not None, "槽为 None 时没有建引擎（懒初始化丢失）"
    assert isinstance(eng, ui.PaperEngine)
    assert len(built) == 1, f"首帧应恰好构造 1 个引擎，实际 {len(built)}"
    assert eng is built[0], "写回的必须是刚构造的那个对象"
    assert eng.state.analysis_results == {}, "新引擎应是无分析结果的干净状态（借数守卫的触发前提）"


def test_existing_engine_is_reused_by_identity(harness):
    """态②（承重用例）：槽里已有引擎 → 复用**同一对象**（is），不得每帧重建（会丢引擎内状态）。"""
    ui, fake_st, built, real_engine_cls = harness
    _apply_defaults(fake_st.session_state)
    seeded = real_engine_cls()                               # 走真实实现，不经计数器
    seeded.state.logs.append("sentinel-已在引擎里")            # 引擎内状态不得被重建冲掉
    seeded.pin_sentinel = "跨帧存活标记"
    fake_st.session_state[STATE_KEY] = seeded

    ui.render_paper_writing_ui()

    reused = fake_st.session_state[STATE_KEY]
    assert reused is seeded, "引擎被换成了新对象——复用被改成每帧重建（引擎内状态已丢）"
    assert built == [], f"槽里已有引擎却仍构造了 {len(built)} 个新引擎"
    assert reused.state.logs == ["sentinel-已在引擎里"]
    assert reused.pin_sentinel == "跨帧存活标记"


def test_none_slot_rebuild_is_once_across_frames(harness):
    """态③跨帧：None 首帧重建，第二帧必须复用（构造计数恒为 1）。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)

    ui.render_paper_writing_ui()
    first = fake_st.session_state[STATE_KEY]

    ui.render_paper_writing_ui()
    second = fake_st.session_state[STATE_KEY]

    assert len(built) == 1, f"两帧共构造 {len(built)} 个引擎——第二帧发生了重建"
    assert second is first, "第二帧换掉了引擎对象（每帧重建）"


# ═══════════════ 三、借数守卫（:591）：导入恰好 1 次 ═══════════════

def test_borrow_import_is_called_exactly_once(harness, monkeypatch):
    """借数正例：有 analysis_output + 引擎无结果 + 点了导入 → 导入函数被调**恰 1 次**，且落在会话引擎上。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)
    output = {"test_type": "pearson_corr", "test_name_zh": "Pearson相关"}
    fake_st.session_state[OUTPUT_KEY] = output
    fake_st.clicked_keys.add(IMPORT_BUTTON_KEY)

    imported: list = []

    def _stub_import(self, outputs):                          # 桩掉真实现（不落任何真实导入副作用）
        imported.append((self, outputs))

    monkeypatch.setattr(ui.PaperEngine, "import_analysis_results", _stub_import)

    with pytest.raises(RerunRequested):                       # 导入成功 ⇒ 立刻重跑让新数据回灌
        ui.render_paper_writing_ui()

    assert IMPORT_BUTTON_KEY in fake_st.button_keys(), (
        "借数按钮根本没渲染出来——用例没钉到目标路径（守卫第一个合取项已失效？）"
    )
    assert len(imported) == 1, f"借数路径应恰好导入 1 次，实际 {len(imported)}"
    engine, payload = imported[0]
    assert engine is fake_st.session_state[STATE_KEY], (
        "导入必须发生在会话里那个引擎上，而不是临时新建 / 别的对象"
    )
    assert engine is built[0], "同一帧里懒初始化应先建引擎，再被借数用上（顺序反转即错）"
    assert payload == {"pearson_corr": output}, f"导入载荷形状变了：{payload!r}"
    assert payload["pearson_corr"] is output, "导入的必须是会话里那份输出对象本身（不是拷贝）"


def test_borrow_is_one_shot_because_import_writes_engine_state(harness, monkeypatch):
    """借数闭环：桩复刻真实现的唯一副作用（写回 state.analysis_results）⇒ 第二帧不再借（两帧合计仍 1 次）。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)
    fake_st.session_state[OUTPUT_KEY] = {"test_type": "ttest"}
    fake_st.clicked_keys.add(IMPORT_BUTTON_KEY)

    imported: list = []

    def _stub_import(self, outputs):
        imported.append(outputs)
        self.state.analysis_results = outputs                # 复刻 paper_engine.py:151

    monkeypatch.setattr(ui.PaperEngine, "import_analysis_results", _stub_import)

    with pytest.raises(RerunRequested):
        ui.render_paper_writing_ui()                         # 帧 1：借到 → 导入（1 次）
    ui.render_paper_writing_ui()                             # 帧 2：引擎已有结果 ⇒ 守卫第二项为假

    assert len(imported) == 1, f"两帧合计应只导入 1 次，实际 {len(imported)}"
    assert fake_st.session_state[STATE_KEY].state.analysis_results == {"ttest": {"test_type": "ttest"}}


def test_no_borrow_when_engine_already_has_results(harness, monkeypatch):
    """借数反例（守卫第二个合取项）：引擎已有结果 → 即便有输出且点了按钮，也一次都不导入。"""
    ui, fake_st, built, real_engine_cls = harness
    _apply_defaults(fake_st.session_state)
    seeded = real_engine_cls()
    seeded.state.analysis_results = {"anova": {"test_type": "anova"}}
    fake_st.session_state[STATE_KEY] = seeded
    fake_st.session_state[OUTPUT_KEY] = {"test_type": "pearson_corr"}
    fake_st.clicked_keys.add(IMPORT_BUTTON_KEY)

    imported: list = []
    # ⚠️ 桩必须打在 seeded 的**真实类**上：harness 把 ui.PaperEngine 换成了 _CountingEngine（子类），
    #    而 seeded 是 real_engine_cls（父类）实例 ⇒ 打子类属性对 seeded 无效（2026-09-23 修正的红字原因）。
    monkeypatch.setattr(real_engine_cls, "import_analysis_results",
                        lambda self, outputs: imported.append(outputs))

    ui.render_paper_writing_ui()                             # 不抛 = 没走到重跑（借数块整段跳过）

    assert imported == [], "引擎已有分析结果却仍触发借数导入（重复导入会把已改过的结果冲掉）"
    assert IMPORT_BUTTON_KEY not in fake_st.button_keys(), "守卫为假时不该渲染借数按钮"
    assert built == [], "引擎已存在时不该重建"


def test_no_borrow_when_analysis_output_is_absent(harness, monkeypatch):
    """借数反例（守卫第一个合取项）：没有 analysis_output → 一次都不导入。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)
    assert fake_st.session_state[OUTPUT_KEY] is None
    fake_st.clicked_keys.add(IMPORT_BUTTON_KEY)

    imported: list = []
    monkeypatch.setattr(ui.PaperEngine, "import_analysis_results",
                        lambda self, outputs: imported.append(outputs))

    ui.render_paper_writing_ui()

    assert imported == [], "没有分析输出却触发了借数导入"
    assert IMPORT_BUTTON_KEY not in fake_st.button_keys(), "没有输出时不该渲染借数按钮"


def test_stub_must_target_the_seeded_instance_class(harness, monkeypatch):
    """防复发（s922-134 复跑时踩到的假靶）：桩打在 harness 的子类上，对**父类实例**不生效。

    harness 把 `ui.PaperEngine` 换成了 `_CountingEngine(real_engine_cls)` 子类 ⇒
    `monkeypatch.setattr(ui.PaperEngine, ...)` 只能命中"懒初始化新建的引擎"，
    命中不了手工 `seeded = real_engine_cls()` 那个父类实例。
    凡是先塞 seeded 再断"导入次数"的用例，桩必须打在 `real_engine_cls` 上
    （:380 与 :460 两处就是这么修的）。本用例把这个陷阱钉成断言，免得下次又写回子类。
    """
    ui, fake_st, built, real_engine_cls = harness
    seeded = real_engine_cls()
    calls: list = []

    monkeypatch.setattr(ui.PaperEngine, "import_analysis_results",
                        lambda self, outputs: calls.append(("child-patch", outputs)))
    seeded.import_analysis_results({"probe": 1})
    assert calls == [], "子类桩竟命中了父类实例 ⇒ harness 的类关系变了，本套件的桩位需重排"

    monkeypatch.setattr(real_engine_cls, "import_analysis_results",
                        lambda self, outputs: calls.append(("parent-patch", outputs)))
    seeded.import_analysis_results({"probe": 1})
    assert calls == [("parent-patch", {"probe": 1})], "父类桩没生效 ⇒ 借数用例失去计数能力"
    assert not isinstance(seeded, ui.PaperEngine), "seeded 竟已是 harness 子类，前提变了"


# ═══════════════ 四、锚点原文 + 判别力自证 + 纯本地 ═══════════════

def test_source_anchors_are_still_intact(harness):
    """两处守卫与借数调用的**原文**仍在（文本锚定；行号漂移不算，原文被改写才算）。"""
    ui, _fake_st, _built, _real = harness
    source = _render_source(ui)

    assert source.count(GUARD_SOURCE) == 1, (
        f"懒初始化守卫原文变了（现存 {source.count(GUARD_SOURCE)} 处）——请更新 GUARD_SOURCE 与用例"
    )
    assert source.count(BORROW_GUARD_SOURCE) == 1, (
        f"借数守卫原文变了（现存 {source.count(BORROW_GUARD_SOURCE)} 处）——请更新 BORROW_GUARD_SOURCE 与用例"
    )
    assert BORROW_CALL_SOURCE in source, "借数调用形状变了（{test_type: output} 载荷）"
    assert BORROW_BUTTON_SOURCE in source, "借数按钮的 key 变了——用例的点击把手失效"


def test_pin_discriminates_per_frame_rebuild_mutant(harness):
    """变异体：把 :41 守卫改成「每帧重建」，本套件的复用不变量必须判红（证明钉桩非空转）。"""
    ui, fake_st, built, real_engine_cls = harness
    source = _render_source(ui)
    assert source.count(GUARD_SOURCE) == 1, "守卫原文变了，变异体测试失去靶点"

    namespace = dict(vars(ui))
    namespace["st"] = fake_st
    namespace["PaperEngine"] = type("MutantEngine", (ui.PaperEngine,), {})
    exec(compile(source.replace(GUARD_SOURCE, "if True:  # 变异：每帧重建"),
                 "<mutant:per-frame-rebuild>", "exec"), namespace)
    mutant_render = namespace["render_paper_writing_ui"]

    _apply_defaults(fake_st.session_state)
    seeded = real_engine_cls()                               # 不走计数器，built 只统计变异体建的对象
    fake_st.session_state[STATE_KEY] = seeded

    mutant_render()
    mutant_render()

    replaced = fake_st.session_state[STATE_KEY]
    assert replaced is not seeded, "变异体没生效，判别力自证无效（守卫替换失败）"
    assert len(built) == 2, f"变异体两帧应重建 2 次（被本套件判红的锚点），实际 {len(built)}"


def test_borrow_guard_discriminates_duplicate_import_mutant(harness, monkeypatch):
    """变异体：把 :591 借数守卫改成恒真 → 引擎已有结果时仍会重复导入，本套件判红（借数那一半钉也不是空转）。"""
    ui, fake_st, built, real_engine_cls = harness
    source = _render_source(ui)
    assert source.count(BORROW_GUARD_SOURCE) == 1, "借数守卫原文变了，变异体测试失去靶点"

    namespace = dict(vars(ui))
    namespace["st"] = fake_st
    namespace["PaperEngine"] = type("MutantEngine", (ui.PaperEngine,), {})
    exec(compile(source.replace(BORROW_GUARD_SOURCE, "if True:  # 变异：守卫恒真"),
                 "<mutant:borrow-always>", "exec"), namespace)
    mutant_render = namespace["render_paper_writing_ui"]

    _apply_defaults(fake_st.session_state)
    seeded = real_engine_cls()
    seeded.state.analysis_results = {"anova": {"test_type": "anova"}}   # 引擎已有结果：真代码该整段跳过
    fake_st.session_state[STATE_KEY] = seeded
    fake_st.session_state[OUTPUT_KEY] = {"test_type": "pearson_corr"}
    fake_st.clicked_keys.add(IMPORT_BUTTON_KEY)

    imported: list = []
    # 同上：桩打在 seeded 的真实类上，否则变异体跑的是真导入，计数恒 0（s922-134 复跑时发现的假靶）。
    monkeypatch.setattr(real_engine_cls, "import_analysis_results",
                        lambda self, outputs: imported.append(outputs))

    with pytest.raises(RerunRequested):
        mutant_render()

    assert len(imported) == 1, (
        "变异体没生效（或真代码本来就恒真）——借数守卫对「引擎已有结果」的拦截是假的"
    )
    assert imported[0] == {"pearson_corr": {"test_type": "pearson_corr"}}
    assert built == [], "变异体不该重建已有引擎"


def test_engine_construction_is_local_only(monkeypatch):
    """引擎构造纯本地：断网（socket 换炸雷）下仍能建——首帧懒初始化不得依赖任何外部服务。"""
    from src.paper_writer import PaperEngine

    def _no_network(*args, **kwargs):
        raise AssertionError("PaperEngine 构造触网了")

    monkeypatch.setattr(socket, "socket", _no_network)

    eng = PaperEngine()

    assert eng.state.analysis_results == {}, "新引擎不该自带分析结果（借数守卫的触发前提）"
    assert eng.lit_manager.entries, "预置文献库应是纯内存加载（无网也有货）"
