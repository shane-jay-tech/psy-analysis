"""Streamlit 渲染辅助函数 — 结果表、图表、导出"""
import base64
import io

import streamlit as st
import pandas as pd

from src.analysis.ttest import TTestResult
from src.analysis.anova import ANOVAResult
from src.analysis.correlation import CorrResult
from src.analysis.chi_square import ChiSquareResult
from src.analysis.reliability import ReliabilityResult
from src.analysis.cfa import CFAResult
from src.analysis.validity import ValidityResult
from src.questionnaire.ai_content_review import AIItemReviewResult
from src.visualization.charts import (
    bar_with_error, box_plot, scatter_with_regression,
    correlation_heatmap, distribution_plot, interaction_plot,
    scree_plot, qq_plot, forest_plot, mediation_diagram,
)
from src.visualization.paper_export import (
    to_paper_png, KaleidoMissingError, get_palette_label,
)
from src.utils.friendly_errors import render_friendly_error
from src.output.interpretation import generate_interpretation


def render_assumption(r, label: str):
    icon = "✅" if r.passed else "⚠"
    st.text(f"{icon} {label}: {r.message_zh}")
    if r.suggested_action:
        st.caption(f"   → {r.suggested_action}")


# ===========================================================================
# Phase 1.3 — 路由建议横幅 + 事后样本量建议
# ===========================================================================

def render_routing_banner(output: dict, df=None, on_apply=None):
    """渲染假设违反路由横幅（仅显示建议；切换需用户主动点击）。

    业界惯例（R afex / pingouin / JASP / SPSS）：跨族不静默切换。
    n<20 / n>5000 时禁用切换按钮（小/大样本假设检验不可信）。

    Args:
        output: run_analysis 返回的字典。
        df: 当前数据，仅用于点击应用时调起新检验（可选）。
        on_apply: 点击"按建议改跑"时的回调；签名 on_apply(new_test_type)；
            None 时只显示信息不渲染按钮。
    """
    routing = output.get("routing")
    if not routing:
        return

    has_sugg = routing.get("has_suggestion", False)
    hard_ok = routing.get("hard_route_allowed", True)
    reasons = routing.get("reasons", [])
    sugg_zh = routing.get("suggested_test_zh", "")
    sugg = routing.get("suggested_test", "")
    n = routing.get("sample_size", 0)

    # 没有建议且 hard_route_allowed=True → 不显示
    if not has_sugg and hard_ok:
        return

    if has_sugg:
        st.warning(
            f"⚠ **检测到假设违反 → 推荐改用「{sugg_zh}」**\n\n"
            + "\n".join(f"- {r}" for r in reasons)
            + "\n\n_本系统不会自动切换检验（业界惯例）。如确认理论上恰当，请点击下方按钮改跑。_"
        )
    if not hard_ok:
        hr_reason = routing.get("hard_route_reason", "")
        st.info(f"ℹ {hr_reason}")

    if has_sugg and hard_ok and on_apply is not None:
        if st.button(
            f"按建议改跑：{sugg_zh}",
            key=f"_route_apply_{sugg}_{n}",
            help="点击后将以建议的检验重新分析（不会修改原结果，但当前界面将更新）。",
        ):
            on_apply(sugg)


def render_post_hoc_power(output: dict):
    """渲染事后样本量建议（仅 power<0.80 时；不显示 achieved_power 数值）。

    Hoenig & Heisey 2001：post-hoc observed power 是循环论证 anti-pattern；
    仅显示 n_needed_for_080，并附 footnote 警示"非证据强度解读"。
    """
    ph = output.get("post_hoc_power")
    if not ph:
        return

    if ph.get("needs_more_n"):
        n_obs = ph.get("observed_n", 0)
        n_need = ph.get("n_needed_for_080", 0)
        eff = ph.get("observed_effect", 0.0)
        eff_name = ph.get("observed_effect_name", "")
        footnote = ph.get("footnote", "")
        st.info(
            f"💡 **样本量建议**：当前 n={n_obs}，"
            f"若想以 0.80 把握检出该效应（{eff_name}={eff}），"
            f"建议样本量 n≈{n_need}。\n\n"
            f"_{footnote}_"
        )
    elif ph.get("skipped_reason"):
        # 已达 0.80 时给一个简短确认（可选展示）
        with st.expander("样本量评估"):
            st.caption(ph["skipped_reason"])
            st.caption(ph.get("footnote", ""))


def render_result_table(result):
    if isinstance(result, TTestResult):
        if result.group_stats is not None:
            st.dataframe(result.group_stats, use_container_width=True)
        r_cols = st.columns(5)
        r_cols[0].metric("t", f"{result.t_statistic:.3f}")
        r_cols[1].metric("df", f"{result.df:.2f}")
        r_cols[2].metric("p", f"{result.p_value:.4f}")
        r_cols[3].metric("均值差", f"{result.mean_diff:.3f}")
        r_cols[4].metric(result.effect_size_name, f"{result.effect_size:.3f}")
        if result.is_welch:
            st.caption("⚠ 已使用Welch校正（方差不齐）")
        if result.assumption_equal_var:
            eq = result.assumption_equal_var
            if not eq.get("passed", True):
                st.warning(f"Levene：F={eq['statistic']}, p={eq['p_value']} — 方差不齐，已使用Welch校正。")

    elif isinstance(result, ANOVAResult):
        st.dataframe(result.table, use_container_width=True)
        st.metric(result.effect_size_name, f"{result.effect_size:.4f}")
        if result.post_hoc is not None and not result.post_hoc.empty:
            st.caption("事后多重比较 (Tukey HSD):")
            st.dataframe(result.post_hoc, use_container_width=True)
        if result.assumption_homogeneity and not result.assumption_homogeneity.get("passed", True):
            st.warning("⚠ 方差齐性假设未满足。建议 Welch ANOVA 或 Kruskal-Wallis。")

    elif isinstance(result, CorrResult):
        st.caption("显著性标记：\\*p<.05, \\*\\*p<.01, \\*\\*\\*p<.001")
        display = pd.DataFrame(index=result.corr_matrix.index, columns=result.corr_matrix.columns)
        for i in display.index:
            for j in display.columns:
                rv = result.corr_matrix.loc[i, j]
                sig = result.sig_mask.loc[i, j]
                if pd.notna(rv):
                    display.loc[i, j] = f"{rv:.3f}{sig}"
                else:
                    display.loc[i, j] = "-"
        st.dataframe(display, use_container_width=True)
        # Phase 1.3：显示 Fisher-z 95% CI 矩阵（仅在有 CI 时）
        ci_low = getattr(result, "ci_low_matrix", None)
        ci_high = getattr(result, "ci_high_matrix", None)
        if ci_low is not None and ci_high is not None:
            with st.expander("95% 置信区间（Fisher-z 变换）"):
                ci_display = pd.DataFrame(
                    index=result.corr_matrix.index,
                    columns=result.corr_matrix.columns,
                )
                for i in ci_display.index:
                    for j in ci_display.columns:
                        if i == j:
                            ci_display.loc[i, j] = "—"
                            continue
                        lo = ci_low.loc[i, j]
                        hi = ci_high.loc[i, j]
                        if pd.notna(lo) and pd.notna(hi):
                            ci_display.loc[i, j] = f"[{lo:.3f}, {hi:.3f}]"
                        else:
                            ci_display.loc[i, j] = "-"
                st.dataframe(ci_display, use_container_width=True)

    elif isinstance(result, ChiSquareResult):
        st.dataframe(result.contingency_table, use_container_width=True)
        r_cols = st.columns(4)
        r_cols[0].metric("χ²", f"{result.chi_sq:.3f}")
        r_cols[1].metric("df", str(result.df))
        r_cols[2].metric("p", f"{result.p_value:.4f}")
        # 显示效应量 + 95% CI（Phase 1.3 新增）
        es_text = f"{result.effect_size:.3f}"
        if (result.effect_size_ci_lower is not None
                and result.effect_size_ci_upper is not None):
            es_text += (
                f"\n95% CI [{result.effect_size_ci_lower:.3f}, "
                f"{result.effect_size_ci_upper:.3f}]"
            )
        r_cols[3].metric(result.effect_size_name, es_text)
        if result.warning:
            st.warning(result.warning)

    elif isinstance(result, ReliabilityResult):
        _render_reliability(result)

    elif isinstance(result, CFAResult):
        _render_cfa(result)

    elif isinstance(result, ValidityResult):
        _render_validity(result)

    elif isinstance(result, AIItemReviewResult):
        _render_ai_item_review(result)


def _render_reliability(r: ReliabilityResult):
    """渲染信度结果：主指标 + CI + 题目/因子明细表"""
    sym_map = {
        "cronbach_alpha": "α",
        "split_half": "SB-r",
        "mcdonald_omega": "ω",
        "composite_reliability": "CR",
        "icc": f"ICC ({r.icc_type})" if r.icc_type else "ICC",
        "test_retest": "r",
        "cohens_kappa": "κ",
        "fleiss_kappa": "Fleiss' κ",
    }
    sym = sym_map.get(r.test_type, "值")
    cols = st.columns(4)
    cols[0].metric(sym, f"{r.alpha:.3f}")
    cols[1].metric("95% CI 下限", f"{r.ci_lower:.3f}")
    cols[2].metric("95% CI 上限", f"{r.ci_upper:.3f}")
    cols[3].metric("样本量", str(r.n_cases))

    if r.test_type == "composite_reliability" and r.cr_per_factor:
        st.caption("**各因子组合信度：**")
        cr_df = pd.DataFrame([
            {"因子": f, "CR": cr, "评估": "✅ 合格" if cr >= 0.70 else "⚠ 偏低"}
            for f, cr in r.cr_per_factor.items()
        ])
        st.dataframe(cr_df, use_container_width=True)
        if r.item_stats is not None:
            st.caption("**因子载荷明细：**")
            st.dataframe(r.item_stats, use_container_width=True)
    elif r.item_stats is not None:
        st.caption("**题目分析：**")
        st.dataframe(r.item_stats, use_container_width=True)

    if r.warning:
        st.warning(r.warning)


def _render_cfa(r: CFAResult):
    """渲染 CFA：拟合卡片 + 载荷表 + AVE/CR per-factor + HTMT 矩阵"""
    if r.is_fallback:
        st.warning(r.fallback_note)
        if r.loadings is not None:
            st.dataframe(r.loadings, use_container_width=True)
        return

    # 拟合指标卡片
    fit_cols = st.columns(4)
    fit_cols[0].metric("CFI", f"{r.cfi:.3f}",
                       delta="≥.95 良好" if r.cfi >= 0.95 else ("≥.90 可接受" if r.cfi >= 0.90 else "偏低"))
    fit_cols[1].metric("TLI", f"{r.tli:.3f}",
                       delta="≥.95 良好" if r.tli >= 0.95 else ("≥.90 可接受" if r.tli >= 0.90 else "偏低"))
    fit_cols[2].metric("RMSEA", f"{r.rmsea:.3f}",
                       delta="≤.05 良好" if r.rmsea <= 0.05 else ("≤.08 可接受" if r.rmsea <= 0.08 else "偏高"),
                       delta_color="inverse")
    fit_cols[3].metric("SRMR", f"{r.srmr:.3f}",
                       delta="≤.05 良好" if r.srmr <= 0.05 else ("≤.08 可接受" if r.srmr <= 0.08 else "偏高"),
                       delta_color="inverse")

    sub_cols = st.columns(3)
    sub_cols[0].metric("χ²", f"{r.chi2:.3f}")
    sub_cols[1].metric("df", str(r.chi2_df))
    sub_cols[2].metric("p", f"{r.chi2_p:.4f}")

    if r.fit_summary_zh:
        if r.fit_good:
            st.success(r.fit_summary_zh)
        elif r.fit_acceptable:
            st.info(r.fit_summary_zh)
        else:
            st.warning(r.fit_summary_zh)

    # 因子载荷
    if r.loadings is not None and not r.loadings.empty:
        st.caption("**标准化因子载荷：**")
        st.dataframe(r.loadings, use_container_width=True)

    # AVE / CR per factor
    if r.ave_per_factor or r.cr_per_factor:
        rows = []
        for f in (r.ave_per_factor or {}).keys():
            ave = (r.ave_per_factor or {}).get(f, None)
            cr = (r.cr_per_factor or {}).get(f, None)
            rows.append({
                "因子": f,
                "AVE": ave if ave is not None else "-",
                "AVE 评估": ("✅" if ave is not None and ave >= 0.50 else "⚠") if ave is not None else "-",
                "CR": cr if cr is not None else "-",
                "CR 评估": ("✅" if cr is not None and cr >= 0.70 else "⚠") if cr is not None else "-",
            })
        if rows:
            st.caption("**聚合效度（AVE）与组合信度（CR）：**")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Fornell-Larcker 矩阵
    if r.fl_matrix is not None and not r.fl_matrix.empty:
        st.caption("**Fornell-Larcker 区分效度矩阵**（对角线为 √AVE，下三角为因子相关；带 ⚠ 表示违例）：")
        st.dataframe(r.fl_matrix, use_container_width=True)

    # HTMT 矩阵
    if r.htmt_matrix is not None and not r.htmt_matrix.empty:
        st.caption("**HTMT 矩阵**（异质-单质特征比，>0.85 警告）：")
        try:
            st.dataframe(r.htmt_matrix.style.applymap(_htmt_color, subset=pd.IndexSlice[:, r.htmt_matrix.columns[1:]]),
                         use_container_width=True)
        except Exception:
            st.dataframe(r.htmt_matrix, use_container_width=True)

    # 因子协方差
    if r.factor_cov is not None and not r.factor_cov.empty:
        st.caption("**因子间协方差/相关：**")
        st.dataframe(r.factor_cov, use_container_width=True)

    if r.warnings:
        for w in r.warnings:
            st.warning(w)


def _htmt_color(val):
    """HTMT 矩阵单元格条件着色"""
    try:
        v = float(val)
    except (ValueError, TypeError):
        return ""
    if v > 0.90:
        return "background-color:#fdd"
    if v > 0.85:
        return "background-color:#fff3cd"
    return ""


def _render_validity(r: ValidityResult):
    """渲染效度结果：主指标 + 明细表 + 解读"""
    if r.test_type == "cvi":
        st.metric("S-CVI/Ave", f"{r.main_value:.3f}",
                  delta=f"{r.n_cases} 位专家")
    elif r.test_type == "ave":
        st.metric("AVE 均值", f"{r.main_value:.3f}",
                  delta="≥0.50 合格" if r.main_value >= 0.50 else "偏低")
    elif r.test_type == "discriminant_fl":
        if r.fornell_larcker_pass:
            st.success("✅ Fornell-Larcker 区分效度通过")
        else:
            st.warning("⚠ Fornell-Larcker 区分效度未通过")
    elif r.test_type == "discriminant_htmt":
        st.metric("最大 HTMT", f"{r.main_value:.3f}",
                  delta="≤0.85 通过" if r.main_value <= 0.85 else "超阈值",
                  delta_color="inverse")
    elif r.test_type == "criterion_validity":
        cols = st.columns(4)
        cols[0].metric("r", f"{r.criterion_r:.3f}")
        cols[1].metric("p", f"{r.criterion_p:.4f}")
        cols[2].metric("n", str(r.n_cases))
        cols[3].metric("95% CI", f"[{r.criterion_ci_lower:.3f}, {r.criterion_ci_upper:.3f}]")
    elif r.test_type == "known_groups_validity":
        cols = st.columns(4)
        stat_sym = "t" if r.known_groups_test == "ttest" else "F"
        cols[0].metric(stat_sym, f"{r.known_groups_stat:.3f}")
        cols[1].metric("p", f"{r.known_groups_p:.4f}")
        cols[2].metric(r.known_groups_effect_name, f"{r.known_groups_effect_size:.3f}")
        cols[3].metric("n", str(r.n_cases))

    if r.detail is not None and not r.detail.empty:
        st.dataframe(r.detail, use_container_width=True)

    if r.interpretation:
        st.caption(r.interpretation)

    if r.warning:
        st.warning(r.warning)


def _render_ai_item_review(r: AIItemReviewResult):
    """渲染 AI 题目预审结果（v3.8）。

    ⚠ 此结果**非正式 CVI**，UI 顶部强提醒，并提供 Markdown 报告下载。
    """
    # ── 顶部 disclaimer ──
    st.error(
        "⚠️ **AI 模拟非正式 CVI**——本结果仅作题目修订预审，"
        "**不构成正式内容效度证据**，请送真领域专家确认后再写入论文方法学。"
    )

    # ── 元信息 ──
    meta_cols = st.columns(4)
    meta_cols[0].metric("题目数", r.n_items)
    meta_cols[1].metric("成功 persona", f"{r.n_personas_succeeded}/{r.n_personas}")

    n_pass = 0
    n_flagged = len(r.flagged_items)
    if r.items_table is not None and not r.items_table.empty:
        avg_series = pd.to_numeric(r.items_table["平均"], errors="coerce")
        n_pass = int((avg_series >= 3.0).sum())
    meta_cols[2].metric("平均 ≥3 题数", f"{n_pass}/{r.n_items}")
    meta_cols[3].metric("标记需修订", n_flagged,
                         delta_color="inverse")

    st.markdown(f"**构念**：{r.construct_name}")
    with st.expander("📖 用户提供定义", expanded=False):
        st.markdown(r.construct_definition)
    if r.kb_definition_used:
        with st.expander("📚 KB 参考定义（仅供对照）", expanded=False):
            st.markdown(r.kb_definition_used)

    # ── 评分表（高亮 flagged 行） ──
    if r.items_table is not None and not r.items_table.empty:
        st.markdown("### 题目级评分")
        flagged_set = set(r.flagged_items)

        def _highlight_flagged(row):
            if row["题目"] in flagged_set:
                return ["background-color: #fff4f4"] * len(row)
            return [""] * len(row)

        try:
            styled = r.items_table.style.apply(_highlight_flagged, axis=1)
            st.dataframe(styled, use_container_width=True)
        except Exception:
            st.dataframe(r.items_table, use_container_width=True)

    # ── 标记需修订 ──
    if r.flagged_items:
        with st.expander(f"⚠ 标记需修订的题目（{len(r.flagged_items)} 道）",
                          expanded=True):
            df = r.items_table
            for it in r.flagged_items:
                sub = df[df["题目"] == it]
                if sub.empty:
                    continue
                row = sub.iloc[0]
                avg = row.get("平均", "-")
                dis = row.get("分歧", "-")
                sug = row.get("改进建议", "")
                st.markdown(f"- **{it}** — 平均 {avg}，分歧 {dis}")
                if sug:
                    st.caption(f"  改进建议：{sug}")

    # ── Markdown 报告下载 ──
    if r.summary_markdown:
        from datetime import datetime
        fname_safe = (r.construct_name or "construct").replace("/", "_").replace(" ", "_")
        st.download_button(
            "📥 下载预审报告（Markdown）",
            data=r.summary_markdown.encode("utf-8"),
            file_name=f"ai_pre_review_{fname_safe}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
        )

    # ── 调用警告 ──
    if r.warnings:
        with st.expander("调用提示", expanded=False):
            for w in r.warnings:
                st.warning(w)


def render_charts(charts_data: dict, df: pd.DataFrame, ctx: dict = None):
    """渲染分析产生的图表，每张图下方提供论文版导出 + 加入收藏夹按钮。

    Args:
        charts_data: 来自 output["charts_data"] 的字典
        df: 原始数据
        ctx: 可选元信息（test_type, test_name_zh），用于收藏夹元数据
    """
    ctx = ctx or {}
    charts: list = []  # list of (fig, chart_type_zh, variables)
    if "box_data" in charts_data:
        bd = charts_data["box_data"]
        charts.append((
            box_plot(df, bd["dv"], bd["iv"], title=f"{bd['dv']} 分组箱线图"),
            "箱线图", [bd["dv"], bd["iv"]],
        ))
    if "corr_matrix" in charts_data:
        cm = charts_data["corr_matrix"]
        charts.append((
            correlation_heatmap(cm), "相关热力图",
            list(cm.columns) if hasattr(cm, "columns") else [],
        ))
    if "scatter_cols" in charts_data:
        cols = charts_data["scatter_cols"]
        if len(cols) >= 2:
            charts.append((
                scatter_with_regression(df, cols[0], cols[1], title=f"{cols[0]} vs {cols[1]}"),
                "散点图", cols[:2],
            ))
    if "bar_data" in charts_data:
        bd = charts_data["bar_data"]
        if isinstance(bd, pd.DataFrame) and "组别" in bd.columns:
            dv_name = charts_data.get("box_data", {}).get("dv", "因变量")
            iv_name = charts_data.get("box_data", {}).get("iv", "分组")
            charts.append((bar_with_error(bd, dv_name, iv_name), "柱状图", [dv_name, iv_name]))
    if "anova_result" in charts_data and "box_data" in charts_data:
        bd = charts_data["box_data"]
        charts.append((
            box_plot(df, bd["dv"], bd["iv"], title=f"{bd['dv']} 各组箱线图（ANOVA）"),
            "ANOVA箱线图", [bd["dv"], bd["iv"]],
        ))
    if "interaction_data" in charts_data:
        id_ = charts_data["interaction_data"]
        charts.append((
            interaction_plot(df, id_["dv"], id_["iv1"], id_["iv2"]),
            "交互图", [id_["dv"], id_["iv1"], id_["iv2"]],
        ))
    if "histogram_cols" in charts_data:
        for col in charts_data["histogram_cols"][:3]:
            if col in df.columns:
                charts.append((
                    distribution_plot(df, col, title=f"{col} 分布图"),
                    "分布图", [col],
                ))
    if "scree_data" in charts_data:
        eigen = charts_data["scree_data"]
        if isinstance(eigen, pd.DataFrame):
            charts.append((scree_plot(eigen, title="因素分析碎石图"), "碎石图", []))
    if "qq_col" in charts_data:
        col = charts_data["qq_col"]
        if col in df.columns:
            charts.append((qq_plot(df, col, title=f"{col} Q-Q 图"), "QQ图", [col]))
    if "forest_data" in charts_data:
        fd = charts_data["forest_data"]
        if isinstance(fd, pd.DataFrame):
            charts.append((forest_plot(fd, title="回归系数森林图"), "森林图", []))
    if "mediation_data" in charts_data:
        md = charts_data["mediation_data"]
        if isinstance(md, dict):
            coef = md.get("coef_table")
            ci = md.get("bootstrap_ci")
            if isinstance(coef, pd.DataFrame):
                charts.append((
                    mediation_diagram(coef, ci, title="中介效应路径图"),
                    "中介路径图", [],
                ))
    if "paired_cols" in charts_data:
        cols = charts_data["paired_cols"]
        if isinstance(cols, (list, tuple)) and len(cols) >= 2:
            charts.append((
                box_plot(df, cols[0], None, title=f"{cols[0]} 与 {cols[1]} 箱线图对比"),
                "配对箱线图", list(cols[:2]),
            ))

    if charts:
        interactive = st.session_state.get("interactive_charts", False)
        plotly_config = None if interactive else {"staticPlot": True}
        for i, (fig, chart_type, variables) in enumerate(charts):
            try:
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"chart_{i}")
                _render_paper_export_button(fig, idx=i)
                _render_add_to_collection_button(
                    fig, idx=i, chart_type=chart_type, variables=variables, ctx=ctx,
                )
            except Exception as e:
                render_friendly_error(st, e, show_technical=False)
    else:
        st.info("暂无适用的图表。")


def _render_add_to_collection_button(fig, idx: int, chart_type: str,
                                     variables: list, ctx: dict):
    """v2.9: 把图表加入论文图表集（收藏夹）。"""
    from src.utils.figure_collection import get_collection_from_session

    coll = get_collection_from_session(st.session_state)
    test_type = ctx.get("test_type", "unknown")
    test_name = ctx.get("test_name_zh", "分析")
    default_title = f"{test_name} - {chart_type}"
    if variables:
        default_title += f"（{', '.join(str(v) for v in variables[:2])}）"

    # 检查是否已收藏
    existing = coll.find_duplicate(
        test_type=test_type, variables=variables, chart_type=chart_type,
    )

    with st.expander(
        ("✅ 已加入论文图表集（点击修改备注）" if existing else "📌 加入论文图表集"),
        expanded=False,
    ):
        if existing:
            st.success(f"已收藏：{existing.title}")
            st.caption(f"加入时间：{existing.created_at}")
            new_note = st.text_area(
                "修改备注", value=existing.note,
                key=f"coll_note_edit_{idx}", height=80,
            )
            cols = st.columns(2)
            if cols[0].button("💾 保存备注", key=f"coll_save_note_{idx}"):
                coll.update_note(existing.figure_id, new_note)
                st.success("备注已更新")
            if cols[1].button("🗑️ 从收藏夹移除", key=f"coll_remove_{idx}"):
                coll.remove(existing.figure_id)
                st.rerun()
        else:
            title = st.text_input(
                "图表标题（可编辑）",
                value=default_title,
                key=f"coll_title_{idx}",
            )
            note = st.text_area(
                "备注（论文中如何使用、要点等）",
                value="", key=f"coll_note_{idx}", height=80,
                placeholder="例：用于展示实验组与控制组焦虑得分的差异分布",
            )
            if st.button("📌 加入论文图表集", type="primary",
                         key=f"coll_add_{idx}", use_container_width=True):
                coll.add(
                    title=title.strip() or default_title,
                    test_type=test_type,
                    variables=variables,
                    fig_object=fig,
                    note=note,
                    chart_type=chart_type,
                )
                # v3.0: 收藏后触发 autosave
                try:
                    from src.utils.autosave import trigger_autosave
                    from src.utils.workspace import build_workspace_snapshot
                    trigger_autosave(st.session_state, build_workspace_snapshot)
                except Exception:
                    pass
                st.rerun()
            st.caption(f"💡 当前收藏夹共 {len(coll)} 张图。")


def _render_paper_export_button(fig, idx: int):
    """在每个图表下方渲染论文版 PNG 下载控件（含配色选择）。"""
    with st.expander("💾 下载论文版图表（PNG 300dpi）", expanded=False):
        cols = st.columns([2, 1])
        palette = cols[0].radio(
            "学术配色",
            options=["grayscale", "color", "mono"],
            format_func=get_palette_label,
            horizontal=True,
            key=f"paper_palette_{idx}",
        )
        size_label = cols[1].selectbox(
            "尺寸",
            options=["6×4 英寸", "8×5 英寸", "5×3.5 英寸"],
            key=f"paper_size_{idx}",
        )
        size_map = {
            "6×4 英寸": (1800, 1200),
            "8×5 英寸": (2400, 1500),
            "5×3.5 英寸": (1500, 1050),
        }
        width_px, height_px = size_map[size_label]

        if st.button("生成 PNG", key=f"paper_gen_{idx}"):
            try:
                png_bytes = to_paper_png(
                    fig, palette=palette,
                    width_px=width_px, height_px=height_px,
                )
                st.download_button(
                    "⬇ 下载 PNG",
                    data=png_bytes,
                    file_name=f"figure_{idx + 1}_{palette}.png",
                    mime="image/png",
                    key=f"paper_dl_{idx}",
                )
                st.caption(f"已生成 {width_px}×{height_px} px PNG，可直接拖入 Word。")
            except KaleidoMissingError as e:
                st.error(str(e))
            except Exception as e:
                st.warning(f"导出失败：{e}")


def export_html(output: dict, df: pd.DataFrame):
    html_parts = [
        "<html><head><meta charset='utf-8'>",
        "<style>",
        "body { font-family: 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; }",
        "h1 { color: #2c3e50; } h2 { color: #2980b9; margin-top: 2rem; }",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { border: 1px solid #ddd; padding: 8px; } th { background: #f2f2f2; }",
        "</style></head><body>",
        f"<h1>心理学数据分析报告</h1>",
        f"<p>数据文件：{st.session_state.file_name}</p>",
        f"<p>分析需求：{output.get('plan', None).raw_request if output.get('plan') else ''}</p>",
    ]
    desc = output.get("descriptive")
    if desc is not None and not desc.empty:
        html_parts.append("<h2>描述性统计</h2>")
        html_parts.append(desc.to_html(index=False))
    interpretation = generate_interpretation(output)
    html_parts.append(f"<h2>结果解读</h2><p>{interpretation}</p>")
    html_parts.append("</body></html>")
    full_html = "\n".join(html_parts)
    b64 = base64.b64encode(full_html.encode("utf-8")).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="分析报告.html">点击下载 HTML 报告</a>'
    st.markdown(href, unsafe_allow_html=True)


def export_csv(output: dict):
    """导出分析结果的核心数据为 CSV 文件"""
    desc = output.get("descriptive")
    result = output.get("result")

    if desc is None and result is None:
        st.warning("没有可导出的数据。")
        return

    buf = io.StringIO()

    if desc is not None and not desc.empty:
        buf.write("# 描述性统计\n")
        buf.write(desc.to_csv(index=False))
        buf.write("\n")

    if result is not None:
        if isinstance(result, TTestResult):
            buf.write("\n# t检验结果\n")
            buf.write("t,df,p,均值差,效应量,效应量名称\n")
            buf.write(f"{result.t_statistic},{result.df},{result.p_value},{result.mean_diff},{result.effect_size},{result.effect_size_name}\n")
            if result.group_stats is not None:
                buf.write("\n# 分组描述\n")
                buf.write(result.group_stats.to_csv(index=False))
                buf.write("\n")

        elif isinstance(result, ANOVAResult):
            buf.write("\n# 方差分析表\n")
            buf.write(result.table.to_csv(index=False))
            buf.write("\n")
            buf.write(f"\n# 效应量,{result.effect_size_name},{result.effect_size}\n")
            if result.post_hoc is not None and not result.post_hoc.empty:
                buf.write("\n# 事后多重比较\n")
                buf.write(result.post_hoc.to_csv(index=False))
                buf.write("\n")

        elif isinstance(result, CorrResult):
            buf.write("\n# 相关矩阵 (r)\n")
            buf.write(result.corr_matrix.to_csv())
            buf.write("\n# 显著性矩阵 (p)\n")
            buf.write(result.p_matrix.to_csv())
            buf.write("\n# 显著性标记\n")
            buf.write(result.sig_mask.to_csv())

        elif isinstance(result, ChiSquareResult):
            buf.write("\n# 卡方检验结果\n")
            buf.write("χ²,df,p,效应量,效应量名称\n")
            buf.write(f"{result.chi_sq},{result.df},{result.p_value},{result.effect_size},{result.effect_size_name}\n")
            buf.write("\n# 列联表\n")
            buf.write(result.contingency_table.to_csv())
            buf.write("\n")

    csv_content = buf.getvalue()
    b64 = base64.b64encode(csv_content.encode("utf-8-sig")).decode()
    href = f'<a href="data:text/csv;charset=utf-8;base64,{b64}" download="分析结果.csv">点击下载 CSV 数据</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success("✅ CSV 数据已生成，可用 Excel 打开。")
