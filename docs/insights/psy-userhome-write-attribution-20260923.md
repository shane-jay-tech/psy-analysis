# psy userhome `index.json` 重写与 feed WAL 触点归因（H1／H5）· 2026-09-23

> 班：`qoder-executor-20260923-0022-psy16` ｜ 单：`s923-36` ｜ 性质：**只读归因**——未写任何库、未删任何文件、未启动 app、未跑 `AppTest`。
> 上游在册前提：`zcode-bridge/done/s922-128-userhome-archive-census.result.md`（H1「`projects/index.json` 今晨 05:56 被重写而唯一工作区文件停在 08-24 ⇒ 候选只剩『真实运行 app 的会话动作』，本班不认定」＋ H5「`data/literature_feed/` 今晨 04:16 出现 WAL/SHM 与 lock 触点 ⇒ 需归因」）。
> 🔴 **两案都已归因到机制层**（谁、经哪条命令行、留了哪三枚化石）；**只剩「12:15 那次是谁点的」这一格未坐实**，且它不影响机制结论。

## 0. 结论一句话

| 案 | s922-128 的原话 | 本班结论 | 置信度 |
|---|---|---|---|
| **H1** | index.json 被重写、原因不认定 | **一次真实 app 会话在启动/切项目时经 `set_active_project → touch_project → _write_index` 重写索引**；同型事件本夜又发生一次（09-23 12:15:14），**不是一次性偶发而是「每次开真 app 都会来一遍」** | **高**（三枚独立化石同秒对齐＋写方唯一定位到代码行） |
| **H5** | feed WAL/SHM 与 lock 触点、需归因 | **`start-bg.bat` 起的 headless 真 app 会话触发 `app_startup` 抓取**（pid 135684，`fetch_runs.run_id=44`，09-23 12:15:30→12:16:18 六源 raw 落盘）；**同窗口 11:55:07 另有 psy10 未沙盒探针留下的 `run_id=43`**（同表同形）⇒ 现存**两条僵尸 running 行＋两条锁记录并存** | **高**（log 首行与 `start-bg.bat` 第 4 行逐字对齐） |
| 附带 | — | 「唯一工作区文件停在 08-24」这句**框架需收窄**：index 里那 1 条与盘上那 1 个是**两个不同项目**（id 互不相交），两者 mtime 本就不该对表 | 高（可直接复算） |

## 1. 时间轴对照表（两案并排，全部 `ls -la --time-style=full-iso` 级读数）

复算命令（本班实际用的那两条，输出即下表）：

```
$ ls -la --time-style=full-iso ~/.psy_analysis ~/.psy_analysis/projects
$ ls -la --time-style=full-iso data/literature_feed/ data/literature_feed/locks/ data/literature_feed/raw/2026-09-23/
```

### 1.1 昨天那次（s922-128 的观察对象，09-22）

| 本地时刻 | 事件 | 化石 |
|---|---|---|
| 09-22 05:56:39 | 真 app 会话，访问「模板中心」 | `logs/usage_events_20260922.jsonl` **全文就这一行** `{"timestamp":"2026-09-22T05:56:39","event":"page_visit","page_id":"🗂️ 模板中心"}`（96 B） |
| 09-22 05:56（同分） | `index.json` 被重写 | s922-128 现场记 mtime；埋点同分钟＝**同一会话**（埋点只在真 app 里产） |
| 09-22 04:16:23（=04:16Z 本地 12:16？否，**UTC 20:16:23Z**） | `run_id=42` 起跑后死掉 ⇒ WAL/SHM/lock 三件同秒 | `feed.sqlite-wal`/`-shm` mtime 与锁记录 `pid=111228 acquired_at=2026-09-21T20:16:23+00:00` 逐秒同（s923-12 证据 5 已记） |

### 1.2 本夜这次（09-23，本班现取）

| 本地时刻（`full-iso`） | 化石 | 归属 |
|---|---|---|
| 12:15:11.146 | `logs/streamlit_run.log` 首行 `Uvicorn server started on :::8503` | 会话起点 |
| 12:15:14.381 | `~/.psy_analysis/projects/index.json`（170 B） | **H1 写点** |
| 12:15:14.386 | 父目录 `projects/` mtime 同步为 12:15:14 | 原子写（`os.replace`）的旁证 |
| 12:15:20.240 | `~/.psy_analysis/user_prefs.json`（97 B） | 同会话（偏好落盘） |
| 12:15:20.449 | `logs/` 目录 mtime ＋ `usage_events_20260923.jsonl` 建文件 | 首个 `page_visit 数据分析` 12:15:20 |
| 12:15:30.420 / .432 | `feed.sqlite` / `feed.sqlite-shm` | `page_visit 文献与选题` 同为 12:15:30 |
| 12:15:30.492 | `locks/feed_fetch.lock` 第 2 条记录 `\npid=135684 acquired_at=2026-09-23T04:15:30+00:00\n`（52→**104 B**） | **H5 写点** |
| 12:15:42 → 12:16:18 | `raw/2026-09-23/`：`hrm`(103,890B) → `jap`(30,558) → `job`(30,924) → `johp`(20,455) → `jvb`(130,387) → `personnel_psych`(29,245)，**6 源、每源约 7-8 秒** | 抓取真的跑了一遍 |
| 12:15:57（log 第 17 行**无时间戳前缀**；紧随其后的 `12:15:57.831` 是 label 空值告警） | `WARNING [lock-alert] held_by_other … held by pid=130036` | 见 §3.3（**这条告警的 pid 是错的**） |
| 12:16:18.816 | `feed.sqlite-wal`（741,632 B） | 抓取写 WAL |
| 12:16:25 | 末次 `page_visit 交付包导出`（该文件共 8 条 page_visit） | 会话点击阶梯走完 |
| 12:16:45 | `streamlit_run.log` 尾行 `Stopping...` ＋ `^C` | 会话被 Ctrl-C 掐死 ⇒ **`finish_run` 没执行** |
| 11:55:07.761（早于上表） | 锁记录第 1 条 `pid=130036 acquired_at=2026-09-23T03:55:07+00:00`、`fetch_runs.run_id=43 started_at=…03:55:07Z status='running'` | **psy10 未沙盒探针**（其 result 自证：`s923-17.result.md:63` 记四件指纹由 `c9e6a208/5815d8c2/db7e00e8/4e0139f4` 变为 `167f6a81/2d2e386b/35d020ba/010c4852`） |

**指纹三方对账**（同型可比：sha256 前 8 位，同一文件同一算法）：psy10 改法落地后自证「11:55 之后四件指纹再无变化」——**在它自己的窗口内属实**；现值 `feed.sqlite 6bf5776b / -wal 4f9f07db / -shm 07f52991` 与它记的 `167f6a81 / 2d2e386b / 35d020ba` **不同** ⇒ 差异**发生在 12:15:30-12:16:18 的那次真 app 会话**，不是 psy10 后续又写了。此即 §廿一 里「当前主库与 s923-10 副本又不一致（后续又有 checkpoint/写入）」那句的**那个「后续」**。

## 2. H1：谁写的 `index.json`

1. **写方唯一定位**：`src/utils/project_manager.py` 内改 `updated_at` 并落盘的只有三处 —— `rename_project:230`、`update_note:242`、`touch_project:286`；而 `touch_project` 的生产调用点是 `set_active_project:370`（另一处是 `save_workspace:304`，本例工作区文件没动故排除）。`set_active_project` 的调用面：`app.py:482`、`src/ui/project_panel.py:58/86/100/105/128`、`src/ui/template_center_panel.py:179` ⇒ **「打开/新建/切换项目」即重写索引**，与用户是否保存无关。
2. **内容形状自证**（只读键与时间戳，`name`/`note` 未抄录）：index 是**长度 1 的 list**，`created_at=2026-09-13 00:54:43`、`updated_at=2026-09-23 12:15:14` ⇒ 12:15:14 就是 `touch_project` 敲的 `_now_str()`，**不是**索引恢复路径（`_read_index:144` 恢复时 `updated_at` 会取**工作区文件 mtime**，那样会写成 08-24）。
3. 🔴 **收窄 s922-128 的框架**：`index.json` 里那 1 条的 id 是 `fcc90a0fd0f4`，而 `projects/` 下唯一工作区文件叫 `9b2b71937e1d.json`（`_saved_at=2026-08-24 01:53:25`，与自身 mtime 同秒）。⇒ **二者是两个不同项目**，「索引新、工作区旧」不是同一项目脱节，而是**双向孤儿并存**：索引项无工作区文件、工作区文件无索引项。（`df_b64` 字段存在 ⇒ 本班**未读其值**。）
4. **测试直写假设再次排除**（守卫面普查，本班现跑）：`tests/conftest.py:34-52` 的 `isolate_streamlit_app_test_storage` 白名单 8 件；盘上提到 `AppTest` 的 11 件里**有 6 项不在名单**（＝守卫件 `conftest.py` 自身 ＋ 下面 5 个用例文件；名单与盘面的交集是 5 件），逐件核实其自身声明——`test_experiment_engine_lazy_init:21`／`test_paper_engine_lazy_init:22`「手桩 st（非 AppTest）」、`test_instance_lock_oserror_branch:24`「零 app、零 AppTest…全跑在 tmp_path」、`test_lr_dirty_entry_matrix:14`「不导入 app.py、不跑 AppTest」、`test_questionnaire_import_panel_render:16-23`「会话桩级而非 AppTest」并留话「后来人若升级成真 AppTest，必须同时改 `_APP_TEST_FILES`」⇒ **没有一个真起 app**，测试直写面仍为零。
5. **候选排序（H1）**：① 真 app 会话切/开项目 —— **高**；② pytest 直写 —— **排除**（第 4 点＋「本夜数十次 pytest 跑、index mtime 只动 2 次」的频次不匹配）；③ 索引损坏恢复路径 —— **排除**（`updated_at` 会取文件 mtime，与实测相反）；④ 便携/受管环境变量误配 —— **低**（同会话的 `user_prefs.json`、`logs/usage_events_*` 与 `streamlit_run.log` 三处都按**默认根**落，说明没有任何覆盖生效）。

## 3. H5：feed 的 WAL/SHM/lock 触点

### 3.1 启动子已逐字对上仓内脚本

```
$ cat -n start-bg.bat
     1	@echo off
     2	cd /d D:\code\psy-analysis
     3	if not exist logs mkdir logs
     4	".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8503 > logs\streamlit_run.log 2>&1
$ sed -n '1,2p' logs/streamlit_run.log
2026-09-23 12:15:11.146 Uvicorn server started on :::8503
$ sed -n '17p' logs/streamlit_run.log
WARNING:root:[lock-alert] held_by_other lock=D:\code\psy-analysis\data\literature_feed\locks\feed_fetch.lock held by pid=130036
```

⇒ 端口 8503、`logs\streamlit_run.log` 这个重定向目标、`.venv` 解释器、CWD＝仓根（第 2 行的 `cd /d`）**四件事同时吻合**，写手即「有人跑了 `start-bg.bat`（或与之同命令行）」。**顺带解释 P5**：正因为脚本 `cd /d` 到仓根，`export_snapshot` 那个 CWD 相对默认分支一旦被点就会落在 `D:\code\psy-analysis\reports\snapshots\`（见 s923-35 方案 §2）。

### 3.2 库里那两行（**必须走副本＋`mode=ro`**）

```
$ cp -p data/literature_feed/feed.sqlite data/literature_feed/feed.sqlite-wal data/literature_feed/feed.sqlite-shm tmp/s923-36/
$ sha256sum tmp/s923-36/feed.sqlite tmp/s923-36/feed.sqlite-wal tmp/s923-36/feed.sqlite-shm | cut -c1-8
6bf5776b
4f9f07db
07f52991
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import sqlite3; con=sqlite3.connect('file:tmp/s923-36/feed.sqlite?mode=ro', uri=True); print(list(con.execute('select run_id,trigger,started_at,ended_at,status from fetch_runs order by run_id desc limit 3')))"
[(44, 'app_startup', '2026-09-23T04:15:30Z', None, 'running'), (43, 'app_startup', '2026-09-23T03:55:07Z', None, 'running'), (42, 'app_startup', '2026-09-21T20:16:23Z', '2026-09-23T03:55:07Z', 'abandoned')]
```

- `run_id=44` `started_at=04:15:30Z`＝本地 **12:15:30**＝锁记录第 2 条＝`feed.sqlite` mtime＝`page_visit 文献与选题` ⇒ **三枚化石同秒**，H5 的 12:15 触点归给 pid 135684 的 `app_startup` 抓取，**已坐实**。
- `run_id=43` 同形（`03:55:07Z`＝11:55:07＝锁第 1 条）⇒ 归 psy10 探针（其 result 自证过改法与指纹），**已坐实**。
- `run_id=42` 的 `ended_at` 恰等于 `run_id=43` 的 `started_at` ⇒ 与 s923-12 的「**7/7 逐秒算术**」链一致，且本班把它延长到 **8/8**（42→43）。
- 🔴 **为什么 `run_id=43` 没被 44 扫成 abandoned（初看像对账失效）**：按 s923-12 的算术口径 `abandon_stale_runs` 默认 `ttl_seconds=3600`，`04:15:30Z − 3600s = 03:15:30Z`，而 43 起跑于 `03:55:07Z > 03:15:30Z` ⇒ **未过 TTL，合规地不标**。⇒ 两行都是"合规僵尸"，**下次开 app 且间隔 >1 小时**就会把 43/44 一起扫成 abandoned（`ended_at` 会等于那次的 `started_at`）；**手工 UPDATE 会毁掉这条取证链**（s923-12 遗留 1 已明说）。
- `psutil`／`tasklist` 侧：两个 pid 均已不存在（s923-19 已实测 `tasklist //FI "PID eq …"` 皆「没有运行的任务」），本班不重复跑。

### 3.3 顺带钉出一枚**告警 pid 取错**的机制（只登记，不改码）

`lock_manager.py` 两处放一起看：`_write_owner_info:237-248` 是 `seek(0,2)` **追加**写（s923-12 证据 6 已记），而 `_read_owner_pid:75-82` 是 `fh.seek(1)` 读全尾后 **`re.search(r"pid=(\d+)")` ⇒ 取的是**第一条****。锁文件一旦被多次 acquire 就会累积记录（本例 104 B＝两条），此后**任何 `held_by_other` 告警报出的 pid 都是历史上第一个持有者，不是当前持有者**。实测吻合：12:15:57 告警报 `pid=130036`（11:55 那条），而当时活跃持有者是 135684（12:15:30 追加）。⇒ **归因结论要打的补丁**：既往文档/告警日志里出现的 `held by pid=…` 只能当"某个历史 acquire"读，不能当"抢锁瞬间的持有者"读。（`is_stale` 走 mtime、`break_stale()` TTL 21600 s，不受此影响。）

## 4. 交叉：done/ 与 outbox/ 执行窗对账

```
$ rg -n '2026-09-23T1[12]:' logs/claims.log | rg 'psy' | cut -c1-150   ← 11:02-12:47 的 psy 班表
```

| 窗口（claims 实测） | 班 | 与 12:15:11-12:16:45 会话的关系 |
|---|---|---|
| 11:50→12:08（s923-17） | psy10 | 11:55:07 的 `run_id=43` 落在其窗内（其 result 自证） |
| 12:08→12:13（s923-18） | psy10 | 收工于 12:13，**早于会话起点 12:15:11** |
| （12:13-12:19 空窗） | — | 会话 12:15:11 正落在此空窗 |
| 12:19→12:32（s923-19） | psy11 | 开工即观测到该现场并明确「不是本班造的，主班要查」（`s923-19.result.md:80`） |

⇒ **信箱账上没有任何一班申报过 12:15 的真 app 会话**；`start-bg.bat` 的引用只在 `done/d914-49-psy-launch-port-unify.task.md:39`（规划班描述件，非执行记录）。**H5 的机制已坐实、"谁点的"这一格未坐实**（见 §6）。

## 5. 本班自身的零副作用自证（完成标准 3）

**userhome 与 `data/` 前后 mtime／sha 逐位未动**（前＝18:11 与 18:34 两次现取，后＝18:4x 收工再取）：

| 对象 | 前 | 后 |
|---|---|---|
| `~/.psy_analysis/projects/index.json` | 12:15:14.381718200／170 B | **同** |
| `~/.psy_analysis/projects/9b2b71937e1d.json` | 08-24 01:53:25.892501700／1261 B | **同** |
| `~/.psy_analysis/user_prefs.json` | 12:15:20.240784900／97 B | **同** |
| `data/literature_feed/feed.sqlite` | 12:15:30.420985200／`6bf5776b` | **同** |
| `…feed.sqlite-wal` | 12:16:18.816653800／`4f9f07db` | **同** |
| `…feed.sqlite-shm` | 12:15:30.432029000／`07f52991` | **同** |
| `…locks/feed_fetch.lock` | 12:15:30.492887900／104 B | **同**（本班只读其内容） |

三件 sha8 与本班 18:10 首取、与主班 18:01 参考值、与 `outbox/s923-28.result.md:66-68`／`s923-29.result.md:76-78` **四方一致** ⇒ 12:16 之后**至今无人再写**。沙盒副本在 `tmp/s923-36/`（`.gitignore:29` 覆盖，不进 git）；`locks/feed_fetch.lock` **未碰**（未删未截）。

## 6. 未坐实与需裁决

1. **12:15:11 那次 `start-bg.bat` 是谁点的（未坐实）**：信箱账无申报、两班自证排除、claims 空窗吻合 ⇒ 剩三种可能（用户本人／主班手工冒烟／某班未申报的越界动作）。本班无权限查进程历史，**只能到机制层**。建议主班向 12:13-12:19 在场窗口（psy10 尾部、psy11 头部、主班自己）逐个问一句并登台账。
2. **`feed.sqlite` 还原配方是否仍要做**：§廿一 的配方是把 `tmp/s923-13/` 三件回写。现值与 psy10 副本、与 s923-13 副本**三方互不相等**，且**现态里含 12:15 那次真抓取的 6 个源的新 raw 与 WAL**——**回滚会连带抹掉它们**。⇒ 归因更新后建议主班把「还原」改判为「接受现状＋只清僵尸锁/僵尸行」，但**清库属写库，须人工授权**（s923-12 遗留 1 同判：正解是"跑一次让它自己被扫"）。
3. **H1 的双向孤儿（索引项无工作区／工作区无索引）** 是缺陷还是历史正常态：需产品口径（涉及用户项目可见性），本班**未下结论**。
4. §3.3 的"告警 pid 取第一条"是否立案：属可观测性缺陷，改法（`re.findall` 取末条）一行级，但**并发窗口内改锁码属危险面**，本班只登记。
