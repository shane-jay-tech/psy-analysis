# PsychoPy 生成脚本「引用-定义序」静态审计（s920-02，只读）

生成：2026-09-20 03:1x（任务单编号日期 20260919，执行落在 09-20 凌晨）｜执行：Qoder 会话
口径：**纯静态 AST 审计**——不装 psychopy、不执行任何生成脚本、`src/` 与 `tests/` 零改动。
上游：`done(s919-01)`（缩进 BLOCKER 修复）遗留 1「`kb`/`timer` 等对象创建点是否都在引用之前未查——需真机才能定论，静态可先做」。

## 一句话结论

**12 种形态（6 范式 × feedback 开/关）零违例**：顶层没有任何"先引用后定义"、没有任何引用了全模块从未定义的名字；
`run_trial` 的函数体也**不引用任何在其定义行之后才绑定的模块级名字**（它拿的是形参）⇒
s919-01 留的那个"要真机才能定论"的疑点，在**名字序**这一层已经可以判定为安全（剩下的运行时属性/分支走位仍属真机面，见二、六节）。

## 二、方法与边界

对每个形态取 `generate_psychopy_script(PsychoPyExperiment(paradigm=P, show_feedback=F))` 的产物，`ast.parse` 后：

| 检查 | 判据 |
|---|---|
| 顶层顺序违例 | 按 `tree.body` 语句序维护"已定义集合"，某语句里的 `Name(Load)` 若不在集合内、且其首次定义出现在**更晚的语句** ⇒ 记违例 |
| 从未定义的名字 | 同上，但全模块任何位置都没有该名字的 `Store`/`import`/`def`/`with as`/`except as`/`for 目标` ⇒ 记孤儿（内置名与 `__name__` 类除外） |
| 函数体的延迟绑定 | 对每个模块级 `FunctionDef`，列出它引用的**定义行晚于该函数定义行**的模块级名字，再比对它的**调用点行号**是否早于那些定义 ⇒ 早于才是真风险 |

**看不到什么**（静态审计的固有边界，别高估这份报告）：
- 条件分支的实际走位（`if show_feedback:` 只有生成期知道）；
- `psychopy.*` 运行时对象的属性是否存在（`kb.getKeys()` 之类要真机）；
- 闭包/global 声明带来的重绑定（本产物里没有 `global` 语句，已核）。
⇒ 本报告能定论"**名字层面顺序无违例**"，不能定论"实验跑得通"。后者仍需一台装 psychopy 的机器（遗留 1）。

## 三、结果（12 形态全量）

| 范式 | fb=False | fb=True | 顶层违例 | 从未定义 | 行数（off/on） |
|---|---|---|---|---|---|
| stroop | ✅ | ✅ | 无 | 无 | 223 / 234 |
| flanker | ✅ | ✅ | 无 | 无 | 220 / 231 |
| emotion | ✅ | ✅ | 无 | 无 | 215 / 226 |
| memory | ✅ | ✅ | 无 | 无 | 218 / 229 |
| custom | ✅ | ✅ | 无 | 无 | 215 / 226 |
| 未知范式串（走默认分支） | ✅ | ✅ | 无 | 无 | 215 / 226 |

所有形态的模块级 `def` 只有一个：`run_trial@78`；调用点两处在主循环与练习循环内（fb=True 时 stroop 为 `:179`/`:204`）。

`run_trial` 引用的模块级对象及其定义行（stroop）：

| 对象 | 定义行 | 与 `def@78` 的关系 |
|---|---|---|
| `core` / `random` / `datetime`（import） | 12 / 15 / 18 | 在前 ✅ |
| `win` | 23 | 在前 ✅ |
| `kb` | 31 | 在前 ✅ |
| `fixation` | 36 | 在前 ✅ |
| `trial_stim` | 40 | 在前 ✅ |
| `feedback` | 42 | 在前 ✅（且**两种 fb 形态都在**，见第四节 1） |
| `trial` | —（模块级 `for trial in trials:` 在 `:167`/`:178`） | **不构成引用**：`run_trial(trial, trial_num)` 的形参把它遮住了，函数体读的是形参（见第四节 2） |
| `timer`/`key_events`/`correct`/`rt`/`response`/`expected`/`color`/`color_to_key`/`keys` | 函数体内（`timer` 在 `:92`） | 局部变量，不参与模块序 |

## 四、两条具体结论

1. **`feedback` 安全结论复核一致**（s919-01 遗留 1 里已经答掉的那半）：
   `show_feedback=False` 的产物里 `feedback = visual.TextStim(...)` 仍出现在 **`:42`（无条件创建）**，
   并在 **`:173-175`**（"练习结束"屏）被 `.text/.color/.draw()` 使用 ⇒ **不会 NameError**，与上游结论一致。
   顺带量了一下：fb=False 产物里 `feedback` 只出现 4 次（创建＋练习结束屏 3 次），fb=True 出现 9 次（多出试次内的对错反馈块）。
2. **`kb`/`timer` 那类"创建点是否都在引用之前"已有答案**（正面回答 s919-01 遗留 1 的静态可查部分）：
   `run_trial@78` 的函数体**不引用任何在其定义行之后才绑定的模块级名字**——它读的 6 个外部对象
   （`core`/`random`/`datetime` 三个 import＋`win@23`/`kb@31`/`fixation@36`/`trial_stim@40`/`feedback@42`）
   全部创建在 `:23-42` 的 `_script_window_setup`/`_script_stimuli_setup` 段里，早于 `def`；
   `timer` 是函数体内 `:92` 的局部对象。12 个形态逐行都是 `引用后段定义的名字=无`（输出见第五节）。
   ⚠️ 顺带记一次**审计自己的假阳性**：第一版探针没扣函数形参与局部变量，把 `trial` 误报成
   "函数体裸读外层循环变量"（`run_trial(trial, trial_num)` 其实有同名形参遮蔽）⇒ 判据必须
   **先减形参/局部，再谈"引用了模块级名字"**；本节结论以修正后的版本为准。

## 五、复现命令

一次性 AST 脚本**未落盘于仓内**（与 s918-28/s919-01 同口径），下面是可整段贴进 shell 的最小复现：

```bash
cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe - <<'PY'
import ast, builtins
from src.experiment_design.psychopy_generator import PsychoPyExperiment, generate_psychopy_script
B = set(dir(builtins)) | {"__name__", "__file__", "__doc__"}

def stores(nodes):                       # 在这里被绑定的名字（含 import / def / with as / except as / for 目标 / 形参）
    out = set()
    def rec(n):
        for ch in ast.iter_child_nodes(n):
            if isinstance(ch, ast.Name) and isinstance(ch.ctx, (ast.Store, ast.Del)):
                out.add(ch.id)
            elif isinstance(ch, ast.arg):
                out.add(ch.arg)
            elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(ch.name); rec(ch)
            elif isinstance(ch, ast.alias):
                out.add(ch.asname or ch.name.split(".")[0])
            elif isinstance(ch, ast.ExceptHandler):
                if ch.name:
                    out.add(ch.name)
                rec(ch)
            else:
                rec(ch)
    for x in (nodes if isinstance(nodes, list) else [nodes]):
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(x.name)
        rec(x)
    return out

def loads(nodes):                        # 本层读取的名字（嵌套 def/class 单独按作用域算）
    out = []
    def rec(n):
        for ch in ast.iter_child_nodes(n):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(ch, ast.Name) and isinstance(ch.ctx, ast.Load):
                out.append(ch.id)
            rec(ch)
    for x in (nodes if isinstance(nodes, list) else [nodes]):
        rec(x)
    return set(out)

def calls_of(tree, name):
    return sorted({n.lineno for n in ast.walk(tree)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name})

def audit(src, label):
    tree = ast.parse(src)
    mdl = {}                             # 模块级名字 -> 首次绑定所在语句的行号
    for st in tree.body:
        for nm in stores([st]):
            mdl.setdefault(nm, st.lineno)
    defined, bad, never = set(), [], set()
    for st in tree.body:                 # ① 顶层线性序：先引用后定义 / 从未定义
        for nm in loads([st]):
            if nm in B or nm in defined:
                continue
            if nm in mdl and mdl[nm] > st.lineno:
                bad.append((st.lineno, nm, mdl[nm]))
            elif nm not in mdl:
                never.add(nm)
        defined |= stores([st])
    print(f"[{label}] 顶层顺序违例={bad or '无'} 顶层从未定义={sorted(never) or '无'}")
    for fn in [f for f in tree.body if isinstance(f, ast.FunctionDef)]:   # ② 函数体的延迟绑定
        late = sorted({nm for nm in loads(fn.body) | loads(fn.decorator_list)
                       if nm in mdl and mdl[nm] > fn.lineno})
        cs = calls_of(tree, fn.name)
        risk = [nm for nm in late if cs and min(cs) <= mdl[nm]]
        print(f"    {fn.name}@{fn.lineno} 引用后段定义的名字={late or '无'} 调用点={cs} 运行时风险={risk or '无（调用都在定义之后）'}")

for p in ("stroop", "flanker", "emotion", "memory", "custom", "unknown"):
    for fb in (True, False):
        audit(generate_psychopy_script(PsychoPyExperiment(paradigm=p, show_feedback=fb)), f"{p}/fb={fb}")
PY
```

上面的脚本已**原样跑过**，12 形态逐行输出（节选，全部同形）：

```
[stroop/fb=True] 顶层顺序违例=无 顶层从未定义=无
    run_trial@78 引用后段定义的名字=无 调用点=[179, 204] 运行时风险=无（调用都在定义之后）
[stroop/fb=False] 顶层顺序违例=无 顶层从未定义=无
    run_trial@78 引用后段定义的名字=无 调用点=[168, 193] 运行时风险=无（调用都在定义之后）
[flanker/fb=True]  … 引用后段定义的名字=无 调用点=[176, 201]
[flanker/fb=False] … 引用后段定义的名字=无 调用点=[165, 190]
[emotion/fb=True]  … 引用后段定义的名字=无 调用点=[171, 196]
[emotion/fb=False] … 引用后段定义的名字=无 调用点=[160, 185]
[memory/fb=True]   … 引用后段定义的名字=无 调用点=[174, 199]
[memory/fb=False]  … 引用后段定义的名字=无 调用点=[163, 188]
[custom/fb=True]   … 引用后段定义的名字=无 调用点=[171, 196]
[custom/fb=False]  … 引用后段定义的名字=无 调用点=[160, 185]
[unknown/fb=True]  … 引用后段定义的名字=无 调用点=[171, 196]
[unknown/fb=False] … 引用后段定义的名字=无 调用点=[160, 185]
```

`run_trial` 的行号 `@78` 与两处调用点位置在 12 个形态里完全一致（只有 fb=False 少 11 行，故调用点前移），
说明**引用序对范式分支与 feedback 开关都不敏感**——这两处分支只换块内内容，没有挪动对象的创建点。

## 六、零改动自证

- 只读命令：`ast.parse`／`inspect.signature`／生成函数调用（产物只在内存里，未落盘）
- `git status --porcelain src tests` 在本次审计前后均为**该单零改动**（本文件是唯一产出）
- 未装任何依赖、未 import psychopy（生成器本身不依赖它，`generate_psychopy_script` 只拼字符串）
- 消费面沿用 s919-01 的结论：`generate_psychopy_script` **UI 未接线**，故本审计的实害面是"直接调 API 的人"
