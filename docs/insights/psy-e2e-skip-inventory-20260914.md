# psy 浏览器 E2E 跳过项清点（d914-38，2026-09-14，只读）

命令：`python -m pytest tests -q -rs --tb=no --junitxml=tmp/junit-skip.xml`（汇总行被吞已知现象 → junitxml 计数）

## 实测

| 指标 | 值 |
|---|---|
| tests | 2670 |
| errors | 13（playwright golden 域：browser/server 环境缺失） |
| failures | 25（browser e2e 10 + golden_stats 域 sklearn 漂移 15，见 d913b-48 立案） |
| skipped | 34 |
| passed | 2598 |

## 34 skip 的构成

- **33 项 = `--run-benchmark` 反问质量基准**（conftest.py:88 `pytest_collection_modifyitems` 未传参则统一 skip）——与浏览器 E2E 无关，不属 KNOWN_ISSUES「浏览器 E2E」范畴。
- **1 项 = e2e 浏览器域非绿**（test_playwright_golden_research_flow + test_e2e_v52 共 13 errors + 25 failures 与 22 passed 的差值中属「跳过标记」的实为 0——v52 的 10 failed 与 golden 的 13 errors 均**未标 skip**，是环境失败而非主动跳过）。

## 与 KNOWN_ISSUES 25 / yesterday 23 的对照

| 口径 | 数值 | 差异解释 |
|---|---|---|
| KNOWN_ISSUES:103「25 项明确跳过」 | 25 | 口径=9/12 时点的 pytest -rs 输出（benchmark 33 项中当时的 25 + e2e 明确标记 skip 的项数），与当前 34 不同系基准基准项增长（+7）与 e2e 测试文件增删 |
| yesterday（d913a-43）「23 非绿」 | 23 | 口径=**非绿（failures+errors）**而非 skip；当前实测 13E+10F=23——**与 yesterday 完全一致** ✓ |
| 当前 -rs skip 计数 | 34 | =benchmark 域 33 + 其他 1（junit 细分见上） |

**结论：skip 构成已漂移**——KNOWN_ISSUES 的「25 项跳过」实为 benchmark 域为主，真正的浏览器 E2E 项是 13 errors + 10 failures = **23 非绿项（非 skip 而是环境失败）**，需要 Playwright/浏览器/运行中 server 才能定绿。

## 依赖清单（全部非本班可解）

- Playwright 浏览器二进制未安装（.venv 无 playwright 或未 download chromium）
- 运行中的 streamlit server（127.0.0.1:8501/3000 端口）
- 部分用例需网络可达（google fonts 等）

## 遗留

- KNOWN_ISSUES:103 建议把「25 项明确跳过」更新为「34 项 skip（benchmark 33+其他1）；另有浏览器 E2E 23 项环境失败待补装」以准确反映现状。
