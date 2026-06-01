# Psy Analysis v2.7 升级报告

**升级日期**：2026-05-17
**版本定位**：v2.6 研究助手 → **v2.7 本科生论文交付器**
**升级范围**：新增 7 项任务，覆盖论文产出最后一公里

---

## 1. 升级核心：差异化价值

v2.6 解决「分析」，v2.7 解决「分析后到论文/答辩成品」的最后一公里。
针对单用户、本科生场景重构优先级，砍掉了多用户/工程化等无关诉求。

| 任务 | 价值 | 类别 |
|---|---|---|
| 论文版图表导出（PNG 300dpi）| 期刊/论文级配色与清晰度 | Tier 1 |
| Word 一键导出（.docx）| 直接生成可交作业的 Word 文档 | Tier 1 |
| 答辩问题模拟器 | 自动生成针对性答辩问答 | Tier 1（差异化） |
| 错误信息友好化 | 把 traceback 翻译成本科生能懂的提示 | Tier 2 |
| 数据清洗向导 | 引导式处理缺失/常数列/异常值，方法部分自动生成 | Tier 2 |
| CFA 软依赖明确提示 + 长操作 spinner 文案 | 配套小修 | Tier 3 |

---

## 2. 文件改动清单

### 新增文件（8 个）

| 文件 | 用途 | 行数 |
|---|---|---|
| `src/visualization/paper_export.py` | Plotly→PNG 300dpi，黑白/灰度/彩色配色 | 200 |
| `src/output/docx_styles.py` | APA7 字体/字号/页边距常量 | 35 |
| `src/output/docx_exporter.py` | Word 文档生成（标题页、Markdown→docx、三线表、图片嵌入） | 320 |
| `src/paper_writer/defense_qa.py` | 答辩问题生成器（按 plan + result 填充模板） | 220 |
| `src/paper_writer/defense_qa_kb.py` | 问题模板库（10+ 种检验，6 大类问题） | 230 |
| `src/utils/friendly_errors.py` | 错误信息翻译字典（30+ 模式） | 180 |
| `src/ui/cleaning_wizard.py` | 数据清洗向导（缺失/常数列/异常值处理） | 230 |
| `UPGRADE_REPORT_V2.7.md` | 本文件 | — |

### 修改文件（5 个）

| 文件 | 改动 |
|---|---|
| `app.py` | 版本号 v2.6 → v2.7 |
| `src/ui/undergrad_wizard.py` | 第 3 步加清洗向导 expander；第 7 步加 Word 下载 + 答辩问答 expander；spinner 文案智能化；方法部分自动注入清洗段落 |
| `src/ui/renderers.py` | 每个图表下方加"下载论文版"控件；图表渲染失败用 friendly_error |
| `src/analysis/runner.py` | 异常处理接入 friendly_explain，error 字典增加 friendly_* 字段 |
| `src/utils/env_check.py` | 新增 kaleido 检测；提示信息加 pip install 建议 |
| `requirements.txt` | +`kaleido>=0.2.1` |

### 新增测试（4 个文件）

| 文件 | 测试条数 |
|---|---|
| `tests/test_paper_export.py` | 8（含 1 条 kaleido smoke skip） |
| `tests/test_docx_export.py` | 7 |
| `tests/test_defense_qa.py` | 9 |
| `tests/test_friendly_errors.py` | 10 |
| `tests/test_cleaning_wizard.py` | 9 |

---

## 3. 测试结果

| 指标 | v2.6 | v2.7 | 变化 |
|---|---|---|---|
| 常规测试数 | 279 | 322 | +43 |
| 真实浏览器测试 | 11 | 11 | 0 |
| 测试总计 | 290 | 333 | +43 |
| 通过率 | 100% | 100% | — |
| 跳过 | 0 | 1 | kaleido smoke（缺包时跳过） |
| 警告 | 6 | 6 | 不变（HLM 奇异警告） |

**全量回归命令**：`pytest tests/ -q --ignore=tests/test_playwright_e2e.py`
**结果**：322 passed, 1 skipped, 6 warnings in ~30s

---

## 4. 功能详解

### 4.1 论文版图表导出（PNG 300dpi）
- **接口**：`paper_export.to_paper_png(fig, palette='grayscale')`
- **配色**：彩色（PPT/电子稿）、灰度（期刊/论文）、纯黑（复印/扫描）
- **黑白模式**线条自动循环 dash 与 marker 形状，确保印刷可辨识
- **CJK 字体**：自动检测 `msyh.ttc`/`simhei.ttf`/`simsun.ttc` 嵌入 SVG/PNG
- **降级**：kaleido 缺失时抛 `KaleidoMissingError`，UI 给清晰安装提示
- **集成**：每个图表下方"💾 下载论文版图表"expander，配色 + 尺寸可选

### 4.2 Word 一键导出（.docx）
- **接口**：`docx_exporter.build_thesis_docx(meta, method_md, result_md, ...)`
- **包含**：标题页、摘要、关键词、方法部分、结果部分、描述统计三线表、嵌入图、答辩问答附录
- **样式**：APA7 标准（页边距、行距 1.5、首行缩进 2 字符、宋体/黑体/Times New Roman 混排）
- **三线表**：仅顶/表头底/末行三条横线，符合心理学论文规范
- **集成**：向导第 7 步"📄 下载 Word 论文初稿"expander，可选嵌入图表/答辩问答

### 4.3 答辩问题模拟器
- **6 大问题类别**：方法选择 / 数据合规 / 效应量 / 假设验证 / 研究局限 / 推论谨慎
- **覆盖检验**：t 检验（独立/配对）、ANOVA、Pearson/Spearman、Mann-Whitney、中介、信度、EFA、卡方
- **答案模板化**：每个问题附标准答案模板，自动填入实际统计量
  - 例："你的 d=0.55 是大还是小？" → 自动判断为"中等效应"并生成完整解释
- **数据驱动**：从 plan + result 抽取占位符（n、effect_size、Levene 状态、KMO 等）
- **集成**：向导第 7 步"🎤 答辩问题预演"expander，按类别分组展示

### 4.4 错误信息友好化
- **30+ 错误模式**：文件编码、非数值数据、零方差列、奇异矩阵、API Key、网络超时等
- **三段式提示**：标题（中文病因）+ 解释 + 怎么办（具体行动建议）
- **保留技术细节**：折叠展开框含原始 traceback，反馈 Bug 时可复制
- **集成**：runner.py 异常处理 + renderers.py 图表失败 + 装饰器 `@friendly_handler`

### 4.5 数据清洗向导
- **检测项**：缺失值（按列/总比例）、常数列、异常值（IQR）
- **处理动作**：删除行、删除列、均值填补、中位数填补、Winsorize、强制数值化
- **可追溯**：每步 CleaningStep 记录前后 shape、操作描述
- **撤销机制**：一键恢复原始数据
- **方法部分自动生成**：清洗步骤转中文段落，自动注入论文方法部分
- **集成**：向导第 3 步"🧹 数据清洗助手"expander

### 4.6 CFA 软依赖 + spinner 文案
- `env_check.py` 加 kaleido 检测，启动时 toast 提示
- 提示信息含 `pip install <pkg>` 安装命令
- 向导第 5 步 spinner 根据 test_type 智能切换：
  - mediation: "运行 5000 次 Bootstrap 模拟，约 10–30 秒..."
  - efa: "进行平行分析与因子提取..."

---

## 5. 升级前后对比

### 用户体验
| 场景 | v2.6 | v2.7 |
|---|---|---|
| 写论文 | 复制 Markdown → Word 调格式 30 分钟 | 一键导出 Word，直接交 |
| 论文配图 | Plotly 截图，分辨率不够 | PNG 300dpi 灰度，期刊级 |
| 准备答辩 | 自己想老师可能问什么 | 系统列 7 个问题 + 答案模板 |
| 数据有缺失 | 看到警告但不知道怎么办 | 一键清洗，论文方法自动写 |
| 报错 | 红色 traceback 看不懂 | 中文病因 + 解决建议 |

### 代码体量
- 新增代码：~1400 行（含测试）
- 新增测试：43 条
- 既有代码改动：~50 行（非破坏性）

---

## 6. 已知局限

| 项目 | 说明 | 应对 |
|---|---|---|
| kaleido 在部分 Win 环境安装失败 | 优雅降级；UI 显示明确安装提示 | 可手动 `pip install kaleido` |
| Word 中文字体依赖系统 | 默认引用宋体/黑体，未嵌入字体文件 | Win/Mac 通用；Linux 需安装 Noto Serif CJK |
| 答辩模板库覆盖 ~10 种检验 | 偏冷门方法（HLM/Meta）暂未覆盖 | 后续 v2.8 扩展 |
| 数据清洗向导限本科常用动作 | 不含多重插补/FIML | 复杂场景建议导出后用 mice/FIML |

---

## 7. 部署验证清单（建议手动跑一遍）

- [ ] `pip install -U kaleido python-docx pillow` 安装新依赖
- [ ] 启动 `streamlit run app.py`，确认侧边栏显示 v2.7
- [ ] 加载演示数据 → 第 3 步看到清洗向导 expander
- [ ] 第 5 步运行中介分析 → 看到 "5000 次 Bootstrap" spinner 文案
- [ ] 第 7 步生成方法 + 结果 → 点"下载 Word" → Word 打开格式正确
- [ ] 第 7 步点"答辩问题预演" → 看到 7 个问题分类显示
- [ ] 任意图表下方点"下载论文版" → 灰度 PNG 300dpi
- [ ] 故意上传错误编码 CSV → 看到友好错误提示而非 traceback

---

## 8. 后续展望（v2.8 候选）

- 答辩模板库扩展到 HLM / Meta-analysis / SEM
- 论文图表批量导出（一次 ZIP 含所有图）
- 多重插补（mice）与 FIML 集成
- 实验设计模块也加 Word 导出（实验程序文档）
- 视频教程/动画引导（截图 → GIF）

---

**升级负责人**：Claude（首席架构师 & 开发工程师）
**用户**：本科生研究者（单用户场景）
**状态**：✅ 升级完成，全量测试通过
