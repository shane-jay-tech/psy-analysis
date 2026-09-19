# psy「pytest 终端汇总行被吞」诊断（s918-51，只读）

生成：2026-09-19 12:0x｜执行：Qoder 会话（班次 `qoder-rev-20260919-1020`，倒序尾部续班）
**不改任何文件**（只跑测试与检索；跑出的 `.pytest_cache`/`__pycache__` 属 pytest 既有行为，均在 .gitignore 内）。

## 结论一句

**今天不复现，且原猜想的两条代码依据都被否证**——
全量日常跑汇总行正常输出：`2859 passed, 1 skipped, 89 deselected, 43 warnings in 277.72s (0:04:37)`，退出码 **0**。
建议日间把 9/13 那条记为「未复现·已否证猜想」，别再让下一班照"e2e conftest 硬退出"去查。

## 一、原猜想的两处否证

| 猜想 | 实测 | 复现命令 |
|---|---|---|
| 「**浏览器 e2e conftest 的 atexit 硬退出**」（`psy-app-split-2-20260913.md:35`，行号命中 ✓） | `grep -n "pytest_sessionfinish\|pytest_terminal_summary\|pytest_unconfigure\|atexit\|os\._exit\|sys\.exit" tests/conftest.py` → **零命中**；且**仓内根本没有顶层 `conftest.py`**（只有 `tests/conftest.py`） | `cd /d/code/psy-analysis && ls conftest.py` |
| 「全仓某处 `os._exit` 硬退出」 | 全仓唯一 `atexit.register` 是 `src/utils/autosave.py:128 atexit.register(flush_background, 5.0)`；`flush_background`（:118-125）**吞掉一切异常、返回元组、不打印、不调用 `os._exit`/`sys.exit`** | `cd /d/code/psy-analysis && grep -rn "atexit" src --include=*.py` |

e2e 侧的 `proc.terminate()`／`proc.kill()`（`test_playwright_e2e.py:70/79/83`、`test_e2e_v52_paths.py:86/95/99`）
只作用于**自己 Popen 的 streamlit 子进程**，不可能吞掉父进程的 stdout 尾行。

## 二、复现尝试（四组，全部没能吞掉）

```
A  .venv/Scripts/python.exe -m pytest tests/test_startup_checks.py tests/test_error_messages.py -q > /tmp/a.txt 2>&1
   → 尾行「16 passed in 2.86s」在，文件 2 行
B  .venv/Scripts/python.exe -m pytest tests/test_error_messages.py -q > /tmp/b.txt 2>&1
   → 「12 passed in 0.16s」（完成标准要求的基线回绿 ✓）
C  同 A 但不重定向（直连终端）
   → 「16 passed in 2.12s」
D  .venv/Scripts/python.exe -m pytest -m "not online and not e2e and not benchmark" -q > /tmp/full.txt 2>&1
   → 退出码 0；57 行输出；**尾行汇总完整**：
     2859 passed, 1 skipped, 89 deselected, 43 warnings in 277.72s (0:04:37)
```

A/C 故意挑了 `test_startup_checks.py`——它是**测试路径里唯一在 import 期动全局 stdout** 的文件
（`tests/test_startup_checks.py:19 sys.stdout.reconfigure(encoding="utf-8")`，全仓 `grep -rn "sys.stdout" tests/ src` 仅此一处），
但它与汇总行共存无碍 ⇒ 该嫌疑也排除。

## 三、还剩哪一面没验（以及为什么本单不验）

**真跑 e2e/playwright 那一层**（`-m e2e`／`-m playwright`）。本单**未跑**：
它会真的 `Popen` streamlit 服务并拉浏览器，属重外呼且可能改 `logs/`、占端口——与「只读诊断」边界冲突。
若要结案，日间按此二分（每条都留全量输出，别用 `head` 截断，见第四节）：

```
cd /d/code/psy-analysis
.venv/Scripts/python.exe -m pytest -m "e2e or playwright" -q > /tmp/e2e.txt 2>&1; tail -3 /tmp/e2e.txt
.venv/Scripts/python.exe -m pytest -m "not online and not benchmark" --ignore=tests/test_playwright_e2e.py --ignore=tests/test_e2e_v52_paths.py -q > /tmp/mix.txt 2>&1; tail -3 /tmp/mix.txt
```

## 四、一个能解释当年现象的替代假设（**未证实，仅登记**）

`autosave.py:128` 注册的 `flush_background(5.0)` 会在 **pytest 打完汇总行之后**再阻塞最多 5 秒（等后台保存队列排空）。
如果当时的人是用 **`pytest -q | head -20`** 这类**提前关闭管道**的方式看结果，
`head` 退出让管道关闭，尾行（以及那 5 秒的等待期间任何输出）就可能**看起来"被吞"**——
即问题在**读取方式**而不是 pytest。这与"影响所有『看汇总行』的场景"的描述吻合（人会反复看不到尾行）。
验证：`cd /d/code/psy-analysis && .venv/Scripts/python.exe -m pytest -q 2>&1 | head -20`（应看不到尾行）
vs 落盘后再 `tail`（应看得到）。**本单未跑该验证**（全量重跑一次要 4-5 分钟，留给日间或下一班顺手做）。

## 五、顺带产出的基线数字（供对账引用）

| 指标 | 本次实测（2026-09-19 12:0x） |
|---|---|
| 全量（日常口径，排除 online/e2e/benchmark） | **2859 passed, 1 skipped, 89 deselected, 43 warnings, 0 failed**，277.72s |
| 收集数（本会话早期实测） | 2709 →（本会话补测后）2766 → 本次全量通过数 2859 |
| 对比 9/17 基线报告 | `psy-baseline-recheck-20260917.md` 记 collect **2701**；本次数字比它高 ≈158 条，其中本会话 33 单贡献 ≈230 条断言（部分为同类目） |

## 六、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 报告含复现命令＋二分结论 | 第二/三节（A-D 四条命令与结果、e2e 二分两条待跑命令） | 见文中代码块 |
| `tests/test_error_messages.py -q` 顺带回绿留基线 | **12 passed** in 0.16s（B 组） | `cd /d/code/psy-analysis && .venv/Scripts/python.exe -m pytest tests/test_error_messages.py -q` |
| 只读、不改任何文件（自加门） | 只跑测试与检索；`git status --porcelain tests/ src` 无本单新增（本单产出仅本文件） | `cd /d/code/psy-analysis && git status --porcelain \| grep -c "test_error_messages"` → 0 |

## 遗留问题

1. **e2e 层未验**（第三节），是本单唯一没闭合的面；但两条替代证据（conftest 无钩子、全量汇总行正常）已让"硬退出"猜想基本无立足点。
2. 第四节的管道假设**未跑验证**，只登记不结论——若要结案，一条命令即可。
3. `tests/test_startup_checks.py:19` 在 import 期改全局 `sys.stdout` 编码，虽本次证明无害，
   仍是个传染性的写法（任何同层 import 的模块都会被影响）；建议后续测试文件不要再复制这一行。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
