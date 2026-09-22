# psy session_state 下标式裸读面普查（s922-136，2026-09-23 夜班实取）

> 只读普查材料，补 `docs/insights/psy-session-state-attr-read-census-20260921.md`（下称**上份**）
> 遗留第 4 条明示未做的对偶面：「本普查只看**属性式**读取，下标式对偶面未纳入逐点判定」。
> 本档扫下标式面，并与属性式合并成一张总风险面表，最后回答上份留的问题：
> **「两种形态是否同一条纪律」**。
>
> - 零改动：不改 `src/`、不改 `app.py`（该件此刻仍是别班的 ` M` 在途件）、不改任何统计/经济/医疗数值。
> - 取值时刻 **2026-09-23T01:06–01:16**，psy HEAD **`bcb21f4`**，解释器 `.venv`（Python 3.12.9 / streamlit 1.59.1）。
> - 判定分类只登记，不处置；需要动码的建议一律写在第六节，交主班裁。

## 〇、先记三处与任务书/上份不一致的实测（前提否证，按实况收窄）

| # | 书面前提 | 现场实测 | 证据 |
|---|---|---|---|
| 1 | 锚点 `app.py:299`＝`for key, val in _defaults.items():` | **不成立**：现读在 **`app.py:116`**（−183）。`_defaults` 字典本体同步从 :273 → **`app.py:90`** | `python -c` 打行 ＋ `git show 4230640:app.py` 里确为 :273/:299 |
| 2 | 漂移原因 | 上份落档（commit `4230640`，09-21 21:52）之后，三笔「迁出 app.py」提交把 app.py 逐级削薄：**2698 →（`49cee8a` s922-18，03:23）2515 →（`385ae24` s922-101，04:20）2485 →（`f1b4a38` s922-102，04:35＝现 HEAD）2433**；现工作树 2405（他班在途 ` M` 再 −28） | `git log --format='%h %ad %s' --date=short -- app.py` ＋ 逐 commit `git show <c>:app.py \| wc -l` |
| 3 | 上份的 67 点属性式表可直接并表 | **行号整体失效**（同一批迁出），且**总点数 67 → 65**。少的 2 点全部是 `app.py` 的 `st.session_state.language`，被 `f1b4a38`（迁出片 7a「问卷页混装侧栏」）搬走：该 commit 前 app.py 内 `session_state.language` 命中 **3**、之后 **0** ⇒ 属性式面 −2 读 −1 写 | `git log -S "st.session_state.language" -- app.py` ＋ `git show <c>:app.py \| grep -c` |
| 4 | 扫描面「app.py＋src＋scripts 共 257 文件」 | 现读 **260** 文件（＋3，来自 s922-18/101/102 新拆出的模块）。`scripts/` 11 个文件里两式命中均为 **0**（上份亦然） | 附录 A 命令 1 |
| 5 | （并发盘，非任务书前提但影响行号） | 本档取值窗口 **01:06–01:17** 内，兄弟子班改了 `src/ui/questionnaire_panel.py`（该件由「未改」变 ` M`）⇒ 该文件的属性读行号由 :94/:98/:440/:441 → **:95/:99/:441/:442**（＋1 行）。两次的**合计读数完全一致**（65/14/5/9、119/27、162/14/440），只是那 4 个行号漂移 ⇒ 本档正文表未引用该文件行号，不受影响；引用本档行号者请现跑附录 A 命令 1 | `git diff --name-only` 两次对照 ＋ 复跑附录 A |


**因此本档的合并表是「今日重算的属性式 65 点 ＋ 新扫的下标式面」，不是抄上份的 67 点。** 上份的四条承重结论本身**仍然成立**（未登记键的两点 `analysis_pipeline`/`polished_draft` 今日复算仍是 4 个点位，与上份结论 2 逐字相同），只是行号需要整体重取——已另登记给主班（见 result 的回报）。

## 一、口径

- **下标式读** = AST 里 `Subscript(value=<st.session_state>, ctx=Load)`。
  写＝`ctx=Store`，删＝`ctx=Del`，成员测试 `"k" in st.session_state`（`Compare`＋`In/NotIn`）**不是读**，单列成「守卫」类。
- **谓词沿用上份同一条**：只认字面写法 `st.session_state`（`Attribute(attr='session_state', value=Name('st'))`）。
  ⇒ 经别名（`wiz = st.session_state`、形参 `session_state`）的下标读**不进主口径**，本档单列 **3.3 节**并给计数，避免与上份不可比。
- **排除的安全形态**：`.get/.pop/.setdefault/.update/.keys/.values/.items/.clear/.to_dict`（实测它们**天然不抛**，见第五节证据）。
- 三分类（任务书点名）：
  **A 键在 `_defaults`** ／ **B 就近守卫**（读点前同一块/同一函数内有 `in` 测试、`.get()` 真值判定或前置写）／ **C 真裸读**（既不登记也无守卫）。
  动态键（`st.session_state[var]`／f-string 键）静态不可判 ⇒ **单列 D 类**，逐点人工核。
- 行号一律**工作树版**（`app.py` 带他班在途 ` M`，净 −28 行；`git diff --stat -- app.py` → `12 insertions(+), 40 deletions(-)`）。

## 二、双路计数（AST 路 ＋ 正则路，差异留痕）

| 量 | AST 路 | 正则路 | 差 | 差的解释 |
|---|---|---|---|---|
| 下标式**总访问**（读＋写＋删） | 162（读 19＋写 143＋删 0） | `grep -o "st\.session_state\["` → **162** | **0** | 无需解释：散文里不会写 `st.session_state[` |
| 下标式**字面键读** | **14** | **14**（`["k"]` 且不紧随 `] =`） | **0** | 两路一致，本档主口径取 14 |
| 下标式**动态键读** | **5** | 不计 | — | 正则无从判定变量键 |
| 属性式总访问（读＋写） | **179**（读 65＋写 114） | `grep -o "st\.session_state\.\w+"` → **440** | **261** | 正则把安全方法也算进来了：`.get` 196／`.pop` 53／`.setdefault` 6／`.clear`/`.update`/`.keys`/`.items` 各 1 ＝ **259**；余 **2** 条是 `src/ui/paper_writing_ui.py:609` 的 **docstring 散文**（`依赖 st.session_state.plan + st.session_state.analysis_output；`） |
| 成员守卫 `in`/`not in` | **13**（字面键 8＋动态键 5） | 不另计 | — | — |

⇒ **本档口径**：下标式面两路**零差异**，可以放心用；属性式面的 **＋2 正则虚高与上份完全同值、同一行**（上份也记了「差 2 个读全在 `paper_writing_ui.py:609` 散文里」）⇒ 「采 AST 为准」这条约定经两档复证成立。

## 三、下标式逐点表（本单主面）

### 3.1 A/B/C 分类：字面键读 14 点

| 位置 | 键 | 类 | 最近守卫依据（现场读码核对，非工具自判） |
|---|---|---|---|
| app.py:2365 | `analysis_output` | **A**（＋本键真值守卫） | :2364 `if st.session_state.get("analysis_output"):`；键在 `_defaults`（app.py:90 表内） |
| src/ui/experiment_design_ui.py:406 | `_exp_protocol_docx` | B | :403 `if st.session_state.get("_exp_protocol_docx"):` 真值 ⇒ 键必在场；同块 :397 写 |
| src/ui/undergrad_wizard.py:230 | `_reviewer_qa` | B | :223 `if "_reviewer_qa" not in st.session_state:` → :224 `= {}` 补种，读点在其后同块 |
| src/ui/undergrad_wizard.py:236 | `_reviewer_qa` | B | 同上；注意本行是 **`st.session_state["_reviewer_qa"][str(i)] = ans`**——外层 Store、内层读，AST 判为读正确（读-改-写） |
| src/ui/undergrad_wizard.py:252 | `_reviewer_qa` | B | 同上（推导式里 `.items()`） |
| src/ui/undergrad_wizard.py:288 | `_reviewer_revised` | B | :284 `if st.session_state.get("_reviewer_revised"):`；:277 写 |
| src/ui/undergrad_wizard.py:458 | `_delivery_zip` | B | :454 `if st.session_state.get("_delivery_zip"):`；:446 写 |
| src/ui/undergrad_wizard.py:780 | `_collection_zip` | B | :776 get 真值守卫；:773 写 |
| src/ui/undergrad_wizard.py:855 | `_handbook_pdf` | B | :852 get 真值守卫；:843 写 |
| src/ui/undergrad_wizard.py:896 | `_reviewer_student_text` | B | :895 get 真值守卫；:176 写 |
| src/ui/undergrad_wizard.py:898 | `_reviewer_revised` | B | :897 get 真值守卫 |
| src/ui/undergrad_wizard.py:1541 | `_docx_bytes` | B | :1537 get 真值守卫；:1529 写 |
| src/ui/undergrad_wizard.py:1661 | `_figures_zip` | B | :1657 get 真值守卫；:1652 写 |
| src/utils/env_check.py:316 | `_env_deep_check` | B | :313 `if "_env_deep_check" not in st.session_state:` → :314 就地补种（与上份 `pipeline_manager` 同型） |

**小计：A 1 ／ B 13 ／ C 0。**
14 点里**只有 1 点**（`analysis_output`）的键在 `_defaults`——⇒ **上份「63/67 都靠 `_defaults` 兜住」的承重在下标式面上几乎不适用**（详见第六节结论 1）。

### 3.2 D 类：动态键读 5 点（静态不可判，逐点人工核）

| 位置 | 键来源 | 人工判定 |
|---|---|---|
| src/ui/cleaning_wizard.py:194 | `df_key = f"{prefix}_df"` | 成员测试本体（`df_key not in st.session_state or st.session_state[df_key] is None`），`or` 短路 ⇒ 读只在键存在时发生。**安全** |
| src/ui/cleaning_wizard.py:198 | 同上 | :194-196 守卫＋补种后的读。**安全** |
| src/ui/cleaning_wizard.py:199 | `log_key = f"{prefix}_log"` | 🔴 **本面唯一的跨键依赖**：:194 测的是 `df_key`，`log_key` 只在 :196 的**同一 if 分支里**被写。若 `*_df` 在场而 `*_log` 缺席 ⇒ **KeyError**。可达性核查：全仓只有 `:195-196 / :244-245 / :320-321` 三处成对写，且 `workspace.py:606-610` 的恢复是 **9 键白名单**（不含 `*_df`/`*_log`）⇒ **现状不可达**，但「两键永不同生同灭」这条约定**没有任何断言锁住**（上份结论 4「他键守卫」在下标式面的同型样本） |
| src/ui/project_panel.py:47 | 推导式 `for k in [...]` | 同一推导式 :52 的 `if k in st.session_state` 自身过滤 ⇒ **安全**（这正是上份结论 3 讲的 clear 现场） |
| src/utils/workspace.py:327 | `for key in list(st.session_state.keys())` | 键直接取自 `keys()` ⇒ **在场性由来源保证**，安全 |

**D 类小计 5，其中 1 点（cleaning_wizard:199）登记为脆点，其余 4 点由守卫/来源保证。**

### 3.3 别名面（上份谓词看不见的一层，单列不并主口径）

`ssobj()` 只认字面 `st.session_state`，而本仓有 **15 处 `X = st.session_state` 赋值别名** ＋ **23 个文件里 87 个函数的形参名就叫 `session_state`**。经别名的下标读共 **9 点**，逐点核后**全部有就近守卫、零真裸读**：

| 位置 | 键 | 依据 |
|---|---|---|
| src/ui/evidence_table_panel.py:32, :34 | `_STORE_KEY` | :32 `not in … or … is None` ⇒ :33 补种 ⇒ :34 读。**安全** |
| src/ui/questionnaire_import_panel.py:61, :62 | `_RAW_DF_KEY` | :61 `if _RAW_DF_KEY in session_state and session_state[_RAW_DF_KEY] is not None:` 短路 ⇒ :62 读。**安全** |
| src/ui/state_store.py:94 | `ANALYSIS_CARDS_KEY` | :92-93 `not in` → 补 `[]`。**安全** |
| src/ui/template_center_panel.py:199 | `current_file_name` | 同块 :194 前置写（`session_state["current_file_name"] = file_name`），:199 读它再赋给 `file_name`。**安全但脆**：依赖「:194 与 :199 同在 `if df is not None:` 体内不被拆开」 |
| src/upstream/tier.py:101 | `upstream_state` | :99-100 `if not isinstance(session_state.get("upstream_state"), dict): 写 {}`；且整段在 `try/except Exception` 兜底分支内。**安全** |
| src/utils/autosave.py:99 | 全键 | `{k: session_state[k] for k in list(session_state.keys())}` ＋ 外层 `try/except`。**安全** |
| src/utils/figure_collection.py:198 | `SESSION_KEY` | :194-197 `not in or not isinstance(..., FigureCollection)` → 补种。**安全** |

⇒ **口径建议（要主班裁的）**：`_defaults` 的登记纪律若只管字面写法，就漏掉这 23 个文件 87 个函数入口的别名面。别名**不是** Streamlit 专属对象——实测调用点传的都是 `st.session_state`（`renderers.py:570`、`undergrad_wizard.py:78/308/357` 等），所以安全方法仍可用；但**类型标注在撒谎**：这些形参一律标成 `session_state: dict`，而 `SessionStateProxy` 并非 dict 子类。`src/utils/concurrency.py:36` 已经用 `session_state.get(...) if hasattr(session_state, "get") else None` 做过防御——**说明有人真撞过「receiver 不是 proxy」**。

### 3.4 写侧与守卫侧登记（只登记不判定）

- 下标式**写 143 点**（字面键 **96**＋常量/动态键 **47**），删 **0**；连同属性式写 114 点，**全仓写点 257 处，用到 104 个不同字面键，其中只有 26 个在 `_defaults`**（78 个不在，含 **68 个 `_` 前缀临时键**，如 `_q_design_pending`、`_reviewer_qa`、`_lr_pending_rescore`）。
  写点 Top6（字面键）：`questionnaire_design` 15／`analysis_output` 6／`plan` 6／`app_mode` 6／`df` 6／`_q_design_pending` 6。
- 成员守卫 13 点（字面 8／动态 5），全表见附录 A 命令 1 输出。
- 安全方法调用（AST 属性访问计）：`get` **196**／`pop` **53**／`setdefault` **6**／`clear` 1／`update` 1／`keys` 1／`items` 1 ＝ **259**。
  其中**第一参是字面键**的：`get` 166／`pop` 38／`setdefault` 5（＝附录 A 命令 2 的 `safe-*` 列合计）；其余 30／15／1 处传的是变量或 `*_KEY` 常量 ⇒ **两处口径差完全可解释，不是计数漂移**。



## 四、合并总风险面表（属性式 65 ＋ 下标式 28＝14 字面＋5 动态＋9 别名）

| 面 | 点数 | A 键在 `_defaults` | B 就近守卫 | C 真裸读 | D 静态不可判（人工收口） |
|---|---|---|---|---|---|
| 属性式读（今日复算，上份 67） | **65** | **61**（键在 27 键表内） | 4（`analysis_pipeline`×2、`polished_draft`×2，函数内 `in` 就地补种） | 0 | 0 |
| 下标式读·字面键 | **14** | 1 | 13 | **0** | 0 |
| 下标式读·动态键 | **5** | — | 4 | 0 | 5（内含 1 脆点：cleaning_wizard:199） |
| 别名面下标读 | **9** | 0 | 9（其中 :199 同块前置写、tier:101 try 兜底） | 0 | 0 |
| **合计** | **93** | **62（66.7%）** | **39（41.9%）** | **0** | **5** |

> 属性式面的 61/4 由本档重算（谓词与上份同一条），不是抄上份：上份是 63/4（分母 67）。
> **A 与 B 不互斥**（app.py:2365 既在 `_defaults` 又有本键守卫），所以两列之和大于合计。

### 4.1 登记面 vs 使用面（本档最重要的一个数）

把两式读写、`.get/.pop/.setdefault`、成员测试里**被字面点名的键**去重合并：

| 量 | 读数 |
|---|---|
| 全仓被字面点名的 `session_state` 键 | **119** |
| 其中在 `_defaults` 里登记的 | **27**（＝覆盖率 **22.7%**） |
| 被字面点名但**不在** `_defaults` 的 | **93** |
| `_defaults` 里**从未被任何字面点位引用**的键 | **1**：`workspace_saved`（app.py:106） |

### 4.2 第二登记处 `src/ui/state_keys.py`：存在，但被字面量绕穿

普查中发现仓里其实**已有第二个键登记处**——`src/ui/state_keys.py`（34 行）定义 **17 个 `*_KEY` 常量**，被 7 个文件引用（`state_store.py`、`export_gate.py`、`deliverable_center_panel.py`、`method_recommender_panel.py`、`session_reset.py`、`undergrad_wizard.py`、`next_step_engine.py`）：

| 量 | 读数 |
|---|---|
| `state_keys` 常量数 | 17 |
| 与 `_defaults` 的**交集** | **5**（`df`/`meta`/`inspector`/`analysis_output`/`plan`） |
| 只在 `state_keys`、**不在** `_defaults` | **12**（`analysis_cards`、`paper_bundle`、`export_allowed`、`recipe_executed`、`review_queue_filters`… ） |
| **17 个键里「常量与字面量并用」的** | **17／17（全部）** |
| 典型比值 | `df`：常量引用 **5** 次 vs 字面量 `"df"` **89** 次；`analysis_output`：3 vs 20；`plan`：3 vs 24 |

⇒ 两个登记处**互不覆盖**（并集 39 个登记名、交集 5），且**已登记的键仍然到处被写裸字面量**——`state_keys` 是「有常量、无强制」。
⇒ 本档 3.1 的 14 个下标读点里，**没有一个是经 `state_keys` 常量读写的**（走 `state_keys` 那批键都被封装进 `state_store.py` 一类函数里了）——这正是 §五.3 建议①要把「登记」变成硬约束的原因：**已有的两条登记路都没接住 93 个未登记键**。


## 五、两种形态是否同一条纪律？——**故障面同源，承重不同源**

### 5.1 现场实测的语义差（`.venv`／streamlit 1.59.1，附录 A 命令 3 可复跑）

```
st.session_state["nope"]        -> KeyError: 'st.session_state has no key "nope". Did you forget to initialize it?'
st.session_state.nope           -> AttributeError: st.session_state has no attribute "nope". Did you forget to initialize...
st.session_state.get("nope")    -> OK None
'nope' in st.session_state      -> OK False
st.session_state.pop("nope", None) -> OK None
st.session_state.setdefault("z", 0) -> OK 0
```

实现依据（同版本）：`SessionStateProxy.__getattr__` 是 `return self[key]` 的 `except KeyError: raise AttributeError(...)` ⇒
**属性式只是下标式的一层转写，异常类被换掉、语义完全相同**；两者都**未捕即整页红**。
`SessionStateProxy` 自有 `clear/get/items/keys/pop/popitem/setdefault/to_dict/update/values` ⇒ 上份排除安全方法的口径正确。

### 5.2 结论口径（给下一道收口单）

1. **是同一条纪律**：「读一个可能不存在的键 ⇒ 整页红」。既然属性式实为下标式的转写，**统一成一条**比两条并行好——按形态分别立规会产生上份第 4 条担心的「属性式收口、下标式继续裸读」的假整洁。
2. **但收口手段必须分开**（这是本档的核心否证）：
   - 属性式面的承重是 **`_defaults` 启动补种**（61/65 点）；
   - 下标式面的承重是 **就近 `.get()`/`in` 守卫**（13/14 点，键基本不登记）。
   ⇒ 把键补进 `_defaults` **治不到**下标式面（14 点里只有 1 点受益）；反之给下标式加守卫也动不到属性式面。
3. **因此真正的统一收口点是「键必须有登记处」，而不是「禁止某种写法」**。建议三条：
   - ① 登记处二选一并写进 AGENTS/评审清单：进 `_defaults`（启动补种），或进集中登记模块（`state_store` 那一型：`KEY` 常量＋`get_/set_/append_` 函数）。**新增 `st.session_state["_xxx"] = ...` 而两处都不登记 ⇒ 视为缺项**。
   - ② 「就近 `.get()` 守卫 ＋ 紧随下标读」这一族（本档 13 点）应改成**一次 `.get()` 存进局部变量再判**（零行为变更、纯消除冗余读），比强制登记容易落地，可作为第一批机械收口。
   - ③ 别名面补**类型标注**：`session_state: MutableMapping`，不是 `dict`——实测 `isinstance(st.session_state, dict)` 为 **False**，其 MRO 是 `SessionStateProxy → MutableMapping → Mapping → Collection → Sized → Iterable → Container → object`（**不是 dict 子类**，但确为 MutableMapping），所以 `: dict` 标注是**错的且会误导调用方传普通 dict**（普通 dict 没有 Streamlit 的键↔控件同步语义）。另给 `*_df`/`*_log` 这类**成对键**加一条「成对写/成对读」断言（现状见 3.2 的 cleaning_wizard:199）。登记处本身建议收敛：**`_defaults`（27 键）∪ `state_keys.py`（17 常量，12 个不在 `_defaults`）交集只有 5**，见 §4.2。


4. **不改码**：①②③ 都需要动 `src/`，本单只读位一律不推；主班裁后可拆成「机械收口 13 点」＋「登记面合并」两张单。

## 六、结论（本档新增的五条承重）

1. **下标式面比属性式面小一个数量级，但更不登记**：字面键裸读 14 点 vs 属性式 65 点；14 点里 **13 点的键不在 `_defaults`**，全靠就近守卫活着。上份「63/67 由 `_defaults` 兜住」的结论**不可外推到本面**。
2. **两面的真裸读都是 0**（属性式 0、下标式 0），当前盘态没有「随时会炸」的点位——这是好消息，也是**假整洁的温床**：唯一的结构约束（`_defaults` 补种）只覆盖 27/119 个键。
3. **登记面覆盖率 22.7%（27/119），且登记处有两个互不覆盖**：`_defaults` 27 键 ∪ `state_keys.py` 17 常量，**交集只有 5**；`_defaults` 内还有 **1 个僵尸登记键**（`workspace_saved` 从未被字面引用），`state_keys` 的 17 个键则 **17/17 都在被裸字面量绕穿**（`df`：常量 5 次 vs 字面量 89 次）。⇒ 凡「补进 `_defaults` 就全局安全」式建议，都要先按这组数打折。

4. **脆点 2 个（都不可达但无断言锁住）**：`src/ui/cleaning_wizard.py:199`（`log_key` 由兄弟键 `df_key` 的守卫掩护，恢复白名单恰好救它）、`src/ui/template_center_panel.py:199`（同块前置写；改条件顺序即炸）。
5. **上份的 app.py 行号已整体失效**（−183），67 点表实为 65 点；差异全部归因到 `f1b4a38`（s922-102）搬走的 3 处 `st.session_state.language`。**引用上份锚点的任何后续单，行号需按本档重取。**

## 附录 A·复现命令

**命令 1（扫描面与两式总量、逐点表）**——把下面整段存成 `tmp/psy2_ss_census.py`（`tmp/` 已在 `.gitignore:29`，且 `pytest.ini` 的 norecursedirs 含 `tmp`）后 `.venv/Scripts/python.exe tmp/psy2_ss_census.py`：

```python
"""s922-136 普查器（只读）：session_state 下标式裸读面 ＋ 属性式对偶面同表复算。

放 tmp/（已 .gitignore:29 确认忽略），不进版、不被 pytest 收（pytest.ini norecursedirs 含 tmp）。
零写入：只 read_text。
"""
import ast
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(".")
FILES = [ROOT / "app.py"] + sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py"))
FILES = [p for p in FILES if p.exists()]

# 属性式安全方法（天然不抛 KeyError），沿用上份普查口径并显式列出
SAFE_METHODS = {
    "get", "pop", "setdefault", "keys", "values", "items", "clear", "update",
    "to_dict", "from_dict", "__contains__", "register_session_state_callbacks",
    "on_key_change", "on_new_state", "get_stats", "filtered_data",
}


def ssobj(n):
    """表达式是否就是 `st.session_state`（上份普查的同一条谓词）。"""
    return (isinstance(n, ast.Attribute) and n.attr == "session_state"
            and isinstance(n.value, ast.Name) and n.value.id == "st")


def rel(p):
    return p.as_posix()


def parse_all():
    out = []
    for p in FILES:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:  # pragma: no cover
            print("!! 解析失败", rel(p), e)
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        parents = {}
        for node in ast.walk(tree):
            for ch in ast.iter_child_nodes(node):
                parents[ch] = node
        out.append((p, tree, lines, parents))
    return out


ALL = parse_all()

# ── _defaults 键集（app.py:90 起的 Dict 字面量）──
DEFAULTS = {}
for p, tree, lines, parents in ALL:
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "_defaults" and isinstance(n.value, ast.Dict):
                    for k in n.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            DEFAULTS[k.value] = (rel(p), n.lineno)
print("== _defaults 注册键 ==")
print("个数", len(DEFAULTS), "定义处", sorted(set(DEFAULTS.values()))[:1])
print("键", sorted(DEFAULTS))

# ── 逐点扫描 ──
rows = []            # 读点（属性式 + 下标式）
writes = {"attr": 0, "sub": 0, "del": 0}
membership = []      # `"k" in st.session_state` 类守卫
safe_calls = {}      # st.session_state.<safe_method>(...)
alias_subs = []      # 经别名（X = st.session_state / 形参 session_state）的下标读


def key_of(slice_node):
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return slice_node.value, "literal"
    if isinstance(slice_node, ast.Name):
        return slice_node.id, "dynamic-name"
    return None, "dynamic-expr"


def guard_for(node, parents, key, lines):
    """最近守卫：祖先链上最近一层测试式里出现该键名（子串匹配，沿用前口径）。"""
    cur = parents.get(node)
    while cur is not None:
        test = None
        if isinstance(cur, ast.If):
            test = cur.test
        elif isinstance(cur, (ast.For, ast.AsyncFor)) and isinstance(cur.iter, ast.Call):
            test = None
        if test is not None:
            src = ast.unparse(test)
            if key and key in src:
                return ("if", cur.lineno, src[:110])
        cur = parents.get(cur)
    return None


def membership_hits_in_scope(node, parents):
    """同函数内、位于读点之前的 `"k" in st.session_state` / `st.session_state[k] = ...`。"""
    fn = None
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = cur
            break
        cur = parents.get(cur)
    scope = fn if fn else parents.get(node) or node
    if fn is None:  # 模块级：用整个树
        scope = None
    return scope


for p, tree, lines, parents in ALL:
    # 收集别名
    aliases = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and ssobj(n.value):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    aliases.add(t.id)
        if isinstance(n, ast.arg) and n.arg in ("session_state",):
            aliases.add(n.arg)

    for n in ast.walk(tree):
        # 属性式：st.session_state.<attr>
        if isinstance(n, ast.Attribute) and ssobj(n.value):
            if n.attr in SAFE_METHODS:
                if isinstance(n.ctx, ast.Load):
                    safe_calls[n.attr] = safe_calls.get(n.attr, 0) + 1
                continue
            if isinstance(n.ctx, ast.Load):
                rows.append(dict(file=rel(p), line=n.lineno, form="attr", key=n.attr,
                                 kind="read", src=lines[n.lineno - 1].strip()[:110]))
            elif isinstance(n.ctx, ast.Store):
                writes["attr"] += 1
            continue
        # 下标式：st.session_state[...]
        if isinstance(n, ast.Subscript) and ssobj(n.value):
            key, kclass = key_of(n.slice)
            if isinstance(n.ctx, ast.Load):
                rows.append(dict(file=rel(p), line=n.lineno, form="sub", key=key,
                                 kclass=kclass, kind="read",
                                 src=lines[n.lineno - 1].strip()[:110]))
            elif isinstance(n.ctx, ast.Store):
                writes["sub"] += 1
                k, kc = key_of(n.slice)
                rows.append(dict(file=rel(p), line=n.lineno, form="sub", key=k, kclass=kc,
                                 kind="write", src=lines[n.lineno - 1].strip()[:110]))
            elif isinstance(n.ctx, ast.Del):
                writes["del"] += 1
                rows.append(dict(file=rel(p), line=n.lineno, form="sub", key=key_of(n.slice)[0],
                                 kind="del", src=lines[n.lineno - 1].strip()[:110]))
            continue
        # 成员测试：`"k" in st.session_state`
        if isinstance(n, ast.Compare) and any(ssobj(c) for c in n.comparators):
            op = "in" if isinstance(n.ops[0], ast.In) else ("not in" if isinstance(n.ops[0], ast.NotIn) else "?")
            lk = n.left
            if isinstance(lk, ast.Constant) and isinstance(lk.value, str):
                membership.append((rel(p), n.lineno, op, lk.value))
            else:
                membership.append((rel(p), n.lineno, op, "<dyn:%s>" % ast.unparse(lk)[:40]))
        # 别名下的下标读
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in aliases:
            if isinstance(n.ctx, ast.Load):
                alias_subs.append((rel(p), n.lineno, key_of(n.slice)[0], lines[n.lineno - 1].strip()[:90]))

reads = [r for r in rows if r["kind"] == "read"]
attr_reads = [r for r in reads if r["form"] == "attr"]
sub_reads = [r for r in reads if r["form"] == "sub"]

print("\n== 两路总量 ==")
print("文件面 app.py+src+scripts 文件数:", len(FILES), " 实际解析:", len(ALL))
print("属性式读:", len(attr_reads), " 下标式读:", len(sub_reads),
      " 属性式写:", writes["attr"], " 下标式写:", writes["sub"], " del:", writes["del"])
print("成员守卫 in/not in 次数:", len(membership))
print("安全方法调用:", dict(sorted(safe_calls.items())))
print("别名系下标读(不计入主口径):", len(alias_subs))

lit = [r for r in sub_reads if r.get("kclass") == "literal"]
dyn = [r for r in sub_reads if r.get("kclass") != "literal"]
print("下标式读：字面键", len(lit), " 动态键", len(dyn))
print("下标式字面键去重:", len({r["key"] for r in lit}))
print("下标式动态键点位:", [(r["file"], r["line"], r["src"][:60]) for r in dyn])

# ── 正则路（文本实现，第三方复核用）──
rx_sub_all = re.compile(r"st\.session_state\[")
n_sub_all = 0
for p, tree, lines, parents in ALL:
    for l in lines:
        n_sub_all += len(rx_sub_all.findall(l))
rx_sub_read = re.compile(r"st\.session_state\[\s*[\"']([A-Za-z0-9_\u4e00-\u9fff\- ]+)[\"']\s*\](?!\s*=)")
n_sub_read = sum(len(rx_sub_read.findall(l)) for _, _, lines, _ in ALL for l in lines)
rx_attr = re.compile(r"st\.session_state\.[A-Za-z_][A-Za-z0-9_]*")
n_attr_all = sum(len(rx_attr.findall(l)) for _, _, lines, _ in ALL for l in lines)
print("\n== 正则路 ==")
print("st.session_state[ 总命中(含写):", n_sub_all)
print("字面键读形态(排除紧随 `] =`):", n_sub_read)
print("属性式总命中(含写):", n_attr_all)

# ── 分类：A 键在 _defaults / B 就近守卫 / C 真裸读 ──
mem_keys = {}
for f, ln, op, k in membership:
    mem_keys.setdefault(k, []).append((f, ln, op))

by_file = {}
for p, tree, lines, parents in ALL:
    by_file[rel(p)] = (tree, lines, parents)


def nearest_guard(r):
    tree, lines, parents = by_file[r["file"]]
    key = r["key"]
    if not key:
        return None
    target = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.Attribute, ast.Subscript)) and n.lineno == r["line"]:
            if (isinstance(n, ast.Subscript) and r["form"] == "sub") or \
               (isinstance(n, ast.Attribute) and r["form"] == "attr"):
                nm = key_of(n.slice)[0] if isinstance(n, ast.Subscript) else n.attr
                if nm == key:
                    target = n
                    break
    if target is None:
        return None
    return guard_for(target, parents, key, lines)


print("\n== 逐点分类（下标式字面键读）==")
cls_counts = {}
detail = []
for r in sorted(lit, key=lambda x: (x["file"], x["line"])):
    k = r["key"]
    in_def = k in DEFAULTS
    g = nearest_guard(r)
    mem = mem_keys.get(k)
    if in_def:
        c = "A 键在_defaults" + ("（有外层含键 if）" if g else "（读点无外层含键 if）")
    elif mem:
        c = "B 就近守卫(成员测试)"
    elif g:
        c = "B 就近守卫(外层 if)"
    else:
        c = "C 真裸读"
    cls_counts[c] = cls_counts.get(c, 0) + 1
    detail.append((r["file"], r["line"], k, c, (g[1] if g else (mem[0][1] if mem else "")),
                   (g[2] if g else ("`%s\"%s\" in st.session_state`" % ("", k) if mem else r["src"][:70]))))

for c in sorted(cls_counts):
    print("  %-34s %d" % (c, cls_counts[c]))
print("  合计", sum(cls_counts.values()))
print("\n== 逐点表 ==")
for f, ln, k, c, gl, gs in detail:
    print("%s:%d | %s | %s | 守卫行 %s | %s" % (f, ln, k, c, gl, gs))

print("\n== 动态键下标读（静态不可判）==")
for r in sorted(dyn, key=lambda x: (x["file"], x["line"])):
    print("%s:%d | %s | %s" % (r["file"], r["line"], r.get("kclass"), r["src"][:80]))

print("\n== 下标式写/删（对偶面，登记不判定）==")
for r in sorted([x for x in rows if x["kind"] in ("write", "del")], key=lambda x: (x["file"], x["line"])):
    print("%s:%d | %s | %s | %s" % (r["file"], r["line"], r["kind"], r.get("key"), r["src"][:70]))

print("\n== 成员守卫全表 ==")
for f, ln, op, k in sorted(membership):
    print("%s:%d | %s | %s" % (f, ln, op, k))

print("\n== 别名系下标读 ==")
for f, ln, k, s in sorted(alias_subs):
    print("%s:%d | %s | %s" % (f, ln, k, s[:70]))

print("\n== 属性式读（今日复算，供合并表用）==")
ad = {}
for r in sorted(attr_reads, key=lambda x: (x["file"], x["line"])):
    ad.setdefault(r["file"], []).append((r["line"], r["key"]))
for f in sorted(ad):
    print("%s | %s" % (f, ", ".join(":%d %s" % t for t in ad[f])))
print("属性式读合计", len(attr_reads), " 去重键", len({r['key'] for r in attr_reads}),
      " 其中键不在 _defaults 的点数",
      sum(1 for r in attr_reads if r["key"] not in DEFAULTS))
```

**命令 2（登记面 vs 使用面的键清单）**——`tmp/psy2_ss_keys.py`：

```python
"""s922-136 附表器：全仓 session_state 字面键清单（按形态分列）＋ _defaults 覆盖差。

只读，放 tmp/（.gitignore:29 已确认）。与 psy2_ss_census.py 同一谓词（`st.session_state` 直连），
别名面单列，避免把「receiver 可能不是 proxy」的点位混进主口径。
"""
import ast
import collections
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILES = [pathlib.Path("app.py")] + sorted(pathlib.Path("src").rglob("*.py")) + sorted(pathlib.Path("scripts").rglob("*.py"))
SAFE = {"get", "pop", "setdefault", "keys", "values", "items", "clear", "update", "to_dict",
        "from_dict", "register_session_state_callbacks", "on_key_change", "on_new_state",
        "get_stats", "filtered_state", "_keys"}


def ssobj(n):
    return (isinstance(n, ast.Attribute) and n.attr == "session_state"
            and isinstance(n.value, ast.Name) and n.value.id == "st")


DEFAULTS = set()
KEYS = collections.defaultdict(lambda: collections.Counter())
WHERE = collections.defaultdict(set)

for p in FILES:
    tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    for n in ast.walk(tree):
        # _defaults 键集
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "_defaults":
                    for k in n.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            DEFAULTS.add(k.value)
        # 属性式
        if isinstance(n, ast.Attribute) and ssobj(n.value):
            if n.attr in SAFE or n.attr.startswith("__"):
                continue
            form = "attr-read" if isinstance(n.ctx, ast.Load) else "attr-write"
            KEYS[n.attr][form] += 1
            WHERE[n.attr].add("%s:%d" % (p.as_posix(), n.lineno))
            continue
        # 下标式
        if isinstance(n, ast.Subscript) and ssobj(n.value):
            sl = n.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                form = {ast.Load: "sub-read", ast.Store: "sub-write", ast.Del: "sub-del"}[type(n.ctx)]
                KEYS[sl.value][form] += 1
                WHERE[sl.value].add("%s:%d" % (p.as_posix(), n.lineno))
            continue
        # 安全方法里的字面键（.get/.pop/.setdefault）与成员测试
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and ssobj(n.func.value):
            if n.func.attr in ("get", "pop", "setdefault", "update") and n.args:
                a0 = n.args[0]
                if n.func.attr == "update":
                    continue
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    KEYS[a0.value]["safe-" + n.func.attr] += 1
                    WHERE[a0.value].add("%s:%d" % (p.as_posix(), n.lineno))
            continue
        if isinstance(n, ast.Compare) and any(ssobj(c) for c in n.comparators):
            lk = n.left
            if isinstance(lk, ast.Constant) and isinstance(lk.value, str):
                KEYS[lk.value]["in-test"] += 1
                WHERE[lk.value].add("%s:%d" % (p.as_posix(), n.lineno))

COLS = ["attr-read", "attr-write", "sub-read", "sub-write", "sub-del", "safe-get", "safe-pop", "safe-setdefault", "in-test"]
print("全仓被字面点名的 session_state 键总数:", len(KEYS), " 其中在 _defaults:", len(DEFAULTS))
print("_defaults 里从未被字面点名的键:", sorted(DEFAULTS - set(KEYS)))
print("被点名但不在 _defaults 的键数:", len(set(KEYS) - DEFAULTS))
print()
hdr = "键 | 在_defaults | " + " | ".join(COLS) + " | 首现位置"
print(hdr)
tot = collections.Counter()
unreg_reads = []
for k in sorted(KEYS, key=lambda x: (-sum(KEYS[x].values()), x)):
    c = KEYS[k]
    tot.update(c)
    first = sorted(WHERE[k])[0]
    print("%s | %s | %s | %s" % (k, "Y" if k in DEFAULTS else "N",
                                 " | ".join(str(c[x]) for x in COLS), first))
    if k not in DEFAULTS and (c["attr-read"] or c["sub-read"]):
        unreg_reads.append((k, c["attr-read"], c["sub-read"], sorted(WHERE[k])[:6]))
print()
print("列合计:", dict((x, tot[x]) for x in COLS))
print()
print("== 未登记键（不在 _defaults）却被直读的属性式/下标式点位 ==")
for k, a, s, w in unreg_reads:
    print("%-28s attr-read=%d sub-read=%d  %s" % (k, a, s, ", ".join(w)))
```

**命令 3（两形态语义差，第五节读数）**

```bash
D:/code/psy-analysis/.venv/Scripts/python.exe - <<'PY'
import streamlit as st
st.session_state["seed"] = 1
for expr in ('st.session_state["nope"]', 'st.session_state.nope', 'st.session_state["seed"]',
             'st.session_state.seed', 'st.session_state.get("nope")', "'nope' in st.session_state",
             'st.session_state.pop("nope", None)', 'st.session_state.setdefault("z", 0)'):
    try: print('%-40s -> OK %r' % (expr, eval(expr)))
    except BaseException as e: print('%-40s -> %s: %s' % (expr, type(e).__name__, str(e)[:70]))
PY
```

**命令 4（正则路，第三方复核用）**

```bash
git grep -c "st\.session_state\[" -- app.py src scripts | …   # 本机无 ripgrep，用 git grep
python -c "…见附录 A 命令 1 的『正则路』段…"                    # 162 / 14 / 440 三个数
```

## 附录 B·本档**没有**覆盖的面（避免被当成全量）

1. `st.session_state` **经 widget `key=` 参数**的隐式读写（`st.text_input(key="_reviewer_a_1")`、`st.selectbox(..., key="app_mode")` 一类）——app.py＋src＋scripts 里 **`key=` 实参出现 757 次**（含同名非 Streamlit 调用，未逐点甄别），它由 Streamlit 自己往 session_state 注册键、**不经下标/属性写法**，因此**不在本档 93 点内**。
   ⚠️ 这是本面**唯一未开垦的大块**：`app_mode`（写 6 点，见 §3.4 Top6）**不在 `_defaults` 的 27 键里**，它靠 widget `key=` 注册 ⇒ 说明「_defaults 覆盖属性式面」这句话还有第二个例外源。**下一单若要收口，必须先把这一面并进来看**，否则 93/119 两个分母都会漂移。

2. `**st.session_state`、`st.session_state.to_dict()`、`for k in st.session_state`（迭代形态）未逐点判定。
3. `tests/` 与 `archive/` 不在扫描面（与上份一致）。
4. Streamlit 组件级 API（`st.query_params`、`st.experimental_...`）不在面内。

