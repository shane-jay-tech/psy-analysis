"""测试 v3.7 新增效度方法：CVI / AVE / FL / HTMT / 效标 / 已知组别"""
import pandas as pd
import numpy as np
import pytest

from src.analysis.validity import (
    content_validity_index,
    average_variance_extracted,
    discriminant_fornell_larcker,
    discriminant_htmt,
    criterion_validity,
    known_groups_validity,
    ValidityResult,
)


# ---------------------------------------------------------------------------
# CVI 内容效度指数
# ---------------------------------------------------------------------------
def test_cvi_all_high_ratings():
    """所有专家全打 4 分 → I-CVI = 1.0, S-CVI/Ave = 1.0"""
    ratings = pd.DataFrame(
        np.full((6, 6), 4),  # 6 题 × 6 专家
        index=[f"item{i}" for i in range(1, 7)],
        columns=[f"E{j}" for j in range(1, 7)],
    )
    result = content_validity_index(ratings)
    assert isinstance(result, ValidityResult)
    assert result.test_type == "cvi"
    assert result.main_value == 1.0
    assert result.warning == ""
    assert (result.detail["I-CVI"] == 1.0).all()


def test_cvi_low_ratings_warn():
    """部分题目低相关 → 警告非空"""
    np.random.seed(42)
    n_items, n_experts = 5, 6
    ratings = pd.DataFrame(
        np.random.choice([1, 2], size=(n_items, n_experts)),
        index=[f"item{i}" for i in range(1, n_items + 1)],
        columns=[f"E{j}" for j in range(1, n_experts + 1)],
    )
    result = content_validity_index(ratings)
    assert result.main_value < 0.78
    assert "⚠" in result.warning


def test_cvi_too_few_experts():
    """专家数 < 3 应拒绝"""
    ratings = pd.DataFrame({"E1": [4, 4], "E2": [3, 4]})
    with pytest.raises(ValueError):
        content_validity_index(ratings)


# ---------------------------------------------------------------------------
# AVE 平均方差抽取量
# ---------------------------------------------------------------------------
def test_ave_high_loadings_pass():
    """高载荷因子 AVE > 0.5"""
    loadings = pd.DataFrame({
        "因子": ["F1"] * 4 + ["F2"] * 3,
        "题目": ["a1", "a2", "a3", "a4", "b1", "b2", "b3"],
        "标准化载荷": [0.85, 0.80, 0.78, 0.82, 0.90, 0.75, 0.83],
    })
    result = average_variance_extracted(loadings)
    assert result.test_type == "ave"
    assert result.main_value > 0.5
    assert (result.detail["AVE"] > 0.5).all()


def test_ave_low_loadings_warn():
    """低载荷 → AVE < 0.5，触发警告"""
    loadings = pd.DataFrame({
        "因子": ["F1"] * 3,
        "题目": ["a1", "a2", "a3"],
        "标准化载荷": [0.40, 0.35, 0.45],
    })
    result = average_variance_extracted(loadings)
    assert result.main_value < 0.5
    assert "⚠" in result.warning


def test_ave_english_columns():
    """英文列名兼容"""
    loadings = pd.DataFrame({
        "factor": ["F1"] * 3,
        "item": ["x1", "x2", "x3"],
        "loading": [0.80, 0.75, 0.85],
    })
    result = average_variance_extracted(loadings)
    assert result.main_value > 0.5


# ---------------------------------------------------------------------------
# Fornell-Larcker 区分效度
# ---------------------------------------------------------------------------
def test_fornell_larcker_pass():
    """高 AVE + 低因子相关 → 通过"""
    ave = {"F1": 0.65, "F2": 0.60, "F3": 0.55}
    corr = pd.DataFrame(
        [[1.0, 0.30, 0.25],
         [0.30, 1.0, 0.20],
         [0.25, 0.20, 1.0]],
        index=["F1", "F2", "F3"], columns=["F1", "F2", "F3"],
    )
    result = discriminant_fornell_larcker(ave, corr)
    assert result.fornell_larcker_pass is True
    assert result.main_value == 1.0


def test_fornell_larcker_fail():
    """低 AVE + 高因子相关 → 违例"""
    ave = {"F1": 0.30, "F2": 0.30}
    corr = pd.DataFrame(
        [[1.0, 0.80], [0.80, 1.0]],
        index=["F1", "F2"], columns=["F1", "F2"],
    )
    result = discriminant_fornell_larcker(ave, corr)
    assert result.fornell_larcker_pass is False
    assert "⚠" in result.warning


# ---------------------------------------------------------------------------
# HTMT 区分效度
# ---------------------------------------------------------------------------
def test_htmt_distinct_factors_pass():
    """两个独立潜变量，HTMT 应低"""
    np.random.seed(42)
    n = 200
    f1 = np.random.normal(0, 1, n)
    f2 = np.random.normal(0, 1, n)
    data = {}
    for i in range(1, 4):
        data[f"a{i}"] = f1 + np.random.normal(0, 0.4, n)
        data[f"b{i}"] = f2 + np.random.normal(0, 0.4, n)
    df = pd.DataFrame(data)
    factors = {"F1": ["a1", "a2", "a3"], "F2": ["b1", "b2", "b3"]}
    result = discriminant_htmt(df, factors)
    assert result.test_type == "discriminant_htmt"
    assert result.main_value < 0.85
    assert result.fornell_larcker_pass is True


def test_htmt_overlapping_factors_warn():
    """两个因子高度重叠 → HTMT 超阈值"""
    np.random.seed(42)
    n = 200
    shared = np.random.normal(0, 1, n)
    data = {}
    for i in range(1, 4):
        data[f"a{i}"] = shared + np.random.normal(0, 0.3, n)
        data[f"b{i}"] = shared + np.random.normal(0, 0.3, n)
    df = pd.DataFrame(data)
    factors = {"F1": ["a1", "a2", "a3"], "F2": ["b1", "b2", "b3"]}
    result = discriminant_htmt(df, factors, threshold=0.85)
    assert result.main_value > 0.85
    assert "⚠" in result.warning


# ---------------------------------------------------------------------------
# 效标效度
# ---------------------------------------------------------------------------
def test_criterion_validity_concurrent():
    """量表总分与效标高度相关 → r > 0.5"""
    np.random.seed(42)
    n = 150
    latent = np.random.normal(0, 1, n)
    items = {f"q{i}": latent + np.random.normal(0, 0.5, n) for i in range(1, 6)}
    df = pd.DataFrame(items)
    df["criterion"] = latent + np.random.normal(0, 0.4, n)
    result = criterion_validity(df, list(items.keys()), "criterion", kind="concurrent")
    assert result.test_type == "criterion_validity"
    assert result.criterion_r is not None
    assert result.criterion_r > 0.5
    assert result.criterion_p < 0.05


def test_criterion_validity_invalid_kind():
    df = pd.DataFrame({"q1": [1, 2, 3], "c": [1, 2, 3]})
    with pytest.raises(ValueError):
        criterion_validity(df, ["q1"], "c", kind="bogus")


# ---------------------------------------------------------------------------
# 已知组别效度
# ---------------------------------------------------------------------------
def test_known_groups_two_groups_significant():
    """两组分数有真实差异 → t 检验显著"""
    np.random.seed(42)
    n = 60
    data = pd.DataFrame({
        f"q{i}": np.concatenate([
            np.random.normal(3.5, 0.8, n),  # 组 A
            np.random.normal(2.0, 0.8, n),  # 组 B
        ])
        for i in range(1, 5)
    })
    data["group"] = ["A"] * n + ["B"] * n
    result = known_groups_validity(data, [f"q{i}" for i in range(1, 5)], "group")
    assert result.test_type == "known_groups_validity"
    assert result.known_groups_test == "ttest"
    assert result.known_groups_p < 0.05
    assert result.known_groups_effect_name == "Cohen's d"
    assert result.known_groups_effect_size > 0.5


def test_known_groups_three_groups_anova():
    """三组使用 ANOVA + η²"""
    np.random.seed(42)
    n = 40
    data = pd.DataFrame({
        f"q{i}": np.concatenate([
            np.random.normal(2, 0.8, n),
            np.random.normal(3, 0.8, n),
            np.random.normal(4, 0.8, n),
        ])
        for i in range(1, 4)
    })
    data["group"] = ["低"] * n + ["中"] * n + ["高"] * n
    result = known_groups_validity(data, [f"q{i}" for i in range(1, 4)], "group")
    assert result.known_groups_test == "anova"
    assert result.known_groups_effect_name == "η²"
    assert result.known_groups_p < 0.05


# ---------------------------------------------------------------------------
# CFA 整合 AVE/CR/HTMT 验证
# ---------------------------------------------------------------------------
def test_cfa_integrates_validity_metrics():
    """CFA 跑完后顺手返回 ave_per_factor / cr_per_factor / htmt_matrix"""
    from src.analysis.cfa import confirmatory_factor_analysis

    np.random.seed(42)
    n = 200
    f1 = np.random.normal(0, 1, n)
    f2 = np.random.normal(0, 1, n)
    data = {}
    for i in range(1, 4):
        data[f"a{i}"] = f1 + np.random.normal(0, 0.4, n)
        data[f"b{i}"] = f2 + np.random.normal(0, 0.4, n)
    df = pd.DataFrame(data)
    factors = {"焦虑": ["a1", "a2", "a3"], "抑郁": ["b1", "b2", "b3"]}

    result = confirmatory_factor_analysis(df, factors)
    # 三个新字段应存在（即便 semopy 失败也走 fallback 计算）
    assert result.ave_per_factor is not None
    assert result.cr_per_factor is not None
    assert result.htmt_matrix is not None
    assert set(result.ave_per_factor.keys()) == {"焦虑", "抑郁"}
