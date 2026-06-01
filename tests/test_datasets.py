"""真实数据集的回归测试 (Task 14)

数据集来源：
  1. 模拟经典心理学研究数据（基于已发表研究的描述统计）
  2. 所有数据均为人工生成，但参数基于真实研究
"""

import pandas as pd
import numpy as np


def make_performance_feedback_data(n: int = 80, seed: int = 42) -> pd.DataFrame:
    """
    模拟「反馈类型对任务表现的影响」实验数据。

    设计：单因素被试间，3水平（积极反馈/消极反馈/无反馈）
    DV：任务正确率 + 反应时
    参数基于 Kluger & DeNisi (1996) 元分析的效应量范围。
    """
    rng = np.random.default_rng(seed)

    # 确保每组等量
    n_per = n // 3
    n_actual = n_per * 3

    conditions = np.array(
        ["积极反馈"] * n_per + ["消极反馈"] * n_per + ["无反馈"] * n_per
    )

    accuracy = np.concatenate([
        rng.normal(0.82, 0.08, n_per),   # 积极反馈
        rng.normal(0.70, 0.10, n_per),   # 消极反馈
        rng.normal(0.75, 0.09, n_per),   # 无反馈
    ])

    rt = np.concatenate([
        rng.normal(450, 60, n_per),       # 积极反馈 → 较快
        rng.normal(520, 75, n_per),       # 消极反馈 → 较慢
        rng.normal(490, 65, n_per),
    ])

    self_efficacy = np.concatenate([
        rng.normal(4.2, 0.8, n_per),
        rng.normal(3.1, 0.9, n_per),
        rng.normal(3.6, 0.7, n_per),
    ])

    return pd.DataFrame({
        "condition": conditions,
        "accuracy": np.round(accuracy, 3),
        "reaction_time": np.round(rt, 1),
        "self_efficacy": np.round(self_efficacy, 1),
        "age": rng.integers(18, 26, n_actual),
        "gender": rng.choice(["男", "女"], n_actual),
    })


def make_mediation_data(n: int = 150, seed: int = 123) -> pd.DataFrame:
    """
    模拟「工作压力 → 心理倦怠 → 离职意向」中介模型数据。

    参数基于 Schaufeli & Bakker (2004) 等经典研究，
    效应量范围参考 Alarcon (2011) 元分析。
    """
    rng = np.random.default_rng(seed)

    stress = rng.normal(3.0, 0.8, n)           # 工作压力 (1-5)
    burnout = 0.45 * stress + rng.normal(0, 0.65, n)  # 心理倦怠 (b1路径)
    turnover = 0.30 * stress + 0.50 * burnout + rng.normal(0, 0.55, n)  # 离职意向

    neuroticism = rng.normal(3.0, 0.7, n)       # 协变量: 神经质

    return pd.DataFrame({
        "work_stress": np.round(stress, 2),
        "burnout": np.round(burnout, 2),
        "turnover_intention": np.round(turnover, 2),
        "neuroticism": np.round(neuroticism, 2),
        "age": rng.integers(22, 56, n),
        "tenure_years": rng.integers(0, 15, n),
    })


def make_moderation_data(n: int = 120, seed: int = 456) -> pd.DataFrame:
    """
    模拟「社会支持在压力→抑郁关系中的调节效应」数据。

    参数基于 Cohen & Wills (1985) 缓冲假说，
    效应量参考 Rueger et al. (2016) 元分析。
    """
    rng = np.random.default_rng(seed)

    stress = rng.normal(0, 1, n)
    social_support = rng.normal(0, 1, n)
    # 交互效应: 高社会支持减弱压力对抑郁的影响
    interaction = stress * social_support
    depression = (
        0.35 * stress
        - 0.25 * social_support
        + 0.15 * interaction     # 交互项
        + rng.normal(0, 0.5, n)
    )

    return pd.DataFrame({
        "stress": np.round(stress, 2),
        "social_support": np.round(social_support, 2),
        "depression": np.round(depression, 2),
        "gender": rng.choice(["男", "女"], n),
    })


def make_reliability_data(n: int = 200, seed: int = 789) -> pd.DataFrame:
    """
    模拟「心理幸福感量表」数据（6个维度 × 4题 = 24题）。

    参数基于 Ryff (1989) 心理幸福感模型，
    信度范围参考 Ryff & Keyes (1995)。
    6个维度：自我接纳、积极关系、自主性、环境掌控、
            人生目标、个人成长
    每个维度4题，含反向题。
    """
    rng = np.random.default_rng(seed)

    # 6个潜在因子（维度分数）
    n_factors = 6
    factors = rng.normal(0, 1, (n, n_factors))
    # 因子间相关 ~0.3-0.6
    factor_corr = np.array([
        [1.0, 0.5, 0.3, 0.4, 0.5, 0.4],
        [0.5, 1.0, 0.3, 0.4, 0.4, 0.3],
        [0.3, 0.3, 1.0, 0.5, 0.3, 0.4],
        [0.4, 0.4, 0.5, 1.0, 0.4, 0.3],
        [0.5, 0.4, 0.3, 0.4, 1.0, 0.5],
        [0.4, 0.3, 0.4, 0.3, 0.5, 1.0],
    ])
    # Cholesky 分解使因子相关
    L = np.linalg.cholesky(factor_corr)
    factors_corr = factors @ L.T

    dim_names = ["自我接纳", "积极关系", "自主性", "环境掌控", "人生目标", "个人成长"]
    items_per_dim = 4
    total_items = n_factors * items_per_dim

    loadings = rng.uniform(0.5, 0.85, total_items)  # 载荷
    items = np.zeros((n, total_items))

    col_names = []
    for d in range(n_factors):
        for i in range(items_per_dim):
            col_idx = d * items_per_dim + i
            items[:, col_idx] = (
                loadings[col_idx] * factors_corr[:, d]
                + rng.normal(0, np.sqrt(1 - loadings[col_idx] ** 2), n)
            )
            col_names.append(f"{dim_names[d]}_{i+1}")

    # 添加反向题标记（每个维度1个反向题）
    rev_cols = set()
    for d in range(n_factors):
        rev_idx = d * items_per_dim  # 每个维度第1题为反向
        items[:, rev_idx] = 6 - items[:, rev_idx]  # 反向：高分→低分
        rev_cols.add(col_names[rev_idx])

    # 转换为1-6的范围
    for j in range(total_items):
        items[:, j] = np.clip(np.round(items[:, j] + 3.5), 1, 6)

    df = pd.DataFrame(items, columns=col_names)
    df["age"] = rng.integers(18, 65, n)
    df["gender"] = rng.choice(["男", "女"], n)

    # 附加元数据
    df.attrs["dimensions"] = dim_names
    df.attrs["items_per_dim"] = items_per_dim
    df.attrs["reversed_items"] = list(rev_cols)
    df.attrs["expected_alpha"] = "0.80-0.90"
    df.attrs["source"] = "模拟数据，参数基于 Ryff (1989) 心理幸福感模型"

    return df


def make_longitudinal_data(n: int = 60, seed: int = 999) -> pd.DataFrame:
    """
    模拟「正念干预对焦虑水平影响」的2×2重复测量数据。

    设计：2(时间: T1/T2) × 2(组别: 干预/对照)
    参数基于 Hofmann et al. (2010) 元分析（d ≈ 0.50-0.63）。
    """
    rng = np.random.default_rng(seed)
    groups = np.repeat(["干预组", "对照组"], n // 2)

    # 基线焦虑
    anxiety_t1 = rng.normal(25, 5, n)

    # T2: 干预组下降 ~6分 (d≈0.5)
    anxiety_t2 = np.where(
        groups == "干预组",
        anxiety_t1 - rng.normal(6, 4, n),
        anxiety_t1 - rng.normal(1, 3, n),
    )

    # 正念水平 (FFMQ)
    mindfulness_t1 = rng.normal(120, 15, n)
    mindfulness_t2 = np.where(
        groups == "干预组",
        mindfulness_t1 + rng.normal(12, 8, n),
        mindfulness_t1 + rng.normal(1, 5, n),
    )

    return pd.DataFrame({
        "id": np.arange(1, n + 1),
        "group": groups,
        "anxiety_t1": np.round(anxiety_t1, 2),
        "anxiety_t2": np.round(anxiety_t2, 2),
        "mindfulness_t1": np.round(mindfulness_t1, 1),
        "mindfulness_t2": np.round(mindfulness_t2, 1),
        "age": rng.integers(18, 45, n),
        "gender": rng.choice(["男", "女"], n),
    })


def make_all_test_datasets() -> dict:
    """生成所有测试数据集"""
    return {
        "performance_feedback": make_performance_feedback_data(),
        "mediation": make_mediation_data(),
        "moderation": make_moderation_data(),
        "reliability": make_reliability_data(),
        "longitudinal": make_longitudinal_data(),
    }
