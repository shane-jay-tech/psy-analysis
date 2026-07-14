"""个人研究档案系统

自动归档每次完整分析到 ./archive/ 目录，支持：
- 原始数据 CSV（姓名列自动哈希脱敏）
- 分析快照（复用 SHA256 机制）
- APA7 报告文本（Markdown）
- 参数配置（JSON）
- 时间戳 + 课程标签

历史检索面板：按时间倒序列出，点击可加载复现。
"""

import json
import os
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


ARCHIVE_ROOT = Path(__file__).resolve().parent.parent.parent / "archive"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_tag(tag: str) -> str:
    """清理标签为安全目录名"""
    safe = "".join(c for c in tag if c.isalnum() or c in "._-（）()")
    safe = safe[:50].strip(".")
    return safe or "未分类"


def archive_analysis(
    df: pd.DataFrame,
    analysis_output: Dict,
    report_md: str,
    params: Dict,
    tag: str = "",
    file_name: str = "",
) -> Dict:
    """
    保存一次完整分析到档案目录。

    返回: {"archive_id": ..., "path": ...}
    """
    now = datetime.now()
    archive_id = hashlib.sha256(
        f"{now.isoformat()}_{tag}".encode("utf-8")
    ).hexdigest()[:16]
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    # 子目录：标签/时间戳_archive_id
    if tag:
        subdir = _ensure_dir(ARCHIVE_ROOT / _sanitize_tag(tag) / f"{timestamp}_{archive_id}")
    else:
        subdir = _ensure_dir(ARCHIVE_ROOT / f"{timestamp}_{archive_id}")

    # 1. 原始数据（脱敏）
    df_saved = df.copy()
    from src.utils.guardrails import detect_name_columns, hash_column
    name_cols = detect_name_columns(df_saved)
    for col in name_cols:
        df_saved[col] = hash_column(df_saved, col)
    df_saved.to_csv(subdir / "data.csv", index=False, encoding="utf-8-sig")

    # 2. 参数配置
    param_record = {
        "archive_id": archive_id,
        "timestamp": now.isoformat(),
        "tag": tag,
        "file_name": file_name,
        "test_type": analysis_output.get("test_type", ""),
        "test_name_zh": analysis_output.get("test_name_zh", ""),
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "columns": list(df.columns),
        "params": params,
    }
    with open(subdir / "params.json", "w", encoding="utf-8") as f:
        json.dump(param_record, f, ensure_ascii=False, indent=2, default=str)

    # 3. APA7 报告
    if report_md:
        with open(subdir / "report.md", "w", encoding="utf-8") as f:
            f.write(report_md)

    # 4. 索引条目
    _update_index(archive_id, param_record)

    return {
        "archive_id": archive_id,
        "path": str(subdir),
        "timestamp": timestamp,
    }


def _update_index(archive_id: str, record: Dict):
    """更新档案索引文件"""
    index_path = ARCHIVE_ROOT / "index.json"
    entries = []
    if index_path.exists():
        try:
            entries = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []

    # 去重
    entries = [e for e in entries if e.get("archive_id") != archive_id]

    entries.append({
        "archive_id": record["archive_id"],
        "timestamp": record["timestamp"],
        "tag": record.get("tag", ""),
        "test_type": record.get("test_type", ""),
        "test_name_zh": record.get("test_name_zh", ""),
        "file_name": record.get("file_name", ""),
        "n_rows": record.get("n_rows", 0),
        "n_cols": record.get("n_cols", 0),
    })

    # 按时间倒序，保留最近200条
    entries.sort(key=lambda x: x["timestamp"], reverse=True)
    entries = entries[:200]

    _ensure_dir(ARCHIVE_ROOT)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def list_archives(tag: str = "") -> List[Dict]:
    """列出所有档案，按时间倒序。可按标签过滤。"""
    index_path = ARCHIVE_ROOT / "index.json"
    if not index_path.exists():
        return []

    try:
        entries = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if tag:
        entries = [e for e in entries if e.get("tag") == tag]

    return entries


def list_tags() -> List[str]:
    """列出所有标签"""
    entries = list_archives()
    tags = set(e.get("tag", "") for e in entries if e.get("tag"))
    return sorted(tags)


def load_archive(archive_id: str) -> Optional[Dict]:
    """加载指定档案的全部内容"""
    # 查找档案路径
    candidates = list(ARCHIVE_ROOT.rglob(f"*_{archive_id}"))
    if not candidates:
        return None

    archive_dir = candidates[0]

    result = {"archive_id": archive_id}

    # 加载数据
    data_path = archive_dir / "data.csv"
    if data_path.exists():
        result["df"] = pd.read_csv(data_path, encoding="utf-8-sig")

    # 加载参数
    params_path = archive_dir / "params.json"
    if params_path.exists():
        with open(params_path, "r", encoding="utf-8") as f:
            result["params"] = json.load(f)

    # 加载报告
    report_path = archive_dir / "report.md"
    if report_path.exists():
        result["report"] = report_path.read_text(encoding="utf-8")

    return result


def get_archive_count() -> int:
    """获取档案总数"""
    return len(list_archives())


def get_tag_counts() -> Dict[str, int]:
    """获取各标签的档案数量"""
    entries = list_archives()
    counts = {}
    for e in entries:
        tag = e.get("tag", "未分类")
        counts[tag] = counts.get(tag, 0) + 1
    return counts
