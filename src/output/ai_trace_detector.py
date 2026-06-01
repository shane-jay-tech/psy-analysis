"""v3.8 O3: 中文学术写作 AI 痕迹检测器。

针对学生用 deepseek/gpt 生成论文后留下的"AI 烙印"做检测，
帮助学生在交稿前去除一眼可见的机械八股。

核心入口：
- ``detect_ai_traces(text)`` —— 规则层检测，返回 AITraceReport
- ``score_ai_likelihood(text)`` —— 综合评分（0-100，越高越像 AI）
- ``rewrite_suggestion(sentence)`` —— 单句替换建议（基于规则）

用法：
    >>> report = detect_ai_traces(paper_text)
    >>> for h in report.hits:
    ...     print(h.line_no, h.pattern_label, h.suggestion)

设计原则：
- 规则可扩展（PATTERNS 列表）+ 严格度可配
- 零 LLM 依赖（规则层），可选 LLM 二次评估
- 行级定位 + 上下文摘录，便于 UI 渲染标红
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# 模式库：每条 = (label, severity, regex, why, suggestion_tpl)
# severity: "high" 必删 / "med" 强烈建议改 / "low" 提醒
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TracePattern:
    label: str          # 简短标签（"八股开头"）
    severity: str       # "high" / "med" / "low"
    pattern: str        # regex
    why: str            # 为什么是 AI 痕迹
    suggestion: str     # 建议改法


PATTERNS: List[TracePattern] = [
    # —— 开头八股（开场白）——
    TracePattern(
        label="开场八股",
        severity="high",
        pattern=r"(?:^|(?<=[\n。！？]))[ \t　]*(?:首先|其次|再次|然后|最后)[，,。、]",
        why="顺序词串联是 AI 最典型的开场标志，老师一眼看出来",
        suggestion="去掉「首先/其次/最后」，让段落自然推进；或换成「一方面...另一方面」「在...层面，则...」",
    ),
    TracePattern(
        label="总结套话",
        severity="high",
        pattern=r"(?:^|(?<=[\n。]))[ \t　]*(?:综上所述|总而言之|总的来说|由此可见|不难发现|不难看出)[，,。、]",
        why="收束句是 AI 标准模板的结尾固件，过于程式化",
        suggestion="直接陈述结论，不需要承接词；或用「因此」「这意味着」",
    ),
    TracePattern(
        label="冗余自我指称",
        severity="med",
        pattern=r"在本研究中[，,]?",
        why="一篇论文里出现 5+ 次「在本研究中」是 AI 高频烙印",
        suggestion="开篇 1 次足够，正文用「我们」「该研究」「本文」交替使用",
    ),
    # —— AI 高频套话 ——
    TracePattern(
        label="值得深入探讨",
        severity="high",
        pattern=r"值得(?:进一步|深入)?(?:探讨|思考|研究)",
        why="ChatGPT 类模型的高频结尾用语，学生不会自然写出",
        suggestion="说清楚「探讨什么」：'对照组样本量过小，未来需 N≥120 的复制研究'",
    ),
    TracePattern(
        label="具有重要意义",
        severity="high",
        pattern=r"(?:具有|有着)\s*(?:重要|重大|深远)?\s*(?:理论|实践|学术|现实)?\s*(?:意义|价值)",
        why="空洞的意义陈述，无具体所指",
        suggestion="改为「对...的具体启示」+ 一句话举例（如「为高校心理咨询初筛设计提供量表证据」）",
    ),
    TracePattern(
        label="为...提供...",
        severity="med",
        pattern=r"为\s*[^，,。\n]{2,15}\s*提供[了]?\s*(?:有益|有力|重要|科学)?\s*(?:参考|借鉴|依据|启示|思路|视角)",
        why="模板化的功能性陈述，几乎所有 AI 论文结尾都有",
        suggestion="说清楚「谁能用、怎么用」：'高校心理中心可据此优化筛查阈值'",
    ),
    TracePattern(
        label="日新月异",
        severity="high",
        pattern=r"(?:日新月异|与日俱增|蓬勃发展|蒸蒸日上|方兴未艾)",
        why="八股开场用语，老师反感",
        suggestion="直接给数据：'近 5 年抑郁量表自评分上升 12%（中国心理健康发展报告 2024）'",
    ),
    TracePattern(
        label="必要性陈述",
        severity="med",
        pattern=r"(?:开展|进行|实施)?\s*[^，,。\n]{0,15}\s*研究?\s*(?:显得|十分|非常|尤为|特别|愈发)?\s*(?:必要|重要|迫切|关键)",
        why="为研究找理由的 AI 模板句",
        suggestion="把「为什么必要」具体化：'前人研究均在 N<50 临床样本中进行，社区样本仍是空白'",
    ),
    # —— 关联词堆叠 ——
    TracePattern(
        label="然而句首滥用",
        severity="low",
        pattern=r"(?:^|(?<=[\n。]))[ \t　]*(?:然而|但是|不过)[，,]\s*(?:[^。\n]{0,40}然而|[^。\n]{0,40}但是)",
        why="同段反复使用「然而」「但是」是 AI 翻译腔",
        suggestion="一段最多用一次转折词；多次需要转折时改写为「尽管...仍...」",
    ),
    TracePattern(
        label="并列连用",
        severity="low",
        pattern=r"(?:不仅|不但)[^，,。\n]{0,30}[，,]\s*(?:而且|并且|同时也)\b",
        why="「不仅...而且...」结构连用 3 次以上偏 AI",
        suggestion="散开成两个短句，让节奏更自然",
    ),
    # —— 模板化结构 ——
    TracePattern(
        label="本文研究表明",
        severity="med",
        pattern=r"(?:本文|本研究|该研究)\s*(?:研究)?\s*(?:表明|发现|揭示|显示)[，,]",
        why="过于工整，且与摘要语句重复",
        suggestion="'我们的数据显示...'/'结果表明...'/直接陈述发现",
    ),
    TracePattern(
        label="...表明...",
        severity="low",
        pattern=r"(?:研究|结果|数据|分析)\s*(?:表明|说明|显示|揭示)\s*[，,：]",
        why="未必是 AI 痕迹，但出现 5+ 次说明句式单一",
        suggestion="交替使用：'数据指向...'/'我们观察到...'/'这与 X 研究一致'",
    ),
    # —— 程式化引用 ——
    TracePattern(
        label="结论部分模板",
        severity="high",
        pattern=r"(?:本研究|本文)\s*(?:得出|得到)\s*(?:以下|如下)\s*(?:结论|发现)",
        why="「得出以下结论」是论文结尾的 AI 模板套语",
        suggestion="去掉框架句，直接列具体结论；或用「我们的主要发现是...」",
    ),
    TracePattern(
        label="未来研究展望",
        severity="med",
        pattern=r"未来(?:的)?\s*研究(?:可以|可)?\s*(?:进一步|从|针对|围绕)",
        why="所有 AI 论文结尾都有这句，但内容往往空洞",
        suggestion="换成具体动作：'下一步用 EEG 替代自评，N=80 跨文化复制'",
    ),
    # —— 翻译腔 ——
    TracePattern(
        label="作出贡献",
        severity="med",
        pattern=r"(?:作出|做出|提供)\s*(?:重要|有益|积极)?\s*(?:贡献|努力)",
        why="英文 'contribute to' 直译，中文学术写作偏少使用",
        suggestion="'推进了...的理解'/'扩展了...的边界'",
    ),
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TraceHit:
    """单个命中。"""
    line_no: int            # 1-indexed
    char_start: int         # 在原文中的起始字符位置
    char_end: int           # 原文中的结束位置
    matched_text: str       # 命中的原文片段
    line_text: str          # 所在行（最多 160 字符截断）
    pattern_label: str
    severity: str           # "high" / "med" / "low"
    why: str
    suggestion: str


@dataclass
class AITraceReport:
    """整篇文本的检测报告。"""
    total_chars: int = 0
    total_lines: int = 0
    hits: List[TraceHit] = field(default_factory=list)
    score: float = 0.0      # 0-100，越高越像 AI
    severity_counts: dict = field(default_factory=dict)  # {"high": int, "med": int, "low": int}
    summary: str = ""

    @property
    def has_high_severity(self) -> bool:
        return self.severity_counts.get("high", 0) > 0

    def hits_by_severity(self, severity: str) -> List[TraceHit]:
        return [h for h in self.hits if h.severity == severity]


# ---------------------------------------------------------------------------
# 核心检测
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT = {"high": 5.0, "med": 2.0, "low": 0.5}


def _line_context(text: str, char_pos: int, max_len: int = 160) -> tuple[int, str]:
    """从字符位置反推行号 + 该行内容（截断）。"""
    line_no = text.count("\n", 0, char_pos) + 1
    # 找当前行的起止
    line_start = text.rfind("\n", 0, char_pos) + 1
    line_end = text.find("\n", char_pos)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    if len(line) > max_len:
        # 居中截断
        center = char_pos - line_start
        half = max_len // 2
        s = max(0, center - half)
        e = min(len(line), center + half)
        line = "..." + line[s:e] + "..."
    return line_no, line


def detect_ai_traces(
    text: str,
    *,
    extra_patterns: Optional[List[TracePattern]] = None,
    severity_filter: Optional[List[str]] = None,
) -> AITraceReport:
    """检测整篇中文学术文本中的 AI 痕迹。

    Args:
        text: 待检测全文（中文 + 标点）
        extra_patterns: 额外自定义规则
        severity_filter: 仅返回这些严重度（如 ["high", "med"]）

    Returns:
        AITraceReport
    """
    if not text or not text.strip():
        return AITraceReport(total_chars=0, total_lines=0, summary="文本为空")

    patterns = list(PATTERNS) + (extra_patterns or [])
    hits: List[TraceHit] = []

    for pat in patterns:
        if severity_filter and pat.severity not in severity_filter:
            continue
        try:
            regex = re.compile(pat.pattern)
        except re.error:
            continue
        for m in regex.finditer(text):
            line_no, line_text = _line_context(text, m.start())
            hits.append(TraceHit(
                line_no=line_no,
                char_start=m.start(),
                char_end=m.end(),
                matched_text=m.group(0).strip(),
                line_text=line_text,
                pattern_label=pat.label,
                severity=pat.severity,
                why=pat.why,
                suggestion=pat.suggestion,
            ))

    # 排序：行号升序，同行按 char_start
    hits.sort(key=lambda h: (h.line_no, h.char_start))

    # 评分：weighted hits / 文本长度（千字单位归一化）
    total_chars = len(text)
    n_lines = text.count("\n") + 1
    sev_counts = {"high": 0, "med": 0, "low": 0}
    weighted_sum = 0.0
    for h in hits:
        sev_counts[h.severity] = sev_counts.get(h.severity, 0) + 1
        weighted_sum += _SEVERITY_WEIGHT.get(h.severity, 0.0)

    # 每千字加权命中数 → 映射到 0-100
    per_kchar = weighted_sum / max(total_chars / 1000, 1.0)
    # 经验阈值：≤2 几乎正常，≥10 重度
    score = min(100.0, per_kchar * 10)

    summary = _format_summary(hits, sev_counts, score)

    return AITraceReport(
        total_chars=total_chars,
        total_lines=n_lines,
        hits=hits,
        score=round(score, 1),
        severity_counts=sev_counts,
        summary=summary,
    )


def _format_summary(hits: List[TraceHit], sev_counts: dict, score: float) -> str:
    """生成一句话总结。"""
    if not hits:
        return "未发现明显 AI 痕迹（不代表零痕迹，仅规则层判断）。"

    parts = []
    if sev_counts.get("high", 0):
        parts.append(f"🔴 {sev_counts['high']} 处必删")
    if sev_counts.get("med", 0):
        parts.append(f"🟡 {sev_counts['med']} 处建议改")
    if sev_counts.get("low", 0):
        parts.append(f"🟢 {sev_counts['low']} 处提醒")

    level = "重度" if score >= 50 else ("中度" if score >= 20 else "轻度")
    return f"AI 痕迹评分 {score:.0f}/100（{level}）；" + "，".join(parts)


def score_ai_likelihood(text: str) -> float:
    """快捷接口：返回 0-100 评分。"""
    return detect_ai_traces(text).score


# ---------------------------------------------------------------------------
# 单句替换建议（规则层，不依赖 LLM）
# ---------------------------------------------------------------------------

# 简单替换映射：单词级
_WORD_REPLACE = {
    "首先": "",  # 删除
    "其次": "",
    "最后": "",
    "综上所述": "",
    "总而言之": "",
    "由此可见": "因此",
    "不难发现": "可以看到",
    "不难看出": "可以看到",
    "值得深入探讨": "需要后续研究",
    "值得进一步探讨": "需要后续研究",
    "具有重要意义": "对...有具体启示",
    "具有重大意义": "对...有具体启示",
    "日新月异": "迅速变化",
    "蓬勃发展": "快速增长",
}


def rewrite_suggestion(sentence: str) -> str:
    """对单句给出快速替换建议（规则层）。

    仅做表层替换，复杂改写仍需 LLM。
    """
    if not sentence:
        return sentence
    out = sentence
    for k, v in _WORD_REPLACE.items():
        out = out.replace(k, v)
    # 收尾清理：连续标点 + 首尾标点
    out = re.sub(r"[，,]\s*[，,]", "，", out)
    out = re.sub(r"^\s*[，,。、]\s*", "", out)
    out = out.strip()
    return out


def render_report_markdown(report: AITraceReport, *, max_hits: int = 20) -> str:
    """把报告渲染为 Markdown，UI 直显或入 PDF 附录。"""
    if not report.hits:
        return "## 🟢 AI 痕迹检测\n\n" + report.summary + "\n"

    lines = ["## 🔍 AI 痕迹检测", "", report.summary, ""]
    sev_emoji = {"high": "🔴", "med": "🟡", "low": "🟢"}
    sev_label = {"high": "必删", "med": "建议改", "low": "提醒"}

    for sev in ("high", "med", "low"):
        bucket = report.hits_by_severity(sev)
        if not bucket:
            continue
        lines.append(f"### {sev_emoji[sev]} {sev_label[sev]}（{len(bucket)} 处）")
        lines.append("")
        for h in bucket[:max_hits]:
            lines.append(f"- **第 {h.line_no} 行 · {h.pattern_label}**：「{h.matched_text}」")
            lines.append(f"  - 原因：{h.why}")
            lines.append(f"  - 建议：{h.suggestion}")
        if len(bucket) > max_hits:
            lines.append(f"  - ...另外 {len(bucket) - max_hits} 处略")
        lines.append("")
    return "\n".join(lines)
