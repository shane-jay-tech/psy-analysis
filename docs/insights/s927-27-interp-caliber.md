# s927-27 · 全量套件解释器口径基线档（钉桩）

> 生成：2026-09-29T06:0x，班 `qoder-executor-20260929-0600-psy105`，cwd `D:\code\psy-analysis`。
> 位别：**只读／材料位**——本档是新增文档，未改任何代码、未改 README、未改 KNOWN_ISSUES 本体（注记以新档形态给）。
> 上游：`zcode-bridge/done/s922-03-psy-slow-tier.result.md` 遗留 1（「解释器口径没人钉，3336 vs 3347」）。
> **本档所有数字为 2026-09-29 现取**，不抄 s922-03 的旧数（旧数已漂移，见 §5）。

---

## 1. 两把解释器是谁（现点身份）

| | 系统 python | 仓 `.venv` |
|---|---|---|
| 可执行文件 | `D:\Program\python.exe`（`which python` → `/d/Program/python`） | `D:\code\psy-analysis\.venv\Scripts\python.exe` |
| `sys.prefix` | `D:\Program` | `D:\code\psy-analysis\.venv` |
| Python | 3.12.9 | 3.12.9 |
| `include-system-site-packages` | —— | **false**（`.venv/pyvenv.cfg` 现读 ⇒ 两侧包互相独立，不会串读） |
| `pandas.__file__` | `D:\Program\Lib\site-packages\pandas\__init__.py` | `.venv\Lib\site-packages\pandas\__init__.py` |

⇒ 两把解释器是**真隔离的两套包环境**，不是同一 site-packages 的两个入口。

## 2. 依赖面：两侧对 `requirements-lock.txt`（磁盘在途版）的符合度

现取（`importlib.metadata.version`，同一一命令两侧各跑一次）：

| 包 | `.venv` | 系统 python | lock（磁盘） | 谁偏离 lock |
|---|---|---|---|---|
| pandas | 3.0.3 | 3.0.3 | 3.0.3 | 两侧都符 |
| numpy | **2.5.1** | 2.3.5 | 2.3.5 | `.venv` 偏 |
| scipy | 1.18.0 | 1.18.0 | 1.18.0 | 两侧都符 |
| pingouin | 0.6.1 | 0.6.1 | 0.6.1 | 两侧都符 |
| semopy | 2.3.11 | 2.3.11 | 2.3.11 | 两侧都符 |
| scikit-learn | 1.5.2 | **1.9.1** | 1.5.2 | 系统侧偏 |
| streamlit | **1.59.1** | 1.58.0 | 1.58.0 | `.venv` 偏 |
| playwright | **ABSENT** | 1.62.0 | **未 pin** | —— |

两点必须记下：

1. **两侧都不是 lock 的洁净实现**。`.venv` 在 numpy/streamlit 上超前，系统 python 在 scikit-learn 上超前。⇒「用 `.venv` 就等于按 lock 跑」这句**不成立**。
2. **playwright 根本不在 lock 里**。⇒ 浏览器族用例不属于本仓被钉住的依赖面，任何"全量必须含浏览器族"的验收口径都缺一个版本依据（要含它，先得决定 playwright 的钉法）。
3. `requirements-lock.txt` 自身是 ` M` 在途件（HEAD 是 streamlit 1.57.0 / numpy 2.4.4 / scipy 1.17.1），上表按**磁盘现值**比——本班只读未动。

## 3. 收集数差（完成标准 ①，实测）

同一命令两侧各跑一次（`--collect-only`，**未真跑全量**）：

```
$ .venv/Scripts/python.exe -m pytest -p no:randomly --collect-only -q
5567 tests collected in 10.64s          rc=0
$ python -m pytest -p no:randomly --collect-only -q
5578 tests collected in 10.66s          rc=0
```

**差 = 11 条，`comm` 对拍两侧完整 nodeid 清单，差集 100% 落在一个文件**：

```
$ .venv/… --collect-only -q | grep "::" > collected_venv.txt      （5567 行）
$ python -m pytest … --collect-only -q | grep "::" > collected_system.txt   （5578 行）
$ comm -13 <(sort collected_venv.txt) <(sort collected_system.txt)
tests/test_playwright_e2e.py::TestPrivacyAndUpload::test_privacy_modal_dismissible
tests/test_playwright_e2e.py::TestPrivacyAndUpload::test_sidebar_navigation
tests/test_playwright_e2e.py::TestPrivacyAndUpload::test_upload_csv_and_see_column_selector
tests/test_playwright_e2e.py::TestQuestionnaireLLM::test_questionnaire_mode_accessible
tests/test_playwright_e2e.py::TestQuestionnaireLLM::test_text_area_visible_in_questionnaire
tests/test_playwright_e2e.py::TestStreamlitHealth::test_health_endpoint
tests/test_playwright_e2e.py::TestStreamlitHealth::test_main_page_loads
tests/test_playwright_e2e.py::TestStreamlitHealth::test_no_critical_error
tests/test_playwright_e2e.py::TestWorkspaceSaveLoad::test_full_save_load_cycle
tests/test_playwright_e2e.py::TestWorkspaceSaveLoad::test_workspace_load_button_exists
tests/test_playwright_e2e.py::TestWorkspaceSaveLoad::test_workspace_save_button_exists
$ comm -13 … | sed 's/::.*//' | sort | uniq -c
     11 tests/test_playwright_e2e.py
$ comm -23 …        # 反向差集（只在 .venv 有）
（空——无一条用例是 .venv 独有的）
```

**机理**（`tests/test_playwright_e2e.py` 现读）：

```
22:pytestmark = pytest.mark.e2e
24:pytest.importorskip("playwright", reason="playwright 未安装，跳过浏览器 E2E 测试")
```

⇒ 用的是 **`importorskip`（模块级 import 即短路）**，不是 `skipif`。后果是这 11 条在 `.venv` 下**连收集都不发生**——它们不出现在 5567 这个数里，也不会以 SKIPPED 形式出现在报告里。**这是"分母会静默变化"的那一类差，比 skip 更危险**：拿 5567 当基线写"全量 N 例全绿"，换把解释器就变成 5578，两次的"全绿"覆盖的不是同一个集合。

## 4. skip 恢复面（完成标准 ① 的另一半）

浏览器族三件在两侧的**收集面**（现取）：

```
tests/test_playwright_e2e.py                        venv=0   system=11
tests/test_e2e_v52_paths.py                         venv=12  system=12
tests/test_playwright_golden_research_flow.py       venv=28  system=28
```

⇒ 只有 `test_playwright_e2e.py` 受解释器影响；另两件两侧都收得到（它们用 `skipif`/运行时判定，收得到但跑不跑是另一回事）。

标记面（现取）：

```
$ .venv/… -m "e2e or playwright" --collect-only
collected 5567 items / 5542 deselected / 1 skipped / 25 selected
$ python -m pytest … -m "e2e or playwright" --collect-only
collected 5578 items / 5542 deselected / 36 selected
$ .venv/… -m "not (e2e or playwright)" --collect-only
5542/5567 tests collected (25 deselected)
$ python -m pytest … -m "not (e2e or playwright)" --collect-only
5542/5578 tests collected (36 deselected)
```

**`-m "not (e2e or playwright)"` 这个表达式两侧都给 5542** ⇒ 它是当前唯一**跨解释器稳定的分母**（5542 = 两侧共同可跑的非浏览器集合）。

`skipif` 那一族在 `.venv` 下的实际 skip 读数（定向跑，未起任何 server／浏览器，3.60s 完成）：

```
$ .venv/Scripts/python.exe -m pytest -p no:randomly tests/test_playwright_e2e.py \
    tests/test_e2e_v52_paths.py tests/test_playwright_golden_research_flow.py -q -rs
15 passed, 26 skipped in 3.60s
  SKIPPED … Playwright not installed or browsers not available      （test_e2e_v52_paths.py:385）
  SKIPPED ×14 … Playwright not installed                            （test_playwright_golden_research_flow.py:455-568）
```

⇒ `.venv` 下的"恢复面"要分**两个不可互换的口径**（本仓 `KNOWN_ISSUES.md:101` P1「浏览器 E2E」行已按 2026-09-25 复测立过同一勘误，本班现测复核一致）：
- **skip 条目数 = 26** ＝ 25 条逐个用例的 `skipif`（可见、有 reason）＋ **1 条模块级 `Skipped` 记账**
  （`test_playwright_e2e.py` 的 `importorskip`，整件 0 item、**无 nodeid**）；
- **被激活的用例数 = 36** ＝ 25 ＋ 那 1 条模块级记账背后的 **11 例静默不收集**（不可见，这才是钉口径要防的那一处）；
  对平证据：系统侧 `-m "e2e or playwright"` 实测 **36 selected**（§4 上方）。
- ⚠ 别把 26 当用例数、也别把 26＋11=37 当"恢复面"——那是把模块级记账与它所代表的 11 例重复计了一次。

## 5. 对 s922-03 旧数的否证与收窄（按实况改口）

本班现读现跑，旧锚点的两处数值与一处定性**已不成立**，按实况收窄：

| s922-03 的说法 | 2026-09-29 现值 | 判定 |
|---|---|---|
| 收集数 **3336 vs 3347**（`-m "not slow"`） | **5567 vs 5578**（default addopts） | 数值全漂（仓内测试总量涨了两千多条）；**但"差 = 11"这个差值原样复现** |
| `-m "not slow"` 口径 | `pytest.ini` markers 现读**无 `slow`** 注册；`grep -rn "pytest.mark.slow" tests/` 亦零命中 | 旧口径**已不存在**，今天该用 `-m "not (e2e or playwright)"`（§4 实测两侧同为 5542） |
| addopts | 现值 `addopts = --strict-markers`（`-q` 被在途改动摘掉，本班未动） | 本班每条命令**显式补 `-q`**，避免两侧输出体积差干扰读数 |
| 「系统 python 全量有 15 条统计域红，`.venv` 下这些全绿」＝解释器差 | 统计族定向两侧**同读数**（见下） | **否证**：至少在统计域，"两把解释器结论不同"今天**不成立** |

统计域对照（同一批文件、两侧各真跑一次，非 `--collect-only`）：

```
$ .venv/… -m pytest -p no:randomly tests/test_golden_stats_v2.py -q      → 45 passed in 14.91s
$ python -m pytest -p no:randomly tests/test_golden_stats_v2.py -q      → 45 passed in 15.48s
$ .venv/… tests/test_reliability_extended.py tests/test_validity.py tests/test_robustness.py -q
                                                                         → 41 passed in 9.88s
$ python -m pytest …同上三件 -q                                          → 41 passed in 10.08s
```

⇒ s922-03 当年那 15 条统计红是**当时的 sklearn/pandas 版本差**造成的；今天系统侧 sklearn 反而更**新**（1.9.1），`.venv` 侧仍是 lock 钉的 1.5.2，两侧在这批统计用例上**结果一致**。
⚠ 如实标注边界：**本班未跑全量**（班规：399 s 量级＋同刻有兄弟班），所以「全量任何时刻两侧零红差」不成立也不主张——只主张「统计域抽样 86 例无差」＋「收集面差 11 例已定位到单文件」。

## 6. 口径建议（完成标准 ②：全量验收用哪个解释器）

> 这是**材料＋建议**，不是裁决。拍板权在主班／人工。

**主口径（建议）：全量验收固定用 `.venv/Scripts/python.exe`，并把分母钉成 `-m "not (e2e or playwright)"` 的 5542。**

理由（每条都能复算）：

1. **统计口径归 lock 管**：pingouin/semopy/scipy/pandas 两侧同版，唯一参与统计结论的 scikit-learn 只有 `.venv` = lock 的 1.5.2；系统侧 1.9.1 属未经仓内认可的偏移。判分口径类结论应跑在被钉住的那侧。
2. **系统 python 是本机共享件、不受本仓控**：`D:\Program\python.exe` 同时服务 learning/kaoyan/quant 等别的仓（同刻兄弟班在跑），它装什么、什么时候被谁升级，本仓无从固定 ⇒ 拿它当验收基线＝基线在别人手里。
3. **`.venv` 至少是仓内的、可重建的**（`pyvenv.cfg` 现读 `command = D:\Program\python.exe -m venv …`），系统 python 没有这个性质。
4. **分母稳定**：`-m "not (e2e or playwright)"` 两侧同为 5542；裸全量则是 5567/5578 两个数，写"两次绿"必须先声明是哪一个。

**浏览器族单列一班（不进主门禁）**：**36 例**（25 条 skipif ＋ 11 条静默不收集；对应 skip 条目数 26）
用系统 python（唯一有 playwright 的一侧）单独跑一班，并且先解决两件事再谈门禁化：
- playwright **不在 lock 里**（§2）——浏览器结论今天没有任何版本依据；
- 该族在系统 python 下会起 live server 跑浏览器（s922-03 实测单文件 35 s～516 s 量级），塞进门禁会把门禁时长抬高一个数量级。

**必须先补的洞（建议随口径一起做，都是文档/配置面，本班未动）**：

- **洞 A：`importorskip` 的静默不收集没有任何守卫**。今天没有任何一条测试或门禁会红——只是分母从 5578 悄悄变成 5567。建议主班排一枚单，把「两侧收集数差 = 11 且全部来自 `tests/test_playwright_e2e.py`」钉成断言（形如 `collect-only` 两侧对拍），换解释器时立刻红，而不是靠人记得。
- **洞 B：`.venv` 本身对 lock 有 3 处偏移**（numpy 2.5.1 / streamlit 1.59.1 vs lock 2.3.5 / 1.58.0）。⇒ 建议口径落定后，**先按 lock 重建一次 `.venv` 再取全量基线**；否则"钉了解释器"只钉住了包名的来源，没钉住包的版本。此项要动 `requirements-lock.txt`（在途 ` M`）⇒ **本班未碰**。
- **洞 C：`pytest.ini` addopts 现无缺省 `-m` 表达式**（且 `-q` 被在途摘掉）。口径要机读生效就得写进 addopts ⇒ 又撞 `pytest.ini` 在途件 ⇒ **本班未碰**，按 brief §C「撞在途面直接交回、不自创绕法」处理，只把要写的行给出来：
  ```
  - addopts = --strict-markers
  + addopts = --strict-markers -m "not (e2e or playwright)"
  ```

## 7. 复算命令（主班可直接原样跑）

```bash
cd /d/code/psy-analysis
# 收集数与差集（§3，各约 10 s）
.venv/Scripts/python.exe -m pytest -p no:randomly --collect-only -q | grep "::" > /tmp/cv.txt
python            -m pytest -p no:randomly --collect-only -q | grep "::" > /tmp/cs.txt
comm -13 <(sort /tmp/cv.txt) <(sort /tmp/cs.txt)          # 期望：11 行，全在 tests/test_playwright_e2e.py
comm -13 <(sort /tmp/cv.txt) <(sort /tmp/cs.txt) | sed 's/::.*//' | sort | uniq -c
# 稳定分母（§4）
.venv/Scripts/python.exe -m pytest -p no:randomly -m "not (e2e or playwright)" --collect-only -q | tail -1
python            -m pytest -p no:randomly -m "not (e2e or playwright)" --collect-only -q | tail -1
# 版本对 lock（§2）
for P in pandas numpy scipy pingouin semopy scikit-learn streamlit playwright; do
  printf "%-14s venv=%s sys=%s lock=%s\n" "$P" \
    "$(.venv/Scripts/python.exe -c "import importlib.metadata as m
try:print(m.version('$P'))
except Exception:print('ABSENT')")" \
    "$(python -c "import importlib.metadata as m
try:print(m.version('$P'))
except Exception:print('ABSENT')")" \
    "$(grep -iE "^$P==" requirements-lock.txt | sed 's/.*==//')"; done
```

**局限（如实写）**：
- 以上均为**收集数／版本**读数，跑一次就变（测试文件增删即变 5567/5578）——本档的价值在「差 11 落在哪个文件、为什么是静默不收集」，那两条比数字更耐时间。
- §4 的 `15 passed, 26 skipped` 是**定向跑**（三件浏览器文件，3.60s，不起 server），**不是全量**；全量在 `.venv` 下会 skip 多少条，本班未测（班规禁全量）。
- §5 的统计域对照只覆盖 4 个文件 86 例，**不能外推成"全量两侧无差"**。
- 主班复跑这些命令属**同源复算**（同一台机、同一 `.venv`），不构成独立环境验证。

## 8. 零改动自证与安全边界

- `git status --porcelain` 开工 **11** → 收工 **11**，同一集合（全部为他人在途：`app.py`／`pytest.ini`／`requirements-lock.txt`／`src/analysis/{__init__,cfa,result_card}.py`／`src/output/interpretation.py`／`tests/test_cfa_sem_golden.py`／`?? scripts/research_release_gate.py`／`?? src/analysis/_sklearn_compat.py`／`?? docs/insights/s924-36-…md`）。本班**零 git 写、零 add、零 commit**。
- 本班唯一产出＝本档（新增文档）。**未改 README、未改 KNOWN_ISSUES、未改他人档**。
- 文献真库零触碰（跑前＝跑后逐位相同）：`data/literature_feed` **181 件 / 21,059,126 B**。
  守卫 `LITERATURE_FEED_DATA_ROOT` → `tmp/qoder-executor-20260929-0600-psy105/feedroot`，生效反证现取：
  ```
  no-env   DATA_ROOT: D:\code\psy-analysis\data\literature_feed
  with-env DATA_ROOT: D:\code\psy-analysis\tmp\qoder-executor-20260929-0600-psy105\feedroot
  ```
  沙盒目录跑后仍为空 ⇒ 定向跑没有向真库落任何字节。
  ⚠ 该守卫对 **`import src.literature_feed` 这条链无效**（`src/literature_feed/__init__.py:10-18` 在包导入期就把 `paths` 的常量复制进包命名空间）——这正是 s927-66 台账 `test_lr_rerun_apptest.py` 8 errors 的同源机理，本班未修、只留这条交叉注记。
- 红线自查：本档不含统计数值结论、不含隐私医疗内容、不判分口径裁决（§6 明确写成材料＋建议）。
