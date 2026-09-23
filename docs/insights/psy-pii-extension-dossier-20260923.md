# psy 座机分机号脱敏残留裁决材料（s923-33，只读设计稿）

- 班次：`qoder-executor-20260923-0022-psy15` ／ 2026-09-23（claim 17:49）
- 被试件：`src/utils/privacy_ethics.py`（**零改动**）、`src/utils/guardrails.py`（零改动）
- 🔴 **红线域自认**：隐私检测规则／隐私分级＝本班只出设计稿。一个正则字符都没改，两案都不自签，处置一律落「需人工裁决」。
- 探针：`tmp/s923-33/probe.py`（现状 12 形态）＋ `tmp/s923-33/pipeline.py`（两案全管道对照），均 gitignored、纯内存、不 import 测试件。

## 0. 结论先行

1. 🔴 **卷宗前提已被否证（最重要一条）**：s922-124 记的「座机号脱敏后分机号残留（`… 转 802`）」**在 2026-09-22 已被 pd01（`20260922-1830`）修掉**，并且已有一族在册用例锁死。盘上现状：`转 802`／`转802`／`分机 802`／`（分机号 802）`／`ext. 802`／`#802`／`extension 802` **7 种形态全部逐字脱敏干净**（`tests/test_guardrails_pii_probes.py:156-176`，且该文件 `:35` 的交接口注释就写着"分机号残留**已修**"）。
2. **但残留问题没有消失，只是换了形态**：实测 12 形态里仍有 **6 条留数字**，其中 3 条是"关键字缺失/超限"的新缺口，3 条属已登记在册的漏检（不属本单）。真正的**未在册残留**是这三类：
   - `座机：010-12345678-802` ⇒ 脱敏产物 `[REDACTED_LANDLINE]-802`（卷宗点名的连字符形态，**这条仍然漏**）
   - `座机：010-12345678（802）` ⇒ `[REDACTED_LANDLINE]（802）`（括号内无关键字）
   - `座机：010-12345678 转 1234567`（分机 7 位，超 `\d{1,6}`）⇒ `[REDACTED_LANDLINE] 转 1234567`
3. **两案都各有硬代价**（§4 全管道实测）：案 A（并入 landline、关键字改可选）修得掉连字符与括号形态，但会把"号码后跟年份/工位编号"当分机吞掉；案 B（新增 `extension` 规则）**修不掉连字符与括号形态**（它要求关键字），却会把任何 `#数字`／`转 NNN` 在**没有座机上下文**时也认成 high 档 ⇒ 直接触发导出门禁阻断，并对 7 位分机产生 `[REDACTED_EXTENSION]7` 这种**半吞半留的新残留**。
4. **推荐**：先按"案 A 的收窄版"（只把 `[-#]` 与"括号内纯数字"两种**强指向性**写法并入，不动空格裸数字）走；它同时是**只收紧不放宽**的形态，与本文件内 pd01 自己立下的"只许收紧"约束一致。但任何一条落地都要**四件一体**同改（见 §6），且属隐私分级 ⇒ **交人工自签，执行手不得代签**。

## 1. 锚点与前提逐条复核

```
$ cd /d/code/psy-analysis && rg -n '"landline"|电话\|座机\|tel' src/utils/privacy_ethics.py
65:    "landline": (
66:        r"(?i)(?:电话|座机|tel(?:ephone)?)\s*[：:=]?\s*0\d{2,3}-?\d{7,8}"
$ cd /d/code/psy-analysis && rg -n "分机号残留" tests/test_guardrails_pii_probes.py
35:  - 上面第 2 条点名的"座机加分机"分机号残留**已修**（`_PATTERNS["landline"]` 的替换段吃到分机号）。
170:    """收紧面①：座机后挂的分机号不许活到导出文本里（旧行为只摘主体号，留 "转 802"）。"""
```

| 卷宗前提 | 盘上实况 | 判定 |
|---|---|---|
| `src/utils/privacy_ethics.py:62` 是 landline 那条 | 现为 **:65-68**，且内容是**两段拼接式**（多了分机可选组） | 🔴 **锚点漂移 ＋ 内容已变** |
| 引文 `"landline": (r"(?i)…0\d{2,3}-?\d{7,8}(?!\d)", "high")` | 单行式已不存在；`(?!\d)` 现在挂在**第二个片段**末尾 | 🔴 否证（引的是修前旧版） |
| 「座机号脱敏后分机号残留（`… 转 802`）」 | `转 802` 已闭合（在册 7 形态用例逐字断言 `"802" not in text`） | 🔴 否证 |
| 「两条都属"隐私面"，动正则即改检测规则，超出本单授权」 | 成立，且更强：本仓对该面还立了**双向护栏**（既防放宽、也防误吞） | ✅ 成立 |
| 「`-802`／`#802` 与 `转 802` 同属残留」 | `#802` 已闭合；`-802` 确实仍残留 | ⚠️ 部分成立（三形态里只剩两条，见 §2） |

## 2. 现状读数（12 形态，含卷宗点名三条）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-33/probe.py > tmp/s923-33/probe.out 2>&1; echo RC=$?
RC=0
$ rg -n "残留形态数" tmp/s923-33/probe.out
残留形态数 = 6/12
$ sed -n '5,40p' tmp/s923-33/probe.out
```

| # | 形态（合成样本，无任何真实号码） | 检出 | 脱敏产物 | 判定 |
|---|---|---|---|---|
| ① | `座机：010-12345678 转 802`（卷宗点名） | landline×1 | `[REDACTED_LANDLINE]` | ✅ 已闭合 |
| ② | `座机：010-12345678-802`（卷宗点名） | landline×1 | `[REDACTED_LANDLINE]-802` | 🔴 **残留 802** |
| ③ | `座机：010-12345678#802`（卷宗点名） | landline×1 | `[REDACTED_LANDLINE]` | ✅ 已闭合 |
| ④ | `座机：010-12345678 802`（无关键字＋空格） | landline×1 | `[REDACTED_LANDLINE] 802` | 🔴 残留（在册护栏**有意**不吞，见 §5） |
| ⑤ | `座机：010-12345678转802`（无空格） | landline×1 | `[REDACTED_LANDLINE]` | ✅ |
| ⑥ | `tel 010-12345678 ext802` | landline×1 | `[REDACTED_LANDLINE]` | ✅ |
| ⑦ | `座机：010-12345678（802）`（括号内无关键字） | landline×1 | `[REDACTED_LANDLINE]（802）` | 🔴 **残留 802** |
| ⑧ | `座机：01012345678 转 802`（主体无连字符） | landline×1 | `[REDACTED_LANDLINE]` | ✅ |
| ⑨ | `座机：010 1234 5678 转 802` | **无检出** | 原样不动 | 属**已登记漏检**（`座机空格分组`，`MISSED_VALUE_PROBES:77`），非本单新账 |
| ⑩ | `座机：010-12345678（转 802）` | landline×1 | `[REDACTED_LANDLINE]` | ✅ |
| ⑪ | `座机：010-12345678 转 1234567`（7 位分机） | landline×1 | `[REDACTED_LANDLINE] 转 1234567` | 🔴 **残留**（`\d{1,6}` 上限） |
| ⑫ | 一条文本里两处号码，第二处**无标签** | landline×1 | `[REDACTED_LANDLINE]，备用 021-65432100 转 100` | 属**已登记漏检**（`座机无标签裸号`，`MISSED:76`） |

**缺口定位（一句话）**：`:66-67` 的分机可选组把"**关键字**"当必要项（`(?:转|分机号?|extension|ext\.?|#)`），且数字上限钉死 `\d{1,6}` ⇒ 凡"分机号前没有中英文关键字"（②连字符、⑦括号）或"分机号超过 6 位"（⑪）就整段不吃，`(?!\d)` 又在连字符/括号处放行（后面不是数字）⇒ 主体被摘、分机留在导出文本里。

## 3. 两案设计（都不实施）

- **案 A（并入 landline）**：把分机组的关键字改为**可选**并允许 `[-#\s]`／全角括号作连接符。
- **案 A收窄（推荐候选）**：只加两条强指向性连接：`(?:-\d{1,6}|（\d{1,6}）|\(\d{1,6}\))`，**不**碰"空格＋裸数字"（那是在册护栏明确拒绝吞的形态）。
- **案 B（新增 `extension` 规则）**：`_PATTERNS` 追加一条独立规则（关键字＋数字），与座机解耦，可覆盖"无座机上下文但写了转 XXX"的行文。

探针里三版候选正则逐字见 `tmp/s923-33/probe.py:55-63`（`CAND_A`／`CAND_A2`／`CAND_B`）。

## 4. 全管道对照实测（案 A / 案 B 的净效果与误伤面）

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-33/pipeline.py > tmp/s923-33/pipeline.out 2>&1; echo RC=$?
RC=0
$ cat tmp/s923-33/pipeline.out
$ probe 全管道对照（顺序＝_PATTERNS 原序：id_card, phone, landline, email, api_key, password, messenger）
--- 身份证并列: 电话：010-12345678 11010119900307551X
    现 : '[REDACTED_LANDLINE] [REDACTED_ID_CARD]' {'id_card': 1, 'landline': 1}
    案A: '[REDACTED_LANDLINE] [REDACTED_ID_CARD]' {'id_card': 1, 'landline': 1}
    案B: '[REDACTED_LANDLINE] [REDACTED_ID_CARD]' {'id_card': 1, 'landline': 1}
--- 年份尾巴: 电话：010-12345678-2024 年立项
    现 : '[REDACTED_LANDLINE]-2024 年立项' {'landline': 1}
    案A: '[REDACTED_LANDLINE]年立项' {'landline': 1}          ← 误伤：年份被当分机吞掉
    案B: '[REDACTED_LANDLINE]-2024 年立项' {'landline': 1}
--- 卷宗②: 座机：010-12345678-802
    现 : '[REDACTED_LANDLINE]-802' {'landline': 1}
    案A: '[REDACTED_LANDLINE]' {'landline': 1}               ← 修好
    案B: '[REDACTED_LANDLINE]-802' {'landline': 1}           ← 不修（B 要关键字）
--- 括号无关键字⑦: 座机：010-12345678（802）
    现 : '[REDACTED_LANDLINE]（802）' {'landline': 1}
    案A: '[REDACTED_LANDLINE]' {'landline': 1}               ← 修好
    案B: '[REDACTED_LANDLINE]（802）' {'landline': 1}         ← 不修
--- 转 7 位⑪: 座机：010-12345678 转 1234567
    现 : '[REDACTED_LANDLINE] 转 1234567' {'landline': 1}
    案A: '[REDACTED_LANDLINE] 转 1234567' {'landline': 1}     ← 不修（仍是 1..6 上限）
    案B: '[REDACTED_LANDLINE] [REDACTED_EXTENSION]7' {'landline': 1, 'extension': 1}
                                                            ← 🔴 新形态残留：半吞半留，比原样更难被任何下游检出来
--- 订单号: 订单号 #802
    现 : '订单号 #802' {}
    案A: '订单号 #802' {}
    案B: '订单号 [REDACTED_EXTENSION]' {'extension': 1}        ← 🔴 无座机上下文也认 high 档
--- 护栏①: 办公 021-65432100 8023   现/案A/案B 全部原样 {}      ← 三条在册反向护栏均未被 A/B 破坏
--- 护栏②: 座机：010-12345678 备注 20231234567   三版都保留 20231234567
```

### 误伤面评估（裁决要点）

| 维度 | 案 A（关键字可选＋`[-#\s]`） | 案 A收窄（只认连字符与括号） | 案 B（独立 extension 规则） |
|---|---|---|---|
| 修好 ②（`-802`） | ✅ | ✅ | ❌ |
| 修好 ⑦（`（802）`） | ✅ | ✅ | ❌ |
| 修好 ④（空格裸数字） | ✅（但正是在册护栏**有意不吞**的形态） | ❌ | ❌ |
| 修好 ⑪（>6 位） | ❌（要另改上限） | ❌ | ⚠️ 半修 ⇒ **造新残留** `[REDACTED_EXTENSION]7` |
| 误伤业务编号 | 🔴 会（`-2024 年立项`、`-0001 号工位` 被吞） | ✅ 低（连字符＋括号仍强指向，但要目检年份类） | 🔴 会（`#802` 订单号／工号一律认 high） |
| 对导出门禁的影响 | 少吞 ⇒ 更多文本被摘，不误拦 | 同上、幅度更小 | 🔴 **多拦**：high 档全量阻断（`privacy_ethics.py:_BLOCKING_MEDIUM_TYPES` 之外的所有 high 都拦），非个人信息的 `#编号` 会被拦成 PII |
| 是否触碰"只许收紧"约束 | ⚠️ 部分是放宽（吞非分机数字）→ 违反 | ✅ 基本守住 | ⚠️ 新增检测面＝新语义，另档另判 |
| 与在册反向护栏的相容性 | 通过（三条实测未破） | 通过 | 通过（但 ⑪ 产生新形态，现有断言测不到） |

## 5. 在册护栏清单（改动前必须逐条对视，别绕过）

```
$ cd /d/code/psy-analysis && rg -n "def test.*(landline|extension|value_rule_count|inventory)" tests/test_guardrails_pii_probes.py
123: def test_probe_inventory_matches_the_recorded_baseline_counts()        # 25=9+16（值级）、20=10+10（列名）
169: def test_landline_extension_is_redacted_together_with_the_number(sample)          # 7 形态，逐字 == "[REDACTED_LANDLINE]"
183: def test_landline_extension_group_does_not_swallow_unrelated_trailing_digits(...) # 反向护栏：无关键字不得吞
191: def test_landline_fix_did_not_loosen_any_registered_miss()                        # 两条已登记漏检必须仍漏
354: def test_value_rule_count_and_names_are_pinned_so_extensions_are_visible()        # 值级正则名单钉死 7 条
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_guardrails_pii.py tests/test_guardrails_pii_probes.py -q
73 passed, 26 xfailed in 2.22s      # 现状基线（本班零改动下取得，可直接当对照）
```

⚠️ **`_PATTERNS` 是"一处定义、两面消费"**：`scan_text_for_sensitive`（`:83`，门禁检出）与 `redact_sensitive_text`（`:99`，导出/归档脱敏）共用同一张表（`:102` docstring 明写"使用与导出预检完全相同的模式，避免出现'门禁能发现、归档却未处理'的分叉"）。⇒ 任何案都**同时改判"检不出"与"不脱敏"两件事**，且案 B 会让门禁多拦。这正是"不自签"的理由。

## 6. 若放行，需同步的一体清单（按案分列）

- **案 A／A收窄（四件一体）**：① `src/utils/privacy_ethics.py:66-67` 正则；② `tests/test_guardrails_pii_probes.py:156-164` 的 `LANDLINE_EXTENSION_FORMS` **补 ②⑦ 两形态**（否则改动无看守＝静默失明的绿）；③ 反向护栏 `:179-181` 的样本要按"年份尾巴/编号尾巴"是否被吞重新取**反例**（案 A 全版会把 `-2024` 吞掉 ⇒ 该护栏必须新增一条断言，否则它测不到自己该测的东西）；④ `test_landline_fix_did_not_loosen_any_registered_miss`（`:191`）——若改后两条已登记漏检被认领，**必须人工重判漏检名单**，不许执行手自行把它们挪出 `MISSED_VALUE_PROBES`（那是**计数口径改动**，§五.4 规定一律停手）。
- **案 B（五件一体，且含计数口径）**：上述①②③④ 之外，还要 ⑤ `test_value_rule_count_and_names_are_pinned_so_extensions_are_visible:354`（名单从 7 条变 8 条）**＋** `:123` 的 `25=9+16`／`20=10+10` 基线两数**重跑探针再记**。⇒ 案 B 天然要改计数口径 ⇒ **按纪律一律 partial 交人工**，本班连"重记基线"都没做。

## 7. 遗留与未坐实

1. 🔴 **停手线命中确认（引卷宗原句）**：「隐私检测规则红线：只出设计稿。……改正则留授权单」＋「完成标准：……`src/utils/privacy_ethics.py` 零改动」⇒ 本班按此执行：**未改任何正则、未改脱敏函数、未加规则、未动门禁分级、未重记探针基线**，两案都只是设计稿。
2. **需人工裁决**：三形态残留（②⑦⑪）是否要修、修哪案；案 A 全版对"号码后跟 4 位年份/工位编号"的误伤是否可接受（这是**放宽**方向，与文件内 pd01 立下的「只许收紧」注释互斥，须 owner 亲自裁决）。
3. **未坐实**：④「空格＋裸数字」被在册护栏**有意**不吞（`test_..._does_not_swallow_unrelated_trailing_digits` 的反例 `办公 021-65432100 8023`），但同一形态在**有座机标签**时（`座机：010-12345678 802`）究竟是"真分机"还是"下一列数字"，本班无法判定——需要真实导出文本样本目检，而真实样本涉隐私、本班不采集不落档。
4. **未坐实**：分机号位数上限 6 位是否够（⑪ 用 7 位当反例）。真实号码位数分布属数据面，本班无样本。
5. 顺带登记（不属本单）：`tests/test_guardrails_pii_probes.py:11-12` 自己写明「"座机加分机／微信号／住址门牌／病历号"写在**内容**里时，`_PII_PATTERNS` 结构上不可能检出——不是漏检，是不归它管」⇒ `guardrails.py:371-391` 的列名面与本档的值级面是两条通道，讨论 A/B 时不要把两通道混成一件事。
