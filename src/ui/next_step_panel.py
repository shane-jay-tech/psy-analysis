"""标准模式的紧凑“下一步”导航。"""

from __future__ import annotations

import html
import streamlit as st

from src.ui.navigation import PAGE_MODES
from src.utils.next_step_engine import recommend_next_steps


def render_next_step_panel(current_mode: str) -> None:
    """显示最高优先级建议，并允许一键跳转到真实存在的主入口。"""
    steps = recommend_next_steps(st.session_state, max_steps=1)
    if not steps:
        return
    step = steps[0]
    if step.page_target not in PAGE_MODES:
        return

    title = html.escape(str(step.title))
    description = html.escape(str(step.description))
    status_icon = "⛔" if step.blocked else ("📍" if step.page_target == current_mode else "→")
    st.markdown(
        f'<div class="psy-next-step"><strong>{status_icon} 下一步：{title}</strong>'
        f'<span>{description}</span></div>',
        unsafe_allow_html=True,
    )
    if step.blocked:
        return
    if step.page_target == current_mode:
        return
    if st.button(
        f"继续到 {step.page_target}",
        key=f"_next_step_{step.step_id}",
        width="stretch",
        help=step.description,
    ):
        # app_mode 已绑定本轮 radio，不能在控件实例化后直接改；下一轮渲染前应用。
        st.session_state["_pending_app_mode"] = step.page_target
        st.rerun()
