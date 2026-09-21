# -*- coding: utf-8 -*-
"""问卷设计页的混装侧栏（s922-102 自 app.py 片 7a 逐字节迁入）。

原位置：app.py:1586-1639 `elif mode == "📋 问卷设计":` 分支内的 `with st.sidebar:` 块。
行内容与其缩进层级未作改动；**唯一改动**是 3 处会话状态的接收者，由 streamlit 模块别名
换成下面的形参 `session_state`（调用侧传进去的就是 app.py 里那个会话状态对象本身，
同一对象，属性读写语义完全相同）。

会话口径：本块对 `language` 键是**读写同块闭合**（原 :1593/:1597 读、:1598 写，全在块内），
键的初值仍由 app.py 的模块级 `_defaults`（app.py:107）播种 ⇒ 不构成生产者/消费者跨文件拆分。
问卷主体输入框的会话键与快速模板区段**不在本模块**（属片 7b）。
"""

import streamlit as st

from src.utils.i18n import t
from src.utils.memory_manager import render_memory_manager_ui


def render_settings_sidebar_panel(session_state):
    """渲染问卷页侧栏：语言切换 / LLM 状态 / 记忆管理 / 使用指南。

    `session_state` 必须是调用方的会话状态本体（不是拷贝），否则语言切换的
    写入不会回流、rerun 之后读到的还是旧值。
    """
    with st.sidebar:
        st.divider()
        st.header("🌐 " + t("language"))
        lang = st.radio(
            "",
            ["zh", "en"],
            format_func=lambda x: t("chinese") if x == "zh" else t("english"),
            index=0 if session_state.language == "zh" else 1,
            key="lang_select",
            horizontal=True,
        )
        if lang != session_state.language:
            session_state.language = lang
            st.rerun()

        st.divider()
        st.header("🤖 LLM 状态")
        from src.llm_gateway.active_config import get_active_llm_config as _get_llm
        _active_cfg = _get_llm()
        if _active_cfg:
            st.success(f"✅ `{_active_cfg.get('model', '?')}` 已激活（来自顶部「🤖 AI 模型」）")
        else:
            st.info(
                "📴 未激活 LLM — 将走关键词匹配引擎。\n"
                "如需 LLM：在侧栏顶部「🤖 AI 模型」选一个预设；"
                r"密钥配在 `D:\code\.env.local`（模板见 `.env.local.example`）。"
            )

        # Memory manager
        render_memory_manager_ui()

        st.divider()
        st.header("💡 使用指南")
        st.markdown("""
        **如何使用：**
        1. 在输入框中描述您想测量的心理学构念
        2. （可选）配置 LLM 以获得更智能的设计
        3. 系统自动分析并生成维度框架和题目
        4. 查看完整设计报告（含参考文献）

        **支持领域：**
        - 临床与健康心理
        - 人格心理学
        - 社会心理学
        - 教育心理学
        - 认知心理学
        - 组织行为学

        **示例输入：**
        - "调查大学生的社交焦虑水平"
        - "测量员工的工作满意度"
        - "编制一个大学生自尊量表"
        - "我想研究青少年的学习动机"
        """)
