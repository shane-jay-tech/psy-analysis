"""实验设计 UI — 从 app.py 拆分出的独立模块"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd

from src.experiment_design import (
    ExperimentDesignEngine, format_power_report,
    design_experiment_llm_async, cancel_design_request, CancelledLLMError,
)


def render_experiment_design_ui():
    """渲染实验设计界面"""
    if st.session_state.experiment_engine is None:
        st.session_state.experiment_engine = ExperimentDesignEngine()

    eng = st.session_state.experiment_engine

    st.title("🧪 实验设计")
    st.caption("输入研究方向 → 智能推荐设计模板 → 统计检验力分析 → 生成完整方案")

    with st.sidebar:
        st.divider()
        st.header("💡 设计指南")
        st.markdown("""
        **支持的设计类型：**
        - 单因素被试间/被试内设计
        - 多因素因素设计
        - 混合实验设计
        - 问卷调查研究
        - 情绪诱发实验
        - 干预研究（前测-后测）
        - 启动实验 / IAT

        **如何使用：**
        1. 输入您的研究方向和目标人群
        2. 可选择指定设计类型偏好
        3. 系统自动推荐最合适的设计模板
        4. 进行统计检验力分析，确定样本量
        5. 生成包含完整程序的实验方案
        """)

        st.divider()
        if st.button("🔄 重置设计", width="stretch"):
            st.session_state.experiment_engine = ExperimentDesignEngine()
            st.rerun()

    # -- 主界面 --
    col_e1, col_e2 = st.columns([3, 1])
    # 前向传递：从向导预填充
    _prefill_topic = st.session_state.pop("_prefill_exp_topic", "")
    _prefill_ivs = st.session_state.pop("_prefill_exp_ivs", "")
    _prefill_dvs = st.session_state.pop("_prefill_exp_dvs", "")
    _prefill_design = st.session_state.pop("_prefill_exp_design_hint", "")
    _design_hint_options = ["自动推荐", "被试间设计", "被试内设计", "混合设计", "问卷调查研究", "干预研究"]
    _design_hint_map = {
        "between": "被试间设计",
        "within": "被试内设计",
        "mixed": "混合设计",
    }
    _design_hint_default = 0
    if _prefill_design in _design_hint_map:
        try:
            _design_hint_default = _design_hint_options.index(_design_hint_map[_prefill_design])
        except ValueError:
            _design_hint_default = 0

    with col_e1:
        exp_topic = st.text_area(
            "请输入您想研究的方向或论题：",
            value=_prefill_topic,
            placeholder="例如：\n"
                       "\"考察不同情绪状态（积极/消极/中性）对大学生认知控制能力的影响\"\n"
                       "\"正念训练对高中生考试焦虑的干预效果研究\"\n"
                       "\"大学生社交焦虑与自尊、社会支持的关系研究\"\n"
                       "\"启动老年人积极老化刻板印象对其记忆表现的影响\"",
            height=100,
            key="exp_topic",
        )
        exp_population = st.text_input(
            "目标人群",
            placeholder="例如：在校大学生、高中生、60岁以上老年人、企业员工",
            key="exp_population",
        )

    with col_e2:
        st.markdown("<br>", unsafe_allow_html=True)

        exp_design_hint = st.selectbox(
            "设计类型偏好",
            _design_hint_options,
            index=_design_hint_default,
            key="exp_design_hint",
        )
        exp_effect = st.selectbox(
            "预期效应量",
            ["中（medium, d=0.5）", "小（small, d=0.2）", "大（large, d=0.8）"],
            key="exp_effect",
        )
        exp_power = st.slider("目标统计检验力", 0.50, 0.99, 0.80, 0.05, key="exp_power")
        use_llm_enhance = st.checkbox(
            "🤖 使用LLM增强设计",
            value=False,
            key="exp_use_llm_enhance",
            help="启用后，系统将调用大语言模型对实验设计进行深度增强（生成更丰富的背景、假设、程序等）。需要配置API密钥。",
        )
        design_btn_exp = st.button("🔬 设计实验", type="primary", width="stretch")

    # 高级选项
    with st.expander("⚙ 高级选项"):
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            exp_ivs = st.text_input(
                "自变量（用逗号分隔，留空自动推断）",
                value=_prefill_ivs,
                placeholder="情绪状态, 任务难度",
                key="exp_ivs",
            )
            exp_dvs = st.text_input(
                "因变量（用逗号分隔，留空自动推断）",
                value=_prefill_dvs,
                placeholder="反应时, 正确率",
                key="exp_dvs",
            )
        with col_adv2:
            exp_n_hint = st.number_input(
                "指定样本量（0=自动计算）",
                min_value=0, value=0, key="exp_n_hint",
                help="留空则由系统通过统计检验力分析自动计算所需样本量",
            )
            exp_include_budget = st.checkbox("包含预算估算", value=False, key="exp_budget")

    # ── LLM 增强 pending 状态 ──
    pending = st.session_state.get("_exp_design_pending")
    if pending is not None:
        st.info("⏳ 正在通过大语言模型增强实验设计，请稍候...")
        col_cancel, _ = st.columns([1, 3])
        with col_cancel:
            if st.button("❌ 取消增强", width="stretch", key="cancel_exp_design"):
                cancel_design_request(pending["cancel_id"])
                try:
                    pending["future"].cancel()
                except Exception:
                    pass
                st.session_state.pop("_exp_design_pending", None)
                st.warning("已取消实验设计增强。")
                st.rerun()

        future = pending["future"]
        if future.done():
            st.session_state.pop("_exp_design_pending", None)
            try:
                llm_result = future.result()
                _apply_llm_enhancement(eng, llm_result)
                st.success("LLM 增强完成！")
            except CancelledLLMError:
                st.warning("实验设计增强已被取消。")
            except Exception as e:
                st.error(f"LLM 增强失败：{e}")
            st.rerun()

    # 执行设计
    if design_btn_exp and exp_topic.strip():
        hint_map = {
            "自动推荐": "", "被试间设计": "被试间", "被试内设计": "被试内",
            "混合设计": "混合", "问卷调查研究": "问卷", "干预研究": "干预",
        }
        effect_map = {"小（small, d=0.2）": "small", "中（medium, d=0.5）": "medium", "大（large, d=0.8）": "large"}

        with st.spinner("正在分析研究方向并设计实验方案..."):
            try:
                design = eng.design_experiment(
                    topic=exp_topic.strip(),
                    target_population=exp_population.strip(),
                    design_type_hint=hint_map.get(exp_design_hint, ""),
                    ivs=[iv.strip() for iv in exp_ivs.split(",") if iv.strip()] or None,
                    dvs=[dv.strip() for dv in exp_dvs.split(",") if dv.strip()] or None,
                    n_subjects_hint=int(exp_n_hint),
                    power=exp_power,
                    effect_size_expected=effect_map[exp_effect],
                    include_budget=exp_include_budget,
                )
                st.success("实验方案设计完成！")
                st.balloons()
            except Exception as e:
                st.error(f"设计失败：{e}")

        # LLM 增强（v4.6: 单轨化，从顶部「🤖 AI 模型」激活的预设读）
        from src.llm_gateway.active_config import get_active_llm_config as _gac_exp
        _exp_cfg = _gac_exp()
        if use_llm_enhance and _exp_cfg:
            async_result = design_experiment_llm_async(
                topic=exp_topic.strip(),
                api_key=_exp_cfg["api_key"],
                base_url=_exp_cfg["base_url"],
                model=_exp_cfg["model"],
                target_population=exp_population.strip(),
                design_type=hint_map.get(exp_design_hint, ""),
                ivs=[iv.strip() for iv in exp_ivs.split(",") if iv.strip()] or None,
                dvs=[dv.strip() for dv in exp_dvs.split(",") if dv.strip()] or None,
                temperature=_exp_cfg["temperature"],
                max_tokens=4096,
                timeout=900,
            )
            st.session_state._exp_design_pending = {
                "future": async_result["future"],
                "cancel_id": async_result["cancel_id"],
            }
            st.rerun()
        elif use_llm_enhance and not _exp_cfg:
            st.warning(
                "未激活 AI 模型，无法使用 LLM 增强。请在侧栏顶部「🤖 AI 模型」选一个预设；"
                r"密钥配在 `D:\code\.env.local`。"
            )

    elif design_btn_exp and not exp_topic.strip():
        st.error("请输入研究方向或论题！")

    # 展示设计方案
    if eng.design is not None:
        d = eng.design

        st.divider()
        st.subheader(f"📋 {d.title}")

        # 概览
        col_ov1, col_ov2, col_ov3, col_ov4 = st.columns(4)
        col_ov1.metric("设计类型", d.design_type_zh)
        col_ov2.metric("模板", d.template_name)
        col_ov3.metric("样本量", f"N = {d.n_subjects}")
        col_ov4.metric("预计时长", f"{d.procedure.total_duration_min}分钟" if d.procedure else "待定")

        # 标签页展示详细内容
        det1, det2, det3, det4, det5 = st.tabs([
            "📖 研究框架", "👥 被试与效力", "🔬 实验程序", "📊 分析计划", "📄 完整报告"
        ])

        with det1:
            st.markdown("### 研究背景与目的")
            st.info(d.background)

            st.markdown("### 研究假设")
            for h in d.hypotheses:
                st.markdown(f"- **{h}**")

            st.markdown("### 变量定义")
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.markdown("**自变量**")
                for iv in d.independent_vars:
                    st.markdown(f"- **{iv['name']}**: {iv.get('type', '')}, {iv.get('levels', '?')}个水平")
                    if 'levels_labels' in iv:
                        st.caption(f"  水平: {', '.join(iv['levels_labels'])}")

                st.markdown("**因变量**")
                for dv in d.dependent_vars:
                    st.markdown(f"- **{dv['name']}**: {dv.get('measure', '')}")
            with col_v2:
                st.markdown("**控制变量**")
                for cv in d.control_vars:
                    st.markdown(f"- {cv}")

        with det2:
            st.markdown("### 目标人群与招募")
            st.markdown(f"**总体：** {d.target_population}")

            col_inc, col_exc = st.columns(2)
            with col_inc:
                st.markdown("**纳入标准**")
                for c in d.inclusion_criteria:
                    st.markdown(f"- ✅ {c}")
            with col_exc:
                st.markdown("**排除标准**")
                for c in d.exclusion_criteria:
                    st.markdown(f"- ❌ {c}")

            st.markdown(f"### 样本量")
            st.markdown(f"**总样本量：N = {d.n_subjects}**")
            if d.n_groups > 1:
                st.markdown(f"**分组：** {d.n_groups}组，每组{d.n_per_group}人")

            if d.power_result:
                with st.expander("📊 统计检验力分析详情"):
                    st.markdown(format_power_report(d.power_result))

        with det3:
            st.markdown("### 实验材料")
            if d.materials:
                for m in d.materials:
                    st.markdown(f"- **{m.get('name', '?')}** ({m.get('items', '?')}题, α={m.get('alpha', '?')})")
                    if m.get('source'):
                        st.caption(f"  来源: {m['source']}")

            st.markdown("### 实验设备")
            for a in d.apparatus:
                st.markdown(f"- {a}")

            if d.procedure:
                st.markdown(f"### 实验程序（总计约{d.procedure.total_duration_min}分钟）")

                # 时间线
                st.markdown("#### 时间线")
                tl_data = []
                for t in d.procedure.timeline:
                    tl_data.append({
                        "阶段": t['name'],
                        "开始(分钟)": t['start_min'],
                        "结束(分钟)": t['end_min'],
                        "时长(分钟)": t['duration_min'],
                    })
                st.dataframe(pd.DataFrame(tl_data), width="stretch")

                # 各阶段详情
                for phase in d.procedure.phases:
                    with st.expander(f"阶段{phase['phase']}: {phase['name']}（{phase['duration_min']}分钟）"):
                        st.write(phase['description'])
                        st.caption("检查清单：")
                        for item in phase.get('checklist', []):
                            st.checkbox(item, key=f"chk_{phase['phase']}_{item[:10]}")

                # 随机化方案
                if d.procedure.randomization:
                    with st.expander("🎲 随机化方案"):
                        st.markdown(f"**方法：** {d.procedure.randomization.get('method', '')}")
                        st.markdown(d.procedure.randomization.get('description', ''))
                        if 'latin_square' in d.procedure.randomization:
                            ls = d.procedure.randomization['latin_square']
                            st.markdown("**拉丁方矩阵：**")
                            for row in ls:
                                st.markdown(f"- {' → '.join(row)}")

                # 平衡方案
                if d.procedure.counterbalancing:
                    with st.expander("⚖ 顺序平衡方案"):
                        st.markdown(f"**方法：** {d.procedure.counterbalancing.get('method', '')}")
                        st.markdown(d.procedure.counterbalancing.get('description', ''))
                        ls = d.procedure.counterbalancing.get('latin_square', [])
                        if ls:
                            for row in ls:
                                st.markdown(f"- {' → '.join(row)}")
                        for rec in d.procedure.counterbalancing.get('additional_recommendations', []):
                            st.info(rec)

        with det4:
            st.markdown(d.analysis_plan_detailed)

        with det5:
            st.markdown("### 📄 完整实验设计报告")
            if st.button("🔄 生成/刷新报告", key="gen_exp_report"):
                pass
            report = eng.format_design_report()
            st.markdown(report)

            # 导出
            import base64
            b64 = base64.b64encode(report.encode("utf-8")).decode()
            title_safe = d.title.replace("/", "-").replace(":", "")
            href = f'<a href="data:text/markdown;base64,{b64}" download="{title_safe}_实验设计方案.md">点击下载 Markdown 文件 (.md)</a>'
            st.markdown(href, unsafe_allow_html=True)

            # v2.8: 实验程序文档 Word 导出
            st.divider()
            st.markdown("#### 📄 下载实验程序文档（Word）")
            st.caption(
                "生成符合实验心理学规范的实验程序文档（.docx），含被试招募、"
                "实验材料、流程、数据字段、伦理说明等 6 大节。可作为预注册附件。"
            )
            researcher = st.text_input(
                "研究者姓名（文档标题页）",
                value="",
                key="exp_protocol_researcher",
            )
            # v2.9: 完整度提示
            try:
                from src.output.docx_exporter import count_protocol_placeholders
                n_missing = count_protocol_placeholders(d)
                if n_missing >= 3:
                    st.warning(
                        f"⚠️ 该文档包含 {n_missing} 个待补充事项，下载后请查看末尾「📝 待补充事项清单」"
                    )
                else:
                    st.success(f"✅ 文档完整度良好（仅 {n_missing} 个待补项）")
            except Exception:
                pass

            if st.button("📄 生成实验程序文档", type="primary",
                         width="stretch", key="exp_protocol_gen"):
                try:
                    from src.output.docx_exporter import build_experiment_protocol_docx
                    with st.spinner("正在生成 Word 文档..."):
                        docx_bytes = build_experiment_protocol_docx(d, researcher=researcher)
                    st.session_state["_exp_protocol_docx"] = docx_bytes
                    from src.utils.export_naming import export_filename
                    st.session_state["_exp_protocol_filename"] = export_filename("实验设计", "docx", title=title_safe)
                except Exception as e:
                    st.error(f"生成失败：{e}")

            if st.session_state.get("_exp_protocol_docx"):
                st.download_button(
                    "⬇ 下载实验程序文档（Word）",
                    data=st.session_state["_exp_protocol_docx"],
                    file_name=st.session_state.get(
                        "_exp_protocol_filename", "实验程序文档.docx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="exp_protocol_dl",
                    width="stretch",
                )

    st.divider()
    st.caption("💡 提示：实验方案基于您输入的研究方向自动生成，建议在此基础上根据具体情况进行调整，并在正式实验前进行预实验。")


def _apply_llm_enhancement(eng, llm_result: dict):
    """将LLM增强结果应用到实验设计对象中。"""
    if eng.design is None:
        return
    d = eng.design
    if llm_result.get("background"):
        d.background = llm_result["background"]
    if llm_result.get("hypotheses"):
        d.hypotheses = llm_result["hypotheses"]
    if llm_result.get("research_questions"):
        d.research_questions = llm_result["research_questions"]
    if llm_result.get("analysis_plan"):
        d.analysis_plan_detailed = llm_result["analysis_plan"]
    if llm_result.get("ethics_notes"):
        d.ethics = llm_result["ethics_notes"]
    if llm_result.get("expected_results"):
        d.notes.append(f"**预期结果：** {llm_result['expected_results']}")
    # 更新 IV 操纵说明
    iv_details = llm_result.get("iv_details", [])
    for iv_detail in iv_details:
        for iv in d.independent_vars:
            if iv.get("name") == iv_detail.get("name"):
                if iv_detail.get("manipulation"):
                    iv["manipulation"] = iv_detail["manipulation"]
                if iv_detail.get("levels"):
                    iv["levels_labels"] = iv_detail["levels"]
    # 更新 DV 测量详情
    dv_details = llm_result.get("dv_details", [])
    for dv_detail in dv_details:
        for dv in d.dependent_vars:
            if dv.get("name") == dv_detail.get("name"):
                if dv_detail.get("details"):
                    dv["measure"] = dv_detail["details"]
    # 更新程序阶段
    procedure_phases = llm_result.get("procedure_phases", [])
    if procedure_phases and d.procedure:
        for i, phase in enumerate(procedure_phases):
            if i < len(d.procedure.phases):
                if phase.get("description"):
                    d.procedure.phases[i]["description"] = phase["description"]
                if phase.get("checklist"):
                    d.procedure.phases[i]["checklist"] = phase["checklist"]
    d.notes.append("🤖 本设计已通过LLM深度增强")
