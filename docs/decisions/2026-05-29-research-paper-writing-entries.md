# F1 — 论文写作两入口合并评估（v4.7 重启）

**日期**：2026-05-29
**模式**：单方调研（Opus 直查 + 比对，不打多模型，因为这是结构性评估而非复杂决策）
**Source 任务**：v4.6 redundancy cleanup 中跳过的 F1（paper_writing_ui 594 行 vs wizard 第 7 步重叠）

## 现状摸底

### `src/ui/paper_writing_ui.py`（678 行，挂在 mode "📝 论文写作"）

5-tab 结构：

| Tab | 功能 |
|---|---|
| 1️⃣ 研究信息 | topic/hypothesis/methods 全字段表单 + JSON/Excel 方法信息导入 |
| 2️⃣ 文献管理 | `search_literature_async()` 异步检索（Crossref/Semantic Scholar） |
| 3️⃣ 确认问题 | 生成 gap-fill 提问引导用户补全信息 |
| 4️⃣ 生成论文 | 8 个 section（title / abstract / keywords / intro / methods / results / discussion / refs）整稿生成 |
| 5️⃣ 答辩模拟 | `generate_defense_qa()` |

### `src/ui/undergrad_wizard.py` 第 7 步（~470 行，lines 3100-3570）

| 模块 | 功能 |
|---|---|
| 未完成事项卡片 | `_render_unfinished_reminders()` |
| 论文交付包卡片 | 一键 ZIP（Word + PDF + 图集） |
| Method 草稿生成 | 从 step 5 的 `analysis_output` 抽统计量自动填模板 |
| Result 草稿生成 | 同上 |
| 反问式审阅 | AI 反问引导用户改稿（不替写） |
| AI 助教对话 | `_render_ai_tutor(location="step7")` |
| 答辩 QA（paper-aware） | `generate_paper_aware_qa()` |
| Word 导出 | `export_docx_with_paper()` |

## 重叠 vs 互补

| 功能 | wizard 第 7 步 | paper_writing_ui |
|---|---|---|
| 单次分析 method/result 草稿 | ✅（统计量自动填入） | ✅（手动表单） |
| 答辩 QA | ✅ | ✅ |
| Word 导出 | ✅ | ✅ |
| **完整 8-section 整稿** | ❌ | ✅ |
| **文献检索（异步）** | ❌ | ✅ |
| **gap-fill 确认问题** | ❌ | ✅ |
| **JSON/Excel 方法导入** | ❌ | ✅ |
| **从 wizard analysis_output 自动填** | ✅ | ❌ |
| **AI 反问式审阅** | ✅ | ❌（只有 gap-fill） |
| **AI 助教对话** | ✅ | ❌ |

**关键观察**：两边各有 4 个对方没有的核心功能，重叠只有 3 项（方法/结果/导出），这 3 项也走的不是同一条路径——wizard 自动填，paper_writing 手动填或 JSON 导入。

## 决定：保留双入口（不合并）

**理由**：

1. **场景不同**：
   - wizard 第 7 步 = "我刚跑完一个 t 检验，给我一段 method/result"（单分析、轻量）
   - paper_writing_ui = "我要完整写一篇毕业论文"（多 section、文献、整稿、复用素材）

2. **合并代价 > 收益**：
   - 把 paper_writing_ui 的 4 个独占功能塞进 wizard step 7，会让 wizard 一步变成杂烩，违背"7 步漏斗"的设计初衷
   - 把 wizard step 7 的 method/result 自动填 + 反问审阅塞进 paper_writing_ui，需要重写"接收 analysis_output"的接口，且失去 wizard 的步骤上下文

3. **跨链已存在（已查源码）**：
   - `undergrad_wizard.py:3083` 在 step 6 有按钮 `📝 进入论文写作` → 切到 mode "📝 论文写作"
   - `undergrad_wizard.py:3418` 在 step 7 有按钮 `📝 打开完整论文写作模块` → 同上
   - 用户路径已经是"wizard 写完单分析 → 跳完整论文写作"

## 不做埋点

任务描述提到"+埋点"——当前项目无统计/分析基础设施（没有 Mixpanel / 自建 SQLite events 表）。临时为这一个评估搭埋点系统是 over-engineering。如果未来真的要观察哪个入口被用得多，下次接 events 表时一并加。

## 风险 ≥2

1. **新用户首次面对 mode 列表会困惑**："📝 论文写作" 和 "🌱 本科论文向导（→ 第 7 步写论文）" 看起来都跟论文有关 → 容易选错。当前依赖侧边栏的 caption 区分，新用户体验未做用户测试。
   - **缓解**：留观察，等用户反馈再决定要不要在 mode 选择处加 tooltip 说明。

2. **"反问式审阅"（wizard 独有）和"gap-fill 确认问题"（paper_writing_ui 独有）解决相似问题但用了不同 UX**：未来如果想统一 AI 引导风格，需要选其一推到双方。
   - **缓解**：当前两边都能跑，先不动，等 v5 再做统一。

## 反方观点

DeepSeek 如果在场可能会主张："594 + 470 = 1000 多行带相似关键词的 UI 代码长期会变成两份独立衍化的债，迟早一边修了 bug 另一边没修"。

回应：成立。但合并的代价（重设计两个入口的职责边界 + 必然需要的回归测试）当前不值得。可接受方案是：**把 method/result 模板生成抽成 `src/paper_writer/section_templates.py` 公共函数**，让 wizard 和 paper_writing_ui 都调它——但这是重构动作，留给 v4.8 的 cleanup pass，不在本评估范围。

## 置信度

**高**。源码逐项比对完毕，跨链按钮位置已在 wizard 中找到（`undergrad_wizard.py:3083` / `3418`），结论有代码证据。

会改变结论的证据：
- 用户提出 "我每次写论文都同时开两个 mode 来回切，太烦"
- 真正实测发现 paper_writing_ui 的"文献管理"或"gap-fill 确认问题"几乎没人用 → 那时再降级
- 后期实际加上 events 埋点后，发现两入口使用率比 5:95 → 那时再合并/降级

## 落地

- ❌ 不合并
- ❌ 不降级任何一边
- ✅ 跨链按钮已就位（无需新增）
- ✅ 评估文档归档于此
- 📝 后续：把 method/result 模板抽公共函数 → 列入 v4.8 cleanup 候选
