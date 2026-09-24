# psy feed 空响应 raw 可观测性设计稿（s924-18 · 2026-09-25 · 只读出稿）

> 班名 `qoder-executor-20260925-0430-psy40`。**本档是设计稿：零码改、零库改、零 raw 盘面写入**；实施涉及 `daily_runner` 与 `SourceSummary`/JSONL 格式，属生产码面，另行授权。
> 命题来源：`zcode-bridge/done/s923-13.result.md:54`「**`raw/` 空响应零落盘**＝可观测性缺口（`crossref.py:111-119` ＋ `daily_runner.py:480-481`）：『抓回 0 篇』与『请求根本没发／失败』在 raw 层不可区分」＋ `docs/insights/psy-feed-source-census-20260923.md:97`。

## 0. 前提复核（磁盘实况，一处零漂移一处漂移 +12 行）

| 卷宗锚点 | 实测 | 判定 |
|---|---|---|
| `crossref.py:111 "if not items:"` | **零漂移**：`rg -n "if not items" src/literature_feed/fetchers/crossref.py` → `111:        if not items:` | 原样引 |
| `daily_runner.py:480-481 "if result.raw_records:"` 守卫 | **漂到 :492-493**。现读 :480-481 落在通用 `except Exception` 失败分支内（`src_summary.status="failed"` 一带）；归档守卫现值为 `rg -n "if result\.raw_records" src/literature_feed/scheduler/daily_runner.py` → `492:`。漂移归因：s924-14/15 批（`1657af8`）在同文件前段插码推行 | 按实况引 :492-493，注明出处档不回改 |

**空响应路径的两处摘录（落盘现文）**：

```python
# src/literature_feed/fetchers/crossref.py:111-119
        if not items:
            # 不抛 SchemaChangedError；可能就是没新文章
            return FetchResult(
                source_id=self.source_id,
                articles=[],
                raw_records=[],
                probe_signature=self.health_signature(),
                notes="empty result",
            )
```

```python
# src/literature_feed/scheduler/daily_runner.py:490-494（原 480-481 现值）
        # JSONL 归档（即使后续入库失败也保住原始数据）
        try:
            if result.raw_records:
                self.archive.append_many(src_id, result.raw_records)
        except Exception as exc:  # noqa: BLE001
```

## 1. 现状解剖：空响应今天在哪几层留下/不留下痕迹

| 层 | 载体 | 「抓回 0 篇」现读 | 「请求失败/没发」现读 | 可区分？ |
|---|---|---|---|---|
| 内存 | `FetchResult.notes/probe_signature`（`base.py:84-85`） | crossref 置 `notes="empty result"`（:118），且被 `tests/test_literature_feed_fetchers.py:248` 钉成行为字面量 | 抛 `RateLimited/SchemaChanged/Fetch` 异常 | 内存里已可分，**但 notes 无落盘面**（`update_source_status` 不写它；`sources` 表虽有 `notes` 列（`schema.sql:24`）却只被 seed 的 upsert 触碰——见 ①b 否决理由） |
| run 记录 | `fetch_runs.summary_json.sources.<id>`（`SourceSummary.__dict__`，字段：source_id/fetched/new_articles/duplicates/failed/status/error，`daily_runner.py:115-122`） | `fetched:0, status:"ok"` | `status:"rate_limited"` 等——实值 taxonomy：`ok/failed/rate_limited/schema_changed/ok_status_unwritten`（`daily_runner.py:443-500,523`） | **summary 层可区分**，但无「响应体本身长啥样/是否 200 空集」的强证据 |
| raw 归档 | `data/literature_feed/raw/<日>/<src>.jsonl`（`jsonl_archive.py`，UTC 日分片） | **不落盘**（:492 守卫短路，`append_many([])` 即便被调也在 :75-76 early-return） | 同样不落盘 | **不可区分——本单缺口** |
| 库内溯源 | `articles.raw_hash/fetch_run_id` | 无行可挂 | 同左 | 不可区分 |

其它 fetcher 形态（实施时都要覆盖）：`psy_science_official.py:166-171` 空时也回 `FetchResult`（notes=`links=0 parsed=0`）；**`manual_ingest.py:121` 空返回不带 notes/probe**（第三个构造点，勿只盯 crossref）。

raw/ 现场（只读盘点，收工前文献库三项不变量自证见 result）：`date_dirs 30 / files 173 / empty_dirs 0`（s923-13 当时 29/167，增量为后续真 run 落盘，与本设计无关）。

## 2. 消费方普查：raw JSONL 现在谁在读（哨兵行的影响面）

```
$ rg -n "JsonlArchive|iter_day|append_many|JSONL_RAW_DIR" . -g '!docs/**' -g '!src/literature_feed/storage/jsonl_archive.py'
```
读数（现跑，24 命中；关键行）：`src/literature_feed/__init__.py:13,23`＋`storage/__init__.py:4,11`（包级再导出）；`scheduler/daily_runner.py:54,171,185,493`（唯一生产写方）；`paths.py:27,38`（根目录定义）；`tests/test_literature_feed_storage.py:257-290`（`TestJsonlArchive` 直调 append/append_many/iter_day，不经 runner）；`tests/test_lock_stale_boundary.py:20`（仅注释提及路径常量）。

**结论：仓内没有任何生产码读 raw JSONL 回放**（`jsonl_archive.py` 模块 docstring 自称用途①「解析器 bug 修复后可重放」目前无实现消费方；抽取器从 sqlite `articles` 表取数，不碰 raw）。真实读方是**人**＋历史取证档的即席脚本（如 census:111-114 式 `json.loads(line)`）。⇒ 哨兵行的兼容设计只需对「人即席读数」负责：必须带可过滤标记。

## 3. 方案对比（≥2 案，各含数据面写入风险与消费方影响）

| 方案 | 改什么 | 数据面写入风险 | 消费方影响 | 风险行小结 |
|---|---|---|---|---|
| **① FetchResult 侧通道（零库改、零 raw 改）** | `SourceSummary` 加 `notes` 字段（`daily_runner.py:115-122` dataclass 尾追加，默认 None）；成功分支（:514 附近）`src_summary.notes = result.notes`；`to_dict` 的 `sources` 子 dict 走 `v.__dict__` 自动带出。可顺手把 `probe_signature` 一并落到 `sources.<id>`（crossref 空响应时它就在了，白捡 HTTP 形态证据）。**变体 ①b**（把 notes 写进既有 `sources.notes` 列，零形状改动）**予以否决**：该列是人工备注面——`test_seed_literature_sources.py:68-69` 在册警告"重跑 seed 的 `notes=excluded.notes` 会抹掉人工写在 sources.notes 上的备注"，机器流水挤占人工字段必生第二案 | 仅 sqlite 单列 `summary_json` 的 **JSON 内部形状**加键：无 schema 迁移、无新库文件面；旧行缺键读法 `.get()` 天然容缺 | summary_json 读方全仓普查（s924-17 §6 同口径）均为容缺读；attribution:59 `nsources`=sources **键数**不受源内字段影响；测试无钉源内键集（`test_scheduler_cli.py:117` 那处钉的是 CLI 入参非形状） | 低。但**证据强度弱**：notes 是 fetcher 自述字符串，不证明响应体真空；且 `manual_ingest` 不置 notes ⇒ 覆盖面需逐 fetcher 补 |
| **②a daily_runner 空 raw 哨兵行（只动 JSONL 面）** | :492 守卫改 `if result.raw_records: append_many(...) else: append(src_id, {"_kind":"empty_response","run_id":run_id,"ts":...,"probe":...,"http_status":200 语义由 fetcher 传,"fetched":0})`。哨兵必须：`_kind` 字段打头、单行、排在正常记录之前可 grep 过滤 `-v '"_kind"'` | **写 gitignored 现场** `raw/<日>/<src>.jsonl`（本仓唯一无 git 还原点的数据面）：行数口径被 +1/空源/日——任何 `wc -l` 式历史对账需重述口径（census:97 型「抓回 0 篇所以文件不存在」的反向推理自此失效，**这正是本设计的目的**）；`_file_for` 会先 `mkdir` 再在 `append_many([]` early-return（jsonl_archive.py:44-47,75-76），**禁止**用「直接调 `append_many([])`」实现哨兵，必须走显式 `append(哨兵 dict)`，否则会造出空日期目录污染 `list_dates` | 生产码零读方（§2）；测试 `TestJsonlArchive.iter_day` 直调不受 runner 改动影响；人即席脚本遇 `_kind` 行需跳过（`iter_day` 已 suppress JSONDecodeError 但不滤语义行——文档给过滤式即可，不改读 API） | 中。落盘面新增记录类型，历史取证档（不回改）与本档之后「文件存在性」语义分代：分代点＝实施 commit 日期，须写进实施档头 |
| **②b 空＋失败全谱哨兵（②a 扩展）** | rate_limited/schema_changed/failed 分支（:446-486）也各落一行 `{"_kind":"fetch_failure",...}` | raw 层自此成为全谱审计面（与「raw＝原始 payload 归档」的模块定位**冲突**：failure 没有 payload 可归档，写的是状态流水） | 同 ②a ＋ 失败 run 的日志/DB 与 raw 三处冗余 | 高（语义漂移）。**不建议**：失败谱在 summary 层已可区分（§1 表第 2 行），raw 层只补「200 空集」这一种盲区即可 |

**推荐**：**①＋②a 组合**。①管「run 审计要一眼可见空」（summary 内 notes/probe 直读）；②a 管「raw 现场自证当天确实发过请求且拿到空集」。②b 越界。若只许一个，选 ②a——它填的是本档标题那层不可区分性；①的 notes 面实施更轻但不改 raw 缺口。

## 4. 哨兵记录格式（②a 的落盘契约）

```json
{"_kind": "empty_response", "schema": 1, "run_id": 45, "trigger": "scheduler", "source_id": "acta", "probe_signature": "<fetcher.health_signature()>", "fetcher_notes": "empty result", "ts": "2026-09-25T…Z"}
```
- `_kind` 首键＝过滤器锚点（`grep -v '"_kind"'` 得纯 payload 视图，与实施前逐位相同）；`schema` 版本键预留。
- 写入用既有 `JsonlArchive.append()`（单条、`_LOCK`＋append 模式，jsonl_archive.py:52-66 现路径），**不新增写原语**；失败沿用 :494 的 `except Exception: logger.warning` 吞并继续语义（哨兵写失败不得翻掉 run）。
- win32 坑：`append` 已 `newline="\n"` 钉死行尾（:63-64），哨兵沿用即可；判 CR 污染一律 `rg -lP '\x0d'`，别用 `rg -l $'\r'`（§十二工具坑）。

## 5. 向后兼容与回填

- summary 侧（①）：旧行缺 `notes/probe` 键 → `.get()` 默认 None，判「升级前」；不引入版本字段（同 s924-17 §5.3 口径，避免双事实源）。
- raw 侧（②a）：实施日之前的「无文件」仍按旧语义读（＝可能空可能没跑）；实施日之后「有 `_kind` 行」＝空响应实证、「无文件」＝未跑或失败。历史不回补：无证据源可回填（响应体未被记录，回填＝造数）。

## 6. 验收配方（给实施班，本档零执行）

1. 单测：`_Summary` 替身扩展（test_scheduler_cli.py:24-31 处零影响，因它自带 to_dict）；新增鉴别用例「空 raw_records ⇒ raw 文件恰含 1 行 `_kind` 哨兵」「非空 ⇒ 零哨兵」；变异自证＝删 else 分支 ⇒ 目标用例必红（§十二.2 变异坑：注入要能真杀死用例，杀不死不算承重）。
2. 定向套件（沙盒强制）：`LITERATURE_FEED_DATA_ROOT=<repo>\tmp\<班名>\feedroot` 下跑 `-k "literature_feed or jsonl or scheduler"`，并贴 `--collect-only` 节点数（防空选择器假绿）；`-k` 须点名钉桩件 `test_literature_feed_fetchers.py::…::…`（:248 钉 `notes == "empty result"` 字面量——①a 只消费不改 crossref 文案则恒绿，改文案必见其红，红即判别力证明）；收班复验真库 `data/literature_feed` 件数/总字节/聚合摘要三项逐位不变（本档取证时现值：181 件／21,059,126 B）。
3. 若动到导出/下载面则撞 §八在册红门——本设计不触及，无需加跑 `download_buttons or export_gate`。

## 7. 边界自证

本档产出仅此一件新文档；`src/`、`tests/`、`data/` 零接触；`exporters.py` 族与 app.py/pytest.ini/requirements-lock.txt（他班在途）零接触（git status 对照见 result 证据节）。
