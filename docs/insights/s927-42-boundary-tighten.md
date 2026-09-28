# s927-42 · 构念数下界收紧裁决材料（只读落档 · 2026-09-28）

- 班：`qoder-executor-20260928-1440-psy91`（信箱单 `s927-42`，主班 `qoder-main-drain-20260928-0115`）
- 性质：**只读材料**。生产码／测试件／配置／数据零改动；未 `git add`／未 commit。
- 非统计数值域（本单的下界是**测试件常量**，不是效应量／p 值／样本量结论），但**改判据语义属人工闸**，本班只出材料与推荐，未改任何断言。
- 盘面绑定（14:44 与 15:0x 本机 `date` 两次现取；引数前请复点）：

```
HEAD = 429495086addff5b59593ee6d70128fe60ae4963（短 4294950）
sha256 tests/test_questionnaire_design.py      = 47e269ac7902f0d3…（前 16 位现取）
sha256 src/questionnaire/construct_kb.py       = 3c6602950c3389ad…   ← 与 s924-03 注记的字节 sha8 `3c660295` 同值
git diff --numstat HEAD -- tests/ src/questionnaire/  → 只有 59/49 tests/test_cfa_sem_golden.py（他班在途件，本班未碰）
```

  ⇒ **被数对象 `construct_kb.py` 自 2026-09-24（s924-03 取数时刻）逐字节未变**，故 51 这个现值不存在漂移。

---

## 1. 卷宗前提逐条实测（含否证）

| # | 卷宗／锚点前提 | 实测 | 证据 |
|---|---|---|---|
| 1 | 锚点 `zcode-bridge/done/s923-02.result.md` 遗留 1：`tests/test_questionnaire_design.py:101` 的 `>= 40` 松下界**要不要收紧**——交主班裁决，本单未动 | ❌ **前提过期：收紧已落地并入库**。commit `5a8c9ce test(psy): s924-03 两处 print 枚数改双向守恒断言，下界 40→51 现取`（作者时戳 2026-09-25 01:04:51）本笔 `tests/test_questionnaire_design.py 10+/2−`、`tests/test_llm_engine.py 17+/1−` | `git show 5a8c9ce -- tests/test_questionnaire_design.py` 的 hunk 原文＝`- assert len(CONSTRUCTS) >= 40` → `+ assert len(CONSTRUCTS) >= 51` |
| 2 | 锚点行号 `:101` | ⚠ **已漂**：`>= 40` 当年确在 `:101`（`git show 5a8c9ce^` 复点在该行），收紧时加了 8 行 docstring／注记 ⇒ 现值断言在 **`:109`** | `grep -n "len(CONSTRUCTS)" tests/test_questionnaire_design.py` → `109: assert len(CONSTRUCTS) >= 51` |
| 3 | 现值 51、下界 40 ⇒ 有 **11 个构念的静默消失空间** | ✅ **数值成立但范围要订正**：那 11 枚空间**只在 `test_questionnaire_design.py` 这一件内**。套件级早在 9-23 之前就没这个空间——`tests/test_construct_kb_census.py:15 TOTAL = 51` ＋ `:26 assert len(CONSTRUCTS) == TOTAL`（精确等值）在 `5a8c9ce^` 已在场。⇒ 收紧的净增量是**该件与 census 口径归一**（不再"下界 40／精确 51"两套并存），不是"首次拦住掉数" | `git show 5a8c9ce^:tests/test_construct_kb_census.py \| grep -n "TOTAL = 51\|assert len(CONSTRUCTS)"` → `15:`／`26:` 两行原文 |
| 4 | 现值复核 | ✅ `len(CONSTRUCTS) = 51`、`len(DOMAIN_KEYWORDS) = 7`（`.venv` 现取）；census 族独立佐证同态：`tests/test_construct_kb_census.py` **9 passed**、`tests/test_construct_kb_extended_placeholder.py` **7 passed ＋ 1 skipped**、`tests/test_questionnaire_design.py` **22 passed** | 本文 §6 命令原文 |

⇒ 卷宗要裁的三案（收紧到 51／维持 40／中值）**只剩一条是活的**，且它不在卷宗的三案里：`>=` 还是 `==`。见 §4。

---

## 2. 收紧后的看守拓扑（现值，谁在拦什么）

| 点位 | 断言形态 | 拦住"掉数"？ | 拦住"涨数"？ | 采集状态 |
|---|---|---|---|---|
| `tests/test_questionnaire_design.py:109` | `len(CONSTRUCTS) >= 51` | ✅（静默空间 0） | ❌（涨到 52 不红） | 22 passed 内一例 |
| `tests/test_construct_kb_census.py:15/26` | `TOTAL = 51` ＋ `len(CONSTRUCTS) == TOTAL` | ✅ | ✅（52≠51 当场红） | 9 passed |
| `tests/test_construct_kb_extended_placeholder.py:42/104` | `CENSUS_TOTAL = 51` ＋ `len(CONSTRUCTS) == CENSUS_TOTAL` | ✅ | ✅ | 7 passed＋1 skip |
| `tests/test_llm_engine.py:25-30`（s924-03 新增） | `len(construct_sections) == len(CONSTRUCTS)` ＋ 集合双向守恒（**动态**，不写死 51） | 只拦「prompt 少渲染／多渲染一节」 | 不拦（与 KB 同步浮动） | 🔴 **收集 0 例、单跑 rc=5**＝脚本形态：断言只在 collect 期以 import 副作用执行，破了报 collect error 而非 FAIL |

⚠ 第二行的"涨数"由 census 侧承担这一条，是 `5a8c9ce` commit message 自己写的口径：「实测由 census 侧 `52==51` 拦增长，要"增减都红"改一处即可」。

---

## 3. 「静默聚合」这一形态本身：下界拦不住它

卷宗标题写的是"静默聚合"。实测这条通路**与构念条数无关**，因此案一/案二/案三中任何"改下界数字"的方案都对它无效：

```
$ grep -rn "{**CONSTRUCTS, **EXTENDED_CONSTRUCTS}" --include='*.py' src/
src/questionnaire/academic_literature.py:65     all_kb = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}
src/questionnaire/design_engine.py:213          all_constructs = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}
src/questionnaire/design_engine.py:232          all_constructs = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}
```

- `EXTENDED_CONSTRUCTS` 是**用户可编辑追加**的扩展库（`src/questionnaire/construct_kb_extended.py:7` 现值 `{}`）。右侧字典解包 ⇒ **同名键静默覆盖内置构念**，而 `len(CONSTRUCTS)` 一字不变 ⇒ `:109` 的 `>= 51` 与两枚 `== 51` 全都恒绿。
- 现在真正拦它的是 `tests/test_construct_kb_extended_placeholder.py:97/:98/:115`（`EXTENDED == {}`、`len == 0`、键集互斥）——**三枚都只在"扩展库为空"这一态有效**。有人往扩展库塞合法新构念时它们会红，届时"同名覆盖"与"正常追加"两件事会挤在同一次裁决里。
- 另有同族**未收面的松哨**（与原判据同形、同样留静默空间，卷宗未点名，本班也未动）：
  - `tests/test_questionnaire_design.py:97` `len(DOMAIN_KEYWORDS) >= 5`，现值 **7** ⇒ 2 枚域标签的静默空间；
  - 同件 `:61` `sc["n_items"] >= 5` 等计数下界若干。
  ⇒ 若"再也不许掉"要作为原则贯彻，这些点是同一把尺的其余格子；改哪几处属判据面，交人工圈定范围。

---

## 4. 三案矩阵（防回归价值 vs 维护成本）

| | **案一 收紧到 51** | **案二 维持 40** | **案三 中值（如 45）** |
|---|---|---|---|
| 现状 | ✅ **已执行**（`5a8c9ce`，s924-03） | 已被否证（原判据不再在盘） | 未采纳 |
| 静默消失空间 | **0 枚** | 11 枚（仅在该件内；套件级由 census `==` 早已封住） | 6 枚 |
| 涨数（52 条） | 该件不红，census／placeholder 两枚 `==` 红 | 三处全不红（该件 40≪52，两枚 `==` 会红 ⇒ 实际仍被拦） | 同案一（`==` 侧拦） |
| 维护成本（新增 1 枚构念时必改点位） | **3 处常量**：`:109` 的 51 可不改（下界）、`census:15`、`placeholder:42` ＋ 注记里的 N 两行（`test_questionnaire_design.py:103`、`test_llm_engine.py:17`）＋ 在册档 `psy-census-values-recheck-20260923.md` 14 处读数 | 0 处（无牙＝无成本） | 与案一**同成本**，牙却更钝 |
| 回滚成本 | 一行级（`:109` 的 51 改回 40），但回滚＝重新打开静默空间且与该件 docstring 自相矛盾 | — | — |
| 失败可见性 | 红在该件 `test_construct_count` 一例，用例名即语义（"不许低于现值"） | 掉数在该件不可见；仅靠 census 侧红 ⇒ 归因指向"普查件"而不是"设计件" | 同案二形态，只是分界不同 |

三案里**唯一有牙的是案一**，且它已经是盘面现实——本单不存在"要不要收紧"的可批动作，只有"收紧后要不要再往前一步"。

---

## 5. 唯一活口：`>= 51` 还是 `== 51`（在册，非本单新增）

- 出处两处：`5a8c9ce` commit message 的「⚖ 一条交人工」；待人工台账 `docs/insights/drain-20260923-pending-human.md` 第 209 条⑩（「`>= 51` 还是 `== 51`（卷宗写"下界"故留 `>=`）、`test_llm_engine.py` 仍是脚本形态（收集 0 例、单跑 rc=5，函数化属改测试结构）」）。
- 两案改动面（都只动一行，均**不**需要重钉任何数值基线）：
  - **甲：维持 `>= 51`**（现状）。语义＝"再也不许掉"；涨数只改两枚 `==` 常量；该件与 census 分工明确（注记 `:107` 逐字写着"本行刻意留下界而不是等值：精确增减由 census 那件负责"）。代价＝该件自身不拦涨数，读它的人容易误以为"涨过 51 会红"（卷宗前提里就有这句）。
  - **乙：改 `== 51`**（增减都红，一处即够）。代价＝该件与 `census:26`／`placeholder:104` **三枚同值精确钉**并存，涨一枚构念要同改三处常量＋两行注记；漏改任一处即红在那儿（这正是注记里预告的"提醒"机制，但也把"一处漏改"变成第三种红）。
- **推荐：甲（维持现状 `>= 51`，不改）。** 理由三条，全部是可核对的形状事实：①"增减都红"这一价值已由两枚 `==` 在套件内提供，乙的净增量是**重复看守**；②乙把每次合法增长的改动面从 2 枚常量抬到 3 枚常量＋2 行注记，而这三处必须同笔（漏一处＝HEAD 红）；③甲与该件 docstring 的自述一致，改乙还要同时改写那段注记，属"为改判据而改文案"。
- 若人工选乙：改法＝`tests/test_questionnaire_design.py:109` 的 `>= 51` → `== 51` ＋同笔订正 `:100-108` 的 docstring/注记（否则文案与判据相反）。**本班未动这一行。**
- 附带一条同批项（台账 209⑩ 后半）：`tests/test_llm_engine.py` 的脚本形态使那枚双向守恒断言**没有用例名、没有 FAIL 行、单跑 rc=5**。函数化（包成 `def test_...`）属改测试结构，也交人工——它比 `>=`／`==` 之争更影响这组看守的可归因性。

---

## 6. 复算入口与本班实跑原文

```bash
cd /d/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from src.questionnaire.construct_kb import CONSTRUCTS as C, DOMAIN_KEYWORDS as D;print(len(C), len(D))"
# → 51 7

PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_questionnaire_design.py -q              # 22 passed
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_construct_kb_census.py -q                # 9 passed
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_construct_kb_extended_placeholder.py -q  # 7 passed, 1 skipped
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_llm_engine.py -q                          # no tests ran, rc=5（在册形态）

# 判据本体
grep -n "len(CONSTRUCTS)" tests/test_questionnaire_design.py tests/test_construct_kb_census.py tests/test_construct_kb_extended_placeholder.py
git show 5a8c9ce -- tests/test_questionnaire_design.py tests/test_llm_engine.py

# 全局清单型门禁单列加跑（w46 §B psy91 点名）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"
# → 1 failed, 19 passed, 5530 deselected；唯一红 = test_export_gate_global_scan::test_all_download_buttons_accounted_for
#   offender src/ui/questionnaire_panel.py ＝ 待人工台账第 81 条在册红（clean@HEAD 同红），本班未消红
```

本班产物只此一件（`docs/insights/s927-42-boundary-tighten.md`）＋ 信箱侧 `zcode-bridge/outbox/s927-42.result.md`。
判据、常量、docstring、`construct_kb.py`、`construct_kb_extended.py`、census 族三件、测试结构全部零改动；他班 12 枚在途件（含 `tests/test_cfa_sem_golden.py` 的 59/49 与 `result_card.py`）一律未碰。
