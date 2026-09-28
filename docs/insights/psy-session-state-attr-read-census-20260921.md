# psy session_state 属性式读取普查（s922-04，2026-09-21）

> 只读普查材料。来源：`zcode-bridge/outbox/s921-01-psy-paperui-twofix.result.md` 遗留 1
> 「建议单开一单普查 `st.session_state.<key>` 属性式读取点并逐个判『可选键/必置键』」。
> 本档不改 `src/`、不改 `app.py`、不改任何统计数值。

## 口径

- **属性式** = `st.session_state.<ident>`（AST 里 `Attribute(value=<st.session_state>)`）；
  下标式 `st.session_state["k"]`、以及 `.get/.pop/.setdefault/.update/.keys/...` 方法调用**不计入读取风险面**（它们天然不抛 KeyError）。
- 扫描面：`app.py` + `src/**/*.py` + `scripts/**/*.py`，共 257 个文件（`archive/`、`tmp/`、`node_modules/` 不在内）。
- **两条独立计数路**（结果不一致处见「复现与漂移」）：AST 路（含 ctx 判读写）与逐行正则路（按 `= ` 后缀排除赋值）。
- 行号一律取**工作树版**（`app.py` 带他人在途 ` M`，净 -28 行）：凡 ≥384 行的 app.py 锚点，HEAD 版行号 = 本档行号 + 28。

## 总量

| 位置 | 键 | 判定 | 依据（最近一层含键的外层判定） |
|---|---|---|---|
| app.py:455 | `undergrad_mode` | 必置·_defaults＋本键守卫 | if "undergrad_mode_toggle" not in st.session_state: |
| app.py:462 | `undergrad_mode` | 必置·_defaults（读点无外层守卫） | if undergrad_mode != st.session_state.undergrad_mode: |
| app.py:470 | `undergrad_mode` | 必置·_defaults（读点无外层守卫） | if not st.session_state.undergrad_mode: |
| app.py:682 | `onboarding_completed` | 必置·_defaults（读点无外层守卫） | with st.expander("💡 帮助 · 入门", expanded=not st.session_state.onboarding_completed): |
| app.py:721 | `_wizard_return` | 必置·_defaults＋本键守卫 | if st.session_state.get("_wizard_return") is not None: |
| app.py:802 | `env_status` | 必置·_defaults（读点无外层守卫） | if st.session_state.env_status: |
| app.py:803 | `env_status` | 必置·_defaults＋本键守卫 | if st.session_state.env_status: |
| app.py:850 | `undergrad_mode` | 必置·_defaults（读点无外层守卫） | if st.session_state.undergrad_mode: |
| app.py:950 | `df` | 必置·_defaults（无键守卫） | if mode == "📈 数据分析": |
| app.py:1024 | `df` | 必置·_defaults（无键守卫） | if mode == "📈 数据分析": |
| app.py:1060 | `df` | 必置·_defaults（无键守卫） | if mode == "📈 数据分析": |
| app.py:1061 | `df` | 必置·_defaults＋本键守卫 | if st.session_state.df is not None: |
| app.py:1062 | `meta` | 必置·_defaults＋他键守卫 | if st.session_state.df is not None: |
| app.py:1063 | `inspector` | 必置·_defaults＋他键守卫 | if st.session_state.df is not None: |
| app.py:1070 | `file_name` | 必置·_defaults＋他键守卫 | if st.session_state.df is not None: |
| app.py:1119 | `interactive_charts` | 必置·_defaults＋他键守卫 | if st.session_state.df is not None: |
| app.py:1124 | `interactive_charts` | 必置·_defaults＋他键守卫 | if st.session_state.df is not None: |
| app.py:1141 | `df` | 必置·_defaults（无键守卫） | if mode == "📈 数据分析": |
| app.py:1173 | `df` | 必置·_defaults（无键守卫） | if helper_q1 in recommendations: |
| app.py:1173 | `inspector` | 必置·_defaults（无键守卫） | if helper_q1 in recommendations: |
| app.py:1174 | `inspector` | 必置·_defaults＋本键守卫 | if st.session_state.df is not None and st.session_state.inspector is not None: |
| app.py:1233 | `df` | 必置·_defaults（无键守卫） | if mode == "📈 数据分析": |
| app.py:1235 | `df` | 必置·_defaults＋本键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1235 | `inspector` | 必置·_defaults＋他键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1242 | `inspector` | 必置·_defaults＋他键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1245 | `inspector` | 必置·_defaults＋本键守卫 | if st.session_state.inspector: |
| app.py:1249 | `inspector` | 必置·_defaults＋本键守卫 | if st.session_state.inspector: |
| app.py:1263 | `df` | 必置·_defaults＋本键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1270 | `analysis_history` | 必置·_defaults＋他键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1295 | `df` | 必置·_defaults＋本键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1304 | `analysis_output` | 必置·_defaults＋本键守卫 | if _prev_cache == _cache_key and st.session_state.get("analysis_output") is not None: |
| app.py:1309 | `df` | 必置·_defaults＋本键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1314 | `undergrad_mode` | 必置·_defaults＋他键守卫 | if _prev_cache == _cache_key and st.session_state.get("analysis_output") is not None: |
| app.py:1320 | `analysis_history` | 必置·_defaults＋他键守卫 | if not st.session_state.undergrad_mode: |
| app.py:1336 | `df` | 必置·_defaults＋本键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1342 | `df` | 必置·_defaults＋本键守卫 | if analyze_btn and st.session_state.df is not None and request.strip(): |
| app.py:1367 | `analysis_output` | 必置·_defaults（无键守卫） | if mode == "📈 数据分析": |
| app.py:1368 | `analysis_output` | 必置·_defaults＋本键守卫 | if st.session_state.analysis_output is not None: |
| app.py:1369 | `df` | 必置·_defaults＋他键守卫 | if st.session_state.analysis_output is not None: |
| app.py:1380 | `undergrad_mode` | 必置·_defaults＋他键守卫 | if st.session_state.analysis_output is not None: |
| app.py:1381 | `analysis_history` | 必置·_defaults＋他键守卫 | if not st.session_state.undergrad_mode: |
| app.py:1776 | `language` | 必置·_defaults（无键守卫） | elif mode == "📋 问卷设计": |
| app.py:1780 | `language` | 必置·_defaults（无键守卫） | elif mode == "📋 问卷设计": |
| app.py:2112 | `questionnaire_design` | 必置·_defaults（无键守卫） | elif mode == "📋 问卷设计": |
| app.py:2113 | `questionnaire_design` | 必置·_defaults＋本键守卫 | if st.session_state.questionnaire_design is not None: |
| src/ui/experiment_design_ui.py:19 | `experiment_engine` | 必置·_defaults（读点无外层守卫） | if st.session_state.experiment_engine is None: |
| src/ui/experiment_design_ui.py:22 | `experiment_engine` | 必置·_defaults（读点无外层守卫） | eng = st.session_state.experiment_engine |
| src/ui/onboarding.py:206 | `df` | 必置·_defaults（无键守卫） | Try:202 |
| src/ui/onboarding.py:207 | `inspector` | 必置·_defaults（无键守卫） | Try:202 |
| src/ui/pages/privacy_gate.py:13 | `privacy_accepted` | 必置·_defaults（读点无外层守卫） | if not st.session_state.privacy_accepted: |
| src/ui/paper_writing_ui.py:41 | `paper_engine` | 必置·_defaults（读点无外层守卫） | if st.session_state.paper_engine is None: |
| src/ui/paper_writing_ui.py:44 | `paper_engine` | 必置·_defaults（读点无外层守卫） | engine = st.session_state.paper_engine |
| src/ui/paper_writing_ui.py:596 | `analysis_output` | 必置·_defaults＋本键守卫 | if st.session_state.get("analysis_output") is not None and not engine.state.analysis_results: |
| src/ui/questionnaire_panel.py:94 | `language` | 必置·_defaults（读点无外层守卫） | index=0 if st.session_state.language == "zh" else 1, |
| src/ui/questionnaire_panel.py:98 | `language` | 必置·_defaults（读点无外层守卫） | if lang != st.session_state.language: |
| src/ui/questionnaire_panel.py:440 | `questionnaire_design` | 必置·_defaults（读点无外层守卫） | if st.session_state.questionnaire_design is not None: |
| src/ui/questionnaire_panel.py:441 | `questionnaire_design` | 必置·_defaults＋本键守卫 | if st.session_state.questionnaire_design is not None: |
| src/ui/quick_entries.py:705 | `analysis_history` | 必置·_defaults（读点无外层守卫） | st.session_state.analysis_history.append(history_entry) |
| src/ui/renderers.py:685 | `file_name` | 必置·_defaults（读点无外层守卫） | f"<p>数据文件：{st.session_state.file_name}</p>", |
| src/ui/startup_checks.py:31 | `startup_check_done` | 必置·_defaults（读点无外层守卫） | if not st.session_state.startup_check_done: |
| src/ui/undergrad_wizard.py:302 | `undergrad_wizard_data` | 必置·_defaults（读点无外层守卫） | output = st.session_state.undergrad_wizard_data.get("analysis_output") if ( |
| src/ui/undergrad_wizard.py:1939 | `undergrad_wizard_data` | 必置·_defaults＋本键守卫 | if "undergrad_wizard_data" in st.session_state: |
| src/ui/undergrad_wizard.py:2269 | `_wizard_return` | 必置·_defaults＋本键守卫 | if st.session_state.get("_wizard_return") is not None: |
| src/ui/undergrad_wizard.py:3567 | `polished_draft` | 必置·就近守卫（同 else 块 :3534-3535 先 in 检查补种） | 不在 _defaults |
| src/ui/undergrad_wizard.py:3570 | `polished_draft` | 必置·就近守卫（同上，读点在 :3567 之后） | 不在 _defaults |
| src/utils/pipeline_manager.py:67 | `analysis_pipeline` | 必置·就近守卫（同函数 :64-65 先 in 检查再写） | 不在 _defaults |
| src/utils/pipeline_manager.py:183 | `analysis_pipeline` | 必置·就近守卫（:180 get→:181 is None→:182 写→:183 读） | 不在 _defaults |

分类小计：20 × 必置·_defaults＋本键守卫；17 × 必置·_defaults（读点无外层守卫）；13 × 必置·_defaults（无键守卫）；13 × 必置·_defaults＋他键守卫；1 × 必置·就近守卫（同 else 块 :3534-3535 先 in 检查补种）；1 × 必置·就近守卫（同上，读点在 :3567 之后）；1 × 必置·就近守卫（同函数 :64-65 先 in 检查再写）；1 × 必置·就近守卫（:180 get→:181 is None→:182 写→:183 读）。


## 结论（四条承重）

1. **67 个属性式读取点里，63 个读的键都在 `app.py` 的 `_defaults` 会话初始化表里**（表在 `app.py:273-298`，落键循环在 `app.py:299-301`：`for key, val in _defaults.items(): if key not in st.session_state: st.session_state[key] = val`）。这 27 个键覆盖本档 20 个被读键中的 18 个。
   ⇒ 「属性式读取会抛 AttributeError/KeyError 造成整页红」这个担忧，**对本仓绝大多数点位不成立**：键在启动时无条件补种，读到的最坏情况是 `None`，不是「键不存在」。
2. **真正的「键不存在」面只剩 2 个键、4 个点位**：`analysis_pipeline`（`src/utils/pipeline_manager.py:67 / :183`）与 `polished_draft`（`src/ui/undergrad_wizard.py:3567 / :3570`）。两处都不在 `_defaults` 里，都靠**函数内就地 `in` 守卫**自己补种（`pipeline_manager.py:64-65`、`pipeline_manager.py:180-183`、`undergrad_wizard.py:3534-3535`）。
   ⇒ 判语：现状安全，但守卫是**就近补种**而非集中登记，读点与守卫之间只隔着几行同块代码；把这两个键补进 `_defaults` 即可把「必置」从函数局部不变量升级为全局不变量。
3. **`_defaults` 的「必置」保证只按「整脚本从顶重跑」成立**，而 `src/ui/project_panel.py:54` 有 `st.session_state.clear()`（:46-53 只保 10 个全局设置键，:55 `update(preserved)`）。同一次运行内 clear 之后、下一次重跑之前，所有非 preserved 键都瞬时消失。
   ⇒ 本档 67 点里没有点落在 clear 之后（`project_panel.py` 自身 clear 后只用 `pm.set_active_project(st.session_state, ...)` 传对象，不做属性读，实测 :56-110 零属性读）；但这是**结构性前提**：任何人在 :54 之后插一行 `st.session_state.<k>` 属性读，就是一枚随时会炸的整页红，且它不在任何人的 diff 视野里。
4. **值语义风险 ≠ 不存在风险，本仓该收口的是前者**：13 个点位（表中标「必置·_defaults＋他键守卫」）的存在性判断测的是**别的键**，典型是 `app.py:1060-1070 / :1119-1124 / :1233-1249` 一片以 `if st.session_state.df is not None:` 掩护 `meta` / `inspector` / `file_name` / `interactive_charts` 的读取。
   而 `df` 与这三键**只在部分写路径上成对**：成对写的有 `app.py:629-632`、`app.py:1034-1037 / :1044-1047 / :1054-1057`、`src/ui/onboarding.py:169-172`；**不成对的那条正是工作区恢复路径**——`src/utils/workspace.py:594-601` 单独恢复 `df`（`df_b64` 存在即写，且 `except Exception: pass` 静默吞解码失败），而 `meta/inspector/file_name` 走 `:606-611` 的 `if k in loaded` 逐键条件恢复。
   ⇒ 一个只带 `df_b64`、缺 `inspector` 字段的项目文件恢复后：`app.py:1060` 的 df 守卫过、`app.py:1063` 拿到 `None`，报错发生在**离缺键现场很远**的下游，形态是 `AttributeError/TypeError` 而不是缺键。
   全仓把成对关系写成显式合取的只有 **1 处**：`app.py:1173` `if st.session_state.df is not None and st.session_state.inspector is not None:`（说明该风险已被人撞见过一次）；`:1060-1070 / :1233-1249` 均未合取。⇒ 收口顺序建议：先给恢复路径补成对断言（或让恢复只以「四键齐备」为写 df 的前提），再谈属性式/下标式的风格统一。

## 逐点判据（按文件）

见上表（67 行，逐点）：「依据」列取 AST 祖先链里**最近一层含键名的 `if` 测试原文**；无此类祖先时给出读点自身原文或 `Try`/`For`/`While` 容器名。
两点口径注意：① 含键名是**子串匹配**，故 `app.py:455` 的 `if "undergrad_mode_toggle" not in st.session_state:` 会被算作 `undergrad_mode` 的「本键守卫」——它只影响依据文本，不改判定（该键已由 `_defaults` 补种）；② `with st.expander(...)` 一类容器不在祖先链里，所以 `app.py:682` 落在「读点无外层守卫」。
判定分类：

| 判定 | 含义 |
|---|---|
| 必置·_defaults＋本键守卫 | 键有启动补种，且本点外层 `if` 直接测本键存在/非 None |
| 必置·_defaults＋他键守卫 | 键有启动补种；外层守卫测的是别的键（成对依赖，风险见结论 4） |
| 必置·_defaults（无键守卫） | 键有启动补种；外层只有上下文判定（mode/step/按钮） |
| 可选·就近守卫（函数内） | 不在 `_defaults`，靠同函数/同块的 `in` 检查就地补种 |

## 复现命令与两路计数

```bash
# 路 1：AST（读取点、写点、键集）
python - <<'PY'
import ast, pathlib
def ssobj(n):
    return (isinstance(n, ast.Attribute) and n.attr == 'session_state'
            and isinstance(n.value, ast.Name) and n.value.id == 'st')
SAFE = {'get','pop','setdefault','keys','values','items','clear','update','to_dict'}
files = [pathlib.Path('app.py')] + sorted(pathlib.Path('src').rglob('*.py')) + sorted(pathlib.Path('scripts').rglob('*.py'))
R = W = 0; keys = set()
for p in files:
    for n in ast.walk(ast.parse(p.read_text(encoding='utf-8', errors='replace'))):
        if isinstance(n, ast.Attribute) and ssobj(n.value) and n.attr not in SAFE:
            if isinstance(n.ctx, ast.Load): R += 1; keys.add(n.attr)
            elif isinstance(n.ctx, ast.Store): W += 1
print(R, W, len(keys)); print(sorted(keys))
PY
# 路 2：逐行正则（同一口径的文本实现，便于第三方复核）
grep -rn --include=*.py -o "st\.session_state\.[A-Za-z_][A-Za-z0-9_]*" app.py src scripts | wc -l
```

- 路 1：`67` 读 / `115` 写 / 共 `182` 次属性访问，`20` 个被读键。
- 路 2：`184` 命中 / `69` 读 / `115` 写 / `21` 键。
- **差 2 个「读」、多 1 个键（`plan`）全部落在同一行**：`src/ui/paper_writing_ui.py:609` 的 **docstring 正文**里写了 `依赖 st.session_state.plan + st.session_state.analysis_output；`——正则把散文里的两处也算了，AST 不算。
  ⇒ 采用路 1 为准（67），并在此留痕：任何用文本计数做分母的本族单都会虚高 2。

## 已知漂移与前提

1. `app.py` 处于他人在途 ` M`（h912-12/d913a-43/d914-23 拆分：`render_privacy_gate` / `run_once_startup_cleanup` / `run_once_env_check` / 重依赖预热）。本档 app.py 侧全部行号以**工作树**为准；`_defaults` 块（:273-301）在在途 hunk（:321-353）之前，故两版一致。
2. `src/ui/startup_checks.py` 与 `src/ui/pages/privacy_gate.py` 是**新拆出的模块**，其属性读（`startup_checks.py:31`、`privacy_gate.py:13`）在 HEAD 里位于 `app.py` 内联块（HEAD 行号更大）。普查判定不依赖它在哪，只依赖调用序：`app.py:299-301`（补种）→ `:317` 导入 / `:319` 调 `render_privacy_gate()` → `:325` 导入 / `:327` `run_once_startup_cleanup()` / `:333` `run_once_env_check()`——**顺序前提，若有人把 `_defaults` 往后挪，这两处立刻从「必置」变「真 KeyError」**。
3. `_wizard_return`（`app.py:721`、`src/ui/undergrad_wizard.py:2269`）等下划线前缀键同样在 `_defaults` 里（`app.py:288`），不属于「临时键裸读」。
4. 本普查只看**属性式**读取的下标式对偶面（`st.session_state["df"]` 等）未纳入逐点判定；如需合并成一张表，建议下一单先定「两种形态是否同一条纪律」，否则会出现「属性式收口、下标式继续裸读」的假整洁。

## 20260923 行号订正（s923-25 追加节：只做「对号」，不改上文一字结论）

> 取值时刻 2026-09-23 13:5x。psy HEAD `7d73cf3`；`app.py` 现工作树 2405 行 / 现 HEAD 2433 行 / 本档落盘时（`4230640`，09-21 21:52）的 HEAD `d7bc1f4` 版 2698 行。
> 本节把本档 `app.py` 侧 45 个行号锚点重排到现盘；**判定列、口径、计数一律照旧**，未作任何改动。

### 一、本档 :13 的换算式为什么失效

本档 :13 写「凡 ≥384 行的 app.py 锚点，HEAD 版行号 = 本档行号 + 28」。该式对**当时的** HEAD 逐点成立（本节按式回取 45/45 行的键名全部命中，`+28 换算式失配=0`），但 HEAD 本身在本档落盘后又推进了三笔迁出提交：

- `49cee8a` s922-18 片 1-3 迁至 `src/ui/app_pages_text.py`
- `385ae24` s922-101 片 8（文献与选题）＋片 10（模板中心）路由体迁出
- `f1b4a38` s922-102 片 7a（问卷页混装侧栏）迁出 ⇒ **本档 :60/:61 两处 `language` 读点自此离开 app.py**

⇒ 现在正确的换算只有两跳，且第二跳与「+28」反号：

| 关系 | 现值 |
|---|---|
| 本档行号 → 09-21 的 HEAD(`d7bc1f4`) | `+28`（本档原式，仍成立） |
| 现工作树 → 现 HEAD(`7d73cf3`) | **`−28`**（对 45 个锚点逐点等值，最小点位已在工作树 :272） |
| 本档行号 → 现工作树 | **逐点不等**：`−183`（:19–:59 全段）／`−235`（:62/:63）／**已迁出**（:60/:61） |

⚠️ 别把工作树的 `-28` 当成本档 :13 说的那批在途 hunk：`git diff --numstat -- app.py` 现读 `12/40`（净 −28）与本档记载**同值但不是同一批**——现盘 hunk 已整段移到 HEAD 的 139–204 行（隐私门/自动清理/预热），全部落在 384 以下，所以本档 :146「`_defaults` 块（:273-301）在在途 hunk（:321-353）之前，故两版一致」的**前提位置也变了**（见本节末「未覆盖」）。

### 二、承重 4（本档 :101）点位对号：**结论原样成立，只有号码老了**

本档 :101 句「全仓把成对关系写成显式合取的只有 **1 处**：`app.py:1173` `if st.session_state.df is not None and st.session_state.inspector is not None:`」——

| 项 | 本档（09-21） | 现工作树 | 现 HEAD |
|---|---|---|---|
| 显式合取所在行 | `:1173` | **`:990`** | **`:1018`** |
| 合取体内 `inspector = st.session_state.inspector` | `:1174`（本档表 :39 记作 1174，与 :101  prose 差 1） | **`:991`** | `:1019` |
| 外层 `if helper_q1 in recommendations:`（本档表 :37/:38 的「依据」列） | `:1170` 层 | **`:987`** | `:1015` |
| 全仓该合取的**命中处数** | 1 | **1**（复现见本节末命令） | 1 |

⇒ 「只有 1 处显式合取」这个承重**没有被迁出提交削掉**：`rg -n "st\.session_state\.df is not None" app.py` 现读 4 处命中（`:767` / `:877` / `:990` / `:1050`），其中**唯一带 `and st.session_state.inspector is not None` 的仍是原来那一条**。本档 :37/:38/:39 三行的判定（「必置·_defaults」与「本键守卫」）不受影响。

本档 :101 另外两处范围同步对号：`:1060-1070` → **现工作树 `:877-887`**（HEAD `:905-915`）；`:1233-1249` → **现工作树 `:1050-1066`**（HEAD `:1078-1094`）；顺带 :101 同句的 `:1119-1124` → 现工作树 `:936-941`（HEAD `:964-969`）。本档 :100 的 `app.py:1060`/`:1063` 即上表 `:877`/`:880`。

### 三、:99 成对写点（:101 的取证现场）对号

本档 :99 列的四处「df 与 meta/inspector/file_name 成对写」全部仍在盘上、仍是四连写，仅换号：

| 本档 | 现工作树 | 现 HEAD | 定位特征（末行原文） |
|---|---|---|---|
| `app.py:629-632` | **`:446-449`** | `:474-477` | `st.session_state.archive_tag = entry.get("tag", "")` |
| `app.py:1034-1037` | **`:851-854`** | `:879-882` | `st.session_state.file_name = "sample_survey.csv"` |
| `app.py:1044-1047` | **`:861-864`** | `:889-892` | `st.session_state.file_name = "sample_ttest.csv"` |
| `app.py:1054-1057` | **`:871-874`** | `:899-902` | `st.session_state.file_name = "sample_anova.csv"` |

（本档 :99 说的**不成对**那条走 `src/utils/workspace.py:594-601`，不在 app.py 侧，本节未重排。）

### 四、逐点对照表（45 行，全量）

「同型」列 = 现盘上原文逐字相等的行数；>1 时按本档表序单调不减取第一个可行值，故这类点位的对号靠**顺序**而非唯一性，若日后 app.py 再插同类行需重跑本节命令。

| 本档表行 | 本档 app.py 行号 | 键 | 现工作树 | 现 HEAD | 同型 |
|---|---|---|---|---|---|

| :19 | 455 | `undergrad_mode` | 272 | 300 | 1 |
| :20 | 462 | `undergrad_mode` | 279 | 307 | 1 |
| :21 | 470 | `undergrad_mode` | 287 | 315 | 3 |
| :22 | 682 | `onboarding_completed` | 499 | 527 | 1 |
| :23 | 721 | `_wizard_return` | 538 | 566 | 1 |
| :24 | 802 | `env_status` | 619 | 647 | 1 |
| :25 | 803 | `env_status` | 620 | 648 | 1 |
| :26 | 850 | `undergrad_mode` | 667 | 695 | 1 |
| :27 | 950 | `df` | 767 | 795 | 1 |
| :28 | 1024 | `df` | 841 | 869 | 1 |
| :29 | 1060 | `df` | 877 | 905 | 1 |
| :30 | 1061 | `df` | 878 | 906 | 2 |
| :31 | 1062 | `meta` | 879 | 907 | 1 |
| :32 | 1063 | `inspector` | 880 | 908 | 2 |
| :33 | 1070 | `file_name` | 887 | 915 | 1 |
| :34 | 1119 | `interactive_charts` | 936 | 964 | 1 |
| :35 | 1124 | `interactive_charts` | 941 | 969 | 1 |
| :36 | 1141 | `df` | 958 | 986 | 1 |
| :37 | 1173 | `df` | 990 | 1018 | 1 |
| :38 | 1173 | `inspector` | 990 | 1018 | 1 |
| :39 | 1174 | `inspector` | 991 | 1019 | 2 |
| :40 | 1233 | `df` | 1050 | 1078 | 1 |
| :41 | 1235 | `df` | 1052 | 1080 | 1 |
| :42 | 1235 | `inspector` | 1052 | 1080 | 1 |
| :43 | 1242 | `inspector` | 1059 | 1087 | 1 |
| :44 | 1245 | `inspector` | 1062 | 1090 | 1 |
| :45 | 1249 | `inspector` | 1066 | 1094 | 1 |
| :46 | 1263 | `df` | 1080 | 1108 | 1 |
| :47 | 1270 | `analysis_history` | 1087 | 1115 | 1 |
| :48 | 1295 | `df` | 1112 | 1140 | 1 |
| :49 | 1304 | `analysis_output` | 1121 | 1149 | 2 |
| :50 | 1309 | `df` | 1126 | 1154 | 1 |
| :51 | 1314 | `undergrad_mode` | 1131 | 1159 | 3 |
| :52 | 1320 | `analysis_history` | 1137 | 1165 | 1 |
| :53 | 1336 | `df` | 1153 | 1181 | 1 |
| :54 | 1342 | `df` | 1159 | 1187 | 1 |
| :55 | 1367 | `analysis_output` | 1184 | 1212 | 1 |
| :56 | 1368 | `analysis_output` | 1185 | 1213 | 2 |
| :57 | 1369 | `df` | 1186 | 1214 | 2 |
| :58 | 1380 | `undergrad_mode` | 1197 | 1225 | 3 |
| :59 | 1381 | `analysis_history` | 1198 | 1226 | 1 |
| :60 | 1776 | `language` | **已迁出 app.py** | — | 0 |
| :61 | 1780 | `language` | **已迁出 app.py** | — | 0 |
| :62 | 2112 | `questionnaire_design` | 1877 | 1905 | 1 |
| :63 | 2113 | `questionnaire_design` | 1878 | 1906 | 1 |

### 五、未覆盖（如实登记，别把本节当全档已对号）

1. 本节只重排了**表内 45 个 app.py 锚点**与正文 :99/:100/:101 引用的 app.py 锚点。本档「已知漂移与前提」:146-:148 里的 **<384 行侧锚点未对号**，且已确知它们同样老了：`_defaults` 块本档记 `:273-301`（补种循环 `:299-301`），现盘实际在 **`app.py:90`（`_defaults = {`）/ `:116`（`for key, val in _defaults.items():`）**，工作树与 HEAD 同值；本档 :147 的调用序锚点 `:317/:319/:325/:327/:333` 未逐个复核。⇒ 引「承重 1/2」（`_defaults` 补种覆盖面）时**先重取这两个号**，别沿用 :273-301。
2. `src/**/*.py` 侧的 22 个锚点（本档表 :64-:85 区段）与 `src/utils/workspace.py:594-601 / :606-611` 的恢复路径行号**未对号**。
3. 本节 :37/:38 之外，本档表把同一句合取记成两行（df 与 inspector 各一行），:41/:42 同型；对号后仍是「同号两行」，不是漏项。

### 六、复现

```
$ cd /d/code/psy-analysis
$ git show d7bc1f4:app.py > tmp/s923-25/app-0921HEAD.py    # 09-21 21:52 的 HEAD 版
$ git show HEAD:app.py     > tmp/s923-25/app-HEAD.py       # 对号当时的现 HEAD
$ rg -n "st\.session_state\.df is not None" app.py       # 现工作树 4 命中：767/877/990/1050
$ rg -n "st\.session_state\.df is not None and st\.session_state\.inspector is not None" app.py   # 唯一命中 990
$ rg -n "helper_q1 in recommendations" app.py              # 987
$ .venv/Scripts/python.exe -X utf8 tmp/s923-25/remap_census.py   # 整表重排（含「+28 换算式失配=0」自检）
```

> 注：`tmp/` 在本仓 `.gitignore:29` 内，上面两个脚本与两份 app.py 副本**不入库**；第四节表格由该脚本生成，若脚本被清、按上面三条 `rg` 仍能复核本节承重 4 的对号结论。

## 20260928 回写节（s927-37：把结论 1 的「27 键」逐键落盘）

> 取值时刻 2026-09-28 13:5x。psy HEAD `4ad0664`；执行班 `qoder-executor-20260928-0340-psy88`（波次 44 写位／文档面）。
> 触发点：`zcode-bridge/done/s922-112-defaults-keys-snapshot.result.md:51-52` 遗留 2——「快照与普查档是**两份独立清单**：
> 分片真丢键时本测试翻红，但 `psy-session-state-attr-read-census-20260921.md` 的结论 1（27 键）需人工按提示回写；
> 本单只在测试里写了回写指引，未改普查档（属规划/文档域）」。本节就是那次回写，**零生产码／零测试件改动**。
> 与 s923-25 追加节同规：**只追加、上文一字未改**（`git diff --numstat` 现读 deletions=0）——
> 本仓同族档（`psy-session-subscript-read-census-20260922.md:71` 引「上份『63/67 都靠 `_defaults` 兜住』」、
> 本档自述「本档 :101」「:146-:148」）都在按**行号**引用上文，改上文会让别人的锚点整体位移。

### 一、结论 1（本档 :92）那两处旧锚先对号

本档 :92 原记「表在 `app.py:273-298`，落键循环在 `app.py:299-301`」——即第五节「未覆盖 1」点名的、
当时只补了行号没补清单的那一格：

| 本档 :92（09-21 落盘） | 现盘（工作树与 `HEAD:app.py` 逐位同） |
|---|---|
| `_defaults` 表体 `app.py:273-298` | **`app.py:90-115`**（`:90 _defaults = {` ／ `:115 }`；`:96` 是注释行，`:110`/`:111`/`:113`/`:114` 带尾注） |
| 落键循环 `app.py:299-301` | **`app.py:116-118`**（`:116 for key, val in _defaults.items():`／`:117 if key not in st.session_state:`／`:118 st.session_state[key] = val`） |

⇒ 结论 1 的**承重不变**：仍是"唯一启动补种表、无条件 `if key not in` 落种"，只是号码老了；
本档 :147 那条顺序前提（补种在前、`render_privacy_gate`／`run_once_*` 在后）本确节**未复核**，引它前先现跑。

### 二、27 键逐键清单（AST 现场解析工作树 `app.py`，不执行 app.py）

按**源码序**（哨兵清单是同一 27 枚的**排序态**，二者经第三节三向等式互绑）。
「本档读面」＝该键是否出现在本档 :18-:85 的 67 行属性式读取逐点表里。

| # | 键 | 盘上行号 | 播种默认值 | 本档读面 |
|---|---|---|---|---|
| 1 | `df` | :91 | `None` | ✓ |
| 2 | `meta` | :91 | `None` | ✓ |
| 3 | `inspector` | :91 | `None` | ✓ |
| 4 | `analysis_output` | :92 | `None` | ✓ |
| 5 | `plan` | :92 | `None` | ✗（正则路多出的那 1 键，见本档 :141——散文里的 `st.session_state.plan`） |
| 6 | `file_name` | :92 | `None` | ✓ |
| 7 | `questionnaire_design` | :93 | `None` | ✓ |
| 8 | `paper_engine` | :94 | `None` | ✓ |
| 9 | `experiment_engine` | :95 | `None` | ✓ |
| 10 | `quick_model_id` | :97 | `""` | ✗ |
| 11 | `onboarding_completed` | :98 | `False` | ✓ |
| 12 | `privacy_accepted` | :99 | `False` | ✓ |
| 13 | `undergrad_mode` | :100 | `False` | ✓ |
| 14 | `undergrad_path` | :101 | `None` | ✗ |
| 15 | `undergrad_step` | :102 | `0` | ✗ |
| 16 | `undergrad_wizard_data` | :103 | `{}` | ✓ |
| 17 | `analysis_history` | :104 | `[]` | ✓ |
| 18 | `_wizard_return` | :105 | `None` | ✓（本档 :148 已点名它不是"临时键裸读"） |
| 19 | `workspace_saved` | :106 | `None` | ✗（死键候选，判语在同族档，见本确节第四节末） |
| 20 | `language` | :107 | `"zh"` | ✓（本档表内两点随 `f1b4a38`／s922-102 片 7a 已离开 app.py，见本档 :162 与 :250-:251；现盘读点＝`src/ui/questionnaire_panel.py:104`/`:108`，本档记的 `:94`/`:98` 又漂了 +10——即本档 :258「src 侧 22 个锚点未对号」的又一例） |
| 21 | `output_language` | :108 | `"zh"` | ✗ |
| 22 | `interactive_charts` | :109 | `False` | ✓ |
| 23 | `archive_tag` | :110 | `""` | ✗（属性**写**侧在本档 :195 行的成对写点里，读侧无） |
| 24 | `quick_entry` | :111 | `None` | ✗ |
| 25 | `show_quick_detail` | :112 | `False` | ✗ |
| 26 | `startup_check_done` | :113 | `False` | ✓ |
| 27 | `env_status` | :114 | `None` | ✓ |

合计 27 枚（`len()` 现算，非手数）；「✓」18 枚／「✗」9 枚。

### 三、与哨兵测试的读数对照（**如实：回写前后不变**）

- 哨兵＝`tests/test_app_defaults_keys_snapshot.py`（s922-112 落）。清单在 `:35-63`（`EXPECTED_DEFAULTS_KEYS`，排序态 27 项）；
  判据是「集合等／有序表等／基数等」三向互证 ＋ `len(EXPECTED_DEFAULTS_KEYS) == 27`。
- 现跑读数：`4 passed in 0.18s`，rc=0。⇒ **哨兵本来就绿，本节没有、也不可能"使它翻绿"**：它 AST 读的是 `app.py`
  磁盘源码，与本档是两份互不依赖的清单（这正是 s922-112 遗留 2 的原话）。差异如实登记为
  **「文档回写对哨兵零影响」**——反过来说，本确节的清单若与哨兵清单不一致，也不会被任何测试发现，
  所以第四节给了独立复算，第五节给了可复现命令。
- 独立复算（AST 两路，`.venv` Python 3.12.9）：
  - 哨兵清单 vs 工作树实测：集合等 **True**／排序等 **True**／「哨兵有·盘上无」∅／「盘上有·哨兵无」∅；
  - 工作树 vs `HEAD:app.py`（`4ad0664`）：键数 27=27、集合等 True、有序等 True、两侧差集均空 ⇒
    在途 ` M app.py`（`git diff --numstat` ＝ `12 40`、净 −28 行）**没动 `_defaults` 的键集与默认值**，
    本档 :146「`_defaults` 块在在途 hunk 之前，故两版一致」的前提在现盘仍成立（位置已换到"hunk 在 384 以下"，见本档 :172）。
  - 哨兵件自带的 `__main__` 自检（`python tests/test_app_defaults_keys_snapshot.py`）打印 `_defaults 键数=27` ＋ 排序清单，rc=0。

### 四、本档属性读面 vs 27 键（doc-side 复算，**不重扫源码**）

- 本档 :18-:85 逐点表去重＝**20 个被读键**；其中 **18 个**在 27 键表内，2 个不在（`analysis_pipeline`／`polished_draft`）
  ⇒ **结论 1 的「20 中的 18」与结论 2 的「真·键不存在面只剩 2 键 4 点」在现盘上仍自洽**。
  注意这一复算的口径：它是对**本档自己的表**做集合运算（文档内自洽性），不是重跑 s922-04 的 AST 普查 ⇒ 不改本档总量读数（67/115/182）。
- 反向 9 枚（27 − 18）＝`archive_tag`／`output_language`／`plan`／`quick_entry`／`quick_model_id`／`show_quick_detail`／
  `undergrad_path`／`undergrad_step`／`workspace_saved` ⇒ 它们**不在属性式读面**（走下标式／别名面／widget `key=` 面，
  或只被写不被读）。同族档已各自登记，本确节**不重复处置、不改判**：
  `psy-session-state-ast-census-20260924.md:62`（「27 键中 26 个有静态直访、`workspace_saved` 仅有播种」）、
  `psy-session-key-implicit-census-20260924.md:60`（`_defaults` 覆盖率按不同分母 22.7%／6.9%／6.2%）。

### 五、复现（一律 `.venv` 解释器）

```
$ cd /d/code/psy-analysis
$ .venv/Scripts/python.exe -m pytest tests/test_app_defaults_keys_snapshot.py -q        # 4 passed，rc=0
$ .venv/Scripts/python.exe tests/test_app_defaults_keys_snapshot.py                     # 打印 键数=27 ＋排序清单，rc=0
$ grep -n "_defaults" app.py                                                            # 现读 :90（表体起）与 :116（落键循环）
$ git diff --numstat -- app.py                                                          # 12  40  app.py（净 −28，键集未变）
```

### 六、本确节的边界（没做什么）

1. **零生产码／零测试件改动**：`app.py` 与 `tests/*` 只读；本确节只动本档一枚文件、纯追加。
2. **没把 `analysis_pipeline`／`polished_draft` 补进 `_defaults`**（本档 :95 的那条建议）：属行为改动、
   且落点是未归因在途件 `app.py`（波次 42/44 列为禁碰面）⇒ 留人工/主班，不在本单面。
3. **没重跑属性式普查**（67/20/18/182 等分母），也**没改** :147 的调用序前提与 :149 的下标式对偶面缺口记载。
4. **没替别人回写同族档或哨兵清单**：三处清单（本档表／哨兵 `:35-63`／同族普查）仍各自独立，本节的作用是把
   本档结论 1 那句"这 27 个键"从**指代**变成**清单**，使三份可比对拍。
5. 红线自查：本确节不涉统计数值／效应量／p 值判定；键名一律先 grep 再引（盘上无 `analysis_ready`，真名 `analysis_recipe`，与本单无关）。

