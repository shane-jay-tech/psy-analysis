# 2026-05-30 — 桌面启动器（A 方案）+ Claude Opus 4.7 → 4.8 升级

## 起源

用户两件事一起提：
1. "你能把心理分析系统做成应用形式的吗，这样用起来会不会好一点" → 经过澄清对比后选 **A 方案先做**（桌面快捷方式 + 一键 .bat 启动），等稳定了再考虑 C 方案（Tauri/Electron 原生壳）。B 方案（PyInstaller 单 exe）跳过。
2. "心理分析系统用的大模型也更新一下，GPT 5.5PRO 和 claude opus 4.8，其他两个不变" → DeepSeek V4 Pro / Kimi K2.6 不动；GPT 5.5 Pro 已经是当前配置；Claude Opus 4.7 → 4.8。

工作量评估：编辑 < 10 个字符串替换 + 写 1 个 .bat + 写 1 个 .ps1，无业务逻辑变化、无架构决策。按 CLAUDE.md "When NOT to trigger collaboration" 条款（"One-line config changes ... where the change is mechanical"），单模型直接干，未走多模型协作。

## 改了什么

### A 方案：桌面启动器

**`D:\code\psy-analysis\run.bat`** — 重写（旧版会在 streamlit 还没起来时就开浏览器，导致首次双击看到"无法访问"）：
- `chcp 65001` UTF-8 + `setlocal enabledelayedexpansion`（注意 .bat 文件本身保持 GBK + CRLF，仅运行时切码页）
- 启动前杀掉占用 8501 端口的旧进程（`netstat -ano | findstr ":8501" | findstr "LISTENING"`）
- 首次运行自动建 `.venv` 并 `pip install -r requirements.txt`
- streamlit 后台启动 → 日志写 `logs\streamlit_run.log`
- **WAIT_LOOP**：每秒 `netstat` 探测端口，最多 30 秒，就绪后才 `start "" http://localhost:8501`
- **HOLD 循环**：每 30 秒探活，关闭命令行窗口 = streamlit 也关；超时 / 异常退出有友好提示

**`D:\code\psy-analysis\scripts\install_desktop_shortcut.ps1`** — 新建。PowerShell 脚本：
- 用 `WScript.Shell.CreateShortcut` 在桌面（`[System.Environment]::GetFolderPath("Desktop")`，OneDrive 重定向也能识别）创建 `心理分析系统.lnk`
- TargetPath = run.bat，WorkingDirectory = 项目根，IconLocation = `cmd.exe,0`
- 幂等（覆盖已存在的同名快捷方式）
- 卸载 = 删除桌面上的 .lnk

**用法**：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcut.ps1
```
之后双击桌面"心理分析系统"= 启动；关命令行窗口 = 退出。

### Claude Opus 4.7 → 4.8 升级

7 处文件改动：

| 文件 | 改动 |
|---|---|
| `D:\code\.env.local` | `CLAUDE_MODEL=claude-opus-4-7` → `claude-opus-4-8`（注：此文件全 D:\code 共享，多模型协作 sub-agent 也吃这套） |
| `src/llm_gateway/quick_models.py` | UI 标签 + docstring `"Claude Opus 4.7"` → `"4.8"` |
| `src/llm_gateway/gateway.py` | 价格表 key `claude-opus-4-7` → `claude-opus-4-8` |
| `src/literature_feed/storage/budget_tracker.py` | 价格表 key `claude-opus-4-7` → `claude-opus-4-8` |
| `config/llm_providers.py` | 模型列表 + 描述文档 |
| `tests/test_literature_feed_storage.py` | 2 处 record(model=...) |
| `tests/test_llm_engine_premium.py` | `_is_reasoning_model("claude-opus-4-7")` 改名 |
| `tests/test_quick_models.py` | 4 处 fixture 改名 |

GPT 侧：`.env.local` 早就是 `gpt-5.5-pro`，`extractor.py` 默认值也是 `gpt-5.5-pro`，价格表用子串匹配（`"gpt-5.5"` 既匹配 `gpt-5.5` 也匹配 `gpt-5.5-pro`），无需改动。

## 回归

- 直接受影响的三个测试文件：105 passed in 2.61s
- 全项目（剔除 playwright e2e 因 .venv 没装 playwright）：**1347 passed, 1 skipped**, 119.77s
- 0 errors, 0 failures

## 风险点

1. **`.env.local` 全局共享** — `D:\code\.env.local` 不是 psy-analysis 专属文件，多模型协作的 Claude sub-agent（通过 `scripts/llm_call.py`）也读这套配置。把 `CLAUDE_MODEL` 改成 `claude-opus-4-8` 意味着 D:\code 下所有项目（量化系统、协作命令、健康检查）都跟着升级。如果某天发现中转站 `claude-opus-4-8` 暂不可用，需要回滚此文件。
2. **中转站可能尚未上线 4-8 别名** — lumos 中转的 `/winky/claude/v1` 端点接受哪些 model id 我们没查证。如果中转还只支持 `claude-opus-4-7`，调用会 404。**建议落地前用 `python scripts/health_check.py` 探活一次**；若 Claude 那家挂了就先把 .env.local 的 CLAUDE_MODEL 回滚到 4-7 待中转上线。
3. **`run.bat` 30 秒就绪超时偏短** — 首次运行需建 venv + pip install（2-5 分钟），第一次启动会跑 TIMEOUT 分支。脚本会显示"check logs"但不会自动重试。建议首次运行手动等 pip install 完，再触发第二次。
4. **PowerShell 执行策略** — Win11 默认 ExecutionPolicy 是 `Restricted`，用户跑 .ps1 必须加 `-ExecutionPolicy Bypass`，否则会报 "execution of scripts is disabled"。这个用法已写在 .ps1 注释里，但用户可能不看。

## 反方观点

- **A 方案只是"看起来像应用，本质还是命令行 + 浏览器"** — 双击图标弹的是 cmd 黑窗口 + Chrome，关一个剩一个，关错就崩。真要"app form"的话 C 方案（Tauri WebView 套壳）是正解：单窗口、原生托盘、关闭即退出、不依赖浏览器。A 是过渡，不是终点。
- **价格表跟实际不同步是惯例风险** — Anthropic 官方 4-8 的实际定价我们没查（中转站本身价格也不透明），`budget_tracker.py` 里用 `{"input": 15.0, "output": 75.0}` 是 4-7 的旧报价继续用。如果 4-8 实际更贵，月预算 $10 可能触线更早。需要在第一次跑完后用 `current_usage()` 校准。

## 置信度

**中**。
- 单元测试 1347 全绿、桌面快捷方式生成 + .bat 启动序列在 Windows 11 上是常见 pattern，逻辑层信心高。
- 但**没有 end-to-end 跑过一次**——没双击 .bat 看 streamlit 是否真的起得来（用户得自己跑一次确认），也没探活 lumos 中转 `claude-opus-4-8` 是否被识别。
- 改变结论的证据：用户首次双击启动失败 → 看 `logs\streamlit_run.log` 定位；或 health_check.py 报 Claude 那家 404 → 中转还没上线 4-8。

## 归档

本档：`docs/decisions/2026-05-30-impl-app-launcher-and-llm-upgrade.md`

启动方式：
1. 在 PowerShell 跑：`powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcut.ps1`
2. 之后双击桌面「心理分析系统」即可启动
3. 关命令行窗口 = 退出
