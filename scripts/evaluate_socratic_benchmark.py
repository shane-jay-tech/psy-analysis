"""LLM prompt 优化时的回归对比 + 历史漂移观测脚本。

两种模式：

# 模式 A：手动两份对比（v3.7 原版）
    pytest tests/test_socratic_quality.py --run-benchmark   # 跑基准 → tests/fixtures/_benchmark_reports/
    python scripts/evaluate_socratic_benchmark.py \\
        --baseline tests/fixtures/_benchmark_reports/benchmark_OLD.json \\
        --candidate tests/fixtures/_benchmark_reports/benchmark_NEW.json

# 模式 B：自动漂移追踪（N10 新增）
    pytest tests/test_socratic_quality.py --run-benchmark   # 先跑一次基准
    python scripts/evaluate_socratic_benchmark.py --track-drift
    # → 把最新报告归档到 data/benchmark_history/，自动对比上一次归档，输出 drift 报告
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "tests" / "fixtures" / "_benchmark_reports"
HISTORY_DIR = REPO_ROOT / "data" / "benchmark_history"


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_by_case_id(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {r["case_id"]: r for r in report.get("results", [])}


def _has_dimension_keyword(reply: str, dim: str) -> bool:
    """简单启发式：反问中是否包含期望维度的核心字。"""
    if not reply or not dim:
        return False
    return any(seg in reply for seg in dim.split() if len(seg) >= 2) \
           or any(c in reply for c in dim if "一" <= c <= "鿿")


def _heuristic_coverage(reply: str, dimensions: List[str]) -> float:
    """启发式覆盖率（粗略，仅作回归对比，不替代人工标注）。"""
    if not dimensions:
        return 0.0
    hits = sum(1 for d in dimensions if _has_dimension_keyword(reply, d))
    return hits / len(dimensions)


def _compare_reports(base: Dict[str, Any], cand: Dict[str, Any]) -> Tuple[List[str], Dict[str, int]]:
    """对比两份报告，返回 (rows, summary)。"""
    base_idx = _index_by_case_id(base)
    cand_idx = _index_by_case_id(cand)

    improved = 0
    regressed = 0
    same = 0
    rows: List[str] = []
    base_avg = 0.0
    cand_avg = 0.0
    n = 0

    for cid, b in base_idx.items():
        c = cand_idx.get(cid)
        if c is None:
            continue
        dims = b.get("expected_dimensions", [])
        score_b = _heuristic_coverage(b.get("llm_reply", ""), dims)
        score_c = _heuristic_coverage(c.get("llm_reply", ""), dims)
        base_avg += score_b
        cand_avg += score_c
        n += 1
        if score_c > score_b + 0.05:
            improved += 1
            tag = "[IMPROVED]"
        elif score_c < score_b - 0.05:
            regressed += 1
            tag = "[REGRESSED]"
        else:
            same += 1
            tag = "[SAME    ]"
        rows.append(f"  {cid:20s}  {tag}  baseline={score_b:.2f}  candidate={score_c:.2f}")

    summary = {
        "improved": improved,
        "regressed": regressed,
        "same": same,
        "n": n,
        "base_avg_pct": int(base_avg / n * 100) if n else 0,
        "cand_avg_pct": int(cand_avg / n * 100) if n else 0,
    }
    return rows, summary


def _print_comparison(base: Dict[str, Any], cand: Dict[str, Any], *,
                      base_label: str, cand_label: str) -> Dict[str, int]:
    print("# Benchmark 对比")
    print(f"- baseline:  {base_label} (LLM={base.get('llm', {}).get('model', '?')})")
    print(f"- candidate: {cand_label} (LLM={cand.get('llm', {}).get('model', '?')})\n")
    rows, summary = _compare_reports(base, cand)
    print("\n".join(rows))
    print()
    print(f"汇总：improved={summary['improved']}  regressed={summary['regressed']}  "
          f"same={summary['same']}  n={summary['n']}")
    print(f"启发式平均覆盖率：baseline={summary['base_avg_pct']}%  candidate={summary['cand_avg_pct']}%")
    print("注：启发式覆盖率仅供粗略对比，最终质量需人工标注 manual_score 字段。")
    return summary


# =============================================================================
# 漂移追踪模式（N10 新增）
# =============================================================================

def _latest_report(report_dir: Path) -> Optional[Path]:
    """返回 _benchmark_reports/ 里 mtime 最新的 benchmark_*.json。"""
    if not report_dir.exists():
        return None
    cands = sorted(report_dir.glob("benchmark_*.json"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def _last_history_entry(history_dir: Path) -> Optional[Path]:
    """返回 data/benchmark_history/ 里上一次的归档（按文件名排序，UTC 时间戳保证字典序＝时间序）。"""
    if not history_dir.exists():
        return None
    cands = sorted(history_dir.glob("*.json"))
    return cands[-1] if cands else None


def _archive_to_history(latest_report: Path, history_dir: Path) -> Path:
    """把最新报告复制到 history，文件名带 UTC 时间戳。"""
    history_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = history_dir / f"socratic_benchmark_{ts}.json"
    shutil.copy2(latest_report, target)
    return target


def _write_drift_markdown(history_dir: Path, *,
                          previous: Optional[Path],
                          archived: Path,
                          summary: Optional[Dict[str, int]]) -> Path:
    """写一份给人看的 drift 报告 markdown 到 data/benchmark_history/_latest_drift.md。"""
    target = history_dir / "_latest_drift.md"
    lines: List[str] = []
    lines.append("# 苏格拉底基准漂移观测")
    lines.append(f"- 归档时间：{datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- 当前归档：`{archived.name}`")
    if previous is None:
        lines.append("- 上一次归档：（无 — 这是第一次跑漂移追踪）")
        lines.append("")
        lines.append("**结论**：仅记录起点，无法计算漂移。下次跑完会自动对比。")
    else:
        lines.append(f"- 上一次归档：`{previous.name}`")
        if summary is None:
            lines.append("")
            lines.append("**结论**：对比失败（报告结构不一致或读取错误）。")
        else:
            lines.append(f"- improved / regressed / same / n: {summary['improved']} / "
                         f"{summary['regressed']} / {summary['same']} / {summary['n']}")
            lines.append(f"- 启发式平均覆盖率：{summary['base_avg_pct']}% → {summary['cand_avg_pct']}%")
            lines.append("")
            delta = summary["cand_avg_pct"] - summary["base_avg_pct"]
            if summary["regressed"] > summary["improved"]:
                lines.append(f"**结论**：⚠ 退化 — regressed > improved，平均覆盖率变化 {delta:+d}%。")
                lines.append("建议人工审阅 prompt / 检查 LLM 响应模板是否漂移。")
            elif summary["improved"] > summary["regressed"]:
                lines.append(f"**结论**：✓ 改进 — improved > regressed，平均覆盖率变化 {delta:+d}%。")
            else:
                lines.append(f"**结论**：≈ 持平 — improved 与 regressed 相当，平均覆盖率变化 {delta:+d}%。")
            lines.append("")
            lines.append("注：启发式覆盖率仅供粗略对比，最终质量需人工标注 manual_score 字段。")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _track_drift() -> int:
    """N10 模式：归档最新报告 + 对比上一次归档。"""
    latest = _latest_report(REPORT_DIR)
    if latest is None:
        print(f"未在 {REPORT_DIR} 找到 benchmark 报告。")
        print("先跑：pytest tests/test_socratic_quality.py --run-benchmark")
        return 1

    previous = _last_history_entry(HISTORY_DIR)
    archived = _archive_to_history(latest, HISTORY_DIR)
    print(f"已归档：{archived}")

    summary: Optional[Dict[str, int]] = None
    if previous is None:
        print("（上一次归档不存在 — 这是首次记录起点。）")
    else:
        try:
            prev_report = _load(previous)
            curr_report = _load(archived)
            summary = _print_comparison(
                prev_report, curr_report,
                base_label=previous.name, cand_label=archived.name,
            )
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            print(f"对比失败：{exc}")
            summary = None

    md = _write_drift_markdown(HISTORY_DIR, previous=previous,
                               archived=archived, summary=summary)
    print(f"漂移报告：{md}")
    return 0


# =============================================================================
# CLI
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="对比两次 socratic benchmark 报告")
    ap.add_argument("--baseline", type=Path, help="基准报告路径（手动模式）")
    ap.add_argument("--candidate", type=Path, help="候选报告路径（手动模式）")
    ap.add_argument("--track-drift", action="store_true",
                    help="N10 模式：归档最新报告 + 对比上一次归档")
    args = ap.parse_args()

    if args.track_drift:
        return _track_drift()

    if not args.baseline or not args.candidate:
        ap.print_help()
        return 2

    base = _load(args.baseline)
    cand = _load(args.candidate)
    _print_comparison(base, cand,
                      base_label=str(args.baseline),
                      cand_label=str(args.candidate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
