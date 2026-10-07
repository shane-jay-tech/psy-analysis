# -*- coding: utf-8 -*-
"""s1004-14：数据面审计日志装配——幂等（二次装配 handler 不翻倍）＋落盘可读＋propagate 闸。"""
from __future__ import annotations

import logging

from src.utils.data_audit_logging import (
    _AUDIT_HANDLER_NAME,
    attach_data_audit_handler,
    attach_to_data_modules,
)


def _fresh_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    for h in list(logger.handlers):
        if getattr(h, "_audit_handler_name", None) == _AUDIT_HANDLER_NAME:
            logger.removeHandler(h)
    logger.setLevel(logging.DEBUG)
    return logger


def test_double_attach_is_idempotent(tmp_path):
    """二次装配幂等：handler 数不翻倍。"""
    lg = _fresh_logger("psy.test.audit_idem")
    first = attach_data_audit_handler(lg, "idem", base_dir=tmp_path)
    handlers_after_first = list(lg.handlers)
    second = attach_data_audit_handler(lg, "idem", base_dir=tmp_path)
    assert first is True
    assert second is False                      # 幂等跳过
    assert lg.handlers == handlers_after_first  # 不翻倍
    assert lg.propagate is False                # 材料纪律：审计行只落盘


def test_log_line_lands_readable(tmp_path):
    """日志行落盘可读：emit 后文件含格式化行。"""
    lg = _fresh_logger("psy.test.audit_write")
    attach_data_audit_handler(lg, "audit_write", base_dir=tmp_path)
    lg.info("审计写入测试行 12345")
    for h in lg.handlers:
        h.flush()
    log_file = tmp_path / "audit_write.log"
    content = log_file.read_text(encoding="utf-8")
    assert "审计写入测试行 12345" in content
    assert "psy.test.audit_write" in content
    # 恢复 propagate，防污染其他用例
    lg.propagate = True


def test_attach_to_data_modules_wires_four(tmp_path, monkeypatch):
    """材料案 2 清单：四数据面模块（workspace/autosave/project_manager/usage_logger）全部挂上。

    （s1007-23：usage_logger 自 s1002-33 收口后补装入清单。）
    """
    import importlib

    attached = attach_to_data_modules(base_dir=tmp_path)
    assert set(attached) == {"src.utils.workspace", "src.utils.autosave",
                             "src.utils.project_manager", "src.utils.usage_logger"}
    for mod_name, flag in attached.items():
        assert flag is True, mod_name
        lg = logging.getLogger(mod_name)
        audit_handlers = [h for h in lg.handlers
                          if getattr(h, "_audit_handler_name", None) == _AUDIT_HANDLER_NAME]
        assert len(audit_handlers) == 1
        assert lg.propagate is False
        # 还原：移除测试环境的审计 handler 与 propagate 翻转，防污染他用例
        logger = importlib.import_module(mod_name).logger
        for h in audit_handlers:
            logger.removeHandler(h)
        logger.propagate = True
