# psy 用户主目录 / archive / demo_projects 三区面簿（s922-128，2026-09-22，只读）

> 班：`qoder-executor-20260922-0000-psy13`｜仓：`D:/code/psy-analysis`｜基线 HEAD `2fe3bc6`
> 口径：延续 `docs/insights/psy-data-dirs-20260919.md`（s920-26）——**只做文件级聚合**（计数/体积/mtime/写方推断），不读数据正文、不开库、不列可能含个人信息的样本内容。
> 🔒 **零 mv／零 rm／零写入／零 chmod**；`projects/` 是真实用户数据，本文所有"清理建议"只写文档、**一律不实施**。
> 本班**未跑任何测试**（遵主班 08:22 零全量口径），本单也**不需要**跑测试。

---

## 0. 锚点复核（2 条，1 处漂移）

| 任务书锚点 | 实测 | 结论 |
|---|---|---|
| `src/utils/app_paths.py:17` `APP_HOME = _configured_path("PSY_ANALYSIS_HOME", Path.home() / ".psy_analysis")` | 该行实在 **`:18`**；`:17` 是空行（`sed -n '13,18p'`：`:13 def _configured_path` … `:18 APP_HOME`） | ❌ 漂移 **−1 行**，按磁盘实况修正 |
| `.gitignore:41` `archive/` | 实测 **41**；`wc -l .gitignore` = **45** 行 | ✅ |
| （上游）`psy-data-dirs-20260919.md` §五-3（`:75-76`）「`archive/` 与 `~/.psy_analysis`（**projects/ 与 autosave 都在那儿**）未纳入本面簿」 | 两个区域属实未面簿；但括号断言**半否证**（见 §1） | ⚠️ |

---

## 1. 前提否证清单（本单 4 处，全部按实况收窄）

1. ❌ **「`~/.psy_analysis` 含 autosave 遗留件」** → 实测**该根下只有 2 个条目**：`projects/` 与 `user_prefs.json`；`autosave.json` / `autosave_meta.json` **不存在**。机制已坐实：一次性迁移在搬完后**主动 unlink 原件**——`src/utils/project_manager.py:333` `legacy_file = PROJECTS_DIR.parent / "autosave.json"`、`:348 legacy_file.unlink()`、`:349-351` 连 meta 一起删；`src/utils/autosave.py:4` 亦自述「不再写 ~/.psy_analysis/autosave.json」、`:227` 只保留 `.exists()` 探测。⇒ **09-19 面簿 §五-3 那句已过期**，本单不列"autosave 遗留区"。
2. ❌ **`demo_projects/` 不属"用户数据未面簿区"** → 它**整目录被 git 跟踪**：`git ls-files demo_projects | wc -l` = **6**（＝磁盘 6 文件，全跟踪），`git check-ignore -v` 对它**非零不命中**（`.gitignore` 45 行里无 `demo_projects`）。它是**版本化夹具**：`tests/test_demo_project_validation.py:13` 与 `tests/test_playwright_golden_research_flow.py:30` 各以 `DEMO_DIR = .../demo_projects/psychology_questionnaire_demo` 引它。⇒ 与 `data/`／`archive/` 的"无版本历史、误删不可恢复"性质**相反**，本单把它当第四类区域（可回滚区）登记。
3. ⚠️ **"projects/ 里有很多项目"不成立** → 实测**工作区文件 1 个**（`9b2b71937e1d.json`，1261 B）＋ `index.json`（170 B）。且**两者 mtime 差 28 天**：工作区文件停在 `2026-08-24 01:53`，`index.json` 却在 `2026-09-22 05:56` 被重写（见 §4 写方推断）。
4. ❌ **"测试可能直写真实 home"这一候选解释，静态穷举后不成立**（本单主动证伪了自己的假设）：`tests/conftest.py:32-52` 的 autouse 隔离 fixture **有白名单门**（`:35-36` 不在 `_APP_TEST_FILES`（`:20-29`，8 个文件）就早退）。逐件核查引用了 home/archive 写函数的测试件：共 **9 个**，其中「不在白名单**且**无自带打桩」＝**0 个**（探针 `tmp/psy13/home_write_leak_probe.py`）。最可疑的一条也已被排除——`tests/test_autosave_throttle.py` 打桩 `PROJECTS_DIR` 却**不**打桩 `INDEX_FILE`，看似会写真索引，但它在 `:37` 直接 `monkeypatch.setattr(pm, "save_workspace", _fake_save)`，调用链根本走不到 `project_manager._write_index`（真索引写点在 `:214/:231/:243/:262/:287` 与恢复路径 `:168`）。

---

## 2. 三区面簿主表（全部 `find`/`du`/`stat` 只读，命令见 §7）

| 区域 | 路径根（代码常量实测） | 条目／文件数 | 体积（字节和｜`du -sk`） | 最早 mtime | 最后 mtime | 版本历史 | 写方（实测锚） |
|---|---|---|---|---|---|---|---|
| **① 用户数据根** | `~/.psy_analysis` ＝ `APP_HOME`（`app_paths.py:18`，可被 `PSY_ANALYSIS_HOME` 覆盖 `:13-15`） | 顶层 2 项；递归 **3 文件／2 目录** | **1 463 B**｜10 KB | `2026-08-24 01:53:25`（`projects/9b2b71937e1d.json`） | `2026-09-22 05:56:39`（`projects/index.json` 与其父目录） | 仓外，git 不看 | 工作区文件＝`project_manager.py:54 file_path`→`:113-116` 临时件＋`os.replace`（原子写），锁 `:85 project_lock(PROJECTS_DIR)`；索引＝`:39 INDEX_FILE`→`_write_index`；偏好＝`user_prefs.py:23` 引 `PREFS_FILE`→`:67 save_prefs`→`:82-85` 临时件＋`os.replace`（另有删除口 `:152-153 unlink`） |
| **② 归档区** | 仓内 `archive/` ＝ `ARCHIVE_ROOT`（`app_paths.py:26`，可被 `PSY_ANALYSIS_ARCHIVE_DIR` 覆盖） | 顶层 **18 项**＝17 归档目录＋`index.json`；递归 **52 文件／18 目录** | **149 132 B（≈146 KB）**｜218 KB | `2026-08-15 00:46:17` | `2026-08-15 00:56:13`（`index.json` 与最后一个 `report.md`） | `.gitignore:41` 排除 ⇒ **零版本历史，误删不可恢复** | `archive_manager.py:37 archive_analysis`：目录名 `:54 timestamp=%Y%m%d_%H%M%S`＋`:51-53 archive_id=sha256(now.isoformat()_tag)[:16]`，布局 `:58`（有 tag）`标签/秒_id`、`:60`（无 tag）`秒_id`；三构件 `:65 data.csv`（过 `:63-64 redact_dataframe_for_storage`）＋`report.md`＋`params.json`；索引 `:99 _update_index`（`:110` 按 archive_id 去重、`:124` 按 timestamp 字符串**倒序**、`:125` 只留 200 条） |
| **③ 夹具区** | 仓内 `demo_projects/psychology_questionnaire_demo` | 顶层 1 项；递归 **6 文件／2 目录** | **6 407 B**｜28 KB | `2026-07-03 22:02:59`（父目录）／`22:03:14`（首文件） | `2026-07-03 23:30:31`（`WALKTHROUGH.md`） | **全部 git 跟踪**（6/6）⇒ 可 `git checkout` 回滚 | **无生产写方**：`rg -n 'demo_projects' app.py src/` **0 命中**；只有 2 个测试件以 `DEMO_DIR` 只读引用（`tests/test_demo_project_validation.py:13`、`tests/test_playwright_golden_research_flow.py:30`）。⇒ 它是**手工种子**，mtime 停在 07-03 且 81 天零改动，与"运行时数据"性质完全不同 |

构件构成（`find -printf '%f'` 去重，未读内容）：

- ② `archive/`：**每个归档 3 件**＝`data.csv 17／params.json 17／report.md 17`，加顶层 `index.json` = 52。单文件区间 `report.md` 最小 193 B、`data.csv` 最大 8 999 B。
- ① `~/.psy_analysis`：`json 3`（1 261／170／32 B）。
- ③ `demo_projects`：`json 3／md 2／csv 1`，即 `README.md 968`、`WALKTHROUGH.md 1 856`、`data.csv 1 192`、`expected_analysis_cards.json 833`、`literature_seed.json 883`、`questionnaire_schema.json 675`。

---

## 3. 三处落盘根的差异（本单核心读数）

| 根 | 定义 | 默认定位方式 | 换 CWD 会不会散 | 进 .gitignore | 覆盖开关 |
|---|---|---|---|---|---|
| `APP_HOME` | `app_paths.py:18` | **绝对**：`Path.home()/.psy_analysis` | 不会（家目录稳定） | 仓外不适用 | `PSY_ANALYSIS_HOME` |
| `ARCHIVE_ROOT` | `app_paths.py:26` | **绝对**：`REPOSITORY_ROOT/archive`（`REPOSITORY_ROOT` `:25` 由 `__file__` 反推，注释自述"默认值不可改变"） | 不会 | `:41` | `PSY_ANALYSIS_ARCHIVE_DIR` |
| `LOG_DIR` | `app_paths.py:27` | **CWD 相对 `Path("logs")`** | **会**——换启动目录即换日志根，历史面簿会"看似缺天" | `:16 logs/`＋`:17 *.log` | `PSY_ANALYSIS_LOG_DIR` |
| （对照）`data/` | `psy-data-dirs-20260919.md` | 仓内，`.gitignore:42` 整目录排除 | 不会 | `:42` | — |
| （缺口）`reports/snapshots/` | `src/analysis/runner.py:1078`（写点 `:1081 open(...,'w')`） | **CWD 相对 `Path("reports/snapshots")`**，且**绕过 `app_paths`** | **会** | ❌ **`.gitignore` 全文 45 行无 `reports` 条目**，`git check-ignore -v reports` → **非零不命中** | 无（只有 `export_snapshot(file_path=...)` 形参） |

⇒ 两点必须交人工/主班：① `reports/` 在本机**当前不存在**（`ls -d reports` → No such file，`find reports -type f` = 0），即「💾 保存快照」按钮（`app.py:1501`）**从未在本机被点过**；一旦被点，就会在仓根新建一个**未被忽略**的目录并污染 `git status`（与 s922-126 遗留 P5 同源）。② 五个根里**两个是 CWD 相对**（logs／reports），三个是绝对 ⇒ "全部落盘面簿"的口径本身要按根分列，不能一张表混算。

---

## 4. 写方推断与陈旧项（只登记）

- **H1｜`projects/index.json` 在今晨 05:56 被重写，而唯一的工作区文件停在 08-24 01:53。** 二者相差 28 天 ⇒ 那次动作**只碰了索引、没保存工作区**。代码侧能"只写索引"的入口是 `_write_index`（调用点 `project_manager.py:168/214/231/243/262/287`，对应 create/update/delete/rename 与索引损坏恢复）。§1-4 已穷举排除测试直写，故候选只剩"真实运行 app 的会话动作"（含白名单外的手工/子班跑 streamlit）。**本班不认定，标需人工**。同窗口旁证（不属于本区，但同一时间轴）：`user_prefs.json` mtime `2026-09-22 03:11:43`（32 B）。
- **H2｜`archive/` 自 `2026-08-15 00:56` 停摆 38 天。** 17 个归档全部落在 08-15 **00:46:17–00:56:13 的 10 分钟内** ⇒ 是**一次批量动作**（同一批里还包含同仓 `data/literature_feed/raw/` 的 08-15 那 1 个文件，见 09-19 面簿 §一「raw 日分布 08-15:1」），不是日常使用轨迹。归档区因此**不代表用户真实归档习惯**，只测得出"那次批量跑了 17 次"。
- **H3｜同秒归档真实发生过，但没撞车。** 目录名秒级前缀重复计数：`004831×2`、`004832×3`、`004927×3` ⇒ **17 个里有 8 个挤在 3 个秒内**。逃过静默覆盖的原因是 `archive_id` 参与目录名（`archive_manager.py:51-60`）且 id 派生自 `now.isoformat()`（**含微秒**，`:52`）——在册缺陷「时间戳只到秒 ⇒ 同秒两次归档静默覆盖」在 **`benchmark_history` 的 `_archive_to_history`** 一侧成立，在 `archive_manager` 一侧被 id 挡下（本单只复述，不修）。**结构性残留**：有 tag 时目录是 `标签/秒_id`（`:58`），目录名不再以时间戳开头 ⇒ 任何"按目录名字典序取末次归档"的写法在此布局下**失去时间序语义**（现值 17 个全为无 tag 布局，本轮无实例）。
- **H4｜`demo_projects/` 81 天零改动**（07-03 → 今日），无生产写方 ⇒ 不是陈旧数据问题，是"看起来像数据、其实是夹具"的**分类问题**；下次面簿别再把它列进用户数据区。
- **H5（合并视图 delta，属 `data/` 区但在本次 stat 中撞到）**：`data/literature_feed/` 下出现 `feed.sqlite-wal 20 632 B`、`feed.sqlite-shm 32 768 B`、`locks/feed_fetch.lock`，三者 mtime 均 **`2026-09-22 04:16`**。09-19 面簿的 A2 记录的是「lock 停在 08-24 12:33 的 27 天墓碑」，A3 记录「`feed.sqlite` 未开库、8-24 后数据面停摆」⇒ **今天 04:16 有人开过这个库并碰过锁**，A3 的"停摆"结论在 09-22 04:16 起不再成立。本班**未开库、未读库**（只 `find -printf '%s %TY-%Tm-%Td'` 取 stat），写方归因交主班。
- **H6**：`.gitignore:36-37` 已覆盖 `*.sqlite-wal`/`*.sqlite-shm`，且 `data/` 整目录在 `:42` ⇒ H5 不污染 `git status`。

---

## 5. 与 `data/` 面簿的合并视图（s920-26 同口径拼接）

| 区域 | 文件数 | 体积 | 最后写入 | 面簿出处 |
|---|---:|---:|---|---|
| `data/literature_feed/`（含 raw/locks/logs） | 173（09-20 读数） | 19 838 KB | 2026-08-24 12:42 →**今日 04:16 见 H5** | 09-19 面簿 §一 |
| `data/benchmark_history/` | 4 | 49 KB | 2026-09-16 01:21 | 09-19 面簿 §一 |
| `data/` 顶层散落（`perf_history.jsonl`／`kaoyan.db` 0 B 异常件 A1） | 2 | 1.5 KB | 2026-09-19 05:41 | 09-19 面簿 §一／§二 A1 |
| **小计 `data/`（本次 stat 现值）** | **181** | **20 036 661 B ≈ 19.1 MiB** | 2026-09-22 04:16（H5 三个 sidecar） | 本单只 `find -printf '%s'` 求和，未读正文 |
| ① `~/.psy_analysis` | **3** | **1 463 B** | 2026-09-22 05:56 | 本单 §2 |
| ② `archive/` | **52** | **149 132 B** | 2026-08-15 00:56 | 本单 §2 |
| ③ `demo_projects/` | **6** | **6 407 B** | 2026-07-03 23:30 | 本单 §2（**性质＝夹具，非用户数据**） |
| ④ `reports/snapshots/` | **0（目录不存在）** | 0 | 从未写 | 本单 §3 |

**体积口径提醒（沿用 09-19 §三）**：`du -sk` 是磁盘占用不是字节和——本单实测差值 `archive/` 218 KB vs 146 KB（1.49 倍）、`~/.psy_analysis` 10 KB vs 1 463 B（NTFS 簇开销），两口径**不可互换引用**。
**总量结论（只算体积，不算价值）**：三区合计 57 文件／约 154 KB，而 `data/` 一区就 19.1 MiB ⇒ **"未面簿区域"的体量其实很小，缺的是"哪些是用户数据、哪些是夹具、哪些没版本历史"的分类**（② ① 皆零版本历史，③ 全可回滚）。

---

## 6. 隐私红线自证（完成标准 3）

1. **未读任何正文**：全程只用 `ls -la`、`find -printf`（`%s %f %p` 与 `%TY..` 时间）、`du -sk`、`wc -l`、`sort/uniq -c`；**未 `cat`／未 `head`／未 `Read` 任何一个数据文件**，未开 `feed.sqlite`（连 sqlite3 客户端都未启动），未解析任何 JSON 的值。
2. **唯一例外，如实交代**：为把「17 个归档目录 ↔ 索引条目数」对上，对 `archive/index.json` 跑过一次 `rg -o '"[a-z_]+":'` **只取键名并计数**（读数：8 个键各 17 次＝17 条，键名 `archive_id/timestamp/tag/test_type/test_name_zh/file_name/n_rows/n_cols`，与 `archive_manager.py:112-121` 写入 schema 逐一对齐）。**未取任何 value**——`tag`/`test_name_zh`/`file_name` 三个字段的值可能含项目名，一律未读。
3. **未列**任何用户项目的内容、样本行、被试信息；文件名只出现哈希 id（`9b2b71937e1d`）与归档目录名（时间戳＋sha256 前缀），均为不可逆标识。
4. **零破坏动作**：`projects/`（真实用户数据）**未 mv、未 rm、未 chmod、未改名**；本文 §2–§5 的"停摆/陈旧"判定全部是登记性质，**不构成清理指令**。清理（若要做）属人工判断动作，09-19 面簿 §二 同一立场。
5. **零写入 cwd 外**：探针与中间产物一律落 `D:/code/psy-analysis/tmp/psy13/`（`.gitignore:29 tmp/` 覆盖，`git status` 不显）；`~/.psy_analysis` 侧只读。
6. **零测试执行**：遵主班 08:22「零全量跑」口径，本单未跑任何 pytest（面簿只需文件系统 stat），因此本班不产出全量失败名集（归 s922-132）。

---

## 7. 复现命令（全部只读，可整段粘贴）

```bash
cd /d/code/psy-analysis
# —— 三区通用聚合（计数／体积／mtime 区间）——
for R in "$HOME/.psy_analysis" archive demo_projects reports; do
  ls -la "$R"
  find "$R" -type f | wc -l ; find "$R" -type d | wc -l
  find "$R" -type f -printf '%s\n' | awk '{t+=$1} END{print t}'      # 字节和
  du -sk "$R"                                                          # 磁盘占用（两口径别混）
  find "$R" -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' | sort | sed -n '1p;$p'   # 最早/最后 mtime
done
# —— 构件构成（只看文件名，不读内容）——
find archive -mindepth 2 -maxdepth 2 -type f -printf '%f\n' | sort | uniq -c
find ~/.psy_analysis -maxdepth 2 -type f -printf '%s\t%p\n'
find demo_projects -type f -printf '%s\t%p\n'
# —— 同秒归档核验 ——
ls archive | sed -E 's/^([0-9]{8}_[0-9]{6})_.*/\1/' | sort | uniq -c | awk '$1>1'
# —— 跟踪与忽略口径 ——
git ls-files demo_projects | wc -l ; git ls-files archive | wc -l
git check-ignore -v archive/index.json demo_projects/psychology_questionnaire_demo/data.csv reports
wc -l .gitignore
# —— 写方锚点 ——
rg -n 'APP_HOME|PROJECTS_DIR|PREFS_FILE|ARCHIVE_ROOT|LOG_DIR' src/utils/app_paths.py
rg -n 'legacy_file|unlink' src/utils/project_manager.py
rg -n 'def archive_analysis|_update_index|timestamp =|archive_id' src/utils/archive_manager.py
rg -n 'demo_projects' app.py src/ tests/                       # 预期：src/app 0 命中，tests 2 命中
rg -n 'reports/snapshots' src/analysis/runner.py
# —— 测试泄漏静态探针（不执行任何测试）——
PYTHONUTF8=1 .venv/Scripts/python.exe tmp/psy13/home_write_leak_probe.py
# —— data/ 合并视图（只 stat）——
find data -type f -printf '%s\n' | awk '{t+=$1} END{print t}'
find data -type f -newermt '2026-09-19 12:00' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
```
