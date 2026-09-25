# psy `data/` 治理对账单：kaoyan.db 孤儿归因＋raw 轮转＋wal 体检＋benchmark 草稿件裁决

> 班名 `qoder-executor-20260925-0800-psy58` ｜ 单号 s924-70 ｜ 取数时刻 2026-09-25 08:03–08:15 ｜ cwd `D:\code\psy-analysis` ｜ HEAD `928e62e`（现取）
> **全程只读**：未启动 app、未跑 pytest、未删/移/改任何 `data/` 文件、未对真库开过任何 sqlite 句柄。
> 所有 sqlite 取证都在 `tmp/qoder-executor-20260925-0800-psy58/` 下的**副本**上做（`copy2` 三件套＋sha8 逐位自证）。
> ⚠️ 本仓 `data/` 整层被 `.gitignore:42` 忽略 ⇒ **git 完全没有还原点**，故本档所有"可删"判断都必须自带可还原证明，且**一律交人工**。

## 〇、零写自证（先给门禁，再给结论）

| 判据 | 读数 |
|---|---|
| `data/` 全树（前／后） | 187 条目 / 21,103,172 B ⇔ 187 / 21,103,172 B |
| 真库不变量 `data/literature_feed` | **181 件 / 21,059,126 B**（与派单在册值逐位同） |
| 前后逐件 diff（size＋mtime＋sha8） | **0 项差异**（含 `feed.sqlite`／`-wal`／`-shm` 三件的 mtime 全部未前进） |
| 写句柄被拒（在沙盒副本上） | `CREATE TABLE`／`DROP TABLE`／`VACUUM` 三种纯写语句在 `mode=ro` 下全抛 `attempt to write a readonly database`；`PRAGMA query_only=ON` 同样抛 |

```
$ cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 python -c "
import os,hashlib,json,datetime
root='data'; rows=[]
for dp,dns,fns in os.walk(root):
    dns.sort()
    for f in sorted(fns):
        p=os.path.join(dp,f); st=os.stat(p)
        rows.append((p.replace(chr(92),'/'),st.st_size,datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
                     hashlib.sha256(open(p,'rb').read()).hexdigest()[:8] if st.st_size<=8_000_000 else 'BIG'))
print('entries',len(rows),'bytes',sum(r[1] for r in rows))
lf=[r for r in rows if r[0].startswith('data/literature_feed/')]
print('literature_feed',len(lf),sum(r[1] for r in lf))
"
```

⚠️ **一条本单自己踩到并现场纠正的错法读数**（写给下一班）：
- `UPDATE fetch_runs SET id=id` 在 `mode=ro` 下抛的是 `no such column: id`——那是**准备期**的 schema 错误，**不是只读门禁**，拿它当"零写主证"等于没证。零写探针必须用不依赖既有列名的纯写语句（`CREATE TABLE`／`VACUUM`）。
- `rg kaoyan src tests scripts app.py conftest.py pyproject.toml` 会因 `conftest.py`／`pyproject.toml` **不存在**而 **rc=2**（但已扫到的命中照打）。只看 rc 会把"参数含缺失路径"读成"扫描失败/零命中"。

---

## 一、`data/kaoyan.db`：孤儿归因＋删除裁决

### 现值
| 项 | 读数 |
|---|---|
| 路径 | `data/kaoyan.db` |
| 字节 | **0** |
| mtime | **2026-09-19 05:41:26.584**（Birth/Modify/Change 三者同值 ⇒ 自创建起一字未动过） |
| 侧车 | **无** `-wal`、无 `-shm`（`ls data/` 全列只有 `benchmark_history/`、`kaoyan.db`、`literature_feed/`、`perf_history.jsonl`） |
| git | `git check-ignore -v data/kaoyan.db` 命中 `.gitignore:42` ⇒ 未被跟踪，**git 无还原点** |

### 零引用（三轨对数，非单轨）
```
$ rg -in "kaoyan" src tests scripts app.py pytest.ini            # rc=0，1 命中
$ git grep -niE "kaoyan" -- .                                    # HEAD 树全量
$ PYTHONIOENCODING=utf-8 python -c "
import os
skip={'.git','node_modules','.venv','data','tmp','__pycache__','.pytest_cache'}
hits=[];n=0
for dp,dns,fns in os.walk('.'):
    dns[:]=[d for d in dns if d not in skip]
    for f in fns:
        if f.endswith(('.py','.ini','.toml','.bat','.ps1','.md','.json','.yaml','.yml','.txt','.cfg')):
            p=os.path.join(dp,f); n+=1
            for i,l in enumerate(open(p,encoding='utf-8',errors='replace').read().splitlines(),1):
                if 'kaoyan' in l.lower(): hits.append((p,i))
print('scanned',n,'hits',len(hits))
print('code hits',[h for h in hits if os.sep+'docs'+os.sep not in h[0]])
"
```
读数：python 全仓字面扫 **834 件 → 12 命中**，其中 **11 命中全在 `docs/insights/`（既往面簿的叙述文字）**，代码面 **仅 1 处**：
`tests/test_app_defaults_keys_snapshot.py:11` —— **卷宗措辞订正**：它在**模块 docstring 第 11 行**（"…三向互证（kaoyan 三向等式风格）…"），不是 `#` 注释。该处是散文提及，无任何路径/建库语义。⇒ **"psy 侧零代码引用"成立**。

### 0 字节机理（可复跑，不靠断言）
```
$ PYTHONIOENCODING=utf-8 python -c "
import sqlite3,os
p='tmp/qoder-executor-20260925-0800-psy58/probe.db'
c=sqlite3.connect(p); c.execute(\"SELECT name FROM sqlite_master\").fetchall(); c.close()
print('open+read+close ->',os.path.getsize(p),'B')     # => 0
c=sqlite3.connect(p); c.execute('CREATE TABLE t(x)'); c.commit(); c.close()
print('after one write ->',os.path.getsize(p),'B')     # => 8192
"; rm tmp/qoder-executor-20260925-0800-psy58/probe.db
```
⇒ **"0 B ＋ 无侧车"＝"被打开并查询过、从未写入"**：SQLite 只在首次写事务才落 100 字节页头；查询空库不落头、也不长 `-wal`/`-shm`。

### 归因（写手在本仓之外，指向 kaoyan 侧工具在错误 cwd 运行）
1. **机理锚（跟踪件，权威）**：`kaoyan-system/src/lib/db.ts:14`
   `const DB_PATH = configuredDbPath || path.join(process.cwd(), 'data', 'kaoyan.db');`
   ⇒ 未设 `KAOYAN_DB_PATH` 时**路径随 cwd 漂移**，且目标不存在就建一个空文件（`better-sqlite3` 默认 `OPEN_READWRITE|OPEN_CREATE`）。
   同型写法在 kaoyan 侧广度：`rg -n -F "|| 'data/kaoyan.db'" src scripts | wc -l` → **55 处**；`process.cwd(), 'data', 'kaoyan.db'` 形态命中 `src/lib/db.ts` 与 4 个 `scripts/*.ts`。
2. **时间窗吻合（旁证）**：`data/kaoyan.db` 出生时刻 05:41:26 正落在 kaoyan 仓一次活跃会话中间——按 mtime 扫 `kaoyan-system`（排除 `.git`/`node_modules`/`.next`）05:20–06:00 命中 **13 件**，最近的两件是 `tmp/audit/f2b-scoped-dryrun.mjs`（**05:39:39**）与 `docs/insights/b011r-expl-rewrite-material-20260918.md`（05:42:17）。
3. **头号候选写手**：`kaoyan-system/tmp/audit/f2b-scoped-dryrun.mjs:9`
   `const db = new Database('data/kaoyan.db');` —— **纯相对路径**，早于本件 1 分 47 秒落盘。该件第 4 行 `import Database from 'better-sqlite3'` 走 ESM **文件相对**解析 ⇒ 从**任何** cwd 都能 import 成功，唯独 `data/kaoyan.db` 跟着 **cwd** 走：这正是"脚本跑通了、文件落错仓"的组合条件。第 15 行的 `db.prepare(...)` 在空库上抛错 → 进程退出，留下 0 B 空件（与 §机理 完全一致）。
4. **同族病灶已被 kaoyan 侧修过**：commit `1eb9823`（9-19 06:53，k918-27）"两审计脚本假只读修复——审计路径 readonly 直连（不落迁移/WAL）"，说明确有一批审计脚本以可写方式直连相对路径 db。

🔴 **未坐实部分（如实标注）**：本机没有进程/shell 审计日志能直接证明"05:41 那次调用的 cwd 就是 `D:\code\psy-analysis`"，且候选件在 kaoyan 的 `tmp/` 里（scratch 件，非跟踪证据链）。⇒ 归因等级＝**机理成立＋时间窗吻合＋候选唯一**，不等于铁证。要坐实需 `security` 审计策略或 PowerShell PSReadLine 历史，均超出只读面。

### 裁决：**建议删除，交人工执行**（本单不删）
理由：① psy 侧零代码引用（三轨对数）；② 0 B ⇒ **不携带任何信息**，删除属信息无损；③ 可还原性**可证**（见下）；④ 留在原地持续误导"psy 有个 kaoyan 库"的判断（已有 ≥4 份面簿为它花费篇幅）。

删除命令草稿（**执行前置条件：先跑还原点自证两行**）：
```
# 1) 证伪"里面有东西"：必须读回 (no tables)
PYTHONIOENCODING=utf-8 python -c "
import sqlite3;c=sqlite3.connect('file:data/kaoyan.db?mode=ro',uri=True)
print([r[0] for r in c.execute(\"SELECT name FROM sqlite_master\")]); print('journal_mode',c.execute('PRAGMA journal_mode').fetchone()[0])"
# 2) 记录指纹（0 B 文件的 sha256 是常量，故"还原点"＝一条重建命令）
sha256sum data/kaoyan.db     # 实测 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 ＝ 空件常量
# 3) 删除（人工授权后才跑）
rm data/kaoyan.db
# 4) 可还原证明：任何时刻一条命令复原到逐位相同
python -c "open('data/kaoyan.db','ab').close()"
```
> ⚠️ 本机 **`sqlite3` 命令行工具不存在**（`which sqlite3` 空），别照别的仓的配方写 `sqlite3 <db> ".tables"`——会 command-not-found；上面一律用 python 的 sqlite3 模块。
> 若第 1 步列出任何表名，或第 2 步 sha256 不等于空文件常量 ⇒ **本裁决当场作废**，退回"待人工看图"。

---

## 二、`data/literature_feed/raw/`：轮转现状

### 🔴 否证卷宗前提：**"raw/ 无轮转策略"不成立——90 天策略已在仓内落地且有测试**
| 在册实现 | 锚点（现取） |
|---|---|
| 策略常量 | `scripts/prune_archive.py:23-24` → `RAW_DIR = REPO/"data"/"literature_feed"/"raw"`、`RAW_KEEP_DAYS = 90` |
| 判定逻辑 | `:51-68` `rule_raw()`：按**目录 mtime** 与 `cutoff = now - 90*86400` 比较 |
| 安全默认 | `:72-76` argparse，`--apply` 才删；文档串 `:10` 自述"Default is --dry-run (print only)" |
| 特征化测试 | `tests/test_prune_archive.py:83-84`（`rule_raw(apply=False)` 不删）；面簿 `docs/insights/psy-prune-archive-guard-20260917.md`、`psy-prune-archive-fix-20260917.md`（917-33 加 `is_dir` 守卫） |
| 另一条规则 | rule1：`archive/` 超额保留 20 件（`ARCHIVE_KEEP=20`），现值 `ls archive | wc -l` = **18**（未触发） |

⇒ 本项**不需要新政策**，真正缺的是"**没人跑 dry-run 看清单**"与"**桶增长已停摆**"（见下）。

### 现值
```
$ find data/literature_feed/raw -type d | wc -l                    # => 31   ← 卷宗写 30
$ find data/literature_feed/raw -mindepth 1 -type d | wc -l        # => 30   ← 桶数实为 30
$ du -sb data/literature_feed/raw                                  # => 19,779,006 B
```
**口径差说明（错法读数 vs 正解读数）**：卷宗完成标准点名的命令含 `raw` 自身那一层，读数 **31**；按 `-mindepth 1` 才是 30 个日期桶。桶数 30 这一**实质**与磁盘一致，最老桶 **2026-06-03** ✓ 亦与卷宗一致；"20M" 应读作十进制 19.78 MB（=18.86 MiB）。

桶清单（30）：`06-03…06-09`、`06-12…06-28`（缺 06-10/06-11）、`07-05`、`07-10`、`07-15`、`08-14`、`08-24`、`09-23`。
⇒ **06-28 之后 30 天里只有 5 个桶**，最新桶 2026-09-23（与 `feed.sqlite-wal` 末次写帧同批）。轮转的"体积"压力其实来自 6 月那批密集桶，而非新增；抓取停摆另有其因，见 `docs/insights/psy-feed-scheduler-attribution-20260923.md`（本单不重开该题）。

### 按现行 90 天策略的回收清单（现在时刻算）
```
$ PYTHONIOENCODING=utf-8 python -c "
import time,os
from pathlib import Path
RAW=Path('data/literature_feed/raw'); cut=time.time()-90*86400
st=[p for p in sorted(RAW.iterdir()) if p.stat().st_mtime<cut]
tb=lambda p:(p.stat().st_size if p.is_file() else sum(sum(os.path.getsize(os.path.join(d,f)) for f in fs) for d,_,fs in os.walk(p)))
print('cutoff',time.strftime('%Y-%m-%d',time.localtime(cut)),'stale',len(st),'files',sum(1 for p in st for _ in p.rglob('*') if _.is_file()),'bytes',sum(tb(p) for p in st))
"
```
读数（2026-09-25 08:08，cutoff 2026-06-27）：**22 桶 / 132 文件 / 15,659,519 B ＝ raw 的 79.2%**；剪后余 **4,119,487 B（3.93 MiB）**。
⚠️ 该读数**随取数日漂移**（每天滑 1 桶），复算必须在同日窗口内。

### 裁决＋命令草稿（**一律不执行**）
- **A（建议，零风险）**：把 `prune_archive.py` 的 dry-run 纳入例行观察——它默认就是只读的。
  ```
  .venv\Scripts\python.exe scripts\prune_archive.py            # DRY-RUN，只打印
  ```
  本单**未代跑**（避免与兄弟班并发仓里对该脚本的在途改动混读），上面的清单是用同一条 cutoff 公式独立复算的，可与 dry-run 输出互验。
- **B（属删除动作 ⇒ 人工闸后）**：`--apply`。
  ```
  .venv\Scripts\python.exe scripts\prune_archive.py --apply    # 会 rmtree 22 个日期桶
  ```
  放行前置：① 先解决"抓取停摆"，否则剪掉 6 月桶＝剪掉**唯一存量**；② 确认 raw 的下游只需 `feed.sqlite`（写侧 `src/literature_feed/paths.py:27 JSONL_RAW_DIR` → `storage/jsonl_archive.py:40`，读侧全仓无回放消费者——`rg -F JSONL_RAW_DIR src scripts tests` 仅命中定义/导出/`ensure_dirs`/一处测试文字）；③ 因 `data/` 无 git 还原点，**必须先把待剪桶打包到 `D:\code\backups\psy-analysis\` 再 `--apply`**。
- **C（卷宗提的"20M 上限"备选）**：**不采纳**。raw 现值 19.78 MB 已在阈值上，按体积上限会当场剪到个位数桶，比 90 天口径更激进且不可解释；`RAW_KEEP_DAYS=90` 的时间口径更利于回放定位。

---

## 三、`feed.sqlite` 的 WAL 体检：结论是"备份纪律有洞"，不是"WAL 太大"

### 现值（全部来自**纯字节解析**，未开任何 sqlite 句柄 ⇒ 对生产文件零影响）
| 项 | 读数 | 卷宗前提比对 |
|---|---|---|
| `feed.sqlite` | **499,712 B** = 122 页 × 4096 | 488K ✓ |
| `feed.sqlite-wal` | **741,632 B** | 728K ✓ |
| `feed.sqlite-shm` | 32,768 B，mtime **2026-09-25 05:04:38** | 存在 ✓ |
| 页大小 | 4096（WAL 头与主库头一致 ✓） | — |
| `write/read version` | 2 / 2 ⇒ 文件确为 WAL 模式 | — |
| WAL magic / format | `0x377f0682`（大端字节序正常）/ 3007000 | — |
| **`ckpt_seq`** | **0** ⇒ 这条 WAL 自打开张起**从未记录过任何 checkpoint** | — |
| 帧数 | **180**，且 `(741632-32) % (4096+24) == 0` ⇒ **无半帧、无撕裂尾** | — |
| commit 帧 | **33**；末帧声明库大小 **132 页** | — |
| 主库头 `change_counter` == `version_valid_for` | 32 == 32 ⇒ 头自洽 | — |
| WAL/主库比 | **1.48×** | "同量级" ✓ |

```
$ PYTHONIOENCODING=utf-8 python -c "
import struct,os
db='data/literature_feed/feed.sqlite'; wal=db+'-wal'
b=open(db,'rb').read(120)
print('pg',struct.unpack('>H',b[16:18])[0],'wv',b[18],'rv',b[19],'chg',struct.unpack('>I',b[24:28])[0],
      'pages',struct.unpack('>I',b[28:32])[0],'cookie',struct.unpack('>I',b[40:44])[0],
      'validfor',struct.unpack('>I',b[92:96])[0],'ver',struct.unpack('>I',b[96:100])[0])
w=open(wal,'rb').read()
m,fmt,ps,ck,s1,s2,_,_=struct.unpack('>IIIIIIII',w[:32])
print('wal magic',hex(m),'fmt',fmt,'pg',ps,'ckpt_seq',ck,'salt',hex(s1),hex(s2))
n=(len(w)-32)//(ps+24); print('frames',n,'exact',((len(w)-32)%(ps+24))==0)
off=32; last=None; cc=0
for i in range(n):
    d=struct.unpack('>II',w[off:off+8])[1]; off+=ps+24
    if d: cc+=1; last=d
print('commit_frames',cc,'declared_pages',last,'=> folded size',last*ps)
"
```

### 沙盒实证（副本，sha8 逐位自证后操作）
| 实验 | 读数 |
|---|---|
| 从副本 `mode=ro` 走 `backup()` 出单文件快照 | **540,672 B ＝ 132×4096，与字节头预测逐位相同**；开两次比对 `(articles=175, fetch_runs=44, integrity=ok)` 两次一致 |
| 副本上 `PRAGMA wal_checkpoint(FULL)` | 返回 `(0, 180, 180)`（busy=0，180/180 折完）；`page_count` 132；**干净 close 后 `-wal`/`-shm` 双双消失、主库 540,672 B** |
| 真库 `integrity_check`（在副本上） | `ok`；`journal_mode=wal`；`user_version=0` |
| **只带主库、不带 `-wal` 打开**（模拟周备的 zip 内容） | articles **151**、fetch_runs **43** |
| 带 `-wal` 打开（实况） | articles **175**、fetch_runs **44** |

🔴 **本单最重要的发现——备份正在静默丢数据**：
`scripts/backup_user_data.py:19` 认 `FEED_DB = .../feed.sqlite`，`:35-36` **只 `zf.write(FEED_DB, ...)` 主库一个成员**，`-wal`/`-shm` 从不入包。而真库现在有 33 个未折叠的 commit 帧。⇒
**每一份 `\PsyWeeklyBackup` 产出的 zip 里的 feed.sqlite 都是旧镜像，恢复它等于回滚 24 条 `articles` ＋ 1 条 `fetch_run`（articles 的 13.7%）。**
调度实况（`schtasks /Query /TN "PsyWeeklyBackup" /FO LIST /V`）：动作为 `D:\Program\python.exe D:\code\psy-analysis\scripts\backup_user_data.py`，上次运行 **2026/9/20 09:30:01 结果 0（成功）**，下次 **2026/9/27 09:30**。"成功"恰恰掩盖了内容缺失——`verify()`（`:57-71`）只验 zip 条目数与 CRC，**不验库内行数**。
（附带一条与只读面无关但值得登记的观察：该计划任务用的是**全局** `D:\Program\python.exe` 而非 `.venv`，与纪律档 §七"psy 必用 `.venv` 解释器"是同族隐患。）

### `-shm` 残留是不是"上次非干净收尾的证据"？—— 是"没干净收尾"的证据，但**不是** `-shm` 提供的
- 决定性证据是 **`-wal` 仍有 741,632 B 且 `ckpt_seq=0`**：SQLite 默认在**最后一个连接干净关闭**时做一次 checkpoint 并**删除** `-wal`/`-shm`；本单在沙盒副本上亲眼复现了"close 后侧车消失、主库 540,672 B"。真库侧车俱在 ⇒ **末次收尾没走到 close()**。
- ❌ **不能用 `-shm` 的 mtime（09-25 05:04）说事**：只读连接也会刷 `-shm`/`-wal` 的 mtime（纪律档 §十二／§十四已记），且 05:04 之后 `-wal` 字节与 mtime 均未前进 ⇒ 那不是写入。本机现读 `tasklist /FI "IMAGENAME eq python.exe"` → **无任何 python 进程**，锁文件里的 `pid=135684`/`130036` 也都不存在 ⇒ 无活连接。**归因：未坐实**，不据此指控任何写手。
- 代码面 close 纪律**大体是有的**（全仓唯一建连点 `src/literature_feed/storage/feed_store.py:157`）：`scripts/seed_literature_sources.py:103-111` `try/finally: store.close()`；`scheduler/bootstrap_check.py:47-55` 带 `finally`；`scheduler/daily_runner.py:666` 由 `runner.close()` 负责；`ui/feed_panel.py:77` 注释声明"短生命周期：本 render 用完关"、`:114 store.close()`。⇒ 遗留嫌疑只剩两类：①`feed_store.close()` 用 `contextlib.suppress(sqlite3.Error)` **吞掉关闭期错误**（`:175-177`，真出错时无人知晓且 WAL 会留下）；②Streamlit rerun 被中断/进程被杀。两者都不需要改架构，只需**收尾自检**。
- 附带一条不影响本结论的观察：锁文件 `locks/feed_fetch.lock`（104 B，两行 `pid=…/acquired_at=…`）是**设计上的 append 审计痕迹**，释放只在 `break_stale()` 里 `unlink()`（`lock_manager.py:157-164`），`is_stale` 走 TTL 6h（`:54`）⇒ 残留**不是**缺陷。但 `_read_owner_pid()`（`:68-82`）用 `re.search` 取**第一条** pid，随着追加累积它会长期把"持有者"报成**最老那位**（当前报 130036 而非 135684）⇒ 登记为可读性缺陷，本单不修。

### 裁决：需要"**checkpoint 纪律**"，但落点在备份与收尾，不在 WAL 体积
- ❌ **不建议**为 WAL 体积做什么（0.5 MB 级，绝对体积无风险；且 `ckpt_seq=0` 说明它还从没被折过）。
- ✅ **出口 A（首选，最小且消除实际危害）**：把 `backup_user_data.py` 的 feed 采集改为 **`sqlite3.backup()` 出单文件**（或至少 `-wal` 同包＋`verify()` 里加一条 `SELECT COUNT(*) FROM articles` 的行数钉桩）。属代码改动 ⇒ **超出本单只读面，请主班另派写单**。
- ✅ **出口 B（低成本运维）**：日跑收尾追加一次 `PRAGMA wal_checkpoint(TRUNCATE)`——但**必须**按纪律以 `mode=ro` 打开源库、用 `backup()` 出快照，**绝不可读写直连**（纪律档 §十四：读写打开的最后一次干净 close 会 checkpoint，**改掉生产库文件本身**）。
- ⚠️ **本周日（09-27 09:30）之前必须知道**：下一次自动周备仍会产出一份缺 24 条 articles 的 zip。若需要一份"当下真镜像"，用纪律档 §十四/§十五 的正解手动出一份，别指望那个 zip：
  ```
  PYTHONIOENCODING=utf-8 .venv\Scripts\python.exe -c "
  import sqlite3
  src=sqlite3.connect('file:D:/code/psy-analysis/data/literature_feed/feed.sqlite?mode=ro',uri=True,isolation_level=None)
  src.execute('PRAGMA query_only=ON')
  dst=sqlite3.connect(r'D:\code\psy-analysis\tmp\qoder-executor-20260925-0800-psy58\feed-folded.db')
  src.backup(dst); dst.close(); src.close()"
  ```
  （⚠ 快照被再次打开会长出自己的 `-wal`(0B)/`-shm`(32,768B)，**不要**声称"零侧车"；纪律档 §十五.5。）

---

## 四、`data/benchmark_history/benchmark_backfill_draft.json`：草稿件裁决

### 现值
| 项 | 读数 |
|---|---|
| 路径/大小/mtime | `data/benchmark_history/benchmark_backfill_draft.json` ／ **18,209 B** ／ **2026-09-16 01:21** |
| sha256 前 16 | `092d61b07350b2bb` ⇒ 与 `docs/insights/psy-benchmark-observe-20260922.md:12` 在册值**逐位相同**（9 天来未被动过） |
| 顶层键 | `artifact=benchmark-manual-score-backfill-sidecar`、`source_file`、`source_sha256`、`generated_by`、`n_entries=30`、`manual_score_null_count=30`、`entries[30]` |
| 条目字段 | `case_id, stage, input, llm_reply, error, expected_dimensions, manual_score, manual_notes` |
| 生成方 | `generated_by="backfill-draft.py --apply（20260915-130540-dd4d；授权记录 docs/decisions/2026-09-15-psy-benchmark-scoring-baseline.md）"` ⇒ **有授权链的正式产物**，不是野文件 |

**关键三判**：
1. **它不是孤儿件**：由 `tests/fixtures/benchmark_backfill_draft.py:92` 的缺省 side-car 路径产出（`bench_path.parent/"benchmark_backfill_draft.json"`），且 `:22-23` 里 `REPO` 硬编码为 `D:/code/psy-analysis`。
2. **可再生性已证**（这条支撑"删了也无损"）：`source_sha256` 字段前 16 位 `909b479962e3fe0e` == 主 JSON `socratic_benchmark_20260909T192139Z.json` 的**实算** sha256（逐位相等，本单亲验）⇒ 源件没被改过 ⇒ 重跑同一 fixture 可原样再生：
   ```
   .venv\Scripts\python.exe tests\fixtures\benchmark_backfill_draft.py --apply
   ```
   （该件 `:101` 落盘前先备份既有 side-car、`:113` 自行复验源 sha 一致；⚠ 但它**会写 `data/benchmark_history/`** ⇒ 属写动作，本单没跑。）
3. **草稿本身仍是空壳**：`manual_score_null_count == n_entries == 30` ⇒ 自 09-16 起**人工打分零进展**，"转正"缺的是人，不是基建。

### 它会不会污染 drift 基线？—— 实况收窄（**当前惰性，非急症**，但确有一枚雷）
`scripts/evaluate_socratic_benchmark.py:128-142 _last_history_entry()` 的过滤是"不以 `_` 开头 且 以 `.json` 结尾"，**`benchmark_backfill_draft.json` 两项都满足 ⇒ 落在收集面内**（面簿 `psy-knownissues-v512-20260920.md:30` 的担心方向是对的）。但：
- 现值实测：`collected = ['benchmark_backfill_draft.json','socratic_benchmark_20260909T192139Z.json']`，`cands[-1]` 选中 **socratic_benchmark_…** ⇒ 草稿**没有**被当基线。
- 原因可解释：`:155` 归档名 stem 固定为 `f"socratic_benchmark_{ts}"`，`'s'(0x73) > 'b'(0x62)` ⇒ 只要有任一真归档在场，草稿永远排在末位之前。
- 🔴 **雷在这里**：草稿会进入基线的充要条件＝**全部 `socratic_benchmark_*.json` 都不在**（例如有人清理 history 或改名）。那时 `--track-drift` 会拿一份 shape 完全不同的 JSON（顶层 7 键、无 `results`/`n_cases`）当"上一次归档"喂给 `_compare_reports()`。两份件的 shape 实测：草稿 7 键 vs 归档 5 键（`generated_at/llm/n_cases/results/version`）。

### 裁决：**保持原位＋改名脱面**（二阶段），不转正、不删除
- **不"转正"**：`manual_score` 30/30 为空，转正＝把未打分件冒充成评分资产，且它会污染 drift 归档族。
- **不建议删除**：虽然可再生性已证（技术上删得），但它是 **dd4d 授权批的唯一机器产物**，且 `data/` 无 git 还原点；删除的收益（少一个文件）小于代价（断掉那条授权链的实物凭据）。
- ✅ **建议的正解是最小改名的对立面——给它加 `_` 前缀以退出收集面**（`_benchmark_backfill_draft.json`）：一处改名即永久消除 §四 的那枚雷，且与既有约定天然一致（同目录 `_latest_drift.md`、`_relay_calls.jsonl` 那一族 sidecar **正是**用 `_` 前缀表达"非归档件"，见 `:131-134` 的 docstring）。
  ```
  # 命令草稿（人工闸后执行；改名不删数据，且可原名改回）
  mv data/benchmark_history/benchmark_backfill_draft.json data/benchmark_history/_benchmark_backfill_draft.json
  ```
  ⚠️ **本单没有代跑**，两个理由：① `mv` 会改 `data/` ⇒ 直接违反完成标准③"对账前后 `data/` 无 mtime/条目变化"；② 改名要连带核 `psy-benchmark-observe-20260922.md`／`psy-benchmark-history-recheck-20260918.md` 里以旧名登记的 sha 锚点，属跨件动作 ⇒ 交主班裁定。
- 另须登记一条**在册陈旧项**（非本单范围）：`psy-knownissues-v512-20260920.md:30` 说 `scripts/benchmark_relay_shim.py:20` 的 `LOG_PATH` "少一层"——现读该件 `:20` 已是 `parents[1] / "data" / "benchmark_history"` 并带 s922-09/A5 订正注，且有 `tests/test_benchmark_relay_paths.py:66-69` 钉住。**该面簿描述已陈旧**，别据它重复开单。

---

## 五、汇总：四项裁决与出口

| # | 项 | 卷宗前提 | 盘上实况 | 裁决 | 是否需人工闸 |
|---|---|---|---|---|---|
| ① | `data/kaoyan.db` | 0 B／9-19 05:41／零引用 | **全中**；机理可复跑；写手指向 kaoyan 侧相对路径 db 打开（`db.ts:14`＋候选 `tmp/audit/f2b-scoped-dryrun.mjs:9`） | **建议删除**，命令草稿见 §一；cwd 归属"高度吻合非铁证" | 是（删除） |
| ② | `raw/` 轮转 | "无轮转策略" | **否证**：`prune_archive.py:23-24` 已有 90d 策略＋默认 dry-run＋特征化测试；30 桶 19.78 MB，按策略今日回收清单＝22 桶/132 件/15.66 MB(79.2%) | **不加新政策**；把 dry-run 纳入例行，`--apply` 留人工且须先打包；"20M 上限"不采纳 | 是（`--apply`） |
| ③ | WAL 体检 | "wal 与主库同量级，`-shm` 残留＝非干净收尾" | 741,632 vs 499,712 B ✓、`ckpt_seq=0`、180 帧/33 commit、预测 132 页被 `backup()` 逐位验证 ✓；**新发现：周备只 zip 主库 ⇒ 缺 24 条 articles＋1 条 fetch_run**；`-shm` mtime 不可当写证据 | **需要 checkpoint 纪律，落点在备份侧（首选改 `sqlite3.backup()`）＋收尾自检**；体积本身无害 | 是（属代码改动，超只读面） |
| ④ | benchmark 草稿 | "滞留，归档或转正" | 18,209 B／sha `092d61b0…` 与 9-22 面簿逐位同；源 sha 绑定仍成立 ⇒ 可再生；30/30 未打分；**在 drift 收集面内但未被选中** | **保持原位**；建议以 `_` 前缀改名退出收集面（草稿备好未执行）；不转正、不删 | 是（改名/删除/`--apply` 均闸后） |

### 本单一句话结论
`data/` 四项里**没有一项是"体积问题"**：真孤儿（kaoyan.db）可安全删、raw 已有策略只是没人跑、WAL 无害但**它暴露了周备静默丢 13.7% articles**、benchmark 草稿只是需要一次改名。
唯一带真实数据风险的是 ③ 的备份面 ⇒ **建议主班优先派一张写单修 `backup_user_data.py`**。

---

## 订正注（主班代附 · 2026-09-25 08:3x · 出处＝`psy58` 自己 08:27 的收工更正 note）

1. 🔴 **§四 的出口 B（"给侧车草稿加 `_` 前缀以退出收集面"）已被更优形态取代，勿再据本档草稿开改名单。**
   本档入库后，同仓 `s924-65`（psy59 出码、接班班 psy61 第三方复核）以 **`4443b3e`** 在
   `scripts/evaluate_socratic_benchmark.py` 的 `_last_history_entry` 里落了**侧车件过滤**（含 `_` 前缀件与目录排除），
   并配了 17 例钉桩（含"改名不抢末位"的正反对照）⇒ 收集面已不再吃 `benchmark_backfill_draft.json` 这类杂物，
   **改名这条既无必要、还会留一个"为什么带下划线"的悬案**。§四 原文保留不改（那是当时的实况）。
2. ⚠ **§四 所引 `evaluate_socratic_benchmark.py` 行号（`:128`／`:138-142`／`:155`）是 `4443b3e` 之前基线的读数**，
   现已整体下移 ⇒ 引用本档该节行号前，按 `git show 928e62e:scripts/evaluate_socratic_benchmark.py` 或直接现取为准。
3. ✅ §〇／§一／§二／§三 的读数主班已独立复点通过（`data/` 全树 187 文件／21,103,172 B、
   `literature_feed` 181 件／21,059,126 B、`data/kaoyan.db` 确在盘且 0 字节）——**四项裁决里"删除"类动作一律仍未执行，等人工**。


## 订正注二（主班自纠 · 2026-09-25 08:3x · 🔴 撤回上面「订正注」第 1 条）

上面那条订正注说"§四 出口 B 已被 `4443b3e` 的侧车过滤取代"——**这句不成立，主班转述了一条被子班自己撤回的结论**。
主班现已打开实现逐行复点（`scripts/evaluate_socratic_benchmark.py:138-142`）：

```
$ .venv/Scripts/python.exe -c "…读取 _last_history_entry 函数体…"
140:         if p.is_file() and not p.name.startswith("_") and p.name.endswith(".json")
```

⇒ 收集面判据是「**不**以 `_` 开头 **且** 以 `.json` 结尾」。`benchmark_backfill_draft.json` **既不是下划线前缀、又以 .json 结尾**
⇒ **它仍然被收进收集面**，`4443b3e` 的过滤只挡掉了 `UPPER.JSON`（大小写）与 `_latest_drift.md`／`_relay_calls.jsonl` 那一族 sidecar。
**所以 §四 出口 B（把它改成 `_benchmark_backfill_draft.json`）依然是活的、且正是这条过滤认得的形态**；
另一条等价解是 `s924-65` 的"想做但没做①"——把收集面收窄到**归档名形状**（能一并干掉这类"小写 .json、非归档"的三不管杂物）。
两条都属改名或改收集面，**都要单独一单、由人工或主班点头后才动**；本档 §四 原文与出口 B 的建议**按原判保留**。

（订正注第 2 条仍成立：§四 所引 `evaluate_socratic_benchmark.py` 行号系 `4443b3e` 之前基线，现已下移。
 第 3 条仍成立：四项读数主班独立复点通过、删除类动作一律未执行。）

**这条自纠的成因值得记**：`psy58` 08:27 那批 note 里，第一条写"出口 B 已被取代"、随后两条把它撤回——
主班只读到第一条就落笔追加了订正注，**没有打开被转述的那段代码**。教训：转述链上每一跳都要重验，
尤其是"某改动已经覆盖了你的建议"这类会让人**取消动作**的结论（取消动作比执行动作更没人复核）。
