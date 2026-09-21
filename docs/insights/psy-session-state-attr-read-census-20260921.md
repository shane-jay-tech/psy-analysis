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
