# v5.8 升级报告：启动/加载性能优化 + 关键 Bug 修复

**版本**：v5.7 → v5.8
**日期**：2026-08-15
**主题**：启动速度、交互响应速度、反人类设计清除、3 个关键数据加载 Bug

---

## 一句话总结

v5.7 冷启动首屏要等 20~40 秒（启动自检同步 import pingouin/statsmodels/semopy 等重型依赖），
每次点击交互还要在侧栏重算全量工作区快照（大文件下 1~3s/次）。
v5.8 把首屏压到 **~1.3s**（服务器 1.3s + 首帧 1.3s），交互 rerun 压到 **~0.2s**，
并修掉了 Excel 上传必崩、大文件上传必失败两个数据入口级 Bug。

---

## 一、启动性能（P0）

### 1.1 启动自检「免导入」化 — 30s → 740ms

**问题**：`run_startup_check()` / `render_env_health_banner()` 在首次页面加载时
**同步 import** pingouin（冷盘 ~17s）、statsmodels（~4.4s）、semopy（~2.9s）、
scipy/sklearn/openpyxl/kaleido 等，注释写「5 秒自检」实际阻塞 20~30s。

**修复**（`src/utils/env_check.py`）：
- 全部依赖探测改为 `importlib.util.find_spec` + `importlib.metadata.version`
  ——只查「是否安装」，**不执行模块代码**，毫秒级返回，结果文案保持不变。
- `run_deep_environment_check(fast=True)`（默认，启动提示条路径）跳过
  实测 PDF/Word 生成；完整实测仅保留给用户主动点「运行系统诊断」。

**实测**：`run_startup_check` 740ms（含 .env.local 读取）；`run_deep_environment_check(fast)` 2.2ms。

### 1.2 重型依赖后台预热线程

自检不再 import 重型依赖后，用户**第一次点「开始分析」**会撞上懒加载导入。
新增 daemon 预热线程（首帧渲染后启动，不阻塞 UI）：用户在阅读界面/上传数据时，
scipy/statsmodels/pingouin/semopy/sklearn/factor_analyzer/openpyxl/jieba/kaleido
已在后台导入完成，首次分析零额外等待。预热失败静默（真正用到时仍有明确报错）。

### 1.3 桌面启动器 splash 文案与超时校准

`launcher.pyw`：READY_TIMEOUT 120s→90s；进度文案不再声称「重型依赖正在导入」
（v5.8 已后台化），阶段划分对齐真实 3~8s 启动节奏。

### 1.4 启动自检失败不再白屏

`run_startup_check` 包 try/except：任何异常只降级 `env_status=None`，绝不让整个应用白屏。

**端到端实测**（本机）：
| 指标 | v5.7 | v5.8 |
|---|---|---|
| Streamlit 服务器就绪 | ~3s（冷） | **1.34s** |
| 首帧渲染（含自检） | 20~40s（冷）/ ~4.4s（热） | **1.26s** |
| 交互 rerun | 0.3~3s（大文件更糟） | **0.19s** |

---

## 二、交互响应（反人类设计清除）

### 2.1 侧栏工作区快照改为按需生成

**问题**：`build_workspace_snapshot()`（含全量 `df.to_csv` + base64 + 全部会话状态
序列化）此前在**每次 rerun** 都被执行——Streamlit 无条件执行 expander 内容，
大文件下每点一下按钮都要卡 1~3s。

**修复**（`app.py`）：改为「点『导出项目快照』才生成」的两步式：
1. 点击 → spinner 中打包，结果暂存 session_state；
2. 出现「下载快照文件」按钮 + 「丢弃快照」按钮（防止大 JSON 常驻内存）。
日常使用路径（不导出）从此零成本。

### 2.2 系统状态内存估算 TTL 缓存

`get_system_status()`（侧栏设置页）此前每次 rerun 都跑
`DataFrame.memory_usage(deep=True)` 深扫描。加 30s TTL 缓存
（`estimate_session_state_memory(force=True)` 可强制重算），交互路径不再重复扫描。

### 2.3 分析缓存键全表哈希记忆化

每次点「开始分析」都 `hash_pandas_object(df)` 全表哈希；改为按 df 对象 id 记忆化
（数据未换不重算），大表重复分析时省下每次 ~1s。

---

## 三、数据入口 Bug 修复（P0）

### 3.1 Excel 上传必崩（pandas 3.x 回归）

**现象**：任何 .xlsx/.xls 上传都报
`'dict' object has no attribute 'columns'`——pandas 3.x 中 `read_excel(sheet_name=None)`
**永远**返回 {sheet: DataFrame} 字典（单 sheet 也一样），pandas 2.x 行为不同。

**修复**（`src/data/loader.py::load_excel`）：`sheet_name=None` 时显式探测并取第一个
sheet 名称读取；多 sheet 取第一个，`meta["sheet_name"]` 记录实际表名。
新增 4 个回归测试（`tests/test_data_loader.py::TestExcelLoaderPandas3Regression`）。

### 3.2 大文件（>20MB）上传必失败（文件指针被预览消耗）

**现象**：app.py 大文件列预览 `pd.read_csv(file, nrows=0)` 读完后指针停在 EOF，
随后 `load_data` 从 EOF 解析 → 空表 / EmptyDataError。

**修复**（`load_data` 统一入口）：解析前 `seek(0)` 归零（对类文件对象），
覆盖 CSV/Excel/jsPsych/Word/Markdown 全部格式。

### 3.3 其他修复

- **#L5（KNOWN_ISSUES 路线图项）**：`socratic_engine.ask_socratic` /
  `ask_socratic_stream` 的 `llm_config: Dict` 类型 lie 收口——改
  `Optional[Dict]` + None 早返回 fallback，绕过 gate 直调也永不 crash
  （新增 2 个测试）。
- **测试陈旧断言**：`test_grouped_methods_are_sorted_disjoint_and_consistent`
  断言 experimental 组为空，与 method_catalog 现实（18 个 experimental 方法）不符，
  改为校验三组排序/互斥/一致性。

---

## 四、测试基线

| 项目 | 数量 |
|---|---|
| 新增测试 | +12（env_check 免导入 6 / socratic None 2 / loader 回归 4；修正陈旧断言 1）|
| 全量回归 | **2437 passed, 59 skipped**（0 失败，237.6s），日志见 `logs/pytest_final.log` |

新增文件：
- `tests/test_env_check.py` — 启动自检「不 import 重型依赖」性能回归护栏
- `UPGRADE_REPORT_V5.8.md`（本文）

修改文件：
- `src/utils/env_check.py` / `src/utils/memory_manager.py`
- `src/data/loader.py` / `src/upstream/socratic_engine.py`
- `app.py` / `launcher.pyw`
- `tests/test_data_loader.py` / `tests/test_upstream_socratic.py`
  / `tests/test_method_exposure.py`

---

## 五、留给 v5.9 的事

1. `analysis_output` / `df` 仍整对象存 session_state（Streamlit 每次 rerun
   向浏览器序列化）；大数据集（>50MB）可进一步改为 cache_resource + 会话 token 方案。
2. 深度环境检查（PDF/Word 实测）与「运行系统诊断」按钮合并入口，减少重复代码。
3. KNOWN_ISSUES 中 #L2（F1 论文写作双入口）、#L4（SELF_ASSESSMENT_REPORT 过期）继续跟踪。
