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
import logging
import os
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any

from src.utils.app_paths import LOG_DIR

logger = logging.getLogger(__name__)

# 静默吞错的观测接线（s924-66）。**铁律：这些日志行里只允许出现路径、计数、
# 异常类型与一行摘要**——绝不含待写内容、prompt/响应片段或任何用户文本
# （本模块记的是用量事件，正文里可能有页面名/量表名，顺手带进日志就是泄露）。
_ALERT_PREFIX = "[usage-log-alert]"      # 与 `_alert_once` 同一命名空间，运维侧一条 grep 收齐
_EXC_SUMMARY_MAX = 160


def _exc_summary(exc: BaseException) -> str:
    """把异常压成「类型: 单行摘要」并截断——折叠换行，绝不让整段待写内容进日志。"""
    return f"{type(exc).__name__}: {' '.join(str(exc).split())[:_EXC_SUMMARY_MAX]}"


# 显式覆盖点（测试/嵌入部署用）；为 None 时**调用期**解析，不再吃 import 期的旧绑定。
_LOG_DIR: Optional[Path] = None
_ENABLED = True
_ALERTED: set[str] = set()


def _log_dir() -> Path:
    """解析日志目录：显式打桩 > 环境变量 `PSY_ANALYSIS_LOG_DIR` > `app_paths.LOG_DIR`。

    早先是模块顶部 `_LOG_DIR = LOG_DIR` 一次性绑定——`.env`/测试在 import 之后才设环境变量就不认了，
    而 `LOG_DIR` 的**默认值本身没动**（仍是 `app_paths` 里那个 `Path("logs")`）。
    """
    if _LOG_DIR is not None:
        return Path(_LOG_DIR)
    value = os.environ.get("PSY_ANALYSIS_LOG_DIR", "").strip()
    return Path(value).expanduser() if value else LOG_DIR


def _alert_once(kind: str, message: str) -> None:
    """同一 kind 只报一次：日志目录坏了会被每次埋点撞上，全报会把控制台刷死。"""
    if kind in _ALERTED:
        return
    _ALERTED.add(kind)
    logging.warning("[usage-log-alert] %s %s", kind, message)


def _warn_once(kind: str, message: str) -> None:
    """`_alert_once` 的同纪律版本，但走**模块 logger**（`logger.warning`）。

    写侧失败会被每个埋点撞上，所以同样按 kind 去重；kind 里带文件名，日志按天轮转 ⇒ 新的一天
    会重新吱一声，不会永久哑掉。
    """
    if kind in _ALERTED:
        return
    _ALERTED.add(kind)
    logger.warning("%s %s %s", _ALERT_PREFIX, kind, message)


def _ensure_log_dir():
    """确保日志目录存在。建不出来照旧抛 `OSError`，但先吱一声。

    告警文案里**不再二次调用** `_log_dir()`：解析本身也可能失败，在 except 里再抛一个异常
    会让告警一条都发不出去（写这版时正是被自己的用例抓到）。
    """
    target = None
    try:
        target = _log_dir()
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _alert_once("mkdir_failed", f"日志目录不可用 dir={target if target is not None else '未解析'}：{exc!r}")
        raise


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
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event_type,
        **kwargs,
    }

    log_file = _log_dir() / f"usage_events_{date.today().strftime('%Y%m%d')}.jsonl"
    try:
        _ensure_log_dir()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        # 原先是裸 pass：写侧失败完全无痕，线上用量丢了没人知道（签名与返回值不变，纯加观测）。
        _warn_once(f"write_failed:{log_file.name}",
                   f"写入用量日志失败 file={log_file} {_exc_summary(exc)}")


def log_error(error_type: str, **kwargs):
    """记录一个错误事件。

    Args:
        error_type: 错误类型标识
        **kwargs: 错误附加字段（不记录原始错误文本中的敏感内容）
    """
    if not _ENABLED:
        return
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error_type,
        **kwargs,
    }

    log_file = _log_dir() / f"error_events_{date.today().strftime('%Y%m%d')}.jsonl"
    try:
        _ensure_log_dir()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        # 同上：`log_error` 的写侧原先也是裸 pass（卷宗把这处误记成"读侧同型"，实测它是写侧）。
        _warn_once(f"write_failed:{log_file.name}",
                   f"写入错误日志失败 file={log_file} {_exc_summary(exc)}")


def get_usage_summary(days: int = 7) -> dict:
    """获取最近 N 天的使用摘要。目录建不出来只给空摘要——读侧不许把界面带崩。"""
    events_by_type: dict[str, int] = {}
    total_events = 0

    try:
        _ensure_log_dir()
        files = sorted(_log_dir().glob("usage_events_*.jsonl"))[-days:]
    except OSError:
        files = []

    for log_file in files:
        seen_lines = counted = 0
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                seen_lines += 1
                if line.strip():
                    entry = json.loads(line)
                    evt = entry.get("event", "unknown")
                    events_by_type[evt] = events_by_type.get(evt, 0) + 1
                    total_events += 1
                    counted += 1
        except (OSError, json.JSONDecodeError) as exc:
            # 读侧按**文件**汇总一条 warning（不逐行刷屏）：坏行数量原本完全不可知。
            # 只报路径＋计数＋异常摘要，绝不回贴行内容——行里是事件字段，带进日志就是泄露。
            logger.warning("%s read_degraded file=%s 读到=%d行 已计=%d条 %s",
                           _ALERT_PREFIX, log_file, seen_lines, counted, _exc_summary(exc))

    return {
        "period_days": days,
        "total_events": total_events,
        "events_by_type": events_by_type,
    }


def get_error_summary(days: int = 7) -> dict:
    """获取最近 N 天的错误摘要。同 `get_usage_summary`：读侧不抛。"""
    errors_by_type: dict[str, int] = {}
    total_errors = 0

    try:
        _ensure_log_dir()
        files = sorted(_log_dir().glob("error_events_*.jsonl"))[-days:]
    except OSError:
        files = []

    for log_file in files:
        seen_lines = counted = 0
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                seen_lines += 1
                if line.strip():
                    entry = json.loads(line)
                    err = entry.get("error", "unknown")
                    errors_by_type[err] = errors_by_type.get(err, 0) + 1
                    total_errors += 1
                    counted += 1
        except (OSError, json.JSONDecodeError) as exc:
            # 与 `get_usage_summary` 同型（卷宗未列这处，实测它是第 4 个静默吞错点）。
            logger.warning("%s read_degraded file=%s 读到=%d行 已计=%d条 %s",
                           _ALERT_PREFIX, log_file, seen_lines, counted, _exc_summary(exc))

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
    """清除所有本地日志文件。目录不可用时视为"没有可清的"，不抛。"""
    try:
        _ensure_log_dir()
        files = list(_log_dir().glob("*.jsonl"))
    except OSError:
        return

    for f in files:
        try:
            f.unlink()
        except OSError as exc:
            # 删不掉的日志文件要留痕（"清除"静默失败＝用户以为已清、实际还在盘上，属隐私面可观测性）。
            _warn_once(f"clear_failed:{f.name}", f"清除日志失败 file={f} {_exc_summary(exc)}")
