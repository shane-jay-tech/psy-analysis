"""成对键/前置写两处脆点的特征化钉桩（s924-32，纯测试新增，零生产码改）。

上游卷宗：`zcode-bridge/done/s922-136-session-subscript-census.result.md` ——
「`cleaning_wizard.py:199`（`log_key`）是本面唯一脆点：守卫测兄弟键 `df_key`，
两键只靠『:195-196 成对写』维系」。现有 `tests/test_cleaning_wizard.py` 只测纯算法，
首行自陈「UI 渲染部分依赖 streamlit session_state，留给 e2e/playwright 测试」⇒ 这半张网一直没铺。

钉的两处行为（都不是文本长相）：

1. `src/ui/cleaning_wizard.py:194-199`：首帧守卫里 `df_key` 与 `log_key` **必须同帧成对写**，
   且 `log_key` 初值是空列表；`:199` 是无条件读，半路径（只写 df_key）必然 `KeyError`。
2. `src/ui/template_center_panel.py:194→:199`：`:194` 前置写 `current_file_name`，
   `:199` 用 `session_state["file_name"] = session_state["current_file_name"]` 后置读同一值
   ——两键的等值关系**只由这两行的先后**保证，删前者则整段 `try` 抛 `KeyError`。

实现口径：沿用仓内手桩法（`tests/test_experiment_design_ui_reset_pin.py` 与
`test_export_gate_global_scan.py` 同路）——只替换 UI 模块属性 `st`，不用 AppTest，
不启 app、不触网。模板那一例把 `project_manager.PROJECTS_DIR/INDEX_FILE` 指向 `tmp_path`
（与既有 `tests/test_template_center_ui.py` 的隔离夹具同形），真用户项目目录零写入。

判别力自证在**同一文件内**完成：用 `inspect.getsource` 取原文 → 字符串级删掉那一行 →
`exec(compile(...))` 跑变异体（全程内存、零磁盘写入、不改 `src/`），
断言变异体必红（`KeyError` 缺的正是成对键的另一半 / `st.error` 被记录）。
故本文件自身就是"改前基线 + 变异 + 判别力"三件套，不需要临时改生产码（纪律 §十三.7）。

⚠ 一处实测形态（写在这儿防后来人误判）：`_create_project` 外层是 `try/except Exception`
→ `st.error(...)`，所以那条面上的 `KeyError` **不会向上冒泡**，只会变成一个泛化报错。
本件因此断"`st.error` 零记录"（正向）与"`st.error` 有记录 + `file_name` 未落盘"（变异体）。
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ── 锚点原文（缩进即身份：同文本在别处以更深缩进出现，本锚点不会误命中）──
CW_DF_WRITE = "        st.session_state[df_key] = df.copy()"          # cleaning_wizard.py:195
CW_LOG_WRITE = "        st.session_state[log_key] = []"               # cleaning_wizard.py:196
CW_LOG_READ = "    log: List[CleaningStep] = st.session_state[log_key]"  # :199（无条件读＝脆点）
TC_PRE_WRITE = '            session_state["current_file_name"] = file_name'          # :194
TC_POST_READ = '            session_state["file_name"] = session_state["current_file_name"]'  # :199


# ═══════════════ 手桩 ═══════════════

class _FakeSessionState(dict):
    """`st.session_state` 的下标语义最小复刻：缺键 `[]` 读抛 `KeyError`、`in` 判存在。

    真 `SessionStateProxy` 这两条与 dict 一致，而成对键脆点恰好只靠这两条暴露。
    """


class _RerunRequested(RuntimeError):
    """`st.rerun()` 替身：真实 Streamlit 在此抛异常中止本帧。"""


class _FakeCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeCol:
    """`st.columns()` 返回的列容器：按钮一律不放行，其余记录后 None。"""

    def __init__(self, st):
        self._st = st

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self._st.calls.append((f"col.{name}", args[0] if args else kwargs.get("key", "")))
            return False

        return _record


class _FakeST:
    """够渲染清洗向导 / 只喂 `_create_project` 的展示面手桩。

    按钮只有标签出现在 `pressed` 里才返回 True（MagicMock 恒真会误入清洗动作分支，
    把首帧测打成假红）。`error()` 单独记录，供"异常被 except 吞掉"那一面判红。
    """

    def __init__(self, session_state=None, pressed=()):
        self.session_state = session_state if session_state is not None else _FakeSessionState()
        self.pressed = set(pressed)
        self.calls: list = []
        self.errors: list = []
        self.rerun_count = 0

    def columns(self, spec, **kwargs):
        n = spec if isinstance(spec, int) else len(spec)
        return [_FakeCol(self) for _ in range(n)]

    def expander(self, *args, **kwargs):
        return _FakeCtx()

    def container(self, *args, **kwargs):
        return _FakeCtx()

    def button(self, *args, **kwargs):
        label = args[0] if args else kwargs.get("label", "")
        self.calls.append(("button", label))
        return label in self.pressed

    def multiselect(self, *args, **kwargs):
        return list(kwargs.get("default") or (args[2] if len(args) > 2 else []) or [])

    def error(self, *args, **kwargs):
        msg = args[0] if args else kwargs.get("body", "")
        self.errors.append(str(msg))
        return None

    def rerun(self, *args, **kwargs):
        self.rerun_count += 1
        raise _RerunRequested("st.rerun() 被调用")

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _display(*args, **kwargs):
            self.calls.append((name, args[0] if args else kwargs.get("label", "")))
            return None

        return _display


def _clean_df() -> pd.DataFrame:
    """无缺失、无常数列、无 IQR 异常值的干净数据：首帧只走守卫，不进任何清洗分支。"""
    return pd.DataFrame({
        "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "b": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0],
        "c": [3.0, 1.0, 4.0, 1.0, 5.0, 9.0],
    })


@pytest.fixture()
def isolated_project_store(tmp_path, monkeypatch):
    """项目库改道 tmp_path（与 tests/test_template_center_ui.py 同形），真用户目录零写。"""
    from src.utils import project_manager as pm

    projects_dir = tmp_path / "projects"
    monkeypatch.setattr(pm, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(pm, "INDEX_FILE", projects_dir / "index.json")
    return projects_dir


def _first_template_with_data():
    from src.templates.registry import list_templates

    for tpl in list_templates():
        if (tpl.get_path() / "data.csv").exists():
            return tpl
    raise AssertionError("模板库里没有任何带 data.csv 的模板，本件前提失效")


# ═══════════════ 一、锚点前提（漂移即红，强制后来人同步钉桩）═══════════════════

def test_pair_write_anchors_are_unique_and_in_order():
    """两处锚点各只出现 1 次、且"写在前读在后"——锚点漂了本文件全部断言失去意义。"""
    from src.ui import cleaning_wizard, template_center_panel

    cw_src = inspect.getsource(cleaning_wizard.render_cleaning_wizard)
    for anchor, label in ((CW_DF_WRITE, ":195 df_key 写"),
                          (CW_LOG_WRITE, ":196 log_key 写"),
                          (CW_LOG_READ, ":199 log_key 无条件读")):
        assert cw_src.count("\n" + anchor) == 1, f"清洗向导锚点不唯一/已漂移：{label}"
    assert cw_src.index(CW_DF_WRITE) < cw_src.index(CW_LOG_WRITE) < cw_src.index(CW_LOG_READ), (
        "成对写与无条件读的行序变了——『两键只靠成对写维系』这条前提需重新核对"
    )

    tc_src = inspect.getsource(template_center_panel._create_project)
    assert tc_src.count("\n" + TC_PRE_WRITE) == 1, ":194 前置写锚点漂移"
    assert tc_src.count("\n" + TC_POST_READ) == 1, ":199 后置读锚点漂移"
    assert tc_src.index(TC_PRE_WRITE) < tc_src.index(TC_POST_READ), (
        "前置写不再早于后置读——两键等值关系不成立了"
    )


# ═══════════════ 二、cleaning_wizard 成对键（卷宗例①）═══════════════════

def test_cleaning_wizard_first_frame_writes_both_paired_keys(monkeypatch):
    """首帧：`df_key` 与 `log_key` 同帧成对出现，且清洗日志初值是空列表。"""
    from src.ui import cleaning_wizard

    fake_st = _FakeST(session_state=_FakeSessionState())
    monkeypatch.setattr(cleaning_wizard, "st", fake_st)
    df = _clean_df()

    out_df, log = cleaning_wizard.render_cleaning_wizard(df, key_prefix="clean")

    ss = fake_st.session_state
    assert "clean_df" in ss, "成对键的 df_key 没写——守卫分支没执行？"
    assert "clean_log" in ss, "成对键的 log_key 没写——:196 那条写消失了"
    assert ss["clean_log"] == [], f"log_key 初值应为空列表，实际 {ss['clean_log']!r}"
    assert isinstance(ss["clean_df"], pd.DataFrame)
    assert out_df is ss["clean_df"] and log is ss["clean_log"], "返回值不是会话槽里那两个对象"
    pd.testing.assert_frame_equal(ss["clean_df"], df)
    assert ss["clean_df"] is not df, "df_key 存的是原对象引用——就地清洗会污染调用方数据"
    assert fake_st.errors == [], f"首帧渲染却报错：{fake_st.errors}"


def test_paired_key_pin_kills_log_key_half_write(monkeypatch):
    """判别力自证（卷宗完成标准②）：删掉 :196 的 log_key 写 ⇒ :199 无条件读必 `KeyError`。

    变异全程在内存里（`inspect.getsource` → 字符串级删一行 → `exec`），
    `src/ui/cleaning_wizard.py` 一个字节都没动。
    """
    from src.ui import cleaning_wizard

    src = inspect.getsource(cleaning_wizard.render_cleaning_wizard)
    assert src.count("\n" + CW_LOG_WRITE) == 1, "变异靶点丢失，判别力自证无效"
    mutated = src.replace("\n" + CW_LOG_WRITE, "", 1)
    assert mutated != src, "变异没改到源码，判别力自证无效"
    assert CW_DF_WRITE in mutated, "半路径形态应是『只写 df_key、不写 log_key』"

    fake_st = _FakeST(session_state=_FakeSessionState())
    namespace = dict(vars(cleaning_wizard))
    namespace["st"] = fake_st
    exec(compile(mutated, "<mutant:drop-log-key-write>", "exec"), namespace)

    with pytest.raises(KeyError) as exc:
        namespace["render_cleaning_wizard"](_clean_df(), key_prefix="clean")
    assert str(exc.value.value if hasattr(exc.value, "value") else exc.value).strip("'") \
        == "clean_log", f"抛的应是成对键的另一半，实际 {exc.value!r}"
    assert "clean_df" in fake_st.session_state, "半路径应已写完 df_key（否则测的不是成对写）"
    assert "clean_log" not in fake_st.session_state


# ═══════════════ 三、template_center 前置写→后置读（卷宗例②）═══════════════════

def test_template_center_post_read_equals_pre_write(monkeypatch, isolated_project_store):
    """`:194` 写 `current_file_name` 后，`:199` 读到同值；两键等值由这两行的先后保证。"""
    from src.ui import template_center_panel

    fake_st = _FakeST(session_state=_FakeSessionState())
    monkeypatch.setattr(template_center_panel, "st", fake_st)
    tpl = _first_template_with_data()
    session_state = _FakeSessionState()

    template_center_panel._create_project(tpl, session_state)

    assert fake_st.errors == [], f"创建路径被 except 吞成报错：{fake_st.errors}"
    assert session_state["current_file_name"] == f"{tpl.name}_样例数据.csv"
    assert session_state["file_name"] == session_state["current_file_name"], (
        ":199 的后置读没拿到 :194 的前置写——两键已脱钩"
    )
    assert session_state["df"] is session_state["uploaded_df"]
    assert session_state["project_id"] and session_state["template_source"] == tpl.template_id
    assert session_state["template_created_project"]["data_path"].endswith("data.csv")


def test_front_write_pin_kills_current_file_name_half_write(monkeypatch, isolated_project_store):
    """判别力自证（同款半路径）：删掉 `:194` 的前置写 ⇒ `:199` 抛 `KeyError`，
    而它被外层 `try/except Exception` 吞成 `st.error` ⇒ 断"报错被记录 + file_name 未落盘"。
    """
    from src.ui import template_center_panel

    src = inspect.getsource(template_center_panel._create_project)
    assert src.count("\n" + TC_PRE_WRITE) == 1, "变异靶点丢失，判别力自证无效"
    mutated = src.replace("\n" + TC_PRE_WRITE, "", 1)
    assert mutated != src, "变异没改到源码，判别力自证无效"
    assert TC_POST_READ in mutated, "半路径形态应是『没有前置写、只剩后置读』"

    fake_st = _FakeST(session_state=_FakeSessionState())
    namespace = dict(vars(template_center_panel))
    namespace["st"] = fake_st
    exec(compile(mutated, "<mutant:drop-current-file-name-write>", "exec"), namespace)

    session_state = _FakeSessionState()
    namespace["_create_project"](_first_template_with_data(), session_state)   # 不抛：except 兜住

    assert len(fake_st.errors) == 1, f"半路径必须留下一条泛化报错，实际 {fake_st.errors!r}"
    assert "current_file_name" in fake_st.errors[0] or "KeyError" in fake_st.errors[0], (
        f"报错文本没指向缺失键：{fake_st.errors[0]!r}"
    )
    # `clear_research_session` 先把 file_name 恢复成默认 None，:199 又是中断点
    # ⇒ 半路径留下的形态是"键在、值为 None"，故这里断**值**不断键存在（键存在会是假阴）。
    assert session_state.get("file_name") is None, "后置读竟拿到了文件名——两键等值另有来源？"
    assert "current_file_name" not in session_state, (
        "clear_research_session 之后 current_file_name 不该存在（前置写正是它唯一的写点）"
    )
    assert "template_created_project" not in session_state, (
        "整段 try 提前中断后，项目信息键不应留下半成品"
    )
