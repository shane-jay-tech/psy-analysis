# s927-67 · psy 备份目录命名口径普查与统一方案材料（2026-09-29 现值，只读单）

> 取数时刻：`date` = 2026-09-29 06:36（本地北京时区）。全部读数由本单现跑命令得到，未转抄任何历史数字。
> 本单**零改名、零写备份目录**：对 `D:\code\backups\**` 只做 `ls`／`glob`／`read_text`；
> 备份根目录在 cwd（`D:\code\psy-analysis`）之外，系任务书点名的普查对象，只读口径按信箱侧同例处理。

## 1. 先纠正一条派单前提（磁盘实况 ≠ 卷宗叙述）

卷宗与锚点 `zcode-bridge/done/k921-52-kyn-backup-integrity.result.md:109` 把这件事描述成
「北京日命名 vs **UTC 日命名/UTC 时间戳命名**」混杂（kaoyan 面的实例是
`kaoyan-before-batch2-20260921-2026-09-21T10-54-11-882Z.db`）。**psy 面实测不成立**：

| 档名内时间戳 | 该文件 mtime（本地北京） | 该文件 mtime（UTC） | 判语 |
|---|---|---|---|
| `psy-20260904-232142` | 2026-09-04T23:21:42 | 2026-09-04T15:21:42 | 档名＝**北京日** |
| `psy-20260906-093000` | 2026-09-06T09:30:00 | 01:30:00 | 北京日 |
| `psy-20260913-093000` | 2026-09-13T09:30:01 | 01:30:01 | 北京日 |
| `psy-20260920-093001` | 2026-09-20T09:30:01 | 01:30:01 | 北京日 |
| `psy-20260927-093001` | 2026-09-27T09:30:01 | 01:30:01 | 北京日 |
| `psy-projects-20260905-010256`（manifest） | 2026-09-05T01:02:56 | 2026-09-04T17:02:56 | 北京日（跨日差 1 天的是 **UTC 侧**，档名跟的是本地） |
| `psy-projects_20260913-090009838` | 2026-09-13T09:00:09 | 01:00:09 | 北京日 |
| `psy-projects_20260920-090011330` | 2026-09-20T09:00:11 | 01:00:11 | 北京日 |
| `psy-projects_20260927-090004999` | 2026-09-27T09:00:05 | 01:00:05 | 北京日 |

代码侧同向坐实（两把生成器都取本地钟）：

- `psy-analysis/scripts/backup_user_data.py:69` `stamp = datetime.now().strftime("%Y%m%d-%H%M%S")` → `:71` `psy-{stamp}.zip`
- `D:\code\scripts\backup_guard.py:104` 同 `datetime.now()` ＋ `%f` 前 3 位（毫秒）→ `:105` `{name}_{stamp}.zip`

⇒ **psy 面没有"日历混杂"（无 UTC 命名件）**。真实混杂的是另外三轴，见 §2。
若照抄 kaoyan 的"UTC 日切"叙事开治理单，方向就是空的——本档按实况收窄。

## 2. 混杂计数（两轨各报一次，命令＋数字）

### 轨 1：`D:\code\backups\psy-analysis\`（psy 仓自己的周备）

```
$ python -c "import pathlib;p=pathlib.Path(r'D:/code/backups/psy-analysis');z=sorted(x.name for x in p.glob('psy-*.zip'));print(len(z),'zips');[print(' ',n) for n in z]"
5 zips
  psy-20260904-232142.zip
  psy-20260906-093000.zip
  psy-20260913-093000.zip
  psy-20260920-093001.zip
  psy-20260927-093001.zip
$ python -c "... p.iterdir() 非 .zip ..."
non-zip 文件: ['README-RESTORE.md']
```

**轨 1 读数：档 5 枚，命名口径 100% 单一**（`psy-` ＋ `-` 分隔 ＋ 秒级 `YYYYMMDD-HHMMSS`）。
轨 1 内部**不混杂**。

### 轨 2：`D:\code\backups\psy-projects\`（工作区级 backup_guard 代管）

```
$ python -c "import pathlib;p=pathlib.Path(r'D:/code/backups/psy-projects')
u=sorted(x.name for x in p.glob('psy-projects_*.zip'));d=sorted(x.name for x in p.glob('psy-projects-*.zip'))
dm=sorted(x.name for x in p.glob('psy-projects-*.manifest.json'));rm=[x.name for x in p.glob('manifest.json')]
print('underscore+ms zips:',len(u),u);print('dash zips(现存):',len(d),d)
print('dash 时间戳命名 manifest:',len(dm),dm);print('滚动 manifest:',rm)"
underscore+ms zips: 3 ['psy-projects_20260913-090009838.zip', 'psy-projects_20260920-090011330.zip', 'psy-projects_20260927-090004999.zip']
dash zips(现存): 0 []
dash 时间戳命名 manifest: 1 ['psy-projects-20260905-010256.manifest.json']
滚动 manifest: ['manifest.json']
```

**轨 2 读数：现存档 3 枚（全 `underscore` ＋ 毫秒口径）＋ 1 枚 dash 命名的历史 manifest 遗件 ＋ 1 枚滚动 `manifest.json`。**

### 合并计数（同一口径下的两个"两种命名"数法，别混用）

| 数法 | 数值 | 命令依据 |
|---|---|---|
| psy 命名备份**档**总数 | **8**（轨 1 共 5 ＋ 轨 2 共 3） | 上两段 `glob('*.zip')` 计数 |
| 北京日命名档 / UTC 日命名档 | **8 / 0** | §1 表逐枚对 mtime |
| dash＋秒级口径件（含 manifest） | **6**（轨 1 的 5 档 ＋ 轨 2 的 1 manifest） | 轨 1 `psy-*.zip` 5 ＋ 轨 2 `psy-projects-*.manifest.json` 1 |
| underscore＋毫秒级口径件 | **3**（全为轨 2 的 zip） | 轨 2 `psy-projects_*.zip` |
| 混杂的目录个数 | **1**（仅 `psy-projects`；`psy-analysis` 目录内单一口径） | 两轨各自口径是否 >1 种 |

### 三轴实况（真正的混杂在这里）

1. **分隔符**：`psy-<stamp>` / `psy-projects-<stamp>`（dash，0x2D）vs `psy-projects_<stamp>`（下划线，0x5F）。
2. **时间精度**：秒（`HHMMSS`）vs 毫秒（`HHMMSSmmm`）。
3. **manifest 方案**：轨 2 旧法＝每跑落一枚 `<档名>.manifest.json`；新法＝只写滚动 `manifest.json`。
   实测遗件指向已消失的档：

```
$ python -c "...读两份 manifest，查 zip 字段所指档是否存在..."
旧 manifest 指向档: psy-projects-20260905-010256.zip 存在? False  sha256前8: 3c4f65ce
滚动 manifest 指向档: psy-projects_20260927-090004999.zip 存在? True  sha256前8: a2b84f50
```

⇒ 轨 2 有一枚**孤儿 manifest**（描述的 zip 已被 `rotate()` 轮换删除，manifest 不参与 glob 所以没被清）。

### 混杂是**活口径**、不是纯历史件（决定方案选型的硬事实）

```
$ schtasks //query //fo CSV //nh | grep -ai "psy|backup"
"\PsyWeeklyBackup",    "2026/10/4 9:30:00", ...   ← 写轨 1（dash＋秒）
"\WorkspaceBackupGuard","2026/10/4 9:00:00", ...   ← 写轨 2（underscore＋毫秒）
```

两把生成器下次运行都在 2026-10-04 ⇒ **两种新档会持续并行产出**。这不是"旧档没洗干净"，
是"两条在跑的口径不同源"。

## 3. 为什么这事不只是难看：`rotate()`/`prune()` 按**档名字典序**淘汰

两处保留逻辑都不看 mtime、只看文件名排序：

- `D:\code\scripts\backup_guard.py:80` `zips = sorted(backup_dir.glob("*.zip"), reverse=True)` → `zips[keep:]` 逐个 `unlink()`
- `psy-analysis/scripts/backup_user_data.py:105` `sorted(BACKUP_ROOT.glob("psy-*.zip"), reverse=True)` → `zips[keep:]` `unlink()`

分隔符差异直接进入排序键。内存内模拟（零写盘）：

```
$ PYTHONUTF8=1 python - <<EOF   # 复刻 rotate() 的排序，不碰任何文件
cur = [三枚现存的 underscore 档]
mixed = cur + ["psy-projects-20261004-090000.zip"]     # 假设一枚 dash 命名的新档落进同目录
rotate_names(mixed, keep=3)
EOF
现况 keep=3 保留: ['psy-projects_20260927-090004999.zip', 'psy-projects_20260920-090011330.zip', 'psy-projects_20260913-090009838.zip'] 删除: []
混合 keep=3 保留: ['psy-projects_20260927-090004999.zip', 'psy-projects_20260920-090011330.zip', 'psy-projects_20260913-090009838.zip']
混合 keep=3 删除: ['psy-projects-20261004-090000.zip']   ← 2026-10-04 的最新档被删，2026-09-13 的最旧档被留
'-' = 45  '_' = 95
```

**机制**：`'_'`(95) > `'-'`(45)，反序排列时 underscore 族**整族压在** dash 族之上，与日期无关 ⇒
一旦同一目录内两种分隔符并存，保留窗口就按"分隔符"而不是按"时间"淘汰。方向与 kaoyan 那条
（UTC 日切 ⇒ **漏删**）**相反**：这里是**删掉更新的档、留下更旧的档**（真误删，风险更硬）。
现况之所以没踩到，是因为轨 2 只剩单一分隔符的档＋一枚不参与 glob 的 manifest 遗件。

## 4. 两案材料

### 案 A：改新不改旧 ＋ 口径注记（＋可选：把排序键改成 mtime）

- 做法：① 历史件一律不动；② 在两个备份根各留一枚 `README-NAMING.md`（轨 1 已有 `README-RESTORE.md` 可并段），
  写明「档名时间戳＝北京日；两族口径并存（`psy-*` 秒级 / `psy-projects_*` 毫秒级）；
  还原点选择请按 mtime 或 manifest 的 `created` 字段，不要按档名推断日历」；
  ③ 若要真堵住 §3 的排序风险，**最小且唯一有效**的落点是改两处保留逻辑为按 `mtime` 排序
  （`sorted(..., key=lambda p: p.stat().st_mtime, reverse=True)`）——属代码改动，另派写单。
- 覆盖写权域：`backup_user_data.py` 在 psy 仓（可派写单）；`D:\code\scripts\backup_guard.py` 在**工作区根仓**，
  不在 psy 的 cwd 内 ⇒ 若采纳 ③，两把码要分两笔、由两个仓各自主班代提交。
- 成本／风险：零移动文件（无数据风险）；注记不改变"新档继续混着产出"的事实，只让读的人不误解；
  排序键若不改，§3 那颗雷仍在（下次有人往轨 2 目录手放 dash 命名的档就炸）。
- 遗留：轨 2 的孤儿 manifest（`psy-projects-20260905-010256.manifest.json`）不属命名问题，属"轮换不清理伴随件"，
  是否删＝人工闸（见 §6）。

### 案 B：批量改名（把历史件统一到单一口径）

- 做法：把 §2 列的 8 枚档（或只轨 2 的 4 枚含 manifest）统一成一种分隔符＋精度，并同步改 `manifest.json` 的 `zip` 字段。
- 硬成本：**移动/重命名生产备份文件**＝本会话红线里的人工闸动作；一旦改错方向就同时破坏三样东西：
  1. `manifest.json` 的 `zip` 字段与 sha256 对照断链（现值：滚动件 `a2b84f50…`、孤儿件 `3c4f65ce…`）；
  2. 档名内时间戳与 mtime 不再同源 ⇒ 未来任何"按名取日历"的判断全部要重新对表；
  3. 若只改部分件，反而**制造** §3 的并存局面（现况轨 2 恰好单一，是"没炸"而不是"不会炸"）。
- 零收益面：改名并不会改变保留窗口行为（除非同时改 `rotate()`），也不会把 UTC/北京日历对齐——
  因为 §1 已实测**psy 根本没有 UTC 命名件**。

### 对照

| 维度 | 案 A | 案 B |
|---|---|---|
| 是否移动生产档 | 否 | 是（人工闸） |
| 是否可逆 | 完全可逆（只加文档／改排序键） | 改名后原档名即丢失，无 git 追踪（`D:\code\backups` 不在 psy 仓） |
| 对 §3 排序雷 | 需配 ③ 才消除 | 单改名**不消除**（除非同目录全档同分隔符，且不保证下次不新增） |
| 对 manifest 链 | 不断 | 有断链风险 |
| 需要的写权域 | psy 仓 1 处＋工作区根仓 1 处＋备份根 1 枚 README | 备份根内多枚档＋manifest 内容 |

## 5. 推荐

**推荐案 A（改新不改旧 ＋ 口径注记），并把 §3 的"按档名排序"列成独立写单建议**，理由全部来自上面的实数：

1. §1 实测 8/0——**psy 无 UTC 命名件**，案 B 想修的"日历混杂"在 psy 面不存在，改了也没有对照收益；
2. §3  `'_'`=95 > `'-'`=45 是机械事实：真正要治的是**保留逻辑的排序键**，不是文件名。案 B 治不到点上；
3. 案 B 要动 `D:\code\backups` 里的生产档与 manifest 的 `zip`／sha256 字段，属移动文件＋断校验链，
   本会话红线（人工闸）之内；本单**不执行、不代跑**。

补充给主班的选型材料（不由本单裁决）：注记若要落成文件，落点建议是
`D:\code\backups\psy-analysis\README-RESTORE.md` 追加一节（该件已存在、mtime 2026-09-27T00:41:41、1437 B）
＋ `D:\code\backups\psy-projects\README-NAMING.md` 新建。**两处都在 psy 仓之外**，写权域与提交路径需人工确认。

## 6. 待人工项（本单不动）

- 轨 2 孤儿 manifest `psy-projects-20260905-010256.manifest.json`（其 zip 已不存在）：删 or 留作历史，人工闸。
- 两把生成器的分隔符是否同源统一（`backup_guard.py:105` 与 `backup_user_data.py:71` 谁对齐谁）：跨两个仓，属人工派单决策。
- §3 排序键改 `mtime` 的写单：`backup_guard.py` 在工作区根仓、`backup_user_data.py` 在 psy 仓，需分别授权。

## 7. 取证命令附录（可复跑）

```bash
# 轨 1 / 轨 2 计数（§2 两段原样）
# 档名 vs mtime 对表（§1，逐枚）
PYTHONUTF8=1 python -c "
import pathlib,datetime
for d in (r'D:\code\backups\psy-analysis', r'D:\code\backups\psy-projects'):
    for p in sorted(pathlib.Path(d).iterdir()):
        if p.is_file():
            m=datetime.datetime.fromtimestamp(p.stat().st_mtime)
            print(p.name, m.isoformat(timespec='seconds'))"
# 生成器口径（两把码的 stamp 行）
grep -n "strftime\|f\"{name}_\|psy-{stamp}" D:/code/scripts/backup_guard.py psy-analysis/scripts/backup_user_data.py
# 保留逻辑排序键
grep -n "sorted(.*glob" D:/code/scripts/backup_guard.py psy-analysis/scripts/backup_user_data.py
# 在跑的产出口径（两枚计划任务下次运行时刻）
schtasks //query //fo CSV //nh | grep -ai "PsyWeeklyBackup\|WorkspaceBackupGuard"
```

局限如实写明：`rotate()` 的排序后果本单只用**内存内模拟**证明（不落文件、不碰目录），
主班复跑这段模拟会用到同一份推名假设，不算独立复算；要独立复算请在**沙盒目录**里造两枚不同分隔符的空 zip
跑一次 `rotate()`（勿在 `D:\code\backups\psy-projects` 真目录上做）。
