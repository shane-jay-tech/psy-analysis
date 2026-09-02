"""标准模式下一步导航测试。"""

from types import SimpleNamespace

from src.ui import next_step_panel
from src.utils.next_step_engine import NextStep


class _FakeStreamlit:
    def __init__(self, *, click=False):
        self.session_state = {}
        self.click = click
        self.rerun_called = False
        self.markdown_calls = []

    def caption(self, _text):
        pass

    def markdown(self, text, **kwargs):
        self.markdown_calls.append((text, kwargs))

    def button(self, *_args, **_kwargs):
        return self.click

    def rerun(self):
        self.rerun_called = True


def test_next_step_click_queues_navigation_without_mutating_widget_key(monkeypatch):
    fake_st = _FakeStreamlit(click=True)
    step = NextStep(
        step_id="write",
        title="开始写作",
        description="整理结果",
        page_target="📝 论文写作",
        priority=1,
    )
    monkeypatch.setattr(next_step_panel, "st", fake_st)
    monkeypatch.setattr(next_step_panel, "recommend_next_steps", lambda *_a, **_k: [step])

    next_step_panel.render_next_step_panel("📈 数据分析")

    assert fake_st.session_state["_pending_app_mode"] == "📝 论文写作"
    assert "app_mode" not in fake_st.session_state
    assert fake_st.rerun_called is True
    assert "psy-next-step" in fake_st.markdown_calls[0][0]


def test_next_step_ignores_unknown_route(monkeypatch):
    fake_st = _FakeStreamlit(click=True)
    step = SimpleNamespace(
        step_id="bad",
        title="不存在",
        description="",
        page_target="不存在的页面",
        blocked=False,
    )
    monkeypatch.setattr(next_step_panel, "st", fake_st)
    monkeypatch.setattr(next_step_panel, "recommend_next_steps", lambda *_a, **_k: [step])
    next_step_panel.render_next_step_panel("📈 数据分析")
    assert fake_st.session_state == {}
