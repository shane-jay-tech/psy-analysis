"""高质量问卷设计引擎（v3.7.7 直连模式）。

哲学转变：v3.7.6 之前是「5 步流水线」，每步用专注小 prompt 让 LLM 分步输出。
**实测发现拆得越细，LLM 越容易丢失你研究问题的整体语境**——对复杂研究意图（如 HRBP
"基于人岗匹配的用人标准复盘"）反而把研究层次/答题人/题目主语判错。

v3.7.7 改为「直连模式」：
1. **一次性完整调用**：把研究问题原句 + 紧凑设计原则一起发给 LLM，让它用全局智能理解
2. **本地质检**：item_quality.py 检查双重负载/语义重复/弱反向
3. **弱题并行重写**（可选，仅必要时）

调用次数：1-3 次（vs 旧版 7-10 次）；速度：~15-30 秒；质量：通常等于或好于直接对话 LLM。
"""

from __future__ import annotations

import json
import re
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from .construct_kb import CONSTRUCTS
from .item_quality import check_item_quality
from .llm_engine import (
    CancelledLLMError,
    LLMEngineError,
    LLMResponseParseError,
    _alloc_cancel_id,
    _build_design_dict,
    _call_llm,
    _cleanup_cancel_id,
    _is_cancelled,
)


# ---------------------------------------------------------------------------
# Few-shot 高质量题目示例库
# ---------------------------------------------------------------------------

ITEM_FEW_SHOT = """\
## 高质量题目对比（学习这种风格）

### 行为锚定 vs 抽象（好 vs 差）

❌ 差：「我感到焦虑」（太抽象）
✅ 好：「过去一周，我经常因为小事担心而难以入睡」（具体行为+情境+频率）

❌ 差：「我有自尊」（无可观察内容）
✅ 好：「在他人面前发言时，我能保持自己的观点不被轻易动摇」（可观察情境）

❌ 差：「我的工作满意度高」（直接问构念）
✅ 好：「我每天上班路上会期待今天要做的工作」（行为锚定满意度）

### 反向题：错误的"镜像题" vs 正确的"反向情境"

❌ 错误（伪反向）：
  正向：「我对自己感到满意」
  反向：「我对自己不感到满意」  ← 仅加"不"，本质是同一题，会与正向题极强相关

✅ 正确（真反向）：
  正向：「我对自己感到满意」
  反向：「我经常觉得自己一无是处」  ← 描述不同情境/不同强度

❌ 错误：
  正向：「我能控制好自己的情绪」
  反向：「我不能控制好自己的情绪」  ← 镜像

✅ 正确：
  正向：「我能控制好自己的情绪」
  反向：「遇到挫折时我容易情绪崩溃，连自己都吓一跳」  ← 描述失控的具体表现

### 双重负载（必须避免）

❌ 差：「我感到又累又难过」（累 + 难过 = 两个概念）
✅ 好：拆成两题：「我经常感到疲倦」/「我经常感到难过」
"""


# ---------------------------------------------------------------------------
# Prompts（每步独立、短小专注）
# ---------------------------------------------------------------------------

def _parse_research_system_prompt() -> str:
    """Step 0: 研究问题结构化解析。

    v3.7.5: 加入 research_type 识别，区分 object-level 测构念 vs meta-level 评估工具/流程。
    """
    return """你是研究方法学专家。**仔细通读研究问题的整句话**，**不要只抓关键词**。
你的核心任务是判断研究的**真实层次**——别把"评估招聘标准"当成"测员工人岗匹配水平"来设计问卷！

## 🔴 第一步：判断研究层次（最关键）

研究问题分两大类，**对应完全不同的问卷结构**：

### A. construct_measurement（构念测量型，object-level）
**测量某个心理构念在个体身上的水平。**
- 例：「调查大学生的社交焦虑水平」 → 测被试自己的焦虑
- 例：「研究员工人岗匹配感与离职意向」 → 测员工自己感受到的匹配
- 题目主语：**「我...」**

### B. instrument_evaluation（工具/标准评估型，meta-level）
**评估某个工具/流程/标准/政策的质量、有效性、合理性。**
- 例：「基于人岗匹配视角的用人标准复盘」 → 评估**公司招聘标准**（不是测员工匹配感！）
- 例：「评估员工绩效考核体系的合理性」 → 评估**考核体系**（不是测员工绩效）
- 例：「调查现行心理咨询服务的有效性」 → 评估**咨询服务**
- 题目主语：**「我们公司的标准 X...」「现行流程 Y...」**

### C. process_diagnostic（流程诊断型，meta-level 变体）
**诊断组织/系统中某流程哪里出了问题。**
- 例：「招聘流程中候选人体验的薄弱环节诊断」 → 诊断**流程**

### D. multi_perspective_audit（多视角对照型）
**让多个角色（员工/上司/HR）对同一对象评分对照。**
- 例：「HRBP/招聘官/用人部门对人岗匹配标准的认知差异」

## 关键区分提示词

含「**复盘 / 评估 / 审视 / 诊断 / 反思 / 优化 / 合理性 / 有效性**」+ 工具/流程/标准 → **B/C/D meta-level**
含「**水平 / 程度 / 状况 / 影响 / 关系 / 预测**」+ 心理构念 → **A object-level**

## 解析要求

1. **理解整句**：研究者真正想知道什么？测人，还是评估某个东西？
2. **识别评估对象**：如果是 B/C/D 类，**research_object** 必须填具体的工具/流程名（如"用人标准"），而非心理构念名
3. **识别答题人角色**：自评？管理者评下属？HR 评流程？
4. **不要被"理论视角"误导**：「基于 X 视角」中的 X 通常是**框架**（用来组织维度），不是**研究对象**

## 输出（严格 JSON，不要 markdown）

```json
{
  "research_type": "construct_measurement | instrument_evaluation | process_diagnostic | multi_perspective_audit",
  "research_object": "真正被评估/测量的对象（如「用人标准/招聘流程/员工焦虑水平」）",
  "theoretical_framework": "用作组织维度的理论框架（如「人岗匹配 D-A&N-S 模型」），可空",
  "respondent_role": "self（自评） | supervisor（上级评下属） | hr_practitioner（HR 评流程/标准） | recruiter（招聘官） | mixed（多角色）",
  "item_subject_template": "题目主语模板（如「我...」「我们公司的招聘标准...」「现行 X 流程...」）",
  "primary_construct": "本问卷主要测量/评估的对象名（构念测量型填构念名，工具评估型填工具名）",
  "primary_construct_reason": "为什么选这个作为本次问卷设计目标（1-2 句）",
  "all_constructs": ["研究问题里提到的所有构念/对象"],
  "population": "答题者人群（具体到细节，如「初入职场 3 个月内的新员工」「企业 HRBP/招聘负责人」）",
  "context": "研究情境（如「初入职场」「招聘选拔环节」「年度复盘期」），无明显情境写'一般情境'",
  "study_design": "correlational | experimental | cross-sectional | longitudinal | qualitative | diagnostic",
  "key_relationships": ["X→Y 描述", "X 通过 M 影响 Y", "..."],
  "scale_orientation": "state（瞬时状态） | trait（稳定特质） | attitude（态度同意度） | behavior（行为频次） | quality_judgment（对工具/标准的质量判断）",
  "summary": "用 1-2 句话总结这位研究者在研究什么"
}
```

## 范例

输入：「基于'人岗匹配'视角的用人标准复盘（HRBP 视角）」
✅ 正确解析：
- research_type: instrument_evaluation
- research_object: 公司用人标准（招聘选拔标准）
- theoretical_framework: 人岗匹配 D-A&N-S 模型
- respondent_role: hr_practitioner
- item_subject_template: 「我们公司目前的用人标准 X...」
- primary_construct: 用人标准的合理性
- summary: 「以人岗匹配理论为框架，评估当前用人标准是否真正覆盖能力-需要的匹配度」

❌ 错误解析（旧版会犯）：
- primary_construct: 人岗匹配
- item_subject_template: 「我...」
- → 出来一份测员工匹配感的标准量表，跟用户的复盘需求完全跑偏"""


def _parse_research_question(
    research_question: str,
    api_key: str,
    base_url: str,
    model: str,
    *,
    temperature: float,
    timeout: int,
    cancel_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Step 0: 解析研究问题为结构化要素。LLM 失败时返回带默认值的最简结构。"""
    msgs = [
        {"role": "system", "content": _parse_research_system_prompt()},
        {"role": "user", "content": f"研究问题：{research_question}\n\n请按系统提示中的 JSON 格式严格输出。"},
    ]
    try:
        # v3.7.4: 推理模型自动 bump
        _tokens = 4096 if _is_reasoning_model(model) else 1024
        raw = _call_llm(
            msgs, api_key, base_url, model,
            temperature, _tokens, timeout, cancel_id,
        )
        parsed = _parse_json(raw, "research_parse")
        # 必须有 primary_construct
        if not parsed.get("primary_construct"):
            parsed["primary_construct"] = research_question[:30]
        # 兜底字段（含 v3.7.5 新增）
        parsed.setdefault("research_type", "construct_measurement")
        parsed.setdefault("research_object", parsed["primary_construct"])
        parsed.setdefault("theoretical_framework", "")
        parsed.setdefault("respondent_role", "self")
        parsed.setdefault("item_subject_template", "我...")
        parsed.setdefault("all_constructs", [parsed["primary_construct"]])
        parsed.setdefault("population", "一般成人")
        parsed.setdefault("context", "一般情境")
        parsed.setdefault("study_design", "cross-sectional")
        parsed.setdefault("key_relationships", [])
        parsed.setdefault("scale_orientation", "trait")
        parsed.setdefault("summary", research_question)
        parsed.setdefault("primary_construct_reason", "（未提供）")
        return parsed
    except Exception:
        return {
            "research_type": "construct_measurement",
            "research_object": research_question[:30],
            "theoretical_framework": "",
            "respondent_role": "self",
            "item_subject_template": "我...",
            "primary_construct": research_question[:30],
            "primary_construct_reason": "（解析失败，使用研究问题前 30 字作为构念名）",
            "all_constructs": [],
            "population": "一般成人",
            "context": "一般情境",
            "study_design": "cross-sectional",
            "key_relationships": [],
            "scale_orientation": "trait",
            "summary": research_question,
        }


def _format_research_context_for_prompt(parsed: Dict[str, Any]) -> str:
    """把 Step 0 的解析结果格式化为后续 prompt 可吃的上下文段。

    v3.7.5: 加入 research_type / research_object / item_subject_template，
    让后续步骤明确题目主语应该用「我...」还是「我们公司的标准 X...」。
    """
    rt = parsed.get("research_type", "construct_measurement")
    rt_label = {
        "construct_measurement": "🧠 构念测量型（测被试个人状态/特质）",
        "instrument_evaluation": "🛠 工具/标准评估型（评估某工具的合理性/有效性）",
        "process_diagnostic": "🔍 流程诊断型（诊断某流程的薄弱环节）",
        "multi_perspective_audit": "👥 多视角对照型（多角色对同一对象评分）",
    }.get(rt, rt)

    ctx_parts = [
        "## 🔴 研究背景（已从研究问题结构化提取，必须严格遵守）",
        f"- **研究层次**：{rt_label}",
        f"- **真实评估对象**：{parsed.get('research_object', '?')}",
        f"- **答题者角色**：{parsed.get('respondent_role', '?')}",
        f"- **题目主语模板**：{parsed.get('item_subject_template', '我...')}",
    ]
    if parsed.get("theoretical_framework"):
        ctx_parts.append(f"- **理论框架（用作组织维度，不是测量对象）**：{parsed['theoretical_framework']}")
    ctx_parts.extend([
        f"- **本问卷主名**：{parsed.get('primary_construct', '?')}",
        f"  └ 选择理由：{parsed.get('primary_construct_reason', '')}",
        f"- **目标人群（答题者）**：{parsed.get('population', '?')}",
        f"- **研究情境**：{parsed.get('context', '?')}",
        f"- **研究设计**：{parsed.get('study_design', '?')}",
        f"- **量表导向**：{parsed.get('scale_orientation', '?')}",
    ])
    rels = parsed.get("key_relationships") or []
    if rels:
        ctx_parts.append(f"- **核心关系**：{' / '.join(rels)}")
    other_constructs = [
        c for c in (parsed.get("all_constructs") or [])
        if c != parsed.get("primary_construct")
    ]
    if other_constructs:
        ctx_parts.append(f"- **其他相关构念**：{', '.join(other_constructs)}")
    summary = parsed.get("summary") or ""
    if summary:
        ctx_parts.append(f"- **研究意图**：{summary}")

    # v3.7.5 关键警示
    if rt in ("instrument_evaluation", "process_diagnostic"):
        ctx_parts.append("")
        ctx_parts.append(
            "## ⚠️ 工具/流程评估型研究专属规则\n"
            "1. 所有题目必须用 **「我们公司的 X / 现行流程 X / 招聘标准 X」** 等指代评估对象\n"
            "2. **绝对禁止** 写成「我感到...」「我表现出...」这种自评心理状态题\n"
            "3. 维度应按「评估对象的不同方面」划分（如标准的全面性/有效性/可操作性/一致性），\n"
            "   而不是按「被测构念的子维度」\n"
            "4. 量表导向应是 **quality_judgment**（质量判断），用同意度量表"
        )
    elif rt == "multi_perspective_audit":
        ctx_parts.append("")
        ctx_parts.append(
            "## ⚠️ 多视角对照型研究专属规则\n"
            "题目应表述为对**评估对象**的判断（如「标准 X 能有效预测候选人胜任力」），"
            "而非个人状态。"
        )

    return "\n".join(ctx_parts)


def _skeleton_system_prompt(parsed: Optional[Dict[str, Any]] = None) -> str:
    """Step 1: 仅生成构念骨架（不生成题目）。

    v3.7.3: 接收 Step 0 的解析结果，让 skeleton 设计紧扣研究人群/情境/导向。
    """
    parts = [
        "你是心理测量学专家。根据研究问题与解析后的研究背景，**仅设计构念骨架**（不生成题目）。\n",
    ]
    # v3.7.3: 注入研究背景（最关键改进）
    if parsed:
        parts.append(_format_research_context_for_prompt(parsed))
        parts.append("")
        parts.append(
            "**核心要求**：\n"
            "- 你设计的维度必须**紧扣研究人群和情境**，而非通用版本\n"
            f"- 例如人群是「{parsed.get('population', '?')}」，"
            f"维度的 desc 应明确说明「适用于该人群在 {parsed.get('context', '?')} 下」\n"
            f"- 量表导向是 {parsed.get('scale_orientation', 'trait')}，"
            "测特质就别用频率量表，测状态就别用同意度\n"
        )
    parts.extend([
        "",
        "## 量表点数选择规则",
        "- 临床/健康（焦虑/抑郁等）：4 点频率量表（避免中间倾向）",
        "- 人格/社会（自尊/支持等）：5 点同意度量表",
        "- 态度/幸福感等宽泛构念：7 点同意度量表",
        "",
        "## 🔴 关键规则：理论丰富的构念必须分解到「可操作的子维度」",
        "",
        "**绝对禁止**：仅给出 2-3 个**抽象的一级维度**就停。",
        "只要构念背后有成熟理论框架（如人岗匹配/工作满意度/职业倦怠/依恋等），",
        "**必须把一级维度继续下钻为可直接出题的具体子维度**。",
        "",
        "### ❌ 差范例（理论分解不足，不要这样做）",
        "构念「人岗匹配」→ 维度只列：",
        "- 要求-能力匹配（D-A fit）",
        "- 需要-供给匹配（N-S fit）",
        "→ 这两个维度太宽泛，每个维度内部混杂多个独立构念，因子分析会拆。",
        "",
        "### ✅ 好范例（理论充分分解）",
        "构念「人岗匹配」→ 6-8 个具体子维度：",
        "- 要求-能力·知识匹配（个人知识储备与岗位需求匹配）",
        "- 要求-能力·技能匹配（技能水平匹配）",
        "- 要求-能力·能力匹配（认知/人际/动手能力匹配）",
        "- 要求-能力·经验匹配（工作经验匹配）",
        "- 需要-供给·物质回报（薪酬/福利与个人需要匹配）",
        "- 需要-供给·社交回报（人际关系/团队氛围匹配）",
        "- 需要-供给·自我实现（成长机会/自主性匹配）",
        "- 需要-供给·工作环境（物理环境/工作时间匹配）",
        "",
        "### 其他范例",
        "- 「职业倦怠」（Maslach 三因素）→ 情绪耗竭、去个性化、个人成就感降低（3 维度足够，已成熟）",
        "- 「工作满意度」（JDI 模型）→ 工作内容、薪酬、晋升、上司、同事 5 维度",
        "- 「焦虑」（4 因素）→ 认知焦虑、情感焦虑、生理焦虑、行为焦虑 4 维度",
        "",
        "## 判断是否继续下钻的准则",
        "1. 看一级维度的描述：如果一句话能完整说清这个维度的可观察行为 → 不需要下钻",
        "2. 如果描述里包含「包括 X、Y、Z」「涵盖多个方面」→ **必须下钻**",
        "3. 如果一级维度对应的成熟量表通常有子量表（subscale）→ **必须下钻**",
        "4. 一级维度对应的题目超过 6 题才能覆盖 → **必须下钻**",
        "",
        "## 维度设计原则",
        "- **总维度数 4-8**（理论丰富时偏向 6-8，简单时 3-5）",
        "- 每维度内容**彼此独立**（不交叉、不重叠）",
        "- 每维度**题数 3-5**（题量少是因为已经下钻得够细）",
        "",
        "## 参考已有构念库",
    ])
    # 短摘要每个 KB 构念
    for cname, c in list(CONSTRUCTS.items())[:30]:    # 截断避免 prompt 过长
        parts.append(f"- {cname}（{c.get('name_en', '')}）：{c.get('definition', '')[:80]}")
    parts.append("")
    parts.append("## 输出（严格 JSON，不要 markdown）")
    parts.append(json.dumps({
        "construct_name": "中文构念名（2-6 字）",
        "construct_name_en": "English Name",
        "domain": "临床与健康/人格/社会心理/教育心理/认知/组织行为/发展/其他",
        "definition": "学术定义 2-3 句",
        "theory_framework": "理论框架名（如 Maslach 倦怠三因素 / Edwards 人岗匹配 D-A&N-S 模型 / JDI 工作满意度）",
        "dimensions": [
            # 注：name 应为「可直接出题的具体子维度」名，不要写抽象的一级维度名！
            # 如「要求-能力·知识匹配」，而非笼统的「要求-能力匹配」
            {
                "name": "可操作的具体子维度名（含一级分组前缀）",
                "desc": "维度描述：定义 + 涵盖的具体观察内容（不要笼统）",
                "parent_dimension": "一级分组名（可选；下钻时写，扁平时空字符串）",
                "item_count": 4,
            }
        ],
        "scale_type": "likert_agreement / frequency / semantic_differential",
        "scale_points": 5,
        "scale_type_label": "agreement / frequency / satisfaction",
        "anchor_labels": ["1=...", "2=...", "..."],
        "match_reason": "为何这样分维度（说明用了哪个理论框架，是否充分下钻到子维度）",
    }, ensure_ascii=False, indent=2))
    return "\n".join(parts)


def _items_system_prompt(
    construct_name: str,
    construct_def: str,
    dimension: Dict[str, Any],
    scale_type: str,
    scale_points: int,
    related_scales: List[str],
    parsed: Optional[Dict[str, Any]] = None,
) -> str:
    """Step 2: 为单个维度生成题目（短而专注的 prompt）。

    v3.7.3: 接收 Step 0 解析结果，让题目自然嵌入人群和情境。
    """
    n_items = int(dimension.get("item_count") or 5)
    n_reverse = max(1, round(n_items * 0.25))   # 25% 反向

    parts = [
        f"你是心理测量学专家。为构念「{construct_name}」的"
        f"「{dimension['name']}」维度撰写 {n_items} 道题目。\n",
    ]
    # v3.7.3 关键：注入研究背景，让题目嵌入人群+情境
    if parsed:
        parts.append(_format_research_context_for_prompt(parsed))
        parts.append("")
        rt = parsed.get("research_type", "construct_measurement")
        subj_template = parsed.get("item_subject_template", "我...")
        if rt in ("instrument_evaluation", "process_diagnostic", "multi_perspective_audit"):
            # v3.7.5: 工具评估型——题目主语必须指评估对象，不能写"我..."
            parts.append(
                f"## 🎯 题目主语要求（v3.7.5 工具评估型）\n"
                f"- 这是**工具/流程评估型**研究，题目主语必须用：「{subj_template}」\n"
                f"- 例：✅「我们公司目前的招聘标准能够准确评估候选人的专业知识储备」\n"
                f"- 例：❌「我感到自己的知识与岗位要求匹配」（这是构念测量型主语，禁止用）\n"
                f"- 答题者是 **{parsed.get('respondent_role', '?')}**，从 ta 的视角对评估对象做**质量判断**\n"
                f"- 反向题也用同样主语模板，描述评估对象**有问题的方面**\n"
                f"  例：✅「我们公司的某些招聘标准与实际岗位需求脱节」\n"
            )
        else:
            # 构念测量型（原 v3.7.3 行为）
            parts.append(
                f"## 🎯 题目情境化要求（构念测量型）\n"
                f"- 题干必须**嵌入研究人群与情境**——不要写通用模糊题\n"
                f"- 人群是「{parsed.get('population', '?')}」、情境是「{parsed.get('context', '?')}」\n"
                f"- 例：通用版「我感到焦虑」 → 情境化版「作为新员工，过去一周我经常因不熟悉工作流程而紧张」\n"
                f"- 量表导向「{parsed.get('scale_orientation', 'trait')}」决定题干时态：\n"
                f"  - state：「过去一周/此刻我...」\n"
                f"  - trait：「我通常/一般...」\n"
                f"  - behavior：「我会/我经常...」\n"
                f"  - quality_judgment：「我认为 X...（质量判断）」\n"
            )
    parts.extend([
        f"## 构念定义",
        construct_def[:300],
        "",
        f"## 维度描述",
        dimension.get("desc", ""),
        "",
        f"## 量表",
        f"- 类型：{scale_type}（{scale_points} 点）",
        "",
        f"## 反向题要求",
        f"- 共 {n_items} 题中，**正好 {n_reverse} 题为反向题**（reverse=true）",
        f"- 反向题必须描述**与该维度方向相反的具体行为/情境**，而非简单加'不'",
        "",
        ITEM_FEW_SHOT,
    ])
    if related_scales:
        parts.append("## 已有量表参考（仅供风格借鉴，不要直接抄）")
        for s in related_scales[:3]:
            parts.append(f"- {s}")
        parts.append("")
    parts.append("## 输出（严格 JSON，不要 markdown）")
    parts.append(json.dumps({
        "items": [
            {"text": "题目正文（行为锚定，单一概念）", "reverse": False}
        ]
    }, ensure_ascii=False, indent=2))
    parts.append("")
    parts.append(
        f"严格输出 {n_items} 题，**正好 {n_reverse} 题 reverse=true**，"
        f"按维度方向均匀混合（不要前几题全正向后几题全反向）。"
    )
    return "\n".join(parts)


def _metadata_system_prompt(skeleton: Dict[str, Any], parsed: Optional[Dict[str, Any]] = None) -> str:
    """Step 3: 生成 instructions + scoring + psychometrics + references。

    v3.7.3: 接收 Step 0 解析结果，让 instructions 自然包含人群+情境+研究意图。
    """
    bg = ""
    if parsed:
        bg = (
            "\n\n## 研究背景（必须嵌入 instructions）\n"
            f"- 人群：{parsed.get('population', '?')}\n"
            f"- 情境：{parsed.get('context', '?')}\n"
            f"- 研究意图：{parsed.get('summary', '?')}\n"
            f"  → instructions 必须明确告知被试本研究的背景和他们为何被选中\n"
        )
    return (
        "你是心理测量学专家。基于以下构念骨架，"
        "生成问卷的指导语、计分方式、心理测量学评估方案和参考文献。\n\n"
        f"构念：{skeleton.get('construct_name')}\n"
        f"维度：{[d.get('name') for d in skeleton.get('dimensions', [])]}\n"
        f"量表：{skeleton.get('scale_type')}（{skeleton.get('scale_points')} 点）"
        f"{bg}\n\n"
        "## 输出（严格 JSON，不要 markdown）\n"
        + json.dumps({
            "instructions": "完整问卷指导语：研究目的+保密声明+填写说明+评分标准（≥120 字）",
            "scoring": "计分方式：正向题/反向题计分规则、分维度计分、总分范围及含义",
            "psychometrics": {
                "内容效度": "本问卷内容效度保障策略（≥30 字）",
                "表面效度": "表面效度检查要点",
                "结构效度": "EFA/CFA 策略，预期因子数及拟合标准",
                "信度": "信度评估方案（α/重测/分半）",
                "社会称许性控制": "控制策略",
            },
            "references": [
                "APA 格式参考文献 1（构念定义来源）",
                "APA 格式参考文献 2（维度框架来源）",
                "APA 格式参考文献 3（已有量表）",
            ],
            "established_scales": ["已有成熟量表名+作者+年份"],
        }, ensure_ascii=False, indent=2)
    )


def _regenerate_item_prompt(
    old_text: str,
    issues: List[str],
    construct_name: str,
    dimension_name: str,
    is_reverse: bool,
) -> str:
    """Step 5: 重写单个弱题的 prompt（短而精）。"""
    direction = "反向题（描述与该维度方向相反的具体情境）" if is_reverse else "正向题"
    return (
        f"你写的题目质检不通过：\n"
        f"  原文：「{old_text}」\n"
        f"  问题：{'；'.join(issues)}\n\n"
        f"请改写。约束：\n"
        f"- 构念：{construct_name}\n"
        f"- 维度：{dimension_name}\n"
        f"- 方向：{direction}\n"
        f"- 行为锚定（具体可观察）+ 单一概念 + 长度 8-30 字\n\n"
        + ITEM_FEW_SHOT
        + "\n## 输出（严格 JSON，仅一句话题目）\n"
        + json.dumps({"text": "改写后的题目正文", "reverse": is_reverse},
                      ensure_ascii=False)
    )


def _regenerate_item_prompt_v2(
    old_text: str,
    issues: List[str],
    construct_name: str,
    dimension_name: str,
    is_reverse: bool,
    *,
    sibling_items: Optional[List[str]] = None,
) -> str:
    """v3.7.10: 增强版重写 prompt——传入同维度其他题（避免改后与它们重复）。"""
    direction = (
        "反向题（描述与该维度方向相反的具体情境，**禁止仅在正向题前加'不'制造镜像题**）"
        if is_reverse else "正向题"
    )
    parts = [
        "你写的题目经过本地质检与 LLM 同行评审，被标记为不达标。\n",
        f"  原文：「{old_text}」\n",
        f"  违反规则：{'；'.join(issues) if issues else '（多重质量问题）'}\n\n",
        "请改写。约束：\n",
        f"- 构念：{construct_name}\n",
        f"- 维度：{dimension_name}\n",
        f"- 方向：{direction}\n",
        "- **行为锚定**（具体可观察行为/情境）+ 单一概念 + 长度 8-25 字\n",
        "- **抗过拟合**：情境应典型，不能仅在某狭窄场景成立\n",
        "- **避免极端词**（总是/从不/绝对）+ **避免假设句**（如果...就...）\n",
        "- **避免直接含构念名**（不要写「我的{construct} 高」）\n",
    ]
    if sibling_items:
        parts.append("\n## 同维度其他题（你的改写**必须**在语义/措辞上与这些题区分）\n")
        for s in sibling_items[:5]:
            parts.append(f"- {s}\n")
    parts.append("\n")
    parts.append(ITEM_FEW_SHOT)
    parts.append("\n## 输出（严格 JSON，仅一句话题目，不要 markdown）\n")
    parts.append(json.dumps({"text": "改写后的题目正文", "reverse": is_reverse},
                            ensure_ascii=False))
    return "".join(parts)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def design_questionnaire_premium(
    research_question: str,
    api_key: str,
    base_url: str,
    model: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: int = 60,
    cancel_id: Optional[int] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    parsed_research_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """高质量问卷生成主入口（直连模式）。

    一次性把研究问题原文和设计原则一起喂给 LLM；可选弱题重写。

    Args:
        parsed_research_override: 用户手动校正的解析；作为额外上下文注入
            user prompt + 填充 research_parse。
    """
    direct_max_tokens = max(max_tokens, 8192)
    return design_questionnaire_direct(
        research_question, api_key, base_url, model,
        temperature=temperature,
        max_tokens=direct_max_tokens,
        timeout=max(timeout, 180),
        cancel_id=cancel_id,
        progress_callback=progress_callback,
        parsed_research_override=parsed_research_override,
    )



# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _parse_json(text: str, label: str) -> Dict:
    """容错解析 LLM JSON 输出。"""
    if not text:
        raise LLMResponseParseError(f"{label}: LLM 返回空内容")
    s = text.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        s = s[first_nl + 1:] if first_nl > 0 else s
        if s.endswith("```"):
            s = s[:-3]
    s = s.strip()
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end <= start:
        raise LLMResponseParseError(f"{label}: 无 JSON 结构")
    try:
        return json.loads(s[start: end + 1])
    except json.JSONDecodeError as e:
        raise LLMResponseParseError(f"{label}: JSON 解析失败 - {e}")


def _validate_skeleton(skeleton: Dict) -> None:
    required = ["construct_name", "dimensions"]
    missing = [k for k in required if k not in skeleton]
    if missing:
        raise LLMResponseParseError(f"skeleton 缺字段：{missing}")
    if not skeleton["dimensions"]:
        raise LLMResponseParseError("dimensions 为空")


# ---------------------------------------------------------------------------
# v3.7.2: 维度分解充分性检查（阻止"两个抽象维度就完事"的偷懒输出）
# ---------------------------------------------------------------------------

# 已知理论丰富的构念关键词 → 期望的最少维度数
_THEORY_RICH_KEYWORDS = {
    "人岗匹配": 6, "人组织匹配": 4, "人职匹配": 6,
    "工作满意度": 5, "职业倦怠": 3, "工作投入": 3,
    "组织承诺": 3, "心理资本": 4, "工作-家庭冲突": 4,
    "依恋": 4, "亲子关系": 4, "婚姻": 4,
    "学习动机": 4, "学业拖延": 3,
    "自尊": 3, "自我效能": 3,
    "人格": 5, "大五": 5, "big five": 5,
    "情绪智力": 4, "心理韧性": 4,
    "领导风格": 4, "变革型领导": 4,
    "person-job fit": 6, "person-organization fit": 4,
}


def _is_under_decomposed(skeleton: Dict[str, Any], research_question: str) -> bool:
    """v3.7.2: 检测 skeleton 是否对理论丰富的构念分解不足。

    规则（满足任一即视为不足）：
    1. 维度数 ≤ 3 但研究问题/构念名命中"理论丰富"关键词列表
    2. 任一维度的 desc 含「包括/涵盖/包含 X、Y、Z」等列举词（说明该维度内部还有子结构）
    3. 维度数 = 2 且每个维度的 item_count ≥ 6（说明应该再拆）
    """
    dims = skeleton.get("dimensions") or []
    n_dims = len(dims)
    if n_dims == 0:
        return False    # 空维度由 _validate_skeleton 处理

    construct_name = (skeleton.get("construct_name") or "").lower()
    research_q = (research_question or "").lower()
    blob = construct_name + " " + research_q

    # 规则 1：理论丰富 + 维度太少
    expected_min = 0
    for keyword, min_n in _THEORY_RICH_KEYWORDS.items():
        if keyword.lower() in blob:
            expected_min = max(expected_min, min_n)
    if expected_min and n_dims < expected_min:
        return True

    # 规则 2：维度描述含列举词（说明内部还有子结构）
    listing_markers = ["包括", "涵盖", "包含", "如"]
    for d in dims:
        desc = d.get("desc", "")
        # 含 "包括 X、Y、Z" 模式（含 1 个列举词 + 至少 2 个顿号）
        if any(m in desc for m in listing_markers) and desc.count("、") >= 2:
            return True

    # 规则 3：仅 2 维度且每维度题量 >= 6（典型欠分解）
    if n_dims == 2:
        max_items = max(int(d.get("item_count", 5)) for d in dims)
        if max_items >= 6:
            return True

    return False


def _build_decomposition_critique(skeleton: Dict[str, Any]) -> str:
    """v3.7.2: 生成"分解不足"的反馈 prompt，要求 LLM 重新输出更细的维度。"""
    current_dims = skeleton.get("dimensions") or []
    dim_summary = "\n".join(
        f"- {d.get('name', '?')}（{d.get('desc', '')[:60]}）"
        for d in current_dims
    )
    return (
        "你的分解**不够充分**。\n\n"
        f"你给出了 {len(current_dims)} 个维度：\n{dim_summary}\n\n"
        "问题：这些维度太抽象，每个内部混杂多个独立的可操作子维度。\n"
        "因子分析时会被拆开，违反测量学单一概念原则。\n\n"
        "**请重新输出**：\n"
        "1. 把每个抽象维度**继续下钻**为可直接出题的具体子维度\n"
        "2. 总维度数应在 5-8 个之间（理论丰富时偏向 7-8）\n"
        "3. 每维度的 desc 应是**单一可观察内容**，不能再列举多个方面\n"
        "4. 用 `parent_dimension` 字段标注一级分组（如「要求-能力匹配」）\n\n"
        "再次输出完整 JSON，不要解释。"
    )


# ===========================================================================
# v3.7.7 直连模式 prompt（核心改进：保留完整原句语境）
# ===========================================================================

DIRECT_MODE_SYSTEM_PROMPT = """你是资深心理测量学专家。根据用户的研究问题设计完整问卷，**严格遵循 2020s 测量学最新共识**：
- 基础经典：Podsakoff et al. (2003) JAP；DeVellis (2017) *Scale Development* 4ed；Boateng et al. (2018) *Front Public Health* 9 步框架
- 最新方法学综述：**Ward & Meade (2023) *Annual Review of Psychology*** — careless responding 系统综述
- 测量学改革倡议：**Flake & Fried (2020) *AMPPS*** "measurement schmeasurement" — 强调构念透明、操作化合理性
- 反向题最新批判：**Schroeders et al. (2022)** — 反向题在人格测量的方法因子证据
- IER 检测：DeSimone, DeSimone, Harms, Wood (2018) *J Bus Psych*；Hauser, Ellsworth, Gonzalez (2018) *Behav Res Meth*；Bowling et al. (2021) *Psych Methods*
- 构念验证最新框架：Tay & Jebb (2022) *Annu Rev Organ Psychol*
- 因子结构现代方法：ESEM（Marsh, Morin, Asparouhov, Muthén 2014+）；bifactor model；网络心理测量学（Christensen & Golino 2021）
- 跨文化警示：Henrich, Heine, Norenzayan (2010, 2020 update) — WEIRD 样本

# 第一步：先理解整句话
**反复通读用户研究问题原文**，识别（不要只抓一个关键词）：
- 真实的研究意图：测人的心理状态？还是评估某个工具/政策/流程？
- 答题人是谁：自评？管理者评下属？HR 评流程？
- 研究情境：什么人群、什么场景、什么时间段
- 理论框架（如有）：用作组织维度，不是测量对象

# 第二步：构念前置判断（在写题前必须完成 — 这是地基）

## 0. 构念清晰度 + 模型类型判断

### (a) Jingle-Jangle 谬误检测（Block 1995；Tay & Jebb 2017）

⚠️ **Jingle**（同名异质）：两份"工作满意度"量表可能测的根本不是同一回事
⚠️ **Jangle**（异名同质）：「工作敬业度」与「工作投入」事实上重合 ≥80%

**任务**：
1. 给出构念的**操作性定义**（≥2 句，明确包含什么、**不**包含什么）
2. 列出 2-3 个**邻近构念**及与本构念的差异（前置区分效度，Borsboom et al. 2004）
3. 给出 1-2 个**收敛构念**（应高相关，用作未来效标）

### (b) Reflective vs Formative 模型判断（Edwards & Bagozzi 2000；Diamantopoulos & Winklhofer 2001；Bollen & Diamantopoulos 2017）

⚠️ **这一判断决定后续是否能做 EFA/CFA/α！搞错全错。**

| 类型 | 方向 | 题目关系 | 例子 | 验证方法 |
|---|---|---|---|---|
| **Reflective**（反思性） | 构念 → 题目 | 各题是构念的"症状"，互相高相关 | 焦虑、自尊、人格特质 | EFA/CFA/Cronbach α/IRT |
| **Formative**（形成性） | 题目 → 构念 | 各题是构念的"成因"，可独立变化 | SES（教育+收入+职业）、生活质量综合指数 | **不能做 EFA、不能算 α**；用 PLS-SEM、indicator weights |

**判断准则**（任一为 yes 即 formative）：
- 题目能否互换？（不能 → formative）
- 删一题，构念意义是否实质改变？（改变 → formative）
- 题目间高相关是否反而不合理？（是 → formative）

**混合模型**：复杂构念可能混合（人岗匹配：「需要-供给·物质回报」是 reflective，「整体人岗匹配度」是 formative）→ 在 dimensions 中**逐维度标注 model_type**。

### (c) 构念定义边界 + 抽样代表性（WEIRD 警示，Henrich et al. 2010, 2020）

- 明确**目标人群**与**情境边界**：构念在何种群体/情境中的何种意义
- 警示 WEIRD 偏差：避免用美国大学生样本量表直接测中国职场人群——构念表征可能不等价

# 第三步：八大题目设计原则

## 1. 题目主语必须正确
- 测心理状态/特质 → 题目主语「我...」
- 评估工具/标准/政策 → 题目主语「我们公司的 X...」「现行 Y 流程...」
- 多视角对照 → 题目主语指向被评估对象

**例：HRBP 想做"基于人岗匹配的用人标准复盘"，让员工答题**
→ 答题人是员工 → 题目主语「我...」（员工自评匹配感）
→ HR 用结果反推用人标准的有效性（数据用途，不是题目主语）
→ 维度严格按 D-A/N-S 框架细分，便于诊断

## 2. 维度必须充分下钻
**绝对禁止**仅给 2-3 个抽象一级维度。理论丰富的构念必须下钻：
- 人岗匹配 → 要求-能力·知识/技能/能力/经验 + 需要-供给·物质/社交/自我实现/工作环境（6-8 维度）
- 工作满意度（JDI）→ 工作内容/薪酬/晋升/上司/同事（5 维度）
- 焦虑 → 认知/情感/生理/行为（4 维度）
- 简单单因子构念可保持 2-3 维度

## 3. 行为锚定 + 抗过拟合（带宽-保真度平衡，Cronbach & Gleser 1957）

**(a) 必须行为锚定（避免抽象）**
❌ 差：「我感到焦虑」（直接问构念，无可观察内容）
✅ 好：「过去一周，我经常因小事担心难以入睡」

❌ 差：「我对工作满意」
✅ 好：「我每天上班路上会期待今天要做的工作」

**(b) 抗过拟合（带宽-保真度平衡）**

测量学的核心张力：**过窄**（仅在一个情境成立）→ 高保真但带宽窄，外部效度差；**过宽**（无具体情境）→ 高带宽但保真度低，测不准。

❌ 过拟合：「在地铁上手机没电时我会感到不安」（情境过窄，仅特定场景）
❌ 过宽泛：「我经常感到不安」（无情境锚定，混入其他构念变异）
✅ 适度：「在不熟悉的环境中我会感到紧张」（覆盖一类典型情境）

**判断准则**：题目情境应是**该构念在目标人群中典型表现的代表性切片**——既不是一个独特故事，也不是漂浮在情境之外的形容词。**测量的是构念，不是某个特定故事**。

**(c) 时间窗口具体化（避免"最近/有时"等模糊修饰）**
- state（瞬时状态）→「过去 7 天/此刻我...」（精确到天数，不写"最近"）
- trait（稳定特质）→「我通常/一般...」
- behavior（行为频次）→「过去一个月，我有 ___ 次...」或「我会经常...」
- quality_judgment（质量判断）→「我认为 X...」

**(d) 题间独立性**：同一维度的多道题应**采样该维度不同侧面**，不要互为同义改写
- 改写题（同义换词）会人为抬高 Cronbach's α 但降低真实信度（Hinkin 1998）
- 例：测「工作满意度·薪酬」时，避免「我对薪酬满意」+「我对收入满意」+「我对工资满意」三题——只能算一题
- 正确：「薪酬水平」「薪酬涨幅」「薪酬与工作量匹配度」三个不同侧面

**(e) 题干长度 8-25 字（中文）**：过短信息不足，过长增加阅读负担与理解错误率（Holbrook et al. 2006）。

**(f) 阅读水平**：成人问卷应不超过中国初中水平；老人/低教育群体应小学水平。避免文言、生僻字、专业术语。

**(g) 避免地板/天花板效应**：题目内容不应让 95%+ 被试都同意（或都不同意）——此类题目区分度极低，建议替换。

## 4. 反向题 → 注意力检测题（v3.7.8 重大共识更新）

**当代测量学共识**：反向题（reverse-coded items）会制造**方法因子**（method factor），污染因子结构、降低内部一致性、增加阅读理解负担。证据脉络从经典到最新：
- 经典：Schmitt & Stults (1985)；Marsh (1996)；Tomas & Oliver (1999) — 反向题方法因子可达 16-30% 方差
- 中坚：Hinkin (1998)；Podsakoff et al. (2003)；Weijters & Baumgartner (2012)
- **最新（2018-2024）**：
  - **Schroeders, Schmitt, Lippold, Ringeisen (2022)** — 大五人格量表反向题诱发的 method factor 在年龄/教育水平间不变性差
  - **Suárez-Álvarez et al. (2018)** *Eur J Psych Assessment* — 否定式表述题的反应风格污染
  - **Ward & Meade (2023)** *Annu Rev Psych* — 综述明确建议**优先使用注意力检测题而非反向题**

**当代替代方案**：用**注意力检测题（attention check / IMC）**抗直线作答与机器作答：
- Meade & Craig (2012) *Psychological Methods* — 系统提出 IER 检测框架
- Curran (2016) *J Experimental Social Psych* — 多维统计指标
- **Hauser, Ellsworth, Gonzalez (2018)** *Behav Res Meth* — 警示：单一 IMC 容易被识破，须用 IRI + Bogus + Infrequency 多类型混合
- **DeSimone, DeSimone, Harms, Wood (2018)** *J Bus Psych* — IER 与内容相关回答区分方法
- **Bowling, Huang, Brower, Bragg (2021)** *Psych Methods* — IER 的 nomological network 与多指标融合

**新做法（默认）**：
1. **所有构念题 reverse=false**——不再依赖反向题做方法控制
2. **嵌入 1-3 道注意力检测题**（item_type="attention_check"）
   - 占比约总题数 5-10%（最少 1 题，最多 3 题）
   - 不计入任何维度分数（dimension 字段填 "_attention_check"）
   - 三种典型类型：
     - **指令型（IRI, Instructed Response Item）**：「这道题请选择"3"以表明你认真作答」
     - **不可能型（Bogus item）**：「我曾经在 25 小时之内吃下过 100 个苹果（请选"非常不同意"）」
     - **低频率型（Infrequency item）**：「我能用思维让物品移动（不思考请选最左）」
   - 多道题时建议**类型混合**而非全是同一种
3. **可选**：嵌入 1 道**社会赞许性检测题**（item_type="social_desirability_check"）
   - 例：「我从来没有对任何人说过谎」（Crowne-Marlowe 风格，极端选项揭示社会赞许）

**例外（保留反向题的情形）**：
- 用户明确要求保留反向题
- 该构念领域**强约定**使用反向题（如 Rosenberg 自尊量表 RSES、BDI 抑郁量表）

例外时反向题写法：必须是**真反向情境**而非镜像题
❌ 镜像：正「我感到自信」/反「我感到不自信」（仅加"不"）
✅ 真反向：正「我感到自信」/反「遇到挫折时我容易情绪崩溃」（描述相反方向的具体行为）

**统计检测建议**（写入 psychometrics 字段）：除注意力检测题外，建议施测后用 Mahalanobis distance、longstring index、IRV（intra-individual response variability）综合识别 careless responder（Curran 2016）。

## 5. 题干禁忌（绝对禁止的写法）

- ❌ **双重负载（double-barreled）**：「我又累又难过」（拆成两题）
- ❌ **双重否定**：「我不感到不满意」（处理负担过高）
- ❌ **假设/条件句**：「如果有人骂我，我会反击」（测的是想象，不是真实行为）
- ❌ **极端词**：「我总是/从不/绝对...」（强迫极端反应，破坏区分度）
- ❌ **直接问构念**：「我的工作满意度高」（应行为锚定）
- ❌ **社会赞许敏感（直问道德）**：「我会撒谎/我会偷东西」（用间接表述）
- ❌ **题间镜像/同义重复**：同维度题不要互为换词改写（影响内部一致性 α 虚高）
- ❌ **专业术语/jargon**：成人问卷应不超过初中阅读水平
- ❌ **多义模糊词**：避免「有时候/可能/也许」等让答题者困惑的修饰

## 6. 量表锚点设计

**(a) 量表点数选择**
- 临床/健康（焦虑、抑郁、压力）→ **4 点频率**（避免中间倾向）
- 人格/社会/态度 → **5 点同意度**
- 宽泛构念/幸福感/生活满意度 → **7 点同意度**（区分度高）
- 工具/政策评估 → **5 点同意度** 或 **5 点满意度**
- 儿童/低教育人群 → 3 点（理解负担最低）

**(b) 全标签优于仅端点标签**（Krosnick & Presser 2010）
- 优：「1=完全不同意 / 2=不同意 / 3=不确定 / 4=同意 / 5=完全同意」（每点都有词标签）
- 差：「1=完全不同意 ... 5=完全同意」（中间几点无标签，被试随意解释）

**(c) 锚点对称**：负向选项数 = 正向选项数；力度对称（"完全不同意"对应"完全同意"）

**(d) 避免极端语气**：「绝对不」「丝毫不」等强迫被试选不到

**(e) 频率量表禁止用同意度锚点**：测「我每周锻炼几次」就用「从不/偶尔/每周 1-2 次/每周 3-4 次/几乎每天」；不要写「同意我经常锻炼吗」

## 7. 现代结构验证方法（按构念复杂度分层）

### (a) 三条主路径（按 model_type 选择）

| 路径 | 适用 | 推荐场景 | 最小样本 |
|---|---|---|---|
| **CTT + EFA/CFA** | reflective，传统 | 经典心理量表（焦虑、自尊等） | EFA ≥ 题数×10；CFA ≥ 200 |
| **IRT（GRM/Rasch/PCM）** | reflective，**推荐用于新量表** | NIH PROMIS 范式；支持 CAT 减题量；可做 DIF 公平性检验 | ≥ 500 |
| **PLS-SEM / indicator weights** | **formative** | 综合指数（SES、生活质量综合指数） | ≥ 200 |

**ESEM**（Marsh, Morin, Asparouhov, Muthén 2014+）：介于 EFA 与 CFA 之间，允许小的交叉载荷，多维构念首选 CFA 替代品。

**Bifactor model**（Reise et al. 2010+）：构念既有总分又有子分时（如智力 g + 子能力），比一阶因子更准确。

**网络心理测量（network analysis）**（Christensen & Golino 2021）：探索性辅助，识别题间局部依赖与潜在 jangle 谬误。

### (b) 跨群体测量等价（MI / DIF）— 必做项

跨群体（性别/年龄/教育水平/文化/语言）施测时**必须做**配置-度量-标量等价检验（van de Schoot et al. 2020；International Test Commission Guidelines 2017）：
- **Configural invariance**（配置等价）：因子结构跨组一致
- **Metric invariance**（度量等价）：因子载荷跨组一致
- **Scalar invariance**（标量等价）：截距跨组一致 ← 跨组比均值的前提
- IRT 路径：DIF（Differential Item Functioning）检测识别"不公平题"

**中文版必须做**：与英文原版的跨语言 MI；不能假设直译就保持等价。

### (c) 经典 EFA/CFA 阈值（兜底标准）
- KMO ≥ 0.80；Bartlett p < 0.001
- 主因子载荷 ≥ 0.40；交叉载荷 < 0.30
- CFI ≥ 0.90（更好 ≥ 0.95）；RMSEA < 0.08（更好 < 0.06）；SRMR < 0.08
- α ≥ 0.70（可接受），≥ 0.80（良好）；同时报告 **ω（McDonald's omega）**——α 在违反 tau-equivalent 假设时偏低，ω 更稳

### (d) 数据质量统计指标（Curran 2016；Bauer et al. 2007；Greszki et al. 2015）
- **Mahalanobis distance**：识别多元离群被试
- **longstring index**：连续相同选项段长度
- **IRV（intra-individual response variability）**：被试方差过低=直线作答
- **响应时间**：< 3 秒/题（careless）或 > 90 秒/题（分心）剔除

## 8. 版面与施测设计

- **题目顺序**：先一般性 / 易答 / 不敏感题 → 中段是核心构念题 → 末尾是敏感与人口学问题（漏斗设计，Krosnick & Presser 2010）
- **维度内题目应跨题位散布**：避免同一维度题目连续出现（减少情境效应）
- **注意力检测题**：随机插入但不放首末两题；多道注意力题之间间隔≥5题
- **总长度上限**：自评问卷 ≤ 60 题（含检测题），临床访谈式 ≤ 30 题（疲劳效应；Galesic & Bosnjak 2009）
- **指导语必含**：研究目的、保密承诺、回答时间估计、注意力题说明（"问卷中含若干检测题用于数据筛查"）、知情同意标准条款
- **维度命名一致性**：维度名在 dimensions 与 items.dimension 中**必须严格一致**（包括标点）

# 第三步：输出格式（严格 JSON，不要 markdown 代码块）

```json
{
  "construct_name": "中文构念名（2-6 字）",
  "construct_name_en": "English Name",
  "domain": "临床与健康/人格/社会心理/教育心理/认知/组织行为/发展/其他",
  "definition": "学术定义 2-3 句",
  "theoretical_framework": "用作维度组织的理论（可选）",
  "research_understanding": "你对研究问题的理解（2-3 句话，让用户验证）",
  "respondent_role": "self/supervisor/hr_practitioner/recruiter/mixed",
  "population": "答题人群（具体）",
  "context": "研究情境",
  "construct_clarity": {
    "operational_definition": "≥2 句的操作性定义，明确包含什么、不包含什么",
    "boundary_conditions": ["不包含 X 因为...", "..."],
    "discriminant_constructs": [
      {"name": "邻近构念A", "key_difference": "本构念强调 X，邻近构念强调 Y"}
    ],
    "convergent_constructs": ["应高相关的构念，用作未来效标"],
    "jingle_jangle_check": "已检查是否与现有同名/异名构念混淆，结论：..."
  },
  "dimensions": [
    {
      "name": "维度名（含父级前缀如要求-能力·知识匹配）",
      "desc": "维度描述",
      "item_count": 4,
      "model_type": "reflective | formative | mixed"
    }
  ],
  "scale_type": "likert_agreement | frequency | semantic_differential",
  "scale_points": 5,
  "scale_type_label": "agreement/frequency/satisfaction/quality_judgment",
  "anchor_labels": ["1=完全不同意", "2=不同意", "3=不确定", "4=同意", "5=完全同意"],
  "items": [
    {
      "text": "题目正文（行为锚定，单一概念，8-25 字）",
      "reverse": false,
      "dimension": "所属维度名（注意力检测题填 _attention_check）",
      "item_type": "construct"
    },
    {
      "text": "这道题请选择\"3\"以表明你认真作答",
      "reverse": false,
      "dimension": "_attention_check",
      "item_type": "attention_check"
    }
  ],
  "instructions": "完整指导语：研究背景+答题指引+保密声明+注意力检测题说明+回答时间估计",
  "scoring": "计分方式（正向题计分、维度均分、总分含义；formative 维度用 indicator weights 而非简单求和；说明注意力检测题不计入分数仅用于数据筛查）",
  "psychometrics": {
    "内容效度": "I-CVI ≥ 0.78、S-CVI/Ave ≥ 0.90；3-5 位领域专家评分",
    "表面效度": "目标人群小样本认知访谈（n=10-15）",
    "结构效度": "首选路径（EFA/CFA 或 IRT-GRM 或 PLS-SEM，按 model_type 选择）+ 备选 ESEM/bifactor + 拟合阈值",
    "信度": "Cronbach α + McDonald ω + 重测 ICC（间隔 2-4 周）",
    "测量等价": "跨性别/年龄/教育水平/文化的配置-度量-标量等价检验（van de Schoot 2020）；中文版 vs 英文版跨语言 MI",
    "样本量规划": "EFA ≥ 题数×10；CFA ≥ 200；IRT ≥ 500（MacCallum et al. 1999）",
    "数据质量控制": "注意力检测题（答错≥1 剔除）+ 响应时间监测（<3 秒/题剔除）+ longstring index + Mahalanobis distance + IRV",
    "社会称许性控制": "Crowne-Marlowe 量表筛查或题干用间接表述"
  },
  "references": [
    "构念定义来源（APA 格式）",
    "维度框架理论来源",
    "相似已有量表（APA 格式）",
    "方法学引用（建议含 Podsakoff 2003、Meade & Craig 2012、Boateng et al. 2018、Ward & Meade 2023 等）"
  ],
  "established_scales": ["已有成熟量表名+作者+年份"],
  "match_reason": "设计思路：为什么 reflective/formative 这样判定、为什么这样分维度、为什么选这种量表、为什么用注意力检测题代替反向题"
}
```

# 重要约束
- 构念题数量 = 各 dimensions item_count 之和（通常 16-30 题）
- 必须额外包含 1-3 道 item_type="attention_check"（约总题数 5-10%）
- items 按维度顺序排列；注意力检测题**随机插入**（不放首尾）
- 默认所有题 reverse=false；仅领域强约定时保留 reverse=true（用真反向情境写法）
- **必须**完成 construct_clarity 字段（jingle-jangle 检测 + 操作性定义 + 区分/收敛构念）
- **必须**为每个 dimension 标注 model_type（reflective/formative/mixed）
- **必须**在 psychometrics 中包含测量等价（MI）、样本量规划、数据质量控制
- 所有中文字段用中文输出
- 不要用 markdown 代码块包裹 JSON
"""


# ===========================================================================
# v3.7.10：LLM 自审核 pass（critique pass）
# ===========================================================================

CRITIQUE_SYSTEM_PROMPT = """你是心理测量学审稿人（**同行评审视角，不是设计者**）。

对一份心理学问卷的题目进行严格批判性评审，找出违反**当代测量学规则**的题。

# 评审规则清单（按违反严重度从高到低）

## 1. 行为锚定缺失（severity: warning）
题目仅含构念词（如"焦虑/满意/自信"+程度词），无可观察行为或具体情境锚定。
❌「我感到焦虑」 ✅「过去一周我经常因小事担心难以入睡」

## 2. 过拟合（severity: warning）
题目情境过窄，仅在特定边缘场景成立，损害外部效度。
❌「在地铁上手机没电时我会感到不安」 ✅「在不熟悉的环境中我会感到紧张」

## 3. 双重负载（severity: error）
一题包含两个独立概念或情绪。
❌「我又累又难过」 ✅ 拆为「我经常感到疲倦」+「我经常感到难过」

## 4. 镜像反向题（severity: error）
反向题仅在正向题前加"不"形成的伪反向（与正向题同概念，制造方法因子）。
❌ 正「我感到自信」/反「我感到不自信」
✅ 正「我感到自信」/反「遇到挫折时我容易情绪崩溃」

## 5. 假设句/极端词/直问构念（severity: warning）
- 假设句：「如果...就...」（测想象不是行为）
- 极端词：「总是/从不/绝对」（强迫极端反应）
- 直问构念：题干含构念名（如「我的工作满意度高」）

## 6. 题目主语与答题人角色不符（severity: warning）
工具评估型研究的题目主语应为「我们公司的 X / 现行流程 Y」而非「我...」。

## 7. 题间同义改写（severity: warning）
同维度多题语义重复（互为换词改写），人为抬高 α 但降低真实信度。

## 8. 题干长度不当（severity: info）
长度 < 8 字（信息不足）或 > 30 字（阅读负担过大）。

## 9. 注意力检测题数量不达标（overall_issue）
未嵌入注意力检测题，难以识别 careless responder。

# 输出格式（严格 JSON，不要 markdown）

```json
{
  "items_with_issues": [
    {
      "index": 1,
      "score": 0-10,
      "issues": ["问题简短描述1", "问题简短描述2"],
      "severity": "error | warning | info"
    }
  ],
  "overall_issues": ["整问卷级问题1", "..."],
  "summary": "1-2 句话总评：本问卷整体质量评估"
}
```

# 重要约束
- 只输出有问题的题目（score < 8 的题进 items_with_issues）
- 没问题的题不要输出
- 同一道题可有多个 issues
- severity 按最严重的违规级别取
- 用客观批判的语气，避免吹捧或委婉
"""


def _format_items_for_critique(
    items: List[Dict],
    construct_name: str,
    parsed_research: Optional[Dict[str, Any]] = None,
) -> str:
    """构造 critique pass 的 user message：把题目列表 + 上下文喂给评审员。"""
    parts = [f"## 待评审问卷\n构念：{construct_name}\n"]
    if parsed_research:
        rt = parsed_research.get("research_type", "construct_measurement")
        rt_label = {
            "construct_measurement": "构念测量型（测被试个人状态/特质）",
            "instrument_evaluation": "工具/标准评估型（评估工具合理性）",
            "process_diagnostic": "流程诊断型",
            "multi_perspective_audit": "多视角对照型",
        }.get(rt, rt)
        parts.append(f"研究层次：{rt_label}")
        if parsed_research.get("respondent_role"):
            parts.append(f"答题人角色：{parsed_research['respondent_role']}")
        if parsed_research.get("item_subject_template"):
            parts.append(f"题目主语模板：{parsed_research['item_subject_template']}")
        if parsed_research.get("population"):
            parts.append(f"目标人群：{parsed_research['population']}")
    parts.append("")

    # 按维度分组列出
    by_dim: Dict[str, List[Dict]] = {}
    for it in items:
        d = it.get("dimension", "默认")
        by_dim.setdefault(d, []).append(it)

    parts.append("## 题目列表（按维度分组）")
    for dim_name, dim_items in by_dim.items():
        if dim_name == "_attention_check":
            parts.append(f"\n### 注意力检测题 ({len(dim_items)} 道)")
        else:
            parts.append(f"\n### 维度：{dim_name} ({len(dim_items)} 道)")
        for it in dim_items:
            rev = "（反向）" if it.get("reverse") else ""
            it_type = it.get("item_type", "construct")
            type_mark = "" if it_type == "construct" else f"[{it_type}]"
            parts.append(f"#{it.get('index', '?')} {type_mark}{rev} {it.get('text', '')}")

    parts.append("\n请按系统提示中的规则严格评审，输出 JSON。")
    return "\n".join(parts)


def _run_llm_critique(
    items: List[Dict],
    construct_name: str,
    parsed_research: Optional[Dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    *,
    temperature: float = 0.2,
    timeout: int = 60,
    cancel_id: Optional[int] = None,
) -> Dict[str, Any]:
    """v3.7.10: LLM 自审核 pass。

    返回：
    {
      "items_with_issues": [{"index", "score", "issues", "severity"}],
      "overall_issues": [...],
      "summary": "..."
    }

    失败时返回空骨架（不阻塞主流程）。
    """
    msgs = [
        {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
        {"role": "user", "content": _format_items_for_critique(items, construct_name, parsed_research)},
    ]
    actual_tokens = 6144 if _is_reasoning_model(model) else 2048
    try:
        raw = _call_llm(msgs, api_key, base_url, model, temperature, actual_tokens, timeout, cancel_id)
        if not raw or not raw.strip():
            return {"items_with_issues": [], "overall_issues": [], "summary": "（LLM 评审返回空）"}
        parsed = _parse_json(raw, "critique")
        # 兜底字段
        parsed.setdefault("items_with_issues", [])
        parsed.setdefault("overall_issues", [])
        parsed.setdefault("summary", "")
        return parsed
    except Exception as e:
        return {
            "items_with_issues": [],
            "overall_issues": [],
            "summary": f"（评审失败：{type(e).__name__}）",
        }


def design_questionnaire_direct(
    research_question: str,
    api_key: str,
    base_url: str,
    model: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    timeout: int = 180,
    cancel_id: Optional[int] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    parsed_research_override: Optional[Dict[str, Any]] = None,
    enable_llm_critique: bool = True,
) -> Dict[str, Any]:
    """v3.7.10 直连模式 + 自审核闭环。

    流程：
    1. 一次主调用（research_question 原文 + 直连 prompt）→ 完整 design JSON
    2. 本地质检（item_quality.py，v3.7.10 含抽象度/过拟合/镜像/主语等）
    3. v3.7.10：LLM 自审核 pass（critique pass，独立评审视角）
    4. 弱题候选集合并（本地 ∪ critique）→ 并行重写

    Args:
        parsed_research_override: 用户手动校正的研究背景
        enable_llm_critique: 是否运行 LLM 自审核 pass（默认 True；False 退化为 v3.7.9 行为）
    """
    def report(msg: str, pct: float):
        if progress_callback:
            try:
                progress_callback(msg, pct)
            except Exception:
                pass

    # ---- Step 1: 一次性主调用 ----
    report("步骤 1/3：直连 LLM 设计完整问卷（保留完整研究语境）...", 0.10)
    if cancel_id is not None and _is_cancelled(cancel_id):
        raise CancelledLLMError("已取消")

    user_content = research_question
    if parsed_research_override:
        # 把用户校正过的关键字段拼成「研究者已确认」段，附在原句后
        confirmed_lines = []
        for key, label in [
            ("research_type", "研究层次"),
            ("research_object", "真正评估的对象"),
            ("respondent_role", "答题者角色"),
            ("item_subject_template", "题目主语模板"),
            ("population", "目标人群"),
            ("theoretical_framework", "理论框架"),
            ("summary", "研究意图概要"),
        ]:
            v = parsed_research_override.get(key)
            if v:
                confirmed_lines.append(f"- {label}：{v}")
        if confirmed_lines:
            user_content = (
                f"研究问题原文：\n{research_question}\n\n"
                f"## 研究者已手动确认的关键背景（必须严格遵守）\n"
                + "\n".join(confirmed_lines)
            )

    msgs = [
        {"role": "system", "content": DIRECT_MODE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # 推理模型自动加 token
    actual_max_tokens = max_tokens
    if _is_reasoning_model(model):
        actual_max_tokens = max(max_tokens, 16384)

    raw = _call_llm(
        msgs, api_key, base_url, model,
        temperature, actual_max_tokens, timeout, cancel_id,
    )
    if not raw or not raw.strip():
        # 空输出重试一次（更高 token）
        raw = _call_llm(
            msgs, api_key, base_url, model,
            temperature, max(actual_max_tokens * 2, 32768), timeout, cancel_id,
        )
    parsed = _parse_json(raw, "direct_design")

    # 校验必需字段
    required = ["construct_name", "dimensions", "items"]
    missing = [k for k in required if k not in parsed]
    if missing:
        raise LLMResponseParseError(f"LLM 输出缺字段：{missing}")
    if not parsed["dimensions"] or not parsed["items"]:
        raise LLMResponseParseError("dimensions 或 items 为空")

    # 编号 + 兜底字段 + 区分构念题/注意力检测题
    for i, item in enumerate(parsed["items"]):
        item["index"] = i + 1
        item.setdefault("reverse", False)
        item.setdefault("item_type", "construct")
        item.setdefault("dimension", parsed["dimensions"][0].get("name", "默认维度"))

    # 抽出注意力检测 / 社会赞许性检测题（不参与质检与重写）
    construct_items = [it for it in parsed["items"] if it.get("item_type", "construct") == "construct"]
    quality_check_items = [
        it for it in parsed["items"]
        if it.get("item_type") in ("attention_check", "social_desirability_check")
    ]

    # ---- Step 2: 本地质检（v3.7.10 含抽象度/过拟合/镜像反向/主语等）----
    report(f"步骤 2/4：本地质检（构念题 {len(construct_items)} 道，跳过 {len(quality_check_items)} 道检测题）...", 0.40)
    # 从 parsed 提取主语模板与答题人角色，传给主语一致性检查
    item_subject_template = (
        parsed.get("item_subject_template", "")
        or (parsed_research_override or {}).get("item_subject_template", "")
        or ""
    )
    respondent_role = (
        parsed.get("respondent_role", "")
        or (parsed_research_override or {}).get("respondent_role", "")
        or ""
    )
    quality_report = check_item_quality(
        parsed["items"],   # v3.7.10：传完整 items 列表（含 attention_check），让 quota 检查能跑
        parsed["construct_name"],
        respondent_role=respondent_role,
        item_subject_template=item_subject_template,
    )

    # ---- v3.7.10 Step 3: LLM 自审核 pass（critique pass）----
    critique_report: Dict[str, Any] = {
        "items_with_issues": [], "overall_issues": [], "summary": "（已跳过 LLM 评审）"
    }
    if enable_llm_critique:
        report("步骤 3/4：LLM 独立审核每道题（评审员视角）...", 0.55)
        if cancel_id is None or not _is_cancelled(cancel_id):
            critique_report = _run_llm_critique(
                construct_items, parsed["construct_name"],
                parsed_research=parsed,
                api_key=api_key, base_url=base_url, model=model,
                temperature=max(0.1, temperature - 0.1),   # critique 用更低温度
                timeout=timeout, cancel_id=cancel_id,
            )
    else:
        report("步骤 3/4：已跳过 LLM 自审核（enable_llm_critique=False）", 0.55)

    # ---- v3.7.10 Step 4: 合并弱题候选集（本地 ∪ critique）+ 并行重写 ----
    weak_indices = set()
    # 本地规则识别
    for s in quality_report.item_scores:
        if s.get("status") in ("error", "warning") and s.get("score", 10) < 6:
            weak_indices.add(s["index"])
    # LLM critique 识别
    for c in critique_report.get("items_with_issues", []):
        if c.get("severity") in ("error", "warning") and c.get("score", 10) < 6:
            weak_indices.add(c["index"])

    # 索引仅含构念题（注意力检测题不重写）
    construct_index_set = {it["index"] for it in construct_items}
    weak_indices &= construct_index_set

    report(f"步骤 4/4：合并弱题（本地+LLM 评审），共 {len(weak_indices)} 道并行重写...", 0.75)

    if weak_indices:
        index_to_item = {it["index"]: it for it in construct_items}
        # 索引 → 该题的所有 issues（合并本地与 critique）
        index_to_issues: Dict[int, List[str]] = {}
        for s in quality_report.item_scores:
            if s["index"] in weak_indices:
                index_to_issues.setdefault(s["index"], []).extend(
                    [iss.get("msg", "") for iss in s.get("issues", [])]
                )
        for c in critique_report.get("items_with_issues", []):
            if c.get("index") in weak_indices:
                index_to_issues.setdefault(c["index"], []).extend(c.get("issues", []))

        # 索引 → 同维度兄弟题（用作重写时的避免重复参考）
        dim_to_items: Dict[str, List[Dict]] = {}
        for it in construct_items:
            dim_to_items.setdefault(it.get("dimension", ""), []).append(it)

        def _regen_one(weak_idx: int) -> None:
            if cancel_id is not None and _is_cancelled(cancel_id):
                return
            old_item = index_to_item.get(weak_idx)
            if not old_item:
                return
            issues = [m for m in index_to_issues.get(weak_idx, []) if m]
            siblings = [
                it["text"] for it in dim_to_items.get(old_item.get("dimension", ""), [])
                if it["index"] != weak_idx and it.get("text")
            ][:5]
            regen_msgs = [
                {"role": "system", "content": _regenerate_item_prompt_v2(
                    old_text=old_item["text"],
                    issues=issues,
                    construct_name=parsed["construct_name"],
                    dimension_name=old_item.get("dimension", ""),
                    is_reverse=bool(old_item.get("reverse", False)),
                    sibling_items=siblings,
                )},
                {"role": "user", "content": "请改写为高质量版本，严格 JSON 输出。"},
            ]
            try:
                regen_raw = _call_llm(
                    regen_msgs, api_key, base_url, model,
                    temperature, 384, timeout, cancel_id,
                )
                if regen_raw and regen_raw.strip():
                    rewritten = _parse_json(regen_raw, "regenerate")
                    new_text = rewritten.get("text", "").strip()
                    if new_text and len(new_text) >= 5:
                        old_item["text"] = new_text
                        old_item["_regenerated"] = True
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=min(len(weak_indices), 5)) as ex:
            list(ex.map(_regen_one, list(weak_indices)))

    # ---- 装配最终 design（用 _build_design_dict 保持 schema 一致）----
    report("装配最终问卷...", 0.95)
    design = _build_design_dict(parsed, research_question)

    # premium 特有字段
    design["premium_mode"] = True
    design["direct_mode"] = True   # v3.7.7 标识

    # v3.7.9: 构念前置判断字段（Section 0 产物）propagate 到 design
    if "construct_clarity" in parsed:
        design["construct_clarity"] = parsed["construct_clarity"]
    if "theoretical_framework" in parsed:
        design["theoretical_framework"] = parsed["theoretical_framework"]

    # research_parse：直连模式下从 LLM 输出抽取；如有 override，override 字段优先
    research_parse = {
        "research_understanding": parsed.get("research_understanding", ""),
        "respondent_role": parsed.get("respondent_role", ""),
        "population": parsed.get("population", ""),
        "context": parsed.get("context", ""),
        "theoretical_framework": parsed.get("theoretical_framework", ""),
        "summary": parsed.get("research_understanding", ""),
        "research_object": parsed.get("construct_name", ""),
        "primary_construct": parsed.get("construct_name", ""),
    }
    if parsed_research_override:
        # 用户校正字段优先（仅覆盖非空值）
        for k, v in parsed_research_override.items():
            if v not in (None, ""):
                research_parse[k] = v
        # 兜底字段（保持与流水线模式一致的 schema）
        research_parse.setdefault("research_type", "construct_measurement")
        research_parse.setdefault("item_subject_template", "我...")
        research_parse.setdefault("primary_construct", parsed.get("construct_name", ""))
    design["research_parse"] = research_parse
    design["quality_report"] = {
        "total_items": quality_report.total_items,
        "passed": quality_report.passed,
        "warnings": quality_report.warnings,
        "errors": quality_report.errors,
        "summary": quality_report.summary,
        "regenerated_count": len(weak_indices),
        "overall_warnings": quality_report.overall_warnings,   # v3.7.10
        "item_scores": quality_report.item_scores,             # v3.7.10：透明展示每题问题
    }
    # v3.7.10：LLM 自审核报告（与本地 quality_report 并列）
    design["critique_report"] = critique_report

    # v3.7.8: 注意力检测题/社会赞许性检测题单独暴露
    design["attention_checks"] = [
        {
            "index": it.get("index"),
            "text": it.get("text", ""),
            "item_type": it.get("item_type", "attention_check"),
            "expected_answer": it.get("expected_answer", ""),
        }
        for it in quality_check_items
    ]
    design["data_quality_strategy"] = (
        f"已嵌入 {len(quality_check_items)} 道数据质量检测题"
        f"（{sum(1 for x in quality_check_items if x.get('item_type') == 'attention_check')} 道注意力检测，"
        f"{sum(1 for x in quality_check_items if x.get('item_type') == 'social_desirability_check')} 道社会赞许性检测）。"
        "建议施测时答错任一注意力检测题即剔除该被试。"
    ) if quality_check_items else "未嵌入数据质量检测题（建议补加 1-3 道）。"

    report("完成！", 1.0)
    return design


def _is_reasoning_model(model: str) -> bool:
    """v3.7.4: 检测是否为推理模型（thinking/reasoner/o1/o3 系列）。

    推理模型的特点：先生成 reasoning tokens 再生成实际输出。如果 max_tokens
    设得太小，会被 reasoning 吃光，实际内容字段返回空。
    """
    if not model:
        return False
    m = model.lower()
    reasoning_markers = [
        "reasoner", "thinking",
        "o1", "o3", "o4-mini",   # OpenAI o-series
        "r1",                     # DeepSeek R1
        "kimi-thinking", "kimi-k2",   # Kimi 推理变体
        "qwq",                    # 千问推理
    ]
    return any(marker in m for marker in reasoning_markers)


def _safe_skeleton_call(
    messages: list,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    timeout: int,
    cancel_id: Optional[int],
    base_max_tokens: int = 2048,
) -> str:
    """v3.7.4: 健壮的 skeleton 调用——空内容时自动重试 + 推理模型自动加 token。

    返回非空字符串。失败时抛 LLMResponseParseError 并附带诊断。
    """
    # 推理模型自动 bump
    if _is_reasoning_model(model):
        actual_tokens = max(base_max_tokens, 8192)
    else:
        actual_tokens = base_max_tokens

    # 第一次调用
    raw = _call_llm(
        messages, api_key, base_url, model,
        temperature, actual_tokens, timeout, cancel_id,
    )
    if raw and raw.strip():
        return raw

    # 空内容 → 大概率推理模型 token 不够；用更大 token 再试一次
    bigger_tokens = max(actual_tokens * 2, 16384)
    raw2 = _call_llm(
        messages, api_key, base_url, model,
        temperature, bigger_tokens, timeout, cancel_id,
    )
    if raw2 and raw2.strip():
        return raw2

    raise LLMResponseParseError(
        f"LLM 两次返回空内容（model={model}，token 已尝试 {actual_tokens}/{bigger_tokens}）。"
        f"如果你选的是推理模型（如 deepseek-reasoner / o1 / kimi-thinking），"
        f"建议切换到非推理模型（deepseek-chat / gpt-4o / kimi-latest）——"
        f"推理模型会用 token 思考，结构化生成任务下输出常被截断。"
    )


def _default_psychometrics() -> Dict[str, str]:
    """v3.7 兜底：metadata 步骤失败时给一份通用心理测量学策略。

    避免 UI st.tabs([]) 崩；同时给用户一份学术上能用的默认方案。
    """
    return {
        "内容效度": (
            "邀请 3-5 位心理学领域专家对题目进行评定（每题 1-4 分相关性评分），"
            "计算 I-CVI ≥ 0.78（项目水平）和 S-CVI/Ave ≥ 0.90（量表水平）。"
        ),
        "表面效度": (
            "在小样本（n=10-15）目标人群中进行预试，访谈每位被试对题目的理解，"
            "确保题意清晰、无歧义、文化适应。"
        ),
        "结构效度": (
            "样本量 ≥ 200。先做探索性因素分析（EFA，KMO ≥ 0.80，Bartlett p < 0.001），"
            "提取因子（平行分析/碎石图），保留载荷 ≥ 0.40 且交叉载荷 < 0.30 的题目。"
            "另一独立样本做验证性因素分析（CFA），目标 CFI ≥ 0.90，RMSEA < 0.08，SRMR < 0.08。"
        ),
        "内部一致性信度": (
            "计算各维度和总量表的 Cronbach's α，目标 ≥ 0.70（可接受），"
            "≥ 0.80（良好）。同时报告 alpha-if-item-deleted 检查冗余题。"
        ),
        "重测信度": (
            "间隔 2-4 周对同一群体施测，计算 ICC（intra-class correlation），"
            "目标 ≥ 0.70。"
        ),
        "社会称许性控制": (
            "1）使用反向题（约 25%）打乱默认反应模式；"
            "2）问卷开头明确「无对错答案」声明；"
            "3）必要时加 Marlowe-Crowne 社会称许性量表筛查。"
        ),
    }


def _lookup_kb_scales(construct_name: str) -> List[str]:
    """从 construct_kb 找匹配的已有量表（用作 few-shot 风格参考）。"""
    cname = construct_name.strip().lower()
    for key, c in CONSTRUCTS.items():
        if key.lower() == cname or c.get("name_zh", "").lower() == cname:
            return c.get("established_scales", [])[:5] or []
    return []


def design_questionnaire_premium_async(
    research_question: str,
    api_key: str,
    base_url: str,
    model: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: int = 60,
    parsed_research_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """异步入口：返回 {"future": Future, "cancel_id": int, "progress": dict}。"""
    cancel_id = _alloc_cancel_id()
    progress = {"msg": "排队中...", "pct": 0.0, "lock": threading.Lock()}

    def _on_progress(msg: str, pct: float):
        with progress["lock"]:
            progress["msg"] = msg
            progress["pct"] = pct

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="premium_design")

    def _run():
        try:
            return design_questionnaire_premium(
                research_question, api_key, base_url, model,
                temperature=temperature, max_tokens=max_tokens, timeout=timeout,
                cancel_id=cancel_id, progress_callback=_on_progress,
                parsed_research_override=parsed_research_override,
            )
        finally:
            _cleanup_cancel_id(cancel_id)

    future = executor.submit(_run)
    return {"future": future, "cancel_id": cancel_id, "progress": progress}
