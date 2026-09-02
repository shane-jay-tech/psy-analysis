"""全局无障碍样式与键盘导航入口。"""

from __future__ import annotations

import streamlit as st


ACCESSIBILITY_CSS = """
<style>
/* 键盘用户始终能看见焦点；使用双层轮廓兼顾浅色与深色背景。 */
:where(button, input, textarea, select, a, [role="button"], [tabindex]):focus-visible {
    outline: 3px solid #005fcc !important;
    outline-offset: 3px !important;
    box-shadow: 0 0 0 2px #ffffff !important;
}

/* 主要交互目标保持至少 44px，便于触屏和运动能力受限用户。 */
.stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {
    min-height: 44px;
}

.psy-skip-link {
    position: fixed;
    left: 1rem;
    top: -4rem;
    z-index: 1000000;
    padding: .65rem 1rem;
    color: #ffffff !important;
    background: #111111;
    border-radius: .35rem;
    text-decoration: none;
}
.psy-skip-link:focus { top: 1rem; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }
}

@media (forced-colors: active) {
    :where(button, input, textarea, select, a, [role="button"]):focus-visible {
        outline: 3px solid Highlight !important;
    }
}
</style>
<a class="psy-skip-link" href="#psy-main-content">跳至主要内容</a>
<span id="psy-main-content" tabindex="-1"></span>
"""


def render_accessibility_support() -> None:
    """注入静态、无用户输入的无障碍支持。"""
    st.markdown(ACCESSIBILITY_CSS, unsafe_allow_html=True)
