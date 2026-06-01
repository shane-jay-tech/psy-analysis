"""HR / People Analytics 演示数据集

面向 People Analytics 学习与作品集场景。生成 4 组模拟 HR 数据：

1. 敬业度调研（UWES-9 + 离职意愿 + 加班 + 部门 + 司龄）— 信效度检验、回归、ANOVA
2. 培训效果（前-后测，实验/对照）— 配对 t、独立 t、ANCOVA
3. 离职预测（500 人 binary outcome）— 卡方、Logistic 回归
4. 360 度评估（自评/上级/同事/下级）— 信度、ICC、配对偏差检验

所有函数 seed=42 默认可复现，约 3% 缺失模拟真实情况。

故事线（用于 SOP / 作品集说明）：
- 敬业度数据展示心理测量信效度全套能力
- 培训数据展示因果推断与效应量解读能力
- 离职数据展示分类预测与特征筛选能力
- 360 数据展示评分者一致性与偏差量化能力
"""

import numpy as np
import pandas as pd


DEPARTMENTS = ["研发", "策划", "美术", "运营", "HR", "市场"]
LEVELS = ["P3", "P4", "P5", "P6", "P7"]
PERF_RATINGS = ["A", "B", "C", "D"]


def generate_demo_engagement_data(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """游戏公司全员敬业度调研模拟数据

    列结构（19 列）：
        - 员工ID, 部门, 司龄_年, 职级, 年龄, 性别
        - UWES-9 九题：活力1-3, 奉献1-3, 专注1-3（1-7 李克特）
        - 工作投入_总分（9 题求和，9-63）
        - 离职意愿（单题 1-5）
        - 周均加班小时

    设计要点：
        - 敬业度与离职意愿负相关 r ≈ -0.5
        - 司龄 ≤ 1 年员工敬业度显著低（新员工融入问题）
        - 加班 vs 敬业度呈倒 U 型（适度挑战 vs 过劳）
        - HR/市场部门敬业度略高，研发略低（行业经验）
    """
    rng = np.random.default_rng(seed)

    emp_id = np.arange(1, n + 1)
    dept = rng.choice(DEPARTMENTS, n, p=[0.30, 0.15, 0.15, 0.20, 0.08, 0.12])
    tenure = np.clip(rng.exponential(3.0, n), 0.5, 12.0).round(1)
    level = rng.choice(LEVELS, n, p=[0.20, 0.30, 0.25, 0.15, 0.10])
    age = np.clip(22 + tenure * 1.5 + rng.normal(0, 4, n), 22, 50).round(0).astype(int)
    gender = rng.choice(["男", "女"], n, p=[0.62, 0.38])

    # 部门基线敬业度（HR/市场略高，研发略低）
    dept_baseline = np.array([
        {"研发": 4.2, "策划": 4.6, "美术": 4.7, "运营": 4.5, "HR": 4.9, "市场": 4.8}[d]
        for d in dept
    ])
    # 新员工（≤1年）敬业度较低
    tenure_effect = np.where(tenure <= 1.0, -0.6, 0.1 * np.log(tenure + 1))
    # 加班的倒 U 型效应
    overtime_hours = np.clip(rng.gamma(2.0, 3.5, n), 0, 30).round(1)
    overtime_effect = -0.0015 * (overtime_hours - 12) ** 2 + 0.18

    base_engagement = dept_baseline + tenure_effect + overtime_effect

    # UWES-9 三维度，每维度 3 题（1-7 李克特，加随机噪声）
    def gen_dim(mean_offset, item_count=3):
        items = []
        for _ in range(item_count):
            score = np.clip(base_engagement + mean_offset + rng.normal(0, 0.9, n), 1, 7).round(0).astype(int)
            items.append(score)
        return items

    vigor_items = gen_dim(0.0)
    dedication_items = gen_dim(0.2)
    absorption_items = gen_dim(-0.1)

    total_engagement = sum(vigor_items) + sum(dedication_items) + sum(absorption_items)

    # 离职意愿与敬业度负相关
    turnover_intent = np.clip(
        6.0 - 0.07 * total_engagement + rng.normal(0, 0.7, n),
        1, 5
    ).round(0).astype(int)

    df = pd.DataFrame({
        "员工ID": emp_id,
        "部门": dept,
        "司龄_年": tenure,
        "职级": level,
        "年龄": age,
        "性别": gender,
        "活力1": vigor_items[0], "活力2": vigor_items[1], "活力3": vigor_items[2],
        "奉献1": dedication_items[0], "奉献2": dedication_items[1], "奉献3": dedication_items[2],
        "专注1": absorption_items[0], "专注2": absorption_items[1], "专注3": absorption_items[2],
        "工作投入_总分": total_engagement,
        "离职意愿": turnover_intent,
        "周均加班小时": overtime_hours,
    })

    # 注入 ~3% 缺失（在 UWES 题项和加班时长上）
    miss_cols = ["活力2", "奉献2", "专注2", "周均加班小时"]
    for col in miss_cols:
        mask = rng.random(n) < 0.03
        df.loc[mask, col] = np.nan

    return df


def generate_demo_performance_data(n_per_group: int = 50, seed: int = 42) -> pd.DataFrame:
    """培训项目效果评估（实验组 vs 对照组，前-后测）

    列结构（10 列）：
        - 员工ID, 组别, 部门
        - 前测_KPI得分, 后测_KPI得分（0-100）
        - 前测_技能评估, 后测_技能评估（0-100）
        - 参与培训时长_小时, 年龄, 性别

    设计要点：
        - 实验组培训 16-40 小时，对照组 0 小时
        - 实验组 KPI 提升均值 8 分（d ≈ 0.5），对照组提升 1 分
        - 实验组技能评估提升均值 12 分（d ≈ 0.7）
        - 控制前测后效应仍显著（适合 ANCOVA 演示）
    """
    rng = np.random.default_rng(seed)
    n = n_per_group * 2

    emp_id = np.arange(1, n + 1)
    group = ["实验组"] * n_per_group + ["对照组"] * n_per_group
    group_arr = np.array(group)
    dept = rng.choice(["研发", "产品", "设计"], n, p=[0.5, 0.3, 0.2])

    # 前测两组基线匹配
    pre_kpi = np.clip(rng.normal(70, 10, n), 40, 95).round(1)
    pre_skill = np.clip(rng.normal(65, 12, n), 30, 95).round(1)

    # 后测：实验组 + 8（KPI），+ 12（技能）；对照组 + 1，+ 2
    is_treat = group_arr == "实验组"
    post_kpi = np.where(
        is_treat,
        np.clip(pre_kpi + rng.normal(8, 5, n), 40, 100),
        np.clip(pre_kpi + rng.normal(1, 4, n), 40, 100),
    ).round(1)
    post_skill = np.where(
        is_treat,
        np.clip(pre_skill + rng.normal(12, 6, n), 30, 100),
        np.clip(pre_skill + rng.normal(2, 4, n), 30, 100),
    ).round(1)

    training_hours = np.where(
        is_treat,
        np.clip(rng.normal(28, 6, n), 16, 40),
        np.zeros(n),
    ).round(1)

    age = rng.integers(24, 45, n)
    gender = rng.choice(["男", "女"], n, p=[0.6, 0.4])

    return pd.DataFrame({
        "员工ID": emp_id,
        "组别": group,
        "部门": dept,
        "前测_KPI得分": pre_kpi,
        "后测_KPI得分": post_kpi,
        "前测_技能评估": pre_skill,
        "后测_技能评估": post_skill,
        "参与培训时长_小时": training_hours,
        "年龄": age,
        "性别": gender,
    })


def generate_demo_turnover_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """离职预测数据（binary outcome）

    列结构（11 列）：
        - 员工ID, 司龄_年, 年龄, 性别, 部门, 职级
        - 近12月加薪幅度_pct, 近6月周均加班_小时, 上司满意度（1-5）
        - 近一年绩效评级（A/B/C/D）, 通勤时间_分钟
        - 已离职（0/1，约 18% 离职率）

    设计要点：
        - 上司满意度低 → 强离职信号（OR ≈ 2.5）
        - 加薪幅度低 → 强离职信号
        - 周加班 > 25 小时 → 中等离职信号
        - 通勤 > 60 分钟 → 弱离职信号
        - 适合卡方、Logistic 回归、特征重要性演示
    """
    rng = np.random.default_rng(seed)

    emp_id = np.arange(1, n + 1)
    tenure = np.clip(rng.exponential(3.5, n), 0.5, 15.0).round(1)
    age = np.clip(22 + tenure * 1.6 + rng.normal(0, 5, n), 22, 55).round(0).astype(int)
    gender = rng.choice(["男", "女"], n, p=[0.60, 0.40])
    dept = rng.choice(["研发", "产品", "运营"], n, p=[0.5, 0.3, 0.2])
    level = rng.choice(LEVELS, n, p=[0.25, 0.30, 0.25, 0.15, 0.05])

    raise_pct = np.clip(rng.normal(8, 6, n), -3, 30).round(1)
    weekly_overtime = np.clip(rng.gamma(2.5, 4, n), 0, 40).round(1)
    boss_satisfaction = np.clip(rng.normal(3.5, 0.9, n), 1, 5).round(0).astype(int)
    perf = rng.choice(PERF_RATINGS, n, p=[0.20, 0.50, 0.25, 0.05])
    commute = np.clip(rng.gamma(2, 20, n), 5, 120).round(0).astype(int)

    # 离职概率 = sigmoid(线性组合)
    logit = (
        -2.2
        - 0.45 * (boss_satisfaction - 3)
        - 0.08 * (raise_pct - 8)
        + 0.04 * (weekly_overtime - 15)
        + 0.008 * (commute - 30)
        + np.where(perf == "D", 0.8, 0.0)
        + np.where(perf == "A", -0.3, 0.0)
        - 0.05 * tenure
        + rng.normal(0, 0.3, n)
    )
    prob = 1 / (1 + np.exp(-logit))
    turnover = (rng.random(n) < prob).astype(int)

    return pd.DataFrame({
        "员工ID": emp_id,
        "司龄_年": tenure,
        "年龄": age,
        "性别": gender,
        "部门": dept,
        "职级": level,
        "近12月加薪幅度_pct": raise_pct,
        "近6月周均加班_小时": weekly_overtime,
        "上司满意度": boss_satisfaction,
        "近一年绩效评级": perf,
        "通勤时间_分钟": commute,
        "已离职": turnover,
    })


def generate_demo_360_review_data(n: int = 80, seed: int = 42) -> pd.DataFrame:
    """360 度评估数据（4 维度 × 4 评估来源）

    列结构（18 列）：
        - 员工ID, 部门, 职级, 是否新经理（0/1）
        - 自评_{领导力, 专业能力, 协作能力, 创新能力}（1-7）
        - 上级评_{...} 4 项
        - 同事评_{...} 4 项
        - 下级评_{...} 4 项（无下级时 NaN，约 35%）

    设计要点：
        - 资深员工：上级评高 + 自评偏低（典型谦逊）
        - 新经理：自评高 + 上级评低（盲点）
        - 同事评向均值回归
        - 适合演示 ICC（评分者间一致性）、配对 t（自评 vs 他评偏差）、Cronbach α（同一来源跨维度）
    """
    rng = np.random.default_rng(seed)

    emp_id = np.arange(1, n + 1)
    dept = rng.choice(["研发", "产品", "运营", "HR"], n, p=[0.40, 0.25, 0.25, 0.10])
    level = rng.choice(["P5", "P6", "P7"], n, p=[0.50, 0.35, 0.15])
    is_new_mgr = rng.choice([0, 1], n, p=[0.70, 0.30])
    has_subordinate = rng.choice([1, 0], n, p=[0.65, 0.35])

    dims = ["领导力", "专业能力", "协作能力", "创新能力"]
    df_data = {
        "员工ID": emp_id,
        "部门": dept,
        "职级": level,
        "是否新经理": is_new_mgr,
    }

    # 每个员工有"真实能力"潜变量（1-7）
    true_ability = {
        d: np.clip(rng.normal(5.0, 0.9, n), 1, 7) for d in dims
    }

    for d in dims:
        ta = true_ability[d]
        # 自评：新经理偏高，资深偏低
        self_bias = np.where(is_new_mgr == 1, 0.6, -0.4)
        self_score = np.clip(ta + self_bias + rng.normal(0, 0.5, n), 1, 7).round(0).astype(int)
        # 上级评：新经理偏低，资深偏高
        boss_bias = np.where(is_new_mgr == 1, -0.5, 0.3)
        boss_score = np.clip(ta + boss_bias + rng.normal(0, 0.5, n), 1, 7).round(0).astype(int)
        # 同事评：均值回归
        peer_score = np.clip(ta + rng.normal(0, 0.4, n), 1, 7).round(0).astype(int)
        # 下级评：仅有下级才有
        sub_score = np.where(
            has_subordinate == 1,
            np.clip(ta + rng.normal(0, 0.6, n), 1, 7).round(0),
            np.nan,
        )

        df_data[f"自评_{d}"] = self_score
        df_data[f"上级评_{d}"] = boss_score
        df_data[f"同事评_{d}"] = peer_score
        df_data[f"下级评_{d}"] = sub_score

    df = pd.DataFrame(df_data)
    # 下级评列保持 float dtype 以承载 NaN
    for d in dims:
        df[f"下级评_{d}"] = df[f"下级评_{d}"].astype(float)

    return df


# ──────────────────────────────────────────────────────────────────────
# HR 数据集元信息（供 UI 展示用）
# ──────────────────────────────────────────────────────────────────────

HR_DATASET_CATALOG = [
    {
        "key": "engagement",
        "title": "🎮 游戏公司敬业度调研",
        "n": 300,
        "loader": generate_demo_engagement_data,
        "description": "300 名员工 UWES-9 工作投入量表 + 离职意愿 + 6 部门 + 司龄。可做信度（Cronbach α）、效度（EFA 三因子）、敬业度→离职意愿回归、不同部门 ANOVA。",
        "scenarios": ["量表信效度检验", "敬业度→离职预测", "部门间敬业度差异"],
        "core_methods": ["Cronbach α", "EFA", "线性回归", "单因素 ANOVA"],
    },
    {
        "key": "performance",
        "title": "📈 培训项目效果评估",
        "n": 100,
        "loader": lambda: generate_demo_performance_data(50),
        "description": "100 名员工随机分配至培训组/对照组的前-后测 KPI 与技能评估。可做配对 t、独立 t、ANCOVA（控制前测）、效应量计算。",
        "scenarios": ["培训前后差异", "实验组-对照组比较", "控制前测的因果推断"],
        "core_methods": ["配对 t 检验", "独立 t 检验", "ANCOVA", "Cohen's d"],
    },
    {
        "key": "turnover",
        "title": "🚪 员工离职预测数据",
        "n": 500,
        "loader": generate_demo_turnover_data,
        "description": "500 名员工的 11 项特征 + 已离职 binary outcome（约 18% 离职率）。可做卡方独立性检验、二元 Logistic 回归、特征重要性分析。",
        "scenarios": ["离职信号筛选", "高风险人群画像", "干预效果模拟"],
        "core_methods": ["卡方检验", "Logistic 回归", "OR 计算"],
    },
    {
        "key": "review_360",
        "title": "🔄 360 度评估数据",
        "n": 80,
        "loader": generate_demo_360_review_data,
        "description": "80 名核心员工 4 个维度 × 4 个评估来源（自评/上级/同事/下级）。可做评分者一致性（ICC）、自评-他评偏差检验、新经理盲点识别。",
        "scenarios": ["评分者一致性", "自评他评偏差", "新经理盲点诊断"],
        "core_methods": ["ICC", "配对 t 检验", "相关分析"],
    },
]


def list_hr_datasets() -> list:
    """返回 HR 数据集元信息列表（用于 UI 渲染）"""
    return HR_DATASET_CATALOG
