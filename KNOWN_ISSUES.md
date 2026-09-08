# 已知局限与待办

记录当前明确已知但**不阻塞使用**的局限。

> **2026-08-15 v5.8 性能收口**：启动自检免导入化（30s→740ms）+ 侧栏快照按需生成
> + 后台预热线程 + Excel 上传必崩/大文件上传必失败两个数据入口 Bug 修复，详见
> `UPGRADE_REPORT_V5.8.md`。#L5 已完成。
>
> **2026-08-15 v5.9 交互深化**：关闭 magic AST 重写（rerun 0.31s→0.10s）、
> 修独立 t 检验/配对检验图表必崩两个 P0、卡方新增列联表热力图、三处破坏性
> 操作加两步确认、179 处 width 迁移，详见 `UPGRADE_REPORT_V5.9.md`。
>
> **2026-08-24 v5.10 系统体验收口**：接通实验设计主路由、统一导航事实源、
> “保存并开始新研究”隔离跨项目资产、恢复一次性新手引导、接入下一步提示、
> 自动保存原子写盘、Kaleido 浏览器回退及版本/隐私声明统一，详见
> `UPGRADE_REPORT_V5.10.md`。
>
> 历史 v3.x 记录见 `UPGRADE_REPORT_V3.0.md` ~ `UPGRADE_REPORT_V3.9.md`，
> v4.x 决策见 `docs/decisions/2026-05-23-*.md` 与 `2026-05-26-*.md`。

---

## v4.0 → v4.6 已修汇总 ✅

每条都有对应决策文档，本节只列收口状态，避免重复细节。

| 版本 | 主题 | 决策档案 |
|---|---|---|
| **v4.0** | 假设路由建议（不静默切）+ χ²/相关 CI 补缺 + 事后样本量（不显 power 数值） | 见 `psy_v4.0_phase_1_3` 记忆 |
| **v4.1** | 上传题目 → 预审 → Word/PDF 排版 | `docs/decisions/2026-05-23-impl-questionnaire-upload.md` |
| **v4.2** | AI 预审分维度模式（创新维度不被压低分） | `docs/decisions/2026-05-23-impl-ai-review-dimensions.md` |
| **v4.3** | 侧栏顶 4 个预设 selectbox（GPT-5.5/DeepSeek V4 Pro/Kimi K2.6/Claude Opus 4.7） | `docs/decisions/2026-05-23-impl-quick-models.md` |
| **v4.4** | 维度编辑器粘贴导入（Markdown/Tab/CSV/段落 KV） | `docs/decisions/2026-05-23-impl-dimensions-paste-import.md` |
| **v4.5** | 题目解析器加指导语启发式 + 「保留」CheckboxColumn 双保险 | `docs/decisions/2026-05-23-impl-instruction-heuristic-and-keep-column.md` |
| **v4.6.a** | LLM 单轨化（删底部配置面板 + 备用模型 fallback；侧栏 9→4 块） | `docs/decisions/2026-05-25-merge-llm-config-quickonly.md` + `2026-05-26-llm-single-track-review.md` |
| **v4.6.b** | 冗余清理：A 类 ~1500 行 src 死代码 + B 类 legacy 函数 + F2/F3 用户视角冗余 | `docs/decisions/2026-05-26-redundancy-audit.md` |

**测试基线**：v3.9 (1140) → v4.0 (1166) → v4.1+4.2 (1208) → v4.3 (1222) → v4.4 (1253) → v4.5 (1260) → v4.6.a (1260) → v4.6.b (1235) → v5.10 当前 2544 个离线收集项。

---

## 仍未修复（v4.7+ 路线）

### 🔴 #L1 自学习模块（4 顶刊每日抓摘要 → 知识库扩充 + 趋势提示）

- **影响**：当前 `construct_kb` / 方法库是静态的，最新心理学顶刊新构念/新方法（尤其工业组织、HR、组织行为方向）进不来；选题漏斗里的"领域热点"无法体现学术界近期动向。
- **范围**：心理学报 / 心理科学进展 / 心理科学 / 管理世界（4 本 CSSCI 顶刊，覆盖工业组织 / HR / 组织行为）。
- **关键风险**：摘要 → LLM 抽构念，幻觉直接入库会**污染所有下游推荐**。必须有 staging + 人工 review gate，不能直接进 `construct_kb`。
- **存储位置**：`D:\code\psy-analysis\data\literature_feed\`（不进 C 盘 .claude）。
- **领域加权**：用户研究方向偏 IO / HR / 组织行为，关键词加权表（领导力/组织承诺/敬业度/职业倦怠/工作满意度/HR 实践/团队/绩效/选拔/培训/组织行为）需在抽取与趋势聚合时双重加权。
- **触发**：Windows Task Scheduler 每日 + 应用启动检查（≥24 小时未抓时补拉，`bootstrap_check.py` 的 `DEFAULT_STALE_HOURS = 24`）。
- **状态**：已落地——`src/literature_feed/` 已实现（fetchers / parsers / extract / scheduler 全链路），补拉阈值 24 小时。

### 🟡 #L2 F1 论文写作两入口合并

- **影响**：`paper_writing_ui.py` (594 行独立 mode) 和 `undergrad_wizard.py` 第 7 步「写方法+结果」**功能重叠**：两条最终都调 `PaperEngine` 生成论文，差别只是独立入口要重填一遍信息，wizard 入口已有数据。
- **决策**：v4.6 redundancy 时跳过（用户表态可能保留独立模式作为高级用户入口）。v4.7 重启评估，决定是否真合并、降级、或保留双入口加埋点观测使用率。
- **预期产出**：合并 → 省 ~600 行 UI；保留 → 至少加埋点。

### 🟡 #L3 N10 苏格拉底基准 LLM-as-judge 漂移连续观测

- **影响**：v3.7 加了 8 边界案例的金标，但单次对照；judge 漂移检测需要多次跑 + 历史曲线。
- **计划**：CI 跑 `scripts/evaluate_socratic_benchmark.py` + 历史趋势记录到 `D:\code\psy-analysis\data\benchmark_history\`，与 #L1 共用 D 盘数据目录约定。

### ✅ #L4 SELF_ASSESSMENT_REPORT.md 严重过期（2026-09-08 关闭：已归档）

- **原状**：根目录 `SELF_ASSESSMENT_REPORT.md` 停留在 2026-05-16 v2.0（74 个文件 / 11 测试 / 68 用例），与当前 v4.6+ 严重失真。
- **闭环结论**：过期报告已于 2026-09-04 由 commit `4add02e`（chore: archive historical reports into docs/history）归档至 `docs/history/SELF_ASSESSMENT_REPORT.md`——根目录已无此文件（2026-09-08 实查 `git ls-files` 唯一命中 docs/history/ 路径；无删除记录，属归档移动）。内容定格为 v2.0 历史快照、不再刷新；项目演进史由 `docs/history/UPGRADE_REPORT_V*.md` 序列承载。
- **证据命令**：`git log --oneline --diff-filter=A -- docs/history/SELF_ASSESSMENT_REPORT.md` → `4add02e`；`git log -S 'SELF_ASSESSMENT_REPORT' --oneline --all` → ec45485（新增根目录版）/ 17faa95（末次内容修改）。

### ✅ #L5 socratic_engine.ask_socratic 类型签名 lie（v5.8 已修）

- **修复**：`ask_socratic` / `ask_socratic_stream` 签名改 `Optional[Dict[str, Any]]`，
  None 早返回 fallback 模板（`_safe_chat` 同样加 None 双保险）。绕过 gate 直调永不 crash。
- **测试**：`tests/test_upstream_socratic.py` 新增 2 个 None 降级测试。
- **报告**：`UPGRADE_REPORT_V5.8.md` 三.3。

---

## 已废弃（不再追踪）

### ~~#N11 多用户成本预算~~
- **理由**：用户已明确「单人使用，不做团队版/作品集」（feedback_two_systems_goals）。多用户/月度预算需求不存在，永久关闭。

---

## 优先级看板

| 严重度 | 局限 | 目标版本 | 状态 |
|---|---|---|---|
| 🔴 高 | #L1 自学习模块 | v4.7 主线 | 已落地 |
| 🟡 中 | #L2 F1 论文写作合并 | v4.7 | 待评估 |
| 🟡 中 | #L3 N10 评分趋势观测 | v4.7 | 待开 |
| 🟢 低 | #L4 自评报告刷新 | — | 已关闭（过期件已归档 docs/history/，commit 4add02e，不再刷新） |
| 🟢 低 | #L5 socratic_engine 类型 lie | v5.8 | 已完成 |

## v5.10 后续硬化路线

| 优先级 | 项目 | 当前边界 |
|---|---|---|
| P1 | 多实例项目写入 | 当前原子替换与 `RLock` 覆盖单进程；多实例需 OS 文件锁或事务存储 |
| P1 | 大工作区快照 | 首次自动保存仍同步序列化完整数据；评估增量资产/后台队列 |
| P1 | 浏览器 E2E | 当前 `.venv` 未安装 Playwright，25 项明确跳过；发布认证环境补装后重跑 |
| P2 | 交付入口收敛 | 正式交付已统一硬门禁；草稿、作业包与正式交付仍需统一入口语义 |
| P2 | 编排层拆分 | `app.py` 保持兼容但体量较大；按页面控制器渐进拆分 |

---

## 已知功能边界

> 2026-09-04 由 docs/KNOWN_LIMITATIONS.md 并入（该文件保留并加横幅指向本节）。

| 限制 | 影响范围 | 降级策略 |
|------|---------|---------|
| Logistic 系列细分不完整 | 二元/有序/多项 Logistic 解释有限 | 标记为"高级方法"，使用基础卡片 |
| MANOVA 结果卡片缺失 | 多元方差分析结果展示不完整 | 使用通用输出格式 |
| ICC 评估卡片缺失 | 评分者一致性结果需手动解释 | 输出原始数值供用户解读 |
| 部分 advanced 方法无 APA 表格 | 中介/SEM 等需手动排版 | 结果卡片仍可用 |
| 无 Mac/Linux 支持 | 仅限 Windows 用户 | 未来版本计划 |
| 无云端部署 | 必须本地安装 | 提供安装指南 |
| 最大数据文件约 100MB | 大文件读取 | 提示选择部分列 |
| 最大行数约 100 万行 | 大表运算变慢 | 可能变慢但不崩溃 |
| 分类变量水平数 | 超过 10 级时提醒 | 无硬限制，仅提示 |
| 缺失值默认 listwise | 分析样本缩减 | 提示缺失比例 |

> 2026-09-09（pm30）：其余四节（环境边界/方法支持分层/安全与隐私边界）已由 docs/KNOWN_LIMITATIONS.md 迁入本文件（映射依据 docs/insights/known-issues-doc-alignment-20260905.md）；KL 自此为对外派生口径页，以本文件为准。

## 环境边界

| 场景 | 行为 | 降级提示 |
|------|------|---------|
| 无 Word/LibreOffice | Word 导出正常（python-docx）；PDF 转换不可用 | "PDF 不可用，请手动在 Word 中导出" |
| 无 LLM API Key | 统计/表格/图表/导出全部正常；方法推荐、论文段落生成、智能解释不可用 | "AI 功能不可用，可手动选择方法" |
| 无网络 | 核心功能全部可用（离线设计） | 无（默认即离线模式） |
| 中文字体缺失 | 图表中文可能显示为方框；Word 导出不受影响 | "安装 SimHei 字体可改善图表显示" |
| Playwright 未安装 | E2E 测试跳过（开发/测试依赖，用户无需安装） | — |

## 方法支持分层

- **默认推荐方法（完整支持）**：Pearson/Spearman 相关、独立/配对 t 检验、单因素/双因素方差分析、重复测量方差分析、非参数检验（Mann-Whitney/Wilcoxon/Kruskal-Wallis）、卡方检验、多元/层次回归、Cronbach's α / McDonald's ω、描述统计。
- **高级方法（大部分有 APA 表格）**：中介分析（路径系数表+Bootstrap CI）、调节分析（回归系数+简单斜率表）、Logistic 回归（B/SE/Wald/OR/CI 表）、EFA/CFA/SEM（因子载荷/模型拟合表）、HLM/混合效应（固定+随机效应表）、AVE/CR/区分效度（无自动表格，结果卡片可用）。
- **实验性方法（基础支持）**：未注册结果卡片的方法输出为原始格式，需用户自行整理。实验性标记以 runner 结果卡片注册现状为准（2026-09-09 注：假设检验路由已扩至 14 法，精确清单以 src/analysis/ 代码为准）。

## 安全与隐私边界

- 数据存储在本机，不自动上传。
- AI 调用前会提示用户确认。
- 导出前隐私预检可能有假阴性（未覆盖所有敏感模式）。
- 使用日志可被用户关闭和清除。
- 不适用于涉及真实患者数据的临床研究。
