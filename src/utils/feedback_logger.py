"""本地反馈日志与匿名诊断包 v5.1。

隐私优先设计：
- 默认不上传原始数据
- 默认不记录具体答题值
- 反馈日志只记录事件和错误类型
- 用户主动点击后才导出匿名诊断包
- 诊断包脱敏变量名、文件名和项目名
"""

from __future__ import annotations

import json
import hashlib
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


FEEDBACK_DIR = Path("data/feedback_logs")


@dataclass
class FeedbackEvent:
    event_type: str  # "page_visit" / "action" / "error" / "export" / "abandon"
    timestamp: str = ""
    page: str = ""
    action: str = ""
    duration_ms: int = 0
    error_type: str = ""
    error_message: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")


class FeedbackLogger:
    """本地反馈事件记录器。所有数据仅保存在本地。"""

    def __init__(self, session_id: str = "", log_dir: Path = FEEDBACK_DIR):
        self._log_dir = log_dir
        self._session_id = session_id or hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:8]
        self._events: list[FeedbackEvent] = []
        self._start_time = time.time()

    @property
    def session_id(self) -> str:
        return self._session_id

    def log_event(self, event: FeedbackEvent):
        self._events.append(event)

    def log_page_visit(self, page: str):
        self.log_event(FeedbackEvent(event_type="page_visit", page=page))

    def log_action(self, page: str, action: str, **metadata):
        self.log_event(FeedbackEvent(
            event_type="action", page=page, action=action, metadata=metadata,
        ))

    def log_error(self, page: str, error_type: str, error_message: str = ""):
        sanitized_msg = _sanitize_error(error_message)
        self.log_event(FeedbackEvent(
            event_type="error", page=page,
            error_type=error_type, error_message=sanitized_msg,
        ))

    def log_export(self, format: str, success: bool, duration_ms: int = 0):
        self.log_event(FeedbackEvent(
            event_type="export", action=format,
            duration_ms=duration_ms,
            metadata={"success": success},
        ))

    def log_abandon(self, page: str):
        self.log_event(FeedbackEvent(event_type="abandon", page=page))

    def save_session(self) -> Path:
        """保存当前 session 日志到本地文件。"""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        filename = f"session_{self._session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        filepath = self._log_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for event in self._events:
                f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return filepath

    def get_session_summary(self) -> dict:
        """获取当前 session 的统计摘要。"""
        total_duration = time.time() - self._start_time
        pages_visited = set(e.page for e in self._events if e.page)
        errors = [e for e in self._events if e.event_type == "error"]
        exports = [e for e in self._events if e.event_type == "export"]

        return {
            "session_id": self._session_id,
            "total_events": len(self._events),
            "duration_seconds": round(total_duration),
            "pages_visited": list(pages_visited),
            "error_count": len(errors),
            "export_count": len(exports),
            "export_success": sum(1 for e in exports if e.metadata.get("success")),
        }


def generate_diagnostic_package(
    session_state: dict,
    feedback_logger: Optional[FeedbackLogger] = None,
) -> dict:
    """生成匿名诊断包（脱敏后的项目状态快照）。"""
    package = {
        "generated_at": datetime.now().isoformat(),
        "version": "5.1",
        "system_state": {},
        "session_summary": {},
    }

    package["system_state"] = {
        "has_data": session_state.get("uploaded_df") is not None,
        "data_shape": _safe_shape(session_state.get("uploaded_df")),
        "has_recommendations": bool(session_state.get("method_recommendations")),
        "n_analysis_cards": len(session_state.get("analysis_cards", [])),
        "n_figures": len(session_state.get("apa_figures", [])),
        "n_evidence": len(session_state.get("evidence_records", [])),
        "has_paper": session_state.get("paper_bundle") is not None,
        "template_source": _anonymize(session_state.get("template_source", "")),
    }

    if feedback_logger:
        package["session_summary"] = feedback_logger.get_session_summary()

    return package


def clear_feedback_logs(log_dir: Path = FEEDBACK_DIR) -> int:
    """清除所有本地反馈日志。返回删除的文件数量。"""
    if not log_dir.exists():
        return 0
    count = 0
    for f in log_dir.glob("*.jsonl"):
        f.unlink()
        count += 1
    return count


def _sanitize_error(msg: str) -> str:
    """脱敏错误消息中的路径和个人信息。"""
    msg = re.sub(r"[A-Z]:\\[^\s\"']+", "<path>", msg)
    msg = re.sub(r"/home/[^\s/]+", "<user>", msg)
    msg = re.sub(r"\b\d{11}\b", "<phone>", msg)
    msg = re.sub(r"[\w.]+@[\w.]+", "<email>", msg)
    return msg[:500]


def _safe_shape(df) -> Optional[list]:
    if df is None:
        return None
    try:
        return [int(df.shape[0]), int(df.shape[1])]
    except Exception:
        return None


def _anonymize(s: str) -> str:
    if not s:
        return ""
    return hashlib.md5(s.encode()).hexdigest()[:8]
