# psy feed run 进程指纹字段设计稿（s924-17 · 2026-09-25 · 只读出稿）

> 班名 `qoder-executor-20260925-0430-psy40`。**本档是设计稿：零码改、零库改**；实施属写库＋schema 面，待授权单。
> 命题来源：`zcode-bridge/done/s923-10.result.md:54`「零进程指纹是根因缺口」＋ `zcode-bridge/done/s923-13.result.md` 与 `docs/insights/psy-feed-zombie-runs-20260923.md:106` 的方案表第 3 行。

## 0. 前提复核（卷宗锚点 vs 磁盘实况，两处按实况收窄）

| 卷宗前提 | 实测 | 判定 |
|---|---|---|
| 锚点 `daily_runner.py:142 "run_id": self.run_id,` | 实测在 **:143**（`rg -n '"run_id": self.run_id,' src/literature_feed/scheduler/daily_runner.py` → `143:`） | 漂移 +1 行，按实况引 :143 |
| 「summary_json 只有 12 个键」 | **HEAD 码内已是 13 键**：`abandoned_stale` 由 `1657af8`（s924-15）加进 `RunSummary.to_dict()`（`daily_runner.py:125-158`）。**盘上真库旧行仍全部是 12 键**（快照实测 34/34 行无 `abandoned_stale`，见 §2） | 两读并存：键清单以码内 13 键为准，历史 cohort 为 12 键 |

**HEAD 码内键清单（13）**：`run_id, trigger, started_at, ended_at, status, sources, extracted_articles, extracted_constructs, extracted_methods, extracted_failed, budget_exceeded, error, abandoned_stale`
**盘上历史 cohort（12）**＝上表去掉 `abandoned_stale`（与 s923-10 原文「run_id/trigger/started_at/ended_at/status/sources/extracted_*/budget_exceeded/error」一致）。

## 1. 现状解剖：指纹为什么现在归不了因

写路径只有一个 choke point，但它**只在 run 结束时落盘**：

- `feed_store.py:289 start_run()` → `INSERT INTO fetch_runs(trigger, started_at, status) VALUES(?,?,'running')` —— **不写 summary_json**（该列 NULL）。
- `feed_store.py:297 finish_run()` → `:309 UPDATE ... SET ended_at=?, status=?, summary_json=?, error_json=?`，`:315 json.dumps(summary)`。
- `feed_store.py:321 abandon_stale_runs()` → 只 UPDATE `status/ended_at`，**summary_json 永久 NULL**。
- 调用面：`daily_runner.py:391/:401`（正常收尾／顶层异常收尾）两处 `finish_run(summary.to_dict())`。

⇒ **推论（已被真库证实）**：进程若腰斩，指纹无处可查。快照实测（§2）：`fetch_runs` 44 行中 **10 行 summary_json 全 NULL**（`status='abandoned'` 8 ＋ `'running'` 2，trigger 清一色 `app_startup`）——23% 的 run 是盲行，且恰是最需要归因的那批。

三条触发路径的进程身份完全不同，现值只能靠 `trigger` 粗分：

1. 计划任务 → `scripts/run_daily_feed.bat`（.venv 钉死解释器，s923-11 修入）→ `python -m src.literature_feed.scheduler` → `trigger=scheduler`；
2. app 启动 → `bootstrap_check.py:109 run_daily(trigger="app_startup")` **在 Streamlit 进程内后台线程执行**（`:90` `thread.start()`）→ pid＝服务器进程；
3. UI 按钮 → `feed_panel.py:579 _spawn_scheduler_subprocess()` 用 `sys.executable` 起 DETACHED_PROCESS 子进程 → `trigger=ui_manual`。

现存唯一 pid 落点：`lock_manager.py:236-245 _write_owner_info()` 把 `pid=… acquired_at=…` **追加**进 `locks/feed_fetch.lock`——无 host/executable，不携 run_id，与 `fetch_runs` 只能靠时间戳人工对表（`psy-feed-scheduler-attribution-20260923.md` 即此法）。本档取证时该文件已叠两条：`pid=130036 @03:55:07`／`pid=135684 @04:15:30`，分别对应 run 43/44 两个僵尸。

## 2. 真库取证（§十二 正解：backup() 出单文件快照＋开两次比对）

```
$ .venv/Scripts/python.exe -c "src=sqlite3.connect('file:data/literature_feed/feed.sqlite?mode=ro',uri=True,isolation_level=None); src.execute('PRAGMA query_only=ON'); dst=sqlite3.connect('tmp/qoder-executor-20260925-0430-psy40/dbcheck/snap.db'); src.backup(dst)"
读快照（同一进程内开两次比对，读数 stable=True）：
total rows                     44
keycount dist                  {12: 34, 'NULL': 10}     # 13 键行 0 条：1657af8 之后尚无 run 收尾落库
NULL 按状态                     abandoned 8 / running 2（trigger 全部 app_startup）
LIKE '%abandoned_stale%'       0
真库三件套（开库前后）：feed.sqlite 6bf5776b/499712 B、-wal 4f9f07db/741632 B 逐位不变；
-shm 32768 B 尺寸不变、内容哈希漂移（07f52991→144cf1db）——只读连接触碰 WAL 索引属正常，字节数与件数不变。
```

## 3. 字段设计（4 键）

| 键 | 取值表达式 | 取值点（计算一次） | 用途 |
|---|---|---|---|
| `pid` | `os.getpid()` | 见 §4 双落点 | 腰斩行归因、与 `logs/daily_runner.log`／锁文件对表；Windows pid 会复用 ⇒ 必须与 `started_at` 联合判读 |
| `host` | `socket.gethostname()`（等价 `platform.node()`） | 同上 | 现在恒为单机值，但 NAS 映射盘/多机 checkout 场景（quant 教训：仓被搬盘后 .bat 硬编码盘符指错树）下是唯一防串台字段 |
| `executable` | `sys.executable` | 同上 | **区分 .venv 与全局解释器**——本仓真实事故面：sklearn 1.5.2(.venv) vs 1.9.1(全局)，裸 python 跑批造 ~30 条假红；s923-11 给 .bat 钉 venv 正是此患。`ui_manual` 路径用 `sys.executable` 起子进程，指纹直接暴露服务器用的哪个解释器 |
| `python_version` | `platform.python_version()` | 同上 | 与 executable 配对，识别"同路径不同版本"（venv 重建）漂移 |

统一由一个 helper 产出（单一事实源，禁两处手抄）：

```python
def process_fingerprint() -> dict[str, ...]:   # 建议放 scheduler/_fingerprint.py 或 daily_runner 模块级
    return {"pid": os.getpid(), "host": socket.gethostname(),
            "executable": sys.executable, "python_version": platform.python_version()}
```

格式约定：全为 JSON 标量字符串/整数，`executable` 存原始平台路径不做归一化（归一化交给读侧），键序按上表。

## 4. 方案对比（数据面写入风险与消费方影响）

| 方案 | 写入面 | 僵尸行可见性 | schema 改动 | 消费方影响 | 判定 |
|---|---|---|---|---|---|
| A：`RunSummary`＋4 字段，`to_dict()` 出 17 键 | 仅 `finish_run` 的 json.dumps（`feed_store.py:315`） | **不可见**（summary_json 仍 NULL，10/44 盲行照旧） | 无 | 无——全部读方 `.get()` 容缺（§5），测试不钉键集（§6） | 单用不解决根因 |
| B：`fetch_runs` 新增 `proc_json TEXT`，`start_run()` INSERT 即写 | 写点提前到 `:292`；`abandon_stale_runs` 不碰该列 | **可见**（开跑即落，僵尸行自带指纹） | 1 条 `ALTER TABLE fetch_runs ADD COLUMN`——仓内已有幂等迁移通道 `storage/migrations.py`（`run_migrations`：schema_migrations 台账＋ADD COLUMN＋fail-soft，仅启动时补齐），非裸 DDL | 新列对 `SELECT *` 读方（`latest_successful_run` 的 `dict(row)`）只增键不改语义 | 解决归因主诉求 |
| **A＋B（建议）** | helper 双写：`start_run` 落 `proc_json`，`to_dict` 尾部并入同 4 键 | 可见＋人读友好（summary 内一眼可见，`--json-summary` 行 `__main__.py:80` 顺带把 4 键打进日志） | 同 B | 同 B | **推荐**。双写同源（同一 helper 返回值），无漂移面；若嫌双写冗余，退化为 B-only 亦可，A 是便利项非必需项 |

红线自查：4 键全为进程元数据，不触内容表、不触隐私（无用户数据）、不触任何统计数值语义。风险残量：迁移在并发窗口下旧进程 INSERT 不带新列 → NULL，读侧按「缺＝升级前」处理即闭合。

## 5. 向后兼容：旧行缺键读法

1. **码层**：一律 `d.get("pid") is None` 判"未知"，**不得用 `d.get("pid", 0)`**——面板已有反面教材：`feed_panel.py:561-563` 读 `articles_new/constructs/methods`，而生产者写的键是 `extracted_articles/extracted_constructs/extracted_methods`，三个键名从未存在，`.get(..., 0)` 把键名错配静默掩成恒零读数（本档只登记否证，不在只读单内修，见遗留①）。缺键与零值必须可区分 ⇒ 默认 None／"unknown"。
2. **SQL 层**：`json_extract(summary_json,'$.pid')` 对缺键与 NULL 列都返回 NULL，天然安全；cohort 查询可用 `summary_json IS NULL`（升级前僵尸）／`json_extract(...) IS NULL`（升级前正常行）。
3. **cohort 规则（写死进实施档）**：≤`1657af8` 前收尾 → 12 键；`1657af8` 后收尾 → 13 键；本设计实施后 → 17 键（A 面）且 `proc_json` 非空（B 面）。不引入 `fp_version` 字段——键在否即可判代，加版本号是第二事实源。
4. `test_literature_feed_storage.py:178` 直接向 `finish_run(summary={"acta":{"new":3}})` 传自由 dict、`:181` 只钉 `["acta"]["new"]`，**不钉顶层键集**；`test_scheduler_cli.py:24-31` 用自带 `to_dict` 的最小替身——两处均不受加键影响（免改测试的依据）。

## 6. summary_json 全仓消费方普查（逐处分类）

复跑口径（本档自身会加命中，故排除本档）：

```
$ rg -n "summary_json" . -g '!docs/insights/psy-feed-run-fingerprint-design-20260924.md'
18 命中 / 9 文件
$ rg -n "summary_json" . -g '!docs/**'
6 命中 / 4 文件   # 码侧权威口径，不受新增 docs 影响
```

| 命中 | 分类 | 对本设计的含义 |
|---|---|---|
| `src/literature_feed/storage/schema.sql:36` | 生产者·列定义 | 注释里的形状示例 `{"acta_psych":{"new":3,...}}` 已过期（实际顶层 13 键）——实施时顺带修注释 |
| `src/literature_feed/storage/feed_store.py:309` | 生产者·唯一写点（finish_run） | A 面加键自动生效；B 面在 :292 另加 INSERT 列 |
| `src/literature_feed/ui/feed_panel.py:540,550,552` | 消费者·UI（SELECT＋json.loads，`JSONDecodeError` 吞为 `{}`） | 键缺失安全（.get）；恒零缺陷见 §5.1 |
| `tests/test_literature_feed_storage.py:181` | 消费者·测试 | 不钉键集，免改（§5.4） |
| `docs/insights/psy-feed-scheduler-attribution-20260923.md:44,59,141` | 消费者·历史取证（行 44 直查该列、141 是本设计命题出处） | 不回改 |
| `docs/insights/psy-feed-source-census-20260923.md:97,111,114` | 消费者·历史取证（:114 `where summary_json is not null`＋`.get('sources')` 双容缺——若 B 面在 start 落骨架 JSON 也不会污染此查询，因为它还要求 sources 真值） | 不回改 |
| `docs/insights/psy-feed-zombie-runs-20260923.md:15,33,51,106` | 消费者·历史取证（:106 即"start_run 即写 pid/host"提案原文，与本稿 B 面同向） | 不回改 |
| `docs/insights/psy-litfeed-data-plane-probe-20260922.md:50`、`psy-litfeed-evidence-loss-rollback-20260924.md:95` | 消费者·历史取证（run 41 样本／fetch_runs 行内形状记录） | 不回改 |

间接读方（不解析该字符串，但读整行）：`feed_store.latest_successful_run` `:339 SELECT *`（`bootstrap_check.py` 消费其 `ended_at`）、`__main__.py:80 --json-summary` 到 stdout→`logs/daily_runner.log`。

## 7. 回填策略＝不回填

- **不可知**：旧行的 pid/host 未在任何地方记录过，回填＝造数。
- **唯一残留源只覆盖 2/10**：锁文件 `locks/feed_fetch.lock` 的追加链现存 `pid=130036/135684`，按 `acquired_at`↔`started_at` 同秒可对到 run 43/44；其余 8 条 abandoned 行无任何 pid 证据。部分回填还会造成「哪些行是推测值」的二义账面——比全空更坏。
- 历史归因走已入库取证档（zombie/attribution 两档的时间戳法）；本设计只管增量。

## 8. 实施清单（交授权单，本档零执行）

1. `migrations.py`：新迁移函数 `ALTER TABLE fetch_runs ADD COLUMN proc_json TEXT`（走既有台账幂等口）；`schema.sql:30-37` 同步加列（新库直建）。
2. `feed_store.start_run(trigger, proc: dict|None)` INSERT 带列；`finish_run` 不动 `proc_json`。
3. `daily_runner`：模块级 `process_fingerprint()`；`RunSummary` 加 4 字段（默认 None）；`_run_locked` 建 summary 时注入；`to_dict` 追加 4 键；锁冲突路径（`:224` run_id=0，不落库）指纹仅随返回值/日志。
4. 测试：新增键形状正例（`proc_json` 开跑即非 NULL）＋变异鉴别（删 helper 注入行 ⇒ 用例转红）。`-k` 点名 `test_fetch_runs_lifecycle_and_stale`，配 `--collect-only` 节点数防空选择器假绿。
5. 验收加跑（psy 在册门）：`pytest tests -q -k "download_buttons or export_gate"` 仅当改动触及导出面——本清单不触及，预计不必跑，实施班自判。

## 遗留与边界

- 本档产出为设计文档一件，无码改无库改；`git status` 中本仓仅新增本文件（`?? docs/insights/psy-feed-run-fingerprint-design-20260924.md`），在途他班件（app.py/pytest.ini/requirements-lock.txt/exporters 族）零接触。
- 文献库不变量收工自证见 result「证据」节（沙盒纪律：本档取证仅 mode=ro＋backup() 快照，未跑 feed 族测试；复跑者必须 `LITERATURE_FEED_DATA_ROOT` 指 `tmp/<班名>/feedroot`）。
