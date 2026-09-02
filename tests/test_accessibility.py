"""全局无障碍支持的静态契约测试。"""

from unittest.mock import patch

from src.ui.accessibility import ACCESSIBILITY_CSS, render_accessibility_support


def test_accessibility_css_covers_keyboard_motion_and_touch_targets():
    assert ":focus-visible" in ACCESSIBILITY_CSS
    assert "outline: 3px" in ACCESSIBILITY_CSS
    assert "min-height: 44px" in ACCESSIBILITY_CSS
    assert "prefers-reduced-motion: reduce" in ACCESSIBILITY_CSS
    assert "forced-colors: active" in ACCESSIBILITY_CSS


def test_accessibility_support_has_skip_link_and_static_safe_markup():
    assert 'href="#psy-main-content"' in ACCESSIBILITY_CSS
    assert 'id="psy-main-content"' in ACCESSIBILITY_CSS
    with patch("streamlit.markdown") as markdown:
        render_accessibility_support()
    markdown.assert_called_once_with(ACCESSIBILITY_CSS, unsafe_allow_html=True)
