# -*- coding: utf-8 -*-
"""`_set_east_asian_font`（`src/questionnaire/exporters.py:238-251`）**静默回退面的观测现状**钉桩（s923-05）。

出处：`zcode-bridge/done/s922-13-psy-exporters-docx.result.md:92-94`
——「CJK 字体设置可能一直在悄悄失败而无人知，**现有观测面为零（不抛、不 log）**。
要不要在 except 里补一行 `logger.debug`…属改生产行为，本单一律未动」。
本件把「观测面为零」这件事从**口头结论**变成**可回归的断言**：哪天有人补了日志/返回值，
本件用例会红，届时按下面的建议稿口径评审，而不是靠记性。

s922-13 已钉过的两条**本件刻意不重复**：
成功路写 `w:eastAsia`（其 :168-180）、五种垃圾入参不抛（其 :183-194）。
本件钉的是它没测的维度：**失败时除了"不抛"之外到底留下什么信号**（答：什么都不留）。

════════════════ 观测补齐建议（**建议稿，本单零落码**）════════════════
现状：`except Exception: pass`（:250-251），且 `exporters.py` 整个模块**没有 logging 面**
（实测 `hasattr(exporters, "logging") is False`），故失败既不抛也不记。两种补齐口径：

**口径 A · 诊断级（`logger.debug`，推荐先走这档）**
- 改法：模块顶 `logger = logging.getLogger(__name__)`（本仓既有约定，见
  `src/utils/autosave.py:26`、`src/utils/project_manager.py:36`、`src/utils/recent_files.py:19`
  四处同型），except 里 `logger.debug("CJK eastAsia 字体映射失败：%s（不影响导出）", exc)`。
- 优点：零行为改动、零用户可见面变化、异常对象仍可拿到 traceback。
- **代价要说清**：debug 默认不外泄 ⇒ 生产现场**仍然看不见**，只对"愿意开 DEBUG 的诊断环境"
  （本仓有诊断件先例）可见。它治的是「事后查不到」，治不了「当下没人知」。
- 断言影响：本件 :5 号例（无 logging 面）与 :1/:2 号例（`caplog.records == []`）会红 ——
  红是**期望行为**，届时要把「有 debug 记录」写成新断言而不是删用例。

**口径 B · 告警级（`logger.warning` / 一次性 `warnings.warn`）**
- 改法：同 A，但级别抬到 warning；或只在**首个失败**时 warn 一次（避免 5 个调用点刷屏）。
- 优点：真正进入可观测面，CJK 悄悄掉字不再需要有人主动开 DEBUG 才看得见。
- **代价**：`export_to_docx` 被 `src/ui/questionnaire_panel.py` 的导出按钮直接调用，
  Streamlit 侧若已配 logging 捕获/回显，warning 会**出现在用户界面上**，
  而函数文档写死「不是关键功能」⇒ 把一个刻意设计成无关紧要的失败抬成"看起来像出错"，
  属行为/UX 改动，**需主班裁决**，不在执行手授权内。

**口径 C（记一笔，不建议）**：把 `-> None` 改成返回 `bool` 让调用方决定。
签名扩散到 3 个调用点与 UI 层，改动面最大、收益不比 B 高。

**共同前提**：无论 A/B，都得先把「字体名非法」这一类**根本不会进 except** 的情况分开处理
（见本件 :3 号例的否证）——补日志不会让它变得可见。

红线自约：design 全为「合成构念/合成题干」人造文案，不含真实被试数据、不含统计/研究结论数值。
"""
from __future__ import annotations

import contextlib
import io
import logging
import warnings

import docx.oxml.ns as oxml_ns
import pytest
from docx import Document
from docx.oxml.ns import qn

from src.questionnaire import exporters
from src.questionnaire.exporters import _set_east_asian_font, export_to_docx

_RPR_TAGS = ("w:rPr", "w:rFonts")


def _design() -> dict:
    return {
        "construct_name": "合成构念",
        "research_question": "合成研究问题？",
        "template_used": {"name": "合成题型"},
        "scale_config": {
            "points": 5, "n_items": 2, "n_dimensions": 1, "n_reverse": 1, "reverse_ratio": "50%",
            "anchors": ["完全不同意", "完全同意"],
        },
        "match_reason": "合成匹配理由",
        "dimensions_used": [{"name": "维度甲", "desc": "合成描述", "item_count": 2}],
        "instructions": "合成指导语",
        "items": [
            {"dimension": "维度甲", "reverse": False, "index": 1, "text": "合成题干一"},
            {"dimension": "维度甲", "reverse": True, "index": 2, "text": "合成题干二"},
        ],
        "scoring": "合成计分方式",
        "psychometrics": {"信度": "合成信度策略", "效度": "合成效度策略"},
    }


def _east_asia_of(element):
    rpr = element.find(qn("w:rPr"))
    if rpr is None:
        return "<无 rPr>"
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        return "<无 rFonts>"
    return rfonts.get(qn("w:eastAsia"))


@contextlib.contextmanager
def failing_cjk_lookup():
    """把 `docx.oxml.ns.qn` 换成「只对 rPr/rFonts 两个标签抛」的版本 ⇒ 制造**真**的结构化失败。

    为什么这么造：`_set_east_asian_font` 是在 try 内 `from docx.oxml.ns import qn` **按调用时刻**取属性，
    所以打这个模块属性就能命中它；而 python-docx 自己在 import 期已把 `qn` 绑成局部引用的路径**不受影响**
    （实测：打了之后 `export_to_docx` 仍正常出稿），这样造出来的失败只落在被测函数身上。
    用 `contextlib` 而不是 `monkeypatch`：`export_under_cjk_failure()` 要在**导出之后**立刻还原，
    才能干净地回读产物（fixture 的还原时机太晚）。
    """
    real_qn = oxml_ns.qn
    stats = {"hits": 0}                                      # 命中计数：证明 except **真的**被走到

    def _qn(tag: str):
        if tag in _RPR_TAGS:
            stats["hits"] += 1
            raise RuntimeError(f"forced failure on {tag}")
        return real_qn(tag)

    oxml_ns.qn = _qn
    try:
        yield stats
    finally:
        oxml_ns.qn = real_qn


# ═══════════════ 1. 单点失败：除了"不抛"，什么都没有 ═══════════════
def test_structural_failure_leaves_no_log_record_and_no_return_signal(caplog):
    """核心钉桩：真失败时**零日志记录、零返回值、零告警** —— 「观测面为零」的可执行版本。"""
    style = Document().styles["Normal"]

    with caplog.at_level(logging.DEBUG):                    # 放到最低门限，任何级别都得录到
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with failing_cjk_lookup() as stats:
                result = _set_east_asian_font(style, "宋体")

    assert stats["hits"] >= 1                               # except 真的被走到（防空转的判别实验）

    assert result is None                                   # 返回 None：调用方无从判断成败
    assert caplog.records == []                             # 一条记录都没有
    assert caught == []                                     # 连 warnings 都不发
    assert _east_asia_of(style.element) == "<无 rPr>"        # 失败后不留半成品节点（不会"写一半"）


def test_exporters_module_itself_has_no_observability_surface() -> None:
    """守卫：`exporters.py` 里根本没有 logging 面 ⇒ 上面那条"零记录"不是巧合而是结构性的。

    哪天补了 logger（建议稿口径 A/B），本例会红——那是**预期的提醒**，
    届时请把断言改成「有且只有一条 debug/warning」并连同生产码一起评审，别只摘用例。
    """
    assert not hasattr(exporters, "logging")
    assert not hasattr(exporters, "logger")
    assert not hasattr(exporters, "getLogger")

    with open(exporters.__file__, encoding="utf-8") as fh:
        body = fh.read()
    assert "import logging" not in body and "logger." not in body
    assert "except Exception:" in body                      # :250 就是那个吞点，行号会漂、文本不会
    assert "\n        pass\n" in body                        # :251 的裸 pass（缩进含在内）


# ═══════════════ 2. 生产面：整篇导出成功，但 CJK 映射其实没写上 ═══════════════
def test_docx_ships_normally_while_cjk_mapping_silently_missing(caplog) -> None:
    """s922-13 说的「生产里可能一直在悄悄失败而无人知」——本例把它**演出来**并钉住判据。

    强制 `_set_east_asian_font` 全程失败后：
    ① `export_to_docx` 照样出稿、不抛、零日志；
    ② 回读文档里 Normal 样式的 `w:ascii` **仍是「宋体」**（`:33` 设的），
       所以任何只看 `style.font.name` 的检查都会**误判为"字体配好了"**；
    ③ 而 `w:eastAsia` 压根不存在 ⇒ 中文实际没拿到东亚字体映射。
    ②③ 之差就是"常量说谎"的现场，也是本件存在的理由。
    """
    caplog.set_level(logging.DEBUG)
    blob, hits = export_under_cjk_failure()                 # 全程失败态出稿，见文件尾 helper
    assert hits == 5                                        # 5 个调用点**全部**悄悄失败（判别实验）

    doc = Document(io.BytesIO(blob))
    normal = doc.styles["Normal"]
    assert normal.font.name == "宋体"                       # ② 看着是对的（这是 latin 槽）
    assert _east_asia_of(normal.element) is None            # ③ eastAsia 真的没写
    assert "Q1. 合成题干一" in "\n".join(p.text for p in doc.paragraphs)   # ① 正文照常
    assert caplog.records == []                             # 全程零记录


# ═══════════════ 3. 任务书前提否证：非法字体名**不会**触发 except ═══════════
def test_invalid_font_name_is_not_a_failure_at_all_and_lands_verbatim() -> None:
    """**否证**任务书口径「monkeypatch 字体名为必失败值」：字体名根本**不校验**。

    `:249` 只做 `rFonts.set(qn("w:eastAsia"), font_name)` —— 任意字符串都塞得进去，
    不抛 ⇒ 走不到 `:250-251` 的 except。于是「字体名写错」这一类比"结构化失败"**更安静**：
    它连失败都不算，直接把错值写进 XML，等到 Word 打开才现形。
    故本件的失败桩改用 `fail_cjk_lookup`（制造真异常），而不是任务书说的"必失败字体名"。
    """
    style = Document().styles["Normal"]
    junk = "不存在的字体名XYZ"

    assert _set_east_asian_font(style, junk) is None        # 不抛
    assert _east_asia_of(style.element) == junk             # 错值逐字落盘，无人拦


# ═══════════════ 4. 「静默」不等于「压根没跑」：三个调用点五次调用 ═══════════
def test_three_call_sites_fire_five_times_per_export(monkeypatch) -> None:
    """判别实验：证明上面的"零信号"不是因为函数没被调用。

    `:36` Normal（1 次）＋ `:44` Heading 1/2/3 循环（3 次）＋ `:54` 封面标题 run（1 次）
    ⇒ 一次导出共 5 次。任务书"三处调用"指**调用点 3 个**，实际**调用 5 次**（口径收窄，见 result 证据节）。
    """
    seen: list[str] = []
    real = exporters._set_east_asian_font

    def spy(style, font_name: str):
        seen.append(font_name)
        return real(style, font_name)                        # 委托真实现：不改变产物

    monkeypatch.setattr(exporters, "_set_east_asian_font", spy)
    export_to_docx(_design())

    assert seen == ["宋体", "黑体", "黑体", "黑体", "黑体"]
    assert len(seen) == 5


# ═══════════════ 5. 附带在册现状（超出钉桩主体，只登记不改） ═══════════
def test_subtitle_kaiti_run_has_latin_slot_only_no_eastasia_mapping() -> None:
    """**附带发现**：封面副标题的「楷体」（`:60`）只设 latin 字体名，**没有**对应调用点 ⇒ 覆盖不对称。

    5 次调用覆盖了 Normal / Heading 1-3 / 封面主标题 run，副标题 run 被漏掉。
    后果与"悄悄失败"同类：正文里唯一的楷体行在 Word 中拿不到东亚映射，
    而 `run.font.name == "楷体"` 会让任何只看名字的检查误判为已配好。
    属现状钉桩，**本单不补调用**（补它＝改版式/改行为）。
    """
    doc = Document(io.BytesIO(export_to_docx(_design())))
    subtitle_run = doc.paragraphs[1].runs[0]

    assert subtitle_run.font.name == "楷体"                 # 看着配了
    assert _east_asia_of(subtitle_run.element) is None      # 实际没有 eastAsia


def test_run_fallback_append_would_land_rpr_after_text_and_stays_silent() -> None:
    """**附带在册隐患**：`:245` 的 `etree.SubElement(style.element, qn("w:rPr"))` 是**尾插**。

    run 元素里 `w:rPr` 必须是**首子元素**；若哪天有人在设任何字体属性之前先调这个 helper，
    rPr 会被插到 `w:t` 之后 —— 不抛、不 log、能存能读回（本例前半段），
    但产物不符 OOXML 元素序，Word 侧行为未定义。
    今天**没踩到**是因为 `:51-53` 先设了 size/bold/name，rPr 已由 python-docx 按正确位置建好
    （本例后半段把"今天是对的"一起钉住，防止有人反过来改）。
    """
    doc = Document()
    early_run = doc.add_paragraph().add_run("正文")
    _set_east_asian_font(early_run, "黑体")
    order = [child.tag.split("}")[1] for child in early_run.element]
    assert order == ["t", "rPr"], order                     # 尾插现状（不抛＝隐患）

    healthy_run = Document(io.BytesIO(export_to_docx(_design()))).paragraphs[0].runs[0]
    assert [c.tag.split("}")[1] for c in healthy_run.element][:2] == ["rPr", "t"]


# ==== helper ====
def export_under_cjk_failure():
    """在 `qn` 被搞坏的状态下**完成整篇导出**，出来后立即还原 => (产物, 失败命中次数)。"""
    with failing_cjk_lookup() as stats:
        blob = export_to_docx(_design())
    return blob, stats["hits"]
