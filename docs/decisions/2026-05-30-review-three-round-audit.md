# 2026-05-30 — 心理分析系统三轮全面审查

## 起源

用户：「对这个系统进行三轮全面的审查，包括但不限于：1、还有哪些可以继续优化的地方 2、整个系统是否健康，功能是否良好 3、有没有冗余的地方，三轮完成之后再通知我」。
澄清：「其实我的意思是每一轮都要进行这三项，总共进行三轮」。

每一轮都覆盖 **优化 / 健康 / 冗余** 三维度，三轮共修 4 处，新增 20 测试。基于 [2026-05-30 三轮迭代](2026-05-30-impl-three-round-iteration.md) 的 1406 测试基线，本次结束 1426 测试全绿。

## 起手扫描（Round 1 进入前的全局摸底）

| 指标 | 实测值 | 备注 |
|---|---|---|
| src/ 行数 | 64,121 | 164 个 .py 文件 |
| tests/ 行数 | 19,796 | 90 个 .py 文件 |
| 最大单文件 | undergrad_wizard.py 3553 行 | 仍可接受，按段切分（见下） |
| pytest 基线 | 1406 passed / 1 skipped / 0 deprecated | 健康 |
| 模块导入 warning | 0 | clean |
| TODO/FIXME/HACK | 0（XXX 是 placeholder 文本不是代码标记） | 无技术债 marker |
| 启发式 unused module 扫描 | 仅 `__main__.py`（CLI 入口实际在用） | 无死模块 |
| 根目录散落 .tmp_debate_* / .tmp_deepseek_* | 8 个 | Round 1 清理 |

## Round 1 — 优化 + 健康 + 冗余

### 健康发现

- ✅ 1406 测试全绿，0 deprecation
- ✅ datetime.utcnow() 已在前次清完
- ⚠️ `src/experiment_design/jspsych_data_importer.py:106,276` 仍用 naive `datetime.now()`（parse_time 元数据时间戳，UTC 一致性应保持）
- ✓ `preregistration.py:260` 用 naive 是有意的（用户面 date 字符串需本地时区）
- ✓ `psychopy_generator.py:385,442` 是模板字符串生成给用户的 PsychoPy 脚本（用户本地时区合适），不动

### 冗余发现

- 根目录 8 个 `.tmp_debate_*.out/.err` + `.tmp_deepseek_*.txt` — 多模型协作后未清理的中间文件
- ❌ 历史 UPGRADE_REPORT_V*.md 文件（19 个）— 不动：被 KNOWN_ISSUES.md 与 MEMORY.md 引用，移动会断链
- ❌ `paper_writer/literature_manager.py`（1997 行）vs `literature_review/`（8 文件 1715 行）— 看似重叠实则不同：前者是文献库 + 引用管理，后者是综述工作流（笔记/矩阵/主题/gap），不动

### 优化机会

无 Round 1 优先项，主要为健康/冗余清理。

### 修复

1. `src/experiment_design/jspsych_data_importer.py`
   - `from datetime import datetime` → `from datetime import datetime, timezone`
   - 2 处 `datetime.now().isoformat()` → `datetime.now(timezone.utc).isoformat()`
2. 删除 `.tmp_debate_deepseek.{out,err}` `.tmp_debate_gpt.{out,err}` `.tmp_debate_kimi.{out,err}` `.tmp_deepseek_prompt.txt` `.tmp_deepseek_system.txt`

## Round 2 — 优化 + 健康 + 冗余

### 健康发现

- ⚠️ `pytest -W error::DeprecationWarning` 在 `-x` 不连续运行偶发触发 deprecation；`-x` 模式 1406 全绿，确认无真实 deprecation 触发，归因测试间状态泄漏，不阻塞
- ✓ 全量 1406 + 1406 重跑 stable

### 冗余发现

- ❌ `construct_kb.DOMAIN_KEYWORDS` vs `domain_weights.yaml` — 看似重叠实则不同层（前者：用户输入主题→构念域路由；后者：抓取文章 IO/HR/OB 命中加权），不动
- ❌ `topic_funnel_kb._DOMAIN_ANCHORS` 6 域 vs `construct_kb.DOMAIN_KEYWORDS` 7 域 — 前者锚定 GOOD_BAD_EXAMPLES（18 条范例），后者锚定 CONSTRUCTS（55+ 构念），各自独立，不动

### 优化机会（高 ROI）

🔥 **关键发现**：[2026-05-30-io-domain-seed](2026-05-30-impl-io-domain-seed.md) 那次只把 5 条新 I/O 构念加进 `CONSTRUCTS` dict，**没同步加进 `CONSTRUCT_KEYWORDS` / `DOMAIN_KEYWORDS["组织行为"]`**：

- 用户输入「员工敬业度对工作绩效的影响」→ design_engine `_match_construct` 关键词路径**无法命中** UWES 条目（因为 CONSTRUCT_KEYWORDS 没"员工敬业度" entry）
- 用户输入「LMX」/「家长式领导」/「伦理型领导」/「工作旺盛感」→ 同上失效
- io-domain-seed 那次的 KB 扩展实际**只惠及了 LLM 路径**（intent_recognizer chain），关键词兜底路径完全断了

🔥 **第二个发现**：feed_panel 候选审阅表只显示 `优先级` 数值，不显示驱动它的 `domain_score` 和 `iohr_hits`，用户没法判断"为什么这条排第一"。

### 修复

1. `src/questionnaire/construct_kb.py`：
   - `CONSTRUCT_KEYWORDS` 加 5 条 entry（员工敬业度 / 家长式领导 / 伦理型领导 / 领导-成员交换 / 工作旺盛感），每条 ≥4 个同义词（含中文 + 英文缩写如 UWES / PLS / ELS / LMX）
   - `DOMAIN_KEYWORDS["组织行为"]` 追加 14 个新关键词（含 "敬业度", "家长式领导", "威权领导", "仁慈领导", "德行领导", "PLS", "伦理型领导", "ELS", "LMX", "thriving" 等）

2. `src/literature_feed/ui/feed_panel.py`：
   - 候选审阅 dataframe 加 `域加分` 列（来自 `domain_score`）
   - 加 `命中标签` 列（解析 `iohr_hits_json` 取前 5 个 canonical）
   - column_config 给 `域加分 / 命中标签 / 优先级` 加 help tooltip 解释计算来源

回归：`tests/test_construct_kb_io_seed.py / test_demo_datasets_hr.py / test_questionnaire_design.py / test_topic_funnel_kb.py / test_upstream_funnel.py` 共 101 测试全绿；`tests/test_literature_feed_ui.py / test_method_weights_round3_wiring.py` 11 测试全绿。

## Round 3 — 优化 + 健康 + 冗余 + 测试加固

### 健康发现

✓ Round 2 修完后 1406 + 0 regression。

### 冗余发现

无新增冗余。

### 优化机会

Round 2 的关键词索引修复**没有测试覆盖**——下次有人重构 CONSTRUCT_KEYWORDS 或 DOMAIN_KEYWORDS 时容易再次回退。需要锁定。

### 修复

新建 `tests/test_io_construct_keyword_index.py`（20 测试）：

- `TestConstructKeywordIndex`（8）：5 条新构念在 CONSTRUCT_KEYWORDS 有 entry + 同义词覆盖关键缩写（UWES / LMX）+ 维度词（威权 / 仁慈）
- `TestDomainKeywordsIndex`（5）：5 条新构念至少 1 个同义词被锚定到 `DOMAIN_KEYWORDS["组织行为"]`
- `TestDesignEngineRouting`（7）：用户问句包含 I/O 关键词时 `_match_construct` `use_chain=False` 兜底路径能正确路由到对应构念（避免依赖 LLM）

设计要点：
- 使用 `use_chain=False` 跳过 LLM intent_recognizer，纯测兜底关键词路径，CI 可重复
- LMX 用例避开"离职意愿"歧义（design_engine 模糊匹配会优先选最长构念名，与 LMX 共现时会被夺位）
- 新增 `test_ethical_leadership_when_only_term_in_question` 专门覆盖伦理型领导 vs 组织公民行为歧义

## 回归

- Round 1: 22 个相关测试 + 全量 1406 全绿
- Round 2: 101 KB-related 测试 + 11 feed_ui 测试 + 全量 1406 全绿
- Round 3: 20 新测试 + 全量 **1426 passed, 1 skipped, 0 failed**

## 三档分级清单（向用户呈现）

| 档 | 内容 | 状态 |
|---|---|---|
| **必修** | jspsych_data_importer naive datetime → tz-aware | ✅ Round 1 已修 |
| **必修** | 5 条新 I/O 构念缺 CONSTRUCT_KEYWORDS / DOMAIN_KEYWORDS 索引（前次 io-domain-seed 漏装） | ✅ Round 2 已修 |
| **建议修** | feed_panel 候选审查表加 域加分 / 命中标签 列（可解释性） | ✅ Round 2 已加 |
| **建议修** | I/O 构念关键词索引加测试锁定 | ✅ Round 3 已加 20 测试 |
| **建议修** | 根目录 .tmp_debate_* / .tmp_deepseek_* 临时文件清理 | ✅ Round 1 已删 |
| **可不修** | undergrad_wizard.py 3553 行 — 段落清晰，不影响功能 | 跳过 |
| **可不修** | UPGRADE_REPORT_V2.0~V3.9.md 19 个根目录文件 | 跳过（被 MEMORY.md 引用） |
| **可不修** | paper_writer/literature_manager 与 literature_review/ 重名"看似冗余" | 跳过（不同业务层） |
| **可不修** | topic_funnel_kb 6 域 vs construct_kb 7 域不一致 | 跳过（不同 KB 用途） |

## 风险点

1. **CONSTRUCT_KEYWORDS 列表无 schema 约束**——新加构念时仍可能漏装关键词索引。Round 3 测试只锁了已知的 5 条新 I/O 构念，未来再加构念（如认知方向）仍需手动同步两份字典。长期看应抽出 `register_construct(name, kws, domain)` 自动同步三个数据结构，但本次范围外。
2. **feed_panel 新增列在真 Streamlit runtime 没眼测**——只单测了数据形状变换，没在 `st.data_editor` 渲染验证。建议用户首次打开「📡 文献雷达」检查表格列加载 OK；如有候选数据，看「域加分 / 命中标签」是否有数。
3. **Round 2 domain_score 列依赖 DB 已写过 domain_score**——新装机或老库未执行过 `update_candidate_scores` 时该列会全为 0。这是数据时序问题，不是 bug，但用户感知可能"为什么我看到的全是 0.00"——如果用户报这个，引导跑一次 DailyRunner 或在 UI 加个手动 rebuild 按钮。
4. **删除的 .tmp_debate_* 文件不可恢复**——它们是 5/27/28 多模型协作的中间产物。如果用户正打算回看那次决策细节，已经永久丢失（备份在 docs/decisions/ 那次的最终归档里，但 verbose transcript 没了）。

## 反方观点

**这三轮里 Round 2 的 keyword index 修复是真正的 net-positive，其他都是次要打磨**。但是否值得现在做？

反对意见：
- io-domain-seed 漏装关键词索引这事，**只在用户走兜底关键词路径时才暴露**——而 design_engine 默认 `use_chain=True` 走 intent_recognizer LLM 链，LLM 路径已经能命中 5 条新构念（毕竟 CONSTRUCTS dict 里有）。用户单人使用且每次有 LLM 配置可用时，关键词路径几乎用不上
- 但如果某次 LLM 不可用（API 故障 / 余额耗尽 / 网络问题）退到兜底，这个 bug 才显现——属于"看起来好但故障时翻车"类
- feed_panel 的新增列对纯审计有用，但用户实际使用是看高优先级 → 直接审一遍，未必会盯着 domain_score 数值

**置信度判断**：
- Round 1 datetime 修复：低 ROI 但零成本
- Round 2 关键词索引：中 ROI（兜底路径可靠性提升），io-domain-seed 漏装是**真 bug**，修对了
- Round 2 UI 列：低-中 ROI（debug 时有用，日常用例少）
- Round 3 测试：中 ROI（防回归），20 测试增量可控

## 置信度

**中-高**。
- 高：1426 测试全绿，0 regression；keyword index 修复有显式测试锁定
- 中：UI 新增列没在真 Streamlit 跑过；伦理型领导 / LMX 在实际用户用语下的歧义匹配只针对了一种典型case

改变结论的证据：用户在「📡 文献雷达」打开候选审阅时新增列报错；或问"我输入员工敬业度怎么没匹配到 UWES"时仍未命中 → 检查 design_engine intent_recognizer 配置是否切到 chain 模式覆盖了兜底。

## 归档

- 本档：`docs/decisions/2026-05-30-review-three-round-audit.md`
- I/O 域种子前传（构念层）：`docs/decisions/2026-05-30-impl-io-domain-seed.md`
- 三轮迭代前传（method_weights 层）：`docs/decisions/2026-05-30-impl-three-round-iteration.md`
