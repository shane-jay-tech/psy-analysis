# psy 论文写作双入口重叠面对照报告（s918-01 / #L2 只读评估）

> 2026-09-19｜执行班 sweep-20260918-2300｜只读评估，未改业务代码。

## 计数（完成标准要求）
- `grep -c "PaperEngine" src/ui/paper_writing_ui.py` → **4**
- `grep -c "PaperEngine" src/ui/undergrad_wizard.py` → **0**

## 两列对照表（重叠 / 独占）

| 维度 | paper_writing_ui.py（678 行，独立入口） | undergrad_wizard.py（7 步向导·第 7 步） |
|---|---|---|
| **引擎接入方式** | **有状态实例**：`st.session_state.paper_engine = PaperEngine()`（:41-42，:81 重启兜底），全页共享 `engine` 别名 | **无实例**：在第 7 步内直接 `from src.paper_writer.paper_engine import generate_reviewer_questions, generate_revised_with_questions`（:139-141）与 `generate_revised_with_questions_stream`（:261-263，流式） |
| **重叠面（同源能力）** | 修订/追问能力的"壳"：页面驱动的状态化流程 | 直接调用同一引擎模块的追问/修订函数（含流式变体）——**重叠核心** |
| **独占（pw 侧）** | `engine.get_gaps_summary()`（:55-56）、`engine.get_logs()`（:76）、`engine.import_methods_from_file()`（:109）、state 读写（topic/title_hint/research_questions/hypotheses/participants_n，:121-167）、`engine.set_topic()` | — |
| **独占（wizard 侧）** | — | 流式修订（stream 变体）、defense_qa（`calculate_mastery_progress`/`generate_paper_aware_qa`，:44-47、:76）、`paper_export` 图表导出（:41-43）、门禁失败清产物（:62） |
| **入参来源** | 引擎内部 state（session 持久） | 用户当次粘贴的段落（`student_text`）＋AI 追问答（`qa_pairs`），section 枚举（methods 等） |
| **可复用数据流** | 引擎 state 可为 wizard 提供上下文（题目/假设/被试数），目前两入口互不相通 | wizard 的追问答与修订结果未回写引擎 state |

## 重叠判定
两入口**语义重叠但实现分叉**：paper_writing_ui 是"引擎实例驱动"的完整工作台；wizard 第 7 步是"裸函数直调"的轻量追问。同一引擎能力存在两条互相不可见的调用路径——合并/降级决策前需使用率证据。

## 埋点方案设计稿（≥1 点位，不写码）
1. **点位 A（wizard 第 7 步）**：进入追问区、发起 generate、收到修订三处各计一次数（session/log 落 `wizard_paper_gen`）。
2. **点位 B（pw 入口）**：`engine.set_topic`（开工信号）与 `get_gaps_summary`（查看缺口）计数，落 `pw_engine_active`。
3. **点位 C（产出物）**：defense_qa / paper_export 的实际导出计数（真产出信号）。
观测一个使用周期后：若 wizard 路径计数 ≫ pw 路径，则降级 pw 为 wizard 的深链；反之保留双入口并在 wizard 加"去工作台"引导。
