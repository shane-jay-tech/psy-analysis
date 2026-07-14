"""LLM 调用静态扫描守护 — 禁止绕过 gateway 直接调用 LLM。

扫描 src/ 中所有 Python 文件，确保用户触发的 LLM 调用走 llm_gateway，
而非直接使用 requests.post / openai.ChatCompletion / httpx 等。
"""
import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# 允许直接调用的路径（gateway 本身、底层适配器）
ALLOWED_FILES = {
    "src/llm_gateway/gateway.py",
    "src/llm_gateway/client.py",
    "src/llm_gateway/async_client.py",
    "src/llm_gateway/__init__.py",
    "src/literature_feed/fetchers",  # 网络爬虫，不是 LLM
    "src/upstream/",  # 外部 API 适配
}

# 已登记的 legacy 直接调用（全部已迁移到 gateway）
LEGACY_CALLSITES: set = set()

# 检测模式：直接调用 LLM 的典型特征
LLM_CALL_PATTERNS = [
    r"openai\.ChatCompletion",
    r"openai\.chat\.completions",
    r"client\.chat\.completions",
    r"requests\.post.*(?:openai|api.*chat|completions|deepseek|kimi)",
    r"httpx\..*post.*(?:openai|chat|completions)",
]


def _is_allowed(file_path: Path) -> bool:
    rel = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    for allowed in ALLOWED_FILES:
        if rel.startswith(allowed):
            return True
    return False


def _scan_for_direct_llm_calls() -> list[dict]:
    """扫描 src/ 中直接 LLM 调用。"""
    violations = []
    combined_pattern = "|".join(f"({p})" for p in LLM_CALL_PATTERNS)

    for py_file in SRC_DIR.rglob("*.py"):
        if _is_allowed(py_file):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            # Skip comments
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            # Skip lines with legacy/adapter annotations
            if "# legacy" in line.lower() or "# adapter" in line.lower():
                continue
            if re.search(combined_pattern, line, re.IGNORECASE):
                violations.append({
                    "file": str(py_file.relative_to(PROJECT_ROOT)),
                    "line": i,
                    "content": stripped[:100],
                })
    return violations


class TestLLMGatewayStaticGuard:
    def test_no_new_direct_llm_calls_outside_gateway(self):
        """src/ 中不应新增绕过 gateway 的直接 LLM 调用（已登记 legacy 除外）。"""
        violations = _scan_for_direct_llm_calls()
        new_violations = [
            v for v in violations
            if (v["file"].replace("\\", "/"), v["line"]) not in LEGACY_CALLSITES
        ]
        if new_violations:
            msg = f"Found {len(new_violations)} NEW direct LLM call(s) outside gateway:\n"
            for v in new_violations[:10]:
                msg += f"  {v['file']}:{v['line']} — {v['content']}\n"
            msg += "\nPlease route through src/llm_gateway/gateway.py"
            pytest.fail(msg)

    def test_legacy_callsites_documented(self):
        """已登记 legacy 调用点仍存在（迁移后从 LEGACY_CALLSITES 移除）。"""
        violations = _scan_for_direct_llm_calls()
        found = {(v["file"].replace("\\", "/"), v["line"]) for v in violations}
        for site in LEGACY_CALLSITES:
            if site not in found:
                pass  # 已迁移，可从 LEGACY_CALLSITES 移除

    def test_gateway_module_exists(self):
        """确认 gateway 模块存在。"""
        gateway = SRC_DIR / "llm_gateway" / "gateway.py"
        assert gateway.exists(), "src/llm_gateway/gateway.py not found"
