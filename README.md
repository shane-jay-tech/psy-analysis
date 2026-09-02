# psy-analysis

本地优先的心理与问卷分析工作台，面向问卷调研、实验设计与论文交付。系统把数据检查、统计分析、可视化、文献综述、隐私防护和报告生成收敛到同一条研究流水线中。

## 技术架构

- Python + Streamlit 工作台（网页/桌面双模式）
- pandas / NumPy / SciPy / statsmodels / pingouin / scikit-learn / semopy 本地统计
- Plotly + Kaleido 图表与导出
- 文献综述与论文写作模块
- DeepSeek 兼容的 OpenAI API 用于解释生成与智能辅助（凭据只保存在本地环境变量）

本地数据库、原始文献抓取、实验归档和用户上传数据均被 Git 忽略，不会进入公开仓库。

## 环境要求

- Python 3.10+
- pip
- 可选：桌面模式依赖 PyWebView 与 WebView2（Windows 10/11 自带）

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

精确复现部署环境可改用 `requirements-lock.txt`（pip freeze 锁定）。

## 启动

网页模式：

```powershell
streamlit run app.py
```

桌面模式：

```powershell
python launcher.pyw
```

环境变量示例：

```text
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4-pro
```

## 分析方法

- **描述与质量**：描述统计、缺失值、异常值、正态性与假设检验路由。
- **组间与前后测**：t 检验、ANOVA、非参数检验、MANOVA。
- **关系与预测**：相关、回归、logistic 回归、卡方、HLM。
- **结构与效度**：因子分析、CFA、SEM、信度、效度、中介与调节。
- **进阶**：效应量与置信区间、事后检验与统计功效、元分析、方法推荐与方法契约。

系统提供方法目录（`method_catalog.py`）、方法 ID（`method_ids.py`）和分析契约（`contracts.py`），把「选方法 → 跑分析 → 出结果卡」的路径固定下来。

## 研究闭环

- **数据导入**：CSV、Excel、SPSS（pyreadstat）与常见问卷格式。
- **分析结果卡**：统一 result card 结构，附统计量、效应量、置信区间与解释。
- **图表输出**：APA 图表、论文导出与可视化面板。
- **文献工作流**：文献抓取、综述、阅读与缓存管理。
- **隐私与伦理**：PII 防护、匿名化检查、导出门禁与使用日志。
- **模板与向导**：研究设计模板、本科生向导、快速录入与交付中心。

## 验证

```powershell
pytest                           # 单元与回归测试
python scripts/release_gate.py   # 发布门禁（环境/隐私/导出等）
python scripts/perf_smoke.py     # 性能冒烟
```

测试覆盖分析结果、UI 面板、隐私防护、导出门禁、版本一致性与模板流程。公开仓库不包含 `data/` 与 `archive/` 实验数据；请在共享分析结果前确认已去标识化，并遵守知情同意、伦理审查和数据最小化要求。

## 目录

```text
app.py                   Streamlit 入口
config/                  配置与量表中英文映射
src/analysis/            统计方法与结果模型
src/data/                数据加载、校验与检查
src/literature*/         文献抓取、综述与阅读
src/ui/                  页面与交互组件
src/output/              图表、表格与报告
src/utils/               隐私、导出、存档与日志
project_templates/       研究设计模板
demo_projects/           演示项目
tests/                   测试套件
```

## 研究边界

软件输出是分析辅助，不替代研究者的统计判断、方法审查或伦理责任。任何结论都应结合研究设计、数据质量、效应量、不确定性和可复现证据解释。
