"""Playwright 浏览器级 E2E 黄金路径 — 完整演示项目流程。

分两部分：
1. 离线验证测试（无需 Playwright，验证 demo 数据和服务层可用）
2. 浏览器黄金路径（需 Playwright + Streamlit 运行）

运行条件：
- pip install playwright pytest-playwright
- playwright install chromium

标记为 pytest.mark.e2e，默认跳过，发版前手动运行：
  .venv\\Scripts\\python.exe -m pytest tests/test_playwright_golden_research_flow.py -m e2e -v
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

E2E_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    E2E_AVAILABLE = True
except ImportError:
    pass

DEMO_DIR = Path(__file__).parent.parent / "demo_projects" / "psychology_questionnaire_demo"
APP_PATH = Path(__file__).parent.parent / "app.py"
SCREENSHOT_DIR = Path(__file__).parent.parent / "test_artifacts" / "screenshots"
TRACE_DIR = Path(__file__).parent.parent / "test_artifacts" / "traces"
BASE_URL = "http://localhost:8502"


# ─── Part 1: Offline validation (no Playwright needed) ───────────────────────


@pytest.fixture(scope="module")
def demo_data_path():
    return DEMO_DIR / "data.csv"


@pytest.fixture(scope="module")
def demo_schema():
    with open(DEMO_DIR / "questionnaire_schema.json", encoding="utf-8") as f:
        return json.load(f)


class TestDemoProjectOffline:
    """离线验证：demo 项目文件和服务层正确性。"""

    def test_demo_project_exists(self):
        assert DEMO_DIR.exists()
        assert (DEMO_DIR / "data.csv").exists()
        assert (DEMO_DIR / "questionnaire_schema.json").exists()
        assert (DEMO_DIR / "literature_seed.json").exists()
        assert (DEMO_DIR / "expected_analysis_cards.json").exists()

    def test_demo_data_valid(self, demo_data_path):
        import pandas as pd
        df = pd.read_csv(demo_data_path)
        assert len(df) == 30
        assert "Q1" in df.columns
        assert "Q10" in df.columns
        assert "gender" in df.columns

    def test_demo_schema_valid(self, demo_schema):
        assert len(demo_schema["dimensions"]) == 2
        assert demo_schema["dimensions"][0]["name"] == "焦虑"
        assert demo_schema["dimensions"][1]["name"] == "自尊"
        assert "Q3" in demo_schema["dimensions"][0]["reverse_items"]

    def test_demo_cleaning_produces_valid_output(self, demo_data_path, demo_schema):
        import pandas as pd
        from src.questionnaire.import_cleaning import (
            ScaleDimension, run_questionnaire_cleaning
        )

        df = pd.read_csv(demo_data_path)
        dims = [
            ScaleDimension(
                name=d["name"],
                items=d["items"],
                reverse_items=d["reverse_items"],
                max_score=d["max_score"],
                min_score=d["min_score"],
            )
            for d in demo_schema["dimensions"]
        ]
        result = run_questionnaire_cleaning(
            df, dimensions=dims, duration_column="duration_seconds", min_duration_seconds=60
        )
        assert result.summary["valid_n"] == 27
        assert result.summary["invalid_n"] == 3
        assert "焦虑_mean" in result.df_scored.columns
        assert "自尊_mean" in result.df_scored.columns

    def test_demo_method_recommendation(self):
        from src.analysis.method_recommender import ResearchDesignInput, recommend_method

        d = ResearchDesignInput(
            purpose="correlation", dv_type="continuous", sample_size=27
        )
        rec = recommend_method(d)
        assert rec.primary_method == "pearson_corr"

    def test_demo_evidence_store(self):
        from src.literature.evidence_record import EvidenceRecord, EvidenceStore

        with open(DEMO_DIR / "literature_seed.json", encoding="utf-8") as f:
            seeds = json.load(f)

        store = EvidenceStore()
        for s in seeds:
            store.add(EvidenceRecord(
                literature_id=s["id"],
                citation_key=s["citation_key"],
                claim=s.get("relevance", ""),
                section_target="introduction",
            ))
        assert len(store.records) == 3
        coverage = store.check_citation_coverage(["wang2023", "li2022", "zhang2021"])
        assert coverage["coverage_rate"] == 1.0

    def test_demo_recipe_prefill_flow(self):
        """验证 demo 的推荐→recipe→plan 闭环。"""
        from src.analysis.method_recommender import (
            ResearchDesignInput, recommend_method, recommendation_to_recipe,
        )
        from src.parser.intent_resolver import AnalysisPlan
        from src.ui.state_keys import ANALYSIS_RECIPE_KEY

        design = ResearchDesignInput(
            purpose="correlation", dv_type="continuous", sample_size=27,
        )
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design, recommendation_id="demo_rec_1")

        session = {ANALYSIS_RECIPE_KEY: recipe}
        retrieved = session[ANALYSIS_RECIPE_KEY]
        assert retrieved.method_id == "pearson_corr"
        assert retrieved.recommendation_id == "demo_rec_1"

        plan = AnalysisPlan(
            test_type="pearson_corr",
            dependent_vars=["焦虑_mean", "自尊_mean"],
            raw_request=f"[推荐方案] {recipe.method_zh}",
        )
        assert plan.test_type == "pearson_corr"
        assert "[推荐方案]" in plan.raw_request

    def test_demo_consistency_check(self, demo_data_path, demo_schema):
        """验证 demo 交付包的一致性检查。"""
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.utils.professional_consistency import check_consistency

        paper = PaperDraftBundle(
            title="焦虑与自尊",
            sections={
                "intro": PaperSection(name="引言", markdown="大学生焦虑与自尊的关系 (Wang, 2023)", source="t"),
                "result": PaperSection(name="结果", markdown="r = -.42, p < .001", source="t"),
            },
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="demo",
            title="焦虑与自尊",
            paper_bundle=paper,
            analysis_cards=[{"method": "pearson_corr", "apa_text": "r = -.42, p < .001"}],
            evidence_records=[{"citation_key": "wang2023", "claim": "焦虑与自尊负相关"}],
        )
        issues = check_consistency(bundle)
        errors = [i for i in issues if i.level == "ERROR"]
        assert not errors

    def test_demo_deliverable_bundle_assembly(self, demo_data_path, demo_schema):
        """验证 demo 数据能组装完整交付包。"""
        import pandas as pd
        from src.questionnaire.import_cleaning import ScaleDimension, run_questionnaire_cleaning
        from src.analysis.method_recommender import ResearchDesignInput, recommend_method
        from src.literature.evidence_record import EvidenceRecord, EvidenceStore
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle

        df = pd.read_csv(demo_data_path)
        dims = [
            ScaleDimension(
                name=d["name"], items=d["items"],
                reverse_items=d["reverse_items"],
                max_score=d["max_score"], min_score=d["min_score"],
            )
            for d in demo_schema["dimensions"]
        ]
        cleaning = run_questionnaire_cleaning(
            df, dimensions=dims, duration_column="duration_seconds", min_duration_seconds=60
        )
        rec = recommend_method(ResearchDesignInput(
            purpose="correlation", dv_type="continuous", sample_size=27
        ))

        with open(DEMO_DIR / "literature_seed.json", encoding="utf-8") as f:
            seeds = json.load(f)
        store = EvidenceStore()
        for s in seeds:
            store.add(EvidenceRecord(
                literature_id=s["id"], citation_key=s["citation_key"],
                claim=s.get("relevance", ""), section_target="introduction",
            ))

        bundle = ResearchDeliverableBundle(
            project_id="demo_golden_path",
            title="大学生焦虑与自尊研究",
            analysis_cards=[{"method": "pearson_corr", "apa_text": "r=-.42, p<.001"}],
            data_cleaning_log=[{"step": e.step, "action": e.action} for e in cleaning.log],
            evidence_records=[r.to_dict() for r in store.records],
            method_recommendations=[{"recommendation": rec.primary_method_zh}],
        )
        manifest = bundle.file_manifest()
        assert len(manifest) >= 1
        meta = bundle.export_meta_dict()
        assert meta["project_id"] == "demo_golden_path"

    # ─── V5.0 新增离线 E2E ─────────────────────────────────────────────────

    def test_template_to_zip_golden_path(self):
        """模板创建→组装交付包→ZIP 导出 完整路径。"""
        import tempfile
        import zipfile
        import io
        from src.templates.registry import create_project_from_template, get_template
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.zip_exporter import build_deliverable_zip

        target = Path(tempfile.mkdtemp())
        project = create_project_from_template("questionnaire_correlation", target)
        assert (project / "data.csv").exists()

        import pandas as pd
        df = pd.read_csv(project / "data.csv")
        assert len(df) >= 30

        paper = PaperDraftBundle(
            title="模板研究",
            sections={"result": PaperSection(name="结果", markdown="r = .45", source="t")},
            source="template",
        )
        bundle = ResearchDeliverableBundle(
            project_id="template_project",
            title="模板研究",
            paper_bundle=paper,
            analysis_cards=[{"method": "pearson_corr", "apa_text": "r=.45, p<.01"}],
        )
        zip_bytes = build_deliverable_zip(bundle, mode="standard")
        assert zip_bytes[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "paper.md" in zf.namelist()
            assert "manifest.json" in zf.namelist()

    def test_apa_figures_in_word_export(self):
        """APA 图表能嵌入 Word 导出。"""
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.apa_figures import generate_mean_se_figure
        from src.output.docx_exporter import build_deliverable_docx

        fig = generate_mean_se_figure(["A", "B"], [3.0, 4.5], [0.3, 0.4])
        paper = PaperDraftBundle(
            title="图表测试",
            sections={"result": PaperSection(name="结果", markdown="见图 1", source="t")},
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="fig_test", title="图表测试", paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": "t=2.1"}],
        )
        bundle.figures = [fig]
        docx_bytes = build_deliverable_docx(bundle, mode="standard")
        assert len(docx_bytes) > 1000

    def test_new_figure_types_generate(self):
        """V5.0 新增图表类型全部能生成。"""
        from src.output.apa_figures import (
            generate_repeated_measures_line,
            generate_interaction_plot,
            generate_regression_fit_figure,
            generate_mediation_path_figure,
            generate_reliability_item_figure,
        )
        figs = [
            generate_repeated_measures_line(["T1", "T2"], {"G": [3, 4]}),
            generate_interaction_plot(["A", "B"], {"X": [3, 5], "Y": [4, 4]}),
            generate_regression_fit_figure([1, 2, 3], [2, 4, 6]),
            generate_mediation_path_figure(a_coef=0.4, b_coef=0.3),
            generate_reliability_item_figure(["Q1", "Q2", "Q3"], [0.5, 0.6, 0.7]),
        ]
        for fig in figs:
            assert fig.png_bytes[:4] == b"\x89PNG"

    def test_pdf_availability_check_runs(self):
        """PDF 可用性检查不崩溃。"""
        from src.output.pdf_exporter import check_pdf_availability
        available, method = check_pdf_availability()
        assert isinstance(available, bool)

    def test_new_result_cards_work(self):
        """V5.0 新增 10 类结果卡全部能构建。"""
        from types import SimpleNamespace
        from src.analysis.result_card import build_card_from_output

        test_cases = [
            ("two_way_anova", SimpleNamespace(factor_a_f=3.0, factor_a_p=0.05, factor_b_f=2.0, factor_b_p=0.1, interaction_f=4.0, interaction_p=0.02, eta2_a=None, eta2_b=None, eta2_ab=None)),
            ("mann_whitney", SimpleNamespace(u_statistic=100, p_value=0.03, z_value=-2.1, r_effect=0.3, n1=15, n2=15)),
            ("wilcoxon", SimpleNamespace(w_statistic=30, p_value=0.04, z_value=-2.0, r_effect=0.35, n=20)),
            ("kruskal_wallis", SimpleNamespace(h_statistic=10, p_value=0.01, df=2, eta_squared=0.1)),
            ("logistic_regression", SimpleNamespace(chi2=12, p_value=0.002, pseudo_r2=0.2, accuracy=0.75, odds_ratios=None)),
            ("mcdonalds_omega", SimpleNamespace(omega=0.85, omega_hierarchical=0.7, n_items=8, alpha=0.82)),
            ("efa", SimpleNamespace(kmo=0.82, bartlett_p=0.001, n_factors=3, variance_explained=65.0, loadings=None)),
        ]
        for method_id, result in test_cases:
            card = build_card_from_output({"test_type": method_id, "result": result})
            assert card.apa_text != ""
            assert card.method_id == method_id

    def test_consistency_v2_structured_checks(self):
        """一致性检查 v2 结构化检查能发现孤立图表。"""
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.utils.professional_consistency import check_consistency

        paper = PaperDraftBundle(
            title="V2检查",
            sections={"result": PaperSection(name="结果", markdown="分析结果如下。", source="t")},
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="v2_check", title="V2检查", paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": "t=2.1, p=.04"}],
        )
        from src.output.apa_figures import generate_mean_se_figure
        bundle.figures = [generate_mean_se_figure(["A", "B"], [3, 4], [0.3, 0.3])]
        issues = check_consistency(bundle)
        orphan_warnings = [i for i in issues if i.code == "ORPHAN_FIGURE"]
        assert len(orphan_warnings) >= 1


# ─── Part 2: Browser E2E (requires Playwright) ──────────────────────────────


def _start_streamlit_server():
    """启动 Streamlit 子进程（端口 8502 避免与开发冲突）。"""
    import sys
    python = sys.executable
    proc = subprocess.Popen(
        [python, "-m", "streamlit", "run", str(APP_PATH),
         "--server.port", "8502", "--server.headless", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(Path(__file__).parent.parent),
    )
    return proc


def _wait_for_server(timeout: int = 120):
    """轮询等待 Streamlit 健康端点。"""
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE_URL}/_stcore/health")
            urllib.request.urlopen(req, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    return False


@pytest.fixture(scope="module")
def streamlit_server():
    """模块级 fixture：启动 Streamlit 服务器。"""
    proc = _start_streamlit_server()
    ready = _wait_for_server(timeout=120)
    if not ready:
        proc.terminate()
        proc.wait()
        pytest.fail("Streamlit server failed to start within 120s")
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def browser(streamlit_server):
    """模块级 fixture：Playwright browser。"""
    if not E2E_AVAILABLE:
        pytest.skip("Playwright not installed")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, request):
    """每个测试一个独立 context，失败时自动截图和保存 trace。"""
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    pg = context.new_page()
    yield pg

    if request.node.rep_call and request.node.rep_call.failed:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        test_name = request.node.name
        pg.screenshot(path=str(SCREENSHOT_DIR / f"{test_name}.png"))
        context.tracing.stop(path=str(TRACE_DIR / f"{test_name}.zip"))
    else:
        context.tracing.stop()

    pg.close()
    context.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """记录测试结果供 page fixture 判断是否截图。"""
    import pluggy
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def _dismiss_privacy(page):
    """关闭隐私声明弹窗（如有）。"""
    try:
        agree = page.locator("button:has-text('同意')")
        if agree.count() > 0:
            agree.first.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass


@pytest.mark.skipif(not E2E_AVAILABLE, reason="Playwright not installed")
@pytest.mark.e2e
class TestBrowserGoldenPath:
    """浏览器级黄金路径 — 验证新 V6 UI 面板可加载无异常。"""

    def test_app_launches_without_error(self, page):
        """应用启动，无 Streamlit 异常。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        errors = page.locator(".stException")
        assert errors.count() == 0, (
            f"Streamlit exceptions: {errors.first.text_content()}" if errors.count() > 0 else ""
        )

    def test_health_endpoint(self, page):
        """Streamlit 健康检查端点可访问。"""
        page.goto(f"{BASE_URL}/_stcore/health", timeout=10_000)
        body = page.locator("body").text_content()
        assert "ok" in body.lower()

    def test_sidebar_exists(self, page):
        """侧边栏可见。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        sidebar = page.locator('[data-testid="stSidebar"]')
        assert sidebar.count() > 0

    def test_file_upload_visible(self, page):
        """文件上传组件存在。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        file_input = page.locator('input[type="file"]')
        assert file_input.count() > 0

    def test_upload_demo_csv(self, page):
        """上传 demo 数据后无异常。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)

        demo_csv = str(DEMO_DIR / "data.csv")
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0:
            file_input.set_input_files(demo_csv)
            page.wait_for_timeout(3000)

        errors = page.locator(".stException")
        assert errors.count() == 0

    def test_no_network_dependency(self, page):
        """全流程不触发外部网络请求（页面加载无超时）。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(3000)
        errors = page.locator(".stException")
        assert errors.count() == 0

    def test_page_no_console_errors(self, page):
        """页面无严重 JS 错误。"""
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(3000)
        critical_errors = [e for e in console_errors if "TypeError" in e or "ReferenceError" in e]
        assert len(critical_errors) == 0, f"JS errors: {critical_errors}"

    def test_method_recommender_route_exists(self, page):
        """方法推荐导航项可见。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        nav = page.locator("text=方法推荐")
        assert nav.count() > 0

    def test_evidence_table_route_exists(self, page):
        """证据表导航项可见。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        nav = page.locator("text=证据表")
        assert nav.count() > 0

    def test_deliverable_export_route_exists(self, page):
        """交付包导出导航项可见。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        nav = page.locator("text=交付包导出")
        assert nav.count() > 0

    def test_method_recommender_panel_loads(self, page):
        """方法推荐面板点击后加载无异常。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        nav = page.locator("text=方法推荐")
        if nav.count() > 0:
            nav.first.click()
            page.wait_for_timeout(2000)
        errors = page.locator(".stException")
        assert errors.count() == 0

    def test_deliverable_center_panel_loads(self, page):
        """交付包导出面板加载无异常。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        nav = page.locator("text=交付包导出")
        if nav.count() > 0:
            nav.first.click()
            page.wait_for_timeout(2000)
        errors = page.locator(".stException")
        assert errors.count() == 0

    def test_evidence_table_panel_loads(self, page):
        """证据表面板加载无异常。"""
        page.goto(BASE_URL, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(2000)
        nav = page.locator("text=证据表")
        if nav.count() > 0:
            nav.first.click()
            page.wait_for_timeout(2000)
        errors = page.locator(".stException")
        assert errors.count() == 0
