# psy `session_state['df']` 就地变更风险审计（s918-09，只读）

生成：2026-09-19 01:5x｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
**零源码改动。**
锚点 `KNOWN_ISSUES.md:156` 原文「**UI 线程禁止就地变更 df**（来源：0912-02-08 线程审计；2026-09-13 登记）：
方案 B 后台保存按「整体替换、不就地改」的 St…」逐字命中 ✓（行号 :156 与任务书一致）。

## 结论一句

**全仓 24 处命中，就地变更形态为 0 条**——KNOWN_ISSUES:156 这条红线今天是成立的；
但它**只靠"没人写就地代码"维持，没有任何机械守护**（无测试、无 lint 规则拦得住一次 `df[col] = …`）。
唯一需要动一行的是 `anova.py:152` 缺 `.copy()` 的形态不统一（实测无害，见第三节）。

## 一、全量命中分类（`grep -rn "session_state\.df\b\|session_state\[.df.\]" src app.py --include="*.py"` → 24 行）

| 类别 | 处数 | 位置 |
|---|---|---|
| **整体替换**（赋新对象，符合红线） | **8** | `src/ui/onboarding.py:169`、`src/ui/template_center_panel.py:196`、`src/ui/upload_state.py:32`、`src/utils/workspace.py:598`、`app.py:629`、`app.py:1034`、`app.py:1044`、`app.py:1054` |
| **取别名（共享引用）** | **4** | `src/ui/onboarding.py:206`、`app.py:1061`、`app.py:1295`（`_df_obj`）、`app.py:1369` |
| **只读**（判空／读形状／当实参传出去） | **11** | `app.py:950`、`:1024`、`:1060`、`:1141`、`:1173`、`:1233`、`:1235`（传 `resolve_intent`）、`:1263`（`.shape[0]`）、`:1309`（传 `run_analysis`）、`:1336`（传 `archive_analysis`）、`:1342` |
| **注释文本**（非代码） | **1** | `src/utils/pipeline_manager.py:87` |
| 合计 | **24** | — |

## 二、就地形态的定点排查（三查全空）

1. **`inplace=True`**：`grep -rnE "\b(df|_df|_df_obj|data)\.[a-z_]+\([^)]*inplace\s*=\s*True" src app.py --include=*.py`
   → **零命中**（全仓没有对 df 变量用 inplace 的调用）。
2. **别名之后的下标赋值**：4 个别名点各自往后整段扫 `df[`／`df.loc[`／`df.iloc[`／`df.update(`：
   `app.py:1061`（往后 80 行）、`app.py:1369`（52 行）、`src/ui/onboarding.py:206`（17 行）→ **全部零命中**；
   `app.py:1295` 的 `_df_obj` 只作为参数传给 `archive_analysis`（`:1336`），未再写。
3. **分析层的写入**：`src/analysis/*` 里确有大量 `clean[col] = …` 形态，但其接收者一律是副本：
   `advanced.py:42/149/407` 是 `df[cols].copy()`，`anova.py:331/619` 同；
   `advanced.py:171` 是 `clean.copy()`。⇒ **不触达 session df 对象**。

## 三、唯一的不统一形态（建议补一行，非缺陷）

`src/analysis/anova.py:152`（在 `two_way_anova`，:139）：

```python
clean = df[[dv, iv1, iv2]].dropna()      # ← 同文件 :331 / :619 都写的是 .copy()
clean[iv1] = clean[iv1].astype(str)      # :153  随后写列
clean[iv2] = clean[iv2].astype(str)      # :154
```

**实测无害**（pandas 3.0.3）：fancy-index `df[[a,b]]` 已是新对象，写列不回写父帧，且不再报
`SettingWithCopyWarning`。复现：
`cd /d/code/psy-analysis && .venv/Scripts/python.exe -c "import pandas as pd; df=pd.DataFrame({'y':[1.0,2.0],'g':['a','b'],'h':[1,2]}); b=df['g'].tolist(); c=df[['y','g','h']].dropna(); c['g']=c['g'].astype(str)+'_X'; print(df['g'].tolist()==b, pd.__version__)"`
→ `True 3.0.3`（父帧未变）。

但仍建议补 `.copy()`：①与同文件另两处形态统一；②不把正确性押在
「fancy-index 恰好返回副本」这一 pandas 实现细节上（CoW 语义历史上变过两次）。
本单按「只读」纪律**未改**。

## 四、真正的风险不在"现在有人违反"，而在"没有任何东西守着"

红线 :156 登记于 2026-09-13，靠人记。今天 0 违反是**结果**不是**约束**。
建议（属新工作项，本单不做）：加一条静态守护测试，钉住「session df 只被整体替换」——
最小实现即对本审计第二节的两条 grep 断言零命中，成本约 15 行，能挡住未来任何人写
`st.session_state.df[col] = ...` 或对别名做 inplace 调用。
这条与本夜班 `n918-15-pipe-anchor-gate-pattern`（锚点闸模式）同族：**把"靠人遵守"的条款转成可跑的门**。

## 五、方案 B 依赖面的补充说明

`KNOWN_ISSUES:156` 提到的「方案 B 后台保存依赖引用快照语义」——本次顺带核实：
后台保存路径的入参就是 `st.session_state.df` 本体（`app.py:1336` 传给 `archive_analysis`），
所以红线一旦被违反，破坏的正是**在途后台任务的快照一致性**，且现象会是"存档内容与实际数据不符"，
不会报错。⇒ 第四节那道守护门的优先级应按此上调。

## 六、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| grep 全量命中入表并逐条分类 | **24 行**全部入表（第一节表格 4 类，8＋4＋11＋1＝24） | `cd /d/code/psy-analysis && grep -rn "session_state\.df\b\|session_state\[.df.\]" src app.py --include="*.py" \| wc -l` → 24 |
| 零源码改动 | 本单只新增本报告；`git status --porcelain app.py src/` 出 **6 项**，其中 **2 项属本夜班更早的 `s918-10`**（`src/questionnaire/academic_literature.py`、`kb_search.py` 的 APA7 收敛），**其余 4 项为班前既有**（`app.py`/`lock_manager.py` modified ＋ `heavy_preload.py`/`startup_checks.py` untracked）——**本单自身 0 改动**，第三节建议项未落地 | `cd /d/code/psy-analysis && git status --porcelain app.py src/` → 6 行；逐文件归因见本行说明 |

## 遗留问题

1. 本审计的检索面是 `session_state.df` 与 `session_state["df"]` 两种写法；
   若有人先 `ss = st.session_state` 再 `ss.df[...] = ...`，正则与 AST 两版都抓不到
   （`template_center_panel.py:196`／`upload_state.py:32` 正是**函数参数名就叫 `session_state`** 的形态——
   但它们做的是整体替换，安全）。守护门落地时需把这一形态一并纳入。
2. `pipeline_manager.py:87` 是 docstring 提及，非代码；分类表已单列，避免后人误数为命中。
3. 本单未审 `session_state.df` 之外的其他可变对象（如 `inspector`、`analysis_results`）——
   任务书范围只到 df；同类风险在那些键上是否也存在，未查。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
