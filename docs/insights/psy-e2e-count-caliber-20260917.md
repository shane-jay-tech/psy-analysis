# psy KNOWN_ISSUES E2E 跳过口径取证（916p-a4-002，2026-09-17）

## 三条实测（命令与尾行原文同段）

```
$ .venv/Scripts/python.exe -m pytest --collect-only -q -m "playwright"
12/2674 tests collected (2662 deselected) in 10.47s
$ .venv/Scripts/python.exe -m pytest --collect-only -q -m "e2e"
25/2674 tests collected (2649 deselected) in 11.07s
$ .venv/Scripts/python.exe -m pytest -q -rs -m "playwright or e2e"
26 skipped, 2649 deselected in 10.22s（SKIPPED 原因=Playwright not installed，无 error）
（原始输出：tmp/a4-002-skip.log）
```

## 口径判定（排除法）

- 「25」＝**e2e 标记项数**（collect -m e2e 恰为 25）——旧值口径是 e2e 单标记收集数。
- playwright 标记 12 项（其中 12 项与 e2e 项重叠？并集实跑 26=25+1，说明 playwright-only 有 1 项不在 e2e 内、且 e2e 25 项均含 playwright 或纯 e2e）。
- **当次实际跳过数＝26**（e2e∪playwright 并集全 skip，原因=Playwright not installed，无 error）。

## 订正（KNOWN_ISSUES.md:103，diff ≤3 行）

「25 项明确跳过」→「26 项明确跳过（e2e∪playwright 标记项实测，2026-09-17；复现命令同行）」，并补「安装 Playwright 后本行及 :138 行作废」。:138 环境边界表 Playwright 行语义仍成立（未装→跳过），已由 :103 的作废条款覆盖。

## 验收对照

- ✅ 旧值 25/新值 26/复现命令/口径名四件套。- ✅ git diff --stat 仅 KNOWN_ISSUES.md。- ✅ 改动 ≤3 行。- ✅ rg "25 项明确跳过" 命中 0。
