"""端到端黄金路径服务集成测试。

验证一个标准心理学问卷研究项目能完整跑通：
数据 → 分析 → 结果卡 → 文献审核 → 论文 Bundle → 差异对比 → 健康检查 → 导出。

注意：此测试不启动 Streamlit，纯服务层调用。
"""

import sqlite3
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.result_card import AnalysisResultCard, build_card_from_output
from src.literature_feed.review_queue_ui import (
    ReviewAction,
    build_queue_items,
    compute_queue_summary,
    filter_queue,
)
from src.literature_feed.review_service import review_candidate, list_review_events
from src.paper_writer.adapters import bundle_from_wizard_template
from src.paper_writer.bundle_export import (
    bundle_to_markdown,
    bundle_to_export_result,
    validate_bundle_for_export,
)
from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.section_diff import compute_section_diff
from src.utils.project_health import (
    run_health_checks,
    has_blocking_issues,
    issues_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_questionnaire_data():
    """标准心理学问卷数据（模拟 Likert 5 点量表）。"""
    np.random.seed(42)
    n = 60
    return pd.DataFrame({
        "id": range(1, n + 1),
        "gender": np.random.choice(["男", "女"], n),
        "age": np.random.randint(18, 25, n),
        "anxiety_1": np.random.randint(1, 6, n),
        "anxiety_2": np.random.randint(1, 6, n),
        "anxiety_3": np.random.randint(1, 6, n),
        "depression_1": np.random.randint(1, 6, n),
        "depression_2": np.random.randint(1, 6, n),
        "depression_3": np.random.randint(1, 6, n),
        "self_esteem": np.random.randint(1, 6, n),
    })


@pytest.fixture
def mock_store(tmp_path):
    """内存 SQLite store mock，用于文献审核测试。"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE llm_candidates (
            candidate_id INTEGER PRIMARY KEY,
            title TEXT, authors TEXT, year INTEGER,
            source TEXT, abstract TEXT, status TEXT DEFAULT 'pending',
            reviewer TEXT, reviewed_at TEXT,
            rejection_reason TEXT, target_kb_id TEXT,
            relevance_score REAL DEFAULT 0.0
        )
    """)
    conn.execute("""
        CREATE TABLE candidate_review_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER, old_status TEXT, new_status TEXT,
            reviewer TEXT, reason TEXT, note TEXT,
            target_kb_id TEXT, created_at TEXT
        )
    """)
    # 插入测试文献
    candidates = [
        (1, "焦虑与自尊的关系研究", "张三,李四", 2023, "cnki", "本研究探讨...", "pending", 0.9),
        (2, "大学生抑郁现状调查", "王五", 2024, "wos", "采用问卷法...", "pending", 0.85),
        (3, "心理韧性综述", "赵六", 2022, "scopus", "回顾近十年...", "pending", 0.7),
        (4, "无关论文", "other", 2020, "cnki", "这是一篇无关文献", "pending", 0.2),
    ]
    conn.executemany(
        "INSERT INTO llm_candidates VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,?)",
        candidates,
    )
    conn.commit()

    class MockStore:
        def __init__(self, conn):
            self.connection = conn
            self._conn = conn

        def transaction(self):
            return _NullContext()

    class _NullContext:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    return MockStore(conn)


# ---------------------------------------------------------------------------
# 黄金路径测试
# ---------------------------------------------------------------------------


class TestGoldenResearchFlow:
    """完整研究项目端到端服务层测试。"""

    def test_step1_data_loading(self, sample_questionnaire_data):
        """步骤 1：加载问卷数据。"""
        df = sample_questionnaire_data
        assert len(df) == 60
        assert "anxiety_1" in df.columns
        assert "depression_1" in df.columns

    def test_step2_variable_setup(self, sample_questionnaire_data):
        """步骤 2：设置变量类型。"""
        df = sample_questionnaire_data
        variable_roles = {
            "anxiety_1": "continuous",
            "anxiety_2": "continuous",
            "anxiety_3": "continuous",
            "depression_1": "continuous",
            "self_esteem": "continuous",
            "gender": "categorical",
            "age": "continuous",
        }
        for var, role in variable_roles.items():
            assert var in df.columns

    def test_step3_descriptive_statistics(self, sample_questionnaire_data):
        """步骤 3：运行描述统计并生成结果卡。"""
        df = sample_questionnaire_data
        # 模拟 run_analysis() 输出格式（用 test_type 字段）
        output = {
            "test_type": "descriptive",
            "test_name_zh": "描述统计",
            "variables": {"target": "anxiety_1"},
            "results": {
                "mean": float(df["anxiety_1"].mean()),
                "std": float(df["anxiety_1"].std()),
                "n": len(df),
                "min": float(df["anxiety_1"].min()),
                "max": float(df["anxiety_1"].max()),
                "skewness": float(df["anxiety_1"].skew()),
                "kurtosis": float(df["anxiety_1"].kurtosis()),
            },
        }
        card = build_card_from_output(output)
        assert card is not None
        assert card.method_id == "descriptive"
        assert card.apa_text  # APA 文本非空
        assert card.plain_language_summary

    def test_step4_correlation(self, sample_questionnaire_data):
        """步骤 4：运行 Pearson 相关并生成结果卡。"""
        df = sample_questionnaire_data
        from scipy import stats
        r, p = stats.pearsonr(df["anxiety_1"], df["self_esteem"])

        class CorrResult:
            def __init__(self, r, p, n):
                self.r = r
                self.p_value = p
                self.n = n

        output = {
            "test_type": "pearson_correlation",
            "test_name_zh": "Pearson 相关",
            "result": CorrResult(float(r), float(p), len(df)),
        }
        card = build_card_from_output(output)
        assert card is not None
        assert "r" in card.apa_text.lower() or "r =" in card.apa_text

    def test_step5_result_card_markdown(self, sample_questionnaire_data):
        """步骤 5：结果卡导出 Markdown。"""
        output = {
            "test_type": "descriptive",
            "test_name_zh": "描述统计",
            "variables": {"target": "anxiety_1"},
            "results": {"mean": 3.0, "std": 1.1, "n": 60, "min": 1, "max": 5,
                        "skewness": 0.1, "kurtosis": -0.5},
        }
        card = build_card_from_output(output)
        md = card.to_markdown()
        assert "描述统计" in md
        assert "APA" in md or "apa" in md.lower() or "M =" in md

    def test_step6_literature_review(self, mock_store):
        """步骤 6：文献审核 — 纳入、排除、查看历史。"""
        rows = mock_store.connection.execute("SELECT * FROM llm_candidates").fetchall()
        items = build_queue_items([dict(r) for r in rows])
        assert len(items) == 4

        summary = compute_queue_summary(items)
        assert summary.pending == 4

        # 纳入 2 篇
        review_candidate(mock_store, 1, "approved", "user")
        review_candidate(mock_store, 2, "approved", "user")
        # 排除 1 篇
        review_candidate(mock_store, 4, "rejected", "user", rejection_reason="irrelevant_domain")
        # 待定 1 篇
        review_candidate(mock_store, 3, "deferred", "user")

        events = list_review_events(mock_store)
        assert len(events) == 4

        # 重新加载验证
        rows2 = mock_store.connection.execute("SELECT * FROM llm_candidates").fetchall()
        items2 = build_queue_items([dict(r) for r in rows2])
        summary2 = compute_queue_summary(items2)
        assert summary2.approved == 2
        assert summary2.rejected == 1
        assert summary2.deferred == 1
        assert summary2.pending == 0

    def test_step7_paper_bundle_creation(self):
        """步骤 7：生成论文 Bundle。"""
        sections = {
            "introduction": PaperSection(name="引言", markdown="焦虑与自尊的关系是心理学经典课题...", source="template"),
            "method": PaperSection(name="方法", markdown="本研究采用问卷法，选取 60 名大学生...", source="template"),
            "result": PaperSection(name="结果", markdown="焦虑量表得分 M = 3.0, SD = 1.1...", source="data"),
            "discussion": PaperSection(name="讨论", markdown="结果表明焦虑与自尊呈负相关...", source="template"),
        }
        bundle = PaperDraftBundle(title="焦虑与自尊关系研究", sections=sections, source="template")
        assert len(bundle.sections) == 4
        assert bundle.all_markdown()

    def test_step8_ai_diff_selection(self):
        """步骤 8：AI 差异对比和逐段选择。"""
        original = "本研究采用问卷法，选取 60 名大学生为被试。"
        revised = "本研究采用横断面问卷调查法，以便利抽样方式选取某高校 60 名大学生为被试。"

        diff = compute_section_diff(original, revised, "method")
        assert diff.change_count >= 1

        # 选择 AI 版
        diff.select_all_revised()
        result = diff.get_selected_text()
        assert "横断面" in result

    def test_step9_health_check(self):
        """步骤 9：项目健康检查。"""
        # 健康项目
        issues = run_health_checks(
            has_data=True,
            variable_types_set=True,
            literature_pending_count=0,
            literature_approved_count=5,
            analysis_results=[{"method": "descriptive"}],
        )
        assert not has_blocking_issues(issues)

        # 不健康项目
        issues_bad = run_health_checks(has_data=False)
        assert has_blocking_issues(issues_bad)

    def test_step10_export_markdown(self):
        """步骤 10：导出 Markdown。"""
        sections = {
            "introduction": PaperSection(name="引言", markdown="焦虑研究...", source="template"),
            "method": PaperSection(name="方法", markdown="问卷法...", source="template"),
            "result": PaperSection(name="结果", markdown="M=3.0, SD=1.1", source="data"),
            "discussion": PaperSection(name="讨论", markdown="支持假设...", source="template"),
        }
        bundle = PaperDraftBundle(title="焦虑与自尊研究", sections=sections, source="template")

        issues = validate_bundle_for_export(bundle)
        assert not any("为空" in i for i in issues)

        result = bundle_to_export_result(bundle, format="markdown")
        assert result.format == "markdown"
        assert "焦虑与自尊研究" in result.content
        assert "## 引言" in result.content
        assert "## 方法" in result.content
        assert "## 结果" in result.content
        assert "## 讨论" in result.content
        assert "source: data" in result.content

    def test_step11_review_action_validation(self):
        """步骤 11：审核操作前端校验。"""
        # 合法操作
        action = ReviewAction(candidate_id=1, decision="approved")
        assert action.validate() == []

        # 排除缺原因
        action_bad = ReviewAction(candidate_id=1, decision="rejected")
        assert len(action_bad.validate()) > 0

        # 合并缺目标
        action_merge = ReviewAction(candidate_id=1, decision="merged")
        assert len(action_merge.validate()) > 0

    def test_full_golden_path_integration(self, sample_questionnaire_data, mock_store):
        """完整黄金路径：数据→分析→文献→论文→导出。"""
        df = sample_questionnaire_data

        # 1. 数据
        assert len(df) == 60

        # 2. 描述统计结果卡
        card = build_card_from_output({
            "test_type": "descriptive",
            "test_name_zh": "描述统计",
            "variables": {"target": "anxiety_1"},
            "results": {"mean": 3.0, "std": 1.1, "n": 60, "min": 1, "max": 5,
                        "skewness": 0.1, "kurtosis": -0.5},
        })
        assert card is not None

        # 3. 文献审核
        review_candidate(mock_store, 1, "approved", "user")
        review_candidate(mock_store, 2, "approved", "user")

        # 4. 构建论文 Bundle
        bundle = PaperDraftBundle(
            title="焦虑与自尊关系研究",
            sections={
                "introduction": PaperSection(name="引言", markdown="焦虑研究...", source="template"),
                "method": PaperSection(name="方法", markdown="问卷法...", source="template"),
                "result": PaperSection(name="结果", markdown=card.apa_text, source="data"),
                "discussion": PaperSection(name="讨论", markdown="结果支持假设...", source="template"),
            },
            source="mixed",
        )

        # 5. 健康检查
        issues = run_health_checks(
            has_data=True,
            variable_types_set=True,
            literature_approved_count=2,
            analysis_results=[{"method": "descriptive"}],
        )
        assert not has_blocking_issues(issues)

        # 6. 导出
        export = bundle_to_export_result(bundle, format="markdown")
        assert "焦虑与自尊关系研究" in export.content
        assert card.apa_text in export.content  # 结果卡 APA 文本在导出中
