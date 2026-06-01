"""AI 题目预审：4 位"模拟专家"对量表题目相关性平行打分 + 改进建议。

⚠ 重要：本模块输出**非正式 CVI**。CVI 公式假设专家独立判断，多 persona 同模型
的相关接近 1.0，I-CVI / S-CVI / 修正 κ* 在此场景下失去统计意义。
此处仅作为送给真专家做内容效度（CVI）评定**之前**的预审工具，识别"明显不
对劲"的题目，节省真专家时间。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.llm_gateway import LLMUnavailableError, llm_chat


# ---------------------------------------------------------------------------
# 4 位模拟专家 persona
# ---------------------------------------------------------------------------

PERSONAS: List[Dict[str, str]] = [
    {
        "role": "clinical",
        "name_zh": "临床实践派",
        "system": (
            "你是从业 15 年的临床心理学家。"
            "关注题目能否被被试理解、是否会触发防御性回答、表述是否符合临床访谈语境。"
        ),
    },
    {
        "role": "measurement",
        "name_zh": "测量学派",
        "system": (
            "你是心理测量学博士。"
            "关注题目对构念的边界覆盖度、是否双重负载（double-barreled）、"
            "题目方差是否充足、是否会出现地板/天花板效应。"
        ),
    },
    {
        "role": "applied",
        "name_zh": "应用研究派",
        "system": (
            "你是组织/教育/健康心理学应用研究者。"
            "关注题目在真实应用场景下是否可用、是否会因情境（行业、年龄段、文化）"
            "差异而失效、是否能区分关键人群。"
        ),
    },
    {
        "role": "linguistic",
        "name_zh": "语言学派",
        "system": (
            "你是中文语言学博士。"
            "关注题目语法、是否歧义、是否双重否定、用词正式度、"
            "估测阅读年级是否符合目标受众。"
        ),
    },
]


@dataclass
class AIItemReviewResult:
    """AI 题目预审结果。"""
    test_type: str = "ai_item_review"
    construct_name: str = ""
    construct_definition: str = ""
    kb_definition_used: Optional[str] = None
    n_personas: int = 4
    n_personas_succeeded: int = 0
    n_items: int = 0
    items_table: Optional[pd.DataFrame] = None
    persona_long: Optional[pd.DataFrame] = None
    flagged_items: List[str] = field(default_factory=list)
    summary_markdown: str = ""
    warnings: List[str] = field(default_factory=list)
    # v4.2 维度模式
    dimensions: Optional[List[Dict[str, Any]]] = None
    dimension_summary: Optional[pd.DataFrame] = None


# ---------------------------------------------------------------------------
# JSON 解析（数组）
# ---------------------------------------------------------------------------

def _safe_json_parse_array(text: str) -> Optional[List[Dict[str, Any]]]:
    """容错解析 LLM 返回的 JSON 数组。

    剥 markdown ```json``` 包裹 → 找首个 [ 与最末 ] → json.loads。
    """
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_nl = cleaned.find("\n")
        if first_nl > 0:
            cleaned = cleaned[first_nl + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return parsed


# ---------------------------------------------------------------------------
# 维度校验
# ---------------------------------------------------------------------------

def _validate_dimensions(dimensions: List[Dict[str, Any]],
                          n_items: int) -> Dict[int, str]:
    """校验 dimensions 结构并返回 item_idx(0-based) → dim_name 映射。

    规则：
    - 每个维度必须有 name 和 definition（非空）
    - item_indices 必须是 0-based 合法索引
    - 一个题目最多归属一个维度（重复归属抛错）
    - 不要求覆盖所有题目（未归属的题目按"未分配"处理，但会警告）
    """
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("dimensions 必须是非空列表。")

    item_to_dim: Dict[int, str] = {}
    seen_names = set()
    for i, d in enumerate(dimensions):
        if not isinstance(d, dict):
            raise ValueError(f"dimensions[{i}] 不是 dict。")
        name = (d.get("name") or "").strip()
        definition = (d.get("definition") or "").strip()
        if not name:
            raise ValueError(f"dimensions[{i}] 缺少 name。")
        if not definition:
            raise ValueError(f"维度【{name}】缺少 definition。")
        if name in seen_names:
            raise ValueError(f"维度名重复：{name}")
        seen_names.add(name)

        idx_list = d.get("item_indices") or []
        if not isinstance(idx_list, (list, tuple)):
            raise ValueError(f"维度【{name}】的 item_indices 必须是列表。")
        for idx in idx_list:
            try:
                idx_i = int(idx)
            except (TypeError, ValueError):
                raise ValueError(f"维度【{name}】含非整数题号：{idx}")
            if idx_i < 0 or idx_i >= n_items:
                raise ValueError(
                    f"维度【{name}】题号越界：{idx_i}（有效 0..{n_items - 1}）"
                )
            if idx_i in item_to_dim:
                raise ValueError(
                    f"题号 {idx_i} 同时归属【{item_to_dim[idx_i]}】"
                    f"和【{name}】，每题只能归属一个维度。"
                )
            item_to_dim[idx_i] = name

    return item_to_dim


# ---------------------------------------------------------------------------
# Prompt 构造
# ---------------------------------------------------------------------------

def _build_prompt(persona: Dict[str, str],
                  items: List[str],
                  construct_name: str,
                  construct_definition: str,
                  kb_definition: Optional[str] = None,
                  dimensions: Optional[List[Dict[str, Any]]] = None,
                  item_to_dim: Optional[Dict[int, str]] = None) -> List[Dict[str, str]]:
    """构造单 persona 的 prompt（system + user）。

    若提供 dimensions / item_to_dim，则启用维度模式：每题在序号后标维度标签，
    顶部列出维度结构与定义；评分依据从"对总构念"切到"对所属维度"。
    """
    has_dims = bool(dimensions) and bool(item_to_dim)
    if has_dims:
        items_block = "\n".join(
            f"{i + 1}. [{item_to_dim.get(i, '未分配')}] {item}"
            for i, item in enumerate(items)
        )
    else:
        items_block = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))

    kb_block = ""
    if kb_definition:
        kb_block = f"\nKB 参考定义：{kb_definition}\n"

    if has_dims:
        dim_lines = []
        for d in dimensions:
            dname = d.get("name", "")
            ddef = d.get("definition", "")
            extra = d.get("note", "") or ""
            line = f"- 维度【{dname}】：{ddef}"
            if extra:
                line += f"（{extra}）"
            dim_lines.append(line)
        dim_block = "\n".join(dim_lines)

        scoring_rule = (
            "评分标准：1=完全无关，2=关联但表述不当，3=相关，4=高度相关\n"
            "评分依据：题目与其【所属维度】的相关性（不是与总构念）。\n"
            "重要：若某维度是研究者基于多个理论融合或本研究创新提出，请按维度定义本身\n"
            "判断契合度，不要因为它超出经典构念边界就扣分。"
        )
        construct_block = (
            f"总构念：{construct_name}\n"
            f"总构念定义：{construct_definition}{kb_block}\n\n"
            f"维度结构（共 {len(dimensions)} 个维度）：\n{dim_block}\n"
        )
        items_lead = "题目（按序号；方括号内为所属维度）："
    else:
        scoring_rule = "评分标准：1=完全无关，2=关联但表述不当，3=相关，4=高度相关"
        construct_block = (
            f"构念名：{construct_name}\n"
            f"用户提供定义：{construct_definition}{kb_block}"
        )
        items_lead = "题目（按序号）："

    user_msg = (
        f"你是 {persona['name_zh']}。{persona['system']}\n\n"
        f"请对以下 {len(items)} 道题进行相关性评分。\n"
        f"{scoring_rule}\n\n"
        f"{construct_block}\n"
        f"{items_lead}\n{items_block}\n\n"
        "请输出严格 JSON 数组（每题一个对象），不要任何其他文字、不要加 ```json``` 包裹。\n"
        "格式如下：\n"
        '[\n'
        '  {"item_idx": 1, "relevance": 4, "suggestion": ""},\n'
        '  {"item_idx": 2, "relevance": 2, "suggestion": "若 relevance<4，给出具体的≤80字改进建议；否则空字符串"}\n'
        ']'
    )

    return [
        {"role": "system", "content": persona["system"]},
        {"role": "user", "content": user_msg},
    ]


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def ai_content_review(
    items: List[str],
    construct_name: str,
    construct_definition: str,
    *,
    kb_definition: Optional[str] = None,
    n_personas: int = 4,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    dimensions: Optional[List[Dict[str, Any]]] = None,
) -> AIItemReviewResult:
    """AI 模拟 4 位专家对题目做相关性预审。

    Args:
        items: 题目列表（每条一道题）
        construct_name: 构念名
        construct_definition: 构念定义（用户提供）
        kb_definition: 可选的 KB 参考定义
        n_personas: 使用的 persona 数（默认 4，截取前 N 个）
        llm_config: LLM 配置（测试注入）
        requests_module: requests 模块（测试注入 mock）
        progress_callback: 进度回调 callback(idx, name_zh)
        dimensions: 可选维度列表，启用"分维度评分"模式。每个 dict:
            ``{"name": str, "definition": str, "item_indices": List[int],
            "note": str (可选,如"本研究创新")}``。``item_indices`` 是 0-based。
            未传则按单一构念评分（向后兼容）。

    Returns:
        AIItemReviewResult

    Raises:
        ValueError: items 数量不足或参数缺失，或 dimensions 校验失败
        LLMUnavailableError: 全部 persona 调用失败
    """
    if not items or len(items) < 1:
        raise ValueError("题目列表为空。")
    if not construct_name or not construct_definition:
        raise ValueError("构念名和构念定义都必填。")

    n_items = len(items)
    item_to_dim: Optional[Dict[int, str]] = None
    if dimensions:
        item_to_dim = _validate_dimensions(dimensions, n_items)

    chosen_personas = PERSONAS[: max(1, min(n_personas, len(PERSONAS)))]

    result = AIItemReviewResult(
        test_type="ai_item_review",
        construct_name=construct_name,
        construct_definition=construct_definition,
        kb_definition_used=kb_definition,
        n_personas=len(chosen_personas),
        n_items=n_items,
        dimensions=list(dimensions) if dimensions else None,
    )

    # persona × item → relevance / suggestion
    persona_scores: Dict[str, Dict[int, int]] = {}
    persona_suggestions: Dict[str, Dict[int, str]] = {}

    for idx, persona in enumerate(chosen_personas):
        if progress_callback:
            try:
                progress_callback(idx, persona["name_zh"])
            except Exception:
                pass

        messages = _build_prompt(persona, items, construct_name,
                                 construct_definition, kb_definition,
                                 dimensions=dimensions,
                                 item_to_dim=item_to_dim)

        try:
            response = llm_chat(
                messages,
                temperature=0.3,
                retries=1,
                llm_config=llm_config,
                requests_module=requests_module,
            )
        except LLMUnavailableError as exc:
            result.warnings.append(
                f"persona「{persona['name_zh']}」LLM 调用失败：{exc}"
            )
            continue
        except Exception as exc:
            result.warnings.append(
                f"persona「{persona['name_zh']}」未预期错误：{exc}"
            )
            continue

        if not response.ok:
            result.warnings.append(
                f"persona「{persona['name_zh']}」返回空内容。"
            )
            continue

        parsed = _safe_json_parse_array(response.content)
        if parsed is None:
            result.warnings.append(
                f"persona「{persona['name_zh']}」JSON 解析失败，已跳过。"
            )
            continue

        scores: Dict[int, int] = {}
        suggestions: Dict[int, str] = {}
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            try:
                idx_1based = int(entry.get("item_idx"))
                rel = int(entry.get("relevance"))
            except (TypeError, ValueError):
                continue
            if idx_1based < 1 or idx_1based > n_items:
                continue
            if rel < 1 or rel > 4:
                continue
            scores[idx_1based] = rel
            sug = entry.get("suggestion", "")
            suggestions[idx_1based] = str(sug) if sug else ""

        if not scores:
            result.warnings.append(
                f"persona「{persona['name_zh']}」未返回任何有效评分。"
            )
            continue

        persona_scores[persona["name_zh"]] = scores
        persona_suggestions[persona["name_zh"]] = suggestions
        result.n_personas_succeeded += 1

    if result.n_personas_succeeded == 0:
        raise LLMUnavailableError(
            f"全部 {len(chosen_personas)} 位 AI 专家调用失败。"
            f"详情：{'; '.join(result.warnings) or '未知错误'}"
        )

    # 聚合：构造 items_table
    persona_names = [p["name_zh"] for p in chosen_personas]
    rows: List[Dict[str, Any]] = []
    long_rows: List[Dict[str, Any]] = []
    flagged: List[str] = []

    for i, item_text in enumerate(items, start=1):
        row: Dict[str, Any] = {"序号": i, "题目": item_text}
        if item_to_dim is not None:
            row["维度"] = item_to_dim.get(i - 1, "未分配")
        scores_for_item: List[int] = []
        suggestion_chunks: List[str] = []

        for pname in persona_names:
            scores = persona_scores.get(pname, {})
            sugs = persona_suggestions.get(pname, {})
            if i in scores:
                row[pname] = scores[i]
                scores_for_item.append(scores[i])
                long_rows.append({
                    "题目序号": i,
                    "题目": item_text,
                    "persona": pname,
                    "relevance": scores[i],
                    "suggestion": sugs.get(i, ""),
                })
                if sugs.get(i):
                    suggestion_chunks.append(f"[{pname}] {sugs[i]}")
            else:
                row[pname] = np.nan

        if scores_for_item:
            avg = float(np.mean(scores_for_item))
            disagreement = int(max(scores_for_item) - min(scores_for_item))
        else:
            avg = float("nan")
            disagreement = 0

        row["平均"] = round(avg, 2) if not np.isnan(avg) else "-"
        row["分歧"] = disagreement
        row["改进建议"] = "；".join(suggestion_chunks) if suggestion_chunks else ""

        if scores_for_item:
            if avg < 3.0 or disagreement >= 2:
                flagged.append(item_text)

        rows.append(row)

    if item_to_dim is not None:
        columns = ["序号", "题目", "维度"] + persona_names + ["平均", "分歧", "改进建议"]
    else:
        columns = ["序号", "题目"] + persona_names + ["平均", "分歧", "改进建议"]
    result.items_table = pd.DataFrame(rows, columns=columns)
    result.persona_long = pd.DataFrame(long_rows) if long_rows else None
    result.flagged_items = flagged

    if item_to_dim is not None and dimensions:
        result.dimension_summary = _build_dimension_summary(
            result.items_table, dimensions, flagged
        )

    result.summary_markdown = _build_markdown_report(result, items)

    return result


def _build_dimension_summary(items_table: pd.DataFrame,
                              dimensions: List[Dict[str, Any]],
                              flagged: List[str]) -> pd.DataFrame:
    """按维度聚合：题数 / 平均分 / 标记题数 / 维度定义。"""
    flagged_set = set(flagged)
    rows: List[Dict[str, Any]] = []
    for d in dimensions:
        name = d.get("name", "")
        sub = items_table[items_table["维度"] == name]
        if sub.empty:
            mean_val = float("nan")
            n_flag = 0
        else:
            avg_series = pd.to_numeric(sub["平均"], errors="coerce")
            mean_val = float(avg_series.mean()) if not avg_series.empty else float("nan")
            n_flag = int(sub["题目"].isin(flagged_set).sum())
        rows.append({
            "维度": name,
            "题数": int(len(sub)),
            "维度均分": round(mean_val, 2) if not np.isnan(mean_val) else "-",
            "标记题数": n_flag,
            "维度定义": d.get("definition", ""),
            "备注": d.get("note", "") or "",
        })
    return pd.DataFrame(rows, columns=["维度", "题数", "维度均分", "标记题数", "维度定义", "备注"])


# ---------------------------------------------------------------------------
# Markdown 报告生成
# ---------------------------------------------------------------------------

def _build_markdown_report(result: AIItemReviewResult,
                            items: List[str]) -> str:
    """生成可下载的 Markdown 报告（顶部强提醒此非正式 CVI）。"""
    lines: List[str] = []
    lines.append("# AI 题目预审报告")
    lines.append("")
    lines.append(
        "> ⚠️ 此报告为 **AI 模拟专家预审**，**不是**正式内容效度（CVI）证据。"
        "请送真领域专家确认后再写入论文方法学。"
    )
    lines.append("")
    lines.append(f"**构念**：{result.construct_name}")
    lines.append(f"**用户提供定义**：{result.construct_definition}")
    if result.kb_definition_used:
        lines.append(f"**KB 参考定义**：{result.kb_definition_used}")
    lines.append(
        f"**题目数**：{result.n_items} | "
        f"**模拟专家数**：{result.n_personas_succeeded}/{result.n_personas}"
    )
    lines.append(f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if result.items_table is not None and not result.items_table.empty:
        df = result.items_table
        avg_series = pd.to_numeric(df["平均"], errors="coerce")
        n_pass = int((avg_series >= 3.0).sum())
        lines.append("## 整体摘要")
        lines.append("")
        lines.append(f"- 平均相关性 ≥ 3 的题数：{n_pass} / {result.n_items}")
        lines.append(f"- 标记需修订题数（平均<3 或分歧≥2）：{len(result.flagged_items)}")
        lines.append("")

        if result.dimension_summary is not None and not result.dimension_summary.empty:
            lines.append("## 维度级摘要")
            lines.append("")
            ds = result.dimension_summary
            cols = list(ds.columns)
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("|" + "|".join(["---"] * len(cols)) + "|")
            for _, drow in ds.iterrows():
                cells = [str(drow[c]) if pd.notna(drow[c]) else "-" for c in cols]
                cells = [c.replace("|", "\\|").replace("\n", " ") for c in cells]
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")

        # 题目级表格
        lines.append("## 题目级评分")
        lines.append("")
        cols = list(df.columns)
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for _, row in df.iterrows():
            cells = [str(row[c]) if pd.notna(row[c]) else "-" for c in cols]
            cells = [c.replace("|", "\\|").replace("\n", " ") for c in cells]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    if result.flagged_items:
        lines.append("## 标记需修订的题目")
        lines.append("")
        df = result.items_table
        for it in result.flagged_items:
            sub = df[df["题目"] == it]
            if sub.empty:
                continue
            row = sub.iloc[0]
            avg = row.get("平均", "-")
            dis = row.get("分歧", "-")
            sug = row.get("改进建议", "")
            lines.append(f"- **{it}** — 平均 {avg}，分歧 {dis}")
            if sug:
                lines.append(f"  - 建议：{sug}")
        lines.append("")

    if result.warnings:
        lines.append("## 调用提示")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append("*本报告由 AI 模拟生成，不构成正式效度证据。*")
    return "\n".join(lines)
