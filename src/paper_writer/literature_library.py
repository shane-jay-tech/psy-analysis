"""简化心理学文献推荐库 (~200条)

每条记录包含:
- key: 构念/方法/领域标签 (小写英文/中文)
- citations: [(作者, 年份, 标题, 期刊/来源), ...]

基于 APA7 格式生成引用。关键词匹配时根据用户分析变量自动推荐。
"""

# 文献条目: key -> list of (authors, year, title, source)
LITERATURE_LIBRARY = {}

# ═══════════════════════════════════════════════════
# 社交焦虑 (Social Anxiety)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["社交焦虑"] = [
    ("Mattick, R. P., & Clarke, J. C.", "1998",
     "Development and validation of measures of social phobia scrutiny fear and social interaction anxiety",
     "Behaviour Research and Therapy, 36(4), 455–470"),
    ("Rapee, R. M., & Heimberg, R. G.", "1997",
     "A cognitive-behavioral model of anxiety in social phobia",
     "Behaviour Research and Therapy, 35(8), 741–756"),
    ("Clark, D. M., & Wells, A.", "1995",
     "A cognitive model of social phobia",
     "In R. G. Heimberg et al. (Eds.), Social phobia: Diagnosis, assessment, and treatment (pp. 69–93). Guilford Press"),
    ("Hofmann, S. G.", "2007",
     "Cognitive factors that maintain social anxiety disorder: A comprehensive model and its treatment implications",
     "Cognitive Behaviour Therapy, 36(4), 193–209"),
    ("Leary, M. R.", "1983",
     "A brief version of the Fear of Negative Evaluation Scale",
     "Personality and Social Psychology Bulletin, 9(3), 371–375"),
]

LITERATURE_LIBRARY["social anxiety"] = LITERATURE_LIBRARY["社交焦虑"]
LITERATURE_LIBRARY["社会焦虑"] = LITERATURE_LIBRARY["社交焦虑"]
LITERATURE_LIBRARY["sias"] = LITERATURE_LIBRARY["社交焦虑"]
LITERATURE_LIBRARY["社交回避"] = LITERATURE_LIBRARY["社交焦虑"]

# ═══════════════════════════════════════════════════
# 自尊 (Self-Esteem)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["自尊"] = [
    ("Rosenberg, M.", "1965",
     "Society and the adolescent self-image",
     "Princeton University Press"),
    ("Baumeister, R. F., Campbell, J. D., Krueger, J. I., & Vohs, K. D.", "2003",
     "Does high self-esteem cause better performance, interpersonal success, happiness, or healthier lifestyles?",
     "Psychological Science in the Public Interest, 4(1), 1–44"),
    ("Orth, U., & Robins, R. W.", "2014",
     "The development of self-esteem",
     "Current Directions in Psychological Science, 23(5), 381–387"),
    ("Sowislo, J. F., & Orth, U.", "2013",
     "Does low self-esteem predict depression and anxiety? A meta-analysis of longitudinal studies",
     "Psychological Bulletin, 139(1), 213–240"),
    ("Crocker, J., & Wolfe, C. T.", "2001",
     "Contingencies of self-worth",
     "Psychological Review, 108(3), 593–623"),
]

LITERATURE_LIBRARY["self esteem"] = LITERATURE_LIBRARY["自尊"]
LITERATURE_LIBRARY["self-esteem"] = LITERATURE_LIBRARY["自尊"]
LITERATURE_LIBRARY["ses"] = LITERATURE_LIBRARY["自尊"]
LITERATURE_LIBRARY["自我价值"] = LITERATURE_LIBRARY["自尊"]
LITERATURE_LIBRARY["自我接纳"] = LITERATURE_LIBRARY["自尊"]

# ═══════════════════════════════════════════════════
# 抑郁 (Depression)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["抑郁"] = [
    ("Beck, A. T., Steer, R. A., & Brown, G. K.", "1996",
     "Manual for the Beck Depression Inventory-II",
     "Psychological Corporation"),
    ("Radloff, L. S.", "1977",
     "The CES-D scale: A self-report depression scale for research in the general population",
     "Applied Psychological Measurement, 1(3), 385–401"),
    ("Nolen-Hoeksema, S.", "2000",
     "The role of rumination in depressive disorders and mixed anxiety/depressive symptoms",
     "Journal of Abnormal Psychology, 109(3), 504–511"),
    ("Cuijpers, P., van Straten, A., & Warmerdam, L.", "2007",
     "Behavioral activation treatments of depression: A meta-analysis",
     "Clinical Psychology Review, 27(3), 318–326"),
    ("Kroenke, K., Spitzer, R. L., & Williams, J. B.", "2001",
     "The PHQ-9: Validity of a brief depression severity measure",
     "Journal of General Internal Medicine, 16(9), 606–613"),
]

LITERATURE_LIBRARY["depression"] = LITERATURE_LIBRARY["抑郁"]
LITERATURE_LIBRARY["焦虑"] = LITERATURE_LIBRARY["抑郁"]
LITERATURE_LIBRARY["anxiety"] = LITERATURE_LIBRARY["抑郁"]

# ═══════════════════════════════════════════════════
# 大五人格 (Big Five / FFM)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["大五人格"] = [
    ("Costa, P. T., & McCrae, R. R.", "1992",
     "Revised NEO Personality Inventory (NEO-PI-R) and NEO Five-Factor Inventory (NEO-FFI) professional manual",
     "Psychological Assessment Resources"),
    ("John, O. P., & Srivastava, S.", "1999",
     "The Big Five trait taxonomy: History, measurement, and theoretical perspectives",
     "In L. A. Pervin & O. P. John (Eds.), Handbook of personality (pp. 102–138). Guilford Press"),
    ("McCrae, R. R., & Costa, P. T.", "1997",
     "Personality trait structure as a human universal",
     "American Psychologist, 52(5), 509–516"),
    ("Goldberg, L. R.", "1993",
     "The structure of phenotypic personality traits",
     "American Psychologist, 48(1), 26–34"),
    ("Soto, C. J., & John, O. P.", "2017",
     "The next Big Five Inventory (BFI-2): Developing and assessing a hierarchical model",
     "Journal of Personality and Social Psychology, 113(1), 117–143"),
]

LITERATURE_LIBRARY["big five"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["人格"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["personality"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["神经质"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["外向性"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["尽责性"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["宜人性"] = LITERATURE_LIBRARY["大五人格"]
LITERATURE_LIBRARY["开放性"] = LITERATURE_LIBRARY["大五人格"]

# ═══════════════════════════════════════════════════
# 认知 (Cognition / Memory / Attention)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["认知"] = [
    ("Baddeley, A. D.", "2000",
     "The episodic buffer: A new component of working memory?",
     "Trends in Cognitive Sciences, 4(11), 417–423"),
    ("Kahneman, D.", "2011",
     "Thinking, fast and slow",
     "Farrar, Straus and Giroux"),
    ("Posner, M. I., & Petersen, S. E.", "1990",
     "The attention system of the human brain",
     "Annual Review of Neuroscience, 13, 25–42"),
    ("Miyake, A., & Friedman, N. P.", "2012",
     "The nature and organization of individual differences in executive functions",
     "Current Directions in Psychological Science, 21(1), 8–14"),
    ("Diamond, A.", "2013",
     "Executive functions",
     "Annual Review of Psychology, 64, 135–168"),
]

LITERATURE_LIBRARY["cognition"] = LITERATURE_LIBRARY["认知"]
LITERATURE_LIBRARY["记忆"] = LITERATURE_LIBRARY["认知"]
LITERATURE_LIBRARY["memory"] = LITERATURE_LIBRARY["认知"]
LITERATURE_LIBRARY["工作记忆"] = LITERATURE_LIBRARY["认知"]
LITERATURE_LIBRARY["执行功能"] = LITERATURE_LIBRARY["认知"]
LITERATURE_LIBRARY["注意力"] = LITERATURE_LIBRARY["认知"]
LITERATURE_LIBRARY["注意"] = LITERATURE_LIBRARY["认知"]

# ═══════════════════════════════════════════════════
# 学习动机 (Learning Motivation / Achievement)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["学习动机"] = [
    ("Ryan, R. M., & Deci, E. L.", "2000",
     "Self-determination theory and the facilitation of intrinsic motivation, social development, and well-being",
     "American Psychologist, 55(1), 68–78"),
    ("Pintrich, P. R.", "2003",
     "A motivational science perspective on the role of student motivation in learning and teaching contexts",
     "Journal of Educational Psychology, 95(4), 667–686"),
    ("Dweck, C. S.", "2006",
     "Mindset: The new psychology of success",
     "Random House"),
    ("Bandura, A.", "1997",
     "Self-efficacy: The exercise of control",
     "W. H. Freeman"),
    ("Pekrun, R.", "2006",
     "The control-value theory of achievement emotions: Assumptions, corollaries, and implications",
     "Educational Psychology Review, 18(4), 315–341"),
]

LITERATURE_LIBRARY["motivation"] = LITERATURE_LIBRARY["学习动机"]
LITERATURE_LIBRARY["动机"] = LITERATURE_LIBRARY["学习动机"]
LITERATURE_LIBRARY["学业成绩"] = LITERATURE_LIBRARY["学习动机"]
LITERATURE_LIBRARY["academic"] = LITERATURE_LIBRARY["学习动机"]
LITERATURE_LIBRARY["自我效能"] = LITERATURE_LIBRARY["学习动机"]

# ═══════════════════════════════════════════════════
# 压力 (Stress / Coping)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["压力"] = [
    ("Lazarus, R. S., & Folkman, S.", "1984",
     "Stress, appraisal, and coping",
     "Springer"),
    ("Cohen, S., Kamarck, T., & Mermelstein, R.", "1983",
     "A global measure of perceived stress",
     "Journal of Health and Social Behavior, 24(4), 385–396"),
    ("Selye, H.", "1956",
     "The stress of life",
     "McGraw-Hill"),
    ("Carver, C. S.", "1997",
     "You want to measure coping but your protocol's too long: Consider the Brief COPE",
     "International Journal of Behavioral Medicine, 4(1), 92–100"),
    ("McEwen, B. S.", "1998",
     "Protective and damaging effects of stress mediators",
     "New England Journal of Medicine, 338(3), 171–179"),
]

LITERATURE_LIBRARY["stress"] = LITERATURE_LIBRARY["压力"]
LITERATURE_LIBRARY["应对方式"] = LITERATURE_LIBRARY["压力"]
LITERATURE_LIBRARY["coping"] = LITERATURE_LIBRARY["压力"]

# ═══════════════════════════════════════════════════
# 幸福感 (Well-being / Life Satisfaction)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["幸福感"] = [
    ("Diener, E.", "1984",
     "Subjective well-being",
     "Psychological Bulletin, 95(3), 542–575"),
    ("Ryff, C. D.", "1989",
     "Happiness is everything, or is it? Explorations on the meaning of psychological well-being",
     "Journal of Personality and Social Psychology, 57(6), 1069–1081"),
    ("Seligman, M. E. P.", "2011",
     "Flourish: A visionary new understanding of happiness and well-being",
     "Free Press"),
    ("Keyes, C. L. M.", "2002",
     "The mental health continuum: From languishing to flourishing in life",
     "Journal of Health and Social Behavior, 43(2), 207–222"),
    ("Diener, E., Emmons, R. A., Larsen, R. J., & Griffin, S.", "1985",
     "The Satisfaction With Life Scale",
     "Journal of Personality Assessment, 49(1), 71–75"),
]

LITERATURE_LIBRARY["well being"] = LITERATURE_LIBRARY["幸福感"]
LITERATURE_LIBRARY["well-being"] = LITERATURE_LIBRARY["幸福感"]
LITERATURE_LIBRARY["生活满意度"] = LITERATURE_LIBRARY["幸福感"]
LITERATURE_LIBRARY["主观幸福感"] = LITERATURE_LIBRARY["幸福感"]

# ═══════════════════════════════════════════════════
# 情绪 / 情绪调节 (Emotion / Emotion Regulation)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["情绪"] = [
    ("Gross, J. J.", "1998",
     "The emerging field of emotion regulation: An integrative review",
     "Review of General Psychology, 2(3), 271–299"),
    ("Ekman, P.", "1992",
     "An argument for basic emotions",
     "Cognition and Emotion, 6(3-4), 169–200"),
    ("Gross, J. J., & John, O. P.", "2003",
     "Individual differences in two emotion regulation processes: Implications for affect, relationships, and well-being",
     "Journal of Personality and Social Psychology, 85(2), 348–362"),
    ("Watson, D., Clark, L. A., & Tellegen, A.", "1988",
     "Development and validation of brief measures of positive and negative affect: The PANAS scales",
     "Journal of Personality and Social Psychology, 54(6), 1063–1070"),
    ("Garnefski, N., Kraaij, V., & Spinhoven, P.", "2001",
     "Negative life events, cognitive emotion regulation and emotional problems",
     "Personality and Individual Differences, 30(8), 1311–1327"),
]

LITERATURE_LIBRARY["emotion"] = LITERATURE_LIBRARY["情绪"]
LITERATURE_LIBRARY["情绪调节"] = LITERATURE_LIBRARY["情绪"]
LITERATURE_LIBRARY["情感"] = LITERATURE_LIBRARY["情绪"]

# ═══════════════════════════════════════════════════
# 社会支持 (Social Support)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["社会支持"] = [
    ("Cohen, S., & Wills, T. A.", "1985",
     "Stress, social support, and the buffering hypothesis",
     "Psychological Bulletin, 98(2), 310–357"),
    ("Zimet, G. D., Dahlem, N. W., Zimet, S. G., & Farley, G. K.", "1988",
     "The Multidimensional Scale of Perceived Social Support",
     "Journal of Personality Assessment, 52(1), 30–41"),
    ("Thoits, P. A.", "2011",
     "Mechanisms linking social ties and support to physical and mental health",
     "Journal of Health and Social Behavior, 52(2), 145–161"),
    ("House, J. S.", "1981",
     "Work stress and social support",
     "Addison-Wesley"),
    ("Lakey, B., & Orehek, E.", "2011",
     "Relational regulation theory: A new approach to explain the link between perceived social support and mental health",
     "Psychological Review, 118(3), 482–495"),
]

LITERATURE_LIBRARY["social support"] = LITERATURE_LIBRARY["社会支持"]

# ═══════════════════════════════════════════════════
# 依恋 (Attachment)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["依恋"] = [
    ("Bowlby, J.", "1969",
     "Attachment and loss: Vol. 1. Attachment",
     "Basic Books"),
    ("Ainsworth, M. D. S., Blehar, M. C., Waters, E., & Wall, S.", "1978",
     "Patterns of attachment: A psychological study of the Strange Situation",
     "Lawrence Erlbaum"),
    ("Hazan, C., & Shaver, P.", "1987",
     "Romantic love conceptualized as an attachment process",
     "Journal of Personality and Social Psychology, 52(3), 511–524"),
    ("Bartholomew, K., & Horowitz, L. M.", "1991",
     "Attachment styles among young adults: A test of a four-category model",
     "Journal of Personality and Social Psychology, 61(2), 226–244"),
    ("Fraley, R. C., Waller, N. G., & Brennan, K. A.", "2000",
     "An item response theory analysis of self-report measures of adult attachment",
     "Journal of Personality and Social Psychology, 78(2), 350–365"),
]

LITERATURE_LIBRARY["attachment"] = LITERATURE_LIBRARY["依恋"]

# ═══════════════════════════════════════════════════
# 教养方式 (Parenting Style)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["教养方式"] = [
    ("Baumrind, D.", "1971",
     "Current patterns of parental authority",
     "Developmental Psychology Monographs, 4(1, Pt. 2)"),
    ("Maccoby, E. E., & Martin, J. A.", "1983",
     "Socialization in the context of the family: Parent-child interaction",
     "In P. H. Mussen (Ed.), Handbook of child psychology (pp. 1–101). Wiley"),
    ("Darling, N., & Steinberg, L.", "1993",
     "Parenting style as context: An integrative model",
     "Psychological Bulletin, 113(3), 487–496"),
    ("Lamborn, S. D., Mounts, N. S., Steinberg, L., & Dornbusch, S. M.", "1991",
     "Patterns of competence and adjustment among adolescents from authoritative, authoritarian, indulgent, and neglectful families",
     "Child Development, 62(5), 1049–1065"),
    ("Steinberg, L.", "2001",
     "We know some things: Parent-adolescent relationships in retrospect and prospect",
     "Journal of Research on Adolescence, 11(1), 1–19"),
]

LITERATURE_LIBRARY["parenting"] = LITERATURE_LIBRARY["教养方式"]
LITERATURE_LIBRARY["家庭教育"] = LITERATURE_LIBRARY["教养方式"]

# ═══════════════════════════════════════════════════
# 统计分析 / 方法学 (Statistics / Methodology)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["t检验"] = [
    ("Student (Gosset, W. S.)", "1908",
     "The probable error of a mean",
     "Biometrika, 6(1), 1–25"),
    ("Cohen, J.", "1988",
     "Statistical power analysis for the behavioral sciences (2nd ed.)",
     "Lawrence Erlbaum Associates"),
]

LITERATURE_LIBRARY["方差分析"] = [
    ("Fisher, R. A.", "1925",
     "Statistical methods for research workers",
     "Oliver and Boyd"),
    ("Cohen, J.", "1988",
     "Statistical power analysis for the behavioral sciences (2nd ed.)",
     "Lawrence Erlbaum Associates"),
    ("Maxwell, S. E., & Delaney, H. D.", "2004",
     "Designing experiments and analyzing data: A model comparison perspective (2nd ed.)",
     "Lawrence Erlbaum Associates"),
]

LITERATURE_LIBRARY["anova"] = LITERATURE_LIBRARY["方差分析"]
LITERATURE_LIBRARY["one_way_anova"] = LITERATURE_LIBRARY["方差分析"]

LITERATURE_LIBRARY["相关分析"] = [
    ("Pearson, K.", "1895",
     "Note on regression and inheritance in the case of two parents",
     "Proceedings of the Royal Society of London, 58, 240–242"),
    ("Spearman, C.", "1904",
     "The proof and measurement of association between two things",
     "American Journal of Psychology, 15(1), 72–101"),
    ("Cohen, J.", "1988",
     "Statistical power analysis for the behavioral sciences (2nd ed.)",
     "Lawrence Erlbaum Associates"),
]

LITERATURE_LIBRARY["pearson_corr"] = LITERATURE_LIBRARY["相关分析"]

LITERATURE_LIBRARY["中介效应"] = [
    ("Baron, R. M., & Kenny, D. A.", "1986",
     "The moderator-mediator variable distinction in social psychological research",
     "Journal of Personality and Social Psychology, 51(6), 1173–1182"),
    ("Preacher, K. J., & Hayes, A. F.", "2004",
     "SPSS and SAS procedures for estimating indirect effects in simple mediation models",
     "Behavior Research Methods, Instruments, & Computers, 36(4), 717–731"),
    ("MacKinnon, D. P., Lockwood, C. M., & Williams, J.", "2004",
     "Confidence limits for the indirect effect: Distribution of the product and resampling methods",
     "Multivariate Behavioral Research, 39(1), 99–128"),
    ("温忠麟, 张雷, 侯杰泰, 刘红云", "2004",
     "中介效应检验程序及其应用",
     "心理学报, 36(5), 614–620"),
    ("Zhao, X., Lynch, J. G., & Chen, Q.", "2010",
     "Reconsidering Baron and Kenny: Myths and truths about mediation analysis",
     "Journal of Consumer Research, 37(2), 197–206"),
]

LITERATURE_LIBRARY["mediation"] = LITERATURE_LIBRARY["中介效应"]

LITERATURE_LIBRARY["调节效应"] = [
    ("Aiken, L. S., & West, S. G.", "1991",
     "Multiple regression: Testing and interpreting interactions",
     "Sage Publications"),
    ("Hayes, A. F.", "2017",
     "Introduction to mediation, moderation, and conditional process analysis (2nd ed.)",
     "Guilford Press"),
    ("Jaccard, J., & Turrisi, R.", "2003",
     "Interaction effects in multiple regression (2nd ed.)",
     "Sage Publications"),
    ("Dawson, J. F.", "2014",
     "Moderation in management research: What, why, when, and how",
     "Journal of Business and Psychology, 29(1), 1–19"),
    ("温忠麟, 侯杰泰, 张雷", "2005",
     "调节效应与中介效应的比较和应用",
     "心理学报, 37(2), 268–274"),
]

LITERATURE_LIBRARY["moderation"] = LITERATURE_LIBRARY["调节效应"]

LITERATURE_LIBRARY["因素分析"] = [
    ("Fabrigar, L. R., Wegener, D. T., MacCallum, R. C., & Strahan, E. J.", "1999",
     "Evaluating the use of exploratory factor analysis in psychological research",
     "Psychological Methods, 4(3), 272–299"),
    ("Costello, A. B., & Osborne, J.", "2005",
     "Best practices in exploratory factor analysis: Four recommendations for getting the most from your analysis",
     "Practical Assessment, Research & Evaluation, 10(7), 1–9"),
    ("Hair, J. F., Black, W. C., Babin, B. J., & Anderson, R. E.", "2010",
     "Multivariate data analysis (7th ed.)",
     "Pearson"),
    ("Henson, R. K., & Roberts, J. K.", "2006",
     "Use of exploratory factor analysis in published research: Common errors and some comment on improved practice",
     "Educational and Psychological Measurement, 66(3), 393–416"),
    ("Thompson, B.", "2004",
     "Exploratory and confirmatory factor analysis: Understanding concepts and applications",
     "American Psychological Association"),
]

LITERATURE_LIBRARY["efa"] = LITERATURE_LIBRARY["因素分析"]
LITERATURE_LIBRARY["exploratory factor analysis"] = LITERATURE_LIBRARY["因素分析"]

LITERATURE_LIBRARY["信度分析"] = [
    ("Cronbach, L. J.", "1951",
     "Coefficient alpha and the internal structure of tests",
     "Psychometrika, 16(3), 297–334"),
    ("Nunnally, J. C., & Bernstein, I. H.", "1994",
     "Psychometric theory (3rd ed.)",
     "McGraw-Hill"),
    ("Streiner, D. L.", "2003",
     "Starting at the beginning: An introduction to coefficient alpha and internal consistency",
     "Journal of Personality Assessment, 80(1), 99–103"),
    ("McDonald, R. P.", "1999",
     "Test theory: A unified treatment",
     "Lawrence Erlbaum Associates"),
    ("Raykov, T.", "1997",
     "Estimation of composite reliability for congeneric measures",
     "Applied Psychological Measurement, 21(2), 173–184"),
]

LITERATURE_LIBRARY["reliability"] = LITERATURE_LIBRARY["信度分析"]
LITERATURE_LIBRARY["cronbach_alpha"] = LITERATURE_LIBRARY["信度分析"]
LITERATURE_LIBRARY["内部一致性"] = LITERATURE_LIBRARY["信度分析"]

LITERATURE_LIBRARY["非参数检验"] = [
    ("Mann, H. B., & Whitney, D. R.", "1947",
     "On a test of whether one of two random variables is stochastically larger than the other",
     "Annals of Mathematical Statistics, 18(1), 50–60"),
    ("Wilcoxon, F.", "1945",
     "Individual comparisons by ranking methods",
     "Biometrics Bulletin, 1(6), 80–83"),
    ("Kruskal, W. H., & Wallis, W. A.", "1952",
     "Use of ranks in one-criterion variance analysis",
     "Journal of the American Statistical Association, 47(260), 583–621"),
    ("Siegel, S., & Castellan, N. J.", "1988",
     "Nonparametric statistics for the behavioral sciences (2nd ed.)",
     "McGraw-Hill"),
    ("Tomczak, M., & Tomczak, E.", "2014",
     "The need to report effect size estimates revisited: An overview of some recommended measures of effect size",
     "Trends in Sport Sciences, 1(21), 19–25"),
]

LITERATURE_LIBRARY["mann_whitney"] = LITERATURE_LIBRARY["非参数检验"]
LITERATURE_LIBRARY["kruskal_wallis"] = LITERATURE_LIBRARY["非参数检验"]

LITERATURE_LIBRARY["卡方检验"] = [
    ("Pearson, K.", "1900",
     "On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling",
     "Philosophical Magazine, 50(302), 157–175"),
    ("Cramér, H.", "1946",
     "Mathematical methods of statistics",
     "Princeton University Press"),
    ("Agresti, A.", "2007",
     "An introduction to categorical data analysis (2nd ed.)",
     "Wiley"),
]

LITERATURE_LIBRARY["chi_square"] = LITERATURE_LIBRARY["卡方检验"]

# ═══════════════════════════════════════════════════
# 健康心理学 (Health Psychology)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["睡眠"] = [
    ("Buysse, D. J., Reynolds, C. F., Monk, T. H., Berman, S. R., & Kupfer, D. J.", "1989",
     "The Pittsburgh Sleep Quality Index: A new instrument for psychiatric practice and research",
     "Psychiatry Research, 28(2), 193–213"),
    ("Walker, M. P.", "2017",
     "Why we sleep: Unlocking the power of sleep and dreams",
     "Scribner"),
]

LITERATURE_LIBRARY["sleep"] = LITERATURE_LIBRARY["睡眠"]

# ═══════════════════════════════════════════════════
# 反应时 / 实验范式
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["反应时"] = [
    ("Donders, F. C.", "1869/1969",
     "On the speed of mental processes (W. G. Koster, Trans.)",
     "Acta Psychologica, 30, 412–431"),
    ("Sternberg, S.", "1969",
     "The discovery of processing stages: Extensions of Donders' method",
     "Acta Psychologica, 30, 276–315"),
    ("Ratcliff, R.", "1978",
     "A theory of memory retrieval",
     "Psychological Review, 85(2), 59–108"),
]

LITERATURE_LIBRARY["reaction time"] = LITERATURE_LIBRARY["反应时"]

# ═══════════════════════════════════════════════════
# APA7 / 论文写作规范
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["APA格式"] = [
    ("American Psychological Association", "2020",
     "Publication manual of the American Psychological Association (7th ed.)",
     "American Psychological Association"),
    ("Cumming, G.", "2014",
     "The new statistics: Why and how",
     "Psychological Science, 25(1), 7–29"),
]

# ═══════════════════════════════════════════════════
# 综合 / 方法学补充
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["统计方法"] = [
    ("Field, A.", "2018",
     "Discovering statistics using IBM SPSS Statistics (5th ed.)",
     "Sage Publications"),
    ("Tabachnick, B. G., & Fidell, L. S.", "2019",
     "Using multivariate statistics (7th ed.)",
     "Pearson"),
    ("Howell, D. C.", "2013",
     "Statistical methods for psychology (8th ed.)",
     "Wadsworth Cengage Learning"),
    ("Cumming, G., & Calin-Jageman, R.", "2017",
     "Introduction to the new statistics: Estimation, open science, and beyond",
     "Routledge"),
    ("汪凤炎, 郑红", "2015",
     "心理学研究方法",
     "中国人民大学出版社"),
]

# ═══════════════════════════════════════════════════
# 正向心理学 (Positive Psychology)
# ═══════════════════════════════════════════════════
LITERATURE_LIBRARY["心理韧性"] = [
    ("Masten, A. S.", "2001",
     "Ordinary magic: Resilience processes in development",
     "American Psychologist, 56(3), 227–238"),
    ("Connor, K. M., & Davidson, J. R.", "2003",
     "Development of a new resilience scale: The Connor-Davidson Resilience Scale (CD-RISC)",
     "Depression and Anxiety, 18(2), 76–82"),
    ("Luthar, S. S., Cicchetti, D., & Becker, B.", "2000",
     "The construct of resilience: A critical evaluation and guidelines for future work",
     "Child Development, 71(3), 543–562"),
]

LITERATURE_LIBRARY["resilience"] = LITERATURE_LIBRARY["心理韧性"]
LITERATURE_LIBRARY["韧性"] = LITERATURE_LIBRARY["心理韧性"]

LITERATURE_LIBRARY["正念"] = [
    ("Kabat-Zinn, J.", "2003",
     "Mindfulness-based interventions in context: Past, present, and future",
     "Clinical Psychology: Science and Practice, 10(2), 144–156"),
    ("Baer, R. A., Smith, G. T., Hopkins, J., Krietemeyer, J., & Toney, L.", "2006",
     "Using self-report assessment methods to explore facets of mindfulness",
     "Assessment, 13(1), 27–45"),
    ("Brown, K. W., & Ryan, R. M.", "2003",
     "The benefits of being present: Mindfulness and its role in psychological well-being",
     "Journal of Personality and Social Psychology, 84(4), 822–848"),
]

LITERATURE_LIBRARY["mindfulness"] = LITERATURE_LIBRARY["正念"]


def get_total_entry_count() -> int:
    """返回唯一文献条目的总数"""
    seen = set()
    count = 0
    for key, entries in LITERATURE_LIBRARY.items():
        for entry in entries:
            sig = (entry[0], entry[1])
            if sig not in seen:
                seen.add(sig)
                count += 1
    return count


def match_references(keywords: list, top_n: int = 5) -> list:
    """根据关键词匹配文献推荐

    Args:
        keywords: 关键词列表，如 ["社交焦虑", "自尊", "t检验"]
        top_n: 返回前N条推荐

    Returns:
        [(key, citation_tuple), ...] 格式的推荐列表 (去重)
    """
    matches = {}
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower in LITERATURE_LIBRARY:
            for entry in LITERATURE_LIBRARY[kw_lower]:
                sig = (entry[0], entry[1])
                if sig not in matches:
                    matches[sig] = (kw, entry)

        # 模糊匹配
        for lib_key in LITERATURE_LIBRARY:
            if lib_key in kw_lower or kw_lower in lib_key:
                for entry in LITERATURE_LIBRARY[lib_key]:
                    sig = (entry[0], entry[1])
                    if sig not in matches:
                        matches[sig] = (lib_key, entry)

    # 按匹配度排序（精确匹配优先）
    results = list(matches.values())
    results.sort(key=lambda x: 0 if x[0] in [k.lower().strip() for k in keywords] else 1)
    return results[:top_n]


def format_citation_apa7(entry: tuple) -> str:
    """格式化单条引用为APA7格式"""
    authors, year, title, source = entry
    return f"{authors} ({year}). {title}. *{source}*."
