"""隐私声明首次弹窗（h912-12 自 app.py:314-346 原样搬入，行为零变更）。

块内文案、控件、session_state 键（privacy_accepted）与 st.stop() 语义保持原样：
- 未同意时渲染声明并 st.stop()（StopException 穿透函数栈，脚本语义不变）；
- 同意后写 privacy_accepted 并经 user_prefs 持久化，st.rerun() 重跑。
"""

import streamlit as st


def render_privacy_gate() -> None:
    """首次使用弹出隐私声明；未同意则终止本轮脚本（与原内联块逐字等价）。"""
    if not st.session_state.privacy_accepted:
        with st.container():
            st.markdown("### 🔒 隐私声明")
            st.markdown("""
            <div class="info-box">
            <p><strong>数据隐私承诺</strong></p>
            <p>本工具的统计处理和项目存储均在您的本地计算机上完成；项目文件不会由本工具开发者收集。</p>
            <ul>
                <li>上传的数据会进入当前会话，并随自动保存写入本机项目目录，方便恢复</li>
                <li>关闭浏览器不会删除本地项目；可在项目管理或缓存清理中主动删除</li>
                <li>使用云端 AI 功能时，你提交的文本会发送给所选服务商；原始数据不会被自动上传，除非功能明确提示</li>
                <li>文献爬取功能仅向公开 API 发送关键词查询，不涉及个人数据</li>
            </ul>
            <p><em>如使用云端 LLM 服务，请遵守相应平台的数据使用协议。</em></p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✅ 我已阅读并同意", type="primary", width="stretch"):
                    st.session_state.privacy_accepted = True
                    # v3.7: 持久化，下次启动不再弹
                    try:
                        from src.utils.user_prefs import update_pref
                        update_pref("privacy_accepted", True)
                    except Exception:
                        pass
                    st.rerun()

        st.stop()
