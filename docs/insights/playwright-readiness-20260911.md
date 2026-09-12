# psy Playwright 离线就绪盘点 + 日间执行清单（2026-09-12 夜间执行班，任务 p911r-36）

> 执行：GLM-5.3-Flash 夜间执行班 sweep-20260911-2300。**本单零安装、零联网、零删除**（只读盘点）。

## 一、跳过点定位（文件:行号）

| 文件:行号 | 机制 | 覆盖测试数 |
|---|---|---|
| `tests/test_e2e_v52_paths.py:23-36` | `_playwright_available()` ImportError → `pytest.mark.skipif(not _playwright_available())` + `pytest.mark.playwright/e2e` | 12 |
| `tests/test_playwright_golden_research_flow.py:450` | `@pytest.mark.skipif(not E2E_AVAILABLE, reason="Playwright not installed")` | 28 |
| `tests/test_playwright_e2e.py:22`（`pytestmark=pytest.mark.e2e`）+ 同类 skipif | 11 | |
| `tests/test_e2e_rendering.py` / `test_e2e_ui.py` | 同族 | 15 / 6 |
| `tests/conftest.py:24-25` | `_APP_TEST_FILES` 隔离 fixture 集合（非 skip，但 e2e 文件命中隔离存储） | — |

**合计 72 个 def test 分布在 5 个 e2e/playwright 文件**（KNOWN_ISSUES.md:103 记「25 项明确跳过」为历史口径，现收集面更大）。

## 二、环境实测（命令 + 原始输出）

| 检查 | 命令 | 结果 |
|---|---|---|
| .venv playwright 包 | `pip show playwright` | **WARNING: Package(s) not found** ❌ |
| 浏览器缓存 | `ls ~/AppData/Local/ms-playwright` | ✅ **chromium-1234 / chromium_headless_shell-1234 / ffmpeg-1011 均在，含 INSTALLATION_COMPLETE 标记，共 703MB** |
| wheel 离线缓存 | pip cache 目录 + 全仓 *.whl | 未发现 playwright wheel ❌ |

**关键发现：浏览器二进制已就位（703MB，免下载），缺的只是 .venv 里的 playwright Python 包；且 pip cache 无 wheel → 联网安装不可避免**（安装需网络，属日间授权动作）。

## 三、日间执行清单（≥3 步，每步含校验）

1. **安装包**：`.\.venv\Scripts\pip install playwright`（联网，~2MB 纯包；浏览器已免装——若安装器要求 `playwright install`，先跑 `playwright install --dry-run` 确认 chromium-1234 版本匹配，不匹配才补下载）。校验：`pip show playwright` 出现 Version。
2. **连通性校验**：`.\.venv\Scripts\python -c "from playwright.sync_api import sync_playwright"` 退出码 0；再 `playwright install chromium` 确认输出「already installed」。
3. **跑 e2e 子集**：先启 app（`streamlit run app.py`）或确认测试自带 fixture，再 `.\.venv\Scripts\python -m pytest tests/test_e2e_v52_paths.py -v`。期望输出：12 项由 skipped 转为 passed/failed 实跑；**失败判定**：任何 ERROR（非 FAIL）= 环境/路径问题先修，FAIL 才是断言问题。
4. **全量回归**：`pytest tests/test_playwright_e2e.py tests/test_playwright_golden_research_flow.py tests/test_e2e_rendering.py tests/test_e2e_ui.py tests/test_e2e_v52_paths.py -v`，期望 72 项实跑；同时更新 `KNOWN_ISSUES.md:103` 该行为「已安装+实跑结果」。
5. **收尾**：把 `pip show playwright` 版本号记入 KNOWN_ISSUES（便于回滚=卸载包；浏览器缓存保留无害）。

## 四、零安装零联网声明

全程只读（pip show/ls/find/collect-only）；未执行任何 install；未 commit/push。
