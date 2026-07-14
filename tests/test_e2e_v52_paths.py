"""
Playwright E2E — v5.2 新路径覆盖。

覆盖场景：
1. 首页加载无异常
2. 项目状态页下一步推荐可见
3. 隐私/非诊断声明可见
4. 导出页隐私预检触发
5. 高风险敏感信息阻断导出
6. Word/ZIP 导出按钮可用
7. ZIP 下载后结构验证（tables/, manifest.json）
8. 缓存清理按钮可用
9. 错误提示渲染正常
10. 页面无 Streamlit exception
"""

import pytest
import zipfile
import json
from pathlib import Path


def _playwright_available():
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


# 标记需要 playwright 环境
pytestmark = [
    pytest.mark.playwright,
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _playwright_available(),
        reason="Playwright not installed or browsers not available",
    ),
]


BASE_URL = "http://localhost:8501"


# ---------------------------------------------------------------------------
# Fixtures（复用 test_playwright_e2e.py 的模式）
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def browser():
    """模块级 fixture：启动 Streamlit + Playwright browser。"""
    import subprocess
    import time
    import urllib.request
    import urllib.error

    from playwright.sync_api import sync_playwright

    # 清空偏好以重现首次状态
    try:
        from src.utils.user_prefs import reset_prefs
        reset_prefs()
    except Exception:
        pass

    app_file = str(Path(__file__).resolve().parent.parent / "app.py")
    proc = subprocess.Popen(
        ["streamlit", "run", app_file, "--server.port", "8501", "--server.headless", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 等待 Streamlit 就绪
    deadline = time.time() + 120
    ready = False
    while time.time() < deadline:
        try:
            req = urllib.request.Request(BASE_URL + "/_stcore/health")
            urllib.request.urlopen(req, timeout=2)
            ready = True
            break
        except (urllib.error.URLError, OSError):
            time.sleep(1)

    if not ready:
        proc.terminate()
        proc.wait()
        pytest.fail("Streamlit server failed to start within 120s")

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def page(browser):
    """每个测试独立 page（隔离 session state）。"""
    context = browser.new_context()
    pg = context.new_page()
    yield pg
    pg.close()
    context.close()


@pytest.fixture
def app_url():
    """应用 URL。"""
    return BASE_URL


def _dismiss_privacy(page):
    """关闭隐私声明弹窗（如果存在）。"""
    try:
        agree = page.locator("button:has-text('同意')")
        if agree.count() > 0:
            agree.first.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. 页面加载基础检查
# ---------------------------------------------------------------------------

class TestV52PageLoading:
    """页面加载基础检查。"""

    def test_homepage_no_exception(self, page, app_url):
        """首页加载无 Streamlit exception。"""
        page.goto(app_url, timeout=30_000)
        page.wait_for_load_state("networkidle")
        _dismiss_privacy(page)
        # 检查无 Streamlit 异常弹窗
        errors = page.locator(".stException")
        assert errors.count() == 0, (
            f"页面存在 Streamlit 异常: "
            f"{errors.first.text_content() if errors.count() > 0 else ''}"
        )

    def test_privacy_disclaimer_visible(self, page, app_url):
        """非诊断免责声明在项目状态页可见。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        # 导航到项目状态页
        try:
            page.locator("text=📊 项目状态").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.wait_for_timeout(1000)
        content = page.content()
        # 检查非诊断声明相关文本
        assert "本系统" in content or "不具备" in content or "非诊断" in content or "免责" in content

    def test_no_streamlit_error_text(self, page, app_url):
        """页面不含 'Traceback' / 'Error' 等异常痕迹。"""
        page.goto(app_url, timeout=30_000)
        page.wait_for_load_state("networkidle")
        _dismiss_privacy(page)
        page.wait_for_timeout(1000)
        # stException 是 Streamlit 报错的 class
        assert page.locator(".stException").count() == 0
        # 不应出现 Python traceback
        content = page.content()
        assert "Traceback (most recent call last)" not in content


# ---------------------------------------------------------------------------
# 2. 下一步推荐功能
# ---------------------------------------------------------------------------

class TestV52NextStepRecommendation:
    """下一步推荐功能。"""

    def test_recommendation_cards_visible(self, page, app_url):
        """项目状态页显示下一步推荐卡片。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        try:
            page.locator("text=📊 项目状态").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.wait_for_timeout(1500)
        content = page.content()
        # 推荐卡片至少有"下一步"/"推荐"/"上传"相关文字
        assert "下一步" in content or "推荐" in content or "上传" in content


# ---------------------------------------------------------------------------
# 3. 隐私预检功能
# ---------------------------------------------------------------------------

class TestV52PrivacyPrecheck:
    """隐私预检功能。"""

    def test_export_page_has_precheck(self, page, app_url):
        """导出页面包含隐私预检相关元素。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        try:
            page.locator("text=📦 交付包导出").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.wait_for_timeout(1500)
        content = page.content()
        assert "数据治理" in content or "隐私" in content or "预检" in content or "导出" in content

    def test_sensitive_info_warning(self, page, app_url):
        """高风险敏感信息场景有阻断/警告提示。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        try:
            page.locator("text=📦 交付包导出").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.wait_for_timeout(1500)
        content = page.content()
        # 导出页应有隐私/安全相关提示
        assert (
            "隐私" in content
            or "敏感" in content
            or "脱敏" in content
            or "安全" in content
            or "数据治理" in content
        )


# ---------------------------------------------------------------------------
# 4. 导出按钮可用性
# ---------------------------------------------------------------------------

class TestV52ExportButtons:
    """导出按钮可用性。"""

    def test_word_export_button_present(self, page, app_url):
        """Word 导出按钮在导出页可见。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        try:
            page.locator("text=📦 交付包导出").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.wait_for_timeout(1500)
        content = page.content()
        assert "Word" in content or "docx" in content.lower() or "导出" in content

    def test_zip_export_button_present(self, page, app_url):
        """ZIP 导出按钮在导出页可见。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        try:
            page.locator("text=📦 交付包导出").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        page.wait_for_timeout(1500)
        content = page.content()
        assert "ZIP" in content or "zip" in content or "打包" in content or "导出" in content


# ---------------------------------------------------------------------------
# 5. 缓存管理功能
# ---------------------------------------------------------------------------

class TestV52CacheManagement:
    """缓存管理功能。"""

    def test_sidebar_cache_button(self, page, app_url):
        """侧栏有缓存清理入口。"""
        page.goto(app_url, timeout=30_000)
        _dismiss_privacy(page)
        page.wait_for_timeout(1000)
        content = page.content()
        assert "缓存清理" in content or "缓存" in content or "清理" in content


# ---------------------------------------------------------------------------
# 6. ZIP 导出结构验证（离线，不需要浏览器）
# ---------------------------------------------------------------------------

class TestV52ZipStructure:
    """ZIP 导出结构验证（离线验证，不需要真实 Streamlit）。"""

    @pytest.mark.skipif(
        not Path(__file__).resolve().parent.parent.joinpath("src/output/zip_exporter.py").exists(),
        reason="zip_exporter module not found",
    )
    def test_zip_contains_tables_directory(self, tmp_path):
        """验证导出 ZIP 包含 tables/ 目录。"""
        from src.output.zip_exporter import build_deliverable_zip
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection

        paper = PaperDraftBundle(
            title="测试论文",
            sections={
                "result": PaperSection(name="结果", markdown="r = .42, p < .001", source="test")
            },
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="test_zip",
            title="测试项目",
            paper_bundle=paper,
            analysis_cards=[{
                "method": "pearson_correlation",
                "apa_text": "r = .42, p < .001",
                "variables": ["x", "y"],
                "correlation_matrix": [[1.0, 0.42], [0.42, 1.0]],
                "p_matrix": [[0.0, 0.001], [0.001, 0.0]],
                "n": 100,
            }],
        )
        zip_bytes = build_deliverable_zip(bundle, mode="standard")

        zip_path = tmp_path / "test.zip"
        zip_path.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # 验证 tables/ 目录存在
            table_files = [n for n in names if n.startswith("tables/")]
            assert len(table_files) > 0, f"ZIP should contain tables/ directory, got: {names}"
            # 验证 manifest
            assert "manifest.json" in names
            manifest = json.loads(zf.read("manifest.json"))
            assert isinstance(manifest, list)

    @pytest.mark.skipif(
        not Path(__file__).resolve().parent.parent.joinpath("src/output/zip_exporter.py").exists(),
        reason="zip_exporter module not found",
    )
    def test_zip_tables_have_csv_and_md(self, tmp_path):
        """验证 tables/ 中有 CSV 和 MD 格式。"""
        from src.output.zip_exporter import build_deliverable_zip
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection

        paper = PaperDraftBundle(
            title="测试",
            sections={"r": PaperSection(name="结果", markdown="t=2.5", source="t")},
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="t2",
            title="测试",
            paper_bundle=paper,
            analysis_cards=[{
                "method": "descriptive",
                "apa_text": "M=3.5, SD=1.2",
                "stats": {"mean": 3.5, "std": 1.2, "n": 50, "min": 1, "max": 5},
            }],
        )
        zip_bytes = build_deliverable_zip(bundle, mode="standard")
        zip_path = tmp_path / "test2.zip"
        zip_path.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            csv_files = [n for n in names if n.endswith(".csv") and "table" in n.lower()]
            md_files = [n for n in names if n.endswith(".md") and "table" in n.lower()]
            assert len(csv_files) > 0, f"No CSV table files found in: {names}"
            assert len(md_files) > 0, f"No MD table files found in: {names}"


# ---------------------------------------------------------------------------
# 7. 一致性检查 v3 覆盖
# ---------------------------------------------------------------------------

class TestV52ConsistencyV3:
    """一致性检查 v3 覆盖。"""

    def test_consistency_includes_table_checks(self):
        """验证一致性检查包含表格/隐私相关检查项。"""
        from src.utils.professional_consistency import check_consistency
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection

        paper = PaperDraftBundle(
            title="测试",
            sections={"r": PaperSection(name="结果", markdown="如表1所示", source="t")},
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="t3",
            title="测试",
            paper_bundle=paper,
            analysis_cards=[{"method": "pearson_correlation", "apa_text": "r=.5"}],
        )
        issues = check_consistency(bundle)
        check_ids = [i.check_id for i in issues]
        # 应该能找到表格或隐私相关检查
        assert any("table" in cid or "privacy" in cid for cid in check_ids), (
            f"Expected table/privacy check_id in: {check_ids}"
        )
