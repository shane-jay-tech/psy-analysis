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
- **触发**：Windows Task Scheduler 每日 + 应用启动检查（≥36 小时未抓时补拉）。
- **状态**：2026-05-28 启动，Kimi 调研顶刊抓取可行性中，下一步 /debate 架构 → /implement 落地。

### 🟡 #L2 F1 论文写作两入口合并

- **影响**：`paper_writing_ui.py` (594 行独立 mode) 和 `undergrad_wizard.py` 第 7 步「写方法+结果」**功能重叠**：两条最终都调 `PaperEngine` 生成论文，差别只是独立入口要重填一遍信息，wizard 入口已有数据。
- **决策**：v4.6 redundancy 时跳过（用户表态可能保留独立模式作为高级用户入口）。v4.7 重启评估，决定是否真合并、降级、或保留双入口加埋点观测使用率。
- **预期产出**：合并 → 省 ~600 行 UI；保留 → 至少加埋点。

### 🟡 #L3 N10 苏格拉底基准 LLM-as-judge 漂移连续观测

- **影响**：v3.7 加了 8 边界案例的金标，但单次对照；judge 漂移检测需要多次跑 + 历史曲线。
- **计划**：CI 跑 `scripts/evaluate_socratic_benchmark.py` + 历史趋势记录到 `D:\code\psy-analysis\data\benchmark_history\`，与 #L1 共用 D 盘数据目录约定。

### 🟢 #L4 SELF_ASSESSMENT_REPORT.md 严重过期

- **影响**：根目录 `SELF_ASSESSMENT_REPORT.md` 还停留在 2026-05-16 v2.0（74 个文件 / 11 测试 / 68 用例），与当前 v4.6（1239 collected / 几百个文件）已严重失真。
- **计划**：v4.7 收尾时刷新到 v4.7 真实快照，或干脆删除（依赖 `UPGRADE_REPORT_V*.md` 序列即可看清演进）。

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
| 🔴 高 | #L1 自学习模块 | v4.7 主线 | 调研中 |
| 🟡 中 | #L2 F1 论文写作合并 | v4.7 | 待评估 |
| 🟡 中 | #L3 N10 评分趋势观测 | v4.7 | 待开 |
| 🟢 低 | #L4 自评报告刷新 | v4.7 收尾 | 待开 |
| 🟢 低 | #L5 socratic_engine 类型 lie | v5.8 | 已完成 |

## v5.10 后续硬化路线

| 优先级 | 项目 | 当前边界 |
|---|---|---|
| P1 | 多实例项目写入 | 当前原子替换与 `RLock` 覆盖单进程；多实例需 OS 文件锁或事务存储 |
| P1 | 大工作区快照 | 首次自动保存仍同步序列化完整数据；评估增量资产/后台队列 |
| P1 | 浏览器 E2E | 当前 `.venv` 未安装 Playwright，25 项明确跳过；发布认证环境补装后重跑 |
| P2 | 交付入口收敛 | 正式交付已统一硬门禁；草稿、作业包与正式交付仍需统一入口语义 |
| P2 | 编排层拆分 | `app.py` 保持兼容但体量较大；按页面控制器渐进拆分 |
