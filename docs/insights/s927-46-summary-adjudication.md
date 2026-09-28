# s927-46 `generate_design_summary` 接线裁决材料（三问逐问，只出材料不选案）

- 班：`qoder-executor-20260928-1610-psy94`（只读路）　cwd：`D:\code\psy-analysis`　HEAD：`b77ff08`
- 日期：2026-09-28　上游锚点：`zcode-bridge/done/s923-07.result.md` 遗留问题 1（三问）＋ `docs/insights/psy-dead-code-dossier-20260923.md`
- 本档性质：**裁决材料**。三问的选案权在人工闸，本班未拍板、未改任何码、未改任何判据（完成标准 ③ 零码改动）。

---

## 0. 结论先行（三句最要紧的）

1. **卷宗说的"两处在册钉桩缺陷"在磁盘上只剩一处。** 第二处（`dimensions_used=[]` 时摘要挂空标题 `### 维度分配：`）**已被 `s924-41` 入库闭合**（commit `66cc9ff`，源码 `report_generator.py:215-216` 现为注释＋`if dims:` 守卫，测试件 `:244-258` 的断言已从"钉现状空节"翻转为"空态无标题"）。本班实测空 dims 态摘要**不再含该标题**。**⇒ Q② 的裁决面从"两处"收窄为"一处（措辞写死）"。**
2. **Q① 的关键新事实：接 UI 的展示增量几乎为零。** 摘要 7 条事实里有 **6 条已经在问卷设计分支里逐值展示**（`app.py:2047-2053` 构念识别、`app.py:2055` 直接 `st.markdown(design["match_reason"])`、`app.py:2078-2080` 维度清单、`app.py:2084-2090` 技术参数表 5 格＝题型/量表点数/总题量/维度数/反向题）；唯一没展示的是「预计用时」，而它在本件里**已有两种口径**（`report :90` 约 N 分钟、`report :159` N-M 分钟）⇒ 接线等于引入第三个用时数字或同时裁用时口径。
3. **Q③ 的两半不是同一族对象。** `get_test_name_zh` 是 `t(key, lang)` 的一行薄包装（实测三例逐值等值），删它零功能损失；但卷宗第二半的 `src/ui/app_pages_text.py:166-197` 是**整段方法说明文案**（zh 值平均 61 字符、最长 87），而 `i18n.TRANSLATIONS[zh]` 全表**最长值只有 18 字符** ⇒ "并入 i18n 单一来源"是**新增键族的搬家**，不是去重。真正的重复建设在另一处：`config.settings.TEST_NAMES_ZH` 与 `i18n.TRANSLATIONS` **两套检验名表实测同值**（`independent_ttest` 两边都是 `独立样本t检验`）。

---

## 1. 锚点复核与漂移（卷宗读数 vs 磁盘现值）

| 卷宗/锚点读数 | 磁盘现值（本班 `b77ff08` 现取） | 判定 |
|---|---|---|
| `generate_design_summary` 定义 `report_generator.py:200` | `:200`，函数体 `:200-:222` 共 23 行 | 零漂移 |
| import 2 处（`src/ui/questionnaire_panel.py:16`、`app.py:1564`） | 同两行；两文件内该符号**全文各只出现 1 次**（＝import 行本身） | 零漂移，且坐实"死 import" |
| 生产调用 0 处 | 0 处（`src/` 与 `app.py` 除 import 行外零命中） | 成立 |
| 「调用 6 处全在 `tests/test_questionnaire_design.py`」 | 测试内**调用 9 处**（`:181/:214/:222/:231/:238/:253/:265/:275/:278`）＋ import `:15` ＋ 段标 `:125` | **漂移**：s924-41 把 1 例翻正并新增 2 例（:260/:273），钉桩类现为 **8 例** |
| s922-15「6 例成对断言」 | 类 `TestDesignSummaryPins` **8 例／27 条 assert**，其中 **6 条 assert 位引用 report 变量**；`:209` 那条在 `pairs` 循环里运行时执行 **13 次**（7 固定对＋每维 2 对×3 维） | 面变大：净丢失数见 §2 案丙 |
| `get_test_name_zh`「15 行命中」（s923-07 已订正过一次） | `tests/test_i18n.py` **18 行**命中（`:6/:46/:68/:69/:80/:81/:82/:87/:88/:89/:95/:97/:99/:105/:106/:123/:137/:172`），其中**带括号调用 16 处**，另 3 处是 import／docstring／census 说明行 | **漂移 +3**（新增的是注释与 census 里的符号名引用，不是调用） |
| `app.py:1564` 行号 | 该行现值仍是 `generate_design_report, generate_design_summary,` | 零漂移（但 `app.py` 是本波 12 枚在途件之一） |
| 「案 A 第一步要改 `app.py` ⇒ 串行依赖」 | `app.py` 仍 ` M` 在途；**`src/ui/questionnaire_panel.py`、`report_generator.py`、两枚测试件、`i18n.py`、`app_pages_text.py`、`config/settings.py` 全 clean** | 成立但可绕：接线/删除都能先只落 clean 件（见 §2、§5） |

---

## 2. Q① 接 UI，还是接受"永久只作 report 的对照物"——三案材料

公共实测（`probe_summary.py`，matched 态真实 `design_questionnaire` 输出）：摘要 **13 行／158 字符**，报告 **319 行／5718 字符**（36.2 倍）。摘要全文 7 个事实行＋3 行维度小节，无参考文献、无信效度论述。

### 案甲：接 UI（`app.py` 与 `questionnaire_panel.py` 各一处渲染）

- 改动面（最小形状）：在 `questionnaire_panel.py` 报告渲染前插 `st.markdown(generate_design_summary(design))` 约 2 行；`app.py` 同分支对称再一处 ⇒ **2 件 × ~2 行**。
- **收益实测为负**：6/7 事实与现有 UI 逐值重复（`app.py:2085-2090` 技术参数表就是 题型/量表点数/总题量/维度数/反向题，`:2078-2080` 就是维度题数清单，`:2047-2053` ＋ `:2055` 就是构念与 `match_reason`）。唯一增量「预计用时」与 `report :159` 的 施测时间 口径冲突（约 6 分钟 vs 6-9 分钟，n_items＝19 实测）⇒ 同一屏出现两个用时数字。
- 风险面（实测）：KeyError 面**不新增**——摘要顶层必需键 5 枚（`construct_name/dimensions_used/is_exact_match/scale_config/template_used`）是报告必需键 12 枚的**真子集**（matched 与 unmatched **两态各测一次**，`summary ⊆ report` 均 True）；抹掉报告独有的 7 枚键后摘要仍正常出文。⇒ 安全性不是本案的反对理由，**重复展示才是**。
- 门禁：`test_export_gate_global_scan` 按**文件级**记账（`SRC_DIR` 扫 `src/` ＋ `APP_FILE` 单独收 `app.py`）。若接线形态只是 `st.markdown`，零影响；若做成 `st.download_button`：`app.py` 已在 `WHITELIST_EXPORTS`（`:34`），`src/ui/questionnaire_panel.py` **已在当前红名里**（在册红 `test_all_download_buttons_accounted_for` 断言体正是 `['src/ui/questionnaire_panel.py'] == []`）⇒ **红名集合不新增**，但按 w46-brief §B 仍要单列加跑并如实留红，不得自行消红。
- 并发依赖：`app.py` 是在途件 ⇒ 甲案天然拆成两笔（panel 先、app 后），或等 `app.py` 收单。
- 回滚成本：低（纯新增渲染行，删行即回滚，无断言依赖）。
- 工时（形状估计）：0.2 d（含两态冒烟＋门禁加跑）。

### 案乙：接受"永久只作 report 的对照物"（维持现状，但把定位写成契约）

- 改动面：`report_generator.py:200-201` 的 docstring 现值是「生成简短的设计摘要（**用于UI展示**）」——**这句现在是假的**（生产 0 调用）。最小动作＝改一行 docstring 为"仅作 `generate_design_report` 的成对看守参照物，UI 不接"，零行为改动。
- 代价：符号继续被两枚 clean 件 dead-import（`app.py:1564`／`panel:16`），死 import 本身是 lint 债；测试侧 8 例／27 断言继续为"对照物"付维护费。
- 收益：一条零风险的诚实化，且保住 §2 案丙列出的全部 report 看守。
- 回滚成本：零（docstring 单行）。
- 工时：0.05 d。

### 案丙：删除（连同死 import 与测试侧引用一起摘）

- 必须同笔入库的集合（w46-brief §A.4 口径，分开提＝HEAD 红）：**5 件**
  ①`src/questionnaire/report_generator.py`（删 `:200-:222` 23 行）
  ②`app.py`（摘 `:1564` 的 `generate_design_summary,`，**在途件，须等其收单**）
  ③`src/ui/questionnaire_panel.py`（摘 `:16` 同一符号）
  ④`tests/test_questionnaire_design.py`（`:15` import ＋ 类内 8 例／27 断言的改写）
  ⑤`docs/insights/psy-dead-code-dossier-20260923.md`（在册档案的结论行需标"已执行"）
  牙：① 与 ②③ 任一单独提 ⇒ `ImportError`，但两位点不同——`src/ui/questionnaire_panel.py:16` 是**模块级 import**（收集期即炸，凡 import 该模块的测试件全红），`app.py:1564` 是 `elif mode == "📋 问卷设计":` **分支内 import**（跑到该模式才炸，测试件收不到）；①＋②③④ 分笔 ⇒ `tests/test_questionnaire_design.py:15` 直接 import 该符号 ⇒ **整件收集错误，22 例全红**。
- **牙数净丢失实测**（这才是 s923-07 "静默退化"的结构化读数）：类内 27 条 assert 中 **6 条位引用 report**（`:209/:217/:225/:227/:257/:258`），其中 `:209` 在 13 对 `pairs` 循环里运行 13 次 ⇒ 删除即丢 **18 次 report 侧断言执行**；另有 `:240-:242` 两条钉 report 的 `KeyError` 现状（不引用 `report` 名但属 report 行为）。类总例数 8 → 保留 report 侧需把 6 条重写成"report 单侧"断言，**净减 2 例左右、不减覆盖**是本案的真实工作量所在。
- 收益：少一个 UI 假承诺、少两枚死 import、少 23 行无人读的码。
- 风险：拆看守时若只删 summary 侧调用而忘记把 report 侧断言搬走，`pairs` 结构还在 ⇒ 绿着丢覆盖（s923-07 已点名的隐蔽面）；本案**必须**与 ④ 同笔并附"18 次执行"的复算证据。
- 串行依赖：受 `app.py` 在途状态硬约束。
- 工时：0.5 d–1 d（含拆看守与复算）。

---

## 3. Q② 是否授权修剩下的那处钉桩（措辞写死）——修法与影响

缺陷 A 现状（逐字）：`report_generator.py:208`
`f"**匹配方式**：{'精确匹配已有构念知识库' if design['is_exact_match'] else '基于关键词推断'}"`
报告侧同语义走 `design['match_reason']`（`:26-:39`）⇒ 摘要与报告**各说各话**，且该分叉被 `test_questionnaire_design.py:219-227` 显式钉成现状（docstring 原话「钉住，不统一」）。

修法只有一行：把 `:208` 换成 `f"**匹配方式**：{design['match_reason']}"`。

内存变异实测（`probe_summary.py` §3，未写 `src/`）：

```
新摘要该行='**匹配方式**：在研究问题中识别到「心理韧性」相关关键词，匹配得分 10.8（关键词匹配引擎）（内置知识库）。'
测试 :224 断言「**匹配方式**：精确匹配已有构念知识库」 in summary   → False（翻红）
测试 :227 断言「精确匹配已有构念知识库」 not in report              → 仍 True（report 不含该串）
测试 :232/:233（unmatched 态钉「基于关键词推断」）                   → :232 翻红、:233 由 True 变 True（失效但绿）
pairs 事实表（:188-:201）不含该行 ⇒ 成对看守不受影响（7 固定对＋每维 2 对＝13）
```

⇒ **爆炸半径＝2 例 4 断言**（`test_match_method_wording_diverges_by_design`、`test_summary_unmatched_branch_wording`），两例都要**同步翻正**，属"判据语义改动"（w46-brief §B quant 类比：翻正断言与生产码必须同笔）。

副作用（接 UI 与否都成立）：改完后摘要该行内容与 `app.py:2055` 已渲染的 `st.markdown(design["match_reason"])` **逐字相同** ⇒ 案甲的重复面从 6/7 涨到 7/7。也就是说 **Q① 与 Q② 不是独立问**：若选甲＋修 A，摘要就退化成"报告事实行的复读"，此时案丙（删除）的性价比反超。

不修的代价：`match_reason` 里含匹配得分与引擎名（实测串含「匹配得分 10.8（关键词匹配引擎）」），摘要对最终用户展示的是一个**与引擎实现耦合的措辞**——但摘要当前不接 UI，所以零用户可见影响。⇒ 修 A 的唯一净收益是"两生成器不再分叉"，属**代码一致性**收益，不是用户收益。

同集合提交清单（若授权修）：`report_generator.py:208` ＋ `tests/test_questionnaire_design.py`（:219-:233 两例）＋ 本档/在册档结论行。三件分笔＝HEAD 红（前两件），实测已给红位。

---

## 4. Q③ `get_test_name_zh` 删除前，`app_pages_text.py` 的硬编码文案是否并入 i18n

分层读数（`probe_i18n.py`）：

- 符号本体：`src/utils/i18n.py:269-271` 三行，实现是 `return t(test_type, lang)`。实测三例（`mean`／`independent_ttest`+`en`／`nonexistent_key`）与 `t()` **逐值等值** ⇒ 零独有价值，纯别名。
- 生产消费方：`app.py` 0 命中、`src/` 除 def 外 0 命中。在册真正被用的是**另一个同名函数** `config.settings.get_test_name`（`runner.py:992`、`intent_recognizer.py:537`、`undergrad_wizard.py:13/2976/3028/3063`、`app.py:33/1167`）⇒ **两套检验名来源并存**（实测 `TEST_NAMES_ZH['independent_ttest']` 与 `i18n.t('independent_ttest','zh')` 同为 `独立样本t检验`）。
- 删除案的**可验不变式**（本班已实跑）：把 `tests/test_i18n.py` 里 16 处 `get_test_name_zh(` 改写为 `t(`，AST 键 census（`_i18n_referenced_keys()` 的口径，`:165-200`）前后**键集合逐位相同（13 键，差集空）**，改写后源码仍 `compile` 通过 ⇒ 该不变式可直接当判据写进单，不必靠人眼看覆盖。
- 命中数口径提醒（本波在册坑）：`grep` 数到的 **18 行**里有 3 行不是调用（`:6` import、`:46` docstring、`:123/:137/:172` 说明与 census 白名单）⇒ 摘符号时 census 的 `entry_functions = {"t", "get_test_name", "get_test_name_zh"}`（`:172`）也应一起去掉第三项，否则留着无害但成僵尸名。
- 第二半（`app_pages_text.py:166-197`）：AST 实测函数体内 **2 套 Dict**（`:168` en 12 键、`:195` zh 12 键，两套键集合逐字相同）；这些键 **11/12 存在于 `TRANSLATIONS[zh]`**（缺的那枚是 `cronbach_alpha`），但**值类型不同**：说明文案 zh 值平均 61 字符、最长 87，而 `TRANSLATIONS[zh]` 全表最长值 **18 字符** ⇒ 「并入 i18n」＝给 12 个方法各新增 `desc_*` 键族（24 条新表项，跨 zh/en 两表），不是"去重"。
- 该文件的门禁归属：`src/ui/app_pages_text.py` 在 `WHITELIST_EXPORTS`（`test_export_gate_global_scan.py:30`）⇒ 动它的单必须加跑门禁族（该文件 clean，可改）。
- 附带在册件：`tests/test_reliability_bands.py:88` 已写明这套中英说明文案是**原样迁入**、不算新增债 ⇒ 并入 i18n 会同时牵动那条例外的口径。

三问里唯一"改不改都不影响用户可见行为"的是 Q③ 的符号删除部分（零消费方）；"改动面最大"的也是它（要连 census 白名单与 16 处调用一起改，且属判据面）。

---

## 5. 推荐组合（形状排序，拍板属人工闸）

排序依据只用三条客观尺：**改动面行数／牙数净变化／回滚成本**；并发依赖单列。

1. **首选：案乙 ＋ Q③ 的符号删除（不含 `app_pages_text` 并入）**。
   合计改动面约：docstring 1 行 ＋ `i18n.py` 3 行 ＋ `tests/test_i18n.py` 16 处调用改写 ＋ census 白名单 1 处，**零行为改动、零用户可见变化**，且 Q③ 有现成可验不变式（键集合逐位相同，本班已跑通）。牙数：summary 侧 27 条全留，i18n 侧 22 例不减。
2. **次选：案丙（删除 summary）＋ Q② 一起判**。理由见 §3 末：Q② 修完之后摘要就是复读，甲案失去唯一收益、乙案付维护费 ⇒ **丙是"修 A"的必然续着**。但丙必须与 ④（测试件拆看守）**同笔**，且第一步撞 `app.py` 在途件 ⇒ 排期上比首选晚。
3. **不建议：案甲单独成立**。6/7 重复展示是实测而非推测；要做甲，应先裁"用时口径"（`report :90` vs `:159` 两形）这条独立缺口，否则新接的摘要与报告同屏打架。
4. **`app_pages_text` 并入 i18n：建议与 Q③ 拆开单判**（它是 24 条新表项的搬家，牵 `test_reliability_bands.py` 的既有例外与门禁名单），不要和符号删除捆在同一单里。

**本班未拍板、未改码、未改判据**；上面只是形状排序，选案与"是否授权翻正 :219-:233 两例"都超出执行手授权（w40-brief §4 人工闸）。

---

## 6. 复算入口（全部只读，可直接粘）

```
cd D:\code\psy-analysis
PYTHONIOENCODING=utf-8 .venv\Scripts\python.exe D:\code\tmp\qoder-executor-20260928-1610-psy94\probe_summary.py
PYTHONIOENCODING=utf-8 .venv\Scripts\python.exe D:\code\tmp\qoder-executor-20260928-1610-psy94\probe_i18n.py
PYTHONIOENCODING=utf-8 .venv\Scripts\python.exe -m pytest tests/test_questionnaire_design.py tests/test_i18n.py -q
git show --stat 66cc9ff
```

---

## 7. 遗留（交人工/主班）

1. 三问一律**未选案**；`report :90` 与 `:159` 的用时双口径是 Q① 暴露出的**第四问**，卷宗里没有，建议补一枚卷宗（属产品文案裁决，非代码缺陷）。
2. `s923-07` 的"两处在册钉桩"应订正为"一处"（另一处 `66cc9ff` 已闭合）；本档 §0-1 给的是订正证据，**未回写 s923-07 的 result**（append-only，覆写＝销毁前手取证）。
3. 案丙/修 A 都属**四件同集合提交**，见 §2 案丙与 §3 末清单。
4. 全量 pytest 未跑（同仓并发）；本班现取定向读数：`tests/test_questionnaire_design.py` ＋ `tests/test_i18n.py` 合跑 **44 passed**（22＋22，锚点时的 41 例已长到 44），零新增红。门禁族另见 result。
5. 沙盒 `D:\code\tmp\qoder-executor-20260928-1610-psy94\` 三件 s927-45 探针 ＋ 本单两件探针（`probe_summary.py`／`probe_i18n.py`）**保留**——它们是 §2/§3/§4 全部数字的唯一复算入口。

---

## 8. 收笔复点（done 行 16:42 之后落，现取读数）

按新口径「先落账再补产档末段」，本段在 result 与 claims 的 done 行之后写；本班未跑任何写操作，读数如下：

```
HEAD                                   b77ff08（本班全程未推进）
git status --porcelain                 14 行（开工 12 ＋ s927-45 新档 1 ＋ 本档 1）
src/questionnaire/report_generator.py  sha1 ce7752a4666cb0be7ad8fcebdab1f6055731054d  clean
tests/test_questionnaire_design.py     sha1 b33f2f57aa82a7b538eea646cd217e2291c27a39  clean
tests/test_i18n.py                     sha1 629e84ca26babaf4747dac45dae18bea63fd96c8  clean
src/utils/i18n.py                      sha1 eb13ae2374caab57113b46e9d41a51fea13a3d34  clean
config/settings.py                     sha1 4462524e4b014657a74887dc47b82ae80dab1b8b  clean
app.py（他班在途件，本班只读）          sha1 8ea18c3b8f6ebaae7755d9c85d9cab1c766b0a36  130298 B  mtime 2026-09-26 11:47  状态仍 ` M`
本档（§8 落笔前）                      sha1 f905206bbc616e00d02d37dcaa228d871b279990  17277 B
```

- 定向读数：`tests/test_questionnaire_design.py` ＋ `tests/test_i18n.py` 合跑 **44 passed**（22＋22，锚点时 41 例已被 s924-41 长成 44）；门禁族 `-k download_buttons or export_gate` ＝ **1 failed／19 passed／1 skipped／5531 deselected**，唯一红为在册 `test_all_download_buttons_accounted_for`（断言体 `['src/ui/questionnaire_panel.py'] == []`）。与本班 s927-45 收笔读数同形 ⇒ 零新增红。
- 全量 pytest 未跑（同仓并发，w40-brief §5）；`data` 域零触及，本单不需要 `LITERATURE_FEED_DATA_ROOT` 沙盒。
- §8 落笔使本档指纹变化，`f905206b` 是其**正文体（§0-§7）**的锚定值，已进 result 与 done 行；终值由 claims 的补正 note 行给出，主班按精确路径整件代提交即可，不要按 sha 比正文。

