"""前端设计系统与人体工学契约。"""

from pathlib import Path

from src.ui.design_system import DESIGN_SYSTEM_CSS


ROOT = Path(__file__).resolve().parent.parent


def test_design_tokens_and_ergonomic_targets_are_centralized():
    required = {
        "--psy-primary",
        "--psy-bg",
        "--psy-text-muted",
        "--psy-radius-md",
        "min-height: 44px",
        "max-width: 1180px",
        "@media (max-width: 900px)",
        "flex-wrap: wrap",
        "stFileUploaderDropzone",
        "stRadioOption",
        'stSidebar"][aria-expanded="false"]',
        ".psy-stepper--active",
        ".psy-choice-card",
        ".psy-hero--warning",
        ".psy-score-badge--danger",
    }
    assert required <= {token for token in required if token in DESIGN_SYSTEM_CSS}


def test_app_renders_design_system_before_accessibility_support():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    design_pos = source.index("render_design_system()")
    accessibility_pos = source.index("render_accessibility_support()")
    assert design_pos < accessibility_pos
    assert "background-color: #fff0f0" not in source
    assert 'initial_sidebar_state="auto"' in source
    assert source.count('st.title("📈 数据分析")') == 1
    assert 'value=st.session_state.undergrad_mode' not in source
    assert '"undergrad_mode_toggle" not in st.session_state' in source


def test_route_panels_do_not_repeat_page_titles():
    template_source = (ROOT / "src" / "ui" / "template_center_panel.py").read_text(encoding="utf-8")
    deliverable_source = (ROOT / "src" / "ui" / "deliverable_center_panel.py").read_text(encoding="utf-8")
    assert 'st.subheader("📋 项目模板中心")' not in template_source
    assert 'st.subheader("📦 研究交付包导出中心")' not in deliverable_source


def test_wizard_uses_design_system_hero_and_semantic_stepper():
    source = (ROOT / "src" / "ui" / "upstream_panel.py").read_text(encoding="utf-8")
    assert 'class="psy-hero psy-hero--info"' in source
    assert "psy-stepper--{state}" in source
    assert 'f"**{stage.id}' not in source
    wizard_source = (ROOT / "src" / "ui" / "undergrad_wizard.py").read_text(encoding="utf-8")
    assert 'class="psy-choice-card"' in wizard_source
    assert "height:320px" not in wizard_source
    literature_source = (ROOT / "src" / "ui" / "literature_review_panel.py").read_text(encoding="utf-8")
    assert 'class="psy-hero psy-hero--info"' in literature_source
    assert "psy-score-badge--{tone}" in literature_source
    assert '"不足": "#e53935"' not in literature_source


def test_streamlit_theme_matches_design_tokens():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'primaryColor = "#1F5B83"' in config
    assert 'backgroundColor = "#F7F8FA"' in config
    assert 'textColor = "#172033"' in config
