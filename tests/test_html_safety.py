"""本地 HTML 报告不得执行用户或模型提供的标记。"""

from src.ui.html_safety import questionnaire_report_to_html_fragment


def test_questionnaire_html_escapes_untrusted_markup():
    fragment = questionnaire_report_to_html_fragment(
        "# 研究报告\n<script>alert(1)</script>\n<img src=x onerror=alert(2)>"
    )
    assert "<h1>研究报告</h1>" in fragment
    assert "<script>" not in fragment
    assert "<img " not in fragment
    assert "&lt;script&gt;" in fragment
    assert "&lt;img src=x onerror=alert(2)&gt;" in fragment


def test_questionnaire_html_only_converts_controlled_line_prefixes():
    fragment = questionnaire_report_to_html_fragment("## 小节\n---\n正文 # 不是标题")
    assert fragment == "<h2>小节</h2><br><hr><br>正文 # 不是标题"
