"""src/ui/experiment_design_ui.py:49-51 侧栏「🔄 重置设计」按钮路径钉桩（s923-39）。

来源：`zcode-bridge/done/s922-133-expengine-lazyinit.result.md` 遗留问题 2——
「:50 侧栏重置设计是**另一条显式重建路径**（点按钮即换新引擎并 st.rerun()），
本单未覆盖其行为；若要钉，需手桩按钮返回 True」。本文件就是那张接线单。

钉的行为（不是文本长相）：

1. **点击 → 会话槽里的引擎被换成新实例**（id 前后不同 + `is not`），且新实例是干净状态
   （design/logs 归零），旧对象**被整体弃用而非就地清空**——「重置」的实质语义；
2. **点击 → 请求重跑一次**（`st.rerun` 计数 == 1）。手桩按 Streamlit 1.59.1 真实语义让
   rerun **抛异常中止本帧**（生产里是 `RerunException`），这才与 :51 之后的代码不执行相符；
3. **不点 → 引擎对象、构造计数、重跑计数三者都不许动**（对照组：证明 ①② 由按钮造成）；
4. 重置只动 `experiment_engine` 一个会话键（且因 ② 中止在本帧，:56-59 的预填充 pop 尚未执行）。

实现口径：沿用 s922-133 的手桩法——只替换 UI 模块属性 `experiment_design_ui.st`，
不用 AppTest（不启 app、不触网、不写盘）。按钮按**标签文本**逐个放行，其余保持 False
（MagicMock 恒真会误入 :112/:168 的「设计实验」分支，把对照组打成假红）。
判别力自证：把 :50-51 变异成「不重跑」「不写回会话槽」两种坏形态，本套件必须各自判红。

只加测试，不改 `src/ui/experiment_design_ui.py`、不改 `app.py`。
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
RESET_LABEL = "🔄 重置设计"
DESIGN_LABEL = "🔬 设计实验"

#: :49 的按钮原文——变异靶点兼标签锚点；改名后下面的计数断言当场红
BUTTON_SOURCE = f'if st.button("{RESET_LABEL}", width="stretch"):'
#: :50-51 的重建块（12 空格缩进，与 :20 懒初始化的 8 空格版本天然区分）
RESET_BLOCK_SOURCE = (
    "            st.session_state.experiment_engine = ExperimentDesignEngine()\n"
    "            st.rerun()"
)
#: :19 的懒初始化守卫（s922-133 的靶点原文，这里只用来钉「两条路径仍然分立」）
LAZY_SOURCE = "    if st.session_state.experiment_engine is None:"


# ═══════════════ 手桩（按 Streamlit 1.59.1 真实语义） ═══════════════

class RerunRequested(RuntimeError):
    """`st.rerun()` 的替身信号：真实 Streamlit 在此抛 RerunException 中止本帧。"""


class _FakeSessionState:
    """SessionStateProxy 最小复刻：属性读缺键抛 AttributeError，属性写落字典。"""

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
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeST:
    """够渲染 experiment_design_ui 的手桩：只有 `pressed` 里的按钮标签返回 True。"""

    def __init__(self, session_state=None, pressed=()):
        object.__setattr__(self, "session_state", session_state or _FakeSessionState())
        object.__setattr__(self, "pressed", set(pressed))
        object.__setattr__(self, "calls", [])           # [(api, 首个位置参数)]
        object.__setattr__(self, "button_labels", [])
        object.__setattr__(self, "rerun_count", 0)
        object.__setattr__(self, "sidebar", _FakeCtx())

    # ── 容器 ──
    def columns(self, spec, **kwargs):
        self.calls.append(("columns", spec))
        n = spec if isinstance(spec, int) else len(spec)
        return [_FakeCtx() for _ in range(n)]

    def tabs(self, labels, **kwargs):
        return [_FakeCtx() for _ in labels]

    def expander(self, *args, **kwargs):
        return _FakeCtx()

    def spinner(self, *args, **kwargs):
        return _FakeCtx()

    # ── 布尔控件：只有 pressed 命中的标签为真 ──
    def button(self, *args, **kwargs):
        label = args[0] if args else kwargs.get("label", "")
        self.button_labels.append(label)
        self.calls.append(("button", label))
        return label in self.pressed

    def checkbox(self, *args, **kwargs):
        return False

    def toggle(self, *args, **kwargs):
        return False

    def download_button(self, *args, **kwargs):
        return False

    # ── 取值控件：取「用户没改」的中性值 ──
    def text_input(self, *args, **kwargs):
        return kwargs.get("value", "") or ""

    def text_area(self, *args, **kwargs):
        return kwargs.get("value", "") or ""

    def selectbox(self, *args, **kwargs):
        options = args[1] if len(args) > 1 else kwargs.get("options", [])
        return options[0] if options else None

    def slider(self, *args, **kwargs):
        if "value" in kwargs:
            return kwargs["value"]
        return args[3] if len(args) > 3 else (args[1] if len(args) > 1 else 0)

    def number_input(self, *args, **kwargs):
        return kwargs.get("value", 0)

    def file_uploader(self, *args, **kwargs):
        return None

    # ── 重跑：计数后按真实语义中止本帧 ──
    def rerun(self, *args, **kwargs):
        object.__setattr__(self, "rerun_count", self.rerun_count + 1)
        self.calls.append(("rerun", None))
        raise RerunRequested("st.rerun() 被调用")

    # ── 展示类：记录后 None ──
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _display(*args, **kwargs):
            self.calls.append((name, args[0] if args else kwargs.get("label")))
            return None

        return _display


# ═══════════════ 夹具 ═══════════════

@pytest.fixture()
def harness(monkeypatch):
    """UI 模块的 st 换手桩、引擎类换计数器。返回 make(...) → (模块, fake_st, 构造计数, 真实引擎类)。"""
    from src.ui import experiment_design_ui

    real_engine_cls = experiment_design_ui.ExperimentDesignEngine   # 打桩前抓真实类
    built: list = []

    class _CountingEngine(real_engine_cls):
        def __init__(self):
            super().__init__()
            built.append(self)

    def make(pressed=(), initial=None):
        fake_st = _FakeST(session_state=_FakeSessionState(initial or {}), pressed=pressed)
        monkeypatch.setattr(experiment_design_ui, "st", fake_st)
        monkeypatch.setattr(experiment_design_ui, "ExperimentDesignEngine", _CountingEngine)
        return experiment_design_ui, fake_st, built, real_engine_cls

    return make


def _seed_state():
    """复刻 app.py _defaults 的相关键（experiment_engine=None = 生产首帧形态）。"""
    return {STATE_KEY: None, "paper_engine": None, "_prefill_exp_topic": "预填主题"}


def _snapshot(state: _FakeSessionState) -> dict:
    return dict(object.__getattribute__(state, "_data"))


# ═══════════════ 一、锚点前提（漂移即红，强制后来人更新钉桩） ═══════════════

def test_reset_button_anchor_is_a_sidebar_rebuild_path_distinct_from_lazy_init():
    """:49-51 原文在场、仍在侧栏块内，且与 :19 的懒初始化是**两条不同**的重建点。"""
    from src.ui import experiment_design_ui

    source = inspect.getsource(experiment_design_ui.render_experiment_design_ui)
    assert source.count(BUTTON_SOURCE) == 1, (
        "重置按钮原文变了（改名 / 挪位 / 拆分所致）——请同步更新 BUTTON_SOURCE 与标签桩"
    )
    assert source.count(RESET_BLOCK_SOURCE) == 1, (
        ":50-51 的「重建 + 重跑」块不再是这个形状，重置语义需重新核对"
    )
    assert source.count(LAZY_SOURCE) == 1, (
        "s922-133 钉的懒初始化守卫被改写——两路重建的关系需重新登记"
    )
    assert source.index(LAZY_SOURCE) < source.index(BUTTON_SOURCE), (
        "两条路径的先后变了：重置按钮必须仍在懒初始化之后（同一函数里先取引擎再重置）"
    )
    assert "\n        st.divider()\n        " + BUTTON_SOURCE in source, (
        "重置按钮不再位于 with st.sidebar 块内——「侧栏」归属是这条路径的前提"
    )


# ═══════════════ 二、点击后的行为 ═══════════════

def test_click_replaces_engine_instance_and_requests_rerun(harness):
    """核心：点「🔄 重置设计」→ 会话槽换新引擎实例（id 变化）+ 请求重跑一次。"""
    ui, fake_st, built, real_cls = harness(pressed=(RESET_LABEL,), initial=_seed_state())

    old = real_cls()                                   # 走真实类，不经计数器
    old.logs.append("旧引擎里的状态")
    old.pin_sentinel = "旧对象标记"
    fake_st.session_state.experiment_engine = old
    old_id = id(old)

    with pytest.raises(RerunRequested):
        ui.render_experiment_design_ui()

    new = fake_st.session_state.experiment_engine
    assert new is not old, "点击后引擎对象没换——重置丢失"
    assert id(new) != old_id, "会话槽里的引擎 id 前后相同（重置变成就地改写了？）"
    assert old.pin_sentinel == "旧对象标记", "旧对象被就地清空 ⇒ 重置已不是「换新实例」语义"
    assert len(built) == 1, f"重置应恰好构造 1 个新引擎，实际 {len(built)}"
    assert new is built[0], "写回会话槽的必须是重置时新建的那个对象"
    assert fake_st.rerun_count == 1, f"st.rerun 应被请求 1 次，实际 {fake_st.rerun_count}"
    assert isinstance(new, real_cls)


def test_reset_actually_drops_engine_state(harness):
    """:50 是 `= ExperimentDesignEngine()` 而非原地清空——钉住旧 design/logs 确实出槽。"""
    ui, fake_st, built, real_cls = harness(pressed=(RESET_LABEL,), initial=_seed_state())

    old = real_cls()
    old.logs.append("待丢弃")
    fake_st.session_state.experiment_engine = old

    with pytest.raises(RerunRequested):
        ui.render_experiment_design_ui()

    fresh = fake_st.session_state.experiment_engine
    assert fresh.logs == [], "重置后的引擎仍带旧 logs"
    assert fresh.design is None, "重置后的引擎仍挂着旧 design"
    assert fresh is not old


def test_reset_touches_only_the_experiment_engine_session_key(harness):
    """重置只动 experiment_engine 一个键；因 rerun 中止在本帧，:56-59 的预填充 pop 尚未执行。"""
    ui, fake_st, built, real_cls = harness(pressed=(RESET_LABEL,), initial=_seed_state())
    fake_st.session_state.experiment_engine = real_cls()
    before = _snapshot(fake_st.session_state)

    with pytest.raises(RerunRequested):
        ui.render_experiment_design_ui()

    after = _snapshot(fake_st.session_state)
    changed = {k for k in set(before) | set(after) if before.get(k) is not after.get(k)}
    assert changed == {STATE_KEY}, f"重置越界改动了其它会话键：{sorted(changed)}"
    assert after["paper_engine"] is None, "别的引擎槽被牵连"
    assert after["_prefill_exp_topic"] == "预填主题"


# ═══════════════ 三、对照组：不点按钮什么都不能发生 ═══════════════

def test_unpressed_render_keeps_engine_and_never_reruns(harness):
    """对照组：按钮 False 时引擎对象不变、零构造、零重跑（证明上面几条是按钮造成的）。"""
    ui, fake_st, built, real_cls = harness(pressed=(), initial=_seed_state())
    seeded = real_cls()
    seeded.logs.append("必须活着")
    fake_st.session_state.experiment_engine = seeded

    ui.render_experiment_design_ui()                    # 不抛 = 本帧没请求重跑

    assert fake_st.session_state.experiment_engine is seeded
    assert seeded.logs == ["必须活着"]
    assert built == [], f"未点击却构造了 {len(built)} 个引擎"
    assert fake_st.rerun_count == 0, "未点击却请求了重跑"
    assert RESET_LABEL in fake_st.button_labels, (
        "手桩压根没被问过重置按钮标签——按钮锚点已漂移，本对照无效"
    )


def test_reset_and_design_buttons_are_two_different_controls(harness):
    """侧栏「重置」与主区「设计实验」是两枚按钮、且重置在前——防标签桩撞名后互相误放行。"""
    ui, fake_st, built, real_cls = harness(pressed=(), initial=_seed_state())
    fake_st.session_state.experiment_engine = real_cls()

    ui.render_experiment_design_ui()

    assert fake_st.button_labels[:2] == [RESET_LABEL, DESIGN_LABEL], (
        f"按钮出现顺序/文本变了：{fake_st.button_labels}"
    )
    assert built == [] and fake_st.rerun_count == 0


# ═══════════════ 四、判别力自证（变异体必须判红） ═══════════════

MUTANTS = {
    "no-rerun": lambda s: s.replace(RESET_BLOCK_SOURCE, RESET_BLOCK_SOURCE.split("\n")[0]),
    "no-writeback": lambda s: s.replace(
        RESET_BLOCK_SOURCE,
        "            _mutant_local_engine = ExperimentDesignEngine()\n            st.rerun()",
    ),
}


@pytest.mark.parametrize("mutant_name", sorted(MUTANTS))
def test_pin_discriminates_reset_mutants(harness, mutant_name):
    """两种坏形态各自都会撞本套件的某条不变量 ⇒ 证明钉桩非空转（不是永远绿的形状断言）。"""
    ui, fake_st, built, real_cls = harness(pressed=(RESET_LABEL,), initial=_seed_state())
    source = inspect.getsource(ui.render_experiment_design_ui)
    assert source.count(RESET_BLOCK_SOURCE) == 1, "变异靶点丢失，判别力自证无效"

    mutated = MUTANTS[mutant_name](source)
    assert mutated != source, f"变异「{mutant_name}」没改到源码，判别力自证无效"

    namespace = dict(vars(ui))
    namespace["st"] = fake_st
    exec(compile(mutated, f"<mutant:{mutant_name}>", "exec"), namespace)
    mutant_render = namespace["render_experiment_design_ui"]

    old = real_cls()
    fake_st.session_state.experiment_engine = old

    try:                                            # no-rerun 变异体不会中止本帧
        mutant_render()
    except RerunRequested:
        pass

    after = fake_st.session_state.experiment_engine
    if mutant_name == "no-rerun":
        # 本套件的「rerun_count == 1」在此判红 ⇒ 变异体生效且被抓住
        assert fake_st.rerun_count == 0, "变异体没生效（仍在重跑），判别力自证无效"
        assert after is not old, "no-rerun 变异体应仍重建引擎，否则靶点失效"
    else:
        # 本套件的「new is not old」在此判红 ⇒ 变异体生效且被抓住
        assert after is old, "变异体没生效（写回仍发生了），判别力自证无效"
        assert fake_st.rerun_count == 1, "no-writeback 变异体应仍重跑，否则靶点失效"
