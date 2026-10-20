# assumption_router 口径冲突与登记实况对拍材料

> 产出单：s930-18（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-21 遗留（登记口径与 s927-24 对齐；同一仓两套口径风险）。
> **零码改动**；assumption_router.py 与测试快照零触碰。

## 一、I-2/I-5 实现值 vs 注册表现值对拍表

| 点 | 实现值（附行号原文） | 注册表现值（name 原文） | 冲突形状 |
|---|---|---|---|
| **I-2 样本量**（multiple_regression） | `regression.py:166` `if n < (k + 1) * 10:` ⇒ `:167` 告警（**10×(k+1)** 口径已实算） | `assumption_router.py:280-286`「样本量充足（常见口径每预测变量 ≥10–20 例）」＋kind=_placeholder | **实现已算、登记仍 placeholder＋name 口径（10–20）与实现（10×(k+1)）不同**——双重错位 |
| **I-2 VIF 共线性** | `regression.py:127-132` `vif = _calc_vif(clean[ivs])`、`vif[vif["VIF"] > 10]` 告警（**VIF>10 判据已实算**） | `assumption_router.py:282` 等五处 `_ph("自变量间无严重多重共线性（VIF）")`（multiple_regression/hierarchical 等 kind=_placeholder） | **VIF 已实算被登记 placeholder**——s927-21 断言现值复现成立 |
| **I-5 样本量**（sem） | `sem.py:71` `if result.n_obs < len(available) * 5:` ⇒ `:72-73` 告警（**5×观测变量数**） | 注册表 name「常见口径 ≥10–20×自由参数」＋kind=placeholder；**test_assumption_router.py:233 钉 `len(s.existing_checks) == 0`（sem 全 placeholder）** | 口径不同源＋钉桩反向锁定（翻 kind 必先翻钉） |
| assumptions.py 缺失机制 | **零条目**（s927-21 断言；本班未复算逐条，口径沿用） | —— | 与 s927-24 对齐面 |

## 二、口径统一两路径（含连带面）

| 路径 | 改动面 | 连带面（三向判等） |
|---|---|---|
| **路径甲：只改 name**（kind 维持 placeholder，登记文本订正为实现口径） | assumption_router.py：I-2 name「10–20 例」→「10×(k+1) 例」、I-5 name→「5×观测变量数」、VIF 五处 name 加「（regression.py 已实算 VIF>10 告警）」——纯文案 | 快照：注册表 hash 变 ⇒ assumption 快照全变（三向判等的 registry 侧更新）；KNOWN_ISSUES：无；测试：不碰 :233（kind 未动）✅ |
| **路径乙：改 kind=existing**（接线真实现，登记升「已实现」） | assumption_router.py：I-2/VIF/I-5 五处 kind→existing＋check 函数接线（引用 regression.py 的实算产物而非新造） | 快照：同上全变；**KNOWN_ISSUES**：placeholder 债销 N 条（s927-24 债表联动）；**测试**：:233 `existing_checks == 0` 必红须同笔翻（I-5）＋三向判等的 existing 计数面全动——**改动面最大但债表真实收敛** |

## 三、建议（统计规范口径不代裁）

1. **两段式**：先路径甲（name 口径订正，纯文案零行为）——把「登记骗人」的最小面先治；路径乙（kind 接线）随 s927-24 债表批一起走（其人工闸点：I-2 该不该从 10×(k+1) 改 20×，属统计规范域）；
2. VIF 是**最强接线候选**（实算已在仓内，kind=existing 只是指向修正，同 s927-24 §P0 球形先例）——若主班给一个「指向修正」快速通道，VIF 五处可先行；
3. I-5 的 :233 钉是反向锁——路径乙必须同笔翻钉（与 s930-01/02 翻面纪律同构）。
