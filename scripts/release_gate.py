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
import re
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


def _pytest_summary(output: str) -> str:
    """从警告/文档链接之后仍能取到真实 passed/skipped 汇总。"""
    for line in reversed(output.strip().splitlines()):
        if re.search(r"\b(passed|failed|skipped|xfailed|xpassed|error)s?\b", line):
            return line.strip()
    lines = output.strip().splitlines()
    return lines[-1].strip() if lines else ""


def check_unit_tests() -> tuple[bool, str]:
    """单元+集成测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "--ignore=tests/test_online_fetchers.py",
        "--tb=no",
    ], timeout=600)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
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
        "--tb=no",
    ], timeout=120)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
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
        "--tb=no",
    ], timeout=60)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def check_template_golden_flows() -> tuple[bool, str]:
    """模板 Golden Flow 测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_template_golden_flows.py",
        "--tb=no",
    ], timeout=180)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def check_delivery_structure() -> tuple[bool, str]:
    """交付包结构测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_golden_delivery.py",
        "--tb=no",
    ], timeout=120)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def check_apa_tables() -> tuple[bool, str]:
    """APA 表格/图表测试。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest",
        "tests/test_apa_tables.py",
        "--tb=no",
    ], timeout=60)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
    return False, f"FAIL (exit {code}): {output[-200:]}"


def _check_pytest_contracts(files: list[str], *, timeout: int = 180) -> tuple[bool, str]:
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "-m", "pytest", *files, "--tb=no", "-ra",
    ], timeout=timeout)
    if code == 0:
        return True, f"PASS: {_pytest_summary(output)}"
    return False, f"FAIL (exit {code}): {output[-300:]}"


def check_statistics_and_evidence() -> tuple[bool, str]:
    """效应量、CI、APA7、证据引用与高风险统计金标准。"""
    return _check_pytest_contracts([
        "tests/test_golden_stats_v2.py",
        "tests/test_effect_size_ci.py",
        "tests/test_output_formatter.py",
        "tests/test_apa_tables.py",
        "tests/test_evidence_quality.py",
    ], timeout=240)


def check_privacy_ai_integrity() -> tuple[bool, str]:
    """隐私硬门禁、AI 降级与未确认 AI 修改阻断。"""
    return _check_pytest_contracts([
        "tests/test_guardrails_pii.py",
        "tests/test_privacy_archive_usage.py",
        "tests/test_llm_gateway.py",
        "tests/test_export_gate_global_scan.py",
        "tests/test_ui_golden_research_flow.py",
    ], timeout=180)


def check_workspace_compatibility() -> tuple[bool, str]:
    """旧工作区迁移、项目隔离、原子保存与损坏索引恢复。"""
    return _check_pytest_contracts([
        "tests/test_workspace.py",
        "tests/test_workspace_state.py",
        "tests/test_project_manager.py",
        "tests/test_autosave.py",
        "tests/test_template_center_ui.py",
    ], timeout=180)


def check_accessible_ui_flow() -> tuple[bool, str]:
    """隔离存储上的真实 AppTest 上传→分析流程与无障碍契约。"""
    return _check_pytest_contracts([
        "tests/test_accessibility.py",
        "tests/test_e2e_ui.py",
    ], timeout=180)


def check_performance_budget() -> tuple[bool, str]:
    """关键离线操作必须全部低于已固化阈值，且不污染历史基线。"""
    code, output = run_cmd([
        PYTHON, "-X", "utf8", "scripts/perf_smoke.py",
        "--json", "--strict", "--no-history",
    ], timeout=120)
    if code == 0:
        try:
            # 第三方库偶尔会把初始化日志写到 stderr；run_cmd 合并输出后，
            # 从首个 JSON 对象开始解析即可保留可靠的性能摘要。
            json_module = __import__("json")
            payload, _ = json_module.JSONDecoder().raw_decode(output[output.index("{"):])
            results = payload.get("results", {})
            slowest = max(results.items(), key=lambda item: item[1].get("ms", 0))
            return True, f"PASS: 0 WARN/FAIL；最慢 {slowest[0]} {slowest[1]['ms']} ms"
        except Exception:
            return True, "PASS: 性能预算内"
    return False, f"FAIL (exit {code}): {output[-300:]}"


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
            ("统计·APA·证据", check_statistics_and_evidence),
            ("隐私·AI降级·诚信", check_privacy_ai_integrity),
            ("工作区兼容与恢复", check_workspace_compatibility),
            ("无障碍 UI 黄金流", check_accessible_ui_flow),
            ("性能预算", check_performance_budget),
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
