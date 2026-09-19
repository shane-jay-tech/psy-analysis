# psy df in-place 审计盲区扩展（s919-10，只读审计，零代码改动）

- 执行：2026-09-19 18:2x–19:2x（班次 `qoder-rev-20260919-1020`）。
- 上游：`zcode-bridge/outbox/s918-09-psy-df-inplace-audit.result.md:46` 原文
  「`ss = st.session_state` 后再 `ss.df[...] = …` 的形态两版脚本都抓不到」＋「只审了 df 一个键；
  inspector／analysis_results 等可变对象是否也有同类约束，本单未查」。
- **一句话结论**：两个担心都成立，而且比预想的实在——
  ① `X = st.session_state` 整体别名**实测 15 处**（本单初稿报的「0 处」是假数，见第三节）；
  ② 不只 df：按快照键清单复扫，**4 个键上存在真实就地写，严格可证 13 处 ＋ 数据流外 28 处**；
  df／inspector／analysis_output／plan 反倒干净（与 s918-09 一致）。
- ⚠ 本文件是**改写版**：初稿把 `design["llm_used"] = True` 列为命中、把整体别名记为 0，两条都已推翻，
  假数原样留在第二、三节里，免得下一班再信一次。

## 一、为什么约束不止 df（这条决定了要不要管）

```python
src/utils/autosave.py:90  def _capture_refs(session_state):
    """主线程引用级捕获全部键值（零序列化、零深拷贝）。
    大对象（df 等）按 Streamlit 惯例「整体替换、不就地改」；      # :91 ← 约束的原句，"df 等"没写清边界
    """
    return {k: session_state[k] for k in list(session_state.keys())}      # :96 ← **所有键**
```
捕获的是**每一个键的引用**，不是只有 df。快照配方 `src/utils/workspace.py:226 build_workspace_snapshot()`
（函数体 `:226-391`）实际读取的 session_state 键：**23 个具名键 ＋ 1 个前缀族**：

- `for k in [...]` 三行（`:238`、`:267`、`:299`）：`meta`、`inspector`、`file_name`、`analysis_history`、
  `undergrad_mode`、`undergrad_path`、`undergrad_step`、`app_mode`、`quick_model_id`（9 个）
- 直接 `get()`：`df`(:231)、`plan`(:244)、`analysis_output`(:250)、`undergrad_wizard_data`(:256)、
  `questionnaire_design`(:273)、`experiment_engine`(:277)、`paper_engine`(:290)、
  `defense_qa_mastered`(:314)、`download_history`(:319)（9 个）
- 常量键：`figure_collection`(`SESSION_KEY`, :307)、`upstream_state`(`UPSTREAM_SESSION_KEY`, :339)、
  `literature_review_state`(`LITERATURE_REVIEW_SESSION_KEY`, :370)、`workspace_state_v35`(`WORKSPACE_KEY`, :385)（4 个）
- 前缀族：`:326 if key.startswith("_tutor_history_")` ⇒ **所有 AI 助教对话历史**

⇒ **KNOWN_ISSUES 那条"UI 线程禁止就地变更 df"写窄了**：约束对象是"被快照的所有键"，df 只是最大最显眼的一个。

## 二、命中清单（键都在上面那份清单里，快照侧全是原样引用或浅拷贝）

### 严格可证：4 键 13 处

| # | 键 | 写入位置 | 形态 | 别名绑定行 |
|---|---|---|---|---|
| 1 | `undergrad_wizard_data` | `src/ui/undergrad_wizard.py:1941`、`:1942` | **两级嵌套下标写** `wiz_data["wizard_results_context"]["test_type"] = …`（紧接 `st.rerun()` :1944） | `:1939 wiz_data = st.session_state.undergrad_wizard_data`（作用域 `render_assumption_failure_guidance`，def :1824） |
| 2 | `undergrad_wizard_data` | `src/ui/onboarding.py:216`、`:217`、`:218`、`:239`、`:240` | `wiz_data["df"]=…`／`["inspector"]=…`／`["wizard_results_context"]={…}`／`["plan"]=…`／`["analysis_output"]=…` | `:215 wiz_data = st.session_state.setdefault("undergrad_wizard_data", {})` ← **`setdefault` 返回活对象**，两版旧正则都不吃这个式子 |
| 3 | `undergrad_wizard_data` | `src/utils/memory_manager.py:128` | `wiz.pop(wk, None)` —— 就地**删键**（内存回收路径） | `:123 wiz = st.session_state.get("undergrad_wizard_data")` |
| 4 | `defense_qa_mastered` | `src/ui/undergrad_wizard.py:1331`、`:1333` | `mastered_map[item.question_id] = …` | `:1307 mastered_map = st.session_state.setdefault("defense_qa_mastered", {})` |
| 5 | `download_history` | `src/ui/undergrad_wizard.py:870` | `history.append({...})` | `:869 history = st.session_state.setdefault("download_history", [])` |
| 6 | `analysis_history` | `app.py:1320`、`src/ui/quick_entries.py:705` | **不需要别名**：`st.session_state.analysis_history.append(history_entry)` | —（直接方法写） |

快照侧为什么都算数：`workspace.py:256-265` 造 `clean_wd` 时 `clean_wd[wk] = wv`（:262）是**浅拷贝**（内层 dict 仍共享引用）；
`defense_qa_mastered`(:316)、`download_history`(:321)、`analysis_history`(:241) 三处是 `ws[k] = v` 式**原样引用、连浅拷贝都没有**。

### 数据流外、但同一对象：`render_undergrad_wizard()` 里另有 28 处

`src/ui/undergrad_wizard.py:1948 wiz = st.session_state` → `:2049 wiz_data = wiz.undergrad_wizard_data` ⇒ 从 :2155 起
一大片 `wiz_data["title"] = st.text_input(...)` 式写入。静态规则在 `:2301 wiz_data = ret["data"]` 处把别名注销，
只数到 :2155–2193 的 6 处；但紧接着 `:2313 wiz.undergrad_wizard_data = wiz_data` 又把它发布回 session_state，
`:2695`、`:2884`、`:3022`、`:3479-3480`、`:3615-3688`（含 `:3628`、`:3688` 两处两级嵌套）合计 28 处**同样落在活对象上**。
⇒ **这个 1770 行的函数整体就是"就地写向导数据"的形态**，只是要靠数据流才能证明；拆函数不是本单该做的事，只登记。

### 已被推翻的假阳性：`design["llm_used"] = True`（初稿的第 3 类命中）

初稿把 `app.py:1932` 与 `src/ui/questionnaire_panel.py:213` 报成命中，理由是同文件另有
`design = st.session_state.questionnaire_design`（`app.py:2113`、`questionnaire_panel.py:394`）。逐行读码后**不成立**：

```python
src/ui/questionnaire_panel.py:212  design = future.result()      # 线程池返回值，不是 session_state
                               :213  design["llm_used"] = True   # 改的是还没发布的局部 dict
                               :214  st.session_state.questionnaire_design = design   # ← 这之后才是快照对象
```
`app.py:1931-1933` 与 `:2020-2021`、`:2026-2027`、`:2106-2107` 同构，`:2006-2007` 的 `legacy_design` 同理。
真正的别名点（`app.py:2113`、`questionnaire_panel.py:394`、`app.py:726` 的 `.get()` 形）之后只有读
（`design.get(...)`、`design["items"]` 取用），**零左值写** ⇒ **`questionnaire_design` 键干净**。
教训：**同作用域还不够，要看"发布顺序"**——先建新对象、写完再 `session_state.k = X`，与别名后就地改是两回事。

### 存在就地写、但键不在快照清单（因此不算违反）

- `src/ui/method_recommender_panel.py:134`（`:186` 同族）`history.append({...})`，键是 `method_recommendation_history`
  （`:55 _HISTORY_KEY`）——快照不读它 ⇒ 无危害。附：该处别名走 DI 形 `session_state.get(...)`，`:135` 又立刻整体回写，
  属"就地写＋马上发布"的半安全写法。
- `src/ui/paper_writing_ui.py:653→:670 mastered_map[...] = ...`，键是 `paper_defense_qa_mastered`
  （**与快照读的 `defense_qa_mastered` 同名不同键**）⇒ 不算命中。这个区分只能靠读键名，正则一律给不出。

## 三、盲区 A 的实际形态（并纠正本单初稿的「0 命中」）

初稿写「`ss = st.session_state` 一条都没有」——**错，且不可复现**：第七节那条式子实跑 **159 行**（宽口径，含
`.get()`／`.pop()`／派生值），把式子收紧到"行尾即止"得到 **15 处**。0 只能是跑错了式子或目录。三个口径的实数：

```
扫描 248 个生产 .py（排除 .venv/tests/scripts/archive/tmp/node_modules）
^\s*\w+ = st\.session_state\b                       → 159 行（宽口径：混入 .get()/.pop()/派生值，只能当召回上限）
^\s*(\w+)\s*=\s*st\.session_state\s*(?:#.*)?$       →  15 处  ← **整体别名，本节的正题**
^\s*(\w+)\s*=\s*st\.session_state\.(key)$           →  22 处 / 12 键  ← 纯键值别名（s918-09 用的就是这个口径）
含 or{}/.get()/.setdefault() 的别名                → 120 处 / 61 键
```
15 处整体别名的构成：
- **14 处是依赖注入默认值**：`def f(session_state=None): ... session_state = st.session_state`
  —— 5 个 `src/ui/*_panel.py` 渲染入口（`deliverable_center:35`、`evidence_table:40`、`method_recommender:61`、
  `questionnaire_import:30`、`template_center:28`）、`workspace.py:73/99/765/794/834`、`workspace_state.py:236`、
  `upstream/tier.py:74`、`concurrency.py:33/58`。这些后续只做 `session_state.get(...)` ⇒ **本单内无害**，
  但同一条键在别的调用方手里可以被就地改（`method_recommender_panel.py:134` 就是这么写的）⇒ 必须进扫描口径。
- **1 处是真的整体改名**：`src/ui/undergrad_wizard.py:1948 wiz = st.session_state`，即第二节"数据流外 28 处"的源头。
  它名下的写分两种，**这是本次审计最容易误报的地方**（v2/v3 都栽过）：
  `wiz.undergrad_step = 2`、`wiz.df = demo_df` 是**键级整体赋值**（本文件属性式 96 处 ＋ 下标式 7 处），
  与 `st.session_state.x = …` 同义 ⇒ 不违反约束，但 **v1 类正则对这 103 处完全失明**；
  只有 `wiz_data = wiz.undergrad_wizard_data`(:2049) 之后的下标写才违反。

键值别名的两个口径为什么必须都报：

| 口径 | 处数 | 后果 |
|---|---:|---|
| 纯键式（行尾锚定） | 22 处 / 12 键 | s918-09 记的 `df` 4 处（`app.py:1061/1295/1369`、`onboarding.py:206`）与本口径**逐字一致** ⇒ 两轮独立扫描同口径收敛，`df` 结论可信 |
| 含 `or {}`／`.get()`／`.setdefault()` | 120 处 / 61 键 | 第二节命中的 3 个键（`undergrad_wizard_data`、`defense_qa_mastered`、`download_history`）**只出现在这个口径里** |

⇒ **口径二不是"噪声多"，而是"真实命中的唯一来源"**：初稿只报口径一，正好把 5/6 类命中筛掉了。
`.setdefault()` 尤其阴——它返回的就是 session_state 里的活对象，而代码读起来像"安全取值"。

## 四、扫描方法（五版，前四版都给过假数）

1. **v1（旧脚本口径，s918-09）**：只匹配 `st.session_state[...] =` / `st.session_state.x =` ⇒ 任何别名形态都抓不到。
2. **v2**：全文件把"别名变量名"与"就地写模式"配对 ⇒ 35 处，**含跨函数同名假阳性**
   （`questionnaire_panel.py` 别名在 :394、命中却在 :213，早于别名）。且括号类只吃一层，`wiz_data["a"]["b"] =` 反而漏——
   一个计数既虚高又漏项。
3. **v3（本单初稿）**：按 `def/class` 切作用域 ⇒ 报「整体别名 0 处」＋ 3 类命中，**两条都错**：
   0 是不可复现的假数；`design["llm_used"]` 是同作用域但非别名的假阳性。
4. **v4**：作用域 ＋ 顺序重绑定（`X = ...` 注销旧别名）＋ 绑定式扩到 `.get()`/`.setdefault()`/`session_state[...]`
   ＋ "先建新对象再发布"判为局部新建 ⇒ 得到第二节 13 处严格命中。
   残留缺陷：**不会在 `wiz.undergrad_wizard_data = wiz_data` 这类"重新发布"处恢复别名**（少报 28 处）。
5. **v5（本文件采用）**：v4 结果**逐条读码**，每条回到磁盘贴出「绑定行 → 写入行 → 快照行」三段证据 ⇒
   命中／假阳性／键不在快照 三类分开计。这类静态扫描只有这一种可用姿势：**数字落不了三段证据就当没算出来**。
- **未覆盖面（如实）**：① 属性式就地写（`wsv.field = ...`、`coll.items.append(...)`，尤其 `WorkspaceState`、
  `FigureCollection` 两个快照对象）；② 对象跨函数传递后被改；③ 锁／线程池回调里的写。都不在 v4 正则里。

## 五、严重度与触发窗口（如实：窄，但不是零）

- 需要同时满足：① 后台保存**在途**（`autosave.py:128 atexit.register(flush_background, 5.0)` ＋ 提交后到 worker 序列化之间的窗口）；
  ② 主线程在该窗口内对上述键做**就地**改写。
- 不像 df 那样"每次都赌"（df 最大、序列化最慢、窗口最长），命中的 4 个键窗口更短；
  但**危害类型完全相同**：存下来的工作区可能是"改到一半"的状态，且不会报错（引用快照语义）。
- 最扎眼的不是概率而是**语义**：`onboarding.py:216` 把「`df`／`inspector` 这些快照键的引用」**塞进 `undergrad_wizard_data`
  的内层 dict**，`undergrad_wizard.py:2695 wiz_data["df"] = cleaned_df` 同理。快照侧 `workspace.py:260-264` 对 DataFrame
  走 `hasattr(wv,"to_dict")` 分支 ⇒ 存成 `{"__type__":"dataframe","data": to_dict(orient="records")}`，
  于是**同一张表在一份工作区里被写两遍**（顶层 `df_b64` 一份、向导内层 records 一份，两份可以各自漂移）。
  这跟 KNOWN_ISSUES 防的是同一件事，只是绕了一层——而且这条不是"竞态才发作"，**每次保存都真的多写一份**。
- 我没有构造实际竞态复现（要起真后台线程＋时序控制，属实验性改动，本单是只读审计）。

## 六、建议（一条都没执行）

1. **先改规范文本**：把 `KNOWN_ISSUES.md` 那条「UI 线程禁止就地变更 df」的适用范围写成
   「禁止就地变更**任何被 `build_workspace_snapshot()` 读取的 session_state 键**（清单以 workspace 为准，
   别在本文抄一份——抄了就会漂）」。同一句话在 `src/utils/autosave.py:91` 的 docstring 里还有一份
   （"大对象（df 等）"），两处要一起收口，否则又是双源漂移。
2. **严格 13 处里优先 4 处**（都是行为等价改写，但**属生产码改动，需日间批**，本单一行没动）：
   ① `undergrad_wizard.py:1941-1942` 嵌套写 ⇒ 先 `dict(wiz_data["wizard_results_context"])` 改好再整体塞回；
   ② `memory_manager.py:128 wiz.pop(...)` ⇒ 先复制再回收（这条最该看，它在内存压力下随时触发）；
   ③ `undergrad_wizard.py:870` append ⇒ 整体回写（同函数 `:877` 已经是正确写法，照它改即可）；
   ④ `onboarding.py:215-240` ⇒ 一次构造完整 dict 再 `st.session_state.undergrad_wizard_data = {...}`。
3. **防静态漂**：把 v4 规则做成一条 `tests/audit_*` 检查（与 `audit_test_isolation_scan.py` 同构：先报告、不进断言）。
   口径必须含：`.get()`／`.setdefault()`／整体别名 DI 形／嵌套左值／顺序重绑定；键清单从 `build_workspace_snapshot()` 读，不抄。
   `workspace.py:256-265` 的 `clean_wd` 改深拷贝是另一条路，但每次保存加 CPU/内存，要测过量。

## 七、零改动自证与回归

- 本文件是**唯一新增**；`src/`、`app.py`、`tests/` 一字未动 ⇒ 无回归面。
  `.venv` 口径全量复跑（收口时实测）：**2996 passed / 60 skipped / 0 failed（3m50s）**——与本会话开工基线**逐字相同**。
- **口径提醒（本单现场踩到）**：判回归必须用 `.venv/Scripts/python.exe -m pytest`（`docs/TESTING.md:29`）。
  本单收口时先用**系统 python** 复跑，得 **3007 passed / 25 failed / 13 errors**——与 `TESTING.md:37` 记过的那次
  "系统解释器假失败"数字完全一样；逐条落地看是 `factor_analyzer 0.5.1` 撞上系统侧 `scikit-learn 1.9.1`
  （`check_array() got an unexpected keyword argument 'force_all_finite'`，该参数 1.6 起改名 `ensure_all_finite`）
  ＋ Playwright/e2e 依赖缺失。**全是环境口径差、与本单无关**（`.venv` 侧 sklearn 1.5.2、numpy 2.5.1、streamlit 1.59.1；
  系统侧 sklearn 1.9.1、numpy 2.3.5、streamlit 1.58.0）。
  ⚠ 两个口径的 passed 数也会不同（3007 vs 2996）——**别拿汇总数当回归依据，只看 failed/skipped 与解释器名**。
- 复跑（口径即第四节 v4/v5；命中类每条都要落地读码）：
```bash
cd /d/code/psy-analysis
# ① 整体别名 15 处（宽式 ^\s*\w+ = st\.session_state\b 给 159 行，只能当召回上限）
python - <<'PY'
import re,glob,io
for f in [x for x in glob.glob('**/*.py',recursive=True)
          if not x.startswith(('.venv','tests','scripts','archive','tmp','node_modules','.git'))]:
    for i,l in enumerate(io.open(f,encoding='utf-8',errors='replace'),1):
        if re.match(r'^\s*(\w+)\s*=\s*st\.session_state\s*(?:#.*)?$', l): print(f"{f}:{i} {l.strip()}")
PY
# ② 快照键清单（23 键 ＋ 前缀族）与引用/浅拷贝位置
grep -n "session_state\[k\] for k" src/utils/autosave.py            # :96 全键引用捕获
awk 'NR>=226 && NR<=391' src/utils/workspace.py | grep -n 'session_state\.get\|for k in \[\|startswith'
# ③ 严格 13 处逐条（绑定行 → 写入行）
grep -n 'wiz_data = st.session_state.undergrad_wizard_data\|wiz_data\["wizard_results_context"\]\[' src/ui/undergrad_wizard.py
grep -n 'setdefault("undergrad_wizard_data"\|wiz_data\[' src/ui/onboarding.py
grep -n 'session_state.get("undergrad_wizard_data")\|wiz.pop(wk, None)' src/utils/memory_manager.py
grep -n 'setdefault("defense_qa_mastered"\|mastered_map\[item.question_id\]' src/ui/undergrad_wizard.py
grep -n 'setdefault("download_history"\|history.append' src/ui/undergrad_wizard.py | head
grep -rn 'st\.session_state\.analysis_history\.append' src/ app.py
```
