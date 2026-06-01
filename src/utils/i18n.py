"""简易国际化（i18n）模块

支持中英双语切换，基于字典查找。
未找到的键直接返回键名本身（便于开发时定位）。
"""

from typing import Dict

# 默认语言
DEFAULT_LANG = "zh"

# 翻译字典
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh": {
        # UI 通用
        "app_title": "心理学研究工具系统",
        "analysis": "数据分析",
        "questionnaire_design": "问卷设计",
        "experiment_design": "实验设计",
        "paper_writing": "论文写作",
        "undergrad_wizard": "本科向导",
        "settings": "设置",
        "upload_data": "上传数据",
        "start_analysis": "开始分析",
        "clear": "清空",
        "export": "导出",
        "save": "保存",
        "cancel": "取消",
        "confirm": "确认",
        "close": "关闭",
        "loading": "加载中...",
        "success": "成功",
        "error": "错误",
        "warning": "警告",
        "info": "提示",
        # 统计术语
        "mean": "均值",
        "std": "标准差",
        "n": "样本量",
        "median": "中位数",
        "min": "最小值",
        "max": "最大值",
        "skewness": "偏度",
        "kurtosis": "峰度",
        "t_statistic": "t值",
        "df": "自由度",
        "p_value": "p值",
        "ci": "置信区间",
        "effect_size": "效应量",
        "cohens_d": "Cohen's d",
        "eta_squared": "η²",
        "partial_eta_squared": "偏η²",
        "f_statistic": "F值",
        "chi_square": "χ²",
        "correlation": "相关系数",
        "r_value": "r值",
        # 检验名称
        "descriptive": "描述性统计",
        "independent_ttest": "独立样本t检验",
        "paired_ttest": "配对样本t检验",
        "one_sample_ttest": "单样本t检验",
        "one_way_anova": "单因素方差分析",
        "welch_anova": "Welch方差分析",
        "two_way_anova": "双因素方差分析",
        "repeated_anova": "重复测量方差分析",
        "mann_whitney": "Mann-Whitney U检验",
        "wilcoxon": "Wilcoxon符号秩检验",
        "kruskal_wallis": "Kruskal-Wallis H检验",
        "friedman": "Friedman检验",
        "pearson_corr": "Pearson相关分析",
        "spearman_corr": "Spearman相关分析",
        "partial_corr": "偏相关分析",
        "chi_square_independence": "卡方独立性检验",
        "chi_square_gof": "卡方拟合优度检验",
        "linear_regression": "线性回归",
        "multiple_regression": "多元回归",
        "hierarchical_regression": "分层回归",
        "logistic_regression": "逻辑回归",
        "mediation": "中介效应分析",
        "moderation": "调节效应分析",
        "efa": "探索性因素分析",
        "cfa": "验证性因素分析",
        "reliability": "信度分析",
        "normality_test": "正态性检验",
        "homogeneity_test": "方差齐性检验",
        # 表格列名
        "variable": "变量",
        "group": "组别",
        "statistic": "统计量",
        "value": "值",
        "source": "来源",
        "ss": "平方和",
        "ms": "均方",
        # 假设检验
        "null_hypothesis": "原假设",
        "alternative_hypothesis": "备择假设",
        "significance_level": "显著性水平",
        "reject_null": "拒绝原假设",
        "fail_to_reject_null": "不拒绝原假设",
        # 论文写作
        "title": "标题",
        "abstract": "摘要",
        "keywords": "关键词",
        "introduction": "引言",
        "methods": "方法",
        "results": "结果",
        "discussion": "讨论",
        "references": "参考文献",
        "participants": "被试",
        "materials": "材料",
        "procedure": "程序",
        "ethics": "伦理",
        "data_analysis": "数据分析",
        # 实验设计
        "independent_variable": "自变量",
        "dependent_variable": "因变量",
        "control_variable": "控制变量",
        "design_type": "设计类型",
        "sample_size": "样本量",
        "power_analysis": "效力分析",
        "effect_size_expected": "预期效应量",
        # 其他
        "language": "语言",
        "chinese": "中文",
        "english": "英文",
        "llm_config": "LLM配置",
        "memory_manager": "内存管理",
        "pipeline": "分析Pipeline",
    },
    "en": {
        # UI General
        "app_title": "Psychology Research Tool System",
        "analysis": "Data Analysis",
        "questionnaire_design": "Questionnaire Design",
        "experiment_design": "Experiment Design",
        "paper_writing": "Paper Writing",
        "undergrad_wizard": "Undergrad Wizard",
        "settings": "Settings",
        "upload_data": "Upload Data",
        "start_analysis": "Start Analysis",
        "clear": "Clear",
        "export": "Export",
        "save": "Save",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "close": "Close",
        "loading": "Loading...",
        "success": "Success",
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        # Statistical terms
        "mean": "Mean",
        "std": "SD",
        "n": "N",
        "median": "Median",
        "min": "Min",
        "max": "Max",
        "skewness": "Skewness",
        "kurtosis": "Kurtosis",
        "t_statistic": "t",
        "df": "df",
        "p_value": "p",
        "ci": "CI",
        "effect_size": "Effect Size",
        "cohens_d": "Cohen's d",
        "eta_squared": "η²",
        "partial_eta_squared": "Partial η²",
        "f_statistic": "F",
        "chi_square": "χ²",
        "correlation": "Correlation",
        "r_value": "r",
        # Test names
        "descriptive": "Descriptive Statistics",
        "independent_ttest": "Independent Samples t-test",
        "paired_ttest": "Paired Samples t-test",
        "one_sample_ttest": "One-Sample t-test",
        "one_way_anova": "One-Way ANOVA",
        "welch_anova": "Welch's ANOVA",
        "two_way_anova": "Two-Way ANOVA",
        "repeated_anova": "Repeated Measures ANOVA",
        "mann_whitney": "Mann-Whitney U Test",
        "wilcoxon": "Wilcoxon Signed-Rank Test",
        "kruskal_wallis": "Kruskal-Wallis H Test",
        "friedman": "Friedman Test",
        "pearson_corr": "Pearson Correlation",
        "spearman_corr": "Spearman Correlation",
        "partial_corr": "Partial Correlation",
        "chi_square_independence": "Chi-Square Test of Independence",
        "chi_square_gof": "Chi-Square Goodness of Fit",
        "linear_regression": "Linear Regression",
        "multiple_regression": "Multiple Regression",
        "hierarchical_regression": "Hierarchical Regression",
        "logistic_regression": "Logistic Regression",
        "mediation": "Mediation Analysis",
        "moderation": "Moderation Analysis",
        "efa": "Exploratory Factor Analysis",
        "cfa": "Confirmatory Factor Analysis",
        "reliability": "Reliability Analysis",
        "normality_test": "Normality Test",
        "homogeneity_test": "Homogeneity Test",
        # Table columns
        "variable": "Variable",
        "group": "Group",
        "statistic": "Statistic",
        "value": "Value",
        "source": "Source",
        "ss": "SS",
        "ms": "MS",
        # Hypothesis testing
        "null_hypothesis": "Null Hypothesis",
        "alternative_hypothesis": "Alternative Hypothesis",
        "significance_level": "Significance Level",
        "reject_null": "Reject H₀",
        "fail_to_reject_null": "Fail to Reject H₀",
        # Paper writing
        "title": "Title",
        "abstract": "Abstract",
        "keywords": "Keywords",
        "introduction": "Introduction",
        "methods": "Methods",
        "results": "Results",
        "discussion": "Discussion",
        "references": "References",
        "participants": "Participants",
        "materials": "Materials",
        "procedure": "Procedure",
        "ethics": "Ethics",
        "data_analysis": "Data Analysis",
        # Experiment design
        "independent_variable": "Independent Variable",
        "dependent_variable": "Dependent Variable",
        "control_variable": "Control Variable",
        "design_type": "Design Type",
        "sample_size": "Sample Size",
        "power_analysis": "Power Analysis",
        "effect_size_expected": "Expected Effect Size",
        # Others
        "language": "Language",
        "chinese": "Chinese",
        "english": "English",
        "llm_config": "LLM Config",
        "memory_manager": "Memory Manager",
        "pipeline": "Analysis Pipeline",
    },
}


def t(key: str, lang: str = None) -> str:
    """翻译函数。

    参数：
        key: 翻译键
        lang: 语言代码（"zh" 或 "en"），默认从 session_state 读取

    返回：
        翻译后的文本；若未找到则返回键名
    """
    if lang is None:
        try:
            import streamlit as st
            lang = st.session_state.get("language", DEFAULT_LANG)
        except Exception:
            lang = DEFAULT_LANG

    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)


def get_test_name_zh(test_type: str, lang: str = None) -> str:
    """获取检验方法的中文/英文名称"""
    return t(test_type, lang)
