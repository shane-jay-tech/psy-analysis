# export_feedback_package UI 不可达 × 交付入口矩阵 并案裁决材料（1b5e 遗留）——s1004-46

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T02:2x ｜ 性质：只读取证，不接线不删码
> 矿源：`zcode-bridge/done/20260925-154310-1b5e.result.md:101`（遗留逐字核对在册：「UI 不可达 ⇒ 反馈面整条为零，与交付入口矩阵不同族，建议并案裁决」）。

## 一、调用面全量取证（rg 计数内联）

`$ rg -n "export_feedback_package" src/ app.py tests/ --include="*.py"` → **全域 3 命中**：

| 位置 | 性质 |
|---|---|
| `src/utils/usage_logger.py:7` | 模块 docstring 里的用法示例（非真调用） |
| `src/utils/usage_logger.py:222` | `def export_feedback_package(output_dir=None) -> Path`（唯一定义） |
| `tests/test_privacy_archive_usage.py:242` | 唯一真调用（测试件） |

**app.py 与 src/ui/ 命中＝0** ⇒ 1b5e「UI 不可达」复核成立：用户提交反馈这条产品假设现网**零通路**，函数本体（写 usage_summary/error_summary/environment_diagnosis/README 四件到 `feedback_package/` 目录）处于死码态。

## 二、交付入口矩阵对照（新增行：反馈包族）

矩阵档 `docs/insights/psy-delivery-entry-matrix-20260922.md` 现覆盖 4 入口族（A 正式交付／B 作业包／C 草稿导出／D 向导出口）× 8 维度。**反馈包是第 5 族缺位**，按同表列式补一行：

| 维度 | **E 反馈包**（缺位族，现值） |
|---|---|
| 触发点 | ❌ 无任何 UI 入口（rg 实证 §一） |
| 硬门禁 | ❌ 无门禁概念（遥测诊断面，非交付物） |
| 门禁项细目 | ❌ 无 |
| 隐私预检 | ⚠️ **接线前必审**：error_summary/usage_summary 聚合面是否携带用户文本/路径片段未审计 |
| 命名（export_naming） | ❌ 固定目录名 `feedback_package/`（:227），不走 export_filename |
| 落盘方式 | ⚠️ **全仓唯一「服务端写盘」族**（`output_dir.mkdir`＋write_text，:228-241）——矩阵四族均为「浏览器下载、服务端零写入」，反馈包若接线须先定写盘策略 |
| 审计痕迹 | ❌ 自身即遥测产物，无导出事件 |
| 失败/降级语义 | ❌ 无 try/except（JSON 序列化/写盘异常直穿） |

## 三、并案两案（最小改动面清单）

| 案 | 动作 | 最小面 | 前置 |
|---|---|---|---|
| ① 接线 | 设置/诊断类页面加「生成匿名反馈包」按钮：`export_feedback_package(tmp)` → 打包 zip → `st.download_button`；~10-15 行 UI＋zip 包装 ~5 行 | 入口函数零改（签名现成）；隐私面先审（§二 ⚠ 行）；落盘改临时目录＋下载后清理，避免破坏「服务端零写入」族规 | 隐私审计＋产品决策（反馈包发到哪——本仓无上传通路，接线只解决「能导出」） |
| ② 维持死码（判实验性） | 在 usage_logger.py:222 docstring 加「实验性、无 UI 入口」标注（1 行）或列为删除候选 | 1 行 | 需主班确认「用户提交反馈」假设是否仍有效 |

## 四、裁决建议（留主班）

- **不同族确认**：1b5e 判断成立——矩阵四族是「分析结果交付」，反馈包是「遥测诊断导出」，不宜硬塞进同族门禁；建议矩阵档以 **E 列缺位行**（§二）形式并案存档，而非复用 A-D 门禁。
- **推荐**：若「匿名反馈」仍是产品假设 → 案①（先隐私审计后接线）；若已放弃 → 案②标注或删除。维持「无通路但假死码长期在库」是最差态（隐私面未审、族规已破）。
- 关联件：本单与 s1004-53（export_gate blocking_count 文案修）同属导出面，但无代码交集，可分批。

### 证据存根

- `$ rg -n "export_feedback_package" src/ app.py tests/ --include="*.py"` → 3 命中（§一表）。
- `$ sed -n 222,245p src/utils/usage_logger.py` → 函数本体四件套＋固定目录逐字。
- `$ sed -n 40,60p docs/insights/psy-delivery-entry-matrix-20260922.md` → 矩阵列式与 8 维图例逐字。
- 禁令守约：不接线不删码，仓内仅本档。
