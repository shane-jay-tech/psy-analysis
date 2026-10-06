# -*- coding: utf-8 -*-
"""数据面审计日志装配 helper（s1004-14，s930-26 普查档案 2 落地）。

给「用户数据写入面」的数据面模块 logger 挂**命名空间级 FileHandler**（审计落盘），
三条防泄漏纪律：
  1. **去重检查**：按 handler 名字（`_audit_handler_name`）判重，重复装配直接跳过
     （reload/多次 import 场景 handler 不翻倍）；
  2. **propagate=False**：审计行只落盘、不向 root 传播（避免与 Streamlit 控制台
     handler 双写）——副作用是该命名空间的既有 debug/warning 不再上控制台，
     属材料明示的行为变更；
  3. **落盘目录**复用 usage_logger 的 `_log_dir()` 解析链（显式打桩 > 环境变量 >
     app_paths.LOG_DIR），与既有审计文件同域。

不触 usage_logger 的告警面（_alert_once/_warn_once，s1002-33 另案）。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

_AUDIT_HANDLER_NAME = "psy_data_audit_filehandler"
_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def _resolve_log_dir() -> Path:
    """与 usage_logger._log_dir 同链解析（显式打桩 > 环境变量 > app_paths.LOG_DIR）。"""
    try:
        from src.utils.usage_logger import _log_dir

        return _log_dir()
    except Exception:
        return Path("logs")


def attach_data_audit_handler(logger: logging.Logger, log_name: str,
                              base_dir: Optional[Path] = None) -> bool:
    """给 logger 挂命名空间级 FileHandler（幂等）。

    返回 True＝本次新挂；False＝已有同名 handler（幂等跳过）。
    base_dir 仅供测试注入（生产走 _resolve_log_dir）。
    """
    for h in logger.handlers:
        if getattr(h, "_audit_handler_name", None) == _AUDIT_HANDLER_NAME:
            return False
    log_dir = Path(base_dir) if base_dir else _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / f"{log_name}.log", encoding="utf-8")
    handler.set_name(_AUDIT_HANDLER_NAME)
    handler._audit_handler_name = _AUDIT_HANDLER_NAME
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False   # 材料纪律：审计行只落盘（防 root/控制台双写）
    return True


def attach_to_data_modules(base_dir: Optional[Path] = None) -> dict:
    """材料案 2 清单装配：workspace / autosave / project_manager 三数据面模块。

    （usage_logger 在材料清单内，但其告警面属 s1002-33 另案——本装配跳过，
    待另案收口后再补装。）
    """
    import importlib

    attached = {}
    for mod_name, log_name in (("src.utils.workspace", "workspace_audit"),
                               ("src.utils.autosave", "autosave_audit"),
                               ("src.utils.project_manager", "project_manager_audit")):
        mod = importlib.import_module(mod_name)
        logger = logging.getLogger(mod_name)
        attached[mod_name] = attach_data_audit_handler(logger, log_name, base_dir)
    return attached
