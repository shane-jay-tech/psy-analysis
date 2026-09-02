"""本科论文向导 UI — 从 app.py 拆分出的 7 步引导式界面"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd

from config.settings import get_test_name, VAR_ROLE_LABELS
from src.data.loader import load_data, validate_data
from src.data.inspector import inspect_dataframe
from src.parser.intent_resolver import resolve as resolve_intent
from src.analysis.runner import run_analysis
from src.output.formatter import format_result_summary
from src.output.interpretation import generate_interpretation
from src.ui.renderers import (
    render_assumption, render_result_table, render_charts,
    render_routing_banner, render_post_hoc_power,
    export_html, export_csv,
)
from src.data.demo_datasets import (
    generate_demo_questionnaire_data,
    generate_demo_experiment_data,
    generate_demo_repeated_measures_data,
    generate_demo_multi_group_data,
    generate_demo_mediation_data,
)
from src.data.demo_datasets_hr import (
    generate_demo_engagement_data,
    generate_demo_performance_data,
    generate_demo_turnover_data,
    generate_demo_360_review_data,
    list_hr_datasets,
)
from src.output.docx_exporter import (
    FigureItem, ThesisMeta, build_thesis_docx, build_thesis_with_custom_cover,
)
from src.visualization.paper_export import (
    KaleidoMissingError, export_all_figures_zip, to_paper_png,
)
from src.paper_writer.defense_qa import (
    HandbookMeta, apply_mastered_state, calculate_mastery_progress,
    export_defense_handbook_pdf, generate_defense_qa,
    generate_paper_aware_qa,
    group_qa_by_difficulty, render_qa_as_markdown,
)
from src.ui.cleaning_wizard import (
    cleaning_log_to_method_paragraph, render_cleaning_wizard,
)
from src.ui.export_gate import run_export_gate


def _render_official_download(
    label: str,
    *,
    artifact_state_keys: tuple[str, ...] = (),
    **kwargs,
) -> bool:
    """正式论文/图表交付出口：门禁失败时清除产物且不渲染按钮。"""
    allowed, gate_reasons, _ = run_export_gate(st.session_state)
    if not allowed:
        for state_key in artifact_state_keys:
            st.session_state.pop(state_key, None)
        st.error("导出被阻止：" + "; ".join(gate_reasons[:2]))
        return False
    st.download_button(label, **kwargs)
    return True


def _render_status_badges():
    """v2.9: 顶部进度条下显示全局状态徽章。"""
    from src.utils.figure_collection import get_collection_from_session
    from src.paper_writer.defense_qa import calculate_mastery_progress

    coll = get_collection_from_session(st.session_state)
    n_figs = len(coll)

    qa_items = st.session_state.get("_defense_qa_items", [])
    if qa_items:
        progress = calculate_mastery_progress(qa_items)
        n_mastered = sum(p["mastered"] for p in progress.values())
        n_total_qa = sum(p["total"] for p in progress.values())
        qa_badge = f"🎤 答辩 {n_mastered}/{n_total_qa}"
    else:
        qa_badge = "🎤 答辩 未生成"

    history = st.session_state.get("analysis_history", [])
    n_analyses = len(history)

    # 上次工作区保存
    saved_at = st.session_state.get("_workspace_last_saved", "")
    saved_text = f"💾 上次保存：{saved_at}" if saved_at else "💾 未保存"

    cols = st.columns(4)
    cols[0].metric("📊 已运行分析", f"{n_analyses}")
    cols[1].metric("📌 收藏图表", f"{n_figs}")
    cols[2].metric("🎤 答辩掌握", qa_badge.replace("🎤 答辩 ", ""))
    cols[3].caption(saved_text)


def _collect_literature_gaps() -> list:
    """v3.7: 从 workspace literature_review_state 收集已识别的 GapAnalysis。

    Returns:
        List[dict]，每项含 gap_description；workspace 不存在时返回空列表。
    """
    try:
        from src.utils.workspace import get_literature_review_state
        lr_state = get_literature_review_state() or {}
        gaps = lr_state.get("gap_analysis") or []
        # 兼容 dict / dataclass：UI 层只关心 description
        result = []
        for g in gaps:
            if isinstance(g, dict):
                if g.get("gap_description"):
                    result.append(g)
            else:
                desc = getattr(g, "gap_description", "")
                if desc:
                    result.append({"gap_description": desc})
        return result
    except Exception:
        return []


def _render_reviewer_mode(default_draft: str, ctx: dict) -> None:
    """v3.6 反问式审阅 UI（哲学统一核心）。

    流程：
    1. 用户粘贴自己写的初稿
    2. 选择章节类型（方法 / 结果 / 讨论）
    3. 点「生成追问」 → AI 返回 3-5 条反问
    4. 用户在追问下方填写回答
    5. 可选「📝 根据建议生成修订版」
    """
    from src.paper_writer.paper_engine import (
        generate_reviewer_questions,
        generate_revised_with_questions,
    )

    st.caption(
        "💡 在下方粘贴你自己写的方法/结果段落，AI 会以追问的方式指出可改进之处，"
        "**而不是替你改写**。先想清楚再让 AI 检查，比让 AI 直接生成更扎实。"
    )

    section_options = {
        "methods": "方法（Methods）",
        "results": "结果（Results）",
        "discussion": "讨论（Discussion）",
        "introduction": "引言（Introduction）",
    }
    sec = st.selectbox(
        "审阅哪个章节？",
        options=list(section_options.keys()),
        format_func=lambda s: section_options[s],
        key="_reviewer_section",
    )

    # 学生粘贴自己的初稿
    student_text = st.text_area(
        "📝 你写的初稿（粘贴到这里）",
        value=st.session_state.get("_reviewer_student_text", ""),
        height=180,
        key="_reviewer_student_text",
        placeholder="例：本研究采用独立样本 t 检验比较实验组和对照组的焦虑水平……",
        help="先自己写一稿，再让 AI 审阅。如果不知道从哪开始，可参考上方草稿。",
    )

    # 提示：可复制系统草稿到这里
    if not student_text.strip():
        if st.button("📥 把系统草稿复制到上方", key="_reviewer_copy_draft",
                      help="复制系统生成的草稿作为起点，再修改成你自己的版本"):
            st.session_state["_reviewer_student_text"] = default_draft
            st.rerun()

    col_a, col_b = st.columns([1, 1])
    with col_a:
        gen_btn = st.button(
            "🔍 生成追问",
            type="primary",
            disabled=not student_text.strip() or len(student_text.strip()) < 20,
            key="_reviewer_gen_btn",
        )
    with col_b:
        if st.session_state.get("_reviewer_questions"):
            if st.button("🗑 清空追问", key="_reviewer_clear"):
                st.session_state.pop("_reviewer_questions", None)
                st.session_state.pop("_reviewer_method", None)
                st.session_state.pop("_reviewer_qa", None)
                st.rerun()

    if gen_btn:
        from src.utils.llm_timer import llm_status
        with llm_status("AI 正在审阅"):
            try:
                from src.llm_gateway.gateway import _resolve_llm_config
                cfg = _resolve_llm_config()
                # v3.7: 注入文献综述阶段已识别的 gap，避免审阅重复追问
                gap_list = _collect_literature_gaps()
                result = generate_reviewer_questions(
                    student_text, section=sec, llm_config=cfg,
                    gap_analysis=gap_list,
                )
                st.session_state["_reviewer_questions"] = result["questions"]
                st.session_state["_reviewer_method"] = result["method"]
                st.session_state["_reviewer_gap_used"] = result.get("gap_context_used", False)
                st.session_state["_reviewer_qa"] = {}
            except Exception as exc:
                st.error(f"审阅失败：{exc}")
        st.rerun()

    # 显示追问 + 回答输入
    questions = st.session_state.get("_reviewer_questions") or []
    method = st.session_state.get("_reviewer_method", "")
    if questions:
        method_label = {"llm": "🤖 LLM 深度审阅", "rule": "📐 规则模板（无 LLM 时降级）"}.get(method, method)
        gap_badge = " · 📚 已读 gap" if st.session_state.get("_reviewer_gap_used") else ""
        st.markdown(f"**{method_label}**{gap_badge} · 共 {len(questions)} 条追问")

        if "_reviewer_qa" not in st.session_state:
            st.session_state["_reviewer_qa"] = {}

        for i, q in enumerate(questions):
            st.markdown(f"**追问 {i + 1}**: {q}")
            ans = st.text_area(
                f"你的回答（追问 {i + 1}）",
                value=st.session_state["_reviewer_qa"].get(str(i), ""),
                key=f"_reviewer_a_{i}",
                height=68,
                label_visibility="collapsed",
                placeholder="不需要全部回答，针对你认为关键的追问回答即可。",
            )
            st.session_state["_reviewer_qa"][str(i)] = ans

        # 可选：生成修订版
        st.markdown("---")
        with st.expander("📝 根据追问 + 你的回答生成修订版（可选）", expanded=False):
            st.caption(
                "勾选确认后调用 LLM 整合你的回答到原文，**生成修订版仅供参考**——"
                "你仍是论文作者，应自行判断是否采纳。"
            )
            confirm = st.checkbox(
                "我已理解：修订版仅供参考，最终版需自行审定",
                key="_reviewer_confirm_revise",
            )
            if confirm and st.button("生成修订版", key="_reviewer_do_revise"):
                qa_pairs = [
                    {"question": questions[int(k)], "answer": v}
                    for k, v in st.session_state["_reviewer_qa"].items()
                    if v.strip()
                ]
                if not qa_pairs:
                    st.warning("请至少回答一条追问后再生成修订版")
                else:
                    # v3.7 N1: 流式生成（最后一次 yield 是 dict 结果）
                    try:
                        from src.llm_gateway.gateway import _resolve_llm_config
                        from src.paper_writer.paper_engine import (
                            generate_revised_with_questions_stream,
                        )
                        cfg = _resolve_llm_config()
                        st.markdown("**修订版（实时生成中…）**")
                        placeholder = st.empty()
                        accum = []
                        final_text = ""
                        for chunk in generate_revised_with_questions_stream(
                            student_text, qa_pairs, section=sec, llm_config=cfg,
                        ):
                            if isinstance(chunk, dict):
                                final_text = chunk.get("revised_text", "")
                                break
                            accum.append(str(chunk))
                            placeholder.markdown("".join(accum))
                        st.session_state["_reviewer_revised"] = (
                            final_text or "".join(accum)
                        )
                    except Exception as exc:
                        st.error(f"生成失败：{exc}")
                    st.rerun()

            if st.session_state.get("_reviewer_revised"):
                st.markdown("**修订版预览**")
                st.text_area(
                    "修订版（可复制使用，但请自行审阅）",
                    value=st.session_state["_reviewer_revised"],
                    height=200,
                    key="_reviewer_revised_view",
                )


def _render_unfinished_reminders():
    """v2.9: 第 7 步顶部「未完成事项」智能提醒卡片。"""
    from src.utils.figure_collection import get_collection_from_session
    from src.paper_writer.defense_qa import calculate_mastery_progress

    reminders = []

    history = st.session_state.get("analysis_history", [])
    output = st.session_state.undergrad_wizard_data.get("analysis_output") if (
        isinstance(st.session_state.get("undergrad_wizard_data"), dict)
    ) else None
    if not history and output is None:
        reminders.append(("⚠️", "你还没有运行分析，无法生成论文。请回到第 5 步运行分析。"))

    coll = get_collection_from_session(st.session_state)
    if len(coll) < 3:
        reminders.append((
            "💡",
            f"建议至少收藏 3 张论文图表（当前 {len(coll)} 张）。"
            "回到第 5 步对每张图点「📌 加入论文图表集」。"
        ))

    qa_items = st.session_state.get("_defense_qa_items", [])
    if not qa_items:
        reminders.append(("💡", "别忘了生成答辩问题预演（在下方「🎤 答辩问题预演」中点「生成」）。"))
    else:
        progress = calculate_mastery_progress(qa_items)
        must_n = progress["必问"]["total"]
        must_m = progress["必问"]["mastered"]
        if must_n > 0 and must_m / must_n < 0.5:
            reminders.append((
                "⚠️",
                f"必问题掌握率偏低（{must_m}/{must_n}），建议先复习必问题再去答辩。",
            ))

    if not reminders:
        return

    parts = ["**📝 未完成事项提醒**\n"]
    for icon, text in reminders:
        parts.append(f"- {icon} {text}")
    st.warning("\n".join(parts))


def _render_delivery_package_top_card():
    """v2.9: 第 7 步顶部「一键打包论文交付包」卡片。"""
    from src.output.delivery_package import DeliverySpec, build_delivery_package
    from src.utils.figure_collection import get_collection_from_session

    st.markdown(
        """
<div class="info-box">
<strong>🎁 一键打包论文交付包</strong><br>
<span class="psy-panel-copy">
把已生成的论文初稿（Word）+ 答辩备战手册（PDF）+ 论文图表集打包为一个 ZIP，
一次下载齐全交付物，避免遗漏。
</span>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.expander("🎁 配置并下载交付包", expanded=False):
        coll = get_collection_from_session(st.session_state)
        items_qa = st.session_state.get("_defense_qa_items", [])
        n_unmastered = sum(1 for it in items_qa if not it.mastered) if items_qa else 0

        cols = st.columns(2)
        author = cols[0].text_input("作者姓名", value="", key="delivery_author")
        title = cols[1].text_input(
            "研究主题",
            value=st.session_state.get("docx_title", "本科毕业论文"),
            key="delivery_title",
        )

        include_thesis = st.checkbox(
            "📄 包含论文初稿（Word）",
            value=bool(st.session_state.get("_docx_bytes")),
            key="delivery_include_thesis",
            disabled=not st.session_state.get("_docx_bytes"),
            help="需先在下方「下载 Word 论文初稿」expander 中生成 Word",
        )
        include_handbook = st.checkbox(
            "📘 包含答辩备战手册（PDF）",
            value=bool(st.session_state.get("_handbook_pdf")),
            key="delivery_include_handbook",
            disabled=not st.session_state.get("_handbook_pdf"),
            help="需先在「答辩问题预演」中生成 PDF",
        )
        include_figs = st.checkbox(
            f"📁 包含论文图表集（已收藏 {len(coll)} 张）",
            value=len(coll) > 0,
            key="delivery_include_figs",
            disabled=len(coll) == 0,
        )

        palette = st.radio(
            "图表配色",
            options=["grayscale", "color", "mono"],
            format_func=lambda p: {
                "grayscale": "灰度（论文）",
                "color": "彩色（电子稿）",
                "mono": "纯黑（复印）",
            }[p],
            horizontal=True,
            key="delivery_palette",
        )

        notes = st.text_area(
            "README 备注（可选）", height=70,
            placeholder="例：本论文已通过预答辩，2026-06 提交终审版",
            key="delivery_notes",
        )

        if st.button("🎁 生成论文交付包 ZIP", type="primary",
                     width="stretch", key="delivery_gen"):
            with st.spinner("正在打包交付物..."):
                figures = []
                if include_figs:
                    for e in coll.list_all():
                        if e.fig_object is not None:
                            figures.append({
                                "fig": e.fig_object,
                                "test_name_zh": e.test_type,
                                "chart_type": e.chart_type or "图表",
                                "variables": e.variables,
                            })

                spec = DeliverySpec(
                    thesis_docx=(
                        st.session_state.get("_docx_bytes") if include_thesis else None
                    ),
                    thesis_filename=st.session_state.get(
                        "_docx_filename", "论文初稿.docx"
                    ),
                    handbook_pdf=(
                        st.session_state.get("_handbook_pdf") if include_handbook else None
                    ),
                    handbook_filename=st.session_state.get(
                        "_handbook_filename", "答辩备战手册.pdf"
                    ),
                    handbook_is_focused="重点" in st.session_state.get(
                        "_handbook_filename", ""
                    ),
                    figures=figures,
                    figure_palette=palette,
                    research_title=title or "本科毕业论文",
                    author=author,
                    extra_notes=notes,
                )
                try:
                    zip_bytes = build_delivery_package(spec)
                    st.session_state["_delivery_zip"] = zip_bytes
                    from src.utils.export_naming import export_filename
                    st.session_state["_delivery_filename"] = export_filename(
                        "论文交付包", "zip", title=title
                    )
                except Exception as e:
                    st.error(f"打包失败：{e}")

        if st.session_state.get("_delivery_zip"):
            _render_official_download(
                "⬇ 下载论文交付包 ZIP",
                artifact_state_keys=("_delivery_zip", "_delivery_filename"),
                data=st.session_state["_delivery_zip"],
                file_name=st.session_state.get("_delivery_filename", "论文交付包.zip"),
                mime="application/zip",
                key="delivery_dl",
                width="stretch",
                on_click=lambda: _record_download(
                    "ZIP", st.session_state.get("_delivery_filename", "论文交付包.zip")
                ),
            )
            st.caption(
                "💡 ZIP 内含 README.txt 列出所有文件 + 使用说明。"
            )


def _render_download_history():
    """v2.9: 下载历史记录折叠面板。"""
    history = st.session_state.get("download_history", [])
    if not history:
        return
    with st.expander(
        f"📥 已下载文件历史（最近 {min(len(history), 10)} 条）",
        expanded=False,
    ):
        for record in reversed(history[-10:]):
            st.caption(
                f"• {record.get('ts', '—')} · {record.get('type', '?')} · "
                f"{record.get('filename', '未命名')}"
            )
        if st.button("🗑 清空下载历史", key="dl_history_clear"):
            st.session_state["download_history"] = []
            st.rerun()


def _render_ai_tutor(output: dict, ctx: dict, *, location: str = "step7"):
    """v3.0: AI 助教对话面板，向导第 6/7 步均可调用。"""
    from src.paper_writer.ai_tutor import (
        ChatMessage, TutorAPIError, build_tutor_messages,
        build_tutor_system_prompt, chat_with_tutor,
        context_from_analysis, get_suggested_questions,
    )

    from src.llm_gateway.active_config import get_active_llm_config as _gac_tutor
    _tutor_cfg = _gac_tutor()
    has_llm = _tutor_cfg is not None

    expander_label = (
        "💬 问 AI 助教（针对你的研究多轮对话）"
        if has_llm
        else "💬 问 AI 助教（需先配置 LLM）"
    )

    with st.expander(expander_label, expanded=False):
        if not has_llm:
            st.info(
                "💡 在侧栏顶部「🤖 AI 模型」选一个预设后，可与 AI 助教多轮对话讨论你的研究。\n\n"
                r"如下拉框里所有项都标了「⚠️未配置」，请按 `D:\code\.env.local.example` 模板填 "
                r"`D:\code\.env.local`。\n\n"
                "AI 助教会读取你当前的统计方法、样本量、效应量、p 值，答得到点子上。"
            )
            return

        st.caption(
            "AI 助教已读取你的研究上下文（方法、n、效应量、p 值），"
            "你可以问任何与研究相关的问题。"
        )

        history_key = f"_tutor_history_{location}"
        history: list = st.session_state.setdefault(history_key, [])

        # 推荐问题（仅历史为空时显示）
        if not history:
            test_type = ctx.get("test_type", "")
            suggestions = get_suggested_questions(test_type)
            st.markdown("**💭 推荐问题（点击直接发送）：**")
            for i, q in enumerate(suggestions):
                if st.button(q, key=f"_tutor_suggest_{location}_{i}",
                             width="stretch"):
                    st.session_state[f"_tutor_pending_q_{location}"] = q
                    st.rerun()

        # 显示对话历史
        for msg in history:
            with st.chat_message("user" if msg.role == "user" else "assistant"):
                st.markdown(msg.content)

        # 处理待发送（来自推荐按钮）
        pending = st.session_state.pop(f"_tutor_pending_q_{location}", None)

        # 输入框
        user_input = st.chat_input(
            "输入你的问题（按 Enter 发送）...",
            key=f"_tutor_input_{location}",
        )

        new_msg = pending or user_input
        if new_msg:
            # 注入用户消息
            history.append(ChatMessage(role="user", content=new_msg))
            with st.chat_message("user"):
                st.markdown(new_msg)

            # 调用 LLM
            with st.chat_message("assistant"):
                from src.utils.llm_timer import llm_status
                with llm_status("AI 助教思考中"):
                    try:
                        tc = context_from_analysis(output, ctx)
                        sys_prompt = build_tutor_system_prompt(tc, has_result=output is not None)
                        msgs = build_tutor_messages(sys_prompt, history[:-1], new_msg)

                        provider = _tutor_cfg["provider"]
                        base_url = _tutor_cfg["base_url"]
                        model = _tutor_cfg["model"]
                        api_key = _tutor_cfg["api_key"]

                        # v3.7 N1: 流式输出（增强等待体验）
                        try:
                            from src.paper_writer.ai_tutor import chat_with_tutor_stream
                            stream_iter = chat_with_tutor_stream(
                                msgs,
                                provider=provider,
                                base_url=base_url,
                                api_key=api_key,
                                model=model,
                                temperature=0.5,
                                timeout=90,
                            )
                            answer = st.write_stream(stream_iter)
                        except Exception:
                            # 回退到一次性调用
                            answer = chat_with_tutor(
                                msgs,
                                provider=provider,
                                base_url=base_url,
                                api_key=api_key,
                                model=model,
                                temperature=0.5,
                                timeout=90,
                            )
                            st.markdown(answer)
                        history.append(ChatMessage(role="assistant", content=answer))
                    except TutorAPIError as e:
                        st.error(f"AI 助教调用失败：{e}")
                        history.pop()  # 移除空回复
                    except Exception as e:
                        st.error(f"调用异常：{e}")
                        history.pop()

        # 清空 / 导出 按钮（v3.1: 持久化后增加导出能力）
        if history:
            st.divider()
            cols = st.columns([1, 1, 3])
            if cols[0].button("🗑 清空对话", key=f"_tutor_clear_{location}"):
                st.session_state[history_key] = []
                st.rerun()

            # v3.1: 导出对话为 Markdown
            md_lines = [f"# AI 助教对话记录（{location}）", ""]
            for i, msg in enumerate(history, 1):
                role_label = "**👤 我**" if msg.role == "user" else "**🤖 AI 助教**"
                md_lines.append(f"## 第 {i} 条 — {role_label}")
                md_lines.append("")
                md_lines.append(msg.content)
                md_lines.append("")
            md_content = "\n".join(md_lines)

            from datetime import datetime as _dt
            cols[1].download_button(
                "📥 导出 MD",
                data=md_content,
                file_name=f"AI助教对话_{location}_{_dt.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                key=f"_tutor_export_{location}",
                width="stretch",
            )
            cols[2].caption(f"对话历史：{len(history)} 条（已自动保存到当前项目）")


def _render_collection_manager():
    """v2.9: 图表收藏夹管理 expander。"""
    from src.utils.figure_collection import get_collection_from_session
    from src.visualization.paper_export import export_all_figures_zip

    coll = get_collection_from_session(st.session_state)

    with st.expander(
        f"📚 论文图表集（已收藏 {len(coll)} 张，管理与批量导出）",
        expanded=False,
    ):
        if len(coll) == 0:
            st.info(
                "💡 你还没有收藏任何图表。"
                "回到第 5 步运行分析后，每张图下方点「📌 加入论文图表集」即可收藏。"
                "收藏的图表会跟随工作区保存，跨会话保留。"
            )
            return

        st.caption(
            "选中图表后可批量下载为 ZIP（与 v2.8 单次 ZIP 导出格式一致），"
            "或批量删除/编辑备注。"
        )

        # 全选/取消全选
        all_selected_key = "collection_all_selected"
        if all_selected_key not in st.session_state:
            st.session_state[all_selected_key] = False

        cols = st.columns([1, 1, 2])
        if cols[0].button("☑ 全选", key="coll_select_all"):
            st.session_state[all_selected_key] = True
            for e in coll.list_all():
                st.session_state[f"coll_sel_{e.figure_id}"] = True
            st.rerun()
        if cols[1].button("☐ 取消全选", key="coll_unselect_all"):
            st.session_state[all_selected_key] = False
            for e in coll.list_all():
                st.session_state[f"coll_sel_{e.figure_id}"] = False
            st.rerun()
        # v5.9: 收藏夹跨会话累积，误触清空不可恢复 → 两步确认
        if st.session_state.get("_coll_clear_confirm"):
            st.warning(f"⚠️ 将永久删除收藏夹中全部 {len(coll.list_all())} 张图表，不可恢复。")
            _k1, _k2 = st.columns(2)
            if _k1.button("⚠️ 确认清空", type="primary", key="coll_clear_yes"):
                coll.clear_all()
                st.session_state["_coll_clear_confirm"] = False
                st.rerun()
            if _k2.button("取消", key="coll_clear_no"):
                st.session_state["_coll_clear_confirm"] = False
                st.rerun()
        elif cols[2].button("🗑️ 清空整个收藏夹", key="coll_clear_all"):
            st.session_state["_coll_clear_confirm"] = True
            st.rerun()

        st.divider()

        # 列出每个收藏
        selected_ids = []
        for entry in coll.list_all():
            sel_key = f"coll_sel_{entry.figure_id}"
            cell_cols = st.columns([0.4, 5, 1])
            checked = cell_cols[0].checkbox(
                "选中", value=st.session_state.get(sel_key, False),
                key=sel_key, label_visibility="collapsed",
            )
            if checked:
                selected_ids.append(entry.figure_id)

            with cell_cols[1]:
                st.markdown(f"**{entry.title}**")
                st.caption(
                    f"{entry.test_type} · {entry.chart_type} · "
                    f"变量：{', '.join(str(v) for v in entry.variables) if entry.variables else '—'} · "
                    f"加入：{entry.created_at}"
                )
                if entry.note:
                    st.caption(f"📝 备注：{entry.note}")
                with st.expander("👁 预览图表 / 编辑", expanded=False):
                    if entry.fig_object is not None:
                        st.plotly_chart(
                            entry.fig_object, width="stretch",
                            config={"staticPlot": True},
                            key=f"coll_preview_{entry.figure_id}",
                        )
                    new_title = st.text_input(
                        "标题", value=entry.title,
                        key=f"coll_edit_title_{entry.figure_id}",
                    )
                    new_note = st.text_area(
                        "备注", value=entry.note,
                        key=f"coll_edit_note_{entry.figure_id}",
                        height=70,
                    )
                    if st.button("💾 保存修改", key=f"coll_save_edit_{entry.figure_id}"):
                        coll.update_title(entry.figure_id, new_title)
                        coll.update_note(entry.figure_id, new_note)
                        st.rerun()

            if cell_cols[2].button("🗑️", key=f"coll_del_{entry.figure_id}"):
                coll.remove(entry.figure_id)
                st.rerun()

            st.divider()

        # 批量操作
        if selected_ids:
            st.markdown(f"**已选中 {len(selected_ids)} 张图**")
            cols2 = st.columns(2)
            palette = cols2[0].selectbox(
                "ZIP 配色",
                options=["grayscale", "color", "mono"],
                format_func=lambda p: {
                    "grayscale": "灰度（论文）",
                    "color": "彩色（PPT）",
                    "mono": "纯黑（复印）",
                }[p],
                key="coll_zip_palette",
            )
            if cols2[1].button("📦 批量下载 ZIP", type="primary",
                              width="stretch", key="coll_zip"):
                specs = []
                for fid in selected_ids:
                    e = coll.get(fid)
                    if e and e.fig_object is not None:
                        specs.append({
                            "fig": e.fig_object,
                            "test_name_zh": e.test_type,
                            "chart_type": e.chart_type or "图表",
                            "variables": e.variables,
                            "timestamp": e.created_at,
                        })
                with st.spinner(f"正在打包 {len(specs)} 张图..."):
                    zip_bytes = export_all_figures_zip(
                        specs, palette=palette,
                        width_px=1500, height_px=1000,
                    )
                st.session_state["_collection_zip"] = zip_bytes
                st.session_state["_collection_zip_count"] = len(specs)

            if st.session_state.get("_collection_zip"):
                _render_official_download(
                    "⬇ 下载论文图表集 ZIP",
                    artifact_state_keys=("_collection_zip", "_collection_zip_count"),
                    data=st.session_state["_collection_zip"],
                    file_name="论文图表集.zip",
                    mime="application/zip",
                    key="coll_zip_dl",
                    width="stretch",
                )

            if st.button("🗑️ 删除选中", key="coll_batch_del"):
                for fid in selected_ids:
                    coll.remove(fid)
                st.rerun()


def _render_defense_handbook_download(items, ctx: dict):
    """v2.8 + v2.9: 答辩备战手册 PDF 下载控件，含完整版/精准版切换。"""
    with st.expander("📥 下载答辩备战手册（PDF）", expanded=False):
        st.caption(
            "包含问答分级、笔记区、考前 3 天复习计划的完整 PDF，"
            "建议打印后随身携带，答辩前 3 天开始翻阅练习。"
        )

        # v2.9: 完整版 / 精准版选择
        n_unmastered = sum(1 for it in items if not it.mastered)
        version_label = st.radio(
            "PDF 版本",
            options=["full", "focused"],
            format_func=lambda v: {
                "full": f"📋 完整版（所有 {len(items)} 题）",
                "focused": (
                    f"🎯 精准版（仅未掌握 {n_unmastered} 题）"
                    if n_unmastered > 0
                    else "🎯 精准版（你已全部掌握，无未掌握题）"
                ),
            }[v],
            horizontal=True,
            key="handbook_version",
        )

        cols = st.columns(2)
        author = cols[0].text_input(
            "作者姓名（PDF 标题页）", value="", key="handbook_author",
        )
        advisor = cols[1].text_input(
            "指导教师", value="", key="handbook_advisor",
        )
        title = st.text_input(
            "研究主题（标题页用）",
            value=ctx.get("test_name_zh", "本科毕业论文研究"),
            key="handbook_title",
        )
        if st.button("🖨 生成 PDF 手册", type="secondary",
                     width="stretch", key="handbook_gen"):
            try:
                meta = HandbookMeta(
                    research_title=title,
                    author=author,
                    advisor=advisor,
                )
                with st.spinner("正在排版 PDF..."):
                    pdf_bytes = export_defense_handbook_pdf(
                        items, meta,
                        filter_unmastered=(version_label == "focused"),
                    )
                st.session_state["_handbook_pdf"] = pdf_bytes
                version_suffix = "_重点版" if version_label == "focused" else ""
                from src.utils.export_naming import export_filename
                st.session_state["_handbook_filename"] = export_filename(
                    f"答辩备战手册{version_suffix}", "pdf", title=title
                )
            except Exception as e:
                st.error(f"PDF 生成失败：{e}")

        if st.session_state.get("_handbook_pdf"):
            st.download_button(
                "⬇ 下载答辩备战手册 PDF",
                data=st.session_state["_handbook_pdf"],
                file_name=st.session_state.get("_handbook_filename", "答辩备战手册.pdf"),
                mime="application/pdf",
                key="handbook_dl",
                width="stretch",
                on_click=lambda: _record_download(
                    "PDF", st.session_state.get("_handbook_filename", "答辩备战手册.pdf")
                ),
            )


def _record_download(file_type: str, filename: str):
    """v2.9: 把下载操作记入 session_state 历史。"""
    from datetime import datetime
    history = st.session_state.setdefault("download_history", [])
    history.append({
        "type": file_type,
        "filename": filename,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    # 上限 30 条
    if len(history) > 30:
        st.session_state["download_history"] = history[-30:]


def _generate_paper_aware_with_context(plan, output: dict, ctx: dict, max_items: int):
    """v3.9 O2: 收集论文 + 反问历史 + 漏斗状态，调 generate_paper_aware_qa。

    Returns:
        (qa_items, meta_dict) — meta 含 used_paper/used_reviewer/used_funnel/fallback/error。
    """
    from src.utils.workspace import get_upstream_state

    # 1) 论文文本：拼 method_md + result_md + 反问稿
    wiz_data = st.session_state.get("undergrad_wizard_data") or {}
    paper_parts = []
    if wiz_data.get("method_text"):
        paper_parts.append("## 方法\n" + str(wiz_data["method_text"]))
    if wiz_data.get("result_text"):
        paper_parts.append("## 结果\n" + str(wiz_data["result_text"]))
    if st.session_state.get("_reviewer_student_text"):
        paper_parts.append("## 学生稿\n" + str(st.session_state["_reviewer_student_text"]))
    if st.session_state.get("_reviewer_revised"):
        paper_parts.append("## 修订版\n" + str(st.session_state["_reviewer_revised"]))
    paper_text = "\n\n".join(paper_parts).strip()

    # 2) reviewer 历史：从 _reviewer_questions + _reviewer_qa
    reviewer_history = []
    questions = st.session_state.get("_reviewer_questions") or []
    qa_map = st.session_state.get("_reviewer_qa") or {}
    for i, q in enumerate(questions):
        ans = (qa_map.get(str(i)) or "").strip()
        if ans:
            reviewer_history.append({"question": q, "answer": ans})

    # 3) 漏斗决策
    upstream = get_upstream_state(st.session_state) or {}
    candidate_vars = upstream.get("candidate_vars") or {}
    funnel_state = {
        "research_question": upstream.get("research_question") or "",
        "variables": "、".join(filter(None, [
            "/".join(candidate_vars.get("dependent_vars") or []),
            "/".join(candidate_vars.get("independent_vars") or []),
        ])),
        "design": upstream.get("design") or "",
        "sample_size": upstream.get("sample_size") or "",
        "hypothesis": upstream.get("hypothesis") or "",
    }
    funnel_state = {k: v for k, v in funnel_state.items() if v}

    # 4) 调 paper-aware QA（llm_chat_fn 走默认 _resolve_llm_config）
    result = generate_paper_aware_qa(
        paper_text=paper_text,
        reviewer_history=reviewer_history or None,
        funnel_state=funnel_state or None,
        plan=plan,
        output=output,
        ctx=ctx,
        max_items=max_items,
    )
    meta = {
        "used_paper": result.used_paper,
        "used_reviewer_history": result.used_reviewer_history,
        "used_funnel": result.used_funnel,
        "fallback_to_template": result.fallback_to_template,
        "error": result.error,
    }
    return list(result.items), meta


def render_pii_warning(df) -> None:
    """v3.9 U5: 上传后检测 PII 列并提醒。

    高/中危列默认醒目展示并提供「一键脱敏」按钮（哈希替换原列）；低危列折叠。
    """
    from src.utils.guardrails import detect_pii_columns, hash_column

    pii = detect_pii_columns(df)
    if not pii.get("any"):
        return

    high_cols = pii.get("high", [])
    med_cols = pii.get("medium", [])
    low_cols = pii.get("low", [])

    if high_cols:
        st.error(
            "🚨 **高敏感信息预警**：检测到下列列疑似含个人身份信息——\n\n"
            + "、".join(f"`{c}`" for c in high_cols)
            + "\n\n**强烈建议**：在分析前直接删除这些列；勿在交付物/截图中留存。"
        )
    if med_cols:
        st.warning(
            "⚠️ **可识别身份信息**：下列列疑似含真实身份标识——\n\n"
            + "、".join(f"`{c}`" for c in med_cols)
            + "\n\n建议哈希脱敏（系统保存档案时会自动哈希），或在分析前替换为纯数字 ID。"
        )
        if st.button("🔐 一键脱敏（哈希这些列）", key="_pii_hash_all"):
            try:
                for col in med_cols:
                    df[col] = hash_column(df, col)
                st.success(f"✅ 已对 {len(med_cols)} 个列做哈希脱敏；后续分析将使用脱敏后值。")
                st.rerun()
            except Exception as exc:
                st.error(f"脱敏失败：{exc}")
    if low_cols:
        with st.expander(f"💡 弱标识列提醒（{len(low_cols)} 个，通常无害）", expanded=False):
            st.caption(
                "下列列可能是 ID/编号/被试编号——通常无害，但若是从教务系统等带出，"
                "建议在交付时替换为 P001/S01 形式的虚拟编号。"
            )
            st.write("、".join(f"`{c}`" for c in low_cols))


def _render_jspsych_pivot_panel(wiz) -> None:
    """v3.9 N9: jsPsych 长表 → 被试级宽表 UI 面板。

    展示在数据上传后；用户点「转为宽表」即把 ``wiz.df`` 替换为 pivot 后结果，
    便于后续配对 t / RM-ANOVA 直接选条件列做分析。
    """
    from src.data.loader import pivot_jspsych_to_wide

    df = wiz.df
    cols = list(df.columns)

    with st.expander("🔄 jsPsych 长表 → 被试级宽表（推荐用于配对 t / RM-ANOVA）", expanded=False):
        st.caption(
            "jsPsych 导出是试次级长表（每行一 trial）。要做配对 t/重复测量 ANOVA，"
            "需要把数据转成被试级宽表（每被试一行，每条件一列）。"
            "下方根据列名自动嗅探被试/条件/数值列，你可微调后点「转为宽表」。"
        )

        # 自动嗅探默认值
        def _guess(targets: list, default: str = "") -> str:
            for t in targets:
                if t in cols:
                    return t
            for t in targets:
                for c in cols:
                    if t in c or c in t:
                        return c
            return default or (cols[0] if cols else "")

        sub_default = _guess(["subject", "subj_id", "subject_id", "participant", "被试", "id"])
        cond_default = _guess(["condition", "trial_type", "条件", "stimulus_type"])
        val_default = _guess(["反应时_ms", "反应时", "rt", "RT", "response_time"])

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            sub_col = st.selectbox(
                "被试列",
                cols,
                index=cols.index(sub_default) if sub_default in cols else 0,
                key="_jspsych_pivot_sub",
            )
        with col_b:
            cond_col = st.selectbox(
                "条件列",
                cols,
                index=cols.index(cond_default) if cond_default in cols else 0,
                key="_jspsych_pivot_cond",
            )
        with col_c:
            val_col = st.selectbox(
                "数值列（聚合）",
                cols,
                index=cols.index(val_default) if val_default in cols else 0,
                key="_jspsych_pivot_val",
            )
        with col_d:
            agg = st.selectbox(
                "聚合方式",
                ["mean", "median"],
                index=0,
                key="_jspsych_pivot_agg",
            )

        if st.button("🔄 转为宽表", key="_jspsych_pivot_run", type="primary"):
            try:
                wide_df, pivot_meta = pivot_jspsych_to_wide(
                    df,
                    subject_col=sub_col,
                    condition_col=cond_col,
                    value_col=val_col,
                    agg=agg,
                )
                if wide_df.empty or wide_df.shape[1] <= 1:
                    st.error("❌ 转换结果为空。请检查列选择是否正确。")
                else:
                    # 保留原长表副本（_long_df），便于回退
                    if not hasattr(wiz, "_jspsych_long_df") or wiz._jspsych_long_df is None:
                        wiz._jspsych_long_df = wiz.df
                    wiz.df = wide_df
                    wiz.meta = {
                        **(wiz.meta or {}),
                        **pivot_meta,
                        "row_count": int(wide_df.shape[0]),
                        "col_count": int(wide_df.shape[1]),
                    }
                    wiz.inspector = inspect_dataframe(wide_df)
                    wiz.analysis_output = None
                    wiz.plan = None
                    st.success(
                        f"✅ 已转为宽表：{pivot_meta['n_subjects']} 名被试 × "
                        f"{pivot_meta['n_conditions']} 个条件（{agg}）。"
                    )
                    st.rerun()
            except ValueError as exc:
                st.error(f"❌ {exc}")
            except Exception as exc:
                st.error(f"❌ pivot 失败：{exc}")

        if hasattr(wiz, "_jspsych_long_df") and wiz._jspsych_long_df is not None:
            if st.button("↩️ 回退到长表", key="_jspsych_pivot_revert"):
                wiz.df = wiz._jspsych_long_df
                wiz._jspsych_long_df = None
                wiz.inspector = inspect_dataframe(wiz.df)
                wiz.meta = {
                    **(wiz.meta or {}),
                    "source_type": "jspsych_json",
                    "row_count": int(wiz.df.shape[0]),
                    "col_count": int(wiz.df.shape[1]),
                }
                wiz.analysis_output = None
                wiz.plan = None
                st.info("已回退到长表。")
                st.rerun()


def _render_ai_trace_check_section(default_draft: str = "") -> None:
    """v3.9 O3: 交稿前 AI 痕迹自检。

    规则层零成本检测中文学术写作里的 AI 八股（首先/其次、综上所述、
    值得深入探讨、本文研究表明...等 15 类），给出评分 + 必删/建议改 清单。
    """
    from src.output.ai_trace_detector import detect_ai_traces

    with st.expander("🪞 交稿前自检：AI 痕迹检测（推荐）", expanded=False):
        st.caption(
            "把你最终交稿的文本贴进来，规则层（无需 LLM、零成本）扫描"
            "「首先/其次/最后」「综上所述」「值得深入探讨」等 AI 高频套话。"
            "评分 0-100，越高越像 AI；老师一眼能看出的「必删」级别会单独标红。"
        )

        text_to_check = st.text_area(
            "贴入待检测文本",
            value=st.session_state.get("_ai_trace_input", default_draft or ""),
            height=180,
            key="_ai_trace_input",
            help="可粘贴方法+结果初稿、反问后的修订版、或最终成稿。",
        )

        col_a, col_b = st.columns([1, 3])
        with col_a:
            run_check = st.button("🔍 开始自检", key="_ai_trace_run", type="primary")
        with col_b:
            if st.button("🗑️ 清空", key="_ai_trace_clear"):
                st.session_state.pop("_ai_trace_report", None)
                st.session_state.pop("_ai_trace_input", None)
                st.rerun()

        if run_check:
            text = (text_to_check or "").strip()
            if not text:
                st.warning("请先贴入文本。")
            else:
                try:
                    report = detect_ai_traces(text)
                    st.session_state["_ai_trace_report"] = report
                except Exception as exc:
                    st.error(f"检测失败：{exc}")

        report = st.session_state.get("_ai_trace_report")
        if report is None:
            return

        score = float(getattr(report, "score", 0.0))
        if score >= 50:
            st.error(f"AI 痕迹评分：**{score:.1f} / 100** — 重度，老师高概率察觉，建议大改。")
        elif score >= 20:
            st.warning(f"AI 痕迹评分：**{score:.1f} / 100** — 中度，建议优化高优先级条目。")
        else:
            st.success(f"AI 痕迹评分：**{score:.1f} / 100** — 轻度，可放心提交。")

        sev_counts = getattr(report, "severity_counts", {}) or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总命中", len(getattr(report, "hits", []) or []))
        c2.metric("必删 (high)", sev_counts.get("high", 0))
        c3.metric("建议改 (med)", sev_counts.get("med", 0))
        c4.metric("提醒 (low)", sev_counts.get("low", 0))

        if report.has_high_severity:
            st.markdown("### 🚨 必删项（high）")
            for h in report.hits_by_severity("high"):
                st.markdown(
                    f"- **第 {h.line_no} 行** · 命中「{h.pattern_label}」：`{h.matched_text}`  \n"
                    f"  原因：{h.why}  \n"
                    f"  建议：{h.suggestion}"
                )

        med_hits = report.hits_by_severity("med")
        if med_hits:
            with st.expander(f"⚠️ 建议改 ({len(med_hits)} 条)", expanded=False):
                for h in med_hits:
                    st.markdown(
                        f"- **第 {h.line_no} 行** · 「{h.pattern_label}」：`{h.matched_text}`  \n"
                        f"  建议：{h.suggestion}"
                    )

        low_hits = report.hits_by_severity("low")
        if low_hits:
            with st.expander(f"💡 轻度提醒 ({len(low_hits)} 条)", expanded=False):
                for h in low_hits:
                    st.markdown(f"- 第 {h.line_no} 行 · 「{h.pattern_label}」：`{h.matched_text}`")


def _render_defense_qa_section(plan, output: dict, ctx: dict):
    """向导第 7 步：答辩问题模拟器（v3.9 加 paper-aware 个性化选项）。"""
    with st.expander("🎤 答辩问题预演（推荐展开）", expanded=False):
        st.caption(
            "系统根据你的分析方法，自动生成老师答辩时最可能问的问题。"
            "每个问题附带模板化的标准答案，建议在答辩前熟读并结合自己的研究背景修改。"
        )

        max_items = st.slider(
            "生成问题数量", min_value=3, max_value=10, value=7,
            key="defense_qa_max",
        )

        # v3.9 O2: 个性化生成开关
        from src.llm_gateway.active_config import is_llm_active as _is_llm_active
        has_llm = _is_llm_active()
        use_paper_aware = st.checkbox(
            "📝 个性化生成（读你的论文 + 反问历史 + 选题决策）",
            value=False,
            key="defense_qa_use_paper_aware",
            disabled=not has_llm,
            help=(
                "启用后调用 LLM 读你已经写的论文、AI 反问历史、漏斗选题决策，"
                "生成更针对你研究的答辩题（而非通用模板题）。"
                "需要在侧栏配置 LLM API key。LLM 不可用时自动降级到模板版。"
                if has_llm
                else "需在侧栏配置 LLM API key 后才可启用。"
            ),
        )

        if st.button("🎤 生成答辩问题", type="secondary", width="stretch",
                     key="defense_qa_gen"):
            with st.spinner("正在分析检验类型并生成针对性问题..."):
                # v3.9: paper-aware 路径 vs 模板路径
                if use_paper_aware and has_llm:
                    qa_items, _paper_aware_meta = _generate_paper_aware_with_context(
                        plan=plan, output=output, ctx=ctx, max_items=max_items,
                    )
                    st.session_state["_defense_qa_paper_aware_meta"] = _paper_aware_meta
                else:
                    qa_items = generate_defense_qa(
                        plan=plan, output=output, ctx=ctx, max_items=max_items,
                    )
                    st.session_state["_defense_qa_paper_aware_meta"] = None
                # v3.3: 若 ADVANCED 留痕，前置注入研究动机问答
                from src.paper_writer.defense_qa import QAItem
                from src.utils.workspace import get_upstream_state
                from src.upstream.topic_funnel import generate_motivation_qa_from_advanced
                _upstream = get_upstream_state(st.session_state)
                _adv_meta = _upstream.get("advanced_meta") or {}
                motivation_items = generate_motivation_qa_from_advanced(_adv_meta)
                if motivation_items:
                    motivation_qa = [
                        QAItem(
                            question=m["question"],
                            answer=m["answer_template"],
                            category=m["category"],
                            category_label=m["category"],
                            difficulty=m["difficulty"].split()[-1] if " " in m["difficulty"] else m["difficulty"],
                            difficulty_emoji=m["difficulty"].split()[0] if " " in m["difficulty"] else "🟢",
                        )
                        for m in motivation_items
                    ]
                    qa_items = motivation_qa + list(qa_items)
                # v2.9: 注入持久化的掌握状态
                mastered_map = st.session_state.get("defense_qa_mastered", {})
                qa_items = apply_mastered_state(qa_items, mastered_map)
                st.session_state["_defense_qa_items"] = qa_items

        items = st.session_state.get("_defense_qa_items", [])
        # v2.9: 每次渲染时也重新注入（解决 rerun 后状态丢失）
        if items:
            mastered_map = st.session_state.get("defense_qa_mastered", {})
            items = apply_mastered_state(items, mastered_map)
        if items:
            # v3.9 O2: paper-aware 元数据徽章
            _meta = st.session_state.get("_defense_qa_paper_aware_meta")
            if _meta:
                if _meta.get("fallback_to_template"):
                    st.warning(
                        f"⚠️ 个性化生成失败（{_meta.get('error', '未知错误')}），已降级到模板版。"
                    )
                else:
                    badges = []
                    if _meta.get("used_paper"):
                        badges.append("📝 已读论文")
                    if _meta.get("used_reviewer_history"):
                        badges.append("💬 已用反问历史")
                    if _meta.get("used_funnel"):
                        badges.append("🎯 已用选题决策")
                    if badges:
                        st.success("✨ 个性化生成已启用 · " + " · ".join(badges))

            st.divider()
            st.info(
                "**难度分级提示：**\n"
                "- 🟢 **必问**（务必准备）：导师答辩几乎一定会问的核心问题\n"
                "- 🟡 **常问**（建议准备）：常见追问，提前打草稿\n"
                "- 🔴 **刁钻**（视情况准备）：进阶质疑，应对资深评委"
            )
            st.markdown(f"**已生成 {len(items)} 个问题，按难度排序：**")

            # v2.9: 总览进度
            progress = calculate_mastery_progress(items)
            total_mastered = sum(p["mastered"] for p in progress.values())
            total_count = sum(p["total"] for p in progress.values())
            if total_count > 0:
                st.markdown(
                    f"**📊 掌握进度：{total_mastered}/{total_count} "
                    f"（{int(total_mastered/total_count*100)}%）**"
                )
                st.progress(total_mastered / total_count)

            # 按难度分组（必问 → 常问 → 刁钻）
            groups = group_qa_by_difficulty(items)
            counter = 0
            mastered_map = st.session_state.setdefault("defense_qa_mastered", {})
            for diff in ("必问", "常问", "刁钻"):
                diff_items = groups.get(diff, [])
                if not diff_items:
                    continue
                emoji = {"必问": "🟢", "常问": "🟡", "刁钻": "🔴"}[diff]
                # v2.9: 标题显示该难度组的掌握进度
                p = progress.get(diff, {"mastered": 0, "total": len(diff_items)})
                st.markdown(
                    f"#### {emoji} {diff}（{p['mastered']}/{p['total']} 已掌握）"
                )
                for item in diff_items:
                    counter += 1
                    with st.container():
                        cols_q = st.columns([10, 2])
                        cols_q[0].markdown(f"**Q{counter}：{item.question}**")
                        # v2.9: 掌握状态复选框
                        new_mastered = cols_q[1].checkbox(
                            "✅ 已掌握",
                            value=item.mastered,
                            key=f"qa_mastered_{item.question_id}",
                        )
                        if new_mastered != item.mastered:
                            item.mastered = new_mastered
                            mastered_map[item.question_id] = new_mastered
                        else:
                            mastered_map[item.question_id] = item.mastered
                        st.caption(f"{item.category_label} · {emoji} {diff}")
                        st.markdown(f"💬 **答**：{item.answer}")
                        st.markdown("")

            # 导出为 Markdown 供复制
            st.divider()
            md = render_qa_as_markdown(items)
            with st.expander("📋 复制全部问答（Markdown 格式）", expanded=False):
                st.code(md, language="markdown")

            # 答辩备战手册 PDF（v2.8）
            _render_defense_handbook_download(items=items, ctx=ctx)

            # 保存到 session_state 供 Word 导出附录使用
            st.session_state["_defense_qa_md"] = md
            st.success("✅ 已保存。下次导出 Word 时，可在「附录 A」中包含答辩问题。")


def _render_ai_paper_generation(output: dict, ctx: dict, wiz_data: dict):
    """v4.7: 通过 workflow_service 提供 AI 增强论文生成（可选）。"""
    from src.llm_gateway import is_llm_available

    if not is_llm_available():
        return

    with st.expander("🤖 AI 增强论文生成（可选）", expanded=False):
        st.caption(
            "使用 AI 基于你的分析结果和研究设计生成更完整的方法/结果段落。"
            "生成后可替换上方模板文本，也可仅作参考。"
        )
        if st.button("🚀 AI 生成增强版论文段落", key="_ai_paper_gen"):
            with st.spinner("AI 正在生成（可能需要 30-60 秒）..."):
                try:
                    from src.paper_writer.workflow_service import (
                        QuickPaperRequest,
                        generate_paper_quick,
                    )
                    req = QuickPaperRequest(
                        topic=wiz_data.get("title_hint", ""),
                        title_hint=wiz_data.get("title_hint", ""),
                        participants_desc=wiz_data.get("sample_desc", ""),
                        df=st.session_state.get("uploaded_df"),
                        analysis_results=output or {},
                    )
                    result = generate_paper_quick(req)
                    if result.sections:
                        ai_method = result.sections.get("methods", "")
                        ai_result = result.sections.get("results", "")
                        if ai_method:
                            st.session_state["_ai_method_md"] = ai_method
                        if ai_result:
                            st.session_state["_ai_result_md"] = ai_result
                        st.success("✅ AI 增强版已生成，下方 Word 导出将使用 AI 版本。")
                        if ai_method:
                            with st.expander("预览 AI 方法段", expanded=False):
                                st.markdown(ai_method)
                        if ai_result:
                            with st.expander("预览 AI 结果段", expanded=False):
                                st.markdown(ai_result)
                    else:
                        st.warning("AI 未生成有效内容，将继续使用模板版本。")
                except Exception as e:
                    st.error(f"AI 生成失败（将使用模板版本）：{e}")

        if st.session_state.get("_ai_method_md") or st.session_state.get("_ai_result_md"):
            if st.button("🔄 恢复使用模板版本", key="_ai_paper_reset"):
                st.session_state.pop("_ai_method_md", None)
                st.session_state.pop("_ai_result_md", None)
                st.rerun()


def _render_docx_download(method_md: str, result_md: str, output: dict,
                          ctx: dict, wiz_data: dict):
    """向导第 7 步：Word 一键导出控件。

    所有 UI 状态保持局部，避免污染向导主流程的 session_state。
    """
    with st.expander("📄 下载 Word 论文初稿（.docx）", expanded=True):
        st.caption("一键生成符合 APA7 格式的中文论文初稿，含描述统计表、方法、结果。")

        cols = st.columns(2)
        thesis_title = cols[0].text_input(
            "论文题目",
            value=wiz_data.get("title_hint", "心理学实证研究报告"),
            key="docx_title",
        )
        author_name = cols[1].text_input("作者姓名", value="", key="docx_author")

        cols2 = st.columns(2)
        affiliation = cols2[0].text_input("单位/院系", value="", key="docx_affil")
        thesis_date = cols2[1].text_input(
            "日期", value=pd.Timestamp.now().strftime("%Y 年 %m 月"),
            key="docx_date",
        )

        # v2.8: 自定义封面模板
        cover_template_file = st.file_uploader(
            "📎 上传学校封面模板（可选，.docx）",
            type=["docx"],
            key="docx_cover_template",
            help=(
                "上传学校提供的论文封面 docx 模板（含校徽/学院信息），"
                "系统会将正文内容拼接到模板后。如不上传，使用通用 APA7 封面。"
            ),
        )

        include_chart = st.checkbox(
            "嵌入论文版图表（PNG 300dpi）",
            value=True,
            key="docx_include_chart",
            help="使用与「下载论文版图表」完全一致的 300dpi 输出。需要 kaleido 包；缺失时自动跳过。",
        )
        include_qa = st.checkbox(
            "附加「答辩问题预演」附录",
            value=bool(st.session_state.get("_defense_qa_md")),
            key="docx_include_qa",
            help="需先在下方「🎤 答辩问题预演」中生成问题",
            disabled=not st.session_state.get("_defense_qa_md"),
        )
        chart_palette = st.radio(
            "图表配色",
            options=["grayscale", "color", "mono"],
            format_func=lambda p: {
                "grayscale": "灰度（论文/期刊）",
                "color": "彩色（电子稿）",
                "mono": "纯黑（复印）",
            }[p],
            horizontal=True,
            key="docx_palette",
            disabled=not include_chart,
        )

        if st.button("📄 生成 Word 初稿", type="primary", width="stretch",
                     key="docx_generate"):
            with st.spinner("正在生成 Word 文档..."):
                try:
                    figures = []
                    if include_chart:
                        figures = _build_paper_figures(
                            output, ctx, wiz_data, palette=chart_palette,
                        )

                    desc = output.get("descriptive") if output else None

                    meta = ThesisMeta(
                        title=thesis_title or "心理学实证研究报告",
                        author=author_name,
                        affiliation=affiliation,
                        date=thesis_date,
                    )

                    qa_md = (
                        st.session_state.get("_defense_qa_md", "")
                        if include_qa else ""
                    )

                    cover_template = st.session_state.get("docx_cover_template")
                    if cover_template is not None:
                        # v2.8: 用自定义封面模板
                        import tempfile
                        with tempfile.NamedTemporaryFile(
                            suffix=".docx", delete=False
                        ) as tmp:
                            tmp.write(cover_template.getvalue())
                            tmp_path = tmp.name
                        try:
                            docx_bytes = build_thesis_with_custom_cover(
                                cover_template_path=tmp_path,
                                meta=meta,
                                method_md=method_md,
                                result_md=result_md,
                                descriptive_table=desc if isinstance(desc, pd.DataFrame) else None,
                                figures=figures,
                                defense_qa_md=qa_md,
                            )
                            st.success("✅ 已使用你的封面模板生成论文。")
                        except ValueError as ve:
                            st.warning(f"⚠ 封面模板异常，已降级使用默认封面：{ve}")
                            docx_bytes = build_thesis_docx(
                                meta=meta,
                                method_md=method_md,
                                result_md=result_md,
                                descriptive_table=desc if isinstance(desc, pd.DataFrame) else None,
                                figures=figures,
                                defense_qa_md=qa_md,
                            )
                    else:
                        docx_bytes = build_thesis_docx(
                            meta=meta,
                            method_md=method_md,
                            result_md=result_md,
                            descriptive_table=desc if isinstance(desc, pd.DataFrame) else None,
                            figures=figures,
                            defense_qa_md=qa_md,
                        )
                    st.session_state["_docx_bytes"] = docx_bytes
                    from src.utils.export_naming import export_filename
                    st.session_state["_docx_filename"] = export_filename(
                        "论文初稿", "docx", title=thesis_title
                    )
                except Exception as e:
                    st.error(f"生成失败：{e}")

        if st.session_state.get("_docx_bytes"):
            _render_official_download(
                "⬇ 下载 Word 文档",
                artifact_state_keys=("_docx_bytes", "_docx_filename"),
                data=st.session_state["_docx_bytes"],
                file_name=st.session_state.get("_docx_filename", "论文初稿.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="docx_dl",
                width="stretch",
                on_click=lambda: _record_download(
                    "Word", st.session_state.get("_docx_filename", "论文初稿.docx")
                ),
            )
            st.caption("💡 已生成。请用 Word 2016+ 或 WPS 打开；中文字体使用宋体/黑体。")


def _build_figure_specs(output: dict, ctx: dict, wiz_data: dict) -> list:
    """v2.8: 生成图表 spec 列表（用于批量 ZIP 导出，含 metadata）。"""
    from datetime import datetime
    specs = []
    if not output:
        return specs
    charts_data = output.get("charts_data", {}) or {}
    df = wiz_data.get("df")
    if df is None or not charts_data:
        return specs

    test_name = ctx.get("test_name_zh", "分析")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    from src.visualization.charts import (
        bar_with_error, box_plot, scatter_with_regression,
        correlation_heatmap, distribution_plot, qq_plot,
    )

    if "box_data" in charts_data:
        bd = charts_data["box_data"]
        specs.append({
            "fig": box_plot(df, bd["dv"], bd["iv"], title=f"{bd['dv']} 分组箱线图"),
            "test_name_zh": test_name,
            "chart_type": "箱线图",
            "variables": [bd["dv"], bd["iv"]],
            "timestamp": timestamp,
        })
    if "corr_matrix" in charts_data:
        specs.append({
            "fig": correlation_heatmap(charts_data["corr_matrix"]),
            "test_name_zh": test_name,
            "chart_type": "相关热力图",
            "variables": list(charts_data["corr_matrix"].columns),
            "timestamp": timestamp,
        })
    if "scatter_cols" in charts_data:
        cols = charts_data["scatter_cols"]
        if len(cols) >= 2:
            specs.append({
                "fig": scatter_with_regression(df, cols[0], cols[1], title=f"{cols[0]} vs {cols[1]}"),
                "test_name_zh": test_name,
                "chart_type": "散点图",
                "variables": cols[:2],
                "timestamp": timestamp,
            })
    if "histogram_cols" in charts_data:
        for col in charts_data["histogram_cols"][:3]:
            if col in df.columns:
                specs.append({
                    "fig": distribution_plot(df, col, title=f"{col} 分布图"),
                    "test_name_zh": test_name,
                    "chart_type": "分布图",
                    "variables": [col],
                    "timestamp": timestamp,
                })
    if "qq_col" in charts_data and charts_data["qq_col"] in df.columns:
        col = charts_data["qq_col"]
        specs.append({
            "fig": qq_plot(df, col, title=f"{col} Q-Q 图"),
            "test_name_zh": test_name,
            "chart_type": "QQ图",
            "variables": [col],
            "timestamp": timestamp,
        })
    return specs


def _render_figures_zip_download(output: dict, ctx: dict, wiz_data: dict):
    """v2.8: 批量 ZIP 下载控件。"""
    with st.expander("📦 批量下载所有图表（ZIP）", expanded=False):
        st.caption(
            "把当前分析涉及的所有图表打包为 ZIP（含 PNG + 图表说明.txt），"
            "方便论文整理和提交。"
        )
        palette = st.radio(
            "图表配色",
            options=["grayscale", "color", "mono"],
            format_func=lambda p: {
                "grayscale": "灰度（论文/期刊）",
                "color": "彩色（电子稿）",
                "mono": "纯黑（复印）",
            }[p],
            horizontal=True,
            key="zip_palette",
        )
        if st.button("📦 生成 ZIP 包", type="secondary",
                     width="stretch", key="zip_gen"):
            from src.utils.export_naming import export_filename
            specs = _build_figure_specs(output, ctx, wiz_data)
            if not specs:
                st.warning("当前分析没有可导出的图表。")
                return
            with st.spinner(f"正在生成 {len(specs)} 张图表..."):
                try:
                    zip_bytes = export_all_figures_zip(
                        specs, palette=palette,
                        width_px=1500, height_px=1000,
                    )
                    st.session_state["_figures_zip"] = zip_bytes
                    st.session_state["_figures_zip_count"] = len(specs)
                except Exception as e:
                    st.error(f"打包失败：{e}")

        if st.session_state.get("_figures_zip"):
            _render_official_download(
                "⬇ 下载 ZIP 包",
                artifact_state_keys=("_figures_zip", "_figures_zip_count"),
                data=st.session_state["_figures_zip"],
                file_name=export_filename("论文图表", "zip", title=ctx.get('test_name_zh', '分析')),
                mime="application/zip",
                key="zip_dl",
                width="stretch",
            )
            st.caption(
                f"已打包 {st.session_state.get('_figures_zip_count', 0)} 张图，"
                "含「图表说明.txt」帮助你识别每张图。"
            )


def _build_paper_figures(output: dict, ctx: dict, wiz_data: dict,
                        palette: str = "grayscale") -> list:
    """根据 output 中的 charts_data 生成论文版 PNG 列表。"""
    figures = []
    if not output:
        return figures

    charts_data = output.get("charts_data", {}) or {}
    df = wiz_data.get("df")
    if df is None or not charts_data:
        return figures

    from src.visualization.charts import (
        bar_with_error, box_plot, scatter_with_regression,
        correlation_heatmap, distribution_plot, qq_plot,
    )

    candidates = []
    if "box_data" in charts_data:
        bd = charts_data["box_data"]
        candidates.append((
            box_plot(df, bd["dv"], bd["iv"], title=f"{bd['dv']} 分组箱线图"),
            f"{bd['dv']} 分组箱线图",
        ))
    if "corr_matrix" in charts_data:
        candidates.append((
            correlation_heatmap(charts_data["corr_matrix"]),
            "相关矩阵热力图",
        ))
    if "scatter_cols" in charts_data:
        cols = charts_data["scatter_cols"]
        if len(cols) >= 2:
            candidates.append((
                scatter_with_regression(df, cols[0], cols[1], title=f"{cols[0]} vs {cols[1]}"),
                f"{cols[0]} 与 {cols[1]} 的散点图",
            ))
    if "histogram_cols" in charts_data:
        for col in charts_data["histogram_cols"][:2]:
            if col in df.columns:
                candidates.append((
                    distribution_plot(df, col, title=f"{col} 分布图"),
                    f"{col} 频数分布图",
                ))

    for fig, caption in candidates[:3]:  # 最多嵌入 3 张图
        try:
            png = to_paper_png(fig, palette=palette, width_px=1500, height_px=1000)
            figures.append(FigureItem(caption=caption, png_bytes=png, width_cm=12.0))
        except KaleidoMissingError:
            st.info("ℹ 图表导出已跳过：未安装 kaleido。运行 `pip install kaleido` 后重试。")
            break  # 不再尝试后续图
        except Exception:
            continue
    return figures


def render_common_mistake_warnings(output, df, plan):
    """根据分析上下文动态显示本科生常见错误警示"""
    if plan is None:
        return

    test_type = plan.test_type if hasattr(plan, "test_type") else output.get("test_type", "")
    iv_count = len(plan.independent_vars) if hasattr(plan, "independent_vars") else 0
    dv_count = len(plan.dependent_vars) if hasattr(plan, "dependent_vars") else 0

    # ── 警告1: 多次 t 检验（类错误膨胀） ──
    if iv_count >= 1 and dv_count >= 2:
        if test_type in ("independent_ttest", "mann_whitney") and dv_count > 1:
            st.markdown("""
            <div class="warning-box">
            <strong>⚠️ 多次比较提醒：</strong>你同时对 {} 个因变量运行了检验。<br>
            每次检验都有 5% 的一类错误风险，多次检验会累积错误概率。<br>
            <strong>建议：</strong>使用 Bonferroni 校正（α 除以检验次数）或改用 MANOVA。
            </div>
            """.format(dv_count), unsafe_allow_html=True)

    # ── 警告2: 相关 ≠ 因果 ──
    if test_type in ("pearson_corr", "spearman_corr", "partial_corr"):
        st.markdown("""
        <div class="warning-box">
        <strong>⚠️ 相关 ≠ 因果：</strong>相关分析只能说明两个变量存在关联，<strong>不能推断因果关系</strong>。<br>
        可能存在第三变量（混杂因素）同时影响两个变量，或因果关系方向与你的假设相反。<br>
        <strong>在论文中报告相关结果时，请使用"相关"、"关联"等术语，避免使用"导致"、"影响"等因果语言。</strong>
        </div>
        """, unsafe_allow_html=True)

    # ── 警告3: 中介效应前提 ──
    if test_type == "mediation":
        st.markdown("""
        <div class="info-box">
        <strong>📋 中介效应分析前提：</strong>Baron & Kenny (1986) 建议以下条件：<br>
        1. X 对 Y 的总效应显著（c 路径）<br>
        2. X 对 M 的效应显著（a 路径）<br>
        3. 控制 X 后，M 对 Y 的效应显著（b 路径）<br>
        4. 间接效应 (a×b) 的 bootstrap CI 不包含 0<br>
        <strong>常见错误：</strong>未检验总效应是否显著就直接做中介分析。
        </div>
        """, unsafe_allow_html=True)

    # ── 警告4: 调节效应解释 ──
    if test_type == "moderation":
        st.markdown("""
        <div class="info-box">
        <strong>📋 调节效应分析提示：</strong><br>
        - 调节变量影响的是 X→Y 关系的<strong>强度或方向</strong><br>
        - 请报告简单斜率检验结果（调节变量在 ±1SD 处的效应）<br>
        - 交互项显著只是第一步，还需要看简单斜率图来理解调节模式
        </div>
        """, unsafe_allow_html=True)

    # ── 警告5: 缺失数据处理 ──
    if df is not None:
        missing_cols = [c for c in df.columns if df[c].isna().any()]
        if missing_cols:
            total_missing = df.isna().sum().sum()
            pct = total_missing / (df.shape[0] * df.shape[1]) * 100
            st.markdown(f"""
            <div class="info-box">
            <strong>📋 缺失数据提醒：</strong>你的数据包含 {total_missing} 个缺失值（{pct:.1f}%）。<br>
            <strong>缺失列：</strong>{', '.join(missing_cols)}<br>
            大多数统计分析会自动删除含缺失值的行（列表删除），可能导致有效样本减少。<br>
            <strong>论文中应：</strong>报告缺失值数量和比例，说明缺失数据处理方法（列表删除/插补/Full Information ML）。<br>
            <strong>注意：</strong>缺失率 > 5% 时，简单删除可能导致估计偏差。
            </div>
            """, unsafe_allow_html=True)

    # ── 警告6: 小样本警告 ──
    if df is not None:
        n_rows = df.shape[0]
        if n_rows < 30:
            st.markdown(f"""
            <div class="warning-box">
            <strong>⚠️ 小样本提醒：</strong>当前数据仅 {n_rows} 行。<br>
            小样本（n < 30）会降低统计检验力，参数检验的正态性假设也更难满足。<br>
            <strong>建议：</strong>报告效应量和置信区间，考虑使用非参数检验或 Bootstrap 方法。
            </div>
            """, unsafe_allow_html=True)

    # ── 警告7: 方差分析后续比较 ──
    if test_type == "one_way_anova" and iv_count >= 1:
        iv_values = df[plan.independent_vars[0]].nunique() if plan.independent_vars else 0
        if iv_values > 2:
            st.markdown("""
            <div class="info-box">
            <strong>📋 事后比较提示：</strong>ANOVA 显著只说明至少有一组与其他组不同。<br>
            需要进行<strong>事后检验（post-hoc test）</strong>来确定具体哪些组间存在差异。<br>
            常用方法：Tukey HSD（方差齐性）、Games-Howell（方差不齐）。
            </div>
            """, unsafe_allow_html=True)


def render_assumption_failure_guidance(output, plan, df):
    """检测假设检验失败并推荐替代方法"""
    if plan is None or output is None:
        return

    test_type = getattr(plan, "test_type", output.get("test_type", ""))
    errors = output.get("errors", [])
    assumptions = output.get("assumptions", {})

    normality_failed = False
    homogeneity_failed = False

    # 检查 errors 中的警告
    for err in errors:
        msg = err.get("message", "")
        if "正态" in msg and ("不符合" in msg or "未通过" in msg or "不满足" in msg):
            normality_failed = True
        if "方差不齐" in msg or ("方差齐" in msg and "不" in msg):
            homogeneity_failed = True

    # 检查 assumptions 字典
    for key in ["normality", "homogeneity"]:
        val = assumptions.get(key)
        if val is None:
            continue
        if isinstance(val, dict):
            if not val.get("passed", True):
                if key == "normality":
                    normality_failed = True
                elif key == "homogeneity":
                    homogeneity_failed = True
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and not item.get("passed", True):
                    normality_failed = True
                    break

    if not normality_failed and not homogeneity_failed:
        return

    # 正态性失败 → 非参数替代（Welch 仍要求正态性，故正态性失败时不推荐）
    nonparametric_map = {
        "independent_ttest": ("mann_whitney", "Mann-Whitney U 检验", "不依赖正态性假设，比较两组中位数差异"),
        "paired_ttest": ("wilcoxon", "Wilcoxon 符号秩检验", "配对样本的非参数替代方法"),
        "one_way_anova": ("kruskal_wallis", "Kruskal-Wallis H 检验", "单因素方差分析的非参数替代"),
        "pearson_corr": ("spearman_corr", "Spearman 等级相关", "不依赖正态性，基于秩次的相关系数"),
    }

    # 仅方差不齐失败 → Welch 校正（保留正态性假设，放松方差齐性）
    welch_map = {
        "independent_ttest": ("welch_ttest", "Welch t 检验", "方差不齐时的校正 t 检验，结果更稳健"),
        "one_way_anova": ("welch_anova", "Welch ANOVA", "方差不齐时的校正方差分析，不要求方差齐性"),
    }

    # 选择替代策略：正态性失败优先走非参数；仅方差不齐走 Welch
    if normality_failed:
        alt = nonparametric_map.get(test_type)
        reason_text = "正态性检验未通过"
        if homogeneity_failed:
            reason_text += "；方差齐性假设不满足"
    elif homogeneity_failed:
        alt = welch_map.get(test_type)
        reason_text = "方差齐性假设不满足"
    else:
        return

    if alt is None:
        return

    alt_type, alt_name, alt_reason = alt

    # t 检验已自动 Welch 校正 → 只提示，不切换
    already_welch = False
    if test_type == "independent_ttest" and homogeneity_failed and not normality_failed:
        result = output.get("result")
        if result is not None and getattr(result, "is_welch", False):
            already_welch = True

    if already_welch:
        st.markdown("""
        <div style="border:2px solid #2196f3; border-radius:10px; padding:16px; margin:12px 0; background:#e3f2fd;">
        <h4 style="margin:0 0 8px 0; color:#0d47a1;">✅ 方差不齐已自动处理</h4>
        <p style="margin:4px 0;">系统检测到方差不齐，已自动使用 <strong>Welch 校正</strong>计算 t 检验结果，结果可靠，无需切换方法。</p>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(f"""
    <div style="border:2px solid #ff9800; border-radius:10px; padding:16px; margin:12px 0; background:#fff8e1;">
    <h4 style="margin:0 0 8px 0; color:#e65100;">⚠️ 假设条件不满足 — 建议更换分析方法</h4>
    <p style="margin:4px 0;"><strong>检测到问题：</strong>{reason_text}</p>
    <p style="margin:4px 0;"><strong>推荐替代方法：</strong>{alt_name}</p>
    <p style="margin:4px 0; color:#666;">{alt_reason}</p>
    </div>
    """, unsafe_allow_html=True)

    dv = getattr(plan, "dependent_vars", [None])
    dv = dv[0] if dv else None
    iv = getattr(plan, "independent_vars", [None])
    iv = iv[0] if iv else None

    if st.button(f"🔄 一键切换为 {alt_name}", type="primary", width="stretch",
                 key=f"switch_{alt_type}"):
        from src.parser.parser import resolve_intent
        from src.analysis.runner import run_analysis
        request = f"用{alt_name}分析"
        if dv:
            request += f" {dv}"
        if iv:
            request += f" 和 {iv} 的差异"
        new_plan = resolve_intent(df, request)
        new_output = run_analysis(df, new_plan)
        st.session_state.analysis_output = new_output
        st.session_state.plan = new_plan
        if "undergrad_wizard_data" in st.session_state:
            wiz_data = st.session_state.undergrad_wizard_data
            if "wizard_results_context" in wiz_data:
                wiz_data["wizard_results_context"]["test_type"] = new_output.get("test_type", alt_type)
                wiz_data["wizard_results_context"]["test_name_zh"] = new_output.get("test_name_zh", alt_name)
        st.rerun()


def render_undergrad_wizard():
    """本科论文向导模式 — 分步骤引导式界面"""
    wiz = st.session_state

    # ── 路径选择首页 ──
    if wiz.undergrad_path is None:
        st.title("📚 本科论文助手")
        st.caption("选择你的研究类型，跟随向导一步步完成数据分析与论文写作。")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class="psy-choice-card">
            <h3>📋 问卷调查研究</h3>
            <p class="psy-choice-card__lead">适合用问卷收集数据研究变量间关系的同学</p>
            <hr>
            <p style="font-size:0.85em;">✅ 信度分析 → 描述统计<br>
            ✅ t检验 / 方差分析 / 相关<br>
            ✅ APA格式结果表格<br>
            ✅ 白话结果解读</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("📋 开始问卷研究向导", type="primary", width="stretch",
                         key="path_survey"):
                wiz.undergrad_path = "survey"
                wiz.undergrad_step = 1
                # 保留漏斗已填字段（research_q/title/hypothesis/dv/iv 等）
                existing = wiz.get("undergrad_wizard_data") or {}
                wiz.undergrad_wizard_data = {
                    "title": existing.get("title", ""),
                    "research_q": existing.get("research_q", ""),
                    "hypothesis": existing.get("hypothesis", ""),
                    **{k: v for k, v in existing.items() if k not in {"title", "research_q", "hypothesis"}},
                }
                st.rerun()

        with col2:
            st.markdown("""
            <div class="psy-choice-card psy-choice-card--success">
            <h3>🧪 实验研究</h3>
            <p class="psy-choice-card__lead">适合设计实验、操纵自变量、比较组间差异的同学</p>
            <hr>
            <p style="font-size:0.85em;">✅ 随机化检验 / 组间比较<br>
            ✅ t检验 / 方差分析<br>
            ✅ 效应量 + 检验力<br>
            ✅ 实验程序生成</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🧪 开始实验研究向导", type="primary", width="stretch",
                         key="path_experiment"):
                wiz.undergrad_path = "experiment"
                wiz.undergrad_step = 1
                # 保留漏斗已填字段
                existing = wiz.get("undergrad_wizard_data") or {}
                wiz.undergrad_wizard_data = {
                    "title": existing.get("title", ""),
                    "research_q": existing.get("research_q", ""),
                    "hypothesis": existing.get("hypothesis", ""),
                    "iv": existing.get("iv", ""),
                    "dv": existing.get("dv", ""),
                    "design_type": existing.get("design_type", "between"),
                    **{k: v for k, v in existing.items()
                        if k not in {"title", "research_q", "hypothesis", "iv", "dv", "design_type"}},
                }
                st.rerun()

        with col3:
            st.markdown("""
            <div class="psy-choice-card psy-choice-card--neutral">
            <h3>🔓 自由模式</h3>
            <p class="psy-choice-card__lead">我已熟悉系统操作，直接使用完整功能</p>
            <hr>
            <p style="font-size:0.85em;">✅ 所有分析功能<br>
            ✅ 问卷设计 / 实验设计<br>
            ✅ 论文写作工具<br>
            ✅ 完整功能无限制</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔓 进入自由模式", type="secondary", width="stretch",
                         key="path_free"):
                wiz.undergrad_mode = False
                wiz["_pending_undergrad_mode"] = False
                wiz.undergrad_path = None
                st.rerun()

        st.divider()
        with st.expander("🤔 不确定该选哪个？"):
            st.markdown("""
            **问卷调查研究**：你通过问卷星/腾讯问卷等方式发放问卷，收集了一组人的数据，
            想分析各变量之间的关系（如：自尊与焦虑是否相关？不同年级学生压力是否有差异？）。

            **实验研究**：你设计了一个实验，将被试随机分配到不同条件，操纵了自变量
            （如：不同学习策略、不同情绪启动条件），比较各组在因变量上的差异。

            **自由模式**：你已经熟悉心理学统计和本系统，不需要引导式操作。
            """)

        return

    # ── 分步骤向导 ──
    path = wiz.undergrad_path
    step = wiz.undergrad_step
    wiz_data = wiz.undergrad_wizard_data

    # v3.7 N6: 记录断点位置（用户停留在哪一步就记录哪一步）
    try:
        from src.utils.workspace import update_last_position
        if isinstance(step, int) and step >= 1:
            update_last_position("wizard", step=step, session_state=st.session_state)
    except Exception:
        pass

    # 总步骤数
    total_steps = 7
    step_names = [
        "研究信息", "上传数据", "查看数据",
        "选择分析方法", "运行分析", "查看结果与导出",
        "写入论文",
    ]

    # ── 顶部进度条 ──
    st.title("📚 本科论文助手")
    cols_title = st.columns([4, 1])
    with cols_title[0]:
        st.caption(
            f"路径：{'📋 问卷调查研究' if path == 'survey' else '🧪 实验研究'} | "
            f"步骤 {step}/{total_steps}"
        )
    with cols_title[1]:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 回到选题漏斗", key="_wizard_back_to_funnel",
                         help="返回漏斗修订选题——可选继续修改或新建分支"):
                st.session_state["_wizard_back_dialog"] = True
        with col_b:
            # v3.4 文献综述工作台入口
            if st.button("📚 文献综述", key="_wizard_to_literature_review",
                         help="打开文献综述工作台（搜索/笔记/矩阵/Gap 分析）"):
                from src.utils.workspace import (
                    get_upstream_state as _gus,
                    update_last_position as _ulp,
                )
                _us = _gus(st.session_state)
                _us["phase"] = "literature_review"
                _ulp("literature_review", session_state=st.session_state)
                try:
                    from src.utils.autosave import trigger_autosave
                    from src.utils.workspace import build_workspace_snapshot
                    trigger_autosave(st.session_state, build_workspace_snapshot, force=True)
                except Exception:
                    pass
                st.rerun()

    # v3.3 二级确认对话框
    if st.session_state.get("_wizard_back_dialog"):
        st.markdown(
            """<div style="background:#fff3cd;border-left:4px solid #ffc107;
            padding:12px 16px;border-radius:6px;margin:8px 0;">
            <strong>🔄 你想怎么回到漏斗？</strong><br>
            <span style="font-size:0.9em;color:#555;">
            两种模式语义不同，请明确选择，避免无意中丢失或混合不同选题尝试。
            </span></div>""",
            unsafe_allow_html=True,
        )
        cols_dialog = st.columns([1, 1, 1])
        if cols_dialog[0].button("📝 继续修改当前漏斗", key="_wb_continue", type="primary"):
            from src.upstream.topic_funnel import restart_funnel
            restart_funnel(st.session_state, keep_history=True)
            st.session_state["_wizard_back_dialog"] = False
            st.rerun()
        if cols_dialog[1].button("🌱 新建分支重新选题", key="_wb_branch"):
            from src.upstream.topic_funnel import (
                archive_current_branch_and_restart,
            )
            bid = archive_current_branch_and_restart(st.session_state)
            st.session_state["_wizard_back_dialog"] = False
            if bid:
                st.success(f"已归档当前漏斗为分支 {bid}，开始新分支")
            st.rerun()
        if cols_dialog[2].button("取消", key="_wb_cancel"):
            st.session_state["_wizard_back_dialog"] = False
            st.rerun()
    progress = step / total_steps
    st.progress(progress, text=f"第 {step} 步：{step_names[step - 1]}")

    # ── 步骤导航 ──
    nav_cols = st.columns(total_steps)
    for i, name in enumerate(step_names, 1):
        with nav_cols[i - 1]:
            if i < step:
                st.markdown(f"✅ ~~{name}~~")
            elif i == step:
                st.markdown(f"**🔵 {name}**")
            else:
                st.markdown(f"⚪ {name}")

    # ── v2.9: 全局状态徽章 ──
    _render_status_badges()

    st.divider()

    # ================================================================
    # 步骤 1: 研究信息
    # ================================================================
    if step == 1:
        st.subheader("📝 第1步：填写研究信息")
        st.caption("请提供你的论文基本信息，我们将据此推荐合适的分析方法。")

        wiz_data["title"] = st.text_input(
            "论文题目",
            value=wiz_data.get("title", ""),
            placeholder="例如：大学生自尊与社交焦虑的关系研究",
            help="可后续修改，仅用于生成报告标题",
        )
        wiz_data["research_q"] = st.text_area(
            "研究问题",
            value=wiz_data.get("research_q", ""),
            placeholder="例如：大学生的自尊水平是否与社交焦虑存在负相关？不同性别学生的社交焦虑水平是否存在差异？",
            height=80,
            help="描述你主要想探究什么问题",
        )
        wiz_data["hypothesis"] = st.text_input(
            "研究假设",
            value=wiz_data.get("hypothesis", ""),
            placeholder="例如：H1: 自尊与社交焦虑呈显著负相关",
            help="你的研究假设（可以写多条，用编号标记）",
        )

        if path == "experiment":
            col_iv, col_dv = st.columns(2)
            with col_iv:
                wiz_data["iv"] = st.text_input(
                    "自变量 (IV)",
                    value=wiz_data.get("iv", ""),
                    placeholder="例如：学习策略（重复朗读 vs 测试效应）",
                )
                wiz_data["design_type"] = st.selectbox(
                    "实验设计类型",
                    ["between", "within", "mixed"],
                    format_func=lambda x: {
                        "between": "被试间设计",
                        "within": "被试内设计",
                        "mixed": "混合设计",
                    }[x],
                )
            with col_dv:
                wiz_data["dv"] = st.text_input(
                    "因变量 (DV)",
                    value=wiz_data.get("dv", ""),
                    placeholder="例如：记忆测验正确率",
                )

        # ── 模块衔接：问卷/实验设计前置 ──
        st.divider()
        st.markdown("#### 🔗 前置准备（可选）")
        if path == "survey":
            bridge_choice = st.radio(
                "你已经有现成的问卷数据了吗？",
                ["我已经有问卷数据，直接上传分析", "我需要先设计一份新问卷"],
                key="bridge_survey",
                horizontal=True,
            )
            if bridge_choice == "我需要先设计一份新问卷":
                st.info(
                    "💡 问卷设计模块可以帮助你根据研究构念自动生成量表题目。"
                    "点击下方按钮跳转到问卷设计模块，完成后可返回向导继续。"
                )
                if st.button("📋 跳转到问卷设计模块", type="secondary", width="stretch",
                             key="bridge_to_questionnaire"):
                    wiz.undergrad_mode = False
                    wiz["_pending_undergrad_mode"] = False
                    st.session_state.app_mode = "📋 问卷设计"
                    # 前向传递：把向导中的研究主题预填到问卷设计
                    prefill = wiz_data.get("topic", "") or wiz_data.get("construct", "")
                    if prefill:
                        st.session_state._prefill_q_request = prefill
                    # 保留向导状态以便返回
                    st.session_state._wizard_return = {
                        "path": path,
                        "step": 1,
                        "data": wiz_data,
                    }
                    st.rerun()
        elif path == "experiment":
            bridge_choice = st.radio(
                "你需要设计实验程序吗？",
                ["我已经有实验数据，直接分析", "我需要先设计实验程序和范式"],
                key="bridge_experiment",
                horizontal=True,
            )
            if bridge_choice == "我需要先设计实验程序和范式":
                st.info(
                    "💡 实验设计模块可以帮助你生成实验范式、确定样本量、"
                    "创建预注册文档。点击下方按钮跳转，完成后可返回向导继续。"
                )
                if st.button("🧪 跳转到实验设计模块", type="secondary", width="stretch",
                             key="bridge_to_experiment"):
                    wiz.undergrad_mode = False
                    wiz["_pending_undergrad_mode"] = False
                    st.session_state.app_mode = "🧪 实验设计"
                    # 前向传递：把向导中的研究信息预填到实验设计
                    topic = wiz_data.get("topic", "")
                    if topic:
                        st.session_state._prefill_exp_topic = topic
                    iv_text = wiz_data.get("iv", "")
                    if iv_text:
                        st.session_state._prefill_exp_ivs = iv_text
                    dv_text = wiz_data.get("dv", "")
                    if dv_text:
                        st.session_state._prefill_exp_dvs = dv_text
                    design_type = wiz_data.get("design_type", "")
                    if design_type:
                        st.session_state._prefill_exp_design_hint = design_type
                    st.session_state._wizard_return = {
                        "path": path,
                        "step": 1,
                        "data": wiz_data,
                    }
                    st.rerun()

        # ── 从模块返回向导的检测 ──
        if st.session_state.get("_wizard_return") is not None:
            ret = st.session_state._wizard_return
            # 检测模块设计结果并注入到向导数据
            module_context = None
            design = st.session_state.get("questionnaire_design")
            if design is not None and isinstance(design, dict):
                items = design.get("items", [])
                rev_count = sum(1 for it in items if it.get("reverse"))
                module_context = {
                    "module": "questionnaire",
                    "construct_name": design.get("construct_name", ""),
                    "dimensions": design.get("dimensions_used", []),
                    "item_count": len(items),
                    "reverse_count": rev_count,
                    "reverse_ratio": round(rev_count / len(items), 2) if items else 0,
                }
            exp_eng = st.session_state.get("experiment_engine")
            if exp_eng is not None and hasattr(exp_eng, "design"):
                exp_design = exp_eng.design
                if exp_design:
                    module_context = {
                        "module": "experiment",
                        "design_type": getattr(exp_design, "design_type", "between_subjects"),
                        "groups": getattr(exp_design, "groups", []),
                        "dv_count": len(getattr(exp_design, "dependent_vars", [])),
                        "iv_count": len(getattr(exp_design, "independent_vars", [])),
                    }
            st.success(f"✅ 模块操作完成！点击下方按钮返回向导继续。")
            if st.button("🔙 返回向导继续", type="primary", width="stretch"):
                wiz.undergrad_mode = True
                wiz["_pending_undergrad_mode"] = True
                wiz.undergrad_path = ret["path"]
                wiz.undergrad_step = 2
                wiz_data = ret["data"]
                if module_context is not None:
                    wiz_data["module_context"] = module_context
                # 后向回流：保存完整设计数据供论文写作引用
                design = st.session_state.get("questionnaire_design")
                if design is not None and isinstance(design, dict):
                    wiz_data["questionnaire_design_full"] = design
                exp_eng = st.session_state.get("experiment_engine")
                if exp_eng is not None and hasattr(exp_eng, "design"):
                    exp_design = exp_eng.design
                    if exp_design:
                        wiz_data["experiment_design_full"] = exp_design
                wiz.undergrad_wizard_data = wiz_data
                # 清除预填充标记
                for k in ["_prefill_q_request", "_prefill_exp_topic", "_prefill_exp_ivs",
                          "_prefill_exp_dvs", "_prefill_exp_design_hint"]:
                    st.session_state.pop(k, None)
                st.session_state._wizard_return = None
                st.rerun()

        st.divider()
        _, right_col = st.columns([3, 1])
        with right_col:
            if st.button("下一步 ➡️", type="primary", width="stretch"):
                wiz.undergrad_step = 2
                st.rerun()

    # ================================================================
    # 步骤 2: 上传数据
    # ================================================================
    elif step == 2:
        st.subheader("📁 第2步：上传数据文件")
        st.caption("支持 CSV、Excel (.xlsx/.xls)、SPSS (.sav) 格式。")

        # ── 模块返回上下文提示 ──
        module_ctx = wiz_data.get("module_context")
        if module_ctx is not None:
            if module_ctx.get("module") == "questionnaire":
                cn = module_ctx.get("construct_name", "未知构念")
                dims = module_ctx.get("dimensions", [])
                n_items = module_ctx.get("item_count", 0)
                rev_r = module_ctx.get("reverse_ratio", 0)
                st.markdown(f"""
                <div class="info-box" style="border-left:4px solid #4caf50;">
                <strong>📋 问卷设计已完成！</strong><br>
                你刚刚在问卷设计模块中创建了 <strong>「{cn}」</strong> 量表：<br>
                • 维度：{'、'.join(dims) if dims else '未指定'}（共 {len(dims)} 个）<br>
                • 题目数：{n_items} 题（其中反向题 {int(rev_r * n_items)} 题，占比 {int(rev_r * 100)}%）<br>
                <br><em>💡 提示：上传按照此量表收集的 CSV 数据后，系统会自动识别变量类型。</em>
                </div>
                """, unsafe_allow_html=True)
            elif module_ctx.get("module") == "experiment":
                groups = module_ctx.get("groups", [])
                dv_n = module_ctx.get("dv_count", 0)
                iv_n = module_ctx.get("iv_count", 0)
                st.markdown(f"""
                <div class="info-box" style="border-left:4px solid #2196f3;">
                <strong>🧪 实验设计已完成！</strong><br>
                你的实验设计包含：<br>
                • 组别：{'、'.join(groups) if groups else '未指定'}（共 {len(groups)} 组）<br>
                • 自变量数：{iv_n} | 因变量数：{dv_n}<br>
                <br><em>💡 提示：上传实验数据 CSV 时，请确保包含分组列和前测/后测列。</em>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("📋 数据格式要求（上传前请检查）", expanded=True):
            st.markdown("""
            **问卷调查类数据结构：**
            - 第一行为变量名（标题行），如 `性别, 年龄, 自尊总分, 焦虑总分`
            - 每一行为一个被试的数据
            - 分组变量建议使用文字标签（如"男"/"女"、"实验组"/"控制组"），系统会自动识别
            - 量表维度可使用总分或题项分

            **实验类数据结构：**
            - 每组被试的数据在一起，用分组变量区分
            - 被试间设计：一个分组列 + 一个因变量列
            - 被试内设计：每个条件一个因变量列

            **❌ 常见错误：**
            - 不要把多个量表混合在同一个Excel Sheet中
            - 不要在第一行之前添加说明文字
            - 缺失值请留空，不要填"无"、"缺失"等文字
            """)

        # 示例数据下载
        with st.expander("📥 下载示例数据模板"):
            import io as io_mod
            example_type = st.radio(
                "选择模板类型", ["问卷调查", "实验数据"], horizontal=True,
                key="example_type",
            )
            if example_type == "问卷调查":
                example_csv = (
                    "性别,年龄,自尊总分,社交焦虑总分,生活满意度\n"
                    "男,20,28,45,5\n女,21,32,38,4\n男,19,25,50,3\n女,22,30,42,4\n"
                    "男,20,27,48,3\n女,21,33,35,5\n男,22,29,44,4\n女,19,31,40,4\n"
                )
                st.download_button(
                    "📥 下载问卷调查模板 (CSV)",
                    data=example_csv,
                    file_name="survey_template.csv",
                    mime="text/csv",
                )
            else:
                example_csv = (
                    "被试编号,组别,记忆成绩,反应时_ms\n"
                    "1,实验组,85,450\n2,实验组,88,420\n3,实验组,78,480\n"
                    "4,控制组,72,510\n5,控制组,70,530\n6,控制组,75,490\n"
                )
                st.download_button(
                    "📥 下载实验数据模板 (CSV)",
                    data=example_csv,
                    file_name="experiment_template.csv",
                    mime="text/csv",
                )

        # ── 示例数据一键加载 ──
        with st.expander("🧪 一键加载示例数据（无需上传文件）", expanded=False):
            st.markdown("选择一组模拟数据直接体验完整分析流程：")
            demo_col1, demo_col2 = st.columns(2)
            with demo_col1:
                if st.button("📋 加载问卷示例数据", width="stretch",
                             help="200名被试的社交焦虑问卷数据（含焦虑总分、维度分、自尊分）"):
                    demo_df = generate_demo_questionnaire_data(200)
                    wiz.df = demo_df
                    wiz.meta = {
                        "source_type": "csv", "row_count": len(demo_df),
                        "col_count": len(demo_df.columns), "file_name": "demo_questionnaire.csv",
                    }
                    wiz.inspector = inspect_dataframe(demo_df)
                    wiz.file_name = "demo_questionnaire.csv"
                    wiz.analysis_output = None
                    wiz.plan = None
                    wiz_data["data_loaded"] = True
                    wiz_data["is_demo"] = True
                    st.success(f"✅ 已加载问卷示例数据 ({len(demo_df)} 名被试, {len(demo_df.columns)} 个变量)")
                    st.rerun()
            with demo_col2:
                if st.button("🧪 加载实验示例数据", width="stretch",
                             help="80名被试的认知实验数据（实验组/控制组，前测/后测）"):
                    demo_df = generate_demo_experiment_data(40)
                    wiz.df = demo_df
                    wiz.meta = {
                        "source_type": "csv", "row_count": len(demo_df),
                        "col_count": len(demo_df.columns), "file_name": "demo_experiment.csv",
                    }
                    wiz.inspector = inspect_dataframe(demo_df)
                    wiz.file_name = "demo_experiment.csv"
                    wiz.analysis_output = None
                    wiz.plan = None
                    wiz_data["data_loaded"] = True
                    wiz_data["is_demo"] = True
                    st.success(f"✅ 已加载实验示例数据 ({len(demo_df)} 名被试, {len(demo_df.columns)} 个变量)")
                    st.rerun()
            demo_col3, demo_col4 = st.columns(2)
            with demo_col3:
                if st.button("🔄 加载重复测量示例", width="stretch",
                             help="50名被试×3个时间点的焦虑追踪数据（T1→T2→T3递减趋势）"):
                    demo_df = generate_demo_repeated_measures_data(50)
                    wiz.df = demo_df
                    wiz.meta = {
                        "source_type": "csv", "row_count": len(demo_df),
                        "col_count": len(demo_df.columns), "file_name": "demo_repeated_measures.csv",
                    }
                    wiz.inspector = inspect_dataframe(demo_df)
                    wiz.file_name = "demo_repeated_measures.csv"
                    wiz.analysis_output = None
                    wiz.plan = None
                    wiz_data["data_loaded"] = True
                    wiz_data["is_demo"] = True
                    st.success(f"✅ 已加载重复测量示例 ({len(demo_df)} 名被试, {len(demo_df.columns)} 个变量)")
                    st.rerun()
            with demo_col4:
                if st.button("📊 加载多组干预示例", width="stretch",
                             help="120名被试×4组干预数据（1对照组+3实验组，前测/后测）"):
                    demo_df = generate_demo_multi_group_data(30)
                    wiz.df = demo_df
                    wiz.meta = {
                        "source_type": "csv", "row_count": len(demo_df),
                        "col_count": len(demo_df.columns), "file_name": "demo_multi_group.csv",
                    }
                    wiz.inspector = inspect_dataframe(demo_df)
                    wiz.file_name = "demo_multi_group.csv"
                    wiz.analysis_output = None
                    wiz.plan = None
                    wiz_data["data_loaded"] = True
                    wiz_data["is_demo"] = True
                    st.success(f"✅ 已加载多组干预示例 ({len(demo_df)} 名被试, {len(demo_df.columns)} 个变量)")
                    st.rerun()
            demo_col5, _ = st.columns([1, 1])
            with demo_col5:
                if st.button("🔗 加载中介效应示例", width="stretch",
                             help="150名被试的中介模型数据（培训→学习动机→学业成绩, ab路径显著）"):
                    demo_df = generate_demo_mediation_data(150)
                    wiz.df = demo_df
                    wiz.meta = {
                        "source_type": "csv", "row_count": len(demo_df),
                        "col_count": len(demo_df.columns), "file_name": "demo_mediation.csv",
                    }
                    wiz.inspector = inspect_dataframe(demo_df)
                    wiz.file_name = "demo_mediation.csv"
                    wiz.analysis_output = None
                    wiz.plan = None
                    wiz_data["data_loaded"] = True
                    wiz_data["is_demo"] = True
                    st.success(f"✅ 已加载中介效应示例 ({len(demo_df)} 名被试, {len(demo_df.columns)} 个变量)")
                    st.rerun()

        # ── HR / People Analytics 场景示例 ──
        with st.expander("🏢 People Analytics / HR 场景示例（4 套数据）", expanded=False):
            st.caption(
                "面向 HR 数据分析与组织心理学方向。每套数据可直接进入 7 步向导完成分析与论文输出。"
            )
            _hr_specs = list_hr_datasets()
            for i in range(0, len(_hr_specs), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j >= len(_hr_specs):
                        break
                    spec = _hr_specs[i + j]
                    with col:
                        if st.button(
                            spec["title"],
                            width="stretch",
                            help=spec["description"],
                            key=f"hr_demo_{spec['key']}",
                        ):
                            demo_df = spec["loader"]()
                            wiz.df = demo_df
                            wiz.meta = {
                                "source_type": "csv",
                                "row_count": len(demo_df),
                                "col_count": len(demo_df.columns),
                                "file_name": f"demo_hr_{spec['key']}.csv",
                            }
                            wiz.inspector = inspect_dataframe(demo_df)
                            wiz.file_name = f"demo_hr_{spec['key']}.csv"
                            wiz.analysis_output = None
                            wiz.plan = None
                            wiz_data["data_loaded"] = True
                            wiz_data["is_demo"] = True
                            wiz_data["is_hr_demo"] = True
                            st.success(
                                f"✅ 已加载 {spec['title']} "
                                f"({len(demo_df)} 行, {len(demo_df.columns)} 列)"
                            )
                            st.rerun()
            st.markdown(
                "**📚 推荐分析方法**\n"
                "- 敬业度调研 → Cronbach α、EFA、回归（敬业度→离职意愿）、ANOVA（部门差异）\n"
                "- 培训项目 → 配对 t、独立 t、ANCOVA（控制前测）\n"
                "- 离职预测 → 卡方、Logistic 回归（需扩展）\n"
                "- 360 评估 → ICC、配对 t（自评 vs 他评偏差）"
            )

        st.divider()

        # 最近数据集快照（可一键恢复）
        from src.utils.recent_files import load_index, save_dataset, restore_dataset, clear_all
        recent = load_index()
        if recent:
            with st.expander("📂 最近使用的数据集（点击可恢复）", expanded=False):
                for rf in recent:
                    cols_hint = "、".join(rf.get("columns", [])[:5])
                    shape = rf.get("shape", [0, 0])
                    col1, col2 = st.columns([4, 1])
                    col1.caption(
                        f"**{rf.get('display_name', '?')}** — "
                        f"{shape[0]}行×{shape[1]}列 — "
                        f"{rf.get('created_at', '')}\n\n"
                        f"列: {cols_hint or '—'}"
                    )
                    if col2.button("恢复", key=f"restore_{rf['dataset_id']}"):
                        restored_df = restore_dataset(rf["dataset_id"])
                        if restored_df is not None:
                            wiz.df = restored_df
                            wiz.file_name = rf.get("display_name", "restored")
                            wiz.meta = {"row_count": len(restored_df), "col_count": len(restored_df.columns)}
                            wiz.inspector = inspect_dataframe(restored_df)
                            wiz.analysis_output = None
                            wiz.plan = None
                            wiz_data["data_loaded"] = True
                            st.rerun()
                if st.button("🗑️ 清除所有最近数据", key="clear_recent_datasets"):
                    clear_all()
                    st.rerun()

        uploaded_file = st.file_uploader(
            "拖拽数据文件到此处或点击上传",
            type=["csv", "xlsx", "xls", "sav", "json", "jsonl", "docx", "md", "markdown"],
            help="支持 CSV、Excel (.xlsx/.xls)、SPSS (.sav)、jsPsych (.json/.jsonl)、Word 表格 (.docx)、Markdown 表格 (.md) 格式",
            key="wizard_file_uploader",
        )

        if uploaded_file is not None:
            current_name = uploaded_file.name
            if current_name != wiz.file_name:
                wiz.file_name = current_name
                try:
                    with st.spinner("正在加载数据..."):
                        df, meta = load_data(uploaded_file)
                        wiz.df = df
                        wiz.meta = meta
                        wiz.inspector = inspect_dataframe(df)
                        wiz.analysis_output = None
                        wiz.plan = None
                        wiz_data["data_loaded"] = True
                        save_dataset(df, current_name)
                except Exception as e:
                    st.error(f"❌ 数据加载失败：{e}")
                    wiz.df = None

        if wiz.df is not None:
            meta = wiz.meta
            st.success(
                f"✅ 已加载：{wiz.file_name} | "
                f"行数：{meta.get('row_count', '?')} | 列数：{meta.get('col_count', '?')}"
            )
            with st.expander("📋 数据预览（前10行）"):
                st.dataframe(wiz.df.head(10), width="stretch")

            # v3.9 U5: PII 隐私风险检测
            render_pii_warning(wiz.df)

            # v3.9 N9: jsPsych 长→宽 auto-pivot
            if meta.get("source_type") == "jspsych_json":
                _render_jspsych_pivot_panel(wiz)

        st.divider()
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("⬅️ 上一步", width="stretch"):
                wiz.undergrad_step = 1
                st.rerun()
        with col_right:
            if st.button("下一步 ➡️", type="primary", width="stretch"):
                if wiz.df is None:
                    st.error("请先上传数据文件！")
                else:
                    wiz.undergrad_step = 3
                    st.rerun()

    # ================================================================
    # 步骤 3: 查看数据
    # ================================================================
    elif step == 3:
        st.subheader("🔍 第3步：查看数据结构")
        st.caption("系统已自动识别你的变量类型。请确认变量识别是否正确。")

        df = wiz.df
        inspector = wiz.inspector

        var_data = []
        for col, info in inspector.items():
            var_data.append({
                "变量名": col,
                "类型": VAR_ROLE_LABELS.get(info["type"], info["type"]),
                "非缺失值": info.get("n_valid", info.get("n", "?")),
                "缺失值": info.get("n_missing", 0),
                "唯一值数": info.get("n_unique", "?"),
            })
        st.dataframe(pd.DataFrame(var_data), width="stretch")

        numeric_cols = [c for c, info in inspector.items()
                       if info.get("type") in ("continuous", "numeric", "float", "int")]
        if numeric_cols:
            with st.expander("📊 描述性统计（数值变量）"):
                st.dataframe(df[numeric_cols].describe(), width="stretch")

        cat_cols = [c for c, info in inspector.items()
                    if info.get("type") in ("categorical", "object", "string", "str")]
        if cat_cols:
            with st.expander("📊 分类变量分布"):
                for col in cat_cols:
                    st.markdown(f"**{col}**")
                    st.dataframe(df[col].value_counts().reset_index(), width="stretch")

        issues = validate_data(df)
        if issues:
            with st.expander("⚠️ 数据质量提醒", expanded=True):
                for issue in issues:
                    st.warning(issue)

        # ── 数据清洗向导（v2.7 新增）──
        st.divider()
        with st.expander("🧹 数据清洗助手（缺失值/常数列/异常值一键处理）", expanded=False):
            st.caption(
                "按系统检测到的问题逐项处理，每步可撤销。"
                "处理日志会自动写入论文方法部分。"
            )
            cleaned_df, clean_log = render_cleaning_wizard(df, key_prefix="wiz_clean")
            # 同步清洗结果到向导主 df
            if clean_log and len(clean_log) > 0:
                wiz.df = cleaned_df
                wiz_data["df"] = cleaned_df
                wiz_data["cleaning_log_md"] = cleaning_log_to_method_paragraph(clean_log)

        st.divider()
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("⬅️ 上一步", width="stretch", key="step3_back"):
                wiz.undergrad_step = 2
                st.rerun()
        with col_right:
            if st.button("下一步 ➡️", type="primary", width="stretch", key="step3_next"):
                wiz.undergrad_step = 4
                st.rerun()

    # ================================================================
    # 步骤 4: 选择分析方法
    # ================================================================
    elif step == 4:
        st.subheader("🧠 第4步：选择分析方法")
        st.caption("根据你的研究问题，系统会推荐合适的统计方法。你也可以手动选择。")

        df = wiz.df
        inspector = wiz.inspector

        st.markdown("#### 🎯 方法选择助手")

        numeric_cols = [c for c, info in inspector.items()
                       if info.get("type") in ("continuous", "numeric", "float", "int")]
        cat_cols = [c for c, info in inspector.items()
                    if info.get("type") in ("categorical", "object", "string", "str")]

        col_q1, col_q2 = st.columns(2)
        with col_q1:
            analysis_goal = st.selectbox(
                "你的研究目的是什么？",
                [
                    "比较组间差异",
                    "分析变量间关系",
                    "检验前后变化",
                    "检验分布差异",
                    "检验中介/间接效应",
                    "检验调节效应",
                    "探索潜在维度（因素分析）",
                    "检验量表信度",
                    "检验类别变量关联",
                ],
                key="analysis_goal",
            )
        with col_q2:
            if analysis_goal == "比较组间差异":
                n_groups = st.selectbox(
                    "有几组需要比较？",
                    ["两组", "三组及以上"],
                    key="n_groups",
                )
            elif analysis_goal == "分析变量间关系":
                relationship_type = st.selectbox(
                    "变量类型？",
                    ["两个连续变量", "连续变量 + 二分变量", "多个连续变量（控制第三变量）"],
                    key="relationship_type",
                )
            elif analysis_goal == "检验分布差异":
                n_groups = st.selectbox(
                    "有几组需要比较？",
                    ["两组", "三组及以上"],
                    key="n_groups_nonpar",
                )

        st.divider()
        st.markdown("#### 💡 推荐分析方法")

        recommended = None
        if analysis_goal == "比较组间差异":
            if cat_cols and numeric_cols:
                if n_groups == "两组":
                    recommended = "independent_ttest"
                    st.success("🎯 **推荐：独立样本 t 检验**")
                    st.markdown("""
                    **适用条件**: 比较两组在连续变量上的均值差异（如：男生 vs 女生的焦虑分数）
                    **前提假设**: 正态性 + 方差齐性（系统将自动检验）
                    """)
                else:
                    recommended = "one_way_anova"
                    st.success("🎯 **推荐：单因素方差分析 (One-Way ANOVA)**")
                    st.markdown("""
                    **适用条件**: 比较多组在连续变量上的均值差异（如：大一/大二/大三的学业成绩）
                    **前提假设**: 正态性 + 方差齐性（系统将自动检验）
                    """)
            else:
                st.warning("⚠️ 你的数据中可能缺少分类变量或连续变量，请回到第3步确认变量类型。")

        elif analysis_goal == "分析变量间关系":
            if relationship_type == "两个连续变量":
                recommended = "pearson_corr"
                st.success("🎯 **推荐：Pearson 相关分析**")
                st.markdown("""
                **适用条件**: 分析两个连续变量的线性关系（如：自尊与生活满意度的关系）
                **注意事项**: 相关 ≠ 因果！
                """)
            elif relationship_type == "连续变量 + 二分变量":
                recommended = "point_biserial"
                st.success("🎯 **推荐：点二列相关**")
                st.markdown("""
                **适用条件**: 分析一个连续变量与一个二分变量的关系（如：性别与数学成绩的关系）
                """)
            else:
                recommended = "partial_corr"
                st.success("🎯 **推荐：偏相关分析**")
                st.markdown("""
                **适用条件**: 在控制第三个变量的影响下，分析两个变量的净相关
                """)
        elif analysis_goal == "检验前后变化":
            recommended = "paired_ttest"
            st.success("🎯 **推荐：配对样本 t 检验**")
            st.markdown("""
            **适用条件**: 同一组被试前后两次测量的差异（如：干预前后的焦虑水平）
            """)
        elif analysis_goal == "检验分布差异":
            if n_groups == "两组":
                recommended = "mann_whitney"
                st.success("🎯 **推荐：Mann-Whitney U 检验**")
                st.markdown("**适用条件**: 非正态数据的两组比较（非参数检验）")
            else:
                recommended = "kruskal_wallis"
                st.success("🎯 **推荐：Kruskal-Wallis H 检验**")
                st.markdown("**适用条件**: 非正态数据的多组比较（非参数检验）")

        elif analysis_goal == "检验中介/间接效应":
            recommended = "mediation"
            st.success("🎯 **推荐：中介效应分析**")
            st.markdown("""
            **适用条件**: 你想检验自变量(X)是否通过中间变量(M)影响因变量(Y)。
            例如：压力是否通过降低睡眠质量进而影响学习成绩？
            **要求**: X、M、Y 均为连续变量，且理论上存在因果时序关系。
            """)

        elif analysis_goal == "检验调节效应":
            recommended = "moderation"
            st.success("🎯 **推荐：调节效应分析**")
            st.markdown("""
            **适用条件**: 你想检验某个变量(W)是否会加强或减弱X对Y的影响。
            例如：社会支持是否缓冲了压力对抑郁的影响？
            **输出**: 交互效应显著性 + 简单斜率检验。
            """)

        elif analysis_goal == "探索潜在维度（因素分析）":
            recommended = "efa"
            st.success("🎯 **推荐：探索性因素分析 (EFA)**")
            st.markdown("""
            **适用条件**: 你有一组题目/指标，想知道它们背后属于几个潜在维度。
            例如：20道焦虑题目是否能分为"认知焦虑"和"躯体焦虑"两个维度？
            **前提**: KMO > 0.6, Bartlett 球形检验显著。
            """)

        elif analysis_goal == "检验量表信度":
            recommended = "cronbach_alpha"
            st.success("🎯 **推荐：Cronbach's α 信度分析**")
            st.markdown("""
            **适用条件**: 你想检验一组题目是否稳定地测量了同一个概念。
            **输出**: α系数 + 各题删除后的α变化 + 题总相关。
            - α ≥ 0.9: 优秀
            - 0.8 ≤ α < 0.9: 良好
            - 0.7 ≤ α < 0.8: 可接受
            - α < 0.7: 需修订
            """)

        elif analysis_goal == "检验类别变量关联":
            recommended = "chi_square"
            st.success("🎯 **推荐：卡方检验 (χ²)**")
            st.markdown("""
            **适用条件**: 你的自变量和因变量都是类别变量（如：性别 × 是否通过考试）。
            **输出**: χ²值 + 列联系数或Cramér's V效应量。
            **示例**: 不同年级学生的挂科率是否有差异？
            """)

        with st.expander("🔧 更多分析方法（高级）"):
            st.markdown("""
            如果你需要使用更高级的分析方法，请根据需要选择：
            - **信度分析 (Cronbach's α)**：检验量表内部一致性
            - **偏相关**：控制第三变量的相关分析
            - **多因素方差分析**：两个及以上自变量的分析
            - **重复测量方差分析**：同一被试多次测量的分析
            - **中介效应分析**：分析变量间的间接影响路径
            - **调节效应分析**：分析调节变量对主效应的增强/减弱
            - **探索性因素分析 (EFA)**：检验量表结构效度
            - **元分析**：合并多项研究的效应量
            - **HLM 多层线性模型**：嵌套数据的分析（如学生→班级→学校）
            """)

        wiz_data["recommended_method"] = recommended

        # v3.3 跨模块语义对齐警告（不阻塞）
        if recommended:
            from src.upstream.semantic_alignment import check_alignment
            from src.utils.workspace import get_upstream_state as _gus
            _upstream = _gus(st.session_state)
            _research_q = (
                _upstream.get("research_question")
                or wiz_data.get("research_q", "")
            )
            _candidate_vars = _upstream.get("candidate_vars") or {}
            # 若 upstream 候选变量为空，尝试从 wiz_data 提取
            if not _candidate_vars.get("dependent_vars") and wiz_data.get("dv"):
                _candidate_vars = {
                    "dependent_vars": [wiz_data.get("dv", "")],
                    "independent_vars": [wiz_data.get("iv", "")],
                    "grouping_var": wiz_data.get("iv", ""),
                    "covariates": [],
                }
            _alignment = check_alignment(_research_q, _candidate_vars, recommended)
            if not _alignment.is_aligned:
                with st.container():
                    st.markdown(
                        """<div style="background:#fff3cd;border-left:4px solid #ff9800;
                        padding:12px 16px;border-radius:6px;margin:12px 0;">
                        <strong>⚠️ 语义对齐提醒（不阻塞，仅供参考）</strong>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    for w in _alignment.warnings:
                        emoji = "⚠️" if w.severity == "warning" else "💡"
                        st.markdown(f"{emoji} **{w.issue}**\n\n建议：{w.suggestion}")

        st.divider()
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if st.button("⬅️ 上一步", width="stretch", key="step4_back"):
                wiz.undergrad_step = 3
                st.rerun()
        with col_right:
            if st.button("下一步 ➡️", type="primary", width="stretch", key="step4_next"):
                wiz.undergrad_step = 5
                st.rerun()

    # ================================================================
    # 步骤 5: 运行分析
    # ================================================================
    elif step == 5:
        st.subheader("⚙️ 第5步：配置并运行分析")
        st.caption("确认分析设置，点击运行。")

        df = wiz.df
        inspector = wiz.inspector
        recommended = wiz_data.get("recommended_method")

        numeric_cols = [c for c, info in inspector.items()
                       if info.get("type") in ("continuous", "numeric", "float", "int")]
        cat_cols = [c for c, info in inspector.items()
                    if info.get("type") in ("categorical", "object", "string", "str")]

        col_dv, col_iv = st.columns(2)
        with col_dv:
            selected_dv = st.selectbox(
                "选择因变量 (DV) / 分析变量",
                numeric_cols if numeric_cols else ["（未检测到数值变量）"],
                key="wiz_dv",
            )
        with col_iv:
            if recommended in ("independent_ttest", "one_way_anova", "mann_whitney", "kruskal_wallis"):
                selected_iv = st.selectbox(
                    "选择分组变量 (IV)",
                    cat_cols if cat_cols else ["（未检测到分类变量）"],
                    key="wiz_iv",
                )
            elif recommended in ("pearson_corr", "partial_corr"):
                additional_vars = st.multiselect(
                    "选择要分析的变量（至少2个）",
                    numeric_cols,
                    default=numeric_cols[:min(2, len(numeric_cols))] if numeric_cols else [],
                    key="wiz_corr_vars",
                )

        with st.expander("⚙ 高级分析选项"):
            confidence = st.slider("置信水平", 0.80, 0.99, 0.95, 0.01, key="wiz_confidence")

        st.divider()
        st.markdown("#### 📋 分析配置摘要")
        config_lines = [f"- **推荐方法**: {get_test_name(recommended)}"]
        if selected_dv:
            config_lines.append(f"- **因变量**: {selected_dv}")
        if recommended in ("independent_ttest", "one_way_anova", "mann_whitney", "kruskal_wallis") and cat_cols:
            config_lines.append(f"- **分组变量**: {selected_iv}")
        if recommended in ("pearson_corr", "partial_corr") and "additional_vars" in dir():
            config_lines.append(f"- **分析变量**: {', '.join(additional_vars) if additional_vars else '（未选择）'}")
        config_lines.append(f"- **置信水平**: {confidence:.0%}")
        st.markdown("\n".join(config_lines))

        st.divider()
        col_left, col_mid, col_right = st.columns([1, 1, 1])
        with col_left:
            if st.button("⬅️ 上一步", width="stretch", key="step5_back"):
                wiz.undergrad_step = 4
                st.rerun()
        with col_mid:
            run_btn = st.button("🔍 运行分析", type="primary", width="stretch", key="step5_run")

        if run_btn:
            if not selected_dv or selected_dv == "（未检测到数值变量）":
                st.error("请选择因变量！")
            elif (recommended in ("independent_ttest", "one_way_anova", "mann_whitney", "kruskal_wallis")
                  and (not cat_cols or selected_iv == "（未检测到分类变量）")):
                st.error("请选择分组变量！")
            else:
                spinner_messages = {
                    "mediation": "运行 5000 次 Bootstrap 模拟检验间接效应，约 10–30 秒...",
                    "efa": "进行平行分析与因子提取，可能需要数十秒...",
                    "cfa": "拟合 CFA 模型并估计参数，请稍候...",
                    "moderation": "拟合调节模型并计算简单斜率...",
                    "hierarchical_regression": "依次拟合层次回归模型...",
                }
                spinner_text = spinner_messages.get(recommended, "正在分析...")
                with st.spinner(spinner_text):
                    if recommended in ("independent_ttest", "one_way_anova", "mann_whitney", "kruskal_wallis"):
                        request_text = f"比较 {selected_iv} 各组在 {selected_dv} 上的差异"
                    elif recommended == "pearson_corr":
                        corr_vars = additional_vars if "additional_vars" in dir() else numeric_cols[:2]
                        request_text = f"分析 {'、'.join(corr_vars)} 之间的相关性"
                    elif recommended == "paired_ttest":
                        request_text = f"比较 {selected_dv} 的前后测差异"
                    else:
                        request_text = f"对 {selected_dv} 进行 {recommended}"

                    plan = resolve_intent(df, request_text, col_info=inspector)
                    wiz.plan = plan
                    output = run_analysis(df, plan)
                    wiz.analysis_output = output
                    # 保存分析上下文，供第7步论文生成使用
                    wiz_data["wizard_results_context"] = {
                        "test_type": output.get("test_type", recommended),
                        "test_name_zh": output.get("test_name_zh", get_test_name(recommended)),
                        "sample_size": len(df),
                        "dv": selected_dv,
                        "iv": selected_iv if recommended in ("independent_ttest", "one_way_anova", "mann_whitney", "kruskal_wallis") else None,
                        "variables": list(df.columns),
                    }
                    wiz.undergrad_step = 6
                    # v3.0: 分析完成后触发 autosave（节流 30s）
                    try:
                        from src.utils.autosave import trigger_autosave
                        from src.utils.workspace import build_workspace_snapshot
                        trigger_autosave(st.session_state, build_workspace_snapshot)
                    except Exception:
                        pass
                    st.rerun()

    # ================================================================
    # 步骤 6: 查看结果与导出
    # ================================================================
    elif step == 6:
        st.subheader("📊 第6步：分析结果")
        st.caption("以下是你的分析结果。看不懂？展开「白话解读」获取通俗解释。")

        output = wiz.analysis_output
        plan = wiz.plan
        df = wiz.df

        if output is None:
            st.warning("⚠️ 尚未运行分析，请先回到第5步运行分析。")
            if st.button("⬅️ 返回第5步", width="stretch"):
                wiz.undergrad_step = 5
                st.rerun()
            st.stop()

        if plan is not None:
            test_name = get_test_name(plan.test_type)
            st.markdown(f"""
            <div class="info-box">
            <strong>🔬 分析方法：{test_name}</strong><br>
            识别关键词：{'、'.join(plan.parsed_keywords) if plan.parsed_keywords else '用户指定'}
            </div>
            """, unsafe_allow_html=True)

        for err in output.get("errors", []):
            if err["severity"] == "error":
                st.markdown(f'<div class="error-box">❌ {err["message"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="warning-box">⚠ {err["message"]}</div>', unsafe_allow_html=True)

        render_assumption_failure_guidance(output, plan, df)

        desc = output.get("descriptive")
        if desc is not None and not desc.empty:
            with st.expander("📊 描述性统计", expanded=True):
                st.dataframe(desc, width="stretch")

        assumptions = output.get("assumptions", {})
        if assumptions:
            with st.expander("🔬 假设检验（正态性、方差齐性等）"):
                for category, results in assumptions.items():
                    if isinstance(results, dict):
                        for name, r in results.items():
                            render_assumption(r, f"{category}: {name}")
                    else:
                        render_assumption(results, category)

        result = output.get("result")
        if result is not None:
            st.subheader(f"📈 {output.get('test_name_zh', '分析结果')}")
            summary = format_result_summary(output)
            if summary:
                st.markdown(f'<div class="info-box">{summary}</div>', unsafe_allow_html=True)
            render_result_table(result)

            # Phase 1.3: 假设违反路由建议横幅 + 事后样本量建议
            render_routing_banner(output, df=df, on_apply=None)
            render_post_hoc_power(output)

        with st.expander("💬 白话解读（点击展开）", expanded=True):
            interpretation = generate_interpretation(output)
            st.markdown(interpretation)

            st.divider()
            st.markdown("#### 📖 如何理解这些统计指标？")
            st.markdown("""
            <div style="font-size:0.9em; line-height:1.8;">
            <p><strong>p 值（显著性）</strong>：判断结果是否"显著"的指标。<br>
            &nbsp;&nbsp; ✅ <strong>p < 0.05</strong> → 结果显著，组间很可能真的存在差异<br>
            &nbsp;&nbsp; ❌ <strong>p ≥ 0.05</strong> → 结果不显著，组间差异可能是偶然的<br>
            <em>注意：p值不是"效应大小"，p值小不代表效应一定大。</em></p>

            <p><strong>效应量 (Effect Size)</strong>：衡量差异或关系的"大小"。<br>
            &nbsp;&nbsp; 📏 <strong>Cohen's d</strong>: 0.2=小, 0.5=中, 0.8=大<br>
            &nbsp;&nbsp; 📏 <strong>η² (eta-squared)</strong>: 0.01=小, 0.06=中, 0.14=大<br>
            &nbsp;&nbsp; 📏 <strong>r (相关系数)</strong>: 0.1=弱, 0.3=中, 0.5=强</p>

            <p><strong>置信区间 (CI)</strong>：真实效应量可能落在的范围。<br>
            &nbsp;&nbsp; 95% CI 表示：如果重复研究100次，约有95次的真实值落在这个区间内。</p>
            </div>
            """, unsafe_allow_html=True)

        charts_data = output.get("charts_data", {})
        if charts_data:
            st.subheader("📉 可视化图表")
            render_charts(
                charts_data, df,
                ctx=wiz_data.get("wizard_results_context", {}),
            )

            # v3.0: 第 6 步加 AI 助教，方便看完结果直接问
            _render_ai_tutor(
                output=output,
                ctx=wiz_data.get("wizard_results_context", {}),
                location="step6",
            )

            with st.expander("📖 图表阅读指南"):
                st.markdown("""
                <div style="font-size:0.9em; line-height:1.8;">
                <p><strong>📊 柱状图/箱线图</strong>：<br>
                - 柱子的高度代表均值，误差线代表95%置信区间<br>
                - 箱线图中的横线是中位数，盒子是中间50%数据范围</p>

                <p><strong>📈 散点图</strong>：<br>
                - 每个点代表一个被试<br>
                - 点的分布趋势显示了两个变量的关系方向和强度<br>
                - 如果点从坐下到右上分布，表明正相关</p>
                </div>
                """, unsafe_allow_html=True)

        reasoning = output.get("reasoning")
        if reasoning is not None:
            with st.expander("💭 为什么用这个分析方法？"):
                st.markdown(f"**选择 {reasoning.test_name_zh} 的原因：**")
                st.markdown(reasoning.why_this_test)
                if reasoning.interpretation_guide:
                    st.markdown("**🎓 教学式解读：**")
                    st.info(reasoning.interpretation_guide)

            if reasoning.learning_card is not None:
                card = reasoning.learning_card
                with st.expander("📖 方法学习卡片 — 学会这个方法，SPSS也能用", expanded=False):
                    tab_decision, tab_steps, tab_spss, tab_tips = st.tabs(
                        ["🧭 选择逻辑", "📋 通用步骤", "🖥️ SPSS操作", "⚠️ 避坑指南"]
                    )
                    with tab_decision:
                        st.markdown(card.decision_logic)
                    with tab_steps:
                        for step in card.methodology_steps:
                            st.markdown(step)
                    with tab_spss:
                        st.markdown(f"**菜单路径：** `{card.spss_path}`")
                        if card.spss_steps:
                            for i, s in enumerate(card.spss_steps, 1):
                                st.markdown(f"{i}. {s}")
                    with tab_tips:
                        if card.common_mistakes:
                            st.markdown("**常见误区：**")
                            for m in card.common_mistakes:
                                st.markdown(f"- ❌ {m}")
                        if card.key_concepts:
                            st.markdown("**关键概念：**")
                            for k, v in card.key_concepts.items():
                                st.markdown(f"- **{k}**：{v}")

        st.divider()
        st.subheader("📥 导出结果")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            if st.button("📥 导出分析报告 (HTML)", width="stretch", key="wiz_export_html"):
                export_html(output, df)
        with col_exp2:
            if st.button("📄 导出结果数据 (CSV)", width="stretch", key="wiz_export_csv"):
                export_csv(output)
        with col_exp3:
            if st.button("💾 保存分析快照", width="stretch", key="wiz_snapshot"):
                try:
                    from src.analysis.runner import export_snapshot
                    snap_path = export_snapshot(output)
                    snap_id = output.get("snapshot_id", "unknown")
                    st.success(f"✅ 分析快照已保存\\n`{snap_id}`")
                except Exception as e:
                    st.error(f"快照保存失败：{e}")

        with st.expander("⚠️ 学术诚信提醒（重要！）"):
            from src.version import APP_VERSION_LABEL
            st.markdown(f"""
            <div style="font-size:0.9em;">
            <h4>📝 使用本工具的研究者须知：</h4>
            <ol>
                <li><strong>理解你的分析</strong>：请确保你理解所使用统计方法的基本原理。如果不确定，请咨询导师或查阅教材。</li>
                <li><strong>正确报告结果</strong>：报告确切的 p 值和效应量，不要只写"p < 0.05"。</li>
                <li><strong>相关 ≠ 因果</strong>：相关分析只能说明两个变量有关联，不能推断因果关系。</li>
                <li><strong>避免 p-hacking</strong>：不要在分析后根据结果调整假设或选择性报告显著结果。</li>
                <li><strong>辅助工具声明</strong>：在论文中声明使用本工具辅助数据分析。示例声明：<br>
                <em>"本研究使用心理学研究工具 {APP_VERSION_LABEL} 进行数据整理和统计分析。"</em></li>
            </ol>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.subheader("🎯 接下来可以做什么？")
        suggestions = st.columns(4)
        with suggestions[0]:
            if st.button("✍️ 写入论文 → 第7步", type="primary", width="stretch", key="wiz_to_step7"):
                wiz.undergrad_step = 7
                st.rerun()
        with suggestions[1]:
            if st.button("🔄 运行其他分析", width="stretch", key="wiz_rerun"):
                wiz.undergrad_step = 4
                st.rerun()
        with suggestions[2]:
            if st.button("📝 进入论文写作", width="stretch", key="wiz_paper"):
                wiz.undergrad_mode = False
                wiz["_pending_undergrad_mode"] = False
                st.session_state.app_mode = "📝 论文写作"
                st.rerun()
        with suggestions[3]:
            if st.button("🔓 进入自由模式", width="stretch", key="wiz_free"):
                wiz.undergrad_mode = False
                wiz["_pending_undergrad_mode"] = False
                st.rerun()

        st.divider()
        col_left, _ = st.columns([1, 3])
        with col_left:
            if st.button("⬅️ 返回第5步", width="stretch", key="step6_back"):
                wiz.undergrad_step = 5
                st.rerun()

    # ================================================================
    # 步骤 7: 写入论文
    # ================================================================
    elif step == 7:
        st.subheader("✍️ 第7步：写论文方法+结果")
        st.caption(
            "系统首先生成一版草稿（统计量自动填入）。你可以在草稿基础上修改，"
            "或使用「✍️ 反问式审阅」让 AI 帮你发现遗漏和优化点。"
        )
        # v3.6 哲学统一提示
        st.info(
            "💡 **建议**：先自己写一稿或改一稿，再让 AI 审阅，而非让 AI 替你写。"
            "AI 反问能让你想得更清楚，AI 直接改写则会丢失你的写作风格与思路。"
        )

        # v3.0: 引导完成后的亮点提示（仅一次）
        try:
            from src.ui.onboarding import render_post_demo_highlight
            render_post_demo_highlight()
        except Exception:
            pass

        # v2.9: 未完成事项提醒（在交付包卡片之前）
        _render_unfinished_reminders()

        # v2.9: 论文交付包顶部卡片
        _render_delivery_package_top_card()

        output = wiz.analysis_output
        plan = wiz.plan
        ctx = wiz_data.get("wizard_results_context", {})

        if output is None:
            st.warning("⚠️ 尚未运行分析，请先回到第5步完成分析。")
            if st.button("⬅️ 返回第5步", width="stretch"):
                wiz.undergrad_step = 5
                st.rerun()
            st.stop()

        test_type = ctx.get("test_type", output.get("test_type", "unknown"))
        test_name = ctx.get("test_name_zh", output.get("test_name_zh", "未知"))
        sample_n = ctx.get("sample_size", "?")
        dv_name = ctx.get("dv", "因变量")
        iv_name = ctx.get("iv", "分组变量")

        # ── 提取统计量 ──
        result = output.get("result")
        stat_info = {}
        if test_type in ("independent_ttest", "paired_ttest"):
            if hasattr(result, "t_statistic"):
                stat_info["t"] = result.t_statistic
                stat_info["df"] = getattr(result, "df", sample_n - 2)
        elif test_type == "one_way_anova":
            if hasattr(result, "table") and result.table is not None:
                table = result.table
                if "F" in table.columns:
                    stat_info["F"] = table["F"].iloc[0] if len(table) > 0 else None
                    stat_info["df1"] = table.get("df", [None])[0] if "df" in table.columns else None
        elif test_type in ("pearson_corr", "spearman_corr", "partial_corr"):
            if hasattr(result, "corr_matrix") and result.corr_matrix is not None:
                cm = result.corr_matrix
                if hasattr(cm, "iloc"):
                    stat_info["r"] = cm.iloc[0, 1] if cm.shape[0] > 1 and cm.shape[1] > 1 else None

        p_value = output.get("p_value", getattr(result, "p_value", None) if result else None)
        effect_size = output.get("effect_size", getattr(result, "effect_size", None) if result else None)
        ci_lower = output.get("ci_lower", None)
        ci_upper = output.get("ci_upper", None)

        # ── 方法描述模板选择 ──
        method_templates = {
            "independent_ttest": "独立样本t检验",
            "paired_ttest": "配对样本t检验",
            "one_way_anova": "单因素方差分析 (One-Way ANOVA)",
            "pearson_corr": "Pearson相关分析",
            "spearman_corr": "Spearman秩相关分析",
            "partial_corr": "偏相关分析",
            "mann_whitney": "Mann-Whitney U检验",
            "kruskal_wallis": "Kruskal-Wallis H检验",
            "mediation": "Bootstrap中介效应分析",
            "moderation": "调节效应分析",
            "cronbach_alpha": "Cronbach's α信度分析",
            "efa": "探索性因素分析 (EFA)",
            "chi_square": "卡方检验 (χ²)",
        }

        st.markdown("#### 🔧 调整方法描述")
        selected_method_label = st.selectbox(
            "分析方法描述模板",
            list(method_templates.values()),
            index=list(method_templates.keys()).index(test_type) if test_type in method_templates else 0,
            key="paper_method_select",
        )

        # ── 补充研究信息 ──
        with st.expander("📝 补充研究背景信息（可选）"):
            paper_alpha = st.text_input(
                "显著性水平", value=".05",
                help="通常设为 .05",
            )
            paper_tail = st.selectbox(
                "检验方向", ["双侧检验", "单侧检验"],
                help="如无特殊理由，选双侧检验",
            )
            software_name = st.text_input(
                "统计软件名称与版本",
                value="SPSS 26.0",
                help="如实填写你计划使用的统计软件",
            )
            sample_desc = st.text_area(
                "被试描述",
                value=f"本研究共招募 {sample_n} 名被试。",
                height=60,
            )

        # ── 生成论文片段 ──
        st.divider()
        st.markdown("#### 📄 生成结果")

        tab_method, tab_result, tab_combined = st.tabs(["方法部分", "结果部分", "完整草稿"])

        with tab_method:
            # 构建方法段落
            tail_label = "双侧" if "双侧" in paper_tail else "单侧"
            cleaning_paragraph = wiz_data.get("cleaning_log_md", "")
            cleaning_text = f"\n\n{cleaning_paragraph}" if cleaning_paragraph else ""
            method_text = f"""### 数据分析方法

{sample_desc}所有数据分析使用 {software_name} 完成。{cleaning_text}

本研究采用{selected_method_label}，显著性水平设为 α = {paper_alpha}（{tail_label}）。在分析前，对数据进行了正态性检验和方差齐性检验（如适用）。效应量及其95%置信区间依据APA第7版标准报告。"""

            if test_type == "independent_ttest":
                method_text += f"""

以{iv_name}为自变量（分组变量），以{dv_name}为因变量，进行{selected_method_label}。"""
            elif test_type == "one_way_anova":
                method_text += f"""

以{iv_name}为自变量，以{dv_name}为因变量，进行{selected_method_label}。若方差分析显著，进一步采用Tukey HSD法进行事后多重比较。"""
            elif test_type in ("pearson_corr", "partial_corr"):
                method_text += f"""

对{dv_name}等变量进行{selected_method_label}，以检验变量间的关联程度。"""

            # 追加问卷/实验设计详情（若存在完整回流数据）
            q_design_full = wiz_data.get("questionnaire_design_full")
            if q_design_full and isinstance(q_design_full, dict):
                q_name = q_design_full.get("construct_name", "")
                q_items = q_design_full.get("items", [])
                q_dims = q_design_full.get("dimensions_used", [])
                q_scale = q_design_full.get("scale_config", {})
                q_points = q_scale.get("points", 5)
                q_anchors = q_scale.get("anchors", [])
                method_text += f"""

### 测量工具

本研究采用自编《{q_name}》量表进行测量。该量表共包含 {len(q_items)} 个题目，涵盖 {'、'.join(q_dims)} 共 {len(q_dims)} 个维度。采用 {q_points} 点 Likert 量表计分"""
                if q_anchors:
                    method_text += f"（{q_anchors[0]} 到 {q_anchors[-1]}）"
                method_text += "。"
                rev_items = [it.get("text", "") for it in q_items if it.get("reverse")]
                if rev_items:
                    method_text += f"其中第 {', '.join(str(i+1) for i, it in enumerate(q_items) if it.get('reverse'))} 题为反向计分题。"

            exp_design_full = wiz_data.get("experiment_design_full")
            if exp_design_full and hasattr(exp_design_full, "__dict__"):
                exp_type = getattr(exp_design_full, "design_type", "")
                exp_groups = getattr(exp_design_full, "groups", [])
                exp_procedure = getattr(exp_design_full, "procedure", "")
                if exp_type or exp_groups:
                    method_text += "\n\n### 实验设计\n\n"
                    method_text += f"本研究采用{exp_type or '实验'}设计。"
                    if exp_groups:
                        method_text += f"实验设置 {len(exp_groups)} 个条件组，分别为{'、'.join(exp_groups)}。"
                    if exp_procedure:
                        method_text += f"实验流程如下：{exp_procedure}"

            st.markdown(method_text)
            st.caption("💡 可复制上述文本到论文的「方法 → 数据分析策略」部分，根据实际情况修改。")

        with tab_result:
            # 构建结果段落
            result_text = f"### 结果\n\n"
            desc = output.get("descriptive")

            # 描述统计
            if desc is not None and not desc.empty:
                result_text += f"描述性统计结果见表1。\n\n"

            # 推断统计
            if stat_info.get("t") is not None:
                t_str = f"*t*({stat_info['df']}) = {stat_info['t']:.2f}"
                p_str = f"*p* = {p_value:.3f}" if p_value is not None else "*p* = ?"
                result_text += f"{selected_method_label}结果显示，{t_str}，{p_str}"
            elif stat_info.get("F") is not None:
                f_str = f"*F*({stat_info['df1']}, {sample_n}) = {stat_info['F']:.2f}"
                p_str = f"*p* = {p_value:.3f}" if p_value is not None else "*p* = ?"
                result_text += f"{selected_method_label}结果显示，{f_str}，{p_str}"
            elif stat_info.get("r") is not None:
                r_str = f"*r* = {stat_info['r']:.3f}"
                p_str = f"*p* = {p_value:.3f}" if p_value is not None else "*p* = ?"
                result_text += f"{selected_method_label}结果显示，{r_str}，{p_str}"
            else:
                p_str = f"*p* = {p_value:.3f}" if p_value is not None else "*p* = ?"
                result_text += f"{selected_method_label}结果显示，{p_str}"

            if effect_size is not None:
                es_str = f"{effect_size:.3f}" if isinstance(effect_size, (int, float)) else str(effect_size)
                result_text += f"，效应量 = {es_str}"

            if ci_lower is not None and ci_upper is not None:
                result_text += f"，95% CI [{ci_lower:.3f}, {ci_upper:.3f}]"

            result_text += "。\n"
            st.markdown(result_text, unsafe_allow_html=False)
            st.caption("💡 可复制上述文本到论文的「结果」部分。请根据实际统计量进行校对。")

        with tab_combined:
            full_draft = method_text + "\n\n---\n\n" + result_text
            st.markdown(full_draft)
            st.success("✅ 以上为完整的「方法 + 结果」初稿草稿，可直接复制到论文中。")

            # v3.9 O2: 持久化 method/result 文本到 wiz_data，让 paper-aware QA 能读到
            wiz_data["method_text"] = method_text
            wiz_data["result_text"] = result_text

            # ── v4.7: AI 增强论文生成（通过 workflow_service）──
            _render_ai_paper_generation(
                output=output, ctx=ctx, wiz_data=wiz_data,
            )

            # ── Word 一键导出 ──
            _render_docx_download(
                method_md=st.session_state.get("_ai_method_md", method_text),
                result_md=st.session_state.get("_ai_result_md", result_text),
                output=output,
                ctx=ctx,
                wiz_data=wiz_data,
            )

            # ── 图表批量 ZIP 导出（v2.8）──
            _render_figures_zip_download(output=output, ctx=ctx, wiz_data=wiz_data)

            # ── 图表收藏夹管理（v2.9）──
            _render_collection_manager()

            # ── 答辩问题模拟器 ──
            _render_defense_qa_section(plan=plan, output=output, ctx=ctx)

            # ── v3.9 O3: AI 痕迹检测（交稿前自检）──
            _render_ai_trace_check_section(default_draft=full_draft)

            # ── v3.0: AI 助教（第 7 步与第 6 步独立的对话历史）──
            _render_ai_tutor(output=output, ctx=ctx, location="step7")

            # ── v3.6 反问式审阅（推荐方式）──
            with st.expander("✍️ 反问式审阅（推荐：你写一稿，AI 追问）", expanded=True):
                _render_reviewer_mode(full_draft, ctx)

            # ── AI润色（直接替换，警示用法） ──
            with st.expander("✨ AI 润色（可直接替换，谨慎使用）", expanded=False):
                st.warning(
                    "⚠️ **此功能将直接改写你的文本**，可能不保留你的写作风格与思路。"
                    "建议优先使用上方「反问式审阅」——AI 给你建议，你保留作者地位。"
                    "如导师未明确要求，**慎用此模式**。"
                )
                from src.llm_gateway.active_config import get_active_llm_config as _gac_polish
                _polish_cfg = _gac_polish()
                has_llm = _polish_cfg is not None
                if not has_llm:
                    st.info(
                        "💡 在侧栏顶部「🤖 AI 模型」选一个预设后，可使用 AI 对草稿进行润色。"
                    )
                else:
                    st.markdown(
                        "点击下方按钮，AI 将对论文草稿进行润色：优化表达流畅度、"
                        "调整 APA7 格式措辞、统一术语。"
                    )
                    if "polished_draft" not in st.session_state:
                        st.session_state.polished_draft = None
                    if st.button("✨ 开始AI润色", type="secondary", width="stretch",
                                 key="polish_draft_btn"):
                        from src.utils.llm_timer import llm_status
                        with llm_status("AI 正在润色论文草稿"):
                            try:
                                import requests
                                api_url = _polish_cfg["base_url"]
                                api_key = _polish_cfg["api_key"]
                                model = _polish_cfg["model"]
                                payload = {
                                    "model": model,
                                    "messages": [
                                        {"role": "system", "content": "你是一位心理学学术写作专家，擅长APA第7版格式。请润色以下论文草稿的方法和结果部分，使其语言更流畅、更符合APA7风格、术语更规范。保持所有统计量数值不变，不要添加或删除数据。直接输出润色后的完整文本。"},
                                        {"role": "user", "content": f"请润色以下心理学论文的方法与结果草稿：\n\n{full_draft}"},
                                    ],
                                    "temperature": _polish_cfg["temperature"],
                                }
                                resp = requests.post(
                                    f"{api_url}/v1/chat/completions",
                                    json=payload,
                                    headers={"Authorization": f"Bearer {api_key}"},
                                    timeout=120,
                                )
                                if resp.status_code == 200:
                                    data = resp.json()
                                    st.session_state.polished_draft = data.get("choices", [{}])[0].get("message", {}).get("content", full_draft)
                                else:
                                    st.error(f"AI 服务返回错误: {resp.status_code}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"润色失败: {str(e)}")
                    if st.session_state.polished_draft is not None:
                        st.divider()
                        st.markdown("#### ✨ 润色后版本")
                        st.markdown(st.session_state.polished_draft)
                        st.success("💡 润色完成！请仔细核对统计量数值是否保持不变。")
                        if st.button("🔄 恢复原始版本", key="reset_polish"):
                            st.session_state.polished_draft = None
                            st.rerun()

        # ── 跳转到完整论文写作 ──
        st.divider()
        st.markdown("#### 📝 需要完整的论文初稿？")
        if st.button("📝 打开完整论文写作模块", type="secondary", width="stretch"):
            # 切换到标准模式并进入论文写作
            wiz.undergrad_mode = False
            wiz["_pending_undergrad_mode"] = False
            st.session_state.app_mode = "📝 论文写作"
            st.rerun()

        # ── v2.9: 下载历史 ──
        _render_download_history()

        # ── v3.5 文献综述工作台引用注入 ──
        st.divider()
        st.markdown("#### 📚 推荐参考文献")
        try:
            from src.utils.workspace import get_literature_review_state as _glrs
            _lr_state = _glrs(st.session_state)
            _lr_items_raw = _lr_state.get("literature_items") or []
            # 筛选已读 + 高相关
            _selected_lit = []
            for _raw in _lr_items_raw:
                if not isinstance(_raw, dict):
                    continue
                if _raw.get("reading_status") == "done" and float(_raw.get("relevance_score") or 0) >= 0.4:
                    _selected_lit.append(_raw)
            if _selected_lit:
                with st.container():
                    st.markdown(
                        f"""<div style="background:#e8f5e9;border-left:4px solid #43a047;
                        padding:10px 14px;border-radius:6px;margin:8px 0;">
                        <strong>📚 来自文献综述工作台</strong><br>
                        <span style="font-size:0.9em;color:#444;">
                        共 {len(_selected_lit)} 篇已读且相关度 ≥40% 的文献，可直接引入参考文献：
                        </span></div>""",
                        unsafe_allow_html=True,
                    )
                    if "lit_review_checked" not in wiz_data:
                        wiz_data["lit_review_checked"] = {}
                    for _i, _it in enumerate(_selected_lit):
                        _key = _it.get("key") or f"lr_{_i}"
                        _authors = _it.get("authors") or []
                        _first_author = _authors[0] if _authors else "Unknown"
                        _label = (
                            f"{_first_author} ({_it.get('year', '')}). {_it.get('title', '')[:80]}. "
                            f"*{_it.get('journal', '')}*."
                        )
                        if _it.get("doi"):
                            _label += f" https://doi.org/{_it['doi']}"
                        _checked = wiz_data["lit_review_checked"].get(_key, True)
                        _updated = st.checkbox(_label, value=_checked, key=f"lr_lit_{_key}")
                        wiz_data["lit_review_checked"][_key] = _updated
                    st.caption("提示：取消勾选可排除特定文献。下方还有基于变量自动匹配的预设文献库。")
        except Exception:
            pass

        with st.expander("📚 基于分析变量自动推荐文献（点击展开）", expanded=False):
            st.caption("系统根据你的分析变量自动匹配相关文献，勾选后可在论文中引用。")

            from src.paper_writer.literature_library import match_references, format_citation_apa7

            # 收集关键词
            search_keywords = list(ctx.get("variables", []))
            if ctx.get("dv"):
                search_keywords.append(ctx["dv"])
            if ctx.get("iv"):
                search_keywords.append(ctx["iv"])
            if test_type:
                search_keywords.append(test_type)
            # 添加常见中文/英文别名
            alias_map = {
                "independent_ttest": "t检验",
                "paired_ttest": "t检验",
                "one_way_anova": "方差分析",
                "pearson_corr": "相关分析",
                "spearman_corr": "相关分析",
                "mediation": "中介效应",
                "moderation": "调节效应",
                "cronbach_alpha": "信度分析",
                "efa": "因素分析",
                "chi_square": "卡方检验",
                "mann_whitney": "非参数检验",
                "kruskal_wallis": "非参数检验",
            }
            if test_type in alias_map:
                search_keywords.append(alias_map[test_type])

            # 去重
            search_keywords = list(dict.fromkeys(search_keywords))

            refs = match_references(search_keywords, top_n=5)

            if not refs:
                st.info(
                    "当前变量未匹配到预设文献。建议在 CNKI 或 Google Scholar 中"
                    f" 以「{'」「'.join(search_keywords[:3])}」为关键词检索相关文献。"
                )
            else:
                st.caption(f"共匹配到 {len(refs)} 条推荐文献（基于 {len(search_keywords)} 个关键词）")

                if "lit_checked" not in wiz_data:
                    wiz_data["lit_checked"] = {}

                for i, (matched_key, entry) in enumerate(refs):
                    ref_id = f"ref_{i}"
                    checked = wiz_data["lit_checked"].get(ref_id, False)
                    updated = st.checkbox(
                        format_citation_apa7(entry),
                        value=checked,
                        key=f"lit_{ref_id}",
                    )
                    wiz_data["lit_checked"][ref_id] = updated

                if any(wiz_data["lit_checked"].values()):
                    st.divider()
                    st.markdown("**已选文献（可直接复制到论文参考文献列表）：**")
                    selected_refs = []
                    for i, (matched_key, entry) in enumerate(refs):
                        if wiz_data["lit_checked"].get(f"ref_{i}"):
                            selected_refs.append(format_citation_apa7(entry))
                    st.code("\n\n".join(selected_refs), language=None)
                    st.caption("💡 APA 7th 格式要求参考文献按作者姓氏字母顺序排列，请自行调整。")

        # ── 学术诚信 ──
        with st.expander("⚠️ 使用提示"):
            st.markdown("""
            - 生成的段落为**初稿模板**，请仔细核对统计量数值是否正确
            - APA格式要求报告确切的p值（非仅 p < .05）
            - 效应量应附带95%置信区间
            - **请务必使用实际使用的统计软件名称替换模板中的软件名**
            - 论文中的表格编号（表1、表2等）需要根据实际排版调整
            """)

        st.divider()
        col_left, _ = st.columns([1, 3])
        with col_left:
            if st.button("⬅️ 返回第6步", width="stretch", key="step7_back"):
                wiz.undergrad_step = 6
                st.rerun()
