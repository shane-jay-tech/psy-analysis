# questionnaire_panel 渲染页测试设计稿（只读，s918-28）

生成：2026-09-19 00:5x（规划批次标 20260918）｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
口径：**只读设计稿**，`src/` 零改动、未跑任何页、零真实问卷数据。

## 一句话结论

`src/ui/questionnaire_panel.py` 不是「函数太多没测」，而是**只有一个 763 行的渲染函数、页内没有任何可抽出的纯逻辑**：
「纯逻辑可测」这一类实测**空集**。所以本页的测试设计第一步不是写测试，而是**先做 3 处最小抽取**（第 4 节给出签名）。

## 二、实测结构（复现命令见每行末）

| 项 | 实测值 | 复现命令 |
|---|---|---|
| 文件行数 | **790**（与盲区审计一致） | `wc -l src/ui/questionnaire_panel.py` |
| 顶层 `^def` | **1** | `grep -c "^def " src/ui/questionnaire_panel.py` |
| 嵌套函数 | **0**（`__enter__/__exit__` 属类 `_DummyContext`，各 2 行） | AST 扫描（本稿执行记录） |
| 类 | 1（`_DummyContext`，L21-26） | 同上 |
| `render_questionnaire_page` 函数体长度 | **763 行**（L28-790） | 同上 |
| 用到的 `st.*` 方法种类 | **25** | 同上（widgets 集合计数） |
| `st.session_state` 引用 | **20 处**；属性式写入含 `.language`(L57,L62)、`.questionnaire_design`(L155/214/287/302/308)、`._q_design_pending`(L357)；`get()` 式读 `_q_design_pending`/`_q_premium_mode` | `grep -c "st.session_state\." src/ui/questionnaire_panel.py` |
| 回调（`on_click`/`on_change`） | **0** —— 全部交互靠 `st.rerun()` 重入（**9 处**）＋ `st.stop()`（**3 处**：L43/L47/L517） | `grep -n "st.rerun()\|st.stop()" src/ui/questionnaire_panel.py` |
| 子工作流分支判据 | **emoji 前缀串比较**：`startswith("📤")`(L40)、`startswith("📊")`(L44)，两支各自 `st.stop()` 提前终止本页 | `grep -n "startswith" src/ui/questionnaire_panel.py` |
| 进度/等待反馈 | `st.progress(min(1.0, p_pct), text=p_msg)`(L177)、`st.spinner(...)`(L386)、耗时用 `import time` 内联算(L159-165) | `grep -n "progress(\|spinner" src/ui/questionnaire_panel.py` |

锚点复核：`:28` 原文 `def render_questionnaire_page():` **逐字命中**；`docs/insights/psy-test-blindspot-audit-20260915.md:23`
原文 `| 790 | ui.questionnaire_panel | 真盲区：importers=0，Streamlit 页面入口 |` **逐字命中**。

- **importers=0 复核通过**：`grep -rn "questionnaire_panel\|render_questionnaire_page" --include=*.py . --exclude-dir=.venv`
  在 `src/` 与 `app.py` 侧**零命中**，唯一命中在测试侧（见下条）。
- ⚠️ **同名测试是假覆盖线索**：`tests/test_app_routes_v6_panels.py:62` 的 `test_questionnaire_panel_writes_to_state`
  实际 import 的是**另一个模块** `src.ui.questionnaire_import_panel`（数据导入清洗页），
  与本页无关。按函数名做覆盖率归因会把本页误判成「已有测试」——本页确认**零测试**。
  复现：`cd /d/code/psy-analysis && sed -n '62,66p' tests/test_app_routes_v6_panels.py`

## 三、三分类清单

### A. 纯逻辑可测（不依赖 st，可直接 pytest）——**现状为空集**

唯一非渲染代码是 `_DummyContext.__enter__/__exit__`（L22-26，各 2 行 stub，返回值恒 `self`/`False`），
测它没有信息量，**建议不为它写测试**。

> 这一栏为空就是本页的根因诊断：763 行里所有判断、拼串、算术都嵌在 `st.*` 调用之间，取不出来就没法测。

### B. 需「假 st」——`streamlit.testing.v1.AppTest` 可覆盖（仓内已有先例与夹具）

| 测点 | 位置 | 断言面 |
|---|---|---|
| 子工作流 radio 切换 | L34-47 | 选「📤 上传现有题目」/「📊 数据导入与清洗」时**转交外部面板并 `st.stop()`**，主页不再渲染 |
| 语言切换写全局态 | L50-63（sidebar radio `format_func`） | 选语言后 `st.session_state.language` 落值＋`st.rerun()` |
| 模板按钮循环 | L114-121 | 每个模板按钮点击后把该 prompt 灌进输入框并 `st.rerun()` |
| 构念输入＋清空 | L123-156 | 清空按钮 → `session_state.questionnaire_design=None` ＋ `q_request_input` 复位 |
| 高质量模式 toggle | L136-141 | `⭐ 高质量模式` 开关与 `_q_premium_mode` 一致性 |
| 导出区 | L732-745 | 导出格式 radio 选择后下载按钮 `key` 与 label 就位（不断言文件内容） |

先例参照：`tests/test_app_routes_v6_panels.py`、`tests/test_analysis_result_card.py`（`SimpleNamespace` 造 plan），
以及 `tests/conftest.py` 的 `_APP_TEST_FILES` 白名单＋`isolate_streamlit_app_test_storage` autouse 夹具——
**新页面测试必须进该白名单**，否则会污染真实存储。

### C. 需 e2e（跨 rerun、含 LLM 与真实等待）

| 链路 | 位置 | 为什么 AppTest 不够 |
|---|---|---|
| 生成问卷：提交 → pending → 进度/缓存/premium 三分支 → 完成 | L317-393（＋L357 写 `_q_design_pending`、L177 进度、L386 spinner） | 依赖 `time.time()` 差值与多轮 rerun，AppTest 单轮跑不完 |
| 「🔄 用此理解重新生成问卷」 | L484-497 | 改研究意图→回写 pending→再次 rerun，三段式 |
| 报告下载 | L741 | `st.download_button` 产物在 AppTest 里只暴露元信息，落地文件需浏览器 |
| 设计报告渲染（7 页签） | L393-730，`st.tabs`(L639) | 段内还嵌 3 处 `st.stop()`(L517)、多处 `questionnaire_design` 改写 |

## 四、前 3 个最值得测的函数签名（建议抽取，先抽后测）

按「抽出成本 ÷ 测得价值」排序。三条**都不改行为**，只把已有内联逻辑搬到模块级函数，页内改调用。

1. `def classify_questionnaire_sub_mode(choice: str) -> str`（返回 `"ai_design" | "upload_items" | "import_clean"`）
   现状：L40 `if _q_sub_mode.startswith("📤")` 与 L44 `elif startswith("📊")` 两处 emoji 前缀串比较。
   风险：文案改一个字（含 emoji 变体/空格）分支**静默失效**，用户点了上传却仍进 AI 设计页。
   测点：三个真实 label 逐一 + 空串 + 大小写/空白扰动 + 「📤 上传现有题目（预审 + 排版导出）」全串。

2. `def compute_pending_elapsed(pending: dict, now: float) -> tuple[int, bool, bool]`
   （返回 `(elapsed_seconds, from_cache, is_premium)`）
   现状：L159-166 内联 `import time as _t; started_at = pending.get("started_at") or _t.time(); elapsed = int(_t.time() - started_at)`，
   随后 `from_cache = pending.get("from_cache", False)`、`is_premium = pending.get("premium", False)`。
   风险：`started_at` 缺失时**用当前时刻兜底 ⇒ elapsed 恒 0**，进度条永远从 0 开始；键名 `premium` 与属性名 `is_premium` 不一致易错。
   测点：`now` 注入后即可测边界（缺 started_at／started_at 在未来→负数截断与否／三个 get 默认值）。

3. `def resolve_llm_config(active_config: dict | None) -> dict | None`
   现状：L317-322 起，`if design_btn and q_request.strip():` 内联从 `active_config` 单轨化读 LLM 配置（v4.6）。
   风险：这是**唯一决定走不走真实 LLM 调用**的岔口，返回 `None` 时的降级路径直接对用户可见；且 `q_request.strip()` 的空白判定也在同一条件里。
   测点：空串/纯空格 → 不触发；`active_config=None` → 降级值；正常 dict → 透传字段。
   ⚠️ 红线自证：本单**未执行**任何 LLM 调用，只读代码定位。

## 五、落地顺序建议（供日间拍板，本单不动手）

1. 先抽上面 3 个纯函数 → 补 `tests/test_questionnaire_panel_logic.py`（零 st，秒级，预计 12-18 例）；
2. 再开 1 个 `AppTest` 冒烟（进入页面＋切 3 个子工作流＋点清空），**须登记进 `conftest.py:_APP_TEST_FILES`**；
3. C 类链路留 e2e，或在第 1 步抽完后由 `compute_pending_elapsed` 的单测代劳计时面。

按本页 763 行体量，**不建议**追求渲染级全覆盖；先让第 4 节三处岔口有测试钉住，收益最高。

## 六、执行留痕

- 只读命令：`wc -l`／`grep -c`／`grep -n`／`ast.parse`（AST 脚本为一次性，未落盘于仓内）
- `src/` 与 `tests/` 零改动；产出仅本文件
- 执行身份：Qoder 会话直执（非 glmflash），0 桥积分
