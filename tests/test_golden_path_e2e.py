"""v3.8 O1: 黄金路径端到端业务测试。

不依赖 streamlit server —— 直接调真实模块，串完整业务链：
    1. 焦虑量表（信效度路径）：CSV → 描述 → α → CFA 数据 → 答辩 Q&A → Word 导出
    2. 反应时实验（实验路径）：jsPsych JSON → 加载 → 描述 → 配对 t → 答辩 Q&A
    3. 问卷量表（写作 + 反问路径）：CSV → 相关 → reviewer 反问 → AI 痕迹检测 → 个性化答辩 → Word

核心目标：发现单测覆盖不到的集成 bug。
LLM 调用全部 mock，所以可在 CI 离线运行。
"""

import io
import json
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# 通用 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anxiety_scale_data():
    """焦虑量表合成数据：N=120，5 题，单因子结构。"""
    rng = np.random.default_rng(42)
    n = 120
    latent = rng.normal(0, 1, n)
    df = pd.DataFrame({
        f"sa{i}": np.clip(np.round(latent * 0.7 + rng.normal(0, 0.6, n) + 3), 1, 5).astype(int)
        for i in range(1, 6)
    })
    df["gender"] = rng.choice(["男", "女"], n)
    df["age"] = rng.integers(18, 25, n)
    return df


@pytest.fixture
def jspsych_rt_data():
    """jsPsych 反应时实验数据：JSON 数组格式。"""
    rng = np.random.default_rng(7)
    trials = []
    for subj in range(30):
        for cond in ["congruent", "incongruent"]:
            for trial in range(20):
                rt = rng.normal(450 if cond == "congruent" else 520, 60)
                trials.append({
                    "subject": subj,
                    "condition": cond,
                    "trial_index": trial,
                    "rt": int(max(200, rt)),
                    "correct": bool(rng.random() > 0.05),
                })
    return trials


@pytest.fixture
def questionnaire_corr_data():
    """问卷量表合成数据：N=80，3 个量表均值列。"""
    rng = np.random.default_rng(2026)
    n = 80
    anxiety = rng.normal(3.5, 0.8, n)
    return pd.DataFrame({
        "焦虑": anxiety,
        "抑郁": anxiety * 0.6 + rng.normal(0, 0.6, n),  # 与焦虑相关
        "学业满意": -anxiety * 0.4 + rng.normal(4, 0.7, n),  # 与焦虑负相关
        "性别": rng.choice(["男", "女"], n),
    })


# ---------------------------------------------------------------------------
# 路径 1：焦虑量表（信效度路径）
# ---------------------------------------------------------------------------

class TestGoldenPath1_AnxietyScale:
    """学生上传焦虑量表数据 → 跑信度 → 答辩 Q&A → Word 导出。"""

    def test_load_csv_and_describe(self, anxiety_scale_data, tmp_path):
        """步骤 1: 上传 CSV → loader 嗅探编码 → 描述统计。"""
        from src.data.loader import load_data, validate_data
        from src.analysis.descriptive import descriptive_stats

        csv_path = tmp_path / "anxiety.csv"
        anxiety_scale_data.to_csv(csv_path, index=False, encoding="utf-8")

        df, meta = load_data(str(csv_path))
        assert meta["source_type"] == "csv"
        assert meta["row_count"] == 120
        # 数据质量检查不能崩
        issues = validate_data(df)
        assert isinstance(issues, list)

        # 描述统计：5 题
        item_cols = [c for c in df.columns if c.startswith("sa")]
        desc = descriptive_stats(df, item_cols)
        assert desc.shape[0] == 5  # 5 行（每题一行）
        # 实际列名：变量/N/M/SD/SEM/Min/Max/偏度/峰度
        assert "M" in desc.columns and "SD" in desc.columns

    def test_cronbach_alpha_via_runner(self, anxiety_scale_data):
        """步骤 2: AnalysisPlan + run_analysis → Cronbach α。"""
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan

        plan = AnalysisPlan(
            test_type="cronbach_alpha",
            dependent_vars=[f"sa{i}" for i in range(1, 6)],
        )
        out = run_analysis(anxiety_scale_data, plan)
        # α 必须存在且非空
        assert out["test_type"] == "cronbach_alpha"
        assert out["result"] is not None
        # α 通常 > 0.5（合成数据）
        alpha = getattr(out["result"], "alpha", None) or out.get("effect_size")
        assert alpha is not None
        # 不抛异常即视为业务链正常

    def test_defense_qa_template_path(self, anxiety_scale_data):
        """步骤 3: 答辩 Q&A 模板版（无 LLM）。"""
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        from src.paper_writer.defense_qa import generate_defense_qa

        plan = AnalysisPlan(
            test_type="cronbach_alpha",
            dependent_vars=[f"sa{i}" for i in range(1, 6)],
        )
        out = run_analysis(anxiety_scale_data, plan)
        items = generate_defense_qa(plan, out, ctx={
            "test_type": "cronbach_alpha",
            "construct_name": "社交焦虑",
            "sample_size": 120,
        })
        assert len(items) > 0
        # 至少有「method」类
        cats = {it.category for it in items}
        assert "method" in cats

    def test_export_to_word(self, anxiety_scale_data):
        """步骤 4: build_thesis_docx → bytes（不写盘）。"""
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        from src.output.docx_exporter import build_thesis_docx, ThesisMeta

        plan = AnalysisPlan(
            test_type="descriptive",
            dependent_vars=[f"sa{i}" for i in range(1, 6)],
        )
        out = run_analysis(anxiety_scale_data, plan)
        meta = ThesisMeta(title="社交焦虑量表信度研究", author="测试")
        doc_bytes = build_thesis_docx(
            meta=meta,
            method_md="## 方法\n\n本研究...",
            result_md="## 结果\n\n描述统计如表 1。",
            descriptive_table=out.get("descriptive"),
        )
        assert isinstance(doc_bytes, bytes)
        assert len(doc_bytes) > 1000  # docx 最小也得有几 KB

    def test_full_chain_no_exceptions(self, anxiety_scale_data, tmp_path):
        """完整链：load → describe → α → defense_qa → docx，全程不抛。"""
        from src.data.loader import load_data
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        from src.paper_writer.defense_qa import generate_defense_qa, render_qa_as_markdown
        from src.output.docx_exporter import build_thesis_docx, ThesisMeta

        csv_path = tmp_path / "data.csv"
        anxiety_scale_data.to_csv(csv_path, index=False)
        df, _ = load_data(str(csv_path))

        plan = AnalysisPlan(
            test_type="cronbach_alpha",
            dependent_vars=[f"sa{i}" for i in range(1, 6)],
        )
        out = run_analysis(df, plan)
        items = generate_defense_qa(plan, out, ctx={
            "test_type": "cronbach_alpha", "sample_size": 120,
        })
        qa_md = render_qa_as_markdown(items)
        doc_bytes = build_thesis_docx(
            meta=ThesisMeta(title="测试", author="A"),
            method_md="## 方法",
            result_md="## 结果",
            defense_qa_md=qa_md,
        )
        assert len(doc_bytes) > 1000


# ---------------------------------------------------------------------------
# 路径 2：反应时实验（实验路径）
# ---------------------------------------------------------------------------

class TestGoldenPath2_RTExperiment:
    """学生上传 jsPsych 反应时实验 → 配对 t 检验 → 答辩。"""

    def test_load_jspsych_json(self, jspsych_rt_data, tmp_path):
        """步骤 1: jsPsych JSON 数组加载，列名归一化。"""
        from src.data.loader import load_data
        json_path = tmp_path / "rt_data.json"
        json_path.write_text(json.dumps(jspsych_rt_data, ensure_ascii=False),
                              encoding="utf-8")
        df, meta = load_data(str(json_path))
        assert meta["source_type"] == "jspsych_json"
        assert meta["format"] == "json_array"
        assert meta["row_count"] > 0
        # rt 列保留（jsPsych loader 会归一化为「反应时_ms」）
        assert "rt" in df.columns or any("反应时" in c for c in df.columns)

    def test_aggregate_and_paired_ttest(self, jspsych_rt_data):
        """步骤 2: 聚合到被试级 → 配对 t（左右两个条件平均 RT）。"""
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan

        df_long = pd.DataFrame(jspsych_rt_data)
        # 长表→宽表（被试 × 条件）
        wide = df_long.groupby(["subject", "condition"])["rt"].mean().unstack()
        wide = wide.reset_index()
        # 期望两列：congruent / incongruent
        assert "congruent" in wide.columns
        assert "incongruent" in wide.columns

        plan = AnalysisPlan(
            test_type="paired_ttest",
            dependent_vars=["congruent", "incongruent"],
        )
        out = run_analysis(wide, plan)
        assert out["test_type"] == "paired_ttest"
        assert out["result"] is not None

    def test_defense_qa_for_paired_ttest(self, jspsych_rt_data):
        """步骤 3: 答辩题对 paired_ttest 不应崩。"""
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        from src.paper_writer.defense_qa import generate_defense_qa

        df_long = pd.DataFrame(jspsych_rt_data)
        wide = df_long.groupby(["subject", "condition"])["rt"].mean().unstack().reset_index()

        plan = AnalysisPlan(
            test_type="paired_ttest",
            dependent_vars=["congruent", "incongruent"],
        )
        out = run_analysis(wide, plan)
        items = generate_defense_qa(plan, out, ctx={
            "test_type": "paired_ttest", "sample_size": 30,
        })
        assert len(items) > 0


# ---------------------------------------------------------------------------
# 路径 3：问卷量表（写作 + 反问路径，含 N8/O3 集成）
# ---------------------------------------------------------------------------

class TestGoldenPath3_QuestionnaireWritingAndReview:
    """学生用问卷量表数据 → 相关分析 → AI 反问 → AI 痕迹检测 → 个性化答辩。

    覆盖 v3.8 的三个新功能（N8 fallback / O3 trace / O2 paper-aware QA）。
    """

    def test_correlation_analysis(self, questionnaire_corr_data):
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan

        plan = AnalysisPlan(
            test_type="pearson_corr",
            dependent_vars=["焦虑", "抑郁", "学业满意"],
        )
        out = run_analysis(questionnaire_corr_data, plan)
        assert out["result"] is not None

    def test_n8_fallback_with_two_models(self):
        """N8: 主模型挂掉 → 备用模型回包成功。"""
        from src.llm_gateway import llm_chat_with_fallback
        from src.llm_gateway.gateway import register_llm_backend

        def _bad(messages, model="", **kwargs):
            raise RuntimeError("primary timeout")

        def _good(messages, model="", **kwargs):
            return "secondary response"

        register_llm_backend("e2e_bad", _bad)
        register_llm_backend("e2e_good", _good)

        cfg = {"provider": "openai", "base_url": "x", "api_key": "k",
               "model": "x", "timeout": 30}
        result = llm_chat_with_fallback(
            [{"role": "user", "content": "hi"}],
            candidates=[
                {"model": "primary", "llm_config": cfg, "backend": "e2e_bad"},
                {"model": "secondary", "llm_config": cfg, "backend": "e2e_good"},
            ],
        )
        assert result.response.ok
        assert result.winner_model == "secondary"

    def test_o3_ai_trace_on_typical_paper_section(self):
        """O3: 检测一段典型 AI 生成的论文片段。"""
        from src.output.ai_trace_detector import detect_ai_traces

        ai_paragraph = (
            "首先，本研究关注了社交焦虑这一重要议题。"
            "其次，本文采用问卷调查法收集了 120 份有效数据。"
            "综上所述，本研究具有重要理论意义，"
            "未来研究可以进一步从神经机制层面深入探讨。"
        )
        report = detect_ai_traces(ai_paragraph)
        assert report.has_high_severity
        assert report.score >= 30  # 至少中度

    def test_o2_paper_aware_qa_with_mock_llm(self, questionnaire_corr_data):
        """O2: 个性化答辩题（mock LLM）。"""
        from src.paper_writer.defense_qa import generate_paper_aware_qa

        paper = (
            "本研究招募 N=80 名大学生，测量焦虑、抑郁、学业满意度。"
            "采用 Pearson 相关分析变量间关系。"
            "结果显示焦虑与抑郁正相关 (r=.62, p<.001)，"
            "焦虑与学业满意度负相关 (r=-.41, p<.001)。"
        )
        reviewer_history = [
            {"question": "为什么不控制性别？", "answer": "样本量不够亚组分析"},
        ]
        funnel = {
            "research_question": "焦虑如何影响学业",
            "variables": "焦虑/抑郁/学业满意",
            "sample_size": "N=80",
        }

        def _mock(messages, **kwargs):
            resp = MagicMock()
            resp.content = json.dumps([
                {
                    "question": "你的样本 N=80 在 Pearson 相关上 power 够吗？",
                    "answer_outline": "1. r=.62 大效应\n2. N=80 足够检出 r=.30+",
                    "category": "data",
                    "difficulty": "必问",
                    "rationale": "你写到 N=80 但未做 power 分析",
                },
                {
                    "question": "焦虑-抑郁相关 .62 是否过高，可能是同测量法偏差？",
                    "answer_outline": "1. 同方法偏差可能存在\n2. 未来用 EMA 多源验证",
                    "category": "infer",
                    "difficulty": "刁钻",
                    "rationale": "两个量表都是自评，需 CMV 检验",
                },
            ], ensure_ascii=False)
            return resp

        result = generate_paper_aware_qa(
            paper_text=paper,
            reviewer_history=reviewer_history,
            funnel_state=funnel,
            llm_chat_fn=_mock,
            max_items=5,
        )
        assert not result.fallback_to_template
        assert len(result.items) == 2
        assert result.used_paper and result.used_reviewer_history and result.used_funnel
        # 必问优先
        assert result.items[0].difficulty == "必问"

    def test_full_chain_corr_to_export(self, questionnaire_corr_data):
        """完整链：相关 → 写作（mock）→ 反问（mock）→ AI 痕迹检测 → 答辩 → 导出。"""
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        from src.output.ai_trace_detector import detect_ai_traces, render_report_markdown
        from src.paper_writer.defense_qa import generate_defense_qa, render_qa_as_markdown
        from src.output.docx_exporter import build_thesis_docx, ThesisMeta

        # 1) 相关分析
        plan = AnalysisPlan(
            test_type="pearson_corr",
            dependent_vars=["焦虑", "抑郁", "学业满意"],
        )
        out = run_analysis(questionnaire_corr_data, plan)

        # 2) 写作部分（人工）
        result_md = (
            "## 结果\n\n"
            "我们用 Pearson 相关分析三个量表得分。"
            "焦虑与抑郁显著正相关 (r=.62, p<.001)；"
            "焦虑与学业满意度显著负相关 (r=-.41, p<.001)。"
        )

        # 3) AI 痕迹检测
        report = detect_ai_traces(result_md)
        # 这段是手写自然中文，应该是低分
        assert report.score < 30

        # 4) 答辩 Q&A
        items = generate_defense_qa(plan, out, ctx={
            "test_type": "pearson_corr", "sample_size": 80,
        })
        qa_md = render_qa_as_markdown(items)

        # 5) Word 导出
        meta = ThesisMeta(title="问卷相关研究", author="测试")
        doc_bytes = build_thesis_docx(
            meta=meta,
            method_md="## 方法\n\n80 名大学生填答三套量表。",
            result_md=result_md,
            defense_qa_md=qa_md,
        )
        assert len(doc_bytes) > 2000


# ---------------------------------------------------------------------------
# 跨路径：v3.8 集成对照
# ---------------------------------------------------------------------------

class TestV38Integration:
    """v3.8 三大新功能的联合：fallback+trace+paper_aware 串起来跑一次。"""

    def test_fallback_then_trace_then_qa(self, questionnaire_corr_data):
        from src.llm_gateway import llm_chat_with_fallback
        from src.llm_gateway.gateway import register_llm_backend
        from src.output.ai_trace_detector import detect_ai_traces, score_ai_likelihood
        from src.paper_writer.defense_qa import generate_paper_aware_qa

        # —— Step 1: 用 fallback 拿到一段「论文初稿」（mock） ——
        ai_draft = (
            "首先，本研究关注社交焦虑。"
            "其次，本文采用相关分析法。"
            "综上所述，本研究具有重要理论意义。"
        )

        def _slow(messages, model="", **kwargs):
            import time as _t
            _t.sleep(0.1)
            return ai_draft

        def _fast(messages, model="", **kwargs):
            return ai_draft

        register_llm_backend("v38_slow", _slow)
        register_llm_backend("v38_fast", _fast)

        cfg = {"provider": "openai", "base_url": "x", "api_key": "k",
               "model": "x", "timeout": 30}
        fb = llm_chat_with_fallback(
            [{"role": "user", "content": "写结论"}],
            candidates=[
                {"model": "fast", "llm_config": cfg, "backend": "v38_fast"},
                {"model": "slow", "llm_config": cfg, "backend": "v38_slow"},
            ],
        )
        assert fb.response.ok
        draft = fb.response.content

        # —— Step 2: O3 检测 AI 痕迹 ——
        score = score_ai_likelihood(draft)
        report = detect_ai_traces(draft)
        assert score >= 30  # 该段 AI 痕迹明显
        assert report.has_high_severity

        # —— Step 3: O2 个性化答辩题 ——
        def _qa_mock(messages, **kwargs):
            r = MagicMock()
            r.content = json.dumps([
                {"question": "你的相关分析 r=.62 是同方法偏差吗？",
                 "answer_outline": "1. 检查 CMV\n2. Harman 单因素检验",
                 "category": "infer", "difficulty": "刁钻"}
            ], ensure_ascii=False)
            return r

        qa = generate_paper_aware_qa(
            paper_text=draft,
            llm_chat_fn=_qa_mock,
            max_items=3,
        )
        assert len(qa.items) >= 1
        assert qa.used_paper
