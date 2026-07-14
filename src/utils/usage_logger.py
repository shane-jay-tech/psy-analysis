"""使用事件日志模块 — v5.3 新增。

记录匿名化的用户行为事件，用于试用分析和产品改进。
遵循隐私最小化原则：不记录原始数据、论文文本或敏感个人信息。

使用方式：
    from src.utils.usage_logger import log_event, log_error, export_feedback_package

    log_event("page_visit", page_id="项目状态")
    log_event("analysis_execute", method_id="pearson_correlation", success=True, duration_ms=1200)
    log_error("export_failed", error_id="pdf_unavailable", severity="warning")
"""
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any

_LOG_DIR = Path("logs")
_ENABLED = True


def _ensure_log_dir():
    """确保日志目录存在。"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def set_enabled(enabled: bool):
    """启用或禁用事件日志记录。"""
    global _ENABLED
    _ENABLED = enabled


def is_enabled() -> bool:
    """返回日志是否启用。"""
    return _ENABLED


def log_event(event_type: str, **kwargs):
    """记录一个使用事件。

    Args:
        event_type: 事件类型，如 page_visit, analysis_execute, export_execute
        **kwargs: 事件附加字段（不得包含原始数据或敏感信息）
    """
    if not _ENABLED:
        return
    _ensure_log_dir()

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event_type,
        **kwargs,
    }

    log_file = _LOG_DIR / f"usage_events_{date.today().strftime('%Y%m%d')}.jsonl"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_error(error_type: str, **kwargs):
    """记录一个错误事件。

    Args:
        error_type: 错误类型标识
        **kwargs: 错误附加字段（不记录原始错误文本中的敏感内容）
    """
    if not _ENABLED:
        return
    _ensure_log_dir()

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error_type,
        **kwargs,
    }

    log_file = _LOG_DIR / f"error_events_{date.today().strftime('%Y%m%d')}.jsonl"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def get_usage_summary(days: int = 7) -> dict:
    """获取最近 N 天的使用摘要。"""
    _ensure_log_dir()
    events_by_type: dict[str, int] = {}
    total_events = 0

    for log_file in sorted(_LOG_DIR.glob("usage_events_*.jsonl"))[-days:]:
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    evt = entry.get("event", "unknown")
                    events_by_type[evt] = events_by_type.get(evt, 0) + 1
                    total_events += 1
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "period_days": days,
        "total_events": total_events,
        "events_by_type": events_by_type,
    }


def get_error_summary(days: int = 7) -> dict:
    """获取最近 N 天的错误摘要。"""
    _ensure_log_dir()
    errors_by_type: dict[str, int] = {}
    total_errors = 0

    for log_file in sorted(_LOG_DIR.glob("error_events_*.jsonl"))[-days:]:
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    err = entry.get("error", "unknown")
                    errors_by_type[err] = errors_by_type.get(err, 0) + 1
                    total_errors += 1
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "period_days": days,
        "total_errors": total_errors,
        "errors_by_type": errors_by_type,
    }


def export_feedback_package(output_dir: Optional[Path] = None) -> Path:
    """导出匿名反馈包。

    生成结构：
        feedback_package/
        ├── usage_summary.json
        ├── error_summary.json
        ├── environment_diagnosis.json
        └── README.md
    """
    if output_dir is None:
        output_dir = Path("feedback_package")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Usage summary
    usage = get_usage_summary(days=30)
    (output_dir / "usage_summary.json").write_text(
        json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Error summary
    errors = get_error_summary(days=30)
    (output_dir / "error_summary.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Environment diagnosis
    try:
        from src.utils.environment_diagnosis import run_full_diagnosis
        diag = run_full_diagnosis()
        (output_dir / "environment_diagnosis.json").write_text(
            json.dumps(diag.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except ImportError:
        pass

    # README
    (output_dir / "README.md").write_text(
        "# 匿名反馈包\n\n"
        "本反馈包不包含任何原始数据、论文文本或个人可识别信息。\n"
        "仅包含匿名化的使用事件统计和环境诊断信息。\n\n"
        "如需提交反馈，可将此目录打包发送。\n",
        encoding="utf-8",
    )

    return output_dir


def clear_logs():
    """清除所有本地日志文件。"""
    _ensure_log_dir()
    for f in _LOG_DIR.glob("*.jsonl"):
        try:
            f.unlink()
        except OSError:
            pass
