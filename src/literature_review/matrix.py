"""文献矩阵：用户自定义维度构建对比表 + 摘要自动填充 + CSV/HTML 导出。"""

from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, List, Optional

from .models import LiteratureItem, LiteratureMatrix


# ---------------------------------------------------------------------------
# 创建与初始化
# ---------------------------------------------------------------------------

DEFAULT_DIMENSIONS = ["样本量", "研究设计", "主要发现", "效应量", "局限"]


def create_matrix(
    literature_items: List[LiteratureItem],
    dimensions: Optional[List[str]] = None,
) -> LiteratureMatrix:
    """创建一个空矩阵：rows=文献，cols=用户自定义维度。"""
    matrix = LiteratureMatrix(dimensions=list(dimensions or DEFAULT_DIMENSIONS))
    for item in literature_items or []:
        if item.key not in matrix.cells:
            matrix.cells[item.key] = {d: "" for d in matrix.dimensions}
    return matrix


def add_literature_to_matrix(
    matrix: LiteratureMatrix,
    item: LiteratureItem,
) -> None:
    """添加文献到矩阵（不覆盖已有 cell）。"""
    if item.key not in matrix.cells:
        matrix.cells[item.key] = {d: "" for d in matrix.dimensions}


def remove_literature_from_matrix(
    matrix: LiteratureMatrix,
    literature_key: str,
) -> bool:
    if literature_key in matrix.cells:
        del matrix.cells[literature_key]
        return True
    return False


# ---------------------------------------------------------------------------
# 摘要自动填充（关键词提取，无 LLM 依赖）
# ---------------------------------------------------------------------------

# 维度关键词模式（中文 + 英文）
_DIMENSION_PATTERNS: Dict[str, List[str]] = {
    "样本量": [
        r"n\s*=\s*(\d+)",
        r"sample\s+size\s+(?:of\s+|was\s+)?(\d+)",
        r"(\d+)\s*名(?:被试|参与者|受访者|学生)",
        r"(\d+)\s*个(?:被试|参与者)",
        r"参与者\s*[:：]?\s*(\d+)",
    ],
    "研究设计": [
        r"(横断面|纵向|实验|准实验|问卷调查|cross-sectional|longitudinal|experimental)",
        r"(随机对照|RCT|双盲)",
        r"(被试间设计|被试内设计|混合设计|between-subjects|within-subjects)",
    ],
    "效应量": [
        r"(?:cohen'?s\s*)?d\s*=\s*([\-\d.]+)",
        r"η²\s*=\s*([\d.]+)",
        r"r\s*=\s*([\-\d.]+)",
        r"β\s*=\s*([\-\d.]+)",
        r"effect\s+size\s*[:=]?\s*([\d.]+)",
    ],
}


def auto_fill_abstract_info(
    item: LiteratureItem,
    matrix: LiteratureMatrix,
    *,
    overwrite: bool = False,
    use_llm: bool = False,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Dict[str, Any]:
    """从文献摘要中关键词/LLM 提取并填充矩阵的 cell。

    v3.5 加 use_llm 参数：True 时优先用 LLM 网关一次性提取，失败回退正则。

    Returns:
        {"extracted": {dim: value, ...}, "method": "llm" | "regex"}
    """
    if not item.abstract:
        return {"extracted": {}, "method": "regex"}
    if item.key not in matrix.cells:
        matrix.cells[item.key] = {d: "" for d in matrix.dimensions}

    extracted: Dict[str, str] = {}
    method = "regex"

    # v3.5 LLM 路径
    if use_llm:
        llm_extracted = _llm_extract_dimensions(
            item, matrix.dimensions,
            llm_config=llm_config, requests_module=requests_module,
        )
        if llm_extracted is not None:
            method = "llm"
            for dim, value in llm_extracted.items():
                if dim not in matrix.dimensions:
                    continue
                if not overwrite and matrix.get_cell(item.key, dim).strip():
                    continue
                if value:
                    matrix.set_cell(item.key, dim, str(value)[:120])
                    extracted[dim] = value

    # 正则补漏（即便用了 LLM，未填的 cell 也用正则兜底）
    text = item.abstract.lower()
    for dim in matrix.dimensions:
        if not overwrite and matrix.get_cell(item.key, dim).strip():
            continue
        if dim in extracted:
            continue
        patterns = _DIMENSION_PATTERNS.get(dim, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(0)[:80]
                matrix.set_cell(item.key, dim, value)
                extracted[dim] = value
                break

    # 主要发现 / 局限：句子提取
    if "主要发现" in matrix.dimensions:
        if "主要发现" not in extracted and (overwrite or not matrix.get_cell(item.key, "主要发现").strip()):
            finding = _extract_main_finding(item.abstract)
            if finding:
                matrix.set_cell(item.key, "主要发现", finding)
                extracted["主要发现"] = finding

    if "局限" in matrix.dimensions:
        if "局限" not in extracted and (overwrite or not matrix.get_cell(item.key, "局限").strip()):
            limitation = _extract_limitations(item.abstract)
            if limitation:
                matrix.set_cell(item.key, "局限", limitation)
                extracted["局限"] = limitation

    return {"extracted": extracted, "method": method}


def _llm_extract_dimensions(
    item: LiteratureItem,
    dimensions: List[str],
    *,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Optional[Dict[str, str]]:
    """通过 LLM 网关一次性提取所有维度。失败返回 None（由调用方 fallback）。"""
    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        from src.paper_writer.ai_tutor import build_tutor_messages
        import json
    except Exception:
        return None

    dim_list = "、".join(dimensions)
    sys_prompt = (
        f"你是文献信息提取助手。从下面的文献标题和摘要中提取这 {len(dimensions)} 个维度的关键信息：\n"
        f"维度：{dim_list}\n\n"
        "输出严格的 JSON 对象，键为维度名，值为简短文本（≤80 字）。"
        "找不到信息的维度填空字符串。\n"
        "不要包含任何解释，只输出 JSON。"
    )
    user_msg = f"标题：{item.title}\n摘要：{item.abstract[:1500]}"
    msgs = build_tutor_messages(sys_prompt, [], user_msg)

    last_raw = ""
    for attempt in range(2):
        try:
            response = llm_chat(
                msgs,
                temperature=0.1,
                llm_config=llm_config,
                requests_module=requests_module,
                retries=0,
            )
            if not response.ok:
                continue
            last_raw = response.content
            # 提取 JSON 部分
            extracted = _safe_json_parse(response.content)
            if isinstance(extracted, dict):
                # 仅保留 dimensions 中的 key
                return {k: str(v) for k, v in extracted.items() if k in dimensions}
        except (LLMUnavailableError, Exception):
            continue

    return None


def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """容错解析 LLM JSON 输出（去掉 ```json ``` 包裹等）。"""
    import json
    if not text:
        return None
    # 去 markdown code block
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # 找第一个 \n 之后到末尾 ``` 之前
        first_nl = cleaned.find("\n")
        if first_nl > 0:
            cleaned = cleaned[first_nl + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3]
    cleaned = cleaned.strip()
    # 找第一个 { 到最后一个 }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    blob = cleaned[start: end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def _extract_main_finding(abstract: str) -> str:
    """从摘要中提取「主要发现」相关句子。"""
    if not abstract:
        return ""
    # 寻找含「显示/发现/表明/results showed/findings indicate」的句子
    sentences = re.split(r"[。.!?！？]", abstract)
    keywords = ["显示", "发现", "表明", "结果", "found", "showed", "indicated", "revealed", "results"]
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        for kw in keywords:
            if kw.lower() in s.lower():
                return s[:120]
    # fallback：取前 120 字
    return abstract[:120]


def _extract_limitations(abstract: str) -> str:
    if not abstract:
        return ""
    sentences = re.split(r"[。.!?！？]", abstract)
    keywords = ["局限", "limitation", "limited", "constrained", "drawback", "caveat"]
    for s in sentences:
        s = s.strip()
        for kw in keywords:
            if kw.lower() in s.lower():
                return s[:120]
    return ""


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

def export_matrix_csv(
    matrix: LiteratureMatrix,
    literature_lookup: Optional[Dict[str, LiteratureItem]] = None,
) -> str:
    """导出矩阵为 CSV 字符串。第一列为文献标题（如有 lookup）或 key。"""
    output = io.StringIO()
    writer = csv.writer(output)
    header = ["文献"] + list(matrix.dimensions)
    writer.writerow(header)

    for lit_key, row in matrix.cells.items():
        first_col = lit_key
        if literature_lookup and lit_key in literature_lookup:
            item = literature_lookup[lit_key]
            first_author = item.authors[0] if item.authors else "Unknown"
            first_col = f"{first_author} ({item.year}) — {item.title[:40]}"
        line = [first_col] + [row.get(d, "") for d in matrix.dimensions]
        writer.writerow(line)
    return output.getvalue()


def render_matrix_html(
    matrix: LiteratureMatrix,
    literature_lookup: Optional[Dict[str, LiteratureItem]] = None,
) -> str:
    """渲染为 HTML 表格（Streamlit st.markdown(unsafe_allow_html=True) 用）。"""
    html: List[str] = []
    html.append('<table style="border-collapse:collapse;width:100%;font-size:0.9em;">')
    html.append("<thead><tr>")
    html.append('<th style="border:1px solid #ddd;padding:6px;background:#f0f0f0;">文献</th>')
    for d in matrix.dimensions:
        html.append(
            f'<th style="border:1px solid #ddd;padding:6px;background:#f0f0f0;">{d}</th>'
        )
    html.append("</tr></thead>")
    html.append("<tbody>")
    for lit_key, row in matrix.cells.items():
        is_highlight = lit_key in matrix.highlighted_keys
        bg = "#fff8e7" if is_highlight else "#fff"
        title_cell = lit_key
        if literature_lookup and lit_key in literature_lookup:
            item = literature_lookup[lit_key]
            first_author = item.authors[0] if item.authors else "?"
            title_cell = f"{first_author} ({item.year})"
        html.append(f'<tr style="background:{bg};">')
        html.append(f'<td style="border:1px solid #ddd;padding:6px;font-weight:bold;">{title_cell}</td>')
        for d in matrix.dimensions:
            cell = row.get(d, "")
            html.append(f'<td style="border:1px solid #ddd;padding:6px;">{cell}</td>')
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)
