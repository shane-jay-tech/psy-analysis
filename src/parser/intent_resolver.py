"""核心意图解析器：分词 + 关键词匹配 → AnalysisPlan"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import pandas as pd
from difflib import SequenceMatcher

from .tokenizer import tokenize, tokenize_keep_numbers
from .keyword_dict import TEST_KEYWORDS, VARIABLE_ROLE_KEYWORDS


@dataclass
class AnalysisPlan:
    """分析计划：解析器输出"""
    test_type: str
    dependent_vars: List[str] = field(default_factory=list)
    independent_vars: List[str] = field(default_factory=list)
    grouping_var: Optional[str] = None
    covariates: List[str] = field(default_factory=list)
    scale_items: List[str] = field(default_factory=list)
    blocks: List[List[str]] = field(default_factory=list)
    test_value: Optional[float] = None
    confidence_level: float = 0.95
    raw_request: str = ""
    parsed_keywords: List[str] = field(default_factory=list)
    ambiguity_score: float = 0.0
    suggested_followups: List[str] = field(default_factory=list)
    # v3.7 新增：信度/效度专用字段
    factor_structure: Optional[Dict[str, List[str]]] = None  # CR/AVE/HTMT/CFA 的因子→题目映射
    time1_col: Optional[str] = None       # 重测：第一次测量列
    time2_col: Optional[str] = None       # 重测：第二次测量列
    rater_cols: List[str] = field(default_factory=list)      # ICC / Fleiss' κ：评分者列
    rater1_col: Optional[str] = None      # Cohen's κ：评分者1
    rater2_col: Optional[str] = None      # Cohen's κ：评分者2
    icc_type: str = "ICC2"                # ICC1/2/3/1k/2k/3k
    kappa_weights: Optional[str] = None   # None / "linear" / "quadratic"
    expert_ratings: Optional[Any] = None  # CVI 评分矩阵（DataFrame；旁路传入）
    criterion_col: Optional[str] = None   # 效标效度：外部效标列
    criterion_kind: str = "concurrent"    # "concurrent" / "predictive"
    # v3.8 新增：AI 题目预审字段
    items_text: Optional[str] = None       # 用户粘贴的题目文本（一行一题）
    construct_name: Optional[str] = None   # 构念名
    construct_definition: Optional[str] = None  # 构念定义
    n_personas: int = 4                    # 模拟专家数
    # v3.9 新增：SEM 结构路径
    structural_paths: Optional[List[str]] = None  # 结构路径如 ["焦虑 ~ 自尊", "孤独 ~ 焦虑 + 自尊"]


def _score_test_types(tokens: list, col_types: dict) -> list:
    """
    根据分词结果对所有检验类型打分，返回排序后的候选项列表。
    """
    scores = {}
    for test_type, config in TEST_KEYWORDS.items():
        score = 0
        matched = []
        for trigger in config["triggers"]:
            if trigger in tokens:
                score += 1
                matched.append(trigger)
            # 检查组合关键词
            elif any(trigger in t for t in tokens):
                score += 0.5
                matched.append(trigger + "(部分)")
            # 检查多字组合
            elif len(trigger) >= 2:
                for t in tokens:
                    if len(t) >= 2 and (
                        trigger in t or t in trigger
                        or SequenceMatcher(None, trigger, t).ratio() > 0.8
                    ):
                        score += 0.3
                        break

        scores[test_type] = {"score": score, "matched": matched}

    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    return ranked


def _fuzzy_match_column(token: str, columns: list) -> Optional[str]:
    """模糊匹配词条与列名"""
    token_lower = token.lower()

    for col in columns:
        col_lower = col.lower()
        # 精确包含
        if token_lower in col_lower or col_lower in token_lower:
            return col
        # 序列相似度
        if len(token) >= 2 and len(col) >= 2:
            if SequenceMatcher(None, token_lower, col_lower).ratio() > 0.75:
                return col
    return None


def _match_value_in_column(token: str, col_name: str, df: pd.DataFrame) -> bool:
    """检查词条是否匹配某列的某个值"""
    try:
        values = df[col_name].dropna().astype(str).unique()
        for v in values:
            if token in v or v in token:
                return True
            if len(token) >= 2 and len(v) >= 2:
                if SequenceMatcher(None, token, v).ratio() > 0.7:
                    return True
    except Exception:
        pass
    return False


def _extract_test_value(tokens: list) -> Optional[float]:
    """从词条中提取检验值（单样本t检验的对比值）"""
    for t in tokens:
        try:
            val = float(t)
            return val
        except ValueError:
            # 处理"检验值为100"这类
            for part in t.replace("检验值", "").replace("常模", "").replace("标准", "").split():
                try:
                    return float(part)
                except ValueError:
                    continue
    return None


def resolve(df: pd.DataFrame, request: str, col_info: dict = None) -> AnalysisPlan:
    """
    主入口：解析中文分析需求，返回 AnalysisPlan。

    Args:
        df: 已加载的 DataFrame
        request: 用户输入的中文分析需求
        col_info: 可选的预计算列信息字典（由 inspect_dataframe 返回），避免重复计算

    Returns:
        AnalysisPlan 对象
    """
    request = request.strip()
    columns = df.columns.tolist()
    col_types = {}

    if col_info is not None:
        for col, info in col_info.items():
            col_types[col] = info["type"]
    else:
        from src.data.inspector import inspect_dataframe
        col_info = inspect_dataframe(df)
        for col, info in col_info.items():
            col_types[col] = info["type"]

    # Layer 1: 分词
    tokens = tokenize(request)
    tokens_with_nums = tokenize_keep_numbers(request)

    if not tokens:
        return AnalysisPlan(
            test_type="descriptive",
            raw_request=request,
            ambiguity_score=1.0,
            suggested_followups=[
                "请更具体地说明您的分析需求，例如：",
                '"比较男女生在焦虑量表上的得分差异"',
                '"分析焦虑得分与抑郁得分的相关性"',
                '"比较三个年级在学业成绩上的差异"',
            ],
        )

    # Layer 2: 关键词打分
    ranked = _score_test_types(tokens, col_types)
    best_type, best_info = ranked[0] if ranked else (None, {"score": 0})

    # 如果没有匹配到任何检验类型，默认描述统计
    if best_info["score"] == 0:
        plan = AnalysisPlan(
            test_type="descriptive",
            raw_request=request,
            parsed_keywords=[],
            ambiguity_score=0.5,
            suggested_followups=[
                "未检测到明确的统计方法，已默认执行描述性统计。",
                '提示：可以使用"比较"、"相关"、"方差分析"等关键词指定方法。',
            ],
        )
        # 自动选择所有数值列作为描述对象
        for col, ctype in col_types.items():
            if ctype == "numeric":
                plan.dependent_vars.append(col)
        return plan

    # Layer 3: 变量识别
    dependent_vars = []
    independent_vars = []
    scale_items = []

    # 判断每个词条匹配哪个列
    for token in tokens:
        col_match = _fuzzy_match_column(token, columns)
        if col_match is None:
            continue

        ctype = col_types.get(col_match, "numeric")

        # 判断变量角色
        if ctype in ("categorical_binary", "categorical_multi"):
            if col_match not in independent_vars:
                independent_vars.append(col_match)
        elif ctype == "numeric":
            if col_match not in dependent_vars:
                dependent_vars.append(col_match)

    # 如果没找到数值型但因变量为空，检查变量角色关键词
    if not dependent_vars:
        for token in tokens:
            for role_kw in VARIABLE_ROLE_KEYWORDS.get("dependent", []):
                if role_kw in token:
                    # 附近找数值列
                    for col in columns:
                        if col_types.get(col) == "numeric":
                            if col not in dependent_vars:
                                dependent_vars.append(col)

    # 如果还没有DV，选所有数值列
    if not dependent_vars:
        for col, ctype in col_types.items():
            if ctype == "numeric":
                dependent_vars.append(col)

    # 提取检验值
    test_value = _extract_test_value(tokens_with_nums)

    # Layer 4: 数据类型兼容性调整
    test_type = best_type

    # Welch ANOVA 明确关键词覆盖
    if test_type == "one_way_anova" and ("welch" in request.lower() or "方差不齐" in request):
        test_type = "welch_anova"

    # t检验需要有分组变量
    if test_type == "independent_ttest":
        if not independent_vars:
            # 尝试找二分类列
            for col, ctype in col_types.items():
                if ctype == "categorical_binary" and col not in independent_vars:
                    independent_vars.append(col)
                    break
        # 如果分组变量有3+水平，升级为ANOVA
        for iv in independent_vars:
            if col_types.get(iv) == "categorical_multi":
                test_type = "one_way_anova"
                break

    # 相关需要至少2个数值变量
    if test_type in ("pearson_corr", "spearman_corr"):
        if len(dependent_vars) < 2:
            numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
            dependent_vars = numeric_cols[:5]  # 最多5个

    # 信度分析
    if test_type == "cronbach_alpha":
        scale_items = dependent_vars[:]
        dependent_vars = []

    # Layer 5: 计算模糊度
    ambiguity_score = 0.0
    if best_info["score"] < 2:
        ambiguity_score = 0.4
    if best_info["score"] < 1:
        ambiguity_score = 0.7
    if not dependent_vars and test_type not in ("descriptive", "cronbach_alpha"):
        ambiguity_score = max(ambiguity_score, 0.6)

    plan = AnalysisPlan(
        test_type=test_type,
        dependent_vars=dependent_vars[:5],  # 最多5个DV
        independent_vars=independent_vars[:3],  # 最多3个IV
        scale_items=scale_items,
        test_value=test_value,
        raw_request=request,
        parsed_keywords=best_info.get("matched", []),
        ambiguity_score=ambiguity_score,
        suggested_followups=_generate_followups(test_type, ambiguity_score, columns, col_types),
    )

    return plan


def _generate_followups(
    test_type: str,
    ambiguity: float,
    columns: list,
    col_types: dict,
) -> list:
    """生成追问建议"""
    followups = []

    if ambiguity > 0.5:
        col_list = ", ".join(columns[:8])
        followups.append(f"数据中包含以下变量：{col_list}")
        followups.append("请确认分析方法和所选变量是否正确。")

    return followups
