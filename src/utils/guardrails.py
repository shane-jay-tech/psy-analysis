"""本科生防呆设计：阻断常见学术错误

1. 多重比较拦截器 — 连续3+次独立t检验或ANOVA事后>5组时强制阻断
2. 样本量红灯 — N<30且选择参数检验时黄灯警告
3. 效应量强制输出 — APA7报告生成前检查效应量字段
4. 变量类型锁 — 检验方法与数据类型不匹配时阻断并建议替代方法
"""

import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ── 检验方法 ↔ 数据类型要求映射 ──
# 每个检验方法要求的数据类型：(因变量类型, 自变量类型)
TEST_TYPE_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
    "independent_ttest": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_binary", "categorical_multi"],
    },
    "paired_ttest": {
        "dv_types": ["numeric", "numeric"],  # 两个配对列都是数值
    },
    "one_sample_ttest": {
        "dv_types": ["numeric"],
    },
    "one_way_anova": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_multi"],
    },
    "two_way_anova": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_binary", "categorical_multi"],
    },
    "repeated_anova": {
        "dv_types": ["numeric"],
    },
    "pearson_corr": {
        "dv_types": ["numeric"],
    },
    "spearman_corr": {
        "dv_types": ["numeric"],
    },
    "partial_corr": {
        "dv_types": ["numeric"],
    },
    "mann_whitney": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_binary"],
    },
    "kruskal_wallis": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_multi"],
    },
    "wilcoxon": {
        "dv_types": ["numeric", "numeric"],
    },
    "friedman": {
        "dv_types": ["numeric"],
    },
    "chi_square_independence": {
        "dv_types": ["categorical_binary", "categorical_multi"],
        "iv_types": ["categorical_binary", "categorical_multi"],
    },
    "chi_square_gof": {
        "dv_types": ["categorical_binary", "categorical_multi"],
    },
    "cronbach_alpha": {
        "dv_types": ["numeric"],
    },
    "ancova": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_binary", "categorical_multi"],
    },
    "linear_regression": {
        "dv_types": ["numeric"],
    },
    "multiple_regression": {
        "dv_types": ["numeric"],
    },
    "hierarchical_regression": {
        "dv_types": ["numeric"],
    },
    "mediation": {
        "dv_types": ["numeric"],
    },
    "moderation": {
        "dv_types": ["numeric"],
    },
    "efa": {
        "dv_types": ["numeric"],
    },
    "split_half": {
        "dv_types": ["numeric"],
    },
    "point_biserial": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_binary"],
    },
    "welch_anova": {
        "dv_types": ["numeric"],
        "iv_types": ["categorical_multi"],
    },
}


# ── 替代方法建议 ──
ALTERNATIVE_SUGGESTIONS = {
    ("independent_ttest", "categorical_binary", "categorical_binary"): (
        "独立样本t检验要求因变量为连续变量，但检测到两列都是分类变量。",
        "chi_square_independence",
        "卡方独立性检验"
    ),
    ("independent_ttest", "categorical_multi", "categorical_multi"): (
        "独立样本t检验要求因变量为连续变量，但检测到两列都是分类变量。",
        "chi_square_independence",
        "卡方独立性检验"
    ),
    ("pearson_corr", "categorical_binary", "categorical_binary"): (
        "Pearson相关要求连续变量，但检测到分类变量。",
        "chi_square_independence",
        "卡方独立性检验"
    ),
    ("pearson_corr", "categorical_multi", "categorical_multi"): (
        "Pearson相关要求连续变量，但检测到分类变量。",
        "chi_square_independence",
        "卡方独立性检验"
    ),
    ("one_way_anova", "categorical_binary", "categorical_multi"): (
        "ANOVA要求因变量为连续变量，但检测到分类变量作为因变量。",
        "chi_square_independence",
        "卡方独立性检验"
    ),
}


@dataclass
class GuardrailResult:
    passed: bool
    severity: str  # "block", "warn", "info"
    title: str
    message: str
    suggested_action: str = ""
    suggested_test_type: str = ""
    suggested_test_name: str = ""


def check_variable_type_match(
    test_type: str,
    dv_types: List[str],
    iv_types: List[str],
) -> GuardrailResult:
    """检查检验方法与数据类型是否匹配。不匹配则阻断并建议替代方法。"""
    req = TEST_TYPE_REQUIREMENTS.get(test_type)
    if req is None:
        return GuardrailResult(passed=True, severity="info", title="", message="")

    # 检查因变量类型
    required_dv = req.get("dv_types", [])
    if required_dv and dv_types:
        for i, dv_t in enumerate(dv_types):
            expected = required_dv[min(i, len(required_dv) - 1)]
            if dv_t not in ("numeric",) and expected == "numeric":
                key = (test_type, dv_t, iv_types[0] if iv_types else "unknown")
                alt = ALTERNATIVE_SUGGESTIONS.get(key)
                if alt:
                    return GuardrailResult(
                        passed=False,
                        severity="block",
                        title="⚠️ 变量类型不匹配",
                        message=alt[0],
                        suggested_test_type=alt[1],
                        suggested_test_name=alt[2],
                    )
                return GuardrailResult(
                    passed=False,
                    severity="block",
                    title="⚠️ 变量类型不匹配",
                    message=f"当前检验方法要求因变量为连续数值型，但检测到分类变量。请选择合适的分析方法。",
                )

    # 检查自变量类型
    required_iv = req.get("iv_types", [])
    if required_iv and iv_types:
        for i, iv_t in enumerate(iv_types):
            expected = required_iv[min(i, len(required_iv) - 1)]
            if iv_t not in expected:
                if expected == ["categorical_binary", "categorical_multi"]:
                    return GuardrailResult(
                        passed=False,
                        severity="block",
                        title="⚠️ 分组变量类型不匹配",
                        message=f"该检验要求分组变量为分类变量（如性别、年级），但检测到的变量类型不符合要求。",
                    )

    return GuardrailResult(passed=True, severity="info", title="", message="")


def check_sample_size(
    n: int,
    test_type: str,
) -> GuardrailResult:
    """小样本警告：N<30且参数检验时黄灯"""
    parametric_tests = {
        "independent_ttest", "paired_ttest", "one_sample_ttest",
        "one_way_anova", "two_way_anova", "repeated_anova",
        "pearson_corr", "linear_regression", "multiple_regression",
        "hierarchical_regression", "ancova", "welch_anova",
        "partial_corr",
    }

    if n < 30 and test_type in parametric_tests:
        nonparam_map = {
            "independent_ttest": ("mann_whitney", "Mann-Whitney U 检验"),
            "paired_ttest": ("wilcoxon", "Wilcoxon 符号秩检验"),
            "one_way_anova": ("kruskal_wallis", "Kruskal-Wallis H 检验"),
            "pearson_corr": ("spearman_corr", "Spearman 秩相关"),
            "repeated_anova": ("friedman", "Friedman 检验"),
        }
        alt = nonparam_map.get(test_type)
        if alt:
            return GuardrailResult(
                passed=True,
                severity="warn",
                title=f"⚠️ 小样本警告 (N={n})",
                message=f"当前样本量 N={n} < 30，参数检验的假设可能不满足。建议使用非参数检验或 Bootstrap 方法。",
                suggested_test_type=alt[0],
                suggested_test_name=alt[1],
            )
        return GuardrailResult(
            passed=True,
            severity="warn",
            title=f"⚠️ 小样本警告 (N={n})",
            message=f"当前样本量 N={n} < 30，参数检验的假设可能不满足。建议谨慎解读结果。",
        )

    return GuardrailResult(passed=True, severity="info", title="", message="")


def check_multiple_comparisons(
    analysis_history: List[Dict],
    current_test_type: str,
    dv_vars: List[str],
) -> GuardrailResult:
    """多重比较拦截器：检测连续多次独立t检验或ANOVA事后>5组"""
    if current_test_type not in ("independent_ttest", "mann_whitney"):
        return GuardrailResult(passed=True, severity="info", title="", message="")

    recent_similar = []
    for h in analysis_history[-10:]:
        if h.get("test_type") in ("independent_ttest", "mann_whitney"):
            recent_similar.append(h)

    if len(recent_similar) >= 3:
        all_dvs = set()
        for h in recent_similar:
            all_dvs.update(h.get("dv", []))
        if len(all_dvs) <= 3:
            return GuardrailResult(
                passed=False,
                severity="block",
                title="🚫 多重比较风险 — 一类错误膨胀",
                message=(
                    f"检测到你在短时间内进行了 {len(recent_similar)} 次独立样本t检验（或Mann-Whitney检验），"
                    f"且因变量高度重叠。每次检验有5%的一类错误风险，多次检验会累积错误概率。\n\n"
                    f"**强烈建议：** 使用 Bonferroni 校正（将 α 除以检验次数）或改用单因素方差分析（ANOVA）+ Tukey HSD 事后检验。"
                ),
                suggested_test_type="one_way_anova",
                suggested_test_name="单因素方差分析 (ANOVA)",
            )

    return GuardrailResult(passed=True, severity="info", title="", message="")


def check_effect_size_present(
    output: Dict,
) -> GuardrailResult:
    """检查效应量是否存在于分析结果中。APA7要求必须报告效应量。"""
    result = output.get("result")
    if result is None:
        return GuardrailResult(passed=True, severity="info", title="", message="")

    # 检查常见效应量字段
    effect_fields = [
        "effect_size", "eta_squared", "partial_eta_squared",
        "cohens_d", "hedges_g", "cramers_v", "omega_squared",
        "r_squared", "adj_r_squared",
    ]
    test_type = output.get("test_type", "")

    # 描述性统计不需要效应量
    if test_type == "descriptive":
        return GuardrailResult(passed=True, severity="info", title="", message="")

    found = False
    for field in effect_fields:
        val = getattr(result, field, None)
        if val is not None:
            found = True
            break

    if not found:
        # 检查 output 字典本身的效应量字段
        for k in ["effect_size", "eta_squared", "cohens_d"]:
            if output.get(k) is not None:
                found = True
                break

    if not found:
        return GuardrailResult(
            passed=False,
            severity="block",
            title="🚫 APA 第7版要求报告效应量",
            message=(
                "APA 第7版明确规定：所有推断统计必须报告效应量（如 Cohen's d、η²、Cramér's V 等）。\n"
                "当前分析结果中未检测到效应量字段，无法生成符合 APA7 格式的报告。\n\n"
                "请确认：\n"
                "1. 是否选择了支持效应量计算的统计方法\n"
                "2. 数据是否满足该方法的计算条件"
            ),
        )

    return GuardrailResult(passed=True, severity="info", title="", message="")


def hash_column(df, col_name: str) -> str:
    """对姓名列进行 SHA256 哈希脱敏"""
    import pandas as pd
    hashed = df[col_name].astype(str).apply(
        lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:12]
    )
    return hashed


def detect_name_columns(df) -> List[str]:
    """检测可能的姓名列"""
    import pandas as pd
    name_keywords = ["姓名", "名字", "name", "被试", "学生", "编号", "学号", "ID", "id"]
    candidates = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in name_keywords):
            candidates.append(col)
    return candidates


# v3.9 U5: PII 风险分级
_PII_PATTERNS = {
    "high": {
        "keywords": ["身份证", "身份号", "id_card", "idcard", "护照", "passport",
                     "手机号", "电话", "手机", "phone", "mobile", "tel",
                     "邮箱", "email", "微信", "wechat", "qq",
                     "家庭住址", "住址", "address"],
        "label": "高敏感",
        "advice": "建议直接删除，不留在数据集中。",
    },
    "medium": {
        "keywords": ["姓名", "名字", "fullname", "full_name", "学号",
                     "student_id", "工号", "员工号", "employee_id"],
        "label": "可识别身份",
        "advice": "建议哈希脱敏或匿名化处理（系统在保存档案时会自动哈希）。",
    },
    "low": {
        "keywords": ["被试", "学生", "编号", "subject", "participant", "id"],
        "label": "弱标识符",
        "advice": "通常无害，但建议用纯数字 ID（如 P001、S01）替代真实编号。",
    },
}


def detect_pii_columns(df) -> dict:
    """v3.9 U5: 检测 PII（个人可识别信息）列，按风险分级。

    Returns:
        {"high": [col, ...], "medium": [col, ...], "low": [col, ...], "any": bool}
    """
    result: dict = {"high": [], "medium": [], "low": []}
    cols_lower = {col: str(col).lower() for col in df.columns}
    used = set()  # 同一列只归到最高 severity
    for severity in ("high", "medium", "low"):
        cfg = _PII_PATTERNS[severity]
        for col, lower in cols_lower.items():
            if col in used:
                continue
            for kw in cfg["keywords"]:
                if kw in lower:
                    result[severity].append(col)
                    used.add(col)
                    break
    result["any"] = bool(result["high"] or result["medium"] or result["low"])
    return result


def redact_dataframe_for_storage(df):
    """为档案/作业包生成最小化副本，不修改用户当前 DataFrame。

    高敏感列直接移除；可识别身份与弱标识列做稳定哈希，以保留重复测量/分组关系。
    返回 ``(redacted_df, report)``，便于导出物明确披露处理结果。
    """
    redacted = df.copy()
    pii = detect_pii_columns(redacted)
    dropped = list(pii.get("high", []))
    hashed = list(dict.fromkeys(pii.get("medium", []) + pii.get("low", [])))

    if dropped:
        redacted = redacted.drop(columns=dropped, errors="ignore")
    for column in hashed:
        if column in redacted.columns:
            redacted[column] = hash_column(redacted, column)

    # PII 也可能藏在“备注/说明”等普通文本列中，不能只依赖列名。
    from src.utils.privacy_ethics import redact_sensitive_text
    from pandas.api.types import is_object_dtype, is_string_dtype

    content_redactions: dict[str, int] = {}
    for column in redacted.columns:
        if not (is_object_dtype(redacted[column].dtype) or is_string_dtype(redacted[column].dtype)):
            continue

        def _redact_cell(value):
            if not isinstance(value, str):
                return value
            cleaned, counts = redact_sensitive_text(value)
            for pii_type, count in counts.items():
                key = f"{column}:{pii_type}"
                content_redactions[key] = content_redactions.get(key, 0) + count
            return cleaned

        redacted[column] = redacted[column].map(_redact_cell)

    return redacted, {
        "dropped_high_risk_columns": [str(c) for c in dropped],
        "hashed_identifier_columns": [str(c) for c in hashed],
        "redacted_content_matches": content_redactions,
    }
