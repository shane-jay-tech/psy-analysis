"""最近数据集 — 保存 parquet 快照，支持一键恢复上次数据。

功能：
- 上传数据后自动保存快照（parquet 格式，高压缩比）
- 记录文件名、大小、列名、shape、上次分析方案
- 下次进入时可一键恢复数据集 + 变量选择
- 提供清除按钮（隐私保护）
- 最多保留 5 个快照，超出自动清理最旧的
"""
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "recent_datasets"
_INDEX_FILE = _DATA_DIR / "index.json"
_MAX_ENTRIES = 5
_MAX_SNAPSHOT_MB = 10


def _ensure_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _dataset_id(name: str, df: pd.DataFrame) -> str:
    """根据文件名+全量内容哈希+列信息生成稳定 ID。"""
    content_hash = pd.util.hash_pandas_object(df, index=True).values.tobytes()
    col_sig = "|".join(f"{c}:{df[c].dtype}" for c in df.columns)
    raw = (
        name.encode("utf-8")
        + content_hash
        + col_sig.encode("utf-8")
        + str(df.shape).encode("utf-8")
    )
    return hashlib.md5(raw).hexdigest()[:12]


def load_index() -> list[dict]:
    """加载最近数据集索引。"""
    try:
        if _INDEX_FILE.exists():
            data = json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[:_MAX_ENTRIES]
    except Exception:
        logger.debug("recent_datasets: index 读取失败", exc_info=True)
    return []


def _save_index(entries: list[dict]):
    _ensure_dir()
    try:
        _INDEX_FILE.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        logger.debug("recent_datasets: index 保存失败", exc_info=True)


def save_dataset(
    df: pd.DataFrame,
    display_name: str,
    last_plan: Optional[dict] = None,
) -> Optional[str]:
    """保存数据集快照。返回 dataset_id，失败返回 None。"""
    if df is None or df.empty:
        return None

    size_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    if size_mb > _MAX_SNAPSHOT_MB:
        logger.debug("recent_datasets: 数据集 %.1fMB 超过限制 %dMB，跳过", size_mb, _MAX_SNAPSHOT_MB)
        return None

    _ensure_dir()
    ds_id = _dataset_id(display_name, df)
    snapshot_path = _DATA_DIR / f"{ds_id}.parquet"

    try:
        df.to_parquet(snapshot_path, engine="pyarrow", compression="snappy")
    except Exception:
        try:
            csv_path = _DATA_DIR / f"{ds_id}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8")
            snapshot_path = csv_path
        except Exception:
            logger.debug("recent_datasets: 快照保存失败", exc_info=True)
            return None

    # Update index
    entries = load_index()
    entries = [e for e in entries if e.get("dataset_id") != ds_id]

    entry = {
        "dataset_id": ds_id,
        "display_name": display_name,
        "size_kb": round(size_mb * 1024, 1),
        "shape": list(df.shape),
        "columns": list(df.columns[:12]),
        "dtypes_summary": _dtypes_summary(df),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "snapshot_file": snapshot_path.name,
        "last_plan": last_plan,
    }
    entries.insert(0, entry)

    # Clean old entries
    while len(entries) > _MAX_ENTRIES:
        removed = entries.pop()
        _remove_snapshot(removed.get("snapshot_file"))

    _save_index(entries)
    return ds_id


def restore_dataset(dataset_id: str) -> Optional[pd.DataFrame]:
    """从快照恢复数据集。"""
    entries = load_index()
    entry = next((e for e in entries if e.get("dataset_id") == dataset_id), None)
    if entry is None:
        return None

    filename = entry.get("snapshot_file", "")
    path = _DATA_DIR / filename
    if not path.exists():
        return None

    try:
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        elif path.suffix == ".csv":
            return pd.read_csv(path, encoding="utf-8")
    except Exception:
        logger.debug("recent_datasets: 恢复失败 %s", filename, exc_info=True)
    return None


def get_entry(dataset_id: str) -> Optional[dict]:
    """获取某个数据集的索引条目。"""
    entries = load_index()
    return next((e for e in entries if e.get("dataset_id") == dataset_id), None)


def clear_all():
    """清除所有最近数据集快照（隐私保护）。"""
    entries = load_index()
    for e in entries:
        _remove_snapshot(e.get("snapshot_file"))
    _save_index([])


def remove_one(dataset_id: str):
    """删除单个数据集快照。"""
    entries = load_index()
    new_entries = []
    for e in entries:
        if e.get("dataset_id") == dataset_id:
            _remove_snapshot(e.get("snapshot_file"))
        else:
            new_entries.append(e)
    _save_index(new_entries)


def _remove_snapshot(filename: Optional[str]):
    if not filename:
        return
    path = _DATA_DIR / filename
    try:
        if path.exists():
            path.unlink()
    except Exception:
        logger.debug("recent_datasets: 快照文件删除失败 %s", filename, exc_info=True)


def _dtypes_summary(df: pd.DataFrame) -> dict:
    """统计各数据类型的列数。"""
    counts = df.dtypes.apply(lambda x: x.name).value_counts().to_dict()
    return {str(k): int(v) for k, v in counts.items()}


# Legacy compatibility — old API still works
def load_recent() -> list[dict]:
    """兼容旧接口：返回最近文件列表。"""
    return load_index()


def add_recent(name: str, size_kb: float, columns: list[str] | None = None):
    """兼容旧接口（仅记录元信息，不保存快照）。"""
    logger.debug("add_recent legacy API called without DataFrame; use save_dataset() instead")
