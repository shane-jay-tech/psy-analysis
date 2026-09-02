"""分析思路生成器：基于模板字典 + 结果对象动态生成推理过程

设计理念：
- 每个检验类型在 TEST_TEMPLATES 中定义描述片段（why, steps, interpretation_guide, alternatives）
- generate_reasoning() 读取模板 + 结果对象，动态组装 AnalysisReasoning
- 前提检查和假设检验结果从 output 字典中自动提取
- 新增检验类型只需在 TEST_TEMPLATES 中添加条目即可
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from src.output.learning_card import generate_learning_card


@dataclass
class StepCheck:
    name: str
    result: str
    passed: bool
    detail: str = ""


@dataclass
class AnalysisReasoning:
    test_type: str
    test_name_zh: str
    why_this_test: str
    data_requirements: List[StepCheck] = field(default_factory=list)
    assumption_checks: List[StepCheck] = field(default_factory=list)
    analysis_steps: List[str] = field(default_factory=list)
    interpretation_guide: str = ""
    alternatives: List[str] = field(default_factory=list)
    learning_card: Any = None


# ===========================================================================
# 模板字典：test_type → 描述片段
# ===========================================================================
TEST_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "descriptive": {
        "why": "描述性统计是数据分析的第一步，用于了解数据的基本特征和分布情况。",
        "steps": [
            "计算各变量的集中趋势指标（均值、中位数）",
            "计算离散程度指标（标准差、方差、极差）",
            "检查分布形态（偏度、峰度），初步判断正态性",
            "输出频数分布和描述统计表",
        ],
        "guide": (
            "关注各变量的均值和标准差，了解样本的整体水平和变异程度。"
            "偏度绝对值 > 1 提示分布偏斜；峰度绝对值 > 2 提示分布形态偏离正态。"
        ),
        "alts": [],
    },
    "independent_ttest": {
        "why": "因变量是连续数值型变量，自变量是二分类变量（恰好2个组），研究目的是比较两组均值差异。独立样本t检验是最合适的参数检验方法。",
        "steps": [
            "检验前提条件 — 对各组进行正态性检验（Shapiro-Wilk）和方差齐性检验（Levene）",
            "方差不齐 → 自动使用Welch校正的t检验 | 假设满足 → 执行标准独立样本t检验",
            "计算效应量 Cohen's d（小=0.2, 中=0.5, 大=0.8）",
            "计算均值差的95%置信区间",
        ],
        "guide": (
            "首先看p值：p < 0.05 表示两组差异具有统计显著性。"
            "然后看效应量Cohen's d：d的绝对值反映差异的实际大小。"
            "最后看95%置信区间：区间不包含0进一步支持差异存在。"
            "注意：显著性受样本量影响，务必结合效应量判断实际意义。"
        ),
        "alts": [
            "Mann-Whitney U检验 — 非参数替代，不要求正态性",
            "Welch校正 — 不要求方差齐性的t检验变体",
        ],
    },
    "paired_ttest": {
        "why": "配对样本t检验适用于同一组被试在两种条件下（如前后测）的比较。因为数据存在自然配对，使用独立样本t检验会损失统计检验力。",
        "steps": [
            "计算每个被试两次测量的差值（D = 后测 - 前测）",
            "检验差值的正态性（Shapiro-Wilk）",
            "对差值进行单样本t检验（H₀: 均值差=0）",
            "计算效应量 Cohen's dz",
        ],
        "guide": "p < 0.05 表示前后测有显著变化。均值差的正负表示变化方向。Cohen's dz解读同d：0.2小/0.5中/0.8大。",
        "alts": ["Wilcoxon符号秩检验 — 差值为非正态时的非参数替代"],
    },
    "one_sample_ttest": {
        "why": "单样本t检验用于比较样本均值与某个已知的参照值（如常模、理论值）。",
        "steps": [
            "检验样本数据的正态性",
            "计算样本均值与检验值的差值",
            "执行单样本t检验（H₀: 样本均值=检验值）",
            "计算效应量和置信区间",
        ],
        "guide": "p < 0.05 表示样本均值与检验值有显著差异。均值差的正负表示样本均值高于或低于检验值。",
        "alts": ["若数据严重非正态，可考虑Wilcoxon符号秩检验（单样本版）"],
    },
    "one_way_anova": {
        "why": "因变量是连续数值型，自变量有三个或更多水平。单因素ANOVA可以在控制整体α=0.05的前提下，一次性检验所有组的均值是否相等，避免多次t检验导致的α膨胀。",
        "steps": [
            "检验方差齐性（Levene检验）",
            "执行单因素被试间ANOVA — 将总变异分解为组间和组内",
            "计算效应量 η²（小=0.01, 中=0.06, 大=0.14）及其置信区间",
            "F检验显著 → 执行Tukey HSD事后多重比较 | F检验不显著 → 无需事后比较",
        ],
        "guide": (
            "首先看ANOVA F检验p值：p < 0.05 表示至少有一组与其他组不同。"
            "显著时看事后检验确定具体哪些组之间存在差异。"
            "η² 反映组间差异能解释总变异的比例。"
        ),
        "alts": [
            "Welch ANOVA — 不要求方差齐性",
            "Kruskal-Wallis H检验 — 非参数替代，不要求正态性",
        ],
    },
    "two_way_anova": {
        "why": "双因素方差分析用于同时考察两个自变量的主效应及其交互作用，提高统计检验力并更贴近真实情境。",
        "steps": [
            "计算两个自变量的主效应",
            "计算交互效应（A×B）",
            "交互效应显著 → 需做简单效应分析",
            "交互效应不显著 → 分别解读两个主效应",
        ],
        "guide": (
            "优先看交互效应：若显著，说明一个因素的效应在另一个因素的不同水平上不同。"
            "绘制交互作用图可以直观展示交互模式。若交互不显著，则可直接解读两个主效应。"
        ),
        "alts": [],
    },
    "repeated_anova": {
        "why": "重复测量方差分析适用于同一组被试在多个时间点或条件下被重复测量的设计，能分离出被试间差异从而更敏感地检测处理效应。",
        "steps": [
            "检验球形假设（Mauchly检验）",
            "执行重复测量ANOVA",
            "不满足球形假设 → 应用GG校正",
            "显著 → 执行事后配对比较",
        ],
        "guide": "首先看球形假设：p > 0.05 满足，看标准F检验。违反则看GG校正后的p值。广义eta²（η²G）用于跨研究可比性。",
        "alts": [
            "Greenhouse-Geisser校正 — 已自动应用",
            "Friedman检验 — 非参数替代方法",
        ],
    },
    "pearson_corr": {
        "why": "分析变量均为连续数值型，Pearson相关系数是最常用的线性相关指标。注意：只度量线性关系，非线性关系需用Spearman。",
        "steps": [
            "绘制散点图，目测线性趋势和异常值",
            "检验双变量正态性",
            "计算Pearson相关系数r和显著性p值",
            "构建相关矩阵（多变量时）",
        ],
        "guide": (
            "|r| < 0.1：极弱；0.1-0.3：弱；0.3-0.5：中等；0.5-0.7：较强；> 0.7：强。"
            "p < 0.05 表示相关系数显著不等于0。显著性受样本量影响，务必结合r判断。**相关不等于因果！**"
        ),
        "alts": [
            "Spearman相关 — 非参数替代，只要求单调关系",
            "Kendall's τ — 对异常值更稳健的秩相关",
        ],
    },
    "spearman_corr": {
        "why": "Spearman秩相关是Pearson相关的非参数替代，基于秩次而非原始值，不要求正态分布或线性关系。",
        "steps": [
            "将原始数据转换为秩次",
            "计算秩次之间的Pearson相关=Spearman's ρ",
            "检验ρ的显著性",
        ],
        "guide": "Spearman's ρ 的解释与Pearson r 类似。数据同时满足Pearson条件时，Spearman效力略低。",
        "alts": [],
    },
    "partial_corr": {
        "why": "偏相关分析用于衡量在控制其他变量影响后，两个变量之间的'净'相关，剔除第三变量的混淆效应。",
        "steps": [
            "对每个变量对，将其余变量作为控制变量",
            "计算残差（排除控制变量的影响）",
            "计算残差之间的相关系数=偏相关系数",
        ],
        "guide": "偏相关系数的解读与普通相关系数相同，但它排除了指定控制变量的影响。比较偏相关与零阶相关的变化可判断第三变量混淆程度。",
        "alts": [],
    },
    "point_biserial": {
        "why": "点二列相关用于衡量一个连续变量与一个真正的二分类变量之间的关联，是Pearson相关在特殊情形下的等价形式。",
        "steps": [
            "将二分类变量编码为0/1",
            "计算编码后变量与连续变量的Pearson相关=点二列相关系数",
            "检验显著性",
        ],
        "guide": "r_pb的取值范围为[-1, 1]，符号取决于两组均值差异方向。r_pb²=二分类变量能解释的连续变量方差比例。",
        "alts": [],
    },
    "chi_square_independence": {
        "why": "卡方独立性检验用于判断两个分类变量之间是否存在关联，比较实际观测频数与期望频数的差异。",
        "steps": [
            "构建列联表（交叉表）",
            "计算各单元格的期望频数",
            "计算χ²统计量：Σ[(O-E)²/E]",
            "计算Cramér's V（效应量：0.1小/0.3中/0.5大）",
        ],
        "guide": (
            "p < 0.05 表示两个分类变量之间存在显著关联。"
            "Cramér's V 反映关联强度。查看标准化残差（|残差| > 2）识别贡献最大的单元格。"
        ),
        "alts": [
            "Fisher精确检验 — 2×2表且期望频数<5时使用",
            "似然比χ² (G-test) — 卡方的替代统计量",
        ],
    },
    "chi_square_gof": {
        "why": "卡方拟合优度检验用于判断观测频数分布是否与某种理论分布一致，检验的是单一分类变量的分布形态。",
        "steps": [
            "统计各分类的观测频数",
            "根据理论比例计算期望频数",
            "计算χ² = Σ[(O-E)²/E]",
            "检验观测分布与期望分布是否一致",
        ],
        "guide": "p < 0.05 表示观测分布与期望分布存在显著差异。查看残差（观测-期望）可识别偏离最大的类别。",
        "alts": [],
    },
    "linear_regression": {
        "why": "线性回归用于考察一个自变量对一个因变量的预测作用，提供预测方程以量化自变量变化一个单位时因变量的变化量。",
        "steps": [
            "绘制散点图，目测线性趋势",
            "使用最小二乘法(OLS)估计回归系数",
            "检验整体回归模型（F检验）和各系数（t检验）",
            "计算决定系数R²和Cohen's f²效应量",
            "诊断高影响点（Cook's D > 4/n 的个案）",
        ],
        "guide": (
            "R² 表示自变量能解释因变量变异的百分比。"
            "非标准化系数B表示自变量每增加1个单位因变量的变化量。"
            "Cohen's f²：0.02小/0.15中/0.35大。"
            "检查Cook's距离，若有个案D > 4/n，需关注其是否过度影响回归结果。"
        ),
        "alts": ["多元回归 — 纳入多个自变量以提高预测力和控制混淆"],
    },
    "multiple_regression": {
        "why": "多元回归同时考察多个自变量对一个因变量的预测作用，可评估每个自变量的独特贡献并提供整体模型的预测力。",
        "steps": [
            "检验多重共线性（VIF应 < 10，最好 < 5）",
            "OLS估计回归系数",
            "检验整体模型（F检验）",
            "检验各预测变量的独特贡献（t检验、Cohen's f²）",
            "比较标准化系数β判断变量重要性",
            "诊断高影响点（Cook's D, 学生化残差, 杠杆值）",
        ],
        "guide": (
            "调整R²比R²更可靠，惩罚了冗余变量。标准化系数β用于比较不同单位变量的相对重要性。"
            "VIF > 10表示严重共线性问题，应考虑删除或合并相关变量。"
            "Cohen's f²反映每个预测变量的独特效应量。关注Cook's D > 4/n的高影响个案。"
        ),
        "alts": ["层次回归 — 分块进入自变量，检验增量效度"],
    },
    "hierarchical_regression": {
        "why": "层次回归按理论驱动的顺序分块纳入自变量，检验每新增一个变量块是否能显著提高模型解释力（ΔR²），是检验增量效度的主要方法。",
        "steps": [
            "第1块变量进入 — 建立基础模型",
            "第2块变量进入 — 计算ΔR²和ΔF",
            "后续各块依次进入 — 每次检验增量贡献",
            "报告各块ΔR²的Cohen's f²效应量",
            "报告最终模型的完整系数表和诊断信息",
        ],
        "guide": (
            "ΔR² 表示新增变量块在已有变量基础上额外解释的变异比例。"
            "ΔF的p < 0.05 表示该块的增量贡献显著。"
            "Cohen's f²(ΔR²)解读：0.02小/0.15中/0.35大。"
            "最终模型中看各变量的标准化β和p值。"
        ),
        "alts": [],
    },
    "cronbach_alpha": {
        "why": "Cronbach's α 是衡量量表内部一致性的最常用指标，反映各题目测量同一构念的程度。α取值范围[0, 1]。",
        "steps": [
            "计算各题目之间的协方差矩阵",
            "计算Cronbach's α = [k/(k-1)] × [1 - ΣVar(i)/Var(total)]",
            "计算α的95%置信区间",
            "逐题分析（α-if-item-deleted 和 题总相关）",
        ],
        "guide": (
            "α ≥ 0.90 优秀；0.80-0.90 良好；0.70-0.80 可接受；0.60-0.70 探索性边界；< 0.60 不可接受。"
            "查看'删除后α'：若删除某题后α显著上升，说明该题可能质量较差。"
            "题总相关(CITC)应 ≥ 0.30，否则建议删除该题。"
        ),
        "alts": ["分半信度", "McDonald's ω"],
    },
    "split_half": {
        "why": "分半信度将量表题目分为两半（通常奇偶分半），计算两半之间的相关后用Spearman-Brown公式校正。",
        "steps": [
            "按奇偶序号将题目分为两半",
            "计算两半总分之间的Pearson相关",
            "Spearman-Brown校正：r_full = 2r / (1+r)",
        ],
        "guide": "分半信度 ≥ 0.70 为可接受。不同分半方式得到不同估计，Cronbach's α更稳定。",
        "alts": ["Cronbach's α — 更全面的内部一致性指标"],
    },
    "mann_whitney": {
        "why": "Mann-Whitney U检验是独立样本t检验的非参数替代，比较两组数据在秩次上的差异，不要求正态分布。",
        "steps": [
            "合并两组数据并排序，赋予秩次",
            "分别计算两组的秩和",
            "计算U统计量并近似正态分布得到p值",
            "计算效应量 r = Z/√N 及其置信区间",
        ],
        "guide": "p < 0.05 表示两组的分布位置存在显著差异。效应量 r：0.1小/0.3中/0.5大。小样本时注意正态近似可能不精确。",
        "alts": ["独立样本t检验 — 若数据满足正态和方差齐性假设"],
    },
    "wilcoxon": {
        "why": "Wilcoxon符号秩检验是配对样本t检验的非参数替代，利用配对差值的大小和方向信息，不要求差值正态分布。",
        "steps": [
            "计算每对数据的差值",
            "对差值的绝对值排序赋予秩次",
            "分别计算正差值和负差值的秩和",
            "基于较小的秩和计算p值",
        ],
        "guide": "p < 0.05 表示两次测量存在显著差异。匹配对秩双列相关反映效应大小。小样本（n<10）时已自动切换到精确检验。",
        "alts": ["配对样本t检验 — 若差值满足正态分布"],
    },
    "kruskal_wallis": {
        "why": "Kruskal-Wallis H检验是单因素ANOVA的非参数替代，基于秩次比较多组数据的分布差异，不要求正态性或方差齐性。",
        "steps": [
            "合并所有组数据并排序",
            "计算各组的平均秩",
            "计算H统计量（近似χ²分布）",
            "若显著 → Dunn事后多重比较（默认Holm-Bonferroni校正）",
        ],
        "guide": (
            "p < 0.05 表示至少有一组与其他组存在显著差异。"
            "η²H 效应量：0.01小/0.06中/0.14大。"
            "事后检验使用Holm-Bonferroni校正控制多重比较的第I类错误，备选有Bonferroni和FDR(BH)校正。"
        ),
        "alts": ["单因素ANOVA — 若满足正态性和方差齐性"],
    },
    "friedman": {
        "why": "Friedman检验是重复测量ANOVA的非参数替代，比较同一批被试在多个条件下的重复测量数据。",
        "steps": [
            "在每个被试内对重复测量条件排序（赋予秩次1~k）",
            "计算各条件的平均秩",
            "计算Friedman χ²统计量",
            "计算Kendall's W（一致性系数）",
        ],
        "guide": "p < 0.05 表示不同测量条件之间存在显著差异。Kendall's W：0.1小/0.3中/0.5大。",
        "alts": ["重复测量ANOVA — 若满足正态和球形假设"],
    },
    "efa": {
        "why": "探索性因素分析（EFA）用于在无先验理论的情况下，探索多个观测变量背后的潜在结构。",
        "steps": [
            "检验数据充分性（KMO和Bartlett球性检验）",
            "提取初始因素（特征值>1或平行分析）",
            "因子旋转（Varimax正交 / Promax斜交）",
            "检查共同度、交叉载荷、Heywood情况",
            "解释和命名各因素",
        ],
        "guide": (
            "KMO ≥ 0.80优秀/0.70良好/0.60勉强。"
            "载荷 > 0.40 为实质载荷，低于此阈值或存在交叉载荷的题目建议考虑删除。"
            "共同度 < 0.30的条目与提取因素的关联较弱。"
            "共同度 > 1.0为Heywood情况，提示模型设置可能不合理。"
        ),
        "alts": [],
    },
    "ancova": {
        "why": "协方差分析（ANCOVA）在方差分析的基础上纳入连续协变量，在统计上控制协变量的影响后比较组间差异，提高统计检验力。",
        "steps": [
            "检验回归斜率同质性假设",
            "执行ANCOVA（Type III SS）",
            "比较调整后均值（排除协变量影响）",
            "若组间差异显著 → 进行事后比较",
        ],
        "guide": "调整后均值是'假设所有组在协变量上相等时'的估计均值。η²p 反映排除协变量效应后的组间差异效应量。",
        "alts": ["分层回归 — 同样可以控制协变量，且更灵活"],
    },
    "mediation": {
        "why": "中介分析用于检验自变量X是否通过中介变量M间接影响因变量Y，揭示'X为什么会影响Y'的心理机制。",
        "steps": [
            "标准化所有变量以得到完全标准化系数（β）",
            "检验路径a（X→M）和路径b（M→Y）",
            "计算间接效应a*b",
            "执行5000次Bootstrap，计算偏差校正95%置信区间",
            "若Bootstrap CI不包含0 → 中介效应显著",
        ],
        "guide": (
            "仅使用Bootstrap偏差校正置信区间判断中介效应显著性，不再依赖Baron & Kenny逐步法或Sobel检验。"
            "CI不包含0：中介效应显著。中介效应占比 = 间接效应/总效应 × 100%。"
            "支持多个并列中介变量，可同时报告各特定间接效应和总间接效应。"
            "所有系数为完全标准化β，便于跨研究比较。"
        ),
        "alts": ["结构方程模型(SEM) — 可同时检验多中介和潜变量"],
    },
    "moderation": {
        "why": "调节分析用于检验某个变量M是否改变自变量X对因变量Y的影响强度或方向，回答'X对Y的影响在什么条件下不同'。",
        "steps": [
            "中心化X和M（减少共线性）",
            "构建交互项 X×M",
            "回归 Y ~ X + M + X×M",
            "交互项显著 → 简单斜率分析（±1SD）",
            "报告Cohen's f²（交互效应量）",
        ],
        "guide": (
            "交互项p < 0.05 → 调节效应显著。"
            "简单斜率分析显示在不同调节变量水平上X→Y的关系如何变化。"
            "Cohen's f²交互效应量：0.02小/0.15中/0.35大。"
        ),
        "alts": ["多组SEM — 当调节变量为分类变量时"],
    },
}


# ===========================================================================
# 统一生成引擎
# ===========================================================================

def generate_reasoning(output: Dict[str, Any]) -> AnalysisReasoning:
    """
    根据分析输出，使用模板字典 + 结果对象动态生成分析思路。

    流程：
    1. 读取 TEST_TEMPLATES 获取静态描述片段
    2. 从 output["result"] 和 output["assumptions"] 提取动态假设检查结果
    3. 从 output["plan"] 提取变量信息
    4. 组装成完整的 AnalysisReasoning
    """
    test_type = output.get("test_type", "")
    test_name_zh = output.get("test_name_zh", "")
    plan = output.get("plan")
    result = output.get("result")
    assumptions = output.get("assumptions", {})
    data_quality = output.get("data_quality")

    # 获取模板
    tmpl = TEST_TEMPLATES.get(test_type, {})

    # 构建"为什么选择这个检验"（插入变量信息）
    why = _build_why(tmpl, plan, test_type, test_name_zh)

    # 构建前提条件（数据要求）
    requirements = _build_requirements(tmpl, plan, result, test_type)

    # 构建假设检验结果（动态提取）
    checks = _build_assumption_checks(result, assumptions)

    # 构建分析步骤
    steps = tmpl.get("steps", ["执行统计分析", "输出结果和图表"])

    # 解读指南
    guide = _build_guide(tmpl, result, test_type)

    # 替代方法
    alternatives = tmpl.get("alts", [])

    # 附加数据质量警告到替代方法
    if data_quality and data_quality.warnings:
        # 在解读指南后附加DQ信息
        pass  # DQ警告已在output["errors"]中展示

    card = generate_learning_card(test_type, test_name_zh)

    return AnalysisReasoning(
        test_type=test_type,
        test_name_zh=test_name_zh,
        why_this_test=why,
        data_requirements=requirements,
        assumption_checks=checks,
        analysis_steps=steps,
        interpretation_guide=guide,
        alternatives=alternatives,
        learning_card=card,
    )


def _build_why(tmpl: dict, plan, test_type: str, name: str) -> str:
    """构建 why_this_test 文字"""
    base = tmpl.get("why", f"已选择「{name}」进行数据分析。")

    # 插入变量信息
    if plan:
        dv_info = ""
        iv_info = ""
        if plan.dependent_vars:
            dv_info = f"分析变量：{', '.join(plan.dependent_vars[:5])}"
            if len(plan.dependent_vars) > 5:
                dv_info += f"等{len(plan.dependent_vars)}个"
        if plan.independent_vars:
            iv_info = f"分组变量：{', '.join(plan.independent_vars[:3])}"

        if dv_info:
            base += f"\n{dv_info}"
        if iv_info:
            base += f" | {iv_info}"

    return base


def _build_requirements(tmpl: dict, plan, result, test_type: str) -> List[StepCheck]:
    """构建数据要求检查列表"""
    reqs = []

    # 根据检验类型添加通用要求
    if test_type == "descriptive":
        dv_count = len(plan.dependent_vars) if plan and plan.dependent_vars else 0
        reqs.append(StepCheck("变量类型", "数值型变量", True, f"已识别 {dv_count} 个数值变量"))
        reqs.append(StepCheck("样本量", "N ≥ 3", True, "样本量足够计算基本统计量"))

    elif test_type in ("independent_ttest",):
        reqs.append(StepCheck("变量类型", "DV=数值型 | IV=二分类", True, "因变量连续，自变量恰好2个水平"))
        reqs.append(StepCheck("样本独立性", "各组被试互不影响", True, "由研究设计保证"))

    elif test_type == "paired_ttest":
        reqs.append(StepCheck("配对设计", "同一批被试的两次测量", True, "配对是选择此检验的核心依据"))
        reqs.append(StepCheck("差值正态性", "两次测量差值应近似正态", True, "若差值非正态，使用Wilcoxon符号秩检验"))

    elif test_type in ("one_way_anova",):
        reqs.append(StepCheck("变量类型", "DV=数值型 | IV=多分类(3+水平)", True, "自变量有3个或更多水平"))
        reqs.append(StepCheck("样本独立性", "各组被试互不影响", True, "如为重复测量，应使用重复测量ANOVA"))

    elif test_type in ("pearson_corr", "spearman_corr"):
        reqs.append(StepCheck("变量类型", "连续数值型", True, ""))
        reqs.append(StepCheck("线性关系", "变量间应为线性/单调关系", True, "通过散点图验证"))

    elif test_type in ("cronbach_alpha",):
        reqs.append(StepCheck("题目数量", "≥2道题目", True, ""))
        reqs.append(StepCheck("样本量", "建议N ≥ 100", True, "小样本会导致α估计不稳定"))

    elif test_type == "mediation":
        reqs.append(StepCheck("三个变量", "X→M→Y 时序合理", True, "横断数据只能检验统计中介"))
        reqs.append(StepCheck("Bootstrap", "5000次偏差校正", True, "CI不包含0即显著，不需要逐步法"))

    elif test_type == "moderation":
        reqs.append(StepCheck("交互项", "检验X×M交互项显著性", True, "交互项显著是调节成立的前提"))

    elif test_type == "efa":
        kmo = result.kmo if result and hasattr(result, "kmo") else 0
        passed_kmo = kmo >= 0.6
        reqs.append(StepCheck("KMO抽样充分性", f"KMO={kmo}", passed_kmo,
                    "KMO ≥ 0.80良好/0.70中等/0.60勉强"))
        reqs.append(StepCheck("Bartlett球性检验", "p < 0.05", True, "相关矩阵不是单位矩阵"))
        reqs.append(StepCheck("样本量", "N ≥ 5×题目数", True, "最好≥100-200"))

    elif test_type == "ancova":
        reqs.append(StepCheck("回归斜率同质", "协变量与DV关系在各组中应相似", True, "需检验组×协变量交互"))

    return reqs


def _build_assumption_checks(result, assumptions: dict) -> List[StepCheck]:
    """从结果对象和假设检验字典中提取假设检查结果"""
    checks = []

    # 从 result 对象提取
    if result is None:
        return checks

    # 方差齐性（独立t检验、ANOVA）
    for attr in ["assumption_homogeneity", "assumption_equal_var"]:
        if hasattr(result, attr):
            aa = getattr(result, attr)
            if aa and isinstance(aa, dict) and "p_value" in aa:
                passed = aa.get("passed", True)
                checks.append(StepCheck(
                    "方差齐性（Levene）",
                    "通过" if passed else "未通过",
                    passed,
                    f"统计量={aa.get('statistic', '')}, p={aa.get('p_value', '')}",
                ))
                break

    # 球形假设（重复测量ANOVA）
    if hasattr(result, "assumption_sphericity") and result.assumption_sphericity:
        sp = result.assumption_sphericity
        passed = sp.get("passed", True)
        checks.append(StepCheck(
            "球形假设（Mauchly）",
            "通过" if passed else "未通过",
            passed,
            f"W={sp.get('statistic', '')}, p={sp.get('p_value', '')}",
        ))

    # KMO（EFA）
    if hasattr(result, "kmo"):
        kmo = result.kmo
        checks.append(StepCheck(
            "KMO抽样充分性",
            "通过" if kmo >= 0.6 else "未通过",
            kmo >= 0.6,
            f"KMO={kmo}",
        ))

    # Bartlett（EFA）
    if hasattr(result, "bartlett_p"):
        bp = result.bartlett_p
        checks.append(StepCheck(
            "Bartlett球性检验",
            "通过" if bp < 0.05 else "未通过",
            bp < 0.05,
            f"χ²={getattr(result, 'bartlett_chi2', '')}, p={bp}",
        ))

    # 共线性（回归）
    if hasattr(result, "vif_table") and result.vif_table is not None:
        high_vif = result.vif_table[result.vif_table["VIF"] > 10]
        all_ok = len(high_vif) == 0
        checks.append(StepCheck(
            "多重共线性（VIF < 10）",
            "通过" if all_ok else "未通过",
            all_ok,
            f"{len(high_vif)}个变量VIF>10" if not all_ok else "所有VIF < 10",
        ))

    # 高影响点（回归）
    if hasattr(result, "high_influence_cases") and result.high_influence_cases:
        n_high = len(result.high_influence_cases)
        checks.append(StepCheck(
            "影响点诊断（Cook's D）",
            "注意" if n_high > 0 else "通过",
            n_high == 0,
            f"检测到{n_high}个高影响个案（Cook's D > 4/n）",
        ))

    # 从 assumptions 字典提取正态性
    normality = assumptions.get("normality", {})
    for gname, ar in normality.items():
        if hasattr(ar, "passed"):
            checks.append(StepCheck(
                f"正态性（{gname}组）",
                "通过" if ar.passed else "未通过",
                ar.passed,
                f"W={ar.statistic}, p={ar.p_value}",
            ))

    # 从 assumptions 字典提取方差齐性
    homo = assumptions.get("homogeneity")
    if homo and hasattr(homo, "passed"):
        checks.append(StepCheck(
            "方差齐性（Levene）",
            "通过" if homo.passed else "未通过",
            homo.passed,
            f"F={homo.statistic}, p={homo.p_value}",
        ))

    return checks


def _build_guide(tmpl: dict, result, test_type: str) -> str:
    """构建解读指南，可插入结果对象中的实际值"""
    guide = tmpl.get("guide", "请查看上方的统计结果表格和检验指标。")

    # 插入诊断信息
    if result is None:
        return guide

    # Cronbach's α 插入实际值
    if test_type == "cronbach_alpha" and hasattr(result, "alpha"):
        guide = guide.replace("当前α=", f"当前α={result.alpha}，")

    # 插入效应量信息
    es_info = ""
    if hasattr(result, "effect_size") and hasattr(result, "effect_size_name"):
        es_info = f" 效应量：{result.effect_size_name}={result.effect_size}"
        if hasattr(result, "effect_size_ci") and result.effect_size_ci:
            es_info += f" {result.effect_size_ci}"
    if es_info and "效应量" not in guide:
        guide += es_info

    # 插入回归诊断信息
    if test_type in ("linear_regression", "multiple_regression", "hierarchical_regression"):
        if hasattr(result, "warning") and result.warning:
            guide += f" {result.warning}"

    return guide
