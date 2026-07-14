"""UI 状态持久化工具 — 管理 session_state 中的复合状态。

核心职责：
- PaperDiffSelectionState: AI 差异选择持久化（刷新后不丢）
- 状态读写辅助函数
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from src.ui.state_keys import (
    PAPER_DIFF_SELECTION_KEY,
    ANALYSIS_CARDS_KEY,
    PROJECT_HEALTH_ISSUES_KEY,
    PROJECT_HEALTH_CHECKED_AT_KEY,
    EXPORT_ALLOWED_KEY,
    EXPORT_BLOCK_REASONS_KEY,
)


@dataclass
class PaperDiffSelectionState:
    """AI 差异选择持久状态 — 存入 session_state 以跨刷新保留。"""
    original_bundle_id: str = ""
    revised_bundle_id: str = ""
    section_choices: dict[str, str] = field(default_factory=dict)
    paragraph_choices: dict[str, dict[str, str]] = field(default_factory=dict)
    updated_at: str = ""

    def record_section_choice(self, section_key: str, choice: str):
        self.section_choices[section_key] = choice
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def record_paragraph_choice(self, section_key: str, para_idx: str, choice: str):
        if section_key not in self.paragraph_choices:
            self.paragraph_choices[section_key] = {}
        self.paragraph_choices[section_key][para_idx] = choice
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def accept_all_revised(self, section_keys: list[str]):
        for key in section_keys:
            self.section_choices[key] = "revised"
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def keep_all_original(self, section_keys: list[str]):
        for key in section_keys:
            self.section_choices[key] = "original"
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def has_unconfirmed(self, all_section_keys: list[str]) -> bool:
        for key in all_section_keys:
            if key not in self.section_choices:
                return True
        return False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PaperDiffSelectionState:
        return cls(
            original_bundle_id=data.get("original_bundle_id", ""),
            revised_bundle_id=data.get("revised_bundle_id", ""),
            section_choices=data.get("section_choices", {}),
            paragraph_choices=data.get("paragraph_choices", {}),
            updated_at=data.get("updated_at", ""),
        )


def get_diff_selection(session_state: dict) -> PaperDiffSelectionState:
    """从 session_state 获取或初始化差异选择状态。"""
    raw = session_state.get(PAPER_DIFF_SELECTION_KEY)
    if isinstance(raw, PaperDiffSelectionState):
        return raw
    if isinstance(raw, dict):
        return PaperDiffSelectionState.from_dict(raw)
    state = PaperDiffSelectionState()
    session_state[PAPER_DIFF_SELECTION_KEY] = state
    return state


def save_diff_selection(session_state: dict, state: PaperDiffSelectionState):
    """将差异选择状态写回 session_state。"""
    session_state[PAPER_DIFF_SELECTION_KEY] = state


def append_result_card(session_state: dict, card: Any):
    """将结果卡追加到 session_state 中的结果卡列表。"""
    if ANALYSIS_CARDS_KEY not in session_state:
        session_state[ANALYSIS_CARDS_KEY] = []
    session_state[ANALYSIS_CARDS_KEY].append(card)


def get_result_cards(session_state: dict) -> list:
    """获取当前所有结果卡。"""
    return session_state.get(ANALYSIS_CARDS_KEY, [])


def set_health_check_result(session_state: dict, issues: list[dict]):
    """保存健康检查结果到 session_state。"""
    session_state[PROJECT_HEALTH_ISSUES_KEY] = issues
    session_state[PROJECT_HEALTH_CHECKED_AT_KEY] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    has_error = any(i.get("level") == "ERROR" for i in issues)
    session_state[EXPORT_ALLOWED_KEY] = not has_error
    if has_error:
        session_state[EXPORT_BLOCK_REASONS_KEY] = [
            i.get("message", "") for i in issues if i.get("level") == "ERROR"
        ]
    else:
        session_state[EXPORT_BLOCK_REASONS_KEY] = []


def is_export_allowed(session_state: dict) -> tuple[bool, list[str]]:
    """检查是否允许导出。返回 (allowed, block_reasons)。"""
    allowed = session_state.get(EXPORT_ALLOWED_KEY, True)
    reasons = session_state.get(EXPORT_BLOCK_REASONS_KEY, [])
    return allowed, reasons
