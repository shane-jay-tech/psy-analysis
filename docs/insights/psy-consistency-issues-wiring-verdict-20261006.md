# consistency_issues 就绪评分死链接线裁决材料（s1002-47，三处一体，只读）

- 承 s923-31 遗留 A/B/C。现值 rg：`consistency_issues` 生产面 4 处（deliverable_center_panel:155-157 本地变量未回写、session_reset:77 清理名单、next_step_engine:119-123 读侧、readiness_scorer `_score_consistency` 读侧）——**写方确实不存在**（死链实锤复核）。

## 一、三处一体清单（若放行方案 C 接线）

| # | 处 | 现值 | 改动 | 红名单 |
|---|---|---|---|---|
| ① | deliverable_center_panel.py:155 后 | `consistency_issues = check_consistency(bundle)` 局部变量 | +1 行 `st.session_state["consistency_issues"] = consistency_issues` | tests 读 session 隔离面（session_reset:77 在清理名单 ⇒ 会话重置后死链复活，行为一致无需改） |
| ② | paper_bundle 键 | **零写方** ⇒ next_step_engine rule 9（paper_bundle 相关）永不触发 | 裁决点：一并补写 or 明确并存理由（本单登记：rule 9 触发前提与一致性检查无数据依赖，**并存可辩护**——两规则观测不同面） | 无（零改动选项） |
| ③ | readiness_scorer.py:248-249 | `ss.get("consistency_issues", [])` 默认 `[]` ⇒ `if issues is None` 死分支 | 回写后两套口径（next_step 的 None=未运行 / scorer 的缺键=good）**同时吃同一真数据**：scorer 得真分、next_step 得真通过/失败——死分支可顺带删（+−3 行） | tests/test_readiness_scorer.py 的「未运行=80 分」例会翻（默认值改 None 语义或保留 [] 但删死分支二选一，同批） |

## 二、裁决 B（H1/H2 收紧两笔一体配对）——行号尾注清单照录

方案 A（收紧）必红 §6 前两用例；同提交必须连改三处回指注释尾注：tests/test_next_step_engine_core.py:185/:194/:214。H3 tuple 归一案加第三处 :213-214；方案 B（只加告警）第三处不动。**裁决语模板**：主班按选定方案把「两用例」改为「两用例＋N 处尾注」（N=3 方案 A；N=4 H3 归一；N=3 方案 B）。

## 三、裁决 C（同键双口径）收敛建议

| 口径 | 现状 | 收敛建议 |
|---|---|---|
| next_step_engine:120 `is None` ⇒「未通过」 | 缺键=未运行=不通过（保守） | **保留**（引擎面向「下一步动作」，未运行就该提示去运行） |
| readiness_scorer:248 缺键 `[]` ⇒「good 80 分」 | 缺键=未运行=给分（乐观） | **收敛到「未运行=不计分（N/A）」**——既非 good 也非 fail；ReadinessItem 已有 status 枚举可加 "not_run"；红名单=「未运行 80 分」例 1-2 例同批 |

- 双口径根源：两消费方对「键不存在」的语义假设相反。接线（§一①）后键恒存在（None/list 二值），缺键态仅剩「检查从未运行过」的真实形态 ⇒ 收敛后两方行为在**有数据**时天然一致（list→同判），分歧只剩未运行态且各有合理解释。

## 四、零码改自证

rg/读码＋本档；src/ 零触碰。
