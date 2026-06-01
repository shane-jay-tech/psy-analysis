"""HR / People Analytics demo 数据集测试

覆盖：
- 4 个生成函数的形状、列结构、数据类型
- seed 可复现性
- 缺失值注入合理性
- 业务关系正确性（敬业度 vs 离职意愿负相关、实验组提升大于对照组等）
- HR_DATASET_CATALOG 元信息完整
- KB 新增构念（工作满意度/离职意愿）的 schema 完整性
"""

import numpy as np
import pandas as pd
import pytest

from src.data.demo_datasets_hr import (
    generate_demo_engagement_data,
    generate_demo_performance_data,
    generate_demo_turnover_data,
    generate_demo_360_review_data,
    list_hr_datasets,
    HR_DATASET_CATALOG,
    DEPARTMENTS, LEVELS, PERF_RATINGS,
)
from src.questionnaire.construct_kb import (
    CONSTRUCTS, CONSTRUCT_KEYWORDS, DOMAIN_KEYWORDS,
)


# ── 敬业度调研 ─────────────────────────────────────────────────────


def test_engagement_shape_default():
    df = generate_demo_engagement_data()
    assert len(df) == 300
    assert df.shape[1] == 18  # 6 基础 + 9 UWES + 总分 + 离职意愿 + 加班


def test_engagement_columns_present():
    df = generate_demo_engagement_data(50)
    expected = {
        "员工ID", "部门", "司龄_年", "职级", "年龄", "性别",
        "活力1", "活力2", "活力3",
        "奉献1", "奉献2", "奉献3",
        "专注1", "专注2", "专注3",
        "工作投入_总分", "离职意愿", "周均加班小时",
    }
    assert expected.issubset(set(df.columns))


def test_engagement_reproducible():
    df1 = generate_demo_engagement_data(100, seed=42)
    df2 = generate_demo_engagement_data(100, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_engagement_uwes_range():
    df = generate_demo_engagement_data(200)
    for col in ["活力1", "活力3", "奉献1", "专注1"]:
        valid = df[col].dropna()
        assert valid.min() >= 1
        assert valid.max() <= 7


def test_engagement_dept_in_whitelist():
    df = generate_demo_engagement_data(300)
    assert set(df["部门"].unique()).issubset(set(DEPARTMENTS))


def test_engagement_turnover_negatively_correlated():
    """敬业度总分应与离职意愿负相关"""
    df = generate_demo_engagement_data(300)
    valid = df.dropna(subset=["工作投入_总分", "离职意愿"])
    r = valid["工作投入_总分"].corr(valid["离职意愿"])
    assert r < -0.2, f"expected negative correlation, got r={r}"


def test_engagement_has_missing():
    df = generate_demo_engagement_data(300)
    # 至少一列含缺失（注入率 ~3%）
    has_na = df.isna().any().any()
    assert has_na


# ── 培训效果 ───────────────────────────────────────────────────────


def test_performance_shape():
    df = generate_demo_performance_data(50)
    assert len(df) == 100
    expected = {
        "员工ID", "组别", "部门",
        "前测_KPI得分", "后测_KPI得分",
        "前测_技能评估", "后测_技能评估",
        "参与培训时长_小时", "年龄", "性别",
    }
    assert expected.issubset(set(df.columns))


def test_performance_groups_balanced():
    df = generate_demo_performance_data(50)
    counts = df["组别"].value_counts().to_dict()
    assert counts["实验组"] == 50
    assert counts["对照组"] == 50


def test_performance_reproducible():
    df1 = generate_demo_performance_data(40, seed=42)
    df2 = generate_demo_performance_data(40, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_performance_treatment_effect_positive():
    """实验组 KPI 提升应显著大于对照组"""
    df = generate_demo_performance_data(50)
    df["KPI变化"] = df["后测_KPI得分"] - df["前测_KPI得分"]
    treat_gain = df.loc[df["组别"] == "实验组", "KPI变化"].mean()
    ctrl_gain = df.loc[df["组别"] == "对照组", "KPI变化"].mean()
    assert treat_gain - ctrl_gain > 4, \
        f"treat={treat_gain:.2f}, ctrl={ctrl_gain:.2f}"


def test_performance_control_no_training():
    """对照组培训时长应为 0"""
    df = generate_demo_performance_data(50)
    ctrl_hours = df.loc[df["组别"] == "对照组", "参与培训时长_小时"]
    assert (ctrl_hours == 0).all()


# ── 离职预测 ───────────────────────────────────────────────────────


def test_turnover_shape():
    df = generate_demo_turnover_data()
    assert len(df) == 500
    expected = {
        "员工ID", "司龄_年", "年龄", "性别", "部门", "职级",
        "近12月加薪幅度_pct", "近6月周均加班_小时",
        "上司满意度", "近一年绩效评级", "通勤时间_分钟", "已离职",
    }
    assert expected.issubset(set(df.columns))


def test_turnover_binary_outcome():
    df = generate_demo_turnover_data(200)
    assert set(df["已离职"].unique()).issubset({0, 1})


def test_turnover_rate_realistic():
    """离职率应在 5%-40% 区间（业务合理范围）"""
    df = generate_demo_turnover_data(500)
    rate = df["已离职"].mean()
    assert 0.05 <= rate <= 0.40, f"turnover rate={rate}"


def test_turnover_boss_satisfaction_signal():
    """上司满意度低的员工离职率应明显高于满意度高的"""
    df = generate_demo_turnover_data(500)
    low = df.loc[df["上司满意度"] <= 2, "已离职"].mean()
    high = df.loc[df["上司满意度"] >= 4, "已离职"].mean()
    assert low > high, f"low={low}, high={high}"


def test_turnover_perf_in_whitelist():
    df = generate_demo_turnover_data()
    assert set(df["近一年绩效评级"].unique()).issubset(set(PERF_RATINGS))


def test_turnover_reproducible():
    df1 = generate_demo_turnover_data(100, seed=42)
    df2 = generate_demo_turnover_data(100, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


# ── 360 评估 ───────────────────────────────────────────────────────


def test_360_shape():
    df = generate_demo_360_review_data()
    assert len(df) == 80
    # 4 基础列 + 4 维度 × 4 来源 = 20 列
    assert df.shape[1] == 20


def test_360_columns_structure():
    df = generate_demo_360_review_data(50)
    dims = ["领导力", "专业能力", "协作能力", "创新能力"]
    sources = ["自评", "上级评", "同事评", "下级评"]
    for s in sources:
        for d in dims:
            assert f"{s}_{d}" in df.columns


def test_360_subordinate_has_nan():
    """下级评应有 NaN（部分员工无下级）"""
    df = generate_demo_360_review_data(80)
    sub_cols = [c for c in df.columns if c.startswith("下级评_")]
    for col in sub_cols:
        assert df[col].isna().sum() > 0


def test_360_reproducible():
    df1 = generate_demo_360_review_data(40, seed=42)
    df2 = generate_demo_360_review_data(40, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_360_self_boss_bias_for_new_managers():
    """新经理应表现出自评 > 上级评的偏差"""
    df = generate_demo_360_review_data(200)
    new_mgrs = df[df["是否新经理"] == 1]
    self_avg = new_mgrs[[c for c in df.columns if c.startswith("自评_")]].mean(axis=1).mean()
    boss_avg = new_mgrs[[c for c in df.columns if c.startswith("上级评_")]].mean(axis=1).mean()
    assert self_avg > boss_avg, f"self={self_avg}, boss={boss_avg}"


# ── Catalog 元信息 ─────────────────────────────────────────────────


def test_catalog_has_4_entries():
    cat = list_hr_datasets()
    assert len(cat) == 4


def test_catalog_keys_unique():
    cat = list_hr_datasets()
    keys = [s["key"] for s in cat]
    assert len(set(keys)) == len(keys)


def test_catalog_loaders_callable():
    cat = list_hr_datasets()
    for spec in cat:
        df = spec["loader"]()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


def test_catalog_has_required_fields():
    cat = list_hr_datasets()
    for spec in cat:
        for field in ["key", "title", "n", "loader", "description", "scenarios", "core_methods"]:
            assert field in spec, f"missing {field} in {spec.get('key')}"


# ── 新增 KB 构念 ───────────────────────────────────────────────────


def test_kb_has_job_satisfaction():
    assert "工作满意度" in CONSTRUCTS
    c = CONSTRUCTS["工作满意度"]
    assert c["domain"] == "组织行为"
    assert len(c["dimensions"]) >= 3
    assert any("JSS" in s or "Spector" in s for s in c["established_scales"])


def test_kb_has_turnover_intention():
    assert "离职意愿" in CONSTRUCTS
    c = CONSTRUCTS["离职意愿"]
    assert c["domain"] == "组织行为"
    assert len(c["dimensions"]) >= 2
    assert any("TIS" in s or "Bothma" in s for s in c["established_scales"])


def test_kb_keywords_updated():
    assert "工作满意度" in CONSTRUCT_KEYWORDS
    assert "离职意愿" in CONSTRUCT_KEYWORDS
    org_kws = DOMAIN_KEYWORDS["组织行为"]
    assert "工作满意度" in org_kws
    assert "离职意愿" in org_kws


def test_kb_new_constructs_have_references():
    for name in ["工作满意度", "离职意愿"]:
        refs = CONSTRUCTS[name]["references"]
        assert len(refs) >= 1
        # 至少一条引用包含年份和作者
        assert any("(" in r and ")" in r for r in refs)
