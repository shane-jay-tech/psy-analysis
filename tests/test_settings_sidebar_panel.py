# -*- coding: utf-8 -*-
"""s922-102 分片迁移哨兵：app.py 片 7a（问卷页混装侧栏）-> src/ui/settings_sidebar_panel.py。

钉住四件迁移后才可能退化的事：
1. 两个 `st.header`（🌐 语言 / 💡 使用指南）确已离开 app.py，且接线在同位；
2. 迁出模块**只**碰 `language` 一个会话键，且只经注入的形参碰——
   一旦有人改写回 `st.session_state`，就会在 app.py 与 src/ui 之间长出第二条隐式通道；
3. 问卷主体的 `q_request_input` 没被侧栏带走（它必须仍留在 app.py 的问卷区段）；
4. 侧栏的 widget 调用顺序与会话写入结果——这是"原名搬迁"最容易撞坏的东西。

模块级引导（app.py 的 `_defaults`）不在本片范围：本文件第 5 项专门钉它仍在原地。
"""

from __future__ import annotations

import ast
import re
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app.py"
PANEL = REPO / "src" / "ui" / "settings_sidebar_panel.py"


def _app_lines() -> list[str]:
    raw = APP.read_bytes().decode("utf-8")
    return raw.split("\r\n") if "\r\n" in raw else raw.split("\n")


class Rerun(BaseException):
    """真实 `st.rerun()` 抛异常终止本次运行；假 st 只返回会把"中断"钉成"继续跑"。"""


class State(dict):
    """属性与下标双可读写，贴近 Streamlit SessionState。"""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v


class Ctx:
    def __init__(self, log, label):
        self.log, self.label = log, label

    def __enter__(self):
        self.log.append(("ctx:enter", self.label))
        return self

    def __exit__(self, *a):
        self.log.append(("ctx:exit", self.label))
        return False


class FakeSt(types.ModuleType):
    """只够跑侧栏块的假 streamlit：多调一个没准备的方法当场红。"""

    def __init__(self, log, state, radio_value):
        super().__init__("streamlit")
        self.log, self.session_state, self.radio_value = log, state, radio_value
        self.sidebar = Ctx(log, "st.sidebar")

    def divider(self):
        self.log.append(("divider",))

    def header(self, msg):
        self.log.append(("header", msg))

    def radio(self, label, options, **k):
        self.log.append(("radio", label, tuple(options), k.get("key"), k.get("index")))
        return self.radio_value

    def success(self, msg):
        self.log.append(("success", msg))

    def info(self, msg):
        self.log.append(("info", msg[:24]))

    def markdown(self, msg):
        self.log.append(("markdown", len(msg)))

    def rerun(self):
        self.log.append(("rerun",))
        raise Rerun()

    def __getattr__(self, name):
        raise AssertionError(f"侧栏不该碰 st.{name}")


@pytest.fixture
def rig(monkeypatch):
    """把侧栏的三个外部依赖换成记录桩。"""
    import src.ui.settings_sidebar_panel as panel

    seen = {"memory": 0, "cfg": None}

    mm = types.ModuleType("src.utils.memory_manager")
    mm.render_memory_manager_ui = lambda: seen.__setitem__("memory", seen["memory"] + 1)
    ac = types.ModuleType("src.llm_gateway.active_config")
    ac.get_active_llm_config = lambda: seen["cfg"]
    gw = types.ModuleType("src.llm_gateway")
    i18n = types.ModuleType("src.utils.i18n")
    i18n.t = lambda key: {"language": "语言 / Language", "chinese": "中文",
                          "english": "English"}.get(key, key)

    monkeypatch.setitem(__import__("sys").modules, "src.utils.memory_manager", mm)
    monkeypatch.setitem(__import__("sys").modules, "src.llm_gateway", gw)
    monkeypatch.setitem(__import__("sys").modules, "src.llm_gateway.active_config", ac)
    monkeypatch.setattr(panel, "t", i18n.t, raising=False)
    monkeypatch.setattr(panel, "render_memory_manager_ui", mm.render_memory_manager_ui)
    monkeypatch.setattr(panel, "st", None, raising=False)   # 占位，实际由 each test 注入
    return panel, seen, monkeypatch


def _render(panel, monkeypatch, log, state, radio_value):
    fake = FakeSt(log, state, radio_value)
    monkeypatch.setattr(panel, "st", fake)
    with pytest.raises(Rerun):
        panel.render_settings_sidebar_panel(state)
    return log


class TestMigratedOutOfApp:
    def test_headers_left_app_py(self):
        """完成标准 1：两个 st.header 在 app.py 命中 0。"""
        text = "\n".join(_app_lines())
        assert 'st.header("\U0001f310' not in text, "🌐 语言 header 仍在 app.py"
        assert 'st.header("💡 使用指南")' not in text, "💡 使用指南 header 仍在 app.py"

    def test_headers_now_in_panel(self):
        text = PANEL.read_text(encoding="utf-8")
        assert 'st.header("\U0001f310 " + t("language"))' in text
        assert 'st.header("\U0001f4a1 使用指南")' in text
        assert 'st.header("\U0001f916 LLM 状态")' in text

    def test_app_wires_the_panel_at_the_same_place(self):
        lines = _app_lines()
        hits = [i for i, ln in enumerate(lines)
                if ln.strip() == "render_settings_sidebar_panel(st.session_state)"]
        assert len(hits) == 1, hits
        branch = [i for i, ln in enumerate(lines)
                  if ln.startswith('elif mode == "') and "问卷设计" in ln]
        assert len(branch) == 1
        assert branch[0] < hits[0] < branch[0] + 40, "接线不在问卷分支头部"
        assert "\n".join(lines).count("from src.ui.settings_sidebar_panel import") == 1


class TestSessionCaliber:
    def test_only_language_key_and_only_via_injected_param(self):
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body \
                    and isinstance(node.body[0], ast.Expr):
                node.body[0].value = ast.Constant(value="")   # 剥掉说明文字，只查真码
        code = ast.unparse(tree)
        assert "st.session_state" not in code, "模块内又直接用 st.session_state，会形成第二条通道"
        keys = set(re.findall(r"""session_state\s*(?:\.\s*([A-Za-z_]\w*)|\[\s*["'](\w+)["'])""", code))
        flat = {a or b for a, b in keys} - {"language"}
        assert flat == set(), f"侧栏越界碰了其它会话键：{flat}"
        assert "session_state.language" in code

    def test_questionnaire_body_key_not_dragged_along(self):
        """完成标准 3：q_request_input 不得出现在新模块，且必须仍在 app.py 原地。"""
        assert "q_request_input" not in PANEL.read_text(encoding="utf-8")
        assert "q_request_input" in APP.read_text(encoding="utf-8"), "问卷主体键被搬丢了"

    def test_module_level_defaults_seed_still_in_app(self):
        """`language` 的初值播种仍在 app.py 的 `_defaults`——本片没动运行期初始化顺序。"""
        assert re.search(r'^\s{4}"language": "zh",\s*$', APP.read_text(encoding="utf-8"), re.M), \
            "app.py 的 language 默认值引导不见了"

    def test_signature_is_single_injected_param(self):
        from src.ui.settings_sidebar_panel import render_settings_sidebar_panel
        import inspect

        sig = inspect.signature(render_settings_sidebar_panel)
        assert list(sig.parameters) == ["session_state"], sig


class TestRenderSequence:
    def test_unchanged_language_renders_full_sidebar(self, rig):
        panel, seen, monkeypatch = rig
        log, state = [], State(language="zh")
        seen["cfg"] = {"model": "deepseek-v4-flash"}
        monkeypatch.setattr(panel, "st", FakeSt(log, state, "zh"))
        panel.render_settings_sidebar_panel(state)          # 语言未变：不触发 rerun
        assert not any(x[0] == "rerun" for x in log)
        assert state["language"] == "zh"
        assert seen["memory"] == 1

    def test_language_change_writes_then_reruns(self, rig):
        panel, seen, monkeypatch = rig
        log, state = [], State(language="zh")
        seen["cfg"] = None
        monkeypatch.setattr(panel, "st", FakeSt(log, state, "en"))
        with pytest.raises(Rerun):
            panel.render_settings_sidebar_panel(state)
        # rerun 是最后一个 UI 算子；`ctx:exit` 是异常穿越 with 时的正常收尾，真实 streamlit 同样会发生
        assert [x[0] for x in log if x[0] != "ctx:exit"][-1] == "rerun"
        assert log[-1] == ("ctx:exit", "st.sidebar")
        assert state["language"] == "en", "语言写入没回流到注入的会话对象"
        # 写入发生在 rerun 之前，且没渲染使用指南（真实 st.rerun 会中断脚本）
        assert not any(x[0] == "markdown" for x in log)
        assert seen["memory"] == 0

    def test_no_llm_falls_back_to_info(self, rig):
        panel, seen, monkeypatch = rig
        log, state = [], State(language="zh")
        seen["cfg"] = None
        monkeypatch.setattr(panel, "st", FakeSt(log, state, "zh"))
        panel.render_settings_sidebar_panel(state)
        kinds = [x[0] for x in log]
        assert "info" in kinds and "success" not in kinds
        assert kinds.index("header") < kinds.index("info") < kinds.index("markdown")

    def test_sidebar_widget_order_is_exactly_six_ui_steps(self, rig):
        panel, seen, monkeypatch = rig
        log, state = [], State(language="zh")
        seen["cfg"] = {"model": "m"}
        monkeypatch.setattr(panel, "st", FakeSt(log, state, "zh"))
        panel.render_settings_sidebar_panel(state)
        assert [x[0] for x in log] == [
            "ctx:enter", "divider", "header", "radio", "divider", "header",
            "success", "divider", "header", "markdown", "ctx:exit",
        ]
        assert [x[1] for x in log if x[0] == "header"] == [
            "🌐 语言 / Language", "🤖 LLM 状态", "💡 使用指南",
        ]
