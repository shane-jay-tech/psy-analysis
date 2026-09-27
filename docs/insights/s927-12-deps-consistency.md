# s927-12 — requirements-lock.txt 在途变更 × `_sklearn_compat.py` 依赖一致性核查（只读·零码改动）

- 班次：`qoder-executor-20260927-1850-psy77`｜波次 24｜cwd `D:\code\psy-analysis`｜HEAD `c7b8623`
- 取证窗口：`date` 18:55 → 19:03 +0800
- 对象：在途 `requirements-lock.txt`（` M`，955 B，mtime 09-26 11:47:36）＋未跟踪 `src/analysis/_sklearn_compat.py`（89 行，mtime 09-25 17:06:43）＋挂钩件 `src/analysis/__init__.py`（` M`，14 行）
- 🔴 授权边界：未改任何码、未装/卸任何包、未联网、未跑 `pip freeze` 再生成、未开 `data/` 库。统计数值域零接触。

## ① 结论（先给判定）

**不一致，且不是"垫片少覆盖几个 API"这一种形状**，而是三件事叠加：

1. **锁的在途改动来自另一枚解释器**——6 行改动值与**全局** `D:\Program\python.exe` 的实装**逐枚相等**，而 `.venv`（psy 唯一授权解释器）里其中 4 枚是别的值。⇒ 该 diff 不是"更新已验证环境"，是"把 PATH 环境抄进了锁"。
2. **垫片防的版本根本不在锁里**——垫片只在 scikit-learn ≥1.6（`force_all_finite` 已删）时有意义，而锁在 HEAD 与工作树两侧都钉 `scikit-learn==1.5.2`（未改），`.venv` 实装也正是 1.5.2 ⇒ 垫片在受支持环境里**永不触发**（`install()` 实测返回 False），它防的是锁外环境。
3. **垫片在生产启动序列里注定晚于消费方绑定**——`factor_analyzer` 在 import 期就 `from sklearn.utils import check_array`，而 app.py 的后台预热线程（`src/ui/heavy_preload.py:17`）会在垫片安装之前把 `factor_analyzer` 拉进 `sys.modules`；本班实测 Case A／Case B 分叉：**同一份垫片，只换导入顺序，一个仍抛 `TypeError: check_array() got an unexpected keyword argument 'force_all_finite'`，一个不抛**，且两种情况下 `install()` 都返回 True（⇒ 返回值不是生效证明）。

⇒ 卷宗给的两个出口里，**"一致"不成立**；下表给"缺覆盖清单"。本班未修任何一条（改计算码／改锁＝超出授权，且锁的取舍是人工闸）。

## ②-A 交叉对照表：锁 diff × 四方版本（20 枚声明包全量）

命令：`.venv/Scripts/python.exe D:/code/tmp/qoder-executor-20260927-1850-psy77/lock_matrix.py`（rc=0，只读，合成 `importlib.metadata` 读数）

| 包 | lock@HEAD | lock@工作树 | `.venv` 实装 | 全局实装 | 在途 diff | 与 .venv | 与全局 |
|---|---|---|---|---|---|---|---|
| streamlit | 1.57.0 | **1.58.0** | 1.59.1 | 1.58.0 | 改 | ❌ 差 0.1 | ✅ 等 |
| pandas | 3.0.3 | 3.0.3 | 3.0.3 | 3.0.3 | — | ✅ | ✅ |
| numpy | 2.4.4 | **2.3.5（降）** | **2.5.1** | 2.3.5 | 改 | ❌ 差 0.2（且比 HEAD 更远） | ✅ 等 |
| scipy | 1.17.1 | **1.18.0** | 1.18.0 | 1.18.0 | 改 | ✅ | ✅ |
| statsmodels | 0.14.6 | 0.14.6 | 0.14.6 | 0.14.6 | — | ✅ | ✅ |
| pingouin | 0.6.1 | 0.6.1 | 0.6.1 | 0.6.1 | — | ✅ | ✅ |
| plotly | 6.7.0 | **6.8.0** | 6.9.0 | 6.8.0 | 改 | ❌ 差 0.1 | ✅ 等 |
| jieba | 0.42.1 | 0.42.1 | 0.42.1 | 0.42.1 | — | ✅ | ✅ |
| openpyxl | 3.1.5 | 3.1.5 | 3.1.5 | 3.1.5 | — | ✅ | ✅ |
| pyreadstat | 1.3.4 | **1.3.5** | 1.3.5 | 1.3.5 | 改 | ✅ | ✅ |
| openai | 2.36.0 | **2.44.0** | 2.45.0 | 2.44.0 | 改 | ❌ 差 1  minor | ✅ 等 |
| python-docx | 1.2.0 | 1.2.0 | 1.2.0 | 1.2.0 | — | ✅ | ✅ |
| fpdf2 | 2.8.7 | 2.8.7 | 2.8.7 | 2.8.7 | — | ✅ | ✅ |
| factor-analyzer | 0.5.1 | 0.5.1 | 0.5.1 | 0.5.1 | — | ✅ | ✅ |
| **scikit-learn** | **1.5.2** | **1.5.2（未改）** | **1.5.2** | **1.9.1** | — | ✅ | ❌ **垫片防的就是这一格** |
| semopy | 2.3.11 | 2.3.11 | 2.3.11 | 2.3.11 | — | ✅ | ✅ |
| PyYAML | 6.0.3 | 6.0.3 | 6.0.3 | 6.0.2 | — | ✅ | ❌ 唯一"锁对 .venv 对、对全局错"的行 |
| kaleido | 1.3.0 | 1.3.0 | 1.3.0 | 1.3.0 | — | ✅ | ✅ |
| pypdf | 6.14.2 | 6.14.2 | 6.14.2 | 6.14.2 | — | ✅ | ✅ |
| pywebview | 6.2.1 | 6.2.1 | 6.2.1 | 6.2.1 | — | ✅ | ✅ |

- 有差的行 **8/20**；`git diff --numstat` → `6 6 requirements-lock.txt`（6 上 6 下，正是表中标"改"的 6 行）。
- **6 行改动 100% 等于全局解释器值**；工作树锁对 `.venv` 仍有 **4 处不符**（streamlit／numpy／plotly／openai），对全局仍有 **2 处不符**（scikit-learn／PyYAML）。脚本末行断言 `WT==global? False`／`WT==venv? False`。
- 文件头自称「以 D:\psy-analysis 当前已验证环境为基准，发版时手动更新」「若冲突先更新 requirements.txt 再 **pip freeze 重新生成本文件**」，且 `最后更新：2026-07-02` **未随本次改动刷新** ⇒ 既不是 `pip freeze` 全量再生成（只动 6 行），也不是以 `.venv` 为基准（4 行反着）。

## ②-B 交叉对照表：sklearn API 面 × 垫片覆盖面

垫片覆盖面**只有一格**：`sklearn.utils.validation.check_array`（＋条件性 rebind `sklearn.utils.check_array` 别名）的 `force_all_finite → ensure_all_finite` 参数改名转发（`_sklearn_compat.py:51-64`）。

| 调用面 | 出处（tracked） | 经不经过 `check_array` | 垫片是否覆盖 |
|---|---|---|---|
| `sklearn.metrics.cohen_kappa_score` | `src/analysis/reliability.py:393`（函数内懒导入） | 否 | N/A（也不需要） |
| `TfidfVectorizer`／`KMeans` | `src/literature_review/themes.py:140-141`（函数内懒导入） | 是（内部会走 `check_array`，但 sklearn 自家调用用**新名**） | 无影响 |
| `import sklearn.cluster` | `src/ui/heavy_preload.py:16`（预热线程） | 否（只导入） | — |
| 依赖名清单／版本读数 | `scripts/generate_system_report.py:144`、`src/utils/env_check.py:88`（`find_spec`＋`importlib.metadata.version`） | 否 | — |
| 🔴 **`factor_analyzer` 的 4 处旧名调用**（垫片的唯一动机） | `.venv/.../factor_analyzer/factor_analyzer.py:630/:759`、`confirmatory_factor_analyzer.py:684/:827`，全部 `check_array(X, force_all_finite=…, estimator=self, copy=True)` | **是** | **名义覆盖，实测受导入顺序支配**（见 ③-1） |
| `factor_analyzer` 的本仓消费点 | `src/analysis/cfa.py:451`（无 semopy 时的简化 CFA）、`src/analysis/cfa.py:572`（semopy 失败后的载荷回退），两处均**懒导入** ⇒ EFA／McDonald ω／CFA 载荷回退三条路径 | 经上行 | 同上 |
| `factor_analyzer` 的**预热线程**消费点 | `src/ui/heavy_preload.py:17 import factor_analyzer`（daemon 线程） | 经 | 🔴 **正是它抢先绑定，把垫片挤成无效** |

## ③ 缺覆盖清单（按可复算强度排序）

1. 🔴 **导入顺序缺口（决定性）**：`src/analysis/__init__.py` 的挂钩只在 `src.analysis` 首次被导入时 `install()`。本班实测 app.py 在 `:155 start_heavy_preload_once()` **之前**的 18 枚可独立导入顶层依赖件（`src.data.loader`／`src.ui.quick_entries`／`src.ui.pages.privacy_gate`／`src.utils.pipeline_manager`／`src.ui.app_pages_text`／`src.ui.accessibility`／`src.ui.design_system`／`src.utils.autosave`／`src.ui.project_panel`／`src.utils.memory_manager`／`src.utils.guardrails`／`src.utils.archive_manager`／`src.utils.env_check`／`src.ui.navigation`／`src.ui.startup_checks`／`src.ui.heavy_preload`／`src.ui.onboarding`／`src.utils.i18n`／`src.utils.usage_hooks`）逐枚 `importlib.import_module` 后 **`'src.analysis' in sys.modules` 全为 False**；而 app.py 里 `src.analysis` 的首次出现是 **`:741`（函数内懒导入）**。⇒ 预热线程（`:17 import factor_analyzer`）在垫片之前完成 `from sklearn.utils import check_array` 绑定，Case A 成立。
   - 该缺口**与在途 app.py diff 无关**：HEAD 的内联版预热块（`git show HEAD:app.py` :167/:181-184）同样在线程里 import `factor_analyzer`，`src.analysis` 同样懒 ⇒ 属既有次序，垫片未解决它。
2. **`install()` 的布尔返回不是生效证明**：Case A 里 `install() -> True`、`_PATCHED -> True`，调用却仍 `TypeError`（复算 ② 脚本）。挂钩整体被 `except Exception: pass` 包住（`__init__.py:8-13`）⇒ 真失效时既不变红也不留痕（`s927-08` §2.2 已登记为"绿但零覆盖"形态，本单给出机理性成因）。
3. **锁与垫片互不相认**：锁两侧都钉 `scikit-learn==1.5.2`（旧名仍受支持），垫片防的是 ≥1.6 的删除；而 `_sklearn_compat.py:12` 自己写着「正解是锁定经测试的 sklearn/factor_analyzer 版本组合」——**这条正解没被执行**（没有任何一处把"锁内 sklearn 版本"与"垫片触发条件"对齐，也没有 `requirements.txt` 侧的对应改动：本次 diff 只碰 lock 一个文件）。
4. **锁的 numpy／scipy 变更零兼容层、零断言**：
   - numpy `2.4.4→2.3.5`（**降级**，且 `.venv` 实装 2.5.1）：本班扫 `src/`＋`app.py` 的 numpy 属性面 = **402 处 `np.*`**，去重后 40 个属性（`arctanh`／`isfinite`／`percentile`／`polyfit`／`linalg`…），**无 1.24 已删别名**（正则 `np\.(float|int|bool|object)(?![A-Za-z0-9_])` → NONE），故 API 面看不出错；风险全在"锁≠实装"这一事实，而**仓内没有任何一处校验二者一致**（`git grep requirements-lock -- '*.py'` 只命中 3 枚测试里的**注释**）。
   - ⚠ 连带后果：`tests/test_cfa_sem_golden.py:173` 把「按 `requirements-lock.txt` 复原版本后重跑」写成在册**出口** ⇒ 照该出口执行会按现在这份锁把 `.venv` 的 numpy 从 2.5.1 换成 2.3.5（外加 streamlit/plotly/openai 三处降级），**在册出口被这份在途锁反向污染**。这是本班认为"暂不建议提交"的核心理由（`s927-08` §4 C9）。
   - scipy `1.17.1→1.18.0`：与两枚解释器都相等（唯一"改完就一致"的一行），但 scipy 经 pingouin／statsmodels／semopy 三间接面，无版本断言护航。
5. **三处口径互斥，待人工择一**：① `scripts/run_daily_feed.bat:24-27`（已入库，s923-11）＝"钉解释器到 .venv，因为 1.5.2 vs 1.9.1 不同版"；② `_sklearn_compat.py`（未跟踪）＝"给 PATH 解释器补参数改名"；③ 本次锁 diff＝"把 PATH 解释器的版本值写进交付锁"。三者不能同时成立——**受支持环境到底定义为 `.venv` 还是 PATH 环境**，是这单的真问题（数值与交付口径，归人工拍）。

## ④ 零码改动自证

- 未改：`requirements-lock.txt`（收班复点 955 B／mtime 09-26 11:47:36 未变）、`_sklearn_compat.py`、`src/analysis/__init__.py`、任何 `src/` 计算码、任何 golden 快照、任何 `expected_*_cards.json` 期望数据。
- 零 git 写操作：未 add／commit／stash／checkout／restore／clean／push；**原始 12 枚在途件（8 ` M`＋4 `??`）逐件未变**；收班时 `git status --porcelain` ＝ **15 行**＝原 12 枚＋本波三张卷宗的产物 `docs/insights/s927-08-dirty-audit.md`／`s927-09-knownissues-health.md`／`s927-12-deps-consistency.md`（未跟踪，交主班代提交）。
- 未装未卸任何包（brief 禁下载安装依赖）；未联网；`pip freeze` 一次未跑（跑它只读但会诱导"再生成锁"，故不跑）。
- `data/` 零写：本单只跑 `importlib.metadata` 与合成 DataFrame 探针，未开任何库；全树复核 **187 枚／21,103,172 B**，最大 mtime 仍是 `data/literature_feed/feed.sqlite-shm @2026-09-27 09:30:01`（早于本班开窗）。
- 唯一可能的进程级副作用已排除：Case A/B 探针用**全局解释器**导入 `src.analysis`，两枚解释器同为 **3.12.9** ⇒ `.pyc` 文件名相同，但源码 mtime 未变 ⇒ 缓存头命中、不重写。实测跑后 `ls -lt src/analysis/__pycache__`（33 枚）最新条目仍是 **09-26 11:51 的 `cfa.cpython-312.pyc`**、`__init__.cpython-312.pyc` 仍 09-26 11:47 ⇒ **本班未改动任何字节码**（该目录本就 gitignore）。

## ⑤ 复算入口（本班留档，故不清理）

- `D:\code\tmp\qoder-executor-20260927-1850-psy77\lock_matrix.py` — ②-A 全表（20 包四方对照）；`.venv` 解释器起，内部 subprocess 显式 `encoding='utf-8'`、标签 ASCII。
- `D:\code\tmp\qoder-executor-20260927-1850-psy77\order_probe.py` — ③-1 的 Case A／B 分叉；**必须用全局解释器跑**（`D:/Program/python.exe`，sklearn 1.9.1），输入为合成 60×6 正态 DataFrame，只打印是否 `TypeError`，不打印任何统计量。
- `D:\code\tmp\qoder-executor-20260927-1850-psy77\sk_probe.py` — s927-08 §2.2 的垫片状态读数（同批产物，见 `s927-08-dirty-audit.md` §7）。
- 版本面：`git show HEAD:requirements-lock.txt` 由脚本内部完成，未落盘任何副本。
