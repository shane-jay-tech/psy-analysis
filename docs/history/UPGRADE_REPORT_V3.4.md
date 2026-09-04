# v3.4 升级报告 — 启动文献综述工作台（2026-05-17）

## 一句话

v3.3 把上游打磨到可用，v3.4 启动**文献综述工作台**——覆盖科研流程最后一块缺口（选题完成→文献调研→精读整理→gap 识别），同时巩固 v3.3 的退行检测/语义对齐/可研究性。从 639 → **695 passed**（+56 tests），0 warnings，0 failed。

## 核心数字

| 指标 | v3.3 | v3.4 | Δ |
|---|---|---|---|
| 测试 | 639 passed | **695 passed** | **+56** |
| 警告 | 0 | **0** | — |
| 失败 | 0 | **0** | — |
| 新增模块 | — | `src/literature_review/`（5 文件） | +5 |
| 新增 UI | — | `literature_review_panel.py` | +1 |
| 新增测试文件 | — | 4 文件 | +4 |
| Schema 版本 | v3.3 → v3.4 | v3.4 (current) | — |

## 三阶段实现状态

### 阶段一：巩固 v3.3（任务 1-3）✅

#### 任务 1：可操作时间预算估算
- `feasibility_check.py` 加 `_estimate_time_budget`：横断面问卷 4-8 周 / 实验 8-12 周 / 未明 6-10 周
- `OperabilityResult.time_budget` 字段含 design_type/weeks_min/weeks_max/breakdown
- stage 4 UI 显示蓝色卡片（仅 is_feasible=True 时）
- **测试** +3：问卷/实验/高门槛跳过

#### 任务 2：退行检测误判保护
- `_check_no_regression` 加 `is_from_student` 参数
- 学生输入含「正如我之前说的」「像我在阶段 X」等引用短语 → 跳过退行
- 学生 >100 字 + 含「问卷/实验/样本量」等方法关键词 → 跳过退行
- AI 反问保留完整退行检测（is_from_student=False）
- **测试** +3：学生引用历史豁免、超 100 字方法讨论豁免、AI 反问仍触发

#### 任务 3：语义对齐 R9/R10/R11
- 新分类：`_PARTIAL_CORR_METHODS` / `_MEDIATION_METHODS` / `_MODERATION_METHODS`
- **R9** 偏相关需指定 control_var
- **R10** 中介需 X/M/Y 三个不同变量
- **R11** 调节变量为二分时给 info 级提示
- **测试** +6（每条规则正反 2 例）

### 阶段二：文献综述工作台（任务 4-11）✅

#### 任务 4：数据模型 `src/literature_review/models.py`（~250 行）
- **LiteratureItem**（兼容 CrawledReference + reading_status/notes/relevance_score/tags/added_at）
- **ReadingNote**（note_id/literature_key/content/page_or_section/type）
- **ThemeCluster**（theme_name/literature_keys/centroid_keywords/summary）
- **GapAnalysis**（gap_description/supporting_notes/suggested_direction/confidence/source）
- **LiteratureMatrix**（dimensions/cells/highlighted_keys + add/remove dimension）
- 全部 `to_dict/from_dict`，`from_crawled` 兼容现有 literature_crawler

#### 任务 5：搜索 `src/literature_review/search.py`（~200 行）
- `search_literature` 调 `literature_crawler.search_all` + bigram 排序 + 年份过滤
- `deduplicate_by_doi`（DOI 优先，缺失时按 (title.lower(), year) 去重）
- `rank_by_relevance` 复合评分 = max-coverage bigram + 引用数加权
- `_filter_non_journal` 排除 conference/proceedings/thesis
- `crawler_search_all` 注入参数支持 mock 测试

#### 任务 6：阅读笔记 `src/literature_review/notes.py`（~150 行）
- CRUD：`create_note` / `edit_note` / `delete_note`
- 聚合：`get_notes_by_literature` / `get_notes_by_theme` / `filter_notes_by_type`
- 导出：`export_notes_markdown`（按文献分组 + 类型标签 + Markdown 安全清理）
- 序列化：`notes_to_dict_list` / `notes_from_dict_list`

#### 任务 7：文献矩阵 `src/literature_review/matrix.py`（~250 行）
- `create_matrix` / `add_literature_to_matrix` / `remove_literature_from_matrix`
- `auto_fill_abstract_info`：8 维度正则模式（样本量/研究设计/效应量/主要发现/局限）
- `export_matrix_csv` + `render_matrix_html`（高亮行支持）

#### 任务 8：主题聚类与 Gap `src/literature_review/themes.py`（~280 行）
- `auto_cluster_themes`：sklearn KMeans 优先，失败降级到关键词重叠层次聚类
- 笔记 < n_clusters*2 时按文献分组（避免聚类失败）
- `identify_gaps`：LLM 优先（`build_tutor_messages` + `chat_with_tutor`），失败降级启发式
- 启发式 gap 检测：矩阵空格率高 + 学生「疑问」类型笔记
- `generate_gap_report` 输出 Markdown
- jieba + 停用词 + 中英文混合 tokenize

#### 任务 9：UI `src/ui/literature_review_panel.py`（~440 行）
- 顶部搜索栏（自动填 research_q + 摘要信息）
- 三栏布局：列表（按 relevance/状态图标）/ 详情+笔记编辑器 / 矩阵
- 底部 4 tab：📊 主题聚类 / 🕳️ Gap 分析 / 📝 导出综述 / 🚪 完成→wizard
- 漏斗 stage 5 加「📚 进入文献综述工作台」按钮（与「直接进入 wizard」并列）
- wizard 顶部加「📚 文献综述」入口（独立按钮）

#### 任务 10：工作区 + 路由集成
- `workspace.py`：CURRENT_SCHEMA `v3.2 → v3.4`；新增 `_DEFAULT_LITERATURE_REVIEW_STATE` + `get/set_literature_review_state`
- 迁移：`_migrate_v3_2_to_v3_4` 填充空 literature_review_state；MIGRATIONS 加 v2.9/v3.2/v3.3 → v3.4 链
- VERSION_ORDER 加 v3.2/v3.3
- `routing.py`：ROUTING_TABLE 加 (True, "literature_review", "beginner")/(advanced)；`_VALID_PHASES` 加 literature_review；新增 `get_phase_lifecycle` / `next_phase` / `validate_routing_table_at_startup`
- phase 生命周期：`funnel → literature_review → wizard → done`
- `app.py`：路由分发加 `literature_review_beginner/advanced` → `render_literature_review`；版本字符串 v3.4

#### 任务 11：文献综述测试集（24 测试，4 文件）
- `test_literature_review_models.py` +14：LiteratureItem 序列化/from_crawled/short_citation/emoji；ReadingNote update_content；ThemeCluster；GapAnalysis；LiteratureMatrix set/get/add/remove/empty_count/round_trip
- `test_literature_review_search.py` +8：mock 搜索；年份过滤；relevance 排序；失败降级；DOI 去重；title 去重；DOI 归一化
- `test_literature_review_notes.py` +12：CRUD；类型容错；按文献/主题聚合；filter_by_type；Markdown 导出；序列化
- `test_literature_review_integration.py` +6：完整链路（搜索→笔记→矩阵→主题→gap）；funnel→literature_review 转换；literature_review→wizard 转换；workspace 持久化；ADVANCED 路由

### 阶段三：维护性（任务 12-13）✅

#### 任务 12：KNOWN_ISSUES.md
- 8 条已知局限，每条注明影响/复现/缓解/计划修复版本
- 含修复优先级表（🔴 高 / 🟡 中 / 🟢 低）
- 已修复条目（如退行误判）标记 ✅

#### 任务 13：路由维度校验
- `validate_routing_table_at_startup`：遍历所有 (mode, phase, tier) 组合验证完整性
- 维度校验：phase ∈ {funnel, literature_review, wizard, done}，tier ∈ {beginner, advanced}
- **测试** +4：启动自检通过、模拟移除组合检测 missing、literature_review 解析、phase 生命周期顺序

## 文件改动清单

### 新增（11 文件）
```
src/literature_review/__init__.py
src/literature_review/models.py
src/literature_review/search.py
src/literature_review/notes.py
src/literature_review/matrix.py
src/literature_review/themes.py
src/ui/literature_review_panel.py

tests/test_literature_review_models.py     (14)
tests/test_literature_review_search.py     (8)
tests/test_literature_review_notes.py      (12)
tests/test_literature_review_integration.py (6)

KNOWN_ISSUES.md
```

### 修改（10 文件）
```
src/upstream/feasibility_check.py     — 时间预算估算 + OperabilityResult.time_budget
src/upstream/socratic_engine.py       — 退行检测加 is_from_student 豁免
src/upstream/semantic_alignment.py    — R9/R10/R11 + 高级方法分类
src/upstream/routing.py               — literature_review phase + 启动自检 + lifecycle
src/utils/workspace.py                — CURRENT_SCHEMA v3.4 + literature_review_state + 迁移链
src/ui/upstream_panel.py              — stage 4 时间预算卡片 + stage 5 文献综述跳转按钮
src/ui/undergrad_wizard.py            — 顶部加「📚 文献综述」入口
app.py                                — literature_review 路由分发；版本 v3.4

tests/test_workspace.py               — schema 断言 v3.2 → v3.4
tests/test_e2e_rendering.py           — 同上
tests/test_upstream_integration.py    — schema 断言更新
tests/test_upstream_feasibility.py    — TestTimeBudget +3
tests/test_upstream_socratic.py       — TestRegressionFalsePositiveProtection +3
tests/test_semantic_alignment.py      — TestR9/R10/R11 +6
tests/test_routing.py                 — TestRoutingTableValidation +4
```

## 测试覆盖统计

| 文件 | 增量 |
|---|---|
| test_upstream_feasibility.py | +3 (时间预算) |
| test_upstream_socratic.py | +3 (退行豁免) |
| test_semantic_alignment.py | +6 (R9/R10/R11) |
| test_routing.py | +4 (维度校验) |
| test_literature_review_models.py | +14 |
| test_literature_review_search.py | +8 |
| test_literature_review_notes.py | +12 |
| test_literature_review_integration.py | +6 |
| 其他（schema 断言更新等） | +0 (修订) |
| **总计** | **+56**（639 → 695） |

> 与最初目标 700+ 的差距 5 个测试，主要是「真实链路 + 模型 + UI」覆盖比 1:1 任务对应少；下一版可补 UI 单元测试到 700+。

## 关键架构决策

1. **文献综述工作台作 phase=literature_review 而非 wizard 内嵌**
   - 优点：路由清晰，可独立切换；ADVANCED 也可用
   - 缺点：用户多走一步，但有 stage 5 + wizard top 双入口
2. **LiteratureItem 不复用 CrawledReference dataclass**
   - 原因：CrawledReference 是搜索层模型，LiteratureItem 是工作台层（含 reading_status/relevance/tags），分层避免污染
   - 用 `from_crawled` 适配器保证兼容
3. **聚类降级到关键词重叠**
   - sklearn 不可用时不崩，降级质量略低但可用
   - 笔记数 < n_clusters*2 时按文献分组（避免聚类失败）
4. **Gap 识别 LLM 优先 + 启发式降级**
   - LLM 给细致 gap，启发式给空格 + 「疑问」笔记两类
   - source 字段标识来源（"llm" vs "heuristic"），UI 透明
5. **路由表显式优于隐式**（v3.3 决策延续）
   - 加新 phase 必须更新 ROUTING_TABLE，不允许在分支中无序添加 if
   - `validate_routing_table_at_startup` 启动自检捕获遗漏

## 已知局限

详见 `KNOWN_ISSUES.md`：

| 严重度 | 局限 | 计划版本 |
|---|---|---|
| 🔴 高 | 多 tab 编辑无锁 | v3.5 |
| 🟡 中 | 可操作关键词库手维护（VR/AR 漏检） | v3.5 |
| 🟡 中 | benchmark 评估需人工标注 | v3.5（LLM-as-judge） |
| 🟡 中 | 文献综述降级路径无可见提示 | v3.5 UI 改进 |
| 🟢 低 | 语义对齐 11 规则未覆盖中介调节 | v3.5-v3.6 |
| 🟢 低 | 矩阵自动填充正则精度 | v3.5-v3.6 |
| 🟢 低 | session_state 命名空间散落 | v3.6（重构） |

## 部署验证清单

| # | 验证点 | 状态 |
|---|---|---|
| 1 | 启动 → 侧栏显示 v3.4 | ✅ "v3.4 · 文献综述工作台" |
| 2 | 漏斗完成 → stage 5 → 「📚 进入文献综述工作台」按钮 | ✅ 与「直接进入 wizard」并列 |
| 3 | 点击进入 → 自动填 research_q → 一键搜索 | ✅ search_literature 接 crawler.search_all |
| 4 | 点击文献 → 摘要 + 添加阅读笔记 | ✅ 中间面板 + 类型选择 |
| 5 | 主题聚类 → 看到 2-4 主题 | ✅ KMeans + 关键词重叠降级 |
| 6 | Gap 分析 → 至少 1 个 gap 描述 | ✅ LLM + 启发式 |
| 7 | 文献矩阵 → 添加 3 自定义维度 → 手动填 | ✅ + 一键自动填充 |
| 8 | 导出综述 → Markdown 含 5 部分 | ✅ 研究问题/文献列表/主题/gap/笔记 |
| 9 | 关闭浏览器 → 重新打开 → 状态完整恢复 | ✅ workspace v3.4 序列化 |
| 10 | ADVANCED tier → 跳过漏斗 → 第 7 步可选「📚 文献综述」 | ✅ wizard 顶部按钮 |
| 11 | 路由：未注册组合 → 抛 RouteNotFoundError | ✅ validate_routing_table_at_startup |
| 12 | 老 v3.3 项目升 v3.4 → 自动填充空 literature_review_state | ✅ _migrate_v3_2_to_v3_4 |
| 13 | 全量测试 695 passed, 0 warnings, 0 failed | ✅ |

## 复用资产（验证有效）

| 资产 | 位置 | 用途 |
|---|---|---|
| `literature_crawler.search_all()` | `src/paper_writer/literature_crawler.py:239` | 搜索 Crossref + Semantic Scholar |
| `CrawledReference` | 同上 | LiteratureItem.from_crawled 兼容输入 |
| `chat_with_tutor()` | `src/paper_writer/ai_tutor.py:185` | identify_gaps LLM 调用 |
| `build_tutor_messages()` | 同上 | LLM message 构造 |
| workspace MIGRATIONS dict | `src/utils/workspace.py:313` | schema 升级链 |
| `IntentRecognitionChain` | `src/questionnaire/intent_recognizer.py` | （留作 v3.5 文献关键词扩展用） |
| autosave force=True | `src/utils/autosave.py:47` | phase 切换强制保存 |

## 下一步建议（v3.5）

按 KNOWN_ISSUES 优先级：

1. **多 tab 锁**（🔴 高，数据安全）— 最先做
2. **关键词库 LLM 辅助**（🟡）— 解决可操作漏检
3. **LLM-as-judge 反问质量自动评估**（🟡）— 减少人工标注负担
4. **文献综述降级路径 UI 提示**（🟡）— 用户透明
5. **文献矩阵正则模式扩展**（🟢）— 精度提升
6. **语义对齐规则扩到 ~20 条**（🟢）— 覆盖中介调节组合

文献综述工作台是科研流程上游的最后一块拼图。v3.5 应转向**质量保证与协作**（多 tab 锁、自动评估、降级透明）。
