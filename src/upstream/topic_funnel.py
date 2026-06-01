"""选题漏斗状态机：5 阶段（兴趣→现象→变量→可研究性→问题陈述）。

设计：
- 阶段数据存 upstream_state.stages[str(stage_id)]
- advance_stage 强制 force=True 触发 autosave，绕过 30s 节流
- 阶段切换时清空 ai_history（避免阶段 1 的发散内容污染阶段 4）
- 完成漏斗 → phase=wizard，把产物写入 wizard_data
- v3.3 新增：FunnelBranch 历史分支系统（修订选题时不丢失旧分支）
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 阶段定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FunnelStage:
    id: int
    name: str
    description: str


STAGES: List[FunnelStage] = [
    FunnelStage(1, "兴趣捕捉", "从模糊兴趣 → 具体的「让你不爽/困惑的现象」"),
    FunnelStage(2, "现象具象化", "从抽象现象 → 「什么人 + 什么场景 + 什么差异」"),
    FunnelStage(3, "变量识别", "从现象 → 「X 差异 → Y 差异」可观察变量对（接 construct_kb）"),
    FunnelStage(4, "可研究性检查", "可证伪 + 可测量 2 项检查（v3.2 简化版）"),
    FunnelStage(5, "问题陈述", "收敛到标准句式：「在[人群]中，[X]是否影响[Y]？」"),
]

MIN_STAGE = 1
MAX_STAGE = 5


def get_stage(stage_id: int) -> Optional[FunnelStage]:
    for s in STAGES:
        if s.id == stage_id:
            return s
    return None


# ---------------------------------------------------------------------------
# Stage 数据读写（依赖 upstream_state）
# ---------------------------------------------------------------------------

def _stage_key(stage_id: int) -> str:
    return str(int(stage_id))


def _get_stages_dict(upstream_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    stages = upstream_state.get("stages")
    if not isinstance(stages, dict):
        stages = {}
        upstream_state["stages"] = stages
    return stages


def get_stage_data(upstream_state: Dict[str, Any], stage_id: int) -> Dict[str, Any]:
    """读取某阶段数据；缺失时返回默认结构（不写回）。"""
    stages = _get_stages_dict(upstream_state)
    return stages.get(_stage_key(stage_id)) or _default_stage_entry()


def update_stage_data(
    upstream_state: Dict[str, Any],
    stage_id: int,
    **fields: Any,
) -> None:
    """更新某阶段数据（merge）。"""
    stages = _get_stages_dict(upstream_state)
    key = _stage_key(stage_id)
    entry = stages.get(key) or _default_stage_entry()
    entry.update(fields)
    stages[key] = entry


def _default_stage_entry() -> Dict[str, Any]:
    return {
        "interest_text": "",
        "ai_history": [],
        "output": {},
        "completed": False,
    }


# ---------------------------------------------------------------------------
# 阶段推进
# ---------------------------------------------------------------------------

def advance_stage(
    session_state: Any,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> int:
    """推进到下一阶段，返回新的 stage_id。

    关键：阶段切换时强制保存（绕过 30s autosave 节流）。
    """
    from src.utils.workspace import get_upstream_state, update_last_position
    upstream = get_upstream_state(session_state)
    cur = int(upstream.get("current_stage", MIN_STAGE))
    # 当前阶段标记完成
    update_stage_data(upstream, cur, completed=True)
    # 推进
    nxt = min(cur + 1, MAX_STAGE)
    upstream["current_stage"] = nxt
    update_last_position("funnel", step=nxt, session_state=session_state)
    # 强制保存
    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return nxt


def go_to_stage(
    session_state: Any,
    stage_id: int,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> int:
    """直接跳到指定阶段（用户点步进器跳转）。"""
    from src.utils.workspace import get_upstream_state, update_last_position
    upstream = get_upstream_state(session_state)
    target = max(MIN_STAGE, min(MAX_STAGE, int(stage_id)))
    upstream["current_stage"] = target
    update_last_position("funnel", step=target, session_state=session_state)
    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return target


def restart_funnel(
    session_state: Any,
    *,
    keep_history: bool = True,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> None:
    """从 wizard 回到漏斗（保留模式）。

    v3.3 行为：
    - keep_history=True: 仅切回 phase=funnel，stages 不动（"继续修改"语义）
    - keep_history=False: 清空 stages 和产物（"全新开始"）
    - 想要"打包归档分支"语义请用 archive_current_branch_and_restart()
    """
    from src.utils.workspace import get_upstream_state, update_last_position
    upstream = get_upstream_state(session_state)
    upstream["phase"] = "funnel"
    upstream["current_stage"] = MIN_STAGE if not keep_history else 5
    update_last_position("funnel", step=upstream["current_stage"], session_state=session_state)
    if not keep_history:
        upstream["stages"] = {}
        upstream["research_question"] = ""
        upstream["candidate_vars"] = {
            "dependent_vars": [],
            "independent_vars": [],
            "grouping_var": "",
            "covariates": [],
        }
        upstream["feasibility_results"] = {}
    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)


def complete_funnel(
    session_state: Any,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """阶段 5 确认 → phase=wizard，把产物写入 wizard_data。

    Returns: 写入 wizard_data 的字段（供 UI 显示确认）。
    """
    from src.utils.workspace import get_upstream_state, update_last_position
    upstream = get_upstream_state(session_state)
    upstream["phase"] = "wizard"
    update_stage_data(upstream, 5, completed=True)
    update_last_position("wizard", step=1, session_state=session_state)

    # 把产物注入 wizard_data
    wizard = session_state.get("undergrad_wizard_data")
    if not isinstance(wizard, dict):
        wizard = {}
        session_state["undergrad_wizard_data"] = wizard

    research_q = upstream.get("research_question", "") or ""
    candidate = upstream.get("candidate_vars") or {}

    payload: Dict[str, Any] = {}
    if research_q:
        payload["research_q"] = research_q
        # title 默认与 research_q 同；用户可在 wizard step 1 编辑
        if not wizard.get("title"):
            payload["title"] = research_q[:40]
    dvs = candidate.get("dependent_vars") or []
    ivs = candidate.get("independent_vars") or []
    if dvs:
        payload["dv"] = dvs[0]
    if ivs:
        payload["iv"] = ivs[0]

    wizard.update(payload)

    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return payload


# ---------------------------------------------------------------------------
# 阶段 3：变量识别（接 IntentRecognitionChain）
# ---------------------------------------------------------------------------

def recognize_constructs(
    text: str,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """对学生输入做构念匹配，返回阶段 3 候选变量。

    Args:
        text: 学生在阶段 1-2 的合并描述
        llm_config: 含 api_key 时启用 LLM 消歧层

    Returns:
        {
            "is_ambiguous": bool,
            "top_construct": str | None,
            "candidates": [{"name": str, "confidence": float, "domain": str, "reason": str}],
            "suggestion": str,
        }
    """
    if not text or not text.strip():
        return {
            "is_ambiguous": True,
            "top_construct": None,
            "candidates": [],
            "suggestion": "请先描述你想研究的现象再做变量识别。",
        }

    try:
        from src.questionnaire.construct_kb import CONSTRUCTS, CONSTRUCT_KEYWORDS
        from src.questionnaire.construct_kb_extended import EXTENDED_CONSTRUCTS
        from src.questionnaire.intent_recognizer import create_default_chain
    except Exception as exc:
        return {
            "is_ambiguous": True,
            "top_construct": None,
            "candidates": [],
            "suggestion": f"构念库加载失败：{exc}",
        }

    chain = create_default_chain(
        constructs=CONSTRUCTS,
        keywords=CONSTRUCT_KEYWORDS,
        extended_constructs=EXTENDED_CONSTRUCTS,
        llm_config=llm_config if (llm_config and llm_config.get("api_key")) else None,
    )

    try:
        result = chain.recognize(text, llm_config=llm_config)
    except Exception as exc:
        return {
            "is_ambiguous": True,
            "top_construct": None,
            "candidates": [],
            "suggestion": f"识别过程出错：{exc}",
        }

    candidates_out = [
        {
            "name": c.construct_name,
            "confidence": float(c.confidence),
            "domain": c.domain,
            "reason": c.match_reason,
        }
        for c in (result.candidates or [])[:5]
    ]
    return {
        "is_ambiguous": bool(result.is_ambiguous),
        "top_construct": result.top_candidate.construct_name if result.top_candidate else None,
        "candidates": candidates_out,
        "suggestion": result.suggestion,
    }


def set_candidate_vars(
    session_state: Any,
    *,
    dependent_vars: Optional[List[str]] = None,
    independent_vars: Optional[List[str]] = None,
    grouping_var: str = "",
    covariates: Optional[List[str]] = None,
) -> None:
    """写入阶段 3 输出到 upstream_state.candidate_vars（AnalysisPlan schema）。"""
    from src.utils.workspace import get_upstream_state
    upstream = get_upstream_state(session_state)
    upstream["candidate_vars"] = {
        "dependent_vars": list(dependent_vars or []),
        "independent_vars": list(independent_vars or []),
        "grouping_var": grouping_var or "",
        "covariates": list(covariates or []),
    }


# ---------------------------------------------------------------------------
# 内部：autosave 强制触发
# ---------------------------------------------------------------------------

def _force_save(
    session_state: Any,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> None:
    """阶段切换时强制保存 workspace（绕过 autosave 节流）。

    优先用注入的 save_workspace_fn（测试用），否则尝试调 autosave.trigger_autosave。
    """
    if save_workspace_fn is not None:
        try:
            save_workspace_fn(session_state, project_id)
        except Exception:
            pass
        return

    # 默认路径：调 autosave.trigger_autosave(session_state, build_workspace_snapshot, force=True)
    try:
        from src.utils.autosave import trigger_autosave
        from src.utils.workspace import build_workspace_snapshot
        trigger_autosave(session_state, build_workspace_snapshot, force=True)
    except Exception:
        # 静默失败：autosave 故障不应阻塞漏斗推进
        pass


# ---------------------------------------------------------------------------
# v3.3 漏斗分支系统
# ---------------------------------------------------------------------------

@dataclass
class FunnelBranch:
    """归档的漏斗分支：一次完整选题尝试的快照。"""
    branch_id: str
    created_at: str
    final_research_q: str
    stages_snapshot: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    candidate_vars: Dict[str, Any] = field(default_factory=dict)
    feasibility_results: Dict[str, Any] = field(default_factory=dict)
    status: str = "archived"     # active | archived

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FunnelBranch":
        return cls(
            branch_id=data.get("branch_id") or _new_branch_id(),
            created_at=data.get("created_at") or _now_iso(),
            final_research_q=data.get("final_research_q", ""),
            stages_snapshot=data.get("stages_snapshot") or {},
            candidate_vars=data.get("candidate_vars") or {},
            feasibility_results=data.get("feasibility_results") or {},
            status=data.get("status", "archived"),
        )


def _new_branch_id() -> str:
    return uuid.uuid4().hex[:10]


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _serialize_stages(stages: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """把 stages 中的 ChatMessage 序列化为可 JSON 的 dict（便于存入分支）。"""
    out: Dict[str, Dict[str, Any]] = {}
    for sid, sdata in (stages or {}).items():
        if not isinstance(sdata, dict):
            continue
        entry = copy.deepcopy({k: v for k, v in sdata.items() if k != "ai_history"})
        history = sdata.get("ai_history") or []
        entry["ai_history"] = [
            {"role": getattr(m, "role", None) or m.get("role", ""),
             "content": getattr(m, "content", None) or m.get("content", "")}
            if (hasattr(m, "role") or isinstance(m, dict)) else {}
            for m in history
        ]
        out[str(sid)] = entry
    return out


def _deserialize_stages(stages: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """反序列化分支的 stages（把 dict 转回 ChatMessage）。"""
    try:
        from src.paper_writer.ai_tutor import ChatMessage
    except Exception:
        ChatMessage = None
    out: Dict[str, Dict[str, Any]] = {}
    for sid, sdata in (stages or {}).items():
        if not isinstance(sdata, dict):
            continue
        entry = copy.deepcopy({k: v for k, v in sdata.items() if k != "ai_history"})
        history = sdata.get("ai_history") or []
        rebuilt = []
        for m in history:
            if isinstance(m, dict) and "role" in m and "content" in m and ChatMessage:
                rebuilt.append(ChatMessage(role=m["role"], content=m["content"]))
            else:
                rebuilt.append(m)
        entry["ai_history"] = rebuilt
        out[str(sid)] = entry
    return out


def get_funnel_history(session_state: Any) -> List[Dict[str, Any]]:
    """读取已归档分支列表（按创建时间倒序）。"""
    from src.utils.workspace import get_upstream_state
    upstream = get_upstream_state(session_state)
    history = upstream.get("funnel_history")
    if not isinstance(history, list):
        history = []
        upstream["funnel_history"] = history
    return list(history)


def archive_current_branch(
    session_state: Any,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> Optional[str]:
    """把当前 active 漏斗状态打包归档为 FunnelBranch，返回 branch_id。

    若当前 stages 为空（未进入漏斗）→ 不归档，返回 None。
    """
    from src.utils.workspace import get_upstream_state
    upstream = get_upstream_state(session_state)
    stages = upstream.get("stages") or {}
    rq = upstream.get("research_question", "")
    if not stages and not rq:
        return None    # 空白漏斗不归档

    branch = FunnelBranch(
        branch_id=_new_branch_id(),
        created_at=_now_iso(),
        final_research_q=rq,
        stages_snapshot=_serialize_stages(stages),
        candidate_vars=copy.deepcopy(upstream.get("candidate_vars") or {}),
        feasibility_results=copy.deepcopy(upstream.get("feasibility_results") or {}),
        status="archived",
    )
    history = upstream.get("funnel_history")
    if not isinstance(history, list):
        history = []
        upstream["funnel_history"] = history
    history.insert(0, branch.as_dict())     # 最新在前

    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return branch.branch_id


def archive_current_branch_and_restart(
    session_state: Any,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> Optional[str]:
    """归档当前分支 → 清空 active → 切回 phase=funnel/stage=1。"""
    bid = archive_current_branch(
        session_state,
        save_workspace_fn=save_workspace_fn,
        project_id=project_id,
    )
    from src.utils.workspace import get_upstream_state
    upstream = get_upstream_state(session_state)
    upstream["phase"] = "funnel"
    upstream["current_stage"] = MIN_STAGE
    upstream["stages"] = {}
    upstream["research_question"] = ""
    upstream["candidate_vars"] = {
        "dependent_vars": [],
        "independent_vars": [],
        "grouping_var": "",
        "covariates": [],
    }
    upstream["feasibility_results"] = {}
    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return bid


def switch_to_branch(
    session_state: Any,
    branch_id: str,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> bool:
    """切换到指定分支：当前 active 归档，目标分支恢复为 active。"""
    from src.utils.workspace import get_upstream_state
    upstream = get_upstream_state(session_state)
    history = upstream.get("funnel_history") or []

    target = None
    target_idx = -1
    for i, b in enumerate(history):
        if isinstance(b, dict) and b.get("branch_id") == branch_id:
            target = b
            target_idx = i
            break
    if target is None:
        return False

    # 归档当前 active（如果有内容）
    archive_current_branch(
        session_state,
        save_workspace_fn=None,    # 避免双保存
        project_id=project_id,
    )

    # 重新读取（archive 可能修改了 history）
    upstream = get_upstream_state(session_state)
    history = upstream.get("funnel_history") or []
    target_idx = -1
    for i, b in enumerate(history):
        if isinstance(b, dict) and b.get("branch_id") == branch_id:
            target = b
            target_idx = i
            break
    if target is None:
        return False

    # 恢复目标分支为 active
    upstream["stages"] = _deserialize_stages(target.get("stages_snapshot") or {})
    upstream["research_question"] = target.get("final_research_q", "")
    upstream["candidate_vars"] = copy.deepcopy(target.get("candidate_vars") or {})
    upstream["feasibility_results"] = copy.deepcopy(target.get("feasibility_results") or {})
    upstream["phase"] = "funnel"
    upstream["current_stage"] = MAX_STAGE if target.get("final_research_q") else MIN_STAGE
    # 从 history 中移除（已恢复为 active）
    history.pop(target_idx)
    upstream["funnel_history"] = history

    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return True


def delete_branch(
    session_state: Any,
    branch_id: str,
    *,
    save_workspace_fn: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> bool:
    """删除指定归档分支。"""
    from src.utils.workspace import get_upstream_state
    upstream = get_upstream_state(session_state)
    history = upstream.get("funnel_history") or []
    new_history = [b for b in history if isinstance(b, dict) and b.get("branch_id") != branch_id]
    if len(new_history) == len(history):
        return False
    upstream["funnel_history"] = new_history
    _force_save(session_state, save_workspace_fn=save_workspace_fn, project_id=project_id)
    return True


# ---------------------------------------------------------------------------
# v3.3 ADVANCED 留痕 → 答辩问答自动生成
# ---------------------------------------------------------------------------

def generate_motivation_qa_from_advanced(
    advanced_meta: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """根据 advanced_meta 生成答辩动机问答（wizard step 7 调用）。

    Returns: List of {"question", "answer_template", "category", "difficulty"}.
            空 meta 返回空列表。
    """
    if not isinstance(advanced_meta, dict):
        return []
    source = advanced_meta.get("source", "").strip()
    why = advanced_meta.get("why", "").strip()
    most_care = advanced_meta.get("most_care", "").strip()
    if not (source or why or most_care):
        return []

    items: List[Dict[str, str]] = []
    if why or source:
        ans = []
        if source:
            ans.append(f"这个研究问题来自{source}")
        if why:
            ans.append(why if why.endswith("。") else why + "。")
        items.append({
            "question": "你为什么选择这个题目？",
            "answer_template": "".join(ans),
            "category": "研究动机",
            "difficulty": "🟢 必问",
        })
    if most_care:
        items.append({
            "question": "你最希望通过这项研究发现什么？",
            "answer_template": most_care if most_care.endswith("。") else most_care + "。",
            "category": "研究动机",
            "difficulty": "🟢 必问",
        })
    if source:
        items.append({
            "question": f"你提到本研究来自{source}，能具体说说当时的契机吗？",
            "answer_template": (why or "可补充：当时具体观察到什么、产生了什么疑问、为何选择了这个角度。"),
            "category": "研究动机",
            "difficulty": "🟡 常问",
        })
    return items
