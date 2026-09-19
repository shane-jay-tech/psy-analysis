# -*- coding: utf-8 -*-
"""src/ui/paper_preview_panel.py 三个小助手的结构钉桩（s920-18）。

改前实况：`_render_bundle_info:145`／`_render_sections_preview:153`／`_render_warnings:171`
在 `tests/` 里**零覆盖**（面板只有导出侧被间接测到）。本文件用记录型假 `st` 钉三件事＋空 bundle 分支，
**不碰 render_paper_preview / render_ai_diff_panel 主干**（那两个要真实 widget 与 diff 计算，成本另计）。

顺带钉出一条真实不对称（见 test_non_standard_section_…）：标准章节会显示"置信度说明"，
非标准章节那一段**没有** caption 分支——现状如此，改不改由日间定，本单只留证据。
"""
from contextlib import contextmanager

import pytest

import src.ui.paper_preview_panel as pp
from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection


class Rec:
    """记录型假 st：每次 UI 调用落成一条 (通道, 内容)，顺序即渲染顺序。"""

    def __init__(self, log, path="st"):
        self._log = log
        self._path = path

    def _emit(self, kind, *payload):
        self._log.append((kind, self._path, *payload))

    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        cols = [Rec(self._log, f"{self._path}.col{i}") for i in range(n)]
        self._emit("columns", n)
        return cols

    def metric(self, label, value, **k):
        self._emit("metric", label, value)

    def markdown(self, body, **k):
        self._emit("markdown", body)

    def caption(self, body, **k):
        self._emit("caption", body)

    def warning(self, body, **k):
        self._emit("warning", body)

    def error(self, body, **k):
        self._emit("error", body)

    @contextmanager
    def expander(self, label, expanded=False, **k):
        self._emit("expander-open", label, expanded)
        yield Rec(self._log, f"{self._path}>exp({label})")
        self._emit("expander-close", label, expanded)

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}（假 st 未实现，说明渲染走了别的路径）")


@pytest.fixture
def log(monkeypatch):
    recs = []
    monkeypatch.setattr(pp, "st", Rec(recs))
    return recs


def _kinds(recs):
    return [r[0] for r in recs]


def _bundle(**kw):
    kw.setdefault("title", "睡眠与学业表现")
    kw.setdefault("source", "ai")
    return PaperDraftBundle(**kw)


def test_bundle_info_emits_exactly_three_metrics(log):
    """基本信息区固定三列：标题／章节数／来源，值直接取 bundle 字段。"""
    pp._render_bundle_info(_bundle(sections={"introduction": PaperSection(name="引言", markdown="m", source="ai")}))

    metrics = [(r[2], r[3]) for r in log if r[0] == "metric"]
    assert [m[0] for m in metrics] == ["论文标题", "章节数", "来源"]
    assert metrics[1][1] == 1, "章节数就是 len(sections)"
    assert _kinds(log).count("columns") == 1


def test_sections_preview_follows_section_order_and_labels_in_chinese(log):
    """标准章节按 SECTION_ORDER 出展开器、用中文名；置信度说明只在有值时出 caption。"""
    bundle = _bundle(sections={
        "discussion": PaperSection(name="讨论", markdown="d", source="ai", confidence_note="仅两条相关研究"),
        "introduction": PaperSection(name="引言", markdown="i", source="template"),
    })

    pp._render_sections_preview(bundle)

    opened = [r[2] for r in log if r[0] == "expander-open"]
    assert len(opened) == 2, "两个标准章节 ⇒ 两个展开器"
    assert opened[0].startswith("📖 引言"), f"顺序应随 SECTION_ORDER（introduction 在前），实得 {opened}"
    assert "ai" in opened[1], "展开器标题里带来源"
    assert all(r[3] is False for r in log if r[0] == "expander-open"), "默认必须折叠"
    caps = [r[2] for r in log if r[0] == "caption"]
    assert caps == ["置信度说明: 仅两条相关研究"], "无 confidence_note 的章节不该出 caption"


def test_non_standard_section_loses_the_confidence_note(log):
    """现状不对称：非标准章节走第二个循环，**不渲染置信度说明**（只 markdown 正文）。

    钉住它不是认可它——是为了让"要不要统一"这个决定有代价可见：
    今天给非标准章节写 confidence_note，用户在预览里看不见。
    """
    bundle = _bundle(sections={"appendix": PaperSection(name="附录", markdown="a", source="manual",
                                                        confidence_note="手工补充")})

    pp._render_sections_preview(bundle)

    opened = [r[2] for r in log if r[0] == "expander-open"]
    assert len(opened) == 1 and "appendix" in opened[0], "非标准章节按原 key 出现"
    assert not [r for r in log if r[0] == "caption"], "现状：这一段没有置信度说明分支"


def test_warnings_only_render_when_present(log):
    """有警告 ⇒ 一条分隔线 + 每条一个 ⚠️ warning；没警告 ⇒ 整个区块零输出。"""
    empty = _bundle(warnings=[])
    pp._render_warnings(empty)
    assert log == [], "空 warnings 不该出现任何 UI 输出（连分隔线都不该有）"

    bundle = _bundle(warnings=["缺少方法章节", "图表未生成"])
    pp._render_warnings(bundle)

    assert [r[0] for r in log] == ["markdown", "warning", "warning"]
    assert log[0][2] == "---", "分隔线在警告之前"
    assert all(r[2].startswith("⚠️ ") for r in log[1:])


def test_empty_bundle_renders_without_crashing(log):
    """空 bundle（草稿未生成时的状态）：三助手都不抛，章节数为 0、没有展开器。"""
    bundle = _bundle(sections={}, warnings=[])

    pp._render_bundle_info(bundle)
    pp._render_sections_preview(bundle)
    pp._render_warnings(bundle)

    assert [(r[2], r[3]) for r in log if r[0] == "metric"][1] == ("章节数", 0)
    assert "expander-open" not in _kinds(log)
    assert log, "至少要渲染出基本信息区，不能整页空白"
