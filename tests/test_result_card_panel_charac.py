# -*- coding: utf-8 -*-
"""src/ui/result_card_panel.py 结构钉桩（s920-17）。

锚点复核顺带钉出一条**死分支**：`render_result_card:23` 的 `if card is None:` 今天不可达——
`build_card_from_output`（`src/analysis/result_card.py:62-124`）**任何路径都返回卡片**，
没有专用模板的方法走 `else` 分支：`warnings.append("方法 'x' 暂无专用结果卡模板")` ＋ `_generic_card`，
函数体里没有 `return None`（签名也标的是 `AnalysisResultCard` 而非 `Optional`）。
所以"当前统计方法暂未覆盖结果卡"那条 st.info 只有把 builder 桩成 None 才走得到——
本文件把两种情况分别钉住，让"这条提示到底会不会出现"这件事以后不用再猜。

假 st 只记录不渲染；未实现的方法当场 assert 失败，免得渲染悄悄走了别的路径还测绿。
红线：不判断任何统计量、效应量或显著性结论，只钉"走哪条分支、发哪条提示"。
"""
from contextlib import contextmanager

import pytest

import src.analysis.result_card as rc
import src.ui.result_card_panel as panel
from src.analysis.result_card import AnalysisResultCard


class Rec:
    def __init__(self, log, path="st"):
        self._log = log
        self._path = path
        self.session_state = {}

    def _emit(self, kind, *payload):
        self._log.append((kind, self._path, *payload))

    def markdown(self, body, **k):
        self._emit("markdown", body)

    def code(self, body, **k):
        self._emit("code", body)

    def caption(self, body, **k):
        self._emit("caption", body)

    def success(self, body, **k):
        self._emit("success", body)

    def info(self, body, **k):
        self._emit("info", body)

    def warning(self, body, **k):
        self._emit("warning", body)

    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        self._emit("columns", n)
        return [Rec(self._log, f"{self._path}.col{i}") for i in range(n)]

    @contextmanager
    def expander(self, label, expanded=False, **k):
        self._emit("expander-open", label, expanded)
        yield Rec(self._log, f"{self._path}>exp")
        self._emit("expander-close", label, expanded)

    def download_button(self, label, **k):
        self._emit("download_button", label)
        return False

    def button(self, label, **k):
        self._emit("button", label)
        return False          # 本单不模拟点击

    def __enter__(self):
        return self            # `with cols[0]:` 这类容器用法

    def __exit__(self, *exc):
        return False

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


@pytest.fixture
def log(monkeypatch):
    recs = []
    monkeypatch.setattr(panel, "st", Rec(recs))
    return recs


def _msgs(recs, kind):
    return [r[2] for r in recs if r[0] == kind]


# ---------- 一、builder 的默认解析路径 ----------

def test_builder_falls_back_to_generic_card_instead_of_returning_none():
    """dict 里没有 assumptions / 没有任何已知方法 ⇒ 仍返回卡片，并打上"暂无专用模板"警告。"""
    card = rc.build_card_from_output({})

    assert isinstance(card, AnalysisResultCard)
    assert card.method_id == "unknown"
    assert card.assumptions == [] and card.assumption_status == "not_checked"
    assert any("暂无专用结果卡模板" in w for w in card.warnings)


def test_missing_assumptions_key_yields_not_checked_status():
    """`assumptions` 键缺失与给了空 dict 同路：不编造检查结果。"""
    a = rc.build_card_from_output({"test_type": "independent_ttest"})
    b = rc.build_card_from_output({"test_type": "independent_ttest", "assumptions": {}})

    assert a.assumption_status == b.assumption_status == "not_checked"
    assert a.assumptions == [] and b.assumptions == []


# ---------- 二、面板的两条分支 ----------

def test_render_result_card_renders_content_and_does_not_claim_unsupported(log):
    """真实 builder 下走"有卡片"分支：不出"暂未覆盖"提示，返回卡片本身。"""
    card = panel.render_result_card({"test_type": "independent_ttest"})

    assert card is not None
    assert "💡 当前统计方法暂未覆盖结果卡，后续版本将支持更多方法。" not in _msgs(log, "info")
    assert "### 📊 统计结果卡" in _msgs(log, "markdown")
    assert any("前提假设" in m for m in _msgs(log, "caption") + _msgs(log, "success")
               + _msgs(log, "warning") + _msgs(log, "info")), "假设状态四选一必须有输出"


def test_render_result_card_none_branch_only_fires_when_builder_returns_none(log, monkeypatch):
    """把 builder 桩成 None 才走得到那条 st.info ⇒ 钉住"这是死分支"的实况。

    若哪天有人给 `build_card_from_output` 真加了 None 返回（比如按方法白名单拒绝），
    这条用例仍成立，而上一条会红——那时就该回来改注释而不是删测试。
    """
    monkeypatch.setattr(panel, "build_card_from_output", lambda output: None)

    assert panel.render_result_card({"test_type": "brand_new_method"}) is None
    assert _msgs(log, "info") == ["💡 当前统计方法暂未覆盖结果卡，后续版本将支持更多方法。"]
    assert log[-1][0] == "info" and len(log) == 1, "早退 ⇒ 除这条提示外不该有别的渲染"


# ---------- 三、列表渲染的空早退 ----------

def test_result_cards_list_empty_returns_early(log):
    panel.render_result_cards_list([])

    assert _msgs(log, "info") == ["暂无统计结果卡。"]
    assert len(log) == 1, "早退：不标题、不展开、不重复渲染卡片内容"
    assert "expander-open" not in [r[0] for r in log]


def test_result_cards_list_headers_count_and_expands_each(log):
    cards = [AnalysisResultCard(method_id="t", method_name="独立样本t检验", variables={}, apa_text="APA A"),
             AnalysisResultCard(method_id="f", method_name="单因素ANOVA", variables={}, apa_text="APA B")]

    panel.render_result_cards_list(cards)

    assert "### 已生成 2 张结果卡" in _msgs(log, "markdown")
    opened = _msgs(log, "expander-open")
    assert len(opened) == 2 and opened[0].startswith("独立样本t检验 — APA A")
    assert all(r[3] is False for r in log if r[0] == "expander-open"), "批量列表默认折叠"


def test_builder_has_no_return_none_path():
    """静态证据：`build_card_from_output` 全程不返回 None ⇒ 面板那条 `card is None` 是死分支。

    与上面两条一起构成同一件事的两面：真实调用永不走 info 分支（第 3 条），
    桩成 None 才走（第 4 条），而函数体里根本没有 None 出口（本条）。
    """
    import inspect

    src = inspect.getsource(rc.build_card_from_output)

    assert "return None" not in src
    assert "-> AnalysisResultCard:" in src and "Optional" not in src.split("\n")[0]
    assert "暂无专用结果卡模板" in src, "未覆盖方法走的是 warnings ＋ _generic_card 兜底"
