# psy-analysis

本地优先的心理与问卷分析工作台，帮助研究者从问卷或实验数据开始，完成数据检查、统计分析、可视化和可交付报告生成。

## 能做什么

- 导入常见问卷和实验数据格式
- 进行描述统计、相关、组间比较、前后测、回归、中介、调节和量表分析
- 生成 APA 风格表格、图形和研究报告素材
- 提供方法目录、分析契约、隐私防护、导出检查和结果复核
- 使用 Streamlit 提供桌面/浏览器工作台
- 支持通过兼容 OpenAI API 的模型生成辅助解释，但 API 凭据只应保存在本地环境变量中

## 技术栈

Python · pandas · NumPy · SciPy · statsmodels · pingouin · scikit-learn · semopy · Streamlit · Plotly

## 本地运行

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## 目录说明

- `src/analysis/`：分析方法、契约和结果模型
- `src/data/`：数据加载与校验
- `src/ui/`：工作台页面和交互组件
- `src/output/`：图表、表格和报告输出
- `project_templates/`：研究设计模板
- `tests/`：分析、隐私和界面测试

公开仓库不包含本地运行数据库、原始文献抓取、实验归档或用户上传数据。请在发布或共享分析结果前确认已去标识化，并遵守知情同意、伦理审查和数据最小化要求。

## 研究边界

软件输出是分析辅助，不替代研究者的统计判断、方法审查或伦理责任。任何结论都应结合研究设计、数据质量、效应量、不确定性和可复现证据解释。
