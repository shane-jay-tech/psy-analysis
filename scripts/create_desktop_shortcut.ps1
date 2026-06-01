$desktop = [Environment]::GetFolderPath('Desktop')

# Filename via codepoints to avoid UTF-8/GBK mangling
# 0x5FC3 0x7406 0x5206 0x6790 0x7CFB 0x7EDF = psychology analysis system
$nameChars = 0x5FC3, 0x7406, 0x5206, 0x6790, 0x7CFB, 0x7EDF
$name = -join ($nameChars | ForEach-Object { [char]$_ })
$shortcutPath = Join-Path $desktop ($name + '.lnk')

# Remove old (e.g. previous run.bat shortcut)
if (Test-Path -LiteralPath $shortcutPath) { Remove-Item -LiteralPath $shortcutPath -Force }

# Project venv pythonw.exe is required: heavy ML deps (sentence-transformers,
# factor-analyzer, semopy) live only in .venv, system Python cannot run launcher.
$pythonw = 'D:\code\psy-analysis\.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) {
    Write-Error "venv pythonw.exe not found at $pythonw. Run: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = $pythonw
$sc.Arguments = '"D:\code\psy-analysis\launcher.pyw"'
$sc.WorkingDirectory = 'D:\code\psy-analysis'
$sc.IconLocation = 'D:\code\psy-analysis\assets\app.ico,0'
# Description: "psychology analysis system - desktop app" via codepoints
$descChars = 0x5FC3, 0x7406, 0x5206, 0x6790, 0x7CFB, 0x7EDF,
             0x0020, 0x002D, 0x0020,
             0x684C, 0x9762, 0x7AEF, 0x5E94, 0x7528
$sc.Description = -join ($descChars | ForEach-Object { [char]$_ })
$sc.WindowStyle = 1
$sc.Save()

[Console]::OutputEncoding = [Text.Encoding]::UTF8
Write-Host ('Created: ' + $shortcutPath)
Write-Host ('Target:  ' + $pythonw)
Write-Host ('Args:    "D:\code\psy-analysis\launcher.pyw"')
Write-Host ('Icon:    D:\code\psy-analysis\assets\app.ico')
Write-Host ('Exists:  ' + (Test-Path -LiteralPath $shortcutPath))
