# psy schtasks 盘点快照复核（s1007-38 追加时点节）

- 复核时点：**2026-10-08T04:07** ｜ 上游快照：s1007-01（时点 2026-10-07T02:40，zcode-bridge/done/ 信箱只读故本节落 psy insights 承接）
- 方式：PowerShell Get-ScheduledTask 只读查询（零 schtasks 写操作，同 s1007-01 自证口径）

## 现值对照表（vs 快照）

| 任务 | 快照（10-07 02:40） | 现值（10-08 04:07） | 漂移 |
|---|---|---|---|
| \PsyWeeklyBackup | State=Ready；TaskToRun=`D:\Program\python.exe D:\code\psy-analysis\scripts\backup_user_data.py`（全局解释器） | State=Ready；Execute=`D:\Program\python.exe`＋Arguments=`D:\code\psy-analysis\scripts\backup_user_data.py` | **零漂移**（解释器口径维持全局，s1007-01「维持现状」裁决前提不变） |
| \WorkspaceBackupGuard（同族观察） | 同用全局 python | Ready；Execute=`D:\Program\python.exe`＋Arguments=`D:\code\scripts\backup_guard.py --config D:\code\backup_guard.json --run` | 零漂移（同族观察口径维持） |

## 漂移项清单

- 新增/删除/禁用：**无**（psy 域两任务状态与路径全同快照）。
- 相邻同族新见：`\KaoyanBackupMirror`（Ready）——kaoyan 域备份镜像任务，登记观察不入 psy 方案（其解释器/脚本口径属 kaoyan 域自有盘点面）。

## 复现

```
$ powershell -NoProfile -Command "Get-ScheduledTask | Where-Object {$_.TaskName -like '*psy*' -or $_.TaskName -like '*Backup*'} | Select TaskPath,TaskName,State"
$ powershell -NoProfile -Command "(Get-ScheduledTask -TaskName 'PsyWeeklyBackup').Actions | Select Execute,Arguments | Format-List"
```

## 零系统操作声明

本单命令清单仅 Get-ScheduledTask 只读查询；零 /create //change /delete，任务注册表零触碰。
