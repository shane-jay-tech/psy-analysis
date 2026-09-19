# -*- coding: utf-8 -*-
"""d913d-11 草案：psy 苏格拉底基准离线补评（纯本地规则，不调模型、不写库）。

评分规则锚点（仓库内既有实现，零自创口径）：
- src/upstream/socratic_benchmark.py JudgeScore.total：0-100 ＝ 启发性(1-5)×12(60 分)
  ＋ 跨阶段一致性(20 分) ＋ 核心维度命中(20 分)；
- scripts/evaluate_socratic_benchmark.py _heuristic_coverage：expected_dimensions
  关键词覆盖率（0-1，仓库既有的本地启发式，自述「不替代人工标注」）。

本草案只能**客观**计算「核心维度命中」（20 分段）与给出启发式覆盖率作人工预填；
启发性 60 分与跨阶段一致性 20 分属主观维度，离线规则不冒充可评——按 None 透传人工。

设计为 side-car 输出（benchmark_backfill_draft.json），不改写原始基准 JSON；
--apply 未实现（本任务只要求草案＋dry-run）。
"""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(r"D:/code/psy-analysis")
BENCH = REPO / "data/benchmark_history/socratic_benchmark_20260909T192139Z.json"

# 动态加载仓库既有启发式（避免复制规则造成双源漂移）
_spec = importlib.util.spec_from_file_location(
    "eval_socratic", REPO / "scripts/evaluate_socratic_benchmark.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
heuristic_coverage = _mod._heuristic_coverage


def score_case(case: dict) -> dict:
    """单条离线补评：只产出客观可算的 20 分段判定＋人工预填材料。"""
    reply = case.get("llm_reply") or ""
    dims = case.get("expected_dimensions") or []
    coverage = heuristic_coverage(reply, dims) if dims else 0.0
    core_hit = coverage > 0.0
    per_dim = [(d, _mod._has_dimension_keyword(reply, d)) for d in dims]
    return {
        "case_id": case.get("case_id"),
        "stage": case.get("stage"),
        "coverage": round(coverage, 3),
        "per_dim_hits": [d for d, hit in per_dim if hit],
        "offline_core_hit_20pts": core_hit,            # JudgeScore 第三项（20 分）客观判定
        "offline_score_floor": 20 if core_hit else 0,  # 离线可保证的分数下界
        "inspirational_60pts": None,                    # 主观维度：不冒充，透传人工
        "cross_stage_20pts": None,                      # 主观维度：不冒充，透传人工
        "suggested_manual_notes": (
            f"[离线预填] 维度覆盖 {sum(1 for _, h in per_dim if h)}/{len(dims)}"
            f"（{coverage:.0%}）；llm_reply 长度 {len(reply)}。启发性与跨阶段一致性需人工评。"
        ),
    }


def build_sidecar(data: dict, source_name: str = BENCH.name) -> dict:
    """组装 side-car：六原字段原样引用 + manual_score（恒 None）+ manual_notes（客观证据）。"""
    import hashlib
    entries = []
    for case in data.get("results", []):
        evidence = score_case(case)
        entries.append({
            "case_id": case.get("case_id"),
            "stage": case.get("stage"),
            "input": case.get("input"),
            "expected_dimensions": case.get("expected_dimensions"),
            "llm_reply": case.get("llm_reply"),
            "error": case.get("error"),
            "manual_score": None,   # 1-5 启发性为主观维：脚本一律保留 null，不冒充人工
            "manual_notes": evidence["suggested_manual_notes"],
        })
    return {
        "artifact": "benchmark-manual-score-backfill-sidecar",
        "source_file": source_name,
        "source_sha256": hashlib.sha256(BENCH.read_bytes()).hexdigest(),
        "generated_by": "backfill-draft.py --apply（20260915-130540-dd4d；授权记录 docs/decisions/2026-09-15-psy-benchmark-scoring-baseline.md）",
        "n_entries": len(entries),
        "manual_score_null_count": sum(1 for e in entries if e["manual_score"] is None),
        "entries": entries,
    }


def apply_sidecar(bench_path: Path = BENCH, sidecar_path: Path | None = None,
                  data: dict | None = None) -> dict:
    """真正落盘 side-car（20260915-130540-dd4d 授权）：绝不触碰原始基准 JSON。

    - 幂等：同输入产出字节一致；
    - side-car 已存在时先写 .bak 备份；
    - 写后断言原始 JSON 字节未变。
    """
    import hashlib
    sidecar_path = sidecar_path or (bench_path.parent / "benchmark_backfill_draft.json")
    if data is None:
        data = json.loads(bench_path.read_text(encoding="utf-8"))
    payload = build_sidecar(data, source_name=bench_path.name)
    payload["source_sha256"] = hashlib.sha256(bench_path.read_bytes()).hexdigest()

    if sidecar_path.exists():
        backup = sidecar_path.with_suffix(".json.bak")
        backup.write_bytes(sidecar_path.read_bytes())
        print(f"[apply] 已备份既有 side-car → {backup.name}")

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    sidecar_path.write_text(text, encoding="utf-8")

    after = hashlib.sha256(bench_path.read_bytes()).hexdigest()
    assert after == payload["source_sha256"], "原始基准 JSON 发生了变化（不应发生）"

    entries = payload["entries"]
    print(f"[apply] side-car 落盘: {sidecar_path}")
    print(f"[apply] 条数 {len(entries)}；manual_score 为 null {payload['manual_score_null_count']}/{len(entries)}；"
          f"manual_notes 已填 {sum(1 for e in entries if e.get('manual_notes'))} 条")
    print(f"[apply] 原始 JSON sha256 校验一致: {after[:16]}…")
    return payload


def main() -> int:
    data = json.loads(BENCH.read_text(encoding="utf-8"))
    results = data.get("results", [])
    print(f"[load] {BENCH.name}: version={data.get('version')} n_cases={data.get('n_cases')} "
          f"results={len(results)} manual_score=None 条数="
          f"{sum(1 for r in results if r.get('manual_score') is None)}")
    if "--apply" in sys.argv:
        apply_sidecar()
        return 0

    # dry-run：仅第一条样例，打印输入/中间量/输出，零写回
    sample = results[0]
    print("\n[dry-run 样例输入]")
    print(json.dumps({k: sample.get(k) for k in ("case_id", "stage", "input",
                                                 "expected_dimensions")}, ensure_ascii=False))
    print("llm_reply =", repr(sample.get("llm_reply")))
    out = score_case(sample)
    print("\n[dry-run 中间量与输出]")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("\n[dry-run 结论] 纯本地规则可客观预填 20 分段与覆盖率材料；"
          "80/100 分段的另外两维需人工。零写库、零写回基准 JSON。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
