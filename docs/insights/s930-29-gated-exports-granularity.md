# GATED_EXPORTS 文件级粒度归因材料

> 产出单：s930-29（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-53 遗留（GATED_EXPORTS["app.py"] 文件级粒度掩盖 app.py 三枚未门禁问卷按钮——证据 6；panel 裁决完洞仍在）。
> **零改动**；测试件与 app.py 只读。

## 一、粒度掩盖机制复现（实证）

门禁件 `tests/test_export_gate_global_scan.py`：
- `GATED_EXPORTS = {"app.py": "主应用论文导出（已接入 export_gate）", …}`（:33-37）——**键＝文件**；
- `test_gated_files_have_export_gate_import`（:96 起）：对 GATED_EXPORTS 每文件断言「全文含 `export_gate` 字样」——**app.py 只要有一处 export_gate（实况 ：2325-2331，论文预览 tab 的 render_export_gate）就整文件绿**；
- ⇒ 三枚问卷按钮的「未过 gate」状态被文件级粒度**合法掩盖**——矿源证据 6 复现成立（本班按 15 行邻窗实测更严：**4 枚按钮全部 15 行窗无 gate**，其中 ：355 为中间产物性质可豁免）。

## 二、app.py 四枚 download_button 逐枚定性（现点行号）

| 行号 | 按钮 | 定性 | 应属名单 |
|---|---|---|---|
| :355 | 「💾 下载快照文件」（workspace 快照 json） | 中间产物/开发辅助（与 WHITELIST 的 app_pages_text「课程作业包」同型） | WHITELIST（补注） |
| :2257 | 问卷报告下载（问卷设计报告 .docx） | **正式交付面**（问卷报告给被试/导师） | GATED（应过 export_gate） |
| :2269 | （问卷第二格式） | 同上 | GATED |
| :2296 | （问卷第三格式） | 同上 | GATED |

真门禁位：仅 ：2325-2331（`render_export_gate` 在论文预览 tab）——「已接入 export_gate」的文件级描述对问卷三按钮**不成立**。

## 三、归因结论与处置选项

**根因＝门禁名单的键粒度（文件级）小于按钮粒度（按钮级）**：一个文件内「已门禁的论文导出」与「未门禁的问卷导出」并存时，文件级断言只能全绿。处置选项：

| 案 | 内容 | 成本 |
|---|---|---|
| **粒度降级**：GATED_EXPORTS 值改「文件→按钮清单」结构，`test_gated_files_have_export_gate_import` 逐按钮查「15 行邻窗有 gate 或按钮参数含 gate 结果」 | app.py 拆 4 键＋门禁件断言改写 | 中（结构变更+既有 sem 面适应） |
| **拆名单**：app.py 的问卷三按钮移 NEEDS_MIGRATION（待迁移名单，红面显性） | 名单两条目＋app.py 三按钮接 gate（真门禁化） | 高（要真接 gate——行为面） |
| **注释级**：GATED_EXPORTS["app.py"] 描述改为「仅论文 tab 已接 gate；问卷三按钮未门禁（见 s930-29）」 | 一行描述 | 零（诚实化但无守卫力） |

**建议**：粒度降级（案 1）是治本形状；问卷三按钮是否接 gate＝行为面人工闸（它们是「给被试/导师的问卷报告」，门禁语义=效应量检查，对问卷报告是否适用需统计规范裁决——本材料不代裁）。
