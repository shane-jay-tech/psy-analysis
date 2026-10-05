# psy scripts/ .bat/.ps1 绝对盘符与 POSIX 重定向只读普查（s1002-20，2026-10-06）
- 承 s924-14 遗留 3；对象=scripts/ 全部 .bat/.ps1（现 3 件：run_daily_feed.bat〔已治理〕＋create_desktop_shortcut.ps1＋install_desktop_shortcut.ps1）。
- 判据复算命令（见 result 证据节）；扫描用 python 字面计数（s924-14 坑：>/dev/null 会撞 GBK/MSYS 转义）。
- 本单只读零改码。

## 读数总表
| 文件 | D: 命中 | /dev/null 命中 | 状态 |
|---|---|---|---|
| run_daily_feed.bat | 0 | 0 | s923-11/s924-14 已治理，零残留 |
| create_desktop_shortcut.ps1 | 6 | 0 | 硬编码形态在册 |
| install_desktop_shortcut.ps1 | 1 | 0 | 硬编码形态在册 |

## 逐条清单与改法建议

### create_desktop_shortcut.ps1（6 处，全部 D:\code\psy-analysis 前缀）
| 行 | 内容摘要 | 改法建议 |
|---|---|---|
| :14 | $pythonw = venv pythonw.exe | `$PSScriptRoot` 推导：`Join-Path $PSScriptRoot '..\.venv\Scripts\pythonw.exe'` |
| :23 | Arguments = launcher.pyw | 同上 `..\launcher.pyw` |
| :24 | WorkingDirectory | `Split-Path $PSScriptRoot -Parent`（=仓根） |
| :25 | IconLocation app.ico | `..ssetspp.ico` |
| :37-38 | Write-Host 展示串 | 跟随上述变量插值，不单独硬编码 |

### install_desktop_shortcut.ps1（1 处）
| 行 | 内容摘要 | 改法建议 |
|---|---|---|
| :19 | 提示文案「放在 D:\code\psy-analysis\scripts\ 下面」 | 改 `$PSScriptRoot` 插值（文案性，风险最低） |

### /dev/null 族
0 命中——s924-14 治理后全 scripts/ 无 POSIX 重定向残留。

## 边界
- schtasks 注册侧绝对 /TR（s924-14 另判面）不在本单；.ps1 的 D: 前缀属「桌面快捷方式安装器」语义——换机器部署本就要手改，**改法建议非必改项**（与 .bat 的流水线硬编码风险等级不同），是否治理交主班裁。
