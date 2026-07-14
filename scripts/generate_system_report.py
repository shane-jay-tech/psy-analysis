"""系统报告自动生成器 — 从源码实测输出指标，不手写数字。

用法：
    .venv/Scripts/python.exe scripts/generate_system_report.py
    .venv/Scripts/python.exe scripts/generate_system_report.py --format markdown
    .venv/Scripts/python.exe scripts/generate_system_report.py --format markdown --collect-pytest
    .venv/Scripts/python.exe scripts/generate_system_report.py --check docs/SYSTEM_REPORT.md
"""
import argparse
import contextlib
import io
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"


@contextlib.contextmanager
def _suppress_third_party_noise():
    """Suppress stdout/stderr noise from third-party libs (jieba, etc.)."""
    logging.disable(logging.CRITICAL)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
        logging.disable(logging.NOTSET)

EXCLUDE_DIRS = {".venv", ".git", "__pycache__", "node_modules", ".pytest_cache"}


def _iter_py_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f


def count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in open(path, encoding="utf-8", errors="ignore"))
    except Exception:
        return 0


def count_pattern(path: Path, pattern: str) -> int:
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
        return len(re.findall(pattern, text))
    except Exception:
        return 0


def gather_metrics():
    """Collect all system metrics, return as dict."""
    metrics = {}

    # Version — single source of truth
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from src.version import APP_VERSION_LABEL
        version = APP_VERSION_LABEL
    except ImportError:
        version = "unknown"
    metrics["version"] = version

    # File and code stats
    all_py = list(_iter_py_files(PROJECT_ROOT))
    metrics["total_files"] = len(all_py)
    metrics["total_lines"] = sum(count_lines(f) for f in all_py)
    metrics["total_classes"] = sum(count_pattern(f, r"(?m)^class ") for f in all_py)
    metrics["total_functions"] = sum(count_pattern(f, r"(?m)^(?:    )?def ") for f in all_py)

    # Module breakdown
    modules = [
        "src/analysis", "src/questionnaire", "src/paper_writer",
        "src/ui", "src/literature_feed", "src/experiment_design",
        "src/output", "src/literature_review", "src/visualization",
        "src/parser", "src/upstream", "src/llm_gateway",
        "src/data", "src/utils",
    ]
    mod_data = {}
    for mod in modules:
        mod_path = PROJECT_ROOT / mod
        if mod_path.exists():
            files = list(_iter_py_files(mod_path))
            lines = sum(count_lines(f) for f in files)
            mod_data[mod] = {"files": len(files), "lines": lines}
    metrics["modules"] = mod_data

    # Tests
    test_files = [f for f in _iter_py_files(TESTS_DIR) if f.name.startswith("test_")]
    test_funcs = sum(count_pattern(f, r"(?m)^\s*def test_") for f in test_files)
    metrics["test_files"] = len(test_files)
    metrics["test_functions"] = test_funcs

    # Registered methods (suppress jieba/streamlit noise)
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        with _suppress_third_party_noise():
            from src.analysis.runner import AnalysisRegistry
        metrics["registered_methods"] = len(AnalysisRegistry)
    except Exception:
        metrics["registered_methods"] = "?"

    # Learning cards
    try:
        with _suppress_third_party_noise():
            from src.output.learning_card import LEARNING_DB
        metrics["learning_cards"] = len(LEARNING_DB)
    except Exception:
        metrics["learning_cards"] = "?"

    # Dependencies (suppress import noise)
    deps = [
        "streamlit", "pandas", "numpy", "scipy", "statsmodels",
        "pingouin", "plotly", "kaleido", "jieba", "openpyxl",
        "pyreadstat", "openai", "docx", "fpdf", "factor_analyzer",
        "sklearn", "semopy", "yaml", "pypdf", "webview",
    ]
    dep_status = {}
    with _suppress_third_party_noise():
        for dep in deps:
            try:
                __import__(dep)
                dep_status[dep] = True
            except ImportError:
                dep_status[dep] = False
        try:
            __import__("pytest")
            dep_status["pytest"] = True
        except ImportError:
            dep_status["pytest"] = False
    metrics["dependencies"] = dep_status

    return metrics


class PytestCollectResult:
    __slots__ = ("items", "ok", "error")

    def __init__(self, items: int | None, ok: bool, error: str = ""):
        self.items = items
        self.ok = ok
        self.error = error


def collect_pytest_items() -> PytestCollectResult:
    """Run pytest --collect-only and return structured result."""
    try:
        result = subprocess.run(
            [str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
             "-m", "pytest", "--collect-only"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            timeout=90, encoding="utf-8", errors="replace",
        )
        for line in result.stdout.splitlines():
            m = re.search(r"(\d+)\s+tests?\s+collected", line)
            if m:
                return PytestCollectResult(int(m.group(1)), ok=True)
        return PytestCollectResult(None, ok=False, error="no collection summary in output")
    except subprocess.TimeoutExpired:
        return PytestCollectResult(None, ok=False, error="timeout (90s)")
    except Exception as e:
        return PytestCollectResult(None, ok=False, error=str(e))


def print_text_report(metrics):
    """Print human-readable text report (ASCII-safe)."""
    print(f"{'='*60}")
    print(f"  Psy-Analysis System Metrics Report")
    print(f"  Date: {date.today()}")
    print(f"  Version: {metrics['version']}")
    print(f"  Path: {PROJECT_ROOT}")
    print(f"{'='*60}\n")

    print(f"{'─'*40}")
    print(f"  Code Scale")
    print(f"{'─'*40}")
    print(f"  Python files:       {metrics['total_files']}")
    print(f"  Total lines:        {metrics['total_lines']:,}")
    print(f"  Classes:            {metrics['total_classes']}")
    print(f"  Functions:          {metrics['total_functions']}")
    print()

    print(f"{'─'*40}")
    print(f"  Module Breakdown")
    print(f"{'─'*40}")
    for mod, data in metrics["modules"].items():
        print(f"  {mod:<30} {data['files']:>3} files  {data['lines']:>6,} lines")
    print()

    print(f"{'─'*40}")
    print(f"  Tests")
    print(f"{'─'*40}")
    print(f"  Test files:         {metrics['test_files']}")
    print(f"  Test functions:     {metrics['test_functions']}")
    print()

    print(f"{'─'*40}")
    print(f"  Features")
    print(f"{'─'*40}")
    print(f"  Registered methods: {metrics['registered_methods']}")
    print(f"  Learning cards:     {metrics['learning_cards']}/{metrics['registered_methods']}")
    if isinstance(metrics['registered_methods'], int) and isinstance(metrics['learning_cards'], int):
        coverage = metrics['learning_cards'] / metrics['registered_methods'] * 100
        print(f"  Card coverage:      {coverage:.0f}%")
    print()

    print(f"{'─'*40}")
    print(f"  Dependencies")
    print(f"{'─'*40}")
    for dep, ok in metrics["dependencies"].items():
        status = "[OK]" if ok else "[MISS]"
        print(f"  {status:>6} {dep}")
    print()
    print(f"{'='*60}")
    print(f"  Report complete")
    print(f"{'='*60}")


def print_markdown_report(metrics, *, pytest_result: PytestCollectResult | None = None):
    """Print markdown-formatted metrics block (for embedding in docs)."""
    print("<!-- AUTO-GENERATED by scripts/generate_system_report.py -->")
    print(f"<!-- Generated: {date.today()} -->")
    print()
    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Version | {metrics['version']} |")
    print(f"| Python files | {metrics['total_files']} |")
    print(f"| Total lines | {metrics['total_lines']:,} |")
    print(f"| Classes | {metrics['total_classes']} |")
    print(f"| Functions | {metrics['total_functions']} |")
    print(f"| Test files | {metrics['test_files']} |")
    print(f"| Test functions (def test_) | {metrics['test_functions']} |")
    if pytest_result is not None:
        if pytest_result.ok:
            print(f"| Pytest collected items | {pytest_result.items} |")
        else:
            print(f"| Pytest collected items | unavailable |")
            print(f"| Pytest collect error | {pytest_result.error} |")
    print(f"| Registered methods | {metrics['registered_methods']} |")
    print(f"| Learning cards | {metrics['learning_cards']}/{metrics['registered_methods']} |")
    print()
    print("| Module | Files | Lines |")
    print("|--------|------:|------:|")
    for mod, data in metrics["modules"].items():
        print(f"| `{mod}/` | {data['files']} | {data['lines']:,} |")
    tests_lines = sum(count_lines(f) for f in _iter_py_files(TESTS_DIR))
    print(f"| `tests/` | {metrics['test_files']} | {tests_lines:,} |")
    print()
    ok_count = sum(1 for v in metrics["dependencies"].values() if v)
    total_deps = len(metrics["dependencies"])
    print(f"Dependencies: {ok_count}/{total_deps} available")
    missing = [k for k, v in metrics["dependencies"].items() if not v]
    if missing:
        print(f"Missing: {', '.join(missing)}")


def check_report(metrics, report_path: str):
    """Check if an existing report matches current metrics."""
    path = Path(report_path)
    if not path.exists():
        print(f"[FAIL] Report file not found: {report_path}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8", errors="ignore")
    issues = []

    # Check key numbers (handle both plain and comma-formatted)
    checks = [
        ("total_files", metrics["total_files"]),
        ("registered_methods", metrics["registered_methods"]),
        ("test_functions", metrics["test_functions"]),
        ("learning_cards", metrics["learning_cards"]),
    ]
    for label, val in checks:
        if not isinstance(val, int):
            continue
        plain = str(val)
        formatted = f"{val:,}"
        if plain not in text and formatted not in text:
            issues.append(f"  {label}: expected '{plain}' not found in report")

    if issues:
        print(f"[WARN] Report may be outdated:")
        for i in issues:
            print(i)
        print(f"\nRe-run: .venv/Scripts/python.exe scripts/generate_system_report.py")
    else:
        print(f"[OK] Report numbers match source code.")


def main():
    parser = argparse.ArgumentParser(description="Generate system metrics report")
    parser.add_argument("--format", choices=["text", "markdown"], default="text")
    parser.add_argument("--check", metavar="REPORT_PATH", help="Check if report matches source")
    parser.add_argument("--collect-pytest", action="store_true",
                        help="Also run pytest --collect-only (slower)")
    args = parser.parse_args()

    metrics = gather_metrics()
    pytest_result = collect_pytest_items() if args.collect_pytest else None

    if args.check:
        check_report(metrics, args.check)
        if pytest_result and not pytest_result.ok:
            print(f"[WARN] Pytest collection failed: {pytest_result.error}")
            sys.exit(1)
    elif args.format == "markdown":
        print_markdown_report(metrics, pytest_result=pytest_result)
    else:
        print_text_report(metrics)


if __name__ == "__main__":
    main()
