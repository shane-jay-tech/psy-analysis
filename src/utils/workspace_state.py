"""WorkspaceState 顶层 dataclass（v3.5）。

设计：
- WorkspaceState 作为 session_state 上的**类型化视图**，不替换 session_state
- 各模块通过 `get_workspace()` 获取，读写时 to_dict()/from_dict() 与底层同步
- 兼容性：未激活时仍可读旧 session_state 散落字段（v3.4 兼容路径）
- 序列化：workspace.py 优先用 WorkspaceState.to_dict()，回退到旧字段收集

字段分组：
- funnel       : 漏斗+tier+阶段历史+苏格拉底（继承 v3.4 upstream_state 全部字段）
- literature_review: 文献综述工作台（v3.4 literature_review_state）
- wizard       : path/step/wizard_data/results_context
- analysis     : analysis_history/plan/output（向导第 5/6 步运行结果）
- advanced     : ADVANCED 留痕（来源/动机/最关心发现）
- ui           : undergrad_mode/current_tab/各种瞬时状态（不持久化的可标记 transient）
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


WORKSPACE_KEY = "workspace"


# ---------------------------------------------------------------------------
# 子状态
# ---------------------------------------------------------------------------

@dataclass
class FunnelState:
    """漏斗 + tier + 阶段历史（继承 v3.4 upstream_state）。"""
    tier: str = "beginner"
    phase: str = "funnel"                 # funnel | literature_review | wizard | done
    current_stage: int = 1
    stages: Dict[str, Any] = field(default_factory=dict)
    research_question: str = ""
    candidate_vars: Dict[str, Any] = field(default_factory=lambda: {
        "dependent_vars": [],
        "independent_vars": [],
        "grouping_var": "",
        "covariates": [],
    })
    feasibility_results: Dict[str, Any] = field(default_factory=dict)
    funnel_history: List[Dict[str, Any]] = field(default_factory=list)
    asked_themes: List[str] = field(default_factory=list)


@dataclass
class LiteratureReviewState:
    literature_items: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    matrix: Dict[str, Any] = field(default_factory=lambda: {
        "dimensions": ["样本量", "研究设计", "主要发现", "效应量", "局限"],
        "cells": {},
        "highlighted_keys": [],
    })
    themes: List[Dict[str, Any]] = field(default_factory=list)
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    last_search_query: str = ""
    last_search_at: str = ""
    # v3.5 新增：搜索/聚类/gap 的方法标识（UI 透明降级用）
    last_search_method: str = ""              # "online" | "offline" | "chinese_only"
    last_cluster_method: str = ""             # "kmeans" | "keyword_overlap" | "by_literature"
    last_gap_source: str = ""                 # "llm" | "heuristic"


@dataclass
class WizardState:
    undergrad_path: Optional[str] = None       # "survey" | "experiment" | None
    undergrad_step: int = 0
    wizard_data: Dict[str, Any] = field(default_factory=dict)
    wizard_back_dialog: bool = False


@dataclass
class AnalysisState:
    analysis_history: List[Dict[str, Any]] = field(default_factory=list)
    plan: Optional[Dict[str, Any]] = None
    analysis_output: Optional[Dict[str, Any]] = None


@dataclass
class AdvancedMeta:
    source: str = ""           # "已有想法" | "老师指定" | "文献启发" | "实习观察" | "其他"
    why: str = ""
    most_care: str = ""


@dataclass
class UIState:
    undergrad_mode: bool = False
    funnel_intro_shown: bool = False
    quality_preview_dismissed: bool = False


# ---------------------------------------------------------------------------
# 顶层
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceState:
    funnel: FunnelState = field(default_factory=FunnelState)
    literature_review: LiteratureReviewState = field(default_factory=LiteratureReviewState)
    wizard: WizardState = field(default_factory=WizardState)
    analysis: AnalysisState = field(default_factory=AnalysisState)
    advanced: AdvancedMeta = field(default_factory=AdvancedMeta)
    ui: UIState = field(default_factory=UIState)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceState":
        if not isinstance(data, dict):
            return cls()
        return cls(
            funnel=FunnelState(**_safe_subset(FunnelState, data.get("funnel"))),
            literature_review=LiteratureReviewState(
                **_safe_subset(LiteratureReviewState, data.get("literature_review"))
            ),
            wizard=WizardState(**_safe_subset(WizardState, data.get("wizard"))),
            analysis=AnalysisState(**_safe_subset(AnalysisState, data.get("analysis"))),
            advanced=AdvancedMeta(**_safe_subset(AdvancedMeta, data.get("advanced"))),
            ui=UIState(**_safe_subset(UIState, data.get("ui"))),
        )

    @classmethod
    def from_legacy_session(cls, session_state: Any) -> "WorkspaceState":
        """从 v3.4 session_state 散落字段构造 WorkspaceState（兼容入口）。"""
        ws = cls()
        # funnel ← upstream_state
        upstream = session_state.get("upstream_state") if hasattr(session_state, "get") else None
        if isinstance(upstream, dict):
            ws.funnel = FunnelState(
                tier=upstream.get("tier", "beginner"),
                phase=upstream.get("phase", "funnel"),
                current_stage=int(upstream.get("current_stage") or 1),
                stages=dict(upstream.get("stages") or {}),
                research_question=upstream.get("research_question", ""),
                candidate_vars=dict(upstream.get("candidate_vars") or ws.funnel.candidate_vars),
                feasibility_results=dict(upstream.get("feasibility_results") or {}),
                funnel_history=list(upstream.get("funnel_history") or []),
                asked_themes=list(upstream.get("asked_themes") or []),
            )
            ws.advanced = AdvancedMeta(
                source=(upstream.get("advanced_meta") or {}).get("source", ""),
                why=(upstream.get("advanced_meta") or {}).get("why", ""),
                most_care=(upstream.get("advanced_meta") or {}).get("most_care", ""),
            )
        # literature_review ← literature_review_state
        lr = session_state.get("literature_review_state") if hasattr(session_state, "get") else None
        if isinstance(lr, dict):
            ws.literature_review = LiteratureReviewState(
                literature_items=list(lr.get("literature_items") or []),
                notes=list(lr.get("notes") or []),
                matrix=dict(lr.get("matrix") or ws.literature_review.matrix),
                themes=list(lr.get("themes") or []),
                gaps=list(lr.get("gaps") or []),
                last_search_query=lr.get("last_search_query", ""),
                last_search_at=lr.get("last_search_at", ""),
                last_search_method=lr.get("last_search_method", ""),
                last_cluster_method=lr.get("last_cluster_method", ""),
                last_gap_source=lr.get("last_gap_source", ""),
            )
        # wizard
        ws.wizard = WizardState(
            undergrad_path=session_state.get("undergrad_path") if hasattr(session_state, "get") else None,
            undergrad_step=int(session_state.get("undergrad_step") or 0) if hasattr(session_state, "get") else 0,
            wizard_data=dict(session_state.get("undergrad_wizard_data") or {}) if hasattr(session_state, "get") else {},
        )
        # analysis
        ws.analysis = AnalysisState(
            analysis_history=list(session_state.get("analysis_history") or []) if hasattr(session_state, "get") else [],
            plan=session_state.get("plan") if hasattr(session_state, "get") else None,
            analysis_output=session_state.get("analysis_output") if hasattr(session_state, "get") else None,
        )
        # ui
        ws.ui = UIState(
            undergrad_mode=bool(session_state.get("undergrad_mode")) if hasattr(session_state, "get") else False,
            funnel_intro_shown=bool(session_state.get("funnel_intro_shown")) if hasattr(session_state, "get") else False,
            quality_preview_dismissed=bool(session_state.get("_quality_preview_dismissed")) if hasattr(session_state, "get") else False,
        )
        return ws

    def sync_to_legacy_session(self, session_state: Any) -> None:
        """v3.5 过渡期：将 WorkspaceState 写回 session_state 散落字段（保持向后兼容）。"""
        session_state["upstream_state"] = {
            "tier": self.funnel.tier,
            "phase": self.funnel.phase,
            "current_stage": self.funnel.current_stage,
            "stages": self.funnel.stages,
            "research_question": self.funnel.research_question,
            "candidate_vars": self.funnel.candidate_vars,
            "feasibility_results": self.funnel.feasibility_results,
            "funnel_history": self.funnel.funnel_history,
            "asked_themes": self.funnel.asked_themes,
            "advanced_meta": {
                "source": self.advanced.source,
                "why": self.advanced.why,
                "most_care": self.advanced.most_care,
            },
        }
        session_state["literature_review_state"] = asdict(self.literature_review)
        session_state["undergrad_path"] = self.wizard.undergrad_path
        session_state["undergrad_step"] = self.wizard.undergrad_step
        session_state["undergrad_wizard_data"] = self.wizard.wizard_data
        session_state["undergrad_mode"] = self.ui.undergrad_mode
        session_state["funnel_intro_shown"] = self.ui.funnel_intro_shown


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _safe_subset(cls, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """只保留 dataclass 已声明的字段，避免 unknown kwargs 导致 TypeError。"""
    if not isinstance(data, dict):
        return {}
    fields = set(cls.__dataclass_fields__.keys())
    return {k: v for k, v in data.items() if k in fields}


def get_workspace(session_state: Any = None) -> WorkspaceState:
    """获取或初始化 WorkspaceState。

    优先级：
    1. session_state[WORKSPACE_KEY] 已存在 → 直接返回
    2. session_state 含 v3.4 散落字段 → from_legacy_session 重建
    3. 全空 → 新建空 WorkspaceState
    """
    if session_state is None:
        try:
            import streamlit as st
            session_state = st.session_state
        except Exception:
            return WorkspaceState()

    existing = session_state.get(WORKSPACE_KEY) if hasattr(session_state, "get") else None
    if isinstance(existing, WorkspaceState):
        return existing
    if isinstance(existing, dict):
        ws = WorkspaceState.from_dict(existing)
        session_state[WORKSPACE_KEY] = ws
        return ws

    # 兼容路径：从旧 session_state 字段重建
    ws = WorkspaceState.from_legacy_session(session_state)
    session_state[WORKSPACE_KEY] = ws
    return ws


def set_workspace(session_state: Any, workspace: WorkspaceState) -> None:
    session_state[WORKSPACE_KEY] = workspace
    workspace.sync_to_legacy_session(session_state)
