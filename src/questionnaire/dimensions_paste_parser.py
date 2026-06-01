"""维度文本粘贴解析（v4.4）。

把用户粘贴的"维度结构"文本解析为 dimensions data_editor 的 DataFrame。

支持 4 种粘贴格式（按检测优先级）：
    1. **Markdown 表格** — `| 维度名 | 维度定义 | 题号 | 备注 |`，自动跳分隔行 / 表头
    2. **Tab 分隔（Excel/Notion 复制）** — 字段间用 \\t
    3. **CSV** — 字段间用半角 `,`（题号字段需用引号包住）
    4. **段落键值** — 多行 `维度名: ...\\n定义: ...\\n题号: 1,2`（用空行分维度）

题号字段同时支持：
- 半/全角逗号、顿号 `1,2,3` / `1，2，3` / `1、2、3`
- 范围 `1-3` / `1~3` / `1～3`
- 题号前缀 `题1` / `Q1` / `第1题`（前后缀会被剥离）

所有解析失败都不抛异常，只返回 (DataFrame|None, errors_list)。
UI 端可以把 errors 当 warnings 显示给用户。
"""
from __future__ import annotations

import csv
import io
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd


# 与 _render_dimension_editor 中 column 名严格对齐
_COL_NAME = "维度名"
_COL_DEF = "维度定义"
_COL_INDICES = "题号（1-based，逗号分隔）"
_COL_NOTE = "备注"

_HEADER_KEYWORDS_NAME = ("维度名", "名称", "name", "维度")
_HEADER_KEYWORDS_DEF = ("维度定义", "定义", "definition", "desc")
_HEADER_KEYWORDS_INDICES = ("题号", "题目", "items", "indices")
_HEADER_KEYWORDS_NOTE = ("备注", "note", "remark", "说明")


# ---------------------------------------------------------------------------
# 题号字符串 → List[int]
# ---------------------------------------------------------------------------

def parse_indices_text(s: str, n_items: int) -> Tuple[List[int], List[str]]:
    """把题号文本解析为 1-based int 列表（去重保序）。

    Args:
        s: 题号文本（'1,2,3' / '1-3' / '题1, Q2' 等）
        n_items: 全量题数，越界会进 errors

    Returns:
        (indices, errors)。errors 为友好中文提示。
    """
    out: List[int] = []
    errors: List[str] = []
    if not s:
        return out, errors

    # 中文标点 → 英文标点
    text = (
        s.replace("，", ",")
         .replace("、", ",")
         .replace("～", "-")
         .replace("~", "-")
    )
    # 剥离常见前后缀
    text = re.sub(r"[题QqＱ第]", "", text)
    text = text.replace("Question", "")

    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "-" in tok:
            try:
                a, b = tok.split("-", 1)
                ai, bi = int(a.strip()), int(b.strip())
                if ai > bi:
                    ai, bi = bi, ai
                for k in range(ai, bi + 1):
                    if k < 1:
                        errors.append(f"题号 {k} 无效（必须 ≥ 1）")
                        continue
                    if k > n_items:
                        errors.append(f"题号 {k} 超出范围（1..{n_items}）")
                        continue
                    if k not in out:
                        out.append(k)
            except ValueError:
                errors.append(f"无法解析范围「{tok}」")
        else:
            try:
                k = int(tok)
            except ValueError:
                errors.append(f"无法解析题号「{tok}」")
                continue
            if k < 1:
                errors.append(f"题号 {k} 无效（必须 ≥ 1）")
                continue
            if k > n_items:
                errors.append(f"题号 {k} 超出范围（1..{n_items}）")
                continue
            if k not in out:
                out.append(k)
    return out, errors


# ---------------------------------------------------------------------------
# 表头 / 分隔行检测
# ---------------------------------------------------------------------------

def _is_separator_row(cells: List[str]) -> bool:
    """Markdown 表格分隔行：每个 cell 只含 -:= 空白。"""
    non_empty = [c for c in cells if c.strip()]
    if not non_empty:
        return False
    return all(set(c.strip()) <= set("-:= ") for c in non_empty)


def _is_header_row(cells: List[str]) -> bool:
    """第一个非空 cell 含表头关键词且整行较短（避免误伤数据行）。"""
    if not cells:
        return False
    first = cells[0].strip().lower()
    if not first:
        return False
    for kw in _HEADER_KEYWORDS_NAME:
        kw_low = kw.lower()
        if first == kw_low:
            return True
        # 仅当 cell 不太长时允许"包含"匹配，避免数据行被吞掉
        if kw_low in first and len(first) <= 8:
            return True
    return False


def _cells_to_row(cells: List[str]) -> Dict[str, str]:
    """3-4 列 cells → DataFrame 一行的 dict。"""
    cells = [c.strip() for c in cells]
    name = cells[0] if len(cells) >= 1 else ""
    definition = cells[1] if len(cells) >= 2 else ""
    indices = cells[2] if len(cells) >= 3 else ""
    note = cells[3] if len(cells) >= 4 else ""
    return {
        _COL_NAME: name,
        _COL_DEF: definition,
        _COL_INDICES: indices,
        _COL_NOTE: note,
    }


def _empty_row() -> Dict[str, str]:
    return {_COL_NAME: "", _COL_DEF: "", _COL_INDICES: "", _COL_NOTE: ""}


# ---------------------------------------------------------------------------
# 各格式解析
# ---------------------------------------------------------------------------

def _parse_markdown_table(text: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.count("|") < 2:
            continue
        # 切单元
        cells = [c.strip() for c in line.strip("|").split("|")]
        if _is_separator_row(cells):
            continue
        if _is_header_row(cells):
            continue
        if not any(cells):
            continue
        rows.append(_cells_to_row(cells))
    return rows


def _parse_tab_separated(text: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("\t")]
        if _is_header_row(cells):
            continue
        rows.append(_cells_to_row(cells))
    return rows


def _parse_csv(text: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    reader = csv.reader(io.StringIO(text))
    for cells in reader:
        cells = [c.strip() for c in cells]
        if not any(cells):
            continue
        if _is_header_row(cells):
            continue
        rows.append(_cells_to_row(cells))
    return rows


def _parse_paragraph_kv(text: str) -> List[Dict[str, str]]:
    """段落键值格式：

        上级互动
        定义：在上级面前的紧张感
        题号：1, 2
        备注：本研究创新

        客户回避
        定义：...
        ...

    维度之间用空行分隔；第一行（无键）当维度名。
    """
    rows: List[Dict[str, str]] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    kv_pat = re.compile(r"^\s*([一-龥A-Za-z]+)\s*[：:]\s*(.*)$")

    for block in blocks:
        if not block.strip():
            continue
        cur = _empty_row()
        first_line_is_name = False
        for i, raw in enumerate(block.splitlines()):
            line = raw.strip().lstrip("-•*").strip()
            if not line:
                continue
            m = kv_pat.match(line)
            if m:
                key = m.group(1).strip().lower()
                val = m.group(2).strip()
                if any(kw in key or key in kw for kw in _HEADER_KEYWORDS_NAME):
                    cur[_COL_NAME] = val
                elif any(kw in key or key in kw for kw in _HEADER_KEYWORDS_DEF):
                    cur[_COL_DEF] = val
                elif any(kw in key or key in kw for kw in _HEADER_KEYWORDS_INDICES):
                    cur[_COL_INDICES] = val
                elif any(kw in key or key in kw for kw in _HEADER_KEYWORDS_NOTE):
                    cur[_COL_NOTE] = val
                # 未识别的 key 暂忽略
            else:
                # 没有冒号：把第一行当维度名（含可能的括号定义）
                if not first_line_is_name and not cur[_COL_NAME]:
                    # 形如 "上级互动（在上级面前的紧张感）"
                    paren_match = re.match(r"^([^（(]+)[（(]([^）)]+)[）)]\s*(.*)$", line)
                    if paren_match:
                        cur[_COL_NAME] = paren_match.group(1).strip()
                        cur[_COL_DEF] = paren_match.group(2).strip()
                        # 剩余可能是题号
                        rest = paren_match.group(3).strip()
                        if rest:
                            cur[_COL_INDICES] = rest
                    else:
                        # 形如 "1. 上级互动" 或 "上级互动"
                        cleaned = re.sub(r"^\d+[.、)）]\s*", "", line)
                        cur[_COL_NAME] = cleaned
                    first_line_is_name = True

        if cur[_COL_NAME] or cur[_COL_DEF] or cur[_COL_INDICES]:
            rows.append(cur)

    return rows


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def parse_dimensions_text(
    text: str,
    n_items: int,
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """把粘贴文本解析为维度 DataFrame，列与 _render_dimension_editor 严格对齐。

    Args:
        text: 用户粘贴的多行文本
        n_items: 当前题目总数（用于校验题号越界）

    Returns:
        ``(DataFrame | None, errors_list)``：
        - DataFrame：4 列 ``维度名 / 维度定义 / 题号（1-based，逗号分隔）/ 备注``
          —— 题号会被规整为 ``"1,2,3"`` 这种紧凑形式
        - errors_list：友好提示（包括非致命的 warnings，如部分题号越界）
        - 完全解析失败时返回 ``(None, [...])``
    """
    errors: List[str] = []
    if not text or not text.strip():
        return None, ["粘贴内容为空"]

    # 选解析器：优先级 markdown > tab > csv > paragraph
    has_pipe = any(l.count("|") >= 2 for l in text.splitlines() if l.strip())
    has_tab = any("\t" in l for l in text.splitlines() if l.strip())
    has_kv = bool(re.search(r"[：:]", text)) and "\n" in text.strip()

    raw_rows: List[Dict[str, str]] = []
    parser_used = ""
    if has_pipe:
        raw_rows = _parse_markdown_table(text)
        parser_used = "markdown"
    if not raw_rows and has_tab:
        raw_rows = _parse_tab_separated(text)
        parser_used = "tab"
    if not raw_rows and has_kv:
        raw_rows = _parse_paragraph_kv(text)
        parser_used = "paragraph"
    if not raw_rows:
        # 兜底 CSV
        raw_rows = _parse_csv(text)
        parser_used = "csv"

    if not raw_rows:
        return None, ["未识别到任何维度行；支持的格式：Markdown 表格 / Tab 分隔（Excel）/ CSV / 段落键值"]

    # 规整每行
    cleaned: List[Dict[str, str]] = []
    seen_names: set = set()
    used_indices_global: set = set()

    for r_idx, row in enumerate(raw_rows, start=1):
        name = row.get(_COL_NAME, "").strip()
        definition = row.get(_COL_DEF, "").strip()
        indices_text = row.get(_COL_INDICES, "").strip()
        note = row.get(_COL_NOTE, "").strip()

        if not name:
            errors.append(f"第 {r_idx} 行：维度名为空，已跳过")
            continue
        if name in seen_names:
            errors.append(f"维度【{name}】重复出现，已跳过第 {r_idx} 次")
            continue
        seen_names.add(name)

        # 规整题号：解析后回写紧凑形式
        compact_indices = ""
        if indices_text:
            idx_list, idx_errs = parse_indices_text(indices_text, n_items)
            for e in idx_errs:
                errors.append(f"维度【{name}】：{e}")
            # 去掉与已用题号冲突的部分（先到先得，与 _render_dimension_editor 一致）
            kept = []
            for k in idx_list:
                if k in used_indices_global:
                    errors.append(f"维度【{name}】：题号 {k} 已被前面的维度占用，已跳过")
                    continue
                used_indices_global.add(k)
                kept.append(k)
            compact_indices = ",".join(str(k) for k in kept)
        else:
            errors.append(f"维度【{name}】：题号为空（需要后续手填）")

        cleaned.append({
            _COL_NAME: name,
            _COL_DEF: definition,
            _COL_INDICES: compact_indices,
            _COL_NOTE: note,
        })

    if not cleaned:
        return None, errors or ["无有效维度行"]

    df = pd.DataFrame(cleaned, columns=[_COL_NAME, _COL_DEF, _COL_INDICES, _COL_NOTE])
    # 把使用的解析器作为 attrs 元信息（UI 可以展示），不影响展示
    df.attrs["parser"] = parser_used
    return df, errors
