# psy `session_state` 去重键 AST 级复算：26 vs 30 口径归一（s924-21 · 只读）

- 班：`qoder-executor-20260925-0450-psy41`（波次 11 补派）· 2026-09-25 · cwd `D:\code\psy-analysis`
- 前手锚：`zcode-bridge/done/s923-14.result.md:51`（登记本口径差为"属另单"——即本单）
- 性质：**只读出稿**。探针落 gitignored `tmp/`，`src/`、`ui/`、`tests/`、`app.py` 一字未动；零库接触（本单不涉 `data/literature_feed`）。

## 0. 结论速览

1. **口径差完全归一，且两枚伪键被点名剔除**。片 5（`with st.sidebar:` 引导块）真键 = **28**；旧读数 **26＝24 真＋2 伪（`get`/`pop`）**、**30＝28 真＋2 伪**。本班在现盘用两档正则复现：窄档（下标字面量∪裸属性）恰读出 **26**，宽档（再加 `.get/.pop/.setdefault` 字面量）恰读出 **30**——s923-14 记录的 4 键差项在 AST 轨全部确认真实存在。
2. **全仓真实直访键数 N = 164**（app.py＋`src/**/*.py` 共 249 份，AST 轨，剔除伪键；719 处访问、71 处动态键位无法静态归名，另列）。
3. 对拍：`state_keys.py` 17 常量中 14 个在本 scope 有直访、3 个仅作 `session_reset.py` 台账成员；`_defaults` 27 键中 26 个有直访、`workspace_saved` 播种后全仓无静态读侧；164 键中 122 个既不在 `_defaults` 也不在 `state_keys`（面板私有键为主，下划线前缀共 89 个）。
4. 附带否证一卷宗小锚：`state_keys.py:9` 实为 `DATA_META_KEY`——`DATA_FRAME_KEY = "df"` 在盘 **`:8`**，1 行笔误级漂移。

## 1. 锚点复核

| 卷宗锚 | 实测 | 判定 |
|---|---|---|
| `done/s923-14.result.md`「去重键 26 vs 30 的口径差未归一…真要数准需 AST 级取值」 | :51 逐字在 | 成立 |
| `src/ui/state_keys.py:9` `DATA_FRAME_KEY = "df"` | 盘态 :8 命中，:9＝`DATA_META_KEY = "meta"` | **1 行漂（按实况修正）** |
| 片 5 区间 `app.py:196-663`（468 行／65 处，s922-23→s923-14 两度复算一致） | AST `With(st.sidebar)` 节点实界 **:199-662（464 行）**；字面窗 196-663 与 AST 窗 `st.session_state` 计数均 **65 处**、宽档键表均 **30**——块内容自 9/23 起未漂（app.py 在途 diff hunks 全部止于 :155 前区） | 成立（窗尾 3 行为注释/空行，计数不变） |

## 2. 方法（探针：`tmp/qoder-executor-20260925-0450-psy41/probe_session_state.py`）

**AST 轨**（主口径）：逐份 `ast.parse`（249 文件，0 SyntaxError 跳过），识别四形：

- `Subscript`：链根 ∈ {`st.session_state`, `session_state`}（后者为 9 处在册局部别名 `session_state = st.session_state`，右值已逐一验证全是真 SessionState；`src/utils/workspace.py` 等函数参数默认 `None` 形不构成假键）；切片解析＝字面 str ∪ **常量回溯**（本文件模块级 str 常量 ∪ `from …state_keys import X [as Y]` 值表）。
- `Call`：`.get/.pop/.setdefault(字面量|可解析常量)`、`.update(Dict字面)`、`.delete(key=…)`。
- `Attribute`：`st.session_state.<name>` / `session_state.<name>` 裸属性直读直写；**方法名单（get/pop/keys/update/delete/from_state…）白名单剔除**——伪键就生在这里的正则对应物上。
- 解析不了者不猜、不并：落**动态键清单**（71 处，见 §6）。

**正则轨**（复现旧口径）：

- 窄档 `V2 = session_state["k'] 下标字面量 ∪ st.session_state.<bare>`（**不含** `.get(` 字面量子句）
- 宽档 `V3 = V2 ∪ .get/.pop/.setdefault("k") 子句` ＝ s923-14 幸存探针 `tmp/s923-14/remeasure2.py:29-33` 的原式两分支并集（该文件 9/23 盘态留存在 gitignored tmp，本班逐字复用其正则）。

双轨对数：片 5 上 V2=26、V3=30、AST=28；V2∩伪＝V3∩伪＝`{get, pop}`；**AST ⊂ V3 且 AST＝V3 − {get,pop}**。差额全数归因（§4），无悬项。

## 3. 真实键数 N（卷宗 scope：app.py＋src）

- **N_direct = 164**（AST 轨去重；719 处访问）。分布：app-only 45／src-only 153／app∩src 34；下划线前缀私有键 89。
- 164 键全集（按字母序，★＝片 5 内的 28 键）：见 §7 复算输出（探针 `K` 行）；完整清单过长不入正文，收班前快照随 `tmp/…/census_out.txt` 在盘。

## 4. 26 vs 30 vs 28：逐键进出归因表（判据①，片 5 口径）

| 键 | 26（s922-23 窄档） | 30（s923-14 宽档） | AST 真值 | 进出原因 |
|---|---|---|---|---|
| `get` | ✗在 | ✗在 | **✗（伪键）** | 裸属性分支把方法名 `session_state.get(` 的 `get` 当键；`pop` 同理 |
| `pop` | ✗在 | ✗在 | **✗（伪键）** | 同上 |
| `_autosave_last_error` | ✗缺 | ✓ | ✓（真） | 访问形 `st.session_state.get("_autosave_last_error")`（:325）；窄档无 `.get(` 字面量子句 ⇒ 漏 |
| `_pending_app_mode` | ✗缺 | ✓ | ✓（真） | `st.session_state.pop("_pending_app_mode", None)`（:288）；同上漏因 |
| `_workspace_migration_info` | ✗缺 | ✓ | ✓（真） | `st.session_state.get(…)`（:402）＋`pop`（:407）；同上 |
| `questionnaire_design` | ✗缺 | ✓ | ✓（真） | 片 5 内经 `st.session_state.get("questionnaire_design")`（:543）；同上（裸属性读法 :1639 在片外） |
| 其余 24 键（`app_mode`、`df`、`undergrad_*`… 见 §7） | ✓ | ✓ | ✓ | 三轨一致 |

⇒ **两旧读数都不等于真值**：26＝24 真＋2 伪（漏 4 得 2 伪，碰巧近真）；30＝28 真＋2 伪。**片 5 真值 28**。s923-14 预告的「差 4 且都含 get/pop 伪键」与本班复算逐位相合（差项集合、伪键集合均一致）——口径差归一，无遗留分歧。

N（164）对 28 的扩展侧无"键漏进"问题：片 5 之外新增的 136 键全部来自 scope 扩面（app.py 其余段＋src 246 份），逐键位置在探针输出内可按文件归名。

## 5. 与 `state_keys.py`／`_defaults` 对拍

- `state_keys.py`：17 常量（盘态 :8-:34）。**14/17 在 N_direct 中**；3 个值（`paper_revised_bundle`、`review_queue_filters`、`review_queue_last_action`）在 app+src scope **零直访**，唯一消费点是 `src/ui/session_reset.py:23-49` 的 `RESEARCH_SESSION_KEYS` 台账成员（清理名册，非读写）——常量表"登记了但运行期没人碰"的 3 键，属可巡检项，不构成缺陷。
- `_defaults`（app.py 盘态 :90-116，**27 键**）：26 键有静态直访；`workspace_saved` 仅有播种（:116-118 动态循环写）＋全仓 0 静态读侧 ⇒ 死键候选（与 `doi_prefix` 同形态，登记不处置）。
- 反向：164 中 122 键两面表都不在——面板私有键（`_lr_*`、`_exp_*`、`_items_*` 等 89 个下划线族）＋业务公开键（`uploaded_df`、`app_mode`、`language`…）。**统一常量表只覆盖 14/164 ≈ 8.5%**，「避免 key 拼写不一致」的建档初衷实际未铺开（观察，不属本单处置面）。

## 6. 残差（动态键 71 处，静态不可归名，不虚计入 N）

形态分布：subscript-Store 32／call.get 21／call.pop 11／subscript-Load 6／setdefault 1。典型族：

- 运行期键族（f-string）：`_tutor_pending_q_{location}`、`coll_sel_{figure_id}`、`_branch_view_open_{bid}`、`_branch_delete_confirm_{bid}`（undergrad_wizard/upstream_panel）。
- 变量中转（值可跨文件归名，本文件不可）：`SESSION_KEY="figure_collection"`、`WORKSPACE_KEY="workspace"`、`_STORE_KEY="evidence_store"` 等——**这些键值已在他处直访入 164，无少账**；纯循环变量（`user_prefs.py:116 session_state[key] = prefs[key]`、`workspace.py:610` 恢复循环）属整表回放形态，键集＝配置面并集。
- 播种/清理回路：app.py:118（`_defaults` 循环）、session_reset 循环 pop。
- 逐处行号：探针输出 `D ` 行全量在盘（§7 命令可复算）。

## 7. 复算命令（判据②：脚本路径＋一条 python 调用）

```
# 主轨（AST census＋旧正则复现＋对拍，只读，输出 253 行）
$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0450-psy41/probe_session_state.py
  FILES_SCANNED 249 / AST_DISTINCT_KEYS 164 / AST_OCCURRENCES 719 / DYNAMIC 71
  SLICE5_AST_RANGE 199 662 464 LINES / OLDRE_ON_AST_RANGE hits=65 keys=30 / AST_ON_AST_RANGE keys=28
  OLDRE_ON_LITERAL_196_663 hits=65 keys=30 / DEFAULTS_AT 90 N=27 / STATE_KEYS_CONSTS 17 / SET_DIRECT 164 / PSEUDO_like []
# 窄档复现 26（两行验证）
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import re;from pathlib import Path;seg='\n'.join(Path('app.py').read_text('utf-8').splitlines()[195:663]);V1=set(re.findall(r'''st\.session_state\[\s*[\"']([^\"']+)[\"']''',seg));V2=sorted(V1|set(re.findall(r'st\.session_state\.([A-Za-z_]\w*)',seg)));print(len(V2),sorted(V2))"
  → 26（含 get/pop，不含 §4 四真键）；V1 单独=9（旧"下标-only"形态，供参考）
# 盘态自证
$ git status --porcelain        # 收工＝6 项在册他班在途＋本班两档＋兄弟班 psy42 的 ?? tests/test_app_page_branch_pins.py（s924-20，04:50 claims 在册，本班未碰）
$ wc -l app.py                  # 04:58 现读 2405（与 s923-14 的 9/23 现值巧合同数；他班在途 M，非不变量，R0 在册警告仍有效）
```

## 8. 自证与边界

- 本班只动 `docs/insights/` 新档＋gitignored `tmp/qoder-executor-20260925-0450-psy41/`（`git check-ignore` 命中 `.gitignore:29`）；`app.py` 全程只读（含 `git diff` 读法核实在途 hunks 不落片 5）。
- 🔴 **否证派单横幅一条**："同仓无兄弟班（psy37–40 均已交卷入库）"与实况不符——`claims.log:5140` 载 `qoder-executor-20260925-0450-psy42` 于 04:50 领 `s924-20`（psy 测试位，新建 `tests/test_app_page_branch_pins.py`），本班收工时该件已以 `??` 现身 porcelain。按 §十二"先对班名再定性"：属兄弟班正常作业，本班零接触、未据此改任何判据。
- 无库访问：本单零触 `data/`（literature_feed 不变量自证见同班 `s924-19.result.md` 证据节，181 件／21,059,126 B 逐位不变）。
- 解释器：`.venv/Scripts/python.exe`（sklearn 1.5.2 口径），全程 `PYTHONIOENCODING=utf-8`；取 rc 未接管道（`>file 2>&1; echo $?` 形态，§十三.4）。
