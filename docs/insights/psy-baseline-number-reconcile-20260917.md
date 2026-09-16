# psy 测试基线数字「2544」三文档对账（916p-a4-001，2026-09-17）

## 一、官方 venv 解释器实测（命令与尾行原文同段）

```
$ .venv/Scripts/python.exe -m pytest --collect-only -q -m "not online"
2644/2674 tests collected (30 deselected) in 19.18s      ← 收集项现值 2644

$ .venv/Scripts/python.exe -m pytest -q -m "not online and not e2e and not benchmark"
2585 passed, 1 skipped, 89 deselected in 162.49s          ← 通过数现值 2585
```

## 二、对账表（每个出现点：旧值/新值/证据/处置）

| 出现点 | 旧值 | 新值 | 处置 |
|---|---|---|---|
| KNOWN_ISSUES.md:38 | v5.10 当前 2544 个离线收集项 | **2644**＋同行追加复现命令 | 改 ✓ |
| docs/SYSTEM_REPORT.md:20 | 2544 个离线收集项 | 2644 | 改 ✓ |
| docs/SYSTEM_REPORT.md:225 | 2544 | 2644 | 改 ✓ |
| docs/SYSTEM_REPORT.md:366 | 2544 | 2644 | 改 ✓ |
| docs/SYSTEM_REPORT.md:425 | 2544 collected | 2644 collected | 改 ✓ |
| docs/SYSTEM_OPTIMIZATION_COMPLETION_AUDIT.md:20 | 2544 项离线收集 | 保留＋标注「历史值；实测 2644」 | 标注 ✓ |
| docs/decisions/2026-08-24…v510.md:116 | 2544 个离线项目 | 保留＋标注「历史值」 | 标注 ✓ |
| docs/history/UPGRADE_REPORT_V5.10.md:52 | 2544 条离线测试收集基线 | 保留＋标注「历史值」 | 标注 ✓ |
| docs/history/UPGRADE_REPORT_V5.10.md:71 | 2544 items | 保留＋标注「历史值」 | 标注 ✓ |
| tests/fixtures/golden_stats/advanced/hlm_low_icc.csv:52/99 | 数值巧合（1.425447…） | — | 豁免：golden fixture 数据文件，非文档主张，标注会破坏 fixture |

## 三、脚本重生成路径的发现（待拍板）

`scripts/generate_system_report.py --collect-pytest` 重生成后 `--check` 报「expected '2509' not found in report」——脚本内置期望值 2509 本身过期（又一处漂移），且重生成未实际写回 SYSTEM_REPORT（模式判定待核）。故本单按官方 collect 命令实测值手工订正四处，脚本内置期望值修正留日间。

## 四、验收对照

- ✅ rg "2544" 剩 6 行＝4 行已标「历史值」＋2 行 fixture 数据豁免（报告说明）。
- ✅ KNOWN_ISSUES.md:38 数字 2644 与 collect 尾行 2644 逐字一致，复现命令同行。
- ✅ git diff --stat 仅 docs 域 5 文件（KNOWN_ISSUES/SYSTEM_REPORT/AUDIT/decisions/history），不含 src/ 与 tests/。
- ✅ 不装包、不联网、不 push；系统 python 未使用（venv 解释器）。
