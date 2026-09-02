"""上游漏斗 UI（v3.2）：5 阶段步进器 + AI 苏格拉底对话 + ADVANCED 跳过表单。

入口：
- render_funnel()                — BEGINNER 完整 5 阶段
- render_advanced_skip_form()    — ADVANCED tier 一次性表单（v3.3 才做完整折叠）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from src.paper_writer.ai_tutor import ChatMessage
from src.upstream.feasibility_check import (
    check_falsifiability,
    check_measurability,
    check_operability,
    suggest_significance_reflection,
)
from src.upstream.tier import ResearchTier, get_active_tier, set_active_tier
from src.upstream.topic_funnel import (
    MAX_STAGE,
    MIN_STAGE,
    STAGES,
    advance_stage,
    archive_current_branch_and_restart,
    complete_funnel,
    delete_branch,
    get_funnel_history,
    get_stage,
    get_stage_data,
    go_to_stage,
    recognize_constructs,
    set_candidate_vars,
    switch_to_branch,
    update_stage_data,
)
from src.llm_gateway.active_config import is_llm_active
from src.upstream.socratic_engine import ask_socratic, ask_socratic_stream

# v3.6 流式输出开关（可在 session_state 覆盖以便测试关闭）
ENABLE_STREAMING = True


def _streaming_enabled() -> bool:
    return bool(st.session_state.get("_enable_streaming", ENABLE_STREAMING))


def _ask_socratic_with_streaming(
    stage: int,
    user_input: str,
    history,
    *,
    topic_hint: str = "",
) -> str:
    """v3.6: 带流式 UI 渲染的反问调用。

    流式可用时：占位符 + 取消按钮 + 打字机效果
    禁用时：回退同步调用
    """
    if not _streaming_enabled():
        return ask_socratic(
            stage=stage,
            user_input=user_input,
            history=history,
            llm_config=_get_llm_config(),
            topic_hint=topic_hint,
        )

    placeholder = st.empty()
    placeholder.markdown("_AI 正在反问..._")

    buffer: list = []
    _chunk_count = [0]

    def _on_chunk(chunk: str) -> None:
        buffer.append(chunk)
        _chunk_count[0] += 1
        if _chunk_count[0] % 15 == 0 or len(chunk) > 20:
            placeholder.markdown(f"🤖 {''.join(buffer)}▌")

    full = ask_socratic_stream(
        stage=stage,
        user_input=user_input,
        history=history,
        llm_config=_get_llm_config(),
        topic_hint=topic_hint,
        on_chunk=_on_chunk,
    )
    placeholder.markdown(f"🤖 {full}")
    return full
from src.utils.workspace import UPSTREAM_SESSION_KEY, get_upstream_state


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def render_funnel() -> None:
    """BEGINNER 完整漏斗。从 upstream_state.current_stage 决定渲染哪一阶段。"""
    upstream = get_upstream_state(st.session_state)

    # v3.3: 首次进入显示「用户契约」，确认后才进漏斗
    if not st.session_state.get("funnel_intro_shown"):
        _render_user_contract()
        return

    # 顶部：步进器 + tier 选择
    _render_header()
    # v3.3: 选题历史分支面板（仅当有归档分支时显示）
    _render_branch_history_panel()
    _render_stepper(upstream.get("current_stage", MIN_STAGE))

    # LLM 配置检查（强制：v3.2 决策）
    if not is_llm_active():
        _render_llm_required_card()
        return

    # v3.3: 第一次进入漏斗（无对话历史）展示「反问示例」+ LLM 质量预检
    if _is_first_funnel_visit(upstream):
        _render_quality_preview()

    # v3.3: 显示上一轮 LLM 反问质量软警告（如有）
    _quality_warn = st.session_state.get("_funnel_quality_warning")
    if _quality_warn:
        st.warning(_quality_warn)
        if st.button("已了解", key="_quality_warn_dismiss"):
            st.session_state["_funnel_quality_warning"] = None
            st.rerun()

    cur = int(upstream.get("current_stage", MIN_STAGE))
    # v3.7 N6: 记录断点位置
    try:
        from src.utils.workspace import update_last_position
        update_last_position("funnel", step=cur, session_state=st.session_state)
    except Exception:
        pass
    if cur == 1:
        _render_stage_1(upstream)
    elif cur == 2:
        _render_stage_2(upstream)
    elif cur == 3:
        _render_stage_3(upstream)
    elif cur == 4:
        _render_stage_4(upstream)
    elif cur == 5:
        _render_stage_5(upstream)


def render_advanced_skip_form() -> None:
    """ADVANCED tier：一次性表单收集核心字段，不走苏格拉底反问。

    v3.3 增加最简留痕：研究问题来源/动机/最关心发现（用于答辩问答自动生成）。
    """
    upstream = get_upstream_state(st.session_state)
    _render_header(advanced=True)
    _render_branch_history_panel()

    st.markdown("**研究生模式**：直接填写核心字段 + 简短动机说明（用于答辩问答自动生成）。")

    existing_meta = upstream.get("advanced_meta") or {}
    with st.form("advanced_skip_form"):
        rq = st.text_area(
            "研究问题（可选标准句式：「在[人群]中，[X] 是否影响 [Y]？」）",
            value=upstream.get("research_question", ""),
            max_chars=300,
        )
        cols = st.columns(3)
        dv = cols[0].text_input("因变量（DV）", value=", ".join(
            (upstream.get("candidate_vars") or {}).get("dependent_vars", [])
        ))
        iv = cols[1].text_input("自变量（IV）", value=", ".join(
            (upstream.get("candidate_vars") or {}).get("independent_vars", [])
        ))
        cov = cols[2].text_input("协变量（用逗号分隔，可选）", value=", ".join(
            (upstream.get("candidate_vars") or {}).get("covariates", [])
        ))

        st.markdown("---")
        st.markdown("**研究动机留痕**（必填，每项 ≤100 字，用于答辩问答自动生成）")

        SOURCE_OPTIONS = ["已有想法", "老师指定", "文献启发", "实习观察", "其他"]
        existing_source = existing_meta.get("source", "")
        source_index = SOURCE_OPTIONS.index(existing_source) if existing_source in SOURCE_OPTIONS else 0
        source = st.radio(
            "你的研究问题来源",
            options=SOURCE_OPTIONS,
            index=source_index,
            horizontal=True,
        )
        why = st.text_area(
            "为什么选这个问题？",
            value=existing_meta.get("why", ""),
            max_chars=100,
            height=68,
            placeholder="一句话即可。例如：身边同学普遍受困于此，但缺乏针对性研究。",
        )
        most_care = st.text_area(
            "你最关心的发现是什么？",
            value=existing_meta.get("most_care", ""),
            max_chars=100,
            height=68,
            placeholder="一句话即可。例如：希望验证 X 是否真的能预测 Y。",
        )

        submitted = st.form_submit_button("✅ 完成并进入 wizard", type="primary")
        if submitted:
            errors = []
            if not rq.strip():
                errors.append("请填写研究问题")
            if not why.strip():
                errors.append("请填写「为什么选这个问题？」")
            if not most_care.strip():
                errors.append("请填写「你最关心的发现是什么？」")
            if len(why) > 100:
                errors.append(f"「为什么」字数超限（{len(why)}/100）")
            if len(most_care) > 100:
                errors.append(f"「最关心发现」字数超限（{len(most_care)}/100）")
            if errors:
                for e in errors:
                    st.error(e)
                return

            upstream["research_question"] = rq.strip()
            upstream["advanced_meta"] = {
                "source": source,
                "why": why.strip(),
                "most_care": most_care.strip(),
            }
            set_candidate_vars(
                st.session_state,
                dependent_vars=[s.strip() for s in dv.split(",") if s.strip()],
                independent_vars=[s.strip() for s in iv.split(",") if s.strip()],
                grouping_var=iv.split(",")[0].strip() if iv.strip() else "",
                covariates=[c.strip() for c in cov.split(",") if c.strip()],
            )
            complete_funnel(st.session_state)
            st.success("已完成上游设置，进入 wizard...")
            st.rerun()


# ---------------------------------------------------------------------------
# 顶部
# ---------------------------------------------------------------------------

def _render_header(advanced: bool = False) -> None:
    title = "🔬 选题漏斗（研究生快速通道）" if advanced else "🔬 选题漏斗"
    st.markdown(
        f"""<div class="psy-hero psy-hero--info">
<span class="psy-hero__eyebrow">全流程引导</span>
<h3>{title}</h3>
<p class="psy-hero__lead">
从「我想研究 XX」收敛到「可研究的具体问题」。
AI 助教只反问，不替你做决定 —— 你想得越透，论文越扎实。
</p></div>""",
        unsafe_allow_html=True,
    )

    # tier 切换器
    cur_tier = get_active_tier(st.session_state)
    cols = st.columns([3, 1])
    with cols[1]:
        choice = st.selectbox(
            "学历层次",
            options=["本科生", "研究生"],
            index=0 if cur_tier == ResearchTier.BEGINNER else 1,
            key="_funnel_tier_picker",
        )
        target = ResearchTier.BEGINNER if choice == "本科生" else ResearchTier.ADVANCED
        if target != cur_tier:
            set_active_tier(st.session_state, target)
            # 切到 ADVANCED 时跳过漏斗
            if target == ResearchTier.ADVANCED:
                upstream = get_upstream_state(st.session_state)
                upstream["phase"] = "funnel"
                upstream["tier"] = "advanced"
            st.rerun()


def _render_stepper(current_stage: int) -> None:
    """5 阶段步进器（点击可跳转）。"""
    cols = st.columns(5)
    for i, stage in enumerate(STAGES):
        with cols[i]:
            label = f"<strong>{stage.id}. {stage.name}</strong>" if stage.id == current_stage else f"{stage.id}. {stage.name}"
            state = "active" if stage.id == current_stage else (
                "complete" if stage.id < current_stage else "upcoming"
            )
            st.markdown(
                f"<div class='psy-stepper psy-stepper--{state}'>{label}</div>",
                unsafe_allow_html=True,
            )
    st.write("")


# ---------------------------------------------------------------------------
# 阶段 1：兴趣捕捉
# ---------------------------------------------------------------------------

def _render_stage_1(upstream: Dict[str, Any]) -> None:
    stage = get_stage(1)
    st.markdown(f"### 阶段 1：{stage.name}")
    st.caption(stage.description)

    data = get_stage_data(upstream, 1)
    text = st.text_area(
        "你想研究什么？（自由描述，2000 字内）",
        value=data.get("interest_text", ""),
        height=120,
        max_chars=2000,
        key="_funnel_stage1_text",
        placeholder="例如：我发现身边很多同学睡前刷手机停不下来，第二天上课很困……",
    )

    cols = st.columns([1, 1, 2])
    if cols[0].button("💬 让 AI 反问我", key="_funnel_stage1_ask", type="primary"):
        if text.strip():
            update_stage_data(upstream, 1, interest_text=text)
            history = data.get("ai_history") or []
            history.append(ChatMessage(role="user", content=text.strip()))
            reply = _ask_socratic_with_streaming(
                stage=1,
                user_input=text.strip(),
                history=history[:-1],
            )
            history.append(ChatMessage(role="assistant", content=reply))
            update_stage_data(upstream, 1, ai_history=history, interest_text=text)
            warn = warn_if_low_quality_reply(reply)
            if warn:
                st.session_state["_funnel_quality_warning"] = warn
            st.rerun()
        else:
            st.warning("请先描述你想研究的内容")

    if cols[1].button("➡️ 进入下一阶段", key="_funnel_stage1_next"):
        if not text.strip():
            st.warning("请先填写内容再推进")
        else:
            update_stage_data(upstream, 1, interest_text=text, completed=True)
            advance_stage(st.session_state)
            st.rerun()

    _render_history(data.get("ai_history") or [])


# ---------------------------------------------------------------------------
# 阶段 2：现象具象化
# ---------------------------------------------------------------------------

def _render_stage_2(upstream: Dict[str, Any]) -> None:
    stage = get_stage(2)
    st.markdown(f"### 阶段 2：{stage.name}")
    st.caption(stage.description)

    data = get_stage_data(upstream, 2)
    prev_interest = get_stage_data(upstream, 1).get("interest_text", "")
    if prev_interest:
        with st.expander("📌 阶段 1 你的描述", expanded=False):
            st.write(prev_interest)

    text = st.text_area(
        "把它写成「什么人 + 什么场景 + 什么差异」",
        value=data.get("interest_text", ""),
        height=120,
        max_chars=2000,
        key="_funnel_stage2_text",
        placeholder="例如：大学生（什么人）在睡前（什么场景），刷手机时长不同的人焦虑水平不同（什么差异）",
    )

    cols = st.columns([1, 1, 1, 1])
    if cols[0].button("💬 让 AI 反问", key="_funnel_stage2_ask"):
        if text.strip():
            history = data.get("ai_history") or []
            history.append(ChatMessage(role="user", content=text.strip()))
            reply = _ask_socratic_with_streaming(
                stage=2,
                user_input=text.strip(),
                history=history[:-1],
                topic_hint=text.strip()[:30],
            )
            history.append(ChatMessage(role="assistant", content=reply))
            update_stage_data(upstream, 2, ai_history=history, interest_text=text)
            warn = warn_if_low_quality_reply(reply)
            if warn:
                st.session_state["_funnel_quality_warning"] = warn
            st.rerun()

    if cols[1].button("⬅️ 上一阶段", key="_funnel_stage2_back"):
        go_to_stage(st.session_state, 1)
        st.rerun()
    if cols[2].button("➡️ 下一阶段", key="_funnel_stage2_next", type="primary"):
        if not text.strip():
            st.warning("请先填写")
        else:
            update_stage_data(upstream, 2, interest_text=text, completed=True)
            advance_stage(st.session_state)
            st.rerun()

    _render_history(data.get("ai_history") or [])


# ---------------------------------------------------------------------------
# 阶段 3：变量识别（接 IntentRecognitionChain）
# ---------------------------------------------------------------------------

def _render_stage_3(upstream: Dict[str, Any]) -> None:
    stage = get_stage(3)
    st.markdown(f"### 阶段 3：{stage.name}")
    st.caption(stage.description)

    # 自动用阶段 1+2 的描述触发识别
    combined = (
        get_stage_data(upstream, 1).get("interest_text", "") + "。" +
        get_stage_data(upstream, 2).get("interest_text", "")
    )

    if st.button("🔍 自动识别候选构念", key="_funnel_stage3_recognize", type="primary"):
        with st.spinner("正在匹配 construct_kb..."):
            result = recognize_constructs(combined, llm_config=_get_llm_config())
        update_stage_data(upstream, 3, output={"recognition": result})
        st.rerun()

    output = get_stage_data(upstream, 3).get("output") or {}
    rec = output.get("recognition")
    if rec:
        if rec["candidates"]:
            st.success(f"识别到 {len(rec['candidates'])} 个候选：")
            for c in rec["candidates"]:
                st.write(f"- **{c['name']}**（置信度 {c['confidence']:.0%}，领域：{c['domain']}）— {c['reason']}")
        else:
            st.info(rec.get("suggestion", "未识别到候选构念"))

    # 用户手动确认/输入候选变量（v3.2 简化：让用户直接填）
    st.markdown("---")
    st.markdown("**确认候选变量**（可手动编辑）")
    cv = upstream.get("candidate_vars") or {}
    cols = st.columns(3)
    dv_input = cols[0].text_input("因变量 DV", value=", ".join(cv.get("dependent_vars", [])))
    iv_input = cols[1].text_input("自变量 IV", value=", ".join(cv.get("independent_vars", [])))
    cov_input = cols[2].text_input("协变量（可选）", value=", ".join(cv.get("covariates", [])))

    cols2 = st.columns([1, 1, 1, 1])
    if cols2[0].button("⬅️ 上一阶段", key="_funnel_stage3_back"):
        go_to_stage(st.session_state, 2)
        st.rerun()
    if cols2[1].button("➡️ 下一阶段", key="_funnel_stage3_next", type="primary"):
        dvs = [s.strip() for s in dv_input.split(",") if s.strip()]
        ivs = [s.strip() for s in iv_input.split(",") if s.strip()]
        covs = [s.strip() for s in cov_input.split(",") if s.strip()]
        if not dvs or not ivs:
            st.warning("至少需要 1 个因变量和 1 个自变量")
            return
        set_candidate_vars(
            st.session_state,
            dependent_vars=dvs,
            independent_vars=ivs,
            grouping_var=ivs[0],
            covariates=covs,
        )
        update_stage_data(upstream, 3, completed=True)
        advance_stage(st.session_state)
        st.rerun()


# ---------------------------------------------------------------------------
# 阶段 4：可研究性检查（v3.2 仅 2 项）
# ---------------------------------------------------------------------------

def _render_stage_4(upstream: Dict[str, Any]) -> None:
    stage = get_stage(4)
    st.markdown(f"### 阶段 4：{stage.name}")
    st.caption(stage.description)

    data = get_stage_data(upstream, 4)

    # 4.1 可证伪
    st.markdown("#### ① 可证伪检查")
    falsi_answer = st.text_area(
        "如果你的假设错了，数据会长什么样？",
        value=(data.get("output") or {}).get("falsifiable_raw", ""),
        height=80,
        max_chars=500,
        key="_funnel_stage4_falsi",
    )
    falsi_result = check_falsifiability(falsi_answer)
    if falsi_result["answered"]:
        if falsi_result["warning"]:
            st.warning(falsi_result["warning"])
        else:
            st.success("✓ 已记录可证伪条件")

    # 4.2 可测量
    st.markdown("#### ② 可测量检查")
    cv = upstream.get("candidate_vars") or {}
    measure_result = check_measurability(cv)
    if measure_result.get("results"):
        for r in measure_result["results"]:
            if r["scales"]:
                st.success(f"✓ **{r['variable']}** → 「{r['matched_construct']}」，"
                            f"参考量表：{r['scales'][0]}")
            else:
                st.warning(f"⚠ **{r['variable']}**：{r['warning']}")
    else:
        st.info(measure_result.get("warning", ""))

    # 4.3 v3.3 可操作（资源/伦理）
    st.markdown("#### ③ 可操作检查（资源与伦理）")
    rq_for_op = upstream.get("research_question") or (
        get_stage_data(upstream, 1).get("interest_text", "") + "。" +
        get_stage_data(upstream, 2).get("interest_text", "")
    )
    op_result = check_operability(rq_for_op, cv)
    if op_result.is_feasible:
        st.success("✓ 未发现高门槛资源依赖，本科可执行")
        # v3.4 时间预算估算
        if op_result.time_budget:
            tb = op_result.time_budget
            with st.container():
                st.markdown(
                    f"""<div style="background:#e8f4fd;border-left:4px solid #2e86de;
                    padding:12px 16px;border-radius:6px;margin:8px 0;">
                    <strong>⏱️ 建议时间预算</strong>：{tb['suggestion']}<br>
                    <span style="font-size:0.9em;color:#555;">
                    研究类型：{tb['design_label']}（{tb['weeks_min']}-{tb['weeks_max']} 周）
                    </span></div>""",
                    unsafe_allow_html=True,
                )
                with st.expander("📋 时间分配建议", expanded=False):
                    for line in tb.get("breakdown", []):
                        st.markdown(f"- {line}")
    else:
        for c in op_result.concerns:
            st.warning(f"⚠ {c['issue']}")
        if op_result.suggestions:
            with st.expander("💡 替代方案", expanded=True):
                for s in op_result.suggestions:
                    st.markdown(f"- {s}")

    # 4.4 v3.3 有意义反思（不打分，只提示）
    st.markdown("#### ④ 有意义反思（💭 不打分）")
    if st.button("📝 生成反思问题", key="_funnel_stage4_reflect"):
        with st.spinner("生成反思问题..."):
            reflect = suggest_significance_reflection(
                rq_for_op, llm_config=_get_llm_config(),
            )
        update_stage_data(upstream, 4,
                          output={**(get_stage_data(upstream, 4).get("output") or {}),
                                  "reflection_questions": reflect["questions"],
                                  "reflection_is_llm": reflect["is_llm_generated"]})
        st.rerun()

    reflection = (get_stage_data(upstream, 4).get("output") or {}).get("reflection_questions")
    if reflection:
        with st.container():
            st.info(
                "💭 **进一步思考**（试着在心里回答，不必填写）：\n\n" +
                "\n".join(f"- {q}" for q in reflection)
            )

    # 持久化
    feasibility = {
        "falsifiable": falsi_result,
        "measurable": measure_result,
        "operability": op_result.as_dict(),
    }
    upstream["feasibility_results"] = feasibility
    update_stage_data(upstream, 4, output={
        **(get_stage_data(upstream, 4).get("output") or {}),
        "falsifiable_raw": falsi_answer,
        "all_measurable": measure_result.get("all_measurable", False),
        "is_feasible": op_result.is_feasible,
    })

    # 推进
    cols = st.columns([1, 1, 2])
    if cols[0].button("⬅️ 上一阶段", key="_funnel_stage4_back"):
        go_to_stage(st.session_state, 3)
        st.rerun()
    if cols[1].button("➡️ 下一阶段", key="_funnel_stage4_next", type="primary"):
        update_stage_data(upstream, 4, completed=True)
        advance_stage(st.session_state)
        st.rerun()


# ---------------------------------------------------------------------------
# 阶段 5：问题陈述
# ---------------------------------------------------------------------------

def _render_stage_5(upstream: Dict[str, Any]) -> None:
    stage = get_stage(5)
    st.markdown(f"### 阶段 5：{stage.name}")
    st.caption(stage.description)

    cv = upstream.get("candidate_vars") or {}
    default_pop = "大学生"
    default_iv = ", ".join(cv.get("independent_vars", []) or ["[X]"])
    default_dv = ", ".join(cv.get("dependent_vars", []) or ["[Y]"])
    template = f"在 {default_pop} 中，{default_iv} 是否影响 {default_dv}？"

    rq = st.text_area(
        "最终研究问题（标准句式：「在[人群]中，[X] 是否影响 [Y]？」）",
        value=upstream.get("research_question") or template,
        height=80,
        max_chars=300,
        key="_funnel_stage5_rq",
    )

    # 可选：调 AI 反问做最后一次审视
    if st.button("💬 让 AI 看看这个问题", key="_funnel_stage5_ask"):
        history: List[ChatMessage] = []
        from src.utils.llm_timer import llm_status
        with llm_status("AI 正在审视"):
            reply = ask_socratic(
                stage=5,
                user_input=rq,
                history=history,
                llm_config=_get_llm_config(),
            )
        st.info(f"💬 AI: {reply}")

    cols = st.columns([1, 1, 1, 2])
    if cols[0].button("⬅️ 上一阶段", key="_funnel_stage5_back"):
        go_to_stage(st.session_state, 4)
        st.rerun()
    if cols[1].button("✅ 直接进入 wizard", key="_funnel_stage5_done", type="primary"):
        if not rq.strip():
            st.warning("请先填写研究问题")
        else:
            upstream["research_question"] = rq.strip()
            payload = complete_funnel(st.session_state)
            st.success(f"已完成。研究问题、候选变量已写入 wizard。")
            st.rerun()
    # v3.4 文献综述工作台跳转（可选）
    if cols[2].button("📚 进入文献综述工作台", key="_funnel_stage5_review"):
        if not rq.strip():
            st.warning("请先填写研究问题")
        else:
            upstream["research_question"] = rq.strip()
            # 不调 complete_funnel（不切到 wizard），改切到 literature_review
            upstream["phase"] = "literature_review"
            from src.utils.workspace import update_last_position
            update_last_position("literature_review", session_state=st.session_state)
            try:
                from src.utils.autosave import trigger_autosave
                from src.utils.workspace import build_workspace_snapshot
                trigger_autosave(st.session_state, build_workspace_snapshot, force=True)
            except Exception:
                pass
            st.rerun()


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _render_history(history: List[Any]) -> None:
    if not history:
        return
    with st.expander(f"💬 对话历史（{len(history)} 条）", expanded=True):
        for msg in history:
            role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else "")
            content = getattr(msg, "content", "") or (msg.get("content") if isinstance(msg, dict) else "")
            avatar = "👤" if role == "user" else "🤖"
            st.markdown(f"{avatar} **{role}**：{content}")


def _get_llm_config() -> Optional[Dict[str, Any]]:
    """v4.6 单轨化：从顶部「🤖 AI 模型」激活的预设读。未激活返回 None。"""
    from src.llm_gateway.active_config import get_active_llm_config
    cfg = get_active_llm_config()
    if cfg is None:
        return None
    out = dict(cfg)
    out.setdefault("timeout", 30)
    return out


def _render_branch_history_panel() -> None:
    """v3.3 漏斗历史分支：列出归档分支，提供查看/切换/删除。"""
    history = get_funnel_history(st.session_state)
    if not history:
        return    # 无分支时不显示，避免视觉冗余

    with st.expander(f"📚 选题历史（{len(history)} 个归档分支）", expanded=False):
        for i, b in enumerate(history):
            bid = b.get("branch_id", "?")
            created = b.get("created_at", "")
            rq = b.get("final_research_q", "") or "（未确定研究问题）"
            st.markdown(
                f"**分支 {i + 1}** · {created} · `{bid}`\n\n"
                f"> {rq[:120]}"
            )
            cols = st.columns([1, 1, 1, 4])
            if cols[0].button("🔍 查看", key=f"_branch_view_{bid}"):
                st.session_state[f"_branch_view_open_{bid}"] = True
            if cols[1].button("♻️ 切换", key=f"_branch_switch_{bid}"):
                if switch_to_branch(st.session_state, bid):
                    st.success(f"已切换到分支 {bid}")
                    st.rerun()
                else:
                    st.error("切换失败：分支不存在")
            # v5.9: 删除改为两步确认（误触即永久丢失选题历史，不可恢复）
            if st.session_state.get(f"_branch_delete_confirm_{bid}"):
                _c1, _c2 = st.columns([1, 1])
                if _c1.button("⚠️ 确认删除", key=f"_branch_delete_yes_{bid}", type="primary"):
                    st.session_state.pop(f"_branch_delete_confirm_{bid}", None)
                    if delete_branch(st.session_state, bid):
                        st.success("已删除")
                    else:
                        st.error("删除失败：分支不存在")
                    st.rerun()
                if _c2.button("取消", key=f"_branch_delete_no_{bid}"):
                    st.session_state.pop(f"_branch_delete_confirm_{bid}", None)
                    st.rerun()
            elif cols[2].button("🗑️ 删除", key=f"_branch_delete_{bid}"):
                st.session_state[f"_branch_delete_confirm_{bid}"] = True
                st.rerun()

            # 详情弹窗
            if st.session_state.get(f"_branch_view_open_{bid}"):
                with st.container():
                    st.markdown("---")
                    st.markdown(f"### 分支详情 · `{bid}`")
                    stages = b.get("stages_snapshot") or {}
                    for sid in ("1", "2", "3", "4", "5"):
                        sdata = stages.get(sid) or {}
                        if not sdata:
                            continue
                        st.markdown(f"**阶段 {sid}**：{sdata.get('interest_text', '')[:200]}")
                    cv = b.get("candidate_vars") or {}
                    if cv:
                        st.caption(f"候选变量：DV={cv.get('dependent_vars')}，IV={cv.get('independent_vars')}")
                    if st.button("关闭详情", key=f"_branch_close_{bid}"):
                        st.session_state[f"_branch_view_open_{bid}"] = False
                        st.rerun()
            st.divider()


def _render_user_contract() -> None:
    """v3.3 用户契约：明确告知漏斗的"逼你想清楚"哲学，让用户主动选择是否进入。"""
    st.markdown(
        """<div class="psy-hero psy-hero--warning">
        <span class="psy-hero__eyebrow">开始前请确认</span>
        <h2>🎓 选题漏斗不是 AI 替你选题</h2>
        <p class="psy-hero__lead">
            系统会向你提出 <strong>5 轮反问</strong>，帮你把模糊的兴趣转化为可研究的问题。<br>
            预计耗时 <strong>30-60 分钟</strong>（取决于思考速度）。
        </p>
        <p class="psy-hero__meta">
            ⚠️ 如果你只想<strong>快速拿到一个题目</strong>，请选择 ADVANCED 模式跳过漏斗。<br>
            ✅ 如果你愿意花时间想清楚，本工具能帮你避免后续大量返工。
        </p>
        </div>""",
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 1, 2])
    if cols[0].button(
        "✅ 我准备好了，开始漏斗",
        key="_funnel_intro_accept",
        type="primary",
        width="stretch",
    ):
        st.session_state["funnel_intro_shown"] = True
        st.rerun()
    if cols[1].button(
        "⏭️ 我想跳过，切换到 ADVANCED",
        key="_funnel_intro_skip",
        width="stretch",
    ):
        set_active_tier(st.session_state, ResearchTier.ADVANCED)
        st.session_state["funnel_intro_shown"] = True
        st.rerun()


# 静态高质量反问示例（不调用 LLM，纯文本）
_QUALITY_PREVIEW_DIALOG = [
    ("学生", "我想研究焦虑。"),
    ("AI", "是哪种人的焦虑让你最在意——大学生？老人？还是产后？"),
    ("学生", "大学生考试前的焦虑。"),
    ("AI", "你想分清「考前几天的紧张」和「考试当下的躯体反应」吗？这两件事在数据上不一样。"),
    ("学生", "我觉得是考前几天的那种持续担心。"),
    ("AI", "如果数据显示「担心 ≠ 成绩差」，你的研究问题还能成立吗？换个角度看会怎样？"),
]


def _render_quality_preview() -> None:
    """v3.3 LLM 质量预检：展示静态高质量反问对话片段，用户对照判断 LLM 表现。"""
    if st.session_state.get("_quality_preview_dismissed"):
        return
    with st.expander("📺 反问示例（高质量参考）", expanded=True):
        st.caption(
            "下面是高质量苏格拉底反问的样子。"
            "如果你的 AI 反问质量明显不如这个示例，可能是 LLM 模型能力不足，"
            "建议在侧边栏切换更强的模型（DeepSeek-V3 / GPT-4o / Claude 等）。"
        )
        for role, content in _QUALITY_PREVIEW_DIALOG:
            avatar = "👤" if role == "学生" else "🤖"
            st.markdown(f"{avatar} **{role}**：{content}")
        if st.button("我已了解，关闭示例", key="_quality_preview_close"):
            st.session_state["_quality_preview_dismissed"] = True
            st.rerun()


def _is_first_funnel_visit(upstream: Dict[str, Any]) -> bool:
    """无任何阶段对话历史 → 视为首次访问。"""
    stages = upstream.get("stages") or {}
    for sid in stages.values():
        if isinstance(sid, dict) and (sid.get("ai_history") or sid.get("interest_text")):
            return False
    return True


def warn_if_low_quality_reply(reply: str) -> Optional[str]:
    """v3.3 LLM 反问质量软警告。

    触发条件（任一）：
    - 反问字数 < 30
    - 不含启发词「具体/为什么/如果/什么/哪/怎样」之一

    Returns: 警告文案，无问题返回 None。
    """
    if not reply or not isinstance(reply, str):
        return None
    if len(reply) < 30:
        return ("⚠️ 当前 LLM 反问偏短（<30 字），可能模型能力不足。"
                "建议在侧边栏切换更强的模型。")
    keywords = ["具体", "为什么", "如果", "什么", "哪", "怎样", "怎么"]
    if not any(k in reply for k in keywords):
        return ("⚠️ 当前 LLM 反问未含启发词（具体/为什么/如果/什么/哪/怎样），"
                "可能仅在重复表述，建议在侧边栏切换更强的模型。")
    return None


def _render_llm_required_card() -> None:
    st.warning(
        "**上游漏斗需要配置 LLM**：AI 苏格拉底反问是这一阶段的核心，没有它就只是表单。"
        "请到侧边栏设置 LLM API Key（DeepSeek / OpenAI / Zhipu / Ollama 都行）。"
    )
    with st.expander("💡 为什么强制要 LLM？", expanded=False):
        st.markdown(
            """
- 下游分析（清洗/计算/写论文）有规则，没 LLM 也能跑
- 上游选题没标准答案，**反问质量决定一切**
- 模板化反问意义不大——不如先配好 LLM 再来
"""
        )
