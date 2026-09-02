"""Psy-Analysis 全局设计系统：颜色、排版、间距与 Streamlit 组件外观。"""

from __future__ import annotations

import streamlit as st


DESIGN_SYSTEM_CSS = """
<style>
:root {
    --psy-font-sans: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
    --psy-bg: #f7f8fa;
    --psy-surface: #ffffff;
    --psy-surface-soft: #f1f4f7;
    --psy-sidebar: #f3f5f8;
    --psy-text: #172033;
    --psy-text-muted: #5c687a;
    --psy-border: #dce2ea;
    --psy-border-strong: #c7d0dc;
    --psy-primary: #1f5b83;
    --psy-primary-hover: #174968;
    --psy-primary-soft: #e8f1f7;
    --psy-success: #287a5a;
    --psy-success-soft: #e9f5ef;
    --psy-warning: #9a6515;
    --psy-warning-soft: #fff6df;
    --psy-danger: #a43b45;
    --psy-danger-soft: #fbecef;
    --psy-info: #275f8c;
    --psy-info-soft: #eaf3fa;
    --psy-focus: #1167a5;
    --psy-radius-sm: 8px;
    --psy-radius-md: 12px;
    --psy-radius-lg: 16px;
    --psy-shadow-sm: 0 1px 2px rgba(23, 32, 51, .05);
    --psy-shadow-md: 0 8px 24px rgba(23, 32, 51, .08);
}

html, body, [class*="css"], .stApp {
    font-family: var(--psy-font-sans);
}

.stApp,
[data-testid="stAppViewContainer"] {
    color: var(--psy-text);
    background: var(--psy-bg);
}

[data-testid="stHeader"] {
    background: rgba(247, 248, 250, .88);
    border-bottom: 1px solid rgba(220, 226, 234, .72);
    backdrop-filter: blur(12px);
}

[data-testid="stMainBlockContainer"] {
    max-width: 1180px;
    padding: 2.5rem 3rem 7rem;
}

[data-testid="stMainBlockContainer"] h1 {
    margin: 0 0 .45rem;
    color: var(--psy-text);
    font-size: clamp(2rem, 2.6vw, 2.5rem);
    line-height: 1.18;
    letter-spacing: -.025em;
}

[data-testid="stMainBlockContainer"] h2 {
    margin: 1.8rem 0 .65rem;
    color: var(--psy-text);
    font-size: clamp(1.45rem, 2vw, 1.75rem);
    line-height: 1.28;
    letter-spacing: -.015em;
}

[data-testid="stMainBlockContainer"] h3 {
    margin: 1.35rem 0 .5rem;
    color: var(--psy-text);
    font-size: clamp(1.15rem, 1.6vw, 1.35rem);
    line-height: 1.35;
}

[data-testid="stMainBlockContainer"] h4,
[data-testid="stMainBlockContainer"] h5 {
    color: var(--psy-text);
    line-height: 1.4;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    line-height: 1.68;
}

[data-testid="stCaptionContainer"] {
    color: var(--psy-text-muted);
    font-size: .84rem;
    line-height: 1.55;
}

a { color: var(--psy-primary); }
hr { border-color: var(--psy-border) !important; margin: 1.65rem 0 !important; }

/* Sidebar: keep the research path scannable and visually quieter than content. */
[data-testid="stSidebar"] {
    min-width: 300px;
    max-width: 300px;
    background: var(--psy-sidebar);
    border-right: 1px solid var(--psy-border);
}

[data-testid="stSidebar"][aria-expanded="false"] {
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    border-right: 0;
}

[data-testid="stSidebarContent"] {
    padding: 1rem .8rem 2rem;
}

[data-testid="stSidebar"] h1 {
    margin: 0 0 .8rem;
    color: var(--psy-text);
    font-size: 1.28rem;
    line-height: 1.35;
    letter-spacing: -.01em;
}

[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: #445166;
    font-size: .82rem;
    font-weight: 650;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] {
    gap: .2rem;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"] {
    min-height: 36px;
    padding: .35rem .5rem;
    border: 1px solid transparent;
    border-radius: var(--psy-radius-sm);
}

[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
    background: rgba(255, 255, 255, .72);
    border-color: var(--psy-border);
}

[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) {
    color: var(--psy-primary);
    background: var(--psy-primary-soft);
    border-color: #bdd3e2;
    font-weight: 650;
}

/* Buttons and controls share one ergonomic 44px rhythm. */
.stButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"],
button[kind="formSubmit"] {
    min-height: 44px;
    padding: .58rem 1rem;
    border-radius: var(--psy-radius-sm);
    font-weight: 650;
    line-height: 1.25;
    box-shadow: none;
    transition: border-color .16s ease, background-color .16s ease, box-shadow .16s ease, transform .16s ease;
}

[data-testid="stBaseButton-primary"] {
    color: #ffffff;
    background: var(--psy-primary);
    border: 1px solid var(--psy-primary);
}

[data-testid="stBaseButton-primary"]:hover {
    color: #ffffff;
    background: var(--psy-primary-hover);
    border-color: var(--psy-primary-hover);
    box-shadow: 0 5px 14px rgba(31, 91, 131, .18);
}

[data-testid="stBaseButton-secondary"] {
    color: #28364a;
    background: var(--psy-surface);
    border: 1px solid var(--psy-border-strong);
}

[data-testid="stBaseButton-secondary"]:hover {
    color: var(--psy-primary);
    background: #fafdff;
    border-color: #8eafc5;
}

[data-testid="stBaseButton-primary"]:active,
[data-testid="stBaseButton-secondary"]:active {
    transform: translateY(1px);
}

input, textarea, [data-baseweb="select"] > div {
    min-height: 44px;
    color: var(--psy-text) !important;
    background: var(--psy-surface) !important;
    border-color: var(--psy-border-strong) !important;
    border-radius: var(--psy-radius-sm) !important;
}

input:hover, textarea:hover, [data-baseweb="select"] > div:hover {
    border-color: #8eafc5 !important;
}

/* Upload is a clear task surface rather than a low-contrast grey strip. */
[data-testid="stFileUploaderDropzone"] {
    min-height: 108px;
    padding: 1.15rem;
    background: var(--psy-surface);
    border: 1.5px dashed #9bb7ca;
    border-radius: var(--psy-radius-md);
}

[data-testid="stFileUploaderDropzone"]:hover {
    background: #f8fbfd;
    border-color: var(--psy-primary);
}

/* Cards, expanders, alerts and tabs use a restrained surface hierarchy. */
[data-testid="stExpander"] {
    overflow: hidden;
    background: rgba(255, 255, 255, .72);
    border: 1px solid var(--psy-border);
    border-radius: var(--psy-radius-sm);
    box-shadow: var(--psy-shadow-sm);
}

[data-testid="stExpander"] summary {
    min-height: 44px;
    padding: .68rem .8rem;
    font-weight: 600;
}

[data-testid="stAlert"] {
    border: 1px solid #c8dae8;
    border-radius: var(--psy-radius-sm);
    box-shadow: none;
}

[data-testid="stAlertContentInfo"] { color: #244f70; }

[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}

[data-testid="stColumn"] > div:has(> [data-testid="stVerticalBlock"]) {
    min-width: 0;
}

[data-testid="stTabs"] [role="tablist"] {
    gap: .35rem;
    border-bottom: 1px solid var(--psy-border);
}

[data-testid="stTabs"] [role="tab"] {
    min-height: 44px;
    padding: .6rem .85rem;
    color: var(--psy-text-muted);
}

[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--psy-primary);
    font-weight: 700;
}

.error-box, .warning-box, .info-box, .success-box {
    padding: 1rem 1.1rem;
    margin: .65rem 0 1rem;
    border: 1px solid var(--psy-border);
    border-left-width: 4px;
    border-radius: var(--psy-radius-sm);
    box-shadow: var(--psy-shadow-sm);
}
.error-box { color: #722a32; background: var(--psy-danger-soft); border-left-color: var(--psy-danger); }
.warning-box { color: #68470f; background: var(--psy-warning-soft); border-left-color: var(--psy-warning); }
.info-box { color: #244f70; background: var(--psy-info-soft); border-left-color: var(--psy-info); }
.success-box { color: #205f47; background: var(--psy-success-soft); border-left-color: var(--psy-success); }

.onboarding-step {
    padding: .65rem 0;
    border-bottom: 1px solid var(--psy-border);
}
.onboarding-step:last-child { border-bottom: 0; }
.tooltip { position: relative; display: inline-block; border-bottom: 1px dotted #7a8798; cursor: help; }

.psy-hero {
    padding: clamp(1.35rem, 3vw, 2.2rem);
    margin: .25rem 0 1.25rem;
    color: var(--psy-text);
    background: linear-gradient(135deg, #f5f8fb 0%, #e9f1f6 100%);
    border: 1px solid #cedee9;
    border-left: 5px solid var(--psy-primary);
    border-radius: var(--psy-radius-lg);
    box-shadow: var(--psy-shadow-md);
}
.psy-hero h2, .psy-hero h3 { margin-top: 0 !important; }
.psy-hero__eyebrow {
    display: inline-block;
    margin-bottom: .45rem;
    color: var(--psy-primary);
    font-size: .78rem;
    font-weight: 750;
    letter-spacing: .08em;
}
.psy-hero__lead { max-width: 62ch; margin: 0 0 .9rem; font-size: 1.03rem; line-height: 1.72; }
.psy-hero__meta { color: var(--psy-text-muted); font-size: .9rem; line-height: 1.7; }
.psy-hero--info { background: linear-gradient(135deg, #f5f9fc 0%, #eaf3f8 100%); }
.psy-hero--success { background: linear-gradient(135deg, #f2f8f5 0%, #e7f3ed 100%); border-color: #c8e0d4; border-left-color: var(--psy-success); }
.psy-hero--warning { background: linear-gradient(135deg, #fffaf0 0%, #fff3d8 100%); border-color: #ead9af; border-left-color: var(--psy-warning); }

.psy-choice-card {
    min-height: 20rem;
    padding: 1.2rem;
    color: var(--psy-text);
    background: var(--psy-surface);
    border: 1px solid var(--psy-border);
    border-top: 4px solid var(--psy-primary);
    border-radius: var(--psy-radius-md);
    box-shadow: var(--psy-shadow-sm);
}
.psy-choice-card--success { border-top-color: var(--psy-success); }
.psy-choice-card--neutral { border-top-color: #68778b; }
.psy-choice-card h3 { margin-top: 0 !important; }
.psy-choice-card__lead, .psy-panel-copy { color: var(--psy-text-muted); font-size: .9rem; line-height: 1.65; }

.psy-score-badge {
    padding: .6rem .8rem;
    margin: .25rem 0;
    color: var(--psy-text-muted);
    text-align: center;
    background: var(--psy-surface-soft);
    border: 1px solid var(--psy-border-strong);
    border-radius: var(--psy-radius-sm);
}
.psy-score-badge span { font-size: .82rem; }
.psy-score-badge--success { color: #205f47; background: var(--psy-success-soft); border-color: #b9d8c9; }
.psy-score-badge--warning { color: #68470f; background: var(--psy-warning-soft); border-color: #ead8a8; }
.psy-score-badge--danger { color: #722a32; background: var(--psy-danger-soft); border-color: #e6c0c5; }

.psy-next-step {
    padding: .75rem .8rem;
    margin: .25rem 0 .6rem;
    color: #29455d;
    background: var(--psy-primary-soft);
    border: 1px solid #c5d8e5;
    border-radius: var(--psy-radius-sm);
    line-height: 1.55;
}
.psy-next-step strong { display: block; color: var(--psy-primary); font-size: .83rem; }
.psy-next-step span { display: block; margin-top: .18rem; color: #536477; font-size: .77rem; }

.psy-stepper {
    min-height: 44px;
    padding: .65rem .3rem;
    color: var(--psy-text-muted);
    text-align: center;
    border-bottom: 3px solid var(--psy-border-strong);
}
.psy-stepper--active { color: var(--psy-primary); border-bottom-color: var(--psy-primary); }
.psy-stepper--complete { color: var(--psy-success); border-bottom-color: var(--psy-success); }

code, [data-testid="stCode"] {
    border-radius: var(--psy-radius-sm);
}

/* Compact laptop and narrow-screen ergonomics. */
@media (max-width: 1200px) {
    [data-testid="stMainBlockContainer"] { padding: 2rem 2rem 6rem; }
}

@media (max-width: 900px) {
    [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem 5rem; }
    [data-testid="stMainBlockContainer"] h1 { font-size: 1.9rem; }
    [data-testid="stMainBlockContainer"] h2 { font-size: 1.45rem; }
    [data-testid="stHorizontalBlock"] { gap: .75rem; flex-wrap: wrap; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: min(100%, 16rem) !important;
        flex: 1 1 16rem !important;
    }
    .psy-hero { padding: 1.2rem; border-radius: var(--psy-radius-md); }
    .psy-choice-card { min-height: 0; }
}

@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] { padding-inline: .75rem; }
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] { width: 100%; }
    [data-testid="stFileUploaderDropzone"] { min-height: 96px; padding: .85rem; }
}
</style>
"""


def render_design_system() -> None:
    """在页面最前部注入不含用户输入的全局样式。"""
    st.markdown(DESIGN_SYSTEM_CSS, unsafe_allow_html=True)
