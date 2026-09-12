# psy app.py 编排层拆分第一批报告（h912-12，2026-09-13 夜班）：隐私门搬入 src/ui/pages

任务：从 app.py（2725 行）搬出一个自包含页面单元到 ui/pages/，签名与 streamlit 调用原样、行为零变更；app.py 保留兼容入口。

## 选定单元（函数名/行号/session_state 键）

- **隐私声明首次弹窗**：app.py 原 :314-346（内联块，非函数——本次函数化为 `render_privacy_gate()`，逐字搬移）。
- 读写 session_state 键：`privacy_accepted`（读写）；经 `src.utils.user_prefs.update_pref` 持久化（懒导入原样保留）。
- 选它而非更大模式段（模式1 数据分析 :973-1783 等）的原因：隐私门零 app.py 内部依赖（仅 st+user_prefs），预算内可完整搬迁且 st.stop() 的 StopException 穿透函数栈语义不变。

## 拆分前后行数

| 文件 | 拆分前 | 拆分后 |
|---|---|---|
| app.py | 2725 | **2698**（-27） |
| src/ui/pages/privacy_gate.py | — | **42**（含模块 docstring/imports，净搬移量 ≈33 行＋包装） |

路径说明：任务书写 `ui/pages/`，实际落 `src/ui/pages/`——与仓内既有 `src.ui` 包结构对齐（src/ui/onboarding.py 等同层），import 路径 `src.ui.pages.privacy_gate`。

## 兼容入口（grep 证据，命令原文）

```
$ grep -n 'privacy_gate\|render_privacy_gate' app.py
315:# 隐私声明（首次使用时弹出）—— h912-12 拆分至 src/ui/pages/privacy_gate.py（行为零变更）
317:from src.ui.pages.privacy_gate import render_privacy_gate
319:render_privacy_gate()
```

## 冒烟与回归

- 冒烟：`./.venv/Scripts/python.exe -c "import app; from src.ui.pages.privacy_gate import render_privacy_gate; assert callable(render_privacy_gate)"` → **import app OK; render_privacy_gate callable**（bare 模式 ScriptRunContext 警告可忽略，改前同）。
- 基线：psy 仓自 c990033 起零代码变更，全量基线即 h912-06 记录 **2586 passed / 60 skipped / 0 failed**。
- 拆分后全量：`./.venv/Scripts/python.exe -m pytest` → **2586 passed, 60 skipped, 0 failed**（2:43）→ 同一命令改前后均通过 ✓。

## A/B 披露（既有失败，与本单无关）

子集筛选时 `tests/test_e2e_ui.py::TestDataUploadFlow::test_upload_csv_triggers_analysis` 失败（KeyError）。已做 stash A/B 对照：**改前（c990033 原状）同样 FAILED**——既有环境性失败，非本单引入（该用例不在全量 60 skip 名单内，属长期红但其基线全量口径 0 failed 矛盾待查：见遗留）。

> 更正：全量跑（2586 passed/0 failed）中该用例是通过的——它在 `-k "app or ui or privacy"` 子集单独跑才失败（子集运行顺序/夹具差异所致），全量口径本单零回归。A/B 对照中 stash 前后均失败属**子集运行**现象。

## 遗留问题

- e2e 子集单独运行的顺序依赖失败（全量绿、子集红）未定位根因——留日间（疑 AppTest 夹具状态串扰）。
- 下一批候选：模式段函数化（本科论文向导覆盖 :902-972 最小）、启动清理块、环境检查块。
- 任务书路径 `ui/pages/` 已按包约定落 `src/ui/pages/`（报告已注）。
