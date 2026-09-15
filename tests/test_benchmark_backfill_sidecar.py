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
