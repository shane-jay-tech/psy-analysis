# result errors 警告面 str/dict 双形态契约统一裁决材料（7575 遗留）——s1004-35

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T10:5x ｜ 性质：契约变更只出材料不落码
> 矿源：`zcode-bridge/done/20260925-120713-7575.result.md:139-141`（遗留 3 逐字核对在册）。

## 一、写点普查（修正 grep 模式后闭合：写点总和=命中数）

`$ grep -rn 'errors"\]\.append\|errors\.append\|errors"\]\.extend\|errors\.extend' src/ app.py --include="*.py"` → **105 命中**，分流：

| 形态 | 写点数 | 分布 |
|---|---|---|
| dict（`{"severity","message"}`） | **50**（单行）＋**21**（跨行字面量，`append({` 换行——初轮模式漏判已修正） | **全部在 runner.py**；抽样 :73/:421-424 逐字核实含 severity/message |
| str 直入 result 面 | **0**（`errors"].append("` 0 命中；`append(str(e`/`append(e` 0；`extend` 0；`+=`/整体赋值 0） | — |
| str 但属**其他面** | 34 | dimensions_paste_parser(11，自述「解析失败不抛异常只返回 errors_list」:16-17)／items_upload_panel(6)／upstream_panel(5)／review_queue_ui(3)／method_catalog(3，本地校验列表)／routing(2)／deliverable_center_panel(2)／privacy_ethics(1)／env_check(1，status["errors"]) |

**DQ 警告源**：`data_quality.py:172/:191/:195` report.warnings 为 **str 形态**，但唯一入面路径经 `runner.py:919-920` wrapper `{"severity": "warning", "message": w}` **转成 dict**（逐字核实）。

### ⚠ 漂移修正（7575 前提现值不复现）

7575（9/25）所记「errors 里 str 与 dict 混用」——**result 面写侧现值（10-05）已全 dict**（0 处 str 直入写点）。双解释如实并记：①9/25 后写侧已收敛（71 处 dict 化）；②7575 所指「别处」实为上表其他面（各文件局部 errors_list 互不相通）。result 面未定位到「str 写点」现值位。

## 二、消费面逐处标形态假设

| 消费点 | 代码 | 形态假设 |
|---|---|---|
| app.py:1190-1194 | `err["severity"]` → st.error/st.warning 分级 | **dict-only（str 进来即 TypeError 崩）** |
| undergrad_wizard.py:3071-3076 | `err["severity"]` 同款分级渲染 | dict-only |
| undergrad_wizard.py:1841-1846 | `err.get("message","")` 正态/方差齐关键词匹配 | dict-only（str 无 .get 即 AttributeError） |
| next_step_engine.py:127 | `isinstance(i, dict) and i.get("level")` | isinstance 容错（但消费的是 issues 面，非 result errors） |
| readiness_scorer.py:255 | `getattr(i,"level")` or `isinstance(i,dict)` | 同上（issues 面） |

「校验器两种都接受并分别判型」（7575 第二句）——现值最接近的即上两处 isinstance 判型（issues 面）；**result 面现值未见双型兼容校验器**（如实记：7575 所指校验器现值位未定位到）。

## 三、统一两案改动面对照

| 案 | 动作 | 改动面估算 | 迁移风险 |
|---|---|---|---|
| A 全 dict 收敛（推荐） | 写侧已达成（0 str 写点）⇒ 剩余：①契约测试 1 件钉「result errors 元素必含 severity+message 键」②3 处 dict-only 消费点**维持现状**（契约闭环后无需防御）③runner:919 DQ wrapper 注释钉为「唯一 str→dict 转换边界」 | ≈1 测试件＋2-3 行注释 | **≈0**（现状即 dict；唯一残余面=未来新代码误入 str，由契约测试拦截） |
| B 全 str 收敛 | runner 71 写点拆 dict→str＋丢 severity 分级 | ≈74 处＋3 消费点降级重写＋快照面翻红 | 高：丢失 error/warning 分级（3 消费点靠它分流渲染），明确不推荐 |

## 四、裁决建议（留主班）

- **推荐案 A**（事实上已是现网形态，只差把事实钉成契约）：契约测试＋wrapper 边界注释即可，零迁移；
- 顺带修口径注：7575 的「混用」担忧对 **issues 面**（next_step/readiness 的 str/dict 双型容忍）仍然成立——若主班要统一到 issues 面，属另单（其消费面/写点集与 result 面不同，本材料不越界）。

### 证据存根

- `$ grep -rn …105 命中` 分流三表（命令与计数内联）。
- `$ sed -n 421,424p src/analysis/runner.py`（跨行 dict 逐字）；`$ sed -n 918,923p`（DQ wrapper 逐字）；`$ grep -n "warnings.append" src/analysis/data_quality.py` → :172/:191/:195 str 源。
- 消费面：`$ sed -n 3069,3078p src/ui/undergrad_wizard.py`＋`$ sed -n 1188,1196p app.py`＋`$ sed -n 1834,1846p` 逐字。
- 禁令守约：契约变更零落码。
