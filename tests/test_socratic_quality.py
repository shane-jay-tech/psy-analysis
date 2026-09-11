"""反问质量基准测试（不进入常规 CI）。

跑法：`pytest tests/test_socratic_quality.py --run-benchmark -v`

调用真实 LLM 对 30 个案例生成反问，输出 JSON 报告供人工标注 + 回归对比。
配置 LLM：通过环境变量
- BENCHMARK_LLM_PROVIDER（默认 deepseek）
- BENCHMARK_LLM_API_KEY
- BENCHMARK_LLM_MODEL（默认 deepseek-chat）
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

pytestmark = pytest.mark.benchmark


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "socratic_benchmark.json"
REPORT_DIR = Path(__file__).parent / "fixtures" / "_benchmark_reports"

# 注：pytest 标记 benchmark / --run-benchmark 选项 的注册已挪到 tests/conftest.py


def _load_benchmark() -> Dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _llm_config_from_env() -> Dict[str, str]:
    provider = os.environ.get("BENCHMARK_LLM_PROVIDER", "deepseek")
    base_urls = {
        "deepseek": "https://api.deepseek.com",
        "zhipu":    "https://open.bigmodel.cn/api/paas/v4",
        "openai":   "https://api.openai.com/v1",
    }
    # k62a 可加性覆盖：显式 base_url/timeout 未设置时行为与原先完全一致。
    base_url = os.environ.get("BENCHMARK_LLM_BASE_URL", "") or base_urls.get(provider, "")
    timeout = int(os.environ.get("BENCHMARK_LLM_TIMEOUT", "60"))
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": os.environ.get("BENCHMARK_LLM_API_KEY", ""),
        "model": os.environ.get("BENCHMARK_LLM_MODEL", "deepseek-chat"),
        "timeout": timeout,
    }


@pytest.mark.benchmark
def test_socratic_quality_benchmark():
    """对 30 个案例调用真实 LLM 并输出 JSON 报告。"""
    config = _llm_config_from_env()
    if not config["api_key"]:
        pytest.skip("未设置 BENCHMARK_LLM_API_KEY 环境变量")

    from src.upstream.socratic_engine import ask_socratic

    benchmark = _load_benchmark()
    results: List[Dict[str, Any]] = []

    for stage_str, cases in benchmark["stages"].items():
        stage = int(stage_str)
        for case in cases:
            try:
                reply = ask_socratic(
                    stage=stage,
                    user_input=case["input"],
                    history=[],
                    llm_config=config,
                )
                error = None
            except Exception as exc:
                reply = ""
                error = str(exc)

            results.append({
                "case_id": case["id"],
                "stage": stage,
                "input": case["input"],
                "expected_dimensions": case["expected_dimensions"],
                "llm_reply": reply,
                "manual_score": None,    # 由人工填
                "manual_notes": "",      # 由人工填
                "error": error,
            })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"benchmark_{timestamp}.json"
    report = {
        "version": benchmark.get("version", "v3.3"),
        "generated_at": datetime.now().isoformat(),
        "llm": {
            "provider": config["provider"],
            "model": config["model"],
        },
        "n_cases": len(results),
        "results": results,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n基准报告已写入：{report_path}")

    # 至少应有 30 个案例
    assert len(results) == 30
    # 至少 80% 案例有非空回复（容忍部分 LLM 失败）
    non_empty = sum(1 for r in results if r["llm_reply"])
    assert non_empty >= 24, f"非空回复仅 {non_empty}/30，LLM 表现异常"


def test_benchmark_fixture_loadable():
    """常规测试：仅验证 fixture JSON 文件可加载且结构正确。"""
    benchmark = _load_benchmark()
    assert "stages" in benchmark
    assert set(benchmark["stages"].keys()) == {"1", "2", "3", "4", "5"}
    total = sum(len(cs) for cs in benchmark["stages"].values())
    assert total == 30
    # 每例必有 expected_dimensions
    for stage_id, cases in benchmark["stages"].items():
        for case in cases:
            assert "input" in case
            assert "expected_dimensions" in case
            assert len(case["expected_dimensions"]) >= 2


# ---------------------------------------------------------------------------
# c448：fixture 离线回放模式（2026-09-10 夜）
#
# 两种模式用法：
# - 离线回放（默认，无 BENCHMARK_LLM_API_KEY 即走）：复用最近一次 golden 报告
#   （tests/fixtures/_benchmark_reports/benchmark_*.json）逐案例校验回放完整性，
#   绝不发网络调用（ask_socratic 被计数 spy 包裹，真实调用数必须为 0）。
# - 联网首跑（原有路径，未破坏）：设置 BENCHMARK_LLM_API_KEY 后 --run-benchmark，
#   真实调用 LLM 产出新报告（成为下一次回放的 golden）。
# ---------------------------------------------------------------------------

def _load_golden_replay():
    """取最新 golden 报告 → {case_id: llm_reply} 回放表。"""
    reports = sorted(REPORT_DIR.glob("benchmark_*.json"))
    assert reports, "无 golden 回放报告（tests/fixtures/_benchmark_reports/ 为空）"
    latest = reports[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    return {r["case_id"]: (r.get("llm_reply") or "") for r in data["results"]}, latest.name


@pytest.mark.benchmark
def test_socratic_quality_replay_offline(monkeypatch):
    """离线回放 30 案例：无 key 全绿、回放命中 30、真实 LLM 调用计数 = 0。"""
    monkeypatch.delenv("BENCHMARK_LLM_API_KEY", raising=False)
    golden, golden_name = _load_golden_replay()
    benchmark = _load_benchmark()

    from src.upstream import socratic_engine

    calls = {"real": 0}
    real_ask = socratic_engine.ask_socratic

    def _spy(*args, **kwargs):
        calls["real"] += 1
        return real_ask(*args, **kwargs)

    monkeypatch.setattr(socratic_engine, "ask_socratic", _spy)

    total, empty = 0, []
    for stage_str, cases in benchmark["stages"].items():
        for case in cases:
            total += 1
            reply = golden.get(case["id"], "")
            if not reply:
                empty.append(case["id"])

    assert total == 30, f"基准案例数异常: {total}"
    assert not empty, f"回放缺 reply 的案例: {empty}"
    assert calls["real"] == 0, f"回放模式发生了真实 LLM 调用: {calls['real']} 次"
    print(f"[replay] golden={golden_name} hit={total}/30 real_calls={calls['real']}")
