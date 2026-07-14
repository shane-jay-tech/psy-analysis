"""最近数据集快照系统增强测试。

覆盖：
- 保存并恢复 DataFrame（内容一致）
- 内容哈希：同名同 shape 不同内容产生不同 ID
- 超过 5 条清理最旧
- 超过 10MB 不保存
- parquet 不可用时 fallback 到 csv
- clear_all 能清理索引和文件
- remove_one 删除单条
- legacy API 不崩溃
"""
import shutil
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.utils.recent_files import (
    _DATA_DIR,
    _dataset_id,
    add_recent,
    clear_all,
    get_entry,
    load_index,
    load_recent,
    remove_one,
    restore_dataset,
    save_dataset,
)


@pytest.fixture(autouse=True)
def _clean_data_dir(tmp_path):
    """每个测试用独立的数据目录。"""
    test_dir = tmp_path / "recent_datasets"
    test_dir.mkdir()
    with patch("src.utils.recent_files._DATA_DIR", test_dir), \
         patch("src.utils.recent_files._INDEX_FILE", test_dir / "index.json"):
        yield test_dir


def _make_df(rows=100, seed=42):
    np.random.seed(seed)
    return pd.DataFrame({
        "x": np.random.normal(0, 1, rows),
        "y": np.random.normal(5, 2, rows),
        "group": np.random.choice(["A", "B"], rows),
    })


class TestSaveAndRestore:
    def test_basic_save_restore(self):
        df = _make_df()
        ds_id = save_dataset(df, "test_data.csv")
        assert ds_id is not None

        restored = restore_dataset(ds_id)
        assert restored is not None
        pd.testing.assert_frame_equal(df, restored)

    def test_index_updated(self):
        df = _make_df()
        save_dataset(df, "my_file.csv")
        entries = load_index()
        assert len(entries) == 1
        assert entries[0]["display_name"] == "my_file.csv"
        assert entries[0]["shape"] == [100, 3]

    def test_restore_nonexistent_returns_none(self):
        assert restore_dataset("nonexistent_id") is None


class TestContentHash:
    def test_same_name_same_shape_different_content_different_id(self):
        """同名同 shape 但内容不同 → 不同 ID。"""
        df1 = _make_df(seed=1)
        df2 = _make_df(seed=2)
        assert df1.shape == df2.shape

        id1 = _dataset_id("data.csv", df1)
        id2 = _dataset_id("data.csv", df2)
        assert id1 != id2

    def test_same_content_same_id(self):
        """完全相同的数据 → 相同 ID。"""
        df1 = _make_df(seed=42)
        df2 = _make_df(seed=42)
        id1 = _dataset_id("data.csv", df1)
        id2 = _dataset_id("data.csv", df2)
        assert id1 == id2

    def test_different_name_different_id(self):
        """不同文件名 → 不同 ID。"""
        df = _make_df()
        id1 = _dataset_id("file_a.csv", df)
        id2 = _dataset_id("file_b.csv", df)
        assert id1 != id2


class TestCapacity:
    def test_max_5_entries(self):
        """超过 5 条自动清理最旧。"""
        for i in range(7):
            df = _make_df(seed=i)
            save_dataset(df, f"file_{i}.csv")

        entries = load_index()
        assert len(entries) == 5
        # 最新的应该在前面
        assert entries[0]["display_name"] == "file_6.csv"

    def test_oversized_rejected(self):
        """超过 10MB 不保存。"""
        big_df = pd.DataFrame({
            "x": np.random.normal(0, 1, 500_000),
            "y": np.random.normal(0, 1, 500_000),
            "z": ["long_string_" * 10] * 500_000,
        })
        ds_id = save_dataset(big_df, "huge.csv")
        assert ds_id is None


class TestFallback:
    def test_csv_fallback_when_parquet_fails(self):
        """parquet 写入失败时 fallback 到 csv。"""
        df = _make_df()
        with patch("pandas.DataFrame.to_parquet", side_effect=ImportError("no pyarrow")):
            ds_id = save_dataset(df, "fallback_test.csv")

        assert ds_id is not None
        entry = get_entry(ds_id)
        assert entry["snapshot_file"].endswith(".csv")

        restored = restore_dataset(ds_id)
        assert restored is not None
        assert restored.shape == df.shape


class TestCleanup:
    def test_clear_all(self):
        for i in range(3):
            save_dataset(_make_df(seed=i), f"file_{i}.csv")

        assert len(load_index()) == 3
        clear_all()
        assert len(load_index()) == 0

    def test_remove_one(self):
        df = _make_df()
        ds_id = save_dataset(df, "to_remove.csv")
        assert len(load_index()) == 1

        remove_one(ds_id)
        assert len(load_index()) == 0
        assert restore_dataset(ds_id) is None


class TestLegacyAPI:
    def test_load_recent_returns_list(self):
        save_dataset(_make_df(), "legacy.csv")
        result = load_recent()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_add_recent_does_not_crash(self):
        add_recent("test.csv", 100.0, ["col1", "col2"])
