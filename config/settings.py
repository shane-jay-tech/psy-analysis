"""全局配置：多语言标签、检验名称映射、图表默认值"""

try:
    from src.utils.i18n import t
except Exception:
    t = None

# ============================================================
# 统计检验名称（支持动态语言切换）
# ============================================================
TEST_NAMES_ZH = {
    "descriptive": "描述性统计",
    "independent_ttest": "独立样本t检验",
    "paired_ttest": "配对样本t检验",
    "one_sample_ttest": "单样本t检验",
    "one_way_anova": "单因素方差分析",
    "two_way_anova": "双因素方差分析",
    "repeated_anova": "重复测量方差分析",
    "pearson_corr": "Pearson相关",
    "spearman_corr": "Spearman相关",
    "linear_regression": "线性回归",
    "multiple_regression": "多元回归",
    "chi_square_independence": "卡方独立性检验",
    "chi_square_gof": "卡方拟合优度检验",
    "cronbach_alpha": "克隆巴赫α信度",
    "mann_whitney": "Mann-Whitney U检验",
    "wilcoxon": "Wilcoxon符号秩检验",
    "kruskal_wallis": "Kruskal-Wallis H检验",
    "friedman": "Friedman检验",
    "split_half": "分半信度",
    "ancova": "协方差分析（ANCOVA）",
    "mediation": "中介效应分析",
    "moderation": "调节效应分析",
    "efa": "探索性因素分析（EFA）",
    "cfa": "验证性因素分析（CFA）",
    "partial_corr": "偏相关分析",
    "point_biserial": "点二列相关",
    "hierarchical_regression": "层次回归",
    "welch_anova": "Welch方差分析",
    # v3.7：信度方法补全
    "mcdonald_omega": "McDonald's ω 综合信度",
    "composite_reliability": "组合信度（CR）",
    "icc": "组内相关系数（ICC）",
    "test_retest": "重测信度",
    "cohens_kappa": "Cohen's κ 评分者一致性",
    "fleiss_kappa": "Fleiss' κ 多评分者一致性",
    # v3.7：效度方法新增
    "cvi": "内容效度指数（CVI）",
    "ave": "平均方差抽取量（AVE）",
    "discriminant_fl": "区分效度（Fornell-Larcker）",
    "discriminant_htmt": "区分效度（HTMT）",
    "criterion_validity": "效标效度",
    "known_groups_validity": "已知组别效度",
    # v3.8：AI 题目预审（非正式 CVI）
    "ai_item_review": "AI 题目预审（非正式 CVI）",
    # v3.9：Logistic 回归
    "binary_logistic": "二元Logistic回归",
    "ordinal_logistic": "有序Logistic回归",
    "multinomial_logistic": "多项Logistic回归",
    # MANOVA
    "manova": "多元方差分析（MANOVA）",
    "mixed_anova": "混合设计方差分析",
    "hlm": "多层线性模型（HLM）",
    "sem": "结构方程模型（SEM）",
}


def get_test_name(test_type: str) -> str:
    """获取当前语言的检验名称"""
    if t is not None:
        translated = t(test_type)
        if translated != test_type:
            return translated
    return TEST_NAMES_ZH.get(test_type, test_type)


# 向后兼容：保留 TEST_NAMES_ZH 作为别名，但优先使用 get_test_name()

# ============================================================
# 图表配色方案
# ============================================================
COLOR_PALETTE = [
    "#4472C4", "#ED7D31", "#A5A5A5", "#FFC000",
    "#5B9BD5", "#70AD47", "#264478", "#9B59B6",
]

COLORMAP_DIVERGING = "RdBu_r"
COLORMAP_SEQUENTIAL = "Blues"

# ============================================================
# 图表默认布局
# ============================================================
CHART_TEMPLATE = "simple_white"
CHART_HEIGHT = 450
CHART_WIDTH = None  # 自适应

# ============================================================
# 统计检验默认参数
# ============================================================
DEFAULT_CONFIDENCE = 0.95
DEFAULT_ALPHA = 0.05

# ============================================================
# 语言设置
# ============================================================
OUTPUT_LANGUAGE = "zh"  # "zh" (APA7 中文) 或 "en" (APA7 English)


def get_output_language() -> str:
    """从 session_state 读取输出语言设置"""
    try:
        import streamlit as st
        return st.session_state.get("output_language", OUTPUT_LANGUAGE)
    except Exception:
        return OUTPUT_LANGUAGE


# ============================================================
# 输出格式
# ============================================================
DECIMAL_STAT = 3       # 统计量小数位
DECIMAL_P = 3          # p值小数位
DECIMAL_DESC = 2       # 描述统计小数位

# ============================================================
# 变量角色中文
# ============================================================
VAR_ROLE_LABELS = {
    "numeric": "数值型",
    "categorical_binary": "二分类",
    "categorical_multi": "多分类",
    "datetime": "日期型",
    "text_free": "文本型",
}
