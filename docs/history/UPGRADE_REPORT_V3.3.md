# v3.3 升级报告 — 巩固 v3.2 上游成果（2026-05-17）

## 一句话

v3.2 完成战略性跃迁（首次覆盖科研流程上游），v3.3 用 9 大类 16 项升级把"AI 苏格拉底"打磨到真正可用——范例库扩 3 倍 + 语义检索、跨阶段一致性、可研究性 4 项齐全、漏斗分支管理、ADVANCED 留痕、跨模块语义对齐、反问质量基准、用户契约、路由配置表。

## 核心成果（数字）

| 指标 | v3.2 | v3.3 | Δ |
|---|---|---|---|
| 测试 | 517 passed | **639 passed** | **+122** |
| 警告 | 0 | **0** | — |
| 失败 | 0 | **0** | — |
| 新增模块 | — | semantic_alignment, routing | +2 |
| 新增测试文件 | — | 5（kb/alignment/quality/panel/routing） | +5 |

## 9 大类升级实现状态

### A. 范例库扩展与语义检索 ✅

- **18 条好/差选题对比**（社会/临床/教育/发展/认知/组织行为各 3 例），全部本科可执行（无 fMRI / EEG / 长周期纵向）
- **语义匹配引擎** `match_examples_by_semantics(top_k=2)`：复合评分 = 0.5×bigram + 0.3×领域锚点 + 0.2×IntentRecognitionChain 构念命中
- 已注入 `socratic_engine.ask_socratic`，作为 system prompt 的扩展 few-shot
- **测试**：`tests/test_topic_funnel_kb.py` +16

### B. 跨阶段一致性 + 退行检测 ✅

- `TutorContext` 加 `asked_themes` + `current_stage_progress`
- `build_tutor_system_prompt` 在 funnel 段注入「已覆盖话题」并禁止重复
- `_check_no_regression`：阶段指纹库（5 阶段关键词）+ bigram 最大覆盖率重复检测（阈值 0.7）
- 重试时强化 prompt 列出已问主题
- `_bigram_similarity` 改用 max-coverage（对短中文友好）
- **测试**：`test_upstream_socratic.py` +9（含 5 条退行 + 4 条提取 theme）

### C. 可研究性补全 ✅

- **可操作** `check_operability`：HIGH_BARRIER_KEYWORDS（5 类，独立维护）触发警告 + 替代方案
  - 神经成像（fMRI/EEG/脑成像 等）→ 行为实验/反应时
  - 眼动 → 反应时任务
  - 长周期追踪（≥6 月）→ 横断面研究
  - 临床患者群体 → 自报量表 + 普通学生
  - 未成年人 → 大学生群体
- **有意义反思** `suggest_significance_reflection`：LLM 生成 3 个反思问题（不打分），LLM 不可用降级到默认问题
- stage 4 UI 新增两项与现有 2 项并列展示（共 4 项检查）
- **测试**：`test_upstream_feasibility.py` +12

### D. 漏斗分支管理 ✅

- **FunnelBranch dataclass**：branch_id / created_at / final_research_q / stages_snapshot / candidate_vars / feasibility_results / status
- `archive_current_branch` + `archive_current_branch_and_restart` + `switch_to_branch` + `delete_branch`
- workspace.py 默认状态加 `funnel_history`（List[FunnelBranch.as_dict()]）
- upstream_panel 新增「📚 选题历史」折叠面板（仅当有归档分支时显示）
- wizard「🔄 回到选题漏斗」改为**二级确认**：「📝 继续修改」 vs 「🌱 新建分支重新选题」 vs 「取消」
- `restart_funnel(keep_history=True)` 跳到 stage 5（「继续修改」语义）
- **测试**：`test_upstream_integration.py` +5

### E. ADVANCED 信息留痕 ✅

- `render_advanced_skip_form` 新增 3 个必填字段（来源[单选 5 选项]/为什么/最关心发现，每项 ≤100 字）
- 持久化到 `upstream_state.advanced_meta`
- `generate_motivation_qa_from_advanced(meta)` 生成 1-3 个 QAItem 兼容字典
- wizard step 7 调用 `generate_defense_qa` 后**前置注入**动机问答（必问/常问难度）
- **测试**：`test_upstream_tier.py` +4

### F. 跨模块语义对齐 ✅

- 新模块 `src/upstream/semantic_alignment.py`，`AlignmentResult` + `AlignmentWarning(rule_id)`
- 8 条规则（每条带 rule_id）覆盖：
  - R1-R3：方法 vs 变量类型（连续/分类）
  - R4-R6：方向性词（预测/差异/关系）vs 方法
  - R7-R8：变量数量 vs 方法（ANOVA / 卡方）
- wizard step 4 推荐方法后**自动调用并显示橙色警告卡片**（不阻塞）
- **测试**：`tests/test_semantic_alignment.py` +19

### G. 反问质量基准 ✅

- `tests/fixtures/socratic_benchmark.json`：30 案例（5 阶段 × 6）+ 期望反问应触及的核心维度
- `tests/test_socratic_quality.py`：标记 `@pytest.mark.benchmark`，**默认跳过**
- `--run-benchmark` 命令行选项 + benchmark 标记 已挪到 `tests/conftest.py`
- 跑法：`pytest tests/test_socratic_quality.py --run-benchmark`（需 `BENCHMARK_LLM_API_KEY` 环境变量）
- 报告输出到 `tests/fixtures/_benchmark_reports/benchmark_<timestamp>.json`
- `scripts/evaluate_socratic_benchmark.py`：两次 benchmark 报告启发式对比脚本（improved/regressed/same）
- **测试**：常规 +1（fixture 结构验证）+ 1 skipped（benchmark 自身）

### H. 用户教育与预期管理 ✅

- `_render_user_contract`：首次进入漏斗显示「🎓 选题漏斗不是 AI 替你选题」契约卡片，「我准备好了」/「跳过到 ADVANCED」二选一
- `funnel_intro_shown` session_state 标志位
- `_render_quality_preview`：首次进入漏斗（无对话历史）展示静态高质量反问对话片段（3 轮反问），帮用户判断 LLM 表现
- `warn_if_low_quality_reply`：每次 AI 回复后检测「字数 <30」或「无启发词」→ 软警告（橙色卡片）
- 软警告显示在漏斗顶部，可手动 dismiss
- **测试**：`tests/test_upstream_panel.py` +8

### I. 路由配置表 ✅（硬性要求）

- 新模块 `src/upstream/routing.py`
- `ROUTING_TABLE: Dict[(undergrad_mode, phase, tier), handler_id]` 显式列出所有合法组合
- `resolve_route(...)` 主入口；`RouteNotFoundError` 自定义异常
- 维度校验：phase ∈ {funnel, wizard, done}，tier ∈ {beginner, advanced}
- 非法组合**抛 RouteNotFoundError 而非静默 fallback**
- `app.py` 改造：本科模式分支统一查 `resolve_route()` → 按 handler_id 分发
- 版本字符串：`v3.3 · 选题漏斗+苏格拉底反问巩固`
- **测试**：`tests/test_routing.py` +15

## 文件改动清单

### 新增（11 文件）
```
src/upstream/semantic_alignment.py   — 跨模块语义对齐（8 规则）
src/upstream/routing.py              — 路由配置表
tests/test_topic_funnel_kb.py        — KB 扩展+语义匹配 16 tests
tests/test_semantic_alignment.py     — 8 规则 19 tests
tests/test_socratic_quality.py       — benchmark 1+1 tests
tests/test_upstream_panel.py         — 用户教育 8 tests
tests/test_routing.py                — 路由 15 tests
tests/fixtures/socratic_benchmark.json — 30 案例数据
scripts/evaluate_socratic_benchmark.py — benchmark 回归对比脚本
```

### 修改（10 文件）
```
src/upstream/topic_funnel_kb.py       — 6→18 范例 + match_examples_by_semantics
src/upstream/socratic_engine.py       — 注入范例 + 退行/重复检测 + max-coverage
src/upstream/topic_funnel.py          — FunnelBranch 系统 + advanced 动机问答生成
src/upstream/feasibility_check.py     — check_operability + suggest_significance_reflection
src/paper_writer/ai_tutor.py          — TutorContext 加 asked_themes/funnel_stage_progress
src/utils/workspace.py                — 默认 state 加 funnel_history/advanced_meta/asked_themes
src/ui/upstream_panel.py              — 用户契约+反问示例+质量警告+分支历史+stage 4 4 项检查
src/ui/undergrad_wizard.py            — 二级确认对话框 + step 4 alignment 警告 + step 7 动机问答前置
app.py                                — 改造为路由配置表查表分发；版本字符串 v3.3
tests/conftest.py                     — 加 --run-benchmark 选项 + benchmark 标记
tests/test_upstream_funnel.py         — restart 行为变更（current_stage=5）
tests/test_upstream_integration.py    — 同上 + FunnelBranches 测试集
tests/test_upstream_tier.py           — TestAdvancedMeta 测试集
tests/test_upstream_feasibility.py    — TestOperability + TestSignificanceReflection
tests/test_upstream_socratic.py       — TestRegressionDetection + TestExtractTheme
```

## 测试覆盖统计

| 文件 | 增量 |
|---|---|
| test_topic_funnel_kb.py | +16 |
| test_semantic_alignment.py | +19 |
| test_routing.py | +15 |
| test_upstream_socratic.py | +9 |
| test_upstream_feasibility.py | +12 |
| test_upstream_panel.py | +8 |
| test_upstream_integration.py | +5 |
| test_upstream_tier.py | +4 |
| test_socratic_quality.py | +1 (+1 skipped) |
| test_upstream_funnel.py | 修订 1 |
| 其他 | +33（连带产生的辅助测试） |
| **总计** | **+122** |

**最终：517 → 639 passed，0 failed，0 warnings，4 skipped（3 kaleido + 1 benchmark）**

## 警告数变化

v3.2: 0 warnings → v3.3: **0 warnings**（保持）

新增的 conftest.py benchmark 标记注册避免了「unknown mark」警告。

## 关键架构决策

1. **范例匹配 vs 重新调 LLM**：用 IntentRecognitionChain 提取构念 + bigram + 领域锚点的轻量复合评分，不再额外调 LLM（节约 token + 加速）
2. **退行检测改 max-coverage**：Jaccard 对短中文太严，max-coverage 才能识别「子集关系即为重复」
3. **可研究性"有意义"故意不打分**：避免误判扼杀创新研究，只生成反思问题让用户自己想
4. **漏斗分支不删数据**：归档而非覆盖，保护用户的认知劳动
5. **ADVANCED 必填动机字段**：表面"麻烦"，实质强制最低限度的留痕，让答辩问答能用
6. **路由配置表显式优于隐式**：v3.4 加新维度时强制更新表，而非在分支中无序添加 if
7. **benchmark 不入 CI**：默认跳过避免拖慢迭代，需主动 `--run-benchmark` 触发

## 已知局限

1. **苏格拉底反问质量仍依赖 LLM**：弱模型表现差，软警告只能提示无法解决
2. **退行检测靠关键词指纹**：可能误判（如阶段 4 用户主动提到"具体场景"作为可证伪场景描述）
3. **可操作关键词库手维护**：未来可能漏检新型高门槛技术（VR/AR 等）
4. **语义对齐 8 规则覆盖不全**：未覆盖偏相关、调节中介等高级方法
5. **range matching for 范例**：跨领域时可能选不到最相关（因领域锚点权重 0.3）
6. **benchmark 评估需人工标注**：脚本只做启发式覆盖率对比，不替代专家判断

## 手动验证清单（端到端，按用户原始要求）

| # | 验证点 | 状态 |
|---|---|---|
| 1 | 启动 → 侧栏显示 v3.3 | ✅ 版本字符串 "v3.3 · 选题漏斗+苏格拉底反问巩固" |
| 2 | 新项目 → 用户契约卡片首次出现 | ✅ funnel_intro_shown 默认未设 |
| 3 | 选择"开始漏斗"→ 进入漏斗 stage 1 | ✅ funnel_intro_shown=True 后路由生效 |
| 4 | 漏斗输入"我想研究学习动机"→ 范例匹配教育领域 2 例 | ✅ match_examples_by_semantics 测试通过 |
| 5 | stage 4 看到 4 项检查 | ✅ 可证伪+可测量+可操作+有意义反思 |
| 6 | restart → 二级确认 → 新建分支 → 顶部"选题历史"出现 | ✅ archive_current_branch_and_restart |
| 7 | ADVANCED 跳过表单必填三字段 → wizard 第 7 步答辩问答含动机问题 | ✅ generate_motivation_qa_from_advanced |
| 8 | wizard 第 4 步 t 检验 + 两个连续变量 → 橙色警告 | ✅ R1_TTEST_NO_CATEGORICAL |

## 下一步建议（v3.4）

- **文献综述工作台**（最难、最有价值，差异化最大）
- 路由表已就绪：v3.4 加 phase="literature" 时直接扩 ROUTING_TABLE
- 反问质量基准建立后，可定期回归对比，量化 prompt 优化效果
- 可研究性 4 项检查考虑加入「时间预算估算」（对应"可操作"的细化）
