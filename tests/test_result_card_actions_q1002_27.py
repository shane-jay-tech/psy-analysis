# -*- coding: utf-8 -*-
"""s1002-27：resultcard _render_actions 三按钮点击路径补面（s920-17 遗留 2）。

三按钮：📋 导出 APA（download_button）/ 📄 导出 Markdown（download_button）/
📝 插入论文结果章（button → _insert_to_paper_bundle → session_state["paper_bundle"] 写入）。

形态：会话桩级（FakeSt 记 download_button 参数＋button 可编程返回）——真 AppTest 面
download_button 载荷在 streamlit 1.58 结构性缺位（s1002-25 设计档判定），桩级是
当下唯一能断言载荷的口。零生产码改动。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

import src.ui.result_card_panel as rcp
from src.analysis.result_card import AnalysisResultCard
from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection


class FakeSt:
    def __init__(self, pressed=()):
        self.pressed = set(pressed)
        self.downloads = []
        self.messages = {"success": [], "warning": [], "info": []}

    def columns(self, n):
        return [self] * (n if isinstance(n, int) else len(n))

    def expander(self, label, expanded=False, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def button(self, label, **k):
        return label in self.pressed

    def download_button(self, label, data=None, file_name=None, mime=None, **k):
        self.downloads.append(
            {"label": label, "data": data, "file_name": file_name, "mime": mime})
        return True

    def success(self, msg, **k):
        self.messages["success"].append(msg)

    def warning(self, msg, **k):
        self.messages["warning"].append(msg)

    def info(self, msg, **k):
        self.messages["info"].append(msg)

    def __getattr__(self, name):
        raise AssertionError(f"FakeSt 未预期的调用：{name}（零宽桩纪律）")


@pytest.fixture
def card():
    return AnalysisResultCard(
        method_id="ttest_q1002_27",
        method_name="合成 t 检验",
        variables={"group": ["甲", "乙"]},
        apa_text="t(58) = 2.10, p = .040（合成 APA 文本）",
    )


def _bundle_with_result_section() -> PaperDraftBundle:
    return PaperDraftBundle(title="合成草稿", sections={"result": PaperSection(
        name="结果", markdown="既有结果段。", source="data")})


# ---------- ① 复制 APA：download 载荷=card.apa_text ----------

def test_apa_download_payload_is_card_apa_text(card):
    fake = FakeSt()
    rcp.st = fake
    rcp._render_actions(card)
    apa = [d for d in fake.downloads if d["label"] == "📋 导出 APA 文本"]
    assert len(apa) == 1
    assert apa[0]["data"] == card.apa_text
    assert apa[0]["file_name"] == "apa_result.txt"


def test_apa_download_absent_when_apa_text_empty(card):
    card.apa_text = ""
    fake = FakeSt()
    rcp.st = fake
    rcp._render_actions(card)
    assert not [d for d in fake.downloads if "APA" in d["label"]], \
        "空 apa_text 仍渲染 APA 下载口（:119 if 守卫失效）"


# ---------- ② 导出 Markdown：载荷=to_markdown() 全文 ----------

def test_md_download_payload_is_to_markdown(card):
    fake = FakeSt()
    rcp.st = fake
    rcp._render_actions(card)
    md = [d for d in fake.downloads if d["label"] == "📄 导出 Markdown"]
    assert len(md) == 1
    assert md[0]["data"] == card.to_markdown()
    assert md[0]["file_name"] == f"result_card_{card.method_id}.md"
    assert md[0]["mime"] == "text/markdown"


# ---------- ③ 插入论文结果章：paper_bundle 写入两态 ----------

def test_insert_appends_to_existing_result_section(card):
    bundle = _bundle_with_result_section()
    fake = FakeSt(pressed={"📝 插入论文结果章"})
    fake.session_state = {"paper_bundle": bundle}
    rcp.st = fake
    rcp._render_actions(card)
    assert bundle.sections["result"].markdown.endswith(card.apa_text)
    assert "既有结果段。" in bundle.sections["result"].markdown   # 原文保留
    assert "已插入论文结果章。" in fake.messages["success"]


def test_insert_creates_result_section_when_absent(card):
    bundle = PaperDraftBundle(title="合成草稿", sections={})
    fake = FakeSt(pressed={"📝 插入论文结果章"})
    fake.session_state = {"paper_bundle": bundle}
    rcp.st = fake
    rcp._render_actions(card)
    assert "result" in bundle.sections
    assert bundle.sections["result"].markdown == card.apa_text
    assert bundle.sections["result"].source == "data"
    assert "已插入论文结果章。" in fake.messages["success"]


def test_insert_without_bundle_warns_and_no_crash(card):
    fake = FakeSt(pressed={"📝 插入论文结果章"})
    fake.session_state = {}                       # 无 paper_bundle
    rcp.st = fake
    rcp._render_actions(card)
    assert "请先生成论文草稿" in fake.messages["warning"][0]
    assert fake.messages["success"] == []
