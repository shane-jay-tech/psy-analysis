# 冗余审计报告 v4.6

**日期**：2026-05-26
**触发**：用户问"系统有没有冗余可精简"
**两路并行**：通用代理（实证 grep 验证）+ DeepSeek 评审官（结构性批判）

---

## 仲裁后清单

### A. 零风险（可立即删，估计 ~1500 行 src + 5 个 tmp + 杂文件）

通用代理 grep 实证 0 引用，DeepSeek 共识：

| 文件 | 行数 | 验证 |
|---|---|---|
| `src/questionnaire/kb_learner.py` | 729 | 仅 tests/test_ui.py 一处 + 自身注释，运行时 0 引用 |
| `src/utils/llm_models.py` | 205 | v4.6 单轨化遗留，已被 `active_config.py` + `quick_models.py` 替代 |
| `src/utils/api_key_store.py` | 131 | v4.3 改读 `.env.local` 后已废 |
| `src/utils/*.tmp.*` (×5) | — | 编辑器崩溃残留 |
| `mk_prompt.py` + `gpt_prompt_v2.txt` | — | v4.6 重构期一次性 prompt 脚本 |
| `requirements_stable.txt` | — | v2.6 旧固定，已被 `requirements-lock.txt` 替代 |
| `reports/self_assessment_v2.5*.md` / `v2.6*.md` | — | v2.x 自评，被根目录 `UPGRADE_REPORT_V*.md` 替代 |
| `reports/snapshots/snap_*.json` | — | 测试残留 |

**对应测试**：`tests/test_llm_models.py`、`tests/test_api_key_store.py`、kb_learner 相关测试可同步删（DeepSeek 提的"双重测试"问题大头都来自这条）。

### B. 中等风险（建议合并，需先看一处再动）

- **`src/literature_review/search.py:153 search_literature_legacy`** — 名字带 legacy，需确认 UI 调的是新还是旧版本。
- **`src/utils/workspace_state.py` 的 `from_legacy_session` / `sync_to_legacy_session`** — v3.4 兼容层。如果用户没有 v3.4 旧档案要加载，可剪。
- **`src/questionnaire/llm_engine_premium.py:638-918` (~280 行) `_design_questionnaire_legacy_pipeline`** — premium 内部的 legacy 分支，需确认主调用路径是否还会走到。

### C. 重大改造（**不建议现在动**）

DeepSeek 提议但风险大、收益不确定的：
- ~~"gateway.py 是死代码"~~ — **DeepSeek 错判**。grep 实证 gateway.py 被 7+ 模块（runner / matrix / themes / defense_qa / paper_engine / feasibility_check / ai_content_review）通过 `from src.llm_gateway import llm_chat` 间接使用。**保留**。
- ~~"删 llm_engine.py 全文"~~ — **DeepSeek 错判**。app.py:39 还在 import `design_questionnaire_llm_async / cancel_design_request / CancelledLLMError`，是 base 路径主入口。premium 是高质量分支，**两条路径都活的**。
- 文献包合并（`literature_review/` + `paper_writer/literature_*` 共 ~6000 行）— DeepSeek 强烈推。代码确实跨包但功能不完全重叠（综述 vs. 引文库管理）。改动大，建议有具体痛点再动。
- workspace 4 文件合并（workspace + workspace_state + project_manager + autosave）— 1496 行管"项目状态"。耦合深，单用户场景下确实过度，但现在能跑，改动大。
- paper_writing_ui (594) ↔ undergrad_wizard (3553) "二选一" — 两个是独立模式入口（论文写作 vs. 7 步向导），不是双轨。代码内部可能有重叠的"研究信息表单"等元素，但作为模式入口都有用户价值。

---

## 体积大但合理（保留）

- `src/ui/undergrad_wizard.py` 3553 行 — 7 步向导主 UI，按 step 切章节合理
- `src/paper_writer/literature_manager.py` 1997 行 — 文献管理核心
- `src/paper_writer/defense_qa.py` 1023 + `defense_qa_kb.py` 1713 — 不是双轨，`_kb` 是数据/模板被 qa 单向 import

---

## 推荐执行顺序

1. **第一刀（零风险）**：删 A 类 8 项 + 对应 3 个测试文件 → 估计 -1500 行 src，-200 行 test，零回归
2. **第二刀（中风险）**：审 B 类 3 个 legacy 函数，grep 调用方再决定 → 估计 -300~500 行
3. **不动 C 类**：DeepSeek 的 2 个错判已澄清，3 个真重叠的改造工作量太大，等具体功能要改时顺手清

总潜在精简：第一刀 + 第二刀 ≈ -2000 行，约占 src 总量的 5%。比 DeepSeek 估的 30% 保守，但每一行都可验证。

---

# Part 2 — 功能冗余（用户视角）

代码冗余看的是"两份代码做同一件事"，功能冗余看的是"用户能看到几个入口做同一件事"。基于 app.py mode 路由 + 侧栏 toggle 的实际拓扑：

## 系统暴露的入口拓扑

**主控开关**（侧栏顶部）：`🎯 一键全流程引导` toggle

- **开** → `undergrad_wizard` 7 步：研究信息→上传数据→查看结构→选方法→运行→结果→写方法+结果（含答辩模拟）
- **关** → 5 个独立 mode：
  1. 🌱 选题与文献综述（选题漏斗 + 文献综述工作台）
  2. 📋 问卷设计（AI 设计 / 上传预审 子工作流）
  3. 🧪 实验设计
  4. 📈 数据分析
  5. 📝 论文写作

## 真功能冗余（用户视角）

### F1. 论文写作有两个独立入口（最严重）

- 关 toggle → 「📝 论文写作」mode → `paper_writing_ui.py` (594 行)，要用户重填研究主题/方法/文献 4 节再生成
- 开 toggle → wizard 第 7 步「写方法+结果」，复用 wizard 已收集的所有数据生成

两条路径**最终都调 `PaperEngine`** 生成论文。差别只是：独立入口要重填一遍信息；wizard 入口已有数据。

**对单用户的实际意义**：用户大概率只会用其中一个。如果总是开 toggle，paper_writing_ui 永远摸不到。如果总是关 toggle，wizard 第 7 步永远摸不到。

**建议**：保留 wizard 第 7 步（数据复用，体验好），把 paper_writing_ui 降级为 wizard 内部的"独立生成视图"或干脆删掉。预计省 594 行 UI + 至少几百行 PaperEngine 重叠调用。

### F2. 保存状态有 3 套机制并存（认知负担最大）

| 机制 | 入口 | 触发时机 |
|---|---|---|
| 手动 JSON | 侧栏「📁 项目 · 工作区」`📥 保存工作区` 按钮 | 用户主动点 |
| autosave | `trigger_autosave()` 在 wizard / 文献综述 / 渲染器 5+ 处隐式触发 | 写到当前项目 |
| 多项目隔离 | `project_manager` + `ensure_active_project_on_first_visit` | 切项目时 |

3 套都活着，单用户 99% 时间只用一个项目。autosave 已经在写"当前项目"的快照（注释说"语义从全局 autosave 变为当前项目"），意味着**手动保存 + 项目级 + autosave 的存储位置已经合并**，但 UI 层还露 3 个入口。

**建议**：把侧栏「📁 项目 · 工作区」手动保存按钮改成"导出当前项目快照"（语义对齐 autosave），删掉多项目切换 UI（单用户 99% 一个项目就够），保留 autosave 静默工作。预计省 ~400 行 UI + project_panel 大半。

### F3. 答辩模拟只挂 wizard，独立 mode 用户摸不到

- wizard 第 7 步内嵌答辩模拟（undergrad_wizard.py:1158）
- 独立 mode 5 个里没一个有答辩入口

不是冗余，但是**入口缺失**——关 toggle 的用户做完分析、写完论文，没法做答辩。

**建议**：要么把答辩独立成 mode-6，要么在「📝 论文写作」mode 里加个"答辩模拟"子 tab。

## 不算冗余但容易误读

- **wizard 4-6 步 vs 独立「📈 数据分析」**：前者是新手引导版，后者是熟练用版。代码层重叠大但 UX 上分两个用户群（新手 vs. 熟练）是合理的，**不建议合并**。
- **「问卷设计」mode 内 2 个子工作流（AI 设计 / 上传预审）**：互补不重叠。
- **「选题与文献综述」独立入口**：wizard 不做这两块，所以不重叠。

## 推荐执行顺序（功能层）

1. **F2 先动**：autosave 已经接管语义，删手动 JSON 按钮 + 多项目 UI，省 UI 复杂度
2. **F3 跟上**：把答辩模拟挂到独立 mode（轻改动）
3. **F1 最后看**：paper_writing_ui 是不是真的有用户用——可以加埋点观察 1-2 周再决定

---

## 总结

- **代码冗余**（Part 1）：清死代码 ≈ -1500~2000 行，无功能损失
- **功能冗余**（Part 2）：F1+F2 合并 ≈ -1000 行 UI + 减 3 个入口为 1 个，认知负担显著降低
- **DeepSeek 错判**：gateway.py / llm_engine.py 整删都是错的，已澄清

---

# 执行结果（2026-05-26 当日落地）

## A 类（零风险）— 全部完成
- 删 src/questionnaire/kb_learner.py（729 行）
- 删 src/utils/llm_models.py（205 行）
- 删 src/utils/api_key_store.py（131 行）
- 删 5 个 .tmp 残留 + mk_prompt.py / gpt_prompt_v2.txt / requirements_stable.txt
- 删 reports/self_assessment_v2.5*.md / v2.6*.md / snapshots/snap_*.json
- 同步删 tests/test_llm_models.py / test_api_key_store.py / test_ui.py 的 TestKBLearnerFlow
- 联动修：academic_literature.py / construct_kb_extended.py 注释与 import

**结果**：1260 → 1239 passed（-21 测试，与删除一致）

## B 类（中等风险）— 全部完成
- **B1**：删 search_literature_legacy（0 调用方）
- **B2**：保留 workspace_state.from_legacy_session/sync_to_legacy_session — grep 实证 `tier.py:85` 仍读写 `upstream_state` 字段；名字叫 legacy 但是活跃迁移层
- **B3**：删 _design_questionnaire_legacy_pipeline（276 行）+ 同步移除 design_questionnaire_premium / _async 的 use_direct_mode 参数 + 删 tests/test_llm_engine_premium.py 的 TestOverrideParsedResearch + TestPremiumFlow 中的 2 个 legacy 用例

**结果**：1239 → 1235 passed（-4 测试，B3 直接相关）

## F 类（功能冗余）— F2/F3 完成，F1 跳过
- **F1**：跳过（用户表态可能会用独立论文模式）
- **F2.a**：侧栏「📁 项目 · 工作区」按钮重命名 `保存工作区` → `导出项目快照`，加载区改 `导入项目快照`，加 caption 说明 autosave 已接管日常
- **F2.b**：app.py 删 `render_project_panel()` 调用 + 移除 import；保留 ensure_active_project_on_first_visit 后端，单项目自动 active
- **F3**：paper_writing_ui 增第 5 个 tab「答辩模拟」+ _render_paper_mode_defense_qa 函数（80 行）；从 session_state.plan + analysis_output 自动读取，缺失时提示去「📈 数据分析」mode

**结果**：1235 passed 维持（无新增/删除测试，纯 UI 联动）

## 最终战果

- 总删除：约 -1700 行 src + -100 行 test
- 测试基线：1260 → 1235 passed（-25 个全是被删模块的伴生测试）
- 用户可见变化：
  - 侧栏少 1 个 expander（项目切换 UI）
  - 侧栏「项目 · 工作区」按钮语义对齐 autosave
  - 「📝 论文写作」mode 多 1 个 tab：答辩模拟
