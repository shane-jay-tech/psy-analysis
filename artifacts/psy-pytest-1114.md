# psy-analysis 全量 pytest 实录（2026-11-14）

- 口径：docs/TESTING.md 权威命令 `cd D:\code\psy-analysis && .venv\Scripts\python.exe -m pytest -q`
- 解释器：`.venv` Python 3.12.9（streamlit 1.59.1 / playwright 1.64.1 / kaleido 1.3.0 / pytest 9.1.1）
- 日志：`tmp/s1114/baseline-full.log`（657.48s，约 11 分钟）

## 基线（任务 2 实录，HEAD=b0c3b27，2026-11-14）

**14 failed / 5725 passed / 6 skipped / 28 xfailed / 33 errors（73 warnings）**

> 与任务书所述 5736P/3F/33E（commit 8f4606b 时代读数）对比：F 侧 3→14。
> 差异主因是图形导出族 10 名——kaleido 装后走"真渲染"路径，但 kaleido 1.x 运行时
> 还需要 Chrome/Chromium 二进制（本机无系统 Chrome），渲染失败 ⇒ 10F 回红。
> 这正是 s-env-reds.md §3.1 预警的"装 kaleido 后需重验导出族与降级分叉"。

### 14F 逐名（按家族分组）

| 家族 | 名单 | 归因 |
|---|---|---|
| 图形导出真渲染（8F） | test_fig_to_image_runtime_s93010 ×2（png/svg）、test_figure_export_degradation_keeps_statistics ×4（dependency_path 渲染族）、test_docx_export::test_plotly_figs_to_figure_items_smoke、test_export_all_figures_zip_smoke_s1004_08::test_zip_smoke_members_and_openable | A 型：kaleido 1.3.0 已装但缺 Chrome 运行时（choreographer 报 populate_targets/open 失败）；`_find_local_chromium()` 探测返回 None——本机无系统 Chrome，且探测候选不含 PLAYWRIGHT_BROWSERS_PATH（本机浏览器在 D:\ms-playwright） |
| 论文导出 zip（2F） | test_paper_export::test_to_paper_png_smoke、test_paper_export::test_export_zip_smoke | 同上（PNG 渲染链同根） |
| v52 zip 表（2F） | test_e2e_v52_paths::TestV52ZipStructure::test_zip_contains_tables_directory、::test_zip_tables_have_csv_and_md | 待查（zip 内 0 表） |
| 能力门失配（1F） | test_skip_gates...::test_capability_gate_agrees_with_independent_probe[kaleido] | A 型变体：门判"已装"（import ok）与独立探针（真渲染）不一致——浏览器运行时缺失所致 |
| 文献源探针（1F） | test_seed_literature_sources::test_probe_reports_failure_per_source_without_raising | C 型（s-env-reds 遗留：monkeypatch 入口 dr.build_fetcher 脱钩） |

### 33E 逐名（按家族分组）

| 家族 | 名单 | 归因 |
|---|---|---|
| 黄金流浏览器（13E） | test_playwright_golden_research_flow.py::TestBrowserGoldenPath 全部 13 名（setup 阶段 browser fixture 报 Executable doesn't exist） | A 型：playwright 1.64.1 需要 chromium_headless_shell-1248，D:\ms-playwright 只有 1234 版（旧 playwright 装的） |
| playwright_e2e（11E） | test_playwright_e2e.py 全部 11 名（setup 阶段同类报错） | 同上 |
| v52 浏览器（9E） | test_e2e_v52_paths.py 9 名（setup 阶段同类报错） | 同上 |

### 潜伏缺陷（浏览器装好后将显形）

- B3（s-env-reds 遗留）：`pytest_runtest_makereport` 钩子定义在测试模块内
  （tests/test_playwright_golden_research_flow.py:431），pytest 不从测试模块注册钩子 ⇒
  `request.node.rep_call` 永不落位 ⇒ page fixture teardown AttributeError。
  当前因浏览器缺失在 setup 就炸而未显形；浏览器补装后 13 名黄金流将转为 teardown ERROR。

## 清零战役结果（任务 3，完成后追加）

（待追加）
