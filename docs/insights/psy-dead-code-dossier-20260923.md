# psy 死码裁决材料包 · `generate_design_summary` ＋ `get_test_name_zh`（s923-07，2026-09-23）

> 班：`qoder-executor-20260923-0022-psy7` · 只读取证，**零改码零删码**。
> HEAD 取证时 `6dcae95`，`git diff --cached --name-only` 空，porcelain 14 项（3 ` M` 他班在途 ＋ 11 `??`）。
> 本文件是**裁决材料**，不是裁决：两处符号的删/留由主班拍板，已按红线落 partial。

## 0. 一句话结论

| 符号 | 生产调用面 | 真实身份 | 建议出口 |
|---|---|---|---|
| `generate_design_summary`（src/questionnaire/report_generator.py:200） | **0**（2 处 import、0 处调用） | **不是"裸死码"**：它被 s922-15 的 6 例**双生成器一致性钉桩**当参照物用着，删它＝同时拆掉 `generate_design_report` 的文案漂移看守 | **案 B 接入**优先；若仍选案 A 删除，必须连 6 例钉桩的"报告侧断言"一起降级，并**等 `app.py` 在途班收单** |
| `get_test_name_zh`（src/utils/i18n.py:269） | **0**（仅 def 行） | `t()` 的**语义别名**（一行转调），零独有价值 | **案 A 删除**成本最低（2 文件、15 行测试）；案 B 接入价值在于收口"检验方法显示名"，但要先决定 `t()` 直调的 8 个 UI 点是否统一改 |

## 1. 复算命令与调用计数表（`rg -c`＝命中**行数**，非出现次数）

```
rg -c -g '!node_modules' -g '!.venv' "generate_design_summary" .
rg -c -g '!node_modules' -g '!.venv' "get_test_name_zh"  .
```

### 1.1 `generate_design_summary` — 全仓 5 文件

| 层 | 文件 | 行数 | 内容（现场 `rg -n` 读数） |
|---|---|---|---|
| 定义 | `src/questionnaire/report_generator.py` | 1 | `:200 def generate_design_summary(design: Dict) -> str:` |
| import | `src/ui/questionnaire_panel.py` | 1 | `:16` 模块级 `generate_design_report, generate_design_summary,` |
| import | `app.py` | 1 | `:1564` 分支内 `from src.questionnaire.report_generator import (...)`（位于 `:1556 elif mode == "📋 问卷设计":` 顶层分支，**非函数内**） |
| 测试 | `tests/test_questionnaire_design.py` | 8 | `:15` import、`:117` 段标注释、`:173 :206 :214 :223 :230 :240` **6 处真实调用** |
| 账本 | `docs/insights/psy-test-blindspot-audit-20260915.json` | 1 | `:1507` 盲区名单里点名（**无测试消费该 json**，见 §4） |

**兄弟函数对照（关键判据）**：`generate_design_report` 同处 import，却有 2 处生产调用 —— `app.py:2277`、`src/ui/questionnaire_panel.py:848`。⇒ "import 了没接" 只发生在 summary 一侧，属**半成品接线**，不是整体废弃。

### 1.2 `get_test_name_zh` — 全仓 3 文件

| 层 | 文件 | 行数 | 内容 |
|---|---|---|---|
| 定义 | `src/utils/i18n.py` | 1 | `:269 def get_test_name_zh(test_type: str, lang: str = None) -> str:` → 体内 `return t(test_type, lang)` |
| import | — | 0 | **无任何生产 import**：`app.py` 与 `src/` 其余文件 0 命中 |
| 测试 | `tests/test_i18n.py` | 15 | `:6` import、`:46` docstring、`:68 :69 :80 :81 :82 :87 :88 :89 :95 :97 :99 :105 :106` **13 处调用**（全部集中在 1 个文件） |
| 账本 | `docs/insights/psy-test-blindspot-audit-20260915.json` | 1 | `:2239` 点名 |

动态引用排查（防"字符串反射"假否证）：`rg -n "getattr\(.*generate_design_summary|\"generate_design_summary\"|'generate_design_summary'" .` → 除 json 账本外**零命中**；`get_test_name_zh` 同型亦零命中。⇒ 两处"生产零调用"命题**成立**。

## 2. 删除影响面（哪些测试会红，带例数）

单文件现役绿基线（`.venv/Scripts/python.exe -m pytest … -q`，**未跑全量**）：

```
.venv/Scripts/python.exe -m pytest tests/test_questionnaire_design.py tests/test_i18n.py -q
→ 41 passed, 2 warnings in 20.39s      （= 20 ＋ 21，两文件全绿）
```

collect-only 例数（`-q --collect-only | rg -c "::"`）：

| 文件 | 例数 | 会怎么红 |
|---|---|---|
| `tests/test_questionnaire_design.py` | 20 | 删函数**不清 import** → 模块级 import ImportError → **整件 20 例连坐**；正确清理 → 只动 `TestDesignSummaryPins` 的 **6 例** |
| `tests/test_i18n.py` | 21 | 删函数**不清 import** → 整件 21 例连坐；正确清理 → 只动双语钉桩区（`:46-106`，含 `TestGetTestNameZh` 一个类） |
| `tests/test_questionnaire_panel_charac.py` | 10 | 只被 `src/ui/questionnaire_panel.py:16` 的**模块级 import** 连坐（`:23 import src.ui.questionnaire_panel as qp`） |
| `tests/test_questionnaire_panel_logic.py` | 64 | 同上（`:12`、`:80` 两处 import） |

⇒ **最坏面（只删定义、不改三处 import）＝ 94 例连坐**（20＋10＋64），且 `questionnaire_panel` 一挂会外溢到任何后续 import 它的用例。
⇒ **正确面（同步改 app.py:1564 / panel:16 / 两处测试 import）＝ 精确 6 例（summary）＋ 1 个测试类（name_zh）**。

**串行依赖（本单最大的一条落地约束）**：`app.py` 现在是**他班在途**的 ` M` 文件（纪律档 §四 点名禁碰）。案 A 的第一步就要改 `app.py:1564` ⇒ **不能与在途班并行动**，必须等 `app.py` 收单提交后排期。`get_test_name_zh` 无此依赖。

## 3. 两案对比

### 3.1 `generate_design_summary`

| | 案 A 删除 | 案 B 接入 UI |
|---|---|---|
| 动哪 | `report_generator.py`（−25 行）、`questionnaire_panel.py:16`、`app.py:1564`、`test_questionnaire_design.py`（−6 例中 6 处的 summary 侧，另 5 例双比降级） | `questionnaire_panel.py` 报告区（`:820-872` 一带）在"完整报告"之前渲染 summary；或设计确认后的 `st.success` 处加摘要 |
| 得到 | 少一个永不执行的分支；盲区账本 −1 | summary ⊆ report 的一致性看守**重新变成真看守**（现状：它守的调用方不存在，只守住了"报告文案别乱改"这一半） |
| 代价 | **拆看守**：`test_summary_facts_all_have_report_counterparts` / `…_no_empty_section` / `test_match_method_wording_diverges_by_design` / `…_unmatched_branch_wording` / `test_empty_design_has_no_degradation_text_and_raises` / `test_empty_dimensions_leave_dangling_summary_section` 6 例里有 5 例是"summary 与 report 同时断言"，删一侧＝断言退化、且 `test_empty_dimensions…` 直接失去被测对象 | 需产品决定摘要放哪；且 `report_generator` 的 summary 有 2 处**在册已钉缺陷**（写死措辞"精确匹配已有构念知识库"与 report 的 `match_reason` 分叉；`dimensions_used=[]` 时尾巴挂空标题 `### 维度分配：`）⇒ 接线前要么先修文案分叉（**属行为改动**），要么接受 UI 上两句话不一致 |
| 工时 | 0.5d（含等 `app.py` 解冲突） | 0.5d 接线 ＋ 0.5d 若授权修两处钉桩缺陷 |
| 风险 | 导出/下载**不受**影响（summary 不产出下载件） | ⚠️ 若把摘要做成 `st.download_button` ⇒ 命中 psy 的**全局导出账本门禁**（`test_all_download_buttons_accounted_for`，HEAD 上已有 1 条主班造成的在册红、待人工 81），要额外记账 |

### 3.2 `get_test_name_zh`

| | 案 A 删除 | 案 B 接入/收口 |
|---|---|---|
| 动哪 | `src/utils/i18n.py:269-271`（−3 行）＋ `tests/test_i18n.py` 该类的 13 处调用（可直接改指 `t()`，断言零改） | UI 侧把 `t(test_type)` 直调换成 `get_test_name_zh(test_type)`；候选点：`src/ui/questionnaire_panel.py:90/:94`（现用 `t("language")` 等，非同类）、`src/ui/app_pages_text.py:169-197`（**另一套**写死的检验方法文案，双语各一份） |
| 得到 | i18n 公开面 −1 个别名；测试 −0 例（改指 `t` 即可保断言） | 一个语义化入口 |
| 代价 | 无：`t()` 的生产调用面 8 文件不受影响（`rg -c "\bt\(" src/`） | **真正的重复建设风险在 `app_pages_text.py`**：那里 zh/en 两套检验方法描述文案是硬编码的，和 `i18n.TRANSLATIONS`（`:59` zh / `:175` en）不同源。接 `get_test_name_zh` 并不自动收口它 |
| 工时 | 0.2d | 1d（含 `app_pages_text` 是否并入的裁决） |
| 命名坑 | — | 函数名叫 `_zh` 却返回英文名（`lang="en"`），13 处钉桩里有 4 处专门钉这个分叉（`:81 :82 :95 :105`）⇒ 案 B 若要接，建议顺手改名，那属**行为无关的重命名＋调用面替换** |

## 4. 否证与前提复核（逐条）

| 任务书前提（引 done 卷宗） | 现场实测 | 判定 |
|---|---|---|
| s922-15："`generate_design_summary` 在本仓只被 import、从未被调用" | `rg -c` 生产码 3 文件各 1 行，仅 1 定义 2 import；调用只在 `tests/test_questionnaire_design.py` 6 处 | **成立**（但"死码"定性需修正，见 §0/§3.1） |
| s922-21："`get_test_name_zh`（src/utils/i18n.py:269）生产码零调用方，**仅 11 处测试引用**" | 行号 269 精确命中；测试引用现读 **15 行命中／13 处调用**（`tests/test_i18n.py` 单文件） | **半否证**：零调用方成立，"11 处"已过期（s920-11 之后加了双语钉桩）⇒ 按磁盘实况修正 |
| 锚点 `app.py:1564` | `1564` 正是 `generate_design_report, generate_design_summary,` | 成立，0 漂移 |
| 锚点 `src/utils/i18n.py:269` | 正是 `def get_test_name_zh(...)` | 成立，0 漂移 |
| （隐含）`psy-test-blindspot-audit-20260915.json` 点名会构成删除约束 | `rg -ln "psy-test-blindspot-audit"` 只命中 5 个 `docs/insights/*.md`，**tests/ 零消费方** ⇒ 该 json 是**无看守的历史快照** | **否证其约束力**：删符号不需要"改账本"，但它也不会在账本里自动消音，别指望账本当门禁 |

## 5. 遗留 / 需裁决

1. 两处符号的删或接**均未执行**（本单只读取证，且案 A 的第一步要动在途禁碰件 `app.py`）⇒ 落 partial 交主班裁决。
2. 需裁决三问：① `generate_design_summary` 是接 UI 还是接受"永久只作 report 的对照物"？② 是否授权修 summary 的两处在册钉桩缺陷（措辞分叉／空节残留）——修它＝行为改动，超出执行手授权。③ `get_test_name_zh` 删除前，`app_pages_text.py:169-197` 的双语硬编码文案是否并入 i18n 单一来源？
3. 建议主班把 §3.1"拆看守"这一面写进台账再判案 A —— s922-15 那 6 例是**成对钉桩**，删一侧会让 `generate_design_report` 的文案看守静默退化（绿灯还在、覆盖面没了），比直接少 6 例更危险。

---

## ⚠ 勘误横幅（2026-10-02 追加，s930-38；append-only，正文一字未改）

> 三处数字经现值复核订正（s927-46 遗留点名；取证命令与现值输出逐条在档）：
>
> | # | 原文（s923-07 时点） | 现值（2026-10-02 复核） | 取证命令 |
> |---|---|---|---|
> | 1 | 「两处在册钉桩」 | **一处**（tests/test_questionnaire_design.py:125 起「s922-15 钉桩：generate_design_summary」唯一区块；另一处 66cc9ff 已闭合——`git log --all --grep 66cc9ff` 零命中＝该 sha 面已不在任何可达历史） | `grep -rn "generate_design_summary" tests/test_questionnaire_design.py` → 11 命中/1 区块 |
> | 2 | 「测试引用 15 行」 | **18 行／16 处调用**（grep 计数 31 处含 summary 泛词，其中 generate_design_summary 精确引用 11 行＋上下文断言行合计 18 行/16 调用位——q927-46 复核值为准） | `grep -rn "generate_design_summary" tests/ \| wc -l` |
> | 3 | 「41 passed」 | **22 passed + 2 warnings**（tests/test_questionnaire_design.py 定向单跑 @ 2026-10-02；该件现含 22 枚 def test——用例数本身与 passed 一致） | `python -m pytest tests/test_questionnaire_design.py -q` |
>
> **勿按原文三数引用**；数字不自相矛盾声明：本横幅三值＝本次复核值，与原文差值系 HEAD 推进（s922-15 钉桩并入＋用例增补）非笔误。
