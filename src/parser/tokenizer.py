"""jieba 分词 + 心理学词典 + 停用词过滤"""

import jieba
from .keyword_dict import STOPWORDS

# 添加心理学领域自定义词典
PSYCH_TERMS = [
    "独立样本t检验", "配对样本t检验", "单样本t检验",
    "方差分析", "单因素方差分析", "双因素方差分析",
    "重复测量方差分析", "卡方检验", "卡方",
    "克隆巴赫", "克隆巴赫系数", "α系数",
    "皮尔逊", "斯皮尔曼", "曼惠特尼",
    "威尔科克森", "克鲁斯卡尔",
    "t检验", "ANOVA", "MANOVA",
    "描述性统计", "描述统计", "推断统计",
    "自变量", "因变量", "控制变量", "协变量",
    "被试间", "被试内", "混合设计",
    "正态性", "方差齐性", "球形检验",
    "效应量", "Cohen's d", "η²", "Cramer's V",
    "置信区间", "显著性", "p值",
    "量表", "问卷", "常模", "信度", "效度",
    "项目分析", "因素分析", "探索性因素分析",
    "多重比较", "事后检验", "Tukey", "Bonferroni",
    "回归分析", "线性回归", "多元回归",
    "交互作用", "主效应", "简单效应",
    "被试", "样本", "总体",
    "正态分布", "非参数",
]

for term in PSYCH_TERMS:
    jieba.add_word(term)


def tokenize(text: str) -> list:
    """
    对中文分析需求文本进行分词，返回有意义的词条列表。
    """
    # jieba 精确模式分词
    words = jieba.lcut(text)

    # 过滤：去掉停用词、纯标点、纯数字、纯空格、单字
    result = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if w in STOPWORDS:
            continue
        if len(w) <= 1 and not w.isascii():
            continue
        if w.isdigit():
            continue
        # 纯标点
        if all(c in "，。！？、；：""''（）【】《》…—·,.;:!?()[]{}\"' " for c in w):
            continue
        result.append(w)

    return result


def tokenize_keep_numbers(text: str) -> list:
    """分词但保留数字（用于提取检验值等）"""
    words = jieba.lcut(text)
    result = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if w in STOPWORDS:
            continue
        if len(w) <= 1 and not w.isascii():
            continue
        if all(c in "，。！？、；：""''（）【】《》…—·,.;:!?()[]{}\"' " for c in w):
            continue
        result.append(w)
    return result
