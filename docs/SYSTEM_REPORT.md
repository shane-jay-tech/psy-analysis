# Psy-Analysis 系统报告

**版本**: v5.7.0  
**日期**: 2026-07-05  
**用途**: 个人心理学论文统计分析辅助工具

---

## 1. 系统概况

Psy-Analysis 是一个基于 Streamlit 的本地统计分析工具，面向心理学论文写作。核心能力：数据上传 → 方法推荐 → 统计执行 → APA 表格/图表 → Word/ZIP 交付包。

### 规模

| 指标 | 数值 |
|------|------|
| 源码文件 | 228 个 .py |
| 源码行数 | ~81,800 行 |
| 测试文件 | 150 个 .py |
| 测试用例 | 2313 个（全部通过） |
| 文档 | 8 个（精简后） |
| 注册统计方法 | 48 个 |
| 规范方法 ID | 35 个 |
| APA 表格路由组 | 21 个 |
| 论文模板 | 6 个 |

---

## 2. 核心模块架构

### 2.1 统计分析引擎 (`src/analysis/`)

| 文件 | 行数 | 职责 |
|------|------|------|
| `runner.py` | 1074 | 统一分析入口，48 个注册方法 + 分派 |
| `method_ids.py` | 93 | 方法 ID 规范映射（单一事实源） |
| `advanced.py` | 507 | 中介/调节/ANCOVA 分析 |
| `ttest.py` | — | 独立/配对/单样本 t 检验 |
| `anova.py` | — | 单因素/双因素/重复测量方差分析 |
| `nonparametric.py` | — | Mann-Whitney/Wilcoxon/Kruskal-Wallis/Friedman |
| `chi_square.py` | — | 卡方独立性/拟合优度检验 |
| `logistic_regression.py` | — | 二元/有序/多项 Logistic |
| `regression.py` | — | 多元/层次/线性回归 |
| `reliability.py` | — | Cronbach's α / McDonald's ω |
| `result_card.py` | — | 结构化结果卡片生成器 |
| `method_recommender.py` | — | 根据研究设计推荐方法 |
| `assumption_router.py` | — | 前提假设不满足时的替代方案路由 |
| `post_hoc_power.py` | — | 事后统计效力计算 |

### 2.2 输出层 (`src/output/`)

| 文件 | 行数 | 职责 |
|------|------|------|
| `apa_tables.py` | 875 | APA 格式三线表自动生成（21 路由组） |
| `apa_figures.py` | — | 11 种 APA 图表 |
| `docx_exporter.py` | 1247 | Word 导出（三线表 + APA 格式） |
| `zip_exporter.py` | 280 | ZIP 交付包生成 |
| `reasoning.py` | — | 结果解释生成 |

**APA 表格自动生成支持的方法：**

| 表格函数 | 覆盖方法 |
|----------|---------|
| `descriptive_stats_table()` | 描述统计 |
| `correlation_matrix_table()` | Pearson/Spearman 相关 |
| `ttest_result_table()` | 独立/配对/单样本 t 检验 |
| `nonparametric_result_table()` | Mann-Whitney/Wilcoxon/Kruskal-Wallis |
| `chi_square_result_table()` | 卡方检验（独立性/拟合优度） |
| `anova_result_table()` | 单因素/双因素/重复测量/混合方差分析 |
| `regression_result_table()` | 多元/层次/线性回归 |
| `reliability_table()` | Cronbach's α / McDonald's ω |
| `factor_loading_table()` | EFA 因子载荷 |
| `model_fit_table()` | CFA/SEM 模型拟合 |
| `hlm_result_table()` | HLM 固定效应 + 随机效应 |
| `mediation_result_table()` | 中介路径系数 + Bootstrap CI |
| `moderation_result_table()` | 调节回归系数 + 简单斜率 |
| `logistic_result_table()` | Logistic B/SE/Wald/OR/CI |

### 2.3 模板系统 (`project_templates/`)

6 个内置模板覆盖常见本科论文设计：

| 模板目录 | 研究类型 | 典型方法 |
|----------|---------|---------|
| `questionnaire_correlation` | 问卷相关 | Pearson 相关、描述统计 |
| `independent_group_comparison` | 组间比较 | 独立样本 t、Mann-Whitney |
| `pre_post_experiment` | 前后测 | 配对 t、Wilcoxon |
| `mediation_questionnaire` | 中介分析 | Bootstrap 中介 |
| `moderation_questionnaire` | 调节分析 | 层次回归交互项 |
| `scale_validation` | 信效度 | Cronbach α、EFA、CFA |

每个模板包含 `data.csv`（模拟数据）+ `config.json`（变量角色/方法配置）。

### 2.4 论文写作辅助 (`src/paper_writer/`)

- **draft_bundle.py**: 统一论文交付对象（PaperDraftBundle → Word/ZIP）
- **section_writers.py**: 方法段、结果段 APA 模板生成
- **ai_tutor.py**: Socratic 教学式辅导（需 API Key）
- **literature_library.py**: 方法参考文献库
- **defense_qa_kb.py**: 答辩问答知识库

### 2.5 UI 层 (`src/ui/`)

| 文件 | 行数 | 职责 |
|------|------|------|
| `undergrad_wizard.py` | 3688 | 本科论文向导（主交互入口） |
| `template_center_panel.py` | — | 模板中心面板 |
| `project_panel.py` | — | 项目状态和下一步推荐 |
| `quick_entries.py` | — | 快捷入口（相关分析、t 检验等） |
| `renderers.py` | — | 结果卡片渲染 |

### 2.6 工具层 (`src/utils/`)

| 文件 | 职责 |
|------|------|
| `method_exposure.py` | 方法暴露分级（default/advanced/experimental） |
| `usage_logger.py` | 使用事件记录（本地 JSONL，可关闭） |
| `usage_hooks.py` | 12 类事件埋点 |
| `professional_consistency.py` | 22 项一致性检查 |
| `privacy_precheck.py` | 导出前敏感信息扫描 |
| `environment_diagnosis.py` | 环境自检 |

---

## 3. 方法覆盖

### 3.1 Default 级（23 个，完整交付链）

完整交付 = 分析执行 → 结果卡片 → APA 表格 → APA 图表 → Word/ZIP

| 类别 | 方法 |
|------|------|
| 相关分析 | `pearson_corr`, `spearman_corr` |
| t 检验 | `independent_ttest`, `paired_ttest`, `one_sample_ttest` |
| 方差分析 | `one_way_anova`, `two_way_anova`, `factorial_anova`, `repeated_measures_anova` |
| 非参数检验 | `mann_whitney`, `wilcoxon`, `kruskal_wallis` |
| 卡方检验 | `chi_square` |
| 回归 | `multiple_regression`, `hierarchical_regression` |
| 信度 | `cronbach_alpha`, `mcdonalds_omega` |
| 描述统计 | `descriptive` |

### 3.2 Advanced 级（21 个，有卡片 + 大部分有表格）

| 方法 | APA 表格 |
|------|---------|
| `mediation` | 路径系数表 + Bootstrap CI 表 |
| `moderation` | 回归系数表 + 简单斜率表 |
| `logistic_regression` | B/SE/Wald/OR/CI 表 |
| `efa` | 因子载荷表 |
| `cfa`, `sem` | 模型拟合指标表 |
| `hlm`, `mixed_effects` | 固定效应 + 随机效应表 |
| `ave_cr`, `discriminant_validity` | 无自动表格 |
| `partial_corr` | 无自动表格 |
| `ancova` | 无自动表格 |
| `mixed_anova` | 有 ANOVA 表 |

### 3.3 Experimental 级

未注册结果卡片的方法，输出为原始格式。

---

## 4. 方法 ID 体系

### 单一事实源：`src/analysis/method_ids.py`

- **35 个规范 ID**（canonical），所有别名映射到此
- **`resolve_method_id(raw_id)`**：任意方法名 → 规范 ID
- **`get_table_route_group(method_id)`**：查询表格路由归属
- **21 个表格路由组**：确保路由查找无歧义

示例解析：
```
pearson_correlation → pearson_corr
independent_t_test → independent_ttest
chi_square_test → chi_square
rm_anova → repeated_measures_anova
```

### 方法暴露分级：`src/utils/method_exposure.py`

| 级别 | 含义 | 数量 |
|------|------|------|
| default | 新手默认推荐，完整交付链 | 23 |
| advanced | 有结果卡片，部分有表格 | 21 |
| experimental | 基础支持，需手动整理 | 余量 |

---

## 5. 测试体系

```
总用例:      2313
通过率:      100%
跳过:        59（可选依赖如 semopy 未装时）
测试耗时:    ~137 秒
```

### 关键测试类别

| 测试文件 | 覆盖范围 | 用例数 |
|----------|---------|--------|
| `test_golden_stats.py` | 21 个数据集验证统计正确性 | 40 |
| `test_golden_stats_v2.py` | 扩展金标准覆盖 | — |
| `test_template_golden_flows.py` | 6 个模板完整分析链 | — |
| `test_golden_delivery.py` | ZIP 输出格式验证 | — |
| `test_method_id_consistency.py` | 方法 ID 漂移防护 | 9 |
| `test_apa_tables.py` | 表格格式正确性 | 16 |
| `test_apa_figures_v2.py` | 图表格式正确性 | — |
| `test_ui.py` | 核心 UI 交互路径 | — |

---

## 6. 质量自检

```bash
python scripts/release_gate.py              # 快速模式（5 项，~2 分钟）
python scripts/release_gate.py --mode full  # 完整模式（9 项，~4 分钟）
```

### 快速模式（日常用）

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | 单元+集成测试 | 2313 用例全过 |
| 2 | ZIP 导出 | 交付包正常生成 |
| 3 | Word 导出 | docx 正常生成 |
| 4 | 金标准统计 | 21 个数据集结果正确 |
| 5 | 模板完整性 | 6 个模板各含 data.csv |

### 完整模式（交付前 / 换电脑后）

| # | 额外检查项 | 说明 |
|---|-----------|------|
| 6 | Method ID 一致性 | 9 项防漂移测试 |
| 7 | 模板 Golden Flow | 6 个模板完整分析链 |
| 8 | 交付包结构 | ZIP 文件列表验证 |
| 9 | APA 表格 | 16 项格式正确性 |

---

## 7. 交付包结构

### ZIP 交付包内容

```
delivery_package.zip
├── paper.md                       # 论文草稿（Markdown）
├── paper.docx                     # 论文草稿（Word）
├── analysis_cards/                # 结构化结果卡片 JSON
├── tables/                        # APA 三线表（CSV + Markdown）
│   ├── table_001_tbl_*.csv
│   └── table_001_tbl_*.md
├── figures/                       # APA 图表（PNG）
├── manifest.json                  # 包清单（版本、方法、时间戳）
├── AI_USAGE_DISCLOSURE.md         # AI 使用声明
├── PRIVACY_PRECHECK_SUMMARY.md    # 隐私预检报告
└── REPRODUCIBILITY_MANIFEST.md    # 可复现清单
```

### Word 导出

- APA 格式三线表自动嵌入
- 结果段落模板
- 统计值正确格式化（斜体统计符号、精确 p 值）

---

## 8. 安装与使用

### 一键安装

```bash
双击 install.bat
```

5 步自动完成：检查 Python → 创建 .venv → 安装依赖 → 验证核心模块 → 检查可选模块。

失败时自动写 `logs/install_diagnosis.txt`。

### 一键启动

```bash
双击 run.bat
```

自动处理：端口清理 → 虚拟环境激活 → Streamlit 启动 → 等待就绪 → 打开浏览器。

启动失败时自动写 `logs/startup_diagnosis.txt`（含 Python 版本、端口状态、错误日志）。

### 环境要求

| 依赖 | 要求 | 缺失时 |
|------|------|--------|
| Python | 3.10+ | 安装提示 |
| pip | 最新版 | 自动升级 |
| streamlit | 必需 | install.bat 安装 |
| pandas/scipy/statsmodels | 必需 | install.bat 安装 |
| semopy | 可选 | SEM/CFA 不可用 |
| factor_analyzer | 可选 | EFA 不可用 |
| LLM API Key | 可选 | AI 功能不可用，统计正常 |
| Word/LibreOffice | 不需要 | python-docx 独立生成 |

---

## 9. 实用脚本

| 脚本 | 用途 | 用法 |
|------|------|------|
| `release_gate.py` | 质量自检（fast/full） | `python scripts/release_gate.py [--mode full]` |
| `analyze_usage_logs.py` | 使用日志分析 | `python scripts/analyze_usage_logs.py --days 30` |
| `generate_system_report.py` | 生成系统报告 | `python scripts/generate_system_report.py` |
| `perf_smoke.py` | 性能基准 | `python scripts/perf_smoke.py` |

---

## 10. 数据安全与隐私

| 策略 | 实现 |
|------|------|
| 数据本地存储 | 不自动上传任何数据 |
| AI 功能可选 | 无 API Key 时核心统计正常 |
| 隐私预检 | 导出前扫描敏感信息 |
| 使用日志 | 本地 JSONL，可关闭/清除 |
| AI 不接触原始数据 | 仅处理变量名、摘要统计 |
| 交付包声明 | 自动附带 AI_USAGE_DISCLOSURE |

---

## 11. 文件结构

```
psy-analysis/
├── app.py                        # Streamlit 主入口
├── run.bat                       # 一键启动（含诊断日志）
├── install.bat                   # 一键安装（含诊断日志）
├── requirements.txt              # 依赖清单
├── src/
│   ├── analysis/                 # 统计分析引擎（48 注册方法）
│   │   ├── runner.py             # 统一分派入口
│   │   ├── method_ids.py         # 方法 ID 单一事实源
│   │   ├── ttest.py              # t 检验
│   │   ├── anova.py              # 方差分析
│   │   ├── nonparametric.py      # 非参数检验
│   │   ├── chi_square.py         # 卡方检验
│   │   ├── regression.py         # 回归分析
│   │   ├── logistic_regression.py # Logistic 回归
│   │   ├── advanced.py           # 中介/调节/ANCOVA
│   │   ├── reliability.py        # 信度分析
│   │   └── ...
│   ├── output/                   # APA 表格/图表/导出
│   │   ├── apa_tables.py         # 21 路由组 APA 表格
│   │   ├── apa_figures.py        # 11 种图表
│   │   ├── docx_exporter.py      # Word 导出
│   │   └── zip_exporter.py       # ZIP 交付包
│   ├── paper_writer/             # 论文写作辅助
│   ├── templates/                # 模板注册
│   ├── ui/                       # Streamlit UI
│   │   └── undergrad_wizard.py   # 主向导（3688 行）
│   ├── utils/                    # 工具层
│   │   ├── method_exposure.py    # 方法分级
│   │   ├── usage_logger.py       # 日志记录
│   │   └── privacy_precheck.py   # 隐私预检
│   ├── questionnaire/            # 问卷智能识别
│   └── literature_feed/          # 文献动态
├── tests/                        # 2313 个测试
├── project_templates/            # 6 个论文模板 + 测试数据
├── scripts/                      # 实用脚本
├── docs/                         # 8 个精简文档
└── logs/                         # 使用日志（本地，可删）
```

---

## 12. 文档目录

| 文档 | 内容 |
|------|------|
| `SYSTEM_REPORT.md` | 本报告（系统当前状态） |
| `USER_QUICKSTART.md` | 快速上手指南 |
| `KNOWN_LIMITATIONS.md` | 已知限制与降级策略 |
| `DELIVERY_PACKAGE_GUIDE.md` | 交付包使用说明 |
| `INSTALLATION_TROUBLESHOOTING.md` | 安装排错 |
| `PRIVACY_AND_AI_USAGE.md` | 数据隐私与 AI 声明 |
| `ACADEMIC_INTEGRITY_GUIDE.md` | 学术诚信/答辩参考 |
| `TESTING.md` | 测试体系说明 |

---

## 13. 已知限制

| 限制 | 影响 | 应对 |
|------|------|------|
| AVE/CR/区分效度无自动表格 | 需手动排版 | 结果卡片可用 |
| 仅 Windows | 不能在 Mac 用 | 暂无计划 |
| 需要 Python 3.10+ | 安装有门槛 | install.bat |
| AI 功能需 API Key | 离线时推荐不可用 | 核心统计离线可用 |
| undergrad_wizard.py 3688 行 | 维护时定位稍慢 | 未来渐进拆分 |
| 部分 experimental 方法无卡片 | MANOVA/ICC 等需手动 | 标注为实验性 |

---

## 14. 版本演进

| 版本 | 关键变更 |
|------|---------|
| v5.3 | 方法推荐 + 6 模板 + 基础交付包 |
| v5.4 | method_ids 单一事实源 + 方法分级 + 金标准测试 |
| v5.5 | 删除 76 个过度设计文件 + release_gate 精简 |
| v5.6 | default 方法 APA 表格补齐(+11) + release_gate full 模式 + 文档重命名 |
| **v5.7** | **advanced 方法表格（中介/调节/Logistic）+ 安装诊断日志 + 文档清理** |

---

## 15. 版本信息

```
版本:         5.7.0
Python:       3.10+
框架:         Streamlit
平台:         Windows 10/11
测试:         2313 passed / 0 failed / 59 skipped
注册方法:     48
APA 表格路由:  21 组
论文模板:     6
文档:         8
启动:         双击 run.bat 或 streamlit run app.py
自检:         python scripts/release_gate.py [--mode full]
```
