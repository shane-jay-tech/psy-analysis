# 文献推送 `from-issued-date` 策略三选裁决材料：三案的抓取覆盖差异与成本（2026-09-28，只读登记）

- 单号：`s927-50`（班 `qoder-executor-20260928-1745-psy96`，cwd `D:\code\psy-analysis`，**只读路**）
- 上游锚点：`zcode-bridge/done/s923-13.result.md:51`（三选项原文）＋ 其产物 `docs/insights/psy-feed-source-census-20260923.md` §七.1
- 性质：**研究面簿红线**。本单**零抓取、零写库、零改数值口径**，只登记三案的覆盖差异与成本；**选案交人工拍板**。
- 现场基线（本班现取）：HEAD `9364550`，`git status --porcelain` **12 项**；本单引用的所有源件（`src/literature_feed/**`、`scripts/seed_literature_sources.py`、`scripts/run_daily_feed.bat`、`tests/fixtures/literature_feed/**`）经 `git diff --name-only` 核为**与 HEAD 逐字节相同**（不在 12 枚在途件里）⇒ 下文行号 HEAD／工作树同值，无需分两版报。
- 在册 12 枚在途件本单一件没碰：` M` 7 枚（`app.py`／`pytest.ini`／`requirements-lock.txt`／`src/analysis/__init__.py`／`src/analysis/cfa.py`／`src/analysis/result_card.py`／`src/output/interpretation.py`）＋ ` M` 测试 `tests/test_cfa_sem_golden.py` ＋ `??` 4 枚（`docs/insights/s924-36-a1-backport-draft-20260925.md`／`node_modules/`／`scripts/research_release_gate.py`／`src/analysis/_sklearn_compat.py`）。

## 一、结论（一句话）

三案**不是同一件事的三个改法，而是三个不同的切片**：`from-issued-date` 与 `from-created-date` 是**互有得失的两个子集**（不是超集关系），换路由是唯一能同时修好「抓取层」与「显示／趋势层」的出口但要把官网抓取面新建起来。**推荐形状＝(b′) 逐源口径选择，且用 `sources.notes` 的既有 JSON 通道承载（不占迁移号），但必须与 `sort` 一起换、必须先解掉 seed 抹 `notes` 的在册副作用**；三案都**修不到显示层**（入库的 `issued_date` 仍是 `2026-01-01`），该处属数值口径、独立交人工。**前置未拍板项：14 天窗口口径**——上游的 47 条是 **60 天探针口径**的读数，生产实际只看 14 天。

## 二、现状机制（本单实测/复算的，不是抄上游）

| 层 | 代码位置（HEAD＝工作树） | 现读机制 |
|---|---|---|
| 过滤轴 | `src/literature_feed/fetchers/crossref.py:71` | `filter = f"issn:{issn},from-issued-date:{since}"` —— **轴名硬编码在全 8 源共用的 fetcher 里**，`SourceConfig.extra`／`sources` 表没有任何口径入口 |
| 排序 | `crossref.py:72-73` | `sort=issued`、`order=desc`（与过滤轴**分离**的两个常量） |
| 单次量 | `crossref.py:74` | `rows = min(max(1,limit),100)`；生产 `limit`＝`DEFAULT_FETCH_LIMIT = 20`（`scheduler/daily_runner.py:73`） |
| 窗口 | `daily_runner.py:72`／`:423-426` | `DEFAULT_DAYS_BACK = 14`；`since` 由 `_compute_since()` 算，**全局单值套所有源**（`:308` 在 source 循环之外算出，`:318` 逐源透传），`sources.last_success_at` **未当逐源水位用** |
| 探针轴 | `scripts/seed_literature_sources.py:83-88` | `fetcher.fetch_since(None, limit=10)` → `crossref.py:166-170 _default_since(days_back=60)` ⇒ **60 天／rows 10**，与生产 14 天／rows 20 **两条口径不同** |
| 生产调用 | `scripts/run_daily_feed.bat:59` | `"python" -m src.literature_feed.scheduler --json-summary --log-level INFO`，**不传 `--days-back`／`--fetch-limit`** ⇒ 走 `scheduler/__main__.py:34-36` 的默认（14 天／20 条）；抽取上限 `MAX_EXTRACT_ARTICLES_PER_RUN = 12`（`daily_runner.py:74`） |
| 日期解析 | `src/literature_feed/parsers/csl_normalizer.py:226-233` | 优先级 `issued > published-print > published-online > created`；`normalize_iso_date`（`:30-45`）对 `date-parts:[[2026]]` **缺月补 01、缺日补 01** |
| 去重 | `daily_runner.py:572-587`＋`storage/feed_store.py:360-380` | 三层：DOI 唯一 → `(source_id, title_norm, issued_date)` 唯一 → `raw_hash`；**去重发生在抓取之后** ⇒ `rows=20` 的名额会被重复条目吃掉 |
| 空响应 | `crossref.py:111-119`＋`daily_runner.py:492` | 空结果 `raw_records=[]` 且 `if result.raw_records:` 才归档 ⇒ **抓回 0 篇与没发请求在 raw 层不可区分**（在册可观测性缺口） |
| 审计指纹 | `fetchers/base.py:126-128` | `health_signature() = f"{fetcher_type}:{source_id}:v1"` —— 版本串**写死 `:v1`**，不含日期轴 |

**锚点行号漂移（双报）**：上游 census 记的 `daily_runner.py:296`（全局 `since_iso`）与 `:480-481`（`if result.raw_records:`）在**当时 HEAD `1d022ca`** 逐字成立（本单 `git show 1d022ca:… \| grep -n` 复算＝296／480）；**当前 HEAD `9364550`／工作树** 已漂到 `:308`／`:492`。漂移由 `1657af8`（s924-14／s924-15，2026-09-25，给 stale 弃单加计数）等后续提交加行造成，**不是语义变化**。`crossref.py:71`／`:166` 两版同值，零漂移。

## 三、三案覆盖差异（分层登记）

> 记号：`issued 轴`＝Crossref 服务端按出版日期过滤；`created 轴`＝按沉积（入库 Crossref）日期过滤。
> 上游 09-23 的六条探针读数（**本单未复采——任务禁联网**）：`from-issued-date:2026-07-25` → 0；`from-issued-date:2026-01-01` → 149；`from-created-date:2026-07-25` → 47（`created=[[2026,9,11]]`）；`issn:1671-3710,from-issued-date:2026-07-25` → 14；`/works?filter=issn:0439-755X` total-results 2380。引自 `psy-feed-source-census-20260923.md` §四。

### 3.1 覆盖差异表

| 维度 | 现状（基线） | (a) 全局换 `from-created-date` | (b) 逐源口径选择（新增列／配置） | (c) acta 改走 `official_site`／`manual` |
|---|---|---|---|---|
| acta 抓取层 | **恒 0**（年粒度 `issued` 被服务端按 `2026-01-01` 比掉） | 修好（60 天窗口实测 47 条） | 修好（该源单点换轴，其余不动） | 取决于官网目录页能否解析；**只取「最新一期」**（`psy_science_official.py:34 _LIST_PATH = "/CN/volumn/current.shtml"`，拼用在 `:74`，非增量轴） |
| 其余 7 源抓取层 | 正常（60 天窗口 2–17 篇／源） | 🔴 **会丢**：`created < 窗口` 但 `issued` 落在窗口内的条目（先注册后出版／分配远期卷期）**被 created 轴滤掉** ⇒ created 不是 issued 的超集 | 零影响（逐源生效） | 零影响 |
| 会新增的「非新发表」条目 | — | 🔴 「旧文新沉积」被当新文入库（`created ≠ 新发表`，上游原判） | 同样存在，但只落在被改口径的那 1–2 枚源上 | 无此问题（按目录页期次取） |
| 显示／趋势层（`articles.issued_date`） | acta 无行 ⇒ 无显示 | 🔴 **仍不见新文**：解析层 `issued` 优先（`csl_normalizer.py:227-233`），年粒度条目入库即 `2026-01-01`（本单实测 `normalize_iso_date({'date-parts':[[2026]]}) = 2026-01-01`）；`feed_store.py:435`／`:497` 与 `trend/aggregator.py:47,75` 全按 `issued_date` 开窗 ⇒ 面板与趋势加权仍把它算成 1 月的文 | 同 (a) | ✅ **唯一能同时修显示层的一案**：`psy_science_official.py:214` 用站点 meta 的 `citation_date` 走 `normalize_iso_date`，若官网给全日期则 `issued_date` 精确；⚠ 该 fetcher 另有**本地** `since` 过滤（`:216`）⇒ 站点若只给年份，同样的年粒度问题会换个位置复现 |
| 与 `rows=20` 名额的相互作用 | 6 源正常轮转 | 🔴 **饿死风险**：47 条 > 20；`sort` 仍是 `issued`，acta 全批条目 `issued` 同为 `2026-01-01` ⇒ 并列名次由 Crossref 二级排序决定（**本仓代码未指定、本单未测**），若每轮返回同一批，则 DOI 去重（`feed_store.py:370-375`）把 20 个名额全记成 `duplicates`，`new_articles` 长期 0。**⇒ 走 (a) 或 (b) 都必须把 `sort` 一起换成 `created`**（本单推演的 (a+) 请求形状即此组合） | 同 (a) 的处置；逐源换轴时该源的 sort 也要跟着换 | 官网路由无 `rows` 概念，改为 `limit` 截断目录链接数（`psy_science_official.py:103-111`） |
| 与 14 天生产窗口的相互作用 | 探针 60 天读数**不能**当生产收益 | 同左：47 是 60 天口径，14 天口径下能落几条**本单未测**（禁联网） | 同左 | 期次驱动，与天数窗口解耦（但一期可能就几篇） |
| 审计层（能否区分改前／改后） | — | 🔴 **区分不了**：`health_signature` 恒 `crossref:{source_id}:v1`，换轴不涨版本号 ⇒ `sources.probe_signature` 与 `fetch_runs.summary_json` 里查不到"策略变了"这件事（`daily_runner.py:515-520`） | 若把口径写进配置并涨签名则可区分；**建议把 `v1` 一起改成含轴名**（本单不改） | ✅ 会自动变：`fetcher_type` 进签名 ⇒ `crossref:acta…:v1` → `official_site:acta…:v1`（现值见 census §3.1） |
| 空响应可观测性 | 0 篇与没发请求不可分 | 同左（`crossref.py:111-119`＋`daily_runner.py:492` 未动）⇒ **(a)/(b) 改完"到底抓到没有"仍只能看 `fetch_runs.summary_json`** | 同左 | 官网路由空目录会抛 `SchemaChangedError`（`psy_science_official.py:97-98`）⇒ 反而把"没抓到"变成响的失败态 |

### 3.2 成本／改动面（最小形状＋回滚成本）

| 案 | 最小改动面 | 要碰的在册件 | 迁移／写库 | 回滚成本 | 主要风险 |
|---|---|---|---|---|---|
| (a) 全局换轴 | `crossref.py:71` 一行（`sort` 若同换则 `:72` 也动） | `tests/test_literature_feed_fetchers.py`（现仅 `:210` 钉 `issn:0439-755X` 出现在 filter 里，**无一条钉 `from-issued-date` 字面** ⇒ 改轴不会让它红，也就**没有测试会拦住这次语义变化**） | 零 | 极低（单行 revert） | 🔴 7 枚好源一起换语义＝一次改动打 8 个源；`created` 当"新文"＝研究面簿污染；显示层仍 0 收益 |
| (b′) 逐源口径（**推荐形状**） | ① `crossref.py:70-76` 把轴名／sort 键变成从 `config.extra` 读；② 口径值落在**已有的** `sources.notes` JSON 通道（`daily_runner.py:85-99` 已 `json.loads(notes)` 并塞进 `SourceConfig.extra`）⇒ **不新增列、不占迁移号** | `seed_literature_sources.py`（注册值需带口径，否则重 seed 即丢）；`tests/test_seed_literature_sources.py:49-51` 逐字钉 `issn`/`doi_prefix`（两笔一体，改注册面须同批改测试）；`tests/test_literature_feed_fetchers.py` 补一钉"按 extra 选轴" | **零迁移**（若走新增列＝迁移：`storage/migrations.py:99-103` 现仅 3 条，全为 `20260703_*`，且 `:5` 自述只能 `ADD COLUMN`） | 低（配置面 revert 即回基线；代码面 1 个函数） | 🔴 **seed 的在册副作用直接打在 `notes` 上**：`feed_store.py:231-237` 的 `ON CONFLICT DO UPDATE SET notes = excluded.notes` 且 seed 不传 notes ⇒ **重跑 seed 会把口径配置抹成 NULL**（census §七.5 已记「抹掉 `sources.notes`」＋「重新打开人工停用的源」两条在册副作用）。⇒ (b′) 落地**必须先把 notes 从"被 seed 覆写"里解耦**，或把口径另置（新增列／配置文件） |
| (c) 换路由 | ① acta 的 `fetcher_type` 改 `official_site`；② **新建／改造 fetcher**：`psy_science_official.py` 的 `base_url` 可经 `notes` JSON 注入（`daily_runner.py:91`），但 `_LIST_PATH`（`:34`）与 `_ARTICLE_LINK_RE`（`:36-37`，用点 `:259`）是**模块常量**，路径结构按华东师大 psysci 写死 ⇒ 直接给 acta 复用＝高概率 0 命中并抛 `SchemaChangedError`；`manual` 路由更不可用：`manual_ingest.py:119-121` 的 `fetch_since` **恒返回空列表**（不参与定时拉取） | `schema.sql:18` 注释已承认三种 `fetcher_type` 合法（无 schema 改动）；`build_fetcher`（`daily_runner.py:101-106`）路由已存在，**当前 8 源全走 crossref、`official_site`／`manual` 零源使用**（census §3.1） | 零迁移 | 中（路由字段一改，抓取面从 API 换成 HTML 解析，改版即失效） | 唯一修显示层的出口，但**成本最大**：要新写站点解析＋HTML 快照＋限流；且 acta 官网路径结构本单**未联网核实**，属人工实测项 |

## 四、三案共同缺口（拍板前要先知道）

1. **验收面是空的**：`tests/fixtures/literature_feed/crossref_acta_psych_sample.json` 里 3 条 item 的 `issued.date-parts` **全是全精度**（`[[2026,5,1]]`／`[[2026,4,20]]`／`[[2026,4,10]]`）、**3/3 没有 `created` 字段**（本单实测逐条打印）。⇒ 该夹具**复现不了年粒度、也测不到 created 轴**，三案任一件改完都不会被现有测试拦住或验出。补夹具属实现改动，本单未做。
2. **数值口径缺口与三案正交**：只要 `csl_normalizer.py:227-233` 的优先级不变，(a)/(b) 抓回的行 `issued_date` 就是 `2026-01-01`。把它改成"created 优先／或保留原始粒度标记"＝**改数值口径**，命中红线，本单不动、不判定。
3. **窗口口径先于策略选择**：47／149／14 是 60 天探针读数，生产是 14 天（`daily_runner.py:72`）。不同轴的收益必须在同一窗口下才可比。调 `DEFAULT_DAYS_BACK` 或启用 `last_success_at` 逐源水位＝**改抓取量口径**，在册红线（census §七.2），本单不动。
4. **`rows=20` 与 `sort` 的耦合**：只换过滤轴不换排序＝可能永久饿死（见 3.1 倒数第三行）。这是本单相对上游新加的一条**实施约束**。
5. **调度层另有一案**：全库 `articles` 最后 `fetched_at` 与 run 42 `running` 僵尸行属调度归因域（census §七.7／`psy-feed-zombie-runs-20260923.md`），**与本案正交**，别并案。

## 五、推荐（交人工拍板的材料，不构成放行）

按「修复收益 ÷ 污染面」排序：

1. **首选 (b′)**：逐源口径选择 + **`sort` 同轴** + 用 `sources.notes` JSON 通道（**免迁移**）。附带两条硬前置：① 先把 `feed_store.py:231-237` 的 `notes = excluded.notes` 改成 `COALESCE(excluded.notes, notes)` 或让 seed 显式保留 notes（否则重 seed 即静默丢配置）；② 把 `health_signature` 的写死 `:v1` 涨成含轴名（否则审计层无法区分改前／改后）。收益＝只动 1–2 枚坏源，7 枚好源零风险；代价＝配置面＋一处 upsert 语义，两个文件级改动。
2. **次选 (c)**，且只在"要让心理学报真进面板／趋势"时选：它是唯一能修显示层的出口，但要为 acta 新写官网解析（现有 `psy_science_official` 是 psysci 专用，`_LIST_PATH` 与链接正则不接受配置），HTML 面脆弱，`manual` 路由不构成自动增量（`manual_ingest.py:119-121`）。**建议与 (b′) 分两笔**：先 (b′) 止血抓取层，再评估显示层要不要单开官网路由。
3. **不推荐 (a)**：全局把 8 源一起换成 created 轴，会对 6–7 枚**当前工作正常**的源造成结构性漏抓（`created` 早于窗口但 `issued` 在窗口内的条目），同时把「旧文新沉积」当新文——**一手换一手丢**，且显示层零收益、审计层无法区分、现有测试零拦截。
4. **三案都不解的**：窗口口径（第 4.3 条）、空响应不落 raw 的可观测性缺口、夹具无 created。这三条建议单列，别塞进策略选择里当附加条件。

## 六、复算入口（沙盒，零网络零写库）

探针：`D:\code\tmp\qoder-executor-20260928-1745-psy96\s927-50_probe_filter_shape.py`（**复算入口，保留**）

```bash
# cwd D:\code\psy-analysis；必须先在进程外设沙盒根（paths.py:25 在 import 期就把 DATA_ROOT 定死）
LITERATURE_FEED_DATA_ROOT="D:/code/tmp/qoder-executor-20260928-1745-psy96/feed_sandbox" \
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -X utf8 \
  D:/code/tmp/qoder-executor-20260928-1745-psy96/s927-50_probe_filter_shape.py
```

三道闸与反证读数（本单 17:48 沙盒实跑 rc=0；另跑一次不带变量 ⇒ **rc=3 拒跑**，stderr 落 `tmp/qoder-executor-20260928-1745-psy96/noenv_stderr.txt`）：

- **拒跑闸**：脚本第 24-29 行（`if not os.environ.get(...)` 起）在未设 `LITERATURE_FEED_DATA_ROOT` 时 `sys.exit(3)` 并写明理由（不设变量 ⇒ 文献库根指到生产 `data/literature_feed`＝研究面簿，`.gitignore:42 data/` 覆盖、**无 git 还原点**）。**本闸实跑验过**：不带变量直跑 rc=3、零输出到 stdout。
- **生效反证**：`assert paths.DATA_ROOT == 沙盒` 打印 `DATA_ROOT = D:\code\tmp\qoder-executor-20260928-1745-psy96\feed_sandbox`、`DB exists = False`（探针不建库）。
- **零抓取反证**：8 源请求形状经**真实 `fetch_since` 代码路径**产出，`requests` 被换成只记录参数不发请求的桩，并断言 `res.notes == "empty result"` 且 `articles == []`／`raw_records == []`。

关键读数（本单产出，非上游）：

```
现状（生产路径，逐源）：filter=issn%3A<ISSN>%2Cfrom-issued-date%3A2026-09-14 & sort=issued & order=desc & rows=20
(a)  ：…from-created-date:2026-09-14 & sort=issued   ← 轴换了、排序没换 ⇒ 并列/饿死风险
(a+) ：…from-created-date:2026-09-14 & sort=created  ← 必须的组合
(b)  ：仅 acta 一行变 (a+) 形状，其余 7 源逐行复算仍为基线形状
normalize_iso_date({'date-parts': [[2026]]}) = 2026-01-01
合成 created=[[2026,9,11]] / issued=[[2026]] 条目 → crossref_to_raw.issued_date = 2026-01-01
在册夹具：3 条 item 全为全精度 issued，created 字段 0/3 存在
```

零改动自证（`data/literature_feed` 现点，本单全程未打开该库）：

- `feed.sqlite` **499712 B**／mtime `2026-09-23 12:15:30`，`sha256_8 = 6bf5776b`；`-wal` 741632 B／`2026-09-23 12:16:18`；`-shm` 32768 B／`2026-09-28 17:09:01`（**早于本班 17:41 开窗**，非本班造成；本班探针从未 `import sqlite3` 连它）。
- `raw/`：30 个日期目录／**173** 个文件（上游 09-23 记 29 目录／167 文件 ⇒ 增量是 09-23 那次跑批，非本班）；去重后文件名仍恰 6 个（`hrm jap job johp jvb personnel_psych`）⇒ **`acta_psych_sinica`／`adv_psych_science` 至今零落盘**（上游 §五 结论在现值成立）。
- `git status --porcelain` 开工 12 → 交班 13，本班只贡献 1 枚 `?? docs/insights/s927-50-feed-strategy.md`。

门禁跑法读数（本单零受版码改动，跑它是为了给主班留一条现值，不是自证）：

```
LITERATURE_FEED_DATA_ROOT=<沙盒> PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -q -k "download_buttons or export_gate"
1 failed, 19 passed, 1 skipped, 5531 deselected in 19.98s
唯一红 = tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for（:88，unaccounted == ['src/ui/questionnaire_panel.py']）
```

- 该红＝**在册主班红**（s923-18 当时同形读数 `1 failed, 19 passed, 1 skipped, 4901 deselected`；本班只 deselected 计数从 4901 涨到 5531＝套件在长，红没变）。本班**未消红、未挂 `NEEDS_MIGRATION`、未写白名单**。
- ⚠ 跑法口径：该次跑**带**了 `LITERATURE_FEED_DATA_ROOT`。按主班口径，文献面测试件**不带**该变量会有 8 errors——那是 `paths.py:25` 在 import 期定死 `DATA_ROOT` 造成的**跑法问题、不是回归**（本仓在册坑）。跑后复点 `data/literature_feed`：`feed.sqlite` sha256_8 仍 `6bf5776b`、size 499712／mtime `2026-09-23 12:15:30` 逐位不变，`raw/` 仍 173 文件；沙盒目录 `tmp/qoder-executor-20260928-1745-psy96/pytest_sandbox` 为空（该 `-k` 选择集里没有用例落到文献库根）。
