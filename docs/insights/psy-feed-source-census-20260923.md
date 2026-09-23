# psy 文献雷达源侧普查：`acta_psych_sinica` 为何 0 篇（2026-09-23，只读核查）

- 单号：`s923-13`（班 `qoder-executor-20260923-0022-psy9`，cwd `D:\code\psy-analysis`）
- 性质：**纯只读**。未改 `scripts/seed_literature_sources.py`、未改 `data/literature_feed/`（含 feed.sqlite 与 raw/）、未改研究面簿。
- 现场基线：HEAD `1d022ca`，开工 `git status --porcelain` 14 项（`app.py`／`pytest.ini`／`requirements-lock.txt` 三件 ` M` 属他班在途，本单未碰）。
- 上游锚点：`zcode-bridge/done/s922-17-psy-litfeed-probe.result.md:70`、`scripts/seed_literature_sources.py:37`

## 一、结论（一句话）

任务书给的二选一（「源侧注册面问题」vs「ISSN 选错」）**两个都不成立**，真因是第三种：**心理学报向 Crossref 只沉积「年粒度」的 `issued` 日期，而本仓 fetcher 的增量窗口按 `from-issued-date` 过滤 ⇒ 年粒度条目永远落不进 60 天（或生产实际用的 14 天）窗口**。ISSN 与 DOI 前缀都是对的，源侧注册面也是有的（2380 条 / 其中 2026 年 149 条）。

## 二、各源 60 天计数表（feed.sqlite 只读）

> **零副作用口径**：库是 WAL 模式（`feed.sqlite-wal` 20632B / `-shm` 32768B 现存，mtime 09-22 04:16）。按纪律档 §十三，`mode=ro` 仍会生成/推进 sidecar，故**先把三件套 `shutil.copy2` 到 `tmp/s923-13/`（`tmp/` 已被 `.gitignore:29 tmp/` 忽略）再对副本查询**，原库 mtime/size/sha 全程未动（复算见 §六）。

| source_id | enabled | fetcher_type | **60 天内新入库**（`fetched_at ≥ now-60d`） | **60 天内有 issued**（`issued_date ≥ now-60d`） | 全库累计 | 最后一次 `fetched_at` |
|---|---|---|---|---|---|---|
| jap | 1 | crossref | 10 | 17 | 47 | 2026-08-24T04:32:12Z |
| job | 1 | crossref | 8 | 8 | 31 | 2026-08-24T04:32:18Z |
| jvb | 1 | crossref | 3 | 12 | 25 | 2026-08-24T04:32:30Z |
| johp | 1 | crossref | 9 | 9 | 20 | 2026-08-24T04:32:24Z |
| personnel_psych | 1 | crossref | 4 | 4 | 12 | 2026-08-24T04:32:36Z |
| hrm | 1 | crossref | 2 | 2 | 16 | 2026-08-14T09:17:20Z |
| **acta_psych_sinica** | 1 | crossref | **0** | **0** | **0（全库从未有过 1 行）** | — |
| **adv_psych_science** | 1 | crossref | **0** | **0** | **0（全库从未有过 1 行）** | — |

⚠️ **对锚点的一处否证**：`s922-17` 的「而同为心理所刊的 `adv_psych_science` 拿满 10 篇」只在**探针轴**成立（`--probe` 是「只抓不入库」，见 `scripts/seed_literature_sources.py:79-93`）。在**库内计数轴**上 `adv_psych_science` 同样是 0 篇、全库 0 行 ⇒ 用「adv 有、acta 没有」做对照来推断「ISSN 选错」的原始论证**不成立**，两刊在库里是**同一种失败**。

## 三、`acta_psych_sinica` 注册值逐字段抄录

### 3.1 `sources` 表现值（sqlite 只读，逐字段）

| 字段 | 值 |
|---|---|
| `source_id` | `acta_psych_sinica` |
| `journal_name` | `心理学报 (Acta Psychologica Sinica)` |
| `issn` | `0439-755X` |
| `doi_prefix` | `10.3724` |
| `fetcher_type` | `crossref` |
| `enabled` | `1` |
| `last_attempt_at` | `2026-08-24T04:33:59Z` |
| `last_success_at` | `2026-08-24T04:33:59Z` |
| `probe_signature` | `crossref:acta_psych_sinica:v1` |
| `status` | `ok` |
| `notes` | `NULL` |

源表共 8 行，**全部 `fetcher_type='crossref'`**、全部 `enabled=1`；`build_fetcher`（`src/literature_feed/scheduler/daily_runner.py:81-107`）另有 `official_site` / `manual` 两条路由，**当前没有任何源挂在上面**。

### 3.2 代码侧注册值（`scripts/seed_literature_sources.py:37-38`，与库内逐字段一致）

```
dict(source_id="acta_psych_sinica", journal_name="心理学报 (Acta Psychologica Sinica)",
     issn="0439-755X", doi_prefix="10.3724", fetcher_type="crossref"),
```

### 3.3 抓取实际用了哪些字段（关键）

`src/literature_feed/fetchers/crossref.py:65-76` 构造的请求只有：

```
filter = f"issn:{issn},from-issued-date:{since}"
sort=issued  order=desc  rows=min(max(1,limit),100)  mailto=...
```

⇒ **`doi_prefix` 在 fetcher 里完全没被读取**（全仓 `git grep --no-index doi_prefix` 只见 seed 注册、`SourceConfig` 透传与测试钉值，无任何消费方）。它既没被「选错」的机会，也就无法解释 0 篇。

## 四、Crossref 源侧实测（决定性证据）

探针脚本留在 `tmp/s923-13/crossref_probe{,2}.py`（只读 GET，polite `mailto`，间隔 2s，共 10 次请求）。

| # | 查询 | 读数 |
|---|---|---|
| 1 | `GET /journals/0439-755X` | HTTP 200，title=`Acta Psychologica Sinica`，publisher=`China Science Publishing & Media Ltd.`，ISSN=`["0439-755X"]` ⇒ **ISSN 没选错** |
| 2 | `GET /works?filter=issn:0439-755X` | **total-results = 2380** ⇒ **源侧注册面是有的**，不是没沉积 |
| 3 | `filter=issn:0439-755X,from-issued-date:2026-07-25`（60 天窗口，本单复算） | **total-results = 0** ← 与库内 0 篇同形 |
| 4 | `filter=issn:0439-755X,from-issued-date:2026-01-01` | **149** 条，样例 `10.3724/sp.j.1041.2026.2200`，`issued.date-parts=[[2026]]` |
| 5 | `filter=issn:0439-755X,from-created-date:2026-07-25` | **47** 条，`created=[[2026,9,11]]` |
| 6 | 对照组 `filter=issn:1671-3710,from-issued-date:2026-07-25` | **14** 条，`issued=[[2026,9,1]]` ⇒ 同一 issuer、同一 DOI 前缀、同一过滤器，**换了刊就有** |

**读法**：#3 与 #4 之差（0 vs 149）加上 #4 的 `issued` 只有年，说明 Crossref 对这些条目的 issued 有效日期按 **2026-01-01** 参与比较 ⇒ 任何晚于 1 月 1 日的 `from-issued-date` 都会把它们全部滤掉。#5（`created` 轴 47 条）证明**内容确实在窗口内新到达**，只是 `issued` 轴看不见 —— 这就是「增量抓不到但库里也不是漏抓」的分界。#6 是同行同前缀的**正对照**，排除了网络/限流/ISSN 解析路径本身坏了的可能。

⇒ **ISSN 选错：否证。DOI 前缀选错：否证（且该字段无消费方）。源侧注册面缺失：否证（2380 条）。真因＝源侧 `issued` 日期粒度为「年」，与 `from-issued-date` 增量过滤不相容。**

### 4.1 顺带量出的一处**窗口口径不一致**（与 0 篇独立的第二个问题）

- 探针轴：`fetcher.fetch_since(None, limit=10)` → `crossref.py:166-170 _default_since(days_back=60)` ⇒ **60 天**。
- 生产轴：`daily_runner.py:72 DEFAULT_DAYS_BACK = 14` → `_compute_since()` → **14 天**，且 `since` 是**全局一个值套所有源**（`daily_runner.py:296`），`sources.last_success_at` **不做逐源水位**。

⇒ 锚点里「60 天内 0 篇」是探针口径；真实调度只看 14 天。对月刊性质的 `adv_psych_science`（#6 显示其 60 天内 14 条集中在 `issued=2026-09-01` 一期），14 天窗口同样会周期性抓空。**改源表之前，这个窗口/水位口径要先拍板。**

## 五、`raw/` 空响应样本存在性

**结论：不存在，且是结构性不可能存在。**

- 实测：`data/literature_feed/raw/` 共 **29 个日期目录 / 167 个 .jsonl**，去重后的文件名恰为 6 个，全是英文源（`hrm jap job johp jvb personnel_psych`）；**没有 `acta_psych_sinica.jsonl`、也没有 `adv_psych_science.jsonl`**（`grep -rl "acta_psych_sinica|adv_psych_science" raw/` 空）。
- 根因：`crossref.py:111-119` 空结果直接 `return FetchResult(articles=[], raw_records=[], notes="empty result")`，而 `daily_runner.py:480-481` 是 `if result.raw_records: self.archive.append_many(...)` ⇒ **空响应零字节都不落盘**。
- ⇒ 「抓回 0 篇」与「压根没发请求／请求失败」在 raw 层**不可区分**；只有 `fetch_runs.summary_json` 留着 `fetched:0,status:"ok"`。这是本次核查能推进、而 raw 帮不上忙的原因，属**可观测性缺口**（登记，不在本单修）。
- 28 条带 per-source 摘要的 `fetch_runs` 汇总：`acta_psych_sinica` 与 `adv_psych_science` **fetched 求和都是 0，nonzero 次数 0/28**，状态 `ok` 27 次 + `failed` 1 次（run 35，`2026-08-14T16:38:31Z`，错误是 WinError 10053 连接被本机中止 = 网络层，不是源层）。最近一次完整跑 run 41（`2026-08-24T04:33:58Z`）逐源：acta 0/adv 0/hrm 1/jap 8/job 6/johp 7/jvb 6/personnel_psych 1。

## 六、复算命令

```bash
# 1) 零副作用取副本（原库不动）
.venv/Scripts/python.exe -X utf8 -c "import shutil,os,pathlib; d=pathlib.Path('tmp/s923-13'); d.mkdir(exist_ok=True); \
  [shutil.copy2('data/literature_feed/feed.sqlite'+s, d/('feed.sqlite'+s)) for s in ('','-wal','-shm') if os.path.exists('data/literature_feed/feed.sqlite'+s)]"

# 2) 各源 60 天计数
.venv/Scripts/python.exe -X utf8 -c "import sqlite3; c=sqlite3.connect('file:tmp/s923-13/feed.sqlite?mode=ro',uri=True); \
  [print(r) for r in c.execute(\"select s.source_id,count(a.article_id) from sources s left join articles a on a.source_id=s.source_id and a.fetched_at>=datetime('now','-60 day') group by s.source_id order by 2 desc\")]"

# 3) 逐源历史 fetched 求和（fetch_runs.summary_json）
.venv/Scripts/python.exe -X utf8 -c "import sqlite3,json; c=sqlite3.connect('file:tmp/s923-13/feed.sqlite?mode=ro',uri=True); \
  agg={}; [agg.setdefault(k,[0,0]).__setitem__(0, agg.get(k,[0,0])[0]+(v.get('fetched') or 0)) \
  for s, in c.execute('select summary_json from fetch_runs where summary_json is not null') if s and json.loads(s).get('sources') \
  for k,v in json.loads(s)['sources'].items()]; print(agg)"

# 4) raw/ 存在性
find data/literature_feed/raw -type f | wc -l           # 167
find data/literature_feed/raw -type f -printf '%f\n'|sort -u   # 只有 6 个英文源

# 5) Crossref 注册面（本单结论的来源）
.venv/Scripts/python.exe -X utf8 tmp/s923-13/crossref_probe2.py
```

## 七、遗留问题 / 需主班或人工裁决

> 命中「研究面簿＝源表」与「抓取窗口口径」两处，本单一律**只登记不动数值**（§五 纪律 3）。

1. **要不要动 `from-issued-date` 这一策略**（唯一能实质修复 0 篇的杠杆）。候选三条，均未实施：
   - (a) acta 改用 `from-created-date` 增量（实测 #5 有 47 条）——但会改变全部 8 源的语义，且 `created` 不等于「新发表」，会把旧文新沉积当成新文；
   - (b) 给 `sources` 增一列（如 `date_field`）做逐源口径选择——**新增列＝迁移**，要占迁移号；
   - (c) acta 走 `official_site`/`manual` 路由（`build_fetcher` 已支持，现无源使用），绕开 Crossref 的年粒度。
   取舍属源表/研究面簿改动 ⇒ **未拍板，一行没改**。
2. **`DEFAULT_DAYS_BACK=14` 与探针 60 天的口径分岔**（§4.1）：调大窗口、或改成逐源水位（用起 `last_success_at`），都会改变抓取量与后续统计面输入。本单未动。
3. **`doi_prefix` 是死配置**：注册了、透传了、没有任何消费方，且被 `tests/test_seed_literature_sources.py:49-51` 钉住。要么接进 fetcher（例如按前缀过滤），要么删掉；**删/接都超出执行手授权**。
4. **改 ISSN 会撞在册钉值**：`tests/test_seed_literature_sources.py:49` 逐字钉 `issn=="0439-755X"` 与 `doi_prefix=="10.3724"`（两笔一体）。本单已证该 ISSN **是对的**，故不要照「ISSN 选错」的旧假设去改；若真要改，须连测试一起回退。
5. **重跑 seed 的既有副作用**（在册，非本单引入）：`test_seed_literature_sources.py` 自述 `upsert` 会把人工停用的源重新打开、并抹掉 `sources.notes`。若裁决走「改源表后重 seed」，这两个副作用要先知道。
6. **空响应不落 raw**（§五）＝可观测性缺口，建议单列一条待人工，不在本单修。
7. 全库 `articles` 最大 `fetched_at` 为 **2026-08-24**，此后仅有 run 42（`2026-09-21T20:16:23Z`，状态仍是 `running`，无 summary）⇒ **近 30 天调度实际没产出任何新行**，这与「acta 0 篇」是两个问题，别混成一个。
