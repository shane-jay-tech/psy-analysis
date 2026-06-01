"""5 分钟引导路径 — 首次访问时让新用户秒懂系统能力。

设计：
- 检测条件：onboarding_completed=False + 无 df + 无 analysis_history
- 引导步骤：欢迎 → 加载演示数据 → 自动跑 t 检验 → 跳到第 7 步看产出
- 任意步骤可"跳过引导"，标记 onboarding_completed=True 不再显示
"""

from __future__ import annotations

import streamlit as st


ONBOARDING_KEY = "onboarding_completed"
ONBOARDING_STAGE_KEY = "_onboarding_stage"  # welcome / loading / running / done
SKIP_KEY = "_onboarding_skipped"


def is_first_visit() -> bool:
    """判断是否首次访问（无任何数据 + 未完成引导 + 未跳过）。"""
    if st.session_state.get(SKIP_KEY):
        return False
    if st.session_state.get(ONBOARDING_KEY):
        return False
    if st.session_state.get("df") is not None:
        return False
    if st.session_state.get("analysis_history"):
        return False
    return True


def mark_onboarding_done():
    st.session_state[ONBOARDING_KEY] = True
    st.session_state.pop(ONBOARDING_STAGE_KEY, None)


def skip_onboarding():
    st.session_state[SKIP_KEY] = True
    st.session_state[ONBOARDING_KEY] = True


def render_onboarding_card() -> bool:
    """渲染首次访问引导卡片，返回是否显示了卡片（影响后续渲染逻辑）。"""
    if not is_first_visit():
        return False

    stage = st.session_state.get(ONBOARDING_STAGE_KEY, "welcome")

    with st.container():
        if stage == "welcome":
            _render_welcome()
        elif stage == "loading":
            _render_loading()
        elif stage == "running":
            _render_running()

    return True


def _render_welcome():
    """欢迎页 + 选择路径。"""
    st.markdown(
        """
<div style="background:linear-gradient(135deg,#fff8e7 0%,#ffeacc 100%);
            border-left:5px solid #f5a623;padding:20px 24px;
            border-radius:8px;margin:8px 0 18px 0;">
<h2 style="margin-top:0;">👋 欢迎使用心理学研究工具</h2>
<p style="font-size:1.05em;margin-bottom:14px;">
你将看到一个完整的<strong>本科论文产出流程</strong>：
从数据分析到 Word 论文初稿、答辩备战手册、论文版图表，一气呵成。
</p>
<p style="font-size:0.95em;color:#555;">
🎯 <strong>5 分钟体验</strong>：用演示数据走完一遍，看看每个产出物长什么样。<br>
🚀 <strong>直接开始</strong>：跳过演示，进入向导从你自己的研究开始。
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    cols = st.columns([1, 1])
    if cols[0].button(
        "🎯 5 分钟体验（推荐新用户）",
        type="primary",
        use_container_width=True,
        key="ob_start_demo",
    ):
        st.session_state[ONBOARDING_STAGE_KEY] = "loading"
        st.rerun()
    if cols[1].button(
        "🚀 直接开始我的研究",
        use_container_width=True,
        key="ob_skip",
    ):
        skip_onboarding()
        st.rerun()

    with st.expander("💡 这个系统能帮我做什么？", expanded=False):
        st.markdown(
            """
- **数据分析**：26 种本科常用统计检验（t 检验、ANOVA、相关、回归、信度、EFA…）
- **论文产出**：APA7 中文 Word 初稿，含描述统计表、嵌入图表、自定义封面
- **答辩备战**：基于你的方法生成 7-10 个答辩问题，分级（必问/常问/刁钻），含 PDF 手册
- **图表收藏夹**：跨会话累积所有论文图表，一键批量 ZIP 导出
- **数据清洗向导**：缺失值、常数列、异常值一键处理，自动生成方法段落
- **论文交付包**：一个 ZIP 含 Word + PDF + 图表集 + README
"""
        )


def _render_loading():
    """加载演示数据。"""
    st.markdown(
        """
<div style="background:#e8f4fd;border-left:5px solid #4472c4;
            padding:16px 20px;border-radius:6px;margin:8px 0;">
<h3 style="margin-top:0;">📊 第 1/3 步：加载演示数据</h3>
<p>正在加载一份模拟的<strong>大学生社交焦虑问卷</strong>（n=200）：</p>
<ul style="margin-top:8px;">
<li>因变量：社交焦虑总分、自尊总分</li>
<li>自变量：性别、年级</li>
<li>含 ~3% 随机缺失（演示数据真实性）</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button(
        "▶ 加载演示数据并继续",
        type="primary",
        use_container_width=True,
        key="ob_load_demo",
    ):
        from src.data.demo_datasets import generate_demo_questionnaire_data
        from src.data.inspector import inspect_dataframe

        df = generate_demo_questionnaire_data(200)
        st.session_state.df = df
        st.session_state.file_name = "演示数据_社交焦虑问卷.csv"
        st.session_state.meta = {"source_type": "csv", "row_count": 200, "col_count": 10}
        st.session_state.inspector = inspect_dataframe(df)
        st.session_state[ONBOARDING_STAGE_KEY] = "running"
        st.rerun()

    cols = st.columns([1, 5])
    if cols[0].button("⏭ 跳过", key="ob_skip2"):
        skip_onboarding()
        st.rerun()


def _render_running():
    """自动跑 t 检验 + 引导到向导第 7 步。"""
    st.markdown(
        """
<div style="background:#e8f5e8;border-left:5px solid #4caf50;
            padding:16px 20px;border-radius:6px;margin:8px 0;">
<h3 style="margin-top:0;">🔬 第 2/3 步：自动运行 t 检验</h3>
<p>系统将自动运行<strong>「比较性别在社交焦虑总分上的差异」</strong>，
等价于：进入向导 → 选「比较组间差异」→ 推荐独立样本 t 检验 → 一键运行。</p>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button(
        "▶ 一键运行 t 检验",
        type="primary",
        use_container_width=True,
        key="ob_run_demo",
    ):
        try:
            from src.parser.intent_resolver import resolve as resolve_intent
            from src.analysis.runner import run_analysis

            df = st.session_state.df
            inspector = st.session_state.inspector
            plan = resolve_intent(
                df, "比较 性别 各组在 社交焦虑总分 上的差异",
                col_info=inspector,
            )
            output = run_analysis(df, plan)

            # 注入向导上下文（让第 7 步就有数据）
            wiz_data = st.session_state.setdefault("undergrad_wizard_data", {})
            wiz_data["df"] = df
            wiz_data["inspector"] = inspector
            wiz_data["wizard_results_context"] = {
                "test_type": output.get("test_type", "independent_ttest"),
                "test_name_zh": output.get("test_name_zh", "独立样本t检验"),
                "sample_size": len(df),
                "dv": "社交焦虑总分",
                "iv": "性别",
                "variables": list(df.columns),
            }

            st.session_state.plan = plan
            st.session_state.analysis_output = output
            st.session_state.analysis_history = [
                {"test_type": "independent_ttest", "dv": ["社交焦虑总分"], "iv": ["性别"]},
            ]

            # 切到向导 + 第 7 步
            st.session_state.undergrad_mode = True
            st.session_state.undergrad_path = "survey"
            st.session_state.undergrad_step = 7
            # 同步到 wiz_data
            wiz_data["plan"] = plan
            wiz_data["analysis_output"] = output

            mark_onboarding_done()
            st.rerun()
        except Exception as e:
            st.error(f"演示运行失败：{e}（请尝试「直接开始我的研究」）")
            if st.button("🚀 直接开始", key="ob_fallback"):
                skip_onboarding()
                st.rerun()

    cols = st.columns([1, 5])
    if cols[0].button("⏭ 跳过", key="ob_skip3"):
        skip_onboarding()
        st.rerun()


def render_post_demo_highlight():
    """演示完成后在第 7 步顶部显示亮点引导（仅一次）。"""
    if st.session_state.get("_post_demo_highlight_shown"):
        return
    if not st.session_state.get(ONBOARDING_KEY):
        return
    # 仅在 onboarding 刚完成且当前是第 7 步时显示
    if st.session_state.get("undergrad_step") != 7:
        return

    st.success(
        "🎉 **演示完成！现在你看到的是论文产出页面。建议依次尝试：**\n\n"
        "1. **📄 下载 Word 论文初稿** — 看看 APA7 中文论文长什么样\n"
        "2. **🎤 答辩问题预演** — 系统给你 7 个针对性问题 + 标准答案\n"
        "3. **📦 批量下载所有图表** — 论文版 PNG（300dpi 灰度）\n"
        "4. **🎁 一键打包论文交付包** — Word + PDF + 图表 + README\n\n"
        "完成体验后，回到侧边栏切换到「📊 数据分析」上传你自己的数据即可。"
    )
    st.session_state["_post_demo_highlight_shown"] = True
