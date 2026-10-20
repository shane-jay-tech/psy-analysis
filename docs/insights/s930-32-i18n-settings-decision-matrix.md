# i18n×settings 键位并轨与归类矛盾：一页决策矩阵

> 产出单：s930-32（exec-shift-20261002-0151）｜2026-10-02
> 四悬决：s924-11（并轨方案 A/B/C）·s927-56（22 键取侧勾选表）·s927-60（cronbach 差集案 A/B）·归类矛盾（mean/reliability）。
> **零码改动**；i18n/settings/测试零触碰。22 处逐条清单见 s927-56-drift22-decisions.md §三（勾选表现成，本单不重复）。

## 一、决策矩阵（四悬决×依赖×连带面）

| 悬决 | 内容一句话 | 依赖 | 连带面（改动时必动） |
|---|---|---|---|
| **D1 并轨方案**（s924-11） | A=4 生产+1 测试／B=2~3 生产+1 测试／C=1 新哨兵测试+0 生产 | **被 app.py 在途锁**：A/B 的 import 面要改 app.py:33 ⇒ 排 app.py 收单后；C 首版必带豁免清单（22 键现状必红）＋`test_i18n.py:112` 的 `==106` 计数钉同笔改字面 | test_i18n.py:112；豁免清单维护 |
| **D2 取侧勾选**（s927-56） | 22 键逐键「取 i18n/取 settings/不判」——建议侧已按三判据排好（运行时生效＞测试钉＞频次），勾选表现成 | **依赖 D1**：取侧落地方式由 D1 决定（方案 A=改 settings 侧、B=删 settings 键走 i18n、C=不并轨只勾不落）；**🔴 两键不判**：ave（统计量 vs 构念名）、chi_square（符号 vs 名字，s924-11 人工项） | `test_i18n.py` 4 处 parametrize 钉（:55/:56/:58/:59/:63/:64 六键命中）；取 i18n 侧不删 settings 同键 ⇒ 死值留表（下轮盘点复报 22——须与「没改」区分，本行即矿源提醒） |
| **D3 cronbach 差集**（s927-60 案 A/B） | cronbach_alpha 三形态（克隆巴赫α信度/Cronbach's α信度分析/Cronbach's α（内部一致性））差集处置 | **依赖 D2 的 F5 家族勾选**（cohens/fleiss/mcdonald/cronbach 四键必须同族同形态，否则 κ 家族互斥关系不清） | 与 D2 同批落地 |
| **D4 归类矛盾**（mean/reliability） | 同键在「均值类」与「信度类」归类表位置冲突 | **依赖 D2**（先定键权威侧，归类表随权威侧对齐） | 归类表文件（随 D2 落地面） |

## 二、决策依赖图（文字版）

```
app.py 收单（在途解锁）
      │
      ▼
D1 并轨方案（A/B/C 三选一）
      │
      ▼
D2 取侧勾选（22 键按 D1 的机制落地；🔴 ave/chi_square 两键留人工）
      │
      ├──► D4 归类矛盾（随 D2 权威侧对齐）
      └──► D3 cronbach 差集（随 D2 的 F5 家族形态，与 D2 同批）
```

**唯一串行根**＝app.py 收单 ⇒ D1。D2 的**勾选**（人工过表）不被 app.py 阻塞（勾选是决策不是落地）——主班可先勾 D2，落地等 D1。

## 三、零改动声明与复跑命令

i18n/settings/test_i18n/interpretation 全部零触碰；22 键现状复跑命令（s927-56 §一原文）：`PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -c "from config.settings import get_test_name;print(get_test_name('cfa'),get_test_name('chi_square'))"`。
