# s927-06 · conclusion_gate 接线窗口裁决材料（三闸口对照＋门禁同步草案＋推荐形状，零码改动）

- 班：`qoder-executor-20260927-1820-psy76`｜cwd `D:\code\psy-analysis`｜HEAD `6bf76af`
- 判据：①三闸口对照 ②门禁同步草案 ③推荐 ④零码改动 —— **四条全中**
- 锚点：`done/20260925-120653-3298.result.md` 遗留 2（原写 `outbox/…`，按 brief §3a 到 `done/` 取到）
- 🔴 红线自证：**"接哪个闸口"＝产品裁决（锚点原话），本班只给对照与推荐形状，不代拍**；
  "阻断判定取哪一档字段集""要不要从 warn 升 block""白名单门槛取几"等**取值题一律写成 §7 判断题**，不选案、不改数值、不改 golden 快照、不重钉基线。

---

## 1. 锚点复算（先证其在世）

| 复点 | 本班读数 | 判定 |
|---|---|---|
| 「`conclusion_gate` 没有生产调用点」 | `git grep -n conclusion_gate -- src tests docs` → 命中 10 行：定义 `field_lineage.py:640` ＋ `__all__:759` ＋ **测试 4 处**（`test_analysis_field_lineage.py:130/131/199/207/214`）＋ **文档 3 处** ⇒ `src/` 内**除定义与导出外零调用点** | ✅ 锚点成立（截至本班时点） |
| 3298 的闸语义 | `Gate(blocked, supporting, ineligible, untraceable)`；`blocked = bool(untraceable) or bool(ineligible)`；`report_lines()` 出 `🚫 不可追溯：…` | 三态判定，**没有"部分放行"档** |
| 3298 在册红 | `pytest tests/test_export_gate_global_scan.py -q` → **1 failed / 10 passed（RC=1）**，唯一红名 `TestExportGateGlobalScan::test_all_download_buttons_accounted_for`，offender `src/ui/questionnaire_panel.py` | ✅ **与 3298 交回时逐字同名同 offender**，本班未消红、未加白名单、未新增入口 |

## 2. 设计意图（档内四条之四）

`field_lineage.py:15`：**「不可追溯即阻断结论」**——对登记表覆盖不到的字段、以及有登记但 `conclusion_eligible=False` 的字段，一律判 `blocked`。
它的登记面**只有锚点与定位符字符串**（`:207` 注释＋`test_registry_carries_no_numeric_values` 硬自证），所以这道闸的语义是**溯源资格闸，不是数值正确性闸**——过闸≠数对，只表示"这个字段能回溯到某个原始文件／抽取步骤／清洗规则／版本锚"。
⚠ 接线前请先把这句话写进闸口文案：否则"✅ 已通过溯源闸"极易被用户读成"✅ 统计结论已核验"（与 s927-03／s927-04 点名的显示层问题同族）。

---

## 3. 判据① · 三候选闸口对照

| 维度 | **G1 导出前** | **G2 渲染前** | **G3 报告写入前** |
|---|---|---|---|
| 盘上位置（本班实测） | `src/ui/export_gate.py:54 def run_export_gate()`；次选 `src/paper_writer/bundle_export.py:165 def validate_bundle_for_export()` | `src/ui/result_card_panel.py:95 def _render_apa_text()`（`:56` 是唯一调用它的主渲染路径） | 三条独立出口：`src/output/docx_exporter.py:1162`、`src/output/zip_exporter.py:202`、`src/ui/deliverable_center_panel.py:285`（都是 `card.get('apa_text','')` 直拼进正文） |
| 是否已有同类闸可挂 | ✅ **已有**：现正聚合 `run_health_checks` + `[BUNDLE]` + `[UNCONFIRMED_AI]` + `[PRIVACY_HIGH]` 四类 `block_reasons`，返回 `(allowed, reasons, issues)`，**加第 5 类是纯增量** | ❌ 无闸，只有 `st.code(card.apa_text)`；要新写判定与文案 | ❌ 无闸；`validate_bundle_for_export` 在 G1 侧已被调用，G3 若另立会出现**两道闸两套文案** |
| 调用点数 | 4 处生产调用：`deliverable_center_panel.py:170/182`、`undergrad_wizard.py:66`、（`render_export_gate` 供 UI） | 1 处（但只覆盖"结果卡面板"，不覆盖 docx/zip 直出） | 需**逐出口接**：3 处（+`professional_consistency.py`、`readiness_scorer.py` 两处间接读 `apa_text`，见 §5） |
| 入参（字段名列表）可得性 | ◐ 拿得到 `card` 与 `bundle` 对象，但**没有"本条结论由哪些字段支撑"的记录面**（§4） | ◐ 单张卡在手，同样缺记录面，但**离结果对象最近**（`output["result"]` 尚可用） | ✗ 到这一步只剩**已渲染的字符串** `apa_text`，字段名信息**已丢失**，只能反解文案 |
| 拦截后的用户体验 | 明确："导出被阻止 — 请先修复以下问题" 逐条列，**可回改** | 结论根本不出现在屏上／或就地降级为警示条 ⇒ 用户可能不知道少了什么 | 报告已写到一半才发现内容被抽掉，**最难解释** |
| 与在册门禁账本的耦合 | 🔴 直接落在 `test_export_gate_global_scan.py` 的三本账（`WHITELIST_EXPORTS` 11／`GATED_EXPORTS` 3／`NEEDS_MIGRATION` 0）上，**同步改法有现成形状**（§5） | 弱：`result_card_panel.py` 已在 `WHITELIST_EXPORTS`（理由"结果卡 Markdown 导出（中间产物，无需门禁）"）⇒ 若在此接闸，**该条理由文案立刻失真**，需同步改写 | 强但分散：`docx_exporter.py` 也在白名单（理由"注释中提及，非实际按钮"），`zip_exporter`/`deliverable_center` 走 GATED ⇒ 三处账本口径要重对 |
| 覆盖"结论出口"的比例 | 只覆盖**走导出按钮的那批**；`deliverable_center_panel.py:285` 那条 `apa_text` 拼接正好在 G1 之后 | 只覆盖结果卡面板 | ✅ 覆盖最全（三处直出口都能拦），但入参最差 |
| 回滚成本 | 低（一个 `block_reasons.append`） | 低但改文案面 | 高（三处分别改） |

---

## 4. 🔴 真正的阻塞不在三选一，在「闸没有入参」

`conclusion_gate(names)` 要的是**字段名列表**，而盘上没有任何地方记录"这条结论由哪些字段支撑"：

```
$ sed -n '129,132p' src/analysis/result_card.py
card.provenance = {"method_id": method_id, "generated_by": "AnalysisResultCard"}
⇒ 来源记录＝方法标签，无字段清单（3298 §E4 已否证过一次"结果侧已有来源记录"，本班复算同结论）
```

于是接线前必须先定"入参从哪来"。三种形状的**实测读数**（决定这道闸接上去是真拦还是装饰）：

| 入参形状 | 实测 | 读数 |
|---|---|---|
| **甲：结果对象的全字段面** | 6 个方法族真跑（合成数据，见 `out_s92706b.txt` §6＋补测） | **3/6 被拦**：`independent_ttest`／`paired_ttest` 因 `assumption_normality`+`assumption_equal_var`；`one_way_anova` 因 `assumption_homogeneity`+`assumption_sphericity`+`table`。`pearson_corr_matrix`／`mann_whitney`／`kruskal_wallis` **全放行**（9/9、7/7 supporting） |
| **乙：统一报告口径五字段**（`report_fields.REQUIRED_REPORT_FIELDS`） | `conclusion_gate(('alpha','omega','n_items','n_cases','ci'))` | `blocked=False, supporting=5` ⇒ **永远放行＝装饰闸** |
| **丙：builder 实际读到的字段名**（AST 抽 `getattr`／`result.x`） | 30 个 builder 全量 | **29/30 被拦**（唯一放行＝`_build_corr_matrix_card`）；拦因一大半正是 **s927-04 点名的"名接缝"**——builder 要 `t`/`p`/`F`/`dof`/`cohens_d`/`U`/`W`/`r_effect`/`n1`，结果类给的是 `t_statistic`/`p_value`/`statistic`/`effect_size`/`df` ⇒ 这些名字**在登记表面前根本不存在**，一律落 `untraceable` |

🔴 三条读数合起来就是裁决要点：**甲会把两族常用方法误拦（且只因 5 个字段）、乙等于不接、丙等于全红**。
⇒ **"接哪个闸口"其实是第四位一体问题：闸口 × 入参形状 × 阻断档语义 × 是否先补那 5 条 spec**。卷宗把它写成三选一，按盘上实况要收窄成这四方（brief §3b：锚点与实况冲突按实况收窄，不判 failed）。

**顺带一条能立刻减压的数**：甲案的拦截面 6 法里**只由 5 个字段造成**——`assumption_normality`、`assumption_equal_var`、`assumption_homogeneity`、`assumption_sphericity`、`table`。这 5 枚在 s927-05 全部落在 **A 栏（宿主类数=1、语义唯一、按名补一条 spec 即可）**。⇒ 先补这 5 条再谈接线，甲案的"误拦"基本消解；反之先接线，就是拿 3/6 方法族挡用户的导出。

---

## 5. 判据② · 门禁同步改法草案（只写形状，不执行）

在册门禁 `tests/test_export_gate_global_scan.py` 的三本账（本班实测条目数：白名单 11／已接闸 3／待迁移 **0**）。硬规则（`:76-88`）：`src/**/*.py` ＋ `app.py` 里**任何一行含 `st.download_button` 的文件**必须出现在三本账之一，否则红；另有 `test_no_pending_migrations`（`:159` `assert len(NEEDS_MIGRATION)==0`）与 `test_gated_files_have_export_gate_import`（`:96` 只要文本含 `export_gate`）两条配套。

| # | 草案改法（选 G1 时） | 动到的在册件 | 会翻红的用例 | 备注 |
|---|---|---|---|---|
| D1 | `run_export_gate` 内加第 5 类 `block_reasons`，前缀 token `[LINEAGE]`，文案取 `Gate.report_lines()` | `src/ui/export_gate.py` | `tests/test_ui_golden_research_flow.py:198/210/239/282`（四例断言 `(allowed, reasons)` 内容）；`:213` 认 `[PRIVACY_HIGH]` 前缀 ⇒ 新前缀**必须另立断言**，不要复用旧 token | 与 `[PRIVACY_HIGH]` 同型（该条注释已在册说明"计数改 blocking_count 免得文案自相矛盾"——同一坑别再踩） |
| D2 | `Gate` 三态→文案分档：**不得作结论**与**不可追溯**要分开印 | `src/analysis/field_lineage.py` | `test_analysis_field_lineage.py:199/207/214`（三例逐字钉 `blocked/untraceable/ineligible/supporting`） | :216 那条 `len(supporting)==5` 是**硬编码全等**＝本仓"重钉基线"的等价形态（**本仓无 `--freeze`**，s927-04 已独立复点） |
| D3 | 若同时新增导出按钮（G1 之外任何入口） ⇒ **同批必须**登记 `GATED_EXPORTS` | `tests/test_export_gate_global_scan.py` | `test_all_download_buttons_accounted_for` | 🔴 该用例**今天已经红着**（offender `questionnaire_panel.py`），本班不动它；新接线**不得把消红夹带进来**（3298 同训） |
| D4 | 白名单理由文案同步：`WHITELIST_EXPORTS["src/ui/result_card_panel.py"]`＝"中间产物，无需门禁"、`["src/output/docx_exporter.py"]`＝"非实际按钮" | 同上 | `test_whitelist_has_reasons`（只校非空与长度>5，**不校语义**）⇒ 接 G1 后这两条理由是否仍成立，**不会自动翻红**＝静默失真风险 | 建议同步改写文案，但这条属"改文案"不属"改门禁"，可另批 |
| D5 | 结论出口共 6 件读 `apa_text`：`docx_exporter:1162`、`zip_exporter:202`、`deliverable_center_panel:285`、`result_card_panel:56/95/101/118/121/151/156/170`、`utils/professional_consistency.py:54/110-119/259/381-390`、`utils/readiness_scorer.py:144` | —— | **只有前三件在导出账本里**；后三件（一致性检查／就绪度评分）是**旁路消费结论**，G1 接闸后它们仍会拿着未过闸的 `apa_text` 打分 ⇒ 若要收口需另设账本 | 🔴 这是"接一处会漏几条"的量化答案：**6 件出口，G1 只覆盖 3 件** |

---

## 6. 判据③ · 推荐（建议形状，待拍板，本班不自签）

**推荐 G1（导出前）为唯一闸口，且按"先 annotate／出声，后 block"分两步走；G2 只做就地标注不做拦截；G3 不接。**

理由（全部指回盘上事实）：
1. **G1 是唯一已有同类闸的位置**——`run_export_gate` 现成聚合四类 `block_reasons`，加第五类是纯增量、可单点回滚；G2/G3 都要新写判定与文案。
2. **G3 的入参最差**：到 docx/zip 那一步只剩已渲染字符串 `apa_text`，字段名信息已丢（§3），拿不到 gate 要的入参，只能反解文案——那是新造一个脆弱契约。
3. **G2 拦不住出口**：`result_card_panel` 只是 6 件结论消费者之一；在此拦截，docx/zip/交付中心三条出口照旧出件（§5-D5），是**看着最像"接了闸"其实漏得最多**的一案。
4. 但 **G1 单独接会漏旁路**（`professional_consistency`／`readiness_scorer` 会拿未过闸结论继续打分）⇒ 推荐附带一条：这两处**各自加"该结论未过溯源闸"标注**（只标注，不阻断），避免打分面自相矛盾。
5. **第一步不 block 的理由是量，不是态度**：甲案入参下 3/6 方法族会被误拦、丙案 29/30 会被拦 ⇒ 直接阻断等于用溯源登记缺口挡用户的真导出。第二步升 block 的**前置条件**：①§4 那 5 枚 A 栏字段先补 spec；②"入参形状"从 §7-J1 三案里拍定一件。
6. 前置次序建议：**先拍 J1（入参形状）→ 再补那 5 条 spec → 再按 D1 接 G1 出声档 → 观察若干真实使用后另批讨论升 block**。反向做（先接线）会立刻产出"报告导不出来"的现场事故。

⚠ 本推荐**不含任何数值／阈值选择**；凡"取哪一档字段集""何时升 block""白名单门槛"全部落在 §7。

---

## 7. 🔴 四道必须给人拍的判断题（本班不选案）

**J1 · 闸的入参形状取甲／乙／丙哪一案？**
- 甲（结果对象全字段面）：语义最干净（"这条结论用到的字段都可溯"），但实测 3/6 方法族被误拦，拦因只是 5 枚登记缺口 ⇒ 须先补 spec。
- 乙（统一报告五字段）：零误拦、零成本，但 `blocked=False` 恒成立 ⇒ **等于装一扇不锁的门**，且会给出"已通过溯源闸"的错觉（比不接更坏）。
- 丙（builder 实际读到的名字）：最贴"这条结论真的用了什么"，但实测 29/30 拦，且拦因大半是 s927-04 的名接缝 ⇒ **必须与 s927-04 Step 1 同批**，否则闸是废的。
- 复算入口：`out_s92706b.txt` §6、`out_s92706.txt` §2/§3。谁拍：闸语义＝人工（＋s927-05 §4 键空间裁决在前）。

**J2 · 阻断档取哪一档：只 block「不可追溯」、还是连「不得作结论」一起 block？**
现值两档都 block（`field_lineage.py:652`），后果：登记表里 6 条 `conclusion_eligible=False` 的 spec —— `S15_charts_payload`／`S16_snapshot_id`／`S17_timestamp`／`S18_card_provenance`／`S20_routing_advice`／`S21_recommended_size`（本班实测计数）—— 一旦被读进字段面就拦。分档（只提示不拦）要动 `Gate` 三态＝触 D2 那三条逐字钉桩。谁拍：人工。**本班不判该改哪档。**

**J3 · 升 block 的时点与判据取什么？**
需要"多少条真实报告、拦过多少、误拦多少"的数——现网**零调用点 ⇒ 零历史读数**，所以第一步只能出声采数。采多久、按几条还是按比例升档，是**阈值选择**，本班不填数。

**J4 · `table` 这枚字段该算"结论支撑"还是"载体"？**
甲案里 `one_way_anova` 被拦的唯一非 assumption 原因就是 `table`（它是方差分析表**本体**，登记成"数据源"还是"派生容器"两种判法结论相反；s927-05 把 `tables`／`apa_text` 归为"派生展示面"，但 `table` 单数形按名登记又落 A 栏）。这条**直接决定 ANOVA 系接闸后被不被拦**。谁拍：人工＋s927-05 §4 键空间同批。

---

## 8. 零改动自证与复算入口

- 对 `D:\code\psy-analysis` 写入件数 = **1**（本档）。`src/` **一字节未写**；未新增 `st.download_button`／未改三本账／未消在册红／未动 golden 快照。
- 未 import、未读 `src/output/interpretation.py`（波次 18 脏件）；`app.py`／`requirements-lock.txt`／`cfa.py`／`test_cfa_sem_golden.py` 未修改。
- 定向测试只跑 `tests/test_export_gate_global_scan.py`（静态扫描件，无 AppTest、不触库；1 failed/10 passed，RC=1，**红是存量红，非本班造**）。未跑全量（并发窗：同刻 colony40／quant48／learn47 在别仓）。
- 探针输入全为合成 DataFrame 与盘上源码 AST，**未打开 `data/` 任何库**；解释器 `.venv/Scripts/python.exe -B`。

| 件 | 内容 |
|---|---|
| `D:\code\tmp\qoder-executor-20260927-1820-psy76\probe_s92706.py` → `out_s92706.txt` | §1 30 个 builder 读到的字段名全表；§2 丙案读数（29/30 拦）；§3 甲/乙/丙三形状对照；§4 三闸口盘上定位（函数行号）；§5 `apa_text` 六件出口逐行号 |
| `...\probe_s92706_b.py` → `out_s92706b.txt` | §6 真实结果对象字段面 → gate（甲案硬读数）；§7 ttest／mann_whitney 两法逐字段三态标注 |
| `...\t06_scan.log` | 在册红复算原文（offender 与 3298 交回时逐字相同） |
| 命令 | `cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B D:/code/tmp/qoder-executor-20260927-1820-psy76/probe_s92706.py`；`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B -m pytest tests/test_export_gate_global_scan.py -q` |

## 9. 遗留（交主班）

1. 🔴 §7 四道判断题（J1 尤其）必须先拍，且 J1/J4 与 **s927-05 §4 键空间裁决**同批——那 5 枚 A 栏字段与 `table` 的归类正是本案拦截面的全部来源。
2. 本单**未做**也**不该由本班做**的两件：①给 `result_card` 补"结论支撑字段清单"记录面（要写 `src/`，属另开写单）；②D1/D2 的实际改法（要写 `src/` 与 `tests/`）。
3. ⚠ 探针 B 的 8 法造数中 **2 法（`cronbach_alpha`／`chi_square_independence`）签名不匹配跳过、`paired_ttest` 需按列名造数**⇒ 甲案读数面实为 **6/8**，`_build_corr_matrix_card` 之外的 psychometrics 族拦截率**本班未测**，下批补。
4. ⚠ 环境坑登记（给下批省一步）：Windows 下 `subprocess.run(..., text=True)` 默认走 GBK 码页，读含中文的 `src/*.py` 会 `UnicodeDecodeError`（本班首跑撞上，改为按 `encoding="utf-8"` 直接读文件）。这与 brief §6 的 `PYTHONIOENCODING` 是**两个不同的坑**。
5. 本档未进 `docs/insights/` 索引登账件。
