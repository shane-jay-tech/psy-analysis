# -*- coding: utf-8 -*-
"""纯函数单测（零 st、秒级）：classify_questionnaire_sub_mode（s921-06，设计稿 §4.1「测点」）
+ compute_pending_elapsed 边界例（s921-07，设计稿 §4.2）
+ 反向刷齐后的 HTML 转义／下载文件名消毒分支（s922-138，源出 app.py 内联块）。
页面侧行为等价性由 test_questionnaire_panel_charac.py 的分支头五例继续把关。
"""
import ast
import inspect

import pytest

import src.ui.questionnaire_panel as qp
from src.ui.questionnaire_panel import classify_questionnaire_sub_mode

UPLOAD_LABEL = "📤 上传现有题目（预审 + 排版导出）"
IMPORT_LABEL = "📊 问卷数据导入与清洗"
AI_LABEL = "🆕 AI 设计新问卷"


# ── compute_pending_elapsed（s921-07 计时面实装，边界例：缺失/正常/跨日）──
def test_pending_elapsed_missing_started_at_returns_none():
    """started_at 缺失（None 或 0）→ None，页面显示「—」——不再恒 0。"""
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(None, 1000.0) is None
    assert compute_pending_elapsed(0, 1000.0) is None


def test_pending_elapsed_normal_diff_is_int_seconds():
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(1000.0, 1042.7) == 42
    assert compute_pending_elapsed(1000.0, 1000.4) == 0      # 刚起步仍是真 0，不是兜底假 0


def test_pending_elapsed_cross_day_counts_full_seconds():
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(1_000_000.0, 1_000_000.0 + 90_000) == 90_000  # 跨日 25h


def test_pending_elapsed_future_started_at_clamps_to_zero_not_negative():
    """s922-02（s921-07 遗留 1）：started_at 在未来（时钟回拨/跨机时差）⇒ 钳 0，负秒不外泄。"""
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(2000.0, 1000.0) == 0     # 回拨 1000s：旧实现给 -1000
    assert compute_pending_elapsed(1000.5, 1000.4) == 0     # 亚秒级未来
    assert compute_pending_elapsed(None, 1000.0) is None    # 缺失仍是 None（不被钳成 0，两态可分）
    assert compute_pending_elapsed(1000.0, 1000.4) == 0     # 真 0 与钳 0 同值 ⇒ 需 anomaly 判据区分


def test_pending_elapsed_clock_anomaly_is_the_only_negative_source():
    """判据域：True ⇔ started_at 严格晚于 now；缺失/为 0 归「耗时未知」而非「时钟异常」。"""
    from src.ui.questionnaire_panel import pending_clock_anomaly
    assert pending_clock_anomaly(2000.0, 1000.0) is True
    assert pending_clock_anomaly(1000.0, 2000.0) is False
    assert pending_clock_anomaly(1000.0, 1000.0) is False   # 恰等不算异常（< 而非 <=）
    assert pending_clock_anomaly(None, 1000.0) is False
    assert pending_clock_anomaly(0, 1000.0) is False


@pytest.mark.parametrize("started_at,now", [
    (2000.0, 1000.0), (1e9, 0.0), (1000.5, 1000.4),        # 异常族
    (1000.0, 1000.4), (1000.0, 1000.0), (900.0, 1000.0),   # 正常族（含真 0）
])
def test_pending_elapsed_anomaly_true_always_pairs_with_clamped_zero(started_at, now):
    """两函数同源于同一 now 的不变式：判异常 ⇒ 秒必为钳后的 0；不判异常 ⇒ 秒就是真差值。"""
    from src.ui.questionnaire_panel import compute_pending_elapsed, pending_clock_anomaly
    e = compute_pending_elapsed(started_at, now)
    assert e is not None and e >= 0                         # 钳 0 后全谱非负
    if pending_clock_anomaly(started_at, now):
        assert e == 0
    else:
        assert e == int(now - started_at)                   # 未回拨时钳位不改值（真 0 仍是真 0）


def test_pending_elapsed_page_puts_the_clock_anomaly_branch_before_the_under_30_branch():
    """s921-07 遗留原文的病就是「负秒落进 <30 正常文案」——分支次序与单一 now 就是病灶，源码次序钉住。

    只钉次序不钉渲染：页面级 pending 渲染目前无假 st 覆盖（charac 的 StrictSt 只够跑分支头），
    次序一被调换（把 clock_anomaly 挪到 <30 之后）或 now 被拆成两次 time.time() 本例立刻红。
    """
    import inspect
    import src.ui.questionnaire_panel as qp
    src = inspect.getsource(qp.render_questionnaire_page)
    body = src.split(chr(10))

    def first(snip, after=0):
        hits = [i for i, ln in enumerate(body) if snip in ln and i >= after]
        assert hits, snip
        return hits[0]

    assert first("elapsed_txt =") > first("clock_anomaly =") > first("_now = _t.time()")
    # s922-139 起警示出现在**两处**（premium 分支内一处 ＋ 兜底链一处）；s924-37 常量化后两处
    # 都只写常量名，字面量整体搬进模块常量 ⇒ 次序钉改钉调用点原文。
    # 次序钉的是兜底链那一处 ⇒ 从自己的分支头往后找，顺带把「警示紧跟分支头」也钉住。
    anomaly_head = first("elif clock_anomaly:")
    chain = ["elif elapsed is None:", "elif clock_anomaly:", "elif elapsed < 30:"]
    assert [first(c) for c in chain] == sorted([first(c) for c in chain])
    assert anomaly_head < first("st.warning(CLOCK_ANOMALY_WARNING_TEXT)", after=anomaly_head) \
        < first("elif elapsed < 30:")
    assert first("elif clock_anomaly:") < first("elif elapsed < 30:")
    assert src.count("_now = _t.time()") == 1                       # 单一时钟读数，两判据同源
    assert "compute_pending_elapsed(started_at, _t.time())" not in src   # 旧的一次性读数写法已消失



def test_three_real_labels_map_to_their_branches():
    assert classify_questionnaire_sub_mode(AI_LABEL) == "ai_design"
    assert classify_questionnaire_sub_mode(UPLOAD_LABEL) == "upload_items"
    assert classify_questionnaire_sub_mode(IMPORT_LABEL) == "import_clean"


def test_empty_string_falls_through_to_ai_design():
    assert classify_questionnaire_sub_mode("") == "ai_design"


@pytest.mark.parametrize("choice", [
    "📤 上传现有题目（预审 + 排版导出）",   # 全串原样
    "📤上传现有题目（预审 + 排版导出）",     # 丢 emoji 后空格 ⇒ 前缀仍命中
    "📤",                                     # 只有前缀
])
def test_upload_prefix_is_matched_prefix_only(choice):
    assert classify_questionnaire_sub_mode(choice) == "upload_items"


@pytest.mark.parametrize("choice", [
    "📊 问卷数据导入与清洗",
    "📊问卷数据导入与清洗",
    "📊",
])
def test_import_prefix_is_matched_prefix_only(choice):
    assert classify_questionnaire_sub_mode(choice) == "import_clean"


@pytest.mark.parametrize("choice", [
    " 📤 上传现有题目（预审 + 排版导出）",    # 前导空格 ⇒ startswith 失效
    "📥 上传现有题目（预审 + 排版导出）",    # emoji 变体 ⇒ 静默改道
    "上传现有题目（预审 + 排版导出）",        # 丢 emoji ⇒ 静默改道
    "🆕 AI 设计新问卷 ",                       # 尾部空格仍是 AI 分支
    "random text",
])
def test_label_perturbations_fall_through_silently_to_ai_design(choice):
    """现状风险（设计稿 §4.1）：判据只认 emoji 前缀，任何文案扰动都悄悄回到 AI 设计页。"""
    assert classify_questionnaire_sub_mode(choice) == "ai_design"


def test_return_domain_is_exactly_the_three_branches():
    outs = set()
    corpus = [AI_LABEL, UPLOAD_LABEL, IMPORT_LABEL, "", "x", " 📤 a", "📊", "📥"]
    for c in corpus:
        outs.add(classify_questionnaire_sub_mode(c))
    assert outs <= {"ai_design", "upload_items", "import_clean"}


@pytest.mark.parametrize("choice", [
    AI_LABEL, UPLOAD_LABEL, IMPORT_LABEL, "", " 📤", "📥 x", "📊b", "🆕", "  ", "📤📊"
])
def test_parity_with_old_inline_predicate(choice):
    """与抽取前的内联 if/elif（startswith 📤 → 上传；elif startswith 📊 → 导入；否则 AI）逐串对拍。"""
    if choice.startswith("📤"):
        expected = "upload_items"
    elif choice.startswith("📊"):
        expected = "import_clean"
    else:
        expected = "ai_design"
    assert classify_questionnaire_sub_mode(choice) == expected


# ══════════════ s922-138 反向刷齐：转义面 ＋ 下载文件名消毒面 ══════════════
# 这些断言全部写成「取模块源码 → AST 定位」的纯函数形态，故同一组函数既可喂刷齐后的
# questionnaire_panel（应绿），也可喂刷齐前的旧源码（必红）——改前红的取证见
# zcode-bridge/outbox/s922-138-qpanel-backfill-16.result.md。

def _module_source() -> str:
    return inspect.getsource(qp)


def _render_body(source: str) -> str:
    """取 render_questionnaire_page 的源码段（顶层 def ⇒ get_source_segment 结果可直接再 parse）。"""
    fn = next(n for n in ast.parse(source).body
              if isinstance(n, ast.FunctionDef) and n.name == "render_questionnaire_page")
    seg = ast.get_source_segment(source, fn)
    assert seg, "render_questionnaire_page 源码段取不到"
    return seg


def _fstrings_containing(source: str, needle: str):
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.JoinedStr):
            lit = "".join(v.value for v in node.values
                          if isinstance(v, ast.Constant) and isinstance(v.value, str))
            if needle in lit:
                out.append(node)
    return out


def _names_in(node):
    return {sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name)}


# ── 1. 三处 HTML 注入面：研究理解卡 / 技术参数卡，只允许插已转义的量 ──
ESCAPED_RESEARCH_VARS = {
    "_safe_rt_label", "_safe_object", "_safe_population", "_safe_role",
    "_safe_subject", "_safe_framework_line", "_safe_summary",
}


def test_research_understanding_card_interpolates_only_escaped_vars():
    """app.py 版把 rp 的五个字段＋summary＋theoretical_framework 全过 html.escape 再进
    unsafe_allow_html 的 <b> 里；panel 旧副本是原样直插（= 可注入）。s922-138 刷齐后必须只剩转义量。"""
    body = _render_body(_module_source())
    hits = _fstrings_containing(body, "研究层次：")

    assert len(hits) == 1, "研究理解卡的 f-string 应唯一（多一份说明文案要一起看）"
    free = _names_in(hits[0])
    assert free == ESCAPED_RESEARCH_VARS, f"卡面出现未转义/意外的插值：{sorted(free ^ ESCAPED_RESEARCH_VARS)}"


def test_tech_metric_card_interpolates_only_escaped_vars():
    body = _render_body(_module_source())
    hits = _fstrings_containing(body, "font-size:0.85em")

    assert len(hits) == 1
    assert _names_in(hits[0]) == {"_safe_label", "_safe_value"}


def test_escape_call_sites_count_is_nine_and_module_imports_html():
    """七连（研究理解卡：rt_label/object/population/role/subject/summary/framework）
    ＋两连（技术参数卡：label/value）= 9 处 html.escape；缺 `import html` 会当场 NameError。"""
    source = _module_source()

    assert source.count("html.escape(") == 9
    assert "import html" in source.splitlines()[:20]
    assert _render_body(source).count("html.escape(") == 9      # 全部 9 处都在页面体内


# ── 2. 下载文件名消毒：把 panel 里**那两条赋值**原样取出来跑，不复制实现 ──
def _stem_from_panel_source(source: str, raw):
    import textwrap

    body = _render_body(source)
    tree = ast.parse(body)
    stmts = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            stmts[n.targets[0].id] = textwrap.dedent(ast.get_source_segment(body, n))
    missing = {"_construct_name", "_safe_stem"} - set(stmts)
    assert not missing, f"panel 里找不到消毒赋值语句：{sorted(missing)}"

    ns = {"design": {"construct_name": raw}}
    exec(compile("\n".join([stmts["_construct_name"], stmts["_safe_stem"]]),
                 "<questionnaire_panel._safe_stem>", "exec"), ns)
    return ns["_safe_stem"]


@pytest.mark.parametrize("raw, expect", [
    ("组织承诺（v2）_final-1.0", "组织承诺（v2）_final-1.0"),   # 白名单字符逐字保留
    ("Work Engagement 2.0", "WorkEngagement2.0"),               # 空格被剥（不是白名单）
    ("a" * 100, "a" * 60),                                      # 截断到 60
    ("🔥🔥", "问卷"),                                            # 全被剥 ⇒ 兜底
    ("", "问卷"),                                               # falsy ⇒ 兜底（走 str(or) 那一层）
    (None, "问卷"),                                             # 缺键/None ⇒ 兜底
    (123, "123"),                                               # 非串也先 str() 再判
])
def test_download_stem_whitelist_and_fallback_branches(raw, expect):
    assert _stem_from_panel_source(_module_source(), raw) == expect


@pytest.mark.parametrize("raw", [
    "../../windows/win.ini",
    "报告\\..\\secret",
    "C:/Windows/system32",
    '<script>alert("x")</script>',
    "报告|whoami",
    "a\nb\tc",
])
def test_download_stem_kills_path_separators_and_markup(raw):
    """文件名消毒的正题：路径分隔符/重定向符/尖括号一律不能活到 file_name 里。"""
    stem = _stem_from_panel_source(_module_source(), raw)

    assert stem
    for ch in '/\\<>|:;\'"`\n\t':
        assert ch not in stem, f"危险字符 {ch!r} 残留于 {stem!r}"
    assert stem == stem[:60]


# ── 3. base64 data-href 老写法整体退场，换回 st.download_button ──
def test_legacy_base64_data_href_links_are_gone():
    """旧副本用 `st.markdown(href, unsafe_allow_html=True)` 把 construct_name 拼进 download 属性
    ——既是注入面又是整份报告进 DOM 的体积炸弹。刷齐后这些原文必须零残留。"""
    source = _module_source()

    for gone in ("import base64", "b64", "data:application", "data:text/html",
                 "full_report.replace(chr(10)", "download=\"{design["):
        assert gone not in source, f"旧写法残留：{gone}"


def test_three_download_buttons_use_sanitized_stem_and_html_safety():
    body = _render_body(_module_source())

    assert body.count("st.download_button(") == 3
    assert body.count("_safe_stem") == 4                        # 1 定义 + 3 处 file_name
    assert body.count("questionnaire_report_to_html_fragment") == 2   # import + 调用
    assert body.count('on_click="ignore"') == 3
    assert body.count("mime=") == 3
    for suffix, mime in ((".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                         (".pdf", "application/pdf"),
                         (".html", "text/html")):
        assert f'file_name=f"{{_safe_stem}}问卷设计报告{suffix}"' in body
        assert f'mime="{mime}"' in body


def test_html_report_body_comes_from_the_shared_escape_helper():
    """下载件 HTML 在本地浏览器打开 ⇒ 报告正文必须走 src.ui.html_safety 的统一转义，
    不再是 `\\n→<br>` 那种链式 replace。"""
    body = _render_body(_module_source())

    assert "from src.ui.html_safety import questionnaire_report_to_html_fragment" in body
    assert "_safe_report = questionnaire_report_to_html_fragment(full_report)" in body
    assert "{_safe_report}" in body
    assert "html = f\"\"\"<html>" not in body                    # 不再用 `html` 当局部量（遮蔽模块名）


# ═════════ s922-139：Premium 生成链也要报「时钟异常」（s922-02 遗留面） ═════════
def _premium_branch_lines(source: str):
    """取 `elif is_premium:` 的分支体（到下一个平级 elif／else 为止），纯函数便于喂改前源码。"""
    body = _render_body(source)
    lines = body.splitlines()
    indent_of = lambda ln: len(ln) - len(ln.lstrip())
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "elif is_premium:")
    end = next(i for i in range(start + 1, len(lines))
               if lines[i].strip() and indent_of(lines[i]) <= indent_of(lines[start]))

    return lines[start + 1:end]


def test_premium_branch_carries_the_clock_anomaly_warning_right_after_its_heading():
    """分支选择断言：警示必须落在 **premium 分支体内**（否则等于没接），
    且顺序是「标题 → 警示 → 进度条」，并且不能把 >90 那档顶掉。"""
    seg = _premium_branch_lines(_module_source())
    hits = [i for i, ln in enumerate(seg) if ln.strip() == "if clock_anomaly:"]
    heads = [i for i, ln in enumerate(seg) if "### ⭐ 高质量模式生成中" in ln]

    assert len(hits) == 1, f"premium 分支内应有且只有一处 anomaly 警示，实得 {len(hits)} 处"
    assert len(heads) == 1 and heads[0] < hits[0]              # 任务书：补在 st.markdown 之后
    nxt = next(ln for ln in seg[hits[0] + 1:] if ln.strip() and not ln.strip().startswith("#"))
    assert nxt.strip().startswith("st.warning(")               # 跳注释后的第一条语句就是那条 warning
    assert any("elapsed is not None and elapsed > 90" in ln for ln in seg)   # 超时档仍在


def test_clock_anomaly_guard_in_the_pending_chain_is_exactly_two_sites():
    """pending 链的守卫面普查（与完成标准的 `grep -c 'if clock_anomaly' == 2` 同口径，
    但按整行.strip() 比，注释里提一句不会被误计）。premium 侧是平级 `if`，兜底链侧是 `elif`。"""
    lines = _render_body(_module_source()).splitlines()

    assert [ln.strip() for ln in lines if ln.strip() in ("if clock_anomaly:", "elif clock_anomaly:")] == \
        ["if clock_anomaly:", "elif clock_anomaly:"]


def test_both_clock_anomaly_warnings_share_one_verbatim_text():
    """「文案照既有分支」＝两处警示的文案逐字符同一。

    s924-37 常量化前：比的是两处**内联字面量的值**（比源码段更严也更能容缩进——premium 那处
    多一层缩进，比源码段会因空白误红）。抽取后两调用点各引同一个模块常量，"不许漂"从
    「测得出来」升级为「结构上不可能」⇒ 本例改钉三件，覆盖面不缩：
    ①render 体内恰好两处引该常量的 `st.warning`（少一处＝s922-139 那个 premium 缺警示的病复发）；
    ②render 体内不许再内联复制该文案（常量化被半途退回／有人新增第三份拷贝都会红）；
    ③常量是模块级唯一赋值，值仍含原三条关键子串（文案语义不许被顺手改掉）。
    """
    source = _module_source()
    body = _render_body(source)
    CONST = "CLOCK_ANOMALY_WARNING_TEXT"

    sites, leftovers = 0, 0
    for n in ast.walk(ast.parse(body)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "warning" and n.args:
            arg = n.args[0]
            if isinstance(arg, ast.Name) and arg.id == CONST:
                sites += 1
                continue
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "时钟异常" in arg.value:
                leftovers += 1
            if isinstance(arg, ast.JoinedStr) and "时钟异常" in "".join(
                    v.value for v in arg.values if isinstance(v, ast.Constant) and isinstance(v.value, str)):
                leftovers += 1

    assert sites == 2, f"期望两处引 {CONST} 的警示，实得 {sites}"
    assert leftovers == 0, "页面体内仍有内联副本 ⇒ 去重未完成"

    defs = [n for n in ast.parse(source).body
            if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id == CONST]
    assert len(defs) == 1, f"{CONST} 必须是模块级唯一赋值，实得 {len(defs)} 处"
    text = ast.literal_eval(defs[0].value)
    assert "耗时按 0s 显示" in text and "超时判断本轮不生效" in text
    assert "校准系统时间" in text




import time as _t

# ═════════ s922-140：时钟异常文案的**渲染级**端到端断言（只测渲染面，零改生产码）═════════
# 上游 s922-02 的自评缺口就是「『时钟异常』文案的渲染没有端到端断言，只有源码次序钉」。
# 本批用例把整页 render_questionnaire_page() 真跑一遍（假 st ＋ 假 future ＋ 不睡），
# 直接读渲染出来的帧序列，钉「回拨时出现的是警示、不是『<30 正常』那一档」。
class PageRerun(BaseException):
    """真实 `st.rerun()` 抛 RerunException（**BaseException** 派生）⇒ 本帧渲染到此为止。"""


class _NotDoneFuture:
    def done(self):
        return False


class State(dict):
    """session_state 的双面：既要 dict 面（`get/pop/in/[...]`）又要属性面（`st.session_state.language`）。"""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        del self[k]


class RecordingSt:
    """**宽松**假 st：允许并捕获 info/warning/success/error/markdown，把每帧存进 `.frames`。

    与 charac 的 StrictSt 刻意并存、不合并：StrictSt 的纪律是「多调一个方法当场红」，用来钉
    分支头骨架，但它跑不到页面深处的 pending 块（第一个未预期调用就炸）。本件反过来要求
    「整页跑得完且每帧都录得到」，所以未点名实现的方法走 `__getattr__` 兜底录名，
    `columns/container/expander/sidebar` 一律返回 self 以支持 `with …:`。
    """

    def __init__(self, state, sub_mode):
        self.session_state = state
        self.sub_mode = sub_mode
        self.frames = []

    def _add(self, kind, *parts):
        self.frames.append((kind, " ".join(str(p) for p in parts)))

    def title(self, m, **k): self._add("title", m)
    def header(self, m, **k): self._add("header", m)
    def caption(self, m, **k): self._add("caption", m)
    def markdown(self, m, **k): self._add("markdown", m)
    def info(self, m, **k): self._add("info", m)
    def warning(self, m, **k): self._add("warning", m)
    def success(self, m, **k): self._add("success", m)
    def error(self, m, **k): self._add("error", m)
    def code(self, m, **k): self._add("code", m)
    def progress(self, *a, **k): self._add("progress", k.get("text", ""))
    def divider(self, *a, **k): None
    def text_area(self, label, **k): return k.get("value", "") or ""
    def toggle(self, label, **k): return bool(k.get("value", False))
    def button(self, *a, **k): return False

    def radio(self, label, options, **k):
        if label == "选择工作流":
            return self.sub_mode
        return options[k.get("index", 0)]

    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [self for _ in range(n)]

    def container(self, *a, **k): return self
    def expander(self, *a, **k): return self

    @property
    def sidebar(self): return self

    def __enter__(self): return self
    def __exit__(self, *a): return False

    def rerun(self, *a, **k):
        raise PageRerun()

    def stop(self, *a, **k):
        raise PageRerun()

    def __getattr__(self, name):
        if name.startswith("__") or name in ("session_state", "sub_mode", "frames"):
            raise AttributeError(name)
        self.frames.append(("unhandled", name))
        return lambda *a, **k: None

    def text_of(self, kinds=("info", "warning", "success", "error", "markdown")):
        return "\n".join(t for k, t in self.frames if k in kinds)


def render_page_with_pending(module, pending):
    """真跑 `module.render_questionnaire_page()` 一帧，返回录到帧的假 st。

    替掉三处与本页无关的外部门面（记忆面板／LLM 激活配置读／`time.sleep`），**不替任何页面内
    分支判据**——pending 链、premium 链、文案全部走真码。`st.rerun()` 用 BaseException 终止渲染。
    """
    import time as _time

    import src.llm_gateway.active_config as ac

    st = RecordingSt(State({"language": "zh", "_q_design_pending": pending}), AI_LABEL)
    orig = (module.st, module.render_memory_manager_ui, ac.get_active_llm_config, _time.sleep)
    module.st = st
    module.render_memory_manager_ui = lambda *a, **k: None
    ac.get_active_llm_config = lambda: None
    _time.sleep = lambda s: None
    try:
        module.render_questionnaire_page()
    except PageRerun:
        pass
    finally:
        module.st, module.render_memory_manager_ui, ac.get_active_llm_config, _time.sleep = orig
    return st


def _pending(offset_seconds=None, premium=False):
    """started_at 一律**相对真实 now** 构造——写成绝对 epoch 就会像「夹具绝对日期＋相对断言」
    那样每过一天自己漂一次（纪律档第八节那条通用坑）。

    offset_seconds=None ⇒ started_at 缺失；正数 = 未来（时钟回拨族）；负数 = 过去。
    """
    started_at = None if offset_seconds is None else _t.time() + offset_seconds
    return {"started_at": started_at, "premium": premium,
            "from_cache": False, "future": _NotDoneFuture(), "cancel_id": "cid"}


def test_render_clock_anomaly_replaces_the_under_30_hint_on_non_premium_chain():
    """s922-02 的病案本体：回拨 ⇒ 出现「时钟异常」警示，且「<30 正常」那一档**不能**出现。"""
    st = render_page_with_pending(qp, _pending(+3600.0))           # started_at 在未来一小时 = 回拨族
    txt = st.text_of()

    assert "时钟异常" in txt, st.frames
    assert "通常 30-90s 完成" not in txt                          # 即 `elif elapsed < 30` 那一档
    assert "已超过" not in txt                                     # 钳 0 ⇒ >90 档也不触发
    assert any(k == "warning" and "时钟异常" in t for k, t in st.frames)


def test_render_premium_chain_renders_the_clock_anomaly_warning_too():
    """本条是 s922-139 的渲染面：**改前必红**（premium 分支当时只看 elapsed_txt）。"""
    st = render_page_with_pending(qp, _pending(+3600.0, premium=True))
    txt = st.text_of()

    assert "### ⭐ 高质量模式生成中（已 0s）" in txt               # 标题仍按钳 0 显示
    assert "时钟异常" in txt                                       # 但警示已补上（改前红）
    assert "已超过 90s" not in txt
    assert not any(k == "unhandled" for k, _ in st.frames[:6])     # 侧栏/页头没走到兜底通道


@pytest.mark.parametrize("offset, want, veto", [
    (+3600.0, "时钟异常", "通常 30-90s 完成"),                     # 回拨族（started_at 在未来）
    (None, "耗时未知", "时钟异常"),                                 # 缺失族：是"未知"不是"异常"
    (-3600.0, "超过预设超时", "时钟异常"),                           # 真等了一小时 ⇒ 落超时红档，异常文案不许串台
    (-60.0, "仍在生成中（已", "时钟异常"),                           # 正常 60s 档
])
def test_render_branch_selection_matrix_started_at_states(offset, want, veto):
    """四态矩阵：证明上面两条不是「什么都往 txt 里塞」的假绿——警示只在回拨那一格出现。"""
    st = render_page_with_pending(qp, _pending(offset))
    txt = st.text_of()

    assert want in txt, (offset, st.frames)
    assert veto not in txt, offset
