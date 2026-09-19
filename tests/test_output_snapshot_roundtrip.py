"""src/output/snapshot.py create→load 回环测试（s918-48）。

全程 `tmp_path`，不碰真实导出目录；不联网。
锚点：src/output/snapshot.py:34 create_snapshot、:240 _serialize_dict（254 行）。
"""
import io
import json
import zipfile

import pandas as pd
import pytest

from src.output.snapshot import SnapshotConfig, _serialize_dict, create_snapshot, load_snapshot

DF = pd.DataFrame({"分数": [1.5, 2.0, 3.0], "组别": ["a", "b", "c"]})
PARAMS = {"analyses": {"ttest": {"t": 2.34, "p": 0.03}}, "plan": {"dv": ["分数"]}}


@pytest.fixture
def out(tmp_path):
    return tmp_path / "nested" / "snap.zip"


def test_roundtrip_restores_the_dataframe_exactly(out):
    create_snapshot(DF, PARAMS, report_text="# 报告", output_path=str(out),
                    config=SnapshotConfig(title="T", author="A"))

    loaded = load_snapshot(out)

    pd.testing.assert_frame_equal(loaded["data"], DF)
    assert list(loaded["data"].columns) == ["分数", "组别"]     # utf-8-sig BOM 两侧对齐，不残留 \ufeff


def test_params_roundtrip_carries_title_counts_and_columns(out):
    create_snapshot(DF, PARAMS, output_path=str(out),
                    config=SnapshotConfig(title="论文快照", author="张三", description="说明"))

    params = load_snapshot(out)["params"]

    assert params["title"] == "论文快照" and params["author"] == "张三"
    assert params["description"] == "说明"
    assert params["n_rows"] == 3 and params["n_cols"] == 2
    assert params["columns"] == ["分数", "组别"]
    assert "snapshot_created" in params


def test_zip_members_are_the_documented_four_names(out):
    create_snapshot(DF, PARAMS, report_text="# 报告", output_path=str(out))

    with zipfile.ZipFile(out) as zf:
        assert sorted(zf.namelist()) == ["README.txt", "analysis_params.json", "data.csv", "report.md"]


def test_returned_bytes_equal_the_file_written_in_the_same_call(out):
    """改写说明（s919-21 收口时修，本仓内我此前埋的用例）：

    前一版调了 **两次** `create_snapshot`（一次取返回 bytes、一次写文件）再比字节，
    全量跑里间歇性翻红。真因不是 zip 头，而是 `analysis_params.json` 里嵌了
    `snapshot_created`（微秒精度 ISO 时间，实测两次调用只差这一个键），
    即"两次调用的内容本来就不同"，拿它当"同一份内容"是错的断言前提。

    于是按语义拆成两条真不变量：
    ① 同一次调用：返回的 bytes 与落盘文件逐字节相同（实测成立）；
    ② 跨次调用：唯一差异必然落在 `snapshot_created` 上，其余成员逐字节相同。
    """
    blob = create_snapshot(DF, PARAMS, report_text="x", output_path=str(out))

    assert isinstance(blob, bytes)
    assert out.parent.exists()                               # 父目录 nested/ 被自动创建
    assert out.read_bytes() == blob                          # ① 同一次调用：返回值==落盘字节

    def members(src):
        with zipfile.ZipFile(src) as zf:
            return {n: zf.read(n) for n in sorted(zf.namelist())}

    other = create_snapshot(DF, PARAMS, report_text="x")
    m1, m2 = members(io.BytesIO(blob)), members(io.BytesIO(other))
    assert m1.keys() == m2.keys()
    assert {k for k in m1 if m1[k] != m2[k]} == {"analysis_params.json"}   # ② 只有 params 变
    p1, p2 = json.loads(m1["analysis_params.json"]), json.loads(m2["analysis_params.json"])
    assert {k for k in p1 if p1[k] != p2.get(k)} == {"snapshot_created"}   # 且只因这个时间戳键
    assert p1["snapshot_created"] != p2["snapshot_created"]


def test_serialize_dict_truncates_at_depth_greater_than_three():
    """任务书写「深度>2 截断」，实现是 `if depth > 3: return "..."`——按磁盘边界钉。"""
    deep = {"l1": {"l2": {"l3": {"l4": {"l5": "x"}}}}}

    got = _serialize_dict(deep)

    assert got["l1"]["l2"]["l3"] == {"l4": "..."}        # l4 那一层被折成字符串
    assert isinstance(got["l1"]["l2"]["l3"]["l4"], str)


def test_serialize_dict_flattens_values_lists_and_long_strings():
    got = _serialize_dict({
        "num": 3.14159,
        "objs": {"a": 1},
        "many": list(range(50)),
        "long": "x" * 500,
    })

    assert got["num"] == "3.14159"                       # 全部字符串化
    assert got["objs"] == {"a": "1"}
    assert got["many"] == ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]   # 只留前 10 项
    assert len(got["long"]) == 200                        # 单值截到 200 字


def test_optional_members_simply_absent_from_the_loaded_dict(out):
    """关掉的成员不是写空，而是**整个键不存在** ⇒ 下游 `snap["report"]` 会 KeyError。"""
    create_snapshot(DF, PARAMS, report_text="", output_path=str(out),
                    config=SnapshotConfig(include_report=False, include_raw_data=False))

    loaded = load_snapshot(out)

    assert "report" not in loaded and "data" not in loaded
    assert "params" in loaded and "readme" in loaded


def test_empty_dataframe_produces_no_data_member(out):
    create_snapshot(pd.DataFrame(), PARAMS, output_path=str(out))

    assert "data" not in load_snapshot(out)


@pytest.mark.parametrize("compress", [True, False])
def test_store_and_deflate_both_roundtrip(out, compress):
    create_snapshot(DF, PARAMS, report_text="# r", output_path=str(out),
                    config=SnapshotConfig(compress=compress))

    loaded = load_snapshot(out)

    pd.testing.assert_frame_equal(loaded["data"], DF)
    assert loaded["params"]["n_rows"] == 3
