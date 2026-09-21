"""s922-104：benchmark relay 的 LOG_PATH 修复防回归钉桩（只钉现状，不改实现）。

背景（锚点已按磁盘实况复核，见 result 留痕）：
- `scripts/benchmark_relay_shim.py:20` —— LOG_PATH = Path(__file__).resolve().parents[1] / "data" /
  "benchmark_history" / "_relay_calls.jsonl"。s922-09/A5（commit `eec95c3`）前写作 `Path(__file__).parent`
  形态，指向**不存在的** `scripts/data/`，因此 relay 观测日志结构上不可能落盘。
- `scripts/evaluate_socratic_benchmark.py:29` —— HISTORY_DIR = REPO_ROOT / "data" / "benchmark_history"，
  即观测归档侧的同根目录。

观测断档本身的事实表（断档 12.0 天、样本仍 1 批、根因归到 `eec95c3`）已由 s922-19 落在
`docs/insights/psy-benchmark-observe-20260922.md`；**本档不重述也不另造那套判据**，只锁住
「日志落点」这一个路径事实，防止有人把 `parents[1]` 改回 `.parent` 而无人察觉。

口径边界：
- 零网络、零 LLM、零 subprocess；
- 零写盘 —— 唯一的写文件分支是 `Handler._log()`（`benchmark_relay_shim.py:88` 的
  `LOG_PATH.parent.mkdir(...)`），本测试全程不实例化 Handler、不调用 `_log`；
- 断言只做路径等值与目录**不存在**断言，不依赖 `data/`（它被 .gitignore 覆盖，新克隆可能不存在）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import benchmark_relay_shim as shim
from scripts import evaluate_socratic_benchmark as evaluate

REPO_ROOT = Path(__file__).resolve().parents[1]
RELAY_LOG_NAME = "_relay_calls.jsonl"


def _pinned_paths(log_path: Path, history_dir: Path) -> list[str]:
    """把本单全部路径判据收进一个函数：现状下返回空列表，任一漂回旧形态即返回失败原因。

    正向用例直接断言它为空；反向（鉴别力）用例把 LOG_PATH 临时换成修复前的
    `Path(__file__).parent / "data" / ...` 形态再调一次，断言它**必须**报红 ——
    以此证明测试不是恒真断言。
    """
    failures: list[str] = []

    expected_root = REPO_ROOT / "data" / "benchmark_history"

    if log_path.name != RELAY_LOG_NAME:
        failures.append(f"LOG_PATH 文件名漂移：{log_path.name!r} != {RELAY_LOG_NAME!r}")

    if log_path.parent != expected_root:
        failures.append(f"LOG_PATH 未落在仓根观测目录：{log_path.parent} != {expected_root}")

    # 漂回 `Path(__file__).parent` 形态时，落点必然落进 scripts/ 之下。
    scripts_dir = (REPO_ROOT / "scripts").resolve()
    if scripts_dir in log_path.parents:
        failures.append(f"LOG_PATH 又漂回 scripts/ 之下（A5 缺陷形态）：{log_path}")

    if history_dir != expected_root:
        failures.append(f"HISTORY_DIR 与观测目录不同根：{history_dir} != {expected_root}")

    # 两侧必须同根：shim 追加的 jsonl 与 --track-drift 归档要在同一个 benchmark_history/ 里。
    if log_path.parent != history_dir:
        failures.append(f"shim 落点与 evaluate.HISTORY_DIR 不同根：{log_path.parent} != {history_dir}")

    return failures


def test_log_path_resolves_to_repo_root_benchmark_history():
    """LOG_PATH 解析到仓根 data/benchmark_history/_relay_calls.jsonl（s922-09/A5 修复现状）。"""
    assert _pinned_paths(Path(shim.LOG_PATH), Path(evaluate.HISTORY_DIR)) == []
    assert Path(shim.LOG_PATH) == REPO_ROOT / "data" / "benchmark_history" / RELAY_LOG_NAME


def test_log_path_never_lands_under_scripts_dir():
    """落点不得在 scripts/ 之下；且磁盘上确实不存在 scripts/data/（防再漂回的现场证据）。"""
    log_path = Path(shim.LOG_PATH)
    scripts_dir = (REPO_ROOT / "scripts").resolve()
    assert scripts_dir not in log_path.parents
    assert (REPO_ROOT / "scripts" / "data").exists() is False


def test_evaluate_history_dir_shares_the_same_root():
    """shim 的落点父目录 == evaluate_socratic_benchmark.HISTORY_DIR（同一观测根）。"""
    history_dir = Path(evaluate.HISTORY_DIR)
    assert history_dir == REPO_ROOT / "data" / "benchmark_history"
    assert Path(shim.LOG_PATH).parent == history_dir


def test_importing_shim_has_no_side_effects(tmp_path):
    """导入 shim 不建目录、不起服务、不发网络：模块级只有常量与 Handler 类定义。

    `if __name__ == "__main__"` 才 listen；测试里只 import，故服务与 `LOG_PATH.parent.mkdir`
    都不该被触发 —— 这里断言 LOG_PATH 的父目录不是「因为 import 而新出现」的写盘副作用。
    """
    log_path = Path(shim.LOG_PATH)
    expected_root = REPO_ROOT / "data" / "benchmark_history"
    assert log_path.parent == expected_root
    # 本测试文件被 collect 前后，data/ 内容不应被本班改动（零改动自证由 result 用 sha256+mtime_ns 承担）。
    # 这里只守一条：模块级不创建 scripts/data/。
    assert (REPO_ROOT / "scripts" / "data").exists() is False


def test_pinned_assertion_is_discriminating_against_parent_form(monkeypatch):
    """反向用例：若 LOG_PATH 回退为 `Path(__file__).parent` 形态，本文件的判据必须报红。

    做法是把模块属性临时换成修复前的形态再跑同一套判据函数，断言它确实返回失败原因；
    monkeypatch 只改内存里的模块属性，测试结束自动还原，不写生产文件。
    """
    regression_form = Path(shim.__file__).resolve().parent / "data" / "benchmark_history" / RELAY_LOG_NAME
    assert "scripts" in regression_form.parts  # 前提自证：这确实是 A5 的缺陷形态

    monkeypatch.setattr(shim, "LOG_PATH", regression_form)
    failures = _pinned_paths(Path(shim.LOG_PATH), Path(evaluate.HISTORY_DIR))
    assert failures, "判据失去鉴别力：回退到 .parent 形态居然不报红"
    assert any("scripts" in reason for reason in failures)
    assert any("LOG_PATH 未落在仓根观测目录" in reason for reason in failures)


def test_history_dir_mutation_also_turns_red(monkeypatch):
    """反向用例二：evaluate 侧 HISTORY_DIR 若改指别处，同根判据也必须报红。"""
    monkeypatch.setattr(evaluate, "HISTORY_DIR", REPO_ROOT / "data" / "benchmark_history_v2")
    failures = _pinned_paths(Path(shim.LOG_PATH), Path(evaluate.HISTORY_DIR))
    assert failures, "判据对 HISTORY_DIR 漂移无鉴别力"


if __name__ == "__main__":  # pragma: no cover - 便于 `.venv/Scripts/python.exe tests/test_benchmark_relay_paths.py` 自检
    raise SystemExit(pytest.main([__file__, "-q"]))
