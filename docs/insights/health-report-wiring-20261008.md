# health_report 生产-消费接线取证（s1007-33）

- 日期：2026-10-08 ｜ 性质：只读取证零改码 ｜ 上游：s1007-11 遗留「生产-消费接线缺位（project_health 输出从未进 bundle）归主班核」

## 判定：**接线在位，s1007-11「从未进 bundle」系误判**（非功能缺口、非有意留白）

### 完整链路（rg 可复现）

```
src/utils/project_health.py:25   run_health_checks()                      ← 生产函数
src/ui/health_panel.py:14/111    消费 run_health_checks，写 session_state
src/ui/state_keys.py             PROJECT_HEALTH_ISSUES_KEY                ← 中转键（间接链关键）
src/ui/deliverable_center_panel.py:88-89
    health = session_state.get(PROJECT_HEALTH_ISSUES_KEY, [])
    bundle.health_report = health if health else []                  ← bundle 接线点
src/output/docx_exporter.py:1282-1285  消费 bundle.health_report
src/output/zip_exporter.py:124-130     消费（full 模式出 health_report.md）
src/paper_writer/research_deliverable.py:28/44-45/67/102    数据类与渲染消费
```

### 误判根因

- 接线为 **session_state 间接链**（run_health_checks 不直接返回给 bundle，经 `PROJECT_HEALTH_ISSUES_KEY` 中转、在交付中心组装 bundle 时挂上）——naive rg `project_health` 追不到 bundle 侧即得「从未进」假象。
- 溯源：接线点早于 097a657（2026-07-14 checkpoint 前已在码），**远早于 s1007-11 取证时点（2026-10-07T02:00）**——非后补，属漏追。

## 接线方案（若判缺口）

不适用（判定非缺口）。设计备注一条：`health if health else []` 的空默认是静默形态，消费端（research_deliverable:102 `✅/—`）已区分「有报告/无报告」展示，无假信号面；若主班要在导出层区分「未检查 vs 检查通过」，属观测性增强另单。

## 复现

```
$ grep -rn 'health_report' src --include=*.py        # 全链七件
$ grep -n 'bundle.health_report' src/ui/deliverable_center_panel.py   # :89 接线点
$ git log -S 'bundle.health_report' -- src/ui/deliverable_center_panel.py   # 溯源 ≤2026-07-14
```
