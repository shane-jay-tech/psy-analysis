# s927-66 · psy 台账在册红归因汇编（一页清单，供主班排消红单）

> 生成：2026-09-29T06:2x，班 `qoder-executor-20260929-0600-psy105`，cwd `D:\code\psy-analysis`。
> 台账源：`D:\code\docs\insights\drain-20260923-pending-human.md`（**根仓，只读**，现 189 行在册条目）。
> 位别：只读／材料位。**本单一枚红都没消**（完成标准 ③）。
> ⚠ **本档每一条红都是 2026-09-29 现跑或现读**，不抄台账旧数；**抄旧数处一律标出台账原值与现值差**。

---

## 0. 先分类：台账里的"红"其实混了六类，只有第 1 类是真正的"HEAD 红"

主班排单前必读这张分型表——**"消红单"这个词对后几类是错的动词**：

| 类 | 形态 | 判据 | 本汇编命中 |
|---|---|---|---|
| **A 真·在册测试红** | HEAD 上跑就红 | 定向跑 rc≠0 | **#81**（唯一一枚） |
| **B 口径红（非代码缺陷）** | 命令少写守卫 ⇒ 自检**主动拒跑** | 补上正确命令即绿 | **`test_lr_rerun_apptest.py` 8 errors** |
| **C `xfail(strict)` 登记的在册缺陷** | **不是红**，是绿里的 x；修好会 XPASS 报警 | `-rxX` | **#182** |
| **D 静默失效（零红、零覆盖）** | 永不红，因为异常被 `except` 吞／夹具形状与生产不符 | 读码＋最小复现 | **#205⑥、#194③、#194①尾（clear_cache）** |
| **E 已结案但台账未回写** | 现跑**已绿** | 定向跑 rc=0 | **#94、#210**（＋班前提示点名的 `test_cfa_sem_golden.py`） |
| **F 同型未修清单** | 在册但未成红 | grep 计数 | **#194②（8 件仍在）** |
| （G）待拍板出口，非红 | 裁决材料 | — | **#194①、#198①②③④、#96①②③④** |

⇒ **当前 psy 在 HEAD 上唯一一枚真红是 #81。** 其余"红"要么要用别的动词（改口径／撤 xfail／补测试／回写台账），要么根本不该进消红队列。

## 1. 逐条清单（A–E 主力六枚）

| # | 红/缺陷是什么（现值） | 红因（现跑／现读定位） | 消红路径（只给路径，不代拍） | 责任面 |
|---|---|---|---|---|
| **#81** | `tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for` —— 现跑 **`1 failed, 10 passed in 3.72s`**（`.venv`，`-p no:randomly`） | `src/ui/questionnaire_panel.py` 有 **3 枚 `st.download_button`**（现行号 **:829/:841/:868**，台账记 :826/:838/:865 已漂 +3／+3），该文件既不在 `WHITELIST_EXPORTS`(11 项) 也不在 `GATED_EXPORTS`(3 项)，`NEEDS_MIGRATION` 现为**空 `{}`**（`:39`）⇒ `unaccounted != []` 断言红。红源自主班代提交 `f8ca14e`（s922-138/139/140），**HEAD 既有** | 只有两条出口，**都属人工隐私分类权**：① 给这 3 枚按钮接 `export_gate`（生产码行为改动＋要求全量重跑）；② 判"问卷设计报告"为中间产物而豁免（同类先例现读在白名单里：`result_card_panel`"中间产物"／`evidence_table_panel`"中间产物供整理用"／`questionnaire_import_panel`"问卷清洗日志·中间产物"）。⚠ **不可用 `NEEDS_MIGRATION` 绕**：该表有"必须为空"断言＝自我绕过（台账原话，本班复核 `NEEDS_MIGRATION={}` 仍被计入 `known` 集合，`:81`） | 人工（隐私分类）；执行手无权限。**且它是 s927-31 案 A 的硬前置 G1** |
| **#182** | Word 导出在生产路径从未渲染 —— 现跑 **`16 passed, 1 xfailed in 3.05s`**（**不是红**） | `src/output/docx_exporter.py` 两处把 `List[str]` 当 `str` 喂给 `_add_paragraph_with_inline_format`：现行号 **`:803`（ethics）／`:831`（notes）**，台账记 :779/:807 **已漂 +24**。真实 `ExperimentDesign` 一进导出即 `TypeError`，`:404` 的下载口永不到达。钉桩处 `tests/test_experiment_design_ui_detail_branch.py:652 @pytest.mark.xfail(strict=True)`，其 reason 文本**仍写旧行号 :779/:807** | 三出口（台账 A/B/C）：① 导出器内 join ⇒ **撤 xfail 必须与改导出器同笔**（否则 strict xfail 当场 XPASS 红）；② 改 `ExperimentDesign` 字段类型 ⇒ 连带 `format_design_report` 与在册 docx 夹具；③ 维持 xfail，只在交付文档写明限制。**顺手项**：撤 xfail 时该件 reason 里的 :779/:807 与 `:614` 注要一起改 | 人工选案（交付物可用性）；执行手可做的只有"改行号注记" |
| **#205⑥** | `src/questionnaire/kb_search.py:238 from config.llm_providers import get_provider_config` —— **静默失效，零红** | 现跑复现 `ImportError: cannot import name 'get_provider_config' from 'config.llm_providers'`。`config/llm_providers.py` **存在**（台账写"全仓不存在"**不准确**：不存在的是**函数**，模块在），其公开面只有 `LLM_PROVIDERS` 字典（`:149`）＝ `none/deepseek/zhipu/moonshot/openai/claude/ollama/custom`。异常被 `:101-118` 的 `except Exception: llm_results = []` 吞 ⇒ **LLM 降级搜索恒空**。⚠ 第二层坑：就算把 import 改对，`:240 provider.get("api_key")` 仍会返回空——现读 `LLM_PROVIDERS['deepseek']` 的键只有 `name/base_url/default_model/models/supports_fetch_models/description`，**无 `api_key`** | 两步都要拍：① 取法改成现存面（`LLM_PROVIDERS["deepseek"]`）或**新增** `get_provider_config()` 访问器；② 定 `api_key` 从哪来（现由 env／`.env.local` 驱动，静态字典故意不含密钥 ⇒ 不能往字典里塞）。**且必须配一枚"降级搜索非恒空"的测试**，否则修完仍然零覆盖（现状：`_search_via_llm` 全仓仅 `:105` 一处调用，无测试触达） | 人工（②涉凭据装配面）＋执行手可补测试件 |
| **#94** | ✅ **已结案，台账未回写** —— 现跑 `tests/test_literature_feed_ui.py + test_feed_panel_trending_override.py` 同跑 **`15 passed in 0.86s`**（台账记"同跑 **8 failed**"） | 结案方式正是台账推荐的**案 A**：`2a06659` "文献库 UI 夹具污染按案 A 收口（只删自己作用的 3 个模块名）"。现读 `tests/test_literature_feed_ui.py:22-26` 已收窄为 `_FEED_UI_MODULES = (paths, trend, ui.feed_panel)`，并留了注释说明为何刻意**不删** `trend.trending_weights` | **无需消红单，需要的是台账回写**（把 #94 从"待人工"改判"已结案 A 案落地"）＋ 连带核对 #194① 的前置句（#194① 的"裸跑会真写 trending_weights.yaml"前提**依赖 #94 未修**，#94 修了之后该前提是否仍成立要重测 ⇒ 见本表 #194 行） | 主班（台账回写），不占执行手队列 |
| **#210** | ✅ **HEAD 绿** —— 现跑 `tests/test_exporters_cjk_font_fallback.py` **`7 passed in 0.33s`** | 该条红的前提是 `s924-08` 落地（会让三条"观测面为零"钉桩转红），而三单产物**至今未入库**（快照留在 `D:\code\tmp\handover-snapshot-20260924\psy35-s924-060708-pending.patch` 99 行）。台账自己写的处置就是"保持 HEAD 绿" | 不是消红单，是**选案单**（甲：授权改写三条桩并同批改；乙：摘回 `exporters.py` 的 `:4/:8/:242-243/:254-255`）。⚠ 台账另留三条**假绿形态**要一并处理：判据 `-k "exporters"` 不收集唯一被改写的测试件／`-k "A and B"` 可能选空集仍 rc=0／参照写法 `:570-572` if-else 两分支同体（恒真死分支） | 人工选案；**下班禁 checkout/restore/stash**（台账明令） |
| **`test_lr_rerun_apptest.py`**（班前提示点名） | **同一枚文件，两种读数**：无守卫 **`8 errors in 2.78s`** ／ 带守卫 **`8 passed in 4.71s`** | 红因**不是**代码缺陷，而是**文件自己的安全自检在起作用**：`:122 assert not leaked` 扫 `sys.modules` 里所有 `src.*` 模块的 `DB_PATH`，只要有一个仍指向生产 `data/literature_feed/feed.sqlite` 就**拒跑**并打印"请用 `LITERATURE_FEED_DATA_ROOT=<沙盒>` 包住 pytest 命令"。深层机理现读＝`src/literature_feed/__init__.py:10-18` 在**包导入期**把 `paths` 的 7 个常量复制进包命名空间，事后 `monkeypatch.setattr(feed_paths, …)` 打不到已导入的 `src.literature_feed.DB_PATH` | **归 B 类"口径红"，不是消红单**：把守卫写进全量执行口径（`pytest.ini` addopts 或派单模板）即消。若要代码级根治，得把 `__init__.py:10-18` 的常量复制改成惰性求值（**属生产码改动，且它同时是 s927-27 §8 交叉注记的那处**）。⇒ 排单时应写成"改命令口径"而非"修代码"，否则会把一次环境用法问题排成生产码单 | 主班（口径／模板），代码根治另需人工点头 |

## 2. 其余在册项的现值（#194 / #198 / #96，按子条拆）

> 这些多数是 **D／G 类**，列在这里是为了让主班**别把它们误排成消红单**。

- **#194①**（🔴 裸跑复现命令会真写 `trending_weights.yaml` 进真库）：⚠ **前提要重测**——它建立在 #94 未修之上，而 #94 已由 `2a06659` 结案。本班**未裸跑**该命令（守 data 无还原点纪律），只登记这条"前置可能已失效"。**安全纪律仍照旧：任何 feed 复跑一律 `LITERATURE_FEED_DATA_ROOT` 指沙盒**。真库现值 181 件／21,059,126 B（本班跑前＝跑后逐位相同）。
- **#194②**（同型前缀清理 8 件未修）：✅ **仍在册，现值仍是 8 件**——`test_literature_feed_extract/ fetchers/ headless_llm/ lock/ scheduler/ storage/ trend` ＋ `test_lock_alert_log`（现 grep `startswith("src.literature_feed")` 命中 8 文件 9 行）。**是否已成红未测**（要同跑对撞才知道）。
- **#194③**（binary/ordinal/multinomial 结果卡在生产上抛错被吞）：**行号锚全废**——现读 `src/analysis/result_card.py` `_build_logistic_regression` 在 **:868**（台账记 :716/:727），且该文件带 **+180/−13 未归因在途改动**（brief §C 禁碰件）；HEAD 版同区已是防御式 `getattr(...) or getattr(...)` 形态。台账自陈"**没红是因为在册夹具形状与生产 `LogisticResult` 逐位不符**"⇒ **属 D 类静默缺陷，现在没有失败测试可消**，要单开的是"造一个生产同形状的夹具让它先红"。
- **#194①尾 clear_cache**：现读 `clear_cache` 有 `src/llm_gateway/gateway.py:318` 与 `src/paper_writer/literature_crawler.py:719` 两处定义、均经各自 `__init__` 导出 ⇒ "仓内零生产调用方"这句**未按现值复核**（本班未追调用链，列为主班排单时的待核项）。
- **#198①**：✅ 现读**逐字成立**——`src/utils/project_manager.py` `@_locked` 计数 **7**，且 `list_projects:187`／`get_project:194`／`load_workspace:311`／`migrate_legacy_autosave:327`／`_read_index:150` 均在（台账记 `_read_index:151`，漂 −1）。`src/utils/instance_lock.py` 的 `alert` 命中数 **0** ⇒ KNOWN_ISSUES 的 P1 行确未推进。⚠ 路径订正：台账正文只写 `project_manager.py`，真身在 **`src/utils/`** 不在 `src/workspace/`。
- **#198②**（`_CARD_BUILDERS` 44→30 案 A）：属**改计数口径**，非红；要同翻 4＋6 处快照/参数化。未现算 44/30 现值（本班不动生产码注册表判定）。
- **#198③**（流式出口写死 import）：✅ 现读**成立**——`src/llm_gateway/gateway.py:332` 定义 `register_llm_backend`、`:367` 注册默认后端，但流式侧 `:351` 是函数体内 **`from src.llm_gateway.quick_models import …`** 的写死形态，`:612`／`:658` 两处 `streaming=True` ⇒ 注册表对流式路径无效这一形状仍在。翻正要同步 `TestBackendRegistryAsymmetry` 三例。
- **#198④**（p 值 `round(,4)`／权重和 100.1·99.9 vs 硬编码 100.0／`effect_type` 仅标签）：**统计结论域红线** ⇒ 本班**未取任何数值、未判是否缺陷**，只转述台账。排单必须走人工＋独立复核。
- **#96①②③④**：①承 #81；②"panel 独有修复因零生产调用方从未上线"——**本班在 s927-31 独立复核到同一事实**（`compute_pending_elapsed`/`pending_clock_anomaly` 在 app.py 命中 **0**、panel 各 3），两枚单互相佐证；③④ 属选案，非红。
- **`tests/test_cfa_sem_golden.py`（E 类，现跑已绿）**：现值 **`19 passed in 2.24s`，rc=0**。
  ⚠ 边界如实标：跑的是**工作树版**（该件带 `59/49` 未归因在途改动，属 brief §C 禁碰件），**HEAD 版本班未跑** ⇒ "工作树绿"不等于"HEAD 绿"。
  另注防串案：brief §D 引 s927-32 的"台账 **16** 在册红"是**台账行号**，与本件 **19 枚用例**不是同一口径，勿互换引用。

## 3. 给主班的排单建议（顺序，不是裁决）

1. **只有一枚需要"消红单"**：#81。且它是 **s927-31 案 A 的前置闸 G1** ⇒ 排在问卷并单之前。
2. **#182** 排"撤 xfail ＋ 改导出器"的**两笔一体**单（拆笔必翻红）。
3. **#205⑥** 排"修 import ＋ 配一枚非恒空断言"的单，**两笔一体**（只修不测＝再静默一次）。
4. `test_lr_rerun_apptest` 的 8 errors **不要排代码单**——改的是**命令口径**（addopts／派单模板加 `LITERATURE_FEED_DATA_ROOT`），成本≈0；顺带可评估 `__init__.py:10-18` 的惰性化（生产码，需点头）。
5. **#94／#210 是台账回写，不是消红**：#94 改判已结案；#210 走选案（甲／乙），并清掉那三条假绿形态。
6. **#194② 8 件**、**#194③ 夹具形状**、**#198① alert** 各排一枚只读复核单（现值已给，缺的是"要不要动手"的判断）。
7. **#198④ 数值语义** 走人工＋第二方案复核，不进执行手队列。

## 4. 复算命令（主班可原样跑）

```bash
cd /d/code/psy-analysis
export PYTHONIOENCODING=utf-8
# #81（真红，勿消）
.venv/Scripts/python.exe -m pytest -p no:randomly tests/test_export_gate_global_scan.py -q          # 1 failed, 10 passed
# #182（xfail，非红）
.venv/Scripts/python.exe -m pytest -p no:randomly tests/test_experiment_design_ui_detail_branch.py -q -rxX   # 16 passed, 1 xfailed
# #205⑥（静默，零红；直接复现 ImportError）
.venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'.');from config.llm_providers import get_provider_config"
# 班前提示点名那枚：两种读数对照（务必各跑一次才是本档口径）
env -u LITERATURE_FEED_DATA_ROOT .venv/Scripts/python.exe -m pytest -p no:randomly tests/test_lr_rerun_apptest.py -q   # 8 errors
LITERATURE_FEED_DATA_ROOT=/tmp/sandbox .venv/Scripts/python.exe -m pytest -p no:randomly tests/test_lr_rerun_apptest.py -q  # 8 passed
# #94（已结案）
.venv/Scripts/python.exe -m pytest -p no:randomly tests/test_literature_feed_ui.py tests/test_feed_panel_trending_override.py -q  # 15 passed
# #210（HEAD 绿）
.venv/Scripts/python.exe -m pytest -p no:randomly tests/test_exporters_cjk_font_fallback.py -q       # 7 passed
```

**局限（如实写）**：
- 本班**未跑全量** ⇒ 这张表是**"台账点名的红"的现值核对**，**不是 psy HEAD 全量红清单**。
  全量现值要主班按 s927-27 钉好的口径（`.venv` ＋ `-m "not (e2e or playwright)"` ＋ `LITERATURE_FEED_DATA_ROOT` 沙盒）跑一次才成立。
- 多数行号是**工作树现值**；`src/analysis/result_card.py`（+180/−13）等在途件一旦落地，其锚点会再漂。
- D 类（#205⑥／#194③）的"红因"是**读码＋最小复现**得出，**没有失败测试可指**——这正是它们的危险之处，别在排单时按红名找它们。

## 5. 零消红与零改动自证

- **一枚红都没消**：#81 未挂 `NEEDS_MIGRATION`、未加白名单、未接门禁 ⇒ 现跑仍是 `1 failed, 10 passed`（本档 §1 的复算命令可原样验证）。
- 未改任何 `src/`／`tests/`／`app.py`／`pytest.ini`／`requirements-lock.txt`／KNOWN_ISSUES／台账。
- 台账（根仓 `docs/insights/drain-20260923-pending-human.md`）**只读未回写**——§1/§2 里"E 类已结案未回写"的结论**以本档为材料交主班回写**，执行手不代改台账（brief 禁令：待人工台账只读）。
- 文献真库：跑前 181 件／21,059,126 B ＝ 收工同值（本班全程带 `LITERATURE_FEED_DATA_ROOT` 指向自己 tmp；`8 errors` 那一跑是**守卫主动拒跑**，未落任何字节）。
- 红线自查：#198④ 统计数值语义**未取数未判定**；无隐私医疗内容；判分口径只转述不裁决。
