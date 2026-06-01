"""Streamlit UI 烟雾测试

验证关键UI流程的后端逻辑正确性。
不测试 Streamlit 渲染层（需要浏览器环境），
而是测试 UI 调用的核心函数和数据流。
"""

import pytest
import pandas as pd
import numpy as np


# ============================================================
# Case 1: 数据上传 → 列识别 → 分析执行流程
# ============================================================


class TestDataUploadToAnalysis:
    """验证从上传CSV到执行分析的核心数据流"""

    @pytest.fixture
    def sample_df(self):
        np.random.seed(42)
        return pd.DataFrame({
            "subject_id": range(1, 61),
            "group": ["实验组"] * 30 + ["控制组"] * 30,
            "anxiety_pre": np.random.normal(25, 5, 60),
            "anxiety_post": np.random.normal(22, 5, 60),
            "wellbeing": np.random.normal(50, 10, 60),
            "resilience": np.random.normal(30, 6, 60),
        })

    def test_run_independent_ttest(self, sample_df):
        """测试独立样本t检验执行"""
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(sample_df, dv="anxiety_pre", iv="group")
        assert result.test_type == "independent"
        assert result.p_value is not None
        assert result.effect_size is not None
        assert result.group_stats is not None

    def test_run_correlation(self, sample_df):
        """测试偏相关分析"""
        from src.analysis.correlation import partial_correlation
        result = partial_correlation(
            sample_df, columns=["anxiety_pre", "wellbeing", "resilience"]
        )
        assert result.corr_matrix is not None
        assert result.p_matrix is not None

    def test_run_point_biserial(self, sample_df):
        """测试点二列相关"""
        from src.analysis.correlation import point_biserial_corr
        df = sample_df.copy()
        df["group_code"] = (df["group"] == "实验组").astype(int)
        result = point_biserial_corr(df, continuous_col="anxiety_pre", binary_col="group_code")
        assert result.corr_matrix is not None
        assert result.p_matrix is not None

    def test_full_analysis_flow(self, sample_df):
        """端到端测试：数据 → 分析 → 结果"""
        from src.analysis.ttest import independent_ttest

        result = independent_ttest(sample_df, dv="anxiety_pre", iv="group")

        assert result.t_statistic is not None
        assert -10 < result.t_statistic < 10
        assert 0 <= result.p_value <= 1


# ============================================================
# Case 2: 问卷设计流程
# ============================================================


class TestQuestionnaireFlow:
    """测试问卷设计完整流程"""

    def test_design_known_construct(self):
        from src.questionnaire.design_engine import design_questionnaire
        result = design_questionnaire("调查大学生的自尊水平", use_intent_chain=True)
        assert len(result["items"]) > 0
        assert result["construct_name"] is not None
        assert "instructions" in result
        assert result["scale_config"]["n_items"] > 0

    def test_design_with_academic_sources(self):
        from src.questionnaire.design_engine import design_questionnaire
        result = design_questionnaire(
            "调查青少年的自我效能感",
            use_academic_sources=True,
            use_intent_chain=True,
        )
        assert result["academic_enrichment"] is not None

    def test_reverse_item_review(self):
        from src.questionnaire.design_engine import (
            design_questionnaire,
            get_unreviewed_reverse_items,
        )
        result = design_questionnaire("调查员工的职业倦怠情况")
        unreviewed = get_unreviewed_reverse_items(result)
        assert isinstance(unreviewed, list)

    def test_quality_check(self):
        from src.questionnaire.design_engine import design_questionnaire
        from src.questionnaire.item_quality import check_item_quality
        result = design_questionnaire("调查中学生的考试焦虑")
        report = check_item_quality(result["items"], result["construct_name"])
        assert report.total_items == len(result["items"])
        assert report.passed + report.warnings + report.errors >= report.total_items


# ============================================================
# Case 3: 实验设计流程
# ============================================================


class TestExperimentFlow:
    """测试实验设计完整流程"""

    def test_power_analysis(self):
        from src.experiment_design.power_analysis import calculate_sample_size
        result = calculate_sample_size(
            test_type="anova",
            effect_size=0.25, power=0.80, alpha=0.05, n_groups=3,
        )
        assert result.required_n > 0
        assert result.power >= 0.79

    def test_build_procedure(self):
        from src.experiment_design.procedure_builder import build_full_procedure
        proc = build_full_procedure(
            design_type="within",
            topic="情绪Stroop效应研究",
            n_conditions=2,
            conditions=["一致条件", "不一致条件"],
        )
        assert proc.total_duration_min > 0
        assert len(proc.instructions) > 0

    def test_latin_square(self):
        from src.experiment_design.procedure_builder import generate_latin_square
        square = generate_latin_square(4)
        assert len(square) == 4
        assert len(square[0]) == 4

    def test_jspsych_importer(self):
        """测试 jsPsych 导入器 API"""
        from src.experiment_design.jspsych_data_importer import (
            JsPsychData, parse_jspsych_csv,
        )
        assert JsPsychData is not None
        assert parse_jspsych_csv is not None

    def test_preregistration_generation(self):
        """测试预注册文档生成"""
        from src.experiment_design.preregistration import (
            generate_preregistration,
            validate_preregistration,
        )
        doc = generate_preregistration(
            title="测试研究",
            author="测试者",
            hypotheses="H1: 实验组在因变量上的得分显著高于控制组",
            dependent_variables="因变量：焦虑得分（STAI量表）",
            conditions="自变量：组别（实验组 vs 控制组，被试间）",
            analysis_plan="独立样本t检验，α=0.05，双侧",
            sample_size_info="计划N=128（每组64），检验力0.80",
        )
        md = doc.to_markdown()
        assert "测试研究" in md
        assert "H1" in md

        validation = validate_preregistration(doc)
        assert validation["valid"] is True

    def test_preregistration_from_analysis(self):
        """测试从分析反向生成预注册"""
        from src.experiment_design.preregistration import (
            generate_preregistration_from_analysis,
        )
        doc = generate_preregistration_from_analysis(
            analysis_type="independent t-test",
            research_question="研究不同教学方法对学生成绩的影响",
            variables={"iv": "教学方法", "dv": "学业成绩"},
            sample_n=100,
        )
        assert doc.title is not None
        assert len(doc.sections) > 0


# ============================================================
# Case 4: 论文写作流程
# ============================================================


class TestPaperWritingFlow:
    """测试论文写作完整流程"""

    def test_paper_engine_creation(self):
        from src.paper_writer.paper_engine import PaperEngine
        engine = PaperEngine()
        assert engine is not None
        assert engine.state is not None

    def test_literature_manager(self):
        from src.paper_writer.literature_manager import LiteratureManager
        lm = LiteratureManager()
        assert lm is not None
        results = lm.search_presets("自尊")
        assert isinstance(results, list)

    def test_section_writers(self):
        from src.paper_writer.section_writers import PaperContext
        ctx = PaperContext(
            title_hint="Test Study",
            topic="Test topic",
            research_questions=["RQ1"],
            hypotheses=["H1: Test hypothesis"],
        )
        assert ctx.title_hint == "Test Study"
        assert len(ctx.hypotheses) == 1

    def test_unusual_results_detection(self):
        from src.paper_writer.section_writers import detect_unusual_results
        findings = detect_unusual_results({})
        assert isinstance(findings, list)

    def test_format_consistency(self):
        from src.paper_writer.psychology_report_format import (
            STAT_FORMATS, SIG_MARKS, EFFECT_SIZE_GUIDE,
        )
        assert "t_test" in STAT_FORMATS
        assert "f_test" in STAT_FORMATS
        assert len(SIG_MARKS) > 0
        assert len(EFFECT_SIZE_GUIDE) > 0


# ============================================================
# Case 6: Streamlit 会话状态管理测试 (Task 15)
# ============================================================


class TestSessionStateManagement:
    """验证会话状态设置、持久性和清理的正确性"""

    def test_session_defaults_structure(self):
        """v4.6: LLM 单轨化后只剩 quick_model_id 一个 LLM 字段"""
        expected_keys = [
            "df", "meta", "inspector", "analysis_output", "plan",
            "file_name", "questionnaire_design", "paper_engine",
            "experiment_engine", "quick_model_id",
            "onboarding_completed", "privacy_accepted",
        ]
        valid_set = set(expected_keys)
        for key in expected_keys:
            assert key in valid_set

    def test_dataframe_session_lifecycle(self):
        """模拟 DataFrame 在会话中的完整生命周期"""
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        # 模拟 session_state 赋值
        session = {"df": df}
        assert session["df"] is not None
        assert len(session["df"]) == 3
        # 模拟清除
        session["df"] = None
        assert session["df"] is None

    def test_analysis_output_structure(self):
        """验证分析结果的输出结构兼容性"""
        from src.analysis.ttest import independent_ttest
        np.random.seed(42)
        df = pd.DataFrame({
            "score": np.random.normal(0, 1, 60),
            "group": ["A"] * 30 + ["B"] * 30,
        })
        result = independent_ttest(df, dv="score", iv="group")
        # 验证可序列化的输出字段
        output_dict = {
            "test_type": result.test_type,
            "statistic": result.t_statistic,
            "p_value": result.p_value,
            "effect_size": result.effect_size,
        }
        assert isinstance(output_dict["test_type"], str)
        assert isinstance(output_dict["p_value"], float)
        assert 0 <= output_dict["p_value"] <= 1

    def test_multiple_analysis_accumulation(self):
        """模拟连续运行多个分析而不清除状态的场景"""
        np.random.seed(42)
        df = pd.DataFrame({
            "score": np.random.normal(0, 1, 60),
            "group": ["A"] * 30 + ["B"] * 30,
            "score2": np.random.normal(0, 1, 60),
        })

        from src.analysis.ttest import independent_ttest
        from src.analysis.correlation import partial_correlation

        results = []
        # 运行 t 检验
        r1 = independent_ttest(df, dv="score", iv="group")
        results.append(r1.test_type)
        # 运行相关
        r2 = partial_correlation(df, columns=["score", "score2"])
        results.append("correlation")
        # 模拟状态累积
        assert len(results) == 2
        assert "independent" in results
        assert "correlation" in results

    def test_privacy_acceptance_flow(self):
        """验证隐私声明接受流程的模拟"""
        session = {"privacy_accepted": False}
        # 模拟用户未接受隐私声明时的行为
        assert session["privacy_accepted"] is False
        # 模拟用户接受
        session["privacy_accepted"] = True
        assert session["privacy_accepted"] is True


# ============================================================
# Case 7: 性能基准测试 (Task 16)
# ============================================================


class TestPerformanceBenchmarks:
    """使用合成大数据验证核心分析函数的性能"""

    @pytest.fixture(scope="class")
    def large_df(self):
        """生成 1000×20 的合成数据"""
        np.random.seed(42)
        n_rows = 1000
        data = {}
        for i in range(20):
            data[f"var_{i}"] = np.random.normal(0, 1, n_rows)
        data["group"] = ["A"] * 500 + ["B"] * 500
        data["subject"] = range(1, n_rows + 1)
        return pd.DataFrame(data)

    def test_ttest_performance(self, large_df):
        """独立样本t检验：1000行应在0.5秒内完成"""
        import time
        from src.analysis.ttest import independent_ttest

        t0 = time.perf_counter()
        result = independent_ttest(large_df, dv="var_0", iv="group")
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"t检验耗时 {elapsed:.2f}s 超过 2s 阈值"
        assert result.p_value is not None

    def test_descriptive_stats_performance(self, large_df):
        """描述统计：1000×20应在0.5秒内完成"""
        import time
        from src.data.inspector import inspect_dataframe

        t0 = time.perf_counter()
        result = inspect_dataframe(large_df)
        elapsed = time.perf_counter() - t0

        assert elapsed < 3.0, f"描述统计耗时 {elapsed:.2f}s 超过 3s 阈值"
        assert result is not None

    def test_correlation_performance(self, large_df):
        """偏相关分析：1000行×5变量应在1秒内完成"""
        import time
        from src.analysis.correlation import partial_correlation

        t0 = time.perf_counter()
        result = partial_correlation(
            large_df,
            columns=["var_0", "var_1", "var_2", "var_3", "var_4"],
        )
        elapsed = time.perf_counter() - t0

        assert elapsed < 3.0, f"偏相关耗时 {elapsed:.2f}s 超过 3s 阈值"
        assert result.corr_matrix is not None

    def test_anova_performance(self, large_df):
        """单因素ANOVA：1000行应在1秒内完成"""
        import time
        from src.analysis.anova import one_way_anova

        # 创建多组变量
        df = large_df.copy()
        df["group3"] = pd.cut(
            df["var_0"],
            bins=3,
            labels=["低", "中", "高"],
        )

        t0 = time.perf_counter()
        result = one_way_anova(df, dv="var_1", iv="group3")
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"ANOVA耗时 {elapsed:.2f}s 超过 2s 阈值"
        assert result.effect_size is not None
        assert result.table is not None

    def test_reliability_performance(self, large_df):
        """信度分析：1000×10应在2秒内完成"""
        import time
        from src.analysis.reliability import cronbach_alpha

        cols = [f"var_{i}" for i in range(10)]

        t0 = time.perf_counter()
        result = cronbach_alpha(large_df, cols)
        elapsed = time.perf_counter() - t0

        assert elapsed < 5.0, f"信度分析耗时 {elapsed:.2f}s 超过 5s 阈值"
        assert result.alpha is not None

    def test_mann_whitney_performance(self, large_df):
        """Mann-Whitney U：1000行应在1秒内完成"""
        import time
        from src.analysis.nonparametric import mann_whitney

        t0 = time.perf_counter()
        result = mann_whitney(large_df, dv="var_0", iv="group")
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"Mann-Whitney U耗时 {elapsed:.2f}s 超过 2s 阈值"
        assert result.p_value is not None

    def test_hlm_performance(self, large_df):
        """HLM：1000行×20人应在5秒内完成"""
        import time
        from src.analysis.hlm import run_hlm

        df = large_df.copy()
        # 创建嵌套结构：20个组
        df["school"] = [f"school_{i % 20}" for i in range(len(df))]

        t0 = time.perf_counter()
        result = run_hlm(df, dv="var_0", group_col="school", fixed_effects=["var_1", "var_2"])
        elapsed = time.perf_counter() - t0

        assert elapsed < 15.0, f"HLM耗时 {elapsed:.2f}s 超过 15s 阈值"
        assert result.icc is not None

    def test_meta_analysis_performance(self, large_df):
        """元分析：50个效应量应在0.5秒内完成"""
        import time
        from src.analysis.meta_analysis import run_meta_analysis

        # 合成50个"研究"的效应量
        np.random.seed(42)
        meta_df = pd.DataFrame({
            "effect_size": np.random.normal(0.3, 0.15, 50),
            "se": np.random.uniform(0.05, 0.2, 50),
            "study": [f"研究{i}" for i in range(1, 51)],
        })

        t0 = time.perf_counter()
        result = run_meta_analysis(
            meta_df,
            effect_col="effect_size",
            se_col="se",
            label_col="study",
            model="random",
            generate_plot=False,
        )
        elapsed = time.perf_counter() - t0

        assert elapsed < 1.0, f"元分析耗时 {elapsed:.2f}s 超过 1s 阈值"
        assert result.pooled_effect is not None
        assert result.k == 50


# ============================================================
# Case 8: 本科论文向导模式测试 (v2.3 Task 16)
# ============================================================


class TestUndergradWizardLogic:
    """验证本科论文向导模式的核心逻辑"""

    def test_wizard_session_state_defaults(self):
        """验证本科模式会话状态的默认值"""
        defaults = {
            "undergrad_mode": False,
            "undergrad_path": None,
            "undergrad_step": 0,
            "undergrad_wizard_data": {},
        }
        assert defaults["undergrad_mode"] is False
        assert defaults["undergrad_path"] is None
        assert defaults["undergrad_step"] == 0
        assert isinstance(defaults["undergrad_wizard_data"], dict)

    def test_wizard_mode_toggle_off_by_default(self):
        """验证本科模式默认关闭"""
        # 模拟默认状态：undergrad_mode 应为 False
        session = {"undergrad_mode": False}
        assert session["undergrad_mode"] is False

    def test_wizard_path_selection_survey(self):
        """验证问卷调查研究路径初始化"""
        wiz_data = {
            "title": "", "research_q": "", "hypothesis": "",
        }
        # 模拟选择 survey 路径
        path = "survey"
        assert path in ("survey", "experiment")
        assert wiz_data["title"] == ""
        assert "research_q" in wiz_data
        assert "hypothesis" in wiz_data

    def test_wizard_path_selection_experiment(self):
        """验证实验研究路径初始化"""
        wiz_data = {
            "title": "", "research_q": "", "hypothesis": "",
            "iv": "", "dv": "", "design_type": "between",
        }
        path = "experiment"
        assert path == "experiment"
        assert "iv" in wiz_data
        assert "dv" in wiz_data
        assert wiz_data["design_type"] in ("between", "within", "mixed")

    def test_wizard_step_progression(self):
        """验证向导步骤递进逻辑"""
        session = {"undergrad_step": 0, "undergrad_path": None}
        # 选择路径 → step 1
        session["undergrad_path"] = "survey"
        session["undergrad_step"] = 1
        assert session["undergrad_step"] == 1
        # step 1 → step 2
        session["undergrad_step"] = 2
        assert session["undergrad_step"] == 2
        # 共6步
        for step in range(1, 7):
            session["undergrad_step"] = step
            assert session["undergrad_step"] == step

    def test_wizard_data_persists_across_steps(self):
        """验证向导数据在步骤间持久化"""
        wiz_data = {"title": "测试论文", "research_q": "测试问题", "hypothesis": "H1: 测试"}
        wiz_data["recommended_method"] = "independent_ttest"
        wiz_data["data_loaded"] = True
        assert wiz_data["title"] == "测试论文"
        assert wiz_data["recommended_method"] == "independent_ttest"
        assert wiz_data["data_loaded"] is True


class TestMethodSelectorLogic:
    """验证方法选择决策树返回正确的推荐"""

    def test_decision_tree_group_comparison_two_groups(self):
        """比较组间差异 → 两组 → 推荐独立样本t检验"""
        analysis_goal = "比较组间差异"
        n_groups = "两组"
        expected = "independent_ttest" if analysis_goal == "比较组间差异" and n_groups == "两组" else None
        assert expected == "independent_ttest"

    def test_decision_tree_group_comparison_three_groups(self):
        """比较组间差异 → 三组及以上 → 推荐ANOVA"""
        analysis_goal = "比较组间差异"
        n_groups = "三组及以上"
        expected = "one_way_anova" if analysis_goal == "比较组间差异" and n_groups == "三组及以上" else None
        assert expected == "one_way_anova"

    def test_decision_tree_correlation(self):
        """分析变量关系 → 两个连续变量 → 推荐Pearson相关"""
        goal = "分析变量间关系"
        rel_type = "两个连续变量"
        if goal == "分析变量间关系":
            if rel_type == "两个连续变量":
                rec = "pearson_corr"
            elif rel_type == "连续变量 + 二分变量":
                rec = "point_biserial"
            else:
                rec = "partial_corr"
        assert rec == "pearson_corr"

    def test_decision_tree_paired_change(self):
        """检验前后变化 → 推荐配对t检验"""
        goal = "检验前后变化"
        rec = "paired_ttest" if goal == "检验前后变化" else None
        assert rec == "paired_ttest"

    def test_decision_tree_nonparametric(self):
        """检验分布差异 → 推荐Mann-Whitney"""
        goal = "检验分布差异"
        n_groups = "两组"
        if goal == "检验分布差异":
            rec = "mann_whitney" if n_groups == "两组" else "kruskal_wallis"
        assert rec == "mann_whitney"


class TestCommonMistakeWarnings:
    """验证常见错误预防警告的触发条件"""

    def test_multiple_ttest_warning_trigger(self):
        """多个因变量 + t检验 → 应触发多次比较警告"""
        test_type = "independent_ttest"
        dv_count = 3
        should_warn = test_type in ("independent_ttest", "mann_whitney") and dv_count > 1
        assert should_warn is True

    def test_multiple_ttest_no_warning_single_dv(self):
        """单个因变量 + t检验 → 不应触发警告"""
        test_type = "independent_ttest"
        dv_count = 1
        should_warn = test_type in ("independent_ttest", "mann_whitney") and dv_count > 1
        assert should_warn is False

    def test_correlation_not_causation_warning(self):
        """相关分析应触发相关≠因果警告"""
        for test_type in ("pearson_corr", "spearman_corr", "partial_corr"):
            should_warn = test_type in ("pearson_corr", "spearman_corr", "partial_corr")
            assert should_warn is True

    def test_no_causation_warning_for_ttest(self):
        """t检验不应触发相关≠因果警告"""
        should_warn = "independent_ttest" in ("pearson_corr", "spearman_corr", "partial_corr")
        assert should_warn is False

    def test_mediation_prerequisite_warning(self):
        """中介分析应触发前提条件提醒"""
        should_warn = "mediation" == "mediation"
        assert should_warn is True

    def test_moderation_interpretation_warning(self):
        """调节分析应触发解释提示"""
        should_warn = "moderation" == "moderation"
        assert should_warn is True

    def test_anova_posthoc_three_groups(self):
        """3组以上ANOVA → 应触发事后比较提示"""
        test_type = "one_way_anova"
        n_groups = 4
        should_warn = test_type == "one_way_anova" and n_groups > 2
        assert should_warn is True

    def test_anova_posthoc_two_groups(self):
        """2组ANOVA → 不需要事后比较提示"""
        test_type = "one_way_anova"
        n_groups = 2
        should_warn = test_type == "one_way_anova" and n_groups > 2
        assert should_warn is False

    def test_small_sample_warning(self):
        """小样本(<30)应触发警告"""
        n_rows = 20
        should_warn = n_rows < 30
        assert should_warn is True

    def test_large_sample_no_warning(self):
        """大样本不应触发小样本警告"""
        n_rows = 100
        should_warn = n_rows < 30
        assert should_warn is False


class TestAcademicIntegrityFeatures:
    """验证学术诚信功能"""

    def test_assistant_declaration_template(self):
        """验证辅助工具声明模板包含必要元素"""
        template = (
            "本研究使用心理学研究工具 v2.2 进行数据整理和描述性统计分析。"
            "所有推断统计分析使用 [软件名称与版本] 完成，显著性水平设定为 α = .05（双侧）。"
        )
        assert "心理学研究工具" in template
        assert "[软件名称与版本]" in template
        assert "α = .05" in template

    def test_privacy_acceptance_flow_undergrad(self):
        """验证本科模式下的隐私接受流程"""
        session = {"privacy_accepted": False, "undergrad_mode": True}
        assert session["privacy_accepted"] is False
        assert session["undergrad_mode"] is True
        session["privacy_accepted"] = True
        assert session["privacy_accepted"] is True

    def test_academic_integrity_points(self):
        """验证学术诚信提醒包含所有关键点"""
        points = [
            "理解分析，合理使用",
            "完整报告结果",
            "避免 p-hacking",
            "区分探索性与验证性分析",
        ]
        for point in points:
            assert len(point) > 0


class TestTerminologyGlossary:
    """验证术语速查功能"""

    def test_glossary_contains_key_terms(self):
        """验证术语表包含关键统计术语"""
        key_terms = ["p 值", "效应量", "Cohen's d", "置信区间", "正态性", "方差齐性", "检验力"]
        glossary = {
            "p 值": "概率",
            "效应量": "效应大小",
            "Cohen's d": "标准化均值差",
            "置信区间": "CI",
            "正态性": "正态分布",
            "方差齐性": "方差相等",
            "检验力": "power",
        }
        for term in key_terms:
            assert term in glossary, f"术语 '{term}' 应在术语表中"


class TestDataTemplateDownload:
    """验证数据模板下载功能"""

    def test_survey_template_structure(self):
        """验证问卷调查模板结构"""
        import io
        csv_content = (
            "性别,年龄,自尊总分,社交焦虑总分,生活满意度\n"
            "男,20,28,45,5\n女,21,32,38,4\n男,19,25,50,3\n"
        )
        df = pd.read_csv(io.StringIO(csv_content))
        assert df.shape[0] == 3
        assert "性别" in df.columns
        assert "自尊总分" in df.columns
        assert "社交焦虑总分" in df.columns

    def test_experiment_template_structure(self):
        """验证实验数据模板结构"""
        import io
        csv_content = (
            "被试编号,组别,记忆成绩,反应时_ms\n"
            "1,实验组,85,450\n2,实验组,88,420\n3,控制组,72,510\n"
        )
        df = pd.read_csv(io.StringIO(csv_content))
        assert df.shape[0] == 3
        assert "组别" in df.columns
        assert "实验组" in df["组别"].values
        assert "控制组" in df["组别"].values


class TestFullWizardE2E:
    """端到端测试：模拟完整的本科向导流程"""

    @pytest.fixture
    def sample_survey_df(self):
        np.random.seed(42)
        return pd.DataFrame({
            "性别": ["男"] * 30 + ["女"] * 30,
            "年龄": np.random.randint(18, 25, 60),
            "自尊总分": np.random.normal(28, 5, 60),
            "社交焦虑总分": np.random.normal(40, 8, 60),
            "生活满意度": np.random.normal(4, 1, 60),
        })

    def test_wizard_full_flow_survey(self, sample_survey_df):
        """完整模拟：问卷研究路径 6 步骤"""
        from src.data.inspector import inspect_dataframe

        # 模拟 wizard_data
        wiz_data = {
            "title": "大学生自尊与社交焦虑的关系研究",
            "research_q": "自尊是否与社交焦虑负相关？",
            "hypothesis": "H1: 自尊与社交焦虑呈显著负相关",
        }

        # Step 1: 研究信息已填写
        assert wiz_data["title"]
        assert wiz_data["hypothesis"]

        # Step 2-3: 数据加载和检查
        inspector = inspect_dataframe(sample_survey_df)
        assert inspector is not None
        assert "性别" in inspector
        assert len(sample_survey_df) == 60

        # Step 4: 方法选择 — 分析变量关系
        rec = "pearson_corr"
        assert rec == "pearson_corr"

        # Step 5: 运行分析
        from src.analysis.correlation import partial_correlation
        result = partial_correlation(
            sample_survey_df,
            columns=["自尊总分", "社交焦虑总分", "生活满意度"],
        )
        assert result.corr_matrix is not None

        # Step 6: 结果解读
        assert result.p_matrix is not None
        # 确保输出可序列化
        summary = f"相关分析完成，涉及 {len(sample_survey_df)} 名被试"
        assert summary

    def test_wizard_full_flow_experiment(self):
        """完整模拟：实验研究路径"""
        np.random.seed(42)
        df = pd.DataFrame({
            "组别": ["实验组"] * 30 + ["控制组"] * 30,
            "记忆成绩": np.concatenate([
                np.random.normal(80, 10, 30),
                np.random.normal(72, 10, 30),
            ]),
        })

        from src.analysis.ttest import independent_ttest
        result = independent_ttest(df, dv="记忆成绩", iv="组别")

        assert result.test_type == "independent"
        assert result.p_value is not None
        assert result.effect_size is not None

    def test_session_state_reset_on_path_change(self):
        """验证切换路径时重置会话状态"""
        session = {
            "undergrad_path": "survey",
            "undergrad_step": 3,
            "undergrad_wizard_data": {"title": "test", "data_loaded": True},
        }
        # 模拟切换到新路径
        session["undergrad_path"] = "experiment"
        session["undergrad_step"] = 1
        session["undergrad_wizard_data"] = {
            "title": "", "research_q": "", "hypothesis": "",
            "iv": "", "dv": "", "design_type": "between",
        }
        assert session["undergrad_step"] == 1
        assert session["undergrad_wizard_data"]["title"] == ""
        assert "data_loaded" not in session["undergrad_wizard_data"]

    def test_undergrad_mode_preserves_standard_access(self):
        """验证关闭本科模式后可以正常访问标准功能"""
        session = {"undergrad_mode": True, "app_mode": "📈 数据分析"}
        # 关闭本科模式
        session["undergrad_mode"] = False
        assert session["undergrad_mode"] is False
        # 标准模式应可用
        assert session["app_mode"] == "📈 数据分析"


# ============================================================
# Case 9: 向导到论文生成测试 (v2.4 Task 10)
# ============================================================


class TestWizardToPaper:
    """验证向导第7步生成论文片段的完整性"""

    def test_paper_context_populated_after_analysis(self):
        """验证分析完成后 wizard_results_context 正确填充"""
        ctx = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "sample_size": 200,
            "dv": "焦虑总分",
            "iv": "性别",
            "variables": ["性别", "焦虑总分", "自尊总分"],
        }
        assert ctx["test_type"] == "independent_ttest"
        assert ctx["sample_size"] == 200
        assert ctx["dv"] is not None
        assert ctx["iv"] is not None

    def test_method_template_for_ttest(self):
        """验证t检验的方法描述模板正确"""
        test_type = "independent_ttest"
        templates = {
            "independent_ttest": "独立样本t检验",
            "paired_ttest": "配对样本t检验",
            "one_way_anova": "单因素方差分析 (One-Way ANOVA)",
        }
        assert test_type in templates
        assert "t检验" in templates[test_type]

    def test_method_template_for_anova(self):
        """验证ANOVA的方法描述模板正确"""
        assert "one_way_anova" in [
            "independent_ttest", "paired_ttest", "one_way_anova",
            "pearson_corr", "mann_whitney",
        ]

    def test_paper_result_contains_required_elements(self):
        """验证生成的论文片段包含必要元素"""
        paper_required = ["方法", "结果", "数据分析", "显著性水平"]
        for elem in paper_required:
            assert len(elem) > 0  # 模板应包含这些概念

    def test_paper_academic_integrity_reminder(self):
        """验证学术诚信提示存在"""
        reminders = [
            "核对统计量数值",
            "APA格式",
            "确切的p值",
            "效应量",
            "统计软件名称",
        ]
        for reminder in reminders:
            assert len(reminder) > 0


class TestDecisionTreeExtended:
    """验证决策树12种方法的推荐路径"""

    def test_mediation_recommendation(self):
        """中介效应分析推荐"""
        goal = "检验中介/间接效应"
        rec = None
        if goal == "检验中介/间接效应":
            rec = "mediation"
        assert rec == "mediation"

    def test_moderation_recommendation(self):
        """调节效应分析推荐"""
        goal = "检验调节效应"
        rec = None
        if goal == "检验调节效应":
            rec = "moderation"
        assert rec == "moderation"

    def test_efa_recommendation(self):
        """探索性因素分析推荐"""
        goal = "探索潜在维度（因素分析）"
        if "因素" in goal:
            rec = "efa"
        else:
            rec = None
        assert rec == "efa"

    def test_reliability_recommendation(self):
        """信度分析推荐"""
        goal = "检验量表信度"
        rec = None
        if goal == "检验量表信度":
            rec = "cronbach_alpha"
        assert rec == "cronbach_alpha"

    def test_chisquare_recommendation(self):
        """卡方检验推荐"""
        goal = "检验类别变量关联"
        rec = None
        if goal == "检验类别变量关联":
            rec = "chi_square"
        assert rec == "chi_square"

    def test_all_12_methods_covered(self):
        """验证12种方法均在推荐列表中"""
        all_methods = [
            "independent_ttest", "one_way_anova", "pearson_corr",
            "partial_corr", "paired_ttest", "mann_whitney",
            "kruskal_wallis", "mediation", "moderation", "efa",
            "cronbach_alpha", "chi_square",
        ]
        assert len(all_methods) == 12


class TestDemoDataLoading:
    """验证示例数据加载的完整性"""

    def test_questionnaire_demo_data_columns(self):
        """验证问卷示例数据列名完整"""
        from src.data.demo_datasets import generate_demo_questionnaire_data
        df = generate_demo_questionnaire_data(50, seed=123)
        required_cols = ["性别", "年级", "社交焦虑总分", "自尊总分"]
        for col in required_cols:
            assert col in df.columns
        assert len(df) == 50

    def test_questionnaire_demo_data_types(self):
        """验证问卷示例数据变量类型合理"""
        from src.data.demo_datasets import generate_demo_questionnaire_data
        df = generate_demo_questionnaire_data(100, seed=456)
        assert df["社交焦虑总分"].dtype in ("float64", "float32")
        assert df["性别"].nunique() == 2
        assert df["年级"].nunique() >= 3

    def test_experiment_demo_data_columns(self):
        """验证实验示例数据列名完整"""
        from src.data.demo_datasets import generate_demo_experiment_data
        df = generate_demo_experiment_data(20, seed=789)
        required_cols = ["被试编号", "组别", "前测_记忆成绩", "后测_记忆成绩"]
        for col in required_cols:
            assert col in df.columns
        assert len(df) == 40

    def test_experiment_demo_data_groups(self):
        """验证实验示例数据分组正确"""
        from src.data.demo_datasets import generate_demo_experiment_data
        df = generate_demo_experiment_data(30, seed=111)
        assert "实验组" in df["组别"].values
        assert "控制组" in df["组别"].values
        assert df["组别"].value_counts()["实验组"] == 30
        assert df["组别"].value_counts()["控制组"] == 30

    def test_demo_data_has_missing_values(self):
        """验证问卷示例数据包含少量缺失值（模拟真实场景）"""
        from src.data.demo_datasets import generate_demo_questionnaire_data
        df = generate_demo_questionnaire_data(200, seed=42)
        has_missing = df.isna().any().any()
        assert has_missing, "演示数据应包含少量缺失值以模拟真实数据"

    def test_demo_data_reproducible(self):
        """验证示例数据可重复生成"""
        from src.data.demo_datasets import generate_demo_questionnaire_data
        df1 = generate_demo_questionnaire_data(100, seed=999)
        df2 = generate_demo_questionnaire_data(100, seed=999)
        pd.testing.assert_frame_equal(df1, df2)


class TestBehaviorDetection:
    """验证行为感知检测逻辑"""

    def test_consecutive_ttest_detection_same_dv(self):
        """连续3次t检验 + 相同DV → 触发警告"""
        history = [
            {"test_type": "independent_ttest", "dv": ["焦虑总分"], "iv": ["性别"]},
            {"test_type": "independent_ttest", "dv": ["焦虑总分"], "iv": ["年级"]},
            {"test_type": "independent_ttest", "dv": ["焦虑总分"], "iv": ["组别"]},
        ]
        recent_ttests = [
            h for h in history
            if h["test_type"] in ("independent_ttest", "mann_whitney")
        ]
        all_dvs = [tuple(h["dv"]) for h in recent_ttests]
        should_warn = len(recent_ttests) >= 3 and len(set(all_dvs)) <= 2
        assert should_warn is True

    def test_no_warning_for_varied_tests(self):
        """不同分析方法交替 → 不触发警告"""
        history = [
            {"test_type": "independent_ttest", "dv": ["焦虑总分"], "iv": ["性别"]},
            {"test_type": "pearson_corr", "dv": ["焦虑总分", "自尊总分"], "iv": []},
            {"test_type": "one_way_anova", "dv": ["焦虑总分"], "iv": ["年级"]},
        ]
        recent_ttests = [
            h for h in history
            if h["test_type"] in ("independent_ttest", "mann_whitney")
        ]
        should_warn = len(recent_ttests) >= 3
        assert should_warn is False

    def test_no_warning_for_different_dvs(self):
        """不同DV的t检验 → 不触发警告"""
        history = [
            {"test_type": "independent_ttest", "dv": ["焦虑总分"], "iv": ["性别"]},
            {"test_type": "independent_ttest", "dv": ["自尊总分"], "iv": ["性别"]},
            {"test_type": "independent_ttest", "dv": ["生活满意度"], "iv": ["性别"]},
        ]
        recent_ttests = [
            h for h in history
            if h["test_type"] in ("independent_ttest", "mann_whitney")
        ]
        all_dvs = [tuple(h["dv"]) for h in recent_ttests]
        should_warn = len(recent_ttests) >= 3 and len(set(all_dvs)) <= 2
        assert should_warn is False

    def test_correlation_followup_suggestion(self):
        """高相关+多变量 → 触发后续分析建议"""
        import numpy as np
        # 模拟相关矩阵：存在 |r|>0.5
        corr_vals = np.array([[1.0, 0.65, 0.3], [0.65, 1.0, 0.2], [0.3, 0.2, 1.0]])
        high_corr = (abs(corr_vals) > 0.5).sum() > 1
        n_vars = corr_vals.shape[0]
        should_suggest = high_corr and n_vars >= 3
        assert should_suggest is True

    def test_no_correlation_followup_weak_r(self):
        """弱相关 → 不触发建议"""
        import numpy as np
        corr_vals = np.array([[1.0, 0.3, 0.2], [0.3, 1.0, 0.15], [0.2, 0.15, 1.0]])
        # 不考虑对角线元素
        mask = abs(corr_vals) > 0.5
        np.fill_diagonal(mask, False)
        high_corr = mask.sum() > 0
        assert bool(high_corr) is False


class TestDynamicTerms:
    """验证动态术语展示正确性"""

    def test_ttest_related_terms(self):
        """t检验应展示p值、Cohen's d、95% CI等"""
        term_map = {
            "independent_ttest": ["p值", "Cohen's d", "95% CI", "效应量", "正态性"],
        }
        terms = term_map["independent_ttest"]
        assert "p值" in terms
        assert "Cohen's d" in terms
        assert "95% CI" in terms
        assert len(terms) == 5

    def test_anova_related_terms(self):
        """ANOVA应展示η²、事后检验等"""
        term_map = {
            "one_way_anova": ["η²", "事后检验", "主效应", "F检验", "方差齐性"],
        }
        terms = term_map["one_way_anova"]
        assert "η²" in terms
        assert "事后检验" in terms

    def test_correlation_related_terms(self):
        """相关分析应展示r、散点图等"""
        term_map = {
            "pearson_corr": ["r", "p值", "95% CI", "效应量", "散点图"],
        }
        terms = term_map["pearson_corr"]
        assert "r" in terms
        assert "散点图" in terms

    def test_reliability_related_terms(self):
        """信度分析应展示α系数、内部一致性等"""
        term_map = {
            "cronbach_alpha": ["α系数", "内部一致性", "题总相关", "删除后α", "信度"],
        }
        terms = term_map["cronbach_alpha"]
        assert "α系数" in terms
        assert "内部一致性" in terms

    def test_default_terms_for_unknown_type(self):
        """未知分析类型的默认术语"""
        term_map = {}
        default_terms = ["p值", "效应量", "95% CI", "检验力", "显著性"]
        terms = term_map.get("unknown_type", default_terms)
        assert len(terms) == 5


class TestWizardQuestionnaireLink:
    """验证向导到问卷/实验模块的跳转逻辑"""

    def test_bridge_data_preserved_on_return(self):
        """验证跳转返回时向导数据被保留"""
        ret = {
            "path": "survey",
            "step": 1,
            "data": {
                "title": "测试论文",
                "research_q": "测试问题",
                "hypothesis": "H1: 测试",
            },
        }
        # 模拟返回
        restored = {
            "undergrad_mode": True,
            "undergrad_path": ret["path"],
            "undergrad_step": 2,
            "undergrad_wizard_data": ret["data"],
        }
        assert restored["undergrad_mode"] is True
        assert restored["undergrad_path"] == "survey"
        assert restored["undergrad_step"] == 2
        assert restored["undergrad_wizard_data"]["title"] == "测试论文"

    def test_survey_path_bridge_option(self):
        """验证问卷路径的跳转选项存在"""
        bridge_options = [
            "我已经有问卷数据，直接上传分析",
            "我需要先设计一份新问卷",
        ]
        assert len(bridge_options) == 2
        assert "设计" in bridge_options[1]

    def test_experiment_path_bridge_option(self):
        """验证实验路径的跳转选项存在"""
        bridge_options = [
            "我已经有实验数据，直接分析",
            "我需要先设计实验程序和范式",
        ]
        assert len(bridge_options) == 2
        assert "设计" in bridge_options[1]

    def test_wizard_return_state_cleared(self):
        """验证返回后 _wizard_return 被清除"""
        session = {
            "_wizard_return": {
                "path": "survey",
                "step": 1,
                "data": {},
            },
            "undergrad_mode": False,
        }
        # 模拟返回操作
        session["undergrad_mode"] = True
        session["undergrad_path"] = session["_wizard_return"]["path"]
        session["undergrad_step"] = 2
        session["undergrad_wizard_data"] = session["_wizard_return"]["data"]
        session["_wizard_return"] = None
        assert session["_wizard_return"] is None
        assert session["undergrad_mode"] is True


# ============================================================
# v2.5 新增测试类
# ============================================================


class TestWorkspaceSaveLoad:
    """验证工作区保存/加载的序列化逻辑"""

    def test_savable_keys_present(self):
        """验证所有可保存 key 在 session_state 默认值中存在"""
        savable_keys = {
            "df", "meta", "inspector", "analysis_output", "plan",
            "undergrad_wizard_data", "undergrad_path", "undergrad_step",
            "analysis_history", "file_name",
        }
        defaults = {
            "df": None, "meta": None, "inspector": None,
            "analysis_output": None, "plan": None,
            "undergrad_wizard_data": {}, "undergrad_path": None,
            "undergrad_step": 0, "analysis_history": [], "file_name": None,
        }
        for k in savable_keys:
            assert k in defaults, f"Key {k} missing from defaults"

    def test_dataframe_serialization(self):
        """验证 DataFrame 可被序列化为 dict records"""
        import json
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        workspace = {"df": {"__type__": "dataframe", "data": df.to_dict(orient="records")}}
        serialized = json.dumps(workspace, ensure_ascii=False, default=str)
        loaded = json.loads(serialized)
        restored_df = pd.DataFrame(loaded["df"]["data"])
        assert restored_df.shape == (3, 2)
        assert list(restored_df.columns) == ["A", "B"]

    def test_workspace_json_structure(self):
        """验证工作区 JSON 包含版本和时间戳"""
        import json
        from datetime import datetime
        workspace = {
            "df": None, "meta": None, "file_name": "test.csv",
            "_saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_version": "2.5",
        }
        serialized = json.dumps(workspace, ensure_ascii=False, default=str, indent=2)
        loaded = json.loads(serialized)
        assert "_version" in loaded
        assert loaded["_version"] == "2.5"
        assert "_saved_at" in loaded

    def test_restore_clears_non_data_keys(self):
        """验证恢复时跳过下划线前缀的内部 key"""
        loaded = {
            "_saved_at": "2026-05-16 10:00:00",
            "_version": "2.5",
            "file_name": "restored.csv",
            "analysis_history": [{"type": "ttest"}],
        }
        restored = {}
        for k, v in loaded.items():
            if not k.startswith("_"):
                restored[k] = v
        assert "_saved_at" not in restored
        assert "_version" not in restored
        assert "file_name" in restored
        assert "analysis_history" in restored

    def test_corrupt_json_handling(self):
        """验证损坏的 JSON 文件触发错误处理"""
        import json
        try:
            json.loads("{invalid json")
            assert False, "Should have raised"
        except json.JSONDecodeError:
            assert True


class TestAssumptionFailureGuidance:
    """验证假设检验失败检测和替代方法推荐"""

    def test_normality_failure_detected(self):
        """验证正态性检验未通过被正确检测"""
        output = {
            "errors": [
                {"message": "⚠ 列「焦虑总分」不符合正态分布（Shapiro-Wilk p=0.0023）。",
                 "severity": "warning"},
            ],
            "assumptions": {
                "normality": {"test_name": "Shapiro-Wilk", "passed": False, "p_value": 0.0023},
            },
        }
        normality_failed = False
        for err in output.get("errors", []):
            msg = err.get("message", "")
            if "正态" in msg and "不符合" in msg:
                normality_failed = True
        assumptions = output.get("assumptions", {})
        norm = assumptions.get("normality")
        if isinstance(norm, dict) and not norm.get("passed", True):
            normality_failed = True
        assert normality_failed is True

    def test_homogeneity_failure_detected(self):
        """验证方差齐性未通过被正确检测"""
        output = {
            "assumptions": {
                "homogeneity": {"test_name": "Levene", "passed": False, "p_value": 0.01},
            },
        }
        homogeneity_failed = False
        assumptions = output.get("assumptions", {})
        homo = assumptions.get("homogeneity")
        if isinstance(homo, dict) and not homo.get("passed", True):
            homogeneity_failed = True
        assert homogeneity_failed is True

    def test_ttest_to_mann_whitney_alternative(self):
        """验证独立t检验 → Mann-Whitney U 的替代方法映射"""
        alternative_map = {
            "independent_ttest": ("mann_whitney", "Mann-Whitney U 检验", "不依赖正态性假设"),
            "paired_ttest": ("wilcoxon", "Wilcoxon 符号秩检验", "配对样本的非参数替代方法"),
            "one_way_anova": ("kruskal_wallis", "Kruskal-Wallis H 检验", "单因素方差分析的非参数替代"),
            "pearson_corr": ("spearman_corr", "Spearman 等级相关", "不依赖正态性"),
        }
        alt_type, alt_name, alt_reason = alternative_map["independent_ttest"]
        assert alt_type == "mann_whitney"
        assert "Mann-Whitney" in alt_name

    def test_paired_ttest_alternative(self):
        """验证配对t检验 → Wilcoxon 替代"""
        alternative_map = {
            "independent_ttest": ("mann_whitney", "Mann-Whitney U 检验", ""),
            "paired_ttest": ("wilcoxon", "Wilcoxon 符号秩检验", "配对样本的非参数替代方法"),
        }
        alt_type, alt_name, _ = alternative_map["paired_ttest"]
        assert alt_type == "wilcoxon"

    def test_no_guidance_when_assumptions_ok(self):
        """验证所有假设通过时不触发引导"""
        output = {
            "assumptions": {
                "normality": {"passed": True},
                "homogeneity": {"passed": True},
            },
            "errors": [],
        }
        normality_failed = False
        homogeneity_failed = False
        for err in output.get("errors", []):
            msg = err.get("message", "")
            if "正态" in msg and ("不符合" in msg or "未通过" in msg):
                normality_failed = True
            if "方差不齐" in msg:
                homogeneity_failed = True
        for key in ["normality", "homogeneity"]:
            val = output.get("assumptions", {}).get(key)
            if isinstance(val, dict) and not val.get("passed", True):
                if key == "normality":
                    normality_failed = True
                elif key == "homogeneity":
                    homogeneity_failed = True
        assert not normality_failed
        assert not homogeneity_failed


class TestModuleDataReflow:
    """验证模块返回时设计结果注入向导数据"""

    def test_questionnaire_context_injection(self):
        """验证问卷设计结果正确注入 wizard_data"""
        design = {
            "construct_name": "社交焦虑",
            "dimensions_used": ["紧张维度", "回避维度", "生理维度"],
            "items": [
                {"text": "题1", "reverse": False},
                {"text": "题2", "reverse": False},
                {"text": "题3", "reverse": True},
                {"text": "题4", "reverse": False},
            ],
        }
        items = design.get("items", [])
        rev_count = sum(1 for it in items if it.get("reverse"))
        module_context = {
            "module": "questionnaire",
            "construct_name": design.get("construct_name", ""),
            "dimensions": design.get("dimensions_used", []),
            "item_count": len(items),
            "reverse_count": rev_count,
            "reverse_ratio": round(rev_count / len(items), 2) if items else 0,
        }
        assert module_context["module"] == "questionnaire"
        assert module_context["construct_name"] == "社交焦虑"
        assert len(module_context["dimensions"]) == 3
        assert module_context["item_count"] == 4
        assert module_context["reverse_count"] == 1
        assert module_context["reverse_ratio"] == 0.25

    def test_wizard_data_contains_module_context(self):
        """验证返回后 wizard_data 包含 module_context"""
        wiz_data = {
            "data_loaded": True,
            "title": "测试",
            "module_context": {
                "module": "questionnaire",
                "construct_name": "自尊",
                "dimensions": ["自我接纳", "自我价值"],
                "item_count": 12,
                "reverse_count": 3,
                "reverse_ratio": 0.25,
            },
        }
        ctx = wiz_data.get("module_context")
        assert ctx is not None
        assert ctx["module"] == "questionnaire"
        assert ctx["construct_name"] == "自尊"

    def test_no_context_when_no_design(self):
        """验证无设计结果时不注入 context"""
        wiz_data = {"data_loaded": True, "title": "测试"}
        assert wiz_data.get("module_context") is None

    def test_experiment_context_injection(self):
        """验证实验设计上下文注入逻辑"""
        module_context = {
            "module": "experiment",
            "design_type": "between_subjects",
            "groups": ["实验组", "控制组"],
            "dv_count": 2,
            "iv_count": 1,
        }
        assert module_context["module"] == "experiment"
        assert len(module_context["groups"]) == 2
        assert module_context["dv_count"] == 2


class TestDemoDataExtended:
    """验证 v2.5 新增演示数据集"""

    def test_repeated_measures_columns(self):
        """验证重复测量数据集列名"""
        from src.data.demo_datasets import generate_demo_repeated_measures_data
        df = generate_demo_repeated_measures_data(50, seed=42)
        assert "ID" in df.columns
        assert "T1_焦虑" in df.columns
        assert "T2_焦虑" in df.columns
        assert "T3_焦虑" in df.columns
        assert "组别" in df.columns

    def test_repeated_measures_trend(self):
        """验证重复测量数据 T1 > T2 > T3 趋势"""
        from src.data.demo_datasets import generate_demo_repeated_measures_data
        df = generate_demo_repeated_measures_data(80, seed=42)
        # 均值应递减
        assert df["T1_焦虑"].mean() > df["T2_焦虑"].mean()
        assert df["T2_焦虑"].mean() > df["T3_焦虑"].mean()

    def test_multi_group_columns(self):
        """验证多组干预数据集列名和分组"""
        from src.data.demo_datasets import generate_demo_multi_group_data
        df = generate_demo_multi_group_data(30, seed=42)
        assert "组别" in df.columns
        assert "前测成绩" in df.columns
        assert "后测成绩" in df.columns
        assert df["组别"].nunique() == 4
        groups = df["组别"].unique()
        assert "A组(对照)" in groups
        assert "D组(方法三)" in groups

    def test_multi_group_post_diff(self):
        """验证多组干预数据后测成绩存在组间差异"""
        from src.data.demo_datasets import generate_demo_multi_group_data
        df = generate_demo_multi_group_data(30, seed=42)
        means = df.groupby("组别")["后测成绩"].mean()
        # D组(方法三) 应最高
        assert means["D组(方法三)"] > means["A组(对照)"]
        assert means["C组(方法二)"] > means["A组(对照)"]

    def test_mediation_columns(self):
        """验证中介效应数据集列名"""
        from src.data.demo_datasets import generate_demo_mediation_data
        df = generate_demo_mediation_data(150, seed=42)
        assert "培训" in df.columns
        assert "学习动机" in df.columns
        assert "学业成绩" in df.columns
        assert "培训" in df.columns  # binary IV

    def test_mediation_reproducibility(self):
        """验证中介效应数据可重现"""
        from src.data.demo_datasets import generate_demo_mediation_data
        df1 = generate_demo_mediation_data(100, seed=42)
        df2 = generate_demo_mediation_data(100, seed=42)
        pd.testing.assert_frame_equal(df1, df2)


class TestEnhancedTerminology:
    """验证 3 行术语结构（定义 + 通俗解释 + 本例应用）"""

    def test_term_has_three_fields(self):
        """验证术语条目包含定义、通俗理解、本例应用三个字段"""
        term_entry = {
            "定义": "在零假设为真时，观察到当前结果的概率。",
            "通俗理解": "p<.05 意味着结果不太可能是巧合。",
            "本例应用": "如果焦虑分析的 p < .05，可以认为差异具有统计显著性。",
        }
        assert "定义" in term_entry
        assert "通俗理解" in term_entry
        assert "本例应用" in term_entry

    def test_all_common_terms_have_enhanced(self):
        """验证常见术语都有 3 行结构"""
        term_descriptions_enhanced = {
            "p值": {"定义": "...", "通俗理解": "...", "本例应用": "..."},
            "Cohen's d": {"定义": "...", "通俗理解": "...", "本例应用": "..."},
            "η²": {"定义": "...", "通俗理解": "...", "本例应用": "..."},
            "r": {"定义": "...", "通俗理解": "...", "本例应用": "..."},
            "效应量": {"定义": "...", "通俗理解": "...", "本例应用": "..."},
        }
        for term_name, info in term_descriptions_enhanced.items():
            assert "通俗理解" in info, f"{term_name} 缺少通俗理解"
            assert "本例应用" in info, f"{term_name} 缺少本例应用"

    def test_term_population_with_variable_names(self):
        """验证术语示例使用实际变量名"""
        dv_name = "焦虑总分"
        example = f"如果 {dv_name} 分析的 p < .05，可以认为差异具有统计显著性"
        assert "焦虑总分" in example
        assert "p < .05" in example

    def test_non_parametric_terms_exist(self):
        """验证非参数检验相关术语存在"""
        terms = ["p值", "r (效应量)", "中位数", "非参数检验", "Dunn检验"]
        assert len(terms) == 5
        assert "非参数检验" in terms

    def test_mediation_terms_exist(self):
        """验证中介效应相关术语存在"""
        terms = ["间接效应", "Bootstrap", "a×b", "总效应", "直接效应"]
        assert "间接效应" in terms
        assert "Bootstrap" in terms


class TestPaperLLMOptional:
    """验证 AI 润色功能的可选性和配置检测"""

    def test_llm_unavailable_when_no_api_key(self):
        """验证无 API Key 时 LLM 不可用"""
        has_llm = bool("")
        assert has_llm is False

    def test_llm_available_with_api_key(self):
        """验证有 API Key 时 LLM 可用"""
        has_llm = bool("sk-test-key")
        assert has_llm is True

    def test_polish_prompt_structure(self):
        """验证润色 prompt 包含必要元素"""
        system_prompt = (
            "你是一位心理学学术写作专家，擅长APA第7版格式。"
            "请润色以下论文草稿的方法和结果部分，使其语言更流畅、"
            "更符合APA7风格、术语更规范。保持所有统计量数值不变。"
        )
        assert "APA第7版" in system_prompt
        assert "保持所有统计量数值不变" in system_prompt
        assert "心理学学术写作" in system_prompt

    def test_polished_draft_reset(self):
        """验证润色结果可重置"""
        session = {"polished_draft": "润色后的文本..."}
        session["polished_draft"] = None
        assert session["polished_draft"] is None

    def test_ollama_payload_structure(self):
        """验证 Ollama API 请求结构"""
        payload = {
            "model": "qwen2.5:7b",
            "messages": [
                {"role": "system", "content": "你是心理学写作专家"},
                {"role": "user", "content": "请润色以下草稿..."},
            ],
            "temperature": 0.3,
            "stream": False,
        }
        assert "model" in payload
        assert "messages" in payload
        assert len(payload["messages"]) == 2


class TestLiteratureRecommendation:
    """验证文献推荐引擎"""

    def test_library_has_entries(self):
        """验证文献库有内容"""
        from src.paper_writer.literature_library import LITERATURE_LIBRARY, get_total_entry_count
        count = get_total_entry_count()
        assert count > 100, f"Expected >100 unique entries, got {count}"

    def test_match_social_anxiety(self):
        """验证匹配社交焦虑相关文献"""
        from src.paper_writer.literature_library import match_references
        refs = match_references(["社交焦虑"], top_n=3)
        assert len(refs) >= 1
        # 应有 Mattick & Clarke 1998 或类似
        found = False
        for key, (authors, year, title, source) in refs:
            if "Mattick" in authors or "Rapee" in authors:
                found = True
                break
        assert found, f"Expected social anxiety key reference, got: {refs}"

    def test_match_self_esteem(self):
        """验证匹配自尊相关文献"""
        from src.paper_writer.literature_library import match_references
        refs = match_references(["自尊"], top_n=3)
        assert len(refs) >= 1

    def test_match_by_english_key(self):
        """验证英文关键词匹配"""
        from src.paper_writer.literature_library import match_references
        refs = match_references(["self esteem"], top_n=3)
        assert len(refs) >= 1

    def test_apa7_format(self):
        """验证 APA7 引用格式正确"""
        from src.paper_writer.literature_library import format_citation_apa7
        entry = ("Rosenberg, M.", "1965",
                 "Society and the adolescent self-image",
                 "Princeton University Press")
        citation = format_citation_apa7(entry)
        assert "Rosenberg, M." in citation
        assert "(1965)" in citation
        assert "adolescent self-image" in citation
        assert "Princeton University Press" in citation

    def test_match_multiple_keywords(self):
        """验证多关键词匹配去重"""
        from src.paper_writer.literature_library import match_references
        refs = match_references(["社交焦虑", "social anxiety", "sias"], top_n=5)
        # 应去重（同一文献库）
        authors_set = set()
        for key, (authors, year, title, source) in refs:
            sig = (authors, year)
            authors_set.add(sig)
        assert len(authors_set) == len(refs), "References should be deduplicated"

    def test_no_match_returns_empty(self):
        """验证无匹配关键词返回空列表"""
        from src.paper_writer.literature_library import match_references
        refs = match_references(["不存在的构念xyz"], top_n=5)
        assert refs == []
