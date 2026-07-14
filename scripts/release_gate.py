"""质量自检脚本。

快速确认核心功能正常：测试通过、ZIP 能导出、Word 能导出、金标准统计正确。
--mode full 增加 method_id 一致性、模板 Golden Flow、交付包结构、APA 表格测试。

运行:
  python scripts/release_gate.py            # 快速模式（默认）
  python scripts/release_gate.py --mode full  # 完整模式
退出码: 0=全部通过, 1=有失败
"""

import subprocess
import sys
import io
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_cmd(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(ROOT), encoding="utf-8", errors="replace",
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, str(e)


def check_unit_tests() -> tuple[bool, str]:
    """单元+集成测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "--ignore=tests/test_online_fetchers.py",
        "--tb=no", "-q",
    ], timeout=600)
    if code == 0:
        lines = output.strip().split("\n")
        summary = lines[-1] if lines else ""
        return True, f"PASS: {summary}"
    return False, f"FAIL (exit {code}): {output[-300:]}"


def check_zip_export() -> tuple[bool, str]:
    """ZIP 交付包能正常生成。"""
    try:
        sys.path.insert(0, str(ROOT))
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.zip_exporter import build_deliverable_zip
        import zipfile

        paper = PaperDraftBundle(
            title="自检", source="gate",
            sections={"r": PaperSection(name="结果", markdown="t=2.1, p=.04", source="t")},
        )
        bundle = ResearchDeliverableBundle(
            project_id="gate", title="自检", paper_bundle=paper,
            analysis_cards=[{"method_id": "independent_ttest", "apa_text": "t(28)=2.1, p=.04"}],
        )
        zip_bytes = build_deliverable_zip(bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "AI_USAGE_DISCLOSURE.md" in names
        return True, f"PASS: ZIP {len(names)} 个文件"
    except Exception as e:
        return False, f"FAIL: {e}"


def check_word_export() -> tuple[bool, str]:
    """Word 导出。"""
    try:
        sys.path.insert(0, str(ROOT))
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.docx_exporter import build_deliverable_docx

        paper = PaperDraftBundle(
            title="自检", source="gate",
            sections={"r": PaperSection(name="结果", markdown="r=.45", source="t")},
        )
        bundle = ResearchDeliverableBundle(
            project_id="gate", title="自检", paper_bundle=paper,
            analysis_cards=[{"method_id": "pearson_corr", "apa_text": "r=.45"}],
        )
        docx_bytes = build_deliverable_docx(bundle, mode="standard")
        assert len(docx_bytes) > 500
        return True, f"PASS: Word {len(docx_bytes)} bytes"
    except Exception as e:
        return False, f"FAIL: {e}"


def check_golden_stats() -> tuple[bool, str]:
    """金标准统计测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_golden_stats.py",
        "--tb=no", "-q",
    ], timeout=120)
    if code == 0:
        lines = output.strip().split("\n")
        summary = lines[-1] if lines else ""
        return True, f"PASS: {summary}"
    return False, f"FAIL (exit {code})"


def check_template_data() -> tuple[bool, str]:
    """模板目录完整性（每个模板含 data.csv）。"""
    templates_dir = ROOT / "project_templates"
    if not templates_dir.exists():
        return False, "FAIL: project_templates/ 不存在"
    template_dirs = [d for d in templates_dir.iterdir() if d.is_dir()]
    missing = [d.name for d in template_dirs if not (d / "data.csv").exists()]
    if missing:
        return False, f"FAIL: 缺少 data.csv: {', '.join(missing)}"
    return True, f"PASS: {len(template_dirs)} 个模板完整"


# --- Full mode extra checks ---

def check_method_id_consistency() -> tuple[bool, str]:
    """Method ID 一致性测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_method_id_consistency.py",
        "--tb=no", "-q",
    ], timeout=60)
    if code == 0:
        lines = output.strip().split("\n")
        summary = lines[-1] if lines else ""
        return True, f"PASS: {summary}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def check_template_golden_flows() -> tuple[bool, str]:
    """模板 Golden Flow 测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_template_golden_flows.py",
        "--tb=no", "-q",
    ], timeout=180)
    if code == 0:
        lines = output.strip().split("\n")
        summary = lines[-1] if lines else ""
        return True, f"PASS: {summary}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def check_delivery_structure() -> tuple[bool, str]:
    """交付包结构测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_golden_delivery.py",
        "--tb=no", "-q",
    ], timeout=120)
    if code == 0:
        lines = output.strip().split("\n")
        summary = lines[-1] if lines else ""
        return True, f"PASS: {summary}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def check_apa_tables() -> tuple[bool, str]:
    """APA 表格/图表测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_apa_tables.py",
        "--tb=no", "-q",
    ], timeout=60)
    if code == 0:
        lines = output.strip().split("\n")
        summary = lines[-1] if lines else ""
        return True, f"PASS: {summary}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def main():
    mode = "fast"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]
    elif "--full" in sys.argv:
        mode = "full"

    print("=" * 50)
    print(f"  Psy-Analysis 质量自检 [{mode}]")
    print("=" * 50)
    print()

    gates = [
        ("单元+集成测试", check_unit_tests),
        ("ZIP 导出", check_zip_export),
        ("Word 导出", check_word_export),
        ("金标准统计", check_golden_stats),
        ("模板完整性", check_template_data),
    ]

    if mode == "full":
        gates.extend([
            ("Method ID 一致性", check_method_id_consistency),
            ("模板 Golden Flow", check_template_golden_flows),
            ("交付包结构", check_delivery_structure),
            ("APA 表格", check_apa_tables),
        ])

    has_failure = False
    for name, fn in gates:
        print(f"  [{name}] ", end="", flush=True)
        passed, msg = fn()
        print(msg)
        if not passed:
            has_failure = True

    print()
    if has_failure:
        print("有检查未通过")
        sys.exit(1)
    else:
        print("全部通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
