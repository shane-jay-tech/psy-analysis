"""论文写作系统 — 心理学报格式"""

# 心理学报标准格式模板
# 参考文献: GB/T 7714-2015

PAPER_SECTIONS = [
    "title_abstract",      # 标题 + 摘要 + 关键词
    "introduction",        # 引言
    "methods",             # 方法
    "results",             # 结果
    "discussion",          # 讨论
    "conclusions",         # 结论
    "references",          # 参考文献
    "appendix",            # 附录
]

# 心理学报统计报告规范（中文APA风格）
STAT_FORMATS = {
    "t_test": "t({df}) = {t:.2f}, p = {p:.3f}, Cohen's d = {d:.2f}",
    "f_test": "F({df1}, {df2}) = {F:.2f}, p = {p:.3f}, η² = {eta:.3f}",
    "chi_sq": "χ²({df}) = {chi2:.2f}, p = {p:.3f}, Cramér's V = {v:.3f}",
    "correlation": "r({df}) = {r:.2f}, p = {p:.3f}",
    "regression": "β = {beta:.3f}, t = {t:.2f}, p = {p:.3f}",
    "bootstrap": "B = {B:.3f}, 95% CI = [{ci_low:.3f}, {ci_high:.3f}]",
    "alpha": "Cronbach's α = {alpha:.3f}, 95% CI = [{ci_low:.3f}, {ci_high:.3f}]",
    "kmo": "KMO = {kmo:.3f}, Bartlett χ²({df}) = {chi2:.2f}, p = {p:.3f}",
}

# 显著性标注规则
SIG_MARKS = {
    0.001: "***",
    0.01: "**",
    0.05: "*",
}

# 效应量解读阈值
EFFECT_SIZE_GUIDE = {
    "cohens_d": {"小": 0.20, "中": 0.50, "大": 0.80},
    "eta_sq": {"小": 0.01, "中": 0.06, "大": 0.14},
    "eta_sq_p": {"小": 0.01, "中": 0.06, "大": 0.14},
    "r": {"小": 0.10, "中": 0.30, "大": 0.50},
    "cramers_v": {"小": 0.10, "中": 0.30, "大": 0.50},
    "cohens_f2": {"小": 0.02, "中": 0.15, "大": 0.35},
    "cohens_w": {"小": 0.10, "中": 0.30, "大": 0.50},
    "alpha": {"优秀": 0.90, "良好": 0.80, "可接受": 0.70},
}

# 心理学报写作规范
WRITING_RULES = {
    "title": "不超过25个字，准确概括研究核心变量与关系",
    "abstract": "200-300字，包含目的、方法、结果、结论四要素",
    "keywords": "3-5个关键词，优先使用心理学词典术语",
    "introduction": "问题提出→文献综述→研究缺口→本研究假设（1-2-3-4编号）",
    "methods_participants": "被试人数、性别比例、年龄(M±SD)、招募方式、排除标准",
    "methods_materials": "量表全称、题目数、计分方式、信效度(α)、样题示例",
    "methods_procedure": "施测顺序、时间、环境、伦理审批",
    "results": "先描述统计→再假设检验→效应量+CI→图表引用",
    "discussion": "结果总结→与前人比较→理论贡献→实践意义→局限→未来方向",
    "references": "GB/T 7714-2015格式，中文文献在前、英文在后，按作者姓氏拼音/字母排序",
}

# 中文心理学常用表述
ACADEMIC_PHRASES = {
    "purpose": "本研究旨在探讨",
    "hypothesis": "本研究假设(H{num})：",
    "significant": "结果表明，{effect}具有统计显著性",
    "not_significant": "{effect}未达到统计显著性水平",
    "support": "结果支持了研究假设H{num}",
    "not_support": "结果未能支持研究假设H{num}",
    "compare_previous": "这一发现与{author}({year})的研究结果一致/不一致",
    "contribution": "本研究的理论贡献在于",
    "limitation": "本研究存在以下局限",
    "future": "未来研究可以",
}
