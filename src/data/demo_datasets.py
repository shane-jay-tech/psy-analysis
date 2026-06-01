"""演示数据集 — 为本科向导模式提供示例数据

生成两组模拟数据：
1. 问卷示例：200名被试的社交焦虑问卷数据
2. 实验示例：80名被试的认知实验数据（控制组/实验组，前测/后测）
"""

import numpy as np
import pandas as pd


def generate_demo_questionnaire_data(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """生成模拟社交焦虑问卷数据

    返回列：
        - 性别: 男/女
        - 年级: 大一/大二/大三/大四
        - 年龄: 18-24
        - 社交焦虑总分: SIAS 模拟分数 (0-68)
        - 紧张维度: 社交焦虑的紧张分量表
        - 回避维度: 社交焦虑的回避分量表
        - 生理维度: 社交焦虑的生理反应分量表
        - 自尊总分: SES 模拟分数 (10-40)
        - 自我接纳: 自尊子维度
        - 自我价值: 自尊子维度
    """
    rng = np.random.default_rng(seed)

    gender = rng.choice(["男", "女"], n, p=[0.45, 0.55])
    grade = rng.choice(["大一", "大二", "大三", "大四"], n)
    age = rng.integers(18, 25, n)

    # 社交焦虑总分 (SIAS模拟, 范围0-68, 均值~35)
    anxiety_total = np.clip(rng.normal(35, 12, n), 5, 65).round(1)
    # 各维度：与总分的相关 ~0.7-0.85
    tension = np.clip(anxiety_total * 0.38 + rng.normal(0, 3, n), 2, 24).round(1)
    avoidance = np.clip(anxiety_total * 0.35 + rng.normal(0, 3, n), 2, 24).round(1)
    physiology = np.clip(anxiety_total * 0.28 + rng.normal(0, 3, n), 1, 20).round(1)

    # 自尊总分 (SES模拟, 范围10-40, 均值~28, 与焦虑负相关)
    self_esteem = np.clip(40 - anxiety_total * 0.35 + rng.normal(0, 4, n), 10, 40).round(1)
    self_acceptance = np.clip(self_esteem * 0.55 + rng.normal(0, 2, n), 5, 22).round(1)
    self_worth = np.clip(self_esteem * 0.45 + rng.normal(0, 2, n), 5, 18).round(1)

    # 添加一些缺失值（模拟真实数据 ~3%）
    for col_idx in [3, 4, 7]:
        mask = rng.random(n) < 0.03
        if col_idx == 3:
            anxiety_total[mask] = np.nan
        elif col_idx == 4:
            tension[mask] = np.nan
        elif col_idx == 7:
            self_esteem[mask] = np.nan

    return pd.DataFrame({
        "性别": gender,
        "年级": grade,
        "年龄": age,
        "社交焦虑总分": anxiety_total,
        "紧张维度": tension,
        "回避维度": avoidance,
        "生理维度": physiology,
        "自尊总分": self_esteem,
        "自我接纳": self_acceptance,
        "自我价值": self_worth,
    })


def generate_demo_experiment_data(n_per_group: int = 40, seed: int = 42) -> pd.DataFrame:
    """生成模拟认知实验数据（前测-后测设计）

    返回列：
        - 被试编号: 1-80
        - 组别: 实验组/控制组
        - 前测_记忆成绩: 干预前记忆测验分数 (0-100)
        - 后测_记忆成绩: 干预后记忆测验分数 (0-100)
        - 前测_反应时: 干预前反应时(ms)
        - 后测_反应时: 干预后反应时(ms)
        - 年龄: 18-26
        - 性别: 男/女
    """
    rng = np.random.default_rng(seed)
    n = n_per_group * 2

    group = ["实验组"] * n_per_group + ["控制组"] * n_per_group

    # 前测：两组基线相同
    pre_memory = np.clip(rng.normal(65, 10, n), 30, 95).round(1)
    # 实验组后测提升8分，控制组提升1分
    post_memory = np.where(
        np.array(group) == "实验组",
        np.clip(pre_memory + rng.normal(8, 5, n), 35, 100),
        np.clip(pre_memory + rng.normal(1, 4, n), 35, 100),
    ).round(1)

    pre_rt = np.clip(rng.normal(520, 80, n), 300, 800).round(0).astype(int)
    post_rt = np.where(
        np.array(group) == "实验组",
        np.clip(pre_rt - rng.normal(50, 30, n), 250, 750).round(0).astype(int),
        np.clip(pre_rt - rng.normal(5, 25, n), 280, 780).round(0).astype(int),
    )

    age = rng.integers(18, 27, n)
    gender = rng.choice(["男", "女"], n)

    return pd.DataFrame({
        "被试编号": range(1, n + 1),
        "组别": group,
        "前测_记忆成绩": pre_memory,
        "后测_记忆成绩": post_memory,
        "前测_反应时": pre_rt,
        "后测_反应时": post_rt,
        "年龄": age,
        "性别": gender,
    })


def generate_demo_repeated_measures_data(n: int = 50, seed: int = 42) -> pd.DataFrame:
    """生成模拟重复测量数据（3个时间点）

    返回列：ID, T1_焦虑, T2_焦虑, T3_焦虑, 组别
    """
    rng = np.random.default_rng(seed)
    t1 = np.clip(rng.normal(28, 6, n), 10, 40).round(1)
    t2 = np.clip(t1 + rng.normal(-3, 4, n), 8, 40).round(1)
    t3 = np.clip(t2 + rng.normal(-2, 3, n), 5, 40).round(1)
    group = rng.choice(["实验组", "控制组"], n)
    return pd.DataFrame({
        "ID": range(1, n + 1),
        "T1_焦虑": t1, "T2_焦虑": t2, "T3_焦虑": t3,
        "组别": group,
    })


def generate_demo_multi_group_data(n_per_group: int = 30, seed: int = 42) -> pd.DataFrame:
    """生成模拟多组独立干预数据（4组）

    返回列：组别, 前测成绩, 后测成绩
    """
    rng = np.random.default_rng(seed)
    groups = ["A组(对照)", "B组(方法一)", "C组(方法二)", "D组(方法三)"]
    n = n_per_group * 4
    pre = np.clip(rng.normal(62, 8, n), 30, 90).round(1)
    means = [62, 70, 75, 80]
    post = np.concatenate([
        np.clip(rng.normal(means[i], 8, n_per_group), 35, 100)
        for i in range(4)
    ]).round(1)
    group_labels = []
    for i, g in enumerate(groups):
        group_labels.extend([g] * n_per_group)
    return pd.DataFrame({
        "组别": group_labels,
        "前测成绩": pre,
        "后测成绩": post,
    })


def generate_demo_mediation_data(n: int = 150, seed: int = 42) -> pd.DataFrame:
    """生成模拟中介效应数据（X→M→Y, ab路径显著）

    返回列：培训(X), 学习动机(M), 学业成绩(Y)
    """
    rng = np.random.default_rng(seed)
    x = rng.choice([0, 1], n)
    m = np.clip(3.5 + 1.0 * x + rng.normal(0, 0.8, n), 1, 7).round(2)
    y = np.clip(50 + 3.0 * x + 5.0 * m + rng.normal(0, 5, n), 0, 100).round(1)
    return pd.DataFrame({
        "培训": x,
        "学习动机": m,
        "学业成绩": y,
    })
