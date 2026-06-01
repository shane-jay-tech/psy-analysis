# 创建桌面快捷方式：双击 = 启动心理分析系统
#
# 用法：
#   1. 在 PowerShell 中运行：
#      powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcut.ps1
#   2. 或者直接右键 → "用 PowerShell 运行"
#
# 卸载：删除桌面上的 "心理分析系统.lnk" 即可。

$ErrorActionPreference = "Stop"

# ---- 路径计算 ----
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptRoot
$batPath = Join-Path $projectRoot "run.bat"

if (-not (Test-Path $batPath)) {
    Write-Host "[ERROR] 没找到 $batPath" -ForegroundColor Red
    Write-Host "请先确认这个脚本放在 D:\code\psy-analysis\scripts\ 下面。" -ForegroundColor Red
    exit 1
}

# ---- 桌面位置（即使桌面被 OneDrive 重定向也能找对）----
$desktop = [System.Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "心理分析系统.lnk"

# ---- 创建快捷方式 ----
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 1   # 1 = 普通窗口
$shortcut.Description = "心理分析系统 — 双击启动"

# 用 cmd.exe 自带图标（有的话用 streamlit 图标也行，这里保守选 cmd）
$cmdPath = "$env:SystemRoot\System32\cmd.exe"
if (Test-Path $cmdPath) {
    $shortcut.IconLocation = "$cmdPath,0"
}

$shortcut.Save()

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  快捷方式已创建" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  位置：$shortcutPath"
Write-Host "  目标：$batPath"
Write-Host ""
Write-Host "  双击桌面上的「心理分析系统」即可启动。" -ForegroundColor Cyan
Write-Host "  关闭命令行窗口 = 退出应用。" -ForegroundColor Cyan
Write-Host ""
