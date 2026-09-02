"""上传文件身份与数据状态提交工具。"""

from __future__ import annotations

import hashlib
from collections.abc import MutableMapping
from typing import Any


def uploaded_file_identity(uploaded_file: Any) -> tuple[str, int, str]:
    """返回能区分同名替换文件的稳定身份；优先使用 Streamlit file_id。"""
    name = str(getattr(uploaded_file, "name", ""))
    size = getattr(uploaded_file, "size", None)
    file_id = getattr(uploaded_file, "file_id", None)
    if size is None:
        size = len(uploaded_file.getbuffer())
    if file_id is None:
        file_id = hashlib.sha256(bytes(uploaded_file.getbuffer())).hexdigest()
    return name, int(size), str(file_id)


def commit_loaded_dataset(
    session_state: MutableMapping,
    *,
    dataframe: Any,
    meta: Any,
    inspector: Any,
    file_name: str,
    identity: tuple[str, int, str],
) -> None:
    """仅在解析与检查全部成功后一次性替换主数据状态。"""
    session_state["df"] = dataframe
    session_state["meta"] = meta
    session_state["inspector"] = inspector
    session_state["file_name"] = file_name
    session_state["_uploaded_file_identity"] = identity
    session_state.pop("_upload_error", None)
    session_state["analysis_output"] = None
    session_state["plan"] = None

