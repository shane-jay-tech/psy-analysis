# s927-53 · panel 三枚下载按钮：四路出口的成本与后果（承 s923-22 裁决 81）

生成：2026-09-29 03:5x｜执行班：`qoder-executor-20260929-0345-psy99`｜仓/HEAD：`D:\code\psy-analysis` @ `16cddbb`
性质：**只读裁决材料汇编。零码改动**——未写白名单、未挂 `NEEDS_MIGRATION`、未改判据、未动 `src/ui/questionnaire_panel.py`、未动 `tests/test_export_gate_global_scan.py`。在册红**原样留在盘上**（w58-brief §D 第 1 条口径）。
**涉及隐私分类的取舍（路 1）本班不下判定**——那是人工签字位（纪律档红线）。

上游锚点：`done/s923-22.result.md:70`（待人工 1，承裁决 81）＋ 其 **证据 9**（:63，三表以文件路径为键、三条消红路逐条验不可走）；`done/s923-15.result.md`（在册红原样留 HEAD）；结构案源 `docs/insights/psy-qpanel-parallel-impl-census-20260923.md:17,105-140`（案 A/案 B ＋ "片 7 接线前，panel 是测试替身还是待上线本体"）。

---

## 一、事实底盘（8 条，逐条实测；这是三路成本的共同地基）

**F1 🔴 panel 在生产里零调用者 ⇒ 三枚按钮今天用户点不到。**（三条独立证据正向成立）
① `grep -rn "render_questionnaire_page" --include=*.py .`（排除 `tmp/`、`__pycache__`）全仓仅 **3 处命中**：定义 `src/ui/questionnaire_panel.py:74` ＋ 两枚测试件的模块级 `import src.ui.questionnaire_panel as qp`（`charac:27`／`logic:12`）；`grep -c "render_questionnaire_page" app.py` = **0**。
② `grep -n "importlib\|__import__\|globals()\[\|getattr(.*panel" app.py` → **无输出** ⇒ app.py 不存在字符串路由／动态导入型页面分发，"看不见调用者"不是取证方法造成的假象。
③ `sed -n '1556,1557p' app.py` → `elif mode == "📋 问卷设计":` ＋ `from src.questionnaire.design_engine import design_questionnaire` ⇒ **问卷分支至今仍内联在 app.py**；`wc -l app.py` = **2405**，与 census 档"从 2405 行降到约 1650 行"的基线逐字吻合。
⇒ 与 `psy-qpanel-parallel-impl-census-20260923.md:100`「**接线从未发生**」同向，故本班把该档"panel 是测试替身还是待上线本体"的两读**收敛为"测试替身"**。这是全部裁决材料里权重最高的一条：**这不是"一个暴露面没上锁"，是"一段未接线的死码上的三个按钮"**。它同时改变路 1（要签的字比想象的小）与路 2b（删件代价比想象的大，见 F7）的成本读法。
⚠ 适用边界：若存在 Streamlit 之外的宿主入口（人工／主班掌握），本条前提失效，§四 的风险评级需重排。

**F2 三枚按钮与 app.py 那三枚是同一件产物。**
panel：`:829` docx／`:841` pdf／`:868` html，`file_name=f"{_safe_stem}问卷设计报告.{docx,pdf,html}"`（`:832/:844/:871`）；app.py：`:2255/:2267/:2294` 同一串文件名。`_safe_stem` 白名单过滤＋`[:60]`（panel `:822-825`）与 `on_click="ignore"`（`:834/:846/:873` 三处）逐字同构 ⇒ 与 s923-22 证据 4 的 difflib「IDENTICAL」结论方向一致（本班未重跑 difflib，按行号与属性逐项对照复证）。
⇒ 含义：**隐私对象相同**。判 panel 的类同于判 app 那三枚的类，不能拿"panel 是面板壳子"当豁免理由。

**F3 app 侧的 `export_gate` 只有 2 处，且不在问卷分支。**
`grep -n "export_gate" app.py` → 仅 `:2323 from src.ui.export_gate import render_export_gate` 与 `:2329 if render_export_gate(st.session_state):`，属论文/交付分支；问卷三枚所在区间 `sed -n '2240,2300p' | grep "gate|门禁|PRIVACY|效应量"` → **无输出**。
⇒ `GATED_EXPORTS["app.py"] = "主应用论文导出（已接入 export_gate）"` 是**文件级顺带放过**（s923-22 已点名）。**这条直接决定路 1 的污染面**：给 panel 发白名单，等于把"文件级理由盖住文件内未门禁按钮"这个既成惯例从 1 个文件扩到第 2 个。
🟡 漂移：s923-22 证据段写 app 门禁调用在 `:2323/:2329/:2358/:2370` 四处 ⇒ 现盘 `export_gate` 字面量只 2 处；`:2358/:2370` 一带实为 `📦 交付包导出` 分支的 `export_pre_check`/`on_privacy_precheck`（`app.py:2358-2375` 实测），**另一套隐私机制**，不含 `export_gate` 字样。

**F4 红只一枚，同件另 10 例全绿。**
`python -m pytest tests/test_export_gate_global_scan.py -q` → `1 failed, 10 passed in 4.41s`
→ `AssertionError: 以下文件的 download_button 未被门禁覆盖或加入白名单: ['src/ui/questionnaire_panel.py']`，抛在 `tests\test_export_gate_global_scan.py:88`。
判定逻辑（`:80-86`）：`known = set(WHITELIST_EXPORTS) | set(GATED_EXPORTS) | set(NEEDS_MIGRATION)`，逐文件比对 ⇒ **粒度是文件，不是按钮**。

**F5 全局按钮面 38 枚／15 文件，panel 是唯一漏列者。**
脚本化枚举 `_get_all_download_button_files()` 实测：

| 归属 | 文件 | 按钮数 |
|---|---|---|
| GATED | `app.py` 4／`deliverable_center_panel.py` 5／`undergrad_wizard.py` 4 | 13 |
| WHITELIST | `literature_review_panel` 5／`evidence_table_panel` 4／`items_upload_panel` 2／`paper_preview_panel` 2／`renderers` 2／`result_card_panel` 2／`docx_exporter` 1／`app_pages_text` 1／`experiment_design_ui` 1／`project_panel` 1／`questionnaire_import_panel` 1 | 22 |
| **MISSING** | **`src/ui/questionnaire_panel.py`** | **3** |

⇒ `test_no_new_download_button_without_gate`（`:113 assert total_buttons >= 20`）**当前 38，余量 18**：panel 的 3 枚无论消失还是转身份，都**不会**踩到这条数量下限。这是本班新增的量化结论（s923-22 未记）——它把"删按钮会撞数量门"这个顾虑**排除**了。

**F6 三条"进表"路各自撞的机械门（s923-22 证据 9 逐条复证，行号**至今精确**）。**
- 进 `GATED_EXPORTS` → 撞 `test_gated_files_have_export_gate_import`（`:92-101`，逐文件 `assert "export_gate" in content`）⇒ panel 内 `grep -c "export_gate"` = **0** ⇒ **当场把一枚红换成另一枚红**。除非先把门禁真写进 panel（＝路 2a 的正解，不是白挂名）。
- 进 `NEEDS_MIGRATION` → 撞 `test_no_pending_migrations`（`:154-156 assert len(NEEDS_MIGRATION) == 0`）⇒ 表体现在**空**（`:39-40`），挂进去即红。**此路机制上已死**，不是"暂挂"。
- 进 `WHITELIST_EXPORTS`（`:19-31`，现 11 条）→ 只撞 `test_whitelist_has_reasons`（`:103-107`，要求 reason 非空且 `len(reason) > 5`）⇒ **机械上唯一无痛的一条**，代价全在语义（＝替隐私分类签字，见路 1）。

**F7 74 例看守绑在 panel 上，且是模块级 import。**
`--collect-only` 实测：`test_questionnaire_panel_charac.py = 10`、`test_questionnaire_panel_logic.py = 64` ⇒ **74 例**（与 census 档"74 例结构看守"逐字吻合）。两件都在模块顶层 `import src.ui.questionnaire_panel as qp` ⇒ **删 panel 文件 = 74 例 collection 期 ImportError**，不是"红消失"，是**红从 1 枚涨到 2 个文件整件报废**。

**F8 往 panel 里加任何一行都会红两枚体量快照。**
`test_questionnaire_panel_charac.py:283` `assert (fn.end_lineno - fnlineno + 1) == 808`（那个巨型函数的**行数跨度**）、`:329` `assert len(BODY.splitlines()) == 881`（**整文件行数**，注释自述刷齐史"…878；s924-37 常量化…后 881"）。同件另有 `:305`（`st.stop()` 落点位）、`:335`（分支头前缀所在行）等位置敏感例。
🟡 否证：census 档记的 `len(BODY)==878` 已过期 ⇒ 现值 **881**（`wc -l src/ui/questionnaire_panel.py` = 881）。
⇒ 路 2a 的成本里含"刷这些快照桩"，且 `:329` 是**手改数字型**桩——刷它必须与生产码同笔入库，不能被当成"这单弄坏了测试"。

---

## 二、出口对比（卷宗说"三路"，实测是**四条互斥出口**——分歧见 §五分歧 1）

| | 出口 | 做法 | 在册红 | 当场新红 | 用户可见 | 谁签的字 | 可回滚 | 量级 |
|---|---|---|---|---|---|---|---|---|
| **路 1** | 白名单签字 | `WHITELIST_EXPORTS` 加 1 行＋reason | 消 | 无（只过 `len(reason)>5`） | 无 | **人替隐私分类签字** | 删 1 行即回 | 5 分钟 |
| **路 2a** | 随片 7 接线，panel **真接** `export_gate` 后进 `GATED_EXPORTS` | census 案 B：app `:1556-2308` 752 行换成 3 行 `elif … render_questionnaire_page()`，panel 内改懒导入＋侧栏改指 `render_settings_sidebar_panel`＋三枚按钮上门禁 | 消（且是**语义正确**的消） | `charac:283/:329`＋位置桩需同笔刷齐；`-k 'download_buttons or export_gate'` 全局门重跑 | **有**：问卷页首次真上线；同释 D3 三文案缺陷 | 无人替隐私签字（按钮受门禁） | 需 revert 一次接线 | **3–5 小时**（census 记），另加 `app.py` 让位等待 |
| **路 2b** | panel 退休（删文件） | 删 `src/ui/questionnaire_panel.py` | 扫描器 `os.walk`（`:59`）扫不到 ⇒ 红"自消" | 🔴 **74 例 ImportError**（F7），两测试件整件报废 | 无（F1：本来不可达） | 删一份有 74 例看守的实现 | 需从 HEAD 恢复文件 | 表面 5 分钟，实际要先安置 74 例 |
| **路 3** | 挂 `NEEDS_MIGRATION` | 表体加 1 行 | 消 | 🔴 `test_no_pending_migrations`（`:156`）当场红 | 无 | 无人 | 删 1 行 | 机制上不通，**零收益** |
| 路 0 | 维持红不动 | 什么都不做 | **留** | 无 | 无 | 无人 | — | 0 |

**读数口径**：路 1 与路 2b 都"无痛消红"，但路 1 的代价在语义、路 2b 的代价在 74 例。此路由 census 档 `:115` 原话定性：「panel 若退休（文件删除），在册红**自动消失**（扫描器 `os.walk` 扫不到该件）⇒ **但"删一份有 74 例看守的实现"要人工点头**，本班不提」（⚠ 该句出自 `psy-qpanel-parallel-impl-census-20260923.md:115`，**非** s923-22.result.md——后者全文 0 次出现"74 例"，本班初稿曾误标出处，已订正）。路 3 是唯一**连消红都做不到**的（把 D7 红换成 D7′ 红）。

---

## 三、在册红 → 消红映射（完成标准 ②）

| 项 | 内容 |
|---|---|
| 红的名字 | `tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for` |
| 抛点 | `tests\test_export_gate_global_scan.py:88`（`assert unaccounted == []`） |
| 判据源 | `:80-86`：三表键并集 vs `_get_all_download_button_files()` 的**文件键**（`os.walk(SRC_DIR)` `:59` ＋ 单独并入 `"app.py"` `:69-71`） |
| 唯一未列名件 | `src/ui/questionnaire_panel.py`（3 枚按钮，`:829/:841/:868`） |
| 世代 | **HEAD 既有红**，非本班所致：`git status --porcelain` 对 `tests/test_export_gate_global_scan.py` 与 `src/ui/questionnaire_panel.py` **均返回空**（两件干净、已入库）；本班全程只读 |
| 同件状态 | 该文件另 10 例**全绿**（`1 failed, 10 passed`）⇒ 修它不会连带门内其它断言 |
| 消红映射 | 路 1 → 消（语义代价）；路 2a → 消（**语义正确**，代价 3–5 小时＋桩）；路 2b → 消（代价 74 例报废）；路 3 → **不消**（换红）；路 0 → 留 |
| 不可走的路（红线，本班不执行） | 改 `_get_all_download_button_files()` 让它跳过"生产零引用模块"＝**放宽判据**；把 3 枚 `st.download_button` 注释掉骗过 `:49` 的字面匹配＝**销证**。二者都能让红"技术性消失"，均超授权，本班**未做、不建议任何人做**，仅登记以防后来者误用。 |

---

## 四、材料性推荐（不代裁决；路 1 属人工签字位，本班明确不选）

1. **近期（本波可做）：路 0 维持红 ＋ 给红配一条横幅**。红是**哨兵在正常工作**：它如实说"有一个含正式交付物下载按钮的文件不在任何名册上"。在 F1（零引用）为真的今天，这枚红**没有对应的线上暴露面**，所以留着不产生用户风险，却保留了未来接线时的强制提醒。建议主班在派片 7 单时把"红必须随接线一并消"写进完成标准。
2. **终局（推荐）：路 2a**。它是**唯一一条不需要任何人替隐私签字**又能让红正当地消失的出口——红消失的原因是"门禁真的接上了"，而不是"有人写了个理由"。且它与 census 档既有推荐同向（"先 A1、后 B"），顺带把 D3 三个用户可见计时缺陷一次解掉。**成本已量化**：3–5 小时 ＋ `app.py` 让位 ＋ F8 的快照桩同笔刷齐 ＋ 4 道硬门里的 D1（懒导入）／D6（侧栏双份）。
3. **明确不推荐**：路 3（机制上换红，零收益）；路 2b（除非人工同时裁决 74 例的去留，否则是"用一次报废换一枚绿"）。
4. **路 1 留给签字者，但给一句材料**：若人工仍选路 1，reason 串**必须写实测事实**而不是惯例措辞——现 11 条白名单里最接近的先例是 `"src/ui/paper_preview_panel.py": "论文预览面板导出（门禁由 app.py 集成层控制）"`，而**这个先例不可搬到 panel**：paper_preview 的门禁确实挂在 app 集成层，`questionnaire_panel` 却**没有任何集成层**（F1 零引用）。诚实的 reason 只能写成"该模块生产零引用、按钮当前不可达（见 s927-53 F1），片 7 接线时须改判 GATED"——把豁免绑到一个**有时效**的事实上，而不是一句"中间产物"。本班不代签这条。
5. **顺带请人工定的一项（不在卷宗范围，但同源）**：F3 揭示 `GATED_EXPORTS["app.py"]` 的文件级粒度正在掩盖 app.py 自己那三枚未门禁的问卷按钮。**即使 panel 这条裁决完，那个更大的洞仍在**。建议单开一枚归因单，别混进本裁决。

---

## 五、本班对卷宗与上游的否证／分歧（照盘说，不改判据）

1. 🟡 **与卷宗的分歧（按要求点名）**：`s927-53.task.md:20` 与完成标准 ① 说"三路对比"，`done/s923-22.result.md:70` 的三路是"白名单／随片 7 接线消失／维持红"。盘上实况是**四条互斥出口**：所谓"随片 7 消失"这一路含两种代价与后果完全不同的走法（2a 接线并真上门禁 vs 2b 删件红自消），census 档 `:110-113` 自己已把它们分列为"做法 A2（激进）"与"案 B"。本班按四条出表，**未擅自合并**；完成标准 ① 因此以"≥三路"满足。另：路 3（`NEEDS_MIGRATION`）在 s923-22 证据 9 里被列为三条**进表**路之一，与卷宗"三路"的第三种（维持红）**不是同一套三分法**——两处三分法互相错位，本班把 5 个出口全列，以免勾错。
2. 🔴 **"随片 7 接线"的前提 today 是空的**：panel 生产零引用（F1），所以"三枚下载按钮"目前**不构成用户可达的隐私出口**。s923-22/census 都把它当"待上线本体 or 测试替身"两读并列，本班的实测**支持"测试替身"这一读**（零调用者），这一点若被签字者接受，路 1 的实际风险显著低于其字面观感。
3. 🟡 数量门顾虑被排除：`total_buttons` 现 **38**、下限 **20**（F5）⇒ 少 3 枚不触 `test_no_new_download_button_without_gate`。s923-22 未测此数。
4. 🟡 三表键与门断言的行号 **`:19/:33/:39/:94/:156` 全部零漂移**（s923-22 记的即现值）；但 **app.py 侧记号漂了**：`export_gate` 字面量 4 处 ⇒ 实 2 处（F3）。
5. 🟡 census 档 `len(BODY)==878` ⇒ 现值 **881**（`:329` 已被 s924-37 刷过，注释自带刷齐史）。
6. 🟡 **census 档自相矛盾**：`:112` 记「`test_questionnaire_panel_*` 两文件（**38 例**）」，而同档 `:84/:115/:128` 三处记「**74 例**」。本班逐文件 `--collect-only` 实测 `charac = 10` ＋ `logic = 64` ＝ **74** ⇒ `:112` 的 38 是旧值或漏件（疑为只数了 logic 的一部分）。**派"删件"类单前请以 74 为准**，否则人工点头时看到的代价少算 36 例。
7. ⚪ **待人工 81 的台账原文本班未取到**：`zcode-bridge/logs/claims.log` 有"三枚下载按钮"字样命中，但台账本体不在 `zcode-bridge/docs|logs/` 可枚举范围内（该件属主班独占，本班未再深挖）。本档因此以 `s923-22.result.md:70` 的逐字引文为准。若台账里的问句与本文的四路不同形，**以台账问句为准重排本表**。

## 六、红线自查

- **零码改动**：psy 侧唯一新增件是本档；`src/`、`tests/`、`app.py`、`pytest.ini` 一行未动；未写白名单、未挂 `NEEDS_MIGRATION`、未改 `_get_all_download_button_files`、未注释按钮。
- 在册红**未消**，如实留盘并已进入本档＋result 遗留问题（w58 §D 第 1 条口径）。
- **未跑全量套件**：只有 `pytest tests/test_export_gate_global_scan.py -q` 一枚单文件（`4.41s`）＋ 5 枚 `--collect-only -q`（不执行用例）。同刻 5 路兄弟班零争用。
- **隐私／统计口径不代判**：本档只摆成本与后果；"问卷设计报告该不该免门禁"＝人工签字位，本班在 §四.4 明确拒签并说明为何既有白名单措辞不可复用。
- 未碰 §C 在途件（`app.py`／`pytest.ini`／`src/analysis/*`／`src/output/interpretation.py`／`tests/test_cfa_sem_golden.py`／两枚 `??`）；`app.py` 仅 `sed -n`／`grep` 只读取证。
