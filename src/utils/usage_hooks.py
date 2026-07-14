"""v5.4: UI 主路径使用事件接入层。

将 usage_logger 接入 app.py 的关键路径，记录 ≥12 类匿名化事件。
所有事件仅记录结构化元数据，不记录原始数据、论文正文或敏感信息。
"""
import time
from typing import Optional

from src.utils.usage_logger import log_event, log_error


def on_page_visit(page_id: str):
    """记录页面访问事件。"""
    log_event("page_visit", page_id=page_id)


def on_template_select(template_id: str):
    """记录模板选择事件。"""
    log_event("template_select", template_id=template_id)


def on_next_step_show(step_id: str, priority: int):
    """记录下一步推荐展示事件。"""
    log_event("next_step_show", step_id=step_id, priority=priority)


def on_next_step_click(step_id: str, target: str):
    """记录下一步推荐点击事件。"""
    log_event("next_step_click", step_id=step_id, target=target)


def on_data_upload(row_count: int, column_count: int, file_type: str):
    """记录数据上传事件（不记录原始数据）。"""
    log_event("data_upload", row_count=row_count, column_count=column_count, file_type=file_type)


def on_method_recommend(recommended_method: str, template_id: Optional[str] = None):
    """记录方法推荐事件。"""
    log_event("method_recommend", recommended_method=recommended_method, template_id=template_id)


def on_analysis_execute(method_id: str, success: bool, duration_ms: int):
    """记录分析执行事件。"""
    log_event("analysis_execute", method_id=method_id, success=success, duration_ms=duration_ms)


def on_table_generate(table_type: str, success: bool):
    """记录表格生成事件。"""
    log_event("table_generate", table_type=table_type, success=success)


def on_consistency_check(error_count: int, warning_count: int):
    """记录一致性检查事件。"""
    log_event("consistency_check", errors=error_count, warnings=warning_count)


def on_privacy_precheck(high_count: int, medium_count: int, safe: bool):
    """记录隐私预检事件（不记录原始匹配文本）。"""
    log_event("privacy_precheck", high_count=high_count, medium_count=medium_count, safe=safe)


def on_export(format: str, success: bool, duration_ms: int):
    """记录导出事件。"""
    log_event("export", format=format, success=success, duration_ms=duration_ms)


def on_error_display(error_type: str, severity: str):
    """记录错误提示显示事件。"""
    log_error(error_type, severity=severity)


def on_diagnosis_run(ok_count: int, warning_count: int, error_count: int):
    """记录环境诊断运行事件。"""
    log_event("diagnosis_run", ok=ok_count, warnings=warning_count, errors=error_count)


class AnalysisTimer:
    """分析执行计时上下文管理器。"""

    def __init__(self, method_id: str):
        self.method_id = method_id
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self._start) * 1000)
        success = exc_type is None
        on_analysis_execute(self.method_id, success, duration_ms)
        return False
