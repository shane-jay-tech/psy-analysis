"""app.py 片 1-3 拆分：入门指导文本 / 课程作业包 / 统计方法说明文本。

由 s922-18（2026-09-22 执行班）自 app.py 原 76-267 行逐字迁移，行为零变更。
唯一适配：_build_homework_package 调用的 build_apa7_report 原先依赖 app.py 模块级
惰性导入（app.py「数据分析」分支内 import）绑定全局名；迁出后该名字解析落在本模块，
故改为函数内 import，保持「重模块不提前导入」的既有意图。
"""
import io
import json
import zipfile
from datetime import datetime
from typing import Dict

import streamlit as st


def _get_onboarding_text(mode: str) -> str:
    """根据当前模式返回对应的入门指导文本"""
    common = (
        '<div class="onboarding-step">'
        '<strong>📂 步骤1:</strong> 上传数据文件（CSV/Excel），或使用内置示例数据。'
        '</div>'
    )

    guides = {
        "📈 数据分析": (
            common +
            '<div class="onboarding-step">'
            '<strong>🔍 步骤2:</strong> 系统自动识别变量类型和角色。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📊 步骤3:</strong> 选择研究问题和分析方法，点击运行。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📋 步骤4:</strong> 查看分析结果表格、效应量、置信区间和解读。'
            '</div>'
        ),
        "📋 问卷设计": (
            '<div class="onboarding-step">'
            '<strong>🎯 步骤1:</strong> 输入您的研究问题或构念名称。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>🧠 步骤2:</strong> 系统从知识库匹配构念或通过LLM分析。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📝 步骤3:</strong> 自动生成题目列表、指导语和计分方式。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>✅ 步骤4:</strong> 使用质量检查、反向题审阅等功能打磨问卷。'
            '</div>'
        ),
        "🧪 实验设计": (
            '<div class="onboarding-step">'
            '<strong>🔬 步骤1:</strong> 选择实验设计类型和范式。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📐 步骤2:</strong> 运行检验力分析确定所需样本量。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>🔄 步骤3:</strong> 生成实验程序、拉丁方平衡、指导语。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📑 步骤4:</strong> 生成预注册文档（AsPredicted格式）。'
            '</div>'
        ),
        "📝 论文写作": (
            '<div class="onboarding-step">'
            '<strong>📖 步骤1:</strong> 选择研究主题和论文框架。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>📚 步骤2:</strong> 系统自动检索相关文献并格式化引用。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>✍️ 步骤3:</strong> 逐章节生成论文初稿（支持LLM润色）。'
            '</div>'
            '<div class="onboarding-step">'
            '<strong>🔍 步骤4:</strong> 自动检测非常规结果、交叉校验引用。'
            '</div>'
        ),
    }

    guide = guides.get(mode, common)
    return (
        f'<div style="font-size:0.85em; line-height:1.6;">'
        f'{guide}'
        f'<div style="margin-top:6px; color:#888;">'
        f'💡 <em>将鼠标悬停在按钮和输入框上可查看提示信息。</em>'
        f'</div>'
        f'</div>'
    )



def _build_homework_package(output, df, tag=""):
    """生成一键作业包 ZIP：数据 + APA7报告 + 方法说明"""
    plan = st.session_state.get("plan")
    test_type = plan.test_type if plan else output.get("test_type", "")
    test_name = output.get("test_name_zh", test_type)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. 数据文件（脱敏）
        from src.utils.guardrails import redact_dataframe_for_storage
        df_saved, redaction_report = redact_dataframe_for_storage(df)
        zf.writestr("data.csv", df_saved.to_csv(index=False, encoding="utf-8-sig"))

        # 2. APA7 报告
        from src.output.formatter import build_apa7_report  # 迁移适配：原由 app.py 模块级惰性导入绑定
        report = build_apa7_report(output)
        method_desc = _generate_method_description(test_type, test_name, output)
        full_md = (
            f"# {test_name} — 课程作业分析报告\n\n"
            f"生成时间：{now}\n\n"
            f"---\n\n"
            f"## 方法说明\n{method_desc}\n\n"
            f"---\n\n"
            f"{report}"
        )
        zf.writestr("report.md", full_md)

        # 3. 分析参数
        params = {
            "test_type": test_type,
            "test_name": test_name,
            "timestamp": now,
            "privacy_redaction": redaction_report,
        }
        if plan:
            params["dependent_vars"] = plan.dependent_vars if hasattr(plan, "dependent_vars") else []
            params["independent_vars"] = plan.independent_vars if hasattr(plan, "independent_vars") else []
        zf.writestr(
            "params.json",
            json.dumps(params, ensure_ascii=False, indent=2, default=str),
        )

        # 4. README
        readme = (
            "心理学课程作业包\n"
            "==================\n\n"
            f"分析方法：{test_name}\n"
            f"生成时间：{now}\n"
            f"标签/课程：{tag or '未标注'}\n\n"
            "文件说明：\n"
            "- data.csv: 分析数据（高敏感列已移除，身份标识列已哈希）\n"
            "- report.md: APA7 格式分析报告 + 方法说明\n"
            "- params.json: 分析参数记录\n\n"
            "学术诚信提醒：请确保你理解所用方法的原理，在论文中正确表述统计结果。\n"
        )
        zf.writestr("README.txt", readme)

    buf.seek(0)
    safe_name = "".join(c for c in test_name if c.isalnum() or c in "._-（）()")[:20]
    st.download_button(
        f"📥 下载作业包 ({safe_name}.zip)",
        data=buf,
        file_name=f"作业包_{safe_name}_{now}.zip",
        mime="application/zip",
        width="stretch",
    )
    st.success("✅ 作业包已生成！包含数据、APA7报告和方法说明。")


def _generate_method_description(test_type: str, test_name: str, output: Dict) -> str:
    """根据检验方法生成简要方法说明"""
    lang = st.session_state.get("output_language", "zh")
    if lang == "en":
        descriptions = {
            "independent_ttest": "This study used an independent-samples t-test to compare the means of two independent groups. "
                                "Assumptions of normality and homogeneity of variance were checked before analysis. "
                                "Cohen's d was reported as the effect size measure.",
            "paired_ttest": "This study used a paired-samples t-test to compare two related measurements within the same subjects. "
                            "The normality assumption of difference scores was verified.",
            "one_way_anova": "This study used a one-way between-subjects ANOVA to compare means across multiple independent groups. "
                             "Levene's test was used to check homogeneity of variance. Partial η² was reported as effect size. "
                             "Post-hoc comparisons used Tukey HSD correction.",
            "pearson_corr": "This study used Pearson correlation to examine linear relationships between continuous variables. "
                           "Normality was checked via Shapiro-Wilk test; Spearman correlation was used as a non-parametric alternative when necessary.",
            "spearman_corr": "This study used Spearman's rank correlation, a non-parametric method, to examine monotonic relationships.",
            "cronbach_alpha": "Cronbach's α was used to assess the internal consistency reliability of the scale. α ≥ 0.70 was considered acceptable.",
            "chi_square_independence": "A chi-square test of independence examined the association between two categorical variables. "
                                       "Cramér's V was reported as the effect size measure.",
            "mann_whitney": "The Mann-Whitney U test, a non-parametric alternative to the independent t-test, was used due to non-normal data distribution.",
            "kruskal_wallis": "The Kruskal-Wallis H test, a non-parametric alternative to one-way ANOVA, was used. "
                              "Dunn's test with Bonferroni correction was used for post-hoc comparisons.",
            "mediation": "Mediation analysis was conducted using the bootstrap method (5000 resamples). "
                        "The indirect effect (a×b) was considered significant if the 95% CI did not contain zero.",
            "moderation": "Moderation analysis examined whether a third variable moderated the relationship between IV and DV. "
                         "Simple slope analysis was conducted at ±1 SD of the moderator.",
            "efa": "Exploratory Factor Analysis (EFA) was conducted using principal axis factoring with varimax rotation. "
                   "KMO and Bartlett's test confirmed data suitability. Factor retention used Kaiser criterion (eigenvalue > 1).",
        }
        return descriptions.get(test_type, f"This study used {test_name} for statistical analysis. Effect sizes and 95% CIs were reported per APA 7th Edition guidelines.")
    else:
        descriptions = {
            "independent_ttest": "本研究使用独立样本 t 检验比较两组独立样本的均值差异。分析前检验了正态性和方差齐性假设。效应量报告 Cohen's d。",
            "paired_ttest": "本研究使用配对样本 t 检验比较同一组被试在两个条件下的测量差异。分析前检验了差值分的正态性假设。",
            "one_way_anova": "本研究使用单因素被试间方差分析比较多组独立样本的均值差异。使用 Levene 检验检查方差齐性。效应量报告偏 η²。事后比较使用 Tukey HSD 校正。",
            "pearson_corr": "本研究使用 Pearson 相关分析两个连续变量间的线性关系。使用 Shapiro-Wilk 检验检查正态性；不满足时使用 Spearman 相关作为非参数替代。",
            "spearman_corr": "本研究使用 Spearman 秩相关（非参数方法）分析变量间的单调关系。",
            "cronbach_alpha": "使用 Cronbach's α 系数评估量表的内部一致性信度。α ≥ 0.70 为可接受水平。",
            "chi_square_independence": "使用卡方独立性检验分析两个类别变量间的关联。效应量报告 Cramér's V。",
            "mann_whitney": "使用 Mann-Whitney U 检验（独立样本 t 检验的非参数替代）比较两组差异，因数据不满足正态性假设。",
            "kruskal_wallis": "使用 Kruskal-Wallis H 检验（单因素方差分析的非参数替代）比较多组差异。事后比较使用 Dunn 检验 + Bonferroni 校正。",
            "mediation": "使用 Bootstrap 法（5000次重抽样）进行中介效应分析。若间接效应 (a×b) 的 95% CI 不包含 0，则认为中介效应显著。",
            "moderation": "使用调节效应分析检验第三个变量是否调节自变量与因变量间关系的强度或方向。在调节变量 ±1 SD 处进行简单斜率分析。",
            "efa": "使用探索性因素分析（主成分法 + 最大方差旋转）探索潜在因素结构。使用 KMO 和 Bartlett 检验确认数据适合性。因子保留使用 Kaiser 准则（特征值 > 1）。",
        }
        return descriptions.get(test_type, f"本研究使用{test_name}进行统计分析。按 APA 第7版要求报告效应量和95%置信区间。")
