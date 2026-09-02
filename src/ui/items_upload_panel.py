"""上传现有题目工作流面板（v4.1）。

挂在 app.py "📋 问卷设计" 模式的子标签下，独立于 LLM 反向生成流程。

四步：
1. 上传题目文件（.md / .markdown / .docx / .txt）→ 自动解析
2. 编辑题目 / 反向题索引（st.data_editor）
3. 可选：调用 ai_content_review 跑 4 位模拟专家预审
4. 配置 Likert 锚点 → 下载 Word / PDF
"""

from __future__ import annotations

import io
from typing import List

import pandas as pd
import streamlit as st

from src.questionnaire.items_loader import (
    ItemsDoc,
    items_doc_from_lines,
    parse_items_file,
)


_DEFAULT_ANCHORS = {
    5: ["完全不符合", "比较不符合", "一般", "比较符合", "完全符合"],
    7: ["完全不符合", "不符合", "比较不符合", "一般", "比较符合", "符合", "完全符合"],
}


def render_items_upload_panel():
    """主入口：渲染整个"上传现有题目"面板。"""
    st.markdown("### 📤 上传你已有的题目，跑预审 + 排版导出")
    st.caption(
        "已经写好题目了？上传 `.md / .docx / .txt` 文件，系统帮你解析、可选预审、生成正式问卷文档。"
    )

    # Stage 1+2 范围提示
    st.info(
        "✅ 本期支持：上传 → 解析 → 可选 AI 预审 → 导出 Word / PDF\n\n"
        "⏳ 题库存档与后续被试数据按题号关联会在下一阶段开发。"
    )

    # ── Step 1: 上传 ──
    st.markdown("---")
    st.markdown("#### 第 1 步 · 上传题目文件")
    uploaded = st.file_uploader(
        "支持 .md / .markdown / .docx / .txt",
        type=["md", "markdown", "docx", "txt"],
        key="items_upload_file",
        help="文件中每行/每条为一道题；标题用 # 或文档首行；指导语放在标题与第一题之间；"
             "反向题在题目后加 (反向) / (R) / [R] 标注。",
    )

    parsed_doc: ItemsDoc = st.session_state.get("_items_doc_parsed")
    parse_err = None

    if uploaded is not None:
        # 文件变化时重新解析
        signature = (uploaded.name, getattr(uploaded, "size", 0))
        cached_sig = st.session_state.get("_items_doc_sig")
        if signature != cached_sig:
            try:
                parsed_doc = parse_items_file(uploaded, uploaded.name)
                st.session_state["_items_doc_parsed"] = parsed_doc
                st.session_state["_items_doc_sig"] = signature
            except ValueError as exc:
                parse_err = str(exc)
                st.session_state.pop("_items_doc_parsed", None)
                st.session_state.pop("_items_doc_sig", None)
                parsed_doc = None

    if parse_err:
        st.error(f"❌ 解析失败：{parse_err}")

    if parsed_doc is None:
        st.caption("📌 还没上传文件。试试在桌面准备一份 `.md`，每行一题，第一行是 `# 量表名`。")
        return

    # 解析摘要
    with st.expander("📋 解析结果摘要", expanded=True):
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("识别题数", parsed_doc.n_items())
        col_b.metric("反向题", parsed_doc.n_reverse())
        col_c.metric("格式", parsed_doc.source_format.upper())
        col_d.metric("字符数", sum(len(s) for s in parsed_doc.items))
        if parsed_doc.title:
            st.caption(f"📑 标题：**{parsed_doc.title}**")
        if parsed_doc.instructions:
            st.caption(f"📝 指导语：{parsed_doc.instructions}")
        if parsed_doc.raw_warnings:
            for w in parsed_doc.raw_warnings:
                st.warning(f"⚠️ {w}")

    # ── Step 2: 编辑题目 ──
    st.markdown("---")
    st.markdown("#### 第 2 步 · 检查 / 编辑题目")
    st.caption(
        "可以直接在表格里改题干，勾选反向题；本系统不修改你上传的原文件。\n\n"
        "**误识别为题目了？** 取消勾选「保留」即从问卷中删除该行；"
        "也可以右键单元格 → Delete row 或选中行后按 Delete 键。\n\n"
        "🔢 **删除后题号自动补位**：剩余题目会重新连续编号 1, 2, 3...，"
        "下游分维度评分、AI 预审、Word/PDF 导出都按补位后的「最终题号」走。"
    )

    df_items = pd.DataFrame({
        "保留": [True] * parsed_doc.n_items(),
        "原题号": list(range(1, parsed_doc.n_items() + 1)),
        "题干": parsed_doc.items,
        "反向": [i in parsed_doc.reverse_indices for i in range(parsed_doc.n_items())],
    })
    edited_df = st.data_editor(
        df_items,
        key="items_editor",
        num_rows="dynamic",
        column_config={
            "保留": st.column_config.CheckboxColumn(
                "保留",
                default=True,
                width="small",
                help="取消勾选即从问卷中删除此行（指导语被误识别为题目时常用）",
            ),
            "原题号": st.column_config.NumberColumn(
                "原题号",
                disabled=True,
                width="small",
                help="解析时的原始序号；删除「保留=否」的行后，下游会按最终题号 1..N 连续编号（见表格下方映射）",
            ),
            "题干": st.column_config.TextColumn("题干", width="large"),
            "反向": st.column_config.CheckboxColumn("反向题", width="small"),
        },
        hide_index=True,
    )

    title_input = st.text_input(
        "问卷标题", value=parsed_doc.title or "", key="items_title_input"
    )
    instr_input = st.text_area(
        "指导语",
        value=parsed_doc.instructions or "",
        height=80,
        key="items_instr_input",
        help="将印在问卷开头。建议简明告知作答方式与隐私承诺。",
    )

    # 从 editor 重建 ItemsDoc（保留=False 的行直接丢弃，剩余题目自动补位为 1..N）
    items_now: List[str] = []
    rev_now: List[int] = []
    mapping_rows: List[dict] = []  # 原题号 → 最终题号 映射，用于 UI 展示
    n_dropped_by_keep = 0
    for i in range(len(edited_df)):
        row = edited_df.iloc[i]
        keep = row.get("保留", True)
        is_dropped_by_keep = (
            keep is False or (isinstance(keep, float) and pd.isna(keep))
        )
        stem_raw = row.get("题干", "")
        stem = str(stem_raw or "").strip()
        orig_no = row.get("原题号")
        try:
            orig_no_int = int(orig_no) if orig_no is not None and not (
                isinstance(orig_no, float) and pd.isna(orig_no)
            ) else (i + 1)
        except (TypeError, ValueError):
            orig_no_int = i + 1

        if is_dropped_by_keep:
            n_dropped_by_keep += 1
            mapping_rows.append({
                "原题号": orig_no_int,
                "最终题号": "—（已删除）",
                "题干预览": (stem[:30] + "…") if len(stem) > 30 else (stem or "（空行）"),
            })
            continue
        if not stem:
            continue
        items_now.append(stem)
        mapping_rows.append({
            "原题号": orig_no_int,
            "最终题号": str(len(items_now)),
            "题干预览": (stem[:30] + "…") if len(stem) > 30 else stem,
        })
        if bool(row.get("反向", False)):
            rev_now.append(len(items_now) - 1)

    if n_dropped_by_keep > 0:
        st.caption(
            f"🗑️ 已移除 {n_dropped_by_keep} 行；剩余 {len(items_now)} 题已自动补位为最终题号 "
            f"1..{len(items_now)}。"
        )
        with st.expander(
            f"🔢 查看「原题号 → 最终题号」映射（共 {len(mapping_rows)} 行）",
            expanded=False,
        ):
            st.dataframe(
                pd.DataFrame(mapping_rows),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "📌 第 3 步分维度评分填题号、AI 预审、Word/PDF 导出都按「最终题号」走。"
            )

    current_doc = items_doc_from_lines(
        items_now,
        title=title_input,
        instructions=instr_input,
        reverse_indices=rev_now,
        source_format=parsed_doc.source_format,
    )
    st.session_state["_items_doc_current"] = current_doc

    if current_doc.n_items() == 0:
        st.error("当前没有有效题目。请回到第 1 步上传，或在表格中至少保留一行非空题干。")
        return

    # ── Step 3: AI 预审（可选）──
    st.markdown("---")
    st.markdown("#### 第 3 步 · AI 题目预审（可选）")
    enable_ai = st.checkbox(
        "用 4 位 AI 模拟专家给题目相关性打分（30-60 秒）",
        value=False,
        key="items_enable_ai_review",
        help="⚠️ 非正式 CVI，不可写入论文方法学；用作送真专家前的题目修订工具。",
    )

    if enable_ai:
        st.warning(
            "⚠️ **AI 模拟非正式 CVI**——4 位 persona 同模型相关接近 1.0，I-CVI/S-CVI 失去统计意义。"
            "结果只用于识别明显不对劲的题目。"
        )
        construct_name = st.text_input(
            "构念名（如：社交焦虑、工作满意度）",
            key="items_construct_name",
            placeholder="社交焦虑",
        )
        construct_def = st.text_area(
            "构念定义（建议 ≥ 50 字）",
            height=100,
            key="items_construct_def",
            placeholder="个体在社交场合感到不自在、担忧被他人评价的稳定情绪倾向...",
        )

        use_dim_mode = st.checkbox(
            "📐 分维度评分（适合多维度量表 / 融合理论 / 创新维度）",
            value=False,
            key="items_use_dim_mode",
            help="给每道题指定所属维度并填写维度定义。AI 会按"
                 "「题目 vs 所属维度」打分，且不会因维度新颖而扣分。",
        )

        dimensions_payload = None
        if use_dim_mode:
            dimensions_payload = _render_dimension_editor(current_doc)

        if st.button("🚀 运行 AI 预审", type="primary", key="items_run_ai_review"):
            if current_doc.n_items() < 3:
                st.error("至少需要 3 道题。")
            elif not construct_name.strip():
                st.error("请填写构念名。")
            elif len((construct_def or "").strip()) < 10:
                st.error("构念定义太短，请提供更详细的定义（建议 ≥ 50 字）。")
            elif use_dim_mode and not dimensions_payload:
                st.error("分维度模式已开启但维度配置无效，请检查维度名 / 定义 / 题号归属。")
            else:
                _run_ai_review(
                    current_doc, construct_name, construct_def,
                    dimensions=dimensions_payload,
                )

        last_review = st.session_state.get("_items_ai_review_result")
        if last_review is not None:
            _render_ai_review_result(last_review)

    # ── Step 4: Likert 锚点 + 导出 ──
    st.markdown("---")
    st.markdown("#### 第 4 步 · Likert 配置 → 导出问卷")

    col_pts, col_anchors = st.columns([1, 3])
    with col_pts:
        scale_points = st.selectbox(
            "Likert 点数", [4, 5, 6, 7], index=1, key="items_scale_points"
        )
    default_anchors = _DEFAULT_ANCHORS.get(
        scale_points, [str(i + 1) for i in range(scale_points)]
    )
    anchors_text = st.text_input(
        "锚点（用 / 分隔，从最低到最高）",
        value=" / ".join(default_anchors),
        key=f"items_anchors_{scale_points}",
        help="例：完全不符合 / 比较不符合 / 一般 / 比较符合 / 完全符合",
    )
    anchors_list = [s.strip() for s in anchors_text.split("/") if s.strip()]
    if len(anchors_list) != scale_points:
        st.warning(
            f"⚠️ 锚点数量 ({len(anchors_list)}) 与 Likert 点数 ({scale_points}) 不一致；"
            "导出时会按默认中文锚点处理。"
        )
        anchors_list = default_anchors

    with st.expander("更多元信息（可选，会印在标题下）", expanded=False):
        researcher = st.text_input("主试", key="items_meta_researcher")
        project = st.text_input("研究项目", key="items_meta_project")
        version = st.text_input("版本", key="items_meta_version", placeholder="v1.0")
        date = st.text_input("日期", key="items_meta_date", placeholder="2026-05-23")
    header_meta = {
        "researcher": researcher.strip() if researcher else "",
        "project": project.strip() if project else "",
        "version": version.strip() if version else "",
        "date": date.strip() if date else "",
    }
    if not any(header_meta.values()):
        header_meta = None

    show_id = st.checkbox(
        "在问卷头部打印「编号 / 性别 / 年龄 / 日期」填写区",
        value=True,
        key="items_show_id_field",
    )

    col_w, col_p = st.columns(2)
    with col_w:
        try:
            from src.output.docx_exporter import build_questionnaire_docx
            docx_bytes = build_questionnaire_docx(
                current_doc,
                scale_points=scale_points,
                anchors=anchors_list,
                header_meta=header_meta,
                show_id_field=show_id,
            )
            st.download_button(
                "📄 下载 Word",
                docx_bytes,
                file_name=_safe_filename(current_doc.title, "docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
            )
        except Exception as exc:
            st.error(f"Word 生成失败：{exc}")
    with col_p:
        try:
            from src.questionnaire.exporters import build_questionnaire_pdf
            pdf_bytes = build_questionnaire_pdf(
                current_doc,
                scale_points=scale_points,
                anchors=anchors_list,
                header_meta=header_meta,
                show_id_field=show_id,
            )
            st.download_button(
                "📕 下载 PDF",
                pdf_bytes,
                file_name=_safe_filename(current_doc.title, "pdf"),
                mime="application/pdf",
                width="stretch",
            )
        except RuntimeError as exc:
            st.warning(f"PDF 暂不可用：{exc}（请使用 Word 版本）")
        except Exception as exc:
            st.error(f"PDF 生成失败：{exc}")


def _safe_filename(title: str, ext: str) -> str:
    base = (title or "questionnaire").strip()
    # 去掉常见非法字符
    for ch in '\\/:*?"<>|\n\r\t':
        base = base.replace(ch, "_")
    return f"{base}.{ext}"


def _render_dimension_editor(doc: ItemsDoc):
    """渲染维度编辑器，返回校验通过的 dimensions payload，或 None。

    dimensions payload 结构（与 ai_content_review 接口对齐）::

        [{"name": str, "definition": str, "item_indices": List[int],
          "note": str}, ...]
    """
    n_items = doc.n_items()

    st.caption(
        "💡 **怎么填**：先在下表里增删维度行，每个维度填名字 + 定义；"
        "「题号」一栏写归属本维度的题号（**最终题号**，1-based，逗号分隔，例如 `1,2,3`）。"
        "「备注」可以写「本研究创新」等说明，AI 看到后不会因维度新颖压低分。\n\n"
        "📌 这里的题号 = 第 2 步删除「保留=否」的行之后，自动补位的连续编号 1..N。"
    )

    # ── v4.4 粘贴导入 ──
    with st.expander("📋 从文本快速导入维度（支持 Markdown 表格 / Excel 复制 / 段落键值）",
                     expanded=False):
        st.caption(
            "把外面准备好的维度结构粘贴进来，自动填到下方表里，再人工微调。\n\n"
            "**支持的格式（任选其一）**：\n"
            "- Markdown 表格：第一列维度名 / 第二列定义 / 第三列题号 / 第四列备注\n"
            "- Excel/Notion 直接复制（Tab 分隔）\n"
            "- 段落键值，例：`上级互动\\n定义：在上级面前的紧张感\\n题号：1,2`\n\n"
            "题号字段同时认：`1,2,3` / `1、2、3` / `1-3` / `题1, Q2`。"
        )
        with st.expander("看示例", expanded=False):
            st.code(
                "| 维度名 | 维度定义 | 题号 | 备注 |\n"
                "| --- | --- | --- | --- |\n"
                "| 上级互动 | 在上级面前的紧张感 | 1,2 | |\n"
                "| 客户回避 | 陌生客户的回避倾向 | 3 | |\n"
                "| 会议发言恐惧 | 公开发言的恐惧 | 4-6 | 本研究创新 |",
                language="markdown",
            )
        paste_text = st.text_area(
            "粘贴维度文本",
            height=160,
            key="_items_dim_paste_text",
            placeholder="把维度结构粘贴到这里…",
        )
        col_imp, col_clr = st.columns([1, 1])
        if col_imp.button(
            "📥 解析并导入到下方表格",
            key="_items_dim_paste_import_btn",
            disabled=not paste_text.strip(),
            type="primary",
            width="stretch",
        ):
            try:
                from src.questionnaire.dimensions_paste_parser import parse_dimensions_text
                df_parsed, parse_warnings = parse_dimensions_text(paste_text, n_items)
            except Exception as exc:
                st.error(f"解析失败：{exc}")
                df_parsed, parse_warnings = None, []
            if df_parsed is None or df_parsed.empty:
                for w in (parse_warnings or ["未能从粘贴文本中识别出任何维度"]):
                    st.error(f"⚠️ {w}")
            else:
                st.session_state["_items_dim_editor_rows"] = df_parsed
                # 强制 data_editor 重建（否则 widget 内部 state 会盖住默认值）
                st.session_state.pop("items_dim_editor", None)
                parser_used = df_parsed.attrs.get("parser", "")
                st.success(
                    f"✅ 已识别 {len(df_parsed)} 个维度（解析器：{parser_used}），"
                    "已填到下方表格，请检查并修改。"
                )
                for w in parse_warnings:
                    st.warning(f"⚠️ {w}")
                st.rerun()
        if col_clr.button(
            "🗑️ 清空表格回到一行",
            key="_items_dim_paste_clear_btn",
            width="stretch",
        ):
            st.session_state.pop("_items_dim_editor_rows", None)
            st.session_state.pop("items_dim_editor", None)
            st.rerun()

    # 默认值：尝试从 session_state 读，否则给一行空行
    default_rows = st.session_state.get("_items_dim_editor_rows")
    if default_rows is None:
        default_rows = pd.DataFrame({
            "维度名": ["维度1"],
            "维度定义": [""],
            "题号（1-based，逗号分隔）": [",".join(str(i) for i in range(1, n_items + 1))],
            "备注": [""],
        })
    edited = st.data_editor(
        default_rows,
        key="items_dim_editor",
        num_rows="dynamic",
        column_config={
            "维度名": st.column_config.TextColumn("维度名", width="medium"),
            "维度定义": st.column_config.TextColumn("维度定义", width="large"),
            "题号（1-based，逗号分隔）": st.column_config.TextColumn(
                "题号（1-based，逗号分隔）", width="medium"),
            "备注": st.column_config.TextColumn("备注（如：本研究创新）", width="medium"),
        },
        hide_index=True,
    )
    st.session_state["_items_dim_editor_rows"] = edited

    # 校验并组装 payload
    payload = []
    used_indices: set = set()
    errors: list = []
    indices_col = "题号（1-based，逗号分隔）"
    for r_idx in range(len(edited)):
        row = edited.iloc[r_idx]
        name = str(row.get("维度名", "") or "").strip()
        definition = str(row.get("维度定义", "") or "").strip()
        indices_text = str(row.get(indices_col, "") or "")
        note = str(row.get("备注", "") or "").strip()

        if not name and not definition and not indices_text:
            continue  # 整行空，跳过

        if not name:
            errors.append(f"第 {r_idx + 1} 行：维度名为空")
            continue
        if not definition:
            errors.append(f"维度【{name}】定义为空")
            continue

        idx_list_0based = []
        for tok in str(indices_text).replace("，", ",").split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                k = int(tok)
            except ValueError:
                errors.append(f"维度【{name}】题号「{tok}」不是整数")
                continue
            if k < 1 or k > n_items:
                errors.append(f"维度【{name}】题号 {k} 超出范围（1..{n_items}）")
                continue
            zero_based = k - 1
            if zero_based in used_indices:
                errors.append(f"题号 {k} 同时被多个维度归属")
                continue
            used_indices.add(zero_based)
            idx_list_0based.append(zero_based)

        if not idx_list_0based:
            errors.append(f"维度【{name}】没有任何归属题目")
            continue

        payload.append({
            "name": name,
            "definition": definition,
            "item_indices": idx_list_0based,
            "note": note,
        })

    n_assigned = len(used_indices)
    n_unassigned = n_items - n_assigned
    if n_unassigned > 0:
        st.info(
            f"📌 当前 {n_assigned}/{n_items} 题已归属维度，"
            f"剩余 {n_unassigned} 题未归属。"
            "未归属题目仍会评分但 AI 会按总构念判断。"
        )

    if errors:
        for e in errors:
            st.error(f"⚠️ {e}")
        return None

    if not payload:
        st.warning("还没有有效维度。请填写维度名 + 定义 + 题号。")
        return None

    return payload


def _run_ai_review(doc: ItemsDoc, construct_name: str, construct_def: str,
                   *, dimensions=None):
    """调用 ai_content_review 并把结果写入 session_state。"""
    try:
        from src.questionnaire.ai_content_review import ai_content_review
        from src.questionnaire.construct_kb import CONSTRUCTS
    except Exception as exc:
        st.error(f"AI 预审模块加载失败：{exc}")
        return

    kb_def = None
    try:
        rec = CONSTRUCTS.get(construct_name.strip())
        if rec:
            kb_def = rec.get("definition")
    except Exception:
        pass

    spinner_msg = (
        "4 位 AI 专家分维度评分（约 30-60 秒）..." if dimensions
        else "4 位 AI 专家串行评分（约 30-60 秒）..."
    )
    with st.spinner(spinner_msg):
        try:
            result = ai_content_review(
                items=doc.items,
                construct_name=construct_name.strip(),
                construct_definition=construct_def.strip(),
                kb_definition=kb_def,
                n_personas=4,
                dimensions=dimensions,
            )
            st.session_state["_items_ai_review_result"] = result
            st.success("✅ AI 预审完成")
        except Exception as exc:
            st.error(f"AI 预审失败：{exc}")
            st.session_state.pop("_items_ai_review_result", None)


def _render_ai_review_result(result):
    """简单展示 AIItemReviewResult。"""
    dim_summary = getattr(result, "dimension_summary", None)
    if isinstance(dim_summary, pd.DataFrame) and not dim_summary.empty:
        st.markdown("**📐 维度级摘要**")
        st.dataframe(dim_summary, hide_index=True, width="stretch")

    items_table = getattr(result, "items_table", None)
    if isinstance(items_table, pd.DataFrame) and not items_table.empty:
        st.markdown("**4 位 AI 专家评分汇总**")
        st.dataframe(items_table, hide_index=True, width="stretch")
    flagged = getattr(result, "flagged_items", []) or []
    if flagged:
        st.warning(f"⚠️ 标记需关注的题目（共 {len(flagged)} 题）：\n\n" +
                   "\n".join(f"- {s}" for s in flagged))
    summary_md = getattr(result, "summary_markdown", "")
    if summary_md:
        with st.expander("查看完整预审报告", expanded=False):
            st.markdown(summary_md)
