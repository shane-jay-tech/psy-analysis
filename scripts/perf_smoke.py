"""性能 smoke 测试 — 测量关键操作耗时，建立基线。

用法：
    .venv/Scripts/python.exe scripts/perf_smoke.py
    .venv/Scripts/python.exe scripts/perf_smoke.py --json    # 输出 JSON（供 CI）
    .venv/Scripts/python.exe scripts/perf_smoke.py --warm    # 跑热启动（跳过冷启动）

每次运行结果追加到 data/perf_history.jsonl，可用于趋势分析。
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

HISTORY_FILE = PROJECT_ROOT / "data" / "perf_history.jsonl"

THRESHOLDS = {
    "core_imports": 4000,
    "csv_load": 500,
    "descriptive": 2000,
    "ttest": 1000,
    "correlation": 1000,
    "docx_export": 5000,
    "learning_card": 1000,
}


def _time_it(key, label, fn, results, *, emit_text=True):
    threshold = THRESHOLDS.get(key)
    start = time.perf_counter()
    try:
        result = fn()
        elapsed = (time.perf_counter() - start) * 1000
        if threshold and elapsed > threshold:
            status = "WARN"
        else:
            status = "OK"
        if emit_text:
            print(f"  [{status:>4}] {label:<40} {elapsed:>8.1f} ms", end="")
            if status == "WARN":
                print(f"  (threshold: {threshold} ms)", end="")
            print()
        results[key] = {"ms": round(elapsed, 1), "status": status}
        return result
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        if emit_text:
            print(f"  [FAIL] {label:<40} {elapsed:>8.1f} ms  ({type(e).__name__}: {e})")
        results[key] = {"ms": round(elapsed, 1), "status": "FAIL", "error": str(e)}
        return None


def test_imports(results, *, emit_text=True):
    def _import_core():
        import pandas  # noqa: F401
        import numpy  # noqa: F401
        import scipy  # noqa: F401
        import statsmodels  # noqa: F401
        from src.analysis.runner import AnalysisRegistry  # noqa: F401
        return len(AnalysisRegistry)
    return _time_it("core_imports", "Core imports (pandas/scipy/analysis)", _import_core, results, emit_text=emit_text)


def test_load_csv(results, *, emit_text=True):
    import pandas as pd
    import numpy as np
    import tempfile
    import os

    np.random.seed(42)
    df = pd.DataFrame({
        "group": np.random.choice(["A", "B"], 1000),
        "score1": np.random.normal(50, 10, 1000),
        "score2": np.random.normal(60, 15, 1000),
        "age": np.random.randint(18, 65, 1000),
    })
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8")
    df.to_csv(tmp.name, index=False)
    tmp.close()

    def _load():
        from src.data.loader import load_data
        with open(tmp.name, "rb") as f:
            result_df, meta = load_data(f)
        return len(result_df)

    result = _time_it("csv_load", "Load CSV (1000 rows, 4 cols)", _load, results, emit_text=emit_text)
    os.unlink(tmp.name)
    return result


def test_run_ttest(results, *, emit_text=True):
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    df = pd.DataFrame({
        "group": ["A"] * 50 + ["B"] * 50,
        "score": np.concatenate([
            np.random.normal(50, 10, 50),
            np.random.normal(55, 10, 50),
        ]),
    })

    def _run():
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        plan = AnalysisPlan(
            test_type="independent_ttest",
            dependent_vars=["score"],
            independent_vars=["group"],
        )
        return run_analysis(df, plan) is not None

    return _time_it("ttest", "Independent t-test (N=100)", _run, results, emit_text=emit_text)


def test_run_descriptive(results, *, emit_text=True):
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    df = pd.DataFrame({
        f"var_{i}": np.random.normal(0, 1, 500) for i in range(10)
    })

    def _run():
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        plan = AnalysisPlan(
            test_type="descriptive",
            dependent_vars=[f"var_{i}" for i in range(10)],
        )
        return run_analysis(df, plan) is not None

    return _time_it("descriptive", "Descriptive stats (500x10)", _run, results, emit_text=emit_text)


def test_run_correlation(results, *, emit_text=True):
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    df = pd.DataFrame({
        "x": np.random.normal(0, 1, 200),
        "y": np.random.normal(0, 1, 200),
    })
    df["y"] = df["x"] * 0.6 + df["y"] * 0.4

    def _run():
        from src.analysis.runner import run_analysis
        from src.parser.intent_resolver import AnalysisPlan
        plan = AnalysisPlan(
            test_type="pearson_correlation",
            dependent_vars=["x", "y"],
        )
        return run_analysis(df, plan) is not None

    return _time_it("correlation", "Pearson correlation (N=200)", _run, results, emit_text=emit_text)


def test_docx_export(results, *, emit_text=True):
    def _export():
        from src.output.docx_exporter import build_thesis_docx, ThesisMeta
        meta = ThesisMeta(title="测试论文标题", author="测试作者")
        docx_bytes = build_thesis_docx(
            meta=meta,
            method_md="## 方法\n\n这是方法段落。" * 10,
            result_md="## 结果\n\n这是结果段落。" * 10,
        )
        return len(docx_bytes)

    return _time_it("docx_export", "Word export (thesis docx)", _export, results, emit_text=emit_text)


def test_learning_card(results, *, emit_text=True):
    def _gen():
        from src.output.learning_card import generate_learning_card
        card = generate_learning_card("independent_ttest", "独立样本t检验")
        return card is not None

    return _time_it("learning_card", "Learning card generation", _gen, results, emit_text=emit_text)


def save_history(results, run_type="cold"):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "run_type": run_type,
        "results": results,
    }
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON only (CI-friendly)")
    parser.add_argument("--warm", action="store_true", help="Skip cold run, only warm")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any WARN or FAIL")
    args = parser.parse_args()

    results = {}
    run_type = "warm" if args.warm else "cold"
    emit_text = not args.json

    if emit_text:
        print("=" * 64)
        print(f"  Psy-Analysis Performance Smoke Test ({run_type} start)")
        print("=" * 64)
        print()
        print("  Benchmark results:")
        print("  " + "-" * 60)

    test_imports(results, emit_text=emit_text)
    test_load_csv(results, emit_text=emit_text)
    test_run_descriptive(results, emit_text=emit_text)
    test_run_ttest(results, emit_text=emit_text)
    test_run_correlation(results, emit_text=emit_text)
    test_docx_export(results, emit_text=emit_text)
    test_learning_card(results, emit_text=emit_text)

    warns = [k for k, v in results.items() if v.get("status") == "WARN"]
    fails = [k for k, v in results.items() if v.get("status") == "FAIL"]

    if emit_text:
        print()
        print("  " + "-" * 60)
        print("  Thresholds (WARN if exceeded):")
        for key, ms in THRESHOLDS.items():
            print(f"    {key:<20} < {ms} ms")
        print()
        if warns:
            print(f"  [!] {len(warns)} warning(s): {', '.join(warns)}")
        if fails:
            print(f"  [X] {len(fails)} failure(s): {', '.join(fails)}")
        if not warns and not fails:
            print("  All tests within thresholds.")
        print("=" * 64)
    else:
        output = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "run_type": run_type,
            "thresholds": THRESHOLDS,
            "results": results,
            "summary": {
                "warnings": len(warns),
                "failures": len(fails),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    save_history(results, run_type)

    if fails or (args.strict and warns):
        sys.exit(1)


if __name__ == "__main__":
    main()
