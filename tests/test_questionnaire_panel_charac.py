# -*- coding: utf-8 -*-
"""src/ui/questionnaire_panel.py 分支头＋重入骨架钉桩（s920-10）。

按 `docs/insights/psy-questionnaire-panel-testdesign-20260918.md` 的口径做 B 类（假 st）与骨架普查，
**不做设计稿第 4 节的结构性抽取**（那是日间拍板的事）。

锚点复核（相对设计稿有一处漂移，按磁盘实况钉）：
- 设计稿 `st.rerun()` 记 **9 处**，磁盘实况 **8 处**（见 test_rerun_*）；`st.stop()` 仍 3 处（s920-10 时为 :43/:47/:517；s921-06/07 抽取后 :67/:71/:544；s922-02 加 anomaly 判据后 :80/:84/:564；s922-138 反向刷齐后 :81/:85/:576；s922-139 premium 补 anomaly 警示后 :81/:85/:583；s924-37 警示文案提模块常量后 :90/:94/:586）。
- 本页确实零测试：`tests/test_app_routes_v6_panels.py:62` 那个同名用例 import 的是
  `src.ui.questionnaire_import_panel`（别的模块），不是本页。

假 `st` 的 `stop()` **抛异常**——真实 `st.stop()` 就是抛 `StopException` 结束脚本，
返回的话等于把"提前终止"钉成了"继续往下跑"。

s924-42 批一下沉：B 组普查里"写死源码第几行"的位置桩已降级为语义桩——判据原文照旧逐字钉，
但行号由 AST 现取；体量／计数型期望值（函数跨度行数、文件总行数、`st.rerun()` 等出现次数）
不是位置锚，留作续批（原因见 result）。
"""
import ast
import inspect
import pathlib

import pytest

import src.ui.items_upload_panel as iup
import src.ui.questionnaire_import_panel as qip
import src.ui.questionnaire_panel as qp


class PageStopped(BaseException):
    """建模真实 `st.stop()`：它抛 `StopException`，基类是 **`BaseException`**
    （`streamlit/runtime/scriptrunner_utils/exceptions.py:22`）⇒ 业务侧 `except Exception` 吞不掉。
    假 st 的 stop 只返回等于把"提前终止"钉成"继续往下跑"。"""


class StrictSt:
    """只够跑分支头的假 st：多调一个方法就当场红。"""

    def __init__(self, radio_value, state=None):
        self.session_state = state if state is not None else {}
        self.radio_value = radio_value
        self.titles, self.captions = [], []
        self.radios, self.stops = [], 0
        self.anything_else = []

    def title(self, msg, **k):
        self.titles.append(msg)

    def caption(self, msg, **k):
        self.captions.append(msg)

    def radio(self, label, options, **k):
        self.radios.append((label, list(options), k))
        return self.radio_value

    def stop(self, **k):
        self.stops += 1
        raise PageStopped()

    def __getattr__(self, name):
        self.anything_else.append(name)
        raise AssertionError(f"分支头之后不该再碰 st.{name}（st.stop 没生效？）")


@pytest.fixture
def page(monkeypatch):
    """把两个外部子面板换成记录桩；返回 (记录本, 装 radio 值的工厂)。"""
    seen = {"upload": 0, "import": 0, "import_arg": None}

    def fake_upload():
        seen["upload"] += 1

    def fake_import(state):
        seen["import"] += 1
        seen["import_arg"] = state

    monkeypatch.setattr(iup, "render_items_upload_panel", fake_upload)
    monkeypatch.setattr(qip, "render_questionnaire_import_panel", fake_import)
    return seen, monkeypatch


def _run(st):
    qp.render_questionnaire_page()


# ─────────────────────────── A. 分支头（假 st） ───────────────────────────
def test_upload_branch_hands_off_to_items_panel_and_stops(page):
    seen, monkeypatch = page
    st = StrictSt("📤 上传现有题目（预审 + 排版导出）")
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(PageStopped):
        _run(st)

    assert seen["upload"] == 1 and seen["import"] == 0
    assert st.stops == 1
    assert st.titles == ["📋 问卷设计工具"]              # 只有页头，主页其余部分一帧都没渲染
    assert st.radios[0][1] == ["🆕 AI 设计新问卷", "📤 上传现有题目（预审 + 排版导出）", "📊 问卷数据导入与清洗"]
    assert st.radios[0][2]["key"] == "_q_sub_mode_radio" and st.radios[0][2]["horizontal"] is True


def test_import_branch_receives_the_live_session_state(page):
    seen, monkeypatch = page
    state = {"language": "zh"}
    st = StrictSt("📊 问卷数据导入与清洗", state=state)
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(PageStopped):
        _run(st)

    assert seen["import"] == 1 and seen["upload"] == 0
    assert seen["import_arg"] is state                   # 传的是**同一个** session_state 对象，不是副本
    assert st.stops == 1


def test_ai_design_branch_falls_through_without_stopping(page):
    seen, monkeypatch = page
    st = StrictSt("🆕 AI 设计新问卷")
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(AssertionError) as exc:          # 主页继续 ⇒ 撞到假 st 的未预期调用
        _run(st)

    assert "st.sidebar" in str(exc.value)               # 第一个未预期调用就是侧栏 ⇒ 确实往下走了
    assert seen["upload"] == 0 and seen["import"] == 0 and st.stops == 0


def test_branch_dispatch_is_emoji_prefix_only_so_label_edits_silently_fall_through(page):
    """现状风险钉桩：判据是 `startswith("📤")`。文案丢表情 ⇒ **不转交、悄悄回到 AI 设计页**。只钉不改。"""
    seen, monkeypatch = page
    for label in ("上传现有题目（预审 + 排版导出）", "", "📥 上传现有题目"):
        st = StrictSt(label)
        monkeypatch.setattr(qp, "st", st)
        with pytest.raises(AssertionError):
            _run(st)
        assert seen["upload"] == 0 and st.stops == 0


def test_sub_mode_radio_is_rendered_before_any_side_effect(page):
    """顺序契约：radio 必须先于转交（否则切换工作流要点两次）。"""
    _, monkeypatch = page
    st = StrictSt("📤 上传现有题目（预审 + 排版导出）")
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(PageStopped):
        _run(st)

    assert st.captions and st.radios and len(st.radios) == 1  # 页头两条文案＋一次 radio，然后立刻转交


# ─────────────────────── B. 重入骨架（源码普查） ───────────────────────
SRC = pathlib.Path(inspect.getsourcefile(qp))
BODY = SRC.read_text(encoding="utf-8")
TREE = ast.parse(BODY)
PARENT = {c: p for p in ast.walk(TREE) for c in ast.iter_child_nodes(p)}


# ── 语义定位工具（s924-42 批一）：一律按 AST 归属找人，不许写死行号 ──
def _src_line(node):
    """节点起始行的逐字原文——行号由 AST 给出，判据原文仍逐字比对。"""
    return BODY.splitlines()[node.lineno - 1]


def _top_func(name):
    """按名字定位顶层函数（不唯一即当场红）。"""
    hits = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(hits) == 1, f"顶层函数 {name} 应恰好 1 个，实得 {len(hits)} 个"
    return hits[0]


def _first_stmt(fn):
    """函数体里第一条真语句（跳过 docstring）。"""
    body = [s for s in fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    assert body, f"{fn.name} 体内没有任何语句"
    return body[0]


def _sole_assign(fn, var):
    """函数体内对该变量的**唯一**顶层赋值语句（0 条或多条都当场红）。"""
    hits = [s for s in fn.body if isinstance(s, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == var for t in s.targets)]
    assert len(hits) == 1, f"{fn.name} 体内对 {var} 的赋值应恰好 1 处，实得 {len(hits)} 处"
    return hits[0]


def _dispatch_chain():
    """页面里那条 `_q_sub_class` 分派链的头部 `if`（判别调用的下一条语句）。"""
    page = _top_func("render_questionnaire_page")
    cls = _sole_assign(page, "_q_sub_class")
    nxt = page.body[page.body.index(cls) + 1]
    assert isinstance(nxt, ast.If), "判别调用之后紧跟的不是 if 分派链"
    return nxt


def _enclosing_body(stmt):
    """返回 (包含该语句的语句列表, 它在下标几)。"""
    p = PARENT.get(stmt)
    while p is not None:
        for _, val in ast.iter_fields(p):
            if isinstance(val, list):
                for i, item in enumerate(val):
                    if item is stmt:
                        return val, i
        p = PARENT.get(p)
    raise AssertionError("该语句不属于任何语句块（不该发生）")


def _prev_stmt(stmt):
    """同一语句块里紧邻的前一条语句——没有前一条即红（钉"转交完立刻收尾"这类次序）。"""
    body, i = _enclosing_body(stmt)
    assert i >= 1, "该语句是块内第一条，身前没有可钉的语句"
    return body[i - 1]


def _call_name(stmt):
    """把一条表达式语句归一成被调名：`st.stop` / `render_items_upload_panel`；非调用给出类型名。"""
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        f = stmt.value.func
        if isinstance(f, ast.Attribute):
            return f"{f.value.id}.{f.attr}" if isinstance(f.value, ast.Name) else f.attr
        if isinstance(f, ast.Name):
            return f.id
        return ast.unparse(f)
    return type(stmt).__name__


def _stop_calls():
    """源码里所有 `st.stop()` 调用所属的语句，按源码先后排序。"""
    out = []
    for node in ast.walk(TREE):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "stop"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "st"):
            stmt = node
            while not isinstance(stmt, ast.stmt):
                stmt = PARENT[stmt]
            out.append(stmt)
    return sorted(out, key=lambda s: s.lineno)


def _in_subtree(node, root):
    return any(c is node for c in ast.walk(root))


def _stmt_depth(stmt):
    """该语句嵌在多少层语句里（分支头浅、报告深处深）。"""
    d, p = 0, PARENT.get(stmt)
    while p is not None:
        if isinstance(p, ast.stmt):
            d += 1
        p = PARENT.get(p)
    return d


def _call_names(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            yield sub.func.value, sub.func.attr


def test_page_is_still_one_monster_function():
    """抽取一旦发生，本用例红——那是好事，届时把普查数一起改掉（设计稿第 4 节的三个签名）。
    s921-06 已抽 classify_questionnaire_sub_mode ⇒ 按注释同步普查数。

    s924-42 批一：页面函数原来按"写死的起始行号"定位，现改为结构判据——它是模块的**最后一个
    顶层节点**（其后挂任何顶层语句即红），且顶层赋值恰好只有异常警示文案那一枚。
    函数跨度行数是体量桩（防无界膨胀）不是位置锚，本批按原样保留。"""
    tree = ast.parse(BODY)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]

    assert [f.name for f in funcs] == ["classify_questionnaire_sub_mode", "compute_pending_elapsed", "pending_clock_anomaly", "render_questionnaire_page"]
    assert [c.name for c in classes] == ["_DummyContext"]
    fn = funcs[-1]
    assert fn is tree.body[-1]                                   # 页面函数之后不许再有顶层语句
    consts = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert [ast.unparse(c.targets[0]) for c in consts] == ["CLOCK_ANOMALY_WARNING_TEXT"]
    # s921-07 后 51/767；s922-02 加 pending_clock_anomaly 后 64/774；
    # s922-138 反向刷齐（顶部 import html 占 1 行＋三处渲染/下载面按 app.py 加长）后 65/807；
    # s922-139 premium 分支补 anomaly 警示（+7 行）后 65/814；
    # s924-37 警示文案提模块常量（页面外 +9，页面内两处 4 行各收成 1 行 ⇒ −6）后 74/808
    assert (fn.end_lineno - fn.lineno + 1) == 808



def test_reentry_is_all_via_rerun_with_zero_callbacks():
    """本页没有交互回调，全部交互靠 `st.rerun()` 重入 ⇒ 加回调属于骨架换范式，须先过这条。

    s922-138 刷齐后**收紧**（非放宽）：app.py 生产版的三枚 `st.download_button` 带
    `on_click="ignore"`——它不是回调，恰是「点下载不重入」的声明。原断言按字面
    （`"on_click" not in BODY`）会把这条生产事实判成违规，故改为逐字钉「只允许
    `on_click="ignore"` 且恰好 3 枚」：任何 `on_change=` 或第四种 on_click 写法仍当场红。
    """
    reruns = BODY.count("st.rerun()")
    stops = BODY.count("st.stop()")

    assert reruns == 8                                   # 设计稿记 9，磁盘实况 8（已留痕）
    assert stops == 3
    assert BODY.count('on_click="ignore"') == 3           # app.py 生产版同数：只此三枚下载按钮
    assert BODY.count("on_click") == 3                    # 无第四种 on_click 写法混入
    assert "on_change" not in BODY


def test_stop_sites_are_the_two_branch_heads_plus_one_deep_in_report():
    """三处 `st.stop()` 的**身份**：分派链里的两个转交头（身前紧邻对应子面板的渲染调用）
    ＋ 报告深处的一处「没有激活的 AI 模型」守卫（身前紧邻 `st.error`）。

    s924-42 批一：原来逐字钉三处的行号三元组，现按 AST 归属钉——"两枚在分派链内、一枚在链外
    且更深"这条关系照旧成立才绿，把任一 stop 挪出转交头或删掉错误提示都会当场红。
    历史三元组值不再重复留档，见件头 docstring 的刷齐史索引（s920-10 → s924-37 全链）。"""
    stops = _stop_calls()
    assert len(stops) == 3                                       # 与 test_reentry_* 的字面计数同源
    dispatch = _dispatch_chain()
    heads = [s for s in stops if _in_subtree(s, dispatch)]
    deep = [s for s in stops if not _in_subtree(s, dispatch)]
    assert len(heads) == 2 and len(deep) == 1
    assert [_call_name(_prev_stmt(s)) for s in heads] == [
        "render_items_upload_panel", "render_questionnaire_import_panel"]   # 源码先后即分支先后
    assert [_call_name(_prev_stmt(s)) for s in deep] == ["st.error"]
    assert _stmt_depth(deep[0]) > max(_stmt_depth(s) for s in heads)   # 报告那一枚确实更深



def test_session_state_touches_are_20_and_three_keys_dominate():
    """20 处 `st.session_state.` 引用（设计稿口径），其中 language/questionnaire_design/_q_design_pending 是主写键。"""
    n = sum(1 for _ in BODY.splitlines() if "st.session_state" in _)

    assert len(BODY.splitlines()) == 881                 # s921-06 后 805；s921-07 后 817；s922-02 加 anomaly 与负秒钉后 837；s922-138 反向刷齐后 871；s922-139 premium 分支补 anomaly 警示后 878；s924-37 常量化（模块常量 +9、两调用点各 4 行收成 1 行 −6）后 881
    assert BODY.count("st.session_state.") >= 20
    for key in ("language", "questionnaire_design", "_q_design_pending", "_q_premium_mode"):
        assert key in BODY


def test_branch_head_prefixes_live_on_the_expected_lines():
    """s921-06 抽取后翻正：页面判据行变成对纯函数的调用（钉调用原文），emoji 前缀串比较原文
    整体搬进 classify 体内（钉函数体原文）——两处判据仍**逐字**在钉。

    s924-42 批一：判据原文所在的那一行改由 AST 现取（`_src_line`），不再写死它是文件第几行；
    原先"靠相邻行号才成立"的关系显式钉住：radio 赋值 ⇒ 紧跟判别调用 ⇒ 紧跟分派 if，
    以及 `import_clean` 那一支是**同级 elif**（不是塞进 else 的嵌套 if，靠缩进列相等钉）。"""
    page = _top_func("render_questionnaire_page")
    cf = _top_func("classify_questionnaire_sub_mode")
    dispatch = _dispatch_chain()

    # 页面侧：判别调用紧跟 radio，分派 if 紧跟判别调用
    radio = _sole_assign(page, "_q_sub_mode")
    cls = _sole_assign(page, "_q_sub_class")
    assert page.body.index(cls) == page.body.index(radio) + 1
    assert _src_line(cls) == "    _q_sub_class = classify_questionnaire_sub_mode(_q_sub_mode)"
    assert _src_line(dispatch).strip() == 'if _q_sub_class == "upload_items":'
    assert len(dispatch.orelse) == 1 and isinstance(dispatch.orelse[0], ast.If)
    elif_import = dispatch.orelse[0]
    assert elif_import.col_offset == dispatch.col_offset
    assert _src_line(elif_import).strip() == 'elif _q_sub_class == "import_clean":'

    # classify 体内：两条 emoji 前缀判据原文逐字在钉，同样是同级 elif
    head = _first_stmt(cf)
    assert isinstance(head, ast.If)
    assert _src_line(head).strip() == 'if choice.startswith("📤"):'
    assert len(head.orelse) == 1 and isinstance(head.orelse[0], ast.If)
    assert head.orelse[0].col_offset == head.col_offset
    assert _src_line(head.orelse[0]).strip() == 'elif choice.startswith("📊"):'

