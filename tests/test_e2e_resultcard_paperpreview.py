# -*- coding: utf-8 -*-
"""AppTest 实弹：_render_actions 三按钮点击后路径（含 paper_bundle 写入）+ render_paper_preview 主干。

s921-12（合并 s920-17 遗留 2 与 s920-18 遗留 2 的建议）：假 st 里 button 恒 False、
session_state 是字典桩，点击后路径测不了——这里换 streamlit.testing.v1.AppTest 真会话。
**不改生产码**。本文件名已登记 tests/conftest.py:_APP_TEST_FILES ⇒ 运行期
PSY_ANALYSIS_* 全指向 tmp_path，不碰用户真实项目/档案/事件日志。
"""
import pathlib

from streamlit.testing.v1 import AppTest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection

# 脚本在 AppTest 子执行环境里 import：确保仓根在 sys.path（pytest 进程本已插入，防御一层）
_ROOT = pathlib.Path(__file__).resolve().parents[1].as_posix()

_ACTIONS_SCRIPT = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
import streamlit as st
from src.analysis.result_card import AnalysisResultCard
from src.ui.result_card_panel import _render_actions

card = AnalysisResultCard(
    method_id="e2e_t", method_name="独立样本t检验", variables={},
    apa_text="t(18) = 2.10, p = .049",
)
_render_actions(card)
""".replace("__ROOT__", _ROOT)

_PREVIEW_SCRIPT = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
from src.ui.paper_preview_panel import render_paper_preview

render_paper_preview(PAPER_BUNDLE)
""".replace("__ROOT__", _ROOT)


def _at_with_bundle(sections: dict) -> AppTest:
    """起一个真会话，session_state 预置 paper_bundle（跨 run 存活的可变对象）。"""
    at = AppTest.from_string(_ACTIONS_SCRIPT)
    at.session_state["paper_bundle"] = PaperDraftBundle(title="E2E 论文", sections=sections)
    at.run()
    return at


def _insert(at: AppTest) -> AppTest:
    at.button(key="insert_e2e_t").click().run()
    return at


# ─────────────────────────── _render_actions 三按钮 ───────────────────────────
def test_actions_renders_two_downloads_and_one_insert_button():
    at = _at_with_bundle(sections={})
    assert not at.exception

    # AppTest 1.59 的 download_button proto 不回传字节（data 走 deferred_file_id），
    # 载荷内容的逐字断言仍由 s920-17 charac（假 st kwargs 记 data=）钉着；这里钉「两个下载键+插入键齐全」。
    downloads = {d.label: d for d in at.download_button}
    assert "📋 导出 APA 文本" in downloads and "📄 导出 Markdown" in downloads
    assert downloads["📋 导出 APA 文本"].key == "copy_apa_e2e_t"
    assert downloads["📄 导出 Markdown"].key == "export_md_e2e_t"
    # 插入按钮是真 button，且只此一个（第三键路径在点击例里钉）
    assert [b.key for b in at.button] == ["insert_e2e_t"]


def test_insert_click_without_bundle_warns_and_writes_nothing():
    at = AppTest.from_string(_ACTIONS_SCRIPT)
    at.session_state["paper_bundle"] = None
    at.run()

    _insert(at)

    assert not at.exception
    assert len(at.warning) == 1 and "请先生成论文草稿" in at.warning[0].value
    assert at.session_state["paper_bundle"] is None
    assert at.success == []


def test_insert_click_appends_to_existing_result_section_once():
    at = _at_with_bundle(sections={"result": PaperSection(
        name="结果", markdown="既有正文", source="manual")})

    _insert(at)

    sec = at.session_state["paper_bundle"].sections["result"]
    assert sec.markdown == "既有正文\n\nt(18) = 2.10, p = .049"  # 追加一段，不复制粘贴两遍
    assert len(at.success) == 1 and "已插入论文结果章" in at.success[0].value


def test_insert_click_creates_result_section_when_absent():
    at = _at_with_bundle(sections={"method": PaperSection(
        name="方法", markdown="M", source="manual")})

    _insert(at)

    bundle = at.session_state["paper_bundle"]
    sec = bundle.sections["result"]
    assert sec.name == "结果" and sec.source == "data"
    assert sec.markdown == "t(18) = 2.10, p = .049"
    assert "method" in bundle.sections  # 别的章节原样


# ─────────────────────────── render_paper_preview 主干 ───────────────────────────
def test_paper_preview_trunk_metrics_and_warnings():
    script = _PREVIEW_SCRIPT.replace(
        "render_paper_preview(PAPER_BUNDLE)",
        "from src.paper_writer.draft_bundle import PaperDraftBundle as _B, PaperSection as _S\n"
        "b = _B(title='E2E 预览论文', sections={'method': _S(name='方法', markdown='# 方法', source='manual')},"
        " source='mixed', warnings=['缺限制条件'])\n"
        "render_paper_preview(b)",
    )
    at = AppTest.from_string(script, default_timeout=30).run()

    assert not at.exception
    assert at.subheader[0].value == "📄 论文预览"
    metrics = {m.label: str(m.value) for m in at.metric}
    assert metrics["论文标题"] == "E2E 预览论文"
    assert metrics["章节数"] == "1"
    assert metrics["来源"] == "mixed"
    assert any("缺限制条件" in w.value for w in at.warning)
