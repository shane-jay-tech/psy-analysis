"""v3.8 O3: AI 痕迹检测器测试。"""

import pytest

from src.output.ai_trace_detector import (
    AITraceReport,
    TraceHit,
    TracePattern,
    detect_ai_traces,
    render_report_markdown,
    rewrite_suggestion,
    score_ai_likelihood,
)


# ---------------------------------------------------------------------------
# 基础检测
# ---------------------------------------------------------------------------

class TestBasicDetection:
    def test_empty_text_returns_empty_report(self):
        report = detect_ai_traces("")
        assert report.total_chars == 0
        assert report.hits == []
        assert "空" in report.summary

    def test_clean_text_no_hits(self):
        # 一段没有 AI 痕迹的描述性文字
        text = "我们使用 SPSS 26 跑了独立样本 t 检验。男生组（M=4.2, SD=0.8）显著高于女生组（M=3.6, SD=0.9）, t(98)=3.21, p<.01。"
        report = detect_ai_traces(text)
        assert len(report.hits) == 0
        assert report.score < 5
        assert "未发现" in report.summary

    def test_high_severity_hits_counted(self):
        text = "首先，我们分析了数据。其次，我们发现了规律。综上所述，研究值得深入探讨。"
        report = detect_ai_traces(text)
        # 命中：开场八股 ×2（首先/其次）+ 总结套话 ×1（综上所述）+ 值得深入探讨 ×1
        assert report.severity_counts["high"] >= 3
        assert report.has_high_severity
        assert report.score > 20

    def test_score_scales_with_text_length(self):
        """同样数量的命中，文本越长评分越低（每千字归一化）。"""
        # 用单个低权重命中，避免短文本立刻顶到 100
        bad = "结果表明：A。" + "纯净句。" * 30
        long_with_same = "结果表明：A。" + "纯净句。" * 800
        s1 = score_ai_likelihood(bad)
        s2 = score_ai_likelihood(long_with_same)
        assert s1 > s2


# ---------------------------------------------------------------------------
# 模式覆盖
# ---------------------------------------------------------------------------

class TestPatternCoverage:
    def test_opening_cliche_detected(self):
        text = "首先，本研究关注..."
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "开场八股" in labels

    def test_summary_cliche_detected(self):
        text = "综上所述，结果显示..."
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "总结套话" in labels

    def test_xxx_meaningful_detected(self):
        text = "本研究具有重要理论意义。"
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "具有重要意义" in labels

    def test_provide_template_detected(self):
        text = "为本科教学提供了重要参考。"
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "为...提供..." in labels

    def test_worth_exploring_detected(self):
        text = "这一现象值得深入探讨。"
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "值得深入探讨" in labels

    def test_conclusion_template_detected(self):
        text = "本文得出以下结论："
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "结论部分模板" in labels

    def test_future_research_detected(self):
        text = "未来研究可以进一步探索更多变量。"
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "未来研究展望" in labels

    def test_riyuexinyi_detected(self):
        text = "随着信息技术日新月异的发展..."
        report = detect_ai_traces(text)
        labels = [h.pattern_label for h in report.hits]
        assert "日新月异" in labels


# ---------------------------------------------------------------------------
# 行号 + 上下文
# ---------------------------------------------------------------------------

class TestLineContext:
    def test_line_number_correctly_calculated(self):
        text = "第一行干净。\n第二行也干净。\n首先，这里有问题。\n第四行干净。"
        report = detect_ai_traces(text)
        assert len(report.hits) >= 1
        # "首先" 在第三行
        first_hit = report.hits[0]
        assert first_hit.line_no == 3
        assert "首先" in first_hit.line_text

    def test_hits_sorted_by_position(self):
        text = "本研究具有重要意义。综上所述，未来研究可以进一步推进。"
        report = detect_ai_traces(text)
        positions = [h.char_start for h in report.hits]
        assert positions == sorted(positions)


# ---------------------------------------------------------------------------
# 自定义 + 过滤
# ---------------------------------------------------------------------------

class TestCustomization:
    def test_severity_filter(self):
        text = "首先，本研究表明结果有意义。"  # 高 + 低
        report_high = detect_ai_traces(text, severity_filter=["high"])
        for h in report_high.hits:
            assert h.severity == "high"

    def test_extra_pattern_added(self):
        custom = TracePattern(
            label="自定义标记",
            severity="med",
            pattern=r"喵喵喵",
            why="测试",
            suggestion="改成「狗狗狗」",
        )
        text = "正常文本喵喵喵正常文本。"
        report = detect_ai_traces(text, extra_patterns=[custom])
        labels = [h.pattern_label for h in report.hits]
        assert "自定义标记" in labels


# ---------------------------------------------------------------------------
# 单句替换建议
# ---------------------------------------------------------------------------

class TestRewriteSuggestion:
    def test_remove_opening_cliche(self):
        out = rewrite_suggestion("首先，我们分析数据。")
        assert "首先" not in out

    def test_replace_buzhukan(self):
        out = rewrite_suggestion("不难看出，效果显著。")
        assert "不难看出" not in out
        assert "可以看到" in out

    def test_replace_yourujirizengshui(self):
        out = rewrite_suggestion("社会日新月异。")
        assert "日新月异" not in out

    def test_empty_input(self):
        assert rewrite_suggestion("") == ""


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

class TestReportRendering:
    def test_markdown_renders_when_clean(self):
        text = "我们用 SPSS 跑了 t 检验。"
        report = detect_ai_traces(text)
        md = render_report_markdown(report)
        assert "AI 痕迹检测" in md
        assert "未发现" in md

    def test_markdown_groups_by_severity(self):
        text = "首先，本研究综上所述具有重要意义，值得深入探讨。"
        report = detect_ai_traces(text)
        md = render_report_markdown(report)
        assert "🔴" in md  # 必删段
        assert "必删" in md

    def test_max_hits_truncation(self):
        # 制造大量命中
        text = "\n".join(["首先，A。"] * 50)
        report = detect_ai_traces(text)
        md = render_report_markdown(report, max_hits=5)
        assert "另外" in md  # 截断提示


# ---------------------------------------------------------------------------
# 综合：实际论文段落
# ---------------------------------------------------------------------------

class TestRealisticParagraph:
    def test_full_ai_generated_paragraph_high_score(self):
        # 模拟 AI 生成的典型论文结尾段
        ai_text = """
        综上所述，本研究具有重要理论意义和实践价值。
        本研究表明，社交焦虑与抑郁存在显著相关。
        本文得出以下结论：首先，性别差异不显著；
        其次，年龄是重要预测因子；最后，干预方案值得深入探讨。
        未来研究可以进一步从神经机制层面探索。
        本研究为高校心理健康工作提供了重要参考。
        """
        report = detect_ai_traces(ai_text)
        assert report.score >= 50  # 重度
        assert report.severity_counts["high"] >= 4

    def test_human_written_paragraph_low_score(self):
        # 模拟学生自己写的段落
        human_text = """
        我们用独立样本 t 检验比较两组焦虑分。男生组（N=48, M=4.2, SD=0.8）
        与女生组（N=52, M=3.6, SD=0.9）差异不显著，t(98)=3.21, p=.002，
        Cohen's d=0.71。这与 Smith (2018) 在英国样本的发现方向一致，
        但效应量偏大——可能是因为我们的招募渠道偏重高焦虑被试。
        样本量不足以做亚组分析（每组 N<30），下一步需要复制研究。
        """
        report = detect_ai_traces(human_text)
        assert report.score < 20  # 轻度
        assert report.severity_counts.get("high", 0) <= 1
