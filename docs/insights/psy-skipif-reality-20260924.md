# psy `skipif` 依赖实况对账：kaleido／playwright 已装画像＋`socratic_quality` 死件裁决

> 班名 `qoder-executor-20260925-0800-psy58` ｜ 单号 s924-71 ｜ 取数 2026-09-25 08:18–08:28 ｜ cwd `D:\code\psy-analysis` ｜ HEAD `928e62e`（现取）
> **只读单**：零代码／配置改动，零 `data/` 改动，未 `git add`／commit，未 `pip install`，未跑全量执行套（只跑卷宗点名的 3 个件＋一次 `-m e2e` 的 skip 读数）。
> 解释器一律 `.venv\Scripts\python.exe`（Python 3.12.9 ＋ pytest-9.1.1）；全局 python 只作**对照**用（见 §一 的那条否证）。

## 〇、结论先给（三句话）

1. 🔴 **卷宗前提"playwright 已装"被否证**：`find_spec("playwright")` 在 **`.venv` 里 MISSING**，只在**全局 `D:\Program\python.exe`** 里 FOUND。⇒ 按仓内口径跑，**25 个 e2e 用例全部 skip，全量跑一个真浏览器都不会起**（实测 `26 skipped in 0.15s`）。
2. 🔴 **卷宗前提"`test_socratic_quality` 恒 skip 因 `:59` 环境变量"也被否证**：`:59` 在默认跑法下**根本到不了**——先被 `tests/conftest.py:65-72` 的 `--run-benchmark` 门禁在收集期跳掉；而且被跳的是**整件 3 例**（`:22` 模块级 `pytestmark`），不只是联网那 1 例。加 `--run-benchmark` 实测 **2 passed / 1 skipped** ⇒ 有 **2 例零风险本地用例被默认门控误伤**。
3. ✅ **kaleido 族"如今真跑"成立且全绿**：`test_paper_export.py`＋`test_docx_export.py` 定向实跑 **24 passed / 12.49s / rc=0，0 skip**，含 3 个真渲染 smoke（5.40s／2.30s／2.14s）。但**渲染后端其实是系统 Edge**，而 skipif 判的是"kaleido 这个包在不在"——**门禁与真依赖不是同一件事**（§二.3）。

---

## 一、五依赖"已装"画像（`find_spec` ＋ 真 `import` ＋ 版本，双解释器对照）

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys,importlib.util,importlib
print('exe',sys.executable,'ver',sys.version.split()[0])
for m in ['kaleido','PIL','plotly','fpdf','playwright']:
    s=importlib.util.find_spec(m); print('FIND_SPEC',m,'FOUND' if s else 'MISSING',getattr(s,'origin',None))
    try:
        mod=importlib.import_module(m); print('IMPORT',m,'ok ver',getattr(mod,'__version__','(no __version__)'))
    except Exception as e: print('IMPORT',m,'FAIL',type(e).__name__,e)"
```

| 依赖 | `.venv`（仓内口径，权威） | 全局 `D:\Program\python.exe`（对照） | 版本读数（.venv） |
|---|---|---|---|
| `kaleido` | **FOUND** | FOUND | `1.3.0`（`pip show kaleido`；包内**无** `__version__` 属性） |
| `PIL` | **FOUND** | FOUND | `12.3.0` |
| `plotly` | **FOUND** | FOUND | `6.9.0` |
| `fpdf` | **FOUND** | FOUND | `2.8.7` |
| `playwright` | 🔴 **MISSING**（`ModuleNotFoundError`） | FOUND | — |

⇒ 卷宗说"venv：kaleido/PIL/plotly/fpdf/playwright **全装**"——**4/5 中，1/5 否**。
🔴 **这正是纪律档 §七"psy 必须用 `.venv` 解释器"的同族陷阱**：拿全局 python 探依赖会读出"playwright 已装"，进而误判"全量跑会启动真浏览器"。**"已装"一律以 `.venv` 里的实际 import 为准。**

**环境变量判定（第三类证据）**：
```
$ PYTHONIOENCODING=utf-8 python -c "
import os
for k in ['BENCHMARK_LLM_API_KEY','DEEPSEEK_API_KEY','LITERATURE_FEED_DATA_ROOT','KAOYAN_DB_PATH']:
    v=os.environ.get(k); print(k,'=','<UNSET>' if v is None else '<SET>')"
BENCHMARK_LLM_API_KEY = <UNSET>     DEEPSEEK_API_KEY = <UNSET>
LITERATURE_FEED_DATA_ROOT = <UNSET> KAOYAN_DB_PATH = <UNSET>
```
且仓内只有 `.env.example`（1,565 B，09-19 19:12）、**无 `.env`** ⇒ 无"从文件里悄悄加载 key"的形态。`BENCHMARK_LLM_API_KEY` 的读取点唯一：`tests/test_socratic_quality.py:48 os.environ.get(...)`。

**锚点复核（三锚零漂移）**：`tests/test_paper_export.py:107` `@pytest.mark.skipif(` ＋ `:108 importlib.util.find_spec("kaleido") is None` ✅｜`tests/test_socratic_quality.py:59 pytest.skip("未设置 BENCHMARK_LLM_API_KEY 环境变量")` ✅｜`tests/test_playwright_golden_research_flow.py:450 @pytest.mark.skipif(not E2E_AVAILABLE, reason="Playwright not installed")` ✅。

---

## 二、kaleido 族实跑（完成标准②的内联数）

### 1. 总数与红绿
```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_paper_export.py tests/test_docx_export.py -v -rs --durations=12
============================= 24 passed in 12.49s ==============================     rc=0
```
**24 passed / 0 failed / 0 skipped / 12.49s，rc=0**（＝`test_paper_export.py` 11 例 ＋ `test_docx_export.py` 13 例，与逐件 `def test_` 清点同值）。`-rs` 输出**没有任何 SKIPPED 行** ⇒ **skipif 族确实不再 skip，3 个真渲染用例全部被执行**。

### 2. 三个 smoke 的耗时（它们就是"当年会被 skip、今天真跑"的那三例）
| 用例 | 判定链 | 耗时 | 结果 |
|---|---|---|---|
| `test_paper_export.py::test_export_zip_smoke` | `:107-110 skipif(find_spec('kaleido') is None)` | **5.40s call** | PASSED |
| `test_paper_export.py::test_to_paper_png_smoke` | `:132-135` 同款 | **2.30s call** | PASSED |
| `test_docx_export.py::test_plotly_figs_to_figure_items_smoke` | `:136-141 _kaleido_installed()`→`skipif(not …)` | **2.14s call** | PASSED |
| 对照：`test_paper_export.py::test_to_paper_png_raises_friendly_error_when_kaleido_missing`（`:69`） | 用 `monkeypatch.setattr(pe,"_kaleido_available",lambda:False)` **模拟缺失** | <0.04s | PASSED |
| 对照：`…::test_export_zip_returns_zip_with_description_when_kaleido_missing`（`:79`） | 同上 | <0.04s | PASSED |
| 对照：`test_docx_export.py::…_handles_missing_kaleido`（`:124`） | 同上 | <0.04s | PASSED |

⇒ 画像结论：**同一个函数有"缺失分支"与"齐备分支"两条用例，且两条同时在场**——缺失分支靠 monkeypatch 恒定覆盖，齐备分支靠 `find_spec`。所以"kaleido 装了会不会漏测"不成立；**反过来**（换一台没装 kaleido 的机器）才会只剩 3 例 skip。

### 3. 🔴 门禁与真依赖不同件：渲染后端其实是 **Edge**
`kaleido 1.3.0` 不自带 Chromium（`find .venv -iname "chrome*.exe"` → 零命中），且**缺浏览器时是抛错、不是自动下载**——源码直证：`.venv/Lib/site-packages/choreographer/browsers/chromium.py:175-183`，`find_browser()` 取不到路径就 `raise ChromeNotFoundError("Browser not found. You can use get_chrome() or choreo_get_chrome from bash…")`，即**下载是 CLI 手动动作**（`choreographer/cli/`），渲染路径里不会发生。旁证：本机 `AppData/Local/{Chromium,Google/Chrome}`、`~/.cache/choreographer` **全部不存在**，跑完 30 分钟内 `.venv/…/choreographer/` 零文件被修改。缺浏览器时报错文本见 `chromium.py:52` 的 `ChromeNotFoundError(RuntimeError)`。那它是怎么渲染成功的？
```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
from choreographer.browsers.chromium import Chromium
print(Chromium.find_browser(skip_local=True, skip_typical=False))"
C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
```
⇒ **真依赖＝"系统里有 Chromium 系浏览器"**，而 `skipif` 判的是"python 包 `kaleido` 在不在"。本机 Edge 在册 ⇒ 三例绿。**若换一台既无 Edge 也无 Chrome 的机器（CI 即此形态：本仓 `.github/workflows` 不存在，实测 `ls` → No such file），这三例会以 `ChromeNotFoundError` 红，而不是 skip。**
登记为**门禁口径缺陷**（本单只登记不修）：`find_spec("kaleido")` 应升级为"kaleido 可解析到可用浏览器"的探针。

### 4. 本班这次实跑的副作用面（判据"零改动"的自证）
- 三例渲染都返回 **bytes**（`test_to_paper_png_smoke` 断言非空 PNG bytes），**未落盘图片**。
- 跑后复点：`git status --porcelain` 无本班新脏件；`data/` 全树 187 条目 **ADDED 0／CHANGED 0／REMOVED 0**，不变量 `data/literature_feed` **181 件 / 21,059,126 B** 逐位未变。
- `.pytest_cache/` 被 `.gitignore:6` 忽略 ⇒ pytest 跑动不污染 `git status`（先 `git check-ignore -v .pytest_cache` 自证）。

---

## 三、e2e 画像：全量跑到底含不含浏览器用例？

### 1. 收集面读数（卷宗点名的命令）
```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q --collect-only -m e2e
25/5296 tests collected (5271 deselected) in 11.28s        rc=0
```
**25 例带 e2e 标记**（全量收集 5,296 例）＝`test_e2e_v52_paths.py` 12 ＋ `test_playwright_golden_research_flow.py::TestBrowserGoldenPath` 13。第三个 e2e 件 `test_playwright_e2e.py` **贡献 0 例**（见 §三.2）。
⚠️ 顺带登记一条陈旧：口径单源 `docs/TESTING.md:36` 在册"`.venv` collect = **2665 collected / 0 failed**"，现取 **5296**（≈2 倍）。本班**不跑全量执行**（只读位纪律），故只交 collect 口径、不交 passed 口径；该档自己写了"引用前请现跑一次"。

### 2. 三件的门禁形态各不相同（这决定了"会不会起浏览器"）
| 件 | 门禁 | 今日实况 |
|---|---|---|
| `test_e2e_v52_paths.py`（12 例） | 模块级 `pytestmark=[playwright, e2e, skipif(not _playwright_available())]`（`:32-39`；`_playwright_available()` 在 `:23-28` try-import） | 12 例**全 skip** |
| `test_playwright_golden_research_flow.py`（28 例＝15 非 e2e ＋ 13 e2e） | 类级 `:450 skipif(not E2E_AVAILABLE)` ＋ `:451 @pytest.mark.e2e`；**另有第二层**：`browser` fixture `:401-402 if not E2E_AVAILABLE: pytest.skip(...)` | 13 例**全 skip**（15 例离线项被 `-m e2e` deselected） |
| `test_playwright_e2e.py`（313 行） | 🔴 `:24 pytest.importorskip("playwright")` ⇒ **模块期就整件跳**，收集 **0 例** | 单件跑 `rc=5`（"no tests collected"）；套件里算 1 条 collection-skip |
> `E2E_AVAILABLE` 定义在 `:23-28`（try-import `playwright.sync_api`）⇒ venv 下为 **False**。
> `test_playwright_e2e.py` 是纪律档 §十三.17"绿但零覆盖"形态的**第三例**（前有 `test_llm_engine.py` 收集 0 例／rc=5）：它有 3 条真实路径设计，但**在本仓口径下永远不被收集**，`pytest.ini` 也无从报错（`--strict-markers` 只管标记注册）。

### 3. 执行面读数（skip 不是 fail，用 `-rs` 交叉）
```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_e2e_v52_paths.py tests/test_playwright_e2e.py tests/test_playwright_golden_research_flow.py -m e2e -rs
===================== 26 skipped, 15 deselected in 0.15s =====================      rc=0
SKIPPED […] tests\test_playwright_golden_research_flow.py:455: Playwright not installed   （…到 :568 共 13 行）
```
**26 skipped ＝ 25 用例 ＋ 1 条模块级（`importorskip`）**；耗时 **0.15s** ⇒ 物理上不可能起过浏览器或 Streamlit 子进程。

### 4. 若真按文档装了 playwright，会是什么行为（口径画像的关键一环）
两个件**自带拉起真 app** 的 fixture，不是"连既有 app"型：
- `test_playwright_e2e.py:34-37 subprocess.Popen(["streamlit","run",APP_FILE,"--server.port","8501","--server.headless","true"])`
- `test_e2e_v52_paths.py:67-68` 同型（`BASE_URL="http://localhost:8501"`）
- `test_playwright_golden_research_flow.py:382 def streamlit_server()` → `:399 def browser(streamlit_server)` → `p.chromium.launch(headless=True)`（`:404`）
⇒ **一旦 venv 装上 playwright，全量跑会拉起 streamlit 子进程＋Chromium**（并可能在失败时往 `SCREENSHOT_DIR`/`TRACE_DIR` 写图与 trace，见 `:417-422`、`docs/TESTING.md:115`）。安装动作本身是文档规定的显式步骤：`docs/TESTING.md:92-95`（`.venv\Scripts\pip.exe install playwright pytest-playwright` ＋ `.venv\Scripts\playwright.exe install chromium`）——**本班未装**（属"禁止下载安装依赖"红线）。

### 5. 现行调用口径（README／脚本怎么跑全量）
| 入口 | 命令 | 含 e2e？ |
|---|---|---|
| `README.md:81` | `.\.venv\Scripts\python.exe -m pytest` | 收集含（25 例），执行全 skip |
| `docs/TESTING.md:18`（推荐日常） | `pytest -m "not online and not e2e and not benchmark" -q` | **显式排除** |
| `docs/TESTING.md:45`（全量离线） | `pytest -q`；`:57` 另一形 `-m "not online and not benchmark"` | 前者含、后者含 e2e 面 |
| `scripts/release_gate.py:19,50-54` | `PYTHON=.venv\Scripts\python.exe`；`pytest --ignore=tests/test_online_fetchers.py --tb=no`（timeout 600） | **含 e2e 面**（无 `-m` 排除） |
| `docs/TESTING.md:108` | `pytest -m e2e -v` | 专跑 e2e（今日读数＝全 skip） |
- 🔴 `pytest.ini` 侧确认：`addopts = --strict-markers`（工作树）**未**排除 e2e；HEAD 态是 `--strict-markers -q`。差异只是 `-q`——⚠️ **该文件此刻被兄弟班改脏**（`git diff --numstat -- pytest.ini` = **1/1**，在册 7 项脏件之一），本班读的是工作树现值。
- **CI 面**：`.github/workflows` 目录不存在 ⇒ 这三例 kaleido smoke **没有任何自动环境**替我们踩"没浏览器"的雷。

### 6. ③号完成标准的明确结论
**全量跑"包含"浏览器用例的收集面（25 例，占 5,296 的 0.47%），但在本机 `.venv` 口径下不执行任何一个（26 skipped／0.15s／rc=0）——不起真浏览器、不拉 streamlit。** 卷宗"全套跑会启动真浏览器"的前提在**权威解释器**下不成立；它只在**全局 python**（playwright 在册）下成立，而那个解释器同时带 sklearn 1.9.1 vs `.venv` 1.5.2 的版本错配（纪律档 §七：~30 条假红）⇒ **不构成可用的执行口径**。

---

## 四、`test_socratic_quality.py` 死件裁决

### 1. 实况：两层门禁，`-rs` 读数把因果钉死
```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_socratic_quality.py -v -rs
3 skipped in 0.05s                                   rc=0
SKIPPED [1] tests\test_socratic_quality.py:54: 需要 --run-benchmark 才运行（默认跳过）
SKIPPED [1] tests\test_socratic_quality.py:   需要 --run-benchmark 才运行（默认跳过）      ← 无行号＝模块级 pytestmark 所为
SKIPPED [1] tests\test_socratic_quality.py:153: 需要 --run-benchmark 才运行（默认跳过）

$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_socratic_quality.py -v -rs --run-benchmark
2 passed, 1 skipped in 1.09s                         rc=0
SKIPPED [1] tests\test_socratic_quality.py:59: 未设置 BENCHMARK_LLM_API_KEY 环境变量
```
| 用例 | 默认跑 | `--run-benchmark` | 真依赖 |
|---|---|---|---|
| `:55 test_socratic_quality_benchmark` | SKIPPED（conftest 门禁） | SKIPPED（`:59` env） | 真 LLM ＋ 联网 ＋ key |
| `:118 test_benchmark_fixture_loadable` | **SKIPPED（被误伤）** | **PASSED** | 纯本地读 fixture，零风险 |
| `:154 test_socratic_quality_replay_offline` | **SKIPPED（被误伤）** | **PASSED** | 纯本地读 golden 报告，零风险（内部 `:156 monkeypatch.delenv(BENCHMARK_LLM_API_KEY)` 正是为"强制走离线回放"而写） |

**因果订正**：卷宗把"恒 skip"归给 `:59` 的 env 判定。实况是 **`tests/conftest.py:65-72 pytest_collection_modifyitems`**（未传 `--run-benchmark` 就给所有带 `benchmark` 关键字的 item 挂 skip）先动手，`:59` 在默认跑法下**不可达**；而 `:22 pytestmark = pytest.mark.benchmark` 是**模块级**的 ⇒ 门禁覆盖**整件 3 例**。

### 2. 解门是不是"白送 2 例绿"？—— 已验，是
`test_socratic_quality_replay_offline` 依赖 golden 报告在场（`:146-147 assert reports, "无 golden 回放报告…"`）。实测：
```
$ ls -la tests/fixtures/_benchmark_reports/
-rw-r--r-- 1 … 14643 Sep 10 03:19 benchmark_20260910_031938.json
```
⇒ 唯一一份 golden 在盘（09-10 03:19），解门后两例**实测 PASSED**，不会新增红。

### 3. 裁决：**既不是"依赖环境变量属设计"，也不是"移 manual 标记"——是"门禁作用域开错层级"**
- 对 `:55` 那一例：**"依赖环境变量属设计"成立**，留档即可——它要真 key、真联网、真 LLM-as-judge，默认跳过是正确纪律（也与本仓 `online`/`benchmark` 标记的语义一致，见 `docs/TESTING.md:10-12`"月度/季度"）。
- 对 `:118`／`:154` 两例：**不成立**。它们不需要 key、不联网，却因 `:22` 的**模块级** `pytestmark` 与 `conftest:65-72` 一起被默认门控 ⇒ 这才是"事实上的死件"部分，且是**可以零成本救活**的（加 flag 已实测 2 passed）。
- 🔴 **不建议"移 manual 标记"**：那会把两例**永久排除**在执行面之外，方向与"救活"相反；而"移 manual"通常用于"必须人肉判断"的用例，本件这两例是纯断言式本地校验，不该 manual。
- **建议改法（属执行面改动，超本单只读授权 ⇒ 交主班派单）**：把 `:22` 的模块级 `pytestmark` 摘掉，只在 `:55`（必要时 `:153`）保留 `@pytest.mark.benchmark`。
  ⚠️ 连带影响必须一并交代：这会令 `.venv` 全量口径 **+2 passed / −2 skipped**（`docs/TESTING.md:34` 的在册数需同笔重取），且 `conftest:69` 那句"默认跳过"的语义范围随之收窄——这是**改执行面计数**，按纪律档 §五.4 的口径应留人工确认，本班不动。
- 附带一条同族隐患（登记不修）：`:55` 那例一旦有 key 就会**往 `tests/fixtures/_benchmark_reports/` 写新报告**（`:94 report_path`）⇒ "跑基准"是会改仓内 fixture 目录的动作，月度跑之前应确认那目录的入库期望。

---

## 五、复跑配方（三类证据一次跑齐，全部只读）

```
$ cd /d/code/psy-analysis
$ # (1) 五依赖画像 —— 必带 .venv，别用全局
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import importlib.util as u;[print(m,'FOUND' if u.find_spec(m) else 'MISSING') for m in ['kaleido','PIL','plotly','fpdf','playwright']]"
$ # (2) 环境变量空判定
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import os;print('BENCHMARK_LLM_API_KEY', 'UNSET' if not os.environ.get('BENCHMARK_LLM_API_KEY') else 'SET')"
$ # (3) e2e 收集计数
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q --collect-only -m e2e | tail -1
$ # (4) kaleido 族实跑
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_paper_export.py tests/test_docx_export.py -rs --durations=12
$ # (5) socratic 两层门禁交叉
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_socratic_quality.py -rs
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_socratic_quality.py -rs --run-benchmark
```
现值（2026-09-25 08:2x）：`playwright MISSING`／其余 4 项 FOUND｜key `UNSET`｜`25/5296 collected`｜`24 passed in 12.49s`｜`3 skipped in 0.05s` → `2 passed, 1 skipped in 1.09s`。
