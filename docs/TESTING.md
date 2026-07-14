# 测试体系说明

## 测试层级

| 标记 | 含义 | 运行时机 |
|------|------|----------|
| (无标记) | 纯单元测试 | 每次改动后 |
| `integration` | 模块间协作测试 | 日常 |
| `ui` | Streamlit 渲染相关 | 改 UI 时 |
| `e2e` | Playwright 浏览器端到端 | 发版前 |
| `online` | 需要外部网络（Crossref 等） | 月度检查 |
| `benchmark` | LLM 漂移基准 | 月度/季度 |

## 日常开发命令

```powershell
# 快速离线测试（推荐日常使用）
.\.venv\Scripts\python.exe -m pytest -m "not online and not e2e and not benchmark" -q

# 只跑某个文件
.\.venv\Scripts\python.exe -m pytest tests/test_xxx.py -v

# UI 相关改动后
.\.venv\Scripts\python.exe -m pytest -m "ui" -v
```

## 发版前命令

```powershell
# 全量离线测试（含集成）
.\.venv\Scripts\python.exe -m pytest -m "not online and not benchmark"

# 性能 smoke（检查性能退化）
.\.venv\Scripts\python.exe scripts/perf_smoke.py

# 性能 smoke JSON 模式（CI 用，可 json.loads 解析）
.\.venv\Scripts\python.exe scripts/perf_smoke.py --json

# 系统指标报告（确认版本号、代码量一致）
.\.venv\Scripts\python.exe scripts/generate_system_report.py --format markdown --collect-pytest
```

## 月度联网检查

```powershell
# 检查文献源（Crossref 等）是否可达
.\.venv\Scripts\python.exe -m pytest -m online -v
```

## 关键守护测试

以下三组测试是核心闭环守护，每次改动后建议运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_llm_cancel.py tests/test_recent_datasets.py tests/test_export_naming_global.py tests/test_literature_review_service.py tests/test_paper_draft_bundle.py -q
```

## Playwright E2E 测试

浏览器端到端测试使用 Playwright，验证真实用户流程。

### 安装

```powershell
# 安装 Python 包
.\.venv\Scripts\pip.exe install playwright pytest-playwright

# 安装浏览器（仅需 Chromium）
.\.venv\Scripts\playwright.exe install chromium
```

### 运行

```powershell
# 黄金路径（使用 demo 项目数据，无需网络和 API key）
.\.venv\Scripts\python.exe -m pytest tests/test_playwright_golden_research_flow.py -m e2e -v

# 完整 E2E（含更多路径覆盖）
.\.venv\Scripts\python.exe -m pytest tests/test_playwright_e2e.py -m e2e -v

# 所有 E2E
.\.venv\Scripts\python.exe -m pytest -m e2e -v
```

### 失败诊断

- 失败截图保存于 `test_artifacts/screenshots/`
- 失败 trace 保存于 `test_artifacts/traces/`
- 用 Playwright Trace Viewer 打开 trace：`npx playwright show-trace test_artifacts/traces/test_xxx.zip`

### 注意事项

- E2E 使用端口 8502（黄金路径）或 8501（完整路径），避免与开发服务器冲突
- 测试自动启动和关闭 Streamlit 服务器
- `test_artifacts/` 目录已加入 `.gitignore`

---

## 常见失败处理

| 失败情况 | 解法 |
|---------|------|
| `import error` 类测试失败 | 运行 `.venv/Scripts/pip install -e .` 或检查依赖 |
| `online` 标记测试超时 | 检查网络连接，Crossref 可能限流 |
| `perf_smoke` 显示 WARN | 非错误，只是超阈值提醒；FAIL 才需要排查 |
| pytest 收集报错 | 运行 `pytest --collect-only` 查看哪个文件语法错 |
| `test_export_naming` 失败 | 检查新加的 `st.download_button` 是否用了 `export_filename()` |
