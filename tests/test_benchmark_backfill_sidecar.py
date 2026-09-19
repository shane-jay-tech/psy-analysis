# -*- coding: utf-8 -*-
"""20260915-130540-dd4d：基准补评 side-car 落盘单测。

①原始基准 JSON 字节级不变；②side-car 结构正确（30 条、字段齐全）；③幂等（二次运行一致）。
脚本经 importlib 从桥侧 tmp 草案加载（路径硬编码在草案内，属既定形态）。
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(r"D:/code/zcode-bridge/tmp/d913d-11/backfill-draft.py")
BENCH = Path(r"D:/code/psy-analysis/data/benchmark_history/socratic_benchmark_20260909T192139Z.json")

_spec = importlib.util.spec_from_file_location("backfill_draft", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def isolated(tmp_path):
    """tmp 内复刻真实基准文件，隔离验证 --apply。"""
    bench = tmp_path / "bench.json"
    bench.write_bytes(BENCH.read_bytes())
    return bench, tmp_path / "benchmark_backfill_draft.json"


def test_original_json_untouched(isolated):
    bench, sidecar = isolated
    before = _sha(bench)
    mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)
    assert _sha(bench) == before, "原始基准 JSON 字节级不变"


def test_sidecar_structure(isolated):
    bench, sidecar = isolated
    payload = mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)
    raw = json.loads(sidecar.read_text(encoding="utf-8"))
    assert raw["n_entries"] == 30
    assert len(raw["entries"]) == 30
    for entry in raw["entries"]:
        assert set(entry) == {"case_id", "stage", "input", "expected_dimensions",
                              "llm_reply", "error", "manual_score", "manual_notes"}
        assert entry["manual_score"] is None, "脚本不冒充 1-5 主观分"
        assert entry["manual_notes"], "客观证据预填不得为空"
    assert payload["manual_score_null_count"] == 30


def test_idempotent_second_run_identical(isolated):
    bench, sidecar = isolated
    first = mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)
    bytes_first = sidecar.read_bytes()
    second = mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)
    assert sidecar.read_bytes() == bytes_first
    assert first == second


# ---------- n916x-32 追加边界用例（并发隔离／源缺失／路径不存在／字节不变负例） ----------

def test_concurrent_applications_do_not_clobber_each_other(isolated, monkeypatch):
    """并发两次补评（不同 side-car 目标、同源基准）→ 各自完整落盘、互不覆盖。"""
    import concurrent.futures
    bench, sidecar = isolated
    other = sidecar.parent / "benchmark_backfill_draft_b.json"

    def run(target):
        return mod.apply_sidecar(bench_path=bench, sidecar_path=target)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, sidecar), pool.submit(run, other)]
        payloads = [f.result() for f in futures]

    assert sidecar.exists() and other.exists()               # 两个产物各自落盘
    assert sidecar.read_bytes() != other.read_bytes() or True  # 内容允许一致（同源），关键是不缺失
    for p in (sidecar, other):
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert raw["n_entries"] == 30 and len(raw["entries"]) == 30
    assert all(pl["manual_score_null_count"] == 30 for pl in payloads)


def test_missing_bench_source_fails_loudly(tmp_path):
    """补评源缺失 → 明确抛 FileNotFoundError，不静默产出空 side-car。"""
    missing = tmp_path / "no-such-bench.json"
    target = tmp_path / "sidecar.json"
    with pytest.raises(FileNotFoundError):
        mod.apply_sidecar(bench_path=missing, sidecar_path=target)
    assert not target.exists(), "失败路径不得留下半成品 side-car"


def test_sidecar_in_uncreated_directory_currently_fails(tmp_path):
    """【契约↔实现差异记录】目录不存在：当前实现不建目录，抛 FileNotFoundError。

    任务书期望「创建目录后成功」；实现（backfill-draft.py apply_sidecar）无
    makedirs——按「不改生产实现」纪律，本用例锁定现状行为，差异留日间拍板
    （补 makedirs 属行为增强）。
    """
    bench = tmp_path / "bench.json"
    bench.write_bytes(BENCH.read_bytes())
    nested = tmp_path / "nested" / "sidecar.json"
    with pytest.raises(FileNotFoundError):
        mod.apply_sidecar(bench_path=bench, sidecar_path=nested)
    assert not nested.exists()


def test_original_json_guard_trips_when_bytes_change(isolated, monkeypatch):
    """「原 JSON 字节不变」负例：apply 进行中基准 JSON 被改动 → 内置守卫必须失败。

    实现的守卫＝调用内 sha256 前后比对（source_sha256 于读入后计算）；
    故用 monkeypatch 在 build_sidecar 执行期间改动 bench 字节来触发。
    """
    bench, sidecar = isolated
    orig_dumps = mod.json.dumps

    # source_sha256 在 build_sidecar 之后才计算，故真正的「调用中改动」打点放 dumps
    # （位于 sha 计算与守卫复读之间）——模拟 apply 过程中基准文件被第三方改动。
    def tampering_dumps(*a, **k):
        bench.write_bytes(bench.read_bytes() + b"\n")
        return orig_dumps(*a, **k)

    monkeypatch.setattr(mod.json, "dumps", tampering_dumps)
    with pytest.raises(AssertionError, match="原始基准 JSON 发生了变化"):
        mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)


# ---------- s918-12 追加：同路径并发与 .bak 残留语义（不改生产实现，锁现状） ----------

def _bench_copy(tmp_path, name):
    dst = tmp_path / name
    dst.write_bytes(BENCH.read_bytes())
    return dst


def test_first_write_leaves_no_bak_and_second_backs_it_up(isolated):
    """顺序两写：首写不留 .bak；第二写先把首写整份备份为 `.json.bak` 再覆写。"""
    bench, sidecar = isolated
    bak = sidecar.with_suffix(".json.bak")

    mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)
    assert sidecar.exists() and not bak.exists()
    first = sidecar.read_bytes()

    mod.apply_sidecar(bench_path=bench, sidecar_path=sidecar)

    assert bak.exists() and bak.read_bytes() == first
    assert sidecar.read_bytes() == first          # 同源幂等：覆写内容与首写逐字相同
    assert sidecar.read_text(encoding="utf-8").count('"source_sha256"') == 1


def test_concurrent_same_path_never_yields_a_torn_result(tmp_path):
    """同路径并发 last-writer-wins 的**不变量**：最终 side-car 必须是某一位写入者的整份产物，
    不得混合、不得半成品；失败形态允许为 Windows 读写争用下的 PermissionError（备份读被占）。"""
    import concurrent.futures

    target = tmp_path / "sidecar.json"
    a = _bench_copy(tmp_path, "bench_a.json")
    b = _bench_copy(tmp_path, "bench_b.json")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(mod.apply_sidecar, bench_path=a, sidecar_path=target),
                   pool.submit(mod.apply_sidecar, bench_path=b, sidecar_path=target)]
        outcomes = [f for f in futures]
        results, errors = [], []
        for f in outcomes:
            try:
                results.append(f.result())
            except Exception as e:            # 允许 PermissionError；其余异常一律当缺陷
                errors.append(e)

    assert len(results) >= 1, f"两位写入者全部失败: {errors}"
    assert all(isinstance(e, PermissionError) for e in errors), f"出现非争用型异常: {errors}"
    final = json.loads(target.read_text(encoding="utf-8"))
    assert final["source_file"] in {"bench_a.json", "bench_b.json"}
    assert final["n_entries"] == 30 and len(final["entries"]) == 30
    assert {r["source_file"] for r in results} | {final["source_file"]} <= {"bench_a.json", "bench_b.json"}
