"""src/ui/experiment_design_ui.py:19-22 实验引擎懒初始化钉桩（s922-133）。

普查命中形态（docs/insights/psy-session-state-attr-read-census-20260921.md:64-65）：
「必置·_defaults（读点无外层守卫）」——:

    if st.session_state.experiment_engine is None:                      # :19
        st.session_state.experiment_engine = ExperimentDesignEngine()   # :20
    eng = st.session_state.experiment_engine                            # :22

本文件钉的是这段懒初始化的**行为**（不是文本长相）：

1. 引擎槽为 None（生产首帧形态：app.py 的 _defaults 落 None）→ 建引擎并**写回会话**；
2. 槽里已有引擎 → **复用同一对象**（is 断言，构造计数必须为 0）——防重构把「复用」改成
   「每帧重建」，那会丢引擎内状态（design / logs）；
3. 槽为 None 时重建，但**跨帧只建一次**；
4. 键真的不存在时：按 Streamlit 真实语义（1.59.1，.venv 内源码实测：
   SessionStateProxy.__getattr__ 缺键 raise AttributeError，**不是返回 None**）本读点会抛
   AttributeError——该不可达性由 app.py 的 _defaults 无条件补种保证，故把那份补种一并钉住。

实现口径：
- 手桩 st（非 AppTest）：只替换 UI 模块属性 experiment_design_ui.st，与
  test_export_gate_global_scan.py 的 fake_st 手法同路；渲染全程纯本地，不触网、不依赖 psychopy。
- 判别力自证：把守卫变异成「每帧重建」后重跑，必须被判红
  （test_pin_discriminates_per_frame_rebuild_mutant），保证本套件不是空转。

不改 src/、不改 app.py。
"""
from __future__ import annotations

import ast
import inspect
import socket
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PY_PATH = REPO_ROOT / "app.py"

STATE_KEY = "experiment_engine"
#: :19 的守卫原文——变异体测试的替换靶点；若被重构改写，这里当场红（强制维护者更新钉桩）
GUARD_SOURCE = "if st.session_state.experiment_engine is None:"


# ═══════════════ 手桩：SessionStateProxy（照搬真实语义） ═══════════════

class _FakeSessionState:
    """最小 Streamlit SessionStateProxy 复刻。

    属性读**缺键抛 AttributeError**（1.59.1 实测），属性写落到字典——
    这正是「读点无外层守卫」之所以安全 / 不安全的分水岭。
    """

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

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, *default):
        return self._data.pop(key, *default)

    def setdefault(self, key, default=None):
        return self._data.setdefault(key, default)

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    def values(self):
        return self._data.values()

    def update(self, *args, **kwargs):
        self._data.update(*args, **kwargs)

    def clear(self):
        self._data.clear()


class _FakeCtx:
    """可 with、可解包的容器桩（sidebar / expander / spinner / columns / tabs）。"""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeST:
    """够渲染 experiment_design_ui 默认路径的手桩。

    控件默认取「用户没点 / 没改」的中性值：按钮类 **False**（否则 MagicMock 为真会误入
    重置 / 设计分支，把复用用例打成假红），文本类 ""，选择类首项，数值类取传入的 value。
    未显式实现的 API（title/caption/markdown/... 纯展示）一律记录后返回 None。
    """

    def __init__(self, session_state=None):
        object.__setattr__(self, "session_state", session_state or _FakeSessionState())
        object.__setattr__(self, "calls", [])
        object.__setattr__(self, "sidebar", _FakeCtx())

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

    # ── 布尔控件：默认 False ──
    def button(self, *args, **kwargs):
        return False

    def form_submit_button(self, *args, **kwargs):
        return False

    def checkbox(self, *args, **kwargs):
        return False

    def toggle(self, *args, **kwargs):
        return False

    def download_button(self, *args, **kwargs):
        return False

    # ── 取值控件 ──
    def text_input(self, *args, **kwargs):
        return kwargs.get("value", "") or ""

    def text_area(self, *args, **kwargs):
        return kwargs.get("value", "") or ""

    def selectbox(self, *args, **kwargs):
        options = args[1] if len(args) > 1 else kwargs.get("options", [])
        return options[0] if options else None

    def radio(self, *args, **kwargs):
        options = args[1] if len(args) > 1 else kwargs.get("options", [])
        return options[0] if options else None

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

    # ── 其余（展示类）：记录后返回 None ──
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _display(*args, **kwargs):
            self.calls.append(name)
            return None

        return _display


# ═══════════════ 夹具 ═══════════════

@pytest.fixture()
def harness(monkeypatch):
    """UI 模块的 st 换成手桩；引擎构造装计数器。返回 (模块, fake_st, built)。"""
    from src.ui import experiment_design_ui

    real_engine_cls = experiment_design_ui.ExperimentDesignEngine   # 打桩前抓住真实类
    fake_st = _FakeST()
    built: list = []

    class _CountingEngine(real_engine_cls):
        def __init__(self):
            super().__init__()
            built.append(self)

    monkeypatch.setattr(experiment_design_ui, "st", fake_st)
    monkeypatch.setattr(experiment_design_ui, "ExperimentDesignEngine", _CountingEngine)
    return experiment_design_ui, fake_st, built, real_engine_cls


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
    """复刻 app.py 的落键循环：仅在缺键时补种。"""
    for key, val in _app_defaults().items():
        if key not in state:
            state[key] = val


# ═══════════════ 一、必置前提：_defaults 必须有这个键 ═══════════════

def test_app_defaults_seeds_experiment_engine_slot():
    """:19 的读点无外层守卫 ⇒ 唯一保险是 app.py 的 _defaults 无条件补种；补种没了就是整页红。"""
    defaults = _app_defaults()
    assert STATE_KEY in defaults, (
        f"app.py 的 _defaults 少了 {STATE_KEY}：experiment_design_ui.py:19 的属性式读取"
        "会退化成 AttributeError（键不存在），而该读点没有外层守卫"
    )
    assert defaults[STATE_KEY] is None, "初值必须是 None（懒初始化的触发值），否则首帧不会建引擎"

    app_src = APP_PY_PATH.read_text(encoding="utf-8")
    assert "for key, val in _defaults.items():" in app_src and (
        "if key not in st.session_state:" in app_src
    ), "app.py 的 _defaults 落键循环改了形状——「必置」保证需重新核对"


# ═══════════════ 二、三态行为 ═══════════════

def test_none_slot_builds_engine_and_writes_back(harness):
    """态①/③（生产首帧）：槽为 None → 建引擎、写回会话、只建一次。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)          # 复刻 app.py 启动补种
    assert fake_st.session_state.experiment_engine is None

    ui.render_experiment_design_ui()

    eng = fake_st.session_state.experiment_engine
    assert eng is not None, "槽为 None 时没有建引擎（懒初始化丢失）"
    assert isinstance(eng, ui.ExperimentDesignEngine)
    assert len(built) == 1, f"首帧应恰好构造 1 个引擎，实际 {len(built)}"
    assert eng is built[0], "写回的必须是刚构造的那个对象"
    assert eng.design is None and eng.logs == [], "新引擎应是干净状态"


def test_existing_engine_is_reused_by_identity(harness):
    """态②（承重用例）：槽里已有引擎 → 复用**同一对象**，不得每帧重建（会丢引擎内状态）。"""
    ui, fake_st, built, real_engine_cls = harness
    _apply_defaults(fake_st.session_state)
    seeded = real_engine_cls()                       # 走真实实现，不经计数器
    seeded.logs.append("sentinel-已在引擎里")         # 引擎内状态（logs）不得被重建冲掉
    seeded.pin_sentinel = "跨帧存活标记"
    fake_st.session_state.experiment_engine = seeded

    ui.render_experiment_design_ui()

    reused = fake_st.session_state.experiment_engine
    assert reused is seeded, "引擎被换成了新对象——复用被改成每帧重建（引擎内状态已丢）"
    assert built == [], f"槽里已有引擎却仍构造了 {len(built)} 个新引擎"
    assert reused.logs == ["sentinel-已在引擎里"]
    assert reused.pin_sentinel == "跨帧存活标记"


def test_none_slot_rebuild_is_once_across_frames(harness):
    """态③跨帧：None 首帧重建，第二帧必须复用（构造计数恒为 1）。"""
    ui, fake_st, built, _real = harness
    _apply_defaults(fake_st.session_state)

    ui.render_experiment_design_ui()
    first = fake_st.session_state.experiment_engine

    ui.render_experiment_design_ui()
    second = fake_st.session_state.experiment_engine

    assert len(built) == 1, f"两帧共构造 {len(built)} 个引擎——第二帧发生了重建"
    assert second is first, "第二帧换掉了引擎对象（每帧重建）"


def test_missing_key_without_seed_raises_attribute_error(harness):
    """态①的反面：键真缺失且未补种 → 按 Streamlit 真实语义抛 AttributeError（读点无外层守卫）。"""
    ui, fake_st, built, _real = harness
    assert STATE_KEY not in fake_st.session_state          # 空会话，故意不跑 _defaults

    with pytest.raises(AttributeError) as ei:
        ui.render_experiment_design_ui()

    assert STATE_KEY in str(ei.value), "抛的应是缺 experiment_engine 的属性错误"
    assert built == [], "属性错误之前不该构造引擎"
    assert STATE_KEY not in fake_st.session_state, "未补种时不应偷偷写回引擎槽"
    # 该形态在生产不可达，因为 app.py 的 _defaults 无条件补种（见 test_app_defaults_seeds_...）
    assert STATE_KEY in _app_defaults()


# ═══════════════ 三、判别力自证 + 纯本地 ═══════════════

def test_pin_discriminates_per_frame_rebuild_mutant(harness):
    """变异体：把守卫改成「每帧重建」，本套件的复用不变量必须判红（证明钉桩非空转）。"""
    ui, fake_st, built, real_engine_cls = harness
    source = inspect.getsource(ui.render_experiment_design_ui)
    assert source.count(GUARD_SOURCE) == 1, (
        "守卫原文变了（重构 / 拆分所致），变异体测试失去靶点——请更新 GUARD_SOURCE 与用例"
    )

    namespace = dict(vars(ui))
    namespace["st"] = fake_st
    namespace["ExperimentDesignEngine"] = type(
        "MutantEngine", (ui.ExperimentDesignEngine,), {}
    )
    exec(compile(source.replace(GUARD_SOURCE, "if True:  # 变异：每帧重建"),
                 "<mutant:per-frame-rebuild>", "exec"), namespace)
    mutant_render = namespace["render_experiment_design_ui"]

    _apply_defaults(fake_st.session_state)
    seeded = real_engine_cls()                       # 不走计数器，built 只统计变异体建的对象
    fake_st.session_state.experiment_engine = seeded

    mutant_render()
    mutant_render()

    replaced = fake_st.session_state.experiment_engine
    assert replaced is not seeded, "变异体没生效，判别力自证无效（守卫替换失败）"
    assert len(built) == 2, (
        f"变异体两帧应重建 2 次（被本套件判红的锚点），实际 {len(built)}"
    )


def test_engine_construction_is_local_only(monkeypatch):
    """引擎构造纯本地：断网（socket 换炸雷）下仍能建，且不顺带引入 psychopy。"""
    from src.experiment_design import ExperimentDesignEngine

    def _no_network(*args, **kwargs):
        raise AssertionError("ExperimentDesignEngine 构造触网了")

    psychopy_was_loaded = "psychopy" in sys.modules
    sys.modules.pop("psychopy", None)                # 清掉他人可能留下的加载痕迹
    monkeypatch.setattr(socket, "socket", _no_network)

    eng = ExperimentDesignEngine()

    assert eng.design is None and eng.logs == []
    assert "psychopy" not in sys.modules, "引擎构造顺带 import 了 psychopy"
    sys.modules.pop("psychopy", None) if not psychopy_was_loaded else None
