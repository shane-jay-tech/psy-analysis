"""s922-101 分片迁移哨兵：app.py 片 8（文献与选题）＋片 10（模板中心）。

迁移手法＝函数体逐字节搬入 src/ui/，app.py 只留路由接线（同 `deliverable_center_panel` 范式）。
本文件钉住三件**迁移后才可能退化**的事：

1. app.py 侧两个分支体必须保持「仅 title/路由」的薄度，且不得长回原体；
2. 迁出模块对 session_state 只能**整对象透传**，一旦有人补进按键读写，就会造成
   app.py ↔ src/ui 的跨文件会话读写（路线图「撞车风险位」第 1 条），必须红；
3. 两个文件都不得出现 `st.download_button`——导出门禁测试按 app.py / src/ 分桶对账，
   换桶会假绿或假红。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app.py"
LIT = REPO / "src" / "ui" / "literature_entry_panel.py"
TPL = REPO / "src" / "ui" / "template_center_panel.py"


def _lines(p: Path) -> list[str]:
    raw = p.read_bytes().decode("utf-8")
    return raw.split("\r\n") if "\r\n" in raw else raw.split("\n")


def _branch_body(text: str, key: str) -> list[str]:
    """取顶层 `elif mode == "<key>":` 的分支体（缩进行，遇顶层行即止）。"""
    lines = text.split("\r\n") if "\r\n" in text else text.split("\n")
    hits = [i for i, ln in enumerate(lines)
            if ln.startswith('elif mode == "') and key in ln]
    assert len(hits) == 1, f"app.py 中 {key} 分支应有且仅有 1 处，实得 {len(hits)}"
    i = hits[0]
    body: list[str] = []
    for ln in lines[i + 1:]:
        if ln.strip() == "" or ln.startswith(" "):
            if ln.strip() == "" and body and body[-1] == "":
                break
            body.append(ln)
            continue
        break
    while body and body[-1].strip() == "":
        body.pop()
    return body


class TestSlice8Migration:
    def test_literature_panel_is_importable(self):
        from src.ui.literature_entry_panel import render_literature_entry_panel
        assert callable(render_literature_entry_panel)

    def test_panel_body_lives_in_module_not_app(self):
        app_text = APP.read_text(encoding="utf-8")
        lit_text = LIT.read_text(encoding="utf-8")
        # 原体内的**片 8 独有**特征串：必须已离开 app.py，且确实在新模块里。
        # （`render_advanced_skip_form` 不在此列——app.py:720 数据分析分支也用它，非本片。）
        for marker in ("_tab_funnel", "_get_upstream_v37", "FeedStore as _ReviewFS", "文献审核加载失败"):
            assert marker not in app_text, f"{marker} 仍留在 app.py，片 8 未迁净"
            assert marker in lit_text, f"{marker} 未落入 literature_entry_panel.py"

    def test_slice8_branch_body_is_routing_only(self):
        body = _branch_body(APP.read_text(encoding="utf-8"), "文献与选题")
        assert len(body) <= 6, f"片 8 分支体 {len(body)} 行，超过「仅 title/路由」上限 6 行"
        assert any("literature_entry_panel" in ln for ln in body), "片 8 未接线到新面板"
        assert not any(re.match(r"^\s+(if|elif) mode == ", ln) for ln in body)


class TestSlice10Migration:
    def test_template_page_router_exists(self):
        from src.ui.template_center_panel import render_template_center_page
        assert callable(render_template_center_page)

    def test_template_branch_body_is_routing_only(self):
        body = _branch_body(APP.read_text(encoding="utf-8"), "模板中心")
        assert len(body) <= 6, f"片 10 分支体 {len(body)} 行，超过上限 6 行"
        assert any("render_template_center_page" in ln for ln in body)

    def test_load_failure_fallback_stays_in_app(self):
        """导入兜底只能在调用侧：被兜底的模块无法捕获自己的 ImportError。"""
        app_text = APP.read_text(encoding="utf-8")
        assert 'on_error_display("template_center_load_failed", "error")' in app_text

    def test_title_and_caption_moved_verbatim(self):
        """文案逐字节等价：新模块里的 title/caption 必须与迁移前 app.py 的字面值相同。"""
        lit = TPL.read_text(encoding="utf-8")
        assert 'st.title("🗂️ 研究模板中心")' in lit
        assert "st.caption(" in lit and "从研究模板快速开始新项目" in lit


class TestSessionDependencyCaliber:
    """本片的前提是「零会话键依赖」——这条前提必须被钉住，而不是靠人记。"""

    @staticmethod
    def _code_only(path: Path) -> str:
        """去掉 docstring 后的纯代码文本（本文件的口径说明里也提到 session_state）。"""
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc and node.body and isinstance(node.body[0], ast.Expr):
                    node.body[0].value = ast.Constant(value="")
        return ast.unparse(tree)

    def test_slice8_only_passes_session_state_through(self):
        code = self._code_only(LIT)
        refs = re.findall(r"session_state", code)
        assert len(refs) == 1, f"片 8 会话引用应为 1 处透传，实得 {len(refs)}"
        assert re.search(r"\w+\(st\.session_state\)", code), \
            "片 8 的唯一会话引用必须是「整对象透传给某个函数」的形态"

    @pytest.mark.parametrize("path,fn", [(LIT, None), (TPL, "render_template_center_page")],
                             ids=["literature-module", "template-page-fn"])
    def test_no_key_level_session_access_introduced(self, path: Path, fn):
        """禁止 `st.session_state["x"]` / `.get("x")` / `.pop(` 这类按键读写。

        片 10 只检查**本次迁入的函数**：`template_center_panel.py` 原有的面板函数
        本来就持有 `template_created_project` 等键，那是存量、不是本片带来的耦合。
        """
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        if fn is None:
            code = self._code_only(path)
        else:
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
            code = ast.unparse(node)
        offenders = re.findall(
            r"""session_state\s*(?:\[\s*["']|\.get\(\s*["']|\.pop\(\s*["']|\.setdefault\(\s*["'])""",
            code,
        )
        assert not offenders, f"{path.name}::{fn or '<module>'} 出现按键读写 {offenders}：会造成跨文件会话耦合"

    @pytest.mark.parametrize("path,fn", [(LIT, None), (TPL, "render_template_center_page")],
                             ids=["literature-module", "template-page-fn"])
    def test_no_download_button_bucket_change(self, path: Path, fn):
        """导出门禁按 app.py / src/ 分桶，迁入件不得带 download_button 换桶。"""
        import ast

        if fn is None:
            text = path.read_text(encoding="utf-8")
        else:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
            text = ast.unparse(node)
        assert "download_button" not in text


class TestRenderSequence:
    """把行为等价比对里最有价值的一条留成常驻回归：widget 创建顺序不得变。"""

    def test_tab_and_panel_order(self, monkeypatch):
        import types

        log = []

        class Tab:
            def __init__(self, label):
                self.label = label

            def __enter__(self):
                log.append(("tab:enter", self.label))
                return self

            def __exit__(self, *a):
                log.append(("tab:exit", self.label))
                return False

        st = types.ModuleType("streamlit")
        st.session_state = {}
        st.title = lambda *a, **k: log.append(("title",) + a)
        st.error = lambda *a, **k: log.append(("error",) + a)
        st.tabs = lambda labels: (log.append(("tabs", tuple(labels))),
                                  [Tab(x) for x in labels])[1]

        ws = types.ModuleType("src.utils.workspace")
        ws.get_upstream_state = lambda ss: (log.append(("get_upstream_state",)), {"tier": "beginner"})[1]
        up = types.ModuleType("src.ui.upstream_panel")
        up.render_funnel = lambda: log.append(("render_funnel",))
        up.render_advanced_skip_form = lambda: log.append(("render_advanced_skip_form",))
        lr = types.ModuleType("src.ui.literature_review_panel")
        lr.render_literature_review = lambda tier=None: log.append(("render_literature_review", tier))
        feed = types.ModuleType("src.literature_feed.ui")
        feed.render_literature_feed = lambda: log.append(("render_literature_feed",))
        fs = types.ModuleType("src.literature_feed.storage.feed_store")
        fs.FeedStore = lambda: "REVIEW_STORE"
        rq = types.ModuleType("src.ui.literature_review_queue_panel")
        rq.render_review_queue = lambda store: log.append(("render_review_queue", store))

        for name, mod in {
            "streamlit": st,
            "src.utils.workspace": ws,
            "src.ui.upstream_panel": up,
            "src.ui.literature_review_panel": lr,
            "src.literature_feed.ui": feed,
            "src.literature_feed.storage.feed_store": fs,
            "src.ui.literature_review_queue_panel": rq,
        }.items():
            monkeypatch.setitem(__import__("sys").modules, name, mod)

        import importlib

        import src.ui.literature_entry_panel as panel
        importlib.reload(panel)
        try:
            panel.render_literature_entry_panel()
        finally:
            importlib.reload(panel)

        assert log == [
            ("title", "📚 文献与选题"),
            ("tabs", ("选题与综述", "文献雷达", "文献审核")),
            ("tab:enter", "选题与综述"),
            ("get_upstream_state",),
            ("tabs", ("选题漏斗", "文献综述工作台")),
            ("tab:enter", "选题漏斗"),
            ("render_funnel",),
            ("tab:exit", "选题漏斗"),
            ("tab:enter", "文献综述工作台"),
            ("render_literature_review", "beginner"),
            ("tab:exit", "文献综述工作台"),
            ("tab:exit", "选题与综述"),
            ("tab:enter", "文献雷达"),
            ("render_literature_feed",),
            ("tab:exit", "文献雷达"),
            ("tab:enter", "文献审核"),
            ("render_review_queue", "REVIEW_STORE"),
            ("tab:exit", "文献审核"),
        ]
