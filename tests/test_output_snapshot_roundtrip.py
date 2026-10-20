"""src/output/snapshot.py create→load 回环测试（s918-48）。

全程 `tmp_path`，不碰真实导出目录；不联网。
锚点：src/output/snapshot.py:34 create_snapshot、:240 _serialize_dict（254 行）。
"""
import io
import json
import zipfile
from datetime import datetime

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
    # ⚠️ 防回归（s923-21）：下面这两条断言的前提是"两次调用的 `snapshot_created` 必然不同"，
    # 而这个前提**不能**靠 `datetime.now()` 撑——本机墙钟（GetSystemTimeAsFileTime）实际
    # 粒度受系统定时器插值影响并非固定槽宽（`time.get_clock_info('time')`），连续调用
    # 同值率实测 99.945%~99.998%（s924-28 §〇.4/s927-64 两轮口径），
    # 80 组相邻 `create_snapshot` 里有 66 组时间戳完全相同 ⇒ 断言当场红（不是回归，是时钟）。
    # 现由 `src/output/snapshot.py` 的 `+mono<perf_counter_ns()>` 尾数提供区分度（同值率实测 0.000%）。
    # ⇒ 谁把那个尾数摘掉／换成 `time.time_ns()`（同源粗时钟，同样 99.998% 同值），本用例立刻红。
    assert {k for k in m1 if m1[k] != m2[k]} == {"analysis_params.json"}   # ② 只有 params 变
    p1, p2 = json.loads(m1["analysis_params.json"]), json.loads(m2["analysis_params.json"])
    assert {k for k in p1 if p1[k] != p2.get(k)} == {"snapshot_created"}   # 且只因这个时间戳键
    assert p1["snapshot_created"] != p2["snapshot_created"]
    # 尾数只能是附加量：墙钟部分必须仍是可解析的 ISO 串（防有人把整键换成裸计数器）
    assert datetime.fromisoformat(p1["snapshot_created"].split("+mono")[0]).year >= 2024
    assert p1["snapshot_created"].partition("+mono")[2].isdigit() and \
        p2["snapshot_created"].partition("+mono")[2].isdigit()


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


def test_snapshot_created_lexicographic_order_does_not_imply_chronology(
    out, tmp_path, monkeypatch,
):
    """反向钉（s930-13，s927-64 案丙）：`snapshot_created` 的**字典序不保证＝时间序**——
    尾数长度变化可让「后写的值」字典序反而更小，消费方不得用 str 比较判先后，
    时序判据必须走 ISO 部分的 fromisoformat。全部用确定性 monkeypatch 构造，零真实墙钟依赖。

    构造：两次调用**同一墙钟刻**（真实现同值形态——这正是尾数存在的理由）、
    尾数 t1=9 位 900000000、t2=10 位 1000000000——字典序 "+mono1000000000" <
    "+mono900000000"（'1'<'9'）＝后写的反而更小，即字典序与写入序脱钩。
    """
    from datetime import datetime as _dt

    import src.output.snapshot as snap_mod

    df = DF
    same_tick = _dt(2026, 10, 2, 7, 0, 0)
    times = [same_tick, same_tick]          # 同刻：墙钟同值（尾数存在的理由）
    monos = [900_000_000, 1_000_000_000]    # 尾数位数不同 ⇒ 字典序逆序
    calls = {"n": 0}

    class _FrozenDT(_dt):
        @classmethod
        def now(cls, tz=None):
            i = min(calls["n"], 1)
            return times[i]

    monkeypatch.setattr(snap_mod, "datetime", _FrozenDT)
    monkeypatch.setattr(snap_mod.time, "perf_counter_ns", lambda: monos[min(calls["n"], 1)])
    real_ns = snap_mod.time.time_ns
    monkeypatch.setattr(snap_mod.time, "time_ns", lambda: monos[min(calls["n"], 1)] * 1000)

    b1 = snap_mod.create_snapshot(df.copy(), PARAMS, output_path=str(out))
    calls["n"] = 1
    out2 = out.with_name("snap2.zip")
    b2 = snap_mod.create_snapshot(df.copy(), PARAMS, output_path=str(out2))

    import json
    import zipfile

    def _created(blob):
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            return json.loads(zf.read("analysis_params.json"))["snapshot_created"]

    c1, c2 = _created(b1), _created(b2)
    # 字典序逆序：同刻之下尾数位数让后写的 c2 反而「更小」
    assert c2 < c1, f"构造失效（应字典序逆序）：{c1} vs {c2}"
    # 时序判据必须走 fromisoformat：ISO 部分相等（同刻）⇒ 两值代表同一时刻，
    # str 比较（c2 < c1）会给出「c1 在后」的**错误**结论——这正是本钉要防的依赖。
    assert _dt.fromisoformat(c1.split("+mono")[0]) == _dt.fromisoformat(c2.split("+mono")[0])
    # 尾数仍为纯数字（既有不变量保持）
    assert c1.partition("+mono")[2].isdigit() and c2.partition("+mono")[2].isdigit()
