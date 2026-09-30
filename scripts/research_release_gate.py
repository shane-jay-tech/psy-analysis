"""研究发布门禁（五环节可复跑）。

串起：数据来源 → 统计检查 → 图表 → 主张校准 → 匿名化。
与 release_gate.py 的区别：
- 三态输出：pass / fail / blocked（统计结论必须有人工复核签收才可 pass）；
- 每个检查的命令、退出码与输出尾部落盘到 tmp/gate-evidence/<时间戳>/ 作为证据。

用法：
    python scripts/research_release_gate.py                     # 跑全部环节
    python scripts/research_release_gate.py --confirm-review 姓名  # 人工复核签收
    python scripts/research_release_gate.py --fail-probe        # 演练 fail 态
退出码：0=pass，1=fail，2=blocked。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PYTHON = sys.executable or "python"

PASS, FAIL, BLOCKED = "pass", "fail", "blocked"


def run_cmd(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    """跑一条命令，返回 (退出码, 合并输出尾部)。"""
    try:
        r = subprocess.run(
            cmd, cwd=BASE, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def check_data_sources() -> tuple[bool, str]:
    """数据来源：feed 库只读完整性＋来源非空。"""
    db = BASE / "data" / "literature_feed" / "feed.sqlite"
    if not db.exists():
        return False, f"missing: {db}"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            ic = con.execute("pragma integrity_check").fetchone()[0]
            n = con.execute("select count(*) from sources").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        # s927-11 缺陷修（2026-09-30 主班）：损坏/非 sqlite 文件原样抛出会打断整条门禁，
        # 按契约返回 (False, "corrupt: …")，与 missing 同档。
        return False, f"corrupt: {exc}"
    return ic == "ok" and n > 0, f"integrity={ic}, sources={n}"


def pytest_cmd(files: list[str]) -> list[str]:
    return [PYTHON, "-m", "pytest", "-q", "--tb=no", *files]


def main() -> int:
    ap = argparse.ArgumentParser(description="研究发布门禁（五环节·三态）")
    ap.add_argument("--confirm-review", metavar="NAME", help="统计结论人工复核签收人")
    ap.add_argument("--fail-probe", action="store_true", help="注入一个必败检查，演练 fail 态")
    args = ap.parse_args()

    stages: list[tuple[str, object, list[list[str]]]] = [
        ("1-数据来源", check_data_sources, []),
        ("2-统计检查", None, [
            pytest_cmd(["tests/test_golden_stats_v2.py", "tests/test_effect_size_ci.py"]),
            pytest_cmd(["tests/test_golden_delivery.py"]),
        ]),
        ("3-图表", None, [
            pytest_cmd(["tests/test_visualization_charts.py",
                        "tests/test_apa_figures_v2.py",
                        "tests/test_figure_collection.py"]),
        ]),
        ("4-主张校准", None, [
            pytest_cmd(["tests/test_evidence_quality.py"]),
        ]),
        ("5-匿名化", None, [
            pytest_cmd(["tests/test_guardrails_pii.py", "tests/test_guardrails_pii_probes.py"]),
        ]),
    ]
    if args.fail_probe:
        stages.append(("probe-必败演练", None, [[PYTHON, "-c", "import sys; sys.exit(3)"]]))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    ev_dir = BASE / "tmp" / "gate-evidence" / stamp
    ev_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 56)
    print("  Psy-Analysis 研究发布门禁（数据源→统计→图表→主张→匿名化）")
    print("=" * 56)

    any_fail = False
    for name, fn, cmds in stages:
        entries = []
        if fn is not None:
            ok, detail = fn()
            entries.append({"command": f"<inline:{name}>", "exit": 0 if ok else 1,
                            "output": detail})
            state = "PASS" if ok else "FAIL"
        else:
            state = "PASS"
            for cmd in cmds:
                code, out = run_cmd(cmd)
                entries.append({"command": " ".join(cmd), "exit": code, "output": out[-800:]})
                if code != 0:
                    state = "FAIL"
        (ev_dir / f"{name}.json").write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [{name}] {state}  (证据: {name}.json)")
        if state == "FAIL":
            any_fail = True

    if any_fail:
        verdict = FAIL
    elif args.confirm_review:
        (ev_dir / "HUMAN_REVIEW.json").write_text(
            json.dumps({"reviewer": args.confirm_review,
                        "at": datetime.now().isoformat(timespec="seconds")},
                       ensure_ascii=False), encoding="utf-8")
        verdict = PASS
    else:
        verdict = BLOCKED

    print()
    if verdict == PASS:
        print(f"PASS：五环节全绿，人工复核已签收（{args.confirm_review}）。证据目录：{ev_dir}")
        code = 0
    elif verdict == BLOCKED:
        print(f"BLOCKED：检查全绿，但统计结论待人工复核。签收：--confirm-review 姓名。证据目录：{ev_dir}")
        code = 2
    else:
        print(f"FAIL：存在失败环节，先修复再复跑。证据目录：{ev_dir}")
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
