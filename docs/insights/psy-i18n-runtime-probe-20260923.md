# psy i18n `t()` 运行期 key 直方图探针（24 悬置键取证）· s923-17 · 2026-09-23

> **性质：只读取证。** `src/` 零改动（`git status --porcelain src/` 空输出），
> 探针件全在 `tmp/`（`.gitignore:29 tmp/` 覆盖，`git check-ignore -v` 实测两枚产出件均被忽略）。
> 需求出处：`zcode-bridge/done/s922-21-psy-i18n-coverage.result.md:114`
> 「动态通道是死词条判定的唯一不确定性：`t()` 的 3 个非字面量调用点使 24 个键「可能活但看不见」。
> 若将来要以此清单为删除依据，**必须先补运行期探针**（在 `t()` 里记录 key 直方图跑一轮全 UI），静态扫描不足以支撑删键。」

## 〇、锚点复核

| 任务书前提 | 实测 | 判定 |
|---|---|---|
| `src/utils/i18n.py:249 def t(key: str, lang: str = None) -> str:` | `sed -n '249p'` 逐字相符 | ✅ 零漂移 |
| `tests/test_i18n.py:112` 钉 106 键总数 | 该行现为 `assert len(TRANSLATIONS["zh"]) == 106`（行号在 `:112`，与 `s922-21` 引的 `:110-113` 同一条）；盘上实测 `len(TRANSLATIONS["zh"])==106` | ✅ |
| 「24 个悬置键」 | 现场重算（不抄上游）：`dead = 106 键 − 11 个 UI 字面量键`，`pending = dead ∩ set(TEST_NAMES_ZH)` → **恰 24**，逐键名单见第三节 | ✅ |
| 上游未说但影响判定的一个新事实 | 48 个 `TEST_NAMES_ZH` 键里 **只有 24 个在 106 表内**，另外 24 个（`ai_item_review / ancova / ave / binary_logistic / cronbach_alpha / cvi / hlm / icc / manova / sem …`）**运行时查表必然未命中**，由 `config/settings.py:72` 回落 `TEST_NAMES_ZH` | ⚠ 见第四节 F3 |

## 一、探针怎么装（以及为什么不能更简单）

`tmp/i18n_key_probe_s923.py` **不 monkeypatch `t`，而是替换 `i18n.TRANSLATIONS` 为"会记账的 dict 子类"**。
理由（本单最值得留的一条坑）：`t` 被 4 个生产模块按 `from src.utils.i18n import t` 绑进自己的命名空间
（`app.py:40`、`config/settings.py:4`、`src/ui/paper_writing_ui.py:24`、`src/ui/questionnaire_panel.py:19`）。
只 patch `i18n.t` ⇒ 已绑定的引用仍指向原函数，直方图会**近乎全空**，从而把"探针没装上"读成"UI 一个键都不用"——
一个假绿结论。而 `t()` 的取键实现是 `TRANSLATIONS.get(lang, …).get(key, key)`（`i18n.py:266`），
换掉模块全局对象即截获**所有调用方、与 import 写法无关**。

探针鉴别力自证（不通过就 rc=4/5 退出，不出报告）：

- `selftest`：装完立刻 `t("descriptive")`、`get_test_name_zh("welch_anova")`，断言两键已入账。
- `PROBE_ERRORS`：记账器内的异常**不再 `except: pass`**。首版正是这么写的——`code.co_lineno` 拼错
  （code 对象无此属性）⇒ 每条记账抛异常被吞、`SITES/TIERS` 全空、读数"命中 0/106"而退出码 0。
  这就是纪律档说的**静默失明的绿**，本档把它钉在源码注释里。
- `if not TIERS: return 5`：空直方图一律判探针失效，不许当观测结果。

层级（tier）标注：`ui:pytest-e2e`（在册 e2e 套件驱动的 UI 流）／`ui:analyze`、`ui:<模式>:<语言>`（自造 harness）／
`capability`（直接调 `get_test_name()` 的能力探针，**故意不算 UI 命中**）。三档分账是为了不让"我调了它"冒充"UI 到了它"。

## 二、运行期读数（2026-09-23T12:0x 现取，rc=0）

```
A0 在册 pytest harness：tests/test_e2e_ui.py + tests/test_e2e_rendering.py → 21 passed / rc=0 / 8.99s
命中表内键 5 / 106   （(key,lang) 明细 28 条）   运行期出现但表里没有的键：0
t() 的实际调用站点（去重）：
   src/ui/settings_sidebar_panel.py:28  render_settings_sidebar_panel   → key "language"
   src/ui/settings_sidebar_panel.py:32  <lambda>                        → key "chinese" / "english"
   config/settings.py:71                get_test_name                   → 各统计方法键
21 passed 的在册 harness 里只出现 4 键：language / chinese / english / descriptive
（第 5 键 independent_ttest 来自 A3 自造分析流，见第五节）
en 语言表在 A0 里 0 次查询（全库唯一 |en| 记录是 independent_ttest|en，来自自造 harness）
```

## 三、24 悬置键逐键判定

| # | 键 | 判定 | 依据（站点/层级） |
|---|---|---|---|
| 1 | `descriptive` | **活** | `ui:pytest-e2e` 实际命中（`settings.py:71`，3 次）；上传 CSV→"对 score 做描述统计"→点分析即触发 |
| 2 | `independent_ttest` | **活（中等强度）** | `ui:analyze` 命中（`settings.py:71`）；但同一条流在 `app.py:1417` 崩溃（第五节），且 A0 未覆盖 ⇒ 证据链不如 `descriptive` 干净 |
| 3-24 | `cfa` `chi_square_gof` `chi_square_independence` `efa` `friedman` `hierarchical_regression` `kruskal_wallis` `linear_regression` `mann_whitney` `mediation` `moderation` `multiple_regression` `one_sample_ttest` `one_way_anova` `paired_ttest` `partial_corr` `pearson_corr` `repeated_anova` `spearman_corr` `two_way_anova` `welch_anova` `wilcoxon` | **结构可达 · 本轮 UI 未触发**（22 键） | 唯一入口是 `config/settings.py:71`；本轮只在 `capability` 层被直接调用命中。**既不能判活也不能判死** |
| — | （空） | **未见** 0 键 | 无一键是"能力探针也打不到"的孤立词条 |

⇒ **对 s922-21 的直接影响：那 71 个净死词条的删除依据不是变强了，而是变弱了。**
原判定"95/106 是死词条"的前提是"运行期真用不到的概率高"；探针跑完，`t()` 的**全部**运行期入口
只有 3 个站点、在册 harness 只命中 4 键 ⇒ 连"静态认定的 11 个 UI 活键"里都有 8 个（`title/abstract/keywords/
introduction/methods/results/discussion/references`，`src/ui/paper_writing_ui.py:27-34`）**在本轮从未被调用**
——因为 e2e 套件不点论文写作页。所以"活键 11"是**静态可达性**读数，不是运行期证据；
拿它当删除依据仍然不成立，24 悬置键里 22 个维持"可能活但看不见"。

## 四、三条新事实（静态扫描给不出来的）

- **F1 · `t()` 的运行期入口只有 3 个站点，其中 2 个在同一个函数里。** 静态扫描按"引用点"数出 4 个生产文件；
  运行期真正跑到的只有 `settings_sidebar_panel.py:28/32` 与 `settings.py:71`。
  `questionnaire_panel.py:89/93` 那两处（s922-21 记为"语言切换第二实例"）本轮 0 命中 ⇒ 问卷面板的独立语言开关
  要么没被 e2e 覆盖，要么已随 UI 改版失效。**属"有码无证据"，不可反推为死码。**
- **F2 · en 面运行期零覆盖。** 在册 e2e 从不切语言（`language` 键只在 zh 表查到），
  ⇒ 53 个 en 词条的运行期证据 = 0。若将来要做"双语一致性"结论，需要的是**语言切换的 e2e 用例**，
  不是再跑一遍本探针。
- **F3 · "106 键"不是运行期键全集，且未命中是静默的。** `t()` 找不到键返回键名本身（`i18n.py:266`），
  `get_test_name` 再回落 `TEST_NAMES_ZH`（`settings.py:69-72`）⇒ 48 个动态键里 24 个**每次调用都未命中表**
  而用户看到的名字仍然正确。今天没有任何门禁能在"表扩到 130 键 / `TEST_NAMES_ZH` 改名"时报警：
  `tests/test_i18n.py:112` 只钉总数、`test_two_language_tables_are_key_symmetric` 只钉 zh/en 对称，
  **两表与 `TEST_NAMES_ZH` 之间零断言**。这是本探针顺手撞到的结构性缺口，属实现改动范围，本班不动。

## 五、一条未归因的崩溃（如实登记，不判缺陷、不修）

自造 harness（A2/A3：直接 `AppTest.from_file("app.py")` + `privacy_accepted/onboarding_completed/_onboarding_skipped`，
含只设这三键不设 `app_mode` 的最小变体）在 **14/14 次运行**里抛同一个异常：

```
File "app.py", line 1417, in <module>      render_assumption(r, f"{category}: {name}")
File "src/ui/renderers.py", line 30, in render_assumption   icon = "✅" if r.passed else "⚠"
AttributeError: 'str' object has no attribute 'passed'
```

对照读数：**同一套驱动在在册 pytest harness 下不复现**（`pytest tests/test_e2e_ui.py -k "app_loads or questionnaire_mode or upload_csv"` → 3 passed；A0 整体 21 passed rc=0）。
`app.py:1413-1417` 假定 `assumptions` 的 value 是 `AssumptionResult` 对象，而崩的时候拿到的是 `str`；
`src/analysis/assumptions.py:65-72` 的 `check_normality_groups` 现场看**返回的确实是 `{name: AssumptionResult}`**
⇒ 该 str 从何而来**本班未定位**（时间预算内没继续挖）。两种可能都要留：
① 我的沙盒少盖了一个持久化入口，读到了非预期状态（`~/.psy_analysis/autosave.json` 实测**不存在**，此路未证实）；
② `analysis_output` 经序列化/反序列化回内存后 `assumptions` 退化成字符串表 ⇒ 真实用户可达的渲染崩溃。
**判据不满足，故不报缺陷、不派单**，只把复现命令与本读数交主班：要坐实只需
按第四节站点手工点一次"比较两组得分"并观察 `output["assumptions"]` 的实际类型。

## 六、复跑与产出件

```bash
cd /d/code/psy-analysis
# 卷宗判据命令：退出码 0
PYTHONUTF8=1 .venv/Scripts/python.exe tmp/i18n_key_probe_s923.py; echo "EXIT=$?"
# 读数明细（28 条 (key,lang) + tier_of_key + sites）
PYTHONUTF8=1 .venv/Scripts/python.exe -c "import json,pathlib;p=json.loads(pathlib.Path('tmp/s923-17/hits.json').read_text(encoding='utf-8'));print(p['pytest_rc'],p['ui_hit_keys'],p['pending24']['counts'])"
# 悬置键清单本身（不依赖探针）
PYTHONUTF8=1 .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from src.utils.i18n import TRANSLATIONS;from config.settings import TEST_NAMES_ZH;print(sorted((set(TRANSLATIONS['zh'])-{'title','abstract','keywords','introduction','methods','results','discussion','references','language','chinese','english'})&set(TEST_NAMES_ZH)))"
# 零改动自证
git status --porcelain src/ scripts/ ; git diff --numstat -- src/
```

退出码语义（写死在探针里，便于机器判）：`0` 正常／`3` 生产数据被写／`4` 记账器异常／`5` 直方图全空。

**局限（必须连着结论一起引用）**：本轮"一轮全 UI"实际等于"在册 e2e 套件覆盖到的 UI + 自造模式扫描"，
**不等于穷尽 7 个模式的所有页与控件**。要把 22 个"结构可达未触发"降级为"死"，
缺的是**按统计方法逐条走一遍分析流**的覆盖（Playwright 面，见 `docs/insights/playwright-readiness-20260911.md`），
而不是再跑一次本探针。`tests/test_i18n.py` 那 106 键钉桩与探针结果不可互换：前者证"表是全的"，后者证"有人调用"。
