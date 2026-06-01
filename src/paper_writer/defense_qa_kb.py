"""答辩问题模板库 — 按统计方法 × 问题类别 × 难度索引。

每条 QATemplate 字段：
- question: 中文问题
- answer_template: 标准答案模板（用 {占位符} 自动填充）
- placeholders: 该模板需要的占位符
- category: 6 大类别之一
- difficulty: 必问 🟢 / 常问 🟡 / 刁钻 🔴
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# --------------------------------------------------------------------------- #
# 类别 + 难度
# --------------------------------------------------------------------------- #

CATEGORIES = {
    "method": "🎯 方法选择",
    "data": "📊 数据合规",
    "effect": "📐 效应量",
    "assumption": "✅ 假设验证",
    "limit": "⚠ 研究局限",
    "infer": "🔍 推论谨慎",
}

DIFFICULTY_LEVELS = {
    "必问": ("🟢", 0, "导师答辩几乎一定会问"),
    "常问": ("🟡", 1, "常见追问"),
    "刁钻": ("🔴", 2, "进阶质疑，视情况准备"),
}

DIFFICULTY_ORDER = {"必问": 0, "常问": 1, "刁钻": 2}


@dataclass
class QATemplate:
    question: str
    answer_template: str
    category: str
    placeholders: List[str] = field(default_factory=list)
    difficulty: str = "常问"  # 必问 / 常问 / 刁钻


def difficulty_emoji(level: str) -> str:
    return DIFFICULTY_LEVELS.get(level, ("🟡", 1, ""))[0]


def difficulty_label(level: str) -> str:
    emoji = difficulty_emoji(level)
    return f"{emoji} {level}"


# --------------------------------------------------------------------------- #
# 通用模板（跨方法）
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# 类别填补：当某方法缺少 method/data/effect/infer 必备类别时，从这里补
# --------------------------------------------------------------------------- #

CATEGORY_FALLBACK_QA: Dict[str, QATemplate] = {
    "data": QATemplate(
        question="你的样本量 n={n} 是怎么确定的？满足检验要求吗？",
        answer_template=(
            "本研究 n = {n}，依据 G*Power 软件预先计算（α=.05，power=.80，预期中等效应量），"
            "或参考类似研究的样本规模标准。"
            "对{method}而言，建议样本量为 {min_n}，本研究{sample_judgment}。"
        ),
        category="data",
        difficulty="必问",
        placeholders=["n", "method", "min_n", "sample_judgment"],
    ),
    "infer": QATemplate(
        question="结果显著就能说明你的假设成立吗？",
        answer_template=(
            "p < .05 只是「数据与零假设不一致」的统计证据，"
            "不是「假设成立」的直接证明。"
            "推论时还需考虑：(1) 效应量是否实质性大；"
            "(2) 研究设计能否支持因果推断；"
            "(3) 结果在新样本是否可重复。"
            "建议在论文中报告效应量、置信区间，并审慎使用「证明」「导致」等强表述。"
        ),
        category="infer",
        difficulty="必问",
        placeholders=[],
    ),
    "effect": QATemplate(
        question="你的效应量是多少？是否具有实质意义？",
        answer_template=(
            "本研究效应量 = {effect_size:.3f}，属于{effect_label}水平。"
            "效应量比 p 值更能反映「差异有多大」，"
            "p < .05 只说差异不太可能源于偶然，而效应量告诉我们「这个差异有多大意义」。"
        ),
        category="effect",
        difficulty="必问",
        placeholders=["effect_size", "effect_label"],
    ),
    "method": QATemplate(
        question="为什么选择这个统计方法？",
        answer_template=(
            "{method}适合你的数据特征：因变量类型、自变量类型、研究问题。"
            "选择前考察了：(1) 变量尺度（连续/分类）；"
            "(2) 分布特征（正态性、方差齐性）；"
            "(3) 数据结构（独立/配对/重复测量）；"
            "(4) 研究目标（差异/关联/预测）。"
        ),
        category="method",
        difficulty="必问",
        placeholders=["method"],
    ),
}


GENERIC_QA: List[QATemplate] = [
    QATemplate(
        question="你的样本量 n={n}，依据是什么？是否满足检验要求？",
        answer_template=(
            "本研究 n = {n}，达到{method}的最小样本量要求。"
            "样本量依据 G*Power 软件预先计算（α=.05，power=.80，预期中等效应量），"
            "并参考类似研究的样本规模（通常每组 ≥ 30）。"
            "需要承认的局限是：方便抽样可能限制结果对更广泛总体的推论能力。"
        ),
        category="data",
        difficulty="必问",
        placeholders=["n", "method"],
    ),
    QATemplate(
        question="你这个研究的样本是怎么选的？是否能代表总体？",
        answer_template=(
            "本研究采用方便抽样，从{population}中招募被试。"
            "样本规模 n={n} 满足{method}的最小样本量要求。"
            "需要承认的局限是：方便抽样可能限制结果对更广泛总体的推论能力，"
            "未来研究应考虑分层随机抽样以提高外部效度。"
        ),
        category="data",
        difficulty="常问",
        placeholders=["population", "n", "method"],
    ),
    QATemplate(
        question="如果有人质疑你的研究存在局限，你会怎么回应？",
        answer_template=(
            "本研究主要存在三方面的局限：第一，样本来源单一（{population}），"
            "可能限制结果的可推广性；第二，{design_limit}；"
            "第三，{measurement_limit}。"
            "未来研究应通过扩大样本范围、采用纵向设计、加入多源数据来弥补这些不足。"
        ),
        category="limit",
        difficulty="刁钻",
        placeholders=["population", "design_limit", "measurement_limit"],
    ),
    QATemplate(
        question="p 值显著到底是什么意思？",
        answer_template=(
            "p 值是「假设零假设为真，观察到当前或更极端结果的概率」。"
            "本研究 p = {p_value}，<.05，说明若两组（或变量）真的没有差异/关联，"
            "得到当前结果的概率小于 5%，因此我们拒绝零假设。"
            "p 值不是「假设为真的概率」，也不衡量效应大小，"
            "解读必须结合效应量和置信区间。"
        ),
        category="infer",
        difficulty="必问",
        placeholders=["p_value"],
    ),
]


# --------------------------------------------------------------------------- #
# 按检验类型分组
# --------------------------------------------------------------------------- #

TEST_SPECIFIC_QA: Dict[str, List[QATemplate]] = {

    # ====================================================================== #
    # t 检验家族
    # ====================================================================== #
    "independent_ttest": [
        QATemplate(
            question="为什么选用独立样本 t 检验，而不是其他方法？",
            answer_template=(
                "本研究的自变量「{iv}」是两组分类变量，因变量「{dv}」是连续变量，"
                "且两组被试相互独立，因此选用独立样本 t 检验最合适。"
                "若数据严重偏离正态分布，可改用 Mann-Whitney U 检验作为替代。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["iv", "dv"],
        ),
        QATemplate(
            question="你的方差齐性检验通过了吗？如果没通过怎么办？",
            answer_template=(
                "本研究使用 Levene 检验考察方差齐性，结果为 {levene_status}。"
                "{welch_note}"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["levene_status", "welch_note"],
        ),
        QATemplate(
            question="效应量 Cohen's d = {effect_size:.2f} 是大还是小？意味着什么？",
            answer_template=(
                "依据 Cohen (1988) 的标准，d=0.2 为小效应，0.5 为中等效应，0.8 以上为大效应。"
                "本研究的 d = {effect_size:.3f}，属于{effect_label}效应，"
                "意味着两组在「{dv}」上的均值差异具有{practical_meaning}的实际意义，"
                "而非仅在统计上显著。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label", "dv", "practical_meaning"],
        ),
        QATemplate(
            question="t 检验显著就能说自变量「导致」因变量变化吗？",
            answer_template=(
                "不能。t 检验只能说明两组在因变量上存在统计上的差异，"
                "若想推断因果关系，需要满足三个条件：(1) 时间先后；(2) 共变；(3) 排除其他解释。"
                "本研究为{design_type}设计，{causal_judgment}。"
                "在论文中应使用「差异」「关联」等术语，避免「导致」「影响」。"
            ),
            category="infer",
            difficulty="常问",
            placeholders=["design_type", "causal_judgment"],
        ),
        QATemplate(
            question="如果两组样本量差距很大，t 检验结果还可信吗？",
            answer_template=(
                "样本量严重不平衡（如 1:3 以上）会降低检验效力，"
                "且对方差齐性假设更敏感。"
                "建议：(1) 用 Welch t 检验对此更稳健；"
                "(2) 报告每组的具体 n；(3) 用 Bootstrap 重抽样验证结果稳定性。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    "paired_ttest": [
        QATemplate(
            question="为什么选用配对样本 t 检验？",
            answer_template=(
                "本研究在{condition1}和{condition2}两个时点（或条件）下，"
                "对同一组被试测量了「{dv}」，属于配对（重复测量）数据，"
                "因此选用配对样本 t 检验，能更好地控制个体差异，提高检验效力。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["condition1", "condition2", "dv"],
        ),
        QATemplate(
            question="差值的正态性怎么验？",
            answer_template=(
                "配对 t 检验只要求「差值」（条件 1 − 条件 2）服从正态分布，"
                "本研究使用 Shapiro-Wilk 检验考察差值的正态性，结果为 {normality_status}。"
                "若违反正态性，应改用 Wilcoxon 符号秩检验。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["normality_status"],
        ),
        QATemplate(
            question="效应量 d = {effect_size:.2f} 怎么解读？",
            answer_template=(
                "配对 t 检验的 Cohen's d 基于差值的均值除以差值的标准差。"
                "本研究 d = {effect_size:.3f}，属于{effect_label}效应，"
                "表示前后测变化具有{practical_meaning}的实际意义。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label", "practical_meaning"],
        ),
        QATemplate(
            question="前后测显著差异，能确定是干预效果吗？",
            answer_template=(
                "不一定。还可能是：(1) 测试效应（重复测量本身导致变化）；"
                "(2) 时间效应（自然成熟、季节变化）；"
                "(3) 期望效应（被试想配合研究）。"
                "为排除这些可能，需要加入控制组（前后测设计 → 等组前后测设计）。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    "one_sample_ttest": [
        QATemplate(
            question="为什么用单样本 t 检验？比较的常模值从哪来？",
            answer_template=(
                "本研究用单样本 t 检验比较「{dv}」的样本均值与已知常模值 μ₀={mu_0}。"
                "常模值来源于{norm_source}。"
                "适用条件：因变量为连续变量，需要与一个理论值或常模均值比较。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["dv", "mu_0", "norm_source"],
        ),
        QATemplate(
            question="样本数据是否服从正态分布？",
            answer_template=(
                "本研究使用 Shapiro-Wilk 检验，结果为 {normality_status}。"
                "若 n>30，根据中心极限定理，t 检验对正态性偏离稳健。"
                "严重偏态时可改用 Wilcoxon 符号秩检验对应的单样本版本。"
            ),
            category="assumption",
            difficulty="常问",
            placeholders=["normality_status"],
        ),
        QATemplate(
            question="效应量怎么算的？",
            answer_template=(
                "Cohen's d = (M − μ₀) / SD = {effect_size:.3f}，属于{effect_label}效应。"
                "解读：样本均值偏离常模值约 {effect_size_abs:.2f} 个标准差。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label", "effect_size_abs"],
        ),
        QATemplate(
            question="如果与常模差异显著，能直接推断这是「问题」吗？",
            answer_template=(
                "不能直接下结论。差异显著只表明样本与常模不同，"
                "差异的「意义」需要结合：(1) 常模本身的代表性；(2) 样本的特殊性；"
                "(3) 实际效应大小。例如焦虑得分高于常模可能反映样本特殊群体特征，"
                "而非样本「有问题」。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # 方差分析家族
    # ====================================================================== #
    "one_way_anova": [
        QATemplate(
            question="为什么不用多次 t 检验，而用 ANOVA？",
            answer_template=(
                "如果对 {n_groups} 个组进行两两 t 检验，将进行 {n_pairs} 次比较，"
                "每次都有 5% 的一类错误风险，累积误差会显著膨胀（约 {family_error:.0%}）。"
                "ANOVA 通过 F 检验同时比较所有组，控制总体一类错误率在 α=.05 水平。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["n_groups", "n_pairs", "family_error"],
        ),
        QATemplate(
            question="ANOVA 显著之后，你做事后检验了吗？为什么用这个方法？",
            answer_template=(
                "本研究使用 Tukey HSD 法进行事后多重比较。"
                "Tukey HSD 适用于样本量大致相等的情况，能控制总体一类错误率，"
                "在 {n_groups} 组的情境下相对保守且稳健。"
                "结果显示 {tukey_result}。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["n_groups", "tukey_result"],
        ),
        QATemplate(
            question="你的效应量 η² = {effect_size:.3f} 怎么理解？",
            answer_template=(
                "η² 表示自变量「{iv}」能解释因变量「{dv}」总变异的比例。"
                "本研究 η² = {effect_size:.3f}，意味着 {iv} 解释了 {effect_pct:.1f}% 的方差，"
                "依据 Cohen (1988) 标准（小=.01，中=.06，大=.14），属于{effect_label}效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "iv", "dv", "effect_pct", "effect_label"],
        ),
        QATemplate(
            question="方差齐性假设满足吗？不满足怎么办？",
            answer_template=(
                "ANOVA 要求各组方差齐性。本研究通过 Levene 检验考察，"
                "若 p > .05 即满足。若不满足，建议改用 Welch ANOVA（对方差不齐稳健），"
                "或非参数的 Kruskal-Wallis H 检验。"
            ),
            category="assumption",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="组间显著但实际差异很小，怎么解读？",
            answer_template=(
                "这正是为什么必须报告效应量：p 值显著只说明差异不太可能源于偶然，"
                "但 η² 才说明差异有多大。本研究 η² = {effect_size:.3f}，"
                "属于{effect_label}效应。如果 η² < .01，"
                "说明虽然统计显著但实际意义有限，论文中应明确指出。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=["effect_size", "effect_label"],
        ),
    ],

    "two_way_anova": [
        QATemplate(
            question="双因素 ANOVA 比单因素的优势是什么？",
            answer_template=(
                "双因素 ANOVA 同时考察两个自变量的主效应及其交互作用。"
                "本研究的两个自变量分别为「{iv1}」和「{iv2}」。"
                "如果只跑两次单因素 ANOVA，会忽略交互效应——"
                "即一个自变量的效应在另一自变量的不同水平下可能不同。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["iv1", "iv2"],
        ),
        QATemplate(
            question="如果交互效应显著，主效应还能解读吗？",
            answer_template=(
                "需要谨慎。交互效应显著意味着主效应被 qualified（限定），"
                "应优先报告简单效应（在另一自变量的每个水平下分别看）。"
                "例如 A×B 交互显著时，应分别报告 A 在 B=b1 和 B=b2 时的简单效应，"
                "而非笼统说「A 主效应显著」。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="效应量怎么报告？",
            answer_template=(
                "双因素 ANOVA 应分别报告：(1) 自变量 1 的偏 η²；"
                "(2) 自变量 2 的偏 η²；(3) 交互项的偏 η²。"
                "偏 η² 控制了其他效应，比 η² 更适合多因素设计。"
                "Cohen (1988) 标准同样适用：小=.01，中=.06，大=.14。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="样本量需要多大？",
            answer_template=(
                "双因素 ANOVA 的细胞设计（{iv1} × {iv2}）至少每个细胞 n ≥ 15-20，"
                "总样本通常需要 n ≥ 100。若细胞间样本量不平衡，建议用 Type III 平方和。"
            ),
            category="data",
            difficulty="常问",
            placeholders=["iv1", "iv2"],
        ),
    ],

    "repeated_anova": [
        QATemplate(
            question="重复测量 ANOVA 与配对 t 检验的关系？",
            answer_template=(
                "配对 t 检验是 2 个重复测量水平的特例；重复测量 ANOVA 处理 3 个或更多重复测量。"
                "本研究的重复测量水平数为 {n_levels}（如 T1/T2/T3）。"
                "每个被试在所有水平上都被测量，能控制个体差异，提高检验效力。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["n_levels"],
        ),
        QATemplate(
            question="球形假设是什么？没满足怎么办？",
            answer_template=(
                "球形假设要求各重复测量水平之间的「差值方差」相等。"
                "用 Mauchly 检验考察：若 p < .05 表示违反，需用 Greenhouse-Geisser 或 Huynh-Feldt 校正自由度。"
                "本研究的 Mauchly 结果 {sphericity_status}。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["sphericity_status"],
        ),
        QATemplate(
            question="效应量？",
            answer_template=(
                "重复测量 ANOVA 报告偏 η²（partial η²）。"
                "本研究偏 η² = {effect_size:.3f}，属于{effect_label}效应。"
                "Cohen 标准：小=.01，中=.06，大=.14。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
        QATemplate(
            question="出现变化趋势就能说干预有效吗？",
            answer_template=(
                "不能。重复测量本身就有趋势效应（练习效应、疲劳效应、自然成熟）。"
                "若想推断干预效果，需要：(1) 加入控制组；(2) 关注交互效应（组别 × 时间）；"
                "(3) 控制基线差异。单组重复测量只能说明「随时间变化」，"
                "不能说明「因为干预」。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    "welch_anova": [
        QATemplate(
            question="为什么用 Welch ANOVA 而不是普通 ANOVA？",
            answer_template=(
                "本研究的 Levene 检验显示各组方差不齐。"
                "Welch ANOVA 不要求方差齐性，通过调整自由度对方差异质性稳健。"
                "比普通 ANOVA 更不容易得到错误的显著结论。"
            ),
            category="method",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="Welch ANOVA 之后用什么事后检验？",
            answer_template=(
                "应使用 Games-Howell 事后检验，它不要求方差齐性。"
                "不能用 Tukey HSD（要求方差齐性）。"
                "本研究的 Games-Howell 结果显示具体哪些组之间差异显著。"
            ),
            category="method",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="效应量怎么算？",
            answer_template=(
                "可以报告 ω²（omega squared）或 ε²（epsilon squared），"
                "它们在方差不齐时比 η² 更稳健。"
                "本研究效应量 = {effect_size:.3f}，属于{effect_label}效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
        QATemplate(
            question="既然方差不齐，结果还有意义吗？",
            answer_template=(
                "Welch ANOVA 已经处理了方差不齐问题，结果是稳健的。"
                "但需要承认：方差不齐本身可能反映总体异质性，"
                "解读时应考虑各组差异不仅在均值，也在变异程度上。"
                "建议同时报告各组 SD，让读者看清异质性。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量需求和 ANOVA 一样吗？",
            answer_template=(
                "Welch ANOVA 对样本量要求更严，建议每组 n ≥ 20，"
                "总样本 n ≥ 60。若样本量极不平衡，Welch 比标准 ANOVA 更稳健，"
                "但效力仍受小组样本量限制。"
            ),
            category="data",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    "ancova": [
        QATemplate(
            question="为什么用 ANCOVA 而不是 ANOVA？",
            answer_template=(
                "ANCOVA 在比较组间均值时，控制了协变量「{covariate}」的影响。"
                "适用场景：(1) 控制混杂变量，提高检验效力；(2) 比较前测后测设计中调整后的差异。"
                "比 ANOVA 能更精确估计自变量的「净」效应。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["covariate"],
        ),
        QATemplate(
            question="ANCOVA 有哪些前提假设？",
            answer_template=(
                "除了 ANOVA 的常规假设（正态、方差齐、独立），还需要："
                "(1) 协变量与因变量线性相关；"
                "(2) 回归齐性（各组协变量-因变量回归斜率相同，无交互）；"
                "(3) 协变量在自变量之前测得（避免被自变量影响）。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="如果回归齐性假设不满足怎么办？",
            answer_template=(
                "回归齐性违反意味着协变量对因变量的影响在不同组间不同——"
                "即存在交互效应，应改用 Johnson-Neyman 程序或简单斜率分析。"
                "强行使用 ANCOVA 会得出错误结论。"
            ),
            category="assumption",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="协变量必须包括哪些？",
            answer_template=(
                "理论驱动 + 数据驱动结合。理论上：与因变量相关、可能引起组间差异的变量；"
                "数据上：与因变量 r > .30 的变量。"
                "不能纳入「与自变量混淆」的变量（如自变量的果），否则会过度调整。"
            ),
            category="effect",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量需要多大？",
            answer_template=(
                "ANCOVA 样本量需求高于 ANOVA：每组至少 n ≥ 30，"
                "或满足 G*Power 计算的样本量（控制协变量后效应量、α、power 决定）。"
                "样本不足会降低协变量调整的稳定性。"
            ),
            category="data",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="ANCOVA 显著就能说自变量「真的」有效吗？",
            answer_template=(
                "不能直接下因果结论。ANCOVA 控制了你测量的协变量，"
                "但仍可能存在未测量的混杂变量。"
                "推论上的局限同 ANOVA：实验设计是因果推断的金标准，"
                "横断面或观察性数据上的 ANCOVA 仍只是关联。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    "kruskal_wallis": [
        QATemplate(
            question="为什么用 Kruskal-Wallis 而不是 ANOVA？",
            answer_template=(
                "本研究的「{dv}」违反了 ANOVA 的正态性假设，或样本量较小。"
                "Kruskal-Wallis 是 ANOVA 的非参数等价版本，基于秩次比较多组中位数。"
                "对分布形态无要求，对异常值稳健。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["dv"],
        ),
        QATemplate(
            question="Kruskal-Wallis 显著后用什么事后检验？",
            answer_template=(
                "Dunn 检验（with Bonferroni 校正）是最常见的非参数事后检验。"
                "本研究的 Dunn 检验结果显示具体哪些组对差异显著。"
                "不能直接用 Tukey（要求正态性）。"
            ),
            category="method",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="效应量？",
            answer_template=(
                "ε² = (H - k + 1) / (n - k)，类似 η²，"
                "本研究 ε² = {effect_size:.3f}，属于{effect_label}效应。"
                "或报告 r = Z / √n（每对比较）。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
        QATemplate(
            question="非参数检验的检验效力是不是更低？",
            answer_template=(
                "在数据满足参数检验假设时，非参数确实效力略低（约 95%）。"
                "但当数据违反假设时，非参数更稳健。"
                "本研究因正态性不满足，使用非参数是更合理的选择。"
                "若担心效力，可在论文中报告：「即使在保守的非参数检验下，结果依然显著」。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量要求？",
            answer_template=(
                "Kruskal-Wallis 对样本量要求灵活，每组 n ≥ 5 即可应用。"
                "但太小的样本（每组 < 5）建议改用精确检验（exact test）。"
                "不平衡样本量的检验效力会降低，建议每组样本量大致相等。"
            ),
            category="data",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    "friedman": [
        QATemplate(
            question="为什么用 Friedman 而不是重复测量 ANOVA？",
            answer_template=(
                "本研究的重复测量数据违反了正态性或球形假设，或为等级数据。"
                "Friedman 是重复测量 ANOVA 的非参数等价，基于每个被试在不同条件下的秩次比较。"
                "对分布形态和等距尺度无要求。"
            ),
            category="method",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="Friedman 显著后做什么后续？",
            answer_template=(
                "用 Wilcoxon 符号秩检验做两两比较，配合 Bonferroni 校正控制总体一类错误率。"
                "或使用 Nemenyi 检验作为专门的非参数事后程序。"
            ),
            category="method",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="效应量？",
            answer_template=(
                "Kendall's W（Kendall 协调系数）是常用效应量，范围 0-1。"
                "本研究 W = {effect_size:.3f}，"
                "(0=完全无一致性，1=完全一致)，属于{effect_label}水平。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="样本量太小（n<10）时 Friedman 还能用吗？",
            answer_template=(
                "Friedman 检验对小样本相对宽容，但 n<10 时建议使用精确分布"
                "（exact test）而非近似的卡方分布，否则 p 值可能不准。"
                "现代统计软件（R、SPSS）可指定精确法。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量需求？",
            answer_template=(
                "Friedman 检验最少 n ≥ 6（被试数），通常建议 n ≥ 15 以保证检验效力。"
                "本研究 n = {n}，{sample_judgment}。"
            ),
            category="data",
            difficulty="必问",
            placeholders=["n", "sample_judgment"],
        ),
        QATemplate(
            question="重复测量趋势显著就能说效果稳定吗？",
            answer_template=(
                "不能。Friedman 显著只说明「至少有两个时点存在差异」，"
                "需要事后两两比较确定具体哪些时点不同。"
                "且重复测量本身会有练习/疲劳效应，建议加入控制组以排除时间因素。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    "wilcoxon": [
        QATemplate(
            question="为什么用 Wilcoxon 而不是配对 t 检验？",
            answer_template=(
                "本研究的差值数据违反了正态性假设，或为等级数据，或样本量较小。"
                "Wilcoxon 符号秩检验是配对 t 检验的非参数版本，"
                "基于差值的秩次比较，对分布无要求。"
            ),
            category="method",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="Wilcoxon 检验的零假设是什么？",
            answer_template=(
                "零假设：差值的分布对称地围绕 0（即正负差值同样多且同样大）。"
                "拒绝零假设意味着前测后测之间存在系统性差异。"
            ),
            category="assumption",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="效应量怎么算？",
            answer_template=(
                "Wilcoxon 的效应量 r = |Z| / √n。"
                "本研究 r = {effect_size:.3f}，依据 Cohen 标准（小=.10，中=.30，大=.50），"
                "属于{effect_label}效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
        QATemplate(
            question="差值为 0 的被试怎么处理？",
            answer_template=(
                "传统做法：剔除差值为 0 的对（Wilcoxon 原始算法）。"
                "现代做法：保留并赋予平均秩（Pratt's correction）。"
                "建议在论文方法部分明确说明使用了哪种处理方式。"
            ),
            category="data",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="Wilcoxon 显著能直接推断干预有效吗？",
            answer_template=(
                "不能。Wilcoxon 只说前后测在配对数据上有系统差异，"
                "干预有效的因果推断仍需控制组、随机分配等设计层面的支撑。"
                "单组前后测的局限：测试效应、时间效应、期望效应。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    "mann_whitney": [
        QATemplate(
            question="为什么用非参数检验而不是 t 检验？",
            answer_template=(
                "本研究的「{dv}」在至少一组中显著偏离正态分布（Shapiro-Wilk p<.05），"
                "或样本量较小（n<30），无法保证 t 检验的稳健性。"
                "Mann-Whitney U 基于秩次比较两组的中位数，"
                "对分布形态无要求，更适合本研究的数据特征。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["dv"],
        ),
        QATemplate(
            question="Mann-Whitney 检验的零假设？",
            answer_template=(
                "严格地说，零假设是「两个总体的分布相同」，"
                "在分布形状相似的假设下可解读为「中位数相等」。"
                "若两组分布形状不同，应谨慎下「中位数不同」的结论。"
            ),
            category="assumption",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="效应量怎么计算？",
            answer_template=(
                "效应量 r = |Z| / √(n1+n2)。本研究 r = {effect_size:.3f}，"
                "依据 Cohen 标准（小=.10，中=.30，大=.50），属于{effect_label}效应。"
                "或报告概率优势（probability of superiority）。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
        QATemplate(
            question="如果两组样本量差距很大，结果还稳健吗？",
            answer_template=(
                "Mann-Whitney 对样本量不平衡相对稳健，但仍建议每组 n ≥ 10。"
                "极端不平衡（如 5 vs 50）会降低检验效力，"
                "可考虑 Bootstrap 自助法验证结果稳定性。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # 相关分析家族
    # ====================================================================== #
    "pearson_corr": [
        QATemplate(
            question="r = {r:.3f} 算大还是小？相关意味着什么？",
            answer_template=(
                "依据 Cohen (1988) 标准，|r|=0.10 为小，0.30 为中，0.50 以上为大。"
                "本研究 r = {r:.3f}，属于{effect_label}相关，"
                "意味着 {var1} 与 {var2} 共同变化的程度{practical_meaning}。"
                "需要强调：相关不等于因果，只能说两个变量同向（或反向）变化。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["r", "effect_label", "var1", "var2", "practical_meaning"],
        ),
        QATemplate(
            question="为什么用 Pearson 而不是 Spearman？",
            answer_template=(
                "Pearson 适用于两变量都为连续变量、近似正态分布、关系为线性的情况。"
                "本研究的「{var1}」和「{var2}」均为连续测量，正态性检验通过，"
                "且散点图显示线性趋势，因此选用 Pearson。"
                "若数据偏态严重或为等级数据，应改用 Spearman 秩相关。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["var1", "var2"],
        ),
        QATemplate(
            question="既然显著相关，能说一个变量决定另一个吗？",
            answer_template=(
                "不能。相关分析只揭示共变关系，存在三种可能：(1) X 影响 Y；"
                "(2) Y 影响 X；(3) 第三变量同时影响 X 和 Y。"
                "本研究为{design_type}，无法区分这三种可能。"
                "若要推断因果，需采用纵向追踪、实验操纵或工具变量等方法。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=["design_type"],
        ),
        QATemplate(
            question="散点图里如果有非线性趋势，r 还有意义吗？",
            answer_template=(
                "Pearson r 只衡量线性关系。"
                "如果散点图显示曲线（U 型、倒 U 型、对数型）关系，r 可能很低甚至为 0，"
                "但变量间确实存在很强的非线性关系。"
                "建议先看散点图：明显非线性时改用 Spearman、多项式回归或非参数方法。"
            ),
            category="assumption",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    "spearman_corr": [
        QATemplate(
            question="为什么用 Spearman 而不是 Pearson？",
            answer_template=(
                "本研究的「{var1}」或「{var2}」存在以下情况之一：(a) 等级数据/有序变量，"
                "(b) 严重偏态分布，(c) 存在异常值，"
                "因此选用 Spearman 秩相关更稳健。"
                "Spearman 基于秩次而非原始数值，对异常值不敏感，且不要求正态性。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["var1", "var2"],
        ),
        QATemplate(
            question="Spearman ρ = {r:.3f} 怎么解读？",
            answer_template=(
                "Spearman ρ 衡量的是「单调关系」强度（同向或反向变化），"
                "不一定是线性。本研究 ρ = {r:.3f}，属于{effect_label}相关。"
                "标准与 Pearson 类似：|ρ|=0.10 小，0.30 中，0.50 大。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["r", "effect_label"],
        ),
        QATemplate(
            question="Spearman 相关显著就能说明因果吗？",
            answer_template=(
                "同 Pearson，相关不等于因果。Spearman 只是用秩次替换了原始值，"
                "推论上的局限完全相同：可能存在反向因果或第三变量。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="Spearman 的检验效力是不是比 Pearson 低？",
            answer_template=(
                "在数据满足 Pearson 假设时，Spearman 效力约为 91%（轻微损失）。"
                "在违反假设（偏态、异常值、等级数据）时，Spearman 反而效力更高。"
                "选择哪个不应基于「效力」，而应基于数据特征。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="Spearman 对样本量有要求吗？",
            answer_template=(
                "建议 n ≥ 30 以获得稳定的秩相关估计。"
                "n < 10 时建议使用精确检验。"
                "本研究 n = {n}，{sample_judgment}。"
            ),
            category="data",
            difficulty="必问",
            placeholders=["n", "sample_judgment"],
        ),
    ],

    "partial_corr": [
        QATemplate(
            question="偏相关和普通相关的区别？",
            answer_template=(
                "偏相关（partial r）控制了一个或多个第三变量后，"
                "考察 X 和 Y 之间的「净」关联。"
                "本研究控制「{control_vars}」后，{var1} 与 {var2} 的偏相关 = {r:.3f}。"
                "如果偏相关与普通相关差异大，说明被控制变量起重要混杂作用。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["var1", "var2", "control_vars", "r"],
        ),
        QATemplate(
            question="控制变量怎么选？",
            answer_template=(
                "理论驱动：与 X 和 Y 都相关、且在因果链外的变量"
                "（避免控制中介变量，否则会消除真实效应）。"
                "数据驱动：与 X 和 Y 都 r > .30 的变量。"
                "切忌「凡是相关的都控制」，会导致过度调整。"
            ),
            category="method",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="偏相关显著就能说排除了第三变量影响吗？",
            answer_template=(
                "只能说「控制了你测量的协变量」后仍有关联。"
                "未测量的协变量（unmeasured confounders）依然可能存在。"
                "偏相关不等同于因果证据，仍需谨慎推论。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="效应量解读？",
            answer_template=(
                "偏相关的效应量解读与 Pearson r 相同：|r|=0.10 小，0.30 中，0.50 大。"
                "本研究偏 r = {r:.3f}，属于{effect_label}效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["r", "effect_label"],
        ),
        QATemplate(
            question="样本量需求？",
            answer_template=(
                "偏相关需要的样本量比普通相关更大：经验法则 n ≥ 30 + 10×(控制变量数)。"
                "本研究控制 {n_controls} 个变量，建议 n ≥ {min_n}。"
            ),
            category="data",
            difficulty="必问",
            placeholders=["n_controls", "min_n"],
        ),
    ],

    "point_biserial": [
        QATemplate(
            question="点二列相关和 Pearson 是同一回事吗？",
            answer_template=(
                "数学上，点二列相关 = 一个变量是二分类、另一个是连续时的 Pearson r。"
                "本研究中「{var1}」是二分类（0/1），「{var2}」是连续，故用点二列。"
                "在量表分析中常用于评估单题与总分的关联（题项区分度）。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["var1", "var2"],
        ),
        QATemplate(
            question="效应量？",
            answer_template=(
                "rpb = {r:.3f}，属于{effect_label}效应。"
                "解读：连续变量在两个分类之间的均值差异，"
                "相当于 Cohen's d 的另一种表达（d = 2r/√(1-r²)）。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["r", "effect_label"],
        ),
        QATemplate(
            question="题目分析中点二列相关多少算合格？",
            answer_template=(
                "经典测量理论：题目-总分点二列相关 ≥ .30 为可接受，"
                "≥ .40 为良好。低于 .30 的题目区分度不足，建议修订或剔除。"
                "本研究结果可据此判断哪些题需要修订。"
            ),
            category="effect",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="二分类变量是否需要等距尺度？",
            answer_template=(
                "二分类变量赋值（如 0/1、男/女）不影响 rpb 的绝对值，"
                "但会影响符号方向。建议明确编码方式（论文中说明 0=哪个、1=哪个）。"
                "切忌从有序变量人为二分（如把抑郁分数切成「高/低」），会损失信息。"
            ),
            category="data",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="点二列相关显著就说明分类变量「决定」连续变量吗？",
            answer_template=(
                "不能。点二列只揭示关联（一组的均值高于另一组），"
                "不证明因果。例如「性别与数学成绩」rpb 显著，"
                "可能反映社会化、教学方法、自我效能等多种机制，而非性别本身。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # 回归家族
    # ====================================================================== #
    "linear_regression": [
        QATemplate(
            question="为什么用线性回归？模型形式是什么？",
            answer_template=(
                "本研究关心连续因变量「{dv}」如何被一个连续/二分预测变量「{iv}」预测。"
                "模型：Y = β₀ + β₁·X + ε。"
                "比相关分析多了「斜率 β₁」（X 每变化 1 个单位，Y 平均变化 β₁ 个单位）。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["dv", "iv"],
        ),
        QATemplate(
            question="R² = {r_sq:.3f} 是什么意思？",
            answer_template=(
                "R² 表示「{iv}」能解释「{dv}」总变异的比例。"
                "本研究 R² = {r_sq:.3f}，意味着模型解释了 {r_sq_pct:.1f}% 的方差。"
                "Cohen 标准：R²=.02 小，.13 中，.26 大效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["r_sq", "r_sq_pct", "iv", "dv"],
        ),
        QATemplate(
            question="线性回归的前提假设有哪些？",
            answer_template=(
                "(1) 线性关系：散点图无明显曲线趋势；"
                "(2) 残差独立：Durbin-Watson 接近 2；"
                "(3) 同方差性：残差图无漏斗形；"
                "(4) 残差正态：Q-Q 图直线；"
                "(5) 无强影响点：Cook's D < 1。"
                "若违反，可改用 Bootstrap、加权最小二乘或非参数回归。"
            ),
            category="assumption",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="斜率显著就能说 X 导致 Y 吗？",
            answer_template=(
                "不能。回归只是一种关联模型，"
                "不解决因果识别问题（confounders、reverse causality、selection）。"
                "在横断面数据上，斜率显著只说明 X 与 Y 关联在统计上不为 0，"
                "因果推断需要实验设计或准实验方法（IV、DID、RDD）。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="样本量不足会怎样？",
            answer_template=(
                "经验法则：n ≥ 50 + 8k（k 为预测变量数），单变量回归至少 n ≥ 60。"
                "样本不足会：(1) 标准误大，CI 宽；"
                "(2) 假设违反检测能力低；(3) 模型过拟合。"
            ),
            category="data",
            difficulty="常问",
            placeholders=[],
        ),
    ],

    "multiple_regression": [
        QATemplate(
            question="多元回归比简单回归多了什么？",
            answer_template=(
                "多元回归同时纳入多个预测变量，每个β代表「控制其他变量后」对因变量的独立贡献。"
                "本研究纳入了 {n_predictors} 个预测变量。"
                "可以回答：「在其他变量恒定时，X 对 Y 的净效应是多少」。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["n_predictors"],
        ),
        QATemplate(
            question="多重共线性是什么？怎么检测和处理？",
            answer_template=(
                "多重共线性：预测变量之间高度相关，导致回归系数估计不稳定。"
                "检测：VIF（方差膨胀因子）。VIF<5 通常可接受，<10 为容忍上限。"
                "处理：(1) 删除冗余变量；(2) 主成分回归；(3) 岭回归（ridge regression）。"
                "本研究 VIF 检测结果显示{vif_status}。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["vif_status"],
        ),
        QATemplate(
            question="预测变量怎么选？",
            answer_template=(
                "理论驱动优先：基于文献和理论选择有意义的变量。"
                "数据驱动方法（逐步回归 stepwise）易过拟合，结果不稳定，"
                "本科论文不推荐。"
                "若变量很多，建议先用 LASSO 或弹性网络做正则化变量选择。"
            ),
            category="method",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量需要多大？",
            answer_template=(
                "经验法则：n ≥ 50 + 8k（k 为预测变量数）。"
                "本研究有 {n_predictors} 个预测变量，建议 n ≥ {min_n}。"
                "样本不足会导致系数估计不稳定、CI 宽、假设检测能力低。"
            ),
            category="data",
            difficulty="必问",
            placeholders=["n_predictors", "min_n"],
        ),
        QATemplate(
            question="标准化系数 β 和未标准化系数 B 哪个更重要？",
            answer_template=(
                "B（未标准化）：保留原变量单位，便于实际意义解读（X 多 1 元，Y 多 B 个单位）。"
                "β（标准化）：消除单位差异，便于比较不同预测变量的相对重要性。"
                "建议两者都报告：B 解读实际效应，β 比较相对贡献。"
            ),
            category="effect",
            difficulty="常问",
            placeholders=[],
        ),
    ],

    "hierarchical_regression": [
        QATemplate(
            question="层次回归的目的是什么？",
            answer_template=(
                "层次回归把预测变量按理论顺序分层加入模型，"
                "考察每层预测变量是否在控制前层变量后仍有「增量解释力」（ΔR²）。"
                "本研究依次加入：{layer_description}。"
                "可以回答「核心变量在控制人口学变量后是否仍显著」。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["layer_description"],
        ),
        QATemplate(
            question="ΔR² 显著意味着什么？",
            answer_template=(
                "ΔR² 显著表示新加入的预测变量在控制前层变量后，"
                "能额外解释一定比例的因变量变异。"
                "本研究第二层（核心预测变量）ΔR² = {delta_r_sq:.3f}（p={delta_p:.3f}），"
                "F change = {f_change:.2f}。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["delta_r_sq", "delta_p", "f_change"],
        ),
        QATemplate(
            question="变量进入顺序怎么确定？",
            answer_template=(
                "理论驱动：(1) 第一层放入控制变量（人口学、混杂因素）；"
                "(2) 第二层放入核心预测变量；"
                "(3) 后续层可以加交互项或调节变量。"
                "顺序应在分析前确定，事后调换顺序属于 p-hacking。"
            ),
            category="method",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="层次回归与逐步回归（stepwise）的区别？",
            answer_template=(
                "层次回归：研究者基于理论指定变量进入顺序。"
                "逐步回归：算法基于 p 值或 AIC 自动选择变量。"
                "层次回归更可解释、更稳健，本科论文推荐。"
                "逐步回归易过拟合，结果难以重复，仅在探索性分析中使用。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量怎么算？",
            answer_template=(
                "经验法则：n ≥ 50 + 8 × 总预测变量数。"
                "层次回归各层都要在样本支持下进行：建议 n ≥ 100，复杂模型 n ≥ 200。"
                "样本不足会导致 ΔR² 估计不稳定。"
            ),
            category="data",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="层次回归的假设和普通多元回归一样吗？",
            answer_template=(
                "是的，层次回归本质是多个嵌套的多元回归，假设相同："
                "线性、独立、同方差、残差正态、无强多重共线性。"
                "需要在最终模型上检验所有假设。"
            ),
            category="assumption",
            difficulty="常问",
            placeholders=[],
        ),
    ],

    "moderation": [
        QATemplate(
            question="什么是调节效应？为什么用调节模型？",
            answer_template=(
                "调节效应：自变量 X 对因变量 Y 的影响，会随着调节变量 W 的取值而变化。"
                "本研究关心「{moderator}」是否调节「{iv}」对「{dv}」的影响。"
                "用回归方程：Y = β₀ + β₁X + β₂W + β₃(X×W)。β₃ 是调节效应。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["moderator", "iv", "dv"],
        ),
        QATemplate(
            question="为什么要把变量中心化？",
            answer_template=(
                "中心化（每个变量减去均值）能减少 X 与 X×W 之间的多重共线性，"
                "使主效应系数更易解读（在调节变量均值水平下，X 的效应）。"
                "对调节项 β₃ 本身的检验不影响，但常规建议仍是做中心化。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="调节效应显著之后，怎么解读？",
            answer_template=(
                "用简单斜率（simple slopes）分析：在调节变量取低（M-1SD）、中（M）、高（M+1SD）时，"
                "分别考察自变量对因变量的效应是否显著。"
                "本研究的简单斜率分析结果显示具体调节模式。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="如果调节项的 p 值在 .05 边缘，怎么判断？",
            answer_template=(
                "调节效应通常较弱、检验效力低。p 值 .05-.10 属于「边缘显著」，"
                "建议：(1) 看效应量是否实质有意义；"
                "(2) 看 95% CI 是否跨越 0；"
                "(3) 用 Johnson-Neyman 程序找显著区间；"
                "(4) 在论文中如实报告，避免「显著化」表述。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="样本量需要多大？",
            answer_template=(
                "调节效应检测需要较大样本：n ≥ 100 起步，复杂模型 n ≥ 200。"
                "n 不足时，调节项检验效力极低，假阴性风险高。"
                "可用 G*Power 或 Schoemann et al. (2017) 的应用计算所需样本。"
            ),
            category="data",
            difficulty="常问",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # 中介
    # ====================================================================== #
    "mediation": [
        QATemplate(
            question="为什么用 Bootstrap 而不是 Sobel test？",
            answer_template=(
                "Sobel test 假设间接效应 ab 服从正态分布，但实际中 ab 通常偏态。"
                "Bootstrap 通过重复抽样（本研究 5000 次）构造 ab 的实际分布，"
                "得到偏差校正的 95% 置信区间，统计效力更强、Type I 错误率更低（Hayes, 2018）。"
            ),
            category="method",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="间接效应的置信区间不包含 0，能说中介存在吗？",
            answer_template=(
                "可以说间接效应在统计上显著。本研究 Bootstrap 95% CI = [{ci_lower:.3f}, {ci_upper:.3f}]，"
                "不包含 0，表明 {mediator} 在 {iv} → {dv} 关系中起到{mediation_type}中介作用。"
                "但需注意：横断面数据无法严格证明中介的因果链，"
                "未来应采用纵向设计强化推论。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=["ci_lower", "ci_upper", "mediator", "iv", "dv", "mediation_type"],
        ),
        QATemplate(
            question="Baron & Kenny 的逐步法和 Bootstrap 哪个对？",
            answer_template=(
                "Baron & Kenny (1986) 逐步法已被认为过于保守、可能漏检间接效应。"
                "现代共识（Hayes, 2018）：直接用 Bootstrap 检验 ab 的 95% CI，"
                "不必逐步检验 c → a → b → c'。"
                "本研究遵循现代标准。"
            ),
            category="method",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="完全中介和部分中介怎么区分？",
            answer_template=(
                "传统：c' 不显著 → 完全中介；c' 仍显著但减小 → 部分中介。"
                "但「完全/部分」分类已被批评（Hayes 2018）：c' 不显著可能只是检验效力不足，"
                "不应过度解读。建议直接报告间接效应大小及 CI，淡化分类。"
            ),
            category="effect",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="横断面数据做中介分析合理吗？",
            answer_template=(
                "学界对此有争议。横断面数据无法验证中介所暗含的时间顺序（X → M → Y），"
                "结果只能视为「关联模式」而非「因果链」。"
                "本研究承认这一局限，未来需用纵向追踪或实验设计验证。"
                "在论文中应避免使用「导致」、「促使」等强因果语言。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # 信度
    # ====================================================================== #
    "cronbach_alpha": [
        QATemplate(
            question="α = {alpha:.3f} 是高还是低？",
            answer_template=(
                "通常认为 α > .70 表示量表内部一致性可接受，"
                ".80 以上为良好，.90 以上为优秀（Nunnally, 1978）。"
                "本研究 α = {alpha:.3f}，{alpha_judge}，"
                "表明该量表测量的{construct}具有{reliability_level}的内部一致性。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["alpha", "alpha_judge", "construct", "reliability_level"],
        ),
        QATemplate(
            question="α 高就一定是好量表吗？",
            answer_template=(
                "不一定。α 只反映内部一致性，不能保证：(1) 内容效度（题项是否覆盖构念全部内涵）；"
                "(2) 结构效度（题项是否真的测量同一构念）；"
                "(3) 区分效度（与其他构念是否可区分）。"
                "本研究还需结合 EFA/CFA 和效标关联效度等多种证据综合判断。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="α 太高（>.95）也是问题吗？",
            answer_template=(
                "是的。α > .95 可能意味着题目高度冗余（语义重复），"
                "或测量的构念过于狭窄，缺乏内容覆盖度。"
                "建议结合「项已删除时的α」（α-if-item-deleted）和题目相关矩阵看冗余情况。"
            ),
            category="limit",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="α 受样本量影响吗？",
            answer_template=(
                "α 估计的稳定性受样本量影响。建议 n ≥ 200 才能得到稳定估计。"
                "小样本（n < 100）的 α 置信区间较宽，可同时报告 α 的 95% CI（Feldt 公式）。"
            ),
            category="data",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="为什么用 Cronbach α 而不是其他信度系数？",
            answer_template=(
                "α 是连续/Likert 量表最常用的内部一致性信度系数，"
                "本质是题目间相关的一种平均。"
                "比分半信度更稳定，比测验-再测信度便于一次施测。"
                "若题目为二分类，可改用 KR-20；若数据满足τ-等价假设，可用 ω 系数。"
            ),
            category="method",
            difficulty="必问",
            placeholders=[],
        ),
        QATemplate(
            question="α 显著就能直接用这份量表测人吗？",
            answer_template=(
                "α 高只代表内部一致，但不保证：(1) 量表测的是你想测的构念（建构效度）；"
                "(2) 跨样本稳定（再测信度）；(3) 与外部标准吻合（效标效度）。"
                "建议综合多种证据后再用于实测。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    "split_half": [
        QATemplate(
            question="分半信度怎么算？为什么用 Spearman-Brown 校正？",
            answer_template=(
                "把题目分成两半（如奇偶分半），分别求总分，计算两半相关 r。"
                "Spearman-Brown 校正：r' = 2r / (1+r)，校正因为「两半各只有一半题目」"
                "导致的信度低估。本研究分半信度（校正后）= {split_half:.3f}。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["split_half"],
        ),
        QATemplate(
            question="分半信度和 α 哪个更好？",
            answer_template=(
                "α 是所有可能分半的平均，比单次分半更稳定，因此通常优先报告 α。"
                "但分半信度对小样本/题目少（≤10题）的量表仍有诊断价值。"
                "两者不应替代，可同时报告。"
            ),
            category="method",
            difficulty="常问",
            placeholders=[],
        ),
        QATemplate(
            question="效应解读？",
            answer_template=(
                "分半信度评判标准与 α 类似：>.70 可接受，>.80 良好，>.90 优秀。"
                "本研究 = {split_half:.3f}，属于{reliability_level}水平。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["split_half", "reliability_level"],
        ),
        QATemplate(
            question="分半方式（奇偶 vs 前后）会影响结果吗？",
            answer_template=(
                "会。前后分半假设题目顺序无系统性差异（无练习/疲劳效应），"
                "奇偶分半通常更稳健。本研究采用奇偶分半。"
                "若量表有明显顺序效应（如难度递增），应选奇偶或随机分半。"
            ),
            category="data",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="分半信度高就说明量表能用了吗？",
            answer_template=(
                "不能。分半只反映两半的一致性，不保证：(1) 与构念匹配（效度）；"
                "(2) 跨时间稳定（再测）；(3) 题目代表性。"
                "建议综合 α、CFA、效标效度等多种证据。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # EFA
    # ====================================================================== #
    "efa": [
        QATemplate(
            question="你怎么决定保留几个因素？",
            answer_template=(
                "本研究综合三个标准决定因素数：(1) Kaiser 准则（特征值>1）；"
                "(2) 碎石图拐点；(3) 平行分析（与随机数据特征值比较）。"
                "三种方法一致建议保留 {n_factors} 个因素。"
                "其中平行分析最稳健，已被建议作为首选标准（Hayton et al., 2004）。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["n_factors"],
        ),
        QATemplate(
            question="KMO = {kmo:.3f} 和 Bartlett 检验是干什么的？",
            answer_template=(
                "KMO 衡量变量间偏相关的程度，KMO > .60 表示数据适合做因素分析（>0.80 优秀）。"
                "Bartlett 球形检验验证相关矩阵是否显著偏离单位矩阵（如显著则适合 EFA）。"
                "本研究 KMO = {kmo:.3f}（{kmo_judge}），Bartlett χ²(p) = {bartlett_p}（显著），"
                "数据适合进行因素分析。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["kmo", "kmo_judge", "bartlett_p"],
        ),
        QATemplate(
            question="正交旋转和斜交旋转哪个好？",
            answer_template=(
                "Varimax（正交）：假设因素间不相关，结构清晰，便于解读。"
                "Promax/Oblimin（斜交）：允许因素相关，更符合心理学构念实际"
                "（如焦虑维度间常相关）。"
                "现代心理学研究推荐先用斜交，看因素相关矩阵：相关 < .30 可改用正交。"
            ),
            category="method",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="EFA 的样本量要求？",
            answer_template=(
                "经验法则：(1) n ≥ 题目数 × 5（Tabachnick & Fidell）；"
                "(2) n ≥ 200 起步（Comrey & Lee 1992）；"
                "(3) MSA ≥ 0.80 时可放宽。"
                "本研究 n = {n}，{sample_judgment}。"
            ),
            category="data",
            difficulty="必问",
            placeholders=["n", "sample_judgment"],
        ),
        QATemplate(
            question="EFA 找出的「因素」就是真实的心理结构吗？",
            answer_template=(
                "不一定。EFA 找的是「数学上能解释相关」的潜变量，"
                "是否对应真实心理结构需要：(1) 理论支持；(2) 命名合理；"
                "(3) CFA 在新样本验证；(4) 效标关联效度证据。"
                "命名因素时切忌「过度推断」（不能因为有几道题载荷高就贴新标签）。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
    ],

    # ====================================================================== #
    # 卡方
    # ====================================================================== #
    "chi_square_independence": [
        QATemplate(
            question="卡方独立性检验在做什么？",
            answer_template=(
                "卡方独立性检验考察两个分类变量之间是否相互独立。"
                "本研究检验「{var1}」和「{var2}」的关联。"
                "若 p < .05，则拒绝「独立」零假设，说明两变量有关联。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["var1", "var2"],
        ),
        QATemplate(
            question="卡方检验对样本量有要求吗？",
            answer_template=(
                "卡方检验要求每个单元格的期望频数 ≥ 5，"
                "若超过 20% 的单元格期望频数 < 5，结果可能不准。"
                "此时应改用 Fisher 精确检验（2×2 表）或将类别合并。"
                "本研究 {expected_freq_status}。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["expected_freq_status"],
        ),
        QATemplate(
            question="效应量 Cramér's V 怎么解读？",
            answer_template=(
                "Cramér's V = {effect_size:.3f}。"
                "对 2×2 表（=φ系数）：.10 小，.30 中，.50 大。"
                "对更大表，临界值取决于 df。本研究属于{effect_label}效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
        QATemplate(
            question="卡方显著就能说一个变量影响另一个吗？",
            answer_template=(
                "不能。卡方只揭示关联，不证明因果方向。"
                "例如「性别与文理科选择」关联显著，不能推断「性别决定专业」，"
                "可能存在社会期待、家庭引导等中介机制。"
            ),
            category="infer",
            difficulty="必问",
            placeholders=[],
        ),
    ],

    "chi_square_gof": [
        QATemplate(
            question="卡方拟合优度检验和独立性检验的区别？",
            answer_template=(
                "拟合优度检验：考察一个分类变量的实际分布是否符合理论分布"
                "（如均匀分布、正态分布的期望比例）。"
                "独立性检验：考察两个分类变量是否相互独立。"
                "本研究检验「{var}」是否符合预期比例 {expected_ratio}。"
            ),
            category="method",
            difficulty="必问",
            placeholders=["var", "expected_ratio"],
        ),
        QATemplate(
            question="期望频数怎么定？",
            answer_template=(
                "(1) 理论假设：基于先验理论或文献设定（如均匀=每类相等）；"
                "(2) 历史数据：基于过去观察的比例；"
                "(3) 关联零假设：所有类别频数相等。"
                "本研究依据{expected_source}。"
            ),
            category="method",
            difficulty="常问",
            placeholders=["expected_source"],
        ),
        QATemplate(
            question="拟合优度检验的样本量要求？",
            answer_template=(
                "每个类别期望频数 ≥ 5。"
                "若某类别期望频数太小，可考虑合并类别或用精确检验。"
                "本研究的期望频数{expected_freq_status}。"
            ),
            category="assumption",
            difficulty="必问",
            placeholders=["expected_freq_status"],
        ),
        QATemplate(
            question="如果不符合预期分布，意味着什么？",
            answer_template=(
                "意味着实际分布偏离了期望，需要进一步分析「在哪偏离」。"
                "可以看每类的标准化残差（>±1.96 表示该类显著偏离），"
                "或事后做后续描述性分析（计算实际比例）。"
                "拒绝零假设只是「不一致」，不解释「为什么不一致」。"
            ),
            category="infer",
            difficulty="刁钻",
            placeholders=[],
        ),
        QATemplate(
            question="效应量怎么算？",
            answer_template=(
                "可使用 Cohen's w = √(χ²/n)：.10 小，.30 中，.50 大效应。"
                "本研究 w = {effect_size:.3f}，属于{effect_label}效应。"
            ),
            category="effect",
            difficulty="必问",
            placeholders=["effect_size", "effect_label"],
        ),
    ],
}
