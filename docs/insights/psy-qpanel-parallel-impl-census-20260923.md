# psy 问卷设计页两份平行实现漂移普查（s923-22，只读）

> 班次 `qoder-executor-20260923-0022-psy12`｜生成 2026-09-23 13:0x｜cwd `D:\code\psy-analysis`
> **本档零改动生产码**：`git status --porcelain` 中 `src/` 与 `app.py` 的改动归属他班在途（见文末「零改动自证」）。
> 任务来源 `zcode-bridge/inbox/s923-22.task.md`。产物按纪律档 §廿一 走 `LITERATURE_FEED_DATA_ROOT` 沙盒，未跑 AppTest。

---

## 〇、一句话结论

`src/ui/questionnaire_panel.py::render_questionnaire_page()` 与 `app.py:1556-2308` 的「📋 问卷设计」分支**确实是两份平行实现**，
但**漂移面比上游报告说的小且方向相反**：两版 93.6% 的行逐字相同，实质行为差异只有 **1 处（pending 计时/时钟异常面）**，
其余 3 处是**结构差异（行为等值）**。真正要紧的不是"哪份代码旧"，而是——
**panel 侧的 s921-07／s922-02 两个修复在现役 app 里从未生效**（因为 panel 零生产调用方），
而 panel 作为独立文件**天然进不了按文件记账的全局导出门禁**，这就是 HEAD 那条在册红（待人工 81）的根因。

⇒ **裁决焦点不是"合并哪份"，而是"片 7 接线前，panel 是测试替身还是待上线本体"**。本文末节给两案。

---

## 一、锚点复核（任务书前提逐条验，含否证）

| # | 任务书/上游前提 | 实测 | 判定 |
|---|---|---|---|
| A1 | `src/ui/questionnaire_panel.py:64`「def render_questionnaire_page():」 | 现在 **:65**（`rg -uu -n` → `src\ui\questionnaire_panel.py:65`） | ❌ **漂移 +1 行**（s922-138/139 刷齐时顶部 `import html` 占位所致） |
| A2 | 「`render_questionnaire_page()`（**838 行**）」（s922-102 遗留 1 原话） | AST 实测 `lineno=65, end_lineno=878` ⇒ 函数体 **814 行**；文件 **878 行** | ❌ **否证**：838 既不是函数长度也不是文件长度，是 s922-102 当时盘态留痕。现值以本档为准 |
| A3 | 「该函数**全仓零生产调用方**」 | `rg -uu -c render_questionnaire_page` 全仓：`src/` **1**（即定义本身）、`app.py` **0**、`tests/` **9**、`docs/` **4** | ✅ **坐实**（src 侧唯一命中就是 `def` 行） |
| A4 | 「panel 侧用 `classify_questionnaire_sub_mode()`，app.py 侧用 `_q_sub_mode.startswith("📤")`」 | panel :77-82 用函数；app :1576/:1580 用字面 `startswith` | ✅ 坐实（但**行为等值**，见 §三 D2） |
| A5 | 隐含前提：「逐段比对**子模式分类、导出、XSS 处理**」三个维度会有差异 | 导出块（app 2245-2304 vs panel 816-875）与 XSS 面（`html.escape` 11 处 + `questionnaire_report_to_html_fragment`）两侧**逐字相同**（见 §三 D4/D5） | ❌ **部分否证**：任务书点名的三维里，**导出与 XSS 两维零漂移**，只有子模式分类是结构差异。真正的行为漂移在任务书**没点名**的 pending 计时面（§三 D3） |
| A6 | s922-102：「侧栏块 `:86-140` 与迁移前逐行等值」 | panel `with st.sidebar:` 块 :88-141 vs `src/ui/settings_sidebar_panel.py` 同名块 :26-79，dedent＋去空行/注释后**仅 3 行不同**，且全部是 `st.session_state` → 形参 `session_state` 的改名 | ✅ 坐实（现仍是**行为等值副本**；panel 未改指新模块） |

---

## 二、两版规模与同源证据

复现：本档用的比对脚本留在 `tmp/s923-22/`（已 gitignore，`.gitignore:29`）。

```
app.py   分支体 1557-2308：752 行原始 / 664 行（去空行与整行注释）
panel.py 函数体    67-878：813 行原始 / 717 行（同口径）
difflib.SequenceMatcher(line-list) ratio = 0.9356   非相等 opcode 组 = 9（全部列于 §三）
```

- panel 比 app **多 53 个有效行**，全部来自：pending 计时/时钟异常分支（+19）、内联侧栏（+44，app 侧只有 2 行调用）、`elif elapsed is None`／`elif clock_anomaly` 两支。
- panel 比 app **少 9 行**：`from src.questionnaire.*` 的分支内懒导入（panel 挪到模块级 :9-19）。
- **交互骨架普查两侧一致**：`st.stop()` 3／`st.download_button` 3／`st.spinner` 1／`_DummyContext` 1；
  `st.rerun()` app 分支内 7 + `settings_sidebar_panel.py` 内 1 = **8**，panel **8** ⇒ **等值**（别按单文件计数误判成漂移）。
- `st.session_state` 写键集合：panel 6 键 = app 分支 5 键 ∪ 侧栏模块 1 键（`language` 在侧栏模块里）⇒ **零键位漂移**。

---

## 三、差异矩阵（6 维度；只有 D3 是行为漂移）

| # | 维度 | `app.py:1557-2308`（**现役**） | `src/ui/questionnaire_panel.py:67-878`（**零调用方**） | 类型 | 用户可见差异 |
|---|---|---|---|---|---|
| **D1** | 引擎导入点 | 分支内懒导入（:1557-1565）：`design_questionnaire` / `design_questionnaire_llm_async` / `report_generator` 只在选中「问卷设计」模式时进 `sys.modules` | **模块级**导入（:9-19）：任何 import 该模块者（含 pytest 收集）当场加载 `design_engine` | 结构（等价性取决于调用方） | 无（app 侧不变）；**有**——`tests/test_paper_engine_lazy_init.py` 那类「某模块不得出现在 `sys.modules`」式判据对 panel 侧永远更严 |
| **D2** | 子工作流分类 | `_q_sub_mode.startswith("📤")` / `startswith("📊")` 字面串比较（:1576/:1580） | 纯函数 `classify_questionnaire_sub_mode()`（:77，函数体 :29-40 内部**仍是同一串 emoji `startswith`**） | 结构（**真值表逐字相同**） | 无 |
| **D3** | pending 计时 / 时钟接缝 | `started_at = pending.get("started_at") or _t.time()` ＋ `elapsed = int(_t.time() - started_at)`（:1647-1648）；`if elapsed > 90`（:1663）；文案一律 `{elapsed}s` | `started_at = pending.get("started_at")`（不兜底）＋ `compute_pending_elapsed(started_at, _now)` ＋ `pending_clock_anomaly(started_at, _now)` ＋ `elapsed_txt`（:201-205，:227 带 `elapsed is not None` 前置守卫，:229/:231 两个专属分支） | 🔴 **行为**（panel 独有 s921-07 + s922-02 两个修复） | 🔴 **有，且是 3 个**：<br>① `started_at` 缺失时 app 显示「已 0s」（假 0），panel 显示「—」并给「缺少 started_at，耗时未知」<br>② 时钟回拨/跨机时差时 app 给出**负秒**文案「已 -120s」，panel 钳 0 并弹「🕐 时钟异常」警示<br>③ 负秒时 app 的 `elapsed > 90` **永不触发**（premium 档超时警示静默失效），panel 有独立 anomaly 警示补位（s922-139 正是为此补的） |
| **D4** | 导出面（Word/PDF/HTML） | :2245-2304：`_safe_stem` 白名单字符过滤 + `[:60]`、三枚 `st.download_button(on_click="ignore")`、`except Exception as e: st.error(...)` 整块兜底 | :816-875 **逐字相同**（`difflib` 空 diff，见 §二 复现） | 无漂移 | 无 |
| **D5** | XSS / HTML 安全 | `html.escape` 11 处（:1893-1901 研究画像、:2093-2094 摘要表）＋ `questionnaire_report_to_html_fragment`（:2280-2281）；`st.markdown("<br>")` | **同一批行、同一处数**（:464-472、:664-665、:851-852、:172） | 无漂移 | 无 |
| **D6** | 设置侧栏 | 委托 `render_settings_sidebar_panel(st.session_state)`（:1586-1587，s922-102 迁出） | 仍持**迁移前的内联副本** :88-141（46 有效行；dedent 后与新模块仅差 `st.session_state`→形参名 3 行） | 结构（**行为等值**） | 无（当前等值）⇒ **风险在未来**：改侧栏只改新模块时，panel 副本静默落后，成为第三份 |
| **D7** | 门禁记账面 | 文件在 `GATED_EXPORTS`（`tests/test_export_gate_global_scan.py:33-37`）⇒ 三枚问卷下载按钮**被文件级条目顺带放过** | **不在 `WHITELIST_EXPORTS`／`GATED_EXPORTS`／`NEEDS_MIGRATION` 任一张表** ⇒ `test_all_download_buttons_accounted_for` **当场红** | 🔴 记账（非行为） | 无（两版都不调 `export_gate`：app 的门禁调用在 :2323/:2329/:2358/:2370，属论文写作/交付包分支，与问卷分支无关） |

> **D7 是本普查最需要主班知道的一条**：全局门禁的记账颗粒度是**文件级**（`_get_all_download_button_files()` 以文件为键）。
> 所以「panel 未记账」**不代表 panel 比 app 更不安全**——两版问卷导出的安全语义完全一致（D4/D5 已证逐字相同），
> 差别只在 app 被 `"app.py": "主应用论文导出（已接入 export_gate）"` 这条理由**借用**了。
> 反过来：若把 panel 直接挂进 `GATED_EXPORTS`，`test_gated_files_have_export_gate_import` 会因 panel 内零 `export_gate` 字样而红；
> 挂进 `WHITELIST_EXPORTS` 等于**替隐私分类签字**；挂 `NEEDS_MIGRATION` 被 `test_no_pending_migrations`（:156 断言必须为空）挡死。
> ⇒ **三条消红路都超出执行手授权**，与纪律档 §十五 的判断一致，本班一条都没走。

---

## 四、测试引用面（两案成本的真正来源）

| 面 | app 侧（现役分支） | panel 侧 |
|---|---|---|
| 直接引用 `render_questionnaire_page` | **0** | `tests/test_questionnaire_panel_logic.py`（7 处）、`tests/test_questionnaire_panel_charac.py`（2 处） |
| 专属测试件 | 无同名件（`tests/test_app_routes_v6_panels.py:63-65` 已自陈那个同名用例 import 的是**另一个模块** `questionnaire_import_panel`，假覆盖线索） | `test_questionnaire_panel_logic.py` 28 例 ＋ `test_questionnaire_panel_charac.py` 10 例 ⇒ 实跑 **74 passed / 2.99s** |
| 结构钉桩 | 无 | **17 条位置敏感断言**（`test_questionnaire_panel_charac.py`）：函数名列表**精确相等**（:165）、`fn.lineno == 65 and 长度 == 814`（:169）、`st.rerun()==8 / st.stop()==3 / on_click=="ignore" 恰 3 枚`、`st.stop()` 行位 `[81,85,583]`、`lines[76]/[77]/[81]/[35]/[37]` **逐字**、`len(BODY.splitlines())==878` |
| 分支真实执行面 | `tests/test_questionnaire_design.py` 20 例（引擎/报告层，非 UI 分支）、`test_e2e_ui.py:83` `_ready_app("📋 问卷设计")`（**AppTest，纪律档 §廿一 禁跑位**）、`test_navigation_pagemodes_snapshot.py:48` | 同左（不覆盖 app 分支） |
| 侧栏模块哨兵 | `tests/test_settings_sidebar_panel.py` **11 例**（含 :147/:153 反向钉 app.py 必须**恰好一处**调用新模块） | 无（panel 用内联副本 ⇒ 该 11 例对 panel 失明） |

**读数**：现役 app 分支的 UI 层被 AppTest 打到（`test_e2e_ui.py`），但**零结构钉桩**；
panel 有 74 例、其中 17 条钉到行号与逐字文本——**这正是两案成本不对称的原因**：动 panel 结构 = 先付一次「刷桩」税。

复现命令：
```
cd D:/code/psy-analysis
.venv/Scripts/python.exe -m pytest tests/test_questionnaire_panel_logic.py tests/test_questionnaire_panel_charac.py -q   # 74 passed
.venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"                                        # 1 failed / 19 passed / 1 skipped
rg -uu -c render_questionnaire_page src app.py tests docs
```

---

## 五、零调用方是怎么形成的（时间线，全部有码上署名）

1. **抽取**：panel 从 app.py 抽出（文件头 :1「从 app.py 抽取的完整问卷设计流程」），设计稿 `psy-questionnaire-panel-testdesign-20260918.md` §一 已判「**只有一个 763 行渲染函数、页内无可抽纯逻辑**」，§四 要求先做 3 处最小抽取。
2. **抽取落地**：s921-06 抽 `classify_questionnaire_sub_mode`、s921-07 抽 `compute_pending_elapsed`、s922-02 抽 `pending_clock_anomaly`——**三次都只落在 panel**。
3. **接线从未发生**：`docs/insights/psy-apppy-split-roadmap-20260918.md` 修订记录里 **片 7 仍是未迁状态**（该档 :22 行区间 1749-2580/832 行；s923-14 校正后现盘是 1556-2308/752 行）。s922-102 只迁了片 **7a（侧栏）**，且**故意没把函数塞回 panel**——理由写在 s922-102 结果 :18：`test_questionnaire_panel_charac.py:165` 钉函数名列表精确相等，追加函数当场红。
4. **反向刷齐**：s922-138 把 app.py 的导出/下载面**倒灌回 panel**（`test_questionnaire_panel_charac.py:168` 注释记 807 行）、s922-139 给 panel 的 premium 分支补 anomaly 警示（+7 行 ⇒ 现 814）。⇒ **此后 app.py 反而成了较旧的一份**（D3），而 panel 成了"只有测试在读的那份"。

⇒ **漂移根因不是有人改了两处，而是"改进只能落在一处"**：panel 可测（假 st、秒级），app 分支不可测（要 AppTest）⇒ 修复自然落 panel ⇒ 而**用户跑的是 app** ⇒ 修复对线上零生效。这条是本普查最有价值的结论，也是 D3 三个用户可见差异至今仍在的原因。

---

## 六、两案裁决材料

### 案 A：**以 app.py 为准**——panel 降格为「测试替身」或退休

- 做法 A1（最小）：把 D3 的计时面**正向刷回 app.py**（app :1647-1648/:1663/:1660/:1699 共 6 处），并在 app :1586 之后补 `classify_questionnaire_sub_mode` 调用（D2 统一）。panel **不动、不接线**，只把「panel 是待上线本体」这层误解从文档里摘掉。
- 做法 A2（激进）：A1 之后删 panel，`test_questionnaire_panel_*` 两文件（38 例）改指 app.py 分支源码抽取（`inspect.getsource` 拿不到模块级 elif ⇒ 实际不可行，需先把 app 分支包成函数 ⇒ 就变成案 B）。**所以 A2 与 B 同构，不独立成立。**
- **代价**：改 app.py（他班在途禁碰件，须等他班收单）＋ 需要一次 `test_e2e_ui.py:83` 的 AppTest 验收（纪律档 §廿一 沙盒前提）。
- **工时估计**：A1 **约 40-60 分钟**（6 处改动 + 反向刷齐哨兵 + 跑 `-k questionnaire or export_gate`；不含 app.py 让位等待）。风险面：改的是 app.py 主脚本，任何一处 `elapsed` 语义变化会连带 D3 三个文案分支；**须人工先拍板"负秒/缺失态该显示什么"**，属行为改动。
- **门禁**：panel 若退休（文件删除），在册红**自动消失**（扫描器 `os.walk` 扫不到该件）⇒ **但"删一份有 74 例看守的实现"要人工点头**，本班不提。
- 收益：线上立刻拿到 ①②③ 三个修复；重复建设面从 2 份回到 1 份；`test_settings_sidebar_panel.py` 的 11 例仍是唯一侧栏看守（panel 内联副本随之消失）。

### 案 B：**以 panel 为准**——app.py 片 7 剩余部分接线到 `render_questionnaire_page()`

- 做法：app :1556-2308 的 752 行替换为
  `elif mode == "📋 问卷设计": render_questionnaire_page()`（约 3 行，照 s922-102/片 9 `deliverable_center_panel` 的既有模板）。
- **必须先解决的 4 道硬门**（逐条实测）：
  1. **D7 记账**：panel 要进三表之一 ⇒ 三条路都超执行手授权（见 §三 D7 注）⇒ **等人工裁决 81 顺带拍**。
  2. **D1 导入面**：panel 模块级导入 `design_engine`/`llm_engine`/`report_generator`，而 app 分支是懒导入。app.py 全局 `import streamlit` 后即 `from src.ui.questionnaire_panel import ...` 会把这三个重依赖提前拖进冷启动 ⇒ 需改成 panel 内部懒导入或函数内导入，而那会**再动 :165/:169 两条普查桩**。
  3. **D6 侧栏**：接线后 panel 的内联侧栏副本必须改指 `render_settings_sidebar_panel`（否则用户看到两份侧栏）⇒ 动 panel :88-141，`test_questionnaire_panel_charac.py` 的 `len(BODY)==878`／`st.rerun()==8`／`[81,85,583]` **三条桩同走红**（17 条位置敏感断言中受影响的大约 5 条）。
  4. **st.stop() 语义**：app 分支里 `st.stop()` 抛的是 `StopException`（BaseException）终止**整个脚本**；panel 里同样终止整个脚本 ⇒ 等价，但 panel 的 `st.stop()` 前不再走 app 后续的通用尾逻辑。经核 **app :2306-2308 到下一 elif 之间无收尾代码**（:2309 起是注释分隔块）⇒ 本项**无风险**，留此条是为免复核者重查。
- **工时估计**：**约 3-5 小时**（接线 30 分钟 + 上述 1/2/3 三项改造与刷桩 2-3 小时 + 跑 `test_e2e_ui.py` AppTest 与 `-k 'download_buttons or export_gate'` 全局门 30 分钟 + 让位 `app.py` 在途班的等待成本，不可压缩）。
- 收益：片 7 正式收口（路线图最后一个 800+ 行大页），app.py 从 2405 行降到约 **1650 行**，问卷页从此有 74 例结构看守。

### 两案共同的前置（不可跳过）

- `app.py` 正被他班在途修改（本班 `git diff --numstat HEAD -- app.py` = **12/40**，hunk 全在 :139-202 的 startup/heavy_preload 拆分区，**未触及问卷分支**，`git diff -- app.py | rg -c "问卷|questionnaire"` = **0**）。⇒ 两案都要等该件让位。
- 无论哪案，**D3 的用户可见差异今天仍在**：现役 app 仍会显示「已 -120s」「已 0s（缺失态）」并在负秒时静默失去 premium 超时警示。⇒ 这一条可以**独立于两案**先出一个"计时面正向刷齐"小单（＝案 A 的 A1），是本普查建议的**唯一近期动作**。

### 推荐（仅材料，不代裁决）

**先 A1、后 B，且 A1 不等 B。** 理由：A1 是唯一直接止血线上可见缺陷的动作，改动面 6 行、可被 `test_e2e_ui.py:83` 那一条既有 AppTest 验到；
B 的收益是结构性的（app.py 减 750 行）但要过 4 道门、其中 D7 那道**卡在人工裁决 81 上**，把止血绑在裁决上不值。
若裁决倾向"panel 只是测试替身"（案 A 的读法），那 A1 之后还应追加一单：把 `test_questionnaire_panel_*` 的 17 条位置桩**降级为语义桩**，否则每改一次 app 都要在 panel 重刷一次行号。

---

## 七、零改动自证

| 判据 | 命令 | 本班开工前（12:4x 现取） | 收工（13:0x 现取） |
|---|---|---|---|
| 生产码未被本班改动 | `git status --porcelain` 全量 splitlines 计数 | **14** 行（` M app.py`/` M pytest.ini`/` M requirements-lock.txt` ＋ 3 `?? docs/insights` ＋ `?? node_modules/` ＋ 7 `?? tests/`） | 见 result「验收情况」（本档与 result 落盘后为 15/16 行，多出的**只有本档与 tmp 件**） |
| 他班在途三件未被本班改 | `git diff --numstat HEAD -- app.py pytest.ini requirements-lock.txt` | `12 40 app.py` / `1 1 pytest.ini` / `6 6 requirements-lock.txt` | 同上（本班不重跑＝同值；本班不写这三件） |
| `src/` 零改动 | `git diff --name-only HEAD -- src/` | 空 | 空 |
| benchmark 不变量 | 逐件 sha256_8 | `3d83f7e9 / dff47515 / 092d61b0 / 909b4799`，mtime 全 ≤09-16 01:21 | **同值**（本班只读） |
| 文献库未被写坏 | `tmp/psy12/feed_guard.py verify`（181 件 sha8/size/mtime） | 沙盒 before 已记 `tmp/psy12/fingerprint.json` | 见 result（本班跑 pytest 时 `LITERATURE_FEED_DATA_ROOT` 指向 `tmp/psy12-feed-sandbox/literature_feed`） |

> ⚠️ 现场观察（非本班所为）：`data/literature_feed/feed.sqlite` mtime 取到 **09-23 12:15:30**、`feed.sqlite-wal` **12:16:18（741,632 B）**、`raw/2026-09-23/*.jsonl` 12:15-12:16 —— 即**本班上工前约 30 分钟有活跃写手**（与纪律档「本仓有并发写手」一致）。本班因此**没有**沿用 §廿一 里"锁原件已被覆盖"的假设，而是重新做了全量 copy2 快照。

---

## 八、新坑（本普查换来，可复用）

1. **「行数锚点」不能跨单沿用**：s922-102 记 838 行 → 现值 814 行（函数）/878 行（文件），一次反向刷齐就让引用它的任务书全部失真。引用 panel 规模一律用 `ast` 的 `lineno/end_lineno`，别引二手行数。
2. **跨文件普查要按"页面路径"而不是"单文件"计数**：`st.rerun()` 单看 app 分支是 7、看 panel 是 8，像漂移；把 `settings_sidebar_panel.py` 的那 1 条算进 app 侧才等值。**把内联副本迁成模块时，所有骨架普查数都会分叉**，任何"两版一致性"判据要先声明分母。
3. **文件级门禁表 × 页面级抽取 = 假红**：全局导出扫描以文件为键，所以"把导出面从 `app.py` 抽成独立模块"这一步**本身**就会让该模块红一次，与新增多少按钮无关。这条对路线图片 5/6/7 的所有后续抽取都成立，**排单时该计入抽取成本**，而不是当成"抽取者没接门禁"。

---

## ⚠ 勘误横幅（2026-10-02 追加，s930-40；append-only，正文一字未改）

> 两处数字经现值复核订正（s927-53 遗留点名）：
>
> | # | 原文 | 现值（2026-10-02 复核） | 取证命令 |
> |---|---|---|---|
> | 1 | `:112` 两测试件「38 例」 | **74 例**（10＋64，与同档 :84/:115/:128 一致——:112 为旧值；**派删件单前以 74 为准**，否则代价少算 36 例） | `python -m pytest tests/test_questionnaire_panel_charac.py tests/test_questionnaire_panel_logic.py --collect-only -q` |
> | 2 | `len(BODY)==878` | **881**（panel 现行 881 行，s927-25 面板补丁在途后增长） | `wc -l src/ui/questionnaire_panel.py` |
>
> **勿按 38/878 旧值引用**；「测试替身」定性维持引用不展开（s927-53 口径）。
