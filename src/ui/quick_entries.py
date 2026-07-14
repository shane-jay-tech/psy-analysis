"""智能默认首页：本科生最常用三大快捷入口

取代 28 种方法列表，展示：
1. 两组比较（t 检验 / Mann-Whitney）
2. 问卷信度（Cronbach's α）
3. 相关关系（Pearson / Spearman）

每个入口一键跳转对应模块，并自动预填合理默认参数。
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional


QUICK_ENTRIES = [
    {
        "id": "two_group_compare",
        "title": "🔬 两组比较",
        "subtitle": "t 检验 / Mann-Whitney U",
        "icon": "📊",
        "description": "比较两组在某个指标上的差异。适用于实验组 vs 控制组、男生 vs 女生等场景。",
        "methods": ["independent_ttest", "mann_whitney"],
        "default_test": "independent_ttest",
        "example": "如：比较男女生在焦虑量表得分上的差异",
        "tips": [
            "两组数据需要相互独立（不同被试）",
            "如果同一组人前后测，请用配对t检验",
            "数据不满足正态性时自动切换 Mann-Whitney",
        ],
    },
    {
        "id": "reliability",
        "title": "📐 问卷信度",
        "subtitle": "α / ω / 分半 / CR / ICC / 重测 / κ",
        "icon": "✅",
        "description": "检验量表各题目是否测量同一构念。覆盖 8 种信度方法，适用于问卷开发与验证。",
        "methods": ["cronbach_alpha", "split_half", "mcdonald_omega",
                    "composite_reliability", "icc", "test_retest",
                    "cohens_kappa", "fleiss_kappa"],
        "default_test": "cronbach_alpha",
        "example": "如：检验自编焦虑量表的信度",
        "tips": [
            "α/ω > 0.8 良好，0.7-0.8 可接受，< 0.7 需修订",
            "ω 比 α 更稳健（不要求 tau-equivalence），现代心理测量学推荐",
            "评分者一致性用 κ（两人）或 Fleiss' κ（≥3 人）",
            "重测信度需要两次测量，间隔 2-4 周",
        ],
    },
    {
        "id": "validity",
        "title": "🧪 问卷效度",
        "subtitle": "CVI / AVE / FL / HTMT / 效标 / 已知组别",
        "icon": "🎯",
        "description": "检验量表是否真正测量了其声称要测量的构念。覆盖内容、聚合、区分、效标四类效度。",
        "methods": ["criterion_validity", "known_groups_validity", "cvi",
                    "ave", "discriminant_fl", "discriminant_htmt"],
        "default_test": "criterion_validity",
        "example": "如：焦虑量表与抑郁量表的相关 / 抑郁组 vs 健康组的得分差异",
        "tips": [
            "效标效度 = 与外部金标准的相关（最易上手）",
            "已知组别效度 = 量表能否区分预先已知差异的群体",
            "AVE/CR/HTMT 需要先做 CFA 并指定因子结构",
            "CVI 是问卷开发阶段的内容效度，需 ≥6 位专家评分",
        ],
    },
    {
        "id": "correlation",
        "title": "🔗 相关关系",
        "subtitle": "Pearson / Spearman 相关",
        "icon": "📈",
        "description": "分析两个或多个连续变量之间的关系强度。适用于探索变量间关联模式。",
        "methods": ["pearson_corr", "spearman_corr"],
        "default_test": "pearson_corr",
        "example": "如：分析焦虑得分与抑郁得分的相关性",
        "tips": [
            "相关 ≠ 因果，论文中避免使用因果语言",
            "Pearson 要求数据近似正态，否则用 Spearman",
            "建议同时报告散点图",
        ],
    },
    {
        "id": "ai_item_review",
        "title": "🤖 AI 题目预审",
        "subtitle": "AI 模拟 4 位专家给题目相关性打分",
        "icon": "🤖",
        "description": "送给真专家做正式 CVI 之前的预审工具，识别明显不对劲的题目，节省真专家时间。",
        "methods": ["ai_item_review"],
        "default_test": "ai_item_review",
        "example": "如：构念=社交焦虑，题目=10 条，AI 4 位专家平行评分 + 改进建议",
        "tips": [
            "⚠️ AI 模拟 ≠ 真专家，本工具仅作题目修订预审，不构成正式 CVI 证据",
            "建议作为送真专家前的预筛工具",
            "至少 3 道题；建议构念定义 ≥ 50 字",
            "需要在侧栏配置 LLM（OpenAI / DeepSeek / Ollama 任选）",
        ],
    },
]


def render_quick_entry_homepage(df: Optional[pd.DataFrame] = None):
    """渲染智能默认首页：三大快捷入口"""
    st.title("📊 心理学研究工具")
    st.caption("选择你要做的分析类型，一键进入")

    # v3.7.9: 明确告知用户上传入口位置
    cur_df = df if df is not None else st.session_state.get("df")
    if cur_df is not None:
        n_rows, n_cols = cur_df.shape
        st.success(f"✅ 已加载数据：{st.session_state.get('file_name', '未知文件')} | {n_rows} 行 × {n_cols} 列")
    else:
        st.info(
            "👆 **第一步**：在 **页面顶部「📁 数据上传」** 处上传你的数据文件（CSV / Excel / SPSS）\n\n"
            "👇 **第二步**：选择下方的分析类型一键进入"
        )

    # 4 个入口：2×2 网格
    n = len(QUICK_ENTRIES)
    per_row = 2 if n >= 4 else n
    rows_needed = (n + per_row - 1) // per_row
    idx = 0
    for _ in range(rows_needed):
        cols = st.columns(per_row)
        for c in range(per_row):
            if idx >= n:
                break
            entry = QUICK_ENTRIES[idx]
            idx += 1
            with cols[c]:
                with st.container(border=True):
                    st.subheader(f"{entry['icon']} {entry['title']}")
                    st.caption(entry["subtitle"])
                    st.markdown(f"<small>{entry['description']}</small>", unsafe_allow_html=True)

                    st.divider()
                    st.caption(f"💡 {entry['example']}")

                    if st.button(f"进入 {entry['title']}", key=f"quick_{entry['id']}",
                                 type="primary", use_container_width=True):
                        st.session_state.quick_entry = entry
                        st.session_state.show_quick_detail = True
                        st.rerun()

    # ── 底部：完整方法列表入口 ──
    st.divider()
    with st.expander("🔧 更多分析方法（28种完整列表）", expanded=False):
        _render_full_method_list()


def _render_full_method_list():
    """渲染完整方法列表"""
    from config.settings import TEST_NAMES_ZH

    categories = {
        "均值比较": ["independent_ttest", "paired_ttest", "one_sample_ttest",
                     "one_way_anova", "two_way_anova", "repeated_anova",
                     "ancova", "welch_anova"],
        "相关与回归": ["pearson_corr", "spearman_corr", "partial_corr",
                      "point_biserial", "linear_regression", "multiple_regression",
                      "hierarchical_regression"],
        "非参数检验": ["mann_whitney", "wilcoxon", "kruskal_wallis", "friedman"],
        "卡方检验": ["chi_square_independence", "chi_square_gof"],
        "信度分析": ["cronbach_alpha", "split_half", "mcdonald_omega",
                     "composite_reliability", "icc", "test_retest",
                     "cohens_kappa", "fleiss_kappa"],
        "效度分析": ["cvi", "ave", "discriminant_fl", "discriminant_htmt",
                     "criterion_validity", "known_groups_validity"],
        "因素分析": ["efa", "cfa"],
        "高级分析": ["mediation", "moderation"],
        "AI 辅助": ["ai_item_review"],
    }

    for cat, methods in categories.items():
        st.markdown(f"**{cat}**")
        _cols = st.columns(4)
        for j, m in enumerate(methods):
            name = TEST_NAMES_ZH.get(m, m)
            with _cols[j % 4]:
                if st.button(name, key=f"full_method_{m}", use_container_width=True,
                             help=f"直接使用 {name}"):
                    st.session_state.quick_entry = {
                        "id": m,
                        "title": name,
                        "methods": [m],
                        "default_test": m,
                    }
                    st.session_state.show_quick_detail = False
                    st.rerun()


def render_quick_entry_detail():
    """渲染快捷入口的详情页（含参数预填和引导）"""
    entry = st.session_state.get("quick_entry")
    if not entry:
        return

    df = st.session_state.get("df")
    inspector = st.session_state.get("inspector")

    # v3.7.9: 顶部固定返回按钮 + 面包屑导航——比单纯的 ← 返回更醒目
    nav_cols = st.columns([1, 4, 1])
    with nav_cols[0]:
        if st.button("⬅️ 返回首页", key="back_to_home", type="secondary",
                     use_container_width=True):
            st.session_state.pop("quick_entry", None)
            st.session_state.pop("show_quick_detail", None)
            st.rerun()
    with nav_cols[1]:
        st.markdown(
            f"<div style='padding-top:6px;color:#666;font-size:0.9em;'>"
            f"📊 数据分析 &nbsp;›&nbsp; <strong>{entry['title']}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with nav_cols[2]:
        if st.button("🏠 主页", key="back_to_main_home", type="secondary",
                     use_container_width=True,
                     help="回到三大快捷入口主页"):
            st.session_state.pop("quick_entry", None)
            st.session_state.pop("show_quick_detail", None)
            st.rerun()

    st.divider()

    st.title(f"{entry['icon']} {entry['title']}")
    st.caption(entry.get("subtitle", ""))

    st.divider()

    # ── 数据未加载提示（v3.7.9 路径 B 优雅处理） ──
    if df is None or inspector is None:
        st.warning("⚠️ 还没加载数据，请先在 **页面顶部「📁 数据上传」** 处选择文件。")
        st.markdown("##### 这个分析适用于：")
        st.info(f"💡 {entry.get('example', '—')}")
        st.markdown("##### 注意事项：")
        for tip in entry.get("tips", []):
            st.markdown(f"- {tip}")
        st.divider()
        st.caption("上传数据后此页会自动展示参数预填表单，可直接开始分析。")
        return

    # ── 智能参数预填 ──
    if df is not None and inspector is not None:
        numeric_cols = [c for c, info in inspector.items()
                       if info.get("type") in ("numeric", "continuous", "float", "int")]
        cat_cols = [c for c, info in inspector.items()
                   if info.get("type") in ("categorical_binary", "categorical_multi", "object")]

        st.markdown("### 📋 自动检测到的变量")
        col_n, col_c = st.columns(2)
        with col_n:
            st.caption(f"📊 数值变量（{len(numeric_cols)}个）：{', '.join(numeric_cols[:8]) or '无'}")
        with col_c:
            st.caption(f"📁 分类变量（{len(cat_cols)}个）：{', '.join(cat_cols[:8]) or '无'}")

        st.divider()

        # 根据入口类型预填参数
        if entry["id"] == "two_group_compare":
            with st.form("quick_two_group"):
                col1, col2 = st.columns(2)
                with col1:
                    dv = st.selectbox("因变量（要比较的指标）", numeric_cols,
                                     help="如：焦虑得分、成绩等连续变量")
                with col2:
                    iv = st.selectbox("分组变量", cat_cols,
                                     help="如：性别（男/女）、组别（实验/控制）")
                test_method = st.radio("检验方法", ["independent_ttest", "mann_whitney"],
                                      format_func=lambda x: "独立样本t检验" if x == "independent_ttest" else "Mann-Whitney U 检验",
                                      horizontal=True)
                submitted = st.form_submit_button("🚀 开始分析", type="primary", use_container_width=True)
                if submitted and dv and iv:
                    _run_quick_analysis(df, test_method, dv, iv)

        elif entry["id"] == "reliability":
            _render_reliability_form(df, numeric_cols, cat_cols)

        elif entry["id"] == "validity":
            _render_validity_form(df, numeric_cols, cat_cols)

        elif entry["id"] == "ai_item_review":
            _render_ai_item_review_form(df, numeric_cols, cat_cols)

        elif entry["id"] == "correlation":
            with st.form("quick_correlation"):
                corr_vars = st.multiselect("选择要分析的相关变量（至少2个）", numeric_cols,
                                          help="选择需要分析相关关系的变量")
                test_method = st.radio("相关方法", ["pearson_corr", "spearman_corr"],
                                      format_func=lambda x: "Pearson 相关" if x == "pearson_corr" else "Spearman 秩相关",
                                      horizontal=True)
                submitted = st.form_submit_button("🚀 计算相关", type="primary", use_container_width=True)
                if submitted and len(corr_vars) >= 2:
                    _run_quick_analysis(df, test_method, dv_list=corr_vars)

        else:
            # 从完整列表进入的其他方法
            _run_quick_analysis(df, entry["default_test"])

    else:
        st.info("👆 请先在页面顶部「📁 数据上传」处上传数据文件，然后回到这里。")

    # ── 使用提示 ──
    st.divider()
    st.markdown("### 💡 注意事项")
    for tip in entry.get("tips", []):
        st.markdown(f"- {tip}")


def _render_reliability_form(df, numeric_cols, cat_cols):
    """信度方法的智能表单：根据所选方法切换字段。"""
    method_labels = {
        "cronbach_alpha": "Cronbach's α（内部一致性）",
        "split_half": "分半信度（Spearman-Brown）",
        "mcdonald_omega": "McDonald's ω（综合信度）",
        "composite_reliability": "组合信度（CR）",
        "icc": "ICC 组内相关（评分者一致性）",
        "test_retest": "重测信度",
        "cohens_kappa": "Cohen's κ（两评分者）",
        "fleiss_kappa": "Fleiss' κ（≥3 评分者）",
    }
    methods = list(method_labels.keys())
    test_method = st.selectbox(
        "信度方法",
        methods,
        format_func=lambda x: method_labels[x],
        key="reliability_method",
        help="不同方法适用于不同数据形态：α/ω/CR 用题目；ICC/Fleiss 用评分者；重测/Cohen 用两列。",
    )

    extra_kwargs = {}
    valid = False
    dep_vars: list = []
    submit_label = "🚀 计算信度"

    if test_method in ("cronbach_alpha", "split_half", "mcdonald_omega"):
        with st.form(f"form_rel_{test_method}"):
            min_items = 4 if test_method == "split_half" else 3
            scale_items = st.multiselect(
                f"选择量表题目（至少 {min_items} 题）", numeric_cols,
                help="同一量表的题目列",
            )
            submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
            if submitted and len(scale_items) >= min_items:
                dep_vars = scale_items
                valid = True

    elif test_method == "composite_reliability":
        st.caption("CR 需指定因子结构（与 CFA 一致）。")
        n_factors = st.number_input("因子数量", min_value=1, max_value=6, value=2, step=1, key="cr_n")
        factor_struct = {}
        used = set()
        for i in range(int(n_factors)):
            with st.expander(f"因子 {i+1}", expanded=(i < 2)):
                fname = st.text_input(f"因子名", value=f"因子{i+1}", key=f"cr_fn_{i}")
                opts = [c for c in numeric_cols if c not in used]
                items = st.multiselect("题目（至少 2 题）", opts, key=f"cr_items_{i}")
                if fname and items:
                    factor_struct[fname] = items
                    used.update(items)
        if st.button(submit_label, type="primary", use_container_width=True, key="cr_submit"):
            if all(len(v) >= 2 for v in factor_struct.values()) and len(factor_struct) >= 1:
                dep_vars = [it for v in factor_struct.values() for it in v]
                extra_kwargs["factor_structure"] = factor_struct
                valid = True
            else:
                st.error("每个因子至少需要 2 道题。")

    elif test_method == "icc":
        with st.form("form_rel_icc"):
            raters = st.multiselect("评分者列（至少 2 列；每列一个评分者对所有目标的评分）",
                                    numeric_cols, help="wide 格式")
            icc_type = st.selectbox(
                "ICC 类型",
                ["ICC1", "ICC2", "ICC3", "ICC1k", "ICC2k", "ICC3k"],
                index=1,
                help="ICC2 双向随机（最常用）；k 后缀=多评分者均值版本",
            )
            submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
            if submitted and len(raters) >= 2:
                extra_kwargs["rater_cols"] = raters
                extra_kwargs["icc_type"] = icc_type
                valid = True

    elif test_method == "test_retest":
        with st.form("form_rel_retest"):
            t1 = st.selectbox("第一次测量列（time1）", numeric_cols, key="tr_t1")
            t2 = st.selectbox("第二次测量列（time2）", numeric_cols, key="tr_t2",
                              index=min(1, len(numeric_cols) - 1))
            submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
            if submitted and t1 and t2 and t1 != t2:
                extra_kwargs["time1_col"] = t1
                extra_kwargs["time2_col"] = t2
                valid = True
            elif submitted:
                st.error("两次测量列必须不同。")

    elif test_method == "cohens_kappa":
        with st.form("form_rel_cohen"):
            all_cols = list(df.columns)
            r1 = st.selectbox("评分者 1", all_cols, key="ck_r1")
            r2 = st.selectbox("评分者 2", all_cols, key="ck_r2",
                              index=min(1, len(all_cols) - 1))
            weights = st.selectbox("权重", [None, "linear", "quadratic"],
                                   format_func=lambda x: {"None": "无权（标准 κ）", None: "无权（标准 κ）",
                                                          "linear": "线性加权", "quadratic": "二次加权"}.get(x, str(x)))
            submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
            if submitted and r1 and r2 and r1 != r2:
                extra_kwargs["rater1_col"] = r1
                extra_kwargs["rater2_col"] = r2
                extra_kwargs["kappa_weights"] = weights
                valid = True

    elif test_method == "fleiss_kappa":
        with st.form("form_rel_fleiss"):
            all_cols = list(df.columns)
            raters = st.multiselect("评分者列（≥3 列）", all_cols)
            submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
            if submitted and len(raters) >= 3:
                extra_kwargs["rater_cols"] = raters
                valid = True

    if valid:
        _run_quick_analysis(df, test_method, dv_list=dep_vars, **extra_kwargs)


def _render_validity_form(df, numeric_cols, cat_cols):
    """效度方法的智能表单：根据所选方法切换字段。"""
    method_labels = {
        "criterion_validity": "效标效度（与外部标准的相关）",
        "known_groups_validity": "已知组别效度（差异化检验）",
        "ave": "聚合效度 AVE（基于 CFA）",
        "discriminant_fl": "区分效度 Fornell-Larcker",
        "discriminant_htmt": "区分效度 HTMT",
        "cvi": "内容效度 CVI（专家评分）",
    }
    methods = list(method_labels.keys())
    test_method = st.selectbox(
        "效度方法", methods,
        format_func=lambda x: method_labels[x],
        key="validity_method",
        help="效标/已知组别最易上手；AVE/HTMT 需先指定因子结构；CVI 需要专家评分矩阵。",
    )

    extra_kwargs = {}
    dep_vars: list = []
    iv = None
    valid = False

    if test_method == "criterion_validity":
        with st.form("form_val_criterion"):
            scale_items = st.multiselect("量表题目（至少 3 题，将求和为总分）", numeric_cols)
            crit = st.selectbox("外部效标列", [c for c in numeric_cols if c not in scale_items],
                                help="如：临床诊断得分、其他成熟量表总分")
            kind = st.radio("效度类型",
                            ["concurrent", "predictive"],
                            format_func=lambda x: "同时效度（同期测量）" if x == "concurrent" else "预测效度（延迟测量）",
                            horizontal=True)
            submitted = st.form_submit_button("🚀 计算效标效度", type="primary", use_container_width=True)
            if submitted and len(scale_items) >= 3 and crit:
                dep_vars = scale_items
                extra_kwargs["criterion_col"] = crit
                extra_kwargs["criterion_kind"] = kind
                valid = True

    elif test_method == "known_groups_validity":
        with st.form("form_val_known"):
            scale_items = st.multiselect("量表题目（至少 3 题）", numeric_cols)
            group_col = st.selectbox("已知差异分组变量", cat_cols + numeric_cols,
                                     help="2 组用 t 检验，≥3 组用 ANOVA")
            submitted = st.form_submit_button("🚀 计算已知组别效度", type="primary", use_container_width=True)
            if submitted and len(scale_items) >= 3 and group_col:
                dep_vars = scale_items
                iv = group_col
                valid = True

    elif test_method in ("ave", "discriminant_fl", "discriminant_htmt"):
        st.caption(f"{method_labels[test_method]} 需指定因子结构（与 CFA 一致）。")
        min_factors = 1 if test_method == "ave" else 2
        n_factors = st.number_input("因子数量", min_value=min_factors, max_value=6,
                                    value=max(2, min_factors), step=1, key=f"v_n_{test_method}")
        factor_struct = {}
        used = set()
        for i in range(int(n_factors)):
            with st.expander(f"因子 {i+1}", expanded=(i < 2)):
                fname = st.text_input(f"因子名", value=f"因子{i+1}", key=f"v_fn_{test_method}_{i}")
                opts = [c for c in numeric_cols if c not in used]
                items = st.multiselect("题目（至少 3 题）", opts, key=f"v_items_{test_method}_{i}")
                if fname and items:
                    factor_struct[fname] = items
                    used.update(items)
        if st.button("🚀 计算效度", type="primary", use_container_width=True, key=f"v_submit_{test_method}"):
            if (all(len(v) >= 3 for v in factor_struct.values())
                    and len(factor_struct) >= min_factors):
                extra_kwargs["factor_structure"] = factor_struct
                dep_vars = [it for v in factor_struct.values() for it in v]
                valid = True
            else:
                st.error(f"至少 {min_factors} 个因子，每个因子至少 3 道题。")

    elif test_method == "cvi":
        st.caption("CVI 需要专家评分矩阵（题目×专家），每格 1-4 分相关性评分。")
        all_cols = list(df.columns)
        with st.form("form_val_cvi"):
            expert_cols = st.multiselect(
                "专家评分列（≥3 列；每列一位专家对所有题目的相关性打分 1-4）",
                all_cols, help="每行=1 道题；列名建议为专家姓名/编号",
            )
            submitted = st.form_submit_button("🚀 计算 CVI", type="primary", use_container_width=True)
            if submitted and len(expert_cols) >= 3:
                # 直接用主数据的这些列作为评分矩阵
                dep_vars = expert_cols
                valid = True

    if valid:
        _run_quick_analysis(df, test_method, dv_list=dep_vars, iv=iv, **extra_kwargs)


def _render_ai_item_review_form(df, numeric_cols, cat_cols):
    """AI 题目预审表单：题目源（粘贴 / 列名）+ 构念名/定义 + KB 推荐 + 运行按钮。

    ⚠ 此入口输出**非正式 CVI**，UI 顶部强提醒。
    """
    # ── 顶部强警告 ──
    st.error(
        "⚠️ **AI 模拟非正式 CVI**\n\n"
        "本工具用 LLM 扮演 4 位领域专家给题目打分，**不能替代真专家做内容效度（CVI）评定**。"
        "CVI 公式假设专家独立判断，多 persona 同模型相关接近 1.0，结果不可写入论文方法学。\n\n"
        "✅ **正确用法**：作为送真专家前的题目修订工具，识别明显不对劲的题目。"
    )

    # ── 题目来源 ──
    st.markdown("### 1. 题目来源")
    src = st.radio(
        "选择题目来源",
        ["paste", "columns"],
        format_func=lambda x: "📝 文本框粘贴（一行一题，推荐）" if x == "paste"
                                else "📊 从已上传数据列头抽取",
        horizontal=True,
        key="ai_review_src",
    )

    items_text = ""
    items_from_cols: list = []
    if src == "paste":
        items_text = st.text_area(
            "粘贴题目（每行一道，至少 3 道）",
            height=180,
            placeholder=(
                "例：\n"
                "1. 我在陌生人面前感到紧张\n"
                "2. 在聚会上我会担心别人怎么看我\n"
                "3. 公开发言前我会感到强烈不安\n"
                "..."
            ),
            key="ai_review_items_text",
        )
        # 清理序号前缀
        clean_lines = []
        for ln in items_text.splitlines():
            s = ln.strip()
            if not s:
                continue
            # 剥前导编号 "1. " / "1、"
            for sep in [". ", "、", ".", "）", ")"]:
                if sep in s[:5]:
                    head, tail = s.split(sep, 1)
                    if head.strip().isdigit():
                        s = tail.strip()
                        break
            clean_lines.append(s)
        items_count = len(clean_lines)
    else:
        items_from_cols = st.multiselect(
            "选择题目列（每列名作为题目文本）",
            list(df.columns),
            help="如果数据已含题目文本列，可直接选；否则建议用粘贴方式。",
            key="ai_review_items_cols",
        )
        items_count = len(items_from_cols)

    st.caption(f"已识别 **{items_count}** 道题。")

    st.divider()

    # ── 构念名 + 定义（KB 并排）──
    st.markdown("### 2. 构念信息")

    # 先做 KB 命中检查
    kb_def = None
    construct_name = ""
    name_col, kb_col = st.columns([1, 1])
    with name_col:
        construct_name = st.text_input(
            "构念名（如：社交焦虑、工作满意度）",
            key="ai_review_construct_name",
            placeholder="社交焦虑",
        )
    with kb_col:
        if construct_name:
            try:
                from src.questionnaire.construct_kb import CONSTRUCTS
                rec = CONSTRUCTS.get(construct_name)
                if rec:
                    kb_def = rec.get("definition", "")
                    st.success(f"✅ KB 命中：{construct_name}")
                else:
                    st.info("ℹ️ KB 未命中（仅用用户定义）")
            except Exception:
                pass

    if kb_def:
        with st.expander("📚 KB 参考定义（仅供对照，不会自动覆盖你的定义）", expanded=False):
            st.markdown(kb_def)

    construct_def = st.text_area(
        "构念定义（你自己的定义，建议 ≥ 50 字）",
        height=120,
        key="ai_review_construct_def",
        placeholder="个体在社交场合感到不自在、担忧被他人评价的稳定情绪倾向，包含认知、情感与行为三个层面...",
        help="将作为 prompt 送给 4 位 AI 专家，定义越清晰，评分越靠谱。",
    )

    st.divider()

    # ── 提交 ──
    st.markdown("### 3. 运行")
    st.caption("4 位 AI 专家串行评分，约 30-60 秒；缓存命中可秒回。")

    col_run, _ = st.columns([1, 3])
    with col_run:
        if st.button("🚀 运行预审", type="primary", use_container_width=True,
                      key="ai_review_run"):
            # ── 表单验证 ──
            if items_count < 3:
                st.error(f"至少需要 3 道题（当前 {items_count} 道）。")
                return
            if not construct_name.strip():
                st.error("请填写构念名。")
                return
            if not construct_def.strip() or len(construct_def.strip()) < 10:
                st.error("构念定义太短，请提供更详细的定义（建议 ≥ 50 字）。")
                return

            # 构建 plan kwargs
            plan_kwargs = {
                "construct_name": construct_name.strip(),
                "construct_definition": construct_def.strip(),
                "n_personas": 4,
            }
            dep_vars = []
            if src == "paste":
                plan_kwargs["items_text"] = "\n".join(clean_lines)
            else:
                dep_vars = items_from_cols

            from src.utils.llm_timer import llm_status
            with llm_status("正在调用 4 位 AI 专家评分", timeout_hint=60):
                _run_quick_analysis(df, "ai_item_review",
                                     dv_list=dep_vars,
                                     **plan_kwargs)


def _run_quick_analysis(df, test_type: str, dv: str = None, iv: str = None,
                         dv_list: list = None, **plan_kwargs):
    """执行快捷分析，完成后跳转到正常结果展示。

    plan_kwargs 透传到 AnalysisPlan，支持 v3.7 信度/效度专用字段：
    factor_structure / time1_col / time2_col / rater_cols / rater1_col / rater2_col /
    icc_type / kappa_weights / criterion_col / criterion_kind。
    """
    from src.parser.intent_resolver import AnalysisPlan
    from src.analysis.runner import run_analysis

    if dv_list:
        dep_vars = dv_list
    elif dv:
        dep_vars = [dv]
    else:
        dep_vars = []

    ind_vars = [iv] if iv else []

    plan = AnalysisPlan(
        test_type=test_type,
        dependent_vars=dep_vars,
        independent_vars=ind_vars,
        confidence_level=0.95,
        **plan_kwargs,
    )

    with st.spinner("正在执行统计分析..."):
        output = run_analysis(df, plan)
        st.session_state.analysis_output = output
        st.session_state.plan = plan

        # 记录历史
        history_entry = {
            "test_type": test_type,
            "dv": dep_vars,
            "iv": ind_vars,
        }
        if "analysis_history" not in st.session_state:
            st.session_state.analysis_history = []
        st.session_state.analysis_history.append(history_entry)

        # 自动归档
        try:
            from src.output.formatter import build_apa7_report
            from src.utils.archive_manager import archive_analysis
            tag = st.session_state.get("archive_tag", "")
            report_md = build_apa7_report(output)
            params = {
                "test_type": test_type,
                "test_name_zh": output.get("test_name_zh", ""),
                "dependent_vars": dep_vars,
                "independent_vars": ind_vars,
                "confidence_level": 0.95,
            }
            archive_analysis(df, output, report_md, params,
                           tag=tag, file_name=st.session_state.get("file_name", ""))
        except Exception:
            pass

    # 清除快捷入口，让正常流程渲染结果
    st.session_state.pop("quick_entry", None)
    st.session_state.pop("show_quick_detail", None)
    st.rerun()
