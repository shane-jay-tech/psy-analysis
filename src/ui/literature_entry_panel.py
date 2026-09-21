"""文献与选题页主路由（s922-101 自 app.py 片 8 逐字节迁入）。

原位置：app.py:2397-2427 `elif mode == "📚 文献与选题":` 的分支体，
行内容与其缩进层级**未作一字改动**（分支体基础缩进 4 空格 == 本函数体缩进）。

会话依赖口径：本片对 session_state **只做整对象透传**
（`get_upstream_state(st.session_state)`），不读写任何具体键 ——
与已迁样例 `src/ui/deliverable_center_panel.py` 同范式。
调用点必须保持与迁移前同位、同序，以保证 Streamlit widget 创建顺序不变。
"""

import streamlit as st


def render_literature_entry_panel():
    """渲染「文献与选题」三 tab（选题与综述 / 文献雷达 / 文献审核）。"""
    st.title("📚 文献与选题")
    _tab_funnel, _tab_feed, _tab_review = st.tabs(["选题与综述", "文献雷达", "文献审核"])
    with _tab_funnel:
        from src.utils.workspace import get_upstream_state as _get_upstream_v37
        _upstream_v37 = _get_upstream_v37(st.session_state)
        _tier_v37 = _upstream_v37.get("tier", "beginner")
        _sub_tab_f, _sub_tab_l = st.tabs(["选题漏斗", "文献综述工作台"])
        with _sub_tab_f:
            from src.ui.upstream_panel import render_advanced_skip_form, render_funnel
            if _tier_v37 == "advanced":
                render_advanced_skip_form()
            else:
                render_funnel()
        with _sub_tab_l:
            from src.ui.literature_review_panel import render_literature_review
            render_literature_review(tier=_tier_v37)
    with _tab_feed:
        try:
            from src.literature_feed.ui import render_literature_feed
            render_literature_feed()
        except Exception as _feed_err:
            st.error(f"文献雷达加载失败：{_feed_err}")
    with _tab_review:
        try:
            from src.literature_feed.storage.feed_store import FeedStore as _ReviewFS
            from src.ui.literature_review_queue_panel import render_review_queue
            _review_store = _ReviewFS()
            render_review_queue(_review_store)
        except Exception as _review_err:
            st.error(f"文献审核加载失败：{_review_err}")
